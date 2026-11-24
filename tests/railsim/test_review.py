"""Review of I2.1 (railsim lane): each test here failed on the code as the lanes left it.

- Two stops of one name at one place (Line 8 draws Cincinnati State twice at c 1226.5, one stop per station
  record) are one stop on the run, as railsim's ``build_route`` keeps one of a name within 50 m; the run stopped
  twice there, with a second dwell of 20 s in each direction.
- A station row of the run names its own stop's platform and chainage, also when another stop has its name (the
  rows were matched to the stops by name, so the first of two took the second's platform and place).
- Each zone of ``railsim.attribution`` carries ``limit_kmh``, the member the sheet's "where the time goes" reads
  (plan section 1.4); it had only ``kmh``, so the sheet printed no limit.
"""

from __future__ import annotations

from functools import cache
from typing import Any

import numpy as np
import pytest

from tests.railsim import parity as P
from tests.railsim.test_adapter import Files

ROUTE = "Line_6"
STEM = "cin_line_6"


def _parts(stations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "stations": stations,
        "station_defaults": {"psd": False},
        "station_info": {"Middle": {"class": "transfer"}},
        "platform_m": 121.92,
    }


def _st(pid: str, name: str, c: float, removed: bool = False) -> dict[str, Any]:
    return {"platform_id": pid, "name": name, "c_m": c, "removed": removed}


def test_two_stops_of_one_name_at_one_place_are_one_stop():
    from region.ext.railsim.assemble import stops_of

    s_of_c = np.arange(0, 5001, 2.0)
    stations = [
        _st("p0", "West", 50.0),
        _st("p1", "Middle", 1226.5),
        _st("p2", "Middle", 1226.5),
        _st("p3", "Further", 2500.0),
        _st("p4", "Further", 3000.0),  # the same name 500 m on: another stop
        _st("p5", "East", 4950.0),
    ]
    stops, removed, warnings = stops_of(_parts(stations), s_of_c, 2.0)
    assert [s["platform_id"] for s in stops] == ["p0", "p1", "p3", "p4", "p5"]
    assert stops[1]["class"] == "transfer"
    assert removed == []
    assert any("Middle" in w and "one stop" in w for w in warnings), warnings


def test_a_removed_twin_leaves_the_live_one_a_stop():
    from region.ext.railsim.assemble import stops_of

    s_of_c = np.arange(0, 5001, 2.0)
    stations = [
        _st("p0", "West", 50.0),
        _st("p1", "Middle", 1226.5, removed=True),
        _st("p2", "Middle", 1226.5),
        _st("p5", "East", 4950.0),
    ]
    stops, removed, _w = stops_of(_parts(stations), s_of_c, 2.0)
    assert [s["platform_id"] for s in stops] == ["p0", "p2", "p5"]
    assert [r["platform_id"] for r in removed] == ["p1"]


@cache
def _legacy() -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, Any]]:
    from region.ext.railsim.legacy import run_settings

    meta, arrays = P.legacy_route_input(P.legacy_route(STEM), ROUTE, STEM)
    settings = run_settings(Files(), {"id": None, "data": {"key": ROUTE}}, None)
    return meta, arrays, settings


def test_station_rows_name_their_own_stop_when_two_stops_share_a_name():
    import copy

    from region.ext.railsim import adapter

    meta, arrays, settings = _legacy()
    meta = copy.deepcopy(meta)
    for k, st in enumerate(meta["stops"]):
        st["platform_id"] = f"pid{k}"
        st["c_m"] = float(st["s_m"]) + 0.25  # a chainage of its own, not the run's
    meta["stops"][5]["name"] = meta["stops"][12]["name"]  # two stops of one name, far apart
    out, _arrays = adapter.run_route(meta, arrays, settings)
    fwd, rev = out["directions"]
    want = [(st["platform_id"], st["c_m"]) for st in meta["stops"]]
    assert [(r["platform_id"], r["c_m"]) for r in fwd["stations"]] == want
    assert [(r["platform_id"], r["c_m"]) for r in rev["stations"]] == want[::-1]


def test_attribution_zones_carry_their_limit_for_the_sheet(monkeypatch):
    from region.ext.railsim import adapter
    from region.ext.railsim.attribution import attribute

    meta, arrays, settings = _legacy()
    zones = adapter._zones

    def two(route: Any, s_to_c: Any) -> list[dict[str, Any]]:
        out = [z for z in zones(route, s_to_c) if z["reason"] != "line speed"]
        return out[:2]

    monkeypatch.setattr(adapter, "_zones", two)
    att = attribute(meta, arrays, settings)
    for d in att["directions"]:
        assert len(d["zones"]) == 2
        for z in d["zones"]:
            assert z["limit_kmh"] == pytest.approx(z["kmh"])
            assert 0 < z["limit_kmh"] < 120
