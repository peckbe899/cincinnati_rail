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
                                              "platform": 152.4, "legacy_structures": True})
    mp._ground = np.array([np.nan if v is None else v / 10 for v in mp.data["ground_dm_lidar"]])
    for i, s in enumerate(doc["stations"]):
        assert mp.st[i] == pytest.approx(s["rail"], abs=0.02)
        assert mp.type_at(s["c"]) == s["type"]
    assert mp.summary()["km_by_type"]["shield"] == pytest.approx(dict(doc["summary"])["km_by_type"]["shield"], abs=0.02)


def test_metro_default_solver_respects_grade_limit():
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json", records="repo")  # no saved profile
    assert mp.summary()["grades_over_limit"] == 0


def test_rer_core_profile_matches_page():
    """RER cores with the canon rulings: the Union Terminal TRI box one level for A, B and D
    (135.7 m; Ben, 26 October), B/D on the north viaduct into the Straight box, the RER-3 covered
    way at 144 m dipping under the Little Miami (a sunk box), the Ohio sunk boxes, the RER-5 deep bore; values as
    the Rail Profiles page shows them."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile/rer"
    load = lambda l: MetroProfile.load(root / f"lines/{l}.json", None, root / "settings.json", records="repo")
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
    lm = next(r for r in r3.data["rivers"] if r["name"] == "Little Miami River")
    assert float(r3.rail_at((lm["c0"] + lm["c1"]) / 2)) == pytest.approx(132.084, abs=0.01)  # Little Miami sunk box: pool - 3 m bed - 6.6 + 3.0 m
    assert all(r3.type_at(c) == "sunk" for c in (lm["c0"] + 5, lm["c1"] - 5))
    assert r3.modes[names.index("Asbury")] == "surface"
    r5 = load("RER_5")
    assert r5.summary()["km_by_type"]["deep"] == pytest.approx(3.61, abs=0.05)  # shallower than bore + cover: cut and cover (670 ft platforms, Norwood cut at 185.5 m)
    # the Little Miami box inside its band; the Ohio range on RER-3 is the shore beside the embanked covered way (no crossing)
    assert r3.summary()["shallow_tubes"] == 0 and [b["name"] for b in r3.river_tubes()] == ["Little Miami River"]


def test_vertical_curves_and_structure_rules():
    """Vertical curves are smooth (grade continuous) and stay off platforms; Metro structures
    and their cover follow Ben's rules."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json", records="repo")
    c = np.arange(0.0, mp.length, 1.0)
    z = mp.rail_at(c)
    g = np.diff(z)
    assert np.max(np.abs(np.diff(g))) < 1.1 / 1500  # change of grade per metre about 1/R (1 m sampling)
    half = mp.settings["platform"] / 2
    for i, s in enumerate(mp.stations):
        cc = np.arange(max(0.0, s["c"] - half), min(mp.length, s["c"] + half), 2.0)
        assert np.allclose(mp.rail_at(cc), mp.st[i], atol=1e-6)  # platforms level
    # Ben's structure rules (the shared record, 28 October): the bored tunnel follows the building phase, shallow or
    # deep: Lines 1-7 type A twin tubes (5.10 m inside, 5.50 m outside, rail 0.70 m over the invert: 0.90 below, 4.60 to
    # the top), Lines 8-12 the 9.0 m double-track bore (2.50 below, 6.50 to the top); cover one outside diameter over
    # every bored tube (Ben, 28 October: the ground arches over it), 0.6 m over box roofs
    l3 = MetroProfile.load(root / "lines/Line_3.json", None, root / "settings.json", records="repo")
    assert mp.struct_for("shield", 1000.0)["k"] == "bore" and l3.struct_for("shield", 1000.0)["k"] == "tube"
    assert mp.struct_for("deep", 1000.0)["top"] == pytest.approx(6.5) and l3.struct_for("deep", 1000.0)["top"] == pytest.approx(4.6)
    assert l3.struct_for("shield", 1000.0)["od"] == 5.5 and mp.struct_for("cutcover", 1000.0)["top"] == 4.6
    bore = mp.struct_for("shield", 1000.0)
    assert mp.req_cover(bore, 150.0) == 9.0 and mp.req_cover(bore, 140.0) == 9.0 and l3.req_cover(l3.struct_for("shield", 1000.0), 150.0) == 5.5
    assert mp.req_cover(mp.struct_for("cutcover", 1000.0), 150.0) == 0.6
    l1 = MetroProfile.load(root / "lines/Line_1.json", None, root / "settings.json", records="repo")
    r = l1.data["rivers"][0]
    # every river crossing in tunnel is a sunk double-track box (Ben, 30 October): roof from 5 m below the bed to 3 m above
    # it, rail from bed - 10.0 to bed - 2.0 m (the lower limit on the flat bottom only)
    mid = (r["c0"] + r["c1"]) / 2
    assert l1.struct_for("cutcover", mid)["k"] == "sunk" and l1.struct_for("sunk", mid)["top"] == 5.0
    band = l1.river_band(r)
    assert band["ub"] == pytest.approx(band["low"] - 2.0) and band["lb"] <= band["low"] - 9.0 and band["nav"] is not None
    assert l1.type_at(mid) == "sunk"


