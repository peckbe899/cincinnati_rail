"""SectionSolveInput v0 (``section_solve_input/0``, the input of ``section.solve@1``) from records, and the neighbour
view one line gives the lines that cross it (claude/hub_maps/engine_port_plan.md, sections 3 and 3.3).

``section_solve_input(ctx, section_id, neighbours=...)`` reads, through ``ctx`` (a job's ``PlanCtx`` or
``StoreReads``), what ``station_input`` reads (the section, its profile, stops, platforms, ground, Chronology, station
complexes, context, params) plus:

- every setting the solve reads (``settings.*``, or ``settings_rer.*`` with ``settings.*`` where the RER has none),
  each by the page's name, the pool once in metres;
- the page's literals (``literal.*``), each with the page's own value where the registry has no number (the plan's
  section 3.4 lists them; the lead rules them);
- the Metro structure record resolved for the route: each leaf of the old hub's record from its
  ``metro_structure.*`` param where there is one, ``line_phase`` and ``piece_phase`` for the route;
- the canon: ``canon_metro.json`` beside this module, the page's CANON transcribed (293-323) until the canon kind
  lands, read through ``ctx.file`` so its hash is in the key;
- the rivers with their canon params (``canon.rivers.<name>.*``: navigable, bed below the pool);
- the context's streets, roads, Deck runs and blocks (``attrs.blocks`` until section_context v2);
- the crossings that name a line (``wid``) and its chainage there; the neighbours are given by the caller (the
  ``profiles.neighbour`` jobs' results), never read here, so this input does not depend on another line's records;
- the Chronology table for the line (its segments and phase years) and Ben's access choices (for the halls).

``neighbour_view(ctx, section_id, levels)`` is what another line's solve reads of this one: its live stations with
their rail levels (the profile's, else ``levels``, the level solver's for this line), bend points, drawn ground,
streets, ready flag, phase and the settings the structure guess reads.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from region.core.errors import NotFound

from .doc import pvi_points
from .inputs import (
    ERA_1_7,
    PREFIX,
    Chronology,
    _on_grid,
    _param,
    _seed_structure,
    gather,
    ground_info,
    merge_ground,
    params_of,
    station_profile,
)

CONTRACT = "section_solve_input/0"
CANON_FILE = "repo://region/ext/profiles/canon_metro.json"

SETTINGS = (
    "maxGrade",
    "platform",
    "defDepth",
    "elevAbove",
    "coverBelow",
    "deepBelow",
    "shallowMax",
    "deckDepth",
    "vcRadius",
    "vcMinLen",
    "drainMin",
    "curveK",
    "stationMaxGrade",
    "fillSlope",
    "groundWarn",
    "groundSustain",
    "groundMax",
    "sustainedLen",
    "riverRoof",
    "riverSink",
    "riverRise",
    "riverFlatTol",
    "riverClearWater",
    "riverCap",
    "roadClearHighway",
    "roadClearMajor",
    "roadClearMinor",
)
"""The settings by the page's names (profiles.html 277); poolFt is read apart and sent as ``pool`` in metres."""
RER_SETTINGS = ("envelope", "boreCrown", "invertDepth", "minCover", "surfStep")

