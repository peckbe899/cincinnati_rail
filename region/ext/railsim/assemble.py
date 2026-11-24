"""The RouteInput (``route_input/0``) of a route from its records and the solved section. Pure.

``route_input(parts, rail, types, fit)`` lays onto the run grid (``s = i * 2 m`` along the fit, as railsim's
``Route.track_data`` samples a route):

- the rail: the solved rail (``vertical.rail@1``, on the section grid) at each run sample's section chainage;
- the tunnel flags and types: the structure solve's ``type_runs`` (``section.solve@1``); cut and cover, shield,
  deep tube and sunk box are tunnels (railsim's ``TUNNEL_STRUCTURES`` through ``metro_profile.STRUCTURE``, rule
  ``run.tunnel.drag_by_structure``);
- the curvature of the fit (``route.horizontal``), spirals included;
- the stops: the live stations of the section (the stops' platforms less the profile's ``del``, each at its stop's
  point plus the profile's slide, rules ``run.station.removed_leaves_service`` and ``run.station.slide_moves_stop``)
  in chainage order; a removed terminal stays a stop, as railsim kept it. Forward is rising chainage.
- each stop's dwell class and PSD from the line config (the declared fallback until they are records), the
  platform length from the line config or the ``settings.platform`` param;
- the fixed restrictions of the line config (none on any Cincinnati Metro line today): by station names, or by km
  along the route; one by a KMZ segment name cannot be placed and is listed as a warning.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from . import horizontal as H

CONTRACT = "route_input/0"
GRID_M = 2.0
TYPES = ("elevated", "atgrade", "trough", "cutcover", "shield", "deep", "sunk")
"""The structure types of ``section.solve@1``; the ``type`` array holds their index."""


def _tunnel_types() -> set[str]:
    from railsim.metro_profile import STRUCTURE, TUNNEL_STRUCTURES

    return {t for t in TYPES if STRUCTURE[t] in TUNNEL_STRUCTURES}


def types_at(c: np.ndarray, runs: Sequence[Sequence[Any]]) -> np.ndarray:
    """The type index at each section chainage from ``type_runs`` (``[type, c0, c1]``, in order); a chainage before
    the first run takes the first run's, after the last the last run's."""
    if not runs:
        return np.full(len(c), TYPES.index("atgrade"), dtype="u1")
    starts = np.array([float(r[1]) for r in runs])
    idx = np.clip(np.searchsorted(starts, c, side="right") - 1, 0, len(runs) - 1)
    kinds = np.array([TYPES.index(str(r[0])) if str(r[0]) in TYPES else TYPES.index("atgrade") for r in runs])
    return kinds[idx].astype("u1")


def _length_of(d: Mapping[str, Any], key: str) -> float | None:
    from railsim.line import length_of

    v = length_of(dict(d), key)
    return None if v is None else float(v)


def stops_of(parts: Mapping[str, Any], s_of_c: np.ndarray, step_m: float) -> tuple[list[dict], list[dict], list[str]]:
    """``(stops, removed, warnings)``: the section's stations as stops on the run, in chainage order."""
    defaults = dict(parts.get("station_defaults") or {})
    info = dict(parts.get("station_info") or {})
    platform_m = parts.get("platform_m")
    rows = sorted(parts["stations"], key=lambda r: (float(r["c_m"]), r["platform_id"]))
    warnings: list[str] = []
    stops: list[dict] = []
    removed: list[dict] = []
    n = len(rows)
    known = set(info)
    for k, r in enumerate(rows):
        terminal = k in (0, n - 1)
        if r.get("removed") and not terminal:
            removed.append(
                {"platform_id": r["platform_id"], "name": r["name"], "c_m": float(r["c_m"]), "why": "removed on the profile"}
            )
            continue
        d = dict(defaults)
        d.update(info.get(r["name"]) or {})
        cls = str(d.get("class") or "standard")
        source = "config" if "class" in (info.get(r["name"]) or {}) else "default"
        if terminal and cls == "standard":
            cls, source = "terminal", "terminal"
        plat = _length_of(d, "platform_length")
        stops.append(
            {
                "platform_id": r["platform_id"],
                "name": r["name"],
                "c_m": float(r["c_m"]),
                "s_m": float(H.s_of(float(r["c_m"]), s_of_c, step_m)),
                "platform_m": plat if plat is not None else (float(platform_m) if platform_m is not None else 150.0),
                "class": cls,
                "class_source": source,
                "psd": bool(d["psd"]) if "psd" in d else None,
                "dwell_s": d.get("dwell_s"),
                "terminal": terminal,
                "removed": bool(r.get("removed")),
                "reverse": False,
            }
        )
    names = {r["name"] for r in rows}
    for name in sorted(known - names):
        warnings.append(f"the line config names a station {name!r} the records do not have")
    return stops, removed, warnings