def test_sloped_platform_eases_the_bends():
    """A platform grade tilts the platform about its centre level and the transitions carry the
    platform grade on, so a station on a climb needs shorter curves at both ends."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json", records="repo")
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
    base = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json", records="repo")
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
    mp = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json", records="repo")
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
    mp = MetroProfile.load(root / "lines/CVG_Express.json", None, root / "settings.json", records="repo")
    assert mp.settings["platform"] == pytest.approx(670 * 0.3048)
    assert mp.st[[s["name"] for s in mp.stations].index("Union Terminal")] == 160.3
    assert not mp.river_tubes(None)
    b = mp.river_bridges()[0]
    z = mp.rail_at(np.arange(b["c0"], b["c1"], 2.0))
    assert z.min() >= b["lb"] - 0.05 and mp.type_at((b["c0"] + b["c1"]) / 2) == "elevated"
    assert not mp.river_breaks()
    assert MetroProfile.load(root / "lines/Line_1.json", None, root / "settings.json", records="repo").settings["platform"] == 121.92


def test_cut_norwood_context():
    """CUT and Norwood Central context (Ben, 26 October): the Deck's structures as blocks with the
    crossing rule, the Deck's street re-grades and open cuts in the ground, and painted cut and
    cover filled over; as the Rail Profiles page shows them."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    # Line 8 as saved passes 0.25 m under the CUT lower level (rail 144.0 m); with one bore diameter of cover (Ben, 28
    # October) it is cut and cover there, needing 1.0 + 0.5 + 4.6 = 6.1 m (was 8.0 m in the 9.0 m bore)
    l8 = MetroProfile.load(root / "lines/Line_8.json", root / "alignments/Line_8.json", root / "settings.json")
    assert any(b["l"] == "CUT lower level" for b in l8.context_blocks())
    x = next(x for x in l8.context_clearances() if x["with"] == "CUT lower level")
    assert not x["ok"] and x["clear"] == pytest.approx(0.25, abs=0.02) and x["need"] == pytest.approx(6.1, abs=0.01)
    # Line 4 along W 8th: the street raised up to 5 m over the intercity pair (re-grades do not add up)
    l4 = MetroProfile.load(root / "lines/Line_4.json", root / "alignments/Line_4.json", root / "settings.json")
    c = np.arange(11800.0, 12200.0, 2.0)
    dz = np.array([float(l4.ground_at(ci) - l4.ground_dem_at(ci)) for ci in c])
    assert dz.max() == pytest.approx(5.0, abs=0.01)
    # Norwood Central: the surface tracks in their cut, level at 185.5 m; Line 14 passes under them
    l14 = MetroProfile.load(root / "lines/Line_14.json", None, root / "settings.json", records="repo")
    nw = next(b for b in l14.context_blocks() if b["l"] == "Norwood Central tracks")
    assert all(z == 185.5 for _, z in nw["p"])
    cm = (nw["c0"] + nw["c1"]) / 2
    assert float(l14.ground_at(cm)) == pytest.approx(185.5 - 0.8, abs=0.01)  # the cut floor
    # since 27 October its Norwood Central platform is the Deck's, past the north end of the cut: the default profile
    # (no saved profile) holds the station 4.7 m over the tracks' level, short of the 7.8 m a line under them needs
    x = [x for x in l14.context_clearances() if not x["ok"]]
    assert x and all(y["with"] == "Norwood Central tracks" for y in x)
    # painted cut and cover: the box keeps its level and the ground is filled to roof + cover
    l9 = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json", records="repo")
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
    mp = MetroProfile.load(root / "lines/Line_9.json", None, root / "settings.json", records="repo")
    cs = np.arange(0.0, mp.length, 10.0)
    c = next(ci for ci in cs if mp.type_at(ci) == "atgrade" and all(mp.type_at(ci + d) == "atgrade" for d in (-20, 20)))
    z = float(mp.rail_at(c))
    blk = lambda st, gaps: {"n": "test", "l": "test", "k": "fill" if st == "embankment" else "viaduct", "st": st, "c0": c - 10, "c1": c + 10,
                            "p": [[c - 10, z + 9.0], [c, z + 9.0], [c + 10, z + 9.0]], "b": 1.6, "t": 5.8, "o": True, "pl": [], "s": "", "gaps": gaps}
    check = lambda b: (setattr(mp, "ctx", {"blocks": [b]}), mp.context_clearances()[0])[1]
    x = check(blk("embankment", []))          # no street opening: blocked
    assert x["blocked"] and not x["ok"]
    x = check(blk("arch", [[c - 12, c + 12, "a street"]]))   # under an arch over a street: 9.0 m clear, needs 1.6 + 0.5 + 4.57 (Metro clear height, 28 October)
    assert not x["blocked"] and x["ok"] and x["need"] == pytest.approx(6.67, abs=0.01)
    x = check(blk("viaduct", []))             # a normal viaduct: open between its piers
    assert not x["blocked"] and x["ok"]


