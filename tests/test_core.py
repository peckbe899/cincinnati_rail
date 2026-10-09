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


def test_unit_aware_merge():
    from railsim.app import deep_merge
    m = deep_merge({"g": {"line_speed_mph": 79, "max_cant_in": 5}}, {"g": {"line_speed_kmh": 300}})
    assert m["g"] == {"max_cant_in": 5, "line_speed_kmh": 300}


def test_speed_dependent_braking_curve_lowers_high_speed_rate():
    tr = ideal_train(brake_curve_kmh_ms2=[[0, 1.0], [100, 1.0], [101, 0.4], [360, 0.4]])
    sim = Simulator(tr, flat_track(limit=90.0), Driver(speed_margin=0.0))
    assert sim.b_plan(80.0, 0) == pytest.approx(0.4)
    assert sim.b_plan(10.0, 0) == pytest.approx(1.0)


def test_lineside_anticipation_reaches_limit_early():
    tk = flat_track()
    tk.limit[(tk.s >= 1000) & (tk.s <= 1100)] = 10.0
    r = Simulator(ideal_train(), tk, Driver(speed_margin=0.0, anticipation_m=100.0)).run(
        [Stop(0.0), Stop(2000.0)])
    assert np.interp(905.0, r.s, r.v) <= 10.05


def test_neutral_section_costs_time_when_accelerating():
    tk = flat_track()
    base = Simulator(ideal_train(power_kw=2000), tk, Driver(speed_margin=0.0)).run([Stop(0.0), Stop(2000.0)])
    tk2 = flat_track()
    tk2.no_traction[(tk2.s >= 50) & (tk2.s <= 250)] = True
    cut = Simulator(ideal_train(power_kw=2000), tk2, Driver(speed_margin=0.0)).run([Stop(0.0), Stop(2000.0)])
    assert cut.arrivals[1] > base.arrivals[1] + 3.0


# ----------------------------------------------------------------------------- operations

def test_fixed_block_codes_brake_earlier_than_continuous():
    tk = flat_track(L=4000.0)
    tk.limit[(tk.s >= 2000) & (tk.s <= 2300)] = 8.0
    cont = Simulator(ideal_train(), tk, Driver(speed_margin=0.0)).run([Stop(0.0), Stop(3800.0)])
    tk2 = flat_track(L=4000.0)
    tk2.limit[(tk2.s >= 2000) & (tk2.s <= 2300)] = 8.0
    blk = Simulator(ideal_train(), tk2, Driver(speed_margin=0.0, block_length=300.0)).run(
        [Stop(0.0), Stop(3800.0)])
    assert blk.arrivals[1] > cont.arrivals[1] + 1.0


def test_operating_zone_driver_applies_only_in_its_zone():
    tk = flat_track()
    tk.zone = np.where(tk.s > 1000, 1, 0)
    slow = Driver(speed_margin=5.0)
    sim = Simulator(ideal_train(), tk, Driver(speed_margin=0.0), zone_drivers=[slow])
    assert sim.target[500] == pytest.approx(20.0)
    assert sim.target[1500] == pytest.approx(15.0)


def test_tilt_raises_curve_speed_only_below_cutoff():
    base = SpeedPolicy(line_speed=100.0, cant_deficiency=0.09)
    tilt = SpeedPolicy(line_speed=100.0, cant_deficiency=0.09, tilt_cant_deficiency=0.15,
                       tilt_max_speed=265 / 3.6)
    v_tight = curve_speed(1500.0, 0.15, 300.0, base)
    assert curve_speed(1500.0, 0.15, 300.0, tilt) > v_tight + 5.0
    # on a curve fast enough that tilt would exceed the cut-off, tilt gives no gain above it
    assert curve_speed(8000.0, 0.15, 300.0, tilt) <= max(curve_speed(8000.0, 0.15, 300.0, base),
                                                         265 / 3.6) + 1e-6


def test_era_lookup_picks_fleet_and_overlay():
    from pathlib import Path
    from railsim.operations import load_era
    path = Path(__file__).resolve().parent.parent / "data/operations/cincinnati_metro.yaml"
    era, train, year = load_era(path, 1995)
    assert era["goa"] == 2 and train == "CMCC_TYPE1985_10CAR"
    era, train, _ = load_era(path, 2026)
    assert era["goa"] == 3 and era["overlay"]["signalling"]["system"] == "cbtc"


