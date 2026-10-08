import math

import numpy as np
import pytest

from railsim.dynamics import Driver, Simulator, Stop, TrackData
from railsim.geo import INCH, MPH, LocalProjection, cumulative_length
from railsim.horizontal import CurveDesign, fit_horizontal
from railsim.network import Network
from railsim.profile import ProfileDesign, design_profile
from railsim.rollingstock import train_from_dict
from railsim.speed import Restriction, SpeedPolicy, build_from_zones, curve_speed


def ideal_train(**kw):
    d = dict(name="ideal", category="metro", length_m=100, cars=1, mass_empty_t=200, mass_load_t=0,
             rotating_mass_factor=0.0, adhesion=0.5, max_te_kn=1e6, power_kw=1e9, max_accel=1.0,
             service_brake=1.0, max_service_brake=1.2, jerk=1e6, max_speed_kmh=360,
             davis=dict(A_n=0, B_n_per_ms=0, C_n_per_ms2=0))
    d.update(kw)
    return train_from_dict("ideal", d)


def flat_track(L=3000.0, limit=20.0, ds=1.0):
    s = np.arange(0, L + ds, ds)
    n = len(s)
    return TrackData(ds, s, np.full(n, limit), np.zeros(n), np.zeros(n), np.zeros(n, bool))


# ----------------------------------------------------------------------------- dynamics

def test_constant_accel_run_matches_analytic():
    r = Simulator(ideal_train(), flat_track(), Driver(speed_margin=0.0, dt=0.05)).run(
        [Stop(0.0), Stop(2000.0)])
    # 0-20 m/s at 1 m/s^2: 20 s / 200 m twice, 1600 m cruise at 20 m/s
    assert r.arrivals[1] == pytest.approx(120.0, abs=0.3)


def test_restriction_held_until_rear_clears():
    tk = flat_track()
    tk.limit[(tk.s >= 1000) & (tk.s <= 1100)] = 10.0
    r = Simulator(ideal_train(), tk, Driver(speed_margin=0.0, dt=0.05)).run([Stop(0.0), Stop(2000.0)])
    v_at = np.interp([1000, 1150, 1199], r.s, r.v)
    assert np.all(v_at <= 10.0 + 0.05)  # 100 m train: restriction holds to 1200 m
    assert r.arrivals[1] == pytest.approx(135.0, abs=0.5)


def test_power_limit_slows_acceleration():
    weak = ideal_train(power_kw=1000)  # 200 t, 1 MW: a = P/(m v) falls below 1 m/s^2 above 5 m/s
    r = Simulator(weak, flat_track(), Driver(speed_margin=0.0, dt=0.05)).run([Stop(0.0), Stop(2000.0)])
    assert r.arrivals[1] > 125.0


def test_uphill_slower_than_downhill_when_power_limited():
    tr = ideal_train(power_kw=1500)
    tk = flat_track()
    tk.elevation = 0.02 * tk.s
    up = Simulator(tr, tk, Driver(speed_margin=0.0)).run([Stop(0.0), Stop(2000.0)])
    down_tk = tk.reversed()
    down = Simulator(tr, down_tk, Driver(speed_margin=0.0)).run([Stop(0.0), Stop(2000.0)])
    assert up.arrivals[1] > down.arrivals[1] + 3.0


def test_jerk_limit_respected_in_traction():
    tr = ideal_train(jerk=0.5)
    r = Simulator(tr, flat_track(), Driver(speed_margin=0.0, dt=0.1)).run([Stop(0.0), Stop(2000.0)])
    da = np.diff(r.a) / np.maximum(np.diff(r.t), 1e-9)
    moving = r.v[1:] > 0.5
    assert np.max(np.abs(da[moving])) <= 0.5 + 1e-6


# ----------------------------------------------------------------------------- geometry

def test_dense_drawn_arc_is_recovered_as_one_curve():
    d = CurveDesign(line_speed=55 * MPH, max_cant=6 * INCH, max_cant_deficiency=3 * INCH)
    R = 400.0
    th = np.radians(np.linspace(0, 60, 13))
    arc = np.column_stack([R * np.sin(th), R - R * np.cos(th)])
    u = np.array([math.cos(math.radians(60)), math.sin(math.radians(60))])
    pts = np.vstack([[-500, 0], arc, arc[-1] + 500 * u])
    h = fit_horizontal(pts, d)
    assert len(h.curves) == 1
    assert h.curves[0].radius == pytest.approx(R, rel=0.12)
    assert math.degrees(h.curves[0].deflection) == pytest.approx(60.0, abs=0.5)


