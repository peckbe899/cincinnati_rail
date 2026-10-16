"""Build the CVG Express line file for the Rail Profiles page (data/profile/lines/CVG_Express.json)
from data/kmz/CVG_Express.kmz, in the Metro line format: the drawn path with its chainage, map 3
ground every 2 m (the canon riverbed under rivers), stations, rivers, drawn pieces and crossings
with the Metro lines (reciprocal entries are written into their line files; the RER crossings
come from tools/make_rer_profile_lines.py, run it afterwards).

The route: Union Terminal (the drawn start, 90 m from Line 7's Union Terminal; no station is drawn
there) south over the Ohio to CVG, then Terminals 3, 2, 4, 1B and 1A on piece 5 ('Today', or
'Original', which serves 1B and 1A only), and on to the yard lead. Piece 2 is drawn south to north
and runs 125 m past the start of piece 3; the path turns onto piece 3 where it starts (on piece 2's
line) and leaves that stub out.

    python tools/make_cvg_profile_line.py [Today|Original]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from railsim import elevation as elev  # noqa: E402
from railsim.geo import LocalProjection, cumulative_length, project_point_to_polyline  # noqa: E402
from railsim.kml import read_kmz  # noqa: E402
from make_rer_profile_lines import crossings, rivers_along  # noqa: E402

PROFILE = ROOT / "data" / "profile"
KMZ = ROOT / "data" / "kmz" / "CVG_Express.kmz"
DEM = PROFILE / "dem" / "map3_profile_dem_dm.vrt"
STEP = 2.0
LID = "CVG_Express"
TERMINALS = ["Terminal 3", "Terminal 2", "Terminal 4", "Terminal 1B", "Terminal 1A"]


def main(variant: str = "Today"):
    pms = {p.name: p for p in read_kmz(KMZ)}
    lines = {n: np.array([(c[0], c[1]) for c in p.lines[0]]) for n, p in pms.items() if p.lines}  # (lat, lon)
    names = ["CVG Express 1", "CVG Express 2", "CVG Express 3", "CVG Express 4", f"CVG Express 5 - {variant}"]
    allpts = np.vstack([lines[n] for n in names])
    proj = LocalProjection.around(allpts[:, 0], allpts[:, 1])
    xy = {n: np.column_stack(proj.to_xy(lines[n][:, 0], lines[n][:, 1])) for n in names}

    # chain the pieces from the Union Terminal end, each oriented to follow the previous one
    path, pieces, c = [], [], 0.0
    for k, n in enumerate(names):
        P = xy[n]
        if path and np.hypot(*(P[-1] - path[-1])) < np.hypot(*(P[0] - path[-1])):
            P = P[::-1]
        if k + 1 < len(names):
            # the next piece starts on this one's line (piece 2 / piece 3): stop there
            Q = xy[names[k + 1]]
            for q in (Q[0], Q[-1]):
                s = cumulative_length(P)
                cc, off, i = project_point_to_polyline(float(q[0]), float(q[1]), P, s)
                if off < 5.0 and 5.0 < cc < s[-1] - 5.0:
                    t = (cc - s[i]) / max(s[i + 1] - s[i], 1e-9)
                    P = np.vstack([P[:i + 1], P[i] + t * (P[i + 1] - P[i])])
                    print(f"  {n}: cut {s[-1] - cc:.0f} m past the start of {names[k + 1]}")
                    break
        gap = float(np.hypot(*(P[0] - path[-1]))) if path else 0.0
        c0 = c + gap
        path.extend(P.tolist())
        c = c0 + float(cumulative_length(P)[-1])
        pieces.append({"name": n, "id": f"CVG Express|{n}", "c0": round(c0, 1), "c1": round(c, 1),
                       "reversed": bool(not np.allclose(P[0], xy[n][0])), "gap_before": round(gap, 1)})
    pxy = np.array(path)
    keep = np.r_[True, np.hypot(*np.diff(pxy, axis=0).T) > 0.05]
    pxy = pxy[keep]
    ch = cumulative_length(pxy)
    L = float(ch[-1])
    lat, lon = proj.to_latlon(pxy[:, 0], pxy[:, 1])

    # stations: Union Terminal at the drawn start, the terminals where they project
    stations = [{"name": "Union Terminal", "c": 0.0, "lon": round(float(lon[0]), 7), "lat": round(float(lat[0]), 7),
                 "offset": 0.0, "src": "drawn start of the line (no station placemark; 90 m from Line 7's Union Terminal)"}]
    for t in TERMINALS:
        la, lo = pms[t].points[0][:2]
        x, y = proj.to_xy(la, lo)
        cc, off, _ = project_point_to_polyline(float(x), float(y), pxy, ch)
        if off > 50:
            print(f"  {t}: {off:.0f} m off the {variant} route; not served")
            continue
        stations.append({"name": t, "c": round(float(cc), 1), "lon": round(lo, 7), "lat": round(la, 7), "offset": round(float(off), 1)})
    stations.sort(key=lambda s: s["c"])

    # ground every 2 m: the bed under rivers (no water-surface overlay)
    n = int(np.floor(L / STEP)) + 1
    cs = np.arange(n) * STEP
    ground = elev.from_dem(proj, pxy, ch, cs, DEM, scale=0.1, spacing=STEP, water=False, progress=print)
    for s in stations:
        s["ground"] = round(float(np.interp(s["c"], cs, ground)), 2)

    net = json.loads((PROFILE / "network.json").read_text())
    cs10 = np.arange(0.0, L, 10.0)
    ll10 = list(zip(np.interp(cs10, ch, lon), np.interp(cs10, ch, lat)))
    rivers = rivers_along(ll10, cs10, net)

    # crossings with the Metro lines, in this projection (Metro chainage from their line files)
    others = []
    index = json.loads((PROFILE / "lines" / "index.json").read_text())
    for e in index:
        if e["id"] == LID:
            continue
        md = json.loads((PROFILE / "lines" / f"{e['id']}.json").read_text())
        mp = np.array(md["path"])
        others.append((e["id"], md["line"], "metro", np.column_stack(proj.to_xy(mp[:, 2], mp[:, 1])), mp[:, 0]))
    cr = crossings(pxy, ch, others, proj)

    doc = {"id": LID, "line": "CVG Express", "system": "Cincinnati Metro", "variant": variant,
           "length_m": round(L, 1), "step_m": STEP,
           "ground_dm": [None if not np.isfinite(g) else int(round(g * 10)) for g in ground],
           "stations": stations, "rivers": rivers, "pieces": pieces,
           "path": [[round(float(a), 1), round(float(b), 7), round(float(d), 7)] for a, b, d in zip(ch, lon, lat)],
           "crossings": cr,
           "ground_note": "map 3 (alternate 2026) ground from map3_profile_dem_dm.vrt, the canon riverbed under the Ohio "
                          "and Licking; built by tools/make_cvg_profile_line.py from data/kmz/CVG_Express.kmz"}
    (PROFILE / "lines" / f"{LID}.json").write_text(json.dumps(doc, separators=(",", ":")))
    index = [e for e in index if e["id"] != LID] + [{"id": LID, "line": "CVG Express", "length_m": doc["length_m"], "stations": len(stations)}]
    (PROFILE / "lines" / "index.json").write_text(json.dumps(index, separators=(",", ":")))
    net["metro"][LID] = [[round(float(b), 5), round(float(d), 5)] for b, d in zip(lon, lat)]
    (PROFILE / "network.json").write_text(json.dumps(net, separators=(",", ":")))

    # reciprocal crossing entries in the other Metro line files
    for x in cr:
        p = PROFILE / "lines" / f"{x['wid']}.json"
        md = json.loads(p.read_text())
        md["crossings"] = [y for y in md.get("crossings", []) if y.get("wid") != LID]
    for wid in {x["wid"] for x in cr} | {e["id"] for e in index if e["id"] != LID}:
        p = PROFILE / "lines" / f"{wid}.json"
        md = json.loads(p.read_text())
        before = len(md.get("crossings", []))
        md["crossings"] = [y for y in md.get("crossings", []) if y.get("wid") != LID] + \
            [{"c": x["oc"], "wid": LID, "oc": x["c"], "kind": "metro", "with": "CVG Express"} for x in cr if x["wid"] == wid]
        md["crossings"].sort(key=lambda y: y["c"])
        if len(md["crossings"]) != before or any(y.get("wid") == LID for y in md["crossings"]):
            p.write_text(json.dumps(md, separators=(",", ":")))
    print(f"CVG Express ({variant}): {L / 1000:.2f} km, {len(stations)} stations "
          f"{[s['name'] for s in stations]}, {len(rivers)} river spans {[r['name'] for r in rivers]}, "
          f"{len(cr)} Metro crossings {[x['with'] for x in cr]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Today")
