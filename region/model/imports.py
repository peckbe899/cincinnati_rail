"""``apply_import``: an importer's records diffed against its layer by content hash, reported, then committed.

Imports diff by hash outside the write lock, then commit in one short transaction (9.28): the diff reads through a
reader connection, and each op carries the If-Match it was planned against, so a write that lands in between makes the
commit stale and the diff is taken again (three tries).

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
from collections import Counter
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from region.core import ids as core_ids
from region.core.errors import HubError, Invalid, PreconditionFailed
from region.core.protocols import ImportReport, ImportRun, etag
from region.core.view import View

from . import layers as L
from .db import now, run_in_transaction
from .records import SELECT, changed_fields, content, dumps, rev_of

if TYPE_CHECKING:
    from .legacy import IdLookupImpl
    from .store import SqliteStore

ATTEMPTS = 3


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
) -> ImportReport:
    """See the module doc. ``ids``, when given, is flushed into the legacy index in the import's transaction."""
    from .changesets import Txn
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

        def commit(c: Any, ops: list[Any] = ops) -> tuple[Any, Any, Any]:
            txn = Txn(
                store,
                c,
                view,
                by=run.by,
                message=f"import {run.importer}@{run.version}",
                kind="import",
                import_run=run.id,
                on_delete=False,
            )
            res = txn.run(ops)
            written = ids.flush_into(c) if ids is not None else {}
            changed = {p.id for p in txn.written()}
            reb = rebase(store, c, lower=layer.slug, changed=changed, import_run=run.id, by="rebase")
            return res, written, reb

        try:
            res, written, reb = store._writer.run(commit)
        except PreconditionFailed:
            if attempt == ATTEMPTS - 1:
                finish("failed")
                raise
            continue
        except HubError:
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


__all__ = ["apply_import", "report_of"]
