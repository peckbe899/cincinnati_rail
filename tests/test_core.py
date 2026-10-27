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
    fixture = Path(__file__).resolve().parent / "data/Line_1_saved_2026-10-06.json"
    doc = json.loads(fixture.read_text())
    # the page as it was when saved: straight grades, no era cover rule, 500 ft platforms
    # Line 1's path then (before it was tied to the Deck's pieces, 27 October)
    mp = MetroProfile.load(Path(__file__).resolve().parent / "data/Line_1_line_2026-10-06.json", fixture,
                           root / "settings.json",
                           settings_override={"vcRadius": 0.0, "minCover_override": -1e9, "trough_override": -1e9,
                                              "platform": 152.4})
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


def test_rer_core_profile_matches_page():
    """RER cores with the canon rulings: the Union Terminal TRI box one level for A, B and D
    (135.7 m; Ben, 26 October), B/D on the north viaduct into the Straight box, the RER-3 covered
    way at 144 m dipping under the Little Miami, the Ohio tubes, the RER-5 deep bore; values as
    the Rail Profiles page shows them."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile/rer"
    load = lambda l: MetroProfile.load(root / f"lines/{l}.json", None, root / "settings.json")
    mp = load("RER_1")
    # with 3,000 m vertical curves and level transitions off each platform
    assert [round(z, 1) for z in mp.st] == [156.0, 154.8, 135.7, 154.1, 156.6, 148.9, 186.7,
                                           212.9, 217.9, 201.5, 204.5, 195.1]
    assert not mp.design()["short"]
    assert mp.summary()["grades_over_limit"] == 0
    r2 = load("RER_2")
    names = [s["name"] for s in r2.stations]
    # on the north viaduct (North Viaduct Plan), down into the Straight box, bored to Western
    assert [r2.st[names.index(n)] for n in ("Northside / Spring Grove", "Arlington", "Camp Washington", "Straight", "Union Terminal")] == \
        [162.5, 165.9, 165.2, 151.64, 135.7]
    assert r2.type_at(r2.stations[names.index("Arlington")]["c"]) == "elevated"
    assert r2.modes[names.index("Western")] == "under" and r2.modes[names.index("Mitchell Ave / WINTON PLACE")] == "surface"
    r3 = load("RER_3")
    names = [s["name"] for s in r3.stations]
    assert r3.st[names.index("Torrance")] == 144.0
    assert r3.type_at(r3.stations[names.index("Torrance")]["c"]) == "cutcover"
    assert min(z for c, z in r3.pvi) == pytest.approx(126.584, abs=0.01)  # Little Miami: pool - 3 m bed - 9.1 m
    assert r3.modes[names.index("Asbury")] == "surface"
    r5 = load("RER_5")
    assert r5.summary()["km_by_type"]["deep"] == pytest.approx(3.72, abs=0.05)  # shallower than bore + cover: cut and cover (670 ft platforms, Norwood cut)
    assert r3.summary()["shallow_tubes"] == 0


def test_vertical_curves_and_structure_rules():
    """Vertical curves are smooth (grade continuous) and stay off platforms; Metro structures
    and their cover follow Ben's rules."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json")
    c = np.arange(0.0, mp.length, 1.0)
    z = mp.rail_at(c)
    g = np.diff(z)
    assert np.max(np.abs(np.diff(g))) < 1.1 / 1500  # change of grade per metre about 1/R (1 m sampling)
    half = mp.settings["platform"] / 2
    for i, s in enumerate(mp.stations):
        cc = np.arange(max(0.0, s["c"] - half), min(mp.length, s["c"] + half), 2.0)
        assert np.allclose(mp.rail_at(cc), mp.st[i], atol=1e-6)  # platforms level
    # Ben's structure rules: Lines 8-14 shield is a double-track bore, Lines 1-7 a twin tube;
    # deep tube and river crossings are twin tubes; cover 2.0 m above the 140 m water table,
    # one outside diameter at or below it, 0.6 m over box roofs
    l3 = MetroProfile.load(root / "lines/Line_3.json", None, root / "settings.json")
    assert mp.struct_for("shield", 1000.0)["k"] == "bore" and l3.struct_for("shield", 1000.0)["k"] == "tube"
    assert mp.struct_for("deep", 1000.0)["top"] == 4.08 and mp.struct_for("cutcover", 1000.0)["top"] == 4.6
    bore = mp.struct_for("shield", 1000.0)
    assert mp.req_cover(bore, 150.0) == 2.0 and mp.req_cover(bore, 140.0) == 9.0
    assert mp.req_cover(mp.struct_for("cutcover", 1000.0), 150.0) == 0.6
    l1 = MetroProfile.load(root / "lines/Line_1.json", None, root / "settings.json")
    r = l1.data["rivers"][0]
    assert l1.struct_for("cutcover", (r["c0"] + r["c1"]) / 2)["k"] == "tube"


