"""``crhub conflicts``: the review queue from the command line (the review pane is read-only in increment 1).

    crhub conflicts list [--layer SLUG] [--all] [--json] [--db PATH]
    crhub conflicts show ID [--db PATH]
    crhub conflicts resolve ID --take ours|theirs [--db PATH]
    crhub conflicts resolve ID --take merged FILE [--db PATH]
    crhub conflicts resolve --all [--layer SLUG] [--seed] --take ours|theirs [--db PATH]

A conflict keeps Ben's revision on read until he resolves it: ``ours`` keeps his revision (for a seed conflict, the
next export writes it into ``region/seed``), ``theirs`` takes the other side (the seed's revision, or the one below),
and ``merged`` writes the body in FILE (``{"data": ..., "geom": ...}``, as ``crhub conflicts show`` prints under
``proposed``). ``--all`` resolves every open conflict (of one layer with ``--layer``, only the seed ones with
``--seed``) the same way, one by one, and says which it could not.

While a hub serves from ``var``, the commands go through its HTTP API (``GET /conflicts``,
``POST /conflicts/{id}/resolve``; decision 9.28). Otherwise they open the database themselves: ``list`` and ``show``
read-only, ``resolve`` under ``var``'s single-instance lock. Export refuses a layer while one of its seed conflicts is
open, so this is how a blocked export is cleared.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("conflicts", help="list and resolve conflicts (the review queue)")
    sub = p.add_subparsers(dest="conflicts_command", metavar="<action>")
    ls = sub.add_parser("list", help="the open conflicts")
    ls.add_argument("--layer", default=None, help="one layer's conflicts only")
    ls.add_argument("--all", action="store_true", help="resolved and dismissed ones too")
    ls.add_argument("--json", action="store_true")
    ls.add_argument("--db", type=Path, default=None, help="region.db (default var/region.db)")
    show = sub.add_parser("show", help="one conflict, with the revision it proposes")
    show.add_argument("id")
    show.add_argument("--db", type=Path, default=None, help="region.db (default var/region.db)")
    res = sub.add_parser("resolve", help="keep ours, take theirs, or write a merged body")
    res.add_argument("id", nargs="?", default=None, help="the conflict (omit with --all)")
    res.add_argument("file", nargs="?", type=Path, default=None, help="the merged body (with --take merged)")
    res.add_argument("--take", required=True, choices=("ours", "theirs", "merged"))
    res.add_argument("--all", action="store_true", help="every open conflict (see --layer and --seed)")
    res.add_argument("--layer", default=None, help="with --all: one layer's conflicts only")
    res.add_argument("--seed", action="store_true", help="with --all: the seed conflicts only")
    res.add_argument("--by", default=None, help="who resolves (default the config's user, else ben)")
    res.add_argument("--db", type=Path, default=None, help="region.db (default var/region.db)")
    p.set_defaults(func=run)


class _Http:
    def __init__(self, hub: Any) -> None:
        self.hub = hub

    def list(self, state: str, layer: str | None) -> list[dict[str, Any]]:
        return self.hub.json("GET", "/conflicts", query={"state": state, "layer": layer})["items"]

    def resolve(self, cid: str, take: str, body: dict[str, Any] | None) -> dict[str, Any]:
        payload: dict[str, Any] = {"take": take}
        if body is not None:
            payload["body"] = body
        return self.hub.json("POST", f"/conflicts/{cid}/resolve", json_body=payload)


class _Direct:
    def __init__(self, store: Any, by: str) -> None:
        self.store = store
        self.by = by

    def list(self, state: str, layer: str | None) -> list[dict[str, Any]]:
        return self.store.conflicts(state=None if state == "all" else state, layer=layer)

    def resolve(self, cid: str, take: str, body: dict[str, Any] | None) -> dict[str, Any]:
        return self.store.resolve_conflict(cid, take, body, by=self.by)


def _line(c: dict[str, Any]) -> str:
    fields = ", ".join(c.get("fields") or [])
    seed = " (seed)" if c.get("seed") else ""
    return (
        f"{c['id']}  {c['layer']:<20} {c['kind']:<12} {c['rec_id']}  {c['reason']}{seed}"
        + (f"  [{fields}]" if fields else "")
        + (f"  {c['state']}" if c.get("state") != "open" else "")
    )


def _seed_runs(client: Any) -> set[int]:
    """The import runs that are seed imports (their conflicts block export)."""
    store = getattr(client, "store", None)
    if store is None:
        return set()
    return {r[0] for r in store._reader().execute("SELECT id FROM import_run WHERE importer = 'seed'").fetchall()}


def _mark_seed(items: list[dict[str, Any]], runs: set[int], hub: Any) -> None:
    if hub is not None:
        # through the hub: a seed run's report names importer "seed"
        cache: dict[int, bool] = {}
        for c in items:
            run = c.get("import_run")
            if run is None:
                continue
            if run not in cache:
                try:
                    cache[run] = hub.json("GET", f"/imports/{run}").get("importer") == "seed"
                except Exception:
                    cache[run] = False
            c["seed"] = cache[run]
        return
    for c in items:
        c["seed"] = c.get("import_run") in runs


def _work(client: Any, hub: Any, args: argparse.Namespace) -> int:
    action = args.conflicts_command
    if action == "list":
        items = client.list("all" if args.all else "open", args.layer)
        _mark_seed(items, _seed_runs(client), hub)
        if args.json:
            print(json.dumps(items, indent=1, ensure_ascii=False, default=str))
            return 0
        for c in items:
            print(_line(c))
        print(f"{len(items)} conflict(s)" + ("" if args.all else " open"))
        return 0
    if action == "show":
        found = [c for c in client.list("all", None) if c["id"] == args.id]
        if not found:
            print(f"crhub conflicts: no conflict {args.id}", file=sys.stderr)
            return 1
        print(json.dumps(found[0], indent=1, ensure_ascii=False, default=str))
        return 0
    body = None
    if args.take == "merged":
        if args.all or args.file is None:
            print("crhub conflicts resolve: --take merged needs one conflict and its FILE", file=sys.stderr)
            return 2
        from region.core import fsio

        body = fsio.read_json(args.file)
    if args.all:
        items = client.list("open", args.layer)
        _mark_seed(items, _seed_runs(client), hub)
        if args.seed:
            items = [c for c in items if c.get("seed")]
        ids = [c["id"] for c in items]
    elif args.id:
        ids = [args.id]
    else:
        print("crhub conflicts resolve: name a conflict, or pass --all", file=sys.stderr)
        return 2
    from region.core.errors import HubError

    failed = 0
    for cid in ids:
        try:
            out = client.resolve(cid, args.take, body)
        except HubError as e:
            failed += 1
            print(f"{cid}  NOT resolved: {e.detail}", file=sys.stderr)
            continue
        print(f"{cid}  {args.take}" + (f" (changeset {out['changeset']})" if out.get("changeset") else ""))
    print(f"{len(ids) - failed} resolved, {failed} not")
    return 1 if failed else 0


def run(args: argparse.Namespace) -> int:
    from region.core import lock, paths
    from region.core.errors import NotFound

    if getattr(args, "conflicts_command", None) is None:
        args.conflicts_command = "list"
        args.layer, args.all, args.json, args.db = None, False, False, None
    hub = None
    if args.db is None:
        from region.api.client import running_hub

        cfg = paths.config()
        by = getattr(args, "by", None) or str(cfg.get("user") or "ben")
        hub = running_hub(client="crhub-cli", by=by, timeout=120.0)
    if hub is not None:
        print(f"(through the hub serving at {hub.base})", file=sys.stderr)
        return _work(_Http(hub), hub, args)
    from region.model import open_store

    db = Path(args.db) if args.db is not None else paths.var_path("region.db")
    if not db.is_file():
        raise NotFound(f"no database at {db}; run crhub setup first")
    if args.conflicts_command in ("list", "show"):
        with open_store(db, readonly=True) as store:
            return _work(_Direct(store, "ben"), None, args)
    by = args.by or str(paths.config().get("user") or "ben")
    with lock.acquire(paths.var_root(), 0, command="crhub conflicts resolve"), open_store(db, create=False) as store:
        return _work(_Direct(store, by), None, args)


__all__ = ["register", "run"]
