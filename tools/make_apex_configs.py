"""Generate configs for every APEx route (Tier 1 and Tier 2) in data/kmz/APEx_Routes.kmz.

Each route folder's LineStrings are routed end to end (longest turn-feasible route between
dead ends); terminals are the stations nearest the route ends. Stations come from every
station folder in the KMZ; their class comes from the Limited / Express / Local folder
they are in (highest class wins when a station appears in several routes).
Stopping patterns: --stops limited | express | all  (default express).

    python tools/make_apex_configs.py
    python -m railsim.train configs/train/apex_great_lakes_limited.yaml --stops limited
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from railsim.geo import LocalProjection  # noqa: E402
from railsim.kml import read_kmz, select  # noqa: E402
from railsim.network import Network  # noqa: E402

KMZ = "data/kmz/APEx_Routes.kmz"
SNAP = 450.0  # m: continental-scale drawings leave gaps of a few hundred metres between segments


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _routable(net, pms_in_folder, proj) -> bool:
    for t in (90.0, 135.0):
        try:
            net.longest_route_between_leaves(t)
            return True
        except ValueError:
            continue
    return False


def _stub_stations(net, stations, proj):
    """Stations on this route's track that sit at a stub end (a reversal point)."""
    out, seen = [], set()
    for p in stations:
        if p.name in seen:
            continue
        x, y = proj.to_xy(p.points[0][0], p.points[0][1])
        if net.locate(float(x), float(y), 300.0) is None:
            continue
        tip = net.stub_tip(float(x), float(y), 500.0)
        if tip is not None:
            seen.add(p.name)
            out.append((p, tip[:2]))
    return out


def _tip_node(net, tip):
    e = net.edges[tip[0]]
    return e.u if tip[1] == 0.0 else e.v


def _route_with_reversals(net, stations, proj, turn):
    """Longest leaf-to-leaf route that reverses at up to three stub stations."""
    from itertools import permutations
    stubs = _stub_stations(net, stations, proj)
    leaves = [n for n in net.adj if net.degree(n) == 1]
    best = None
    for i, a in enumerate(leaves):
        for b in leaves[i + 1:]:
            for k in range(1, min(3, len(stubs)) + 1):
                for seq in permutations(stubs, k):
                    if any(_tip_node(net, tp) in (a, b) for _, tp in seq):
                        continue  # a route end, not a reversal part-way along
                    stops = [net._node_stop(a)] + [tp for _, tp in seq] + [net._node_stop(b)]
                    try:
                        xy, ch = net.route(stops, turn, reverse_at=range(1, k + 1))
                    except ValueError:
                        continue
                    if best is None or ch[-1] > best[0]:
                        best = (ch[-1], xy, [p for p, _ in seq])
                if best:
                    break  # fewest reversals that work
    return (best[1], best[2]) if best else None


def _length(xy):
    return float(np.sum(np.hypot(*np.diff(np.asarray(xy), axis=0).T)))


def _is_loop(net):
    return bool(net.adj) and all(net.degree(n) == 2 for n in net.adj) and net._connected()


def _loop_entries(net, stations, proj, entry, folder, pms):
    own = [p for p in select(pms, f"{folder}/Stations") if p.points]
    rank = {"Limited": 0, "Express": 1, "Local": 2}
    on = []
    for p in own or stations:
        x, y = proj.to_xy(p.points[0][0], p.points[0][1])
        if net.locate(float(x), float(y), 300.0) is not None:
            on.append((min((rank.get(f, 3) for f in p.folder_path), default=3), p, np.array([x, y], float)))
    on.sort(key=lambda t: t[0])
    origin = on[0]
    far = max(on, key=lambda t: float(np.hypot(*(t[2] - origin[2]))))
    for t in (90.0, 135.0):
        try:
            a = net.locate(*map(float, origin[2]))[:2]
            b = net.locate(*map(float, far[2]))[:2]
            net.route([a, b, a], t)
            return [entry(origin[1]), entry(far[1]), entry(origin[1])], t
        except (ValueError, TypeError):
            continue
    raise ValueError("loop is not turn-feasible")


