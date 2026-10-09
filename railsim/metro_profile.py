"""Cincinnati Metro and RER vertical profiles: a port of the Rail Profiles page
(data/profile/profiles.html, from the Metro Profiles page profile_analyzer.html), so run
times use the designed rail profile.

Model (as in the page):
  * ground: the per-line long section (data/profile/lines/Line_*.json), map 3 (alternate
    2026) ground at 2 m chainage, in decimetres NAVD88; rivers at the Ohio normal pool;
  * rail: each station's 500 ft platform is level at its rail level; straight grades join
    platform ends and any bend points (PVIs);
  * station rail levels: the saved profile (data/profile/alignments/Line_*.json) where there
    is one, else the solver: each station as shallow as the grade limit allows (at most
    `defDepth` below ground), canon levels held, solved in both directions;
  * structure: painted overrides, else by rail vs ground: elevated, at grade, cut and cover
    (shallow station boxes, canal bed), shallow shield (running tunnels) or deep tube, with
    the canon sections for the founding Lines 1-6.

RER lines (data/profile/rer/lines/RER_*.json, the trunk core of each line) add a station
mode: 'under' (default on the drawn trunk) or 'surface' (at grade on the old railroad, rail
at ground, with bend points every `surfStep` that follow the smoothed ground between two
surface stations), and the canon RER-3 covered way and RER-5 deep bore.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

FT = 0.3048
TYPES = ("elevated", "atgrade", "cutcover", "shield", "deep")
# railsim structure names for each analyzer type (all three tunnel kinds use tunnel drag)
STRUCTURE = {"elevated": "viaduct", "atgrade": "at-grade", "cutcover": "cut-and-cover",
             "shield": "shield", "deep": "deep-tube"}
TUNNEL_STRUCTURES = {"tunnel", "cut-and-cover", "shield", "deep-tube"}

DEFAULTS = dict(maxGrade=50.0, platform=152.4, defDepth=7.62, elevAbove=3.0, coverBelow=3.0,
                deepBelow=18.29, shallowMax=12.19, envelope=5.5, clearMin=8.0, poolFt=455.0)
# RER starting values (not canon): 225 m platforms, 35 per mille, 12 m station rail depth,
# 25 m deep-bore threshold, 7 m envelope for 25 kV overhead, surface bend points every 250 m
RER_DEFAULTS = dict(maxGrade=35.0, platform=225.0, defDepth=12.0, elevAbove=3.0, coverBelow=3.0,
                    deepBelow=25.0, shallowMax=18.0, envelope=7.0, clearMin=9.0, poolFt=455.0,
                    surfStep=250.0)
SETTINGS_KEYS = {"surfaceBendPointSpacing_m": "surfStep", "maxGrade_permille": "maxGrade", "platform_m": "platform",
                 "defaultStationRailDepth_m": "defDepth", "elevatedWhenRailAboveGround_m": "elevAbove",
                 "coveredWhenRailBelowGround_m": "coverBelow",
                 "deepTubeOutsideCanonWhenDeeperThan_m": "deepBelow",
                 "flagCanonShallowDeeperThan_m": "shallowMax",
                 "structureHeightAboveRail_m": "envelope",
                 "minRailToRailClearanceAtCrossings_m": "clearMin", "ohioNormalPool_ft": "poolFt"}

# Canon structure for the founding sections (Lines 1-6 as first opened); later entries win.
# m: shallow = basin method (shallow shield tunnels, cut-and-cover station boxes); deep = deep
# tube; canal = cut-and-cover in the canal bed. aIn/bIn False leaves that end station out.
# fixed: station rail level relative to ground (m, + above).
CANON = {
    "Line_1": {"sections": [
        {"a": "University", "b": "Pennsylvania Station", "m": "shallow"},
        {"a": "Central Ave", "aIn": False, "b": "University", "m": "deep"}]},
    "Line_2": {"sections": [
        {"a": "Zoo", "b": "Roebling", "m": "shallow"},
        {"a": "McMicken", "aIn": False, "b": "VA Medical Center", "bIn": False, "m": "deep"}]},
    "Line_3": {"sections": [
        {"a": "St Bernard", "b": "Baltimore", "m": "shallow"},
        {"a": "St Bernard", "b": "Genesee", "m": "canal"}]},
    "Line_4": {"sections": [
        {"a": "Price Hill", "b": "Beecher", "m": "shallow"},
        {"a": "Price Hill", "b": "State", "bIn": False, "m": "deep"}],
        "fixed": {"Price Hill": -18.29, "State": 7.62, "Garrard": 7.62}},
    "Line_5": {"sections": [{"a": "Northside", "b": "Pennsylvania", "m": "shallow"}]},
    "Line_6": {"sections": [{"a": "UC Medical/Corryville", "b": "Public Landing", "m": "shallow"}]},
}
# RER canon: the RER-3 covered way (cut and cover under the embankment, end stations at grade)
# and the RER-5 1996 deep bore; Asbury back on the ground past the embankment.
RER_CANON = {
    "RER_3": {"sections": [{"a": "Sedamsville", "aIn": False, "b": "Riverbend/Belterra", "bIn": False,
                            "m": "covered"}],
              "modes": {"Asbury": "surface"}},
    "RER_5": {"sections": [{"a": "Norwood Central", "aIn": False, "b": "Ludlow", "bIn": False, "m": "deep"}]},
}


def load_settings(path: Optional[str | Path], rer: bool = False) -> dict:
    s = dict(RER_DEFAULTS if rer else DEFAULTS)
    if path and Path(path).exists():
        for k, v in json.loads(Path(path).read_text()).items():
            if k in SETTINGS_KEYS:
                s[SETTINGS_KEYS[k]] = float(v)
    return s


@dataclass
class MetroProfile:
    data: dict
    settings: dict
    st: List[float] = field(default_factory=list)  # station rail levels
    pvi: List[tuple] = field(default_factory=list)  # (chainage, rail level)
    ovr: List[tuple] = field(default_factory=list)  # (from, to, type)
    canon_secs: List[dict] = field(default_factory=list)
    canon_fixed: Dict[int, float] = field(default_factory=dict)
    canon_modes: Dict[int, str] = field(default_factory=dict)
    modes: List[str] = field(default_factory=list)  # RER station modes ('under' / 'surface')

    # ------------------------------------------------------------- loading
    @classmethod
    def load(cls, line_json, alignment_json=None, settings_json=None) -> "MetroProfile":
        data = json.loads(Path(line_json).read_text())
        p = cls(data, load_settings(settings_json, rer="RER" in data.get("system", "")))
        p._ground = np.array([np.nan if v is None else v / 10.0 for v in p.data["ground_dm"]])
        p._build_canon()
        doc = None
        if alignment_json and Path(alignment_json).exists():
            doc = json.loads(Path(alignment_json).read_text())
        p._align_from_doc(doc)
        return p

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def is_rer(self) -> bool:
        return "RER" in self.data.get("system", "")

    @property
    def stations(self) -> List[dict]:
        return self.data["stations"]

    @property
    def length(self) -> float:
        return float(self.data["length_m"])

    def pool(self) -> float:
        return self.settings["poolFt"] * FT

    def st_key(self, i: int) -> str:
        name = self.stations[i]["name"]
        dup = sum(1 for s in self.stations if s["name"] == name) > 1
        return f"{name}#{i}" if dup else name

    # ------------------------------------------------------------- ground
    def ground_at(self, c):
        g = self._ground
        step = float(self.data.get("step_m", 2.0))
        f = np.clip(np.asarray(c, dtype=float) / step, 0, len(g) - 1)
        i = np.floor(f).astype(int)
        t = f - i
        a = g[i]
        b = g[np.minimum(i + 1, len(g) - 1)]
        out = a + (b - a) * t
        out = np.where(np.isnan(a), b, np.where(np.isnan(b), a, out))
        return out

    def river_at(self, c: float) -> Optional[dict]:
        for r in self.data.get("rivers", []) or []:
            if r["c0"] <= c <= r["c1"]:
                return r
        return None

    def surface_at(self, c: float) -> float:
        return self.pool() if self.river_at(c) else float(self.ground_at(c))

    # ------------------------------------------------------------- canon
    def _build_canon(self):
        cn = (RER_CANON if self.is_rer else CANON).get(self.id, {})
        half = self.settings["platform"] / 2

        def idx(name):
            return next((i for i, s in enumerate(self.stations) if s["name"] == name), -1)

        self.canon_secs = []
        for sec in cn.get("sections", []):
            ia, ib = idx(sec["a"]), idx(sec["b"])
            if ia < 0 or ib < 0:
                continue
            A, B = self.stations[ia], self.stations[ib]
            d = math.copysign(1, B["c"] - A["c"]) if B["c"] != A["c"] else 1
            ca = A["c"] + (d * half if sec.get("aIn") is False else -d * half)
            cb = B["c"] + (-d * half if sec.get("bIn") is False else d * half)
            self.canon_secs.append({**sec, "lo": min(ca, cb), "hi": max(ca, cb)})
        self.canon_fixed = {idx(n): off for n, off in cn.get("fixed", {}).items() if idx(n) >= 0}
        self.canon_modes = {idx(n): m for n, m in cn.get("modes", {}).items() if idx(n) >= 0}

    def default_mode(self, i: int) -> str:
        if i in self.canon_modes:
            return self.canon_modes[i]
        return "under" if self.stations[i].get("trunk") else "surface"

    def canon_at(self, c: float) -> Optional[dict]:
        for sec in reversed(self.canon_secs):
            if sec["lo"] <= c <= sec["hi"]:
                return sec
        return None

    # ------------------------------------------------------------- alignment
    def default_align(self, modes: Optional[List[str]] = None) -> List[float]:
        """Each station as shallow as the grade limit allows (<= defDepth under ground),
        canon levels held, solved both ways so steep descents go deeper. RER surface stations
        sit at ground."""
        g, P = self.settings["maxGrade"] / 1000.0, self.settings["platform"]
        n = len(self.stations)
        md = ([modes[i] if modes and modes[i] else self.default_mode(i) for i in range(n)]
              if self.is_rer else None)
        ub, lb = [], []
        for i, s in enumerate(self.stations):
            gr = float(self.ground_at(s["c"]))
            if i in self.canon_fixed and math.isfinite(gr):
                ub.append(gr + self.canon_fixed[i])
                lb.append(gr + self.canon_fixed[i])
            elif md and md[i] == "surface" and math.isfinite(gr):
                ub.append(gr)
                lb.append(gr)
            else:
                ub.append(gr - self.settings["defDepth"] if math.isfinite(gr) else math.inf)
                lb.append(-math.inf)

        def run(i, j):
            return max(0.0, abs(self.stations[j]["c"] - self.stations[i]["c"]) - P * abs(j - i))

        z = [min(ub[j] + g * run(i, j) for j in range(n)) for i in range(n)]
        for i in range(n):
            lo = max((lb[j] - g * run(i, j) for j in range(n) if math.isfinite(lb[j])), default=-math.inf)
            z[i] = max(z[i], lo)
            if not math.isfinite(z[i]):
                z[i] = 0.0
        st = [_js_round(v * 100) / 100 for v in z]
        self.modes = md or []
        self.pvi = self.surface_pvis(st, md) if md else []
        return st

    def surface_pvis(self, st: List[float], md: List[str]) -> List[tuple]:
        """Between two at-grade stations the rail follows the old railroad: bend points every
        surfStep on the ground smoothed over two steps, held to the grade limit both ways."""
        half, step = self.settings["platform"] / 2, self.settings["surfStep"]
        g, L, S = self.settings["maxGrade"] / 1000.0, self.length, self.stations
        n = len(S)

        def smooth(c):
            vals = [self.surface_at(min(max(c + d, 0.0), L)) for d in np.arange(-step, step + 1e-9, step / 4)]
            vals = [v for v in vals if math.isfinite(v)]
            return sum(vals) / len(vals) if vals else math.nan

        runs = []
        if n and md[0] == "surface":
            runs.append((0.0, S[0]["c"] - half - 2, None, st[0]))
        for i in range(n - 1):
            if md[i] == "surface" and md[i + 1] == "surface":
                runs.append((S[i]["c"] + half + 2, S[i + 1]["c"] - half - 2, st[i], st[i + 1]))
        if n and md[n - 1] == "surface":
            runs.append((S[n - 1]["c"] + half + 2, L, st[n - 1], None))
        out = []
        for a, b, za, zb in runs:
            if b - a < step * 1.5:
                continue
            k = math.floor((b - a) / step)
            pts = []
            for j in range(1, k):
                c = a + (b - a) * j / k
                z = smooth(c)
                if math.isfinite(z):
                    pts.append([float(_js_round(c)), z, False])
            if not pts:
                continue
            chain = [[a, za if za is not None else pts[0][1], za is not None], *pts,
                     [b, zb if zb is not None else pts[-1][1], zb is not None]]
            for _ in range(4):
                for j in range(1, len(chain)):
                    if not chain[j][2]:
                        d = g * (chain[j][0] - chain[j - 1][0])
                        chain[j][1] = min(max(chain[j][1], chain[j - 1][1] - d), chain[j - 1][1] + d)
                for j in range(len(chain) - 2, -1, -1):
                    if not chain[j][2]:
                        d = g * (chain[j + 1][0] - chain[j][0])
                        chain[j][1] = min(max(chain[j][1], chain[j + 1][1] - d), chain[j + 1][1] + d)
            out += [(c, _js_round(z * 100) / 100) for c, z, _ in pts]
        return sorted(out)

    def _align_from_doc(self, doc: Optional[dict]):
        modes = None
        if doc and doc.get("mode") and self.is_rer:
            dm = doc["mode"]
            modes = [dm.get(self.st_key(i)) if dm.get(self.st_key(i)) in ("surface", "under")
                     else self.default_mode(i) for i in range(len(self.stations))]
        self.st = self.default_align(modes)
        self.ovr = []
        if not doc:
            return
        by_key = doc.get("st") or {}
        for i in range(len(self.stations)):
            k = self.st_key(i)
            if isinstance(by_key.get(k), (int, float)):
                self.st[i] = float(by_key[k])
        if isinstance(doc.get("pvi"), list):
            self.pvi = [(float(p[0]), float(p[1])) for p in doc["pvi"] if len(p) >= 2]
        for o in doc.get("ovr") or []:
            if len(o) >= 3:
                t = "shield" if o[2] == "bored" else o[2]
                if t in TYPES:
                    self.ovr.append((float(o[0]), float(o[1]), t))

    # ------------------------------------------------------------- rail profile
    def vertices(self):
        half, L = self.settings["platform"] / 2, self.length
        v = []
        for i, s in enumerate(self.stations):
            z = self.st[i]
            v.append((min(max(s["c"] - half, 0.0), L), z, 1))  # platform start
            v.append((min(max(s["c"] + half, 0.0), L), z, 0))  # platform end sorts first on ties
        v += [(c, z, 2) for c, z in self.pvi]
        v.sort(key=lambda t: (t[0], t[2]))
        if not v:
            return np.array([0.0, L]), np.array([0.0, 0.0])
        if v[0][0] > 0:
            v.insert(0, (0.0, v[0][1], 0))
        if v[-1][0] < L:
            v.append((L, v[-1][1], 0))
        return np.array([t[0] for t in v]), np.array([t[1] for t in v])

    def rail_at(self, c):
        vc, vz = self.vertices()
        return np.interp(c, vc, vz)

    def override_at(self, c: float) -> Optional[str]:
        for a, b, t in reversed(self.ovr):
            if a <= c <= b:
                return t
        return None

    def in_station(self, c: float) -> bool:
        half = self.settings["platform"] / 2
        return any(abs(c - s["c"]) <= half for s in self.stations)

    def auto_type(self, c: float, z: float) -> str:
        sec0 = self.canon_at(c)
        if sec0 and sec0["m"] == "covered":
            s0 = self.surface_at(c)
            return "elevated" if math.isfinite(s0) and z - s0 >= self.settings["elevAbove"] else "cutcover"
        if self.river_at(c):
            return "elevated" if z >= self.pool() + 1 else "deep"
        g = float(self.ground_at(c))
        if not math.isfinite(g):
            return "atgrade"
        if z - g >= self.settings["elevAbove"]:
            return "elevated"
        d = g - z
        if d < self.settings["coverBelow"]:
            return "atgrade"
        sec = self.canon_at(c)
        m = sec["m"] if sec else ("deep" if d >= self.settings["deepBelow"] else "shallow")
        if m == "canal":
            return "cutcover"
        if m == "deep":
            return "deep"
        return "cutcover" if self.in_station(c) else "shield"

    def type_at(self, c: float, z: Optional[float] = None) -> str:
        if z is None:
            z = float(self.rail_at(c))
        return self.override_at(c) or self.auto_type(c, z)

    # ------------------------------------------------------------- checks
    def summary(self, dc: float = 10.0) -> dict:
        L = self.length
        km = {t: 0.0 for t in TYPES}
        for c in np.arange(0.0, L, dc):
            cm = min(L, c + dc / 2)
            km[self.type_at(cm)] += float(min(dc, L - c)) / 1000.0
        vc, vz = self.vertices()
        dcs = np.diff(vc)
        ok = dcs > 1e-6
        g = np.zeros_like(dcs)
        g[ok] = np.diff(vz)[ok] / dcs[ok] * 1000.0
        over = int(np.sum(np.abs(g) > self.settings["maxGrade"] + 0.05))
        return {"km_by_type": {k: round(v, 3) for k, v in km.items()},
                "max_grade_permille": round(float(g[np.argmax(np.abs(g))]) if len(g) else 0.0, 1),
                "grades_over_limit": over}


def _js_round(v: float) -> float:
    """JavaScript Math.round (halves up), so the port matches the page."""
    return math.floor(v + 0.5)


def route_profile(mp: MetroProfile, proj, h, grid: float = 5.0):
    """railsim Profile on the fitted alignment `h`: each grid point is projected onto the
    analyzer's drawn path to find its analyzer chainage."""
    from .geo import cumulative_length, project_point_to_polyline
    from .profile import Profile
    path = mp.data["path"]
    pc = np.array([p[0] for p in path], float)
    pxy = np.array([proj.to_xy(p[2], p[1]) for p in path], float)
    ps = cumulative_length(pxy)
    L = h.length
    s = np.arange(0.0, L + grid, grid)
    s[-1] = L
    x = np.interp(s, h.s, h.xy[:, 0])
    y = np.interp(s, h.s, h.xy[:, 1])
    c = np.empty(len(s))
    for i in range(len(s)):
        ch, _, _ = project_point_to_polyline(float(x[i]), float(y[i]), pxy, ps)
        c[i] = np.interp(ch, ps, pc)  # drawn-path length -> analyzer chainage
    z = mp.rail_at(c)
    ground = np.array([mp.surface_at(ci) for ci in c])
    structure = [STRUCTURE[mp.type_at(ci, zi)] for ci, zi in zip(c, z)]
    grade = np.gradient(z, s) if len(s) > 1 else np.zeros_like(s)
    return Profile(s, ground, z, grade, structure, has_ground_data=True)


