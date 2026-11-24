"""Where the time goes: the seconds each speed restriction, the grades and the tunnel drag cost on a run. Pure.

For each direction, railsim's ``Simulator`` is run again on the same track with one thing taken away, and the
running time it saves is what that thing costs:

- each zone of the posted limit below the line speed (a curve, a terminal approach, a throat), lifted to the line
  speed: its ``reason`` is railsim's (``"curve R=420 m"``), its ``rule`` the rule id where the restriction has one;
- the grades: the rail laid level;
- the tunnel drag: every tunnel flag off.

The per-leg split into accelerating, cruising, coasting and braking needs no re-run (``adapter._phases``, in the
run's own result). About 40 zones on Line 6 at 0.15 s per direction each; ``cancelled`` is asked between runs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

import numpy as np

from . import adapter


def _running(sim_run: Any) -> float:
    return float(sum(sim_run.leg_times()))


def attribute(
    meta: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
    settings: Mapping[str, Any],
    *,
    cancelled: Callable[[], bool] = lambda: False,
    progress: Callable[[float, str], None] = lambda f, m: None,
) -> dict[str, Any]:
    """``{"directions": [{dir, zones, grades_s, tunnel_drag_s, dwell_s, running_s}]}`` for one RouteInput."""
    from railsim import app
    from railsim.dynamics import Simulator, Stop

    parts = adapter.build(meta, arrays, settings)
    route, train, driver = parts["route"], parts["train"], parts["driver"]
    opt = settings["options"]
    ds = float(opt["grid_m"])
    s_grid = np.asarray(arrays["s_m"], dtype=float)
    c_grid = np.asarray(arrays["c_m"], dtype=float)
    zones = [z for z in adapter._zones(route, lambda s: np.interp(s, s_grid, c_grid)) if z["reason"] != "line speed"]
    line_v = float(np.max(route.speed.limit)) if len(route.speed.limit) else 0.0
    out = []
    total = 2 * (len(zones) + 2)
    done = 0
    for d, rev in ((1, False), (-1, True)):
        td = route.track_data(ds)
        if rev:
            td = td.reversed()
        seq, stop_s, dwell, jumps = app._stops_for(
            route,
            train,
            rev,
            parts["dwell_of"],
            str(opt["stop_position"]),
            1.0,
            float(opt["reversal_min_s"]),
        )
        stops = [Stop(s, st.name, dw, j) for s, st, dw, j in zip(stop_s, seq, dwell, jumps, strict=True)]
        L = float(td.s[-1])

        def run_on(t: Any, stops: list[Any] = stops) -> float:
            return _running(Simulator(train, t, driver).run(stops))

        base = run_on(td)
        rows = []
        for z in zones:
            if cancelled():
                raise InterruptedError("cancelled")
            a, b = (L - z["s1_m"], L - z["s0_m"]) if rev else (z["s0_m"], z["s1_m"])
            lim = td.limit.copy()
            m = (td.s >= a - 1e-6) & (td.s <= b + 1e-6)
            lim[m] = np.maximum(lim[m], line_v)
            rows.append(
                {
                    **{k: z[k] for k in ("c0_m", "c1_m", "reason", "rule", "kmh")},
                    "limit_kmh": z["kmh"],
                    "lost_s": base - run_on(replace(td, limit=lim)),
                }
            )
            done += 1
            progress(done / total, "forward" if not rev else "reverse")
        level = run_on(replace(td, elevation=np.full_like(td.elevation, float(np.mean(td.elevation)))))
        no_tunnel = run_on(replace(td, tunnel=np.zeros_like(td.tunnel)))
        done += 2
        progress(done / total, "forward" if not rev else "reverse")
        rows.sort(key=lambda r: -r["lost_s"])
        out.append(
            {
                "dir": d,
                "running_s": base,
                "zones": rows,
                "grades_s": base - level,
                "tunnel_drag_s": base - no_tunnel,
                "dwell_s": float(sum(dwell[1:-1])),
            }
        )
    return {"directions": out}


__all__ = ["attribute"]
