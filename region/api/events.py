"""Events: the SSE stream ``GET /events``, its polling fallback ``GET /events/poll``, and the ``EventHub`` that feeds
them (section 5, Events; decision 9.28).

**Durable events** (``record``, ``changeset``) are rows of the outbox in region.db. One tailer thread follows it by
``seq``: an in-process commit (``store.subscribe``) wakes it at once, and every 500 ms it reads ``PRAGMA
data_version``, which changes when another process commits (the CLI, a script, a seed import), so those writes
reach the stream within a second too. Each event goes out as ``id: <seq>``, ``event: <type>``, ``data: <json>``.
When it has passed new events on, the tailer also wakes the scheduler's invalidator.

**Ephemeral events** (``job``, ``result``, ``tier``, ``engine``) are sent once, without an id: jobs and results from
the scheduler's ``subscribe``, tiers from a scan at start and every minute on a thread of its own, so a slow tier
never holds up the outbox (and on every ``GET /tiers``), and ``engine {engine_build, error}`` when the engine pool
answers after streams opened (``Hub.set_engine``).

**Every stream** starts with ``hello {epoch, seq, engine_build}``. ``epoch`` is the server epoch: new at every start
and whenever the database's own epoch changes (a restore), so a client that sees it change resyncs. With
``Last-Event-ID`` (or ``?since=``) the stream first replays the outbox from there up to the hello's ``seq``, then
goes live; a durable event already replayed is never sent twice. ``resync {reason, seq}`` replaces the replay when
it cannot be done: ``pruned`` (the events after the client's id were pruned), ``epoch`` (the client's id is past
the end of this database, or the database was restored while the stream was open) and ``overflow`` (the client
fell more than ``queue`` events behind). A comment line (``: ping``) goes out every 15 s so the client's 60 s
silence timer never fires on a quiet hub.

``/events/poll?since=`` answers ``{epoch, seq, events: [{seq, type, data}]}`` with the same resync rules.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import threading
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

import anyio
from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import Response, StreamingResponse

from region.core import ids
from region.core.errors import HubError

from . import models as M
from .context import hub_of
from .http import json_response

if TYPE_CHECKING:
    from .context import Hub

log = logging.getLogger("region.api.events")
router = APIRouter(tags=["events"])

Item = tuple[str, int | None, str, dict[str, Any]] | None  # (durable|ephemeral|resync, seq, type, data); None ends


class EventsUnavailable(HubError):
    status = 503
    code = "events_unavailable"
    title = "Events unavailable"


def sse(event: str, data: Any, id: int | None = None) -> bytes:
    """One SSE message."""
    lines = [] if id is None else [f"id: {id}"]
    lines.append(f"event: {event}")
    lines.append("data: " + json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=str))
    return ("\n".join(lines) + "\n\n").encode("utf-8")


PING = b": ping\n\n"


class _Client:
    __slots__ = ("closed", "floor", "overflow", "queue")

    def __init__(self, size: int) -> None:
        self.queue: asyncio.Queue[Item] = asyncio.Queue(size)
        self.overflow = False
        self.closed = False
        # the seq a resync sent this client covered: durable items at or below it never enter its queue, so the
        # tailer's backlog after an overflow cannot fill the queue again with events the resync already covered
        self.floor = 0


class EventHub:
    """The outbox tailer and the fan-out to SSE clients of one server (see the module doc)."""

    def __init__(
        self,
        hub: Hub,
        *,
        poll_s: float = 0.5,
        heartbeat_s: float = 15.0,
        queue_size: int = 2000,
        tiers_s: float = 60.0,
    ) -> None:
        self.hub = hub
        self.poll_s = float(poll_s)
        self.heartbeat_s = float(heartbeat_s)
        self.queue_size = int(queue_size)
        self.tiers_s = float(tiers_s)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._clients: set[_Client] = set()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tier_thread: threading.Thread | None = None
        self._unsubscribe: list[Callable[[], None]] = []
        self._cursor = 0
        self._db_epoch = ""
        self._tiers: dict[str, Any] | None = None
        self._tier_lock = threading.Lock()
        self._closing = False
        self.running = False

    # ------------------------------------------------------------------------------------------------ lifecycle

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start following the outbox from its current end; deliver to clients on ``loop``."""
        if self.running:
            return
        self._loop = loop
        store = self.hub.store
        self._cursor = store.last_seq()
        self._db_epoch = store.epoch()
        self._stop.clear()
        self._closing = False
        self._unsubscribe.append(store.subscribe(lambda _seq: self._wake.set()))
        subscribe = getattr(self.hub.jobs, "subscribe", None)
        if callable(subscribe):
            self._unsubscribe.append(subscribe(self._job_event))
        self._thread = threading.Thread(target=self._run, name="api-events", daemon=True)
        self._thread.start()
        # The tier scan has its own thread: a tier on a sleeping drive or a network share can take seconds to
        # answer, and the outbox tailer must never wait on it.
        self._tier_thread = threading.Thread(target=self._run_tiers, name="api-tiers", daemon=True)
        self._tier_thread.start()
        self.running = True

    def stop(self) -> None:
        """End every stream and stop the tailer."""
        self.close_streams()
        self._stop.set()
        self._wake.set()
        for off in self._unsubscribe:
            with contextlib.suppress(Exception):
                off()
        self._unsubscribe.clear()
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self._tier_thread is not None:
            self._tier_thread.join(timeout=5)
        self.running = False

    def close_streams(self) -> None:
        """End every open stream, and any opened from now on (the server is shutting down)."""
        self._closing = True
        self._publish(None)

    # ------------------------------------------------------------------------------------------------- clients

    def register(self) -> _Client:
        c = _Client(self.queue_size)
        c.closed = self._closing
        self._clients.add(c)
        return c

    def unregister(self, c: _Client) -> None:
        self._clients.discard(c)

    @property
    def clients(self) -> int:
        return len(self._clients)

    def _publish(self, item: Item) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        with contextlib.suppress(RuntimeError):  # the loop is shutting down
            loop.call_soon_threadsafe(self._deliver, item)

    def _deliver(self, item: Item) -> None:
        for c in list(self._clients):
            if item is None:
                c.closed = True
                with contextlib.suppress(asyncio.QueueFull):  # wakes a waiting stream; a busy one sees closed
                    c.queue.put_nowait(None)
                continue
            if c.overflow:
                continue
            if item[0] == "durable" and item[1] is not None and item[1] <= c.floor:
                continue
            try:
                c.queue.put_nowait(item)
            except asyncio.QueueFull:
                c.overflow = True

    def publish(self, type: str, data: dict[str, Any]) -> None:
        """Send an ephemeral event (``job``, ``result``, ``tier``, ``engine``) to every open stream."""
        self._publish(("ephemeral", None, type, dict(data)))

    def _job_event(self, kind: str, payload: dict[str, Any]) -> None:
        if kind in ("job", "result"):
            self.publish(kind, payload)

    def poke(self) -> None:
        """Look at the outbox now (tests; an in-process write already does this)."""
        self._wake.set()

    # -------------------------------------------------------------------------------------------------- tailer

    def _run(self) -> None:
        store = self.hub.store
        try:
            version = store.data_version()
        except Exception:
            log.exception("events: data_version failed")
            version = None
        while not self._stop.is_set():
            woke = self._wake.wait(self.poll_s)
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                now = store.data_version()
                if woke or now != version:
                    version = now
                    self._follow()
            except Exception:
                log.exception("events: following the outbox failed")

    def _run_tiers(self) -> None:
        """Scan the data tiers at start (the baseline the first change is measured against), then every ``tiers_s``
        (a ``tier`` event for each change)."""
        try:
            if self._tiers is None:
                self.scan_tiers()
        except Exception:
            log.exception("events: the tier scan failed")
        while not self._stop.wait(self.tiers_s):
            try:
                self.scan_tiers()
            except Exception:
                log.exception("events: the tier scan failed")

    def _follow(self) -> None:
        store = self.hub.store
        epoch = store.epoch()
        last = store.last_seq()
        if epoch != self._db_epoch or last < self._cursor:
            log.warning("events: the database epoch changed (a restore); every client resyncs")
            self._db_epoch = epoch
            self.hub.epoch = ids.new()
            self._cursor = last
            self._publish(("resync", None, "resync", {"reason": "epoch", "seq": last}))
            return
        low = store.min_seq()
        if low > self._cursor + 1:
            self._cursor = last
            self._publish(("resync", None, "resync", {"reason": "pruned", "seq": last}))
            return
        moved = False
        while not self._stop.is_set():
            batch = store.events_since(self._cursor, 1000)
            if not batch:
                break
            for e in batch:
                self._publish(("durable", int(e["seq"]), str(e["type"]), e["data"]))
            self._cursor = int(batch[-1]["seq"])
            moved = True
        if moved:
            notify = getattr(self.hub.jobs, "notify", None)
            if callable(notify):
                notify()

    def scan_tiers(self) -> dict[str, Any]:
        """Scan the data tiers now; send a ``tier`` event for each change since the last scan."""
        from region import tiers as T

        reports = T.scan(self.hub.cfg)
        with self._tier_lock:
            before, self._tiers = self._tiers, reports
        if before is not None:
            for ev in T.changes(before, reports):
                self.publish("tier", dict(ev))
        return reports

    # ------------------------------------------------------------------------------------------------- streams

    async def stream(self, last_event_id: int | None) -> AsyncIterator[bytes]:
        """The bytes of one SSE connection (see the module doc)."""
        store = self.hub.store
        client = self.register()
        try:
            head = int(await anyio.to_thread.run_sync(store.last_seq))
            yield sse("hello", {"epoch": self.hub.epoch, "seq": head, "engine_build": self.hub.engine_build()})
            sent = head
            if last_event_id is not None:
                async for chunk in self._replay(last_event_id, head):
                    yield chunk
            while not client.closed:
                if client.overflow:
                    while not client.queue.empty():
                        client.queue.get_nowait()
                    client.overflow = False
                    sent = int(await anyio.to_thread.run_sync(store.last_seq))
                    client.floor = max(client.floor, sent)
                    yield sse("resync", {"reason": "overflow", "seq": sent})
                    continue
                try:
                    item = await asyncio.wait_for(client.queue.get(), timeout=self.heartbeat_s)
                except TimeoutError:
                    yield PING
                    continue
                if item is None:
                    return
                kind, seq, typ, data = item
                if kind == "durable":
                    assert seq is not None
                    if seq <= sent:
                        continue
                    sent = seq
                    yield sse(typ, data, id=seq)
                elif kind == "resync":
                    sent = int(data.get("seq") or 0)
                    yield sse("resync", data)
                else:
                    yield sse(typ, data)
        finally:
            self.unregister(client)

    async def _replay(self, after: int, head: int) -> AsyncIterator[bytes]:
        store = self.hub.store
        if after > head:
            yield sse("resync", {"reason": "epoch", "seq": head})
            return
        low = int(await anyio.to_thread.run_sync(store.min_seq))
        if after < head and (low == 0 or after < low - 1):
            yield sse("resync", {"reason": "pruned", "seq": head})
            return
        cursor = after
        while cursor < head:
            batch = await anyio.to_thread.run_sync(store.events_since, cursor, 1000)
            batch = [e for e in batch if int(e["seq"]) <= head]
            if not batch:
                break
            for e in batch:
                yield sse(str(e["type"]), e["data"], id=int(e["seq"]))
            cursor = int(batch[-1]["seq"])