LITERALS: tuple[tuple[str, str | None, float], ...] = (
    ("MIN_RUN", "literal.MIN_RUN", 20),
    ("BOX_COVER", "literal.BOX_COVER", 0.6),
    ("SEP_GAP", "literal.SEP_GAP", 0.5),
    ("BED_DEPTH", "literal.BED_DEPTH", 0.8),
    ("VIA_SPAN", "literal.VIA_SPAN", 25),
    ("VIA_CLEAR", "literal.VIA_CLEAR", 7),
    ("RIVER_SPAN", "literal.RIVER_SPAN", 120),
    ("GIRDER_MAX", "literal.GIRDER_MAX", 40),
    ("girder.ratio", None, 10),  # literal.girder_soffit is the expression "span / 10 + 0.8" (no number)
    ("girder.add", None, 0.8),
    ("trussRatio", None, 8),  # literal.truss_depth is "span / 8"
    ("DECK_ON", None, 5),  # no param (864)
    ("GND_W", "literal.GND_W", 15),
    ("SLIDE_M", "literal.SLIDE_M", 150),
    ("CAR_LEN", "literal.CAR_LEN", 15.56),
    ("END_DOOR", "literal.END_DOOR", 5.4),
    ("PLAT_R_ERR", "literal.PLAT_R_ERR", 600),
    ("PLAT_R_WARN", "literal.PLAT_R_WARN", 3000),
    ("DRAW.single", "literal.DRAW.single", 5),
    ("DRAW.nb", None, 2),  # no param
    ("DRAW.kink", "literal.DRAW.kink", 10),
    ("DRAW.kinkSeg", None, 10),  # no param
    ("DRAW.back", "literal.DRAW.back", 90),
    ("DRAW.sErr", "literal.DRAW.sErr", 5),
    ("DRAW.sWarn", None, 2),  # no param (named in sErr's meaning)
    ("openClear", "literal.OPEN_CLEAR.metro", 4.2),
    ("bridgeAbovePool", "literal.bridge_above_pool", 1),
    ("autoTypeRailTol", "literal.autoType_rail_tol", 0.3),
    ("drainageMinLen", "literal.drainage_min_len", 60),
    ("radii.step", None, 10),  # the 10 m check grid (a sampling step)
    ("radii.window", "literal.radii_window", 40),
    ("approachHold", "literal.approach_K_window", 40),
    ("coverHardFallback", "literal.cover_hard_fallback", 0.5),
    ("minDriveFallback", "literal.min_drive_fallback", 300),
    ("minRadiusFallback", "literal.min_radius_fallback", 40),
    ("portalMinFallback", "literal.portal_min_fallback", 100),
    ("approachFallback", None, 40),  # no param (1293)
    ("tubeStreetNoteLen", "literal.tube_street_note_len", 50),
    ("fillOver", "literal.fill_over", 0.02),
    ("fillBand.above", "literal.fill_band", 0.3),
    ("fillBand.below", None, 0.5),  # no param (1715)
    ("platformOverlap", None, 0.5),  # literal.platform_overlap holds a sentence; the page's 0.5 (2101)
    ("limitTol", "literal.station_limit_tol", 0.05),
    ("lowCoverMinShort", "literal.low_cover_min_short", 0.05),
    ("hall.endHallsLen", "literal.hall.end_halls_len", 25),
    ("hall.mezzanineFraction", "literal.hall.mezzanine_fraction", 0.6),
    ("regradeMargin", "literal.regrade_margin", 0.3),
    ("regradeReserve", "literal.regrade_grade_reserve", 2),
)
"""Each literal of ``PortLiterals``: its param, and the page's value where the registry has no number."""

PHASES = ("1", "2", "3", "later")
TUBES = ("A", "C", "bore")


class Memo:
    """``ctx`` with its params remembered for one build: the resolver lists the param records on every call, and one
    input reads some 200 params. Every other read goes to ``ctx`` (a job's reads are still recorded, once each)."""

    def __init__(self, ctx: Any) -> None:
        self._ctx = ctx
        self._params: dict[tuple[str, str | None], Any] = {}

    def param(self, path: str, scope: str | None = None) -> Any:
        import copy

        k = (path, scope)
        if k not in self._params:
            try:
                self._params[k] = (True, self._ctx.param(path, scope))
            except NotFound as e:
                self._params[k] = (False, e)
        ok, v = self._params[k]
        if not ok:
            raise v
        return copy.deepcopy(v)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ctx, name)


def memo(ctx: Any) -> Any:
    return ctx if isinstance(ctx, Memo) else Memo(ctx)


def _num(ctx: Any, path: str | None, scope: str | None, fallback: float) -> float:
    if path is None:
        return float(fallback)
    v = _param(ctx, path, scope, None)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else float(fallback)


def literals_of(ctx: Any, scope: str | None, *, rer: bool = False) -> dict[str, Any]:
    """``PortLiterals`` from the registry (see ``LITERALS``)."""
    out: dict[str, Any] = {}
    for name, path, fallback in LITERALS:
        if rer and name == "openClear":
            path, fallback = "literal.OPEN_CLEAR.rer", 5.8
        v = _num(ctx, path, scope, fallback)
        if name == "radii.window":
            step = out["radii"]["step"]
            out["radii"]["h"] = v / step
            continue
        head, _, tail = name.partition(".")
        if tail:
            out.setdefault(head, {})[tail] = v
        else:
            out[name] = v
    return out


