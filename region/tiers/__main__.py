"""``python -m region.tiers [--json]``: print the data tier scan. Reads only; changes nothing."""

from __future__ import annotations

import argparse
import json
import sys

from region.tiers import as_json, counts, scan


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m region.tiers", description="Scan the data tiers of hub_paths.json.")
    p.add_argument("--json", action="store_true", help="print the body of GET /tiers")
    args = p.parse_args(argv)
    reports = scan()
    if args.json:
        print(json.dumps(as_json(reports), indent=1, ensure_ascii=False))
        return 0
    for r in reports.values():
        flags = ",".join(f for f, on in (("required", r.required), ("mount", r.mount)) if on)
        print(f"{r.status:8} {r.name:20} {r.detail}" + (f"  [{flags}]" if flags else ""))
    c = counts(reports)
    print(f"{c['present']} present, {c['partial']} partial, {c['missing']} missing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
