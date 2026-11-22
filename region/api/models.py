"""The request and response shapes of ``/api/v1`` as pydantic models, for validation and for ``openapi.json``.

Request bodies are validated through these. Responses are written straight from the store's dicts (``Json``), so a
list of ten thousand records is never validated twice; the response models only describe them in the OpenAPI file,
from which the app's types are generated (``app/src/api/gen``, decision 9.21). Record ``data`` is any JSON object:
each kind's own schema is in ``/meta`` and is checked by the store.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Open(BaseModel):
    model_config = ConfigDict(extra="allow")


# ------------------------------------------------------------------------------------------------------- records


class Record(BaseModel):
    """A record in the get() shape (``region.core.protocols.Record``)."""

    id: str
    kind: str
    kv: int
    layer: str = Field(description="the layer the revision was read from")
    version: int
    hash: str = Field(description="content hash of {id, kind, kv, geom, data}")
    deleted: bool
    origin: str
    source: str | None = None
    by: str
    changeset: str
    created: str
    updated: str
    geom: str | None = Field(None, description="WKT in EPSG:26916 metres, snapped to 1 mm")
    data: dict[str, Any]


class RecordPage(BaseModel):
    """One page of a list: ``next`` is the ``after`` of the next page, or null on the last."""

    items: list[Record]
    next: str | None = None


class Body(BaseModel):
    """The writable part of a record (a PUT replaces it whole)."""

    model_config = ConfigDict(extra="forbid")
    data: dict[str, Any]
    geom: Any = Field(None, description="WKT (or a GeoJSON geometry) in EPSG:26916, or null")
    kv: int | None = Field(None, description="the kind version the data is written in (default: current)")
    source: str | None = None


class CreateBody(Body):
    """A new record; ``id`` is minted when absent (a ULID when given)."""

    id: str | None = None


class PatchOp(BaseModel):
    """One RFC 6902 operation; paths are relative to the body (``/data/pvi/3/z_m``)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    op: Literal["add", "remove", "replace", "move", "copy", "test"]
    path: str
    value: Any = None
    from_: str | None = Field(None, alias="from")

    def raw(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_unset=True)


class Ref(BaseModel):
    kind: str
    id: str
    role: str
    layer: str


class RefList(BaseModel):
    items: list[Ref]


class LegacyHit(BaseModel):
    kind: str
    id: str


class History(BaseModel):
    items: list[Record]


class Diff(BaseModel):
    items: list[dict[str, Any]] = Field(description="RFC 6902 operations from one version to the other")


# ---------------------------------------------------------------------------------------------------- changesets


class OpIn(BaseModel):
    """One op of a changeset (``region.core.protocols.Op``)."""

    model_config = ConfigDict(extra="forbid")
    op: Literal["create", "put", "patch", "delete"]
    kind: str
    id: str | None = None
    if_match: str | None = None
    body: Body | None = None
    patch: list[PatchOp] | None = None


class ChangesetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    layer: str = "main"
    message: str = ""
    ops: list[OpIn] = Field(min_length=1)


class WriteResult(BaseModel):
    """What a committed changeset did; ``changeset`` and ``seq`` are null when every op changed nothing."""

    changeset: str | None
    records: list[Record]
    seq: int | None


class Changeset(_Open):
    id: str
    layer: str | None
    by: str | None
    client: str | None = None
    message: str | None = None
    kind: str | None = None
    reverts: str | None = None
    created: str | None = None
    count: int | None = None
    seq: int | None = None


class ChangesetList(BaseModel):
    items: list[Changeset]


class ChangesetFull(Changeset):
    records: list[Record] = []


# -------------------------------------------------------------------------------------------------------- layers


class Layer(_Open):
    slug: str
    tier: str
    parent: str | None = None
    namespace: str | None = None
    state: str = "open"
    title: str | None = None
    note: str | None = None
    created: str | None = None
    by: str | None = None


class LayerList(BaseModel):
    items: list[Layer]


class LayerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    tier: Literal["scenario", "proposal"] = "scenario"
    parent: str = "main"
    title: str | None = None
    note: str | None = None


class PromoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = ""


class TagIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    note: str | None = None


class StateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["open", "archived"]


class Tag(_Open):
    name: str
    seq: int | None = None


class TagList(BaseModel):
    items: list[Tag]


class LayerDiffEntry(_Open):
    kind: str
    id: str
    op: str
    fields: list[str]
    ours: str | None = None
    theirs: str | None = None


class LayerDiff(BaseModel):
    items: list[LayerDiffEntry]


class Conflict(_Open):
    id: str
    reason: str | None = None
    state: str | None = None


