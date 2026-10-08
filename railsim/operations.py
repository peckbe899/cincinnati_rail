"""Operating-practice layer shared by both programs.

Sources: the simulator survey in docs/research/simulators.md (OSRD, Open Rails,
TrainRuns.jl, ETCS Subset-026, IEEE 1474, UIC 451-1, MARECO).

* signalling presets      how train protection changes driving (margins, braking lag/rates)
* driver profile keys     performance %, brake fraction, OSRD anticipation/postponement
* turnout speeds          diverging speed from turnout number (AREMA) or DB geometry
* eco allowance           padding absorbed by a cruising cap + coasting (MARECO-like)
                          instead of uniformly; reports the energy saved
* Monte Carlo             driver/dwell variability -> median and 85th-percentile times
"""

from __future__ import annotations

import copy
import math
import random
from dataclasses import replace
from typing import Callable, Dict, List

import numpy as np

from .dynamics import Driver
from .geo import KMH, MPH

# ---------------------------------------------------------------------------------------
# Signalling. Values: OSRD driver behaviour (lineside 100 m / 50 m), IEEE 1474 CBTC
# delays and ATO margins, ETCS Subset-026 driver/indication times, LZB passenger
# braking-curve table. See docs/research/simulators.md, rank 4.
# ---------------------------------------------------------------------------------------
SIGNALLING = {
    "none": {},
    # lineside block signals (US ABS/CTC, European fixed signals): drivers reach a lower
    # limit before its sign and re-accelerate after clearing it
    "lineside": {"anticipation_m": 100.0, "postponement_m": 50.0},
    # continuous cab signals with code speeds (US ATC): the driver sees the code change in
    # the cab, so no lineside anticipation (OSRD applies offsets only on lineside lines);
    # the effect is the code-step speed rounding (speed.code_steps_mph)
    "cab": {},
    # CBTC with ATO: runs 3 km/h below the ATP profile, ~1.5 s supervision/build-up lag
    "cbtc": {"speed_margin_kmh": 3.0, "brake_anticipation_s": 1.5},
    # ETCS Level 2: braking starts at the indication/permitted curve, ~4 s driver
    # reaction + 2 s warning ahead of the supervised curve
    "etcs2": {"speed_margin_kmh": 3.0, "brake_anticipation_s": 6.0},
    # LZB: constant-deceleration supervision curves for passenger trains (<= 5 per mille)
    "lzb": {"brake_curve_kmh_ms2": [[0, 0.57], [160, 0.57], [161, 0.51], [250, 0.51],
                                    [251, 0.45], [350, 0.45]],
            "brake_anticipation_s": 2.0},
}

# AREMA turnout number -> diverging speed (mph); DB EW radius-ratio -> km/h
TURNOUT_US_MPH = {8: 15, 9: 15, 10: 20, 11: 25, 12: 25, 14: 30, 15: 30, 16: 35, 18: 35, 19: 40,
                  20: 40, 24: 50, 26: 50, 32: 60, 33: 70}
TURNOUT_DB_KMH = {"190-1:9": 40, "300-1:9": 50, "500-1:12": 60, "760-1:14": 80,
                  "1200-1:18.5": 100, "2500-1:26.5": 130, "1:42": 160, "1:65": 220}


def turnout_speed(spec) -> float:
    """m/s for a turnout given as an AREMA number (e.g. 15) or a DB designation."""
    if isinstance(spec, (int, float)):
        n = int(round(float(spec)))
        keys = sorted(TURNOUT_US_MPH)
        k = max([x for x in keys if x <= n] or [keys[0]])
        return TURNOUT_US_MPH[k] * MPH
    if str(spec) in TURNOUT_DB_KMH:
        return TURNOUT_DB_KMH[str(spec)] * KMH
    raise ValueError(f"unknown turnout '{spec}'")