def _restrictions(parts: Mapping[str, Any], stops: list[dict], length: float) -> tuple[list[dict], list[str]]:
    from railsim.line import speed_of
    from railsim.operations import turnout_speed

    by_name = {s["name"]: s for s in stops}
    out: list[dict] = []
    warnings: list[str] = []

    def span(r: Mapping[str, Any]) -> tuple[float, float] | None:
        if "from_km" in r or "to_km" in r:
            return float(r.get("from_km", 0.0)) * 1000, float(r.get("to_km", length / 1000)) * 1000
        if "from_station" in r or "to_station" in r:
            a, b = by_name.get(r.get("from_station")), by_name.get(r.get("to_station"))
            if a is None or b is None:
                return None
            lo, hi = sorted((a["s_m"], b["s_m"]))
            return lo, hi
        return None

    for r in parts.get("restrictions") or []:
        sp = span(r)
        if sp is None:
            warnings.append(f"restriction {r.get('reason') or r} cannot be placed on the records (no km or stations)")
            continue
        if "turnout" in r:
            v, reason = turnout_speed(r["turnout"]), r.get("reason", f"turnout {r['turnout']}")
        else:
            v, reason = speed_of(dict(r), "speed"), r.get("reason", "posted")
        out.append({"s0_m": sp[0], "s1_m": sp[1], "v_ms": float(v), "reason": str(reason), "rule": r.get("rule")})
    ta = parts.get("terminal_approach")
    if ta and stops:
        v = speed_of(dict(ta), "speed")
        dist = float(_length_of(ta, "distance") or 300.0)
        for st in (stops[0], stops[-1]):
            if ta.get("stations") and st["name"] not in ta["stations"]:
                continue
            out.append(
                {
                    "s0_m": max(st["s_m"] - dist, 0.0),
                    "s1_m": min(st["s_m"] + dist, length),
                    "v_ms": float(v),
                    "reason": f"terminal approach {st['name']}",
                    "rule": None,
                }
            )
    throat = parts.get("throat") or {}
    for k, st in enumerate(stops):
        t = throat.get("terminal") if k in (0, len(stops) - 1) else None
        t = t or (throat.get("by_class") or {}).get(st["class"])
        for tier in [t] if isinstance(t, dict) else (t or []):
            half = st["platform_m"] / 2
            d = float(_length_of(tier, "distance") or 500.0)
            out.append(
                {
                    "s0_m": max(st["s_m"] - half - d, 0.0),
                    "s1_m": min(st["s_m"] + half + d, length),
                    "v_ms": float(speed_of(dict(tier), "speed")),
                    "reason": f"{st['name']} station throat",
                    "rule": None,
                }
            )
    for name in ("operating_zones", "neutral_sections", "supply_zones"):
        if parts.get(name):
            warnings.append(f"the line config's {name} are not carried on the records yet (I2.4); the run leaves them out")
    return out, warnings