def main():
    pms = read_kmz(ROOT / KMZ)
    stations = [p for p in pms if p.points and "Stations" in p.folder_path
                or (p.points and any(f in ("Limited", "Express", "Local") for f in p.folder_path))]
    routes = sorted({(p.folder_path[1], p.folder_path[2]) for p in pms
                     if p.lines and len(p.folder_path) >= 3 and p.folder_path[2] != "Stations"})
    out_dir = ROOT / "configs/train"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = []
    for tier, name in routes:
        folder = f"APEx Routes/{tier}/{name}"
        lines = [ln for p in select(pms, folder) if p.lines for ln in p.lines]
        lat = [c[0] for ln in lines for c in ln]
        lon = [c[1] for ln in lines for c in ln]
        proj = LocalProjection.around(lat, lon)
        polys = [np.column_stack(proj.to_xy([c[0] for c in ln], [c[1] for c in ln])) for ln in lines]
        notes = []

        def entry(p):
            return {"name": p.name, "near": [round(p.points[0][0], 6), round(p.points[0][1], 6)]}

        def nearest_station(pt, pool, lim):
            best = None
            for p in pool:
                x, y = proj.to_xy(p.points[0][0], p.points[0][1])
                d = math.hypot(float(x) - pt[0], float(y) - pt[1])
                if best is None or d < best[0]:
                    best = (d, p)
            return best if best and best[0] <= lim else None

        # 1) the route's own Limited stations, listed in route order: first and last;
        #    tight snapping first, widened only to bridge drawing gaps
        own = [p for p in select(pms, f"{folder}/Stations/Limited") if p.points] or \
              [p for p in select(pms, f"{folder}/Stations") if p.points]
        route_entries, turn, snap, net = None, None, None, None
        if len(own) >= 2:
            for snap_try in (60.0, SNAP):
                n_try = Network.build(polys, snap_tol=snap_try)
                # intermediate stations at stub ends (track drawn in and back out) are
                # reversals: the train runs to the buffer and the driver changes ends
                stubs = []
                for p in own[1:-1]:
                    x, y = proj.to_xy(p.points[0][0], p.points[0][1])
                    tip = n_try.stub_tip(float(x), float(y), 500.0)
                    if tip is not None:
                        stubs.append((p, tip[:2]))
                for t in (90.0, 135.0):
                    try:
                        ends = []
                        for p in (own[0], own[-1]):
                            x, y = proj.to_xy(p.points[0][0], p.points[0][1])
                            loc = n_try.locate(float(x), float(y), 3000)
                            if loc is None:
                                raise ValueError("terminal off track")
                            ends.append(loc[:2])
                        try:
                            n_try.route(ends, t)
                            via = []
                        except ValueError:
                            if not stubs:
                                raise
                            n_try.route([ends[0]] + [tp for _, tp in stubs] + [ends[1]], t,
                                        reverse_at=range(1, len(stubs) + 1))
                            via = [dict(entry(p), reverse=True) for p, _ in stubs]
                            notes.append("reverses at stub terminal(s): "
                                         + ", ".join(p.name for p, _ in stubs))
                        route_entries = [entry(own[0])] + via + [entry(own[-1])]
                        turn, snap, net = t, snap_try, n_try
                        break
                    except ValueError:
                        continue
                if route_entries:
                    break
        if route_entries is None:
            for snap_try in (60.0, SNAP):
                n_try = Network.build(polys, snap_tol=snap_try)
                if _routable(n_try, None, proj):
                    net, snap = n_try, snap_try
                    break
            else:
                net, snap = Network.build(polys, snap_tol=SNAP), SNAP
        # 2) otherwise the longest route between dead ends; terminals = nearest stations,
        #    or synthetic end-of-track terminals
        if route_entries is None:
            xy = None
            via = []
            for t in (90.0, 135.0):
                try:
                    xy = net.longest_route_between_leaves(t)
                    turn = t
                    break
                except ValueError:
                    continue
            # stub terminals part-way along (Chicago, St Louis, Cincinnati are drawn as
            # in-and-out tracks): allow the train to reverse at them when that covers
            # clearly more of the drawn line (a dead-end stub can otherwise end the route)
            base_len = _length(xy) if xy is not None else 0.0
            for t in (90.0, 135.0):
                found = _route_with_reversals(net, stations, proj, t)
                if found and _length(found[0]) > 1.15 * base_len:
                    xy, via = found
                    turn = t
                    notes.append("reverses at stub terminal(s): "
                                 + ", ".join(p.name for p in via))
                    break
            if xy is None and _is_loop(net):
                # closed loop (e.g. a Texas Triangle service): start and finish at the
                # highest-class station, running once round via the station farthest from it
                route_entries, turn = _loop_entries(net, stations, proj, entry, folder, pms)
                notes.append("loop service: starts and ends at the same station")
                xy = True
            if xy is None:
                report.append(f"SKIP {tier}/{name}: no turn-feasible end-to-end route "
                              f"(loop line or disconnected drawing: set service.route by hand)")
                continue
        if route_entries is None:
            route_entries = []
            for k, pt in enumerate((xy[0], xy[-1])):
                hit = nearest_station(pt, stations, 5000)
                if hit:
                    route_entries.append(entry(hit[1]))
                else:
                    la, lo = proj.to_latlon(pt[0], pt[1])
                    route_entries.append({"name": f"{name} {'west/south' if k == 0 else 'east/north'} end",
                                          "lat": round(float(la), 6), "lon": round(float(lo), 6)})
                    notes.append("synthetic end-of-track terminal (no station placemark near the end)")
            if via:
                route_entries = ([route_entries[0]] + [dict(entry(p), reverse=True) for p in via]
                                 + [route_entries[1]])
        cfg = {
            "name": f"APEx {name} ({tier})",
            "preset": "hsr",
            "kmz": KMZ,
            "train": "APEX_GEN6",
            "track": {"folder": folder, "snap_tol_m": snap, "max_turn_deg": turn},
            "stations": {
                "folder": "APEx Routes",
                "match_tol_m": 500,
                "class_from_folder": {"Limited": "limited", "Express": "express", "Local": "local"},
                "class_rank": ["limited", "express", "local"],
                "unclassified": "local",
                "defaults": {"platform": "high", "platform_length_m": 400},
            },
            "service": {
                "route": route_entries,
                "stops": "express",
                "patterns": {"limited": ["limited"], "express": ["limited", "express"]},
            },
            "geometry": {"line_speed_mph": 250, "max_cant_mm": 180,
                         "design_cant_deficiency_mm": 90},
            "speed": {"cant_deficiency_mm": 90},
            # canon APEx Gen 6 dwells (PSDs + passenger information): by station class
            "dwell": {"by_class_s": {"local": 45, "express": 75, "limited": 180, "terminal": 180}},
        }
        path = out_dir / f"apex_{slug(name)}.yaml"
        head = f"# generated by tools/make_apex_configs.py ({tier})\n"
        for n in sorted(set(notes)):
            head += f"# NOTE: {n}\n"
        path.write_text(head + yaml.safe_dump(cfg, sort_keys=False))
        report.append(f"OK   {path.relative_to(ROOT)}  {route_entries[0]['name']} - "
                      f"{route_entries[-1]['name']}" + (f"  [{'; '.join(sorted(set(notes)))}]" if notes else ""))
    print("\n".join(report))


if __name__ == "__main__":
    main()
