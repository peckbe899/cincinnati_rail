"""Three-way merge and the rebase planner (decision 9.11).

When a lower layer changes, the revisions copied up from it have a stale base. ``rebase`` finds them and, per record,
merges at the kind's merge unit:

- A change below that touches only fields Ben did not change, and no geometry, no guarded pointer (chainage), applies
  on its own: the merged revision is written as its own listed, revertible ``rebase`` changeset (one per layer).
- Any geometry or guarded change below becomes a ``geometry_under_edit`` conflict, and any overlap with fields Ben
  changed a ``both_changed`` one (a kind can name another reason for overlaps with ``x-conflict`` at the root of its
  schema, such as ``authority_divergence`` for params, 9.25). A kind whose ``merge.rebase`` is ``proposal`` turns
  every change below into a conflict. A conflict row carries a proposed revision; Ben's revision stays on read until
  he resolves it.
- A record gone below (an import tombstone) under one of Ben's revisions is an ``orphan``; a record of Ben's whose ref
  now dangles is a ``dangling_ref``.
- A merged revision the upper layer cannot take (a ref that dangles there, a kind whose authority refuses it) is a
  ``dangling_ref`` or ``invalid`` conflict carrying the proposal. An upper layer's state never makes the write below
  fail.

``merge3`` works on bodies ``{"data", "geom"}``: with unit ``field`` the parts are ``geom`` and each top-level member
of ``data``; with unit ``atomic`` the whole body is one part (a profile, per the 1 November ruling). A member absent
from a body stays absent, and a null stays null.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

from region.core import fsio, ids
from region.core.errors import Conflict, HubError, Invalid, NotFound
from region.core.protocols import etag
from region.core.view import View

from . import layers as L
from .db import now
from .kinds import MISSING, Kind
from .records import SELECT, content, dumps, rev_of

if TYPE_CHECKING:
    from .store import SqliteStore

REASONS = (
    "both_changed",
    "geometry_under_edit",
    "orphan",
    "dangling_ref",
    "invalid",
    "namespace",
    "authority_divergence",
)
TAKES = ("ours", "theirs", "merged")
SEED_RUNS = "(SELECT id FROM import_run WHERE importer = 'seed')"


def is_seed_run(con: sqlite3.Connection, import_run: int | None) -> bool:
    """Whether ``import_run`` is a seed import (whose conflicts block export)."""
    if import_run is None:
        return False
    return (
        con.execute("SELECT 1 FROM import_run WHERE id = ? AND importer = 'seed'", (import_run,)).fetchone() is not None
    )


def _same(a: Any, b: Any) -> bool:
    if a is MISSING or b is MISSING:
        return a is b
    return fsio.canonical_json(a) == fsio.canonical_json(b)


def _parts(body: dict[str, Any] | None, unit: str) -> dict[str, Any]:
    if body is None:
        return {}
    if unit == "atomic":
        return {"*": {"data": body.get("data"), "geom": body.get("geom")}}
    out: dict[str, Any] = {"geom": body.get("geom")}
    for k, v in (body.get("data") or {}).items():
        out["data." + k] = v
    return out


def _join(parts: dict[str, Any], unit: str) -> dict[str, Any]:
    if unit == "atomic":
        whole = parts.get("*", MISSING)
        return {"data": {}, "geom": None} if whole is MISSING else json.loads(json.dumps(whole))
    data = {k[5:]: v for k, v in parts.items() if k.startswith("data.") and v is not MISSING}
    geom = parts.get("geom", MISSING)
    return {"data": json.loads(json.dumps(data)), "geom": None if geom is MISSING else geom}


def merge3(
    base: dict[str, Any] | None,
    ours: dict[str, Any],
    theirs: dict[str, Any],
    *,
    unit: str = "field",
    prefer: str = "ours",
) -> tuple[dict[str, Any], list[str]]:
    """Merge two bodies against their base; return ``(merged, overlapping parts)``.

    A part changed on one side only takes that side; a part changed on both to different values is an overlap and
    takes ``prefer``'s value (``ours`` or ``theirs``). ``merge3(b, x, x) == x``, ``merge3(b, b, y) == y`` and
    ``merge3(b, x, b) == x``.
    """
    b, o, t = _parts(base, unit), _parts(ours, unit), _parts(theirs, unit)
    out: dict[str, Any] = {}
    overlaps: list[str] = []
    for key in sorted(set(b) | set(o) | set(t)):
        bv, ov, tv = b.get(key, MISSING), o.get(key, MISSING), t.get(key, MISSING)
        if _same(ov, tv):
            out[key] = ov
        elif _same(ov, bv):
            out[key] = tv
        elif _same(tv, bv):
            out[key] = ov
        else:
            overlaps.append(key)
            out[key] = ov if prefer == "ours" else tv
    return _join(out, unit), overlaps


def changed_parts(a: dict[str, Any] | None, b: dict[str, Any] | None, unit: str = "field") -> list[str]:
    """The parts that differ between two bodies."""
    pa, pb = _parts(a, unit), _parts(b, unit)
    return [k for k in sorted(set(pa) | set(pb)) if not _same(pa.get(k, MISSING), pb.get(k, MISSING))]


def _body(row: dict[str, Any]) -> dict[str, Any]:
    return {"data": row["data"], "geom": row["geom"]}


# ---------------------------------------------------------------------------------------------- conflict rows


def upsert_conflict(
    con: sqlite3.Connection,
    layer: L.Layer,
    rec_id: str,
    kind: str,
    reason: str,
    *,
    ours_hash: str | None,
    theirs_hash: str | None,
    base_hash: str | None,
    proposed: dict[str, Any] | None,
    fields: list[str],
    import_run: int | None,
) -> dict[str, Any]:
    """Open (or refresh) the conflict of ``(layer, rec_id)``: one open conflict per record and layer from the rebase
    planner, and one from seed imports. The two never replace each other, so a rebase can never close a seed change
    that is not merged yet (export refuses while one is open)."""
    if reason not in REASONS:
        raise Invalid(f"conflict reason {reason!r} is not one of {', '.join(REASONS)}")
    seed = is_seed_run(con, import_run)
    row = con.execute(
        "SELECT id FROM conflict WHERE layer = ? AND rec_id = ? AND state = 'open' AND "
        + (f"import_run IN {SEED_RUNS}" if seed else f"(import_run IS NULL OR import_run NOT IN {SEED_RUNS})"),
        (layer.id, rec_id),
    ).fetchone()
    cid = row[0] if row else ids.new()
    args = (
        layer.id,
        rec_id,
        kind,
        reason,
        ours_hash,
        theirs_hash,
        base_hash,
        dumps(proposed) if proposed is not None else None,
        dumps(fields),
        import_run,
    )
    if row:
        con.execute(
            "UPDATE conflict SET layer = ?, rec_id = ?, kind = ?, reason = ?, ours_hash = ?, theirs_hash = ?, "
            "base_hash = ?, proposed = ?, fields = ?, import_run = ? WHERE id = ?",
            (*args, cid),
        )
    else:
        con.execute(
            "INSERT INTO conflict (layer, rec_id, kind, reason, ours_hash, theirs_hash, base_hash, proposed, "
            "fields, import_run, id, state, created) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)",
            (*args, cid, now()),
        )
    return conflict_row(con, cid)


def conflict_row(con: sqlite3.Connection, cid: str) -> dict[str, Any]:
    row = con.execute(
        "SELECT c.id, l.slug, c.rec_id, c.kind, c.reason, c.ours_hash, c.theirs_hash, c.base_hash, "
        "c.proposed, c.fields, c.state, c.import_run, c.created, c.resolved_by, c.resolution "
        "FROM conflict c JOIN layer l ON l.id = c.layer WHERE c.id = ?",
        (cid,),
    ).fetchone()
    if not row:
        raise NotFound(f"no conflict {cid}")
    keys = (
        "id",
        "layer",
        "rec_id",
        "kind",
        "reason",
        "ours_hash",
        "theirs_hash",
        "base_hash",
        "proposed",
        "fields",
        "state",
        "import_run",
        "created",
        "resolved_by",
        "resolution",
    )
    out = dict(zip(keys, row, strict=True))
    out["proposed"] = json.loads(out["proposed"]) if out["proposed"] else None
    out["fields"] = json.loads(out["fields"]) if out["fields"] else []
    return out


def list_conflicts(
    con: sqlite3.Connection, *, state: str | None = "open", layer: L.Layer | None = None, import_run: int | None = None
) -> list[dict[str, Any]]:
    sql = "SELECT id FROM conflict WHERE 1 = 1"
    args: list[Any] = []
    if state is not None:
        sql += " AND state = ?"
        args.append(state)
    if layer is not None:
        sql += " AND layer = ?"
        args.append(layer.id)
    if import_run is not None:
        sql += " AND import_run = ?"
        args.append(import_run)
    return [conflict_row(con, r[0]) for r in con.execute(sql + " ORDER BY created, id", args).fetchall()]


def _dismiss(con: sqlite3.Connection, layer: L.Layer, rec_id: str) -> None:
    """Close the rebase planner's open conflict of a record that is no longer stale. Seed conflicts stay open until
    Ben resolves them or the seed and his revision agree (``seed.import_seed``)."""
    con.execute(
        "UPDATE conflict SET state = 'dismissed', resolution = 'no longer stale', resolved_by = 'rebase' "
        "WHERE layer = ? AND rec_id = ? AND state = 'open' AND (reason IN "
        "('both_changed', 'geometry_under_edit', 'orphan', 'authority_divergence', 'invalid') "
        "OR (reason = 'dangling_ref' AND proposed IS NOT NULL)) "
        f"AND (import_run IS NULL OR import_run NOT IN {SEED_RUNS})",
        (layer.id, rec_id),
    )


# ---------------------------------------------------------------------------------------------------- planner


def _overlap_reason(kind: Kind) -> str:
    reason = kind.schema.get("x-conflict") if isinstance(kind.schema, dict) else None
    return reason if reason in REASONS else "both_changed"


def rebase(
    store: SqliteStore,
    con: sqlite3.Connection,
    *,
    lower: str | None = None,
    changed: set[str] | None = None,
    import_run: int | None = None,
    by: str = "rebase",
) -> dict[str, Any]:
    """Rebase the copied-up revisions above ``lower`` (every layer when ``None``), only for ``changed`` ids when given.

    Runs inside the caller's write transaction. Returns ``{"changesets": [...], "conflicts": [...], "changes": [...]}``.
    """
    from .changesets import InternalOp, Txn

    layers = L.load(con)
    if lower is not None:
        uppers = layers.above(layers.get(lower))
    else:
        uppers = sorted((r for r in layers.by_id.values() if r.tier != "import"), key=lambda r: (layers.depth(r), r.id))
    report: dict[str, Any] = {"changesets": [], "conflicts": [], "changes": []}
    ids_now = set(changed) if changed is not None else None
    deleted_below: set[str] = set()
    if ids_now:
        for (rid,) in con.execute(
            "SELECT DISTINCT id FROM rec WHERE deleted = 1 AND id IN (SELECT value FROM json_each(?))",
            (json.dumps(sorted(ids_now)),),
        ).fetchall():
            deleted_below.add(rid)
    for upper in uppers:
        if upper.state != "open":
            continue
        chain_below = layers.chain(upper.slug)[1:]
        sql = f"SELECT {SELECT} FROM rec r WHERE r.layer = ? AND r.base_hash IS NOT NULL"
        args: list[Any] = [upper.id]
        if ids_now is not None:
            if not ids_now:
                break
            sql += " AND r.id IN (SELECT value FROM json_each(?))"
            args.append(json.dumps(sorted(ids_now)))
        ops: list[InternalOp] = []
        base_only: list[tuple[int, str]] = []
        planned: dict[str, tuple[Any, str | None, dict[str, Any], list[str]]] = {}
        for row in con.execute(sql, args).fetchall():
            ours = rev_of(row)
            if ours.kind not in store.kinds:
                continue
            kind = store.kinds[ours.kind]
            below = L.resolve(con, chain_below, ours.id)
            theirs_hash = below.hash if below is not None and not below.deleted else None
            if below is not None and not below.deleted and below.hash == ours.base_hash:
                _dismiss(con, upper, ours.id)
                continue
            if below is None or below.deleted:
                if ours.deleted:
                    continue
                c = upsert_conflict(
                    con,
                    upper,
                    ours.id,
                    ours.kind,
                    "orphan",
                    ours_hash=ours.hash,
                    theirs_hash=None,
                    base_hash=ours.base_hash,
                    proposed=None,
                    fields=[],
                    import_run=import_run,
                )
                report["conflicts"].append(c)
                continue
            base_row = L.hist_by_hash(con, ours.id, ours.base_hash or "")
            theirs = below.body()
            mine = ours.body()
            base = _body(base_row) if base_row is not None else None
            unit = kind.merge_unit
            if ours.deleted:
                c = upsert_conflict(
                    con,
                    upper,
                    ours.id,
                    ours.kind,
                    "both_changed",
                    ours_hash=ours.hash,
                    theirs_hash=theirs_hash,
                    base_hash=ours.base_hash,
                    proposed=theirs,
                    fields=changed_parts(base, theirs),
                    import_run=import_run,
                )
                report["conflicts"].append(c)
                continue
            merged, overlaps = merge3(base, mine, theirs, unit=unit, prefer="theirs")
            theirs_changed = changed_parts(base, theirs) if base is not None else ["*"]
            geometry = (
                base is None
                or not _same(base.get("geom"), theirs.get("geom"))
                or bool(kind.guard_changed(base.get("data") if base else None, theirs.get("data")))
            )
            reason = None
            if geometry:
                reason = "geometry_under_edit"
            elif base is None or overlaps:
                reason = _overlap_reason(kind)
            elif kind.rebase == "proposal":
                reason = _overlap_reason(kind)
            if reason is None:
                try:
                    c_new = content(kind, ours.id, merged)
                except Invalid:
                    reason = "invalid"
                    merged = theirs
            if reason is not None:
                c = upsert_conflict(
                    con,
                    upper,
                    ours.id,
                    ours.kind,
                    reason,
                    ours_hash=ours.hash,
                    theirs_hash=theirs_hash,
                    base_hash=ours.base_hash,
                    proposed=merged,
                    fields=overlaps or theirs_changed,
                    import_run=import_run,
                )
                report["conflicts"].append(c)
                continue
            _dismiss(con, upper, ours.id)
            if c_new.hash == ours.hash:
                base_only.append((ours.rid, below.hash))
                continue
            ops.append(
                InternalOp("put", ours.kind, ours.id, etag(upper.slug, ours.version), body=merged, base=below.hash)
            )
            planned[ours.id] = (ours, theirs_hash, merged, theirs_changed)
        for rid, h in base_only:
            con.execute("UPDATE rec SET base_hash = ? WHERE rid = ?", (h, rid))

        def rebase_txn(upper: L.Layer = upper) -> Any:
            return Txn(
                store,
                con,
                View(layer=upper.slug),
                by=by,
                message=f"rebase onto {lower or 'the layers below'}",
                kind="rebase",
                on_delete=False,
                validators=False,
            )

        if ops:
            # A merged revision this layer cannot take (its ref dangles here, or the kind's authority refuses it)
            # becomes a conflict row carrying the proposal: an upper layer's state never aborts the write below.
            try:
                rebase_txn().plan(ops)
            except HubError:
                good = []
                for op in ops:
                    try:
                        rebase_txn().plan([op])
                    except HubError as e:
                        ours, t_hash, merged, fields = planned[op.id]  # type: ignore[index]
                        why = "dangling_ref" if isinstance(e, Conflict) and e.reason == "reference" else "invalid"
                        c = upsert_conflict(
                            con,
                            upper,
                            ours.id,
                            ours.kind,
                            why,
                            ours_hash=ours.hash,
                            theirs_hash=t_hash,
                            base_hash=ours.base_hash,
                            proposed=merged,
                            fields=fields,
                            import_run=import_run,
                        )
                        report["conflicts"].append(c)
                    else:
                        good.append(op)
                ops = good
        if ops:
            txn = rebase_txn()
            res = txn.run(ops)
            if res.changeset:
                report["changesets"].append(res.changeset)
                for p in txn.written():
                    report["changes"].append(
                        {
                            "op": "rebase",
                            "kind": p.kind.name,
                            "id": p.id,
                            "layer": upper.slug,
                            "changeset": res.changeset,
                            "fields": changed_parts(p.before.body() if p.before else None, p.content.body()),
                        }
                    )
                if ids_now is not None:
                    ids_now |= {p.id for p in txn.written()}
    # a record Ben refers to, deleted below: his referring revision now dangles
    if deleted_below:
        for upper in uppers:
            if upper.state != "open":
                continue
            chain = layers.chain(upper.slug)
            for rid in sorted(deleted_below):
                gone = L.resolve(con, chain, rid)
                if gone is None or not gone.deleted:
                    continue
                for src, role in con.execute(
                    "SELECT src, role FROM ref WHERE layer = ? AND dst = ?", (upper.id, rid)
                ).fetchall():
                    rev = L.resolve(con, chain, src)
                    if rev is None or rev.deleted or rev.layer != upper.id:
                        continue
                    c = upsert_conflict(
                        con,
                        upper,
                        src,
                        rev.kind,
                        "dangling_ref",
                        ours_hash=rev.hash,
                        theirs_hash=None,
                        base_hash=rev.base_hash,
                        proposed=None,
                        fields=[role],
                        import_run=import_run,
                    )
                    report["conflicts"].append(c)
    return report


# -------------------------------------------------------------------------------------------------- resolution


def resolve_conflict(
    store: SqliteStore, con: sqlite3.Connection, cid: str, take: str, body: dict[str, Any] | None, *, by: str
) -> dict[str, Any]:
    """Resolve an open conflict: keep ``ours`` (its base moves to theirs), take ``theirs``, or write ``merged``
    (``body``). Refused with ``Conflict(reason="rebase")`` when Ben's revision changed since the conflict opened."""
    from .changesets import InternalOp, Txn

    if take not in TAKES:
        raise Invalid(f"take is one of {', '.join(TAKES)}, not {take!r}")
    c = conflict_row(con, cid)
    if c["state"] != "open":
        raise Conflict(
            f"conflict {cid} is {c['state']}", reason="rebase", conflicts=[{"kind": c["kind"], "id": c["rec_id"]}]
        )
    layers = L.load(con)
    layer = layers.get(c["layer"])
    row = con.execute(f"SELECT {SELECT} FROM rec r WHERE r.layer = ? AND r.id = ?", (layer.id, c["rec_id"])).fetchone()
    ours = rev_of(row) if row else None
    if ours is None or ours.hash != c["ours_hash"] and c["ours_hash"] is not None:
        raise Conflict(
            f"{c['kind']} {c['rec_id']} changed since the conflict opened",
            reason="rebase",
            conflicts=[{"kind": c["kind"], "id": c["rec_id"]}],
        )
    result: dict[str, Any] = {"conflict": cid, "take": take, "changeset": None}
    theirs_hash = c["theirs_hash"]
    view = View(layer=layer.slug)
    tag = etag(layer.slug, ours.version)
    # a seed conflict's "theirs" is the seed's revision (kept in proposed); the base below is not involved
    from_seed = is_seed_run(con, c["import_run"])
    if take == "ours":
        if not from_seed:
            con.execute("UPDATE rec SET base_hash = ? WHERE rid = ?", (theirs_hash, ours.rid))
    else:
        base = None if from_seed else (theirs_hash or "")
        if take == "merged":
            if body is None:
                raise Invalid("take merged needs the merged body")
            op = InternalOp(
                "put", ours.kind, ours.id, tag, body=_body(body), base=base, tombstone=bool(body.get("deleted"))
            )
        elif from_seed:
            proposed = c["proposed"] or {}
            op = InternalOp(
                "put", ours.kind, ours.id, tag, body=_body(proposed), base=base, tombstone=bool(proposed.get("deleted"))
            )
        elif theirs_hash is None:
            op = InternalOp("delete", ours.kind, ours.id, tag)
        else:
            theirs = L.hist_by_hash(con, ours.id, theirs_hash)
            if theirs is None and c["proposed"] is None:
                raise NotFound(f"the revision below ({theirs_hash}) is gone")
            op = InternalOp("put", ours.kind, ours.id, tag, body=_body(theirs or c["proposed"]), base=theirs_hash)
        txn = Txn(store, con, view, by=by, message=f"resolve conflict {cid}: {take}", kind="rebase", on_delete=False)
        res = txn.run([op])
        result["changeset"] = res.changeset
        if res.changeset is None and base is not None:
            con.execute("UPDATE rec SET base_hash = ? WHERE rid = ?", (base or None, ours.rid))
    con.execute("UPDATE conflict SET state = 'resolved', resolved_by = ?, resolution = ? WHERE id = ?", (by, take, cid))
    result["record"] = store._get_on(con, ours.kind, ours.id, view)
    return result


__all__ = [
    "REASONS",
    "TAKES",
    "changed_parts",
    "conflict_row",
    "list_conflicts",
    "merge3",
    "rebase",
    "resolve_conflict",
    "upsert_conflict",
]
