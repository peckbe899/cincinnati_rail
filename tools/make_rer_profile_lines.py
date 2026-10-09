"""Build RER line data for the RER Profiles page, in the Metro Profiles format.

One long section per RER line: the core of a representative through service, from two
stations outside the first underground station or drawn "Trunk" segment to two stations
past the last one (canon station modes in data/profile/rer/canon.json), inside the map 3
ground raster. Writes data/profile/rer/lines/RER_*.json (2 m chainage, map 3
ground in decimetres, stations, rivers, crossings with Metro and other RER lines, trunk
spans), lines/index.json and metro_rails.json (every Metro line's rail, saved profile or
the solver default, for the clearance check at crossings).

    python tools/make_rer_profile_lines.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from railsim import elevation as elev  # noqa: E402
from railsim.app import curve_design_from, deep_merge, profile_design_from, speed_policy_from  # noqa: E402
from railsim.commuter import SPEC  # noqa: E402
from railsim.geo import cumulative_length, project_point_to_polyline  # noqa: E402
from railsim.line import build_route  # noqa: E402
from railsim.metro_profile import MetroProfile  # noqa: E402
from railsim.operations import load_era  # noqa: E402
from railsim.rollingstock import load_library  # noqa: E402

PROFILE = ROOT / "data" / "profile"
OUT = PROFILE / "rer"
DEM = PROFILE / "dem" / "map3_profile_dem_dm.vrt"
STEP = 2.0
APPROACH_STATIONS = 2  # stations kept outside the trunk at each end (portal approaches)

# a representative 2026 through service per line (the core is the same for every branch pair)
SERVICES = {
    "RER-1": "cin_rer_1_northgate__fayetteville",
    "RER-2": "cin_rer_2_kettering__cvg_terminal_1",
    "RER-3": "cin_rer_3_osgood__georgetown",
    "RER-4": "cin_rer_4_dover__greensburg",
    "RER-5": "cin_rer_5_waynesville__williamstown",
}
CANON = json.loads((OUT / "canon.json").read_text())
# when each drawn trunk opened for through-running (data/operations/cincinnati_rer.yaml)
OPENED = {"RER-1": 1985, "RER-2": 1988, "RER-3": 1988, "RER-4": 1990, "RER-5": 1996}


def route_for(cfg_name: str):
    path = ROOT / "configs" / "commuter" / f"{cfg_name}.yaml"
    user = yaml.safe_load(path.read_text())
    era, train_key, _ = load_era(ROOT / user["operations"], 2026)
    cfg = deep_merge(deep_merge(SPEC.defaults, era.get("overlay", {})), user)
    cfg["profile"] = {"sources": []}  # plan only; the ground is sampled here at 2 m
    train = load_library(SPEC.library)[cfg.get("train") or train_key]
    return build_route(cfg, ROOT, curve_design_from(cfg, train), speed_policy_from(cfg, train),
                       profile_design_from(cfg), log=lambda *a: None)


def trunk_spans(route, step=20.0):
    """Fitted-chainage spans of drawn segments named '...Trunk...'."""
    s = np.arange(0.0, route.length, step)
    names = [route.drawn_segment(float(x))[0] for x in s]
    spans, cur = [], None
    for x, n in zip(s, names):
        if "Trunk" in n:
            if cur and cur[2] == n and x - cur[1] <= 2 * step:
                cur[1] = x
            else:
                cur = [x, x, n]
                spans.append(cur)
        else:
            cur = None
    return [(a, b, n) for a, b, n in spans if b - a > 100]


def rivers_along(lonlat, ch, net):
    from shapely.geometry import LineString, Point, Polygon
    out = []
    for name, rings in net["rivers"].items():
        polys = [Polygon(r) for r in rings if len(r) >= 3]
        inside = np.array([any(p.contains(Point(lo, la)) for p in polys) for lo, la in lonlat])
        k = 0
        while k < len(inside):
            if inside[k]:
                j = k
                while j + 1 < len(inside) and inside[j + 1]:
                    j += 1
                if ch[j] - ch[k] > 20:
                    out.append({"name": name, "c0": round(float(ch[k]), 1), "c1": round(float(ch[j]), 1)})
                k = j + 1
            else:
                k += 1
    return sorted(out, key=lambda r: r["c0"])


def centerline_rivers(lonlat, ch, proj):
    """Rivers too narrow for the shoreline outlines (canon `centerline`, e.g. the Little
    Miami): a span of `width_m` around each crossing of the Overture centreline."""
    from shapely.geometry import LineString
    from railsim.kml import read_kml_bytes
    want = {k: v for k, v in CANON["rivers"].items() if v.get("centerline")}
    if not want:
        return []
    water = read_kml_bytes((ROOT / "data/reference/overture_water_cincinnati.kml").read_bytes())
    pxy = np.column_stack(proj.to_xy(np.array([la for _, la in lonlat]), np.array([lo for lo, _ in lonlat])))
    me = LineString(pxy)
    out = []
    for w in water:
        nm = w.name.split(" [")[0]
        if nm not in want:
            continue
        for ln in w.lines:
            oxy = np.column_stack(proj.to_xy(np.array([c[0] for c in ln]), np.array([c[1] for c in ln])))
            inter = me.intersection(LineString(oxy))
            pts = [inter] if inter.geom_type == "Point" else list(getattr(inter, "geoms", []))
            for p in pts:
                if p.geom_type != "Point":
                    continue
                c = project_point_to_polyline(p.x, p.y, pxy, ch)[0]
                hw = want[nm].get("width_m", 60.0) / 2
                out.append({"name": nm, "c0": round(float(c - hw), 1), "c1": round(float(c + hw), 1)})
    return out


def crossings(path_xy, ch, others, proj):
    """Chainage where this line's plan crosses each other line ([(id, label, kind, xy, chain)])."""
    from shapely.geometry import LineString
    me = LineString(path_xy)
    out = []
    for oid, label, kind, oxy, och in others:
        inter = me.intersection(LineString(oxy))
        pts = [inter] if inter.geom_type == "Point" else list(getattr(inter, "geoms", []))
        for p in pts:
            if p.geom_type != "Point":
                continue
            c, _, i = project_point_to_polyline(p.x, p.y, path_xy, ch)
            oc, _, j = project_point_to_polyline(p.x, p.y, oxy, och)
            # shared corridors (a common trunk, parallel tracks) are not crossings
            a = path_xy[min(i + 1, len(path_xy) - 1)] - path_xy[i]
            b = oxy[min(j + 1, len(oxy) - 1)] - oxy[j]
            nab = np.hypot(*a) * np.hypot(*b)
            if nab == 0 or abs(a[0] * b[1] - a[1] * b[0]) / nab < np.sin(np.radians(15)):
                continue
            if any(x["wid"] == oid and abs(x["c"] - c) < 100 for x in out):
                continue
            out.append({"c": round(float(c), 1), "wid": oid, "oc": round(float(oc), 1),
                        "kind": kind, "with": label})
    return sorted(out, key=lambda x: x["c"])


