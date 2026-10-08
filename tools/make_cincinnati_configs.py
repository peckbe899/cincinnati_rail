"""Generate line configs for every Cincinnati Metro line and RER through-route.

Metro: one config per line folder, routed between the stations at its two dead ends.
RER: one config per pair of branch terminals whose route is turn-feasible through the trunk
(a train cannot reverse at a junction), named '<RER-n> <A> - <B>'.
Stations that appear on more than one line are classed as transfer (metro) / hub (RER).

    python tools/make_cincinnati_configs.py            # writes configs/metro/cin_*.yaml, configs/commuter/cin_*.yaml
"""

from __future__ import annotations

import itertools
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from railsim.geo import LocalProjection  # noqa: E402
from railsim.kml import read_kmz, select  # noqa: E402
from railsim.network import Network  # noqa: E402

KMZ = "data/kmz/Cincinnati_Rail.kmz"
HISTORIC_KMZ = "data/kmz/cincinnati_historic.kml"
RER_OPS = "data/operations/cincinnati_rer.yaml"
METRO_TRAIN = "CMCC_TYPE2005_10CAR"
RER_TRAIN = "RER_F_SET"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def build(pms, folder, extra=()):
    tr = [p for p in select(pms, folder) if p.lines] + list(extra)
    st = [p for p in select(pms, folder) if p.points]
    lines = [ln for p in tr for ln in p.lines]
    lat = [c[0] for ln in lines for c in ln]
    lon = [c[1] for ln in lines for c in ln]
    proj = LocalProjection.around(lat, lon)
    polys = [np.column_stack(proj.to_xy([c[0] for c in ln], [c[1] for c in ln])) for ln in lines]
    return Network.build(polys), proj, st


def end_stations(net, proj, st, tol=1500.0):
    out = []
    for n in [n for n in net.adj if net.degree(n) == 1]:
        x, y = net.nodes[n]
        best = None
        for p in st:
            sx, sy = proj.to_xy(p.points[0][0], p.points[0][1])
            d = math.hypot(float(sx) - x, float(sy) - y)
            if best is None or d < best[0]:
                best = (d, p.name)
        if best and best[0] <= tol:
            out.append(best[1])
    return list(dict.fromkeys(out))


# USGS 1 m LiDAR projects covering the region, newest first (no 1 m coverage yet for
# Northern Kentucky: terrain tiles fill it). Point reads only, cached in data/elevation_cache.
LIDAR_PROJECTS = ["OH_Statewide_Phase3_2021_B21", "OH_Statewide_Phase1_2019_B19",
                  "IN_Indiana_Statewide_LiDAR_2017_B17", "KY_Statewide_2021_A21"]

RER_COMMON = {
    "geometry": {"line_speed_mph": 90, "max_cant_in": 5.0},
    "speed": {"cant_deficiency_in": 4.0},
    "profile": {"max_grade": 0.02, "sources": ["csv", "kmz", "dem", "lidar", "terrain"], "lidar_projects": LIDAR_PROJECTS, "usgs": False},
    "padding": {"percent": 5.0, "final_leg_s": 60},
}