def test_north_viaduct_street_rule():
    """The north arch viaduct (Ben, 28 October): rail at the finished street + 7.4 m at every street it crosses,
    165.9 m over the Arlington platform, one dip (1.5% down, one grade up) to Ludlow at 162.5 m; W 8th's hump at most
    1.9 m under the south approach (a median pier); girders span / 10 + 0.8 m; the upper deck 7.9 m over the highest rail it crosses (RER A and R5, 167.0 m)."""
    import sys
    from pathlib import Path
    pytest.importorskip("rasterio")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import make_profile_context as m
    B = m.build()
    N = B["north"]
    for s in N["streets"]:
        if not s["clip"] and s["d1"] < N["dL"] - 15:
            assert s["rail"] >= s["need"] - 0.01, s["name"]
    assert N["z_of_d"](sum(N["dA"]) / 2) == pytest.approx(165.9)
    assert N["z_of_d"](N["dL"]) == pytest.approx(162.5)
    assert 0 < N["climb"] <= 0.015
    zs = [N["z_of_d"](d) for d in np.arange(N["dA"][1], N["dL"], 5.0)]
    assert all(b - a <= 0.015 * 5 + 1e-6 and a - b <= 0.015 * 5 + 1e-6 for a, b in zip(zs, zs[1:]))
    w8 = next(r for r in B["REG"] if r["name"] == "W 8th (viaduct line)")
    assert max(w8["dz"](x, 0) for x in np.arange(m.W8_WEST_FACE, 712941, 5.0)) <= 1.9 + 1e-6   # median pier (Ben, 28 October)
    g = m.girder(33.5, "W 8th (viaduct line)")
    assert g["spans"] == 2 and g["depth"] == pytest.approx(2.48, abs=0.01) and 161.7 - g["depth"] - 4.3 - 153.0 >= 1.9 - 0.01
    assert m.girder(18.3)["depth"] == pytest.approx(2.63, abs=0.01) and m.girder(50.0, "Millvale Boulevard")["flag"]
    assert B["indy"]["H"] == pytest.approx(167.0 + 7.9, abs=0.05)


