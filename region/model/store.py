"""``SqliteStore``: the record store over one truth database (WP1), implementing ``region.core.protocols.Store``.

    store = open_store(var / "region.db")                      # migrates (backing up first), loads the kinds
    rec = store.put({"kind": "note", "id": None, "data": {...}, "geom": None}, View(), if_match=None, by="ben")
    rec = store.patch("note", rec["id"], [{"op": "replace", "path": "/data/text", "value": "x"}], View(),
                      if_match=etag(rec["layer"], rec["version"]), by="ben")
    page, cursor = store.list("note", View(layer="try", year=1931))
    store.close()

Every write goes to ``view.layer`` through one writer thread per database file and is one changeset (see
``changesets``). Reads resolve up the layer chain (see ``layers``) on a per-thread reader connection. Beyond the
protocol the store offers what the API (WP2) serves: layers, promote, tags, layer diffs, changesets, conflicts and
their resolution, reverse refs, legacy keys, import reports, the outbox's bounds and an in-process commit hook.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from region.core import features, fsio
from region.core.errors import Conflict, Invalid, NotFound, PreconditionFailed
from region.core.protocols import ImportReport, ImportRun, Op, WriteResult, etag, parse_ref
from region.core.view import View

from . import db as D
from . import layers as L
from . import legacy as LG
from . import merge as M
from .changesets import InternalOp, Txn, revert_ops
from .kinds import KindRegistry
from .kinds import load as load_kinds
from .migrate import migrate
from .query import list_rows
from .records import COLS, SELECT, Rev, content, dumps, rev_of

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_BASE_COLS = {
    "layer",
    "id",
    "kind",
    "kv",
    "version",
    "hash",
    "base_hash",
    "deleted",
    "origin",
    "source",
    "by",
    "changeset",
    "created",
    "updated",
    "geom",
    "data",
    *COLS,
}


def _discover_validators(kinds: KindRegistry) -> dict[str, Callable[..., Any]]:
    roots: set[Path] = set()
    for k in kinds.values():
        if k.feature is not None and k.path.parent.name == "kinds":
            roots.add(k.path.parent.parent.parent)
    out: dict[str, Callable[..., Any]] = {}
    for root in sorted(roots):
        for f in features.discover(root):
            if f.has("validators"):
                for name, fn in f.validators().items():
                    if name in kinds:
                        out[name] = fn
    return out


def _sync_kinds(con: sqlite3.Connection, kinds: KindRegistry) -> None:
    con.execute("DELETE FROM kind")
    con.executemany(
        "INSERT INTO kind (name, version, feature, geometry, sha256, spec) VALUES (?, ?, ?, ?, ?, ?)",
        [(k.name, k.version, k.feature, k.geometry, k.sha256, dumps(k.spec)) for k in kinds.values()],
    )
    row = con.execute("SELECT value FROM meta WHERE key = 'kinds_sha256'").fetchone()
    if row and row[0] == kinds.sha256:
        return
    for (name,) in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'view' AND name LIKE 'v\\_%' ESCAPE '\\'"
    ).fetchall():
        con.execute(f'DROP VIEW "{name}"')
    for k in kinds.values():
        props = (k.schema.get("properties") or {}) if isinstance(k.schema, dict) else {}
        extra = [p for p in sorted(props) if _IDENT.match(p) and p not in _BASE_COLS]
        cols = ", ".join(f'json_extract(r.data, \'$."{p}"\') AS "{p}"' for p in extra)
        con.execute(
            f'CREATE VIEW "v_{k.name}" AS SELECT l.slug AS layer, r.id, r.kind, r.kv, r.version, r.hash, '
            f"r.base_hash, r.deleted, r.origin, r.source, r.by, r.changeset, r.created, r.updated, "
            f"r.name, r.system, r.parent, r.c0, r.c1, r.ord, r.phase, r.open_lo, r.open_hi, r.close_lo, r.close_hi, "
            f"r.x0, r.y0, r.x1, r.y1, r.geom{', ' + cols if cols else ''}, r.data "
            f"FROM rec r JOIN layer l ON l.id = r.layer WHERE r.kind = '{k.name}'"
        )
    con.execute(
        "INSERT INTO meta (key, value) VALUES ('kinds_sha256', ?) "
        "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        (kinds.sha256,),
    )


class SqliteStore:
    """The record store (see the module doc). Make one with ``open_store``; ``close()`` it (or use ``with``)."""

    def __init__(
        self,
        path: Path,
        *,
        cache: Path | None,
        kinds: KindRegistry,
        validators: dict[str, Callable[..., Any]],
        backup_dir: Path | None,
        readonly: bool = False,
    ) -> None:
        self.path = Path(path)
        self.cache_path = Path(cache) if cache is not None else None
        self.kinds = kinds
        self.validators = validators
        self.backup_dir = Path(backup_dir) if backup_dir is not None else self.path.parent / "backups"
        self.readonly = readonly
        # pre-import backups (section 9): taken before an import or seed import changes records; a throwaway
        # database (crhub rebuild's) turns them off
        self.auto_backups = not readonly
        self._writer: D.Writer | D.ReadOnlyWriter = D.ReadOnlyWriter(self.path) if readonly else D.writer_for(self.path)
        self._readers = D.Readers(self.path, cache=self.cache_path, readonly=readonly)
        self._listeners: list[Callable[[int | None], None]] = []
        self._lock = threading.Lock()
        self._closed = False

    # ---------------------------------------------------------------------------------------------- lifecycle

    def close(self) -> None:
        """Close the readers and release the writer (the last store of a file stops its thread and truncates the
        WAL)."""
        if self._closed:
            return
        self._closed = True
        self._readers.close()
        if not self.readonly:
            D.release_writer(self.path)

    def __enter__(self) -> SqliteStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _reader(self) -> sqlite3.Connection:
        return self._readers.get()

    def _read(self, fn: Callable[[sqlite3.Connection], Any]) -> Any:
        """``fn(con)`` on this thread's reader, in one read transaction (a consistent snapshot)."""
        con = self._reader()
        if con.in_transaction:
            return fn(con)
        return D.run_in_transaction(con, fn, begin="BEGIN")

    def subscribe(self, fn: Callable[[int | None], None]) -> Callable[[], None]:
        """Call ``fn(seq)`` after every commit made through this store (the in-process notify that wakes SSE).
        Returns a function that unsubscribes."""
        with self._lock:
            self._listeners.append(fn)

        def off() -> None:
            with self._lock:
                if fn in self._listeners:
                    self._listeners.remove(fn)

        return off

    def _notify(self, seq: int | None) -> None:
        if seq is None:
            return
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(seq)
            except Exception:  # a listener never breaks a write
                pass

    # ------------------------------------------------------------------------------------------------- reads

    def _chain(self, con: sqlite3.Connection, view: View) -> tuple[L.Layers, list[L.Layer]]:
        layers = L.load(con)
        return layers, layers.chain(view.layer)

    def _get_on(self, con: sqlite3.Connection, kind: str, id: str, view: View) -> dict[str, Any] | None:
        layers, chain = self._chain(con, view)
        rev = L.resolve(con, chain, id)
        if rev is None or rev.deleted or rev.kind != kind:
            return None
        return rev.record(layers.slugs[rev.layer])

    def get(self, kind: str, id: str, view: View, *, at: int | None = None, tag: str | None = None) -> dict[str, Any]:
        """One record as it resolves in ``view`` (``at``: a past version of that revision; ``tag``: the layer as of
        one of its tags). ``NotFound`` for an unknown kind, layer or record, or a tombstone."""
        self.kinds[kind]

        def fn(con: sqlite3.Connection) -> dict[str, Any]:
            layers, chain = self._chain(con, view)
            if tag is not None:
                seq = L.tag_seq(con, layers.get(view.layer), tag)
                rows = L.as_of_rows(con, chain, seq, id=id)
                if not rows or rows[0]["deleted"] or rows[0]["kind"] != kind:
                    raise NotFound(f"no {kind} {id} in {view.layer} at tag {tag}", kind=kind, id=id)
                return rows[0]
            rev = L.resolve(con, chain, id)
            if rev is None or rev.kind != kind:
                raise NotFound(f"no {kind} {id} in layer {view.layer}", kind=kind, id=id)
            if at is not None:
                row = L.lineage_row(con, chain, rev.layer, id, int(at))
                if row is None:
                    raise NotFound(
                        f"no version {at} of {kind} {id} on layer {layers.slugs[rev.layer]}", kind=kind, id=id
                    )
                return row
            if rev.deleted:
                raise NotFound(f"{kind} {id} is deleted in layer {view.layer}", kind=kind, id=id)
            return rev.record(layers.slugs[rev.layer])

        return self._read(fn)

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
        tag: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Records of ``kind`` resolved in ``view`` and open at its instant (``Store.list``); ``tag`` reads the
        layer as of one of its tags."""
        k = self.kinds[kind]

        def fn(con: sqlite3.Connection) -> tuple[list[dict[str, Any]], str | None]:
            layers, chain = self._chain(con, view)
            if tag is not None:
                return self._list_tag(
                    con,
                    layers,
                    chain,
                    view,
                    k,
                    tag,
                    bbox=bbox,
                    parent=parent,
                    ref=ref,
                    ids=ids,
                    q=q,
                    limit=limit,
                    after=after,
                )
            return list_rows(
                con,
                layers.slugs,
                chain,
                k,
                view.instant(),
                bbox=bbox,
                parent=parent,
                ref=ref,
                ids=ids,
                q=q,
                limit=limit,
                after=after,
            )

        return self._read(fn)

    def _list_tag(
        self,
        con: sqlite3.Connection,
        layers: L.Layers,
        chain: list[L.Layer],
        view: View,
        k: Any,
        tag: str,
        *,
        bbox: Any,
        parent: str | None,
        ref: str | None,
        ids: Iterable[str] | None,
        q: str | None,
        limit: int,
        after: str | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        from region.core.view import is_open

        from .geom import bbox_of

        seq = L.tag_seq(con, layers.get(view.layer), tag)
        want = set(ids) if ids is not None else None
        out = []
        for r in L.as_of_rows(con, chain, seq, kind=k.name):
            if r["deleted"] or (after is not None and r["id"] <= after) or (want is not None and r["id"] not in want):
                continue
            cols = k.columns_of(r["data"])
            if parent is not None and cols.get("parent") != parent:
                continue
            if q and q.lower() not in str(cols.get("name") or "").lower():
                continue
            if ref is not None and ref not in {v for _role, v, _spec, _at in k.refs_of(r["data"])}:
                continue
            if bbox is not None:
                b = bbox_of(r["geom"])
                if b is None or b[2] < bbox[0] or b[0] > bbox[2] or b[3] < bbox[1] or b[1] > bbox[3]:
                    continue
            if k.dated and not is_open(view.instant(), *k.dates_of(r["data"])):
                continue
            out.append(r)
        page = out[:limit]
        return page, (page[-1]["id"] if len(out) > limit else None)

    def history(self, kind: str, id: str, view: View) -> list[dict[str, Any]]:
        """Every revision of the record on ``view.layer`` and the layers below it, newest first, in get() shape."""
        self.kinds[kind]

        def fn(con: sqlite3.Connection) -> list[dict[str, Any]]:
            _layers, chain = self._chain(con, view)
            marks = ",".join("?" * len(chain))
            rows = con.execute(
                f"SELECT row FROM rec_hist WHERE id = ? AND layer IN ({marks}) ORDER BY rowid DESC",
                (id, *[c.id for c in chain]),
            ).fetchall()
            out = [json.loads(r[0]) for r in rows]
            if not out or out[0]["kind"] != kind:
                raise NotFound(f"no {kind} {id} in layer {view.layer}", kind=kind, id=id)
            return out

        return self._read(fn)

    def diff(self, kind: str, id: str, view: View, from_version: int, to_version: int) -> list[dict[str, Any]]:
        """The RFC 6902 patch from one version of the record's revision to another (``/k/{kind}/{id}/diff``)."""
        import jsonpatch

        a = self.get(kind, id, view, at=from_version)
        b = self.get(kind, id, view, at=to_version)
        before = {"data": a["data"], "geom": a["geom"]}
        return list(jsonpatch.make_patch(before, {"data": b["data"], "geom": b["geom"]}))

    def hash_of(self, ref: str, view: View) -> str | None:
        """The content hash of a ``rec:<id>`` ref resolved in ``view``, or ``None`` (absent or tombstoned)."""
        kind, rest = parse_ref(ref)
        if kind != "rec":
            raise Invalid(f"the store hashes rec: refs only, not {ref!r}")

        def fn(con: sqlite3.Connection) -> str | None:
            _layers, chain = self._chain(con, view)
            rev = L.resolve(con, chain, rest)
            return None if rev is None or rev.deleted else rev.hash

        return self._read(fn)

    def events_since(self, seq: int, limit: int = 1000) -> list[dict[str, Any]]:
        """Durable events after ``seq``, oldest first, as ``{"seq", "type", "data"}``."""
        rows = (
            self._reader()
            .execute("SELECT seq, type, data FROM event WHERE seq > ? ORDER BY seq LIMIT ?", (int(seq), int(limit)))
            .fetchall()
        )
        out = []
        for s, typ, data in rows:
            payload = json.loads(data) if data else {}
            payload["seq"] = s
            out.append({"seq": s, "type": typ, "data": payload})
        return out

    def last_seq(self) -> int:
        """The newest event ``seq`` (0 when there is none)."""
        return int(self._reader().execute("SELECT coalesce(max(seq), 0) FROM event").fetchone()[0])

    def min_seq(self) -> int:
        """The oldest event ``seq`` still in the outbox (0 when there is none): a client behind it must resync."""
        return int(self._reader().execute("SELECT coalesce(min(seq), 0) FROM event").fetchone()[0])

    def data_version(self) -> int:
        """``PRAGMA data_version`` of this thread's reader: it changes when another connection commits (the CLI,
        a script, a seed import), which is what the server's 500 ms check looks for (9.28)."""
        return int(self._reader().execute("PRAGMA data_version").fetchone()[0])

    def meta(self) -> dict[str, str]:
        """The ``meta`` table: ``db_id``, ``epoch``, ``created``, ``last_export``, ``kinds_sha256``."""
        return dict(self._reader().execute("SELECT key, value FROM meta").fetchall())

    def epoch(self) -> str:
        """The database's epoch (``meta.epoch``): it changes when the database is restored from a backup, so a
        client holding seqs of the old file must resync (``Store.epoch``)."""
        row = self._reader().execute("SELECT value FROM meta WHERE key = 'epoch'").fetchone()
        return str(row[0]) if row is not None and row[0] is not None else ""

    def pending_migrations(self) -> list[int]:
        """The migration versions not applied to this database: always empty for a store opened read-write (open
        migrates), and what a read-only store reports instead of migrating."""
        from .migrate import pending

        return [m.version for m in pending(self._reader())]

    def legacy(self, lkind: str, key: str) -> str | None:
        return LG.lookup(self._reader(), lkind, key)

    def legacy_keys(self, id: str) -> list[dict[str, Any]]:
        """Every old key of ``id`` (the other way of ``legacy``)."""
        return LG.keys_of(self._reader(), id)

    def legacy_record(self, lkind: str, key: str) -> dict[str, str] | None:
        """``{"kind", "id"}`` of an old key (``/legacy/{lkind}/{key}``), or ``None``."""
        rid = self.legacy(lkind, key)
        if rid is None:
            return None
        row = self._reader().execute("SELECT kind FROM rec WHERE id = ? LIMIT 1", (rid,)).fetchone()
        k = self.kinds.for_lkind(lkind)
        return {"kind": row[0] if row else (k.name if k else ""), "id": rid}

    def add_legacy(self, lkind: str, key: str, id: str, *, status: str = "current") -> None:
        """Record one old key for ``id`` (importers use ``IdLookupImpl``; this is for one-off aliases)."""
        self._writer.run(lambda con: LG.put(con, lkind, key, id, status))

    def refs_to(self, id: str, view: View) -> list[dict[str, Any]]:
        """What references ``id`` in ``view``: ``[{"kind", "id", "role", "layer"}]`` (``/refs/{id}``)."""

        def fn(con: sqlite3.Connection) -> list[dict[str, Any]]:
            layers, chain = self._chain(con, view)
            marks = ",".join("?" * len(chain))
            out = []
            for src, role in con.execute(
                f"SELECT DISTINCT src, role FROM ref WHERE dst = ? AND layer IN ({marks}) ORDER BY src, role",
                (id, *[c.id for c in chain]),
            ).fetchall():
                rev = L.resolve(con, chain, src)
                if rev is None or rev.deleted:
                    continue
                if con.execute(
                    "SELECT 1 FROM ref WHERE layer = ? AND src = ? AND role = ? AND dst = ?", (rev.layer, src, role, id)
                ).fetchone():
                    out.append({"kind": rev.kind, "id": src, "role": role, "layer": layers.slugs[rev.layer]})
            return out

        return self._read(fn)

    def layer_records(self, layer: str, kind: str | None = None) -> list[dict[str, Any]]:
        """The live revisions held on ``layer`` itself (not resolved through its chain)."""

        def fn(con: sqlite3.Connection) -> list[dict[str, Any]]:
            layers = L.load(con)
            lay = layers.get(layer)
            sql = f"SELECT {SELECT} FROM rec r WHERE r.layer = ? AND r.deleted = 0"
            args: list[Any] = [lay.id]
            if kind is not None:
                sql += " AND r.kind = ?"
                args.append(kind)
            return [rev_of(r).record(layer) for r in con.execute(sql + " ORDER BY r.id", args).fetchall()]

        return self._read(fn)

    # ------------------------------------------------------------------------------------------------ writes

    def _commit(self, view: View, build: Callable[[Txn], list[Any]], **kw: Any) -> tuple[WriteResult, Txn]:
        def fn(con: sqlite3.Connection) -> tuple[WriteResult, Txn]:
            txn = Txn(self, con, view, **kw)
            res = txn.run(build(txn))
            changed = {p.id for p in txn.written()}
            if res.changeset and changed and txn.layers.above(txn.layer):
                M.rebase(self, con, lower=view.layer, changed=changed, by="rebase")
            if res.changeset and changed:
                M.replan_own(self, con, txn.layer, changed)
            return res, txn

        res, txn = self._writer.run(fn)
        self._notify(res.seq)
        return res, txn

    def write(self, ops: list[Op], view: View, *, by: str, message: str, client: str | None = None) -> WriteResult:
        """Apply ``ops`` as one atomic changeset on ``view.layer``."""
        ops = list(ops)
        return self._commit(view, lambda _txn: ops, by=by, message=message, client=client)[0]

    def put(
        self,
        rec: dict[str, Any],
        view: View,
        *,
        if_match: str | None,
        by: str,
        client: str | None = None,
        message: str = "",
    ) -> dict[str, Any]:
        """Replace or create one record (``rec`` carries ``kind``, ``id``, ``data`` and ``geom``)."""
        if not isinstance(rec, dict) or "kind" not in rec:
            raise Invalid("a record to put names its kind", errors=[{"path": "/kind", "message": "required"}])
        body = {"data": rec.get("data"), "geom": rec.get("geom")}
        for k in ("kv", "source"):
            if k in rec:
                body[k] = rec[k]
        rid = rec.get("id")

        def build(txn: Txn) -> list[Any]:
            cur = txn.resolve(rid) if rid is not None else None
            if cur is None or cur.deleted:
                if if_match is not None:
                    raise PreconditionFailed(
                        f"{rec['kind']} {rid} does not exist in layer {view.layer}",
                        current=None,
                        stale=[{"index": 0, "kind": rec["kind"], "id": rid, "if_match": if_match, "etag": None}],
                    )
                return [Op("create", rec["kind"], rid, None, body=body)]
            return [Op("put", rec["kind"], rid, if_match, body=body)]

        res, _ = self._commit(view, build, by=by, message=message or f"put {rec['kind']}", client=client)
        return res.records[0]

    def patch(
        self,
        kind: str,
        id: str,
        patch: list[dict[str, Any]],
        view: View,
        *,
        if_match: str,
        by: str,
        client: str | None = None,
        message: str = "",
    ) -> dict[str, Any]:
        """Apply RFC 6902 JSON Patch to one record's body (paths under ``/data`` and ``/geom``; nulls are kept)."""
        res, _ = self._commit(
            view,
            lambda _t: [Op("patch", kind, id, if_match, patch=patch)],
            by=by,
            message=message or f"patch {kind}",
            client=client,
        )
        return res.records[0]

    def delete(
        self, kind: str, id: str, view: View, *, if_match: str, by: str, client: str | None = None, message: str = ""
    ) -> dict[str, Any]:
        """Tombstone one record on ``view.layer``; returns the tombstone."""
        res, _ = self._commit(
            view,
            lambda _t: [Op("delete", kind, id, if_match)],
            by=by,
            message=message or f"delete {kind}",
            client=client,
        )
        return res.records[0]

    def restore(
        self, kind: str, id: str, version: int, view: View, *, if_match: str, by: str, client: str | None = None
    ) -> dict[str, Any]:
        """Write the content of a past version as a new version."""
        res, _ = self._commit(
            view,
            lambda _t: [InternalOp("restore", kind, id, if_match, version=int(version))],
            by=by,
            message=f"restore {kind} {id} to version {version}",
            client=client,
        )
        return res.records[0]

    def revert(self, changeset: str, *, by: str, client: str | None = None) -> WriteResult:
        """Undo ``changeset`` as a new ``revert`` changeset; ``Conflict(reason="revert")`` lists every record a later
        edit stands in the way of, with the diff from what the changeset produced to what is there now."""
        import jsonpatch

        def fn(con: sqlite3.Connection) -> WriteResult:
            slug, ops, blocked = revert_ops(con, changeset)
            if blocked:
                layers = L.load(con)
                lay = layers.get(slug)
                for b in blocked:
                    _l, version = b["if_match"].strip('"').rsplit(":", 1)
                    produced = L.hist_row(con, lay.id, b["id"], int(version))
                    row = con.execute(
                        f"SELECT {SELECT} FROM rec r WHERE r.layer = ? AND r.id = ?", (lay.id, b["id"])
                    ).fetchone()
                    if produced is not None and row is not None:
                        b["diff"] = list(
                            jsonpatch.make_patch(
                                {"data": produced["data"], "geom": produced["geom"]}, rev_of(row).body()
                            )
                        )
                        b["by"] = row[9]
                raise Conflict(
                    f"changeset {changeset} cannot be reverted: {len(blocked)} record(s) were edited since",
                    reason="revert",
                    conflicts=blocked,
                )
            txn = Txn(
                self,
                con,
                View(layer=slug),
                by=by,
                message=f"revert {changeset}",
                client=client,
                kind="revert",
                reverts=changeset,
            )
            res = txn.run(ops)
            changed = {p.id for p in txn.written()}
            if res.changeset and changed and txn.layers.above(txn.layer):
                M.rebase(self, con, lower=slug, changed=changed, by="rebase")
            return res

        res = self._writer.run(fn)
        self._notify(res.seq)
        return res

    def apply_import(
        self,
        run: ImportRun,
        records: Iterable[dict[str, Any]],
        *,
        dry_run: bool,
        ids: LG.IdLookupImpl | None = None,
        backup: bool = True,
    ) -> ImportReport:
        """Diff an importer's records against its layer by hash; report, or commit in one transaction. ``ids`` (an
        ``IdLookupImpl``) is flushed in that transaction; ``backup=False`` skips the pre-import backup."""
        from .imports import apply_import

        return apply_import(self, run, records, dry_run=dry_run, ids=ids, backup=backup)

    def import_run(self, run_id: int) -> dict[str, Any]:
        """The stored report of one import run (``/imports/{run}``)."""
        from .imports import report_of

        return report_of(self, run_id)

    def id_lookup(self, *, layer: str, namespace: str, ledger_dir: Path | None = None) -> LG.IdLookupImpl:
        """An ``IdLookupImpl`` over this store for an importer of ``layer`` minting in ``namespace``."""
        return LG.IdLookupImpl(self, layer=layer, namespace=namespace, ledger_dir=ledger_dir)

    # ------------------------------------------------------------------------------------------------ layers

    def layers(self) -> list[dict[str, Any]]:
        """Every layer: ``{"slug", "tier", "parent", "namespace", "state", "title", "note", "created", "by"}``."""
        layers = L.load(self._reader())
        return [r.describe(layers.slugs) for r in sorted(layers.by_id.values(), key=lambda r: r.id)]

    def layer(self, slug: str) -> dict[str, Any]:
        layers = L.load(self._reader())
        return layers.get(slug).describe(layers.slugs)

    def chain(self, view: View | str) -> list[str]:
        """The slugs a read in ``view`` looks through, in order."""
        slug = view.layer if isinstance(view, View) else view
        return [r.slug for r in L.load(self._reader()).chain(slug)]

    def create_layer(
        self,
        slug: str,
        *,
        tier: str | None = None,
        parent: str | None = "main",
        namespace: str | None = None,
        title: str | None = None,
        note: str | None = None,
        by: str = "",
    ) -> dict[str, Any]:
        """Create a scenario or proposal (under ``parent``), or an import or legacy layer."""

        def fn(con: sqlite3.Connection) -> dict[str, Any]:
            lay = L.create(con, slug, tier=tier, parent=parent, namespace=namespace, title=title, note=note, by=by)
            return lay.describe(L.load(con).slugs)

        return self._writer.run(fn)

    def promote(self, slug: str, *, by: str, message: str = "", client: str | None = None) -> WriteResult:
        """Promote ``slug`` into its parent (see ``_promote``). When records changed in the parent since they were
        copied up (a proposal pulled from a seed whose base is older than this database), the rebase planner runs
        for them first: disjoint changes merge as listed rebase changesets and the promote is tried once more; the
        rest become conflict rows (``crhub conflicts list``), named in the refusal."""
        try:
            return self._promote(slug, by=by, message=message, client=client)
        except Conflict as e:
            stale = {c["id"] for c in e.conflicts if c.get("reason") == "changed in the parent since"}
            if e.reason != "rebase" or not stale:
                raise
            parent = self.layer(slug)["parent"] or "main"
            reb = self._writer.run(lambda con: M.rebase(self, con, lower=parent, changed=stale, only=slug, by="rebase"))
            if reb["changesets"]:
                self._notify(self.last_seq())
            if not reb["conflicts"]:
                return self._promote(slug, by=by, message=message, client=client)
            raise Conflict(
                f"{e.detail}; {len(reb['conflicts'])} of them overlap Ben's revisions and are listed as conflicts "
                f"(crhub conflicts list --layer {slug}): resolve them, then promote again",
                reason="rebase",
                conflicts=e.conflicts,
            ) from None

    def _promote(self, slug: str, *, by: str, message: str = "", client: str | None = None) -> WriteResult:
        """Write a scenario's revisions to its parent as one ``promote`` changeset, each with If-Match against the
        parent's revision it was copied from; the layer becomes ``promoted``. ``Conflict(reason="rebase")`` lists
        every record the parent changed since (nothing is written then)."""

        def fn(con: sqlite3.Connection) -> WriteResult:
            layers = L.load(con)
            lay = layers.get(slug)
            if lay.tier not in ("scenario", "proposal"):
                raise Invalid(f"only scenarios and proposals are promoted, not {slug} ({lay.tier})")
            if lay.state != "open":
                raise Conflict(
                    f"layer {slug} is {lay.state}", reason="layer", conflicts=[{"kind": "layer", "id": slug}]
                )
            parent = layers.by_id[lay.parent] if lay.parent is not None else layers.get("main")
            pchain = layers.chain(parent.slug)
            ops: list[Any] = []
            blocked: list[dict[str, Any]] = []
            for row in con.execute(f"SELECT {SELECT} FROM rec r WHERE r.layer = ? ORDER BY r.id", (lay.id,)):
                ours = rev_of(row)
                pcur = L.resolve(con, pchain, ours.id)
                live = pcur is not None and not pcur.deleted
                tag = etag(layers.slugs[pcur.layer], pcur.version) if pcur is not None else None
                if ours.base_hash is None:
                    if live:
                        blocked.append({"kind": ours.kind, "id": ours.id, "reason": "created on both", "etag": tag})
                    elif not ours.deleted:
                        ops.append(InternalOp("create", ours.kind, ours.id, None, body=ours.body(), check_match=False))
                    continue
                if not live or pcur.hash != ours.base_hash:  # type: ignore[union-attr]
                    blocked.append(
                        {"kind": ours.kind, "id": ours.id, "reason": "changed in the parent since", "etag": tag}
                    )
                    continue
                if ours.deleted:
                    ops.append(InternalOp("delete", ours.kind, ours.id, tag))
                else:
                    ops.append(InternalOp("put", ours.kind, ours.id, tag, body=ours.body()))
            if blocked:
                raise Conflict(
                    f"promote of {slug}: {len(blocked)} record(s) changed in {parent.slug} since they were copied up",
                    reason="rebase",
                    conflicts=blocked,
                )
            txn = Txn(
                self,
                con,
                View(layer=parent.slug),
                by=by,
                message=message or f"promote {slug}",
                client=client,
                kind="promote",
            )
            res = txn.run(ops)
            L.set_state(con, lay, "promoted")
            changed = {p.id for p in txn.written()}
            if res.changeset and changed and txn.layers.above(txn.layer):
                M.rebase(self, con, lower=parent.slug, changed=changed, by="rebase")
            return res

        res = self._writer.run(fn)
        self._notify(res.seq)
        return res

    def set_layer_state(self, slug: str, state: str) -> dict[str, Any]:
        """Archive or reopen a scenario or proposal."""

        def fn(con: sqlite3.Connection) -> dict[str, Any]:
            layers = L.load(con)
            lay = layers.get(slug)
            if lay.tier not in ("scenario", "proposal"):
                raise Invalid(f"only scenarios and proposals change state, not {slug}")
            L.set_state(con, lay, state)
            return L.load(con).get(slug).describe(layers.slugs)

        return self._writer.run(fn)

    def tag(self, slug: str, name: str, *, by: str, note: str | None = None) -> dict[str, Any]:
        """Name ``slug`` as it stands now; read it back with ``get(..., tag=name)`` and ``list(..., tag=name)``."""
        return self._writer.run(lambda con: L.tag(con, L.load(con).get(slug), name, by=by, note=note))

    def tags(self, slug: str) -> list[dict[str, Any]]:
        con = self._reader()
        return L.tags(con, L.load(con).get(slug))

    def diff_layers(self, slug: str, against: str | None = None) -> list[dict[str, Any]]:
        """What ``slug``'s own revisions change against ``against`` (default: its parent's view), record by record:
        ``[{"kind", "id", "op", "fields", "ours", "theirs"}]`` with ``op`` ``create``, ``put`` or ``delete``."""
        from .records import changed_fields

        def fn(con: sqlite3.Connection) -> list[dict[str, Any]]:
            layers = L.load(con)
            lay = layers.get(slug)
            if against is not None:
                other = layers.chain(against)
            elif lay.parent is not None:
                other = layers.chain(layers.by_id[lay.parent].slug)
            else:
                other = layers.chain(slug)[1:]
            out = []
            for row in con.execute(f"SELECT {SELECT} FROM rec r WHERE r.layer = ? ORDER BY r.id", (lay.id,)):
                ours = rev_of(row)
                theirs = L.resolve(con, other, ours.id)
                t_live = theirs is not None and not theirs.deleted
                if ours.deleted:
                    if not t_live:
                        continue
                    op, fields = "delete", ["deleted"]
                elif not t_live:
                    op, fields = "create", changed_fields(None, ours.body())
                elif theirs.hash == ours.hash:  # type: ignore[union-attr]
                    continue
                else:
                    op, fields = "put", changed_fields(theirs.body(), ours.body())  # type: ignore[union-attr]
                out.append(
                    {
                        "kind": ours.kind,
                        "id": ours.id,
                        "op": op,
                        "fields": fields,
                        "ours": etag(slug, ours.version),
                        "theirs": etag(layers.slugs[theirs.layer], theirs.version) if theirs else None,
                    }
                )
            return out

        return self._read(fn)

    def flip_authority(self, kind: str, *, by: str, ruling: str | None = None) -> WriteResult:
        """Hand ``kind`` to the model: its ``authority`` record says ``model`` in main, and every legacy revision of
        the kind is squashed into main, as one ``legacy`` changeset (9.23)."""
        self.kinds[kind]

        def build(txn: Txn) -> list[Any]:
            ops: list[Any] = []
            found = None
            chain = txn.layers.chain("main")
            marks = ",".join("?" * len(chain))
            for (rid,) in txn.con.execute(
                f"SELECT DISTINCT id FROM rec WHERE kind = 'authority' AND name = ? AND layer IN ({marks})",
                (kind, *[c.id for c in chain]),
            ).fetchall():
                rev = txn.resolve(rid)
                if rev is not None and not rev.deleted:
                    found = rev
                    break
            data = {"kind": kind, "owner": "model", "ruling": ruling, "note": None}
            if found is not None:
                ops.append(InternalOp("put", "authority", found.id, txn.etag_of(found), body={"data": data}))
            else:
                ops.append(Op("create", "authority", None, None, body={"data": data, "geom": None}))
            for lay in txn.layers.of_tier("legacy"):
                for row in txn.con.execute(
                    f"SELECT {SELECT} FROM rec r WHERE r.layer = ? AND r.kind = ? ORDER BY r.id", (lay.id, kind)
                ).fetchall():
                    rev = rev_of(row)
                    cur = txn.resolve(rev.id)
                    if cur is None or cur.layer != lay.id:
                        continue
                    if rev.deleted:
                        ops.append(InternalOp("delete", kind, rev.id, txn.etag_of(cur)))
                    else:
                        ops.append(InternalOp("put", kind, rev.id, txn.etag_of(cur), body=rev.body(), force=True))
            return ops

        return self._commit(View(), build, by=by, message=f"authority of {kind} to model", kind="legacy")[0]

    # -------------------------------------------------------------------------------------------- changesets

    def changesets(
        self,
        *,
        by: str | None = None,
        since: int | str | None = None,
        layer: str | None = None,
        kind: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Changesets, newest first (``since``: an event seq, or an ISO time)."""
        con = self._reader()
        layers = L.load(con)
        sql = "SELECT id, layer, by, client, message, kind, reverts, created, count, seq FROM changeset WHERE 1 = 1"
        args: list[Any] = []
        if by is not None:
            sql += " AND by = ?"
            args.append(by)
        if layer is not None:
            sql += " AND layer = ?"
            args.append(layers.get(layer).id)
        if kind is not None:
            sql += " AND kind = ?"
            args.append(kind)
        if isinstance(since, int):
            sql += " AND seq > ?"
            args.append(since)
        elif isinstance(since, str):
            sql += " AND created >= ?"
            args.append(since)
        rows = con.execute(sql + " ORDER BY seq DESC LIMIT ?", (*args, int(limit))).fetchall()
        keys = ("id", "layer", "by", "client", "message", "kind", "reverts", "created", "count", "seq")
        out = []
        for r in rows:
            d = dict(zip(keys, r, strict=True))
            d["layer"] = layers.slugs.get(d["layer"])
            out.append(d)
        return out

    def changeset(self, id: str) -> dict[str, Any]:
        """One changeset with the records it wrote (``records``: get() shape of each revision it produced)."""
        con = self._reader()
        row = con.execute(
            "SELECT id, layer, by, client, message, kind, reverts, created, count, seq FROM changeset WHERE id = ?",
            (id,),
        ).fetchone()
        if not row:
            raise NotFound(f"no changeset {id}")
        keys = ("id", "layer", "by", "client", "message", "kind", "reverts", "created", "count", "seq")
        d = dict(zip(keys, row, strict=True))
        d["layer"] = L.load(con).slugs.get(d["layer"])
        d["records"] = [
            json.loads(r[0])
            for r in con.execute("SELECT row FROM rec_hist WHERE changeset = ? ORDER BY rowid", (id,)).fetchall()
        ]
        return d

    # --------------------------------------------------------------------------------------------- conflicts

    def conflicts(
        self, *, state: str | None = "open", layer: str | None = None, import_run: int | None = None
    ) -> list[dict[str, Any]]:
        """The review queue: conflict rows (``/conflicts``)."""
        con = self._reader()
        lay = L.load(con).get(layer) if layer is not None else None
        return M.list_conflicts(con, state=state, layer=lay, import_run=import_run)

    def resolve_conflict(self, id: str, take: str, body: dict[str, Any] | None = None, *, by: str) -> dict[str, Any]:
        """Resolve a conflict: ``ours``, ``theirs`` or ``merged`` (with ``body``)."""
        out = self._writer.run(lambda con: M.resolve_conflict(self, con, id, take, body, by=by))
        if out.get("changeset"):
            self._notify(self.last_seq())
        return out

    def rebase(self, *, lower: str | None = None, by: str = "rebase", only: str | None = None) -> dict[str, Any]:
        """Run the rebase planner over every copied-up revision above ``lower`` (all layers when ``None``), on layer
        ``only`` alone when given (``POST /layers/{slug}/rebase``, ``crhub model rebase``)."""
        out = self._writer.run(lambda con: M.rebase(self, con, lower=lower, by=by, only=only))
        if out["changesets"]:
            self._notify(self.last_seq())
        return out

    # ---------------------------------------------------------------------------------------------- checking

    def check_data(self) -> list[dict[str, Any]]:
        """Validate every current revision again (``doctor --data``): schema, geometry, dates and refs. Returns the
        problems as ``{"layer", "kind", "id", "path", "message"}``."""

        def fn(con: sqlite3.Connection) -> list[dict[str, Any]]:
            layers = L.load(con)
            out = []
            for row in con.execute(f"SELECT {SELECT} FROM rec r WHERE r.deleted = 0 ORDER BY r.layer, r.id"):
                rev: Rev = rev_of(row)
                slug = layers.slugs[rev.layer]
                if rev.kind not in self.kinds:
                    out.append(
                        {"layer": slug, "kind": rev.kind, "id": rev.id, "path": "/kind", "message": "unknown kind"}
                    )
                    continue
                kind = self.kinds[rev.kind]
                try:
                    c = content(kind, rev.id, {"data": rev.data, "geom": rev.geom, "kv": rev.kv})
                except Invalid as e:
                    for err in e.errors or [{"path": "", "message": str(e)}]:
                        out.append({"layer": slug, "kind": rev.kind, "id": rev.id, **err})
                    continue
                if c.hash != rev.hash:
                    out.append(
                        {
                            "layer": slug,
                            "kind": rev.kind,
                            "id": rev.id,
                            "path": "/hash",
                            "message": "stored hash differs from the content",
                        }
                    )
                chain = layers.chain(slug)
                for role, value, spec, _at in c.refs:
                    if not isinstance(value, str):
                        continue
                    dst = L.resolve(con, chain, value)
                    if dst is None or dst.deleted or dst.kind not in spec.kinds:
                        out.append(
                            {
                                "layer": slug,
                                "kind": rev.kind,
                                "id": rev.id,
                                "path": f"/data ref {role}",
                                "message": f"ref to {value} does not resolve",
                            }
                        )
            return out

        return self._read(fn)

    def checkpoint(self) -> None:
        """``PRAGMA wal_checkpoint(TRUNCATE)`` on the writer (after imports; the writer also runs it on shutdown).
        Readers still inside a transaction can keep part of the WAL; that is not an error. A read-only store does
        nothing."""
        if self.readonly:
            return
        self._writer.run(lambda con: con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall(), transaction=False)

    def quick_check(self) -> list[str]:
        from .backup import quick_check

        return quick_check(self._reader())

    def pre_import_backup(self) -> Path | None:
        """A ``pre-import`` backup into the backup folder, then the retention tiers (the newest 10 kept). ``None``
        when backups are off for this store (read-only, or ``auto_backups`` set false)."""
        if self.readonly or not self.auto_backups:
            return None
        from .backup import prune

        path = self.backup("pre-import")
        prune(self.backup_dir)
        return path

    def backup(self, reason: str = "manual", dest: Path | None = None) -> Path:
        """An online, checked backup of this database into ``dest`` (default the store's backup folder)."""
        from .backup import backup_connection

        return backup_connection(self._reader(), Path(dest) if dest is not None else self.backup_dir, reason)


def open_store(
    path: Path,
    *,
    cache: Path | None = None,
    kinds_paths: list[Path] | None = None,
    validators: dict[str, Callable[..., Any]] | None = None,
    backup_dir: Path | None = None,
    create: bool = True,
    readonly: bool = False,
) -> SqliteStore:
    """Open (creating and migrating) the truth database at ``path``.

    - ``cache``: ``cache.db`` to attach to readers as schema ``cache`` (WP3 owns its tables); never attached to the
      writer, so truth writes do not take cache.db's write lock. Its folder is created when absent.
    - ``kinds_paths``: kind files or folders of them (default: the core kinds and every feature's).
    - ``validators``: ``{kind: Validator}`` (default: every ``VALIDATORS`` of the features holding the kinds).
    - ``backup_dir``: where pre-migrate and manual backups go (default ``<db folder>/backups``).
    - ``create=False`` refuses a missing database (``NotFound``) instead of creating an empty one.
    - ``readonly=True`` opens an existing database ``mode=ro`` and changes nothing: no migration (and so no
      pre-migrate backup), no namespace layers made, no kind-table sync, no writer thread. Writes raise
      ``db.ReadOnlyWrite``. The kinds still come from the kind files; ``validators`` default to none, since nothing
      is written. ``pending_migrations()`` says whether the file is older than this code (reads of tables a pending
      migration adds then fail). A ``cache`` is attached ``mode=ro`` and must exist. Use it for commands that only
      read (``crhub model check`` and ``info``, ``doctor --data``), which may run beside a serving hub.

    A read-write database file must pass the write guard (``fsio.check_write``); a read-only one need not.
    """
    path = Path(path)
    if not path.is_file() and (readonly or not create):
        raise NotFound(f"no database at {path} (run crhub setup to create it)")
    if readonly:
        bdir = Path(backup_dir) if backup_dir is not None else path.parent / "backups"
        return SqliteStore(
            path,
            cache=cache,
            kinds=load_kinds(kinds_paths),
            validators=dict(validators or {}),
            backup_dir=bdir,
            readonly=True,
        )
    fsio.check_write(path)
    if cache is not None:
        fsio.check_write(cache)
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    kinds = load_kinds(kinds_paths)
    found = _discover_validators(kinds) if validators is None else dict(validators)
    bdir = Path(backup_dir) if backup_dir is not None else path.parent / "backups"
    writer = D.writer_for(path)
    try:
        writer.run(lambda con: migrate(con, backup_dir=bdir), transaction=False)

        def setup(con: sqlite3.Connection) -> None:
            L.ensure_namespace_layers(con)
            _sync_kinds(con, kinds)

        writer.run(setup)
        store = SqliteStore(path, cache=cache, kinds=kinds, validators=found, backup_dir=bdir)
    finally:
        D.release_writer(path)
    return store


__all__ = ["SqliteStore", "open_store"]