def settings_of(ctx: Any, system: str, scope: str | None) -> dict[str, Any]:
    """``PortSettings``: each setting by the page's name, the system's param first (``settings_rer.*`` on the RER),
    else the Metro's."""
    prefix = PREFIX.get(system, "settings")

    def get(key: str) -> float:
        v = _param(ctx, f"{prefix}.{key}", scope, None)
        if v is None and prefix != "settings":
            v = _param(ctx, f"settings.{key}", scope, None)
        if v is None:
            raise NotFound(f"no param {prefix}.{key}", kind="param", id=f"{prefix}.{key}")
        return float(v)

    out: dict[str, Any] = {k: get(k) for k in SETTINGS}
    out["pool"] = get("poolFt")  # the resolver gives the param in metres (settings.poolFt is recorded in ft)
    if system == "tri":
        out["rer"] = {k: get(k) for k in RER_SETTINGS}
    return out


def structure_params(ctx: Any, route: str, scope: str | None) -> dict[str, Any] | None:
    """``StructureParams``: the old hub's structure record with each leaf from its ``metro_structure.*`` param where
    the registry has a number (or flag, or word) for it; ``line_phase`` and ``piece_phase`` for the route."""
    seed = _seed_structure(ctx)
    if not seed:
        return None

    def leaf(path: str, default: Any) -> Any:
        v = _param(ctx, f"metro_structure.{path}", scope, None)
        if v is not None and type(v) is type(default):
            return v
        if v is not None and isinstance(default, float) and isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        return default

    def walk(node: Any, path: str) -> Any:
        if isinstance(node, Mapping):
            return {k: walk(v, f"{path}.{k}" if path else k) for k, v in node.items() if not k.endswith("about")}
        if isinstance(node, bool) or isinstance(node, str):
            return leaf(path, node)
        if isinstance(node, (int, float)):
            return leaf(path, float(node))
        return node

    tubes = {t: walk(seed["tubes"][t], f"tubes.{t}") for t in TUBES}
    phases: dict[str, Any] = {}
    for ph in PHASES:
        src = ph if ph in seed["phases"] else "3"
        p = walk(seed["phases"][src], f"phases.{src}")
        phases[ph] = {
            "tube": str(p.get("tube", "C")),
            "cc_max": float(p["cc_max"]),
            "min_drive": float(p["min_drive"]),
            "deep_from": float(p["deep_from"]),
            "min_radius": float(p["min_radius"]),
            "grade_max": float(p["grade_max"]),
            "grade_straight": float(p["grade_straight"]),
            "straight_warn": bool(p["straight_warn"]),
            "grade_curve": None if p.get("grade_curve") is None else float(p["grade_curve"]),
            "curve_radius": float(p["curve_radius"]),
            "tbm": bool(p["tbm"]),
            "prefer": str(p["prefer"]),
        }
    box = walk(seed["box"], "box")
    island = walk(seed["island_box"], "island_box")
    hall = walk(seed["hall"], "hall")
    grades = walk(seed["grades"], "grades")
    streets = _param(ctx, "metro_structure.subway_streets", scope, None)
    if not isinstance(streets, list):
        streets = seed.get("subway_streets") or []
    lp = (seed.get("line_phase") or {}).get(route)
    return {
        "box": {k: float(box[k]) for k in ("below", "top", "roof_underside", "inside", "spacing")},
        "island_box": {"spacing": float(island["spacing"]), "roof_underside": float(island["roof_underside"])},
        "tubes": {
            t: {
                "inside": float(tubes[t]["inside"]),
                "outside": float(tubes[t]["outside"]),
                "rail_over_invert": float(tubes[t]["rail_over_invert"]),
                "spacing": float(tubes[t]["spacing"]),
                "label": str(tubes[t].get("label", t)),
            }
            for t in TUBES
        },
        "phases": phases,
        "approach_m": float(leaf("approach_m", float(seed["approach_m"]))),
        "portal_min_m": float(leaf("portal_min_m", float(seed["portal_min_m"]))),
        "min_radius": float(leaf("min_radius", float(seed["min_radius"]))),
        "cost": {"cover_hard": float(walk(seed["cost"], "cost")["cover_hard"])},
        "grades": {
            "straight_radius": float(grades["straight_radius"]),
            "straight_underground_max": None
            if grades.get("straight_underground_max") is None
            else float(grades["straight_underground_max"]),
        },
        "hall": {k: float(hall[k]) for k in ("clear", "roof", "cover")},
        "mezzanine_clear_m": float(
            walk(seed.get("elevated_station") or {}, "elevated_station").get("mezzanine_clear_m", 3.5)
        ),
        "open_clear_height": float(leaf("open_clear_height", float(seed["open_clear_height"]))),
        "subway_streets": [str(s) for s in streets],
        "line_phase": str(lp) if lp else None,
        "piece_phase": {k: str(v) for k, v in ((seed.get("piece_phase") or {}).get(route) or {}).items()},
    }