def main():
    pms = read_kmz(ROOT / KMZ)
    ops = yaml.safe_load((ROOT / RER_OPS).read_text())
    history = ops.get("history", {}) or {}
    through_from = ops.get("through_from", {}) or {}
    psd_lines = yaml.safe_load((ROOT / "data/operations/cincinnati_metro.yaml").read_text()).get(
        "psd_lines", {}) or {}
    metro_folders = sorted({p.folder_path[2] for p in pms if len(p.folder_path) >= 3
                            and p.folder_path[1] == "Cincinnati Metro"},
                           key=lambda f: (int(re.sub(r"\D", "", f) or 0), f))
    rer_folders = sorted({p.folder_path[2] for p in pms if len(p.folder_path) >= 3
                          and p.folder_path[1] == "Cincinnati RER"})
    metro_names = Counter()
    for f in metro_folders:
        metro_names.update({p.name for p in select(pms, f"Cincinnati Metro/{f}") if p.points})
    rer_names = Counter()
    for f in rer_folders:
        rer_names.update({p.name for p in select(pms, f"Cincinnati RER/{f}") if p.points})

    (ROOT / "configs/metro").mkdir(parents=True, exist_ok=True)
    (ROOT / "configs/commuter").mkdir(parents=True, exist_ok=True)
    written = []
    for f in metro_folders:
        folder = f"Cincinnati Metro/{f}"
        net, proj, st = build(pms, folder)
        ends = end_stations(net, proj, st)
        info = {p.name: {"class": "transfer"} for p in st if metro_names[p.name] > 1 or rer_names[p.name] > 0}
        cfg = {
            "name": f"Cincinnati Metro {f}",
            "kmz": KMZ,
            "operations": "data/operations/cincinnati_metro.yaml",  # year -> fleet, signalling, GoA
            "track": {"folder": folder},
            # platform screen doors line-wide on the busiest lines (they apply once the
            # era sets dwell.psd_overhead, i.e. from the GoA3 conversion)
            "stations": {"folder": f"{folder}/{f} Stations", "info": info,
                         "defaults": {"psd": f in psd_lines}},
            "geometry": {"line_speed_mph": 55},
            "profile": {"max_grade": 0.05, "sources": ["csv", "kmz", "dem", "lidar", "terrain"], "lidar_projects": LIDAR_PROJECTS, "usgs": False},
        }
        if len(ends) >= 2:
            cfg["service"] = {"route": [ends[0], ends[-1]]}
        path = ROOT / f"configs/metro/cin_{slug(f)}.yaml"
        path.write_text("# generated by tools/make_cincinnati_configs.py - edit freely\n"
                        + yaml.safe_dump(cfg, sort_keys=False))
        written.append(path)

    for f in rer_folders:
        folder = f"Cincinnati RER/{f}"
        net, proj, st = build(pms, folder)
        ends = end_stations(net, proj, st, tol=600.0)
        info = {p.name: {"class": "hub"} for p in st if rer_names[p.name] > 1 or metro_names[p.name] > 0}
        locs, where = {}, {}
        for n in [n for n in net.adj if net.degree(n) == 1]:
            nx, ny = net.nodes[n]
            near = []
            for p in st:
                if p.name not in ends:
                    continue
                x, y = proj.to_xy(p.points[0][0], p.points[0][1])
                near.append((math.hypot(float(x) - nx, float(y) - ny), p))
            if not near:
                continue
            d, p = min(near, key=lambda t: t[0])
            if d > 600 or p.name in locs:
                continue
            x, y = proj.to_xy(p.points[0][0], p.points[0][1])
            loc = net.locate(float(x), float(y), 600)
            if loc:
                locs[p.name] = loc[:2]
                where[p.name] = [round(p.points[0][0], 6), round(p.points[0][1], 6)]
        for a, b in itertools.combinations([e for e in ends if e in locs], 2):
            try:
                _, ch = net.route([locs[a], locs[b]], 90.0)
            except ValueError:
                continue
            cfg = {
                "name": f"Cincinnati {f} {a} - {b}",
                "kmz": KMZ,
                "operations": "data/operations/cincinnati_rer.yaml",  # year -> fleet, signalling
                "track": {"folder": folder},
                "stations": {"folder": f"{folder}/{f} Stations", "match_tol_m": 200,
                             "defaults": {"class": "standard", "platform": "high"}, "info": info},
                "service": {"route": [{"name": a, "near": where[a]}, {"name": b, "near": where[b]}]},
                **RER_COMMON,
            }
            # when the service ran: branch-to-branch lines (and terminals that predate the
            # RER) since 1934; the rest from the RER opening
            _covered(cfg, ops, f)
            # branch-to-branch services exist from the line's through-running date
            cfg["years"] = [int(through_from.get(f, 1985)), 2100]
            path = ROOT / f"configs/commuter/cin_{slug(f)}_{slug(a)}__{slug(b)}.yaml"
            path.write_text(f"# generated by tools/make_cincinnati_configs.py ({ch[-1] / 1000:.1f} km)\n"
                            + yaml.safe_dump(cfg, sort_keys=False))
            written.append(path)
    written += historic_configs(pms, ops, rer_names, metro_names)
    for p in written:
        print(p.relative_to(ROOT))


def _covered(cfg, ops, line):
    """Covered ways (e.g. RER-3 along the Ohio) as tunnel structures."""
    covered = (ops.get("covered_ways", {}) or {}).get(line) or []
    if covered:
        cfg["profile"] = {**cfg["profile"], "structures": [{"type": "tunnel", **c} for c in covered]}


