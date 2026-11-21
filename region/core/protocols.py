"""The frozen contracts between the hub's packages (section 10, WP0, the interfaces marked with a star).

Every package codes against these and nothing else of another package: the store (WP1) implements ``Store``, the
scheduler (WP3) ``Scheduler``, ``PlanCtx`` and ``RunCtx``, the engine host (WP4) ``EngineClient``, the features
(WP5) ``Importer`` and ``JobType``, and the store's legacy index ``IdLookup``. Tests use fakes of the same shapes.

**Records.** A record crosses every boundary as a plain dict in the *get() shape* (``Record`` below): its bookkeeping
members plus ``geom`` (WKT in EPSG:26916 metres, snapped to 1 mm, or ``None``) and ``data`` (the kind's JSON). Writes
take a *body*, the writable part of a record: ``{"data": {...}, "geom": "LINESTRING (...)" | None}``. JSON Patch
paths are relative to the body (``/data/pvi/3/z_m``), so a patch can never touch bookkeeping.

**ETags and If-Match.** A record's ETag is ``"<layer>:<version>"`` with the quotes (``"main:8"``,
``"import:profiles:1"``), from ``etag()``. ``if_match`` arguments take the ETag as the client sent it; ``parse_etag``
reads it back.

**Refs.** A job's inputs are named by refs, in four forms (section 6): ``rec:<id>``, ``file:<uri>``,
``param:<path>`` and ``job:<type>/<scope>``. Build them with ``ref_rec`` and friends.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypedDict, runtime_checkable

from .errors import Invalid
from .view import Axis, View

if TYPE_CHECKING:
    import numpy as np

# ------------------------------------------------------------------------------------------------- shapes, helpers

Json = Any
Records = list[dict[str, Any]]
JsonPatch = list[dict[str, Any]]
Ref = str
RefKind = Literal["rec", "file", "param", "job"]
REF_KINDS: tuple[str, ...] = ("rec", "file", "param", "job")
OpKind = Literal["create", "put", "patch", "delete"]
Host = Literal["inline", "thread", "process", "engine"]
HOSTS: tuple[str, ...] = ("inline", "thread", "process", "engine")


class Record(TypedDict):
    """The get() shape of a record: what ``Store.get``, ``list``, ``history`` and the API return.

    ``layer`` is the slug of the layer the revision was read from (which may be below the view's layer). ``hash`` is
    the content hash: ``fsio.content_hash({"id", "kind", "kv", "geom", "data"})``, so bookkeeping never enters it
    (9.29). ``deleted`` marks a tombstone, which reads hide unless history is asked for. ``origin`` says how the
    revision was made (``import``, ``legacy``, ``authored``, ``seed``, ``rebase``, ``promote``, ``migration``);
    ``source`` is free provenance (an import run, a ruling id, a file URI).
    """

    id: str
    kind: str
    kv: int
    layer: str
    version: int
    hash: str
    deleted: bool
    origin: str
    source: str | None
    by: str
    changeset: str
    created: str
    updated: str
    geom: str | None
    data: dict[str, Any]


def etag(layer: str, version: int) -> str:
    """The ETag of a revision: ``"main:8"`` (quotes included)."""
    return f'"{layer}:{version}"'


def parse_etag(tag: str) -> tuple[str, int]:
    """``(layer, version)`` from an ETag or If-Match value (a weak ``W/`` prefix and the quotes are accepted)."""
    raw = tag.strip()
    if raw.startswith("W/"):
        raw = raw[2:]
    raw = raw.strip('"')
    layer, sep, version = raw.rpartition(":")
    if not sep or not layer or not version.isdigit():
        raise Invalid(f'{tag!r} is not a record ETag ("layer:version")')
    return layer, int(version)


def ref_rec(id: str) -> Ref:
    """``rec:<id>``: a record as resolved in the view; its hash is the record's content hash."""
    return f"rec:{id}"


def ref_file(uri: str) -> Ref:
    """``file:<uri>``: a file by ``tier://``, ``repo://`` or ``var://`` URI; its hash is the file's sha256."""
    return f"file:{uri}"


def ref_param(path: str) -> Ref:
    """``param:<path>``: a resolved param (``settings.platform_m``); its hash is the hash of the resolved value."""
    return f"param:{path}"


def ref_job(job_type: str, scope: str) -> Ref:
    """``job:<type>/<scope>``: an upstream job's result; its hash is the upstream ``output_hash``."""
    return f"job:{job_type}/{scope}"


def parse_ref(ref: Ref) -> tuple[str, str]:
    """``(kind, rest)`` of a ref: ``("rec", "01K...")``, ``("job", "profiles.solve_section/01K...")``."""
    kind, sep, rest = ref.partition(":")
    if not sep or kind not in REF_KINDS or not rest:
        raise Invalid(f"{ref!r} is not a rec:, file:, param: or job: ref")
    return kind, rest


# ---------------------------------------------------------------------------------------------------------- writes


@dataclass
class Op:
    """One operation of a changeset (``Store.write``, ``POST /changesets``).

    - ``create``: ``body`` is the new record's body; ``id`` is ``None`` (the store mints ``ids.new()``) or given
      (an import's stable id). ``if_match`` must be ``None``.
    - ``put``: ``body`` replaces the record's data and geom whole; ``if_match`` is required.
    - ``patch``: ``patch`` is RFC 6902 JSON Patch over the body; ``if_match`` is required.
    - ``delete``: writes a tombstone; ``if_match`` is required.
    """

    op: OpKind
    kind: str
    id: str | None
    if_match: str | None
    body: dict[str, Any] | None = None
    patch: JsonPatch | None = None


Ops = list[Op]


@dataclass
class WriteResult:
    """What a committed changeset did.

    ``records`` holds each op's resulting record in get() shape, in op order (a delete gives the tombstone; an op
    that changed nothing gives the record unchanged). ``changeset`` is ``None`` and ``seq`` is ``None`` when every
    op was a no-op: an identical write makes no version and no event.
    """

    changeset: str | None
    records: Records = field(default_factory=list)
    seq: int | None = None


class Source(TypedDict):
    """One input an import read: its URI and the sha256 of what was read (a file's bytes, or a folder's listing of
    ``<relpath> <sha256>`` lines)."""

    uri: str
    sha256: str


@dataclass
class ImportRun:
    """One run of an importer, as recorded in ``import_run`` (section 4)."""

    importer: str
    version: str
    layer: str
    namespace: str
    sources: dict[str, Source] = field(default_factory=dict)
    by: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.by:
            self.by = f"import:{self.importer}"


@dataclass
class ImportReport:
    """The result of ``Store.apply_import``, dry run or applied.

    ``counts`` has ``created``, ``updated``, ``unchanged``, ``deleted`` and ``conflicts``; ``by_kind`` the same per
    kind. ``changes`` lists each change as ``{"op": "create" | "put" | "delete", "kind", "id", "fields": [...]}``.
    ``conflicts`` lists conflict rows the run raised (rebase proposals, orphans, namespace). ``changeset`` is set
    when the run was applied and changed something.
    """

    importer: str
    layer: str
    dry_run: bool
    run: int | None = None
    counts: dict[str, int] = field(default_factory=dict)
    by_kind: dict[str, dict[str, int]] = field(default_factory=dict)
    changes: Records = field(default_factory=list)
    conflicts: Records = field(default_factory=list)
    changeset: str | None = None
    errors: Records = field(default_factory=list)


# ----------------------------------------------------------------------------------------------------------- store


@runtime_checkable
class Store(Protocol):
    """The record store (WP1): one truth database, layers by copy-on-write, changesets, an outbox.

    Reads resolve up the view's layer chain (the view's layer, its ancestors up to ``main``, then ``legacy:*``, then
    every ``import:*`` layer); the first revision found wins and a tombstone hides the record. Writes go only to
    ``view.layer``; the first write to a record held below copies it up. Every write belongs to one atomic changeset
    and is validated in full before anything is written.

    Errors: ``NotFound`` (unknown kind, record, layer, changeset), ``PreconditionRequired`` (no If-Match where one is
    needed), ``PreconditionFailed`` (stale If-Match), ``Conflict`` (reference, namespace, authority, revert) and
    ``Invalid`` (schema or validator failure).
    """

    def get(self, kind: str, id: str, view: View, *, at: int | None = None) -> dict[str, Any]:
        """One record as it resolves in ``view``; ``at`` reads a past version of the revision on ``view.layer``.
        ``NotFound`` for an unknown or tombstoned record."""
        ...

    def list(
        self,
        kind: str,
        view: View,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        parent: str | None = None,
        ref: str | None = None,
        ids: Iterable[str] | None = None,
        q: str | None = None,
        limit: int = 500,
        after: str | None = None,
    ) -> tuple[Records, str | None]:
        """Records of ``kind`` resolved in ``view``, open at the view's instant, filtered, ordered by id.

        ``bbox`` is ``(x0, y0, x1, y1)`` in EPSG:26916; ``parent`` matches the promoted ``parent`` column; ``ref``
        keeps records that reference that id; ``q`` searches names. Returns ``(page, cursor)`` where ``cursor`` is
        the ``after`` value of the next page, or ``None`` on the last page.
        """
        ...

    def write(self, ops: Ops, view: View, *, by: str, message: str, client: str | None = None) -> WriteResult:
        """Apply ``ops`` as one atomic changeset on ``view.layer``. A stale op makes ``PreconditionFailed`` whose
        ``stale`` lists every stale op; nothing is written unless every op is valid."""
        ...

    def put(self, rec: dict[str, Any], view: View, *, if_match: str | None, by: str) -> dict[str, Any]:
        """Replace (or create) one record: ``rec`` carries ``kind``, ``id``, ``data`` and ``geom``. ``if_match`` may
        be ``None`` only when the record does not resolve in the view (a create); otherwise it is required."""
        ...

    def patch(self, kind: str, id: str, patch: JsonPatch, view: View, *, if_match: str, by: str) -> dict[str, Any]:
        """Apply RFC 6902 JSON Patch to one record's body. Nulls in the data are kept (no merge patch)."""
        ...

    def delete(self, kind: str, id: str, view: View, *, if_match: str, by: str) -> dict[str, Any]:
        """Tombstone one record on ``view.layer`` (its data is kept in history). Refs apply their ``on_delete``."""
        ...

    def revert(self, changeset: str, *, by: str) -> WriteResult:
        """Undo a changeset as a new ``revert`` changeset, with If-Match on what the original produced, so a later
        edit to any of its records makes ``Conflict(reason="revert")``."""
        ...

    def history(self, kind: str, id: str, view: View) -> Records:
        """Every revision of the record on ``view.layer`` and the layers below it, newest first, in get() shape."""
        ...

    def restore(self, kind: str, id: str, version: int, view: View, *, if_match: str, by: str) -> dict[str, Any]:
        """Write the content of a past version as a new version."""
        ...

    def hash_of(self, ref: str, view: View) -> str | None:
        """The content hash of a ``rec:<id>`` ref as resolved in ``view``, or ``None`` when it does not resolve."""
        ...

    def events_since(self, seq: int, limit: int = 1000) -> Records:
        """Durable events (``record``, ``changeset``) with ``seq`` greater than ``seq``, oldest first, as
        ``{"seq", "type", "data"}`` where ``data`` is the payload of ``region.core.events``."""
        ...

    def legacy(self, lkind: str, key: str) -> str | None:
        """The id an old key maps to (``legacy("alignment_station", "Line_8|Cincinnati State#2")``), or ``None``."""
        ...

    def apply_import(self, run: ImportRun, records: Iterable[dict[str, Any]], *, dry_run: bool) -> ImportReport:
        """Diff an importer's records against its layer by content hash; with ``dry_run`` only report, otherwise
        commit the difference in one short transaction (an absent record becomes an import tombstone)."""
        ...


@runtime_checkable
class ValidateCtx(Protocol):
    """What a feature validator sees: the records as the changeset under validation would leave them."""

    view: View

    def get(self, kind: str, id: str) -> dict[str, Any] | None:
        """One record after the pending changeset, or ``None``."""
        ...

    def list(self, kind: str, **filters: Any) -> Records:
        """Records of ``kind`` after the pending changeset (filters as ``Store.list``)."""
        ...


Validator = Callable[[dict[str, Any], ValidateCtx], list[dict[str, Any]]]
"""A feature validator (``VALIDATORS`` in ``region/ext/<f>/validators.py``): takes one record in get() shape and
returns errors as ``{"path", "message", "rule"}`` dicts (``rule`` a registry rule id, optional). Empty means valid."""


# ------------------------------------------------------------------------------------------------------------ jobs


@dataclass
class Output:
    """What a job's ``run`` returns. ``meta`` is JSON (small numbers, summaries); ``arrays`` are named numpy arrays
    stored as content-addressed blobs and served at ``/results/{key}/a/{name}``; ``blobs`` are other bytes (GLB);
    ``issues`` are check findings as ``{"rule", "sev", "c0", "c1", "msg", "data"}`` dicts."""

    meta: dict[str, Any] = field(default_factory=dict)
    arrays: dict[str, np.ndarray] = field(default_factory=dict)
    blobs: dict[str, bytes] = field(default_factory=dict)
    issues: Records = field(default_factory=list)


@runtime_checkable
class PlanCtx(Protocol):
    """What a job's ``plan`` reads through. Every read is recorded as a ref with its content hash, and exactly
    those refs make the job's key and its dependencies (9.19). ``plan`` reads nothing any other way."""

    view: View

    def read(self, kind: str, id: str) -> dict[str, Any] | None:
        """One record as resolved in the view (ref ``rec:<id>``), or ``None``; an absence is a dependency too."""
        ...

    def list(self, kind: str, **filters: Any) -> Records:
        """Records of ``kind`` (filters as ``Store.list``); each returned record and the query are dependencies."""
        ...

    def param(self, path: str, scope: str | None = None) -> Any:
        """A param resolved by the most specific scope (section, route, system) and year (ref ``param:<path>``)."""
        ...

    def file(self, uri: str) -> Path:
        """A local file by URI (ref ``file:<uri>``, hashed by sha256 and cached by size and mtime)."""
        ...

    def need(self, job_type: str, scope_id: str) -> Ref:
        """Declare an upstream job (ref ``job:<type>/<scope>``); ``RunCtx.upstream`` hands its output to ``run``."""
        ...

    def axis(self, name: Axis) -> Any:
        """Read a view axis (``year``, ``month``, ``timeline``) and declare it: only declared axes enter the key."""
        ...


@runtime_checkable
class EngineClient(Protocol):
    """A client of the TypeScript engine (WP4: ``Pool``, ``OneShot``, ``Fake``); see ``engine/PROTOCOL.md``.

    ``call`` raises ``EngineError`` when the engine answers ``ok: false`` and ``EngineUnavailable`` when it cannot
    answer (no Node, a crash, a timeout, an unknown contract major).
    """

    def hello(self) -> dict[str, Any]:
        """The engine's hello: ``{"engine_version", "engine_build", "contracts", "methods"}``."""
        ...

    def call(self, method: str, params: dict[str, Any], *, timeout_s: float = 30.0) -> dict[str, Any]:
        """Call ``method`` (``"vertical.rail"`` or ``"vertical.rail@1"``) and return its result."""
        ...

    def close(self) -> None:
        """Stop the client's processes (closing stdin; children exit on EOF)."""
        ...


@runtime_checkable
class RunCtx(Protocol):
    """What a job's ``run`` gets besides its inputs. ``run`` is pure: it reads only ``inputs`` and this."""

    engine: EngineClient

    def progress(self, f: float, msg: str = "") -> None:
        """Report progress 0 to 1 with a stage name; call at least every 2 s."""
        ...

    def cancelled(self) -> bool:
        """True once the job is superseded or cancelled; a thread job should return soon after."""
        ...

    def upstream(self, ref: Ref) -> Output:
        """The output of an upstream job ``plan`` declared with ``need``."""
        ...


@runtime_checkable
class JobType(Protocol):
    """A job type (``JOB_TYPES`` in ``region/ext/<f>/jobs.py``), a module-level object so a process host can find it
    by name. ``plan`` reads through ``ctx`` and returns the inputs; ``run`` computes from them alone.

    - ``name``: ``"profiles.solve_section"``; ``version``: ``"1"``, bumped when outputs change meaning.
    - ``scope``: the kind of ``scope_id`` (``"section"``, ``"route"``, ``"network"``).
    - ``host``: ``inline`` (under 50 ms), ``thread`` (I/O), ``process`` (railsim), ``engine`` (the Node pool).
    - ``priority``: the default priority (0 focused pane, 1 open panes, 5 goals, 9 maintenance).
    - ``timeout_s``: killed or cancelled after this long.
    """

    name: str
    version: str
    scope: str
    host: Host
    priority: int
    timeout_s: float

    def plan(self, ctx: PlanCtx, scope_id: str) -> Any:
        """Read the inputs through ``ctx`` and return them (JSON-able, or arrays)."""
        ...

    def run(self, inputs: Any, rt: RunCtx) -> Output:
        """Compute the output from ``inputs`` alone. Never writes records or files."""
        ...


@runtime_checkable
class Scheduler(Protocol):
    """The job scheduler over ``cache.db`` (WP3)."""

    def submit(self, type: str, scope: str, view: View, priority: int = 1) -> dict[str, Any]:
        """Plan the job now and return ``{"key", "state", "job"}``: ``state`` is ``hit`` (a result exists for the
        key, ``job`` is ``None``), ``queued`` or ``running``."""
        ...

    def result(self, type: str, scope: str, view: View) -> str | None:
        """The latest result key for the goal ``(type, scope, view)``, or ``None``."""
        ...

    def watch_goal(self, type: str, scope: str, view: View, priority: int = 5, ttl_s: float | None = None) -> None:
        """Keep ``(type, scope, view)`` fresh: re-plan it whenever its dependencies change, until ``ttl_s``."""
        ...

    def cancel(self, job_id: str) -> None:
        """Cancel a queued or running job (a running process or engine job is killed after 1 s)."""
        ...

    def jobs(self, active: bool = True) -> Records:
        """Jobs as ``{"id", "type", "scope", "view", "state", "progress", "msg", "key", ...}``, newest first."""
        ...


# --------------------------------------------------------------------------------------------------------- imports


@runtime_checkable
class PathResolver(Protocol):
    """What an importer's ``sources`` gets: the ``region.core.paths`` module satisfies it."""

    def resolve(self, uri: str) -> Path:
        """The local path of a ``tier://``, ``repo://`` or ``var://`` URI (``TierMissing`` for an absent tier)."""
        ...

    def available(self, name: str) -> Literal[True] | str:
        """``True`` when the tier is here, else the plain reason."""
        ...


@runtime_checkable
class IdLookup(Protocol):
    """Match before mint (9.17), implemented over the store's legacy index and the id ledger (WP1)."""

    def id_for(
        self,
        lkind: str,
        key: str,
        *,
        kind: str,
        match: Callable[[Records], str | None] | None = None,
    ) -> str:
        """The id for old key ``key`` of legacy kind ``lkind`` (a record of ``kind``).

        In order: the persisted legacy index; then ``match``, called with the records of ``kind`` on the import
        layer that no key of this run has claimed (the orphans), returning the id of the one that is this key
        renamed (by geometry, chainage, neighbours) or ``None``; only then ``ids.stable(namespace, key)``. The
        mapping is persisted and appended to the namespace's ledger.
        """
        ...


@runtime_checkable
class Importer(Protocol):
    """An importer (``IMPORTERS`` in ``region/ext/<f>/importers.py``).

    ``sources`` names the inputs as ``{name: uri}``; the runner resolves and hashes them, then calls ``records``
    with ``{name: local path}``. ``records`` is pure: the same files give the same records, so a rerun writes
    nothing and two databases get identical ids. It yields record dicts with ``kind``, ``id`` (from ``ids``),
    ``data``, ``geom`` (WKT or ``None``) and optionally ``source``.
    """

    name: str
    version: str
    namespace: str
    layer: str

    def sources(self, paths: PathResolver) -> dict[str, str]:
        """The inputs this importer reads, as ``{name: uri}``."""
        ...

    def records(self, src: Mapping[str, Path], ids: IdLookup) -> Iterable[dict[str, Any]]:
        """The records the sources describe."""
        ...


__all__ = [
    "EngineClient",
    "HOSTS",
    "Host",
    "IdLookup",
    "ImportReport",
    "ImportRun",
    "Importer",
    "Json",
    "JsonPatch",
    "JobType",
    "Op",
    "OpKind",
    "Ops",
    "Output",
    "PathResolver",
    "PlanCtx",
    "REF_KINDS",
    "Record",
    "Records",
    "Ref",
    "RefKind",
    "RunCtx",
    "Scheduler",
    "Source",
    "Store",
    "ValidateCtx",
    "Validator",
    "WriteResult",
    "etag",
    "parse_etag",
    "parse_ref",
    "ref_file",
    "ref_job",
    "ref_param",
    "ref_rec",
]