def canon_of(ctx: Any, route: str) -> dict[str, Any]:
    """The route's canon (``CanonRecord``): the transcription's entry, normalised; empty where it has none."""
    from region.core import fsio

    try:
        p = ctx.file(CANON_FILE)
    except Exception:  # noqa: BLE001 - a hub without the file solves with no canon
        p = None
    doc = fsio.read_json(p) if p is not None and p.is_file() else {}
    r = (doc.get("lines") or {}).get(route) or {}
    return {
        "sections": [
            {
                "a": s["a"],
                "b": s["b"],
                "aIn": s.get("aIn") is not False,
                "bIn": s.get("bIn") is not False,
                "m": s["m"],
                "src": str(s.get("src") or ""),
            }
            for s in r.get("sections") or []
        ],
        "fixed": r.get("fixed") or {},
        "modes": r.get("modes") or {},
        "locked": r.get("locked") or [],
        "bridges": r.get("bridges") or {},
        "decks": r.get("decks") or [],
    }


def _canon_river(ctx: Any, name: str, scope: str | None) -> tuple[float | None, bool, bool]:
    bed = _param(ctx, f"canon.rivers.{name}.bed_below_pool_m", scope, None)
    nav = _param(ctx, f"canon.rivers.{name}.navigable", scope, None)
    cov = _param(ctx, f"canon.rivers.{name}.in_covered_way", scope, None)
    return (None if bed is None else float(bed)), bool(nav), bool(cov)


def _chronology(ctx: Any) -> Chronology:
    chrons = ctx.list("chronology")
    return Chronology(sorted(chrons, key=lambda r: r["id"])[0].get("data") if chrons else None)


def _line_phase(ctx: Any, route: str) -> str | None:
    seed = _seed_structure(ctx)
    lp = (seed.get("line_phase") or {}).get(route) if seed else None
    return str(lp) if lp else None


def _context(ctx: Any, section_id: str) -> dict[str, Any]:
    cxs = sorted(ctx.list("section_context", parent=section_id), key=lambda r: r["id"])
    return (cxs[0].get("data") or {}) if cxs else {}


