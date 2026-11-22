"""``apply_import``: an importer's records diffed against its layer by content hash, reported, then committed.

Imports diff by hash outside the write lock, then commit in one short transaction (9.28): the diff reads through a
reader connection, and each op carries the If-Match it was planned against, so a write that lands in between makes the
commit stale and the diff is taken again (three tries). An import of more than 200 changes commits in parts of
``CHUNK`` records, each its own short transaction under one changeset id; the last part writes the changeset row, its
one summary event and the rebase, so a save that arrives meanwhile waits for one part only.

- A record whose content hash equals what resolves on the layer's chain is ``unchanged``; a new one is ``created``;
  another is ``updated``. A record on the layer that the run no longer yields becomes an import tombstone
  (``deleted``). A rerun of the same inputs writes nothing.
- Two records with one id in a run are refused (``Invalid``), as is any id outside the layer's namespace (a 409).
- A dry run validates everything and reports the counts, the changes and the errors, and writes only the
  ``import_run`` row (state ``planned``).
- After an applied run, the rebase planner runs over the layers above; its conflicts (proposals, orphans, dangling
  refs) and its ``rebase`` changesets are listed in the report.

Imports never apply ``on_delete`` to other layers: a record of Ben's that refers to a record the import removed
becomes a ``dangling_ref`` conflict instead of blocking the import.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Iterable
from functools import partial
from typing import TYPE_CHECKING, Any

from region.core import ids as core_ids
from region.core.errors import HubError, Invalid, PreconditionFailed
from region.core.events import BULK_THRESHOLD
from region.core.protocols import ImportReport, ImportRun, etag
from region.core.view import View

from . import layers as L
from .db import now, run_in_transaction
from .records import SELECT, changed_fields, content, content_hash, dumps, rev_of

if TYPE_CHECKING:
    from .legacy import IdLookupImpl
    from .store import SqliteStore

log = logging.getLogger("region.model")

ATTEMPTS = 3
STARTED = now()
"""When this process loaded the module: a run still ``running`` from before it was cut off (the hub stopped or
crashed mid-import), never one of this process's own."""
CHUNK = 100
"""Records per transaction of an import of more than ``BULK_THRESHOLD`` (200) changes: a part holds the writer for a
few tens of milliseconds, so a save of Ben's that arrives during a big import waits for one part, not the whole."""


