"""Parity helpers for the railsim feature's tests and the 16-line report (plan section 3).

- ``legacy_route(stem)``: railsim's own route for a line config, built the legacy way (``line.build_route``: the KMZ,
  the track network, the Metro profile port). Read here as the reference only; the hub never reads a KMZ.
- ``legacy_route_input(route)``: that route as a RouteInput (``route_input/0``), for G1.
- ``compare(base, run)``: a RunResult against a ``tests/baseline/runtimes.json`` entry: running and trip time per
  direction, each station's arrival.
- ``decompose(...)``: the hub's run of a line, and the same RouteInput with the KMZ's curves laid on it, then in the
  KMZ route's own frame (its length, curves and station places, the hub's rail and types carried over), each against
  the baseline. What each step removes is what that class explains:
  the curves are ``geometry`` (D3, the drawn path the hub fits differs from the KMZ's), the centres ``geometry``
  (D4, the Deck stops against the KMZ placemarks); what is left after both is held to the tolerance (``same``),
  else it is ``unexplained``.
"""

from __future__ import annotations

import copy
import json
from functools import cache
from typing import Any

import numpy as np

from region.core import paths

REPO = paths.repo_root()
RUNTIMES = REPO / "tests" / "baseline" / "runtimes.json"
TOL = 0.01
"""1 %: of the running and the trip time, and a station's arrival as a share of its direction's trip time."""

STEMS = (
    "cin_line_1",
    "cin_line_2",
    "cin_line_2b",
    "cin_line_3",
    "cin_line_4",
    "cin_line_5",
    "cin_line_6",
    "cin_line_7",
    "cin_line_8",
    "cin_line_9",
    "cin_line_10",
    "cin_line_11",
    "cin_line_12",
    "cin_line_13",
    "cin_line_14",
    "cvg_express",
)
"""The 16 Metro services of the baseline (one per Metro route)."""


def route_key_of(stem: str) -> str:
    """``cin_line_6`` to ``Line_6``, ``cin_line_2b`` to ``Line_2b``, ``cvg_express`` to ``CVG_Express``."""
    if stem.startswith("cin_line_"):
        return "Line_" + stem[len("cin_line_") :]
    return "CVG_Express" if stem == "cvg_express" else stem


def runtimes(stem: str) -> dict[str, Any]:
    return json.loads(RUNTIMES.read_text(encoding="utf-8"))[stem]


@cache
def legacy_route(stem: str) -> Any:
    """railsim's ``build_route`` on the line config, as ``python -m railsim.metro`` builds it (no files written)."""
    import yaml

    from railsim import app, metro
    from railsim.line import build_route
    from railsim.operations import load_era

    user = yaml.safe_load((REPO / "configs" / "metro" / f"{stem}.yaml").read_text(encoding="utf-8"))
    era, key, _year = load_era(REPO / user["operations"], user.get("year"))
    cfg = app.deep_merge(app.deep_merge(metro.DEFAULTS, era.get("overlay", {})), user)
    key = cfg.get("train") or key
    train = app.load_library(metro.SPEC.library)[key].with_load(float(cfg.get("load_factor", 0.5)), "dry")
    return build_route(
        cfg,
        REPO,
        app.curve_design_from(cfg, train),
        app.speed_policy_from(cfg, train),
        app.profile_design_from(cfg),
        log=lambda *a: None,
    )