def _last_id(header: str | None, since: int | None) -> int | None:
    if header is not None and header.strip().isdigit():
        return int(header.strip())
    return since


@router.get(
    "/events",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}, "description": "the event stream"}},
    summary="Server-sent events",
)
async def events(
    request: Request,
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
    since: int | None = Query(None, ge=0, description="replay after this seq (for clients that cannot send headers)"),
) -> Response:
    hub = hub_of(request)
    if hub.events is None or not hub.events.running:
        raise EventsUnavailable("the event stream is not running")
    return StreamingResponse(
        hub.events.stream(_last_id(last_event_id, since)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/events/poll", response_model=M.Poll, summary="The polling fallback of /events")
def poll(
    request: Request, since: int = Query(0, ge=0), limit: int = Query(1000, ge=1, le=10000)
) -> Response:
    hub = hub_of(request)
    store = hub.store
    last = store.last_seq()
    low = store.min_seq()
    if since > last:
        events = [{"seq": None, "type": "resync", "data": {"reason": "epoch", "seq": last}}]
    elif since < last and (low == 0 or since < low - 1):
        events = [{"seq": None, "type": "resync", "data": {"reason": "pruned", "seq": last}}]
    else:
        events = store.events_since(since, limit)
    return json_response({"epoch": hub.epoch, "seq": last, "events": events})


__all__ = ["EventHub", "EventsUnavailable", "PING", "router", "sse"]