def section_solve_input(
    ctx: Any, section_id: str, *, neighbours: Mapping[str, Any] | None = None, step_m: float | None = None
) -> dict[str, Any]:
    """SectionSolveInput v0 of one section (see the module doc). ``neighbours`` by the other line's key (``wid``)."""
    from .inputs import station_input

    ctx = memo(ctx)
    si = station_input(ctx, section_id, step_m=step_m, cross=False)
    g = gather(ctx, section_id, ground=True)
    d = g.data
    route = str(d.get("key"))
    system = str(d.get("system"))
    scope = g.section["id"]
    metro = system == "metro"
    sys = "rer" if system == "tri" else "cvx" if route == "CVG_Express" else "metro"
    params = params_of(ctx, g.section)
    settings = settings_of(ctx, system, scope)
    settings["platform"] = float(params["platform_m"])
    settings["vcRadius"] = float(params["vc_radius_m"])
    settings["vcMinLen"] = float(params["vc_min_len_m"])
    step = float(step_m if step_m is not None else d["step_m"])
    length = float(d["length_m"])
    n = int(math.floor(length / step + 1e-9)) + 1
    gd = (g.ground or {}).get("data") or {}
    z_dm = list(gd.get("z_dm") or [])
    dem: list[float | None] = [None if v is None else v / 10 for v in z_dm[:n]]
    dem += [None] * (n - len(dem))
    prof = g.profile_data
    sp = station_profile(prof)
    year_of = {p["platform_id"]: p["year"] for p in si["platforms"]}
    platforms = []
    for p in si["platforms"]:
        yr = p["year"]
        cx = p["complex"]
        platforms.append(
            {
                "platform_id": p["platform_id"],
                "key": p["key"],
                "name": p["name"],
                "order": p["order"],
                "point_c": p["point_c_m"],
                "side": p["side"] or "side",
                "sideSet": p["side_source"] != "default",
                "year": yr,
                "yearPhase": p["year_phase"] if p["year_phase"] in ("1", "2", "3", "later") else None,
                "transferAtOpen": yr is not None
                and any(
                    m["sys"] == "metro" and m["line"] != route and m["year"] is not None and m["year"] <= yr for m in cx
                ),
                "interchangeAtOpen": yr is not None and any(m["year"] is not None and m["year"] <= yr for m in cx),
                "trunk": False,
            }
        )
    del year_of
    doc = None
    if g.profile is not None:
        doc = {
            "st": {k: v for k, v in (sp.get("st") or {}).items()},
            "sg": {k: float(v) for k, v in (sp.get("sg") or {}).items() if isinstance(v, (int, float))},
            "so": {k: float(v) for k, v in (prof.get("so") or {}).items() if isinstance(v, (int, float))},
            "del": [str(x) for x in prof.get("del") or []],
            "pvi": [[c, z] for c, z in pvi_points(prof)],
            "ovr": sp.get("ovr") or [],
            "stt": {k: str(v) for k, v in (prof.get("stt") or {}).items()},
            "tf": [[float(o[0]), float(o[1]), str(o[2])] for o in prof.get("tf") or [] if len(o) >= 3],
            "shafts": [float(c) for c in prof.get("shafts") or [] if isinstance(c, (int, float))],
            "gnd": sp.get("gnd") or [],
            "gapfill": [str(x) for x in prof.get("gapfill") or []],
            "mode": {k: v for k, v in (prof.get("mode") or {}).items() if v in ("under", "surface")},
            "ready": bool(prof.get("ready")),
            "frame": _frame(prof.get("frame")),
        }
    sg_path = ("literal.ERA.sgMax.lines_1_7" if route in ERA_1_7 else "literal.ERA.sgMax.lines_8_14") if metro else None
    era = (
        {"shield": "tube" if route in ERA_1_7 else "bore", "sgMax": float(ctx.param(sg_path, scope))}
        if sg_path
        else None
    )
    rivers = []
    for r in d.get("rivers") or []:
        bed, nav, cov = _canon_river(ctx, str(r.get("name")), scope)
        rivers.append(
            {
                "name": str(r.get("name")),
                "c0": float(r["c0"]),
                "c1": float(r["c1"]),
                "bedBelowPool": bed,
                "navigable": nav,
                "inCoveredWay": cov,
            }
        )
    cxd = _context(ctx, section_id)
    blocks = cxd.get("blocks") or (cxd.get("attrs") or {}).get("blocks") or []
    crossings = [
        {
            "c": float(x["c"]),
            "other": x.get("other"),
            "wid": str(x["wid"]),
            "oc": float(x["oc"]),
            "kind": str(x.get("kind") or ""),
            "with": str(x.get("with") or ""),
        }
        for x in d.get("crossings") or []
        if x.get("wid") and x.get("oc") is not None
    ]
    crossings.sort(key=lambda x: x["c"])
    chron = _chronology(ctx)
    table = None
    if chron.present:
        table = {
            "sys": sys if sys != "rer" else "tri",
            "segments": {
                k: {"year": v.get("year"), "phase": v.get("phase")}
                for k, v in chron.segments.items()
                if isinstance(v, Mapping) and k.startswith(f"metro|{route}|" if sys == "metro" else f"{sys}|")
            },
            "phase_years": [[float(a), float(b), str(p)] for a, b, p in chron.phase_years],
        }
    approach = _param(ctx, "station.approach_extra", scope, None)
    if not isinstance(approach, list):
        approach = _approach_seed(ctx, route)
    out: dict[str, Any] = {
        "contract": CONTRACT,
        "section_id": scope,
        "route": route,
        "system": sys,
        "length": length,
        "step": step,
        "path": si["path"],
        "pieces": [
            {"name": str(q.get("name") or ""), "c0": float(q["c0"]), "c1": float(q["c1"])}
            for q in d.get("pieces") or []
        ],
        "dem": dem,
        "platforms": platforms,
        "doc": doc,
        "settings": settings,
        "literals": literals_of(ctx, scope, rer=system == "tri"),
        "structure": structure_params(ctx, route, scope) if metro else None,
        "era": era,
        "canon": canon_of(ctx, route) if metro else canon_of(ctx, "~none"),
        "rivers": rivers,
        "context": {
            "streets": si["streets"],
            "roads": si["roads"],
            "blocks": blocks,
            "add": si["ground_add"],
            "cap": si["ground_cap"],
        },
        "crossings": crossings,
        "neighbours": dict(neighbours or {}),
        "chronology": [],
        "approachExtra": [
            {"station": e.get("station"), "side": float(e["side"]), "c": float(e["c"]), "extra": float(e["extra"])}
            for e in approach
            if isinstance(e, Mapping)
        ],
        "access": {
            pid: str(a["type"])
            for pid, a in (prof.get("access") or {}).items()
            if isinstance(a, Mapping) and a.get("type")
        },
    }
    if table is not None:
        out["chronologyTable"] = table
    return out


