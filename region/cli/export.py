"""``crhub export``: before you commit, take in pulled seeds, then write the main and proposal layers to
``region/seed`` (section 9's runbook name for ``crhub model export``).

    crhub export [--db PATH] [--out region/seed]

A thin alias: the arguments and the work are ``region.cli.model``'s, so the two spellings never drift apart.
"""

from __future__ import annotations

import argparse


def register(subparsers: argparse._SubParsersAction) -> None:
    from region.cli import model

    p = subparsers.add_parser("export", help=model.HELP["export"] + " (the same as crhub model export)")
    model.export_arguments(p)
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    from region.cli import model

    return model.run_action("export", args)


__all__ = ["register", "run"]