def test_tunnel_methods_by_era():
    """Metro tunnels by era (Ben, 28 October): shield only with a tube diameter of cover; a bored stretch is a whole drive
    from box to box (or portal, deep station) at any length, else at least its phase's minimum drive; between the
    shield minimum and the cut-and-cover limit, cut and cover unless it makes a drive. Station approaches (Ben, 28 October:
    the box carries on until the tracks reach the tubes' spacing) are switch points."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    for lid in ("Line_3", "Line_10"):
        mp = MetroProfile.load(root / f"lines/{lid}.json", None, root / "settings.json", records="repo")
        T = mp.stretch_types()
        step, ts = T["step"], T["t"]
        tun = [mp._point_type(min(k * step, mp.length), T["z"][k]) for k in range(len(ts))]
        for a in T["approaches"]:   # station approach boxes are anchors (switch points), like the stations
            for k in range(len(ts)):
                if min(a["c"], a["c"] + a["side"] * a["len"]) - 1e-6 <= k * step <= max(a["c"], a["c"] + a["side"] * a["len"]) + 1e-6:
                    tun[k] = {"t": "cutcover"}
        bored = lambda k: "cls" in tun[k] and ts[k] in ("shield", "deep")
        k = 0
        while k < len(ts):
            if not bored(k):
                k += 1
                continue
            j = k
            while j + 1 < len(ts) and bored(j + 1):
                j += 1
            ends_at_cc = (k > 0 and "cls" in tun[k - 1]) or (j + 1 < len(ts) and "cls" in tun[j + 1])
            # the anchors either side (station boxes, approaches, portals): a drive is the only one between them, at any
            # length (Ben, 29 October: the boxes carry on through the shallow ends), else at least the minimum
            a0 = k
            while a0 > 0 and "cls" in tun[a0 - 1]:
                a0 -= 1
            b0 = j
            while b0 + 1 < len(ts) and "cls" in tun[b0 + 1]:
                b0 += 1
            others = any(bored(i) for i in list(range(a0, k)) + list(range(j + 1, b0 + 1)))
            # (between two anchors the bored stretches are one drive at any length, Ben 29 October; a stretch too shallow
            # to bore inside it is cut and cover, so only the cover is checked below)
            for m in range(k, j + 1, 25):
                c = m * step
                sc = mp.struct_for("shield", c)
                if tun[m].get("cls") != "C":
                    assert float(mp.ground_at(c) - mp.rail_at(c)) >= sc["top"] + sc["od"] - 1e-6, (lid, c)
            k = j + 1
    assert mp.phase_rules(1000.0) == {"cc_max": 16.5, "min_drive": 300.0, "deep_from": 18.29, "tbm": False}   # Line 10, Phase 2


def test_station_approach_boxes():
    """A cut-and-cover station meeting type A tubes keeps its box through the approach (Ben, 28 October): side
    platforms spread 2.42 m a track, islands close 1.08 m; the approach is max(approach_m, sqrt(4 x min radius x shift)), plus
    any straight before an arc into a curve (option A)."""
    import math
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    mp = MetroProfile.load(root / "lines/Line_3.json", None, root / "settings.json", records="repo")
    T = mp.stretch_types()
    ap = [a for a in T["approaches"] if a["station"]]
    assert ap
    for a in ap:
        rmin = mp.ms["phases"][mp._phase_at(a["c"])]["min_radius"]   # by phase (Ben: 40, 55, 70 m)
        want = max(mp.ms["approach_m"], math.sqrt(4 * rmin * abs(a["shift"])))
        want += next((x["extra"] for x in mp.approach_extra if x["side"] == a["side"] and x.get("station") == a["station"]), 0.0)
        assert a["len"] == pytest.approx(want, abs=T["step"] + 1e-6) or a["len"] < want   # (cut short only by a neighbour)
        assert abs(a["shift"]) == pytest.approx(2.42 if a["kind"] == "side" else 1.08, abs=0.01)
        c = a["c"] + a["side"] * a["len"] / 2
        assert mp.type_at(c) == "cutcover"


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


def test_approach_boxes_at_canon_and_tube_stations():
    """Every place a tube meets a box changes the track spacing inside a box (Ben, 30 October: the deep tube up Mt Auburn
    ran straight into McMicken): canon tunnels count as bored, stations in canon sections get their approaches, a tube
    station meeting a box gets one, and a drive made by a later pass gets one too."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent / "data/profile"
    load = lambda l: MetroProfile.load(root / f"lines/{l}.json", Path(__file__).resolve().parent.parent / f"hub/seed/alignments/{l}.json", root / "settings.json")
    for lid in ("Line_2", "Line_3", "Line_5", "Line_7"):
        mp = load(lid)
        T = mp.stretch_types()
        ap = T["approaches"]
        inside = lambda c: any(min(a["c"], a["c"] + a["side"] * a["len"]) - 3 <= c <= max(a["c"], a["c"] + a["side"] * a["len"]) + 3 for a in ap)
        step = T["step"]
        t = [mp.type_at(i * step) for i in range(len(T["t"]))]   # as drawn: paints included
        for i in range(1, len(t)):
            a, b = t[i - 1], t[i]
            if {a, b} & {"shield", "deep"} and "cutcover" in (a, b):
                c = i * step if a in ("shield", "deep") else (i - 1) * step
                tc = (i - 1) * step if a in ("shield", "deep") else i * step   # the tube side
                if mp.struct_for("shield", tc).get("k") == "bore":
                    continue   # the bore runs at the box's 3.90 m
                # the spacing changes in an approach in the box the tube meets (it may be done near the station, the box then
                # carrying on at running spacing to where the shield starts)
                d = 1 if a in ("shield", "deep") else -1
                k, box = (i if d == 1 else i - 1), []
                while 0 <= k < len(t) and t[k] == "cutcover":
                    box.append(k * step)
                    k += d
                assert any(inside(q) for q in box) or mp.override_at(c) == "cutcover", f"{lid}: tube meets box at {c:.0f} m with no approach"


