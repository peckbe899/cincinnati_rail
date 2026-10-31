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

import bisect
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

FT = 0.3048
TYPES = ("elevated", "atgrade", "trough", "cutcover", "shield", "deep", "sunk")
# railsim structure names for each analyzer type (all three tunnel kinds use tunnel drag)
STRUCTURE = {"elevated": "viaduct", "atgrade": "at-grade", "trough": "cut", "cutcover": "cut-and-cover",
             "shield": "shield", "deep": "deep-tube", "sunk": "sunk-box"}
TUNNEL_STRUCTURES = {"tunnel", "cut-and-cover", "shield", "deep-tube", "sunk-box"}

# Platforms 400 ft (Ben, 23 October 2026: 6 cars of about 67 ft or 8 of about 50 ft; was 500 ft)
DEFAULTS = dict(maxGrade=50.0, platform=121.92, defDepth=7.62, elevAbove=3.0, coverBelow=3.0,
                deepBelow=18.29, shallowMax=12.19, poolFt=455.0, deckDepth=1.5,
                vcRadius=1500.0, vcMinLen=30.5, minCover=2.0, fillTaper=50.0,
                riverRoof=1.0, riverSink=5.0, riverRise=3.0, riverFlatTol=1.0, riverClearWater=3.66, riverCap=1.0,
                roadClearHighway=4.9, roadClearMajor=4.3, roadClearMinor=4.3)
# Metro structures (Ben's rules), from the top of rail: below = rail to underside, top = rail to
# top, od = outside diameter. Cut-and-cover box (and station box) 1.0 below / 4.6 to top; twin
# tube (4.4 m inside, 4.76 m outside, rail 0.5 m above invert) 0.68 / 4.08 for deep tube on every
# line, shield on Lines 1-7 and every river crossing; double-track bore (9.0 m outside) 3.2 / 5.8
# for shield on Lines 8-14. Cover over the top: one outside diameter over every bored tube (Ben,
# 28 October; was 2.0 m above the 140 m water table); box roof 0.6 m. Shallower than that is
# built cut and cover.
METRO_ST = {"box": {"k": "box", "below": 1.0, "top": 4.6},
            "tube": {"k": "tube", "below": 0.68, "top": 4.08, "od": 4.76},
            "bore": {"k": "bore", "below": 3.2, "top": 5.8, "od": 9.0}}
BOX_COVER = 0.6
# River crossings (Ben, 30 October; as the editor): every Metro and RER river crossing in tunnel is a sunk double-track
# box (the CVG Express Ohio bridge aside). Its roof sits from riverSink below the bed to riverRise above it (Metro rail
# bed - 10.0 to bed - 2.0 m, RER bed - 11.6 to bed - 3.6 m): the upper limit at every point in the river, the lower on the
# flat bottom only (bed within riverFlatTol of the lowest). A roof above the bed has the bed made up over it (riverCap
# thick); on a navigable river (canon rivers "navigable": the Ohio) that keeps riverClearWater (12 ft) at normal pool.
# A short cut-and-cover transition joins it to a bored tunnel at each bank.
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
                    fillTaper=50.0, riverSink=5.0, riverRise=3.0, riverFlatTol=1.0, riverClearWater=3.66,
                    riverCap=1.0, roadClearHighway=4.9, roadClearMajor=4.3, roadClearMinor=4.3)
RER_CANON_JSON = Path(__file__).resolve().parent.parent / "data" / "profile" / "rer" / "canon.json"
CONTEXT_JSON = Path(__file__).resolve().parent.parent / "data" / "profile" / "context" / "lines.json"
# the shared Metro structure record (Ben, 27-28 October; claude/Metro_Structure_Gauge_Handoff.md), as the editor reads it;
# settings_override {"legacy_structures": True} keeps the structures of before (the 4.76 m tube, 9.0 m bore)
# the hub's records as last exported (hub/seed, Ben's own: 31 October, the editor reads the hub, so the port must too), else
# the repo's defaults
_ROOT = Path(__file__).resolve().parent.parent
_SEED = _ROOT / "hub" / "seed"
_pick = lambda seed, default: seed if seed.exists() else default
MS_JSON = _pick(_SEED / "params" / "metro_structure.json", _ROOT / "data" / "profile" / "metro_structure.json")
CHR_JSON = _pick(_SEED / "chronology" / "segments.json", _ROOT / "data" / "profile" / "chronology.json")   # the Chronology record
PLAT_JSON = _pick(_SEED / "params" / "station_platforms.json", _ROOT / "data" / "profile" / "station_platforms.json")
_CHR_LINES = None
APX_JSON = _pick(_SEED / "params" / "approach_extra.json", _ROOT / "data" / "profile" / "approach_extra.json")


def _tube_of(t: dict) -> dict:
    lin = (t["outside"] - t["inside"]) / 2
    return {"k": "bore" if t["inside"] > 7 else "tube", "below": t["rail_over_invert"] + lin,
            "top": t["inside"] - t["rail_over_invert"] + lin, "od": t["outside"]}
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


