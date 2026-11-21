"""Seeds v2: the design in git, one file per record, per layer (decisions 9.24 and 9.29).

    region/seed/main/<kind>/<id>.json                written only by Ben's export (lane B)
    region/seed/proposals/<slug>/<kind>/<id>.json    a cloud session's proposal layer (lane A), with _layer.json

Only the ``main`` layer and proposal layers are seeded, and only kinds whose file says ``seeded: true``. Import and
legacy layers rebuild from their sources; scenarios stay in the database.

**A seed file** is ``{"id", "kind", "kv", "geom", "data"}`` (geometry as canonical WKT, snapped to 1 mm), plus
``"deleted": true`` for a tombstone (a deletion of Ben's must survive a rebuild) and ``"base"`` for a revision copied up
from a layer below (the content hash it was made from, so a rebuilt database still knows what to rebase). Keys are
sorted, the text is UTF-8 with LF line endings and a final newline. Bookkeeping (version, created, updated, by,
changeset) is left out, so a rebuilt database exports the same bytes.

**Import** is a three-way merge per record against ``seed_base``, the seed as last exported or imported here:

- the seed unchanged since then: ours stands;
- ours unchanged since then: take the seed;
- both the same: nothing to do;
- both changed: ours stays and a ``both_changed`` conflict carries the seed's revision (``crhub`` lists it). While
  it is open, each seed import refreshes it against Ben's revision as it is then (so it can always be resolved) and
  dismisses it once the seed and the database agree. The rebase planner never closes or replaces it;
- a record new in the seed is added; a record gone from the seed is kept and listed.

Comparisons use the seed form of a record (``seed_text``), so bookkeeping can never raise a false conflict (defect 1
of the old store). A seed file is first made into the content it would write (validated, upgraded, geometry snapped)
and compared in that form, so a minimal or hand-written file compares exactly as an exported one does. One seed
import is one transaction and one ``seed`` changeset per layer: records may refer to each other in any order, and a
failure leaves the database as it was.

**Export** first imports any pulled seeds, and refuses while a seed conflict is open, so it never overwrites a change
it has not merged. It writes only files whose bytes change, removes the files of records no longer on the layer, and
records the new ``seed_base``. Two exports in a row give byte-identical output.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from region.core import fsio, ids, paths
from region.core.errors import Conflict, Invalid
from region.core.protocols import etag
from region.core.view import View

from . import layers as L
from .db import now
from .records import SELECT, Rev, content, rev_of

if TYPE_CHECKING:
    from .store import SqliteStore

SEED = paths.repo_root() / "region" / "seed"
SEED_KEYS = frozenset({"id", "kind", "kv", "geom", "data", "deleted", "base"})
LAYER_FILE = "_layer.json"
SEEDED_TIERS = ("main", "proposal")


def seed_text(obj: dict[str, Any]) -> str:
    """The seed form of a record: sorted keys, indent 1, UTF-8 text, LF, a final newline."""
    return json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + "\n"


def seed_obj(rev: Rev) -> dict[str, Any]:
    """The seed object of a stored revision."""
    obj: dict[str, Any] = {"id": rev.id, "kind": rev.kind, "kv": rev.kv, "geom": rev.geom, "data": rev.data}
    if rev.deleted:
        obj["deleted"] = True
    if rev.base_hash:
        obj["base"] = rev.base_hash
    return obj


def seed_hash(obj: dict[str, Any]) -> str:
    return fsio.sha256_hex(seed_text(obj))


def layer_dir(root: Path, slug: str) -> Path:
    """Where a seeded layer's files live under ``root``."""
    if slug == "main":
        return root / "main"
    name = slug.split(":", 1)[1] if ":" in slug else slug
    paths.check_name(name)
    return root / "proposals" / name


def _seeded_layers(layers: L.Layers) -> list[L.Layer]:
    return [
        r
        for r in sorted(layers.by_id.values(), key=lambda r: r.id)
        if r.tier in SEEDED_TIERS and r.state in ("open", "promoted")
    ]


# ------------------------------------------------------------------------------------------------------ import


