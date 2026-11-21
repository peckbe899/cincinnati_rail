"""Event payloads (section 5, Events): what the outbox stores and the SSE stream sends.

Each event goes out as SSE: ``id: <seq>``, then ``event: <type>``, then ``data: <json payload>``.

- ``record`` and ``changeset`` are durable: rows of the outbox (table ``event`` in ``region.db``), written in the same
  transaction as the change, replayed from ``Last-Event-ID``.
- ``job``, ``result``, ``tier`` and ``engine`` are ephemeral: sent once, never stored. After a reconnect the client
  re-reads ``/jobs?active=1``. ``engine`` goes out when the engine pool answers (or fails) after streams opened: a
  stream opened before then said ``engine_build: null`` in its hello.
- ``resync`` tells a client its cursor is no longer valid (events pruned, a new server epoch, a queue overflow): it
  re-reads what it shows. ``hello`` is the first message of every stream.

A changeset of more than ``BULK_THRESHOLD`` records emits one ``changeset`` event with ``summary: true`` and no
``record`` events (9.28).

Layers appear as slugs (``"main"``), never as row ids. ``bbox`` is ``[x0, y0, x1, y1]`` in EPSG:26916 metres.
"""

# No "from __future__ import annotations" here: TypedDict needs NotRequired evaluated to tell required keys apart.
from typing import Literal, NotRequired, TypedDict

EventType = Literal["record", "changeset", "job", "result", "tier", "engine", "resync", "hello"]
RecordOp = Literal["create", "put", "patch", "delete", "restore"]
JobState = Literal["queued", "running", "done", "failed", "cancelled"]
ResultStatus = Literal["ok", "error", "stale"]
TierStatus = Literal["missing", "partial", "present"]
ResyncReason = Literal["pruned", "epoch", "overflow"]
BBox = list[float]

DURABLE: frozenset[str] = frozenset({"record", "changeset"})
EPHEMERAL: frozenset[str] = frozenset({"job", "result", "tier", "engine"})
CONTROL: frozenset[str] = frozenset({"resync", "hello"})
BULK_THRESHOLD = 200


class RecordEvent(TypedDict):
    """One record written. ``fields`` lists the changed paths (``"data.pvi"``, ``"geom"``); ``client`` is the
    ``X-CR-Client`` of the writer, so a tab can skip its own echo."""

    seq: int
    op: RecordOp
    kind: str
    id: str
    layer: str
    version: int
    hash: str
    by: str
    client: str | None
    changeset: str
    fields: list[str]
    bbox: BBox | None


class ChangesetEvent(TypedDict):
    """One changeset committed. ``kinds`` counts its records by kind; ``summary`` is true when it stands in for the
    record events of a bulk changeset."""

    seq: int
    id: str
    layer: str
    by: str
    count: int
    kinds: dict[str, int]
    bbox: BBox | None
    summary: bool
    kind: NotRequired[str]  # edit | import | seed | revert | rebase | promote | migration | legacy
    message: NotRequired[str]
    client: NotRequired[str | None]


class JobEvent(TypedDict):
    """A job's state or progress. ``progress`` is 0 to 1; ``msg`` the stage (``"vertical"``)."""

    id: str
    type: str
    scope: str
    state: JobState
    progress: float
    msg: str
    view: NotRequired[str]  # View.token()
    key: NotRequired[str]
    error: NotRequired[str]


class ResultEvent(TypedDict):
    """A result became current for a goal. ``view`` is ``View.token()``; ``changed`` lists the chainage ranges
    ``[c0, c1]`` (metres) whose arrays differ from the previous result."""

    key: str
    type: str
    scope: str
    view: str
    status: ResultStatus
    changed: list[list[float]]


class TierEvent(TypedDict):
    """A data tier's status changed (after a scan). ``detail`` is plain text, e.g. ``"stage contours"``."""

    tier: str
    status: TierStatus
    detail: str


class EngineEvent(TypedDict):
    """The engine pool answered after the server started: the build its sidecars run (``None`` when it failed, with
    ``error`` saying why). A stream whose hello said ``engine_build: null`` takes the build from here."""

    engine_build: str | None
    error: str | None


class ResyncEvent(TypedDict):
    """The client's cursor is gone: re-read, then follow from ``seq``."""

    reason: ResyncReason
    seq: int


class HelloEvent(TypedDict):
    """The first message of a stream: the server ``epoch`` (new on every server start and database restore), the
    newest ``seq``, and the engine build the server's sidecars run (``None`` when the engine is unavailable)."""

    epoch: str
    seq: int
    engine_build: str | None


EVENT_PAYLOADS: dict[str, type] = {
    "record": RecordEvent,
    "changeset": ChangesetEvent,
    "job": JobEvent,
    "result": ResultEvent,
    "tier": TierEvent,
    "engine": EngineEvent,
    "resync": ResyncEvent,
    "hello": HelloEvent,
}


def required_keys(event_type: str) -> frozenset[str]:
    """The keys a payload of ``event_type`` must carry (for tests and the SSE writer's assertions)."""
    return frozenset(EVENT_PAYLOADS[event_type].__required_keys__)


__all__ = [
    "BBox",
    "BULK_THRESHOLD",
    "CONTROL",
    "ChangesetEvent",
    "DURABLE",
    "EPHEMERAL",
    "EVENT_PAYLOADS",
    "EngineEvent",
    "EventType",
    "HelloEvent",
    "JobEvent",
    "JobState",
    "RecordEvent",
    "RecordOp",
    "ResultEvent",
    "ResultStatus",
    "ResyncEvent",
    "ResyncReason",
    "TierEvent",
    "TierStatus",
    "required_keys",
]