def _frame(f: Any) -> dict[str, Any] | None:
    if not isinstance(f, Mapping) or not isinstance(f.get("point_c"), Mapping):
        return None
    try:
        return {
            "length_m": float(f["length_m"]),
            "point_c": {str(k): float(v) for k, v in f["point_c"].items() if isinstance(v, (int, float))},
        }
    except (KeyError, TypeError, ValueError):
        return None


APPROACH_SEED = "repo://hub/seed/params/approach_extra.json"


def _approach_seed(ctx: Any, route: str) -> list[Any]:
    """approach_extra for the route from the old hub's params (no ``station.approach_extra`` param yet: the plan's
    section 3.4 has the lead add it)."""
    from region.core import fsio

    try:
        p = ctx.file(APPROACH_SEED)
    except Exception:  # noqa: BLE001
        return []
    if not p.is_file():
        return []
    return list((fsio.read_json(p) or {}).get(route) or [])


# ------------------------------------------------------------------------------------------------- neighbours


REFRAME_TOL_M = 0.05
"""A saved point this far from its stop's is in another frame (reframeDoc 1849; engine PORT_REFRAME_TOL_M)."""


def needs_levels(ctx: Any, section_id: str) -> bool:
    """Whether a live station of the section has no saved level (its neighbour view needs the level solver's)."""
    g = gather(ctx, section_id)
    st = g.profile_data.get("st") or {}
    deleted = set(g.profile_data.get("del") or [])
    return any(
        not isinstance(st.get(p["id"]), (int, float)) for _, p in g.ordered_platforms() if p["id"] not in deleted
    )


def frame_moved(ctx: Any, section_id: str) -> bool:
    """Whether the profile was saved against other stop points than the line's now (its ``frame``): the solve maps
    it onto them (reframeDoc, platform.tie.saved_profile_own_frame), as the old page did on load (Line 2b)."""
    g = gather(ctx, section_id)
    frame = _frame(g.profile_data.get("frame"))
    if frame is None:
        return False
    deleted = set(g.profile_data.get("del") or [])
    for stop, p in g.ordered_platforms():
        saved = frame["point_c"].get(p["id"])
        if p["id"] not in deleted and saved is not None and abs(saved - float(stop["data"]["c"])) > REFRAME_TOL_M:
            return True
    return False


def needs_design(ctx: Any, section_id: str) -> bool:
    """Whether the design the section is drawn with is not the saved profile as it stands: a station with no saved
    level (the level solver's, and with no design at all its river bend points too: Lines 10, 11 and 13), or a
    profile in another frame (Line 2b: the lines crossing it read it mapped onto the current stops, as section.solve@1
    and the old page draw it). Then the section's rail as the lines crossing it read it is its solve's."""
    return needs_levels(ctx, section_id) or frame_moved(ctx, section_id)


