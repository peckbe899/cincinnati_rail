"""``crhub serve``: serve the hub on 127.0.0.1 (the default command, decision 9.22).

    crhub serve [--db PATH] [--port N] [--no-browser] [--no-engine] [--no-seeds] [--no-live]

In order it takes ``var``'s single-instance lock, refuses a missing database (``crhub setup`` creates it), checks the
port, runs ``quick_check``, migrates after a backup, imports pulled seeds and prints a report, scans the data tiers,
starts the engine pool, the scheduler and the live hub (``region/live``: every source watched, a change imported
and re-solved as it is saved), and serves ``http://127.0.0.1:8766``. It never runs npm and never touches
the network; a banner says when ``app/dist`` is older than its source. Ctrl+C stops it: the scheduler stops, the
engine pool closes, the WAL is truncated and the lock is released. See ``region/api/serve.py``.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("serve", help="serve the hub on 127.0.0.1 (the default command)")
    p.add_argument("--db", type=Path, default=None, help="the database (default var/region.db)")
    p.add_argument("--port", type=int, default=None, help="the port (default: port in the config, 8766)")
    p.add_argument("--host", default=None, help="loopback only: 127.0.0.1 (default) or ::1")
    p.add_argument("--no-browser", action="store_true", help="do not open the app in a browser")
    p.add_argument("--no-engine", action="store_true", help="run without the Node engine pool")
    p.add_argument("--no-seeds", action="store_true", help="do not import pulled seeds at start")
    p.add_argument(
        "--no-live", action="store_true", help="do not watch the sources (changes are reported at start as dry runs)"
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    from region.api.serve import Serve

    return Serve(
        db=args.db,
        port=args.port,
        host=args.host,
        engine=not args.no_engine,
        browser=not args.no_browser,
        seeds=not args.no_seeds,
        live=False if args.no_live else None,
    ).run()
