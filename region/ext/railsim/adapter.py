"""A RouteInput (``route_input/0``) through railsim's own objects to a RunResult (``run_result/0``). Pure.

``run_route(meta, arrays, settings)`` builds what railsim's ``line.build_route`` would have built, from the
RouteInput alone:

- ``horizontal.HorizontalAlignment`` with the fit's curves (their R, spiral, cant and deflection), on the run grid;
- ``profile.Profile`` with the solved rail at each run sample and a railsim structure name per sample
  (``metro_profile.STRUCTURE``), so ``Route.track_data`` sets the tunnel flags as railsim does;
- ``speed.build_speed_profile`` (the curve limits for this train, plus the RouteInput's fixed restrictions);
- ``line.StationInfo`` per stop (class, platform length, PSD, dwell override);

then ``line.Route.track_data`` (through ``app.run_direction``, both directions), ``app.apply_padding`` and the
numbers of ``app.summary_dict``. It replaces ``build_route`` only: it never calls ``app.main``, ``build_route``,
``elevation``, ``kml``, ``report`` or ``MetroProfile.load``, and it writes nothing.

The answer's arrays are on the section grid of ``meta.grid`` (10 m, ``c = i * 10``): the posted limit, and per
direction the front's speed and the time it passes each sample (NaN where the train never is); the traces are every
simulator step as ``[t, c, v, a]`` rows. Times are unrounded; equal inputs give equal outputs.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

RESULT_CONTRACT = "run_result/0"
RESULT_STEP_M = 10.0
"""The section grid step of the run's arrays."""
PHASE_A = 0.02
"""m/s2: a step accelerating faster than this is accelerating, one slowing faster is braking, the rest cruising."""
KMH = 3.6


def _structure_names(kind: np.ndarray, tunnel: np.ndarray) -> list[str]:
    from railsim.metro_profile import STRUCTURE, TUNNEL_STRUCTURES, TYPES

    names = [STRUCTURE[t] for t in TYPES]
    out = []
    for k, t in zip(kind.tolist(), tunnel.tolist(), strict=True):
        n = names[int(k)] if 0 <= int(k) < len(names) else "at-grade"
        if bool(t) != (n in TUNNEL_STRUCTURES):
            n = "tunnel" if t else "at-grade"
        out.append(n)
    return out


def train_of(settings: Mapping[str, Any]) -> Any:
    """The train of the settings, loaded (``Train.with_load``)."""
    from railsim.rollingstock import train_from_dict

    opt = settings["options"]
    return train_from_dict(settings["train_key"], dict(settings["train"])).with_load(
        float(opt["load_factor"]), str(opt["rail_condition"])
    )


def build(meta: Mapping[str, Any], arrays: Mapping[str, np.ndarray], settings: Mapping[str, Any]) -> dict[str, Any]:
    """railsim's objects for one RouteInput: ``{route, train, driver, dwell_of, cfg, options}``."""
    from railsim import app, metro
    from railsim.geo import LocalProjection
    from railsim.horizontal import Curve, HorizontalAlignment
    from railsim.line import Route, StationInfo
    from railsim.operations import apply_driver_config
    from railsim.profile import Profile
    from railsim.speed import Restriction, build_speed_profile

    cfg = dict(settings["cfg"])
    train = train_of(settings)
    s = np.asarray(arrays["s_m"], dtype=float)
    rail = np.asarray(arrays["rail_z_m"], dtype=float)
    tunnel = np.asarray(arrays["tunnel"]).astype(bool)
    kind = np.asarray(arrays["type"]).astype(int)
    curves = [
        Curve(
            direction=int(c["direction"]),
            deflection=float(c["deflection_rad"]),
            radius=float(c["radius_m"]),
            spiral=float(c["spiral_m"]),
            s_ts=float(c["s_ts"]),
            s_sc=float(c["s_sc"]),
            s_cs=float(c["s_cs"]),
            s_st=float(c["s_st"]),
            tangent=float(c.get("tangent_m") or 0.0),
            cant=float(c["cant_m"]),
        )
        for c in meta["curves"]
    ]
    # the run reads only the curves and the length of the alignment; its xy (for maps and the KMZ export) is not
    # needed, so the run grid stands in for it
    h = HorizontalAlignment(np.column_stack([s, np.zeros_like(s)]), s, curves, float(meta["length_m"]))
    grade = np.gradient(rail, s) if len(s) > 1 else np.zeros_like(s)
    prof = Profile(s, rail.copy(), rail, grade, _structure_names(kind, tunnel))
    policy = app.speed_policy_from(cfg, train)
    extra = [
        Restriction(float(r["s0_m"]), float(r["s1_m"]), float(r["v_ms"]), str(r.get("reason") or "posted"))
        for r in meta.get("restrictions") or []
    ]
    sp = build_speed_profile(h, policy, extra)
    stations = []
    for st in meta["stops"]:
        info = StationInfo(str(st["name"]), 0.0, 0.0)
        info.s = float(st["s_m"])
        info.cls = str(st.get("class") or "standard")
        info.platform_length = float(st.get("platform_m") or 150.0)
        info.dwell_override = st.get("dwell_s")
        info.psd = st.get("psd")
        info.reverse = bool(st.get("reverse"))
        info.stop = True
        stations.append(info)
    proj = meta.get("proj") or {}
    route = Route(
        str(meta.get("name") or meta.get("route_key")),
        LocalProjection(float(proj.get("lat0", 0.0)), float(proj.get("lon0", 0.0))),
        h,
        prof,
        sp,
        stations,
        list(meta.get("warnings") or []),
    )
    driver = apply_driver_config(metro.make_driver(cfg, train), cfg)

    def dwell_of(st: Any) -> float:
        return metro.dwell_fn(st, train, cfg, False)

    return {"route": route, "train": train, "driver": driver, "dwell_of": dwell_of, "cfg": cfg}


