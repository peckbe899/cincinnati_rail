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
- both changed: ours stays and a ``both_changed`` conflict carries the seed's revision (``crhub conflicts list``
  shows it, ``crhub conflicts resolve`` settles it). While it is open, each seed import refreshes it against Ben's
  revision as it is then (so it can always be resolved) and dismisses it once the seed and the database agree. The
  rebase planner never closes or replaces it;
- a record new in the seed is added; a record gone from the seed is kept and listed.

Two states make ``seed_base`` say nothing about the folder being read, so nothing is taken or added silently and
every difference is a listed ``both_changed`` conflict (a record the layer lacks gets one too, resolved by writing
it or keeping it out): the first import after a restore (``region.model.backup``), and a layer folder other than the
one the layer was last exported to or imported from (``seed_roots``: another checkout sharing ``var``). The new
folder is recorded after the import. Comparisons with ``seed_base`` use the file as written and the stored
revision, and the ``same`` test also compares both upgraded to the kind's current version, so a kind version bump
alone never raises a conflict.

A record whose ref dangles in this database (an import below dropped its target, which imports allow) is written as
the seed has it and listed as a ``dangling_ref`` conflict (not a seed conflict: export goes on), so one record never
keeps a layer out of a fresh database. A copy-up whose base is older than what this database holds below (a cloud
session built from an older seed) is rebased at once, so it merges or becomes a conflict instead of blocking a
promote. A seed import that takes or adds records takes a ``pre-import`` backup first.

A proposal layer not yet in the database is created under the parent its ``_layer.json`` names. Proposals are
imported parents first, so one may sit on another proposal of the same seed. A proposal whose parent is not in this
database (a scenario that lives only on the machine that wrote it, say), or cannot hold a proposal, is skipped: the
report lists it under ``skipped`` with the reason, the other layers import as usual, and export leaves its folder as
it is.

Comparisons use the seed form of a record (``seed_text``), so bookkeeping can never raise a false conflict (defect 1
of the old store). A seed file is first made into the content it would write (validated, upgraded, geometry snapped)
and compared in that form, so a minimal or hand-written file compares exactly as an exported one does. One seed
import is one transaction and one ``seed`` changeset per layer: records may refer to each other in any order, and a
failure leaves the database as it was.