def legacy_route_input(route: Any, route_key: str, stem: str) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """A RouteInput of railsim's own route: its fit, its rail and structures sampled on the run grid as
    ``Route.track_data`` samples them, its stations as they stop."""
    from railsim.metro_profile import STRUCTURE, TUNNEL_STRUCTURES, TYPES

    L = route.length
    s = np.arange(0.0, L + 2.0, 2.0)
    s[-1] = L
    rail = route.profile.elevation_at(s)
    names = np.array(route.profile.structure)
    idx = np.clip(np.searchsorted(route.profile.s, s), 0, len(names) - 1)
    at = names[idx]
    inverse = {v: i for i, v in enumerate(STRUCTURE[t] for t in TYPES)}
    tunnel = np.isin(at, list(TUNNEL_STRUCTURES))
    kind = np.array(
        [
            inverse.get(n, TYPES.index("cutcover") if t else TYPES.index("atgrade"))
            for n, t in zip(at, tunnel, strict=True)
        ]
    )
    curves = [curve_dict(c, c.s_ts, c.s_sc, c.s_cs, c.s_st) for c in route.horizontal.curves]
    stops = [
        {
            "platform_id": st.name,
            "name": st.name,
            "c_m": st.s,
            "s_m": st.s,
            "platform_m": st.platform_length,
            "class": st.cls,
            "class_source": "legacy",
            "psd": st.psd,
            "dwell_s": st.dwell_override,
            "terminal": k in (0, len(route.stations) - 1),
            "reverse": st.reverse,
        }
        for k, st in enumerate(route.stations)
        if st.stop
    ]
    meta = {
        "contract": "route_input/0",
        "route_id": None,
        "route_key": route_key,
        "name": route.name,
        "config": stem,
        "section": {"section_id": None, "length_m": L, "step_m": 2.0},
        "run_grid": {"c0": 0.0, "step_m": 2.0, "n": len(s)},
        "length_m": L,
        "proj": {"lat0": route.proj.lat0, "lon0": route.proj.lon0},
        "curves": curves,
        "stops": stops,
        "removed": [],
        "restrictions": [],
        "warnings": [],
        "sources": {"curves": "legacy KMZ fit"},
    }
    arrays = {
        "s_m": s,
        "c_m": s.copy(),
        "rail_z_m": rail,
        "curvature_per_m": np.abs(route.horizontal.curvature(s)),
        "tunnel": tunnel.astype("u1"),
        "type": kind.astype("u1"),
    }
    return meta, arrays


def curve_dict(c: Any, s_ts: float, s_sc: float, s_cs: float, s_st: float) -> dict[str, Any]:
    return {
        "s_ts": float(s_ts),
        "s_sc": float(s_sc),
        "s_cs": float(s_cs),
        "s_st": float(s_st),
        "c_ts": float(s_ts),
        "c_st": float(s_st),
        "radius_m": float(c.radius),
        "spiral_m": float(c.spiral),
        "cant_m": float(c.cant),
        "deflection_rad": float(c.deflection),
        "direction": int(c.direction),
        "tangent_m": float(c.tangent),
    }


def compare(base: dict[str, Any], got: dict[str, Any]) -> dict[str, Any]:
    """Relative differences of running and trip time per baseline direction (paired with the run's direction from
    the same first station), and each station's arrival difference."""
    out = []
    dirs = list(got["directions"])
    by_origin = {str(d["stations"][0]["name"]): d for d in dirs if d.get("stations")}
    for i, b in enumerate(base["directions"]):
        # the baseline names its directions by its service's terminals; the hub's forward is rising chainage
        d = by_origin.get(str(b["stations"][0]["name"]), dirs[i])
        trip = b["trip_time_min"] * 60
        arr = {s["name"]: s["arrive_s"] for s in d["stations"]}
        stations = []
        for s in b["stations"][1:]:
            if s["name"] in arr:
                diff = arr[s["name"]] - s["arrive_s"]
                stations.append({"name": s["name"], "diff_s": round(diff, 1), "rel_own": abs(diff) / s["arrive_s"]})
        worst = max(stations, key=lambda s: abs(s["diff_s"]), default=None)
        out.append(
            {
                "dir": d["dir"],
                "running": d["running_s"] / 60 / b["running_time_min"] - 1,
                "trip": d["trip_s"] / 60 / b["trip_time_min"] - 1,
                "trip_s": trip,
                "worst_s": abs(worst["diff_s"]) if worst else 0.0,
                "worst_at": worst["name"] if worst else None,
                "missing": [s["name"] for s in b["stations"] if s["name"] not in arr],
                "extra": [s["name"] for s in d["stations"] if s["name"] not in {x["name"] for x in b["stations"]}],
                "stations": stations,
            }
        )
    return {"directions": out}