def design_of(out: Mapping[str, Any]) -> dict[str, Any]:
    """What a ``section.solve@1`` answer says of the design it solved, by platform id: ``source`` (saved, default,
    partial), ``note``, ``reframed``, ``defaulted``, the levels ``st``, the slid centres ``c``, the bend points
    ``pvi``. Never written as Ben's record: it is what the rail is drawn with until he edits."""
    d = out.get("design") or {}
    return {
        "source": d.get("source", "saved"),
        "note": d.get("note", "saved"),
        "reframed": bool(d.get("reframed")),
        "defaulted": list(d.get("defaulted") or []),
        "st": {s["platform_id"]: s["level"] for s in out.get("stations") or []},
        "c": {s["platform_id"]: s["c"] for s in out.get("stations") or []},
        "pvi": [{"c": float(p["c"]), "z": float(p["z"])} for p in d.get("pvi") or []],
    }


def with_design(si: Mapping[str, Any], design: Mapping[str, Any] | None) -> dict[str, Any]:
    """A SectionInput (``vertical.rail@1``'s) drawn on ``design`` (``design_of``): each station with no saved level
    at the design's, and, for a default or reframed design, the design's bend points and (reframed) its slid centres.
    A saved design in its own frame leaves the input as it is."""
    if not design or (design.get("source") == "saved" and not design.get("reframed")):
        return dict(si)
    st, cs = design.get("st") or {}, design.get("c") or {}
    stations = []
    for s in si["stations"]:
        row = dict(s)
        pid = row["platform_id"]
        if row.get("level_m") is None and isinstance(st.get(pid), (int, float)):
            row["level_m"] = float(st[pid])
        if design.get("reframed") and isinstance(cs.get(pid), (int, float)):
            row["c_m"] = float(cs[pid])
        stations.append(row)
    out = {**si, "stations": stations}
    if design.get("source") == "default" or design.get("reframed"):
        out["pvi"] = [{"c_m": p["c"], "z_m": p["z"]} for p in design.get("pvi") or []]
    return out


def neighbour_view(
    ctx: Any, section_id: str, levels: Mapping[str, Any] | None = None, *, template: bool = False
) -> dict[str, Any] | None:
    """What a crossing line's solve reads of this section (``Neighbour``; see the module doc). None while a live
    station has neither a saved level nor one in ``levels``. With ``template`` such a station is kept with its
    ``platform_id`` and a null ``rail`` for ``fill_levels`` to fill from the level solver's answer."""
    ctx = memo(ctx)
    g = gather(ctx, section_id)
    d = g.data
    route = str(d.get("key"))
    system = str(d.get("system"))
    scope = g.section["id"]
    prof = g.profile_data
    st = prof.get("st") or {}
    sg = prof.get("sg") or {}
    so = prof.get("so") or {}
    deleted = set(prof.get("del") or [])
    stations = []
    saved = True
    for stop, p in g.ordered_platforms():
        pid = p["id"]
        if pid in deleted:
            continue
        z = st.get(pid)
        if not isinstance(z, (int, float)):
            saved = False
            z = (levels or {}).get(pid)
        if not isinstance(z, (int, float)) and not template:
            return None
        slide = so.get(pid)
        c = float(stop["data"]["c"]) + (float(slide) if isinstance(slide, (int, float)) else 0.0)
        row: dict[str, Any] = {"c": c, "rail": float(z) if isinstance(z, (int, float)) else None}
        row["sg"] = float(sg.get(pid) or 0.0)
        if template:
            row["platform_id"] = pid
            row["point_c"] = float(stop["data"]["c"])
        stations.append(row)
    params = params_of(ctx, g.section)
    sett = settings_of(ctx, system, scope)
    s: dict[str, Any] = {k: sett[k] for k in ("elevAbove", "coverBelow", "deepBelow", "deckDepth")}
    if system == "tri":
        s["rer"] = {k: v for k, v in sett["rer"].items() if k != "surfStep"} | {"surfStep": sett["rer"]["surfStep"]}
        open_clear = _num(ctx, "literal.OPEN_CLEAR.rer", scope, 5.8)
    else:
        s["riverRoof"] = sett["riverRoof"]
        seed = _seed_structure(ctx)
        fallback = float(seed.get("open_clear_height") or _num(ctx, "literal.OPEN_CLEAR.metro", scope, 4.2))
        open_clear = _num(ctx, "metro_structure.open_clear_height", scope, fallback)
    cx = _context(ctx, section_id)
    gnd = []
    for L in prof.get("gnd") or []:
        pts = [{"c": float(q[0]), "z": float(q[1])} for q in L if isinstance(q, list) and len(q) >= 2]
        if pts:
            gnd.append(pts)
    return {
        "section": scope,
        "wid": route,
        "system": "rer" if system == "tri" else "cvx" if route == "CVG_Express" else "metro",
        "length_m": float(d["length_m"]),
        "platform_m": float(params["platform_m"]),
        "vc_radius_m": float(params["vc_radius_m"]),
        "vc_min_len_m": float(params["vc_min_len_m"]),
        "stations": stations,
        "pvi": [{"c": c, "z": z} for c, z in pvi_points(prof)],
        "gnd": gnd,
        "streets": [
            [float(r[0]), float(r[1]), float(r[2] or 0), str(r[3]), str(r[4])] for r in cx.get("streets") or []
        ],
        "ready": bool(prof.get("ready")),
        "source": "profile" if saved and g.profile is not None else "default",
        "phase": _line_phase(ctx, route) if system == "metro" else None,
        "settings": s,
        "open_clear_m": float(open_clear),
    }