**Export** first imports any pulled seeds. A layer with an open seed conflict is not written, so export never
overwrites a change it has not merged; the other layers are written, and export then raises ``Conflict(reason=
"seed")`` naming the blocked layers and their conflicts (``crhub conflicts list`` shows them, ``crhub conflicts
resolve`` settles them). A promoted or frozen layer takes no seed import, so its folder is left as it is when it holds
changes the layer never took in. A layer whose name cannot be a folder is reported and skipped, never fatal to the
others. Export writes only files whose bytes change, removes the files of records no longer on the layer (with the
same retry as ``fsio.write_atomic`` on Windows), and records the new ``seed_base``. Two exports in a row give
byte-identical output.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from region.core import fsio, ids, paths
from region.core.errors import Conflict, Invalid, NotFound
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
        try:
            meta = fsio.read_json(d / LAYER_FILE)
        except (OSError, ValueError) as e:  # merge-conflict markers, cp1252 bytes (UnicodeDecodeError is one)
            errors.append({"path": LAYER_FILE, "message": f"cannot be read as UTF-8 JSON: {e}"})
        if not isinstance(meta, dict):
            errors.append({"path": LAYER_FILE, "message": "is not a JSON object"})
            meta = {}
    for kdir in sorted(p for p in d.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        for f in sorted(kdir.glob("*.json")):
            if f.name.startswith(("_", ".")):
                continue
            where = f"{kdir.name}/{f.name}"
            try:
                obj = json.loads(fsio.read_text(f))
            except UnicodeDecodeError as e:
                errors.append({"path": where, "message": f"not UTF-8 (saved in another encoding?): {e}"})
                continue
            except json.JSONDecodeError as e:
                errors.append({"path": where, "message": f"not JSON: {e}"})
                continue
            except OSError as e:
                errors.append({"path": where, "message": f"cannot be read: {e}"})
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
        try:
            text = fsio.read_text(f)
        except (OSError, ValueError) as e:
            raise Invalid(f"seed {d}: {f.relative_to(d).as_posix()} cannot be read as UTF-8: {e}") from None
        listing.append(f"{f.relative_to(d).as_posix()} {fsio.sha256_hex(text)}")
    try:
        uri = paths.to_uri(d)
    except Invalid:
        uri = d.resolve().as_posix()
    return {"seed": {"uri": uri, "sha256": fsio.sha256_hex("\n".join(listing))}}


def _close(con: sqlite3.Connection, conflict_id: str, why: str, by: str) -> None:
    con.execute(
        "UPDATE conflict SET state = 'dismissed', resolution = ?, resolved_by = ? WHERE id = ?", (why, by, conflict_id)
    )


def _restore_mark(con: sqlite3.Connection) -> dict[str, Any]:
    """The mark a restore leaves (``backup.SEED_RESTORE_KEY``): ``{"epoch", "from", "at", "layers": [layer ids]}``
    for the seeded layers whose next seed import must take nothing silently; ``{}`` when there is none."""
    from .backup import SEED_RESTORE_KEY

    row = con.execute("SELECT value FROM meta WHERE key = ?", (SEED_RESTORE_KEY,)).fetchone()
    if not row:
        return {}
    try:
        mark = json.loads(row[0])
    except ValueError:
        return {}
    return mark if isinstance(mark, dict) else {}


def _clear_restore_mark(con: sqlite3.Connection, layer_ids: list[int] | None) -> None:
    """Drop ``layer_ids`` from the restore mark (every layer when ``None``); the mark goes once it names none."""
    from .backup import SEED_RESTORE_KEY

    mark = _restore_mark(con)
    if not mark:
        return
    left = [] if layer_ids is None else [i for i in mark.get("layers", []) if i not in set(layer_ids)]
    if left:
        mark["layers"] = left
        con.execute("UPDATE meta SET value = ? WHERE key = ?", (json.dumps(mark, sort_keys=True), SEED_RESTORE_KEY))
    else:
        con.execute("DELETE FROM meta WHERE key = ?", (SEED_RESTORE_KEY,))


SEED_ROOTS_KEY = "seed_roots"


def root_key(d: Path) -> str:
    """How a layer's seed folder is recorded: its real path, case-folded where the file system ignores case."""
    import os

    return os.path.normcase(os.path.realpath(d))


def _seed_roots(con: sqlite3.Connection) -> dict[str, str]:
    """``{layer id: root_key}`` of the folder each seeded layer was last exported to or imported from."""
    row = con.execute("SELECT value FROM meta WHERE key = ?", (SEED_ROOTS_KEY,)).fetchone()
    try:
        got = json.loads(row[0]) if row else {}
    except ValueError:
        got = {}
    return {str(k): str(v) for k, v in got.items()} if isinstance(got, dict) else {}


def _set_seed_roots(con: sqlite3.Connection, roots: dict[int, str]) -> None:
    have = _seed_roots(con)
    have.update({str(k): v for k, v in roots.items()})
    con.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        (SEED_ROOTS_KEY, json.dumps(have, sort_keys=True)),
    )


def seed_roots(store: SqliteStore) -> dict[str, str]:
    """``{layer slug: folder}`` each seeded layer was last exported to or imported from (doctor and serve show it)."""
    con = store._reader()
    slugs = {str(i): s for i, s in con.execute("SELECT id, slug FROM layer").fetchall()}
    return {slugs[k]: v for k, v in _seed_roots(con).items() if k in slugs}


def restore_pending(store: SqliteStore) -> list[str]:
    """The seeded layers a restore marked whose seed import has not run yet (see ``region.model.backup``)."""
    con = store._reader()
    mark = _restore_mark(con)
    slugs = dict(con.execute("SELECT id, slug FROM layer").fetchall())
    return [slugs[i] for i in mark.get("layers", []) if i in slugs]


