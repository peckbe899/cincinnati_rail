"""``crhub jobs``: look at and tidy the job cache (``cache.db`` and its blobs).

    crhub jobs list [--all] [--json]        queued and running jobs (every job with --all), newest first
    crhub jobs show <job>                   one job and its log
    crhub jobs types [--json]               the job types this hub knows
    crhub jobs stats [--json]               counts and bytes of the cache
    crhub jobs prune --max-mb N             evict least recently used results down to N MiB (pinned goals kept)
    crhub jobs wipe --yes                   delete the cache; the hub recomputes what it needs
    crhub jobs run <type> <scope> [view]    plan and run one job here, then print its result

``--cache`` names another ``cache.db`` (default ``var/cache/cache.db``). ``wipe`` and ``run`` are for when the
server is not running: the server's scheduler is the only writer of the cache while it runs. They hold ``var``'s
single-instance lock (``region.core.lock``) while they work, so they refuse to start while a server (or another of
them) holds it, and a server cannot start under them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("jobs", help="look at and tidy the job cache (jobs, results, blobs)")
    p.add_argument("--cache", type=Path, default=None, help="cache.db to use (default var/cache/cache.db)")
    sub = p.add_subparsers(dest="jobs_command", metavar="<action>")

    ls = sub.add_parser("list", help="queued and running jobs, newest first")
    ls.add_argument("--all", action="store_true", help="every job, not only active ones")
    ls.add_argument("--limit", type=int, default=50)
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(jobs_func=_list)

    show = sub.add_parser("show", help="one job and its log")
    show.add_argument("job")
    show.add_argument("--json", action="store_true")
    show.set_defaults(jobs_func=_show)

    types = sub.add_parser("types", help="the job types this hub knows")
    types.add_argument("--json", action="store_true")
    types.set_defaults(jobs_func=_types)

    stats = sub.add_parser("stats", help="counts and bytes of the cache")
    stats.add_argument("--json", action="store_true")
    stats.set_defaults(jobs_func=_stats)

    prune = sub.add_parser("prune", help="evict least recently used results (pinned goals are kept)")
    prune.add_argument("--max-mb", type=float, required=True, help="keep at most this many MiB of blobs")
    prune.set_defaults(jobs_func=_prune)

    wipe = sub.add_parser("wipe", help="delete the cache (only while the server is stopped)")
    wipe.add_argument("--yes", action="store_true", help="really delete it")
    wipe.set_defaults(jobs_func=_wipe)

    run = sub.add_parser("run", help="plan and run one job here (only while the server is stopped)")
    run.add_argument("type")
    run.add_argument("scope")
    run.add_argument("--layer", default="main")
    run.add_argument("--year", type=int, default=None)
    run.add_argument("--month", type=int, default=None)
    run.add_argument("--tl", default="canon", help="timeline: canon or real")
    run.add_argument("--db", type=Path, default=None, help="region.db (default var/region.db)")
    run.add_argument("--timeout", type=float, default=600.0)
    run.add_argument("--json", action="store_true")
    run.set_defaults(jobs_func=_run)

    p.set_defaults(func=_main, jobs_parser=p)


def _main(args: argparse.Namespace) -> int:
    fn = getattr(args, "jobs_func", None)
    if fn is None:
        args.jobs_parser.print_help()
        return 2
    return int(fn(args) or 0)


def _cache_path(args: argparse.Namespace) -> Path:
    from region.jobs.cache import default_cache_path

    return Path(args.cache) if args.cache is not None else default_cache_path()


def _open(args: argparse.Namespace) -> Any:
    from region.jobs.cache import Cache

    return Cache(_cache_path(args))


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=1, ensure_ascii=False, default=str))


def _list(args: argparse.Namespace) -> int:
    cache = _open(args)
    try:
        where = "" if args.all else "WHERE state IN ('queued', 'running')"
        rows = [dict(r) for r in cache.query(f"SELECT * FROM job {where} ORDER BY id DESC LIMIT ?", (args.limit,))]
    finally:
        cache.close()
    if args.json:
        _print_json(rows)
        return 0
    if not rows:
        print("no jobs" if args.all else "no active jobs")
        return 0
    for r in rows:
        print(f"{r['id']}  {r['state']:9} p{r['priority']}  {r['type']}  {r['scope']}  {r['view']}  {r['msg'] or ''}")
    return 0


def _show(args: argparse.Namespace) -> int:
    from region.core.errors import NotFound

    cache = _open(args)
    try:
        row = cache.one("SELECT * FROM job WHERE id = ?", (args.job,))
        if row is None:
            raise NotFound(f"no job {args.job}")
        job = dict(row)
        job["log"] = [
            dict(r) for r in cache.query("SELECT at, level, msg FROM job_log WHERE job = ? ORDER BY seq", (args.job,))
        ]
    finally:
        cache.close()
    if args.json:
        _print_json(job)
        return 0
    for k, v in job.items():
        if k != "log":
            print(f"{k:12} {v}")
    print("log")
    for line in job["log"]:
        print(f"  {line['at']} {line['level']:7} {line['msg']}")
    return 0


def _types(args: argparse.Namespace) -> int:
    from region.jobs.registry import default_registry

    rows = default_registry().describe()
    if args.json:
        _print_json(rows)
        return 0
    for r in rows:
        print(f"{r['name']:28} v{r['version']}  {r['host']:7} p{r['priority']}  scope {r['scope']}  {r['module']}")
    return 0


def _stats(args: argparse.Namespace) -> int:
    cache = _open(args)
    try:
        stats = cache.stats()
    finally:
        cache.close()
    if args.json:
        _print_json(stats)
        return 0
    for k, v in stats.items():
        print(f"{k:14} {v}")
    return 0


def _prune(args: argparse.Namespace) -> int:
    cache = _open(args)
    try:
        out = cache.evict(int(args.max_mb * 1024 * 1024))
    finally:
        cache.close()
    print(f"evicted {out['results']} results and {out['blobs']} blobs, {out['bytes']} bytes")
    return 0


def _server_lock(command: str) -> Any:
    """``var``'s single-instance lock for this command (``LockHeld``, a 409 the CLI prints, while a server or another
    command holds it)."""
    from region.core import lock, paths

    return lock.acquire(paths.var_root(), 0, command=command)


def _wipe(args: argparse.Namespace) -> int:
    from region.jobs.cache import wipe

    path = _cache_path(args)
    if not args.yes:
        print(f"this deletes {path} and its blobs; run again with --yes", file=sys.stderr)
        return 2
    with _server_lock("crhub jobs wipe"):
        removed = wipe(path)
    print(f"removed {removed} cache files; the hub recomputes what it needs")
    return 0


def _run(args: argparse.Namespace) -> int:
    from region.core import paths
    from region.core.errors import NotFound
    from region.core.view import View

    try:
        from region.model import open_store  # the store (WP1)
    except ImportError as e:
        print(f"crhub jobs run: the record store is not available here ({e})", file=sys.stderr)
        return 2
    db = Path(args.db) if args.db is not None else paths.var_path("region.db")
    if not db.exists():
        raise NotFound(f"no database at {db}; run crhub setup first")
    view = View(args.layer, args.year, args.month, args.tl)
    with _server_lock("crhub jobs run"):
        store = open_store(db)
        try:
            return _run_with(args, store, view)
        finally:
            close = getattr(store, "close", None)
            if callable(close):
                close()


def _run_with(args: argparse.Namespace, store: Any, view: Any) -> int:
    from region.core.errors import NotFound
    from region.jobs.scheduler import Scheduler

    sched = Scheduler(store, _cache_path(args), None).start()
    try:
        out = sched.submit(args.type, args.scope, view, priority=0)
        key = out["key"]
        if out["state"] != "hit":
            if out["job"] is None:
                raise NotFound(f"{args.type} {args.scope}: nothing was queued")
            sched.wait_idle(args.timeout)
            job = sched.job(out["job"])
            if job["state"] != "done":
                print(f"job {job['id']} {job['state']}: {job.get('error') or job.get('msg')}", file=sys.stderr)
                return 1
            key = sched.result(args.type, args.scope, view)
        res = sched.result_meta(key)
    finally:
        sched.stop()
    if args.json:
        _print_json(res)
    else:
        print(f"{args.type} {args.scope} {view.token()}: {res['status']} {key}")
        print(json.dumps(res["meta"], indent=1, ensure_ascii=False))
    return 0
