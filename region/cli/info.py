"""``crhub info``: where this hub finds things. Reads only; changes nothing.

Prints the repo, the Python running it, ``var`` and where that choice came from, the config files read, each data
tier and whether its root is on this machine, the feature folders and the commands. ``--json`` prints the same as one
JSON object. ``crhub doctor`` (WP0b) is the command that checks; this one only reports.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from typing import Any


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("info", help="show where this hub finds its repo, var, configs, tiers and features")
    p.add_argument("--json", action="store_true", help="print one JSON object")
    p.set_defaults(func=run)


def facts() -> dict[str, Any]:
    """The facts ``crhub info`` prints."""
    from region.cli import commands
    from region.core import features, paths

    cfg = paths.config()
    var, var_from = paths.describe_var(cfg)
    tiers = {}
    for name, tier in paths.tiers(cfg).items():
        ok = tier.available()
        tiers[name] = {"root": str(tier.root), "available": ok is True, "reason": None if ok is True else ok}
    return {
        "repo": str(paths.repo_root()),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "var": str(var),
        "var_from": var_from,
        "configs": cfg.get("_files", []),
        "port": cfg.get("port"),
        "tiers": tiers,
        "features": [f.name for f in features.discover()],
        "commands": commands(),
    }


def run(args: argparse.Namespace) -> int:
    info = facts()
    if args.json:
        print(json.dumps(info, indent=1, ensure_ascii=False))
        return 0
    print(f"repo      {info['repo']}")
    print(f"python    {info['python']} ({info['executable']})")
    print(f"platform  {info['platform']}")
    print(f"var       {info['var']} ({info['var_from']})")
    print(f"port      {info['port']}")
    print("configs   " + (", ".join(info["configs"]) or "none"))
    print("tiers")
    for name, t in info["tiers"].items():
        state = "here" if t["available"] else "missing"
        print(f"  {name:20} {state:8} {t['root']}")
    print("features  " + (", ".join(info["features"]) or "none yet"))
    print("commands  " + ", ".join(info["commands"]))
    return 0