def _file_hash(obj: dict[str, Any]) -> str:
    """The seed hash of a seed file's object as written (no upgrade, no snapping)."""
    return seed_hash({k: obj[k] for k in SEED_KEYS if k in obj})


def _upgraded_hash(store: SqliteStore, own: Rev) -> str | None:
    """The seed hash of a stored revision taken to its kind's current version (``None`` when it is current or
    cannot be upgraded), so a kind version bump alone never makes a record differ from its seed."""
    kind = store.kinds.get(own.kind)
    if kind is None or own.kv == kind.version:
        return None
    try:
        c = content(kind, own.id, {"data": own.data, "geom": own.geom, "kv": own.kv})
    except Invalid:
        return None
    obj: dict[str, Any] = {"id": c.id, "kind": c.kind, "kv": c.kv, "geom": c.geom, "data": c.data}
    if own.deleted:
        obj["deleted"] = True
    if own.base_hash:
        obj["base"] = own.base_hash
    return seed_hash(obj)


class _Probe(Exception):
    """Raised inside a probe of a layer import to roll it back; ``writes`` is how many records it would write."""

    def __init__(self, writes: int) -> None:
        super().__init__(writes)
        self.writes = writes


def _import_layer(store: SqliteStore, slug: str, d: Path, *, by: str, probe: bool = False) -> dict[str, Any]:
    from .changesets import InternalOp, Txn
    from .merge import SEED_RUNS, rebase, upsert_conflict

    objs, meta = _read_layer(d)
    source = _source(d)
    here = root_key(d)

    def fn(con: sqlite3.Connection) -> dict[str, Any]:
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
        layers = L.load(con)
        existed = slug in layers.by_slug
        if not existed:
            parent = meta.get("parent") or "main"
            if parent not in layers.by_slug:
                out.update(skipped=f"its parent layer {parent} is not in this database", missing=True)
                return out
            try:
                # nothing is written before the layer row, so a refusal here leaves the transaction empty
                L.create(
                    con,
                    slug,
                    tier="proposal" if slug != "main" else None,
                    parent=parent,
                    title=meta.get("title"),
                    note=meta.get("note"),
                    by=by,
                )
            except (Invalid, NotFound) as e:
                out.update(skipped=f"the layer cannot be made here: {e.detail}", missing=True)
                return out
            layers = L.load(con)
        lay = layers.get(slug)
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
        roots = _seed_roots(con)
        before_root = roots.get(str(lay.id))
        foreign = existed and before_root is not None and before_root != here
        if foreign:
            out["foreign_root"] = before_root
        if lay.id in _restore_mark(con).get("layers", []):
            out["restored"] = True
        # a restored database, or a seed folder this layer was not last exported to or imported from (another
        # checkout sharing var): its seed_base says nothing about this folder, so nothing is taken or added
        # silently; every difference is a listed seed conflict
        restored = foreign or bool(out.get("restored"))
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
            # the seed as written, before any upgrade: what seed_base holds when the file is unchanged since the
            # last export, though its kind's version moved on since (data-8)
            seed_unchanged = hb is not None and (hs == hb or _file_hash(obj) == hb)
            row = con.execute(
                f"SELECT {SELECT} FROM rec r WHERE r.layer = ? AND r.id = ?", (lay.id, obj["id"])
            ).fetchone()
            own = rev_of(row) if row else None
            ho = seed_hash(seed_obj(own)) if own is not None else None
            if own is not None:
                waiting = open_seed.get(obj["id"])
                if ho == hs or _upgraded_hash(store, own) == hs:
                    out["same"] += 1
                    if waiting is not None:
                        _close(con, waiting, "the seed and the database agree", by)
                    continue
                if ho != hb or restored:
                    if seed_unchanged and waiting is None:
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
            waiting = open_seed.get(obj["id"])
            if (restored or waiting is not None or hb == hs) and (live or not tomb):
                if not restored and waiting is None:
                    # absent here though the seed was seen here as it is: Ben chose to keep it out (a restore's
                    # conflict resolved as ours)
                    out["kept"] += 1
                    continue
                # a restored database lacks a record region/seed has (made after the backup): listed, not added
                conflict = upsert_conflict(
                    con,
                    lay,
                    obj["id"],
                    kind.name,
                    "both_changed",
                    ours_hash=None,
                    theirs_hash=c.hash,
                    base_hash=None,
                    proposed={"data": c.data, "geom": c.geom, **({"deleted": True} if tomb else {})},
                    fields=[],
                    import_run=run_id,
                )
                out["conflicts"].append(conflict)
                continue
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
        if probe:
            raise _Probe(len(ops))
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
                dangling="list",
            )
            res = txn.run(ops)
            out["changeset"] = res.changeset
            out["seq"] = res.seq
            changed = {p.id for p in txn.written()}
            # a ref that dangles here (an import below dropped its target, which the import allows and lists): the
            # revision is written as the seed has it and the ref is listed, so one record never blocks the layer
            for d_ref in txn.dangling:
                p = txn.pending[d_ref["id"]]
                conflict = upsert_conflict(
                    con,
                    lay,
                    d_ref["id"],
                    d_ref["kind"],
                    "dangling_ref",
                    ours_hash=p.content.hash,
                    theirs_hash=p.base,
                    base_hash=p.base,
                    proposed=None,
                    fields=[d_ref["role"]],
                    import_run=None,
                )
                out.setdefault("dangling", []).append(conflict)
        con.executemany(
            "INSERT INTO seed_base (layer, id, hash) VALUES (?, ?, ?) "
            "ON CONFLICT (layer, id) DO UPDATE SET hash = excluded.hash",
            [(lay.id, i, h) for i, h in bases],
        )
        present = {o["id"] for o in objs}
        out["removed_in_seed"] = sorted(i for i in base_of if i not in present)
        if out.get("restored"):
            _clear_restore_mark(con, [lay.id])
        _set_seed_roots(con, {lay.id: here})
        if changed and layers.above(lay):
            reb = rebase(store, con, lower=slug, changed=changed, import_run=run_id, by="rebase")
            out["rebase"] = reb["changesets"]
        below = chain[1].slug if len(chain) > 1 else None
        if changed and below is not None:
            # a copy-up whose base is older than what this database holds below (a cloud session built from an
            # older seed): rebased now, so it merges or becomes a listed conflict instead of blocking a promote
            own = rebase(store, con, lower=below, changed=changed, only=slug, by="rebase")
            if own["changesets"] or own["conflicts"]:
                out["rebased"] = {"changesets": own["changesets"], "conflicts": own["conflicts"]}
        counts = {k: out[k] for k in ("taken", "kept", "added", "same")}
        counts["conflicts"] = len(out["conflicts"])
        con.execute(
            "UPDATE import_run SET state = ?, counts = ?, changeset = ?, finished = ? WHERE id = ?",
            ("applied" if ops else "unchanged", json.dumps(counts), out["changeset"], now(), run_id),
        )
        return out

    if probe:
        try:
            store._writer.run(fn)
        except _Probe as p:
            return {"writes": p.writes}
        return {"writes": 0}
    out = store._writer.run(fn)
    if out.get("changeset"):
        store.checkpoint()
    store._notify(out.get("seq"))
    return out