def run_directions(parts: Mapping[str, Any], options: Mapping[str, Any], *, driver: Any = None, route: Any = None) -> list[Any]:
    """Both directions through ``app.run_direction`` (forward is rising chainage), padded (``app.apply_padding``)."""
    from railsim import app

    out = []
    for rev in (False, True):
        dr = app.run_direction(
            route or parts["route"],
            parts["train"],
            driver or parts["driver"],
            parts["dwell_of"],
            rev,
            ds=float(options["grid_m"]),
            stop_position=str(options["stop_position"]),
            reversal_min_s=float(options["reversal_min_s"]),
        )
        app.apply_padding(dr, parts["cfg"].get("padding") or {})
        out.append(dr)
    return out


def _phases(dr: Any, k: int) -> dict[str, float]:
    """The seconds of leg ``k`` (arrival ``k``) spent accelerating, cruising, coasting and braking, from the trace."""
    run = dr.run
    t0, t1 = run.departures[k - 1], run.arrivals[k]
    m = (run.t > t0) & (run.t <= t1)
    a = run.a[m]
    tt = run.t[m]
    if len(tt) == 0:
        return {"accel_s": 0.0, "cruise_s": 0.0, "coast_s": 0.0, "brake_s": 0.0}
    dt = np.diff(np.concatenate([[t0], tt]))
    accel = float(dt[a > PHASE_A].sum())
    brake = float(dt[a < -PHASE_A].sum())
    cruise = float(dt.sum()) - accel - brake
    return {"accel_s": accel, "cruise_s": cruise, "coast_s": 0.0, "brake_s": brake}


def _vmax(dr: Any, k: int) -> float:
    run = dr.run
    m = (run.t >= run.departures[k - 1]) & (run.t <= run.arrivals[k])
    return float(run.v[m].max()) if m.any() else 0.0


def _passes(trace_s: np.ndarray, values: np.ndarray, at: np.ndarray) -> np.ndarray:
    """``values`` of the trace where the front first reaches each chainage ``at``; NaN outside the trace."""
    out = np.full(len(at), np.nan)
    if len(trace_s) == 0:
        return out
    order = np.argsort(trace_s, kind="stable")
    ss = trace_s[order]
    vv = values[order]
    ss, first = np.unique(ss, return_index=True)
    vv = vv[first]
    inside = (at >= ss[0]) & (at <= ss[-1])
    out[inside] = np.interp(at[inside], ss, vv)
    return out


