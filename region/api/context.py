"""What every route works with: the ``Hub`` (the store, the scheduler, the engine, the config and the event hub of one
server), the view and the writer of a request, and the store of ``Idempotency-Key`` answers.

A route reaches the hub through ``request.app.state.hub`` (``hub_of(request)``, or the ``Depends(get_hub)``
dependency). Feature routers (``region/ext/<f>/router.py``) are mounted under ``/api/v1/x/<f>/`` and may use the
hub, or its parts as ``request.app.state.store``, ``.jobs``, ``.engine`` and ``.cfg``; they write only through the
store.

**Who writes.** ``by`` is the config's ``user`` (``ben`` by default), or the request's ``X-CR-By`` when a script
names itself (a short lowercase token such as ``claude`` or ``import:old_hub``). ``client`` is ``X-CR-Client``,
which the security middleware already requires on every write; it goes into the changeset and its events, so a tab
can skip its own echo.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import re
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastapi import Query, Request

from region.core import fsio, ids
from region.core.errors import HubError, Invalid
from region.core.view import View

if TYPE_CHECKING:
    from .events import EventHub

BY_RE = re.compile(r"^[a-z][a-z0-9_.:@-]{0,63}$")
KIND_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Idempotency:
    """Answers to requests that carried ``Idempotency-Key``, kept in memory for ``ttl_s`` (24 h), at most ``size``.

    A repeat of the same key from the same client with the same request gets the first answer again; the same key
    with another request is refused (422 ``idempotency_key_reused``); a repeat that arrives while the first is still
    running waits for it. Keys do not survive a server restart."""

    def __init__(self, *, ttl_s: float = 86400.0, size: int = 10000) -> None:
        self.ttl_s = float(ttl_s)
        self.size = int(size)
        self._done: collections.OrderedDict[tuple[str, str], tuple[float, str, Any]] = collections.OrderedDict()
        self._busy: dict[tuple[str, str], threading.Lock] = {}
        self._lock = threading.Lock()

    def run(self, client: str, key: str, fingerprint: str, fn: Any) -> tuple[bool, Any]:
        """``(replayed, answer)``: ``fn()`` once per ``(client, key)``; its answer is kept and returned again."""
        k = (client, key)
        with self._lock:
            gate = self._busy.setdefault(k, threading.Lock())
        with gate:
            try:
                with self._lock:
                    self._expire()
                    hit = self._done.get(k)
                if hit is not None:
                    _t, fp, answer = hit
                    if fp != fingerprint:
                        raise Invalid(
                            f"Idempotency-Key {key!r} was used for another request",
                            code="idempotency_key_reused",
                        )
                    return True, answer
                answer = fn()  # an error is not kept: a retry runs again
                with self._lock:
                    self._done[k] = (time.monotonic(), fingerprint, answer)
                    self._done.move_to_end(k)
                    while len(self._done) > self.size:
                        self._done.popitem(last=False)
                return False, answer
            finally:
                with self._lock:
                    if self._busy.get(k) is gate:
                        del self._busy[k]

    def _expire(self) -> None:
        cut = time.monotonic() - self.ttl_s
        while self._done:
            k, (t, _fp, _a) = next(iter(self._done.items()))
            if t >= cut:
                break
            self._done.popitem(last=False)


@dataclass
class Hub:
    """One server's parts. ``epoch`` is the server epoch sent in every SSE ``hello``: new at every start and whenever
    the database's own epoch changes (a restore), so a client's cursor never outlives either."""

    store: Any
    jobs: Any
    engine: Any
    cfg: dict[str, Any]
    epoch: str = field(default_factory=ids.new)
    started: str = field(default_factory=now_iso)
    user: str = "ben"
    idempotency: Idempotency = field(default_factory=Idempotency)
    events: EventHub | None = None
    engine_hello: dict[str, Any] | None = None
    engine_error: str | None = None
    features: list[dict[str, Any]] = field(default_factory=list)
    app: dict[str, Any] = field(default_factory=dict)
    _engine_tried: bool = False

    def engine_status(self) -> tuple[dict[str, Any] | None, str | None]:
        """``(hello, error)``: the engine's hello once known. A client given without a hello (tests, a fake) is
        asked once; serve starts the pool in the background, marks it tried and fills ``engine_hello`` itself, so
        no request waits for Node."""
        if self.engine is None:
            return None, "the hub runs without an engine (serve --no-engine)"
        if self.engine_hello is None and not self._engine_tried:
            self._engine_tried = True
            try:
                self.engine_hello = dict(self.engine.hello())
            except HubError as e:
                self.engine_error = e.detail
            except Exception as e:  # a broken engine never breaks /meta
                self.engine_error = f"{type(e).__name__}: {e}"
        return self.engine_hello, self.engine_error

    def set_engine(self, hello: dict[str, Any] | None, error: str | None) -> None:
        """The engine pool's answer (serve's background start): kept for ``/meta`` and every later hello, and sent
        to the streams already open as an ``engine`` event, since their hello said ``engine_build: null``."""
        self.engine_hello, self.engine_error = (dict(hello) if hello else None), error
        self._engine_tried = True
        if self.events is not None:
            self.events.publish("engine", {"engine_build": self.engine_build(), "error": error})

    def engine_build(self) -> str | None:
        hello = self.engine_hello
        return str(hello["engine_build"]) if hello and hello.get("engine_build") else None


def hub_of(request: Request) -> Hub:
    return request.app.state.hub


def get_hub(request: Request) -> Hub:
    """The dependency form of ``hub_of``."""
    return hub_of(request)


def view_of(
    layer: str = Query("main", description="the layer slug (main, a scenario, proposal:<slug>, import:<name>)"),
    year: int | None = Query(None, description="the view's year; absent means the present"),
    month: int | None = Query(None, ge=1, le=12, description="the view's month (needs a year)"),
    tl: str = Query("canon", description="the timeline: canon or real"),
) -> View:
    """The view of a request from ``layer``, ``year``, ``month`` and ``tl`` (decision 9.16)."""
    return View(layer=layer, year=year, month=month, timeline=tl)


@dataclass(frozen=True)
class Writer:
    by: str
    client: str | None


def writer_of(request: Request) -> Writer:
    """Who writes: ``X-CR-By`` or the config's user, and ``X-CR-Client``."""
    hub = hub_of(request)
    by = request.headers.get("x-cr-by") or hub.user
    if not BY_RE.match(by):
        raise Invalid(f"X-CR-By {by!r} is not a short lowercase token", errors=[{"path": "/headers/X-CR-By"}])
    return Writer(by=by, client=request.headers.get("x-cr-client"))


def fingerprint(*parts: Any) -> str:
    """The hash of a request for ``Idempotency``."""
    return fsio.sha256_hex(json.dumps(list(parts), sort_keys=True, ensure_ascii=False, default=str))


__all__ = [
    "BY_RE",
    "Hub",
    "Idempotency",
    "KIND_RE",
    "Writer",
    "fingerprint",
    "get_hub",
    "hub_of",
    "now_iso",
    "view_of",
    "writer_of",
]