class ConflictList(BaseModel):
    items: list[Conflict]


class ResolveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    take: Literal["ours", "theirs", "merged"]
    body: Body | None = None


# ------------------------------------------------------------------------------------------------------- imports


class Importer(_Open):
    name: str
    version: str
    namespace: str
    layer: str
    feature: str | None = None


class ImporterList(BaseModel):
    items: list[Importer]


class ImportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    importer: str
    dry_run: bool = True


class ImportRunOut(_Open):
    id: int | None = None
    importer: str
    state: str | None = None


# ---------------------------------------------------------------------------------------------------------- jobs


class ViewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    layer: str = "main"
    year: int | None = None
    month: int | None = None
    tl: str = "canon"


class ComputeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str
    scope: str
    view: str | ViewIn = Field("main|-|canon", description='a view token ("try|1931|canon") or a view object')
    priority: int = Field(1, ge=0, le=9)
    watch_s: float | None = Field(None, gt=0, description="also keep the goal fresh for this many seconds")


class ComputeOut(BaseModel):
    key: str | None
    state: Literal["hit", "queued", "running"]
    job: str | None


class LatestResult(BaseModel):
    key: str | None


class Job(_Open):
    id: str
    type: str
    scope: str
    view: str
    state: str
    progress: float | None = None
    msg: str | None = None
    key: str | None = None


class JobList(BaseModel):
    items: list[Job]


class JobLogLine(BaseModel):
    at: str
    level: str
    msg: str


class JobLog(BaseModel):
    items: list[JobLogLine]


class ResultMeta(_Open):
    key: str
    type: str
    scope: str
    status: str
    meta: dict[str, Any] = {}
    arrays: dict[str, Any] = {}


# --------------------------------------------------------------------------------------------------- ops, events


class Health(_Open):
    ok: bool
    epoch: str
    started: str


class Meta(_Open):
    """Kinds with their schemas, features, importers, job types, layers, the engine hello, the schema version and
    the server epoch."""

    kinds: list[dict[str, Any]]
    layers: list[Layer]
    epoch: str
    seq: int
    schema_version: int | None = None
    engine: dict[str, Any] | None = None
    old_hub: str


class Tiers(_Open):
    at: str
    counts: dict[str, int]
    tiers: list[dict[str, Any]]


class PollEvent(BaseModel):
    seq: int | None
    type: str
    data: dict[str, Any]


class Poll(BaseModel):
    epoch: str
    seq: int
    events: list[PollEvent]


class ClientLogIn(_Open):
    level: str = "error"
    msg: str = ""


# ---------------------------------------------------------------------------------------------------------- live


class LiveSummary(BaseModel):
    """What the status bar's Sources chip shows."""

    paused: bool
    pending: int = Field(description="sources that changed and are not yet taken in (changing, importing, paused)")
    updated: str | None = Field(None, description="when the last change was taken in (ISO 8601 UTC)")


class LiveSource(_Open):
    """One watched source: an importer's files, a data tier or the old hub's database."""

    source: str = Field(description="import:<importer> or tier:<tier>")
    label: str
    kind: Literal["import", "tier"]
    state: str = Field(description="idle, changing, waiting, importing, applied, review, held or error")
    text: str = Field(description="what happened last, in plain words")
    at: str | None = None
    changed: str | None = None
    run: int | None = None
    changeset: str | None = None
    review: int = 0
    sections: list[str] = Field(default_factory=list)
    undo: bool = Field(False, description="whether Undo this import is offered (its last import changeset stands)")


class PendingMark(BaseModel):
    type: str = Field(description="import, or the job type re-solving the section")
    scope: str
    view: str
    state: str


class LiveStatus(LiveSummary):
    enabled: bool
    settle_s: float | None = None
    poll_s: float | None = None
    sources: list[LiveSource] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    marks: list[PendingMark] = Field(default_factory=list)


class PendingList(BaseModel):
    items: list[PendingMark]


class FocusIn(BaseModel):
    """How urgent a pane's goal is: 0 for the pane in focus, 1 for an open pane, 5 when the pane closed."""

    model_config = ConfigDict(extra="forbid")
    type: str
    scope: str
    view: str = Field("main|-|canon", description="a view token")
    priority: int = Field(ge=0, le=9)


class Problem(_Open):
    """An RFC 9457 problem body."""

    type: str
    title: str
    status: int
    detail: str
    code: str
    request_id: str | None
    conflicts: list[dict[str, Any]] = []


def problems(*codes: int) -> dict[int | str, dict[str, Any]]:
    """The ``responses`` member naming the problem statuses a route answers with."""
    return {c: {"model": Problem, "description": "a problem (RFC 9457)"} for c in codes}