def times_within(cmp: dict[str, Any], tol: float = TOL) -> bool:
    """Running and trip time within ``tol`` in both directions, and the same stops."""
    return all(abs(d["running"]) <= tol and abs(d["trip"]) <= tol and not d["missing"] for d in cmp["directions"])


def stations_within(cmp: dict[str, Any], tol: float = TOL) -> bool:
    """Every station's arrival within ``tol`` of its direction's trip time."""
    return all(d["worst_s"] <= tol * d["trip_s"] for d in cmp["directions"])


def within(cmp: dict[str, Any], tol: float = TOL) -> bool:
    return times_within(cmp, tol) and stations_within(cmp, tol)


def _reversed(meta: dict[str, Any], legacy: Any) -> bool:
    """Whether the hub's chainage runs against the legacy route's (the KMZ route starts at the hub's far end)."""
    legacy_s = {st.name: float(st.s) for st in legacy.stations}
    pairs = [(legacy_s[s["name"]], float(s["s_m"])) for s in meta["stops"] if s["name"] in legacy_s]
    if len(pairs) < 2:
        return False
    a, b = np.array(pairs).T
    return bool(np.corrcoef(a, b)[0, 1] < 0)


def _legacy_s(legacy: Any, rev: bool) -> dict[str, float]:
    L = float(legacy.length)
    return {st.name: (L - float(st.s)) if rev else float(st.s) for st in legacy.stations}


def _anchor(meta: dict[str, Any], legacy: Any) -> tuple[Any, bool]:
    """``(f, reversed)``: a map from the legacy route's chainage (read from the hub's start when the two run against
    each other) to the hub's run chainage, through the stations both have (each station's centre is the same place
    on both lines, to the D4 metres), the ends pinned."""
    rev = _reversed(meta, legacy)
    legacy_s = _legacy_s(legacy, rev)
    pairs = sorted((legacy_s[s["name"]], float(s["s_m"])) for s in meta["stops"] if s["name"] in legacy_s)
    xs = [0.0] + [a for a, _ in pairs] + [float(legacy.length)]
    ys = [0.0] + [b for _, b in pairs] + [float(meta["length_m"])]
    xs, ys = np.maximum.accumulate(np.array(xs)), np.maximum.accumulate(np.array(ys))

    def f(v: float) -> float:
        return float(np.interp(v, xs, ys))

    return f, rev


def with_kmz_curves(meta: dict[str, Any], legacy: Any) -> dict[str, Any]:
    """The RouteInput with the KMZ fit's curves (radius, spiral, cant, deflection) laid on in its own chainage."""
    f, rev = _anchor(meta, legacy)
    L = float(legacy.length)
    out = copy.deepcopy(meta)
    curves = []
    for c in legacy.horizontal.curves:
        pts = (c.s_ts, c.s_sc, c.s_cs, c.s_st)
        if rev:
            pts = tuple(L - x for x in reversed(pts))
        curves.append(curve_dict(c, *(f(x) for x in pts)))
    out["curves"] = sorted(curves, key=lambda c: c["s_ts"])
    return out