def _normalize(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    out, errors = [], []
    seen: dict[str, int] = {}
    for i, r in enumerate(records):
        if not isinstance(r, dict):
            errors.append({"path": f"/records/{i}", "message": "a record is an object"})
            continue
        missing = [k for k in ("kind", "id", "data") if k not in r]
        if missing:
            errors.append({"path": f"/records/{i}", "message": "missing " + ", ".join(missing), "id": r.get("id")})
            continue
        rid = r["id"]
        if rid in seen:
            errors.append(
                {"path": f"/records/{i}/id", "message": f"duplicate id {rid} (also record {seen[rid]})", "id": rid}
            )
            continue
        seen[rid] = i
        body = {"data": r["data"], "geom": r.get("geom")}
        if "kv" in r:
            body["kv"] = r["kv"]
        if r.get("source") is not None:
            body["source"] = r["source"]
        out.append({"kind": r["kind"], "id": rid, "body": body})
    return out, errors


def _unchanged_fast(store: SqliteStore, con: Any, chain: list[L.Layer], r: dict[str, Any]) -> bool:
    """Whether an incoming record holds exactly the content that resolves on the chain, found by hash alone.

    The full path validates every record against its kind's schema before hashing it, which costs about 1 ms a
    record (1.7 s for the 1,405 records of the Metro line files). A record whose raw body, at the kind's current
    version and with WKT or no geometry, hashes to the stored hash holds the stored bytes, which were validated when
    they were written, so it is ``unchanged`` without the schema pass. Anything else (another version, a geometry
    to normalise, a hash that differs, a tombstone) takes the full path."""
    kind = store.kinds.get(r["kind"]) if hasattr(store.kinds, "get") else None
    if kind is None:
        return False
    body = r["body"]
    data, geom = body.get("data"), body.get("geom")
    if body.get("kv", kind.version) != kind.version or not isinstance(data, dict):
        return False
    if geom is not None and not isinstance(geom, str):
        return False
    cur = L.resolve(con, chain, r["id"])
    if cur is None or cur.deleted or cur.kind != kind.name:
        return False
    try:
        h = content_hash(r["id"], kind.name, kind.version, geom, data)
    except Invalid:
        return False
    return h == cur.hash


def _plan(
    store: SqliteStore, con: Any, layer: L.Layer, chain: list[L.Layer], incoming: list[dict[str, Any]]
) -> tuple[list[Any], list[dict[str, Any]], dict[str, int], list[dict[str, Any]]]:
    from .changesets import InternalOp

    ops: list[Any] = []
    changes: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    unchanged: Counter[str] = Counter()
    slugs = L.load(con).slugs
    for r in incoming:
        if _unchanged_fast(store, con, chain, r):
            unchanged[r["kind"]] += 1
            continue
        try:
            kind = store.kinds[r["kind"]]
            if not core_ids.is_ulid(r["id"]):
                raise Invalid(f"{r['id']!r} is not a ULID", errors=[{"path": "/id", "message": "ULID"}])
            c = content(kind, r["id"], r["body"])
        except HubError as e:
            errs = getattr(e, "errors", None) or [{"path": "", "message": str(e)}]
            errors.extend({**err, "id": r["id"], "kind": r["kind"]} for err in errs)
            continue
        cur = L.resolve(con, chain, r["id"])
        if cur is not None and cur.kind != kind.name:
            errors.append(
                {"path": "/kind", "message": f"id {r['id']} belongs to a {cur.kind}", "id": r["id"], "kind": r["kind"]}
            )
            continue
        if cur is not None and not cur.deleted and cur.hash == c.hash:
            unchanged[kind.name] += 1
            continue
        if cur is None or cur.deleted:
            ops.append(InternalOp("create", kind.name, r["id"], None, body=r["body"], check_match=False, prepared=c))
            changes.append({"op": "create", "kind": kind.name, "id": r["id"], "fields": changed_fields(None, c.body())})
        else:
            ops.append(
                InternalOp("put", kind.name, r["id"], etag(slugs[cur.layer], cur.version), body=r["body"], prepared=c)
            )
            changes.append(
                {"op": "put", "kind": kind.name, "id": r["id"], "fields": changed_fields(cur.body(), c.body())}
            )
    keep = {r["id"] for r in incoming}
    for row in con.execute(
        f"SELECT {SELECT} FROM rec r WHERE r.layer = ? AND r.deleted = 0 ORDER BY r.id", (layer.id,)
    ).fetchall():
        rev = rev_of(row)
        if rev.id in keep:
            continue
        ops.append(InternalOp("delete", rev.kind, rev.id, etag(layer.slug, rev.version)))
        changes.append({"op": "delete", "kind": rev.kind, "id": rev.id, "fields": ["deleted"]})
    return ops, changes, dict(unchanged), errors


def _counts(
    changes: list[dict[str, Any]], unchanged: dict[str, int], conflicts: int
) -> tuple[dict[str, int], dict[str, dict]]:
    names = {"create": "created", "put": "updated", "delete": "deleted"}
    counts = {"created": 0, "updated": 0, "unchanged": sum(unchanged.values()), "deleted": 0, "conflicts": conflicts}
    by_kind: dict[str, dict[str, int]] = {}
    for kind, n in unchanged.items():
        by_kind.setdefault(kind, {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0, "conflicts": 0})
        by_kind[kind]["unchanged"] += n
    for ch in changes:
        if ch["op"] not in names:
            continue
        key = names[ch["op"]]
        counts[key] += 1
        by_kind.setdefault(ch["kind"], {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0, "conflicts": 0})
        by_kind[ch["kind"]][key] += 1
    return counts, dict(sorted(by_kind.items()))


def apply_import(
    store: SqliteStore,
    run: ImportRun,
    records: Iterable[dict[str, Any]],
    *,
    dry_run: bool,
    ids: IdLookupImpl | None = None,
    backup: bool = True,
) -> ImportReport:
    """See the module doc. ``ids``, when given, is flushed into the legacy index in the import's transaction.
    ``backup=False`` skips the ``pre-import`` backup (the live importer takes one at most hourly: each of its runs is
    one revertible changeset)."""
    from .changesets import Part, Txn
    from .merge import rebase

    layers = L.load(store._reader())
    layer = layers.get(run.layer)
    if layer.tier not in ("import", "legacy"):
        raise Invalid(f"imports write import or legacy layers, not {layer.slug} ({layer.tier})")
    if layer.tier == "import" and layer.namespace != run.namespace:
        raise Invalid(
            f"importer {run.importer} declares namespace {run.namespace!r}, but layer {layer.slug} owns "
            f"{layer.namespace!r}"
        )
    incoming, errors = _normalize(records)
    report = ImportReport(importer=run.importer, layer=layer.slug, dry_run=dry_run)
    started = now()

    def record_run(con: Any) -> int:
        cur = con.execute(
            "INSERT INTO import_run (importer, version, layer, sources, dry_run, state, started) "
            "VALUES (?, ?, ?, ?, ?, 'running', ?)",
            (run.importer, run.version, layer.id, dumps(run.sources), int(dry_run), started),
        )
        return int(cur.lastrowid or 0)

    run.id = store._writer.run(record_run)
    report.run = run.id

    def finish(state: str) -> None:
        def fn(con: Any) -> None:
            con.execute(
                "UPDATE import_run SET state = ?, counts = ?, report = ?, changeset = ?, finished = ? WHERE id = ?",
                (state, dumps(report.counts), dumps(_report_json(report)), report.changeset, now(), run.id),
            )

        store._writer.run(fn)

    if errors:
        report.errors = errors
        report.counts, report.by_kind = _counts([], {}, 0)
        finish("failed")
        if dry_run:
            return report
        raise Invalid(f"import {run.importer}: {len(errors)} record(s) refused: {errors[0]['message']}", errors=errors)

    view = View(layer=layer.slug)
    if not dry_run:
        recover_parts(store, layer.slug)
    for attempt in range(ATTEMPTS):
        con = store._reader()
        chain = L.load(con).chain(layer.slug)

        def plan(
            c: Any, chain: list[L.Layer] = chain
        ) -> tuple[list[Any], list[dict[str, Any]], dict[str, int], list[dict[str, Any]]]:
            return _plan(store, c, layer, chain, incoming)

        ops, changes, unchanged, errs = run_in_transaction(con, plan, begin="BEGIN")
        report.changes = changes
        report.counts, report.by_kind = _counts(changes, unchanged, 0)
        if errs:
            report.errors = errs
            finish("failed")
            if dry_run:
                return report
            raise Invalid(f"import {run.importer}: {len(errs)} record(s) refused: {errs[0]['message']}", errors=errs)
        if dry_run:
            try:

                def check(c: Any, ops: list[Any] = ops) -> None:
                    Txn(store, c, view, by=run.by, kind="import", import_run=run.id, on_delete=False).plan(ops)

                run_in_transaction(con, check, begin="BEGIN")
            except HubError as e:
                errs = list(getattr(e, "errors", None) or [])
                if not errs:
                    errs = [{"path": "", "message": str(e), "code": e.code, "conflicts": getattr(e, "conflicts", [])}]
                report.errors = errs
            finish("planned")
            return report
        if not ops:

            def flush_only(c: Any) -> Any:
                return ids.flush_into(c) if ids is not None else {}

            written = store._writer.run(flush_only)
            if ids is not None:
                ids.write_ledger(written)
            finish("unchanged")
            return report

        def txn(c: Any, part: Any = None) -> Any:
            # a part is checked with the whole import before the first part is written (refs may point into a later
            # part), so it is written without checking again
            return Txn(
                store,
                c,
                view,
                by=run.by,
                message=f"import {run.importer}@{run.version}",
                kind="import",
                import_run=run.id,
                on_delete=False,
                part=part,
                validators=part is None,
                dangling="refuse" if part is None else "list",
            )

        def commit(c: Any, ops: list[Any] = ops, part: Any = None, before: frozenset[str] = frozenset()) -> Any:
            t = txn(c, part)
            res = t.run(ops)
            written = ids.flush_into(c) if ids is not None else {}
            changed = set(before) | {p.id for p in t.written()}
            reb = rebase(store, c, lower=layer.slug, changed=changed, import_run=run.id, by="rebase")
            return res, written, reb

        if attempt == 0 and backup:
            store.pre_import_backup()  # section 9: an import that changes records is backed up first
        # A big import (a Deck tie rewriting every line file) is committed in parts of CHUNK records, each its own
        # short transaction, so a save of Ben's waits for one part rather than the whole import (9.28). The parts
        # share one changeset id; the last writes the changeset row, its one summary event and the rebase.
        part = Part() if len(ops) > BULK_THRESHOLD else None
        done: set[str] = set()
        try:
            if part is not None:

                def check_all(c: Any, ops: list[Any] = ops) -> None:
                    txn(c).plan(ops)

                run_in_transaction(store._reader(), check_all, begin="BEGIN")
                # the run names its changeset before any part is written, so parts left by a hub that stopped
                # mid-import are found and closed by the next import of the layer (recover_parts)
                store._writer.run(
                    lambda c, cs=part.id: c.execute("UPDATE import_run SET changeset = ? WHERE id = ?", (cs, run.id))
                )
            if part is None:
                res, written, reb = store._writer.run(commit)
            else:
                for i in range(0, len(ops) - CHUNK, CHUNK):

                    def one(
                        c: Any, chunk: list[Any] = ops[i : i + CHUNK], part: Any = part, first: bool = i == 0
                    ) -> tuple[set[str], Any]:
                        t = txn(c, part)
                        t.run(chunk)
                        # the ids minted by this run go into the legacy index with the first part, so a part
                        # written before a stop keeps its ids when the import runs again
                        flushed = ids.flush_into(c) if (first and ids is not None) else None
                        return {p.id for p in t.written()}, flushed

                    got, flushed = store._writer.run(one)
                    done |= got
                    if flushed is not None and ids is not None:
                        ids.write_ledger(flushed)
                part.last = True
                last = ops[len(ops) - ((len(ops) - 1) % CHUNK + 1) :]
                res, written, reb = store._writer.run(partial(commit, ops=last, part=part, before=frozenset(done)))
        except PreconditionFailed:
            if part is not None and part.count:
                report.changeset = _close_part(store, txn, part, done, layer.slug, run.id)
                finish("failed")
                raise
            if attempt == ATTEMPTS - 1:
                finish("failed")
                raise
            continue
        except HubError:
            if part is not None and part.count:
                report.changeset = _close_part(store, txn, part, done, layer.slug, run.id)
            finish("failed")
            raise
        if ids is not None:
            ids.write_ledger(written)
        report.changeset = res.changeset
        report.conflicts = reb["conflicts"]
        report.changes = changes + reb["changes"]
        report.counts["conflicts"] = len(reb["conflicts"])
        finish("applied")
        store.checkpoint()
        store._notify(res.seq)
        return report
    raise AssertionError("unreachable")


def _close_part(store: SqliteStore, txn: Any, part: Any, done: set[str], layer: str, run_id: int | None) -> str | None:
    """Write the changeset row and summary event of the parts already committed (a later part failed), so what was
    written is one listed changeset that Undo can revert, and rebase Ben's revisions over the records those parts
    changed: a change that touches his edit is a review item, as it is when the whole import lands. Returns the
    changeset id, or ``None`` when it could not be closed."""
    from .merge import rebase

    part.last = True

    def fn(c: Any) -> Any:
        res = txn(c, part).run([])
        if done:
            rebase(store, c, lower=layer, changed=set(done), import_run=run_id, by="rebase")
        return res

    try:
        res = store._writer.run(fn)
    except Exception:  # the import failed already; its report says so
        log.exception("closing the parts of import run %s failed", run_id)
        return None
    store._notify(res.seq)
    return str(part.id)


def recover_parts(store: SqliteStore, layer: str) -> list[str]:
    """Close the parts of imports into ``layer`` that a hub stopped in the middle of (a killed process, a power
    cut): the run names its changeset before its first part is written (``apply_import``), so its revisions are
    found by that id. Each becomes one listed changeset with its summary event, Ben's revisions over its records are
    rebased (a change that touches his edit is a review item), and the run is marked failed. The next import of
    the layer then writes the rest. Returns the changeset ids closed."""
    from .changesets import Part, Txn

    con = store._reader()
    lay = L.load(con).get(layer)
    rows = con.execute(
        "SELECT r.id, r.importer, r.changeset FROM import_run r WHERE r.layer = ? AND r.dry_run = 0 "
        "AND r.state = 'running' AND r.changeset IS NOT NULL AND r.started < ? "
        "AND NOT EXISTS (SELECT 1 FROM changeset c WHERE c.id = r.changeset)",
        (lay.id, STARTED),
    ).fetchall()
    closed: list[str] = []
    seqs: list[int | None] = []
    for run_id, importer, cs in rows:
        written = con.execute(
            "SELECT h.id, json_extract(h.row, '$.kind') FROM rec_hist h WHERE h.layer = ? AND h.changeset = ?",
            (lay.id, cs),
        ).fetchall()
        if written:
            part = Part(id=cs, count=len(written), kinds=Counter(str(k) for _i, k in written), last=True)
            ids_ = {str(i) for i, _k in written}

            def fn(
                c: Any, part: Any = part, ids_: set[str] = ids_, run_id: int = run_id, name: str = f"{importer}"
            ) -> Any:
                from .merge import rebase

                res = Txn(
                    store,
                    c,
                    View(layer=layer),
                    by=f"import:{name}",
                    message=f"import {name} (cut off)",
                    kind="import",
                    import_run=run_id,
                    on_delete=False,
                    part=part,
                    validators=False,
                    dangling="list",
                ).run([])
                rebase(store, c, lower=layer, changed=ids_, import_run=run_id, by="rebase")
                return res

            seqs.append(store._writer.run(fn).seq)
            closed.append(str(cs))

        def mark(c: Any, run_id: int = run_id, cs: str = cs, n: int = len(written)) -> None:
            c.execute(
                "UPDATE import_run SET state = 'failed', finished = ?, report = ? WHERE id = ?",
                (now(), dumps({"interrupted": {"changeset": cs if n else None, "written": n}}), run_id),
            )

        store._writer.run(mark)
        log.warning(
            "import run %s (%s) was cut off; its %d written record(s) are changeset %s",
            run_id,
            importer,
            len(written),
            cs,
        )
    for seq in seqs:
        store._notify(seq)
    return closed


def _report_json(r: ImportReport) -> dict[str, Any]:
    return {
        "importer": r.importer,
        "layer": r.layer,
        "dry_run": r.dry_run,
        "run": r.run,
        "counts": r.counts,
        "by_kind": r.by_kind,
        "changes": r.changes[:5000],
        "conflicts": r.conflicts,
        "changeset": r.changeset,
        "errors": r.errors[:1000],
    }


def report_of(store: SqliteStore, run_id: int) -> dict[str, Any]:
    """The stored report of an import run."""
    from region.core.errors import NotFound

    row = (
        store._reader()
        .execute(
            "SELECT importer, version, layer, sources, dry_run, state, counts, report, "
            "changeset, started, finished FROM import_run WHERE id = ?",
            (run_id,),
        )
        .fetchone()
    )
    if not row:
        raise NotFound(f"no import run {run_id}")
    slugs = L.load(store._reader()).slugs
    return {
        "id": run_id,
        "importer": row[0],
        "version": row[1],
        "layer": slugs.get(row[2]),
        "sources": json.loads(row[3]) if row[3] else {},
        "dry_run": bool(row[4]),
        "state": row[5],
        "counts": json.loads(row[6]) if row[6] else {},
        "report": json.loads(row[7]) if row[7] else None,
        "changeset": row[8],
        "started": row[9],
        "finished": row[10],
    }


def mark_reverted(store: SqliteStore, run_id: int, by: str) -> None:
    """Record that an applied run's changeset was undone (``state = 'reverted'``): ``last_applied`` then skips it, so
    the importer's sources count as changed since the run before it, and the live importer holds those sources
    until they change again (``region/live``). The review items that run raised are about changes that are gone now,
    so the open ones are dismissed (a stop it moved under Ben's profile is back where his profile was drawn)."""

    def fn(con: Any) -> None:
        row = con.execute("SELECT report FROM import_run WHERE id = ?", (run_id,)).fetchone()
        rep = json.loads(row[0]) if row and row[0] else {}
        rep["reverted"] = {"by": by, "at": now()}
        con.execute(
            "UPDATE import_run SET state = 'reverted', report = ? WHERE id = ? AND state = 'applied'",
            (dumps(rep), run_id),
        )
        con.execute(
            "UPDATE conflict SET state = 'dismissed', resolution = 'no longer stale', resolved_by = ? "
            "WHERE import_run = ? AND state = 'open'",
            (by, run_id),
        )

    store._writer.run(fn)


__all__ = ["apply_import", "mark_reverted", "recover_parts", "report_of"]
