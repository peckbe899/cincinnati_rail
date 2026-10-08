"""Force-based, time-stepped train movement simulation.

Each step integrates  m_eff * a = F_traction - F_brake - R_davis(v) - R_curve - m g sin(theta)
with:
  * tractive effort limited by adhesion, max effort and power (F <= P / v),
  * grade and curve resistance averaged over the train's length (mass is distributed),
  * a commanded acceleration limit (load-weighed) and a jerk limit on every change,
  * braking that follows a pre-computed braking curve (planned service rate, reduced on
    steep downgrades when brake capability runs out), started early enough to allow for
    brake build-up delay and jerk-limited onset,
  * posted limits enforced from when the front reaches a restriction until the rear
    clears it (train-length window).

Everything is in SI units.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

from .rollingstock import G, Train


@dataclass
class TrackData:
    """Route data on a uniform grid for one direction of travel."""

    ds: float
    s: np.ndarray
    limit: np.ndarray  # posted limit (m/s) at each point
    elevation: np.ndarray  # track elevation (m)
    curvature: np.ndarray  # |1/R| (1/m)
    tunnel: np.ndarray  # bool

    @property
    def length(self) -> float:
        return float(self.s[-1])

    def reversed(self) -> "TrackData":
        return TrackData(self.ds, self.s.copy(), self.limit[::-1].copy(), self.elevation[::-1].copy(),
                         self.curvature[::-1].copy(), self.tunnel[::-1].copy())


@dataclass
class Driver:
    """How the train is driven.

    brake_rate      planned (timetable) braking rate, m/s^2; None = train.service_brake
    speed_margin    run this far below the posted limit (m/s): ATO ~0.5 km/h, drivers 1-2 mph
    power_fraction  share of available tractive effort used (1.0 = full power)
    dt              integration step (s)
    """

    brake_rate: Optional[float] = None
    speed_margin: float = 0.3
    power_fraction: float = 1.0
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


class Simulator:
    def __init__(self, train: Train, track: TrackData, driver: Driver):
        self.train = train
        self.track = track
        self.driver = driver
        ds = track.ds
        n = len(track.s)
        w = max(int(math.ceil(train.length / ds)), 1)
        self.n = n
        vmax = train.max_speed
        lim = np.minimum(track.limit, vmax)
        self.front_limit = _window_min(lim, w)
        self.target = np.maximum(self.front_limit - driver.speed_margin, 0.5)
        # mean grade over the train: (z_front - z_rear) / L, with the route extended at its ends
        z = track.elevation
        g0 = (z[min(w, n - 1)] - z[0]) / (min(w, n - 1) * ds) if n > 1 else 0.0
        z_pad = np.concatenate([z[0] - g0 * ds * np.arange(w, 0, -1), z])
        self.grade = (z_pad[w:] - z_pad[:-w]) / (w * ds)
        rc = _curve_resistance_per_kn(track.curvature)
        cs = np.concatenate([[0.0], np.cumsum(rc)])
        idx = np.arange(n)
        lo = np.maximum(idx - w + 1, 0)
        self.curve_r = (cs[idx + 1] - cs[lo]) / (idx + 1 - lo)  # N/kN averaged over the train
        self.tunnel = track.tunnel

    # ------------------------------------------------------------------ helpers
    def _idx(self, s: float) -> int:
        return min(max(int(s / self.track.ds), 0), self.n - 1)

    def _ext_force(self, i: int, v: float) -> float:
        """Resistance + grade + curve forces opposing motion (N)."""
        tr = self.train
        weight = tr.mass * G
        return (tr.resistance(v, bool(self.tunnel[i])) + weight * self.grade[i]
                + weight * self.curve_r[i] / 1000.0)

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
        every downstream target, braking at the planned rate (limited by capability on downgrades)."""
        tr = self.train
        ds = self.track.ds
        b_plan = self.driver.brake_rate or tr.service_brake
        B = np.empty(i_stop - i0 + 1)
        d_last = max(s_stop - self.track.s[i_stop], 0.0)
        b = min(b_plan, tr.max_service_brake + G * self.grade[i_stop])
        B[-1] = min(tgt[-1], math.sqrt(2 * max(b, 0.05) * d_last))
        for k in range(len(B) - 2, -1, -1):
            i = i0 + k
            b = min(b_plan, tr.max_service_brake + G * self.grade[i])
            b = max(b, 0.05)
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
        b_plan = dr.brake_rate or tr.service_brake

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
            T.append(t), S.append(s), V.append(0.0), A.append(0.0)
            s_stop = stops[k + 1].s
            i0 = self._idx(s)
            i_stop = self._idx(s_stop)
            leg_tgt = self._leg_target(i0, i_stop, s_stop)
            B = self._braking_curve(i0, i_stop, s_stop, leg_tgt)
            B2 = B * B
            s_grid0 = self.track.s[i0]

            def Bat(x: float) -> float:
                if x >= s_stop:
                    return 0.0
                p = (x - s_grid0) / ds
                q = int(p)
                if q >= len(B) - 1:
                    # inside the last partial cell: exact parabola to the stop
                    return math.sqrt(max(2 * b_plan * (s_stop - x), 0.0))
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
                f_trac_max = tr.tractive_effort(v) * dr.power_fraction
                a_trac = (f_trac_max - f_ext) / m_eff
                tgt = leg_tgt[min(max(i - i0, 0), len(leg_tgt) - 1)]

                # --- will a brake application started now (delay + jerk ramp) stay under B?
                a1 = min(a, a_coast) if td > 0 else a
                s_p = s + v * td + 0.5 * a1 * td * td
                v_p = v + a1 * td
                tr_t = max((a1 + b_plan) / j, 0.0)
                s_r = s_p + v_p * tr_t + 0.5 * a1 * tr_t ** 2 - j * tr_t ** 3 / 6
                v_r = v_p + a1 * tr_t - 0.5 * j * tr_t ** 2
                need = v_r > Bat(s_r) + 0.02 or v > Bat(s + 0.5 * v * dt) + 0.02
                if braking:
                    braking = need or v > tgt + 0.1 or v > Bat(s + v * dt) - 0.05
                else:
                    braking = need
                if braking:
                    brake_clock += dt
                    s_n = s + max(v * dt, 0.02)
                    vb = Bat(s_n)
                    a_req = (vb * vb - v * v) / (2 * (s_n - s))
                    if need and a_req > -b_plan:
                        # below the curve but must start the jerk-limited ramp now
                        a_req = -b_plan
                    a_cmd = max(a_req, -tr.max_service_brake + G * min(self.grade[i], 0.0))
                    a_cmd = min(a_cmd, a_coast)  # no traction while braking
                    if brake_clock < td:
                        a_cmd = max(a_cmd, min(a, a_coast))  # brakes not yet effective
                else:
                    brake_clock = 0.0
                    if v < tgt - 0.05:
                        a_cmd = min(tr.max_accel * dr.power_fraction, a_trac)
                        a_cmd = min(a_cmd, math.sqrt(2 * j * max(tgt - v, 0.0)))
                    else:
                        a_cmd = max(min((tgt - v) / 2.0, a_trac), -b_plan)
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
        return RunResult(np.array(T), np.array(S), np.array(V), np.array(A), arrivals, departures,
                         e_trac / eff / 3.6e6, e_regen / 3.6e6, self.front_limit)