def test_tube_form_by_drive_ends_and_paint():
    """Tube form (Ben, 31 October): a drive between two double-track ends with the bore's cover is the double-track bore,
    with no approach box; an island end or a mined station of a twin-tube phase keeps twin tubes; a painted form decides,
    and a spacing change inside the tunnel is flagged."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent
    load = lambda l: MetroProfile.load(root / f"data/profile/lines/{l}.json", root / f"hub/seed/alignments/{l}.json", root / "data/profile/settings.json")
    mp = load("Line_8")   # Phase 2: the bore between double-track ends, no spacing change
    T = mp.stretch_types()
    i = int(5400 / T["step"])
    assert T["t"][i] in ("shield", "deep") and T["tube"][i] == "bore" and mp.struct_for("deep", 5400)["k"] == "bore"
    assert not [a for a in T["approaches"] if 4500 < a["c"] < 6450 and a["kind"] != "river"]
    mp = load("Line_2")   # Holmes and Meinken are island stations: twin tubes between them
    T = mp.stretch_types()
    assert T["tube"][int(18200 / T["step"])] in ("A", "C")
    mp = load("Line_3")   # Henry Clay (side box) on to Ft Wright (a mined station, Phase 1): twin tubes
    T = mp.stretch_types()
    assert T["tube"][int(21800 / T["step"])] in ("A", "C")   # twin tubes (Phase 3 on Ben's Chronology: type C)
    mp.tf = [(21150.0, 22420.0, "bore")]   # painted bore: no approach at Henry Clay; the spacing change in Ft Wright flagged
    mp._types = None
    T = mp.stretch_types()
    assert T["tube"][int(21800 / T["step"])] == "bore"
    assert not [a for a in T["approaches"] if a.get("station") == "Henry Clay"]
    assert any(f["kind"] == "spacing change in the tunnel" and 22300 < f["c0"] < 22500 for f in T["flags"])


def test_engine_rules_hold_on_every_metro_line():
    """The tunnel engine (Ben, 31 October): no box station deeper than its phase's cut-and-cover limit (unpainted); no box
    between two bored stretches except a shaft or a station; no tube shorter than a drive between two boxes unless it is
    flagged; Paycor (16.95 m in Phase 1) is a mined station with one drive through it to the Ohio bank box."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent
    ids = [f"Line_{k}" for k in range(1, 15)] + ["Line_2b", "CVG_Express"]
    for lid in ids:
        al = root / f"hub/seed/alignments/{lid}.json"
        mp = MetroProfile.load(root / f"data/profile/lines/{lid}.json", al if al.exists() else None, root / "data/profile/settings.json")
        T, step = mp.stretch_types(), None
        step = T["step"]
        for s in mp.stations:
            sec = mp.canon_at(s["c"])
            if mp.override_at(s["c"]) or (sec and sec["m"] in ("canal", "covered")):
                continue   # paints and canon box sections decide there
            g = float(mp.ground_at(s["c"])) - float(mp.rail_at(s["c"]))
            t = T["t"][min(len(T["t"]) - 1, int(round(s["c"] / step)))]
            if t == "cutcover":
                assert g <= mp.phase_rules(s["c"])["cc_max"] + 0.05, (lid, s["name"], g)
        t = T["t"]
        rr, a = [], 0
        for i in range(1, len(t) + 1):
            if i == len(t) or t[i] != t[a]:
                rr.append((a, i - 1, t[a]))
                a = i
        half = mp.settings["platform"] / 2
        in_st = lambda c0, c1: any(s["c"] - half - 2 <= c1 and c0 <= s["c"] + half + 2 for s in mp.stations)
        flagged = lambda c0, c1: any(f["c0"] <= c1 + 2 and c0 <= f["c1"] + 2 for f in T["flags"])
        for k in range(1, len(rr) - 1):
            x, y, ty = rr[k]
            c0, c1 = x * step, y * step
            if ty == "cutcover" and rr[k - 1][2] in ("shield", "deep") and rr[k + 1][2] in ("shield", "deep"):
                assert in_st(c0, c1) or flagged(c0, c1), (lid, "box inside a drive", c0, c1)
    mp = MetroProfile.load(root / "data/profile/lines/Line_3.json", root / "hub/seed/alignments/Line_3.json", root / "data/profile/settings.json")
    T = mp.stretch_types()
    assert mp.type_at(16281) in ("shield", "deep") and all(t in ("shield", "deep") for t in T["t"][int(16160 / 2):int(16480 / 2)])