def overlay_profile(prof, mp: MetroProfile, proj, h, grid: float = 5.0, tol: float = 30.0,
                    taper: float = 400.0):
    """The designed profile of a line core (RER) laid over a route's ground-fitted profile
    `prof`: inside the core (route points within `tol` of the analyzer path) the rail, ground
    and structure come from the design; outside, the difference to the ground-fitted rail
    tapers to zero over `taper` metres so the grades join."""
    from .geo import cumulative_length, project_point_to_polyline
    from .profile import Profile
    path = mp.data["path"]
    pc = np.array([p[0] for p in path], float)
    pxy = np.array([proj.to_xy(p[2], p[1]) for p in path], float)
    ps = cumulative_length(pxy)
    L = h.length
    s = np.arange(0.0, L + grid, grid)
    s[-1] = L
    x = np.interp(s, h.s, h.xy[:, 0])
    y = np.interp(s, h.s, h.xy[:, 1])
    z = prof.elevation_at(s)
    ground = np.interp(s, prof.s, prof.ground)
    sidx = np.clip(np.searchsorted(prof.s, s), 0, len(prof.structure) - 1)
    structure = [prof.structure[i] for i in sidx]
    lo, hi = pxy.min(axis=0) - tol, pxy.max(axis=0) + tol
    inside = np.zeros(len(s), bool)
    c = np.zeros(len(s))
    for i in np.nonzero((x >= lo[0]) & (x <= hi[0]) & (y >= lo[1]) & (y <= hi[1]))[0]:
        ch, off, _ = project_point_to_polyline(float(x[i]), float(y[i]), pxy, ps)
        ci = float(np.interp(ch, ps, pc))
        if off <= tol and 1.0 < ci < mp.length - 1.0:
            inside[i], c[i] = True, ci
    if not inside.any():
        return prof, 0.0
    za = mp.rail_at(c[inside])
    delta = np.zeros(len(s))
    delta[inside] = za - z[inside]
    for i, ci, zi in zip(np.nonzero(inside)[0], c[inside], za):
        ground[i] = mp.surface_at(ci)
        structure[i] = STRUCTURE[mp.type_at(ci, zi)]
    # taper the step at each edge of the core
    idx = np.nonzero(inside)[0]
    out = np.nonzero(~inside)[0]
    if len(out):
        near = idx[np.clip(np.searchsorted(idx, out), 0, len(idx) - 1)]
        prev = idx[np.clip(np.searchsorted(idx, out) - 1, 0, len(idx) - 1)]
        k = np.where(np.abs(s[prev] - s[out]) < np.abs(s[near] - s[out]), prev, near)
        w = np.clip(1.0 - np.abs(s[out] - s[k]) / taper, 0.0, 1.0)
        delta[out] = delta[k] * w
    track = z + delta
    grade = np.gradient(track, s)
    return Profile(s, ground, track, grade, structure, has_ground_data=prof.has_ground_data), \
        float(inside.mean())