def test_sloped_platform_eases_the_bends():
    """A platform grade tilts the platform about its centre level and the transitions carry the
    platform grade on, so a station on a climb needs shorter curves at both ends."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json")
    # a station on a continuous climb or descent (not a crest or sag)
    i = next(k for k in range(1, len(mp.st) - 1) if (mp.st[k] - mp.st[k - 1]) * (mp.st[k + 1] - mp.st[k]) > 0)
    s, half = mp.stations[i], mp.settings["platform"] / 2
    d0 = mp.design()
    need0 = sum(mp.settings["vcRadius"] * abs(d0["g"][k] - d0["g"][k - 1]) for k in range(1, len(d0["dv"]) - 1)
                if d0["dv"][k]["kind"] == "x" and d0["dv"][k]["i"] == i)
    gin = (mp.st[i] - mp.st[i - 1]) / (s["c"] - mp.stations[i - 1]["c"])
    mp.sg[i] = 3.0 if gin > 0 else -3.0
    assert mp.rail_at(s["c"]) == pytest.approx(mp.st[i], abs=1e-9)  # centre level unchanged
    assert mp.rail_at(s["c"] + half - 1) - mp.rail_at(s["c"] - half + 1) == pytest.approx(mp.sg[i] / 1000 * (2 * half - 2), abs=1e-6)
    d1 = mp.design()
    need1 = sum(mp.settings["vcRadius"] * abs(d1["g"][k] - d1["g"][k - 1]) for k in range(1, len(d1["dv"]) - 1)
                if d1["dv"][k]["kind"] == "x" and d1["dv"][k]["i"] == i)
    assert need1 < need0 or need0 == 0


def test_platform_offset_and_removed_station(tmp_path):
    """The page can slide a platform along its drawn point (centre = point + offset, the point
    stays on the platform) and remove a station; the port solves without it and keeps keys."""
    import json
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    base = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json")
    names = [s["name"] for s in base.stations]
    gone, slid = names[2], names[4]
    half = base.settings["platform"] / 2
    doc = {"del": [gone], "so": {slid: 50.0, names[5]: 9999.0}, "st": {}}
    (tmp_path / "a.json").write_text(json.dumps(doc))
    mp = MetroProfile.load(root / "lines/Line_9.json", tmp_path / "a.json", root / "settings.json")
    assert [s["name"] for s in mp.stations] == [n for n in names if n != gone]
    k = [s["name"] for s in mp.stations].index(slid)
    assert mp.stations[k]["c"] == pytest.approx(base.stations[4]["c"] + 50.0)
    assert mp.stations[k]["c0"] == base.stations[4]["c"]
    assert mp.so[k + 1] == half  # clamped: the point is at the platform's end
    cc = np.arange(mp.stations[k]["c"] - half + 1, mp.stations[k]["c"] + half - 1, 2.0)
    assert np.allclose(mp.rail_at(cc), mp.st[k], atol=1e-6)  # the slid platform is level
    assert len(mp.st) == len(names) - 1


def test_platform_curvature_fit():
    """Platform curvature: the circle fit recovers a drawn arc's radius from straight segments,
    a straight span is infinite, and the flags follow 600 m / 3,000 m with the 15.56 m car."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile, fit_radius
    t = np.linspace(0, 152.4 / 500.0, 77)
    arc = np.column_stack([500 * np.cos(t), 500 * np.sin(t)])
    assert fit_radius(arc) == pytest.approx(500.0, rel=1e-6)
    assert fit_radius(np.column_stack([np.arange(0, 152.4, 2.0), np.zeros(77)])) == float("inf")
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json")
    pc = mp.platform_curves()
    assert len(pc) == len(mp.stations)
    for p in pc:
        if p["level"] == "error":
            assert p["R"] < 600 and p["outside"] > 0.05
        elif p["level"] == "warning":
            assert 600 <= p["R"] < 3000 and 0.01 < p["outside"] <= 0.0505
        else:
            assert p["R"] >= 3000 and p["outside"] <= 0.0101