def apply_driver_config(driver: Driver, cfg: dict) -> Driver:
    """Overlay the signalling preset and explicit driver-profile keys on a program's driver."""
    sig = (cfg.get("signalling") or {}).get("system", "none")
    preset = dict(SIGNALLING.get(sig, {}))
    d = dict(preset)
    d.update(cfg.get("driver", {}) or {})
    kw = {}
    if "brake_fraction" in d:
        kw["brake_fraction"] = float(d["brake_fraction"])
    if "anticipation_m" in d:
        kw["anticipation_m"] = float(d["anticipation_m"])
    if "postponement_m" in d:
        kw["postponement_m"] = float(d["postponement_m"])
    if "brake_anticipation_s" in d:
        kw["brake_anticipation_s"] = float(d["brake_anticipation_s"])
    if "coast_window_s" in d:
        kw["coast_window_s"] = float(d["coast_window_s"])
    if "brake_curve_kmh_ms2" in d:
        kw["brake_curve"] = [(float(a) * KMH, float(b)) for a, b in d["brake_curve_kmh_ms2"]]
    user_margin = any(k.startswith("speed_margin") for k in (cfg.get("driver", {}) or {}))
    if not user_margin and "speed_margin_kmh" in preset:
        kw["speed_margin"] = float(preset["speed_margin_kmh"]) * KMH
    return replace(driver, **kw)


# ---------------------------------------------------------------------------------------
# Eco allowance (MARECO-like): spend the padding by cruising below the limit and coasting
# before braking, instead of stretching every leg uniformly.
# ---------------------------------------------------------------------------------------

def eco_driver(run_fn: Callable[[Driver], object], driver: Driver, target_running_s: float,
               coast_window_s: float = 25.0, tol_s: float = 2.0):
    """Find the cruising cap (with coasting) whose total running time matches the padded
    target. run_fn(driver) -> DirectionResult. Returns (driver, result)."""
    base = run_fn(replace(driver, coast_window_s=coast_window_s))
    if sum(base.run.leg_times()) >= target_running_s - tol_s:
        return replace(driver, coast_window_s=coast_window_s), base
    vmax = float(np.nanmax(base.run.v))
    lo, hi = 0.3 * vmax, vmax
    best = (replace(driver, coast_window_s=coast_window_s), base)
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        drv = replace(driver, cruise_cap=mid, coast_window_s=coast_window_s)
        res = run_fn(drv)
        t = sum(res.run.leg_times())
        best = (drv, res)
        if abs(t - target_running_s) <= tol_s:
            break
        if t > target_running_s:
            lo = mid
        else:
            hi = mid
    return best


# ---------------------------------------------------------------------------------------
# Monte Carlo variability (SIMONE/FRISO/OpenTrack practice)
# ---------------------------------------------------------------------------------------

def monte_carlo(run_fn: Callable[[Driver, float], object], driver: Driver, n: int,
                seed: int = 1) -> Dict[str, float]:
    """run_fn(driver, dwell_multiplier) -> DirectionResult. Driver performance 88-100% of
    traction, braking 85-100% of plan, +0-3 km/h extra cruise margin; dwell multiplier
    log-normal with 20% spread. Returns trip-time percentiles in minutes."""
    rng = random.Random(seed)
    trips = []
    for _ in range(n):
        drv = replace(driver,
                      power_fraction=driver.power_fraction * rng.uniform(0.88, 1.0),
                      brake_fraction=driver.brake_fraction * rng.uniform(0.85, 1.0),
                      speed_margin=driver.speed_margin + rng.uniform(0.0, 3.0) * KMH)
        mult = math.exp(rng.gauss(0.0, 0.2) - 0.02)
        res = run_fn(drv, mult)
        trips.append(res.run.arrivals[-1] / 60.0)
    a = np.array(trips)
    return {"runs": n, "min": float(a.min()), "p50": float(np.percentile(a, 50)),
            "p85": float(np.percentile(a, 85)), "p95": float(np.percentile(a, 95)),
            "max": float(a.max())}