def with_kmz_frame(
    meta: dict[str, Any], arrays: dict[str, Any], legacy: Any
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """The RouteInput in the KMZ route's own frame: its length, its curves and its stations where railsim placed
    them, with the hub's rail and structure types carried over station to station (the D3 and D4 geometry taken
    away; the rail, the types, the classes and the train left as the hub has them)."""
    f, rev = _anchor(meta, legacy)
    L = float(legacy.length)
    s = np.arange(0.0, L + 2.0, 2.0)
    s[-1] = L
    hub_s = np.array([f(x) for x in s])
    src = np.asarray(arrays["s_m"], dtype=float)
    idx = np.clip(np.searchsorted(src, hub_s), 0, len(src) - 1)
    out = copy.deepcopy(meta)
    curves = []
    for c in legacy.horizontal.curves:
        pts = (c.s_ts, c.s_sc, c.s_cs, c.s_st)
        if rev:
            pts = tuple(L - x for x in reversed(pts))
        curves.append(curve_dict(c, *pts))
    out["curves"] = sorted(curves, key=lambda c: c["s_ts"])
    legacy_s = _legacy_s(legacy, rev)
    for st in out["stops"]:
        st["s_m"] = legacy_s.get(st["name"], float(np.interp(st["s_m"], hub_s, s)))
    out["stops"].sort(key=lambda x: x["s_m"])
    out["length_m"] = L
    out["run_grid"] = {"c0": 0.0, "step_m": 2.0, "n": len(s)}
    out["section"] = {**dict(out.get("section") or {}), "length_m": L}
    new = {
        "s_m": s,
        "c_m": s.copy(),
        "rail_z_m": np.interp(hub_s, src, np.asarray(arrays["rail_z_m"], dtype=float)),
        "curvature_per_m": np.zeros_like(s),
        "tunnel": np.asarray(arrays["tunnel"])[idx],
        "type": np.asarray(arrays["type"])[idx],
    }
    return out, new


def station_offsets(meta: dict[str, Any], legacy: Any) -> dict[str, float]:
    """The hub's stop centre less the KMZ placemark railsim projected, in metres along each one's own fit, from the
    hub's start (D4)."""
    legacy_s = _legacy_s(legacy, _reversed(meta, legacy))
    return {s["name"]: round(float(s["s_m"]) - legacy_s[s["name"]], 1) for s in meta["stops"] if s["name"] in legacy_s}


def renamed(cmp: dict[str, Any]) -> bool:
    """Whether the stops the baseline has and the run lacks are as many as the run has and the baseline lacks, in
    every direction: stations named differently in the records and the KMZ (class ``design``)."""
    return all(d["missing"] and len(d["missing"]) == len(d["extra"]) for d in cmp["directions"])


def _ok(cmp: dict[str, Any], tol: float = TOL) -> bool:
    times = all(abs(d["running"]) <= tol and abs(d["trip"]) <= tol for d in cmp["directions"])
    stops = renamed(cmp) or not any(d["missing"] or d["extra"] for d in cmp["directions"])
    return times and stops and stations_within(cmp, tol)


def decompose(
    base: dict[str, Any], meta: dict[str, Any], arrays: dict[str, Any], settings: dict[str, Any], legacy: Any
) -> dict[str, Any]:
    """The hub's run, then with the KMZ's curves, then with the KMZ's curves and station centres, each compared with
    the baseline; ``classes`` names what each step explains (see the module doc)."""
    from region.ext.railsim import adapter

    steps = {
        "hub": (meta, arrays),
        "kmz_curves": (with_kmz_curves(meta, legacy), arrays),
        "kmz_curves_stations": with_kmz_frame(meta, arrays, legacy),
    }
    out: dict[str, Any] = {"steps": {}, "offsets": station_offsets(meta, legacy)}
    for name, (m, arr) in steps.items():
        run, _a = adapter.run_route(m, arr, settings)
        out["steps"][name] = {"run": run, "cmp": compare(base, run)}
    hub = out["steps"]["hub"]["cmp"]
    classes = ["design: stations named otherwise in the records"] if renamed(hub) else []
    if _ok(hub):
        classes.append("same")
    elif _ok(out["steps"]["kmz_curves"]["cmp"]):
        classes.append("geometry: curves (D3)")
    elif _ok(out["steps"]["kmz_curves_stations"]["cmp"]):
        classes.append("geometry: curves and station centres (D3, D4)")
    out["classes"] = classes
    out["unexplained"] = not any(c == "same" or c.startswith("geometry") for c in classes)
    return out


__all__ = [
    "STEMS",
    "TOL",
    "compare",
    "decompose",
    "legacy_route",
    "legacy_route_input",
    "renamed",
    "route_key_of",
    "runtimes",
    "station_offsets",
    "stations_within",
    "times_within",
    "with_kmz_curves",
    "with_kmz_frame",
    "within",
]
