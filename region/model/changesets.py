"""Changesets: every write is one atomic changeset, validated in full before anything is written (decision 9.13).

``Txn`` plans and writes one changeset on one layer, on a connection already inside a write transaction (the writer
thread's), in three phases:

1. **Plan.** Each op is resolved against the layer's chain and the changeset's own pending revisions. If-Match is
   checked against the resolved revision (``"<layer>:<version>"``); every stale op is collected, so one
   ``PreconditionFailed`` lists them all. Bodies become validated content (``records.content``). A write identical
   to what resolves is a no-op: no version, no event. A delete applies its referrers' ``on_delete``.
2. **Validate** against the final state of the changeset: refs resolve (so a changeset may hold records that refer
   to each other in any order), the namespace of an import layer, authority, then the feature validators.
3. **Write** the rows, their history (``rec_hist``, in get() shape), their refs, the outbox events and the changeset
   row, all in the caller's transaction. A changeset of more than 200 records writes one summary event instead of
   one event per record (9.28).

The first write to a record held below copies it up, with ``base_hash`` set to the revision it was made from. On a
scenario or proposal layer the copy-up continues the record's lineage: its version is the base revision's version + 1,
so the versions one view shows only ever increase (the ETag still names the new layer). Elsewhere (main, legacy and
import layers) a layer's first revision of a record is version 1.
``revert`` undoes a changeset as a new ``revert`` changeset, with If-Match on what the original produced. Undoing a
layer's first revision of a record (its copy-up) writes the base's content again as the next version; the copy-up's
row stays, so the record's version still only increases.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from region.core import ids
from region.core.errors import Conflict, Invalid, NotFound, PreconditionFailed, PreconditionRequired
from region.core.events import BULK_THRESHOLD
from region.core.protocols import Op, WriteResult, etag, parse_etag
from region.core.view import View

from . import layers as L
from . import refs as R
from .db import now
from .kinds import Kind
from .query import list_rows
from .records import SELECT, Content, Rev, changed_fields, content, dumps

if TYPE_CHECKING:
    from .store import SqliteStore

# the tiers whose copy-ups continue the lineage of the revision below (version = base version + 1)
LINEAGE_TIERS = frozenset({"scenario", "proposal"})

ORIGIN_OF = {
    "edit": "authored",
    "import": "import",
    "seed": "seed",
    "revert": "authored",
    "rebase": "rebase",
    "promote": "promote",
    "migration": "migration",
    "legacy": "legacy",
}


# The changesets an import or legacy layer takes: its importer's, the rebases (and conflict resolutions) that carry
# changes from below into the old hub's revisions, an authority flip, and migrations.
BUILT_LAYER_WRITES = frozenset({"import", "rebase", "legacy", "migration"})


@dataclass
class InternalOp:
    """An op only the store makes: a restore, a rebase or seed write with an explicit base, a seeded tombstone.

    ``op`` is ``create``, ``put``, ``patch``, ``delete`` or ``restore``; ``version`` is the version a restore reads;
    ``base`` overrides the new revision's ``base_hash`` (``""`` clears it); ``tombstone`` writes the body as a
    tombstone even when nothing resolves (a seeded deletion); ``force`` writes a revision on the layer even when its
    content equals what resolves from below (a squash into main).
    """

    op: str
    kind: str
    id: str | None
    if_match: str | None
    body: dict[str, Any] | None = None
    patch: list[dict[str, Any]] | None = None
    version: int | None = None
    base: str | None = None
    tombstone: bool = False
    check_match: bool = True
    force: bool = False
    prepared: Content | None = None


@dataclass
class Pending:
    """One revision the changeset will write on its layer."""

    index: int | None
    op: str
    kind: Kind
    id: str
    before: Rev | None
    own: Rev | None
    content: Content
    deleted: bool
    base: str | None
    source: str | None
    noop: bool = False
    written: dict[str, Any] | None = None
    force: bool = False


def _raw_content(kind: Kind, rev: Rev) -> Content:
    """The content of an existing revision without re-validating it (for tombstones of it)."""
    data = rev.data
    cols = {
        c: None
        for c in (
            "name",
            "system",
            "parent",
            "c0",
            "c1",
            "ord",
            "phase",
            "open_lo",
            "open_hi",
            "close_lo",
            "close_hi",
            "x0",
            "y0",
            "x1",
            "y1",
        )
    }
    cols.update(kind.columns_of(data))
    try:
        opened, closed = kind.dates_of(data)
    except Invalid:
        opened = closed = None
    cols["open_lo"], cols["open_hi"] = opened if opened else (None, None)
    cols["close_lo"], cols["close_hi"] = closed if closed else (None, None)
    if rev.bbox:
        cols["x0"], cols["y0"], cols["x1"], cols["y1"] = rev.bbox
    return Content(kind.name, rev.id, rev.kv, rev.geom, data, rev.hash, cols, kind.refs_of(data), rev.bbox)


def _content(kind: Kind, id: str, op: Any) -> Content:
    prepared = getattr(op, "prepared", None)
    if prepared is not None and prepared.id == id and prepared.kind == kind.name:
        return prepared
    return content(kind, id, op.body)


def _bbox_union(boxes: Iterable[tuple[float, float, float, float] | None]) -> list[float] | None:
    have = [b for b in boxes if b]
    if not have:
        return None
    return [min(b[0] for b in have), min(b[1] for b in have), max(b[2] for b in have), max(b[3] for b in have)]


class Ctx:
    """``region.core.protocols.ValidateCtx`` over a changeset being validated: reads see its pending revisions."""

    def __init__(self, txn: Txn) -> None:
        self.txn = txn
        self.view = txn.view

    def get(self, kind: str, id: str) -> dict[str, Any] | None:
        p = self.txn.pending.get(id)
        if p is not None:
            return None if p.deleted or p.kind.name != kind else self.txn.shape(p)
        r = self.txn.resolve(id)
        if r is None or r.deleted or r.kind != kind:
            return None
        return r.record(self.txn.layers.slugs[r.layer])

    def list(self, kind: str, **filters: Any) -> list[dict[str, Any]]:
        k = self.txn.store.kinds[kind]
        filters.pop("limit", None)
        filters.pop("after", None)
        rows, _ = list_rows(
            self.txn.con, self.txn.layers.slugs, self.txn.chain, k, self.view.instant(), limit=10**9, **filters
        )
        out = {r["id"]: r for r in rows if r["id"] not in self.txn.pending}
        for p in self.txn.pending.values():
            if p.kind.name == kind and not p.deleted and _matches(p, filters):
                out[p.id] = self.txn.shape(p)
        return [out[i] for i in sorted(out)]


def _matches(p: Pending, f: dict[str, Any]) -> bool:
    c = p.content
    if f.get("parent") is not None and c.cols.get("parent") != f["parent"]:
        return False
    if f.get("ids") is not None and p.id not in set(f["ids"]):
        return False
    if f.get("q") and f["q"].lower() not in str(c.cols.get("name") or "").lower():
        return False
    if f.get("ref") is not None and f["ref"] not in {v for _r, v, _s, _a in c.refs}:
        return False
    if f.get("bbox") is not None:
        if c.bbox is None:
            return False
        x0, y0, x1, y1 = f["bbox"]
        if c.bbox[2] < x0 or c.bbox[0] > x1 or c.bbox[3] < y0 or c.bbox[1] > y1:
            return False
    return True


class Txn:
    """One changeset on ``view.layer`` (see the module doc). ``run(ops)`` plans, validates and writes it."""

    def __init__(
        self,
        store: SqliteStore,
        con: sqlite3.Connection,
        view: View,
        *,
        by: str,
        message: str = "",
        client: str | None = None,
        kind: str = "edit",
        origin: str | None = None,
        import_run: int | None = None,
        reverts: str | None = None,
        on_delete: bool = True,
        validators: bool = True,
        dangling: str = "refuse",
    ) -> None:
        if not isinstance(by, str) or not by:
            raise Invalid("every write names who made it (by)", errors=[{"path": "/by", "message": "required"}])
        self.store = store
        self.con = con
        self.view = view
        self.by = by
        self.message = message or ""
        self.client = client
        self.cs_kind = kind
        self.import_run = import_run
        self.reverts = reverts
        self.on_delete = on_delete
        self.run_validators = validators
        # "refuse": a ref that does not resolve to a live record of its kinds fails the changeset (409 reference);
        # "list": the revision is written and the refs are kept in self.dangling (a seed import, which mirrors
        # a state an import below left on purpose and lists it as a dangling_ref conflict)
        if dangling not in ("refuse", "list"):
            raise Invalid(f"dangling is refuse or list, not {dangling!r}")
        self.dangling_mode = dangling
        self.dangling: list[dict[str, Any]] = []
        self.layers = L.load(con)
        self.layer = self.layers.get(view.layer)
        if self.layer.state != "open":
            raise Conflict(
                f"layer {self.layer.slug} is {self.layer.state} and takes no writes",
                reason="layer",
                conflicts=[{"kind": "layer", "id": self.layer.slug}],
            )
        self.chain = self.layers.chain(view.layer)
        self.below = self.chain[1:]
        if origin is None:
            origin = "legacy" if (kind == "import" and self.layer.tier == "legacy") else ORIGIN_OF.get(kind, "authored")
        self.origin = origin
        self.pending: dict[str, Pending] = {}
        self.order: list[Pending] = []
        self.op_ids: list[str] = []
        self.stale: list[dict[str, Any]] = []
        self._resolved: dict[str, Rev | None] = {}
        self._authority: dict[str, str | None] = {}
        self.changeset: str | None = None

    # ------------------------------------------------------------------------------------------------ resolution

    def resolve(self, id: str) -> Rev | None:
        """The revision of ``id`` that resolves on this layer's chain before the changeset (tombstones included)."""
        if id not in self._resolved:
            self._resolved[id] = L.resolve(self.con, self.chain, id)
        return self._resolved[id]

    def own(self, id: str) -> Rev | None:
        r = self.resolve(id)
        if r is not None and r.layer == self.layer.id:
            return r
        return None

    def current(self, id: str) -> tuple[str, bool, dict[str, Any] | None] | None:
        """``(kind, deleted, body)`` of ``id`` with the changeset's pending revisions applied."""
        p = self.pending.get(id)
        if p is not None:
            return p.kind.name, p.deleted, p.content.body()
        r = self.resolve(id)
        if r is None:
            return None
        return r.kind, r.deleted, None

    def shape(self, p: Pending) -> dict[str, Any]:
        """The get() shape the pending revision will have."""
        own = p.own
        return {
            "id": p.id,
            "kind": p.kind.name,
            "kv": p.content.kv,
            "layer": self.layer.slug,
            "version": self.version_of(p),
            "hash": p.content.hash,
            "deleted": p.deleted,
            "origin": self.origin,
            "source": p.source,
            "by": self.by,
            "changeset": "",
            "created": own.created if own else None,
            "updated": None,
            "geom": p.content.geom,
            "data": p.content.data,
        }

    def version_of(self, p: Pending) -> int:
        """The version the pending revision is written as: the next on this layer's own revision; for a copy-up into
        a scenario or proposal layer the base revision's version + 1 (the lineage continues); else 1."""
        if p.own is not None:
            return p.own.version + 1
        if self.layer.tier in LINEAGE_TIERS and p.before is not None and p.before.layer != self.layer.id:
            return p.before.version + 1
        return 1

    def etag_of(self, r: Rev | None) -> str | None:
        return etag(self.layers.slugs[r.layer], r.version) if r is not None else None

    # ----------------------------------------------------------------------------------------------------- plan

    def _matches_if(self, index: int | None, op: Any, cur: Rev | None) -> bool:
        if not getattr(op, "check_match", True):
            return True
        if op.if_match is None:
            raise PreconditionRequired(
                f"{op.op} of {op.kind} {op.id} needs If-Match (its ETag)",
                kind=op.kind,
                id=op.id,
                etag=self.etag_of(cur),
            )
        tag = op.if_match.strip()
        if tag == "*":
            ok = cur is not None and not cur.deleted
        else:
            layer, version = parse_etag(tag)
            ok = cur is not None and self.layers.slugs[cur.layer] == layer and cur.version == version
        if not ok:
            self.stale.append(
                {"index": index, "kind": op.kind, "id": op.id, "if_match": op.if_match, "etag": self.etag_of(cur)}
            )
        return ok

    def _add(self, p: Pending) -> Pending:
        if p.id in self.pending:
            raise Invalid(
                f"{p.kind.name} {p.id} is written twice in one changeset",
                errors=[{"path": f"/ops/{p.index}", "message": "one op per record"}],
            )
        self._set_noop(p)
        self.pending[p.id] = p
        self.order.append(p)
        return p

    @staticmethod
    def _set_noop(p: Pending) -> None:
        """Mark ``p`` a no-op when it would write what already resolves (run again after on_delete changes it)."""
        before = p.before
        forced = p.force and (p.own is None)
        p.noop = not forced and before is not None and before.deleted == p.deleted and before.hash == p.content.hash

    def _base_for(self, before: Rev | None, own: Rev | None, override: str | None) -> str | None:
        if override is not None:
            return override or None
        if own is not None:
            return own.base_hash
        if before is not None and not before.deleted and before.layer != self.layer.id:
            return before.hash
        return None

    def plan(self, ops: Iterable[Op | InternalOp]) -> None:
        """Phases 1 and 2; raises the first class of error found (428, 412 with every stale op, 404, 409, 422)."""
        for index, op in enumerate(ops):
            self._plan_op(index, op)
        if self.stale:
            first = self.stale[0]
            cur = self.resolve(first["id"]) if first["id"] else None
            diff = None
            current = None
            if cur is not None:
                current = cur.record(self.layers.slugs[cur.layer])
                diff = self._diff_from(first["if_match"], cur)
            raise PreconditionFailed(
                f"{len(self.stale)} op(s) carry a stale If-Match; the first, {first['kind']} {first['id']}, is now "
                f"{first['etag']}",
                current=current,
                by=cur.by if cur else None,
                diff=diff,
                stale=self.stale,
            )
        if self.on_delete:
            self._apply_on_delete()
        self._validate()

    def _diff_from(self, if_match: str | None, cur: Rev) -> list[dict[str, Any]] | None:
        import jsonpatch

        if not if_match or if_match.strip() == "*":
            return None
        try:
            slug, version = parse_etag(if_match)
        except Invalid:
            return None
        layer = self.layers.by_slug.get(slug)
        if layer is None:
            return None
        base = L.hist_row(self.con, layer.id, cur.id, version)
        if base is None:
            return None
        return list(jsonpatch.make_patch({"data": base["data"], "geom": base["geom"]}, cur.body()))

    def _plan_op(self, index: int, op: Any) -> None:
        kind = self.store.kinds[op.kind]
        name = op.op
        if name == "create":
            if op.if_match is not None and getattr(op, "check_match", True):
                raise Invalid(
                    "a create carries no If-Match",
                    errors=[{"path": f"/ops/{index}/if_match", "message": "must be null"}],
                )
            rid = op.id
            if rid is None:
                if self.layer.tier == "import":
                    raise Invalid(
                        "records on an import layer carry stable ids (ids.stable or IdLookup)",
                        errors=[{"path": f"/ops/{index}/id", "message": "required on import layers"}],
                    )
                rid = ids.new()
            self._check_id(index, rid)
            before = self.resolve(rid)
            if before is not None and not before.deleted:
                raise Conflict(
                    f"{kind.name} {rid} exists ({self.etag_of(before)})",
                    reason="exists",
                    conflicts=[{"kind": before.kind, "id": rid, "etag": self.etag_of(before)}],
                )
            if before is not None and before.kind != kind.name:
                raise Conflict(
                    f"id {rid} belongs to a {before.kind}",
                    reason="exists",
                    conflicts=[{"kind": before.kind, "id": rid}],
                )
            c = _content(kind, rid, op)
            own = self.own(rid)
            tomb = bool(getattr(op, "tombstone", False))
            self.op_ids.append(rid)
            self._add(
                Pending(
                    index,
                    "create",
                    kind,
                    rid,
                    before,
                    own,
                    c,
                    tomb,
                    self._base_for(before, own, getattr(op, "base", None)),
                    (op.body or {}).get("source"),
                )
            )
            return
        if op.id is None:
            raise Invalid(
                f"a {name} names the record's id", errors=[{"path": f"/ops/{index}/id", "message": "required"}]
            )
        self._check_id(index, op.id)
        internal = isinstance(op, InternalOp)
        cur = self.resolve(op.id)
        if cur is None:
            if not (internal and op.tombstone and op.body is not None):
                raise NotFound(f"no {kind.name} {op.id} in layer {self.layer.slug}", kind=kind.name, id=op.id)
        elif cur.kind != kind.name:
            raise NotFound(f"no {kind.name} {op.id} (the id belongs to a {cur.kind})", kind=kind.name, id=op.id)
        elif cur.deleted and not internal:
            raise NotFound(
                f"no {kind.name} {op.id} in layer {self.layer.slug} (it is deleted)", kind=kind.name, id=op.id
            )
        self.op_ids.append(op.id)
        if not self._matches_if(index, op, cur):
            return
        own = self.own(op.id)
        base = self._base_for(cur, own, getattr(op, "base", None))
        body = op.body if isinstance(op.body, dict) else None
        source = body["source"] if body is not None and "source" in body else (cur.source if cur else None)
        tomb = bool(getattr(op, "tombstone", False))
        if name == "put":
            c = _content(kind, op.id, op)
            self._add(
                Pending(
                    index, "put", kind, op.id, cur, own, c, tomb, base, source, force=bool(getattr(op, "force", False))
                )
            )
        elif name == "patch":
            c = content(kind, op.id, self._patched(index, cur, op.patch))
            self._add(Pending(index, "patch", kind, op.id, cur, own, c, False, base, source))
        elif name == "delete":
            # a store-made delete may carry the tombstone's body (a seeded deletion keeps the seed's data)
            if internal and op.body is not None:
                c = _content(kind, op.id, op)
            else:
                c = _raw_content(kind, cur) if cur is not None else content(kind, op.id, op.body)
            self._add(Pending(index, "delete", kind, op.id, cur, own, c, True, base, source))
        elif name == "restore":
            c = content(kind, op.id, self._version_body(cur, op.version) if op.body is None else op.body)
            self._add(Pending(index, "restore", kind, op.id, cur, own, c, False, base, source))
        else:
            raise Invalid(f"unknown op {name!r}", errors=[{"path": f"/ops/{index}/op", "message": "unknown"}])

    def _check_id(self, index: int, rid: Any) -> None:
        if not ids.is_ulid(rid):
            raise Invalid(f"{rid!r} is not a ULID", errors=[{"path": f"/ops/{index}/id", "message": "ULID"}])

    def _patched(self, index: int, cur: Rev | None, patch: Any) -> dict[str, Any]:
        import jsonpatch
        import jsonpointer

        if not isinstance(patch, list):
            raise Invalid(
                "a patch is an RFC 6902 JSON Patch (a list of operations)",
                errors=[{"path": f"/ops/{index}/patch", "message": "list expected"}],
            )
        assert cur is not None
        try:
            body = jsonpatch.apply_patch(cur.body(), patch)
        except (
            jsonpatch.JsonPatchException,
            jsonpointer.JsonPointerException,
            TypeError,
            KeyError,
            IndexError,
            ValueError,
        ) as e:
            raise Invalid(
                f"the patch does not apply: {e}", errors=[{"path": f"/ops/{index}/patch", "message": str(e)}]
            ) from None
        if not isinstance(body, dict) or set(body) - {"data", "geom"}:
            raise Invalid(
                "a patch changes only /data and /geom",
                errors=[{"path": f"/ops/{index}/patch", "message": "paths start /data or /geom"}],
            )
        return body

    def _version_body(self, cur: Rev | None, version: int | None) -> dict[str, Any]:
        if cur is None or version is None:
            raise Invalid("a restore names a version")
        row = L.lineage_row(self.con, self.chain, cur.layer, cur.id, int(version))
        if row is None:
            raise NotFound(f"no version {version} of {cur.kind} {cur.id} on layer {self.layers.slugs[cur.layer]}")
        return {"data": row["data"], "geom": row["geom"], "kv": row["kv"]}

    # ------------------------------------------------------------------------------------------------ on_delete

    def _apply_on_delete(self) -> None:
        queue = [p.id for p in self.order if p.deleted and not p.noop]
        restrict: list[dict[str, Any]] = []
        seen: set[str] = set()
        while queue:
            dst = queue.pop(0)
            if dst in seen:
                continue
            seen.add(dst)
            for src, role in self._referrers(dst):
                p = self.pending.get(src)
                if p is not None and p.deleted:
                    continue
                rev = self.resolve(src) if p is None else None
                if p is None and (rev is None or rev.deleted):
                    continue
                kname = p.kind.name if p is not None else rev.kind  # type: ignore[union-attr]
                if kname not in self.store.kinds:
                    continue
                kind = self.store.kinds[kname]
                specs = [s for s in kind.refs if s.role == role]
                if not specs:
                    continue
                action = specs[0].on_delete
                if action == "restrict":
                    restrict.append({"kind": kname, "id": src, "role": role, "dst": dst})
                elif action == "cascade":
                    if p is not None:
                        p.deleted = True
                        p.op = "delete"
                        self._set_noop(p)
                    else:
                        assert rev is not None
                        own = self.own(src)
                        self._add(
                            Pending(
                                None,
                                "delete",
                                kind,
                                src,
                                rev,
                                own,
                                _raw_content(kind, rev),
                                True,
                                self._base_for(rev, own, None),
                                rev.source,
                            )
                        )
                    queue.append(src)
                elif action == "nullify":
                    body = p.content.body() if p is not None else rev.body()  # type: ignore[union-attr]
                    data = body["data"]
                    for s in specs:
                        for at, value in s.values(data):
                            if value == dst:
                                data = R.set_at(data, at, None)
                    new = content(kind, src, {"data": data, "geom": body["geom"]})
                    if p is not None:
                        p.content = new
                        self._set_noop(p)
                    else:
                        assert rev is not None
                        own = self.own(src)
                        self._add(
                            Pending(
                                None, "put", kind, src, rev, own, new, False, self._base_for(rev, own, None), rev.source
                            )
                        )
        if restrict:
            first = restrict[0]
            raise Conflict(
                f"{first['kind']} {first['id']} refers to {first['dst']} ({first['role']}, restrict); "
                f"{len(restrict)} ref(s) stand in the way",
                reason="reference",
                conflicts=restrict,
            )

    def _referrers(self, dst: str) -> list[tuple[str, str]]:
        """``(src, role)`` of every record that, as the changeset leaves it, refers to ``dst``."""
        out: set[tuple[str, str]] = set()
        for layer_id, src, role in R.referrers(self.con, self.chain, dst):
            if src in self.pending:
                continue
            rev = self.resolve(src)
            if rev is not None and rev.layer == layer_id:
                out.add((src, role))
        for p in self.pending.values():
            if p.deleted:
                continue
            for role, value, _spec, _at in p.content.refs:
                if value == dst:
                    out.add((p.id, role))
        return sorted(out)

    # ------------------------------------------------------------------------------------------------- validate

    def authority_owner(self, kind: str) -> str | None:
        """``legacy`` or ``model`` when an ``authority`` record for ``kind`` resolves in main's chain (with this
        changeset's pending revisions), else ``None``. The record on the highest layer wins."""
        if kind in self._authority:
            return self._authority[kind]
        if "authority" not in self.store.kinds:
            self._authority[kind] = None
            return None
        chain = self.layers.chain("main")
        rank = {c.id: i for i, c in enumerate(chain)}
        marks = ",".join("?" * len(chain))
        best: dict[str, tuple[int, bool, str]] = {}
        for rid, layer_id, deleted, data in self.con.execute(
            f"SELECT r.id, r.layer, r.deleted, r.data FROM rec r WHERE r.kind = 'authority' AND r.layer IN ({marks})",
            tuple(rank),
        ).fetchall():
            cur = best.get(rid)
            if cur is None or rank[layer_id] < cur[0]:
                best[rid] = (rank[layer_id], bool(deleted), data)
        mine = self.layer.id in rank
        found: list[tuple[int, str, Any]] = []
        for rid, (rk, deleted, text) in best.items():
            p = self.pending.get(rid) if mine else None
            if p is not None:
                if p.deleted:
                    continue
                data, rk = p.content.data, rank[self.layer.id]
            elif deleted:
                continue
            else:
                data = json.loads(text)
            if data.get("kind") == kind:
                found.append((rk, rid, data.get("owner")))
        if mine:
            for p in self.pending.values():
                if (
                    p.kind.name == "authority"
                    and p.id not in best
                    and not p.deleted
                    and p.content.data.get("kind") == kind
                ):
                    found.append((rank[self.layer.id], p.id, p.content.data.get("owner")))
        found.sort(key=lambda f: (f[0], f[1]))
        owner = found[0][2] if found else None
        self._authority[kind] = owner
        return owner

    def _authority_ok(self) -> bool:
        """Writes exempt from the authority check: the flip itself, the legacy importer, and rebases (and conflict
        resolutions) on the legacy layer, which only carry changes from the imports below into the old hub's own
        revisions."""
        if self.cs_kind == "legacy":
            return True
        return self.layer.tier == "legacy" and self.cs_kind in ("import", "rebase")

    def _validate(self) -> None:
        live = [p for p in self.order if not p.noop]
        dangling: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for p in live:
            if self.layer.tier == "import":
                ns = ids.namespace_of(p.id)
                if ns != self.layer.namespace:
                    raise Conflict(
                        f"layer {self.layer.slug} owns namespace {self.layer.namespace!r}; {p.kind.name} {p.id} is "
                        f"{'in namespace ' + repr(ns) if ns else 'an authored id'}",
                        reason="namespace",
                        conflicts=[{"kind": p.kind.name, "id": p.id, "namespace": ns}],
                    )
            if self.layer.tier in ("main", "legacy") and p.kind.name != "authority" and not self._authority_ok():
                if self.authority_owner(p.kind.name) == "legacy":
                    raise Conflict(
                        f"the old hub owns {p.kind.name} records (authority legacy); write them in a "
                        f"scenario, or flip the authority to model",
                        reason="authority",
                        conflicts=[{"kind": p.kind.name, "id": p.id}],
                    )
            if self.layer.tier in ("import", "legacy") and self.cs_kind not in BUILT_LAYER_WRITES:
                # the next run of the layer's importer replaces or tombstones whatever it does not yield, so an
                # authored write there would vanish without a conflict
                raise Conflict(
                    f"layer {self.layer.slug} is rebuilt by its importer, so a write there ({self.cs_kind}) would be "
                    "lost at the next import; write in main, a scenario or a proposal",
                    reason="layer",
                    conflicts=[{"kind": p.kind.name, "id": p.id, "layer": self.layer.slug}],
                )
            if p.deleted:
                continue
            for role, value, spec, at in p.content.refs:
                where = "/data" + "".join(f"/{s}" for s in at)
                if value is None:
                    if spec.required:
                        errors.append({"path": where, "message": f"ref {role} is required"})
                    continue
                if not isinstance(value, str):
                    errors.append({"path": where, "message": f"ref {role} must be a record id"})
                    continue
                cur = self.current(value)
                if cur is None or cur[1] or cur[0] not in spec.kinds:
                    dangling.append(
                        {
                            "kind": p.kind.name,
                            "id": p.id,
                            "role": role,
                            "dst": value,
                            "expected": list(spec.kinds),
                            "path": where,
                        }
                    )
        if errors:
            raise Invalid("; ".join(f"{e['path']}: {e['message']}" for e in errors[:5]), errors=errors)
        if dangling and self.dangling_mode == "list":
            self.dangling = dangling
        elif dangling:
            d = dangling[0]
            raise Conflict(
                f"{d['kind']} {d['id']} refers to {d['dst']} ({d['role']}), which is not a live "
                f"{' or '.join(d['expected'])} in layer {self.layer.slug}",
                reason="reference",
                conflicts=dangling,
            )
        if self.run_validators:
            validators = self.store.validators
            if validators:
                ctx = Ctx(self)
                for p in live:
                    fn = validators.get(p.kind.name)
                    if fn is None or p.deleted:
                        continue
                    for e in fn(self.shape(p), ctx) or []:
                        errors.append(
                            {
                                "path": e.get("path", ""),
                                "message": e.get("message", ""),
                                "rule": e.get("rule"),
                                "id": p.id,
                            }
                        )
                if errors:
                    raise Invalid("; ".join(f"{e['path']}: {e['message']}" for e in errors[:5]), errors=errors)

    # ---------------------------------------------------------------------------------------------------- write

    def _write(self, p: Pending, cs: str, t: str) -> dict[str, Any]:
        c = p.content
        cols = c.cols
        data_text = dumps(c.data)
        common = (
            c.kv,
            c.hash,
            p.base,
            int(p.deleted),
            self.origin,
            p.source,
            self.by,
            cs,
            self.import_run,
            t,
            cols["name"],
            cols["system"],
            cols["parent"],
            cols["c0"],
            cols["c1"],
            cols["ord"],
            cols["phase"],
            cols["open_lo"],
            cols["open_hi"],
            cols["close_lo"],
            cols["close_hi"],
            cols["x0"],
            cols["y0"],
            cols["x1"],
            cols["y1"],
            c.geom,
            data_text,
        )
        version = self.version_of(p)
        if p.own is not None:
            created = p.own.created
            self.con.execute(
                "UPDATE rec SET version = ?, kv = ?, hash = ?, base_hash = ?, deleted = ?, origin = ?, source = ?, "
                "by = ?, changeset = ?, import_run = ?, updated = ?, name = ?, system = ?, parent = ?, c0 = ?, "
                "c1 = ?, ord = ?, phase = ?, open_lo = ?, open_hi = ?, close_lo = ?, close_hi = ?, x0 = ?, y0 = ?, "
                "x1 = ?, y1 = ?, geom = ?, data = ? WHERE rid = ?",
                (version, *common, p.own.rid),
            )
        else:
            created = t
            self.con.execute(
                "INSERT INTO rec (layer, id, kind, version, created, kv, hash, base_hash, deleted, origin, source, "
                "by, changeset, import_run, updated, name, system, parent, c0, c1, ord, phase, open_lo, open_hi, "
                "close_lo, close_hi, x0, y0, x1, y1, geom, data) VALUES (" + ", ".join("?" * 32) + ")",
                (self.layer.id, p.id, p.kind.name, version, created, *common),
            )
        record = {
            "id": p.id,
            "kind": p.kind.name,
            "kv": c.kv,
            "layer": self.layer.slug,
            "version": version,
            "hash": c.hash,
            "deleted": p.deleted,
            "origin": self.origin,
            "source": p.source,
            "by": self.by,
            "changeset": cs,
            "created": created,
            "updated": t,
            "geom": c.geom,
            "data": c.data,
        }
        self.con.execute(
            "INSERT INTO rec_hist (layer, id, version, hash, changeset, at, by, row) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (self.layer.id, p.id, version, c.hash, cs, t, self.by, dumps(record)),
        )
        R.write_rows(self.con, self.layer.id, p.id, [] if p.deleted else R.rows_for(c.refs))
        p.written = record
        return record

    def commit(self) -> WriteResult:
        """Phase 3: write every pending revision, the events and the changeset row."""
        writes = [p for p in self.order if not p.noop]
        if not writes:
            return WriteResult(None, self._op_records(), None)
        cs = ids.new()
        t = now()
        for p in writes:
            self._write(p, cs, t)
        count = len(writes)
        summary = count > BULK_THRESHOLD
        kinds = Counter(p.kind.name for p in writes)
        boxes = []
        for p in writes:
            boxes.append(p.content.bbox)
            if p.before is not None:
                boxes.append(p.before.bbox)
        if not summary:
            rows = []
            for p in writes:
                before_body = p.before.body() if p.before is not None and not p.before.deleted else None
                fields = ["deleted"] if p.deleted else changed_fields(before_body, p.content.body())
                if p.before is not None and p.before.deleted and not p.deleted and "deleted" not in fields:
                    fields.append("deleted")
                bb = _bbox_union([p.content.bbox, p.before.bbox if p.before else None])
                payload = {
                    "op": p.op,
                    "kind": p.kind.name,
                    "id": p.id,
                    "layer": self.layer.slug,
                    "version": p.written["version"],
                    "hash": p.content.hash,
                    "by": self.by,  # type: ignore[index]
                    "client": self.client,
                    "changeset": cs,
                    "fields": fields,
                    "bbox": bb,
                }
                rows.append(
                    (
                        t,
                        "record",
                        self.layer.id,
                        p.kind.name,
                        p.id,
                        payload["version"],
                        p.content.hash,
                        p.op,
                        cs,
                        self.by,
                        self.client,
                        dumps(fields),
                        dumps(bb) if bb else None,
                        dumps(payload),
                    )
                )
            self.con.executemany(
                "INSERT INTO event (at, type, layer, kind, id, version, hash, op, changeset, by, client, fields, "
                "bbox, data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        bb = _bbox_union(boxes)
        payload = {
            "id": cs,
            "layer": self.layer.slug,
            "by": self.by,
            "count": count,
            "kinds": dict(sorted(kinds.items())),
            "bbox": bb,
            "summary": summary,
            "kind": self.cs_kind,
            "message": self.message,
            "client": self.client,
        }
        cur = self.con.execute(
            "INSERT INTO event (at, type, layer, kind, id, version, hash, op, changeset, by, client, fields, bbox, "
            "data) VALUES (?, 'changeset', ?, NULL, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?)",
            (
                t,
                self.layer.id,
                cs,
                self.cs_kind,
                cs,
                self.by,
                self.client,
                dumps(dict(sorted(kinds.items()))),
                dumps(bb) if bb else None,
                dumps(payload),
            ),
        )
        seq = int(cur.lastrowid or 0)
        self.con.execute(
            "INSERT INTO changeset (id, layer, by, client, message, kind, reverts, created, count, seq) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cs, self.layer.id, self.by, self.client, self.message, self.cs_kind, self.reverts, t, count, seq),
        )
        self.changeset = cs
        return WriteResult(cs, self._op_records(), seq)

    def _op_records(self) -> list[dict[str, Any]]:
        out = []
        for p in self.order:
            if p.index is None:
                continue
            if p.written is not None:
                out.append(p.written)
            elif p.before is not None:
                out.append(p.before.record(self.layers.slugs[p.before.layer]))
        return out

    def written(self) -> list[Pending]:
        return [p for p in self.order if p.written is not None]

    def run(self, ops: Iterable[Op | InternalOp]) -> WriteResult:
        self.plan(ops)
        return self.commit()


# ---------------------------------------------------------------------------------------------------- revert


def revert_ops(con: sqlite3.Connection, changeset: str) -> tuple[str, list[InternalOp], list[dict[str, Any]]]:
    """The layer slug and ops that undo ``changeset``, and the records whose later edits stand in the way."""
    row = con.execute("SELECT layer FROM changeset WHERE id = ?", (changeset,)).fetchone()
    if not row:
        raise NotFound(f"no changeset {changeset}")
    layers = L.load(con)
    layer = layers.by_id[row[0]]
    ops: list[InternalOp] = []
    blocked: list[dict[str, Any]] = []
    for rid, version, hist in con.execute(
        "SELECT id, version, row FROM rec_hist WHERE layer = ? AND changeset = ? ORDER BY rowid", (layer.id, changeset)
    ).fetchall():
        produced = json.loads(hist)
        cur = con.execute(f"SELECT {SELECT} FROM rec r WHERE r.layer = ? AND r.id = ?", (layer.id, rid)).fetchone()
        # If-Match on what the changeset produced, by content: a later edit blocks the undo, a later edit that was
        # itself undone does not (so an undo stack unwinds)
        if cur is None or cur[5] != produced["hash"] or bool(cur[6]) != produced["deleted"]:
            blocked.append(
                {
                    "kind": produced["kind"],
                    "id": rid,
                    "if_match": etag(layer.slug, version),
                    "etag": etag(layer.slug, cur[4]) if cur else None,
                }
            )
            continue
        tag = etag(layer.slug, cur[4])
        # the revision before it on this layer; none when the changeset made the layer's first revision of the record
        # (a create, or a copy-up, whose version continues the base's lineage and so need not be 1)
        prior = L.hist_row(con, layer.id, rid, version - 1) if version > 1 else None
        if prior is not None:
            body = {"data": prior["data"], "geom": prior["geom"], "kv": prior["kv"]}
            ops.append(InternalOp("put", produced["kind"], rid, tag, body=body, tombstone=bool(prior["deleted"])))
        else:
            below = L.resolve(con, layers.chain(layer.slug)[1:], rid)
            if below is not None and not below.deleted:
                ops.append(InternalOp("put", produced["kind"], rid, tag, body=below.body(), base=below.hash))
            else:
                ops.append(InternalOp("delete", produced["kind"], rid, tag))
    return layer.slug, ops, blocked


__all__ = ["LINEAGE_TIERS", "Ctx", "InternalOp", "ORIGIN_OF", "Pending", "Txn", "revert_ops"]
