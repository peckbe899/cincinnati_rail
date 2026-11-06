"""Capture the baseline the rebuild must reproduce or explain (checklist 2.0.10).

Sources: the old hub's work folder (`hub/work`, Ben's 5 November snapshot: the headless editors' samples of every
route every 5 m, the saved alignments as the page read them, platforms, approaches, the 3D snapshot's issues) and
railsim's run times for every config.

    python tests/baseline/capture.py --work PATH/TO/hub/work        # profiles, platforms, approaches, issues
    python tests/baseline/capture.py --runtimes metro               # railsim run times, Metro configs (fast)
    python tests/baseline/capture.py --runtimes commuter            # TRI configs (needs the ground; run on Ben's machine)

Writes under tests/baseline/: profiles/<route>.json, platforms.json, approaches.json, issues.json, runtimes.json,
and README.md with the capture date and sources. Deterministic; re-running on the same inputs gives the same files.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tests" / "baseline"


def rle(values):
    """[[value, count], ...] for a list with long runs (structure types, tube forms)."""
    out = []
    for v in values:
        if out and out[-1][0] == v:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return out


def capture_work(work: Path):
    h = json.loads((work / "harness_out.json").read_text())
    (OUT / "profiles").mkdir(parents=True, exist_ok=True)
    plats, apps, summary = {}, {}, {}
    for route, rec in h["profiles"].items():
        samples = rec.get("samples") or []
        c = [s[0] for s in samples]
        step = round(c[1] - c[0], 3) if len(c) > 1 else None
        prof = {
            "route": route, "saved": rec.get("saved"), "c0": c[0] if c else None, "step_m": step, "n": len(c),
            "rail_m": [round(s[1], 3) for s in samples],
            "type": rle([s[2] for s in samples]),
            "tube": rle([s[3] if len(s) > 3 else None for s in samples]),
            "align": rec.get("align"),
        }
        (OUT / "profiles" / f"{route}.json").write_text(json.dumps(prof, separators=(",", ":"), sort_keys=True) + "\n")
        plats[route] = rec.get("platforms")
        apps[route] = rec.get("approaches")
        summary[route] = {"n": len(c), "step_m": step, "saved": rec.get("saved"), "types": sorted({s[2] for s in samples})}
    (OUT / "platforms.json").write_text(json.dumps(plats, indent=0, sort_keys=True) + "\n")
    (OUT / "approaches.json").write_text(json.dumps(apps, indent=0, sort_keys=True) + "\n")
    snap = json.loads((work / "snapshot.json").read_text())
    (OUT / "issues.json").write_text(json.dumps({"synced_at": snap.get("synced_at"), "issues": snap.get("issues")}, indent=1) + "\n")
    return summary, snap.get("synced_at")


def capture_runtimes(kind: str):
    cfgs = sorted((ROOT / "configs" / kind).glob("*.yaml"))
    prog = "railsim.metro" if kind == "metro" else "railsim.commuter"
    path = OUT / "runtimes.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    for cfg in cfgs:
        r = subprocess.run([sys.executable, "-m", prog, str(cfg)], capture_output=True, text=True, cwd=ROOT)
        stem = cfg.stem
        summ = ROOT / "output" / stem / "summary.json"
        if r.returncode != 0 or not summ.exists():
            data[stem] = {"error": (r.stderr or r.stdout)[-800:]}
            print("FAILED", stem, file=sys.stderr)
            continue
        s = json.loads(summ.read_text())
        data[stem] = {
            "kind": kind, "line": s.get("line"), "train": s.get("train"),
            "warnings": s.get("warnings"),
            "directions": [{"direction": d["direction"], "distance_km": d["distance_km"], "running_time_min": d["running_time_min"],
                            "dwell_total_min": d["dwell_total_min"], "trip_time_min": d["trip_time_min"], "scheduled_time_min": d.get("scheduled_time_min"),
                            "stations": [{"name": st["name"], "km": st["km"], "arrive_s": st["arrive_s"], "scheduled_arrive_s": st.get("scheduled_arrive_s")} for st in d["stations"]]}
                           for d in s["directions"]],
        }
        print("%-55s %s" % (stem, "  ".join("%.1f" % d["trip_time_min"] for d in s["directions"])))
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")


def write_readme(summary, synced_at, note):
    lines = ["# Baseline (checklist 2.0.10)", "",
             "Captured %s. Sources: Ben's hub work folder (snapshot synced %s), railsim on the configs." % (dt.date.today().isoformat(), synced_at),
             "", "The rebuild compares every route's solved rail and structure types against `profiles/<route>.json` (every 5 m, rail in m, types",
             "run-length coded) and every service's run time against `runtimes.json`; a difference is classed same, rule fix with its rule id,",
             "or unexplained (must be zero). `issues.json` is the old 3D build's issue list. `platforms.json` and `approaches.json` are the",
             "page's platform and approach records.", ""]
    if summary:
        lines += ["| Route | samples | step | saved | types |", "|---|---|---|---|---|"]
        for r, s in sorted(summary.items()):
            lines.append("| %s | %d | %s | %s | %s |" % (r, s["n"], s["step_m"], s["saved"], ", ".join(s["types"])))
    if note:
        lines += ["", note]
    (OUT / "README.md").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path)
    ap.add_argument("--runtimes", choices=["metro", "commuter"])
    a = ap.parse_args()
    if a.work:
        summary, synced = capture_work(a.work)
        write_readme(summary, synced, "Run times: `python tests/baseline/capture.py --runtimes metro` here, `--runtimes commuter` on Ben's machine (the TRI configs read ground outside the core).")
    if a.runtimes:
        capture_runtimes(a.runtimes)


if __name__ == "__main__":
    main()
