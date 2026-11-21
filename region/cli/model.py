"""``crhub model``: the record store's maintenance commands (WP1).

    crhub model migrate  [--db PATH] [--no-backup]     apply pending migrations (backing up first)
    crhub model export   [--db PATH] [--out region/seed]   import pulled seeds, then write main and proposals
    crhub model import   [--db PATH] [--seed region/seed]  merge seed files into the database
    crhub model backup   [--db PATH] [--reason manual]
    crhub model restore  FILE [--db PATH]               backs the current database up first
    crhub model check    [--db PATH]                    quick_check, then every record validated again
    crhub model info     [--db PATH] [--json]           schema version, layers, record counts
    crhub model kinds    [--json]                       the kind files and whether each is valid
    crhub model schema   [--write]                      print (or rewrite) region/model/schema.sql

``--db`` defaults to ``var/region.db`` (see ``crhub info`` for where ``var`` is). These commands open the database
directly; while a server holds the lock, run writes through the server instead (9.28).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

SCHEMA_FILE = Path(__file__).resolve().parents[1] / "model" / "schema.sql"


def _db_default() -> Path:
    from region.core import paths

    return paths.var_path("region.db")


def _add_db(p: argparse.ArgumentParser) -> None:
    p.add_argument("--db", type=Path, default=None, help="the database (default var/region.db)")


def add_arguments(p: argparse.ArgumentParser) -> None:
    """The ``model`` actions (shared by ``crhub model`` and ``python -m region.model``)."""
    sub = p.add_subparsers(dest="action", metavar="<action>")
    m = sub.add_parser("migrate", help="apply pending migrations, backing the database up first")
    _add_db(m)
    m.add_argument("--no-backup", action="store_true", help="do not back up before migrating")
    e = sub.add_parser("export", help="import pulled seeds, then write the main and proposal layers to the seed")
    _add_db(e)
    e.add_argument("--out", type=Path, default=None, help="the seed root (default region/seed)")
    i = sub.add_parser("import", help="merge seed files into the database (three-way, never overwriting Ben)")
    _add_db(i)
    i.add_argument("--seed", type=Path, default=None, help="the seed root (default region/seed)")
    i.add_argument("--layer", default=None, help="import one layer's folder into this layer")
    b = sub.add_parser("backup", help="an online, checked backup into var/backups")
    _add_db(b)
    b.add_argument("--reason", default="manual")
    r = sub.add_parser("restore", help="replace the database with a backup (the current one is backed up first)")
    r.add_argument("file", type=Path)
    _add_db(r)
    c = sub.add_parser("check", help="quick_check, then validate every record again")
    _add_db(c)
    n = sub.add_parser("info", help="schema version, layers and record counts")
    _add_db(n)
    n.add_argument("--json", action="store_true")
    k = sub.add_parser("kinds", help="the kind files and whether each is valid")
    k.add_argument("--json", action="store_true")
    s = sub.add_parser("schema", help="print the schema after every migration, or rewrite region/model/schema.sql")
    s.add_argument("--write", action="store_true")


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("model", help="the record store: migrate, seeds, backup, restore, check")
    add_arguments(p)
    p.set_defaults(func=run)


def _open(args: argparse.Namespace, **kw: Any) -> Any:
    from region.model import open_store

    return open_store(args.db or _db_default(), **kw)


def schema_text() -> str:
    """The schema of a new database after every migration (what ``schema.sql`` holds)."""
    from region.model.db import dump_schema
    from region.model.migrate import migrate

    con = sqlite3.connect(":memory:", isolation_level=None)
    try:
        migrate(con)
        return dump_schema(con)
    finally:
        con.close()


def run(args: argparse.Namespace) -> int:
    action = getattr(args, "action", None)
    if action is None:
        print(
            "crhub model: name an action (migrate, export, import, backup, restore, check, info, kinds, schema)",
            file=sys.stderr,
        )
        return 2
    return int(globals()[f"_{action}"](args) or 0)


def _migrate(args: argparse.Namespace) -> int:
    from region.core import fsio
    from region.model.db import connect
    from region.model.migrate import current_version, migrate

    db = Path(args.db or _db_default())
    fsio.check_write(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = connect(db)
    try:
        done = migrate(con, backup_dir=None if args.no_backup else db.parent / "backups")
        print(f"schema at version {current_version(con)}" + (f" (applied {done})" if done else " (up to date)"))
    finally:
        con.close()
    return 0


def _export(args: argparse.Namespace) -> int:
    from region.model import seed

    out = args.out or seed.SEED
    with _open(args) as store:
        rep = seed.export(store, out)
    for slug, st in rep["layers"].items():
        print(f"{slug:24} {st['records']:6} records, {st['written']} written, {st['removed']} removed")
    return 0


def _import(args: argparse.Namespace) -> int:
    from region.model import seed

    with _open(args) as store:
        rep = seed.import_seed(store, args.seed or seed.SEED, layer=args.layer)
    for slug, st in rep["layers"].items():
        print(
            f"{slug:24} taken {st['taken']}, added {st['added']}, kept {st['kept']}, same {st['same']}, "
            f"conflicts {len(st['conflicts'])}, removed in seed {len(st['removed_in_seed'])}"
        )
    return 1 if any(st["conflicts"] for st in rep["layers"].values()) else 0


def _backup(args: argparse.Namespace) -> int:
    from region.model.backup import backup

    db = Path(args.db or _db_default())
    print(backup(db, db.parent / "backups", args.reason))
    return 0


def _restore(args: argparse.Namespace) -> int:
    from region.model.backup import restore

    db = Path(args.db or _db_default())
    restore(args.file, db)
    print(f"restored {db} from {args.file}")
    return 0


def _check(args: argparse.Namespace) -> int:
    with _open(args, create=False) as store:
        problems = store.quick_check()
        for p in problems:
            print("quick_check:", p)
        data = store.check_data()
        for p in data:
            print(f"{p['layer']} {p['kind']} {p['id']}: {p.get('path', '')}: {p['message']}")
    print(f"{len(problems)} database problem(s), {len(data)} record problem(s)")
    return 1 if problems or data else 0


def _info(args: argparse.Namespace) -> int:
    from region.model.migrate import current_version

    with _open(args, create=False) as store:
        con = store._reader()
        counts = {
            f"{slug}/{kind}": n
            for slug, kind, n in con.execute(
                "SELECT l.slug, r.kind, count(*) FROM rec r JOIN layer l ON l.id = r.layer WHERE r.deleted = 0 "
                "GROUP BY l.slug, r.kind ORDER BY l.slug, r.kind"
            ).fetchall()
        }
        info = {
            "db": str(store.path),
            "schema_version": current_version(con),
            "meta": store.meta(),
            "layers": store.layers(),
            "records": counts,
            "last_seq": store.last_seq(),
            "kinds": store.kinds.names(),
        }
    if args.json:
        print(json.dumps(info, indent=1, ensure_ascii=False))
        return 0
    print(f"db        {info['db']}")
    print(f"schema    {info['schema_version']}")
    print(f"seq       {info['last_seq']}")
    print("layers    " + ", ".join(f"{la['slug']} ({la['tier']}, {la['state']})" for la in info["layers"]))
    for key, n in counts.items():
        print(f"  {key:40} {n}")
    return 0


def _kinds(args: argparse.Namespace) -> int:
    from region.core import features

    rows = []
    for f in features.kind_files():
        problems = features.check_kind_file(f)
        rows.append({"file": str(f), "problems": problems})
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        for r in rows:
            print(("ok      " if not r["problems"] else "INVALID ") + r["file"])
            for p in r["problems"]:
                print("        " + p)
    return 1 if any(r["problems"] for r in rows) else 0


def _schema(args: argparse.Namespace) -> int:
    text = schema_text()
    if args.write:
        from region.core import fsio

        with fsio.allow_writes(SCHEMA_FILE):
            fsio.write_text(SCHEMA_FILE, text)
        print(f"wrote {SCHEMA_FILE}")
    else:
        sys.stdout.write(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    """``python -m region.model <action>``: the same actions as ``crhub model``."""
    p = argparse.ArgumentParser(prog="python -m region.model", description="The record store's maintenance commands.")
    add_arguments(p)
    args = p.parse_args(argv)
    from region.core.errors import HubError

    try:
        return run(args)
    except HubError as e:
        print(f"region.model {getattr(args, 'action', '')}: {e}", file=sys.stderr)
        return e.exit_code


__all__ = ["SCHEMA_FILE", "add_arguments", "main", "register", "run", "schema_text"]
