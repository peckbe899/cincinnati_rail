"""Build a simulation-ready route from a YAML line config and a KMZ.

Shared by both programs. Steps:
  1. read track LineStrings and station Points from the KMZ (by folder),
  2. build the track network and route through the service's stations (no reversals),
  3. reconstruct a realistic horizontal alignment (tangents, spirals, arcs),
  4. get ground elevation and design a vertical profile (or flat, with a warning),
  5. derive posted speed limits (curves, user restrictions, terminal approaches),
  6. lay the result on a uniform grid for each direction of travel.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import elevation as elev
from .dynamics import TrackData
from .geo import FT, INCH, KMH, MPH, LocalProjection, cumulative_length, project_point_to_polyline
from .horizontal import CurveDesign, HorizontalAlignment, fit_horizontal, fit_horizontal_pieces
from .kml import Placemark, read_kmz, select
from .network import Network
from .profile import Profile, ProfileDesign, design_profile, flat_profile
from .speed import Restriction, SpeedPolicy, SpeedProfile, build_speed_profile, zones_from_profile


# ----------------------------------------------------------------------------- unit helpers

def speed_of(d: dict, key: str, default=None) -> Optional[float]:
    """Read '<key>_mph' or '<key>_kmh' or '<key>_ms' from a dict, return m/s."""
    if f"{key}_mph" in d:
        return float(d[f"{key}_mph"]) * MPH
    if f"{key}_kmh" in d:
        return float(d[f"{key}_kmh"]) * KMH
    if f"{key}_ms" in d:
        return float(d[f"{key}_ms"])
    return default


def length_of(d: dict, key: str, default=None) -> Optional[float]:
    if f"{key}_in" in d:
        return float(d[f"{key}_in"]) * INCH
    if f"{key}_mm" in d:
        return float(d[f"{key}_mm"]) / 1000.0
    if f"{key}_ft" in d:
        return float(d[f"{key}_ft"]) * FT
    if f"{key}_m" in d:
        return float(d[f"{key}_m"])
    return default


# ----------------------------------------------------------------------------- data classes

@dataclass
class StationInfo:
    name: str
    lat: float
    lon: float
    s: float = 0.0  # chainage of platform centre on the fitted alignment
    offset: float = 0.0  # distance of the placemark from the track
    cls: str = "standard"
    platform: str = "high"
    platform_length: float = 150.0
    dwell_override: Optional[float] = None
    early_departure: bool = False  # 'L' stop: may leave early (commuter timetables)
    stop: bool = True
    reverse: bool = False  # stub terminal mid-route: the train reverses here
    psd: Optional[bool] = None  # platform screen doors (None: decided by dwell.psd_classes)


@dataclass
class Route:
    name: str
    proj: LocalProjection
    horizontal: HorizontalAlignment
    profile: Profile
    speed: SpeedProfile
    stations: List[StationInfo]
    warnings: List[str] = field(default_factory=list)
    drawn_route_xy: Optional[np.ndarray] = None
    supply_zones: List[Tuple[float, float, float]] = field(default_factory=list)  # (s0, s1, factor)
    supply_factor: float = 1.0
    neutral_sections: List[Tuple[float, float]] = field(default_factory=list)  # (s0, s1)
    zone_ranges: List[Tuple[float, float, int]] = field(default_factory=list)  # (s0, s1, zone)
    drawn_ranges: list = field(default_factory=list)  # (segment name, s0, s1) on the drawn route
    sketch_ranges: list = field(default_factory=list)  # drawn-chainage sketched stretches

    def drawn_segment(self, s: float) -> Tuple[str, bool, float, float]:
        """(drawn segment name, is sketch, lat, lon) at fitted chainage s."""
        h = self.horizontal
        x, y = np.interp(s, h.s, h.xy[:, 0]), np.interp(s, h.s, h.xy[:, 1])
        lat, lon = self.proj.to_latlon(x, y)
        name, sk = "", False
        if self.drawn_route_xy is not None and self.drawn_ranges:
            d = project_point_to_polyline(float(x), float(y), self.drawn_route_xy,
                                          cumulative_length(self.drawn_route_xy))[0]
            name = next((n for n, a, b in self.drawn_ranges if a <= d <= b), "")
            sk = any(a <= d <= b for a, b in self.sketch_ranges)
        return name, sk, float(lat), float(lon)

    @property
    def length(self) -> float:
        return self.horizontal.length

    def track_data(self, ds: float = 2.0) -> TrackData:
        L = self.length
        s = np.arange(0.0, L + ds, ds)
        s[-1] = L
        lim = self.speed.at(s)
        z = self.profile.elevation_at(s)
        curv = np.abs(self.horizontal.curvature(s))
        st = np.array(self.profile.structure)
        idx = np.clip(np.searchsorted(self.profile.s, s), 0, len(st) - 1)
        tunnel = st[idx] == "tunnel"
        pf = np.full(len(s), self.supply_factor)
        for s0, s1, f in self.supply_zones:
            pf[(s >= s0) & (s <= s1)] = f
        nt = np.zeros(len(s), dtype=bool)
        for s0, s1 in self.neutral_sections:
            nt[(s >= s0) & (s <= s1)] = True
        zone = np.zeros(len(s), dtype=int)
        for s0, s1, k in self.zone_ranges:
            zone[(s >= s0) & (s <= s1)] = k
        return TrackData(ds, s, lim, z, curv, tunnel, pf, nt, zone)

    def latlon_at(self, s_query) -> Tuple[np.ndarray, np.ndarray]:
        h = self.horizontal
        x = np.interp(s_query, h.s, h.xy[:, 0])
        y = np.interp(s_query, h.s, h.xy[:, 1])
        return self.proj.to_latlon(x, y)


# ----------------------------------------------------------------------------- building

def _stations_from_config(cfg: dict, placemarks: List[Placemark]) -> List[StationInfo]:
    st_cfg = cfg.get("stations", {}) or {}
    out: List[StationInfo] = []
    folder = st_cfg.get("folder")
    folder_classes = st_cfg.get("class_from_folder")  # e.g. {Limited: limited, Express: express}
    rank = {c: i for i, c in enumerate(st_cfg.get("class_rank", []) or [])}
    if folder:
        for p in select(placemarks, folder):
            for (lat, lon, _z) in p.points:
                st = StationInfo(p.name, lat, lon)
                if folder_classes:
                    for fname in reversed(p.folder_path):
                        if fname in folder_classes:
                            st.cls = folder_classes[fname]
                            break
                    else:
                        st.cls = st_cfg.get("unclassified", "standard")
                    # same station drawn in several route folders: keep its highest class
                    dup = next((o for o in out if o.name == st.name
                                and abs(o.lat - lat) + abs(o.lon - lon) < 0.003), None)
                    if dup is not None:
                        if rank.get(st.cls, 99) < rank.get(dup.cls, 99):
                            dup.cls = st.cls
                        continue
                out.append(st)
    for item in st_cfg.get("list", []) or []:
        out.append(StationInfo(item["name"], float(item["lat"]), float(item["lon"])))
    info = st_cfg.get("info", {}) or {}
    defaults = st_cfg.get("defaults", {}) or {}
    for s in out:
        d = dict(defaults)
        d.update(info.get(s.name, {}) or {})
        if "class" in (info.get(s.name, {}) or {}) or not folder_classes:
            s.cls = d.get("class", s.cls)
        s.platform = d.get("platform", s.platform)
        s.platform_length = float(length_of(d, "platform_length", s.platform_length))
        s.dwell_override = d.get("dwell_s")
        s.early_departure = bool(d.get("early_departure", False))
        if "psd" in d:
            s.psd = bool(d["psd"])
    return out


def _edge_point(net: Network, eid: int, ch: float):
    e = net.edges[eid]
    return np.array([np.interp(ch, e.s, e.xy[:, 0]), np.interp(ch, e.s, e.xy[:, 1])])


def build_route(cfg: dict, base_dir: Path, design: CurveDesign, policy: SpeedPolicy,
                pdesign: ProfileDesign, log=print) -> Route:
    kmz_path = (base_dir / cfg["kmz"]).resolve()
    placemarks = read_kmz(kmz_path)
    tcfg = cfg.get("track", {}) or {}
    track_pms = select(placemarks, tcfg.get("folder"), tcfg.get("name_regex"))
    excl = tcfg.get("exclude", []) or []
    track_pms = [p for p in track_pms if p.lines and p.name not in excl]
    # more track from other folders or files (e.g. historic rights of way, a shared spur)
    for src in tcfg.get("extra", []) or []:
        pm = read_kmz((base_dir / src["kmz"]).resolve()) if src.get("kmz") else placemarks
        track_pms += [p for p in select(pm, src.get("folder"), src.get("name_regex"))
                      if p.lines and p.name not in (src.get("exclude") or [])]
    if not track_pms:
        raise ValueError("no track LineStrings found (check track.folder in the config)")
    lines = [(p.name, ln) for p in track_pms for ln in p.lines]
    lat_all = [c[0] for _, ln in lines for c in ln]
    lon_all = [c[1] for _, ln in lines for c in ln]
    proj = LocalProjection.around(lat_all, lon_all)
    polys = [np.column_stack(proj.to_xy([c[0] for c in ln], [c[1] for c in ln])) for _, ln in lines]
    net = Network.build(polys, [n for n, _ in lines], snap_tol=float(tcfg.get("snap_tol_m", 30.0)))
    warnings: List[str] = []

    stations = _stations_from_config(cfg, placemarks)
    svc = cfg.get("service", {}) or {}
    route_names = svc.get("route")
    max_turn = float(tcfg.get("max_turn_deg", 90.0))  # reversals through a wye need >120 deg
    tol = float((cfg.get("stations", {}) or {}).get("match_tol_m", 150.0))

    snapped = set()

    def locate_name(entry):
        # entries are "Name" or {name: Name, near: [lat, lon]} to pick between same-named stations
        name = entry["name"] if isinstance(entry, dict) else entry
        cands = [s for s in stations if s.name == name]
        if not cands and isinstance(entry, dict) and "lat" in entry:
            # synthetic terminal (end of drawn track with no station placemark)
            st = StationInfo(name, float(entry["lat"]), float(entry["lon"]), cls="terminal")
            stations.append(st)
            cands = [st]
        if not cands:
            raise ValueError(f"station '{name}' in service.route not found")
        if isinstance(entry, dict) and entry.get("near"):
            la, lo = entry["near"]
            cands = [min(cands, key=lambda c: (c.lat - la) ** 2 + (c.lon - lo) ** 2)]
        best = None
        for c in cands:
            x, y = proj.to_xy(c.lat, c.lon)
            loc = net.locate(float(x), float(y), tol)
            if loc and (best is None or loc[2] < best[2]):
                best = loc
        if best is None:
            # placemark drawn away from the track: snap to the nearest track point, but say so
            for c in cands:
                x, y = proj.to_xy(c.lat, c.lon)
                loc = net.locate(float(x), float(y), 2000.0)
                if loc and (best is None or loc[2] < best[2]):
                    best = loc
            if best is None:
                raise ValueError(f"station '{name}' is more than 2 km from the track")
            warnings.append(f"station '{name}' is {best[2]:.0f} m from the track; routed to the "
                            f"nearest track point (fix the placemark)")
            snapped.add(name)
        if isinstance(entry, dict) and entry.get("reverse"):
            # stub terminal: the train runs to the buffer stop, the driver changes ends
            x, y = _edge_point(net, best[0], best[1])
            tip = net.stub_tip(float(x), float(y), float(entry.get("stub_radius_m", 500.0)))
            if tip is None:
                raise ValueError(f"station '{name}' is marked reverse but has no stub end "
                                 f"within {entry.get('stub_radius_m', 500.0)} m")
            reversing.add(name)
            return tip[:2]
        return best[:2]

    reversing: set = set()
    reversals: List[float] = []
    if route_names:
        def locate_via(entry):
            # non-stop waypoint {via: [lat, lon]} that picks between alternative paths
            x, y = proj.to_xy(float(entry["via"][0]), float(entry["via"][1]))
            loc = net.locate(float(x), float(y), 300.0)
            if loc is None:
                raise ValueError(f"service.route waypoint {entry['via']} is not on the track")
            return loc[:2]

        stops = [locate_via(n) if isinstance(n, dict) and "via" in n else locate_name(n)
                 for n in route_names]
        rev_idx = [k for k, n in enumerate(route_names) if isinstance(n, dict) and n.get("reverse")]
        drawn_xy, stop_ch = net.route(stops, max_turn, reverse_at=rev_idx)
        reversals = [stop_ch[k] for k in rev_idx if 0 < k < len(stops) - 1]
        route_names = [n for n in route_names if not (isinstance(n, dict) and "via" in n)]
    else:
        if not net.is_simple_path():
            warnings.append("track network branches; routing between the farthest dead ends. "
                            "Set service.route to choose a branch.")
        drawn_xy = net.longest_route_between_leaves(max_turn)

    sketch = _sketch_ranges(tcfg.get("finished"), getattr(net, "last_route_ranges", []),
                            drawn_xy, proj) if design.sketch_tol > 0 else []
    if sketch:
        log(f"  Sketched stretches: {sum(b - a for a, b in sketch) / 1000:.0f} km fitted within "
            f"{design.sketch_tol:.0f} m of the drawing")
    h, rev_s = fit_horizontal_pieces(drawn_xy, design, reversals, sketch_ranges=sketch)
    log(f"  Alignment: drawn {h.drawn_length / 1000:.2f} km -> fitted {h.length / 1000:.2f} km, "
        f"{len(h.curves)} curves" + (f", {len(rev_s)} reversal(s)" if rev_s else ""))
    rev_names = [n["name"] for n in (route_names or []) if isinstance(n, dict) and n.get("reverse")]

    # stations on the route, ordered by chainage
    on_route: List[StationInfo] = []
    for st in stations:
        x, y = proj.to_xy(st.lat, st.lon)
        ch, off, _ = project_point_to_polyline(float(x), float(y), h.xy, h.s)
        if st.name in reversing and st.name in rev_names:
            # a folded route passes near a stub station twice: it is served at the buffer
            ch = rev_s[rev_names.index(st.name)] if rev_names.index(st.name) < len(rev_s) else ch
            st.reverse = True
        if off <= tol or (st.name in snapped and off <= 2000.0):
            st.s, st.offset = ch, off
            on_route.append(st)
    on_route.sort(key=lambda s: s.s)
    # drop duplicates (same name within 50 m) e.g. a station drawn in two folders
    dedup: List[StationInfo] = []
    for st in on_route:
        if dedup and dedup[-1].name == st.name and abs(dedup[-1].s - st.s) < 50:
            continue
        dedup.append(st)
    on_route = dedup
    if route_names and len(route_names) > 2:
        n0 = route_names[0]["name"] if isinstance(route_names[0], dict) else route_names[0]
        n1 = route_names[-1]["name"] if isinstance(route_names[-1], dict) else route_names[-1]
        if n0 == n1:
            # loop service: the origin is served at both ends of the unrolled route
            ends = [st for st in on_route if st.name == n0]
            if ends:
                first = replace(ends[0], s=0.0)
                last = replace(ends[0], s=h.length)
                on_route = [first] + [st for st in on_route if st.name != n0] + [last]
    stops_cfg = svc.get("stops", "all")
    skip = set(svc.get("skip", []) or [])
    patterns = svc.get("patterns", {}) or {}  # e.g. {limited: [limited], express: [limited, express]}
    for k, st in enumerate(on_route):
        if isinstance(stops_cfg, str) and stops_cfg in patterns:
            # stopping pattern by station class; the two ends are always served
            st.stop = st.cls in patterns[stops_cfg] or k in (0, len(on_route) - 1)
        else:
            st.stop = stops_cfg == "all" or st.name in stops_cfg
        st.stop = (st.stop and st.name not in skip) or st.reverse  # a reversal is always a stop
    if on_route:
        on_route[0].cls = on_route[0].cls if on_route[0].cls != "standard" else "terminal"
        on_route[-1].cls = on_route[-1].cls if on_route[-1].cls != "standard" else "terminal"

    # a routed service starts and ends at its terminal stations, so every station within
    # tolerance of the routed track is on the service

    # ---- vertical profile
    pcfg = cfg.get("profile", {}) or {}
    sources = pcfg.get("sources", ["csv", "kmz", "usgs"])
    L = h.length
    ground = None
    for src in sources:
        try:
            if src == "csv" and pcfg.get("csv"):
                ground = _ground_fn(elev.from_csv(base_dir / pcfg["csv"], proj, h.xy, h.s, _grid(L)), L)
            elif src == "kmz":
                zlines = [ln for p in track_pms if p.has_z for ln in p.lines]
                if zlines:
                    ground = _ground_fn(elev.from_kmz_lines(zlines, proj, h.xy, h.s, _grid(L)), L)
            elif src == "terrain":
                cache = base_dir / pcfg.get("terrain_cache", "data/elevation_cache/terrarium")
                ground = _ground_fn(elev.from_terrain_tiles(
                    proj, h.xy, h.s, _grid(L), cache, zoom=int(pcfg.get("terrain_zoom", 13)),
                    progress=log), L)
            elif src == "usgs" and pcfg.get("usgs", False):
                cache = base_dir / pcfg.get("usgs_cache", "data/elevation_cache/epqs.json")
                ground = _ground_fn(elev.from_usgs(proj, h.xy, h.s, _grid(L), cache,
                                                   progress=log), L)
        except Exception as e:  # network errors, malformed files
            warnings.append(f"elevation source '{src}' failed: {e}")
            ground = None
        if ground is not None:
            log(f"  Elevation: using '{src}'")
            break
    structures = []
    pieces = getattr(net, "last_route_pieces", [])
    for z in pcfg.get("structures", []) or []:
        # e.g. {type: tunnel, from_station: A, to_station: B} for a covered way, or
        # {type: tunnel, match: "Covered"} for drawn segments whose name matches
        if z.get("match"):
            spans = _match_ranges(z["match"], pieces, h)
            if not spans:
                warnings.append(f"profile structure '{z['match']}' matched no drawn segment")
        else:
            spans = [_zone_chainage(z, on_route, proj, h)]
        structures += [(s0, s1, z.get("type", "viaduct")) for s0, s1 in spans]
    if ground is None:
        warnings.append("no elevation data: profile is FLAT. Provide profile.csv, a KMZ with "
                        "altitudes, or add 'terrain' / 'usgs' to profile.sources (needs internet).")
        prof = flat_profile(L, pdesign.grid)
        for s0, s1, kind in structures:
            m = (prof.s >= s0) & (prof.s <= s1)
            for i in np.nonzero(m)[0]:
                prof.structure[i] = kind
    else:
        prof = design_profile(L, ground, pdesign, stations=[s.s for s in on_route],
                              structures=structures)

    # ---- speed limits
    extra: List[Restriction] = []
    from .operations import turnout_speed
    for r in cfg.get("restrictions", []) or []:
        s0, s1 = _zone_chainage(r, on_route, proj, h)
        if "turnout" in r:  # diverging move through a turnout of this number / type
            v = turnout_speed(r["turnout"])
            reason = r.get("reason", f"turnout {r['turnout']}")
        else:
            v = speed_of(r, "speed")
            reason = r.get("reason", "posted")
        extra.append(Restriction(s0, s1, v, reason))
    st_cfg_all = cfg.get("stations", {}) or {}
    ta = cfg.get("terminal_approach")
    if ta and on_route:
        v = speed_of(ta, "speed")
        dist = float(length_of(ta, "distance", 300.0))
        for st in (on_route[0], on_route[-1]):
            if ta.get("stations") and st.name not in ta["stations"]:
                continue
            extra.append(Restriction(max(st.s - dist, 0), min(st.s + dist, L), v,
                                     f"terminal approach {st.name}"))
    # station throats for trains that stop: entry/exit turnouts onto the platform tracks
    # (stations.throat: {by_class: {cls: {speed_*, distance_m}}, terminal: {...}}); trains
    # that do not stop stay on the through tracks
    throat = st_cfg_all.get("throat") or {}
    stops_idx = [k for k, st in enumerate(on_route) if st.stop]
    for k in stops_idx:
        st = on_route[k]
        t = throat.get("terminal") if k in (stops_idx[0], stops_idx[-1]) else None
        t = t or (throat.get("by_class") or {}).get(st.cls)
        # one {speed, distance} or tiers, e.g. a hub's approach zone then its throat
        for tier in ([t] if isinstance(t, dict) else (t or [])):
            half = st.platform_length / 2
            d = float(length_of(tier, "distance", 500.0))
            extra.append(Restriction(max(st.s - half - d, 0.0), min(st.s + half + d, L),
                                     speed_of(tier, "speed"), f"{st.name} station throat"))
    # trains passing a platform without stopping: optional limit where people stand at the
    # platform edge (slipstream, track intrusion); platform screen doors lift it
    v_pass = speed_of(st_cfg_all, "pass_speed")
    if v_pass:
        for st in on_route:
            if not st.stop and not st.psd:
                half = st.platform_length / 2
                extra.append(Restriction(max(st.s - half, 0.0), min(st.s + half, L), v_pass,
                                         f"passing {st.name} platform"))
    sp = build_speed_profile(h, policy, extra)
    route = Route(cfg.get("name", kmz_path.stem), proj, h, prof, sp, on_route, warnings, drawn_xy)
    route.drawn_ranges = list(getattr(net, "last_route_ranges", []))
    route.sketch_ranges = list(sketch)
    sup = cfg.get("supply", {}) or {}
    route.supply_factor = float(sup.get("factor", 1.0))  # e.g. peak-hour voltage sag
    for z in sup.get("zones", []) or []:
        s0, s1 = _zone_chainage(z, on_route, proj, h)
        route.supply_zones.append((s0, s1, float(z["factor"])))
    # operating zones (e.g. CBTC/ATO trunk): by drawn segment name or between stations
    for k, oz in enumerate(cfg.get("operating_zones", []) or [], start=1):
        if oz.get("match"):
            route.zone_ranges += [(s0, s1, k) for s0, s1 in _match_ranges(oz["match"], pieces, h)]
        else:
            s0, s1 = _zone_chainage(oz, on_route, proj, h)
            route.zone_ranges.append((s0, s1, k))
        if not any(z[2] == k for z in route.zone_ranges):
            warnings.append(f"operating zone {oz.get('name', k)} matched nothing on this route")
    for z in cfg.get("neutral_sections", []) or []:
        z = dict(z)
        z.setdefault("length_m", 400.0)  # gap + announcement/end-sign coasting region
        s0, s1 = _zone_chainage(z, on_route, proj, h)
        route.neutral_sections.append((s0, s1))
    return route


def _grid(L, step=10.0):
    g = np.arange(0.0, L + step, step)
    g[-1] = L
    return g


def _ground_fn(values, L, step=10.0):
    if values is None:
        return None
    g = _grid(L, step)
    vals = np.asarray(values, dtype=float)
    return lambda s: np.interp(s, g, vals)


def _sketch_ranges(finished, ranges, xy, proj) -> List[Tuple[float, float]]:
    """Drawn-chainage intervals of the route that are sketches: every drawn segment except
    those listed as finished (`track.finished`: regex strings, or {match, bbox: [lat_min,
    lon_min, lat_max, lon_max]} for the finished part of a segment)."""
    rules = []
    for f in finished or []:
        f = {"match": f} if isinstance(f, str) else f
        rules.append((re.compile(f["match"], re.I), f.get("bbox")))
    s = cumulative_length(xy)
    lat, lon = proj.to_latlon(xy[:, 0], xy[:, 1])
    starts = np.array([a for _, a, _ in ranges]) if ranges else np.zeros(0)
    sk = np.ones(len(xy), dtype=bool)
    for i in range(len(xy)):
        k = int(np.searchsorted(starts, s[i], side="right")) - 1
        if k < 0:
            continue
        name = ranges[k][0] or ""
        for rx, bb in rules:
            if rx.search(name) and (bb is None or (bb[0] <= lat[i] <= bb[2] and bb[1] <= lon[i] <= bb[3])):
                sk[i] = False
                break
    out, i = [], 0
    while i < len(xy):
        if sk[i]:
            j = i
            while j + 1 < len(xy) and sk[j + 1]:
                j += 1
            out.append((float(s[i]), float(s[j])))
            i = j + 1
        else:
            i += 1
    return out


def _match_ranges(pattern: str, pieces, h) -> List[Tuple[float, float]]:
    """Chainage ranges of the route pieces drawn as segments whose name matches."""
    rx = re.compile(pattern, re.I)
    out = []
    for name, pa, pb in pieces:
        if rx.search(name or ""):
            ca = project_point_to_polyline(float(pa[0]), float(pa[1]), h.xy, h.s)[0]
            cb = project_point_to_polyline(float(pb[0]), float(pb[1]), h.xy, h.s)[0]
            out.append((min(ca, cb), max(ca, cb)))
    return out


def _zone_chainage(z: dict, stations: Sequence[StationInfo], proj, h) -> Tuple[float, float]:
    """Resolve a zone given as chainage, between two stations, or around a lat/lon point."""
    if "from_km" in z:
        return float(z["from_km"]) * 1000, float(z["to_km"]) * 1000
    if "from_station" in z:
        a = next(s.s for s in stations if s.name == z["from_station"])
        b = next(s.s for s in stations if s.name == z["to_station"])
        lo, hi = min(a, b), max(a, b)
        trim = float(z.get("inset_m", 0.0))
        return lo + trim, hi - trim
    if "at" in z:
        lat, lon = z["at"]
        x, y = proj.to_xy(lat, lon)
        ch, _, _ = project_point_to_polyline(float(x), float(y), h.xy, h.s)
        half = float(length_of(z, "length", 200.0)) / 2
        return max(ch - half, 0.0), min(ch + half, h.length)
    if "from" in z and "to" in z:
        pts = []
        for lat, lon in (z["from"], z["to"]):
            x, y = proj.to_xy(lat, lon)
            pts.append(project_point_to_polyline(float(x), float(y), h.xy, h.s)[0])
        return min(pts), max(pts)
    raise ValueError(f"cannot place zone {z}")