def test_single_corner_respects_offset_tolerance():
    d = CurveDesign(line_speed=55 * MPH, max_cant=6 * INCH, max_cant_deficiency=3 * INCH,
                    corner_offset_tol=20.0)
    u = np.array([math.cos(math.radians(60)), math.sin(math.radians(60))])
    h = fit_horizontal(np.array([[-500, 0], [0, 0], 500 * u]), d)
    c = h.curves[0]
    p = c.spiral ** 2 / (24 * c.radius)
    external = (c.radius + p) / math.cos(c.deflection / 2) - c.radius
    assert external <= 20.5
    assert h.length < cumulative_length(np.array([[-500, 0], [0, 0], 500 * u]))[-1]


def test_network_routes_through_branch_without_reversing():
    trunk = np.array([[0, 0], [1000, 0]])
    branch_a = np.array([[1000, 0], [2000, 300]])
    branch_b = np.array([[1000, 0], [2000, -300]])
    net = Network.build([trunk, branch_a, branch_b])
    a = net.locate(100, 0)
    b = net.locate(1900, -270)
    xy, ch = net.route([a[:2], b[:2]])
    assert xy[-1][1] < -200
    assert ch[-1] == pytest.approx(900 + math.hypot(900, 270), rel=0.02)
    # a->b->a would need a reversal at the junction: impossible
    c = net.locate(1900, 270)
    with pytest.raises(ValueError):
        net.route([b[:2], c[:2]], max_turn_deg=50)


def test_t_junction_is_split():
    main = np.array([[0, 0], [2000, 0]])
    spur = np.array([[1000, 5], [1000, 800]])
    net = Network.build([main, spur])
    assert len(net.edges) == 3


def test_profile_respects_grade_limits_and_platforms():
    rng = np.random.default_rng(0)

    def ground(s):
        return 150 + 30 * np.sin(s / 1500) + rng.normal(0, 0.3, len(s))

    d = ProfileDesign(max_grade=0.02)
    p = design_profile(12000, ground, d, stations=[3000, 9000])
    assert np.max(np.abs(p.grade)) <= 0.02 + 1e-6
    assert abs(p.grade_at(3000)) <= 0.005 + 1e-6


def test_curve_speed_formula():
    pol = SpeedPolicy(line_speed=100.0, cant_deficiency=3 * INCH, rail_centres=1.5)
    # metric check: V(km/h) = sqrt(R (Ea+Eu)/11.8) with mm  -> R=400, 150+76 -> ~87.5 km/h
    v = curve_speed(400.0, 0.150, 200.0, pol) * 3.6
    assert v == pytest.approx(math.sqrt(400 * 226.2 / 11.8), rel=0.01)


def test_speed_profile_reverse_is_mirror():
    sp = build_from_zones(1000.0, [Restriction(200, 300, 5.0)], grid=5.0, default=20.0)
    rv = sp.reversed(1000.0)
    assert rv.at(750.0) == 5.0 and rv.at(650.0) == 20.0 and rv.at(805.0) == 20.0


def test_projection_roundtrip():
    p = LocalProjection(39.1, -84.5)
    x, y = p.to_xy(39.2, -84.4)
    lat, lon = p.to_latlon(x, y)
    assert lat == pytest.approx(39.2, abs=1e-9) and lon == pytest.approx(-84.4, abs=1e-9)


def test_adhesion_tapers_with_speed_and_rail_condition():
    tr = ideal_train(adhesion=0.3, adhesive_mass_fraction=0.5, max_te_kn=1e6, power_kw=1e9)
    assert tr.adhesion_at(0.0) == pytest.approx(0.3)
    assert tr.adhesion_at(100 / 3.6) < 0.3 * 0.7  # Curtius-Kniffler: ~0.64 of standstill at 100 km/h
    wet = tr.with_load(0.0, "wet")
    assert wet.tractive_effort(1.0) < tr.tractive_effort(1.0)
