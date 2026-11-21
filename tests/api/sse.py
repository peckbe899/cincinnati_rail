"""A test client of ``/api/v1/events``: reads the stream on a thread and hands parsed messages to the test.

    with Stream(live.url, last_event_id=4) as s:
        hello = s.next()                         # {"id": None, "event": "hello", "data": {...}, "at": t}
        rec = s.until(lambda m: m["event"] == "record")

Comment lines (``: ping``) are counted in ``pings``. ``at`` is ``time.time()`` when the message arrived.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from collections.abc import Callable
from typing import Any


class Stream:
    def __init__(self, base: str, *, last_event_id: int | None = None, since: int | None = None) -> None:
        self.url = base + "/api/v1/events" + (f"?since={since}" if since is not None else "")
        self.headers = {"Accept": "text/event-stream", "X-CR-Client": "test-sse"}
        if last_event_id is not None:
            self.headers["Last-Event-ID"] = str(last_event_id)
        self.messages: queue.Queue[dict[str, Any]] = queue.Queue()
        self.pings = 0
        self.status: int | None = None
        self.content_type: str | None = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._read, daemon=True)

    def __enter__(self) -> Stream:
        self._thread.start()
        assert self._ready.wait(10), "the stream did not open"
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)

    def _read(self) -> None:
        import httpx

        msg: dict[str, Any] = {"id": None, "event": "message", "data": []}
        try:
            with httpx.Client(timeout=httpx.Timeout(10.0, read=5.0)) as c, c.stream(
                "GET", self.url, headers=self.headers
            ) as r:
                self.status = r.status_code
                self.content_type = r.headers.get("content-type")
                self._ready.set()
                for line in r.iter_lines():
                    if self._stop.is_set():
                        return
                    if line.startswith(":"):
                        self.pings += 1
                        continue
                    if line == "":
                        if msg["data"]:
                            data = json.loads("\n".join(msg["data"]))
                            self.messages.put({"id": msg["id"], "event": msg["event"], "data": data, "at": time.time()})
                        msg = {"id": None, "event": "message", "data": []}
                        continue
                    field, _, value = line.partition(":")
                    value = value[1:] if value.startswith(" ") else value
                    if field == "id":
                        msg["id"] = int(value)
                    elif field == "event":
                        msg["event"] = value
                    elif field == "data":
                        msg["data"].append(value)
        except Exception as e:  # the server closed the stream, or the test is over
            self.messages.put({"id": None, "event": "_closed", "data": {"error": repr(e)}, "at": time.time()})
        finally:
            self._ready.set()
        self.messages.put({"id": None, "event": "_closed", "data": {}, "at": time.time()})

    def next(self, timeout: float = 5.0) -> dict[str, Any]:
        return self.messages.get(timeout=timeout)

    def until(self, pred: Callable[[dict[str, Any]], bool], timeout: float = 5.0) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError("no matching event")
            m = self.messages.get(timeout=left)
            if pred(m):
                return m

    def drain(self, wait: float = 0.3) -> list[dict[str, Any]]:
        """Every message that arrives within ``wait`` seconds."""
        out = []
        deadline = time.monotonic() + wait
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return out
            try:
                out.append(self.messages.get(timeout=left))
            except queue.Empty:
                return out
