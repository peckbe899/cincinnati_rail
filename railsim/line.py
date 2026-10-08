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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import elevation as elev
from .dynamics import TrackData
from .geo import FT, INCH, KMH, MPH, LocalProjection, project_point_to_polyline
from .horizontal import CurveDesign, HorizontalAlignment, fit_horizontal
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
        return TrackData(ds, s, lim, z, curv, tunnel)

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
    if folder:
        for p in select(placemarks, folder):
            for (lat, lon, _z) in p.points:
                out.append(StationInfo(p.name, lat, lon))
    for item in st_cfg.get("list", []) or []:
        out.append(StationInfo(item["name"], float(item["lat"]), float(item["lon"])))
    info = st_cfg.get("info", {}) or {}
    defaults = st_cfg.get("defaults", {}) or {}
    for s in out:
        d = dict(defaults)
        d.update(info.get(s.name, {}) or {})
        s.cls = d.get("class", s.cls)
        s.platform = d.get("platform", s.platform)
        s.platform_length = float(length_of(d, "platform_length", s.platform_length))
        s.dwell_override = d.get("dwell_s")
        s.early_departure = bool(d.get("early_departure", False))
    return out


def build_route(cfg: dict, base_dir: Path, design: CurveDesign, policy: SpeedPolicy,
                pdesign: ProfileDesign, log=print) -> Route:
    kmz_path = (base_dir / cfg["kmz"]).resolve()
    placemarks = read_kmz(kmz_path)
    tcfg = cfg.get("track", {}) or {}
    track_pms = select(placemarks, tcfg.get("folder"), tcfg.get("name_regex"))
    excl = tcfg.get("exclude", []) or []
    track_pms = [p for p in track_pms if p.lines and p.name not in excl]
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
        return best[:2]

    if route_names:
        stops = [locate_name(n) for n in route_names]
        drawn_xy, _ = net.route(stops, max_turn)
    else:
        if not net.is_simple_path():
            warnings.append("track network branches; routing between the farthest dead ends. "
                            "Set service.route to choose a branch.")
        drawn_xy = net.longest_route_between_leaves(max_turn)

    h = fit_horizontal(drawn_xy, design)
    log(f"  Alignment: drawn {h.drawn_length / 1000:.2f} km -> fitted {h.length / 1000:.2f} km, "
        f"{len(h.curves)} curves")

    # stations on the route, ordered by chainage
    on_route: List[StationInfo] = []
    for st in stations:
        x, y = proj.to_xy(st.lat, st.lon)
        ch, off, _ = project_point_to_polyline(float(x), float(y), h.xy, h.s)
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
    stops_cfg = svc.get("stops", "all")
    skip = set(svc.get("skip", []) or [])
    for st in on_route:
        st.stop = (stops_cfg == "all" or st.name in stops_cfg) and st.name not in skip
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
    for z in pcfg.get("structures", []) or []:
        s0, s1 = _zone_chainage(z, on_route, proj, h)
        structures.append((s0, s1, z.get("type", "viaduct")))
    if ground is None:
        warnings.append("no elevation data: profile is FLAT. Provide profile.csv, a KMZ with "
                        "altitudes, or set profile.usgs: true (needs internet).")
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
    for r in cfg.get("restrictions", []) or []:
        s0, s1 = _zone_chainage(r, on_route, proj, h)
        extra.append(Restriction(s0, s1, speed_of(r, "speed"), r.get("reason", "posted")))
    ta = cfg.get("terminal_approach")
    if ta and on_route:
        v = speed_of(ta, "speed")
        dist = float(length_of(ta, "distance", 300.0))
        for st in (on_route[0], on_route[-1]):
            if ta.get("stations") and st.name not in ta["stations"]:
                continue
            extra.append(Restriction(max(st.s - dist, 0), min(st.s + dist, L), v,
                                     f"terminal approach {st.name}"))
    for st in on_route:  # per-station platform speed (e.g. stations with crossings)
        pass
    sp = build_speed_profile(h, policy, extra)
    return Route(cfg.get("name", kmz_path.stem), proj, h, prof, sp, on_route, warnings, drawn_xy)


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