def fill_levels(
    view: Mapping[str, Any], levels: Mapping[str, Any], design: Mapping[str, Any] | None = None
) -> dict[str, Any] | None:
    """A ``neighbour_view(template=True)`` with each unset rail from ``levels`` (platform id to level), and, when the
    line's own solve drew its default design or reframed its profile (``design``, ``design_of`` of section.solve@1's
    answer), that design's bend points and (reframed) its slid centres: the design the lines crossing it read is the
    one its own sheet draws, as on the old page. None while a station still has none."""
    reframed = bool(design and design.get("reframed"))
    centres = (design or {}).get("c") or {}
    stations = []
    for s in view["stations"]:
        z = s["rail"] if s["rail"] is not None else levels.get(s.get("platform_id"))
        if not isinstance(z, (int, float)):
            return None
        c = centres.get(s.get("platform_id")) if reframed else None
        stations.append({"c": float(c) if isinstance(c, (int, float)) else s["c"], "rail": float(z), "sg": s["sg"]})
    out = {**view, "stations": stations}
    if design is not None and (design.get("source") == "default" or reframed):
        out["pvi"] = [{"c": float(p["c"]), "z": float(p["z"])} for p in design.get("pvi") or []]
    return out


def lay_dem(
    ssi: Mapping[str, Any], plan: Mapping[str, Any], region: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """A SectionSolveInput with its ``dem`` (the surveyed ground on the section's grid, None where none) as
    ``ground.source`` says: at ``region`` the region ground, each sample it lacks from the line file; at
    ``line_file`` the line file's, each sample it lacks from the region ground. Same length as before. Returns the
    input and ``inputs.ground_info``."""
    dem = list(ssi["dem"])
    n = len(dem)
    step = float(ssi.get("step") or region["step_m"])
    on = _on_grid(list(region["z"]), float(region["step_m"]), step)[:n]
    if plan["source"] == "region":
        z, filled = merge_ground(on, dem)
    else:
        z, filled = merge_ground(dem, on)
    z = (z + [None] * n)[:n]
    missing = sum(1 for v in z if v is None)
    return {**ssi, "dem": z}, ground_info(plan, region, filled, missing)


__all__ = [
    "lay_dem",
    "fill_levels",
    "design_of",
    "frame_moved",
    "needs_design",
    "with_design",
    "CANON_FILE",
    "CONTRACT",
    "LITERALS",
    "SETTINGS",
    "canon_of",
    "literals_of",
    "needs_levels",
    "neighbour_view",
    "section_solve_input",
    "settings_of",
    "structure_params",
]
