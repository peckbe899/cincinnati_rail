"""The gate (I2.1): Line 6 against ``tests/baseline/runtimes.json`` (``cin_line_6``), both directions, running and
trip times and every station's arrival, from the hub's records through the whole job chain (plan section 3).

- G2: the hub's Line 6 records in a scenario whose profile is the baseline's own design (the doc the baseline was
  captured on, ``data/profile/alignments/Line_6.json``). Running and trip times within 1 % in both directions.
  Every station's arrival within 1 % of its direction's trip time once the KMZ's curves are laid on the same
  RouteInput: what the hub's own curves add on top is class ``geometry`` (D3: the drawn path the hub fits differs
  from the KMZ railsim fitted by up to 13 m near Kyles Lane, so a 51 m curve there is 85 m on the hub). Nothing is
  left unexplained.
- G3: Ben's records in main differ from the baseline by his design (D1: his saved profile; D2: Greenlee and Lytle
  Park removed). With his two removed stations restored, the run is explained the same way.

A station's arrival is held to 1 % of the trip time, not 1 % of its own arrival: the first stations of a direction
fail the latter on the station centres alone (D4), and even on railsim's own geometry (3.7 s is 2.4 % of
Brightleaf's 131.8 s)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from region.core.view import View
from tests.importers.helpers import MAIN, fresh_copy, profile_of
from tests.railsim import parity as P
from tests.railsim.conftest import Chain, baseline_profile, put_profile, route_of

TOL = P.TOL
STEM = "cin_line_6"
HUB_STATION_BOUND = 0.02
"""The worst station on the hub's own curves, as a share of the trip time: measured 1.35 % (42.2 s at Fort Mitchell,
forward). Pinned so a change that moves it shows; the excess over 1 % is D3 (``test_g2_..._kmz_curves``)."""


@pytest.fixture(scope="module")
def runs(pool, tmp_path_factory):
    """Line 6 run three ways from one copy of the records: main as Ben has it; scenario ``baseline`` with the
    baseline's design; scenario ``restored`` with Ben's design and his two removed stations put back. Each with its
    RouteInput and the run's settings, for the decomposition."""
    from region.core import fsio
    from region.ext.profiles.inputs import StoreReads
    from region.ext.railsim.legacy import run_settings

    root = tmp_path_factory.mktemp("parity")
    with fsio.allow_writes(root):
        store = fresh_copy(root)
        try:
            store.create_layer("baseline", tier="scenario", parent="main", by="ben")
            store.create_layer("restored", tier="scenario", parent="main", by="ben")
            put_profile(store, "Line_6", baseline_profile(store, "Line_6"), View(layer="baseline"))
            data = json.loads(json.dumps(profile_of(store, "Line_6")["data"]))
            data["del"] = []
            put_profile(store, "Line_6", data, View(layer="restored"))
            route = route_of(store, "Line_6")
            rid = route["id"]
            ch = Chain(store, pool)
            out: dict[str, Any] = {}
            for name, view in (
                ("main", MAIN),
                ("baseline", View(layer="baseline")),
                ("restored", View(layer="restored")),
            ):
                _p, res = ch.compute("railsim.run", rid, view)
                _q, ri = ch.compute("route.assemble", rid, view)
                out[name] = {
                    "run": res.meta,
                    "ri_meta": ri.meta,
                    "ri_arrays": ri.arrays,
                    "settings": run_settings(StoreReads(store, view), route, None),
                }
            yield out
        finally:
            store.close()


def _decompose(runs: dict[str, Any], name: str) -> dict[str, Any]:
    r = runs[name]
    return P.decompose(P.runtimes(STEM), r["ri_meta"], r["ri_arrays"], r["settings"], P.legacy_route(STEM))


def test_g2_running_and_trip_times_within_1_percent(runs):
    """On the baseline's design, from the records, through the whole chain: running and trip time within 1 % of the
    baseline in both directions, with the same 33 stops (measured: running -0.75 % and -0.95 %, trip -0.55 % and
    -0.67 %)."""
    cmp = P.compare(P.runtimes(STEM), runs["baseline"]["run"])
    for d in cmp["directions"]:
        assert abs(d["running"]) <= TOL, d
        assert abs(d["trip"]) <= TOL, d
        assert not d["missing"] and not d["extra"], d
    assert P.times_within(cmp)


def test_g2_every_station_within_1_percent_of_the_trip_once_the_kmz_curves_are_laid_on(runs):
    """The same RouteInput with the KMZ fit's curves: every station's arrival within 1 % of the trip time (measured
    worst 9.1 s against 31.2 s). On the hub's own curves the worst is pinned under ``HUB_STATION_BOUND``; each station
    over 1 % there is class geometry (D3), since the curves alone bring it inside. Nothing is unexplained."""
    dec = _decompose(runs, "baseline")
    kmz = dec["steps"]["kmz_curves"]["cmp"]
    assert P.within(kmz), [(d["dir"], d["worst_s"], d["worst_at"]) for d in kmz["directions"]]
    hub = dec["steps"]["hub"]["cmp"]
    for d in hub["directions"]:
        assert d["worst_s"] <= HUB_STATION_BOUND * d["trip_s"], (d["dir"], d["worst_s"], d["worst_at"])
    assert not dec["unexplained"]
    if not P.within(hub):
        assert dec["classes"] == ["geometry: curves (D3)"]