def _direction(meta: Mapping[str, Any], dr: Any, d: int, s_of: Callable[[float], float]) -> dict[str, Any]:
    run = dr.run
    stops = {str(st["name"]): st for st in meta["stops"]}
    total = float(run.arrivals[-1])
    dist = float(dr.stop_s[-1] - dr.stop_s[0])
    moving = float(sum(run.leg_times()))
    rows = []
    for k, st in enumerate(dr.stations):
        rec = stops.get(st.name) or {}
        leg = None
        if k > 0:
            leg = {"run_s": float(run.arrivals[k] - run.departures[k - 1]), "vmax_kmh": _vmax(dr, k) * KMH}
            leg.update(_phases(dr, k))
        rows.append(
            {
                "platform_id": rec.get("platform_id"),
                "name": st.name,
                "c_m": rec.get("c_m"),
                "s_m": float(st.s),
                "km": float((dr.stop_s[k] - dr.stop_s[0]) / 1000),
                "arrive_s": float(run.arrivals[k]),
                "depart_s": float(run.departures[k]),
                "dwell_s": float(dr.dwell[k]),
                "scheduled_arrive_s": float(dr.padded_arrivals[k]) if dr.padded_arrivals else None,
                "leg": leg,
            }
        )
    first, last = dr.stations[0].name, dr.stations[-1].name
    return {
        "dir": d,
        "label": f"{first} to {last}",
        "from": first,
        "to": last,
        "distance_m": dist,
        "stops": len(dr.stations),
        "running_s": moving,
        "dwell_s": float(sum(dr.dwell[1:-1])),
        "trip_s": total,
        "scheduled_s": float(dr.padded_arrivals[-1]) if dr.padded_arrivals else None,
        "average_kmh": dist / max(total, 1.0) * KMH,
        "max_kmh": float(run.v.max()) * KMH,
        "energy_traction_kwh": float(run.energy_traction_kwh),
        "energy_regen_kwh": float(run.energy_regen_kwh),
        "stations": rows,
    }


def _zones(route: Any, s_to_c: Callable[[np.ndarray], np.ndarray]) -> list[dict[str, Any]]:
    """The posted limit as zones in section chainage, each with the reason of the restriction that set it."""
    sp = route.speed
    lim = sp.limit
    if len(lim) == 0:
        return []
    cut = np.flatnonzero(np.diff(lim)) + 1
    starts = np.concatenate([[0], cut])
    ends = np.concatenate([cut, [len(lim) - 1]])
    out = []
    for a, b in zip(starts.tolist(), ends.tolist(), strict=True):
        s0, s1 = float(sp.s[a]), float(sp.s[b])
        v = float(lim[a])
        mid = (s0 + s1) / 2
        reason = "line speed"
        for z in sp.zones:
            if z.s0 - 1e-6 <= mid <= z.s1 + 1e-6 and abs(z.speed - v) < 1e-6:
                reason = z.reason or "posted"
                break
        else:
            if any(z.s0 - 1e-6 <= mid <= z.s1 + 1e-6 for z in sp.zones):
                reason = "merged zone"
        c0, c1 = (float(x) for x in s_to_c(np.array([s0, s1])))
        out.append({"c0_m": c0, "c1_m": c1, "s0_m": s0, "s1_m": s1, "kmh": v * KMH, "reason": reason, "rule": None})
    return out