def import_seed(
    store: SqliteStore, seed: Path = SEED, *, layer: str | None = None, by: str = "seed", keep_going: bool = False
) -> dict:
    """Merge seed files into the database (see the module doc).

    ``seed`` is a seed root (holding ``main/`` and ``proposals/``), or, with ``layer``, one layer's folder. Returns
    ``{"layers": {slug: {taken, kept, added, same, conflicts, removed_in_seed, changeset, run, skipped?,
    missing?}}, "skipped": [{"layer", "path", "reason"}]}``. The top-level ``skipped`` lists the proposals that are
    not in the database because their parent is not (or cannot hold them); those also carry ``missing: true``. A
    layer that exists but is not open (promoted, frozen) says so in its own ``skipped`` only. With ``keep_going``
    (serve at start), a layer whose files cannot be read or validated is reported as ``{"error": detail}`` and the
    others still import; without it the first such layer raises (export, which must not overwrite a file it could
    not read).
    """
    seed = Path(seed)
    dirs: list[tuple[str, Path]] = []
    if layer is not None:
        dirs.append((layer, seed))
    else:
        if (seed / "main").is_dir():
            dirs.append(("main", seed / "main"))
        if (seed / "proposals").is_dir():
            found = sorted(p for p in (seed / "proposals").iterdir() if p.is_dir() and not p.name.startswith("."))
            dirs.extend(_parents_first([(f"proposal:{d.name}", d) for d in found]))
    report: dict[str, Any] = {"layers": {}, "skipped": []}
    backed_up = not getattr(store, "auto_backups", False)
    for slug, d in dirs:
        try:
            if not backed_up and _import_layer(store, slug, d, by=by, probe=True)["writes"]:
                # section 9: a seed import that takes or adds records is backed up first (once per import)
                report["backup"] = str(store.pre_import_backup())
                backed_up = True
            st = _import_layer(store, slug, d, by=by)
        except (Invalid, Conflict, NotFound) as e:
            if not keep_going:
                raise
            report["layers"][slug] = {"error": e.detail, "path": d.as_posix()}
            continue
        report["layers"][slug] = st
        if st.get("missing"):  # not in the database after all: listed apart from a layer that is merely not open
            report["skipped"].append({"layer": slug, "path": d.as_posix(), "reason": st["skipped"]})
    return report


