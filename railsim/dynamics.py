"""Force-based, time-stepped train movement simulation.

Each step integrates  m_eff * a = F_traction - F_brake - R_davis(v) - R_curve - m g sin(theta)
with:
  * tractive effort from a tabulated F(v) curve or min(adhesion, max effort, P/v), with
    speed-dependent adhesion (Curtius-Kniffler) and rail condition, supply-voltage power
    factor, auxiliary load, diesel power ramp-up after starting, and neutral sections,
  * grade and curve resistance averaged over the train's length (mass is distributed),
  * a commanded acceleration limit (load-weighed) and a jerk limit on every change,
  * braking on a pre-computed braking curve whose rate may depend on speed (HSR brake
    fade, LZB tables), is limited by adhesion in poor rail conditions and by brake
    capability on downgrades, and starts early enough for brake build-up delay, jerk-
    limited onset and any signalling-supervision lag,
  * posted limits enforced from when the front reaches a restriction until the rear
    clears it, with optional driver anticipation/postponement offsets (OSRD practice),
  * optional energy-saving driving: a cruising-speed cap and coasting before braking.

Everything is in SI units.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .rollingstock import G, Train

# drivers brake more defensively than the adhesion limit alone in poor conditions
WEATHER_BRAKE_FACTOR = {"dry": 1.0, "wet": 0.9, "leaf": 0.7}


@dataclass
class TrackData:
    """Route data on a uniform grid for one direction of travel."""

    ds: float
    s: np.ndarray
    limit: np.ndarray  # posted limit (m/s) at each point
    elevation: np.ndarray  # track elevation (m)
    curvature: np.ndarray  # |1/R| (1/m)
    tunnel: np.ndarray  # bool
    power_factor: Optional[np.ndarray] = None  # supply: available power / rated (1.0 nominal)
    no_traction: Optional[np.ndarray] = None  # bool: neutral sections (traction cut)

    def __post_init__(self):
        n = len(self.s)
        if self.power_factor is None:
            self.power_factor = np.ones(n)
        if self.no_traction is None:
            self.no_traction = np.zeros(n, dtype=bool)

    @property
    def length(self) -> float:
        return float(self.s[-1])

    def reversed(self) -> "TrackData":
        return TrackData(self.ds, self.s.copy(), self.limit[::-1].copy(), self.elevation[::-1].copy(),
                         self.curvature[::-1].copy(), self.tunnel[::-1].copy(),
                         self.power_factor[::-1].copy(), self.no_traction[::-1].copy())


@dataclass
class Driver:
    """How the train is driven (driver or ATO profile).

    brake_rate        planned braking rate, m/s^2; None = train.service_brake
    brake_fraction    share of the planned rate actually used (cautious drivers < 1)
    brake_curve       optional [(v m/s, b m/s^2)] cap on planned rate by speed (signalling)
    brake_anticipation_s  start braking this much earlier (ATP supervision / indication lag)
    speed_margin      run this far below the posted limit (m/s)
    power_fraction    share of available tractive effort used (performance %)
    anticipation_m    reach a lower limit this far before its sign (lineside practice)
    postponement_m    re-accelerate this far after the rear clears a restriction
    cruise_cap        absolute cruising-speed cap (m/s) for energy-saving running
    coast_window_s    coast (no traction) when braking will be needed within this time
    dt                integration step (s)
    """

    brake_rate: Optional[float] = None
    brake_fraction: float = 1.0
    brake_curve: Optional[List[Tuple[float, float]]] = None
    brake_anticipation_s: float = 0.0
    speed_margin: float = 0.3
    power_fraction: float = 1.0
    anticipation_m: float = 0.0
    postponement_m: float = 0.0
    cruise_cap: float = math.inf
    coast_window_s: float = 0.0
    dt: float = 0.2
    stop_approach_speed: float = 0.0  # m/s: creep speed for the last metres (0 = none)
    stop_approach_dist: float = 0.0  # m over which stop_approach_speed applies


@dataclass
class Stop:
    s: float  # front-of-train stopping position (m)
    name: str = ""
    dwell: float = 0.0


@dataclass
class RunResult:
    t: np.ndarray
    s: np.ndarray
    v: np.ndarray
    a: np.ndarray
    arrivals: List[float]  # time of arrival at each stop (first = 0)
    departures: List[float]
    energy_traction_kwh: float
    energy_regen_kwh: float
    front_limit: np.ndarray = field(default=None)  # gridded limit seen by the front

    def leg_times(self) -> List[float]:
        return [self.arrivals[k + 1] - self.departures[k] for k in range(len(self.departures) - 1)]


def _window_min(x: np.ndarray, w: int) -> np.ndarray:
    """out[i] = min(x[max(0, i-w) .. i])  (monotone deque, O(n))."""
    out = np.empty_like(x)
    dq: deque = deque()
    for i, xi in enumerate(x):
        while dq and x[dq[-1]] >= xi:
            dq.pop()
        dq.append(i)
        while dq[0] < i - w:
            dq.popleft()
        out[i] = x[dq[0]]
    return out


def _curve_resistance_per_kn(curv: np.ndarray) -> np.ndarray:
    """Roeckl's formula for standard gauge, N per kN of train weight."""
    with np.errstate(divide="ignore"):
        R = np.where(curv > 1e-7, 1.0 / np.maximum(curv, 1e-12), np.inf)
    r = np.zeros_like(R)
    big = R >= 300
    r[big] = 650.0 / (R[big] - 55.0)
    small = (R < 300) & np.isfinite(R)
    r[small] = 500.0 / np.maximum(R[small] - 30.0, 10.0)
    r[~np.isfinite(R)] = 0.0
    return r