def run_route(
    meta: Mapping[str, Any], arrays: Mapping[str, np.ndarray], settings: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """The RunResult of one RouteInput (see the module doc): ``(meta, arrays)``."""
    from railsim.speed import curve_speed

    parts = build(meta, arrays, settings)
    route, train = parts["route"], parts["train"]
    options = settings["options"]
    warnings = list(meta.get("warnings") or [])
    if train.min_curve_radius > 0:
        tight = [c for c in route.horizontal.curves if c.radius < train.min_curve_radius]
        if tight:
            worst = min(tight, key=lambda c: c.radius)
            warnings.append(
                f"{train.name} is not cleared for this route: {len(tight)} curve(s) tighter than "
                f"{train.min_curve_radius:.0f} m (tightest {worst.radius:.0f} m at km {worst.s_ts / 1000:.2f})"
            )
    s_grid = np.asarray(arrays["s_m"], dtype=float)
    c_grid = np.asarray(arrays["c_m"], dtype=float)
    L = float(meta["length_m"])

    def s_to_c(s: np.ndarray) -> np.ndarray:
        return np.interp(s, s_grid, c_grid)

    def c_to_s(c: np.ndarray) -> np.ndarray:
        return np.interp(c, c_grid + np.arange(len(c_grid)) * 1e-9, s_grid)

    drs = run_directions(parts, options)
    directions = [_direction(meta, dr, d, lambda x: x) for dr, d in zip(drs, (1, -1), strict=True)]
    tb = parts["cfg"].get("turnback_min", 0) or 0
    ends = [route.stations[0].name, route.stations[-1].name] if route.stations else ["", ""]
    turns = (
        [float(tb.get(n, tb.get("default", 0)) or 0) * 60 for n in ends]
        if isinstance(tb, dict)
        else [float(tb) * 60] * 2
    )
    sec = meta.get("section") or {}
    sec_len = float(sec.get("length_m") or c_grid[-1])
    n10 = int(math.floor(sec_len / RESULT_STEP_M + 1e-9)) + 1
    c10 = np.arange(n10) * RESULT_STEP_M
    s10 = c_to_s(c10)
    out_arrays: dict[str, np.ndarray] = {"limit_ms": np.asarray(route.speed.at(s10), dtype="<f8")}
    for dr, tag in zip(drs, ("fwd", "rev"), strict=True):
        run = dr.run
        front = np.asarray(run.s, dtype=float)
        s_route = (L - front) if dr.reverse else front
        out_arrays[f"v_{tag}_ms"] = _passes(front, np.asarray(run.v, dtype=float), (L - s10) if dr.reverse else s10)
        out_arrays[f"t_{tag}_s"] = _passes(front, np.asarray(run.t, dtype=float), (L - s10) if dr.reverse else s10)
        out_arrays[f"trace_{tag}"] = np.column_stack(
            [run.t, s_to_c(s_route), run.v, run.a]
        ).astype("<f4")
    for k in list(out_arrays):
        if out_arrays[k].ndim == 1:
            out_arrays[k] = out_arrays[k].astype("<f8")
    policy_curves = []
    from railsim import app

    pol = app.speed_policy_from(parts["cfg"], train)
    for c in route.horizontal.curves:
        v = curve_speed(c.radius, c.cant, c.spiral, pol, c.deflection)
        c0, c1 = (float(x) for x in s_to_c(np.array([c.s_ts, c.s_st])))
        policy_curves.append(
            {"c0_m": c0, "c1_m": c1, "radius_m": c.radius, "spiral_m": c.spiral, "limit_kmh": min(v, pol.line_speed) * KMH}
        )
    out_meta = {
        "contract": RESULT_CONTRACT,
        "route_id": meta.get("route_id"),
        "route_key": meta.get("route_key"),
        "config": settings.get("config"),
        "year": settings.get("year"),
        "year_source": settings.get("year_source"),
        "era": settings.get("era"),
        "train": {
            "key": settings["train_key"],
            "name": train.name,
            "cars": int(train.cars),
            "length_m": float(train.length),
            "load_factor": float(train.load_factor),
            "mass_t": float(train.mass) / 1000.0,
            "rail_condition": train.rail_condition,
            "max_kmh": float(train.max_speed) * KMH,
        },
        "padding": {
            "percent": float((parts["cfg"].get("padding") or {}).get("percent", 0.0)),
            "final_leg_s": float((parts["cfg"].get("padding") or {}).get("final_leg_s", 0.0)),
        },
        "directions": directions,
        "round_trip_s": float(sum(d["scheduled_s"] or d["trip_s"] for d in directions) + sum(turns)),
        "turnback_s": turns,
        "headway_min": (parts["cfg"].get("service") or {}).get("headway_min"),
        "speed_zones": _zones(route, s_to_c),
        "curves": policy_curves,
        "grid": {"c0": 0.0, "step_m": RESULT_STEP_M, "n": n10},
        "warnings": warnings,
        "sources": {**dict(settings.get("sources") or {}), **{k: v for k, v in (meta.get("sources") or {}).items() if k == "curves"}},
    }
    if out_meta["headway_min"]:
        out_meta["trains_needed"] = math.ceil(out_meta["round_trip_s"] / 60 / float(out_meta["headway_min"]))
    return out_meta, out_arrays


__all__ = ["RESULT_CONTRACT", "RESULT_STEP_M", "build", "run_directions", "run_route", "train_of"]