def test_low_cover_drive_needs_regrade():
    """Too shallow partway and too deep elsewhere (Ben, 31 October): a drive whose low stretch cannot be a shaft between
    whole drives stays bored, and the low stretch is unbuildable (hatched, Regrade); Line 7 at 7+348 to 8+108 (Ben's export)."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent
    mp = MetroProfile.load(root / "data/profile/lines/Line_7.json", None, root / "data/profile/settings.json")   # no saved profile: the solver's
    T = mp.stretch_types()
    cov = [b for b in T["bad"] if b["why"] == "cover"]
    assert any(b["c0"] < 7800 < b["c1"] for b in cov), cov
    assert T["t"][int(7800 / T["step"])] in ("shield", "deep")   # stays bored until it is regraded


def test_system_check_nothing_unbuildable_unmarked():
    """The system check (Ben, 31 October: never draw what cannot be built): on every Metro line, every sample drawn as a tube
    with less than one diameter of cover, or as a box past its phase's cut-and-cover limit (the river bank works and canon
    box sections aside), lies inside an unbuildable range the editor hatches and offers to fix; and Line 3 from Benton to
    Henry Clay is a box up to the station, then a drive with its cover (Ben's export)."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile, _tube_of
    root = Path(__file__).resolve().parent.parent
    for lid in [f"Line_{k}" for k in range(1, 15)] + ["Line_2b", "CVG_Express"]:
        al = root / f"hub/seed/alignments/{lid}.json"
        mp = MetroProfile.load(root / f"data/profile/lines/{lid}.json", al if al.exists() else None, root / "data/profile/settings.json")
        T = mp.stretch_types()
        step = T["step"]
        inside = lambda c: any(b["c0"] - 1 <= c <= b["c1"] + 1 for b in T["bad"])
        for i in range(0, len(T["t"]), 5):
            c = i * step
            if c > mp.length or mp.river_at(c) or mp.in_station(c):
                continue
            t = mp.type_at(c)
            d = float(mp.ground_at(c)) - T["z"][i]
            if t in ("shield", "deep") and T["tube"][i]:
                tb = _tube_of(mp.ms["tubes"][T["tube"][i]])
                if d < tb["top"] + tb["od"] - 0.1:
                    assert inside(c), (lid, c, "tube without cover, unmarked")
    mp = MetroProfile.load(root / "data/profile/lines/Line_3.json", root / "hub/seed/alignments/Line_3.json", root / "data/profile/settings.json")
    T = mp.stretch_types()
    assert not [b for b in T["bad"] if 20000 < b["c0"] < 21100]
    assert T["t"][int(20500 / T["step"])] == "cutcover"


def test_road_checks_and_station_streets():
    """Roads (Ben, 29-31 October): from the context's streets and roads, a level crossing where the line runs at grade
    across a road (the Metro never), a trough under a road without room for the road's bridge, and what each station sits
    under (its street, the roads across its platform, or nothing known)."""
    from pathlib import Path
    from railsim.metro_profile import MetroProfile
    root = Path(__file__).resolve().parent.parent
    mp = MetroProfile.load(root / "data/profile/lines/Line_3.json", root / "hub/seed/alignments/Line_3.json", root / "data/profile/settings.json")
    assert mp.roads() and mp.streets()
    rc = mp.road_checks()
    assert any(x["kind"] == "level crossing" and x["sev"] == "error" and 6000 < x["c"] < 6030 for x in rc), rc   # West Mitchell Avenue
    assert all(x["sev"] in ("error", "warn") for x in rc)
    assert mp.summary()["road_clashes"] == len([x for x in rc if x["sev"] == "error"])
    texts = [mp.station_street(s)["text"] for s in mp.stations]
    assert any(t.startswith("under ") for t in texts) and any(t.startswith("crosses ") for t in texts)
    # the RER at grade: a minor street is a warning, a major road an error
    r1 = MetroProfile.load(root / "data/profile/rer/lines/RER_1.json", None, root / "data/profile/rer/settings.json")
    rc = r1.road_checks()
    assert any(x["kind"] == "level crossing" and x["sev"] == "warn" and x["cls"] == "minor" for x in rc)
    assert any(x["kind"] == "level crossing" and x["sev"] == "error" and x["cls"] == "major" for x in rc)