def _read_layer(d: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    objs: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    meta: dict[str, Any] = {}
    if (d / LAYER_FILE).is_file():
        meta = fsio.read_json(d / LAYER_FILE)
    for kdir in sorted(p for p in d.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        for f in sorted(kdir.glob("*.json")):
            if f.name.startswith(("_", ".")):
                continue
            where = f"{kdir.name}/{f.name}"
            try:
                obj = json.loads(fsio.read_text(f))
            except json.JSONDecodeError as e:
                errors.append({"path": where, "message": f"not JSON: {e}"})
                continue
            if not isinstance(obj, dict) or set(obj) - SEED_KEYS or not {"id", "kind", "data"} <= set(obj):
                errors.append({"path": where, "message": "a seed file is {id, kind, kv, geom, data}"})
                continue
            if obj["kind"] != kdir.name or obj["id"] != f.stem:
                errors.append({"path": where, "message": f"names {obj.get('kind')}/{obj.get('id')}, not its path"})
                continue
            if obj["id"] in seen:
                errors.append({"path": where, "message": f"id {obj['id']} is also {seen[obj['id']]}"})
                continue
            seen[obj["id"]] = where
            objs.append(obj)
    if errors:
        raise Invalid(
            f"seed {d}: {len(errors)} file(s) refused: {errors[0]['path']}: {errors[0]['message']}", errors=errors
        )
    return objs, meta


def _source(d: Path) -> dict[str, Any]:
    listing = []
    for f in sorted(d.rglob("*.json")):
        listing.append(f"{f.relative_to(d).as_posix()} {fsio.sha256_hex(fsio.read_text(f))}")
    try:
        uri = paths.to_uri(d)
    except Invalid:
        uri = d.resolve().as_posix()
    return {"seed": {"uri": uri, "sha256": fsio.sha256_hex("\n".join(listing))}}


def _close(con: sqlite3.Connection, conflict_id: str, why: str, by: str) -> None:
    con.execute(
        "UPDATE conflict SET state = 'dismissed', resolution = ?, resolved_by = ? WHERE id = ?", (why, by, conflict_id)
    )


def _import_layer(store: SqliteStore, slug: str, d: Path, *, by: str) -> dict[str, Any]:
    from .changesets import InternalOp, Txn
    from .merge import SEED_RUNS, rebase, upsert_conflict

    objs, meta = _read_layer(d)
    source = _source(d)

    def fn(con: sqlite3.Connection) -> dict[str, Any]:
        layers = L.load(con)
        if slug not in layers.by_slug:
            L.create(
                con,
                slug,
                tier="proposal" if slug != "main" else None,
                parent=meta.get("parent") or "main",
                title=meta.get("title"),
                note=meta.get("note"),
                by=by,
            )
            layers = L.load(con)
        lay = layers.get(slug)
        out: dict[str, Any] = {
            "taken": 0,
            "kept": 0,
            "added": 0,
            "same": 0,
            "conflicts": [],
            "removed_in_seed": [],
            "changeset": None,
            "run": None,
        }
        if lay.state != "open":
            out["skipped"] = f"layer {slug} is {lay.state}"
            return out
        cur = con.execute(
            "INSERT INTO import_run (importer, version, layer, sources, dry_run, state, started) "
            "VALUES ('seed', '2', ?, ?, 0, 'running', ?)",
            (lay.id, json.dumps(source), now()),
        )
        run_id = int(cur.lastrowid or 0)
        out["run"] = run_id
        chain = layers.chain(slug)
        base_of = dict(con.execute("SELECT id, hash FROM seed_base WHERE layer = ?", (lay.id,)).fetchall())
        open_seed = dict(
            con.execute(
                f"SELECT rec_id, id FROM conflict WHERE layer = ? AND state = 'open' AND import_run IN {SEED_RUNS}",
                (lay.id,),
            ).fetchall()
        )
        ops: list[Any] = []
        bases: list[tuple[str, str]] = []
        for obj in objs:
            kind = store.kinds[obj["kind"]]
            body = {"data": obj["data"], "geom": obj.get("geom"), "kv": obj.get("kv", kind.version)}
            base = obj.get("base") or ""
            tomb = bool(obj.get("deleted"))
            # the seed form of what this file would write (validated, upgraded, geometry snapped), so a minimal or
            # hand-written file compares with the database exactly as an exported one does
            c = content(kind, obj["id"], body)
            canon: dict[str, Any] = {"id": c.id, "kind": c.kind, "kv": c.kv, "geom": c.geom, "data": c.data}
            if tomb:
                canon["deleted"] = True
            if base:
                canon["base"] = base
            hs = seed_hash(canon)
            bases.append((obj["id"], hs))
            hb = base_of.get(obj["id"])
            row = con.execute(
                f"SELECT {SELECT} FROM rec r WHERE r.layer = ? AND r.id = ?", (lay.id, obj["id"])
            ).fetchone()
            own = rev_of(row) if row else None
            ho = seed_hash(seed_obj(own)) if own is not None else None
            if own is not None:
                waiting = open_seed.get(obj["id"])
                if ho == hs:
                    out["same"] += 1
                    if waiting is not None:
                        _close(con, waiting, "the seed and the database agree", by)
                    continue
                if ho != hb:
                    if hs == hb and waiting is None:
                        out["kept"] += 1
                        continue
                    # both changed, or a seed change still waiting for Ben: (re)open the conflict against his
                    # revision as it is now, so it can always be resolved
                    conflict = upsert_conflict(
                        con,
                        lay,
                        obj["id"],
                        kind.name,
                        "both_changed",
                        ours_hash=own.hash,
                        theirs_hash=c.hash,
                        base_hash=None,
                        proposed={"data": c.data, "geom": c.geom, **({"deleted": True} if tomb else {})},
                        fields=[],
                        import_run=run_id,
                    )
                    out["conflicts"].append(conflict)
                    continue
                # ours is unchanged since the seed was last seen here: take the seed
                if waiting is not None:
                    _close(con, waiting, "taken from the seed", by)
                tag = etag(slug, own.version)
                if tomb and not own.deleted:
                    ops.append(InternalOp("delete", kind.name, obj["id"], tag, body=body, base=base, prepared=c))
                else:
                    ops.append(
                        InternalOp("put", kind.name, obj["id"], tag, body=body, base=base, tombstone=tomb, prepared=c)
                    )
                out["taken"] += 1
                continue
            below = L.resolve(con, chain[1:], obj["id"])
            live = below is not None and not below.deleted
            if tomb:
                if live:
                    assert below is not None
                    ops.append(
                        InternalOp(
                            "delete",
                            kind.name,
                            obj["id"],
                            etag(layers.slugs[below.layer], below.version),
                            body=body,
                            base=base,
                            prepared=c,
                        )
                    )
                else:
                    ops.append(
                        InternalOp(
                            "put",
                            kind.name,
                            obj["id"],
                            None,
                            body=body,
                            base=base,
                            tombstone=True,
                            check_match=False,
                            prepared=c,
                        )
                    )
            elif live:
                assert below is not None
                ops.append(
                    InternalOp(
                        "put",
                        kind.name,
                        obj["id"],
                        etag(layers.slugs[below.layer], below.version),
                        body=body,
                        base=base,
                        prepared=c,
                    )
                )
            else:
                ops.append(
                    InternalOp(
                        "create", kind.name, obj["id"], None, body=body, base=base, check_match=False, prepared=c
                    )
                )
            out["added"] += 1
        res = None
        changed: set[str] = set()
        if ops:
            txn = Txn(
                store,
                con,
                View(layer=slug),
                by=by,
                message=f"seed import {d.name}",
                kind="seed",
                import_run=run_id,
                on_delete=False,
            )
            res = txn.run(ops)
            out["changeset"] = res.changeset
            out["seq"] = res.seq
            changed = {p.id for p in txn.written()}
        con.executemany(
            "INSERT INTO seed_base (layer, id, hash) VALUES (?, ?, ?) "
            "ON CONFLICT (layer, id) DO UPDATE SET hash = excluded.hash",
            [(lay.id, i, h) for i, h in bases],
        )
        present = {o["id"] for o in objs}
        out["removed_in_seed"] = sorted(i for i in base_of if i not in present)
        if changed and layers.above(lay):
            reb = rebase(store, con, lower=slug, changed=changed, import_run=run_id, by="rebase")
            out["rebase"] = reb["changesets"]
        counts = {k: out[k] for k in ("taken", "kept", "added", "same")}
        counts["conflicts"] = len(out["conflicts"])
        con.execute(
            "UPDATE import_run SET state = ?, counts = ?, changeset = ?, finished = ? WHERE id = ?",
            ("applied" if ops else "unchanged", json.dumps(counts), out["changeset"], now(), run_id),
        )
        return out

    out = store._writer.run(fn)
    if out.get("changeset"):
        store.checkpoint()
    store._notify(out.get("seq"))
    return out


def import_seed(store: SqliteStore, seed: Path = SEED, *, layer: str | None = None, by: str = "seed") -> dict:
    """Merge seed files into the database (see the module doc).

    ``seed`` is a seed root (holding ``main/`` and ``proposals/``), or, with ``layer``, one layer's folder. Returns
    ``{"layers": {slug: {taken, kept, added, same, conflicts, removed_in_seed, changeset, run}}}``.
    """
    seed = Path(seed)
    dirs: list[tuple[str, Path]] = []
    if layer is not None:
        dirs.append((layer, seed))
    else:
        if (seed / "main").is_dir():
            dirs.append(("main", seed / "main"))
        if (seed / "proposals").is_dir():
            for d in sorted(p for p in (seed / "proposals").iterdir() if p.is_dir() and not p.name.startswith(".")):
                dirs.append((f"proposal:{d.name}", d))
    report: dict[str, Any] = {"layers": {}}
    for slug, d in dirs:
        report["layers"][slug] = _import_layer(store, slug, d, by=by)
    return report


def open_seed_conflicts(store: SqliteStore) -> list[dict[str, Any]]:
    """Open conflicts raised by seed imports (export refuses while any remain)."""
    con = store._reader()
    runs = {r[0] for r in con.execute("SELECT id FROM import_run WHERE importer = 'seed'").fetchall()}
    return [c for c in store.conflicts(state="open") if c.get("import_run") in runs]


# ------------------------------------------------------------------------------------------------------ export


def export(store: SqliteStore, out: Path = SEED) -> dict:
    """Write the seeded layers to ``out`` (see the module doc); returns
    ``{"imported": ..., "layers": {slug: {records, written, unchanged, removed}}}``."""
    out = Path(out)
    imported = import_seed(store, out) if out.is_dir() else {"layers": {}}
    pending = open_seed_conflicts(store)
    if pending:
        raise Conflict(
            f"export refused: {len(pending)} seed change(s) are not merged; resolve them first",
            reason="seed",
            conflicts=[
                {"kind": c["kind"], "id": c["rec_id"], "layer": c["layer"], "conflict": c["id"]} for c in pending
            ],
        )

    def collect(con: sqlite3.Connection) -> list[tuple[L.Layer, list[Rev], L.Layers]]:
        layers = L.load(con)
        got = []
        for lay in _seeded_layers(layers):
            revs = [
                rev_of(r)
                for r in con.execute(
                    f"SELECT {SELECT} FROM rec r WHERE r.layer = ? ORDER BY r.id", (lay.id,)
                ).fetchall()
            ]
            got.append((lay, revs, layers))
        return got

    snapshot = store._read(collect)
    report: dict[str, Any] = {"imported": imported, "layers": {}}
    bases: list[tuple[int, str, str]] = []
    for lay, revs, layers in snapshot:
        d = layer_dir(out, lay.slug)
        stats = {"records": 0, "written": 0, "unchanged": 0, "removed": 0, "skipped_kinds": []}
        keep: set[Path] = set()
        if lay.tier == "proposal":
            meta = {
                "slug": lay.slug,
                "parent": layers.slugs.get(lay.parent) if lay.parent else "main",
                "title": lay.title,
                "note": lay.note,
            }
            f = d / LAYER_FILE
            text = seed_text(meta)
            if not f.is_file() or f.read_bytes() != text.encode("utf-8"):
                fsio.write_atomic(f, text)
        skipped: set[str] = set()
        for rev in revs:
            kind = store.kinds.get(rev.kind)
            if kind is None or not kind.seeded:
                if kind is None:
                    skipped.add(rev.kind)
                continue
            obj = seed_obj(rev)
            text = seed_text(obj)
            f = d / rev.kind / f"{rev.id}.json"
            keep.add(f)
            stats["records"] += 1
            bases.append((lay.id, rev.id, fsio.sha256_hex(text)))
            if f.is_file() and f.read_bytes() == text.encode("utf-8"):
                stats["unchanged"] += 1
                continue
            fsio.write_atomic(f, text)
            stats["written"] += 1
        if d.is_dir():
            for kdir in sorted(p for p in d.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
                for f in sorted(kdir.glob("*.json")):
                    if f not in keep and ids.is_ulid(f.stem):
                        fsio.check_write(f)
                        f.unlink()
                        stats["removed"] += 1
        stats["skipped_kinds"] = sorted(skipped)
        report["layers"][lay.slug] = stats

    def record(con: sqlite3.Connection) -> None:
        con.executemany(
            "INSERT INTO seed_base (layer, id, hash) VALUES (?, ?, ?) "
            "ON CONFLICT (layer, id) DO UPDATE SET hash = excluded.hash",
            bases,
        )
        con.execute(
            "INSERT INTO meta (key, value) VALUES ('last_export', ?) "
            "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (now(),),
        )

    store._writer.run(record)
    return report


__all__ = [
    "LAYER_FILE",
    "SEED",
    "export",
    "import_seed",
    "layer_dir",
    "open_seed_conflicts",
    "seed_hash",
    "seed_obj",
    "seed_text",
]
