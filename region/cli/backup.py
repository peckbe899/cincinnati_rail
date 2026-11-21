"""``crhub backup``: an online, checked backup of the database into ``var/backups`` (section 9's runbook name
for ``crhub model backup``).

    crhub backup [--db PATH] [--reason manual]

A thin alias: the arguments and the work are ``region.cli.model``'s, so the two spellings never drift apart.
While a hub serves from ``var``, the backup goes through its HTTP API (decision 9.28).
"""

from __future__ import annotations

import argparse


def register(subparsers: argparse._SubParsersAction) -> None:
    from region.cli import model

    p = subparsers.add_parser("backup", help=model.HELP["backup"] + " (the same as crhub model backup)")
    model.backup_arguments(p)
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    from region.cli import model

    return model.run_action("backup", args)


__all__ = ["register", "run"]