MIN_RUN = 20.0   # no stretch shorter than this outside a station (drawing value, as the editor)

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
             canon_json=None, settings_override: Optional[dict] = None, context_json=None, records: str = "hub") -> "MetroProfile":
        """records: "hub" reads the hub's exported records (hub/seed, Ben's), "repo" the repo's defaults (data/profile)"""
        data = json.loads(Path(line_json).read_text())
        rer = "RER" in data.get("system", "")
        # per-line settings in the line file (e.g. the CVG Express's 200 m platforms)
        p = cls(data, {**load_settings(settings_json, rer=rer), **(data.get("settings") or {}), **(settings_override or {})})
        dp = _ROOT / "data" / "profile"
        ms_j, chr_j, pk, ax = (MS_JSON, CHR_JSON, PLAT_JSON, APX_JSON) if records == "hub" else \
            (dp / "metro_structure.json", dp / "chronology.json", dp / "station_platforms.json", dp / "approach_extra.json")
        p.ms = None
        if not rer and not p.settings.get("legacy_structures") and ms_j.exists():
            p.ms = json.loads(ms_j.read_text())
        p.chr = json.loads(chr_j.read_text()) if p.ms and chr_j.exists() else None
        # island or side at each Metro station (the 3D build's, from the Deck)
        p.platforms_kind = (json.loads(pk.read_text()).get(p.data["id"]) or {}) if p.ms and pk.exists() else {}
        # straights where no single arc fits (the 3D build's)
        p.approach_extra = (json.loads(ax.read_text()).get(p.data["id"]) or []) if p.ms and ax.exists() else []
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
        p._ground = p._ground.astype(np.float32).astype(float)   # the editor's precision (Float32Array), so ties agree
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
        ends. Painted Shallow shield and Deep tunnel re-grade the same way, to the tube's top plus its
        cover (Ben, 30 October). Fill only. Call again after changing st, pvi or ovr."""
        g0 = getattr(self, "_ground0", self._ground)
        cc = [(a, b, t) for a, b, t in self.ovr if t in ("cutcover", "shield", "deep")]
        if not cc:
            self._ground = g0.copy()
            self._ground_v = getattr(self, "_ground_v", 0) + 1
            return
        step = float(self.data.get("step_m", 2.0))
        n = len(g0)
        t = np.full(n, -np.inf)
        for a, b, kind in cc:
            i0, i1 = max(0, math.ceil(a / step)), min(n - 1, math.floor(b / step))
            for i in range(i0, i1 + 1):
                c = i * step
                if self.river_at(c):
                    continue
                sc = self.struct_for(kind, c)
                v = float(self.rail_at(c)) + sc["top"] + self.req_cover(sc, 0.0)
                if not v <= g0[i] + 0.005:   # the taper starts only where the ground is raised
                    t[i] = max(t[i], v)
        drop = float(self.settings.get("fillTaper", 50.0)) / 1000.0 * step
        for i in range(1, n):
            t[i] = max(t[i], t[i - 1] - drop)
        for i in range(n - 2, -1, -1):
            t[i] = max(t[i], t[i + 1] - drop)
        river = np.array([bool(self.river_at(i * step)) for i in range(n)]) if self.data.get("rivers") else np.zeros(n, bool)
        g = g0.copy()
        m = np.isfinite(g0) & (t > g0 + 0.005) & ~river
        g[m] = t[m].astype(np.float32)
        self._ground = g
        self._ground_v = getattr(self, "_ground_v", 0) + 1

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

    def sunk_box(self) -> dict:
        """The sunk unit (as the editor): the canon box section (the structure record's box: rail 1.0 m above its underside,
        4.0 m to the roof underside, 7.90 m inside, 3.90 m track centres) with a 1.0 m roof (riverRoof): 5.0 m rail to roof
        top. RER: the 6.6 m box (the envelope), invertDepth below."""
        st = self.settings
        if self.is_rer:
            return {"k": "sunk", "below": float(st["invertDepth"]), "top": float(st["envelope"])}
        bx = (getattr(self, "ms", None) or {}).get("box") or {"below": METRO_ST["box"]["below"], "roof_underside": 4.0, "inside": 7.9, "spacing": 3.9}
        return {"k": "sunk", "below": float(bx["below"]), "top": float(bx["roof_underside"]) + float(st.get("riverRoof", 1.0)),
                "inside": float(bx["inside"]), "spacing": float(bx["spacing"])}

    def along_shore(self, r: dict) -> bool:
        """A river range along an RER embanked covered way (the canon's, beside the Ohio) is the shore, not a crossing."""
        if not self.is_rer:
            return False
        sec = self.canon_at((r["c0"] + r["c1"]) / 2)
        return bool(sec) and sec["m"] == "covered" and not self._rivers_info().get(r["name"], {}).get("in_covered_way")

    def river_band(self, r: dict) -> Optional[dict]:
        """The band a sunk box keeps under river r, from the points under water (bed below normal pool): ub (rail at most)
        and lb (rail at least, on the flat bottom), the lowest bed, and on a navigable river the rail under which the
        made-up bed keeps its clear water (nav). None: not a crossing."""
        if self.along_shore(r):
            return None
        st, step = self.settings, float(self.data.get("step_m", 2.0))
        beds = np.array([self.bed_at(c) for c in np.arange(r["c0"], r["c1"] + 1e-9, step)])
        beds = beds[np.isfinite(beds) & (beds < self.pool())]
        if not len(beds):
            return None
        top, low = self.sunk_box()["top"], float(beds.min())
        ub = float((beds - top + st["riverRise"]).min())
        lb = float((beds[beds <= low + st["riverFlatTol"]] - top - st["riverSink"]).max())
        nav = self.pool() - st["riverClearWater"] - st["riverCap"] - top if self._rivers_info().get(r["name"], {}).get("navigable") else None
        # the solver: under the clear-water level, or the roof and its cap under the lowest bed (nothing made up)
        ub = min(ub, max(nav, low - top - st["riverCap"])) if nav is not None else ub
        return {"name": r["name"], "c0": r["c0"], "c1": r["c1"], "ub": ub, "lb": lb, "low": low, "nav": nav}

    def river_tubes(self, md: Optional[List[str]] = None) -> List[dict]:
        """River crossings in tunnel the solver holds: every river but a bridge, a sunk box inside its band (river_band)."""
        if self.settings.get("legacy_structures"):
            return []
        out = [self.river_band(r) for r in self.data.get("rivers", []) or [] if not self._bridge(r)]
        return [b for b in out if b]

    def made_bed_at(self, c: float, z: Optional[float] = None) -> float:
        """The made-up bed over a sunk box whose roof stands above the river bed (nan where it does not)."""
        r = self.river_at(c)
        if not r or self._bridge(r) or self.along_shore(r):
            return math.nan
        z = float(self.rail_at(c)) if z is None else z
        if self.type_at(c, z) != "sunk":
            return math.nan
        b, t = self.bed_at(c), z + self.sunk_box()["top"] + float(self.settings["riverCap"])
        return t if math.isfinite(b) and t > b else math.nan

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
        self.tf = []   # painted tube form: (c0, c1, 'twin' | 'bore') (Ben, 2026-10-31)
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
        for o in doc.get("tf") or []:
            if len(o) >= 3 and o[2] in ("twin", "bore"):
                self.tf.append((float(o[0]), float(o[1]), o[2]))
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
                        "vc": np.array([v["c"] for v in dv]), "vz": np.array([v["z"] for v in dv]),
                        # plain lists for the scalar path of rail_at (no numpy per call: the 31 October audit's hot spot)
                        "lc": [v["c"] for v in dv], "lz": [v["z"] for v in dv],
                        "curves": [(dv[k]["c"] - Lk / 2, dv[k]["c"] + Lk / 2, k) for k, Lk in enumerate(L) if Lk > 1e-6]}
        self._design_key = key
        self._grid = None
        return self._design

    def rail_grid(self):
        """the rail at every step of the line, computed once per design: (chainages, levels)"""
        d = self.design()
        if getattr(self, "_grid", None) is None:
            step = float(self.data.get("step_m", 2.0))
            cs = np.minimum(np.arange(int(self.length // step) + 1) * step, self.length)
            self._grid = (cs, np.asarray(self.rail_at(cs), dtype=float))
        return self._grid

    def vertices(self):
        """The straight grades between bends (chainage, rail level)."""
        d = self.design()
        return d["vc"], d["vz"]

    def rail_at(self, c):
        d = self.design()
        if np.ndim(c) == 0:   # one chainage: pure Python (bisect), about 100x cheaper than the array path per call
            c = float(c)
            lc, lz = d["lc"], d["lz"]
            if c <= lc[0]:
                z = lz[0]
            elif c >= lc[-1]:
                z = lz[-1]
            else:
                j = bisect.bisect_right(lc, c)
                z = lz[j - 1] + (lz[j] - lz[j - 1]) * (c - lc[j - 1]) / (lc[j] - lc[j - 1]) if lc[j] > lc[j - 1] else lz[j]
            j = bisect.bisect_right(d["curves"], (c, math.inf, 0)) - 1   # the one curve c may lie on
            if j >= 0:
                a, b, k = d["curves"][j]
                if a < c < b:   # inside it: the parabola
                    Lk, g1, g2 = d["L"][k], d["g"][k - 1], d["g"][k]
                    x = c - a
                    z = d["dv"][k]["z"] - g1 * Lk / 2 + g1 * x + (g2 - g1) * x * x / (2 * Lk)
            return z
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

    def tube_form_at(self, c: float) -> Optional[str]:
        for a, b, t in reversed(getattr(self, "tf", None) or []):
            if a <= c <= b:
                return t
        return None

    def _tube_key(self, c: float) -> str:
        """The tube at c before the drives are solved: the painted form, else the phase's tube (as the editor's metroTube)."""
        ph = self._phase_at(c)
        t = (self.ms["phases"].get(ph) or self.ms["phases"]["later"])["tube"]
        f = self.tube_form_at(c)
        if f == "bore":
            return "bore"
        if f == "twin" and t == "bore":
            return "A" if ph in ("1", "2") else "C"
        return t

    def override_at(self, c: float) -> Optional[str]:
        for a, b, t in reversed(self.ovr):
            if a <= c <= b:
                return t
        return None

    def in_station(self, c: float) -> bool:
        half = self.settings["platform"] / 2
        return any(abs(c - s["c"]) <= half for s in self.stations)

    # Metro tunnels by era (Ben, 28 October; as the Rail Profiles editor): per-phase thresholds in the structure record
    # (cc_max, min_drive, deep_from); shield needs one tube diameter of cover; between the two limits cut and cover
    # unless the bored stretch makes a whole drive (box to box, portal or deep station: any length); no short pockets
    # inside a longer stretch; drives end
    # at station boxes and where the phase changes; deep stations are platform tunnels. Canon and painted still decide.
    def _chr_segments(self) -> list:
        """this line's Chronology segments [(c0, c1, year, phase)], as the editor's chrSegments: the Chronology's own route
        (chronology_lines.json) when it has the line, else the profile's stations"""
        rec = getattr(self, "chr", None)
        if not rec:
            return []
        if getattr(self, "_chr_list", None) is not None and self._chr_list[0] is rec:
            return self._chr_list[1]
        global _CHR_LINES
        if _CHR_LINES is None:
            f = _ROOT / "data" / "profile" / "chronology_lines.json"
            _CHR_LINES = json.loads(f.read_text()).get("routes", []) if f.exists() else []
        cr = next((r for r in _CHR_LINES if r.get("id") == self.id), None)
        sys_ = cr["sys"] if cr else "cvx" if self.id == "CVG_Express" else "metro"
        st = cr["stations"] if cr else sorted(self.stations, key=lambda s: s["c"])
        out = []
        for i in range(len(st) - 1):
            x, y = sorted((st[i]["name"], st[i + 1]["name"]))
            key = cr["segments"][i] if cr else f"metro|{self.id}|{x}|{y}" if sys_ == "metro" else f"{sys_}|{x}|{y}"
            e = (rec.get("segments") or {}).get(key) or {}
            yr = None if e.get("year") in (None, "") else float(e["year"])
            ph = e.get("phase") or next((p for y0, y1, p in rec.get("phase_years") or [] if yr is not None and y0 <= yr <= y1), None)
            out.append((st[i]["c"] if i else 0.0, st[i + 1]["c"] if i + 2 < len(st) else self.length, yr, ph))
        self._chr_list = (rec, out)
        return out

    def _phase_at(self, c: float) -> str:
        ms = self.ms
        if getattr(self, "chr", None):   # as the editor's phaseAt: a station by the earlier-opened segment either side
            segs = self._chr_segments()
            at = lambda q: next((x for x in segs if x[0] <= q <= x[1]), None)
            half = self.settings["platform"] / 2
            st = next((x for x in self.stations if abs(c - x["c"]) <= half), None)
            if st is not None:
                both = [x for x in (at(st["c"] - half - 1), at(st["c"] + half + 1)) if x and x[3]]
                if both:
                    return min(both, key=lambda x: x[2] if x[2] is not None else 9999)[3]
            sg = at(c)
            if sg and sg[3]:
                return sg[3]
        name = next((p["name"] for p in self.data.get("pieces", []) if p["c0"] - 5 <= c <= p["c1"] + 5), None)
        return ((ms.get("piece_phase") or {}).get(self.id) or {}).get(name) or (ms.get("line_phase") or {}).get(self.id) or "later"

    def phase_rules(self, c: float, ph: Optional[str] = None) -> dict:
        if ph is None and getattr(self, "ms", None):
            ph = self._phase_at(c)
        p = (self.ms["phases"].get(ph) or self.ms["phases"]["later"]) if getattr(self, "ms", None) else {}
        return {"cc_max": p.get("cc_max", self.settings["shallowMax"]), "min_drive": p.get("min_drive", 300.0),
                "deep_from": p.get("deep_from", self.settings["deepBelow"]), "tbm": p.get("tbm", ph in ("3", "later"))}

    def _point_type(self, c: float, z: float) -> dict:
        # a station is one type, whatever its depth (Ben, 30 October; as the editor): the platform centre's
        half = self.settings["platform"] / 2
        st = next((s for s in self.stations if abs(c - s["c"]) <= half), None)
        if st is not None and abs(c - st["c"]) > 1e-6:
            q = dict(self._point_type(st["c"], float(self.rail_at(st["c"]))))
            if "cls" not in q:
                q["stn"] = True
            return q
        rv = self.river_at(c)
        if rv and not self.settings.get("legacy_structures") and not self.along_shore(rv):   # a river crossing: a bridge or a sunk box (Ben, 30 October), in a covered way too
            return {"t": "elevated" if z >= self.pool() + 1 else "sunk"}
        sec0 = self.canon_at(c)
        if sec0 and sec0["m"] == "covered":
            s0 = self.surface_at(c)
            return {"t": "elevated" if math.isfinite(s0) and z - s0 >= self.settings["elevAbove"] else "cutcover"}
        if self.river_at(c):
            return {"t": "elevated" if z >= self.pool() + 1 else "deep"}
        g = float(self.ground_at(c))
        if not math.isfinite(g):
            return {"t": "atgrade"}
        if z - g >= self.settings["elevAbove"]:
            return {"t": "elevated"}
        d = g - z
        if d < self.settings["coverBelow"]:
            return {"t": "atgrade"}
        # portal ramps: rail less than a box height down is an open trough (Metro 4.6 m; RER the envelope, Ben 2026-10-28)
        if d < (float(self.settings["envelope"]) if self.is_rer else self.settings.get("trough_override", METRO_ST["box"]["top"])):
            return {"t": "trough"}
        sec = self.canon_at(c)
        if not sec and not self.is_rer and getattr(self, "ms", None):
            R, tube = self.phase_rules(c), self.struct_for("shield", c)
            shield_from = tube["top"] + tube["od"]
            if self.in_station(c):   # a station is one type: by its depth at the platform centre (Ben, 29 October)
                half = self.settings["platform"] / 2
                st = next(s for s in self.stations if abs(c - s["c"]) <= half)
                gs = float(self.ground_at(st["c"]))
                ds = gs - self.rail_at(st["c"]) if math.isfinite(gs) else d
                return {"t": "cutcover" if ds <= R["cc_max"] else ("deep" if R["tbm"] else "shield"), "stn": True}   # by the cut-and-cover limit (Ben, 31 October)
            return {"cls": "C" if d < shield_from else "B" if d > R["cc_max"] else "E", "d": d, "deep": d >= R["deep_from"],
                    "ph": self._phase_at(c), "R": R, "shield_from": shield_from}
        m = sec["m"] if sec else ("deep" if d >= self.settings["deepBelow"] else "shallow")
        if m == "canal":
            return {"t": "cutcover"}
        # too shallow to bore: built cut and cover
        if self.is_rer:
            if d < self.bore_crown() + self.min_cover():
                return {"t": "cutcover"}
        else:
            sc = self.struct_for("deep" if m == "deep" else "shield", c)
            if d - sc["top"] < self.req_cover(sc, z + sc["top"]):
                return {"t": "cutcover"}
        if m == "deep":
            return {"t": "deep"}
        return {"t": "cutcover" if self.in_station(c) else "shield"}

    def _solve_key(self):
        """what a solve of the types depends on, by value (the 31 October audit: no more id() keys, and the paints, platform
        grades and settings count): a change to any of these is a new solve"""
        return (tuple(self.st), tuple(self.sg), tuple((p["c"], p["z"]) if isinstance(p, dict) else tuple(p) for p in self.pvi),
                tuple(self.ovr), tuple(getattr(self, "tf", None) or []), getattr(self, "_ground_v", 0), self.length,
                tuple(sorted((k, v) for k, v in self.settings.items() if isinstance(v, (int, float, str, bool)))),
                tuple(s["c"] for s in self.stations))

    def stretch_types(self) -> Optional[dict]:
        """The era rules over the whole line (Metro with the structure record): types per step and the flagged pockets."""
        if self.is_rer or not getattr(self, "ms", None):
            return None
        key = self._solve_key()
        cached = getattr(self, "_types", None)
        if cached and cached["key"] == key:
            return cached
        self._solving = True   # the tube form of the last solve is not read while this one runs
        try:
            return self._stretch_types(key)
        finally:
            self._solving = False

    def _stretch_types(self, key) -> dict:
        """The Metro tunnel engine (Ben, 31 October; as the editor's solveTypes): stations by the cut-and-cover limit; boxes
        the only break points; each stretch between them one method (cut and cover within the limit, else one bored drive
        through any mined stations, one tube form and depth class, boxes at the ends to its cover, the approaches there);
        low cover inside a drive a shaft only between whole drives, else Regrade; a short leftover drive beside the sunk box
        is the bank works, shorter than its boxes an error, else one short bored piece."""
        step = float(self.data.get("step_m", 2.0))
        n = int(self.length // step) + 1
        st, ms = self.settings, self.ms
        half = st["platform"] / 2
        OPEN = ("atgrade", "trough", "elevated")
        box_top = st.get("trough_override", METRO_ST["box"]["top"])
        flags, approaches = [], []

        def runs(a, b, f):
            out, s = [], -1
            for i in range(a, b + 2):
                on = i <= b and f(P[i])
                if on and s < 0:
                    s = i
                if not on and s >= 0:
                    out.append((s, i - 1))
                    s = -1
            return out
        length = lambda a, b: P[b]["c"] - P[a]["c"] + step
        idx = lambda c: max(0, min(n - 1, int(round(c / step))))

        def base(c, z):
            r = self.river_at(c)
            if r and not self.along_shore(r):
                return {"t": "elevated", "role": "open"} if z >= self.pool() + 1 else {"t": "sunk", "role": "river"}
            sec = self.canon_at(c)
            if sec and sec["m"] == "covered":
                s0 = self.surface_at(c)
                return {"t": "elevated", "role": "open"} if math.isfinite(s0) and z - s0 >= st["elevAbove"] else {"t": "cutcover", "role": "box"}
            g = float(self.ground_at(c))
            if not math.isfinite(g):
                return {"t": "atgrade", "role": "open"}
            if z - g >= st["elevAbove"]:
                return {"t": "elevated", "role": "open"}
            d = g - z
            if d < st["coverBelow"]:
                return {"t": "atgrade", "role": "open"}
            if d < box_top:
                return {"t": "trough", "role": "open"}
            o = self.override_at(c)
            if o == "cutcover":
                return {"t": "cutcover", "role": "box", "d": d}
            if o in OPEN:
                return {"t": o, "role": "open"}
            if sec and sec["m"] == "canal":
                return {"t": "cutcover", "role": "box", "d": d}
            force = o if o in ("shield", "deep") else "bored" if r or (sec and sec["m"] in ("shallow", "deep")) else None   # a paint names its method
            return {"role": "tunnel", "d": d, "force": force}
        P = []
        def step_samples():   # the samples: anchors, tunnel points with their depth; stations one type by the cut-and-cover limit; open slivers inside a tunnel
            gc, gz = self.rail_grid()
            for i in range(n):
                c, z = float(gc[i]), float(gz[i])
                ph = self._phase_at(c)
                P.append(dict(base(c, z), c=c, z=z, ph=ph, R=self.phase_rules(c, ph)))
            # stations: one type for the whole platform, by the centre, by the cut-and-cover limit
            plats = getattr(self, "platforms_kind", None) or {}
            for s in self.stations:
                zc = float(self.rail_at(s["c"]))
                q, o, R = base(s["c"], zc), self.override_at(s["c"]), self.phase_rules(s["c"])
                g = float(self.ground_at(s["c"]))
                ds = g - zc if math.isfinite(g) else 0.0
                if o == "cutcover" or o in OPEN:
                    sd = {"t": o, "role": "box" if o == "cutcover" else "open"}
                elif o in ("shield", "deep"):
                    sd = {"t": o, "role": "mined", "painted": True}
                elif q["role"] != "tunnel":
                    sd = {"t": q["t"], "role": "open" if q["role"] == "river" else q["role"]}
                elif ds <= R["cc_max"]:
                    sd = {"t": "cutcover", "role": "box"}
                else:
                    sd = {"t": "deep" if R["tbm"] else "shield", "role": "mined"}   # the drive's method
                sd.update(s=s, ds=ds, island=sd["role"] == "box" and plats.get(s["name"]) == "island")
                ph = self._phase_at(s["c"])
                for i in range(max(0, math.ceil((s["c"] - half) / step)), min(n - 1, math.floor((s["c"] + half) / step)) + 1):
                    P[i].update(t=sd["t"], role=sd["role"], stn=sd, ph=ph, R=R)
                if sd["role"] == "box" and ds > R["cc_max"] + 0.05:
                    flags.append({"c0": s["c"] - half, "c1": s["c"] + half, "kind": "painted box station past the limit", "len": 2 * half})
            # an open sliver inside a tunnel is not a portal
            for x, y in runs(0, n - 1, lambda p: p["role"] == "open" and not p.get("stn")):
                if length(x, y) >= MIN_RUN or x == 0 or y == n - 1:
                    continue
                if P[x - 1]["role"] in ("tunnel", "mined") and P[y + 1]["role"] in ("tunnel", "mined"):
                    for i in range(x, y + 1):
                        P[i].update(role="tunnel", t=None, d=float(self.ground_at(P[i]["c"])) - P[i]["z"], force=None)
        phase_tube = lambda c: (ms["phases"].get(self._phase_at(c)) or ms["phases"]["later"])["tube"]

        def twin_at(c):
            t = phase_tube(c)
            return ("A" if self._phase_at(c) in ("1", "2") else "C") if t == "bore" else t
        tube_t = lambda k: _tube_of(ms["tubes"][k])
        bt = tube_t("bore")
        bore_need = bt["top"] + bt["od"]
        is_tun = lambda p: p["role"] == "tunnel"

        def anchor_at(j, d):   # d: from the anchor toward the stretch
            p = P[j] if 0 <= j < n else None
            if p is None:
                return {"kind": "end", "double": True}
            if p.get("stn"):
                sd = p["stn"]
                if p["role"] == "box":
                    return {"kind": "island" if sd["island"] else "side", "station": sd["s"]["name"], "sp": ms["island_box"]["spacing"] if sd["island"] else ms["box"]["spacing"],
                            "edge": sd["s"]["c"] + d * half, "double": not sd["island"]}
                return {"kind": "box", "sp": ms["box"]["spacing"], "edge": p["c"], "double": True}
            if p["role"] == "river":
                return {"kind": "river", "river": (self.river_at(p["c"]) or {}).get("name"), "sp": ms["box"]["spacing"], "edge": p["c"], "double": True}
            return {"kind": "box", "sp": ms["box"]["spacing"], "edge": p["c"], "double": True}
        extra_l = getattr(self, "approach_extra", None) or []

        def appr_len(sh, c, info):
            rmin = float((ms["phases"].get(self._phase_at(c)) or ms["phases"]["later"]).get("min_radius") or ms.get("min_radius") or 40)
            e = next((x["extra"] for x in extra_l if x["side"] == info["side"] and (x.get("station") == info["station"] if info["station"] else not x.get("station") and abs(x["c"] - info["c"]) < 20)), 0.0)
            return max(float(ms.get("approach_m") or 40), math.sqrt(4 * rmin * abs(sh))) + e

        def approach_at(i, d):   # i: the drive's end sample, d: outward
            j = i + d
            while 0 <= j < n and P[j].get("t") == "cutcover" and is_tun(P[j]) and not P[j].get("shaft"):
                j += d
            if not (0 <= j < n) or P[j]["role"] == "mined":
                return None
            an = {"kind": "box", "sp": ms["box"]["spacing"], "edge": P[j]["c"]} if P[j].get("shaft") else anchor_at(j, -d)
            if an["kind"] == "end":
                return None
            tb = ms["tubes"].get(P[i].get("tube"))
            sh = ((tb["spacing"] if tb else ms["box"]["spacing"]) - an["sp"]) / 2
            if abs(sh) < 0.01 and an["kind"] != "river":
                return None
            info = {"station": an.get("station"), "kind": an["kind"], "side": -d, "shift": sh, "c": an["edge"]}
            if an.get("river"):
                info["river"] = an["river"]
            lm = appr_len(sh, P[i]["c"], info)
            k, last = j - d, None
            while 0 <= k < n and abs(P[k]["c"] - an["edge"]) < lm + step - 1e-6 and is_tun(P[k]) and not P[k].get("shaft"):
                P[k]["t"] = "cutcover"
                P[k]["appr"] = True
                if an["kind"] == "river":
                    P[k]["bank"] = True
                last = k
                k -= d
            if 0 <= k < n and P[k]["role"] == "mined" and abs(P[k]["c"] - an["edge"]) < lm - 1e-6:
                flags.append({"c0": min(an["edge"], P[k]["c"]), "c1": max(an["edge"], P[k]["c"]), "kind": "approach runs into a station", "len": abs(P[k]["c"] - an["edge"])})
            if last is None:
                return None
            info["len"] = round(abs(P[last]["c"] - an["edge"]), 2)
            approaches.append(info)
            return info
        def step_stretches():   # each stretch between anchors: cut and cover within the limit, else one drive (tube form, launch boxes, low cover, method, approaches, leftovers)
            stretches = []
            for a0, b0 in runs(0, n - 1, lambda p: p["role"] in ("tunnel", "mined")):
                s0 = a0
                for i in range(a0 + 1, b0 + 2):
                    if i > b0 or P[i]["ph"] != P[s0]["ph"]:
                        stretches.append((s0, i - 1))
                        s0 = i
            for a, b in stretches:
                R = P[a]["R"]
                span = P[a:b + 1]
                tun = [p for p in span if is_tun(p)]
                mined = any(p["role"] == "mined" for p in span)
                forced = any(p.get("force") for p in tun)
                if not mined and not forced and all(p["d"] <= p["R"]["cc_max"] + 1e-6 for p in tun):
                    for p in tun:
                        p["t"] = "cutcover"
                    continue
                Lf = anchor_at(a - 1, 1) if a > 0 else {"kind": "end", "double": True}
                Rf = anchor_at(b + 1, -1) if b < n - 1 else {"kind": "end", "double": True}
                pt = phase_tube(P[a]["c"])
                ends2 = Lf.get("double", True) and Rf.get("double", True)
                form = "bore" if (ends2 if pt == "bore" else ends2 and not mined) else "twin"
                if form == "bore":
                    ok = lambda p: p["role"] == "mined" or bool(self.tube_form_at(p["c"])) or p["d"] >= bore_need - 0.005
                    u, v = a, b
                    while u <= v and not ok(P[u]) and P[u]["d"] <= P[u]["R"]["cc_max"]:
                        u += 1
                    while v >= u and not ok(P[v]) and P[v]["d"] <= P[v]["R"]["cc_max"]:
                        v -= 1
                    if not (u <= v and length(u, v) >= (u - a + b - v) * step and all(ok(P[i]) for i in range(u, v + 1))):
                        form = "twin"

                def tkey(p, form=form):
                    f = self.tube_form_at(p["c"]) or form
                    return "bore" if f == "bore" else twin_at(p["c"])
                need = lambda p: (lambda tb: tb["top"] + tb["od"])(tube_t(tkey(p)))
                def launch(frm, d, stop):   # the end boxes carry on, within the limit, through every spot short of cover
                    last, i = frm - d, frm
                    while i != stop + d and is_tun(P[i]) and P[i]["d"] <= P[i]["R"]["cc_max"]:
                        if P[i]["d"] < need(P[i]):
                            last = i
                        i += d
                    return last
                u = launch(a, 1, b) + 1
                v = launch(b, -1, u) - 1
                for i in list(range(a, u)) + list(range(v + 1, b + 1)):
                    P[i]["t"] = "cutcover"
                if u > v:
                    continue
                pieces = [(u, v)]
                low = runs(u, v, lambda p: is_tun(p) and p["d"] < need(p))
                if low:
                    rest = runs(u, v, lambda p: not (is_tun(p) and p["d"] < need(p)))
                    if all(length(x, y) >= P[x]["R"]["min_drive"] for x, y in rest) and all(p["d"] <= p["R"]["cc_max"] for x, y in low for p in P[x:y + 1]):
                        for x, y in low:
                            for i in range(x, y + 1):
                                P[i]["t"] = "cutcover"
                                P[i]["shaft"] = True
                            flags.append({"c0": P[x]["c"], "c1": P[y]["c"], "kind": "low cover, a shaft", "len": length(x, y), "info": True})
                        pieces = rest
                    # else the drive stays bored; its low stretches are unbuildable (below)
                for x, y in pieces:
                    ps = P[x:y + 1]
                    fd = sum(1 for p in ps if p.get("force") == "deep")
                    fs = sum(1 for p in ps if p.get("force") == "shield")
                    cls = ("deep" if fd >= fs else "shield") if fd + fs else ("deep" if P[x]["R"]["tbm"] else "shield")   # one method per drive
                    for p in ps:
                        if is_tun(p) or (p["role"] == "mined" and not p["stn"].get("painted")):
                            p["t"] = cls
                        p["tube"] = tkey(p)
                    mark = len(approaches)
                    ap = [approach_at(x, -1), approach_at(y, 1)]
                    left = sum(length(u2, v2) for u2, v2 in runs(x, y, lambda p: p["t"] in ("shield", "deep")))
                    if left >= R["min_drive"] or any(p["role"] == "mined" for p in ps):
                        continue
                    river = any(q and q["kind"] == "river" for q in ap) or any(0 <= j < n and P[j]["role"] == "river" for j in (a - 1, b + 1))
                    boxes = length(a, b) - left
                    if river or left < boxes:
                        del approaches[mark:]
                        for p in P[a:b + 1]:
                            if is_tun(p):
                                p["t"] = "cutcover"
                                p.pop("appr", None)
                                p.pop("tube", None)
                                if river:
                                    p["bank"] = True
                        over = max([p["d"] - p["R"]["cc_max"] for p in P[a:b + 1] if is_tun(p)] or [0.0])
                        if river:
                            flags.append({"c0": P[a]["c"], "c1": P[b]["c"], "kind": "bank works", "len": length(a, b), "info": True})

                    else:
                        flags.append({"c0": P[x]["c"], "c1": P[y]["c"], "kind": "short drive", "len": left, "info": True})
        def step_tidy():   # types left unset are boxes; tube paints over needed boxes flagged; open-track and box slivers absorbed
            for p in P:
                if not p.get("t"):
                    p["t"] = "cutcover"
            for x, y in runs(0, n - 1, lambda p: self.override_at(p["c"]) in ("shield", "deep") and p["t"] == "cutcover" and not p.get("stn") and not self.river_at(p["c"])):
                flags.append({"c0": P[x]["c"], "c1": P[y]["c"], "kind": "tube paint over a box", "len": length(x, y)})
            # open-track or box slivers between open track and boxes: the longer neighbour's type (tunnels and stations untouched)
            free = lambda p: not p.get("stn") and not p.get("appr") and not p.get("shaft") and p["t"] not in ("shield", "deep", "sunk")
            for _ in range(4):
                ch, R2, a2 = False, [], 0
                for i in range(1, n + 1):
                    if i == n or P[i]["t"] != P[a2]["t"]:
                        R2.append((a2, i - 1))
                        a2 = i
                for k in range(1, len(R2) - 1):
                    x, y = R2[k]
                    if length(x, y) >= MIN_RUN or not all(free(p) for p in P[x:y + 1]):
                        continue
                    (px, py), (nx, ny) = R2[k - 1], R2[k + 1]
                    if P[py]["t"] in ("shield", "deep", "sunk") or P[nx]["t"] in ("shield", "deep", "sunk"):
                        continue
                    t = P[px]["t"] if P[px]["t"] == P[nx]["t"] or py - px >= ny - nx else P[nx]["t"]
                    for i in range(x, y + 1):
                        P[i]["t"] = t
                    ch = True
                if not ch:
                    break
        def step_flags():   # notes and warnings: twin tubes under a narrow street, a spacing change inside the tunnel, a painted bore without cover
            bored = lambda p: p["t"] in ("shield", "deep") and not p.get("stn")
            streets = list(self.ctx.get("streets") or []) if getattr(self, "ctx", None) else []
            street_at = lambda c: next((r for r in streets if r[0] - 5 <= c <= r[1] + 5), None)

            def narrow(p):
                if not bored(p) or not p.get("tube") or p["tube"] == "bore":
                    return False
                s, tb = street_at(p["c"]), ms["tubes"][p["tube"]]
                return bool(s) and s[2] < tb["spacing"] + tb["outside"]
            for x, y in runs(0, n - 1, narrow):
                if length(x, y) >= 50:
                    flags.append({"c0": P[x]["c"], "c1": P[y]["c"], "kind": "twin under a narrow street", "len": length(x, y), "info": True})
            sp_k = lambda p: p.get("tube") if p["t"] in ("shield", "deep") and not p.get("appr") else None
            for i in range(1, n):
                a_, b_ = sp_k(P[i - 1]), sp_k(P[i])
                if a_ and b_ and abs(ms["tubes"][a_]["spacing"] - ms["tubes"][b_]["spacing"]) > 0.01:
                    flags.append({"c0": P[i - 1]["c"], "c1": P[i]["c"], "kind": "spacing change in the tunnel", "len": step})
            for x, y in runs(0, n - 1, lambda p: self.tube_form_at(p["c"]) == "bore" and bored(p) and not self.river_at(p["c"]) and float(self.ground_at(p["c"])) - p["z"] < bore_need - 0.005):
                if length(x, y) >= MIN_RUN:
                    flags.append({"c0": P[x]["c"], "c1": P[y]["c"], "kind": "painted bore lacks cover", "len": length(x, y)})
        def step_unbuildable():   # unbuildable as drawn: a tube short of one diameter of cover, a box past its limit; returns the ranges
            # unbuildable as drawn (paints included; as the editor): a tube short of one diameter of cover, a box past its limit
            def why(p):
                if self.river_at(p["c"]):
                    return None
                st_ = p.get("stn")
                o = self.override_at(st_["s"]["c"] if st_ else p["c"])
                t = o or p["t"]
                d = float(self.ground_at(p["c"])) - p["z"]
                if not math.isfinite(d):
                    return None
                if t in ("shield", "deep") and not st_:
                    tb = tube_t(p.get("tube") or self._tube_key(p["c"]))
                    if d < tb["top"] + tb["od"] - 0.05:
                        return "cover"
                if t == "cutcover" and not p.get("bank"):
                    sec = self.canon_at(p["c"])
                    if not (sec and sec["m"] in ("canal", "covered")) and d > p["R"]["cc_max"] + 0.05:
                        return "box"
                return None
            for p in P:
                p["_w"] = why(p)
            bad = []
            for w in ("cover", "box"):
                for x, y in runs(0, n - 1, lambda p, w=w: p["_w"] == w):
                    if bad and bad[-1]["why"] == w and P[x]["c"] - bad[-1]["c1"] <= 10:
                        bad[-1]["c1"] = P[y]["c"]
                    else:
                        bad.append({"why": w, "c0": P[x]["c"], "c1": P[y]["c"]})
            bad.sort(key=lambda b: b["c0"])
            for b in bad:
                flags.append({"c0": b["c0"], "c1": b["c1"], "kind": "unbuildable " + b["why"], "len": b["c1"] - b["c0"] + step, "error": True})
            return bad
        step_samples()
        step_stretches()
        step_tidy()
        step_flags()
        bad = step_unbuildable()
        self._types = {"key": key, "step": step, "bad": bad, "t": [p["t"] for p in P], "z": [p["z"] for p in P],
                       "tube": [(p.get("tube") if p["t"] in ("shield", "deep") else None) for p in P], "flags": flags, "approaches": approaches}
        return self._types

    def _absorb_short(self, P, step):
        """no stretch shorter than MIN_RUN outside a station (as the editor): the longer neighbour's type"""
        half = self.settings["platform"] / 2
        in_st = lambda c: any(abs(c - s["c"]) <= half for s in self.stations)
        for _ in range(4):
            R, a = [], 0
            for i in range(1, len(P) + 1):
                if i == len(P) or P[i]["t"] != P[a]["t"]:
                    R.append((a, i - 1))
                    a = i
            changed = False
            for k in range(1, len(R) - 1):
                x, y = R[k]
                if (y - x + 1) * step >= MIN_RUN or any(in_st(p["c"]) for p in P[x:y + 1]):
                    continue
                (px, py), (nx, ny) = R[k - 1], R[k + 1]
                prev, nxt = P[px]["t"], P[nx]["t"]
                t = prev if prev == nxt or py - px >= ny - nx else nxt
                for i in range(x, y + 1):
                    P[i]["t"] = t
                changed = True
            if not changed:
                break

    def open_types(self) -> dict:
        """lines without the Metro rules (RER): the point types with the short stretches absorbed"""
        key = self._solve_key()
        cached = getattr(self, "_otypes", None)
        if cached and cached["key"] == key:
            return cached
        step = float(self.data.get("step_m", 2.0))
        P = []
        gc, gz = self.rail_grid()
        for i in range(int(self.length // step) + 1):
            c, z = float(gc[i]), float(gz[i])
            q = self._point_type(c, z)
            P.append({"c": c, "z": z, "t": q.get("t") or (("deep" if q["deep"] else "shield") if q["cls"] == "B" else "cutcover")})
        if not self.settings.get("legacy_structures"):   # the 6 October page (the parity test) had no such rule
            self._absorb_short(P, step)
            # river banks: a short cut-and-cover transition between the sunk box and a bored tunnel (Ben, 30 October)
            n, lim = len(P), float((getattr(self, "ms", None) or {}).get("approach_m") or 40.0)
            for r in self.data.get("rivers", []) or []:
                for edge, d in ((r["c0"], -1), (r["c1"], 1)):
                    i = max(0, min(n - 1, int(round(edge / step))))
                    while 0 <= i < n and self.river_at(P[i]["c"]):
                        i += d
                    if not (0 <= i - d < n) or P[i - d]["t"] != "sunk":
                        continue
                    c0 = P[i - d]["c"]
                    while 0 <= i < n and P[i]["t"] in ("shield", "deep") and abs(P[i]["c"] - c0) <= lim:
                        P[i]["t"] = "cutcover"
                        i += d
        self._otypes = {"key": key, "step": step, "t": [p["t"] for p in P], "z": [p["z"] for p in P]}
        return self._otypes

    def auto_type(self, c: float, z: float) -> str:
        T = self.stretch_types() or self.open_types()
        if T:
            i = int(round(c / T["step"]))
            if 0 <= i < len(T["t"]) and abs(T["z"][i] - z) < 0.3:
                return T["t"][i]
        p = self._point_type(c, z)
        return p.get("t") or (("deep" if p["deep"] else "shield") if p["cls"] == "B" else "cutcover")

    def _era(self) -> Optional[dict]:
        return None if self.is_rer else ERA.get(self.id)

    def struct_for(self, t: str, c: float) -> dict:
        """The tunnel structure at chainage c for a tunnel type (below / top from the rail)."""
        st = self.settings
        rv = self.river_at(c)
        if t == "sunk" or (rv and t in ("cutcover", "shield", "deep") and not st.get("legacy_structures") and not self.along_shore(rv)):
            return self.sunk_box()
        if self.is_rer:
            return ({"k": "box", "below": st["invertDepth"], "top": st["envelope"]}
                    if t == "cutcover" or self.river_at(c) else {"k": "bore", "below": st["invertDepth"], "top": st["boreCrown"]})
        ms = getattr(self, "ms", None)
        if ms:   # the record: the box, else the tube of the phase the stretch was built in
            if t == "cutcover" and not self.river_at(c):
                return {"k": "box", "below": ms["box"]["below"], "top": ms["box"]["top"]}
            T = getattr(self, "_types", None)
            if T and T.get("tube") and not getattr(self, "_solving", False):   # the tube form the drive was given
                k = T["tube"][max(0, min(len(T["tube"]) - 1, int(round(c / T["step"]))))]
                if k:
                    return _tube_of(ms["tubes"][k])
            return _tube_of(ms["tubes"][self._tube_key(c)])
        if self.river_at(c) or t == "deep":
            return METRO_ST["tube"]
        if t == "cutcover":
            return METRO_ST["box"]
        return METRO_ST[(self._era() or {}).get("shield", "tube")]

    def req_cover(self, sc: dict, top_z: float) -> float:
        """Cover a structure needs over its top (top_z = its top level)."""
        if sc["k"] == "sunk":   # the band sets it (river_band)
            return 0.0
        if "minCover_override" in self.settings:
            return float(self.settings["minCover_override"])
        if self.is_rer:
            return 0.0 if sc["k"] == "box" else float(self.settings["minCover"])
        if sc["k"] == "box":
            return BOX_COVER
        return sc["od"]   # one outside diameter over every bored tube (Ben, 28 October)

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
        """River crossings out of their rule: a bridge below its clearance (kind clearance); a crossing on a bridge where it
        must be a sunk box (bridge); a sunk box above or below its band (high, low) or too high for the navigable channel (nav)."""
        step = float(self.data.get("step_m", 2.0))
        out = []
        for b in self.river_bridges():  # bridges: rail at least the navigation clearance level
            zz = self.rail_at(np.arange(b["c0"], b["c1"] + 1e-9, step))
            if len(zz) and zz.min() < b["lb"] - 0.05:
                out.append({"name": b["name"], "c0": b["c0"], "c1": b["c1"], "over": float(b["lb"] - zz.min()), "kind": "clearance"})
        st = self.settings
        for r in self.data.get("rivers", []) or []:
            if self._bridge(r) or st.get("legacy_structures"):
                continue
            B = self.river_band(r)
            if not B:
                continue
            on, mine = {}, []
            top, ceil = self.sunk_box()["top"], self.pool() - float(st["riverClearWater"])

            def hit(k, c, v):
                o = on.get(k)
                if o and c - o["c1"] <= step * 1.5:
                    o["c1"], o["over"] = c, max(o["over"], v)
                else:
                    on[k] = {"kind": k, "name": r["name"], "c0": c, "c1": c, "over": v}
                    mine.append(on[k])
            for i in range(math.ceil(r["c0"] / step), int(math.floor(r["c1"] / step)) + 1):
                c = i * step
                b = self.bed_at(c)
                if not math.isfinite(b) or b >= self.pool():   # under water only
                    continue
                z = float(self.rail_at(c))
                t = self.type_at(c, z)
                if t == "elevated":
                    hit("bridge", c, z - self.pool())
                    continue
                hi = b - top + st["riverRise"]
                if z > hi + 0.005:
                    hit("high", c, z - hi)
                lo = b - top - st["riverSink"]
                if b <= B["low"] + st["riverFlatTol"] and z < lo - 0.005:
                    hit("low", c, lo - z)
                mb = z + top + st["riverCap"]
                if B["nav"] is not None and mb > b and mb > ceil + 0.005:
                    hit("nav", c, mb - ceil)
            if "bridge" in on:   # a crossing on a bridge is one issue
                mine = [dict(on["bridge"], c0=r["c0"], c1=r["c1"])]
            out.extend(mine)
        return out

    def type_at(self, c: float, z: Optional[float] = None) -> str:
        if z is None:
            z = float(self.rail_at(c))
        # a station is one type (Ben, 30 October; as the editor): a paint over part of a platform applies to the whole
        # platform, by the paint at its centre
        half = self.settings["platform"] / 2
        st = next((s for s in self.stations if abs(c - s["c"]) <= half), None)
        if st is not None:
            o = self.override_at(st["c"])
            if o:
                return o
            if self.override_at(c):
                return self.auto_type(st["c"], float(self.rail_at(st["c"])))
        o = self.override_at(c)
        if o and o != "elevated" and not self.settings.get("legacy_structures"):
            r = self.river_at(c)
            if r and not self._bridge(r) and not self.along_shore(r):   # under a river: the sunk box, whatever the paint
                return self.auto_type(c, z)
        return o or self.auto_type(c, z)

    # ------------------------------------------------------------- context
    def context_blocks(self) -> List[dict]:
        """Other systems' structures on this line (context file): name n, short label l, kind k
        (box | trough | atgrade | viaduct | fill), chainage c0..c1, their rail p [[c, z], ...],
        heights below b / top t from their rail (t is the clear height above an open structure),
        open o, their platforms pl [[c0, c1, z], ...], source s; structure type st (embankment, arch,
        viaduct, or the kind) and, on an embankment or arch viaduct, the street openings gaps
        [[c0, c1, street], ...] along this line."""
        return list(self.ctx.get("blocks") or [])

    # ---- roads (Ben, 29-31 October; as the editor's roadChecks): the context's streets along the line [c0, c1, width,
    # name, class] and the roads it crosses [c, c0, c1, width, name, class]; class highway, major or minor
    def streets(self) -> List[list]:
        return list(self.ctx.get("streets") or []) if getattr(self, "ctx", None) else []

    def roads(self) -> List[list]:
        return list(self.ctx.get("roads") or []) if getattr(self, "ctx", None) else []

    def street_at(self, c: float) -> Optional[list]:
        return next((r for r in self.streets() if r[0] - 5 <= c <= r[1] + 5), None)

    def station_street(self, s: dict) -> dict:
        """what a station sits under: its street, the roads crossing its platform, or nothing known"""
        half = self.settings["platform"] / 2
        st = self.street_at(s["c"])
        rd = [r for r in self.roads() if r[2] >= s["c"] - half and r[1] <= s["c"] + half]
        return {"street": st, "roads": rd, "text": f"under {st[3]}" if st else f"crosses {', '.join(r[4] for r in rd)}" if rd
                else ("not under a street" if self.streets() or self.roads() else "no streets known here")}

    def road_checks(self) -> List[dict]:
        """The line against the roads it crosses: over a road the structure underside keeps the class's clearance above
        the street (roadClearHighway / Major / Minor); at grade across a road is a level crossing (the Metro never; the RER
        only on a minor street, a warning); in a trough under a road its bridge needs the clear height plus a 0.8 m deck.
        Over a road this copy uses the deck depth; the editor uses the span's girder depth (span / 10 + 0.8 m), so it can
        flag a shallow girder the copy does not (no viaduct spans here). Viaduct piers in roads are the editor's check."""
        out = []
        st = self.settings
        clear = {"highway": st["roadClearHighway"], "major": st["roadClearMajor"]}
        for r in self.roads():
            c, cls, name = r[0], r[5], r[4]
            z = float(self.rail_at(c))
            t = self.type_at(c, z)
            g = float(self.ground_at(c))
            if not math.isfinite(g):
                continue
            if t == "atgrade":
                out.append({"kind": "level crossing", "sev": "warn" if self.is_rer and cls == "minor" else "error", "c": c, "road": name, "cls": cls})
            elif t == "trough":
                need = self.open_struct(t)["top"] + 0.8
                if g - z < need - 0.02:
                    out.append({"kind": "road bridge over the trough", "sev": "error", "c": c, "road": name, "cls": cls, "short": need - (g - z)})
            elif t == "elevated":
                cl, need = z - float(st["deckDepth"]) - g, clear.get(cls, st["roadClearMinor"])
                if cl < need - 0.02:
                    out.append({"kind": "clearance over a road", "sev": "error", "c": c, "road": name, "cls": cls, "clear": cl, "need": need})
        return sorted(out, key=lambda x: x["c"])

    def open_struct(self, t: str) -> dict:
        """This line's structure when it is in the open (rail to underside, clear height above)."""
        top = OPEN_CLEAR["rer"] if self.is_rer else float((getattr(self, "ms", None) or {}).get("open_clear_height") or OPEN_CLEAR["metro"])
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
        # sustained grades only (Ben, 30 October; as the editor): a chord over the limit counts where the grade averaged
        # over the sustained length (two platform lengths) is over it too; shorter excursions are warnings
        W = min(L, float(self.settings.get("sustainedLen") or 2 * self.settings["platform"]))
        over = 0
        for k in np.where(np.abs(g) > self.settings["maxGrade"] + 0.05)[0]:
            cs = np.arange(max(0.0, vc[k] - W), max(0.0, min(L - W, vc[k + 1])) + 1e-9, 5.0)
            if len(cs) and float(np.max(np.abs(self.rail_at(cs + W) - self.rail_at(cs)) / W * 1000.0)) > self.settings["maxGrade"] + 0.05:
                over += 1
        shallow = len([x for x in self.river_breaks() if x.get("kind") != "clearance"])   # river crossings out of their band
        clashes = [x for x in self.context_clearances() if not x["ok"]]
        return {"shallow_tubes": shallow, "river_breaks": len(self.river_breaks()),
                "context_clashes": len(clashes), "road_clashes": len([x for x in self.road_checks() if x["sev"] == "error"]),
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