def route_input(
    parts: Mapping[str, Any],
    rail: Mapping[str, Any],
    types: Sequence[Sequence[Any]],
    fit: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """``(meta, arrays)`` of the RouteInput (see the module doc).

    ``parts``: what the plan read (route, section, stations, the config's station block and restrictions, the
    platform length); ``rail``: ``{c0, step_m, rail_m}`` on the section grid; ``types``: ``type_runs``; ``fit``: the
    ``route.horizontal`` output as ``{meta, arrays}``."""
    from railsim.horizontal import Curve, HorizontalAlignment

    fm, fa = fit["meta"], fit["arrays"]
    s_of_c = np.asarray(fa["s_of_c"], dtype=float)
    step = float(fm["grid"]["step_m"])
    L = float(fm["length_m"])
    s = H.run_grid(L, GRID_M)
    c = H.c_of_s(s, s_of_c, step)
    rail_m = np.asarray(rail["rail_m"], dtype=float)
    rc = float(rail.get("c0", 0.0)) + np.arange(len(rail_m)) * float(rail["step_m"])
    z = np.interp(c, rc, rail_m)
    kind = types_at(c, types)
    tunnel_types = {TYPES.index(t) for t in _tunnel_types()}
    tunnel = np.isin(kind, list(tunnel_types)).astype("u1")
    curves = [
        Curve(
            direction=int(cv["direction"]),
            deflection=float(cv["deflection_rad"]),
            radius=float(cv["radius_m"]),
            spiral=float(cv["spiral_m"]),
            s_ts=float(cv["s_ts"]),
            s_sc=float(cv["s_sc"]),
            s_cs=float(cv["s_cs"]),
            s_st=float(cv["s_st"]),
            cant=float(cv["cant_m"]),
        )
        for cv in fm["curves"]
    ]
    curvature = np.abs(HorizontalAlignment(np.zeros((2, 2)), np.array([0.0, L]), curves, L).curvature(s))
    stops, removed, warnings = stops_of(parts, s_of_c, step)
    restrictions, more = _restrictions(parts, stops, L)
    warnings += more
    sec = parts["section"]
    route = parts["route"]
    terminals = [str(x["name"] if isinstance(x, Mapping) else x) for x in (parts.get("service_route") or [])]
    if terminals and stops:
        ends = [stops[0]["name"], stops[-1]["name"]]
        if terminals[0] == ends[1] and terminals[-1] == ends[0]:
            warnings.append(
                f"the line config runs {terminals[0]} to {terminals[-1]}; forward here is rising chainage "
                f"({ends[0]} to {ends[1]})"
            )
        elif terminals[0] != ends[0] or terminals[-1] != ends[1]:
            warnings.append(f"the line config's service runs {terminals[0]} to {terminals[-1]}; the records' ends are {ends[0]} and {ends[1]}")
    meta = {
        "contract": CONTRACT,
        "route_id": route["id"],
        "route_key": route["key"],
        "name": route["name"],
        "system": route.get("system"),
        "config": parts["config"],
        "section": {"section_id": sec["id"], "length_m": float(sec["length_m"]), "step_m": float(sec["step_m"])},
        "sections": [
            {"section_id": sec["id"], "dir": 1, "c0_m": 0.0, "c1_m": float(sec["length_m"]), "s0_m": 0.0, "s1_m": L}
        ],
        "run_grid": {"c0": 0.0, "step_m": GRID_M, "n": len(s)},
        "length_m": L,
        "scale": sec.get("scale"),
        "proj": dict(fm.get("proj") or {}),
        "curves": list(fm["curves"]),
        "stops": stops,
        "removed": removed,
        "restrictions": restrictions,
        "operating_zones": [],
        "neutral_sections": [],
        "supply_zones": [],
        "sources": {
            "rail": str(parts.get("rail_source") or "profiles.solve_section"),
            "types": "profiles.solve_structure",
            "curves": "fitted to the section path",
            "stations": "records",
            "classes": f"configs/metro/{parts['config']}.yaml",
        },
        "warnings": warnings,
    }
    arrays = {
        "s_m": s.astype("<f8"),
        "c_m": c.astype("<f8"),
        "rail_z_m": z.astype("<f8"),
        "curvature_per_m": curvature.astype("<f8"),
        "tunnel": tunnel,
        "type": kind,
    }
    return meta, arrays


__all__ = ["CONTRACT", "GRID_M", "TYPES", "route_input", "stops_of", "types_at"]
