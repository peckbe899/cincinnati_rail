"""``crhub model``: the record store's maintenance commands (WP1).

    crhub model migrate  [--db PATH] [--no-backup]     apply pending migrations (backing up first)
    crhub model export   [--db PATH] [--out region/seed]   import pulled seeds, then write main and proposals
    crhub model import   [--db PATH] [--seed region/seed]  merge seed files into the database
    crhub model backup   [--db PATH] [--reason manual]
    crhub model restore  FILE [--db PATH] [--force]     backs the current database up first; refuses while a hub serves,
                                                        a file that is not a hub database, and (without --force) a
                                                        backup of another database
    crhub model check    [--db PATH]                    quick_check, then every record validated again (read-only)
    crhub model info     [--db PATH] [--json]           schema version, layers, record counts (read-only)
    crhub model kinds    [--json]                       the kind files and whether each is valid
    crhub model schema   [--write]                      print (or rewrite) region/model/schema.sql

``crhub export``, ``crhub backup`` and ``crhub restore`` are the same three actions under the runbook's names
(section 9). ``--db`` defaults to ``var/region.db`` (see ``crhub info`` for where ``var`` is).

**Beside a serving hub** (9.28: while ``crhub serve`` holds ``var/hub.lock``, its database is written only through
it). Without ``--db``, ``export`` and ``backup`` go through the running hub's HTTP API (``POST /export``,
``POST /backup``), and ``import`` and ``migrate`` refuse with a message saying what to do instead (the hub imported
the pulled seeds when it started, and every export imports them again first). ``export`` refuses a hub that serves
from another checkout (two checkouts share one ``var`` on Windows): it would write that checkout's ``region/seed``.
The commands that write the database
directly (``migrate``, ``export``, ``import``, ``restore``) hold the lock while they work, so they refuse while a hub
or another command holds it (``LockHeld`` names it), and no hub can start on the database meanwhile. ``check`` and
``info`` open the database read-only (``open_store(readonly=True)``): they never migrate, back up or rewrite the
kind table, so they are safe beside a serving hub.
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


HELP = {
    "export": "import pulled seeds, then write the main and proposal layers to the seed",
    "backup": "an online, checked backup into var/backups",
    "restore": "replace the database with a backup (the current one is backed up first)",
}


def export_arguments(p: argparse.ArgumentParser) -> None:
    """The arguments of ``export`` (shared with ``crhub export``)."""
    _add_db(p)
    p.add_argument("--out", type=Path, default=None, help="the seed root (default region/seed)")


def backup_arguments(p: argparse.ArgumentParser) -> None:
    """The arguments of ``backup`` (shared with ``crhub backup``)."""
    _add_db(p)
    p.add_argument("--reason", default="manual")


def restore_arguments(p: argparse.ArgumentParser) -> None:
    """The arguments of ``restore`` (shared with ``crhub restore``)."""
    p.add_argument("file", type=Path)
    _add_db(p)
    p.add_argument("--force", action="store_true", help="restore a backup of another database (another db_id)")


def run_action(action: str, args: argparse.Namespace) -> int:
    """Run one ``model`` action on ``args`` (the top-level aliases ``crhub export``, ``backup`` and ``restore``)."""
    args.action = action
    return run(args)


def add_arguments(p: argparse.ArgumentParser) -> None:
    """The ``model`` actions (shared by ``crhub model`` and ``python -m region.model``)."""
    sub = p.add_subparsers(dest="action", metavar="<action>")
    m = sub.add_parser("migrate", help="apply pending migrations, backing the database up first")
    _add_db(m)
    m.add_argument("--no-backup", action="store_true", help="do not back up before migrating")
    export_arguments(sub.add_parser("export", help=HELP["export"]))
    i = sub.add_parser("import", help="merge seed files into the database (three-way, never overwriting Ben)")
    _add_db(i)
    i.add_argument("--seed", type=Path, default=None, help="the seed root (default region/seed)")
    i.add_argument("--layer", default=None, help="import one layer's folder into this layer")
    backup_arguments(sub.add_parser("backup", help=HELP["backup"]))
    restore_arguments(sub.add_parser("restore", help=HELP["restore"]))
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


class Refused(Exception):
    """An action that cannot run beside the hub serving from ``var``; the message says what to do instead."""


def _running_hub(args: argparse.Namespace) -> Any:
    """The client of the hub serving from ``var`` when no ``--db`` was given, else ``None``."""
    if args.db is not None:
        return None
    from region.api.client import running_hub

    return running_hub(client="crhub-cli", timeout=600.0)


def _holding_the_lock(action: str) -> Any:
    """``var``'s single-instance lock, held while an action writes the database directly (``LockHeld`` names the
    hub or command holding it)."""
    from region.core import lock, paths

    return lock.acquire(paths.var_root(), 0, command=f"crhub model {action}")


def _through(hub: Any) -> str:
    return f"(through the hub serving at {hub.base})"


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
    try:
        return int(globals()[f"_{action}"](args) or 0)
    except Refused as e:
        name = action if action in HELP else f"model {action}"  # export and backup also have runbook names
        print(f"crhub {name}: {e}", file=sys.stderr)
        return 1


def _migrate(args: argparse.Namespace) -> int:
    from region.core import fsio
    from region.model.db import connect
    from region.model.migrate import current_version, migrate

    db = Path(args.db or _db_default())
    fsio.check_write(db)
    hub = _running_hub(args)
    if hub is not None:
        raise Refused(f"a hub is serving at {hub.base}; it migrated the database when it started. Stop it to migrate.")
    with _holding_the_lock("migrate"):
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
    hub = _running_hub(args)
    if hub is not None:
        _same_checkout(hub, "export", "its export writes that checkout's region/seed")
        if Path(out).resolve() != Path(seed.SEED).resolve():
            raise Refused(
                f"a hub is serving at {hub.base}, and it exports to {seed.SEED} only. Drop --out, or stop the hub to "
                "export elsewhere."
            )
        rep = hub.json("POST", "/export")
        print(f"export {_through(hub)}")
    else:
        with _holding_the_lock("export"), _open(args, create=False) as store:
            rep = seed.export(store, out)
    print(f"{'into':24} {rep.get('out') or out}")
    for skip in rep["imported"].get("skipped", []):
        print(f"{skip['layer']:24} not imported: {skip['reason']} ({skip['path']} left as it is)")
    for slug, st in (rep["imported"].get("layers") or {}).items():
        if st.get("skipped") and not st.get("missing"):
            print(f"{slug:24} not imported: {st['skipped']}")
    for slug, st in rep["layers"].items():
        line = f"{slug:24} {st['records']:6} records, {st['written']} written, {st['removed']} removed"
        if st.get("skipped"):
            line += f" (folder left as it is: {st['skipped']})"
        print(line)
    return 0


def _same_checkout(hub: Any, action: str, what: str = "") -> None:
    """Refuse to work through a hub that serves from another checkout (two checkouts can share one var on
    Windows): its region/seed is not the one this checkout commits."""
    from region.core import lock

    holder = getattr(hub, "holder", None)
    if holder is None or not holder.repo:
        return
    import os

    if os.path.normcase(holder.repo) != os.path.normcase(lock.this_repo()):
        raise Refused(
            f"the hub serving at {hub.base} runs from another checkout, {holder.repo}"
            + (f"; {what}" if what else "")
            + f", not this one ({lock.this_repo()}). Run crhub {action} in that checkout, or stop that hub and run "
            "this again here."
        )


def _import(args: argparse.Namespace) -> int:
    from region.model import seed

    hub = _running_hub(args)
    if hub is not None:
        raise Refused(
            f"a hub is serving at {hub.base}. It imported the pulled seeds when it started, and crhub export imports "
            "them again before it writes; run crhub export, or stop the hub and run this again."
        )
    with _holding_the_lock("import"), _open(args, create=False) as store:
        rep = seed.import_seed(store, args.seed or seed.SEED, layer=args.layer)
    for slug, st in rep["layers"].items():
        if st.get("skipped"):
            print(f"{slug:24} skipped: {st['skipped']}")
            continue
        print(
            f"{slug:24} taken {st['taken']}, added {st['added']}, kept {st['kept']}, same {st['same']}, "
            f"conflicts {len(st['conflicts'])}, removed in seed {len(st['removed_in_seed'])}"
        )
    return 1 if any(st["conflicts"] for st in rep["layers"].values()) else 0


def _backup(args: argparse.Namespace) -> int:
    from region.model.backup import backup

    hub = _running_hub(args)
    if hub is not None:
        if args.reason != "manual":
            raise Refused(f"a hub is serving at {hub.base}; its backups are manual ones. Drop --reason.")
        made = hub.json("POST", "/backup")
        print(made["path"])
        print(f"backup {_through(hub)}", file=sys.stderr)
        return 0
    db = Path(args.db or _db_default())
    print(backup(db, db.parent / "backups", args.reason))
    return 0


def _restore(args: argparse.Namespace) -> int:
    """Holds ``var``'s single-instance lock while it works, so it refuses while a hub serves (``LockHeld``) and no
    hub can start on the database it is replacing."""
    from region.core import lock, paths
    from region.model.backup import restore

    db = Path(args.db or _db_default())
    with lock.acquire(paths.var_root(), 0, command="crhub restore"):
        rep = restore(args.file, db, force=bool(getattr(args, "force", False)))
    replaced, restored = rep["replaced"], rep["restored"]
    if replaced is not None:
        print(
            f"replaced  {db}: {replaced['records']} live records, last export {replaced['last_export'] or 'never'}"
            f" (kept as {rep['pre_restore']})"
        )
    print(
        f"restored  {args.file}: {restored['records']} live records, last export {restored['last_export'] or 'never'}"
    )
    if rep["seed_layers"]:
        print(
            "seeds     region/seed may hold exports newer than this backup. The next crhub serve (or export) takes "
            "nothing from it silently: every record that differs is listed as a seed conflict. Keep the restored "
            "state with crhub conflicts resolve --all --take ours, or take region/seed's with --take theirs."
        )
    return 0


def _pending_note(store: Any, todo: list[int]) -> str:
    return (
        f"{store.path} has {len(todo)} migration(s) pending ({', '.join(map(str, todo))}); crhub model migrate or "
        "crhub serve applies them after a backup"
    )


def _check(args: argparse.Namespace) -> int:
    with _open(args, readonly=True) as store:
        problems = store.quick_check()
        for p in problems:
            print("quick_check:", p)
        todo = [] if problems else store.pending_migrations()
        if problems or todo:
            if todo:
                print(_pending_note(store, todo) + "; the records are not checked until then")
            print(f"{len(problems)} database problem(s), records not checked")
            return 1
        data = store.check_data()
        for p in data:
            print(f"{p['layer']} {p['kind']} {p['id']}: {p.get('path', '')}: {p['message']}")
    print(f"{len(problems)} database problem(s), {len(data)} record problem(s)")
    return 1 if problems or data else 0


def _info(args: argparse.Namespace) -> int:
    """The database's facts; for a file older than this code, its schema version and pending migrations only (the
    rest needs tables a migration adds, and info never migrates)."""
    from region.model.migrate import current_version

    with _open(args, readonly=True) as store:
        con = store._reader()
        todo = store.pending_migrations()
        info: dict[str, Any] = {"db": str(store.path), "schema_version": current_version(con), "pending": todo}
        if not todo:
            info["records"] = {
                f"{slug}/{kind}": n
                for slug, kind, n in con.execute(
                    "SELECT l.slug, r.kind, count(*) FROM rec r JOIN layer l ON l.id = r.layer WHERE r.deleted = 0 "
                    "GROUP BY l.slug, r.kind ORDER BY l.slug, r.kind"
                ).fetchall()
            }
            info.update(meta=store.meta(), layers=store.layers(), last_seq=store.last_seq(), kinds=store.kinds.names())
        note = _pending_note(store, todo) if todo else None
    if args.json:
        print(json.dumps(info, indent=1, ensure_ascii=False))
        return 0
    print(f"db        {info['db']}")
    print(f"schema    {info['schema_version']}")
    if note:
        print(f"pending   {note}")
        return 0
    print(f"seq       {info['last_seq']}")
    print("layers    " + ", ".join(f"{la['slug']} ({la['tier']}, {la['state']})" for la in info["layers"]))
    for key, n in info["records"].items():
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


__all__ = [
    "HELP",
    "SCHEMA_FILE",
    "add_arguments",
    "backup_arguments",
    "export_arguments",
    "main",
    "register",
    "restore_arguments",
    "run",
    "run_action",
    "schema_text",
]