def _declared_parent(d: Path) -> str:
    """The parent a proposal folder's ``_layer.json`` names (``main`` when it names none or cannot be read: the
    import itself reports a broken file)."""
    f = d / LAYER_FILE
    try:
        meta = fsio.read_json(f) if f.is_file() else {}
    except (OSError, ValueError, Invalid):
        return "main"
    parent = meta.get("parent") if isinstance(meta, dict) else None
    return parent if isinstance(parent, str) and parent else "main"


def _parents_first(dirs: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    """Proposal folders ordered so a parent that is itself a proposal of this seed comes before its children (by
    name otherwise). A cycle keeps its members in name order; their missing parents then skip them."""
    parent = {slug: _declared_parent(d) for slug, d in dirs}
    left = list(dirs)
    out: list[tuple[str, Path]] = []
    while left:
        waiting = {slug for slug, _ in left}
        ready = [(slug, d) for slug, d in left if parent[slug] not in waiting]
        if not ready:  # a cycle
            out.extend(left)
            break
        out.extend(ready)
        left = [x for x in left if x not in ready]
    return out


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
    by_slug: dict[str, int] = {}
    for c in pending:
        by_slug[c["layer"]] = by_slug.get(c["layer"], 0) + 1
    ids_of = {r[1]: r[0] for r in store._reader().execute("SELECT id, slug FROM layer").fetchall()}
    # a layer with an open seed conflict is not written (its folder holds a change it has not merged); the others are
    blocked = {ids_of[slug]: n for slug, n in by_slug.items() if slug in ids_of}

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
    report: dict[str, Any] = {"imported": imported, "layers": {}, "out": str(out)}
    bases: list[tuple[int, str, str]] = []
    written_roots: dict[int, str] = {}
    for lay, revs, layers in snapshot:
        stats: dict[str, Any] = {"records": 0, "written": 0, "unchanged": 0, "removed": 0, "skipped_kinds": []}
        report["layers"][lay.slug] = stats
        try:
            d = layer_dir(out, lay.slug)
        except paths.UnsafePath as e:  # a layer name a folder cannot hold never blocks the other layers
            stats["skipped"] = f"its name cannot be a folder ({e.detail}); rename the layer to export it"
            continue
        if lay.id in blocked:
            stats["skipped"] = f"{blocked[lay.id]} seed conflict(s) open on this layer: resolve them first"
            continue
        # what the folder will hold: {path: text}
        plan: dict[Path, str] = {}
        if lay.tier == "proposal":
            meta = {
                "slug": lay.slug,
                "parent": layers.slugs.get(lay.parent) if lay.parent else "main",
                "title": lay.title,
                "note": lay.note,
            }
            plan[d / LAYER_FILE] = seed_text(meta)
        skipped: set[str] = set()
        layer_bases: list[tuple[int, str, str]] = []
        for rev in revs:
            kind = store.kinds.get(rev.kind)
            if kind is None or not kind.seeded:
                if kind is None:
                    skipped.add(rev.kind)
                continue
            text = seed_text(seed_obj(rev))
            plan[d / rev.kind / f"{rev.id}.json"] = text
            layer_bases.append((lay.id, rev.id, fsio.sha256_hex(text)))
        stale = _record_files(d) - set(plan)
        if lay.state != "open" and d.is_dir() and (stale or any(not _same_bytes(f, t) for f, t in plan.items())):
            # a promoted or frozen layer takes no seed import, so a change in its folder (a cloud session's work
            # after the promote) was never merged: leave the folder as it is rather than overwrite it
            stats["skipped"] = f"layer {lay.slug} is {lay.state} and its folder holds changes it never took in"
            continue
        written_roots[lay.id] = root_key(d)
        stats["records"] = len(layer_bases)
        bases.extend(layer_bases)
        for f, text in plan.items():
            if _same_bytes(f, text):
                if f.name != LAYER_FILE:
                    stats["unchanged"] += 1
                continue
            fsio.write_atomic(f, text)
            if f.name != LAYER_FILE:
                stats["written"] += 1
        for f in sorted(stale):
            fsio.remove(f)
            stats["removed"] += 1
        stats["skipped_kinds"] = sorted(skipped)

    def record(con: sqlite3.Connection) -> None:
        con.executemany(
            "INSERT INTO seed_base (layer, id, hash) VALUES (?, ?, ?) "
            "ON CONFLICT (layer, id) DO UPDATE SET hash = excluded.hash",
            bases,
        )
        _set_seed_roots(con, written_roots)
        con.execute(
            "INSERT INTO meta (key, value) VALUES ('last_export', ?) "
            "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (now(),),
        )

    store._writer.run(record)
    if pending:
        done = [slug for slug, st in report["layers"].items() if not st.get("skipped")]
        raise Conflict(
            f"export refused for {', '.join(sorted(by_slug))}: {len(pending)} seed change(s) are not merged; resolve "
            "them first (crhub conflicts list, then crhub conflicts resolve)"
            + (f". The other layers were written: {', '.join(done)}" if done else ""),
            reason="seed",
            conflicts=[
                {"kind": c["kind"], "id": c["rec_id"], "layer": c["layer"], "conflict": c["id"]} for c in pending
            ],
            report=report,
        )
    return report


def _record_files(d: Path) -> set[Path]:
    """The record files under a layer folder (``<kind>/<ulid>.json``)."""
    if not d.is_dir():
        return set()
    return {
        f
        for kdir in d.iterdir()
        if kdir.is_dir() and not kdir.name.startswith(("_", "."))
        for f in kdir.glob("*.json")
        if ids.is_ulid(f.stem)
    }


def _same_bytes(f: Path, text: str) -> bool:
    return f.is_file() and f.read_bytes() == text.encode("utf-8")


__all__ = [
    "LAYER_FILE",
    "SEED",
    "export",
    "import_seed",
    "layer_dir",
    "open_seed_conflicts",
    "restore_pending",
    "root_key",
    "seed_hash",
    "seed_roots",
    "seed_obj",
    "seed_text",
]
