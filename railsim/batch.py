"""Run every config in a folder and write one summary table.

    python -m railsim.batch configs/metro
    python -m railsim.batch configs/commuter --pattern "cin_rer_1*"
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
from pathlib import Path

import yaml


def main(argv=None):
    ap = argparse.ArgumentParser(prog="railsim.batch")
    ap.add_argument("folder")
    ap.add_argument("--pattern", default="*.yaml")
    ap.add_argument("--program", choices=["metro", "commuter"],
                    help="default: inferred from the folder name")
    ap.add_argument("--out", default="output/batch_summary.csv")
    args = ap.parse_args(argv)
    folder = Path(args.folder)
    prog = args.program or ("metro" if "metro" in folder.name else "commuter")
    mod = __import__(f"railsim.{prog}", fromlist=["main"])
    rows = []
    for cfg in sorted(folder.glob(args.pattern)):
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                _, results = mod.main([str(cfg), "--no-plots"])
            for dr, sd in results:
                rows.append([cfg.stem, sd["direction"], sd["distance_km"], sd["stops"],
                             sd["running_time_min"], sd["trip_time_min"], sd["scheduled_time_min"],
                             sd["average_speed_kmh"], sd["max_speed_kmh"]])
            warn = [ln.strip() for ln in buf.getvalue().splitlines() if "WARNING" in ln]
            print(f"OK   {cfg.stem}" + (f"  ({len(warn)} warnings)" if warn else ""))
        except Exception as e:  # keep going; report at the end
            rows.append([cfg.stem, f"FAILED: {e}", "", "", "", "", "", "", ""])
            print(f"FAIL {cfg.stem}: {e}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["config", "direction", "km", "stops", "running_min", "trip_min",
                    "scheduled_min", "avg_kmh", "max_kmh"])
        w.writerows(rows)
    print(f"summary: {out}")


if __name__ == "__main__":
    main()