def historic_configs(pms, ops, rer_names, metro_names):
    """Pre-through services: a branch into its city terminal (Union Terminal or Times)."""
    history = ops.get("history", {}) or {}
    through_from = ops.get("through_from", {}) or {}
    hist = read_kmz(ROOT / HISTORIC_KMZ) if (ROOT / HISTORIC_KMZ).exists() else []
    out = []
    for svc in history.get("services", []):
        f = svc["line"]
        if svc.get("pending"):
            print(f"PENDING historic {f} {svc['from']} - {svc['to']}: {svc['pending']}")
            continue
        folder = f"Cincinnati RER/{f}"
        extra, track_extra, notes = [], [], []
        ex = svc.get("extra")
        if ex:
            extra += [p for p in select(pms, ex["folder"], ex.get("name_regex")) if p.lines]
            track_extra.append(dict(ex))
        via = None
        if svc.get("via"):
            line = next(p for p in hist if p.name == svc["via"] and p.lines)
            # all of this line's historic track (the Miamitown approach joins the Oxford one)
            extra += [p for p in select(hist, f"Cincinnati Historic/{f}") if p.lines]
            track_extra.append({"kmz": HISTORIC_KMZ, "folder": f"Cincinnati Historic/{f}"})
            pts = line.lines[0]
            mid = pts[len(pts) // 2]
            via = [round(mid[0], 6), round(mid[1], 6)]
            notes.append(f"{svc['via']} digitized from data/reference/rer1_historic_approaches.webp")
        if svc.get("approx"):
            notes.append(svc["approx"])
        net, proj, st = build(pms, folder, extra)

        def find(name):
            c = [p for p in st if p.name == name]
            if not c:
                raise SystemExit(f"{f}: no station '{name}'")
            p = c[0]
            return {"name": name, "near": [round(p.points[0][0], 6), round(p.points[0][1], 6)]}

        a, b = find(svc["from"]), find(svc["to"])
        stops = []
        for e in (a, b):
            loc = net.locate(*map(float, proj.to_xy(*e["near"])), 2000)
            if loc[2] > 200:
                notes.append(f"station '{e['name']}' is {loc[2]:.0f} m from the drawn track (snapped)")
            stops.append(loc[:2])
        if via:
            stops.insert(1, net.locate(*map(float, proj.to_xy(*via)), 300)[:2])
        try:
            _, ch = net.route(stops, 90.0)
        except ValueError:
            print(f"SKIP historic {f} {a['name']} - {b['name']}: no turn-feasible route")
            continue
        y0, y1 = svc.get("years") or [None, None]
        years = [int(y0 or 1934), int(y1 or int(through_from.get(f, 1985)) - 1)]
        info = {p.name: {"class": "hub"} for p in st if rer_names[p.name] > 1 or metro_names[p.name] > 0}
        cfg = {
            "name": f"Cincinnati {f} {a['name']} - {b['name']} (before through-running)",
            "kmz": KMZ,
            "operations": RER_OPS,
            "years": years,
            "year": (years[0] + years[1]) // 2,
            "track": {"folder": folder, **({"extra": track_extra} if track_extra else {})},
            # tight match: stations on today's alignments beside the old ROW are not served
            "stations": {"folder": f"{folder}/{f} Stations", "match_tol_m": 120,
                         "defaults": {"class": "standard", "platform": "high"}, "info": info},
            "service": {"route": [a] + ([{"via": via}] if via else []) + [b]},
            # through the station throat into the city terminal
            "terminal_approach": {"speed_mph": 20, "distance_m": 500, "stations": [b["name"]]},
            # the trunk signalling (SACEM, CBTC) came with through-running
            "operating_zones": [],
            **RER_COMMON,
        }
        _covered(cfg, ops, f)
        path = ROOT / f"configs/commuter/cin_{slug(f)}_pre_rer_{slug(a['name'])}__{slug(b['name'])}.yaml"
        head = f"# generated by tools/make_cincinnati_configs.py ({ch[-1] / 1000:.1f} km, pre-RER)\n"
        for n in notes:
            head += f"# NOTE: {n}\n"
        path.write_text(head + yaml.safe_dump(cfg, sort_keys=False))
        out.append(path)
    return out


if __name__ == "__main__":
    main()