def metro_rails():
    """Every Metro line's rail as the page saves it (saved profile, else the solver default)."""
    out = {}
    settings = PROFILE / "settings.json"
    for f in sorted((PROFILE / "lines").glob("Line_*.json")):
        al = PROFILE / "alignments" / f.name
        mp = MetroProfile.load(f, al if al.exists() else None, settings)
        out[mp.id] = {"line": mp.data["line"], "length_m": mp.length, "saved": al.exists(),
                      "stations": [{"name": s["name"], "c": s["c"], "rail": round(float(z), 2)}
                                   for s, z in zip(mp.stations, mp.st)],
                      "pvi": [[round(float(c), 1), round(float(z), 2)] for c, z in mp.pvi]}
    return out


def main():
    net = json.loads((PROFILE / "network.json").read_text())
    (OUT / "lines").mkdir(parents=True, exist_ok=True)
    built = {}
    for line, cfg_name in SERVICES.items():
        print(f"{line}: routing {cfg_name}")
        r = route_for(cfg_name)
        spans = trunk_spans(r)
        if not spans:
            print(f"  no trunk on {cfg_name}; skipped")
            continue
        sts = [s for s in r.stations]
        modes = CANON["lines"].get(line.replace("-", "_"), {}).get("modes", {})
        under = [s.s for s in sts if (modes.get(s.name) or {}).get("mode") == "under"]
        t0 = min([a for a, _, _ in spans] + under)
        t1 = max([b for _, b, _ in spans] + under)
        before = [k for k, s in enumerate(sts) if s.s < t0 - 1]
        after = [k for k, s in enumerate(sts) if s.s > t1 + 1]
        k0 = before[-APPROACH_STATIONS] if len(before) >= APPROACH_STATIONS else 0
        k1 = after[APPROACH_STATIONS - 1] if len(after) >= APPROACH_STATIONS else len(sts) - 1
        # clip to the raster: drop end stations whose surroundings are off the map 3 ground
        s0 = max(0.0, sts[k0].s - 400.0)
        s1 = min(r.length, sts[k1].s + 400.0)
        built[line] = (r, spans, sts[k0:k1 + 1], s0, s1, cfg_name)

    # plans of every line for crossings, in one projection per line
    metro = {k: np.array(v) for k, v in net["metro"].items()}
    index, rails = [], metro_rails()
    for line, (r, spans, sts, s0, s1, cfg_name) in built.items():
        lid = line.replace("-", "_")
        L = s1 - s0
        n = int(np.floor(L / STEP)) + 1
        cs = np.arange(n) * STEP
        h = r.horizontal
        sq = s0 + cs
        ground = elev.from_dem(r.proj, h.xy, h.s, sq, DEM, scale=0.1, spacing=STEP, water=False,
                               progress=lambda *a: None)
        if ground is None:
            print(f"  {line}: no map 3 ground; skipped")
            continue
        # path every ~25 m (the page draws the plan and maps hover chainage with it)
        pc = np.arange(0.0, L, 25.0).tolist() + [L]
        lat, lon = r.latlon_at(np.array(pc) + s0)
        path = [[round(c, 1), round(float(lo), 7), round(float(la), 7)] for c, lo, la in zip(pc, lon, lat)]
        stations = []
        for s in sts:
            c = s.s - s0
            stations.append({"name": s.name, "c": round(c, 1),
                             "ground": round(float(np.interp(c, cs, ground)), 2),
                             "offset": round(s.offset, 1), "lon": round(s.lon, 7), "lat": round(s.lat, 7),
                             "trunk": any(a - 150 <= s.s <= b + 150 for a, b, _ in spans)})
        trunks = [{"name": nme, "c0": round(max(a - s0, 0.0), 1), "c1": round(min(b - s0, L), 1)}
                  for a, b, nme in spans]
        # crossings in this line's projection
        pxy = np.column_stack(r.proj.to_xy(np.array(lat), np.array(lon)))
        pch = np.array(pc)
        others = []
        for mid in metro:
            # Metro plan chainage from its line file (the page's own chainage)
            md = json.loads((PROFILE / "lines" / f"{mid}.json").read_text())
            mp = np.array(md["path"])
            mxy = np.column_stack(r.proj.to_xy(mp[:, 2], mp[:, 1]))
            others.append((mid, md["line"], "metro", mxy, mp[:, 0]))
        for oline, (orr, _, _, os0, os1, _) in built.items():
            if oline == line:
                continue
            oc = np.arange(0.0, os1 - os0, 25.0)
            ola, olo = orr.latlon_at(oc + os0)
            oxy = np.column_stack(r.proj.to_xy(np.array(ola), np.array(olo)))
            others.append((oline.replace("-", "_"), oline, "rer", oxy, oc))
        cr = crossings(pxy, pch, others, r.proj)
        doc = {
            "id": lid, "line": line, "system": "Cincinnati RER", "service": cfg_name,
            "opened": OPENED.get(line), "length_m": round(L, 1), "step_m": STEP,
            "ground_dm": [None if not np.isfinite(g) else int(round(g * 10)) for g in ground],
            "stations": stations, "trunks": trunks,
            "rivers": sorted(rivers_along(list(zip(lon, lat)), pch, net)
                             + centerline_rivers(list(zip(lon, lat)), pch, r.proj), key=lambda x: x["c0"]),
            "path": path, "crossings": cr,
            "route_chainage_m": [round(s0, 1), round(s1, 1)],
            "ground_note": "map 3 (alternate 2026) ground from map3_profile_dem_dm.vrt; "
                           "LiDAR / terrain tiles where the raster has no data",
        }
        (OUT / "lines" / f"{lid}.json").write_text(json.dumps(doc, separators=(",", ":")))
        index.append({"id": lid, "line": line, "length_m": doc["length_m"], "stations": len(stations)})
        print(f"  {line}: {L / 1000:.1f} km, {len(stations)} stations "
              f"({sum(s['trunk'] for s in stations)} on the trunk), {len(cr)} crossings, "
              f"{len(doc['rivers'])} river spans")
    (OUT / "lines" / "index.json").write_text(json.dumps(index, separators=(",", ":")))
    (OUT / "metro_rails.json").write_text(json.dumps(rails, separators=(",", ":")))
    # plan background for the page: Metro and RER cores plus the rivers
    netout = {"metro": net["metro"], "rivers": net["rivers"],
              "rer": {line.replace("-", "_"): [[p[1], p[2]] for p in json.loads(
                  (OUT / "lines" / f"{line.replace('-', '_')}.json").read_text())["path"]]
                  for line in built}}
    (OUT / "network.json").write_text(json.dumps(netout, separators=(",", ":")))


if __name__ == "__main__":
    main()
