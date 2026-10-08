"""Run a config with variations and print trip times against the reference schedule.

    python tools/sensitivity.py commuter configs/commuter/mbta_needham.yaml \
        "geometry.line_speed_mph=50" "padding.percent=10" ...

Each argument after the config is one variant (comma-separate several overrides in one
variant). The baseline is always run first.
"""

from __future__ import annotations

import contextlib
import copy
import io
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def set_path(d, dotted, value):
    keys = dotted.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = yaml.safe_load(value)


def run(program, cfg_dict, cfg_path):
    mod = __import__(f"railsim.{program}", fromlist=["main"])
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", dir=cfg_path.parent, delete=False) as f:
        yaml.safe_dump(cfg_dict, f)
        tmp = Path(f.name)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            _, results = mod.main([str(tmp), "--no-plots", "--out", str(ROOT / "output" / "_sens")])
    finally:
        tmp.unlink()
    return results


def main():
    program, cfg_path = sys.argv[1], Path(sys.argv[2]).resolve()
    base = yaml.safe_load(cfg_path.read_text())
    refs = base.get("reference", {})
    variants = [("baseline", [])] + [(v, v.split(",")) for v in sys.argv[3:]]
    print(f"{'variant':48} {'dir':>4} {'run':>6} {'+dwell':>7} {'sched':>7} {'ref':>5} {'err%':>6}")
    for name, overrides in variants:
        cfg = copy.deepcopy(base)
        for o in overrides:
            k, v = o.split("=", 1)
            set_path(cfg, k.strip(), v.strip())
        for dr, sd in run(program, cfg, cfg_path):
            key = "reverse" if dr.reverse else "forward"
            ref = refs.get(key, {}).get(dr.stations[-1].name)
            sched = sd["scheduled_time_min"]
            err = f"{(sched - ref) / ref * 100:+.1f}" if ref else ""
            print(f"{name[:48]:48} {'rev' if dr.reverse else 'fwd':>4} {sd['running_time_min']:6.1f} "
                  f"{sd['trip_time_min']:7.1f} {sched:7.1f} {ref if ref else '':>5} {err:>6}")


if __name__ == "__main__":
    main()
