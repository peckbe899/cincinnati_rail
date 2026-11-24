"""G1, adapter identity (plan section 3): railsim's own Line 6 route, built here the legacy way (the KMZ is read in
this test as the reference, never by the hub), turned into a RouteInput and run through ``adapter.run_route``,
gives the baseline's numbers: every summary number and every station's arrival as ``tests/baseline/runtimes.json``
has them. This proves the RouteInput to TrackData path, the stops, the dwell, the padding and the summary."""

from __future__ import annotations

from functools import cache
from typing import Any

import numpy as np
import pytest

from region.core.view import View
from tests.railsim.conftest import REPO, runtimes

ROUTE = "Line_6"
STEM = "cin_line_6"


class Files:
    """A plan context for the settings alone: files from the repo, no params registered."""

    view = View()

    def file(self, uri: str) -> Any:
        from region.core import paths

        return paths.resolve(uri)

    def param(self, path: str, scope: str | None = None) -> Any:
        from region.core.errors import NotFound

        raise NotFound(path)


@cache
def legacy_route() -> Any:
    """railsim's ``build_route`` on the line config, as ``python -m railsim.metro`` builds it (no files written)."""
    import yaml
    from railsim import app, metro
    from railsim.line import build_route
    from railsim.operations import load_era

    user = yaml.safe_load((REPO / "configs" / "metro" / f"{STEM}.yaml").read_text())
    era, key, _year = load_era(REPO / user["operations"], None)
    cfg = app.deep_merge(app.deep_merge(metro.DEFAULTS, era.get("overlay", {})), user)
    train = app.load_library(metro.SPEC.library)[key].with_load(0.5, "dry")
    return build_route(
        cfg,
        REPO,
        app.curve_design_from(cfg, train),
        app.speed_policy_from(cfg, train),
        app.profile_design_from(cfg),
        log=lambda *a: None,
    )


def legacy_route_input(route: Any) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """A RouteInput (``route_input/0``) of railsim's own route: its fit, its rail and structures sampled on the run
    grid as ``Route.track_data`` samples them, its stations as they stop."""
    from railsim.metro_profile import STRUCTURE, TUNNEL_STRUCTURES, TYPES

    L = route.length
    s = np.arange(0.0, L + 2.0, 2.0)
    s[-1] = L
    rail = route.profile.elevation_at(s)
    names = np.array(route.profile.structure)
    idx = np.clip(np.searchsorted(route.profile.s, s), 0, len(names) - 1)
    at = names[idx]
    inverse = {v: i for i, v in enumerate(STRUCTURE[t] for t in TYPES)}
    tunnel = np.isin(at, list(TUNNEL_STRUCTURES))
    kind = np.array([inverse.get(n, TYPES.index("cutcover") if t else TYPES.index("atgrade")) for n, t in zip(at, tunnel)])
    curves = [
        {
            "s_ts": c.s_ts,
            "s_sc": c.s_sc,
            "s_cs": c.s_cs,
            "s_st": c.s_st,
            "c_ts": c.s_ts,
            "c_st": c.s_st,
            "radius_m": c.radius,
            "spiral_m": c.spiral,
            "cant_m": c.cant,
            "deflection_rad": c.deflection,
            "direction": int(c.direction),
            "tangent_m": c.tangent,
        }
        for c in route.horizontal.curves
    ]
    stops = [
        {
            "platform_id": st.name,
            "name": st.name,
            "c_m": st.s,
            "s_m": st.s,
            "platform_m": st.platform_length,
            "class": st.cls,
            "class_source": "legacy",
            "psd": st.psd,
            "dwell_s": st.dwell_override,
            "terminal": k in (0, len(route.stations) - 1),
            "reverse": st.reverse,
        }
        for k, st in enumerate(route.stations)
        if st.stop
    ]
    meta = {
        "contract": "route_input/0",
        "route_id": None,
        "route_key": ROUTE,
        "name": route.name,
        "config": STEM,
        "section": {"section_id": None, "length_m": L, "step_m": 2.0},
        "run_grid": {"c0": 0.0, "step_m": 2.0, "n": len(s)},
        "length_m": L,
        "proj": {"lat0": route.proj.lat0, "lon0": route.proj.lon0},
        "curves": curves,
        "stops": stops,
        "removed": [],
        "restrictions": [],
        "warnings": [],
        "sources": {"curves": "legacy KMZ fit"},
    }
    arrays = {
        "s_m": s,
        "c_m": s.copy(),
        "rail_z_m": rail,
        "curvature_per_m": np.abs(route.horizontal.curvature(s)),
        "tunnel": tunnel.astype("u1"),
        "type": kind.astype("u1"),
    }
    return meta, arrays


@cache
def legacy_run() -> dict[str, Any]:
    from region.ext.railsim import adapter
    from region.ext.railsim.legacy import run_settings

    route = {"id": None, "data": {"key": ROUTE}}
    settings = run_settings(Files(), route, None)
    meta, arrays = legacy_route_input(legacy_route())
    out_meta, out_arrays = adapter.run_route(meta, arrays, settings)
    return {"meta": out_meta, "arrays": out_arrays}