def test_g2_station_centres_are_the_kmz_placemarks_but_for_the_d4_stations(runs):
    """D4: the hub's stop centres (the Deck stop plus the profile's slide) against the KMZ placemarks railsim
    projected: within 10 m but at the stations whose placemark and Deck stop are drawn apart (measured: up to 94 m,
    at Bond Hill)."""
    off = P.station_offsets(runs["baseline"]["ri_meta"], P.legacy_route(STEM))
    far = {k for k, v in off.items() if abs(v) > 10.0}
    assert far <= {
        "Towne",
        "Bond Hill",
        "North Avondale",
        "Forest",
        "Oak",
        "Times",
        "Public Landing",
        "Eastside",
        "Bullock",
    }, off


def test_g3_bens_records_differ_by_his_design_only(runs):
    """Main is outside 1 % (his two removed stations, D2), and it is his design that makes it so: with them
    restored the run is within 1 % on running and trip time, and every station is explained as in G2."""
    base = P.runtimes(STEM)
    assert sorted(r["name"] for r in runs["main"]["ri_meta"]["removed"]) == ["Greenlee", "Lytle Park"]
    main = P.compare(base, runs["main"]["run"])
    assert sorted(main["directions"][0]["missing"]) == ["Greenlee", "Lytle Park"]
    assert any(d["trip"] < -TOL for d in main["directions"])  # 31 stops make the trip shorter (D2)
    restored = _decompose(runs, "restored")
    assert P.times_within(restored["steps"]["hub"]["cmp"]), restored["steps"]["hub"]["cmp"]
    assert not restored["unexplained"], restored["steps"]["kmz_curves_stations"]["cmp"]


def test_the_run_names_its_sources(runs):
    m = runs["main"]["run"]
    assert m["sources"]["era"] == "data/operations/cincinnati_metro.yaml"
    assert m["sources"]["train"] == "data/rollingstock/metro.yaml"
    assert m["sources"]["classes"] == "configs/metro/cin_line_6.yaml"
    assert m["sources"]["curves"] == "fitted to the section path"


# ------------------------------------------------------------------------------------------- the 16 Metro lines


@pytest.fixture(scope="module")
def lines(pool, tmp_path_factory):
    """One copy of the records and one chain for the 16 Metro lines, each on the design its baseline ran on: the
    doc in ``data/profile/alignments`` where the config names one, else the solver's default (the profile's levels,
    bend points, paints, slides and removals cleared, so the hub draws its default design)."""
    from region.core import fsio

    root = tmp_path_factory.mktemp("lines")
    with fsio.allow_writes(root):
        store = fresh_copy(root)
        try:
            yield store, Chain(store, pool)
        finally:
            store.close()


@pytest.mark.slow
@pytest.mark.parametrize("stem", P.STEMS)
def test_every_metro_line_is_explained(lines, stem):
    """Each line on its baseline's design, from the records: within 1 % as it is, or brought within 1 % by the KMZ's
    curves (D3), or by the KMZ route's whole frame (its curves and station places, D3 and D4) with the hub's rail and
    types; nothing unexplained. Measured: Lines 7 and 11 and CVG Express same, 12 lines by the curves, Line 2b by
    the frame."""
    from region.ext.profiles.inputs import StoreReads
    from region.ext.railsim.legacy import run_settings
    from tests.importers.helpers import all_records, section_of
    from tests.railsim.conftest import BASELINE_ALIGN

    store, ch = lines
    key = P.route_key_of(stem)
    sid = section_of(store, key)["id"]
    view = View(layer=f"b_{stem}")
    store.create_layer(view.layer, tier="scenario", parent="main", by="ben")
    if (BASELINE_ALIGN / f"{key}.json").exists():
        put_profile(store, key, baseline_profile(store, key), view)
    else:
        data = json.loads(json.dumps(all_records(store, "profile", MAIN, parent=sid)[0]["data"]))
        data.update({"st": {}, "sg": {}, "so": {}, "pvi": [], "ovr": [], "del": []})
        put_profile(store, key, data, view)
    route = route_of(store, key)
    _q, ri = ch.compute("route.assemble", route["id"], view)
    settings = run_settings(StoreReads(store, view), route, None)
    dec = P.decompose(P.runtimes(stem), ri.meta, ri.arrays, settings, P.legacy_route(stem))
    assert not dec["unexplained"], (stem, {k: v["cmp"] for k, v in dec["steps"].items()})