def _interp_table(table, v: float) -> float:
    xs, ys = table
    return float(np.interp(v, xs, ys))


class Simulator:
    def __init__(self, train: Train, track: TrackData, driver: Driver):
        self.train = train
        self.track = track
        self.driver = driver
        ds = track.ds
        n = len(track.s)
        w = max(int(math.ceil((train.length + driver.postponement_m) / ds)), 1)
        self.n = n
        lim = np.minimum(track.limit, train.max_speed)
        fl = _window_min(lim, w)  # held until the rear clears (+ postponement)
        wa = int(round(driver.anticipation_m / ds))
        if wa > 0:  # reached `anticipation_m` before the sign
            fl = _window_min(fl[::-1], wa)[::-1]
        self.front_limit = fl
        self.target = np.minimum(np.maximum(fl - driver.speed_margin, 0.5), driver.cruise_cap)
        # mean grade over the train: (z_front - z_rear) / L, with the route extended at its ends
        wl = max(int(math.ceil(train.length / ds)), 1)
        z = track.elevation
        g0 = (z[min(wl, n - 1)] - z[0]) / (min(wl, n - 1) * ds) if n > 1 else 0.0
        z_pad = np.concatenate([z[0] - g0 * ds * np.arange(wl, 0, -1), z])
        self.grade = (z_pad[wl:] - z_pad[:-wl]) / (wl * ds)
        rc = _curve_resistance_per_kn(track.curvature)
        cs = np.concatenate([[0.0], np.cumsum(rc)])
        idx = np.arange(n)
        lo = np.maximum(idx - wl + 1, 0)
        self.curve_r = (cs[idx + 1] - cs[lo]) / (idx + 1 - lo)  # N/kN averaged over the train
        self.tunnel = track.tunnel
        self.b_base = (driver.brake_rate or train.service_brake) * driver.brake_fraction
        self._drv_bc = (np.array([p[0] for p in driver.brake_curve]),
                        np.array([p[1] for p in driver.brake_curve])) if driver.brake_curve else None

    # ------------------------------------------------------------------ helpers
    def _idx(self, s: float) -> int:
        return min(max(int(s / self.track.ds), 0), self.n - 1)

    def _ext_force(self, i: int, v: float) -> float:
        """Resistance + grade + curve forces opposing motion (N)."""
        tr = self.train
        weight = tr.mass * G
        return (tr.resistance(v, bool(self.tunnel[i])) + weight * self.grade[i]
                + weight * self.curve_r[i] / 1000.0)

    def b_plan(self, v: float, i: int) -> float:
        """Planned braking rate at speed v at grid point i."""
        tr = self.train
        b = self.b_base
        if tr.brake_curve is not None:
            b = min(b, _interp_table(tr.brake_curve, v) * self.driver.brake_fraction)
        if self._drv_bc is not None:
            b = min(b, _interp_table(self._drv_bc, v))
        b *= WEATHER_BRAKE_FACTOR.get(tr.rail_condition, 1.0)
        b = min(b, tr.adhesion_at(v) / max(tr.adhesion, 1e-6) * tr.brake_adhesion * G)
        b = min(b, tr.max_service_brake + G * self.grade[i])  # capability on downgrades
        return max(b, 0.05)

    def _leg_target(self, i0: int, i_stop: int, s_stop: float) -> np.ndarray:
        """Target speeds for one leg: posted limits (train-length aware) minus the driver's
        margin, capped at the creep speed over the final approach to the stop."""
        tgt = self.target[i0:i_stop + 1].copy()
        if self.driver.stop_approach_speed > 0 and self.driver.stop_approach_dist > 0:
            ss = self.track.s[i0:i_stop + 1]
            m = (s_stop - ss) <= self.driver.stop_approach_dist
            tgt[m] = np.minimum(tgt[m], self.driver.stop_approach_speed)
        return tgt

    def _braking_curve(self, i0: int, i_stop: int, s_stop: float, tgt: np.ndarray) -> np.ndarray:
        """Max speed at each grid point i0..i_stop allowing a stop at s_stop and compliance with
        every downstream target, braking at the planned (speed-dependent) rate."""
        ds = self.track.ds
        B = np.empty(i_stop - i0 + 1)
        d_last = max(s_stop - self.track.s[i_stop], 0.0)
        B[-1] = min(tgt[-1], math.sqrt(2 * self.b_plan(0.0, i_stop) * d_last))
        for k in range(len(B) - 2, -1, -1):
            i = i0 + k
            b = self.b_plan(B[k + 1], i)
            B[k] = min(tgt[k], math.sqrt(B[k + 1] ** 2 + 2 * b * ds))
        return B

    # ------------------------------------------------------------------ main loop
    def run(self, stops: Sequence[Stop], record_every: int = 1) -> RunResult:
        tr = self.train
        dr = self.driver
        dt = dr.dt
        ds = self.track.ds
        m_eff = tr.mass_eff
        j = tr.jerk
        td = tr.brake_delay
        ta = dr.brake_anticipation_s
        pf_arr = self.track.power_factor
        nt_arr = self.track.no_traction

        t = 0.0
        s = stops[0].s
        v = 0.0
        a = 0.0
        T, S, V, A = [0.0], [s], [0.0], [0.0]
        arrivals = [0.0]
        departures = []
        e_trac = 0.0
        e_regen = 0.0

        for k in range(len(stops) - 1):
            # dwell at the stop we are standing at
            t += stops[k].dwell
            departures.append(t)
            t_dep = t
            T.append(t), S.append(s), V.append(0.0), A.append(0.0)
            s_stop = stops[k + 1].s
            i0 = self._idx(s)
            i_stop = self._idx(s_stop)
            leg_tgt = self._leg_target(i0, i_stop, s_stop)
            B = self._braking_curve(i0, i_stop, s_stop, leg_tgt)
            B2 = B * B
            s_grid0 = self.track.s[i0]
            b_last = self.b_plan(0.0, i_stop)

            def Bat(x: float) -> float:
                if x >= s_stop:
                    return 0.0
                p = (x - s_grid0) / ds
                q = int(p)
                if q >= len(B) - 1:
                    # inside the last partial cell: exact parabola to the stop
                    return math.sqrt(max(2 * b_last * (s_stop - x), 0.0))
                f = p - q
                # v^2 is linear in distance under constant deceleration: interpolate squares
                return math.sqrt(B2[q] * (1 - f) + B2[q + 1] * f)

            braking = False
            brake_clock = 0.0  # time since brake demand (for build-up delay)
            steps = 0
            while True:
                steps += 1
                i = self._idx(s)
                f_ext = self._ext_force(i, v)
                a_coast = -f_ext / m_eff
                if nt_arr[i]:
                    f_trac_max = 0.0
                else:
                    ramp = 1.0
                    if tr.power_ramp_s > 0:
                        ramp = min(1.0, 0.15 + 0.85 * (t - t_dep) / tr.power_ramp_s)
                    f_trac_max = tr.tractive_effort(v, pf_arr[i] * ramp) * dr.power_fraction
                a_trac = (f_trac_max - f_ext) / m_eff
                tgt = leg_tgt[min(max(i - i0, 0), len(leg_tgt) - 1)]
                b_now = self.b_plan(v, i)

                # --- will a brake application started now (delay + jerk ramp) stay under B?
                a1 = min(a, a_coast) if td > 0 else a
                s_p = s + v * (td + ta) + 0.5 * a1 * td * td
                v_p = v + a1 * td
                tr_t = max((a1 + b_now) / j, 0.0)
                s_r = s_p + v_p * tr_t + 0.5 * a1 * tr_t ** 2 - j * tr_t ** 3 / 6
                v_r = v_p + a1 * tr_t - 0.5 * j * tr_t ** 2
                look = v * ta
                need = v_r > Bat(s_r) + 0.02 or v > Bat(s + look + 0.5 * v * dt) + 0.02
                if braking:
                    braking = need or v > tgt + 0.1 or v > Bat(s + look + v * dt) - 0.05
                else:
                    braking = need
                if braking:
                    brake_clock += dt
                    s_n = s + max(v * dt, 0.02)
                    vb = Bat(s_n + look)
                    a_req = (vb * vb - v * v) / (2 * (s_n - s))
                    if need and a_req > -b_now:
                        # below the curve but must start the jerk-limited ramp now
                        a_req = -b_now
                    a_cmd = max(a_req, -tr.max_service_brake + G * min(self.grade[i], 0.0))
                    a_cmd = min(a_cmd, a_coast)  # no traction while braking
                    if brake_clock < td:
                        a_cmd = max(a_cmd, min(a, a_coast))  # brakes not yet effective
                else:
                    brake_clock = 0.0
                    coast = (dr.coast_window_s > 0 and
                             Bat(s + v * dr.coast_window_s) < v - 0.3)
                    if coast:
                        # energy-saving: let resistance (and the gradient) slow the train
                        a_cmd = min(a_coast, max((tgt - v) / 2.0, -b_now))
                    elif v < tgt - 0.05:
                        a_cmd = min(tr.max_accel * dr.power_fraction, a_trac)
                        a_cmd = min(a_cmd, math.sqrt(2 * j * max(tgt - v, 0.0)))
                    else:
                        a_cmd = max(min((tgt - v) / 2.0, a_trac), -b_now)
                # jerk limit, then physical traction ceiling
                a_new = a + max(-j * dt, min(j * dt, a_cmd - a))
                if a_new > a_coast:
                    a_new = min(a_new, max(a_trac, a_coast))
                v_new = v + a_new * dt
                if v_new <= 0.0:
                    # stopped (short of the stopping point only if braking overshot slightly)
                    tt = v / max(-a_new, 1e-6) if a_new < 0 else dt
                    s_new = s + 0.5 * v * tt
                    v_new = 0.0
                    if s_stop - s_new < 1.0 or steps > 10 ** 6:
                        t += tt
                        s = s_stop
                        v = 0.0
                        a = 0.0
                        break
                    # crept to a halt early: carry on from rest
                    t += tt
                    s = s_new
                    v = 0.0
                    a = 0.0
                    continue
                s_new = s + 0.5 * (v + v_new) * dt
                if s_new >= s_stop:
                    # arrive: time to cover the remaining distance at mean speed
                    rem = s_stop - s
                    tt = 2 * rem / max(v + v_new, 1e-6)
                    t += tt
                    s = s_stop
                    v = 0.0
                    a = 0.0
                    break
                # energy (traction at the wheel; regen on braking for electric stock)
                f_net = m_eff * a_new + f_ext
                if f_net > 0:
                    e_trac += f_net * 0.5 * (v + v_new) * dt
                elif tr.regen_efficiency > 0:
                    e_regen += -f_net * 0.5 * (v + v_new) * dt * tr.regen_efficiency
                t += dt
                s, v, a = s_new, v_new, a_new
                if steps % record_every == 0:
                    T.append(t), S.append(s), V.append(v), A.append(a)
            T.append(t), S.append(s), V.append(0.0), A.append(0.0)
            arrivals.append(t)
        departures.append(t + stops[-1].dwell)
        eff = max(tr.traction_efficiency, 1e-3)
        aux_kwh = tr.aux_kw * (departures[-1]) / 3600.0
        return RunResult(np.array(T), np.array(S), np.array(V), np.array(A), arrivals, departures,
                         e_trac / eff / 3.6e6 + aux_kwh, e_regen / 3.6e6, self.front_limit)
