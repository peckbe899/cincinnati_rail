"""SectionInput v0 from records (section 7): everything ``vertical.rail@1`` needs about one section.

Python builds the input; the engine never reads records. ``section_input(ctx, section_id)`` reads, through ``ctx``
(a job's ``PlanCtx``, or ``StoreReads`` over a store for the router and tests):

- the ``section`` (length, chainage basis, scale, grid step) and its route (for the params' scope);
- its ``profile`` (``/k/profile?parent=<section>``; a section without one solves as an empty profile);
- its ``stop`` and ``platform`` records, in stop order;
- the params ``platform_m``, ``vc_radius_m`` and ``vc_min_len_m``: ``settings.*`` for the Metro, ``settings_rer.*``
  for the RER (``settings.vcMinLen`` where the RER has none), asked for with the section's id as scope, so a value
  scoped to the section wins over its route's (the CVG Express's 204.216 m platforms), and that over the system's;
- with ``ground=True``, its ``ground_profile`` (decimetres to metres; a missing level is interpolated from its
  neighbours, since the contract carries numbers only).

The stations are the stops' platforms minus the profile's ``del``, in stop order, each at its stop's point plus the
profile's slide (``so``), with its level (``st``, null when unset) and grade (``sg``, 0 when unset, as the old page
reads a doc). The PVIs are the profile's, as ``{c_m, z_m}``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from region.core.errors import NotFound
from region.core.view import View

from .doc import pvi_points

CONTRACT = "section_input/0"
PARAMS = (("platform_m", "platform"), ("vc_radius_m", "vcRadius"), ("vc_min_len_m", "vcMinLen"))
PREFIX = {"metro": "settings", "tri": "settings_rer"}


class StoreReads:
    """``PlanCtx``'s reads over a store, for callers that are not jobs (the router, tests). ``params`` is a
    ``ParamResolver`` (default ``region.ext.rules.params.resolve``)."""

    def __init__(self, store: Any, view: View, params: Callable[..., Any] | None = None) -> None:
        from region.ext.rules.params import resolve

        self.store = store
        self.view = view
        self._params = params or resolve

    def read(self, kind: str, id: str) -> dict[str, Any] | None:
        try:
            return self.store.get(kind, id, self.view)
        except NotFound:
            return None

    def list(self, kind: str, **filters: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        after = None
        while True:
            page, after = self.store.list(kind, self.view, **filters, limit=500, after=after)
            out.extend(page)
            if after is None:
                return out

    def param(self, path: str, scope: str | None = None) -> Any:
        return self._params(self.store, self.view, path, scope)

    def file(self, uri: str) -> Any:
        from region.core import paths

        return paths.resolve(uri)


@dataclass
class Section:
    """The records one section's input is built from."""

    section: dict[str, Any]
    profile: dict[str, Any] | None
    stops: list[dict[str, Any]]
    platforms: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    ground: dict[str, Any] | None = None

    @property
    def data(self) -> dict[str, Any]:
        return self.section.get("data") or {}

    @property
    def profile_data(self) -> dict[str, Any]:
        return (self.profile or {}).get("data") or {}

    def ordered_platforms(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """``(stop, platform)`` pairs in stop order (several platforms of one stop by id)."""
        out = []
        for stop in self.stops:
            for p in self.platforms.get(stop["id"], []):
                out.append((stop, p))
        return out


def gather(ctx: Any, section_id: str, *, ground: bool = False) -> Section:
    """Read one section's records through ``ctx``; ``NotFound`` when the section does not resolve."""
    sec = ctx.read("section", section_id)
    if sec is None:
        raise NotFound(f"no section {section_id}", kind="section", id=section_id)
    profiles = sorted(ctx.list("profile", parent=section_id), key=lambda r: r["id"])
    stops = sorted(
        ctx.list("stop", parent=section_id),
        key=lambda r: ((r["data"].get("order") or 0), float(r["data"].get("c") or 0.0), r["id"]),
    )
    plats: dict[str, list[dict[str, Any]]] = {}
    for p in sorted(ctx.list("platform", parent=section_id), key=lambda r: r["id"]):
        plats.setdefault(p["data"].get("stop"), []).append(p)
    grounds = sorted(ctx.list("ground_profile", parent=section_id), key=lambda r: r["id"]) if ground else []
    return Section(sec, profiles[0] if profiles else None, stops, plats, grounds[0] if grounds else None)


def params_of(ctx: Any, section: Mapping[str, Any]) -> dict[str, float]:
    """The section's resolved params, asked for with the section's id as the scope: the resolver ranks a param
    scoped to this section above one scoped to its route, and that above the system's (9.25)."""
    data = section.get("data") or {}
    system = data.get("system")
    prefix = PREFIX.get(str(system)) if system is not None else "settings"
    if prefix is None:
        # an APEX, ORR or TV section has no params of its own yet; taking the Metro's would solve it silently with
        # another system's platforms and curves
        raise NotFound(
            f"no params for system {system!r} (params exist for {', '.join(sorted(PREFIX))})",
            kind="section",
            id=section.get("id"),
        )
    scope = section.get("id") if isinstance(section.get("id"), str) else None
    out: dict[str, float] = {}
    for name, key in PARAMS:
        try:
            out[name] = ctx.param(f"{prefix}.{key}", scope)
        except NotFound:
            if prefix == "settings":
                raise
            out[name] = ctx.param(f"settings.{key}", scope)
    return out


def ground_levels(z_dm: list[int | None]) -> list[float]:
    """Metres from decimetres; a missing level takes the straight line between its nearest neighbours (or the
    nearest one at an end)."""
    known = [(i, v / 10) for i, v in enumerate(z_dm) if v is not None]
    if not known:
        return []
    out: list[float] = []
    k = 0
    for i, v in enumerate(z_dm):
        if v is not None:
            out.append(v / 10)
            continue
        while k + 1 < len(known) and known[k + 1][0] < i:
            k += 1
        lo = known[k] if known[k][0] < i else None
        hi = next((p for p in known[k:] if p[0] > i), None)
        if lo is None:
            out.append(hi[1] if hi else known[0][1])
        elif hi is None:
            out.append(lo[1])
        else:
            t = (i - lo[0]) / (hi[0] - lo[0])
            out.append(lo[1] + t * (hi[1] - lo[1]))
    return out


def build(g: Section, params: Mapping[str, float], *, step_m: float | None = None) -> dict[str, Any]:
    """The SectionInput of gathered records with resolved params."""
    d = g.data
    prof = g.profile_data
    deleted = set(prof.get("del") or [])
    st = prof.get("st") or {}
    sg = prof.get("sg") or {}
    so = prof.get("so") or {}
    stations = []
    for stop, plat in g.ordered_platforms():
        pid = plat["id"]
        if pid in deleted:
            continue
        slide = so.get(pid)
        c = stop["data"]["c"]
        stations.append(
            {
                "platform_id": pid,
                "order": len(stations),
                "c_m": c + slide if isinstance(slide, (int, float)) else c,
                "level_m": st.get(pid),
                "grade_permille": sg.get(pid, 0),
            }
        )
    out: dict[str, Any] = {
        "contract": CONTRACT,
        "section_id": g.section["id"],
        "length_m": d["length_m"],
        "chainage_basis": d["chainage_basis"],
        "scale": d["scale"],
        "step_m": step_m if step_m is not None else d["step_m"],
        "params": dict(params),
        "stations": stations,
        "pvi": [{"c_m": c, "z_m": z} for c, z in pvi_points(prof)],
    }
    if g.ground is not None:
        gd = g.ground.get("data") or {}
        out["ground"] = {"step_m": gd["step_m"], "z_m": ground_levels(list(gd.get("z_dm") or []))}
    return out


def section_input(ctx: Any, section_id: str, *, step_m: float | None = None, ground: bool = True) -> dict[str, Any]:
    """The SectionInput v0 of one section, read through ``ctx`` (see the module doc)."""
    g = gather(ctx, section_id, ground=ground)
    return build(g, params_of(ctx, g.section), step_m=step_m)


# ------------------------------------------------------------------------------------------------- station input

STATION_CONTRACT = "station_input/0"
STRUCTURE_SEED = "repo://hub/seed/params/metro_structure.json"
"""The old hub's structure record: where a leaf the station rules read has no param in the registry (the phases'
tubes, Phase 2's deep_from and tbm, the later phase, line_phase and piece_phase as maps, tube C's rail over invert),
its value comes from here, as the old page read it (params/metro_structure)."""
ERA_1_7 = frozenset({"Line_1", "Line_2", "Line_2b", "Line_3", "Line_4", "Line_5", "Line_6", "Line_7"})
"""The lines of the 7.5 per mille platform grade limit (ERA, profiles.html 1187-1188); every other Metro line and
the CVG Express take 4 per mille (literal.ERA.sgMax.lines_8_14)."""
STATION_PARAMS = (
    ("def_depth_m", "defDepth"),
    ("elev_above_m", "elevAbove"),
    ("cover_below_m", "coverBelow"),
    ("deck_depth_m", "deckDepth"),
    ("pool_m", "poolFt"),
)
LITERALS = (
    ("slide_max_m", "literal.SLIDE_M", None),
    ("car_len_m", "literal.CAR_LEN", None),
    ("end_door_m", "literal.END_DOOR", None),
    ("plat_r_err_m", "literal.PLAT_R_ERR", None),
    ("plat_r_warn_m", "literal.PLAT_R_WARN", None),
    ("s_err_deg", "literal.DRAW.sErr", None),
    # the registry names DRAW.sWarn only in sErr's meaning ("2 deg a warning"); profiles.html 2047 has it as 2
    ("s_warn_deg", "literal.DRAW.sWarn", 2.0),
    ("tol_m", "literal.station_limit_tol", None),
    ("box_cover_m", "literal.BOX_COVER", None),
    ("hall_end_len_m", "literal.hall.end_halls_len", None),
    ("mezzanine_fraction", "literal.hall.mezzanine_fraction", None),
)
GND_W = "literal.GND_W"
STREET_PAD_M = 5.0
"""A street matched to a crossing runs this far past its ends (crossGround, profiles.html 680)."""
PHASES = ("1", "2", "3", "later")
CANON_SECTIONS: dict[str, list[dict[str, Any]]] = {
    "Line_1": [
        {"a": "University", "b": "Pennsylvania Station", "m": "shallow"},
        {"a": "Central Ave", "aIn": False, "b": "University", "m": "deep"},
    ],
    "Line_2": [
        {"a": "Zoo", "b": "Roebling", "m": "shallow"},
        {"a": "McMicken", "aIn": False, "b": "VA Medical Center", "bIn": False, "m": "deep"},
    ],
    "Line_3": [
        {"a": "St Bernard", "b": "Baltimore", "m": "shallow"},
        {"a": "St Bernard", "b": "Genesee", "m": "canal"},
    ],
    "Line_4": [
        {"a": "Price Hill", "b": "Beecher", "m": "shallow"},
        {"a": "Price Hill", "b": "State", "bIn": False, "m": "deep"},
    ],
    "Line_5": [{"a": "Northside", "b": "Pennsylvania", "m": "shallow"}],
    "Line_6": [{"a": "UC Medical/Corryville", "b": "Public Landing", "m": "shallow"}],
}
"""The Metro canon's method sections (profiles.html 293-323, hard-coded there, with their sources): the founding
sections built by the basin method (shallow), the deep tunnels and Line 3's canal bed. Carried as the old page has
them until the canon becomes records (I2.2); the station rules read the canal bed (a box whatever its depth)."""
TUBES = ("A", "C", "bore")


def _param(ctx: Any, path: str, scope: str | None, fallback: Any = NotFound) -> Any:
    try:
        return ctx.param(path, scope)
    except NotFound:
        if fallback is NotFound:
            raise
        return fallback


def _seed_structure(ctx: Any) -> dict[str, Any]:
    from region.core import fsio

    try:
        p = ctx.file(STRUCTURE_SEED)
    except Exception:  # noqa: BLE001 - a hub without the old hub's seed solves on the registry's params alone
        return {}
    return fsio.read_json(p) if p.is_file() else {}


def _dig(doc: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(doc, Mapping) or part not in doc:
            return None
        doc = doc[part]
    return doc


def structure_of(ctx: Any, scope: str | None) -> dict[str, Any]:
    """The Metro structure values the station rules read: each leaf from its ``metro_structure.*`` param, else from
    the old hub's record (``STRUCTURE_SEED``); a later phase without its own value takes Phase 3's."""
    seed = _seed_structure(ctx)

    def leaf(path: str, default: Any = None) -> Any:
        try:
            v = ctx.param(f"metro_structure.{path}", scope)
            if not isinstance(v, str) or isinstance(_dig(seed, path), str) or _dig(seed, path) is None:
                return v
        except NotFound:
            pass
        v = _dig(seed, path)
        return default if v is None else v

    phases: dict[str, Any] = {}
    for ph in PHASES:
        src = ph if _dig(seed, f"phases.{ph}") is not None or ph != "later" else "3"
        phases[ph] = {
            "cc_max_m": float(leaf(f"phases.{src}.cc_max", 0.0)),
            "deep_from_m": float(leaf(f"phases.{src}.deep_from", 0.0)),
            "tbm": bool(leaf(f"phases.{src}.tbm", ph in ("3", "later"))),
            "tube": str(leaf(f"phases.{src}.tube", "A" if ph in ("1", "2") else "C")),
        }
    tubes = {
        t: {k: float(leaf(f"tubes.{t}.{k}", 0.0)) for k in ("inside", "outside", "rail_over_invert")} for t in TUBES
    }
    streets = leaf("subway_streets", [])
    return {
        "box_below_m": float(leaf("box.below")),
        "box_top_m": float(leaf("box.top")),
        "box_roof_underside_m": float(leaf("box.roof_underside")),
        "island_roof_underside_m": float(leaf("island_box.roof_underside")),
        "hall_clear_m": float(leaf("hall.clear")),
        "hall_roof_m": float(leaf("hall.roof")),
        "hall_cover_m": float(leaf("hall.cover")),
        "mezzanine_clear_m": float(leaf("elevated_station.mezzanine_clear_m")),
        "tubes": tubes,
        "phases": phases,
        "subway_streets": [str(s) for s in streets] if isinstance(streets, list) else [],
        "_line_phase": _dig(seed, "line_phase") or {},
        "_piece_phase": _dig(seed, "piece_phase") or {},
    }


class Chronology:
    """The Chronology record's reads the station rules make (profiles.html 1072-1106, 483): the phase of a year,
    a line's segments by chainage, a station's opening year and its phase."""

    def __init__(self, data: Mapping[str, Any] | None) -> None:
        d = data or {}
        self.segments: Mapping[str, Any] = d.get("segments") or {}
        self.stations: Mapping[str, Any] = d.get("stations") or {}
        self.phase_years: list[Any] = list(d.get("phase_years") or [])
        self.routes: dict[str, Any] = {r["id"]: r for r in d.get("routes") or [] if isinstance(r, Mapping)}
        self.present = data is not None

    def phase_of_year(self, y: Any) -> str | None:
        if y is None or not self.present:
            return None
        for a, b, p in self.phase_years:
            if a <= y <= b:
                return str(p)
        return None

    @staticmethod
    def _year(e: Mapping[str, Any]) -> int | None:
        y = e.get("year")
        return None if y is None or y == "" else int(y)

    def line_segments(self, route: str, stations: list[tuple[str, float]], length: float) -> list[dict[str, Any]]:
        """chrSegments (1077): the line's segments [{c0, c1, year, phase}] between its stations (the Chronology's
        own route when it has the line, else the stations as given, by chainage)."""
        if not self.present or len(stations) < 2:
            return []
        cr = self.routes.get(route)
        if cr:
            sys = cr.get("sys")
            st = [(str(s["name"]), float(s["c"])) for s in cr.get("stations") or []]
        else:
            sys = "cvx" if route == "CVG_Express" else "metro"
            st = sorted(stations, key=lambda s: s[1])
        out = []
        for i in range(len(st) - 1):
            x, y = sorted([st[i][0], st[i + 1][0]])
            if cr:
                segs = cr.get("segments") or []
                key = segs[i] if i < len(segs) else None
            else:
                key = f"metro|{route}|{x}|{y}" if sys == "metro" else f"{sys}|{x}|{y}"
            e = self.segments.get(key) or {} if key else {}
            yr = self._year(e)
            out.append(
                {
                    "c0": st[i][1] if i else 0.0,
                    "c1": st[i + 1][1] if i + 2 < len(st) else length,
                    "year": yr,
                    "phase": e.get("phase") or self.phase_of_year(yr),
                }
            )
        return out

    def station_year(self, line: str, name: str, *, here: str, segs: list[dict[str, Any]], c: float | None,
                     half: float) -> int | None:  # fmt: skip
        """chrStationYear (483): the station's own entry, else the earlier of the segments either side of it."""
        if not self.present:
            return None
        route = self.routes.get(line)
        sys = (
            route.get("sys")
            if route
            else ("cvx" if line == "CVG_Express" else "tri" if line.startswith("RER_") else "metro")
        )
        own = self.stations.get(f"{sys}|{name}")
        if isinstance(own, Mapping) and self._year(own) is not None:
            return self._year(own)
        years: list[int] = []
        if route:
            names = [s.get("name") for s in route.get("stations") or []]
            if name not in names:
                return None
            i = names.index(name)
            segs_k = route.get("segments") or []
            for k in (segs_k[i - 1] if i >= 1 else None, segs_k[i] if i < len(segs_k) else None):
                e = self.segments.get(k) if k else None
                if isinstance(e, Mapping) and self._year(e) is not None:
                    years.append(self._year(e))  # type: ignore[arg-type]
        elif line == here and c is not None:
            a, b = c - half - 1, c + half + 1
            for sg in segs:
                if sg["year"] is not None and (sg["c0"] <= a <= sg["c1"] or sg["c0"] <= b <= sg["c1"]):
                    years.append(sg["year"])
        return min(years) if years else None


def _piece_at(pieces: list[Any], c: float) -> str:
    for q in pieces or []:
        if isinstance(q, Mapping) and c >= float(q["c0"]) - 5 and c <= float(q["c1"]) + 5:
            return str(q.get("name") or "")
    return ""


def _phase_at(route: str, c: float, half: float, segs: list[dict[str, Any]], pieces: list[Any],
              ms: Mapping[str, Any]) -> tuple[str, str]:  # fmt: skip
    """phaseAt (1091) at a station's centre: the earlier-opened segment either side of the platform, else the
    segment at c, else the piece's phase, else the line's, else later."""
    if segs:

        def at(q: float) -> dict[str, Any] | None:
            return next((x for x in segs if x["c0"] <= q <= x["c1"]), None)

        pick = sorted(
            (x for x in (at(c - half - 1), at(c + half + 1)) if x and x["phase"]),
            key=lambda x: 9999 if x["year"] is None else x["year"],
        )
        if pick:
            return str(pick[0]["phase"]), "chronology"
        sg = next((x for x in segs if x["c0"] <= c <= x["c1"]), None)
        if sg and sg["phase"]:
            return str(sg["phase"]), "chronology"
    pp = (ms.get("_piece_phase") or {}).get(route) or {}
    pc = _piece_at(pieces, c)
    if pc in pp:
        return str(pp[pc]), "piece_phase"
    lp = (ms.get("_line_phase") or {}).get(route)
    if lp:
        return str(lp), "line_phase"
    return "later", "default"


def canon_sections(route: str, live: list[tuple[str, float]], half: float) -> list[dict[str, Any]]:
    """buildCanon (876): each canon section of the route by chainage, from its end stations' platform centres (an
    end with ``aIn``/``bIn`` false left out of it)."""
    out = []
    names = [n for n, _ in live]
    for sec in CANON_SECTIONS.get(route, []):
        if sec["a"] not in names or sec["b"] not in names:
            continue
        ca0 = live[names.index(sec["a"])][1]
        cb0 = live[names.index(sec["b"])][1]
        sign = (cb0 > ca0) - (cb0 < ca0) or 1
        ca = ca0 + (sign * half if sec.get("aIn") is False else -sign * half)
        cb = cb0 + (-sign * half if sec.get("bIn") is False else sign * half)
        out.append({"m": sec["m"], "c0": min(ca, cb), "c1": max(ca, cb)})
    return out


def phases_along(route: str, length: float, segs: list[dict[str, Any]], pieces: list[Any],
                 ms: Mapping[str, Any], step: float = 2.0) -> list[dict[str, Any]]:  # fmt: skip
    """The building phase along the running line as runs (phaseAt 1091 away from a station: the Chronology segment
    at c, else the piece's phase, else the line's, else later), sampled on the 2 m grid."""
    pp = (ms.get("_piece_phase") or {}).get(route) or {}
    lp = (ms.get("_line_phase") or {}).get(route)
    out: list[dict[str, Any]] = []
    n = int(length // step) + 1
    for i in range(n):
        c = min(i * step, length)
        sg = next((x for x in segs if x["c0"] <= c <= x["c1"]), None)
        if sg and sg["phase"]:
            ph = str(sg["phase"])
        else:
            pc = _piece_at(pieces, c)
            ph = str(pp[pc]) if pc in pp else str(lp) if lp else "later"
        if out and out[-1]["phase"] == ph:
            out[-1]["c1"] = c
        else:
            out.append({"c0": c, "c1": c, "phase": ph})
    return out


def _line_name(line: str, chron: Chronology | None = None) -> str:
    """routeName (336) as the Opening row shows it: an RER route by its short name ("RER B Highland branch" is
    "B Highland", the old page's rer/lines short), a Metro line by its id with a space ("Line 2b")."""
    if line.startswith("RER_") and chron is not None:
        name = str((chron.routes.get(line) or {}).get("name") or "")
        if name:
            name = name.removeprefix("RER ")
            for tail in (" branch", " stem"):
                name = name.removesuffix(tail)
            return name
    return line.replace("_", " ", 1)


def _gnd_lines(raw: Any) -> list[list[tuple[float, float]]]:
    """parseGnd (667) for another line's drawn ground."""
    out = []
    for L in raw if isinstance(raw, list) else []:
        if not isinstance(L, list):
            continue
        P = sorted(
            ((float(p[0]), float(p[1])) for p in L if isinstance(p, list) and len(p) >= 2),
            key=lambda p: p[0],
        )
        if len(P) >= 2 and P[-1][0] - P[0][0] > 1:
            out.append(P)
    return sorted(out, key=lambda P: P[0][0])


def _gnd_level(P: list[tuple[float, float]], c: float) -> float:
    for k in range(1, len(P)):
        if c <= P[k][0]:
            (ac, az), (bc, bz) = P[k - 1], P[k]
            return bz if bc - ac < 1e-6 else az + (bz - az) * (c - ac) / (bc - ac)
    return P[-1][1]


def cross_ground(ctx: Any, section: Mapping[str, Any], width: float) -> list[dict[str, float]]:
    """crossGround (674): the other lines' drawn ground across this line at each crossing, as wide as the other
    line's street there (``width`` where it has none)."""
    out = []
    for cr in (section.get("data") or {}).get("crossings") or []:
        other = cr.get("other")
        if not other or cr.get("oc") is None or other == section.get("id"):
            continue
        profs = sorted(ctx.list("profile", parent=other), key=lambda r: r["id"])
        if not profs:
            continue
        lines = _gnd_lines((profs[0].get("data") or {}).get("gnd"))
        if not lines:
            continue
        cxs = sorted(ctx.list("section_context", parent=other), key=lambda r: r["id"])
        streets = ((cxs[0].get("data") or {}).get("streets") or []) if cxs else []
        oc = float(cr["oc"])
        for P in lines:
            if oc < P[0][0] or oc > P[-1][0]:
                continue
            st = next((r for r in streets if r[0] - STREET_PAD_M <= oc <= r[1] + STREET_PAD_M), None)
            w = float(st[2]) if st and st[2] is not None else width
            c = float(cr["c"])
            out.append({"c0": c - w / 2, "c1": c + w / 2, "z": _gnd_level(P, oc)})
    return out


def _side_source(rec: Mapping[str, Any]) -> str:
    if (rec.get("data") or {}).get("side") not in ("side", "island"):
        return "default"
    layer = str(rec.get("layer") or "")
    return "import" if layer.startswith(("import:", "legacy:")) else "ben"


STATION_PROFILE_FIELDS = ("st", "sg", "so", "del", "stt", "gapfill", "access", "mode", "ovr", "gnd")


def station_profile(prof: Mapping[str, Any]) -> dict[str, Any]:
    """The profile's station fields as station.facts@1 reads them (the record's own values; legacy ``bored`` paints
    read as ``shield``, as alignFromDoc does)."""
    import copy

    out: dict[str, Any] = {}
    for f in STATION_PROFILE_FIELDS:
        if f not in prof:
            continue
        v = copy.deepcopy(prof[f])
        if f == "ovr":
            v = [[float(o[0]), float(o[1]), "shield" if o[2] == "bored" else o[2]] for o in v if len(o) >= 3]
        if f == "gnd":
            v = [[[float(p[0]), float(p[1])] for p in L if isinstance(p, list) and len(p) >= 2] for L in v]
        if f == "st":
            v = {k: x for k, x in v.items() if x is None or isinstance(x, (int, float))}
        out[f] = v
    return out


def station_input(ctx: Any, section_id: str, *, step_m: float | None = None) -> dict[str, Any]:
    """StationInput v0 (``station_input/0``, the input of ``station.facts@1``) of one section: its SectionInput with
    the ground, the profile's station fields, each platform with what the records say about it (side or island,
    opening year and phase, complex), the path, rivers, streets and roads, the Deck's ground runs, the other lines'
    drawn ground across this one, and the params of the station rules."""
    g = gather(ctx, section_id, ground=True)
    params = params_of(ctx, g.section)
    si = build(g, params, step_m=step_m)
    d = g.data
    route_rec = ctx.read("route", d.get("route")) if d.get("route") else None
    route = str(d.get("key"))
    system = str(d.get("system"))
    scope = g.section["id"]
    metro = system == "metro"
    prefix = PREFIX.get(system, "settings")
    sp: dict[str, Any] = {"platform_m": float(params["platform_m"])}
    for name, key in STATION_PARAMS:
        sp[name] = float(_param(ctx, f"{prefix}.{key}", scope, None) or ctx.param(f"settings.{key}", scope))
    if metro:
        sg_path = "literal.ERA.sgMax.lines_1_7" if route in ERA_1_7 else "literal.ERA.sgMax.lines_8_14"
    else:
        sg_path = f"{prefix}.stationMaxGrade"
    sp["sg_max_permille"] = float(ctx.param(sg_path, scope))
    sp["sg_max_param"] = sg_path
    for name, path, fallback in LITERALS:
        sp[name] = float(_param(ctx, path, scope, fallback))
    ms = structure_of(ctx, scope) if metro else None
    half = sp["platform_m"] / 2
    chrons = ctx.list("chronology")
    chron = Chronology(sorted(chrons, key=lambda r: r["id"])[0].get("data") if chrons else None)
    deleted = set(g.profile_data.get("del") or [])
    so = g.profile_data.get("so") or {}
    pairs = g.ordered_platforms()

    def slide(pid: str) -> float:
        v = so.get(pid)
        return float(v) if isinstance(v, (int, float)) else 0.0

    live_c = [
        (str(p["data"].get("name")), float(stop["data"]["c"]) + slide(p["id"]))
        for stop, p in pairs
        if p["id"] not in deleted
    ]
    segs = chron.line_segments(route, live_c, float(d["length_m"]))
    complexes = ctx.list("station_complex")
    platforms = []
    for order, (stop, p) in enumerate(pairs):
        pd = p.get("data") or {}
        name = str(pd.get("name"))
        c = float(stop["data"]["c"]) + slide(p["id"])
        year = chron.station_year(route, name, here=route, segs=segs, c=c, half=half)
        phase, phase_src = _phase_at(route, c, half, segs, d.get("pieces") or [], ms or {})
        others: list[dict[str, Any]] = []
        seen: set[str] = set()
        for cx in sorted(complexes, key=lambda r: r["id"]):
            members = (cx.get("data") or {}).get("members") or []
            if not any(m.get("line") == route and m.get("station") == name for m in members):
                continue
            for m in members:
                k = f"{m.get('line')}|{m.get('station')}"
                if (m.get("line") == route and m.get("station") == name) or k in seen:
                    continue
                seen.add(k)
                line = str(m.get("line"))
                others.append(
                    {
                        "line": line,
                        "station": str(m.get("station")),
                        "sys": str(m.get("sys") or ("rer" if line.startswith("RER_") else "metro")),
                        "name": _line_name(line, chron),
                        "year": chron.station_year(
                            line, str(m.get("station")), here=route, segs=segs, c=None, half=half
                        ),
                    }
                )
        side = pd.get("side")
        platforms.append(
            {
                "platform_id": p["id"],
                "key": str(pd.get("key")),
                "name": name,
                "order": order,
                "point_c_m": float(stop["data"]["c"]),
                "side": side if side in ("side", "island") else None,
                "side_source": _side_source(p),
                "year": year,
                "year_phase": chron.phase_of_year(year),
                "phase": phase,
                "phase_source": phase_src,
                "complex": others,
            }
        )
    cxs = sorted(ctx.list("section_context", parent=section_id), key=lambda r: r["id"])
    cxd = (cxs[0].get("data") or {}) if cxs else {}
    structure = None
    if ms is not None:
        structure = {k: v for k, v in ms.items() if not k.startswith("_")}
    return {
        "contract": STATION_CONTRACT,
        "section": si,
        "route": route,
        "system": system if route_rec is None else str((route_rec.get("data") or {}).get("system", system)),
        "path": [[float(q[0]), float(q[1]), float(q[2])] for q in d.get("path") or []],
        "profile": station_profile(g.profile_data),
        "platforms": platforms,
        "rivers": [
            {"name": str(r.get("name")), "c0": float(r["c0"]), "c1": float(r["c1"])} for r in d.get("rivers") or []
        ],
        "params": sp,
        "structure": structure,
        "streets": [
            [float(r[0]), float(r[1]), float(r[2] or 0), str(r[3]), str(r[4])] for r in cxd.get("streets") or []
        ],
        "roads": [
            [float(r[0]), float(r[1]), float(r[2]), float(r[3] or 0), str(r[4]), str(r[5])]
            for r in cxd.get("roads") or []
        ],
        "ground_add": [{"i0": int(r["i0"]), "v": [float(x) for x in r["v"]]} for r in cxd.get("add") or []],
        "ground_cap": [{"i0": int(r["i0"]), "v": [float(x) for x in r["v"]]} for r in cxd.get("cap") or []],
        "cross_ground": cross_ground(ctx, g.section, float(_param(ctx, GND_W, scope, 15.0))),
        "canon": canon_sections(route, live_c, half) if metro else [],
        "phases_along": phases_along(route, float(d["length_m"]), segs, d.get("pieces") or [], ms) if ms else [],
    }


__all__ = [
    "CONTRACT",
    "PARAMS",
    "STATION_CONTRACT",
    "Chronology",
    "Section",
    "StoreReads",
    "build",
    "cross_ground",
    "gather",
    "ground_levels",
    "params_of",
    "section_input",
    "station_input",
    "station_profile",
    "structure_of",
]