def test_stub_terminal_reversal_routing():
    # line drawn into a stub station and back out the same way (like St Louis Union Station)
    a = np.array([[0, 0], [1000, 0], [2000, 0]])
    b = np.array([[2000, 0], [1000, 5], [0, 400]])
    net = Network.build([a, b], snap_tol=1.0)
    s0 = net.locate(0, 0)[:2]
    s1 = net.locate(0, 400)[:2]
    with pytest.raises(ValueError):
        net.route([s0, s1], max_turn_deg=90)
    tip = net.stub_tip(1990, 0, 100)
    assert tip is not None
    xy, ch = net.route([s0, tip[:2], s1], max_turn_deg=90, reverse_at=[1])
    assert ch[1] == pytest.approx(2000, rel=0.01) and ch[-1] > 3900


def test_duplicate_drawn_track_is_merged():
    a = np.array([[0, 0], [1000, 0]])
    net = Network.build([a, a.copy(), np.array([[1000, 0], [2000, 0]])])
    assert len(net.edges) == 2


def test_reversal_jump_moves_front():
    tk = flat_track(L=3000.0)
    r = Simulator(ideal_train(), tk, Driver(speed_margin=0.0)).run(
        [Stop(0.0), Stop(1000.0, dwell=60.0, jump=106.0), Stop(2500.0)])
    assert r.departures[1] - r.arrivals[1] == pytest.approx(60.0, abs=0.5)
    assert np.max(r.s) == pytest.approx(2500.0, abs=0.5)


def test_driver_only_button_doors_beat_crew_doors_at_low_platforms():
    from railsim.dwell import CommuterDwell
    crew = CommuterDwell(door_control="crew", conductor=8.0)
    button = CommuterDwell(door_control="button", dispatch=4.0)
    # crew opens only some doors at low platforms; driver-only stock opens them all
    assert button.dwell("busy", "low", 12, 1) < crew.dwell("busy", "low", 12, 1) - 20.0
    assert button.dwell("minor", "high", 12, 2) <= crew.dwell("minor", "high", 12, 2)


def test_platform_screen_doors_only_where_fitted():
    from railsim.dwell import MetroDwell
    from railsim.line import StationInfo
    from railsim.metro import has_psd
    d = MetroDwell(psd_overhead=3.0, min_dwell=0.0)
    dcfg = {"psd_classes": ["transfer"]}
    hub, minor = StationInfo("Hub", 0, 0, cls="transfer"), StationInfo("Halt", 0, 0, cls="minor")
    assert has_psd(hub, dcfg) and not has_psd(minor, dcfg)
    minor.psd = True  # per-station override
    assert has_psd(minor, dcfg)
    assert d.dwell("minor", 20, 2, psd=True) == pytest.approx(d.dwell("minor", 20, 2, psd=False) + 3.0)


@pytest.mark.parametrize("R, tilt, mph", [
    (6000, False, 234), (7000, False, 253), (8000, False, 271), (10000, False, 303),
    (2500, False, 159), (1000, False, 101), (1000, True, 121), (2000, True, 172),
    (2500, True, 186),  # 192 mph theoretical, tilt locked above 186 mph
])
def test_apex_canon_curve_speeds(R, tilt, mph):
    """APEx corrected curve model: C = 30.56 V^2/R, D = 180 mm, Eu 130 mm up to 186 mph and
    100 mm above, 8 deg tilt adding ~140 mm below 186 mph."""
    pol = SpeedPolicy(line_speed=320 * MPH, cant_deficiency=0.100,
                      deficiency_bands=((186 * MPH, 0.130), (math.inf, 0.100)),
                      tilt_cant_deficiency=0.140 if tilt else 0.0,
                      tilt_max_speed=186 * MPH if tilt else 0.0)
    v = curve_speed(R, 0.180, 1000.0, pol) / MPH
    assert v == pytest.approx(mph, abs=1.5)


def test_metro_profile_port_matches_saved_page_output():
    """The Python port reproduces the Metro Profiles page: station rail levels and types
    saved with Line 1 (computed on the LiDAR ground the page used when it was saved)."""
    import json
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    doc = json.loads((root / "alignments/Line_1.json").read_text())
    mp = MetroProfile.load(root / "lines/Line_1.json", root / "alignments/Line_1.json",
                           root / "settings.json")
    mp._ground = np.array([np.nan if v is None else v / 10 for v in mp.data["ground_dm_lidar"]])
    for i, s in enumerate(doc["stations"]):
        assert mp.st[i] == pytest.approx(s["rail"], abs=0.02)
        assert mp.type_at(s["c"]) == s["type"]
    assert mp.summary()["km_by_type"]["shield"] == pytest.approx(dict(doc["summary"])["km_by_type"]["shield"], abs=0.02)


def test_metro_default_solver_respects_grade_limit():
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json")  # no saved profile
    assert mp.summary()["grades_over_limit"] == 0
