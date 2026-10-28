"""Cincinnati Metro and RER vertical profiles: a port of the Rail Profiles page
(data/profile/profiles.html, from the Metro Profiles page profile_analyzer.html), so run
times use the designed rail profile.

Model (as in the page):
  * ground: the per-line long section (data/profile/lines/Line_*.json), map 3 (alternate
    2026) ground at 2 m chainage, in decimetres NAVD88; rivers at the Ohio normal pool;
  * rail: each station's 400 ft platform (670 ft on the RER) is level at its rail level;
    straight grades join platform ends and any bend points (PVIs);
  * station rail levels: the saved profile (data/profile/alignments/Line_*.json) where there
    is one, else the solver: each station as shallow as the grade limit allows (at most
    `defDepth` below ground), canon levels held, solved in both directions;
  * structure: painted overrides, else by rail vs ground: elevated, at grade, cut and cover
    (shallow station boxes, canal bed), shallow shield (running tunnels) or deep tube, with
    the canon sections for the founding Lines 1-6.
  * ground, in three layers as on the page: the surveyed raster; the Mill Creek Deck's street
    re-grades and open cuts at CUT and Norwood Central on top (data/profile/context/lines.json,
    the ground the solver uses); and over painted cut and cover the ground filled to the box
    roof plus cover, sloping back past the ends (the ground structure and cover are judged on).
  * context (data/profile/context/lines.json): the other systems' structures at CUT and Norwood
    Central (the lower level and its pairs, the intercity and C&O pairs, the APEx arch viaducts,
    the Norwood surface tracks and trench) as chainage blocks with their rail level, checked
    for clearance with the crossing rule (context_clearances()).

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
TYPES = ("elevated", "atgrade", "trough", "cutcover", "shield", "deep")
# railsim structure names for each analyzer type (all three tunnel kinds use tunnel drag)
STRUCTURE = {"elevated": "viaduct", "atgrade": "at-grade", "trough": "cut", "cutcover": "cut-and-cover",
             "shield": "shield", "deep": "deep-tube"}
TUNNEL_STRUCTURES = {"tunnel", "cut-and-cover", "shield", "deep-tube"}

# Platforms 400 ft (Ben, 23 October 2026: 6 cars of about 67 ft or 8 of about 50 ft; was 500 ft)
DEFAULTS = dict(maxGrade=50.0, platform=121.92, defDepth=7.62, elevAbove=3.0, coverBelow=3.0,
                deepBelow=18.29, shallowMax=12.19, poolFt=455.0, deckDepth=1.5,
                vcRadius=1500.0, vcMinLen=30.5, minCover=2.0, fillTaper=50.0)
# Metro structures (Ben's rules), from the top of rail: below = rail to underside, top = rail to
# top, od = outside diameter. Cut-and-cover box (and station box) 1.0 below / 4.6 to top; twin
# tube (4.4 m inside, 4.76 m outside, rail 0.5 m above invert) 0.68 / 4.08 for deep tube on every
# line, shield on Lines 1-7 and every river crossing; double-track bore (9.0 m outside) 3.2 / 5.8
# for shield on Lines 8-14. Cover over the top: tube or bore with its top above 140.0 m (basin
# water table) 2.0 m, at or below it one outside diameter; box roof 0.6 m. Shallower than that
# is built cut and cover.
METRO_ST = {"box": {"k": "box", "below": 1.0, "top": 4.6},
            "tube": {"k": "tube", "below": 0.68, "top": 4.08, "od": 4.76},
            "bore": {"k": "bore", "below": 3.2, "top": 5.8, "od": 9.0}}
WATER_TABLE, TUBE_COVER_HIGH, BOX_COVER = 140.0, 2.0, 0.6
# rivers: rail at most bed (ground raster) - margin at every chainage of a river range, in tunnel
# (Metro twin tube: 1.0 scour + 2.38 half-diameter cover + 4.08 rail to top; RER sunk box section
# in a dredged trench, Transbay model: 1.0 scour + 1.5 backfill + 6.6 rail to top)
RIVER_MARGIN = {"metro": 7.5, "rer": 9.1}
# Platform curvature (Ben): extra platform gap for the 15.56 m car on a curve of radius R, outside
# face 15.56^2 / 8R, inside face (end doors about 5.4 m from the car centre) 5.4^2 / 2R; R under
# 600 m (outside gap over 5 cm) is an error unless a named gap-filler exception, under 3,000 m a
# warning
CAR_LEN, END_DOOR, PLAT_R_ERR, PLAT_R_WARN = 15.56, 5.4, 600.0, 3000.0
# Drawing checks (Ben): a finished curve is drawn as a run of vertices each turning a little.
# single-angle corner: one vertex turning >= 5 deg with no same-way turn >= 2 deg beside it
# (WARNING); join kink: >= 10 deg beside a segment < 10 m (ERROR); doubling back: > 90 deg (ERROR);
# S-curve platform: turns both ways inside the span, >= 5 deg each way ERROR, >= 2 deg WARNING
DRAW = {"single": 5.0, "nb": 2.0, "kink": 10.0, "kinkSeg": 10.0, "back": 90.0, "sErr": 5.0, "sWarn": 2.0}


def fit_radius(pts: np.ndarray) -> float:
    """Least-squares (algebraic) circle radius through points; infinite when straight within 1 mm."""
    if len(pts) < 3:
        return math.inf
    P = pts - pts.mean(axis=0)
    a, b = P[0], P[-1]
    L = float(np.hypot(*(b - a))) or 1.0
    dev = np.abs((b[0] - a[0]) * (a[1] - P[:, 1]) - (a[0] - P[:, 0]) * (b[1] - a[1])) / L
    if dev.max() < 0.001:
        return math.inf
    z = (P ** 2).sum(axis=1)
    A = np.column_stack([P[:, 0], P[:, 1], np.ones(len(P))])
    (D, E, F), *_ = np.linalg.lstsq(A, -z, rcond=None)
    r2 = (D * D + E * E) / 4 - F
    return math.sqrt(r2) if r2 > 0 else math.inf
ERA = {**{f"Line_{k}": {"shield": "tube"} for k in ("1", "2", "2b", "3", "4", "5", "6", "7")},
       **{f"Line_{k}": {"shield": "bore"} for k in ("8", "9", "10", "11", "12", "13", "14")},
       "CVG_Express": {"shield": "bore"}}  # opening year not yet set: as Lines 8-14 for now
# RER: 35 per mille, 670 ft (204.2 m) platforms (Ben, 5 October 2026) and 12 m station rail depth are canon; the
# 25 m deep-bore threshold, 6.6 m box / 7.5 m bored crown (RATP RER style), 3 m tube cover and 250 m surface
# bend points are starting values
RER_DEFAULTS = dict(maxGrade=35.0, platform=204.2, defDepth=12.0, elevAbove=3.0, coverBelow=3.0,
                    deepBelow=25.0, shallowMax=18.0, envelope=6.6, boreCrown=7.5, invertDepth=1.0, poolFt=455.0,
                    surfStep=250.0, tubeCover=3.0, vcRadius=3000.0, vcMinLen=30.5, minCover=8.5, deckDepth=2.0,
                    fillTaper=50.0)
RER_CANON_JSON = Path(__file__).resolve().parent.parent / "data" / "profile" / "rer" / "canon.json"
CONTEXT_JSON = Path(__file__).resolve().parent.parent / "data" / "profile" / "context" / "lines.json"
# a line in the open under another structure needs this clear height from rail to its underside
# (Ben): Metro 4.2 m, RER 5.8 m (25 kV); track bed 0.8 m below the rail; crossing gap 0.5 m
OPEN_CLEAR = {"metro": 4.2, "rer": 5.8}
BED_DEPTH, SEP_GAP = 0.8, 0.5


def _rer_canon_rivers() -> dict:
    """River entries of the canon (bed depths where there is no survey), for Metro lines too."""
    try:
        return json.loads(RER_CANON_JSON.read_text()).get("rivers") or {}
    except (OSError, ValueError):
        return {}
SETTINGS_KEYS = {"surfaceBendPointSpacing_m": "surfStep", "tubeCover_m": "tubeCover",
                 "verticalCurveRadius_m": "vcRadius", "minBoredCover_m": "minCover",
                 "boredTubeCrownAboveRail_m": "boreCrown", "maxGrade_permille": "maxGrade", "platform_m": "platform",
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
    # CVG Express (1969, Ben Oct 16): Union Terminal at platform M on the CUT platform deck (arch
    # viaduct), level with the APEx field, 160.3 m (Deck; log 10l.19, 10l.24; Ben, 26 October); the
    # Ohio on a bridge (navigation clearance 77.3 ft above normal pool as the Brent Spence, starting value)
    "CVG_Express": {"fixed": {"Union Terminal": {"abs": 160.3}},
                    "bridges": {"Ohio River": {"clear": 23.56}}},
    "Line_6": {"sections": [{"a": "UC Medical/Corryville", "b": "Public Landing", "m": "shallow"}]},
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
    st: List[float] = field(default_factory=list)  # station rail levels (platform centre)
    sg: List[float] = field(default_factory=list)  # platform grades, per mille rising with chainage
    pvi: List[tuple] = field(default_factory=list)  # (chainage, rail level)
    ovr: List[tuple] = field(default_factory=list)  # (from, to, type)
    canon_secs: List[dict] = field(default_factory=list)
    canon_fixed: Dict[int, dict] = field(default_factory=dict)  # {abs | off, ref}
    canon_modes: Dict[int, str] = field(default_factory=dict)
    canon_deck: List[dict] = field(default_factory=list)
    rer_canon: dict = field(default_factory=dict)
    modes: List[str] = field(default_factory=list)  # RER station modes ('under' / 'surface')

    # ------------------------------------------------------------- loading
    @classmethod
    def load(cls, line_json, alignment_json=None, settings_json=None,
             canon_json=None, settings_override: Optional[dict] = None, context_json=None) -> "MetroProfile":
        data = json.loads(Path(line_json).read_text())
        rer = "RER" in data.get("system", "")
        # per-line settings in the line file (e.g. the CVG Express's 200 m platforms)
        p = cls(data, {**load_settings(settings_json, rer=rer), **(data.get("settings") or {}), **(settings_override or {})})
        if rer:
            cj = Path(canon_json) if canon_json else RER_CANON_JSON
            p.rer_canon = json.loads(cj.read_text()) if cj.exists() else {}
        p._ground = np.array([np.nan if v is None else v / 10.0 for v in p.data["ground_dm"]])
        cx = Path(context_json) if context_json else CONTEXT_JSON
        try:
            p.ctx = (json.loads(cx.read_text()).get("lines") or {}).get(p.data["id"], {}) if cx.exists() else {}
        except ValueError:
            p.ctx = {}
        # every drawn station keeps its point (c0) and its index in the line file (idx);
        # data["stations"] becomes the working list (removed ones out, platforms slid)
        p.all_stations = [dict(st, idx=i, c0=st["c"]) for i, st in enumerate(p.data["stations"])]
        p.data["stations"] = list(p.all_stations)
        p.removed, p.so = [], []
        p._build_canon()
        p._apply_deck()
        p._ground_dem = p._ground.copy()   # surveyed (with any canon deck)
        p._apply_regrade()                 # + the Deck's street re-grades and cuts: the solver's ground
        p._ground0 = p._ground.copy()
        doc = None
        if alignment_json and Path(alignment_json).exists():
            doc = json.loads(Path(alignment_json).read_text())
        p._align_from_doc(doc)
        p.refresh_fill()
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

    def key_of(self, st: dict) -> str:
        name = st["name"]
        dup = sum(1 for s in self.all_stations if s["name"] == name) > 1
        return f"{name}#{st['idx']}" if dup else name

    def st_key(self, i: int) -> str:
        return self.key_of(self.stations[i])

    # ------------------------------------------------------------- ground
    def ground_at(self, c):
        """Finished ground: surveyed + Deck re-grades + fill over painted cut and cover."""
        return self._sample(self._ground, c)

    def ground0_at(self, c):
        """The ground the level solver uses: surveyed + Deck re-grades (no painted fill)."""
        return self._sample(getattr(self, "_ground0", self._ground), c)

    def ground_dem_at(self, c):
        """The surveyed ground (the raster, with any canon deck)."""
        return self._sample(getattr(self, "_ground_dem", self._ground), c)

    def _sample(self, g, c):
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

    def surface0_at(self, c: float) -> float:
        return self.pool() if self.river_at(c) else float(self.ground0_at(c))

    def _apply_regrade(self):
        """The Deck's street re-grades (added) and open cuts (ground held at the trough floor),
        from the context file's ground runs (indices into the 2 m ground array)."""
        g = self._ground
        for r in self.ctx.get("add") or []:
            for k, v in enumerate(r["v"]):
                i = r["i0"] + k
                if i < len(g) and np.isfinite(g[i]):
                    g[i] += v
        for r in self.ctx.get("cap") or []:
            for k, v in enumerate(r["v"]):
                i = r["i0"] + k
                if i < len(g) and np.isfinite(g[i]) and v < g[i]:
                    g[i] = v

    def refresh_fill(self):
        """Painted cut and cover (Ben, 26 October): the box keeps its level and the ground is
        regraded over it, at least the box roof plus its cover (Metro 4.6 + 0.6 m above the rail;
        RER the box height), sloping back to the solver's ground at fillTaper per mille past the
        ends. Fill only. Call again after changing st, pvi or ovr."""
        g0 = getattr(self, "_ground0", self._ground)
        cc = [(a, b) for a, b, t in self.ovr if t == "cutcover"]
        if not cc:
            self._ground = g0.copy()
            return
        step = float(self.data.get("step_m", 2.0))
        n = len(g0)
        t = np.full(n, -np.inf)
        for a, b in cc:
            i0, i1 = max(0, math.ceil(a / step)), min(n - 1, math.floor(b / step))
            for i in range(i0, i1 + 1):
                c = i * step
                if self.river_at(c):
                    continue
                sc = self.struct_for("cutcover", c)
                t[i] = max(t[i], float(self.rail_at(c)) + sc["top"] + self.req_cover(sc, 0.0))
        drop = float(self.settings.get("fillTaper", 50.0)) / 1000.0 * step
        for i in range(1, n):
            t[i] = max(t[i], t[i - 1] - drop)
        for i in range(n - 2, -1, -1):
            t[i] = max(t[i], t[i + 1] - drop)
        river = np.array([bool(self.river_at(i * step)) for i in range(n)]) if self.data.get("rivers") else np.zeros(n, bool)
        g = g0.copy()
        m = np.isfinite(g0) & (t > g0 + 0.005) & ~river
        g[m] = t[m]
        self._ground = g

    # ------------------------------------------------------------- canon
    def _build_canon(self):
        cn = ((self.rer_canon.get("lines") or {}) if self.is_rer else CANON).get(self.id, {})
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
        self.canon_fixed = {idx(n): (f if isinstance(f, dict) else {"off": f})
                            for n, f in cn.get("fixed", {}).items() if idx(n) >= 0}
        self.canon_modes = {idx(n): (m["mode"] if isinstance(m, dict) else m)
                            for n, m in cn.get("modes", {}).items() if idx(n) >= 0}
        self.canon_deck = []
        for dk in cn.get("deck", []) or []:
            ia, ib = idx(dk["a"]), idx(dk["b"])
            if ia >= 0 and ib >= 0:
                A, B = self.stations[ia]["c"], self.stations[ib]["c"]
                self.canon_deck.append({**dk, "lo": min(A, B) - half, "hi": max(A, B) + half})

    def _apply_deck(self):
        """Under a deck the raster holds the deck top; the rail runs at yard level."""
        step = float(self.data.get("step_m", 2.0))
        for dk in self.canon_deck:
            i0 = max(0, math.ceil(dk["lo"] / step))
            i1 = min(len(self._ground) - 1, math.floor(dk["hi"] / step))
            self._ground[i0:i1 + 1] -= dk["drop"]

    def ref_at(self, i: int) -> float:
        """Level a station's depth is measured from (canon reference, e.g. track level)."""
        f = self.canon_fixed.get(i)
        return f["ref"] if f and f.get("ref") is not None else self.surface_at(self.stations[i]["c"])

    def _rivers_info(self) -> dict:
        return (self.rer_canon.get("rivers") if self.rer_canon else None) or _rer_canon_rivers()

    def bed_at(self, c: float) -> float:
        """River bed: the canon riverbed in the ground raster, else pool minus the canon bed depth
        where there is no survey (Little Miami)."""
        r = self.river_at(c)
        if r:
            b = self._rivers_info().get(r["name"], {}).get("bed_below_pool_m")
            if b is not None:
                return self.pool() - float(b)
        return float(self.ground_at(c))

    def _bridge(self, r: dict) -> Optional[dict]:
        return None if self.is_rer else (CANON.get(self.id, {}).get("bridges") or {}).get(r["name"])

    def river_bridges(self) -> List[dict]:
        """River crossings on a bridge: rail at least pool + navigation clearance + deck."""
        out = []
        for r in self.data.get("rivers", []) or []:
            if self._bridge(r):
                lb = self.pool() + self._bridge(r)["clear"] + self.settings.get("deckDepth", 1.5)
                out.append({"name": r["name"], "c0": r["c0"], "c1": r["c1"], "lb": lb, "ub": lb})  # at the clearance level
        return out

    def river_tubes(self, md: Optional[List[str]]) -> List[dict]:
        """River crossings in tunnel the solver holds: every river on a Metro line (twin tubes);
        on the RER between two underground stations, inside a canon deep bore, or in the covered
        way where the canon crosses the river in tunnel (sunk box sections). Rail at most the
        lowest bed - margin over the river range."""
        rivers = self._rivers_info()
        margin = RIVER_MARGIN["rer" if self.is_rer else "metro"]
        step = float(self.data.get("step_m", 2.0))
        out = []
        for r in self.data.get("rivers", []) or []:
            if self._bridge(r):
                continue
            if self.is_rer:
                if not md:
                    continue
                info = rivers.get(r["name"], {})
                sec = self.canon_at((r["c0"] + r["c1"]) / 2)
                if sec and sec["m"] == "covered" and not info.get("in_covered_way"):
                    continue
                ip, inx = -1, -1
                for i, st in enumerate(self.stations):
                    if st["c"] < r["c0"]:
                        ip = i
                    if st["c"] > r["c1"] and inx < 0:
                        inx = i
                bore = bool(sec) and (sec["m"] == "deep" or (sec["m"] == "covered" and info.get("in_covered_way")))
                under = ip >= 0 and inx >= 0 and md[ip] != "surface" and md[inx] != "surface"
                if not (bore or under):
                    continue
            beds = [self.bed_at(c) for c in np.arange(r["c0"], r["c1"] + 1e-9, step)]
            beds = [b for b in beds if math.isfinite(b)]
            if beds:
                out.append({"name": r["name"], "c0": r["c0"], "c1": r["c1"], "ub": min(beds) - margin})
        return out

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
        # each platform counts with its transitions (half a curve at the steepest grade each end)
        g = self.settings["maxGrade"] / 1000.0
        P = self.settings["platform"] + max(self.settings["vcRadius"] * g, self.settings.get("vcMinLen", 0.0))
        n = len(self.stations)
        md = ([modes[i] if modes and modes[i] else self.default_mode(i) for i in range(n)]
              if self.is_rer else None)
        ub, lb = [], []
        for i, s in enumerate(self.stations):
            gr = float(self.ground0_at(s["c"]))
            f = self.canon_fixed.get(i)
            if f and (math.isfinite(gr) or f.get("abs") is not None):
                z0 = f["abs"] if f.get("abs") is not None else gr + f["off"]
                ub.append(z0)
                lb.append(z0)
            elif md and md[i] == "surface" and math.isfinite(gr):
                ub.append(gr)
                lb.append(gr)
            else:
                ub.append(gr - self.settings["defDepth"] if math.isfinite(gr) else math.inf)
                lb.append(-math.inf)

        tubes = self.river_tubes(md) + self.river_bridges()
        tube_pvi = []
        if not tubes:
            def run(i, j):
                return max(0.0, abs(self.stations[j]["c"] - self.stations[i]["c"]) - P * abs(j - i))

            z = [min(ub[j] + g * run(i, j) for j in range(n)) for i in range(n)]
            for i in range(n):
                lo = max((lb[j] - g * run(i, j) for j in range(n) if math.isfinite(lb[j])), default=-math.inf)
                z[i] = max(z[i], lo)
                if not math.isfinite(z[i]):
                    z[i] = 0.0
            st = [_js_round(v * 100) / 100 for v in z]
        else:
            # the same solver over stations plus the river banks of each tube
            nodes = [{"c": s["c"], "st": True, "i": i, "ub": ub[i], "lb": lb[i]} for i, s in enumerate(self.stations)]
            # tube bottom half a curve beyond each bank, never closer than a transition to a platform
            e, half = self.settings["vcRadius"] * g / 2, self.settings["platform"] / 2
            for t in tubes:
                before = [st["c"] + half + e for st in self.stations if st["c"] + half <= t["c0"]]
                after = [st["c"] - half - e for st in self.stations if st["c"] - half >= t["c1"]]
                a = min(t["c0"], max([0.0, t["c0"] - e] + before))
                b = max(t["c1"], min([self.length, t["c1"] + e] + after))
                nodes += [{"c": x, "st": False, "ub": t.get("ub", math.inf), "lb": t.get("lb", -math.inf)}
                          for x in (a, b)]
            nodes.sort(key=lambda nd: nd["c"])  # stable, as Array.sort
            cnt, k = [], 0
            for nd in nodes:
                cnt.append(k)
                k += nd["st"]

            def run(a, b):
                x, y = (a, b) if a < b else (b, a)
                between = cnt[y] - cnt[x] - (1 if nodes[x]["st"] else 0)
                return max(0.0, nodes[y]["c"] - nodes[x]["c"] - P * between
                           - (P / 2 if nodes[x]["st"] else 0) - (P / 2 if nodes[y]["st"] else 0))

            N = len(nodes)
            z = [min(nodes[b]["ub"] + g * run(a, b) for b in range(N)) for a in range(N)]
            for a in range(N):
                lo = max((nodes[b]["lb"] - g * run(a, b) for b in range(N) if math.isfinite(nodes[b]["lb"])),
                         default=-math.inf)
                z[a] = max(z[a], lo)
                if not math.isfinite(z[a]):
                    z[a] = 0.0
            st = [0.0] * n
            for nd, za in zip(nodes, z):
                if nd["st"]:
                    st[nd["i"]] = _js_round(za * 100) / 100
                else:
                    tube_pvi.append((_js_round(nd["c"] * 10) / 10, _js_round(za * 1000) / 1000))
        self.modes = md or []
        self.pvi = sorted((self.surface_pvis(st, md) if md else []) + tube_pvi)
        return st

    def surface_pvis(self, st: List[float], md: List[str]) -> List[tuple]:
        """Between two at-grade stations the rail follows the old railroad: bend points every
        surfStep on the ground smoothed over two steps, held to the grade limit both ways."""
        step = self.settings["surfStep"]
        g, L, S = self.settings["maxGrade"] / 1000.0, self.length, self.stations
        half = self.settings["platform"] / 2 + max(self.settings["vcRadius"] * g, self.settings.get("vcMinLen", 0.0)) / 2  # clear of the transitions
        n = len(S)

        def smooth(c):
            vals = [self.surface0_at(min(max(c + d, 0.0), L)) for d in np.arange(-step, step + 1e-9, step / 4)]
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
        # stations removed on the page are left out before solving (as on the page)
        self.removed = [k for k in ((doc or {}).get("del") or []) if isinstance(k, str)]
        if self.removed:
            self.data["stations"] = [s for s in self.all_stations if self.key_of(s) not in self.removed]
            self._build_canon()
        modes = None
        if doc and doc.get("mode") and self.is_rer:
            dm = doc["mode"]
            modes = [dm.get(self.st_key(i)) if dm.get(self.st_key(i)) in ("surface", "under")
                     else self.default_mode(i) for i in range(len(self.stations))]
        self.st = self.default_align(modes)
        self.sg = [0.0] * len(self.stations)
        self.so = [0.0] * len(self.stations)
        self.gapfill = [k for k in ((doc or {}).get("gapfill") or []) if isinstance(k, str)]
        self.ovr = []
        if not doc:
            self._apply_locks()
            return
        # platform slid along its drawn point: centre = point + so, the point stays on it
        half = self.settings["platform"] / 2
        sod = doc.get("so") or {}
        self.so = [min(half, max(-half, float(sod.get(self.st_key(i)) or 0.0)))
                   if isinstance(sod.get(self.st_key(i)), (int, float)) else 0.0
                   for i in range(len(self.stations))]
        sgd = doc.get("sg") or {}
        self.sg = [float(sgd[self.st_key(i)]) if isinstance(sgd.get(self.st_key(i)), (int, float)) else 0.0
                   for i in range(len(self.stations))]
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
        self._apply_locks()
        if any(self.so):
            self.data["stations"] = [dict(s, c=s["c0"] + o) for s, o in zip(self.stations, self.so)]
            self._build_canon()

    def _apply_locks(self):
        """Locked stretches of the canon (Ben, 27 October 2026), as the page holds them: their bend points, station
        levels (level platforms, not slid) and painted structure replace whatever the saved profile has there."""
        cn = ((self.rer_canon.get("lines") or {}) if self.is_rer else CANON).get(self.id, {})
        for lk in cn.get("locked") or []:
            lo, hi = float(lk["c0"]), float(lk["c1"])
            self.pvi = sorted([p for p in self.pvi if p[0] < lo or p[0] > hi] + [(float(c), float(z)) for c, z in lk.get("pvi") or []])
            ovr = []
            for o in self.ovr:
                if o[1] <= lo or o[0] >= hi:
                    ovr.append(o)
                    continue
                if o[0] < lo:
                    ovr.append((o[0], lo, o[2]))
                if o[1] > hi:
                    ovr.append((hi, o[1], o[2]))
            self.ovr = sorted(ovr + [(float(a), float(b), t) for a, b, t in lk.get("ovr") or []])
            for name, z in (lk.get("st") or {}).items():
                for i, st in enumerate(self.stations):
                    if st["name"] == name:
                        self.st[i], self.sg[i], self.so[i] = float(z), 0.0, 0.0

    # ------------------------------------------------------------- rail profile
    def _verts(self) -> List[dict]:
        half, L = self.settings["platform"] / 2, self.length
        v = []
        placed = []
        for i, s in enumerate(self.stations):
            z = self.st[i]
            gp = (self.sg[i] if i < len(self.sg) else 0.0) / 1000.0
            ca, cb = min(max(s["c"] - half, 0.0), L), min(max(s["c"] + half, 0.0), L)
            # the same platform listed twice (overlapping): one platform, the first entry's level
            if any(ca < b - 1e-6 and cb > a + 1e-6 for a, b in placed):
                continue
            placed.append((ca, cb))
            v.append({"c": ca, "z": z + gp * (ca - s["c"]), "kind": "ps", "i": i, "o": 1, "gp": gp})
            v.append({"c": cb, "z": z + gp * (cb - s["c"]), "kind": "pe", "i": i, "o": 0, "gp": gp})
        v += [{"c": c, "z": z, "kind": "pvi", "o": 2} for c, z in self.pvi]
        v.sort(key=lambda t: (t["c"], t["o"]))  # platform end first on ties
        if not v:
            return [{"c": 0.0, "z": 0.0, "kind": "end"}, {"c": L, "z": 0.0, "kind": "end"}]
        if v[0]["c"] > 0:
            v.insert(0, {"c": 0.0, "z": v[0]["z"], "kind": "end"})
        if v[-1]["c"] < L:
            v.append({"c": L, "z": v[-1]["z"], "kind": "end"})
        return v

    def design(self) -> dict:
        """The built rail, as the page draws it: vertical curves of radius vcRadius at every
        change of grade, kept off the platforms by a level transition of half the curve beyond
        each platform end; curves shortened where the straight grade is too short."""
        rv = float(self.settings.get("vcRadius", 0.0) or 0.0)
        lmin = float(self.settings.get("vcMinLen", 0.0) or 0.0) if rv else 0.0

        def curve_len(dg):  # radius x change of grade, never shorter than the minimum (AREMA 100 ft)
            return max(rv * abs(dg), lmin) if abs(dg) > 1e-5 else 0.0

        key = (tuple(self.st), tuple(self.sg), tuple(self.pvi), rv, lmin, self.settings["platform"],
               tuple(s["c"] for s in self.stations))
        if getattr(self, "_design_key", None) == key:
            return self._design
        verts = self._verts()
        n = len(verts)
        ext = [0.0] * n

        def outward(k):
            v = verts[k]
            if (v["kind"] == "pe" and k + 1 < n and not (verts[k + 1]["kind"] == "ps" and verts[k + 1].get("i") == v["i"])
                    and verts[k + 1]["c"] - v["c"] > 1e-6):
                return k + 1
            if (v["kind"] == "ps" and k - 1 >= 0 and not (verts[k - 1]["kind"] == "pe" and verts[k - 1].get("i") == v["i"])
                    and v["c"] - verts[k - 1]["c"] > 1e-6):
                return k - 1
            return -1

        def z_on(k, c):  # along a platform end's own grade (the transition carries it on)
            return verts[k]["z"] + verts[k].get("gp", 0.0) * (c - verts[k]["c"])

        if rv > 0:
            for _ in range(5):
                nx = [0.0] * n
                for k in range(n):
                    o = outward(k)
                    if o < 0:
                        continue
                    d = 1 if o > k else -1
                    piv = verts[k]["c"] + d * ext[k]
                    oc = verts[o]["c"] - d * (ext[o] if outward(o) == k else 0.0)
                    run = abs(oc - piv)
                    if run < 1e-6:
                        continue
                    gq = (z_on(o, oc) - z_on(k, piv)) / (oc - piv)
                    nx[k] = curve_len(gq - verts[k].get("gp", 0.0)) / 2
                for k in range(n - 1):
                    ln = verts[k + 1]["c"] - verts[k]["c"]
                    a = nx[k] if outward(k) == k + 1 else 0.0
                    b = nx[k + 1] if outward(k + 1) == k else 0.0
                    if a + b > 0.5 * ln and a + b > 0:
                        f = 0.5 * ln / (a + b)
                        if a:
                            nx[k] *= f
                        if b:
                            nx[k + 1] *= f
                ext = nx
        dv = []
        for k, v in enumerate(verts):
            if v["kind"] == "ps" and ext[k] > 1e-6:
                dv += [{"c": v["c"] - ext[k], "z": z_on(k, v["c"] - ext[k]), "kind": "x", "i": v["i"]}, v]
            elif v["kind"] == "pe" and ext[k] > 1e-6:
                dv += [v, {"c": v["c"] + ext[k], "z": z_on(k, v["c"] + ext[k]), "kind": "x", "i": v["i"]}]
            else:
                dv.append(v)
        g = [((dv[k + 1]["z"] - dv[k]["z"]) / (dv[k + 1]["c"] - dv[k]["c"]) if dv[k + 1]["c"] - dv[k]["c"] > 1e-9 else 0.0)
             for k in range(len(dv) - 1)]
        L = [0.0] * len(dv)
        need = [0.0] * len(dv)
        if rv > 0:
            for k in range(1, len(dv) - 1):
                if dv[k]["kind"] in ("ps", "pe", "end"):
                    continue
                need[k] = L[k] = curve_len(g[k] - g[k - 1])
        for k in range(len(dv) - 1):
            ln = dv[k + 1]["c"] - dv[k]["c"]
            h = L[k] / 2 + L[k + 1] / 2
            if h > ln and h > 0:
                f = ln / h
                L[k] = min(L[k], L[k] * f)
                L[k + 1] = min(L[k + 1], L[k + 1] * f)
        short = [{"c": dv[k]["c"], "need": need[k], "got": L[k]} for k in range(len(dv)) if need[k] - L[k] > 0.5]
        self._design = {"dv": dv, "g": g, "L": L, "short": short,
                        "vc": np.array([v["c"] for v in dv]), "vz": np.array([v["z"] for v in dv])}
        self._design_key = key
        return self._design

    def vertices(self):
        """The straight grades between bends (chainage, rail level)."""
        d = self.design()
        return d["vc"], d["vz"]

    def rail_at(self, c):
        d = self.design()
        cc = np.asarray(c, dtype=float)
        z = np.interp(cc, d["vc"], d["vz"])
        for k, Lk in enumerate(d["L"]):
            if Lk <= 1e-6:
                continue
            ck = d["dv"][k]["c"]
            m = np.abs(cc - ck) < Lk / 2
            if np.any(m):
                g1, g2 = d["g"][k - 1], d["g"][k]
                x = cc[m] - (ck - Lk / 2) if cc.ndim else cc - (ck - Lk / 2)
                zc = d["dv"][k]["z"] - g1 * Lk / 2 + g1 * x + (g2 - g1) * x * x / (2 * Lk)
                if cc.ndim:
                    z[m] = zc
                else:
                    z = zc
        return z

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
        # portal ramps: rail less than a box height down is an open trough (Metro 4.6 m; RER the envelope, Ben 2026-10-28)
        if d < (float(self.settings["envelope"]) if self.is_rer else self.settings.get("trough_override", METRO_ST["box"]["top"])):
            return "trough"
        sec = self.canon_at(c)
        m = sec["m"] if sec else ("deep" if d >= self.settings["deepBelow"] else "shallow")
        if m == "canal":
            return "cutcover"
        # too shallow to bore: built cut and cover
        if self.is_rer:
            if d < self.bore_crown() + self.min_cover():
                return "cutcover"
        else:
            sc = self.struct_for("deep" if m == "deep" else "shield", c)
            if d - sc["top"] < self.req_cover(sc, z + sc["top"]):
                return "cutcover"
        if m == "deep":
            return "deep"
        return "cutcover" if self.in_station(c) else "shield"

    def _era(self) -> Optional[dict]:
        return None if self.is_rer else ERA.get(self.id)

    def struct_for(self, t: str, c: float) -> dict:
        """The tunnel structure at chainage c for a tunnel type (below / top from the rail)."""
        st = self.settings
        if self.is_rer:  # river crossings: sunk box sections in a dredged trench
            return ({"k": "box", "below": st["invertDepth"], "top": st["envelope"]}
                    if t == "cutcover" or self.river_at(c) else {"k": "bore", "below": st["invertDepth"], "top": st["boreCrown"]})
        if self.river_at(c) or t == "deep":
            return METRO_ST["tube"]
        if t == "cutcover":
            return METRO_ST["box"]
        return METRO_ST[(self._era() or {}).get("shield", "tube")]

    def req_cover(self, sc: dict, top_z: float) -> float:
        """Cover a structure needs over its top (top_z = its top level)."""
        if "minCover_override" in self.settings:
            return float(self.settings["minCover_override"])
        if self.is_rer:
            return 0.0 if sc["k"] == "box" else float(self.settings["minCover"])
        if sc["k"] == "box":
            return BOX_COVER
        return TUBE_COVER_HIGH if top_z > WATER_TABLE else sc["od"]

    def min_cover(self) -> float:
        """Cover over RER bored tunnels (setting)."""
        if "minCover_override" in self.settings:
            return float(self.settings["minCover_override"])
        return float(self.settings["minCover"])

    def bore_crown(self) -> float:
        """RER bored tube crown above rail; Metro: the line's shield structure."""
        return float(self.settings["boreCrown"]) if self.is_rer else self.struct_for("shield", -1e9)["top"]

    def _path_xy(self, c: np.ndarray) -> np.ndarray:
        path = np.array(self.data["path"], float)
        lat0 = math.radians(path[0][2])
        kx, ky = 111320 * math.cos(lat0), 110540
        return np.column_stack([np.interp(c, path[:, 0], path[:, 1]) * kx, np.interp(c, path[:, 0], path[:, 2]) * ky])

    def _turns(self):
        if getattr(self, "_turns_cache", None) is not None:
            return self._turns_cache
        path = np.array(self.data["path"], float)
        lat0 = math.radians(path[0][2])
        xy = np.column_stack([path[:, 1] * 111320 * math.cos(lat0), path[:, 2] * 110540])
        seg = np.hypot(*np.diff(xy, axis=0).T)
        dfl = np.zeros(len(path))
        for i in range(1, len(path) - 1):
            a, b = xy[i] - xy[i - 1], xy[i + 1] - xy[i]
            dfl[i] = math.degrees(math.atan2(a[0] * b[1] - a[1] * b[0], a @ b))
        self._turns_cache = (path, dfl, seg)
        return self._turns_cache

    def drawing_flags(self) -> List[dict]:
        """Corners on the drawn path that are not finished or not correct (see DRAW)."""
        path, dfl, seg = self._turns()
        out = []
        for i in range(1, len(path) - 1):
            a, c = abs(dfl[i]), float(path[i][0])
            piece = next((q["name"] for q in self.data.get("pieces", []) if q["c0"] - 5 <= c <= q["c1"] + 5), "")
            base = {"c": c, "lat": float(path[i][2]), "lon": float(path[i][1]), "piece": piece, "turn": float(a)}
            if a > DRAW["back"]:
                out.append({**base, "kind": "doubles back", "level": "error"})
            elif a >= DRAW["kink"] and min(seg[i - 1], seg[i]) < DRAW["kinkSeg"]:
                out.append({**base, "kind": "join kink", "level": "error", "short_seg": float(min(seg[i - 1], seg[i]))})
            elif a >= DRAW["single"] and all(not (0 < j < len(path) - 1 and abs(dfl[j]) >= DRAW["nb"]
                                                  and np.sign(dfl[j]) == np.sign(dfl[i])) for j in (i - 1, i + 1)):
                out.append({**base, "kind": "single-angle corner", "level": "warning"})
        return out

    def platform_curves(self) -> List[dict]:
        """Per station: radius fitted over the platform span (drawn path every 2 m, platform where
        it has been slid), extra gap on each face, and 'error' / 'warning' / None."""
        half, out = self.settings["platform"] / 2, []
        for i, s in enumerate(self.stations):
            a, b = max(0.0, s["c"] - half), min(self.length, s["c"] + half)
            c = np.arange(a, b + 1e-9, 2.0)
            if b - a > 1e-6 and (b - a) % 2 > 1e-6:
                c = np.append(c, b)
            R = fit_radius(self._path_xy(c))
            fin = math.isfinite(R)
            level = "error" if R < PLAT_R_ERR else "warning" if R < PLAT_R_WARN else None
            gap = self.st_key(i) in (self.gapfill or [])
            path, dfl, _ = self._turns()
            m = (path[:, 0] > s["c"] - half) & (path[:, 0] < s["c"] + half)
            m[0] = m[-1] = False
            pos, neg = float(dfl[m][dfl[m] > 0].sum()), float(dfl[m][dfl[m] < 0].sum())
            lo = min(pos, -neg)
            scurve = "error" if lo >= DRAW["sErr"] else "warning" if lo >= DRAW["sWarn"] else None
            out.append({"name": s["name"], "c": s["c"], "R": R, "outside": CAR_LEN ** 2 / (8 * R) if fin else 0.0,
                        "inside": END_DOOR ** 2 / (2 * R) if fin else 0.0, "level": level, "gapfill": gap,
                        "scurve": scurve, "turn_pos": pos, "turn_neg": neg})
        return out

    def river_breaks(self) -> List[dict]:
        """Stretches in tunnel under a river where the rail is above bed - margin (bed = ground raster)."""
        margin = RIVER_MARGIN["rer" if self.is_rer else "metro"]
        step = float(self.data.get("step_m", 2.0))
        out = []
        for b in self.river_bridges():  # bridges: rail at least the navigation clearance level
            zz = self.rail_at(np.arange(b["c0"], b["c1"] + 1e-9, step))
            if len(zz) and zz.min() < b["lb"] - 0.05:
                out.append({"name": b["name"], "c0": b["c0"], "c1": b["c1"], "over": float(b["lb"] - zz.min()), "bridge": True})
        for r in self.data.get("rivers", []) or []:
            if self._bridge(r):
                continue
            run = None
            for i in range(math.ceil(r["c0"] / step), int(math.floor(r["c1"] / step)) + 1):
                c = i * step
                bed = self.bed_at(c)
                z = float(self.rail_at(c))
                t = self.type_at(c, z)
                over = z - (bed - margin) if math.isfinite(bed) and t in ("cutcover", "shield", "deep") else -math.inf
                if over > 0.005:
                    if run is None:
                        run = {"name": r["name"], "c0": c, "c1": c, "over": over}
                        out.append(run)
                    run["c1"], run["over"] = c, max(run["over"], over)
                else:
                    run = None
        return out

    def type_at(self, c: float, z: Optional[float] = None) -> str:
        if z is None:
            z = float(self.rail_at(c))
        return self.override_at(c) or self.auto_type(c, z)

    # ------------------------------------------------------------- context
    def context_blocks(self) -> List[dict]:
        """Other systems' structures on this line (context file): name n, short label l, kind k
        (box | trough | atgrade | viaduct | fill), chainage c0..c1, their rail p [[c, z], ...],
        heights below b / top t from their rail (t is the clear height above an open structure),
        open o, their platforms pl [[c0, c1, z], ...], source s; structure type st (embankment, arch,
        viaduct, or the kind) and, on an embankment or arch viaduct, the street openings gaps
        [[c0, c1, street], ...] along this line."""
        return list(self.ctx.get("blocks") or [])

    def open_struct(self, t: str) -> dict:
        """This line's structure when it is in the open (rail to underside, clear height above)."""
        top = OPEN_CLEAR["rer" if self.is_rer else "metro"]
        if t == "elevated":
            return {"k": "elevated", "below": float(self.settings.get("deckDepth", 1.5)), "top": top}
        return {"k": t, "below": BED_DEPTH, "top": top}

    def context_clearances(self) -> List[dict]:
        """Each context block against this line at its worst point, with the crossing rule: the
        upper structure's floor + 0.5 m + the lower one's top (a track in the open counts its clear
        height). Under a viaduct only a line in the open is checked: the arches go to the street
        and no footing depth is set (Ben, 26 October). Under an embankment or an arch viaduct
        (block st) a line in the open may pass only inside a street opening (block gaps); anywhere
        else it is blocked. Both in the open within 1 m: crosses at grade."""
        out = []
        open_t = ("atgrade", "trough", "elevated")
        for b in self.context_blocks():
            viad = b["k"] in ("viaduct", "fill")
            # an embankment or an arch viaduct is open only at its street bridges or arches (Ben, 26 October):
            # a line in the open passing under it anywhere else runs into it
            gapped = b.get("st") in ("embankment", "arch")
            gaps = b.get("gaps") or []
            w = None
            for c, zo in b["p"]:
                z = float(self.rail_at(c))
                mt = self.type_at(c, z)
                t = self.open_struct(mt) if mt in open_t else self.struct_for(mt, c)
                up = z >= zo
                if viad and not up and mt not in open_t:
                    continue
                if gapped and not up and not any(g[0] - 0.5 <= c <= g[1] + 0.5 for g in gaps):
                    w = {"c": c, "zo": zo, "z": z, "clear": abs(z - zo), "need": None, "me_up": False, "type": mt,
                         "level": False, "short": float("inf"), "blocked": True}
                    break
                need = (t["below"] + SEP_GAP + b["t"]) if up else (b["b"] + SEP_GAP + t["top"])
                level = mt in open_t and b["k"] in ("atgrade", "trough") and abs(z - zo) < 1.0
                short = need - abs(z - zo)
                if w is None or (level and not w["level"]) or (level == w["level"] and short > w["short"]):
                    w = {"c": c, "zo": zo, "z": z, "clear": abs(z - zo), "need": need, "me_up": up,
                         "type": mt, "level": level, "short": short, "blocked": False}
            if w:
                out.append({**w, "with": b["l"], "kind": b["k"], "st": b.get("st", b["k"]),
                            "ok": not w["blocked"] and not w["level"] and w["short"] <= 0.05, "block": b})
        return out

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
        shallow = 0
        for t in self.river_tubes(self.modes or None):
            zz = self.rail_at(np.arange(t["c0"], t["c1"] + 1e-9, 5.0))
            shallow += int(zz.max() > t["ub"] + 0.05)
        clashes = [x for x in self.context_clearances() if not x["ok"]]
        return {"shallow_tubes": shallow, "river_breaks": len(self.river_breaks()),
                "context_clashes": len(clashes),
                "km_by_type": {k: round(v, 3) for k, v in km.items()},
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
