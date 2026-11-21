"""``crhub restore``: put a backup back, after backing the current database up (section 9's runbook name for
``crhub model restore``). It refuses while a hub serves: stop the hub first.

    crhub restore FILE [--db PATH]

A thin alias: the arguments and the work are ``region.cli.model``'s, so the two spellings never drift apart.
"""

from __future__ import annotations

import argparse


def register(subparsers: argparse._SubParsersAction) -> None:
    from region.cli import model

    p = subparsers.add_parser("restore", help=model.HELP["restore"] + " (the same as crhub model restore)")
    model.restore_arguments(p)
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    from region.cli import model

    return model.run_action("restore", args)


__all__ = ["register", "run"]
