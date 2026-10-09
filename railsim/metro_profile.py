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
                deepBelow=18.29, shallowMax=12.19, envelope=5.5, clearMin=8.0, poolFt=455.0,
                vcRadius=1500.0, minCover=2.0)
# Cover a bored tunnel needs, by the practice of the line's era (Ben's ruling); shallower is
# cut and cover. 1903-1913 basin method: shield and gallery work a few metres under the
# street (about 2 m). From the 1930s shield tubes had about one diameter of cover (Chicago
# State St 1938-43 and Dearborn 1951: 25 ft shields, floors 43-50 ft down): about 6 m.
ERA_COVER = {**{f"Line_{k}": 2.0 for k in ("1", "2", "2b", "3", "4", "5", "6", "7")},
             **{f"Line_{k}": 6.0 for k in ("8", "9", "10", "11", "12", "13", "14")}}
# RER: 35 per mille, 200 m platforms (8-car TRI) and 12 m station rail depth are canon; the
# 25 m deep-bore threshold, 7 m envelope (25 kV overhead), 3 m tube cover and 250 m surface
# bend points are starting values
RER_DEFAULTS = dict(maxGrade=35.0, platform=200.0, defDepth=12.0, elevAbove=3.0, coverBelow=3.0,
                    deepBelow=25.0, shallowMax=18.0, envelope=7.0, clearMin=9.0, poolFt=455.0,
                    surfStep=250.0, tubeCover=3.0, vcRadius=3000.0, minCover=8.5)
RER_CANON_JSON = Path(__file__).resolve().parent.parent / "data" / "profile" / "rer" / "canon.json"
SETTINGS_KEYS = {"surfaceBendPointSpacing_m": "surfStep", "tubeCover_m": "tubeCover",
                 "verticalCurveRadius_m": "vcRadius", "minBoredCover_m": "minCover", "maxGrade_permille": "maxGrade", "platform_m": "platform",
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
    canon_fixed: Dict[int, dict] = field(default_factory=dict)  # {abs | off, ref}
    canon_modes: Dict[int, str] = field(default_factory=dict)
    canon_deck: List[dict] = field(default_factory=list)
    rer_canon: dict = field(default_factory=dict)
    modes: List[str] = field(default_factory=list)  # RER station modes ('under' / 'surface')

    # ------------------------------------------------------------- loading
    @classmethod
    def load(cls, line_json, alignment_json=None, settings_json=None,
             canon_json=None, settings_override: Optional[dict] = None) -> "MetroProfile":
        data = json.loads(Path(line_json).read_text())
        rer = "RER" in data.get("system", "")
        p = cls(data, {**load_settings(settings_json, rer=rer), **(settings_override or {})})
        if rer:
            cj = Path(canon_json) if canon_json else RER_CANON_JSON
            p.rer_canon = json.loads(cj.read_text()) if cj.exists() else {}
        p._ground = np.array([np.nan if v is None else v / 10.0 for v in p.data["ground_dm"]])
        p._build_canon()
        p._apply_deck()
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

    def river_tubes(self, md: Optional[List[str]]) -> List[dict]:
        """River crossings in tube: between two underground stations, or inside a canon deep
        bore (or a covered way where the canon crosses the river in tunnel). Rail at most
        pool - bed - cover - envelope."""
        if not md:
            return []
        rivers = self.rer_canon.get("rivers") or {}
        out = []
        for r in self.data.get("rivers", []) or []:
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
            bed = info.get("bed_below_pool_m", 12.0)
            out.append({"name": r["name"], "c0": r["c0"], "c1": r["c1"],
                        "ub": self.pool() - bed - self.settings["tubeCover"] - self.settings["envelope"]})
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
        P = self.settings["platform"] + self.settings["vcRadius"] * g
        n = len(self.stations)
        md = ([modes[i] if modes and modes[i] else self.default_mode(i) for i in range(n)]
              if self.is_rer else None)
        ub, lb = [], []
        for i, s in enumerate(self.stations):
            gr = float(self.ground_at(s["c"]))
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

        tubes = self.river_tubes(md)
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
            e = self.settings["vcRadius"] * g / 2  # tube bottom half a curve beyond each bank
            for t in tubes:
                nodes += [{"c": max(0.0, t["c0"] - e), "st": False, "ub": t["ub"], "lb": -math.inf},
                          {"c": min(self.length, t["c1"] + e), "st": False, "ub": t["ub"], "lb": -math.inf}]
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
                    tube_pvi.append((float(_js_round(nd["c"])), _js_round(za * 1000) / 1000))
        self.modes = md or []
        self.pvi = sorted(self.surface_pvis(st, md) + tube_pvi) if md else []
        return st

    def surface_pvis(self, st: List[float], md: List[str]) -> List[tuple]:
        """Between two at-grade stations the rail follows the old railroad: bend points every
        surfStep on the ground smoothed over two steps, held to the grade limit both ways."""
        step = self.settings["surfStep"]
        g, L, S = self.settings["maxGrade"] / 1000.0, self.length, self.stations
        half = self.settings["platform"] / 2 + self.settings["vcRadius"] * g / 2  # clear of the transitions
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
    def _verts(self) -> List[dict]:
        half, L = self.settings["platform"] / 2, self.length
        v = []
        for i, s in enumerate(self.stations):
            z = self.st[i]
            v.append({"c": min(max(s["c"] - half, 0.0), L), "z": z, "kind": "ps", "i": i, "o": 1})
            v.append({"c": min(max(s["c"] + half, 0.0), L), "z": z, "kind": "pe", "i": i, "o": 0})
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
        key = (tuple(self.st), tuple(self.pvi), rv, self.settings["platform"])
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
                    nx[k] = rv * abs((verts[o]["z"] - verts[k]["z"]) / run) / 2
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
                dv += [{"c": v["c"] - ext[k], "z": v["z"], "kind": "x", "i": v["i"]}, v]
            elif v["kind"] == "pe" and ext[k] > 1e-6:
                dv += [v, {"c": v["c"] + ext[k], "z": v["z"], "kind": "x", "i": v["i"]}]
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
                need[k] = L[k] = rv * abs(g[k] - g[k - 1])
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
        sec = self.canon_at(c)
        m = sec["m"] if sec else ("deep" if d >= self.settings["deepBelow"] else "shallow")
        if m == "canal":
            return "cutcover"
        if d < self.settings["envelope"] + self.min_cover():  # too shallow to bore in its era
            return "cutcover"
        if m == "deep":
            return "deep"
        return "cutcover" if self.in_station(c) else "shield"

    def min_cover(self) -> float:
        """Cover a bored tunnel needs: the line's era practice (Metro) or the setting (RER)."""
        if not self.is_rer and self.id in ERA_COVER and "minCover_override" not in self.settings:
            return ERA_COVER[self.id]
        return float(self.settings.get("minCover_override", self.settings["minCover"]))

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
        shallow = 0
        for t in self.river_tubes(self.modes or None):
            zz = self.rail_at(np.arange(t["c0"], t["c1"] + 1e-9, 5.0))
            shallow += int(zz.max() > t["ub"] + 0.05)
        return {"shallow_tubes": shallow,
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
