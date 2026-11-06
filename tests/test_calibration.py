"""Calibration gates (checklist 2.0.11): the two reference services must keep their run times.

Regression: each direction's trip time within 1 % of the baseline captured on 6 November 2026
(tests/baseline/calibration.json). Reported, not failing: the model against the published times, and each station's
arrival against the config's reference minutes (the survey's suggested +-3 % per segment).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / "tests/baseline/calibration.json").read_text())
CFG = {"mbta_orange": ("railsim.metro", "configs/metro/mbta_orange.yaml"), "mbta_needham": ("railsim.commuter", "configs/commuter/mbta_needham.yaml")}


def run(stem):
    prog, cfg = CFG[stem]
    r = subprocess.run([sys.executable, "-m", prog, cfg], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-1500:]
    return json.loads((ROOT / "output" / stem / "summary.json").read_text())


@pytest.mark.parametrize("stem", sorted(BASE))
def test_reference_service_keeps_its_run_time(stem, capsys):
    s = run(stem)
    base = BASE[stem]
    assert len(s["directions"]) == len(base["directions"])
    report = []
    for d, b in zip(s["directions"], base["directions"]):
        assert d["direction"] == b["direction"]
        rel = (d["trip_time_min"] - b["trip_time_min"]) / b["trip_time_min"]
        report.append("%s: %.2f min (baseline %.2f, %+.2f %%), padded %s against published %s min" % (
            d["direction"], d["trip_time_min"], b["trip_time_min"], 100 * rel, d.get("scheduled_time_min"), base["published_min"]))
        assert abs(rel) <= 0.01, report[-1]
        # per-station against the config's reference minutes: reported only
        for st in d["stations"]:
            ref = st.get("scheduled_arrive_s")
            if ref and st["arrive_s"] and ref > 0:
                e = (st["arrive_s"] - ref) / ref
                if abs(e) > 0.03:
                    report.append("   %s: model %.0f s, reference %.0f s (%+.1f %%)" % (st["name"], st["arrive_s"], ref, 100 * e))
    print("\n".join(report))