def test_drawing_corner_flags():
    """Drawing checks: Line 1's 6th St platform sits on an S-curve (an error whatever the fitted
    radius); the piece joins with gaps show up as join kinks or doubling back (Line 1 as drawn from the KMZ, before it
    was tied to the Deck's pieces)."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(Path(__file__).resolve().parent / "data/Line_1_line_2026-10-06.json", None, root / "settings.json", settings_override={"platform": 152.4})
    sixth = next(p for p in mp.platform_curves() if p["name"].strip() == "6th")
    assert sixth["scurve"] == "error"
    kinds = {f["kind"] for f in mp.drawing_flags()}
    assert "doubles back" in kinds and all(f["level"] in ("error", "warning") for f in mp.drawing_flags())


def test_cvg_express_profile_canon():
    """CVG Express (Ben, Oct 16): 670 ft platforms of its own, Union Terminal at platform M on the
    CUT platform deck (160.3 m; Ben, 26 October), the Ohio on a bridge held at the navigation
    clearance level (no river tube)."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(root / "lines/CVG_Express.json", None, root / "settings.json")
    assert mp.settings["platform"] == pytest.approx(670 * 0.3048)
    assert mp.st[[s["name"] for s in mp.stations].index("Union Terminal")] == 160.3
    assert not mp.river_tubes(None)
    b = mp.river_bridges()[0]
    z = mp.rail_at(np.arange(b["c0"], b["c1"], 2.0))
    assert z.min() >= b["lb"] - 0.05 and mp.type_at((b["c0"] + b["c1"]) / 2) == "elevated"
    assert not mp.river_breaks()
    assert MetroProfile.load(root / "lines/Line_1.json", None, root / "settings.json").settings["platform"] == 121.92