def test_g1_summary_numbers_are_the_baselines():
    """Every summary number of both directions equals the baseline's (railsim rounds minutes to 0.01)."""
    base = runtimes(STEM)
    got = legacy_run()["meta"]
    assert got["contract"] == "run_result/0"
    for b, d in zip(base["directions"], got["directions"], strict=True):
        assert d["label"] == b["direction"].replace(" -> ", " to ")
        assert round(d["running_s"] / 60, 2) == b["running_time_min"]
        assert round(d["trip_s"] / 60, 2) == b["trip_time_min"]
        assert round(d["dwell_s"] / 60, 2) == b["dwell_total_min"]
        assert round(d["scheduled_s"] / 60, 2) == b["scheduled_time_min"]
        assert round(d["distance_m"] / 1000, 3) == b["distance_km"]


def test_g1_every_station_arrival_is_the_baselines():
    base = runtimes(STEM)
    got = legacy_run()["meta"]
    for b, d in zip(base["directions"], got["directions"], strict=True):
        assert [s["name"] for s in d["stations"]] == [s["name"] for s in b["stations"]]
        for bs, ds in zip(b["stations"], d["stations"], strict=True):
            assert abs(ds["arrive_s"] - bs["arrive_s"]) <= 0.05 + 1e-9, (d["label"], bs["name"])
            assert abs(ds["scheduled_arrive_s"] - bs["scheduled_arrive_s"]) <= 0.05 + 1e-9, (d["label"], bs["name"])
            assert round(ds["km"], 3) == bs["km"]


def test_g1_the_run_reports_era_train_and_legs():
    got = legacy_run()["meta"]
    assert got["year"] == 2026 and got["year_source"] == "default_year"
    assert got["era"]["goa"] == 3 and got["era"]["signalling"] == "cbtc"
    assert got["train"]["key"] == "CMCC_TYPE2005_10CAR" and got["train"]["cars"] == 10
    assert got["train"]["length_m"] == pytest.approx(146.0, abs=0.5)
    fwd = got["directions"][0]
    assert fwd["stations"][0]["leg"] is None
    for st in fwd["stations"][1:]:
        leg = st["leg"]
        parts = leg["accel_s"] + leg["cruise_s"] + leg["coast_s"] + leg["brake_s"]
        assert parts == pytest.approx(leg["run_s"], abs=0.5), st["name"]
        assert 0 < leg["vmax_kmh"] <= got["train"]["max_kmh"] + 0.1
    assert sum(s["leg"]["run_s"] for s in fwd["stations"][1:]) == pytest.approx(fwd["running_s"], abs=1e-6)
    assert got["round_trip_s"] == pytest.approx(sum(d["scheduled_s"] for d in got["directions"]) + sum(got["turnback_s"]))


def test_g1_arrays_on_the_section_grid():
    """The run's arrays are on the section grid of ``meta.grid`` (10 m), so a result event's ``changed`` ranges are
    in Ben's chainage; the speed where the train never is reads NaN, and the trace is every simulator step."""
    got = legacy_run()
    meta, arrays = got["meta"], got["arrays"]
    n = meta["grid"]["n"]
    assert meta["grid"]["step_m"] == 10.0
    for name in ("limit_ms", "v_fwd_ms", "v_rev_ms", "t_fwd_s", "t_rev_s"):
        assert arrays[name].shape == (n,), name
        assert arrays[name].dtype == np.float64
    v = arrays["v_fwd_ms"]
    assert np.isnan(v[0]) or v[0] >= 0
    assert np.nanmax(v) == pytest.approx(meta["directions"][0]["max_kmh"] / 3.6, rel=0.02)
    assert arrays["trace_fwd"].ndim == 2 and arrays["trace_fwd"].shape[1] == 4
    t = arrays["t_fwd_s"]
    ok = ~np.isnan(t)
    assert np.all(np.diff(t[ok]) >= 0)  # the front passes each sample later going forward
    tr = arrays["t_rev_s"]
    ok = ~np.isnan(tr)
    assert np.all(np.diff(tr[ok]) <= 0)  # and earlier going back
    assert np.all(arrays["limit_ms"] > 0)


def test_the_adapter_is_deterministic_and_writes_nothing(tmp_path, monkeypatch):
    """The same RouteInput twice gives the same numbers, and the adapter never calls ``build_route``, the ground
    sources, the KMZ reader or the report writers."""
    import railsim.app as A
    import railsim.elevation as E
    import railsim.kml as K
    import railsim.line as L
    import railsim.report as R

    from region.ext.railsim import adapter
    from region.ext.railsim.legacy import run_settings

    meta, arrays = legacy_route_input(legacy_route())

    def refuse(*a: Any, **k: Any) -> Any:
        raise AssertionError("the adapter reached a legacy side effect")

    for mod, names in (
        (L, ("build_route",)),
        (A, ("main", "build_route")),
        (K, ("read_kmz",)),
        (E, ("from_dem", "from_lidar", "from_terrain_tiles", "from_usgs", "from_csv")),
        (R, ("write_csv", "write_kml", "plot_run")),
    ):
        for n in names:
            if hasattr(mod, n):
                monkeypatch.setattr(mod, n, refuse)
    settings = run_settings(Files(), {"id": None, "data": {"key": ROUTE}}, None)
    a = adapter.run_route(meta, arrays, settings)[0]
    b = adapter.run_route(meta, arrays, settings)[0]
    from region.core import fsio

    assert fsio.canonical_json(a) == fsio.canonical_json(b)
