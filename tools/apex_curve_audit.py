"""List tight curves on finished APEx alignments for review in Google Earth.

Reads output/apex_*/summary.json (run the APEx configs first) and writes
docs/apex_curve_audit.csv and docs/apex_curve_audit.kmz: every fitted curve on a finished
segment (data/operations/apex.yaml) tighter than the 2,000 m new-construction minimum, with
its untilted speed under the canon curve model (C = 30.56 V^2/R, D 180 mm, Eu 130 mm up to
186 mph and 100 mm above). Curves on upgraded legacy rights of way may legitimately be
tighter; the list is for deciding which is which.

    python tools/apex_curve_audit.py [--radius 2000]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from railsim.kml import KmlWriter  # noqa: E402


def canon_speed_mph(R: float) -> float:
    v130 = min(math.sqrt(R * (180 + 130) / 30.56), 186.0)
    v100 = math.sqrt(R * (180 + 100) / 30.56)
    return min(max(v130, v100), 250.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius", type=float, default=2000.0)
    a = ap.parse_args()
    rows, seen = [], set()
    for f in sorted((ROOT / "output").glob("apex_*/summary.json")):
        d = json.loads(f.read_text())
        route = f.parent.name[5:]
        for c in d["curves"]:
            if c.get("sketch", True) or c["radius_m"] >= a.radius:
                continue
            key = (c.get("segment"), round(c["lat"], 3), round(c["lon"], 3))
            if key in seen:  # the same curve on a shared segment
                continue
            seen.add(key)
            rows.append({"segment": c["segment"], "route": route, "radius_m": c["radius_m"],
                         "speed_mph": round(canon_speed_mph(c["radius_m"])),
                         "lat": c["lat"], "lon": c["lon"]})
    rows.sort(key=lambda r: (r["segment"], r["radius_m"]))
    out = ROOT / "docs/apex_curve_audit.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["segment"])
        w.writeheader()
        w.writerows(rows)
    kw = KmlWriter("APEx tight curves on finished alignments")
    for seg in sorted({r["segment"] for r in rows}):
        kw.open_folder(seg or "(unnamed)")
        for r in (r for r in rows if r["segment"] == seg):
            kw.point(f"R {r['radius_m']:.0f} m / {r['speed_mph']} mph", r["lat"], r["lon"],
                     f"{r['route']}: radius {r['radius_m']:.0f} m, untilted {r['speed_mph']} mph")
        kw.close_folder()
    kw.save(ROOT / "docs/apex_curve_audit.kmz")
    print(f"{len(rows)} curves under {a.radius:.0f} m on finished segments "
          f"({len({r['segment'] for r in rows})} segments) -> docs/apex_curve_audit.csv/.kmz")


if __name__ == "__main__":
    main()