def test_cut_norwood_context():
    """CUT and Norwood Central context (Ben, 26 October): the Deck's structures as blocks with the
    crossing rule, the Deck's street re-grades and open cuts in the ground, and painted cut and
    cover filled over; as the Rail Profiles page shows them."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    # Line 8 as saved passes 0.25 m under the CUT lower level (rail 144.0 m), needing 7.3 m
    l8 = MetroProfile.load(root / "lines/Line_8.json", root / "alignments/Line_8.json", root / "settings.json")
    assert any(b["l"] == "CUT lower level" for b in l8.context_blocks())
    x = next(x for x in l8.context_clearances() if x["with"] == "CUT lower level")
    assert not x["ok"] and x["clear"] == pytest.approx(0.25, abs=0.02) and x["need"] == pytest.approx(7.3, abs=0.01)
    # Line 4 along W 8th: the street raised up to 5 m over the intercity pair (re-grades do not add up)
    l4 = MetroProfile.load(root / "lines/Line_4.json", root / "alignments/Line_4.json", root / "settings.json")
    c = np.arange(11800.0, 12200.0, 2.0)
    dz = np.array([float(l4.ground_at(ci) - l4.ground_dem_at(ci)) for ci in c])
    assert dz.max() == pytest.approx(5.0, abs=0.01)
    # Norwood Central: the surface tracks in their cut, level at 178.0 m; Line 14 passes under them
    l14 = MetroProfile.load(root / "lines/Line_14.json", None, root / "settings.json")
    nw = next(b for b in l14.context_blocks() if b["l"] == "Norwood Central tracks")
    assert all(z == 178.0 for _, z in nw["p"])
    cm = (nw["c0"] + nw["c1"]) / 2
    assert float(l14.ground_at(cm)) == pytest.approx(178.0 - 0.8, abs=0.01)  # the cut floor
    # since 27 October its Norwood Central platform is the Deck's, past the north end of the cut: the default profile
    # (no saved profile) holds the station 4.7 m over the tracks' level, short of the 7.8 m a line under them needs
    x = [x for x in l14.context_clearances() if not x["ok"]]
    assert x and all(y["with"] == "Norwood Central tracks" for y in x)
    # painted cut and cover: the box keeps its level and the ground is filled to roof + cover
    l9 = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json")
    s0 = l9.stations[3]["c"]
    l9.ovr = [(s0 - 60.0, s0 + 60.0, "cutcover")]
    l9.refresh_fill()
    for ci in np.arange(s0 - 50.0, s0 + 50.0, 10.0):
        assert float(l9.ground_at(ci)) >= float(l9.rail_at(ci)) + 4.6 + 0.6 - 0.01


def test_context_street_openings():
    """Structure types at CUT (Ben, 26 October): under an embankment or an arch viaduct a line in the
    open may cross only at a street bridge or arch (the block's gaps); under a normal viaduct anywhere."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json")
    cs = np.arange(0.0, mp.length, 10.0)
    c = next(ci for ci in cs if mp.type_at(ci) == "atgrade" and all(mp.type_at(ci + d) == "atgrade" for d in (-20, 20)))
    z = float(mp.rail_at(c))
    blk = lambda st, gaps: {"n": "test", "l": "test", "k": "fill" if st == "embankment" else "viaduct", "st": st, "c0": c - 10, "c1": c + 10,
                            "p": [[c - 10, z + 9.0], [c, z + 9.0], [c + 10, z + 9.0]], "b": 1.6, "t": 5.8, "o": True, "pl": [], "s": "", "gaps": gaps}
    check = lambda b: (setattr(mp, "ctx", {"blocks": [b]}), mp.context_clearances()[0])[1]
    x = check(blk("embankment", []))          # no street opening: blocked
    assert x["blocked"] and not x["ok"]
    x = check(blk("arch", [[c - 12, c + 12, "a street"]]))   # under an arch over a street: 9.0 m clear, needs 1.6 + 0.5 + 4.2
    assert not x["blocked"] and x["ok"] and x["need"] == pytest.approx(6.3, abs=0.01)
    x = check(blk("viaduct", []))             # a normal viaduct: open between its piers
    assert not x["blocked"] and x["ok"]


def test_locked_stretch_holds():
    """Locked stretches of the RER canon (Ben, 27 October): a saved profile cannot move a locked station
    level or add a bend point inside the lock; outside it, it can."""
    import json
    import tempfile
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile/rer"
    lk = next(x for x in json.loads((root / "canon.json").read_text())["lines"]["RER_A_trunk"]["locked"] if "Evans" in x["st"])
    doc = json.loads((root / "alignments/RER_A_trunk.json").read_text())
    inside, outside = (lk["c0"] + lk["c1"]) / 2, lk["c1"] + 2000.0
    doc.setdefault("st", {})["Evans"] = lk["st"]["Evans"] + 5.0
    doc["pvi"] = doc["pvi"] + [[inside, 170.0], [outside, 150.0]]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
    mp = MetroProfile.load(root / "lines/RER_A_trunk.json", f.name, root / "settings.json")
    i = next(k for k, s in enumerate(mp.stations) if s["name"] == "Evans")
    assert mp.st[i] == pytest.approx(lk["st"]["Evans"])
    assert not any(abs(c - inside) < 0.5 for c, _ in mp.pvi)
    assert any(abs(c - outside) < 0.5 for c, _ in mp.pvi)


def test_rer_routes_follow_deck():
    """Every RER route and Metro line of the Rail Profiles page is its Mill Creek Deck pieces (Ben, 27 October): rebuilt
    from the Deck snapshot in data/deck, each path and each seg's length agree within tools/rer_deck_routes.TOL, and each
    station's platform (its point plus the saved slide) is at its Deck platform's centre. A failure means the Deck or a
    route changed: run tools/rer_deck_routes.py --apply and republish the page."""
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "tools"))
    import rer_deck_routes as rdr
    pieces, platforms = rdr.deck_pieces(), rdr.deck_platforms()
    bad, n = [], 0
    for rid, fn, al in rdr.routes():
        r = rdr.jload(fn)
        if not r.get("segs"):
            continue
        n += 1
        xy, segs, _ = rdr.rebuild(r, pieces)
        d, dl = rdr.drift(r, xy)
        dseg = max(abs((n_["c1"] - n_["c0"]) - (o["c1"] - o["c0"])) for o, n_ in zip(r["segs"], segs))
        sd = rdr.station_drift(r, platforms, rdr.slides(r, rdr.saved_doc(rid, al, None)))
        if max(d, dseg, abs(dl)) > rdr.TOL or sd:
            bad.append((rid, round(d, 2), round(dl, 2), round(dseg, 2), sd))
    assert n >= 39 and not bad, bad
