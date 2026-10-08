"""TRAIN program (commuter / RER / intercity / HSR): everything that is not metro.

Also runnable as `python -m railsim.train`. Set `preset: intercity` or `preset: hsr` in a
line config for those service classes (cant rules, ETCS, allowances, dwell).

Differences from the metro program:
  * dwell depends on platform type (level boarding vs steps at low platforms, where crews
    open only some doors), conductor procedures and air-brake release, and much less on
    a door cycle,
  * engineer-style driving: a margin under the posted limit, gentler braking for
    locomotive-hauled stock, brake build-up delay, and a slow final approach to platforms,
  * FRA-style geometry (3 in cant deficiency, 2% grades), longer station spacing,
  * branching RER networks: service.route picks the branch through the trunk.

Usage:
    python -m railsim.commuter configs/commuter/mbta_needham.yaml
    python -m railsim.commuter configs/commuter/cincinnati_rer1.yaml --train RER_F_SET_FLIRT
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from .app import ProgramSpec, main as app_main
from .dwell import CommuterDwell, StationClassLoad
from .dynamics import Driver
from .geo import MPH
from .line import speed_of

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "load_factor": 0.5,
    "geometry": {
        "line_speed_mph": 79,  # FRA: 79 mph without cab signals / ATC
        "max_cant_in": 5.0,
        "design_cant_deficiency_in": 3.0,
        "min_spiral_m": 30.0,
        "min_reverse_tangent_m": 30.0,
        "min_radius_m": 50.0,
        "group_dev_tol_m": 12.0,
        "corner_offset_tol_m": 50.0,
    },
    "speed": {
        "cant_deficiency_in": 3.0,  # 49 CFR 213.57 default for all equipment
        "increment_mph": 5,
        "min_zone_m": 300.0,
        "max_deficiency_rate_mm_s": 55.0,
    },
    "profile": {
        "max_grade": 0.02,
        "platform_grade": 0.005,
        "vertical_curve_m": 150.0,
        "below_ground_weight": 4.0,
        "allow_tunnels": False,
        "viaduct_height_m": 6.0,
        "sources": ["csv", "kmz", "usgs", "terrain"],
    },
    "driver": {
        "power_fraction": 1.0,
        "stop_approach_mph": 0.0,
        "stop_approach_m": 0.0,
    },
    "dwell": {},
    "padding": {"percent": 5.0, "final_leg_s": 0.0},
}


# Service-class presets (config key `preset`). Values: EN 13803 / FRA Part 213 cant rules,
# UIC 451-1 allowances, HSR braking and signalling practice (docs/research/*.md).
PRESETS = {
    "commuter": {},
    "intercity": {  # US higher-speed intercity (110 mph class, qualified equipment, cab signals)
        "geometry": {"line_speed_mph": 110, "max_cant_in": 6.0, "design_cant_deficiency_in": 4.0,
                     "min_spiral_m": 60.0, "min_radius_m": 150.0, "corner_offset_tol_m": 80.0},
        "speed": {"cant_deficiency_in": 5.0, "min_zone_m": 600.0},
        "profile": {"max_grade": 0.02, "vertical_curve_m": 300.0},
        "signalling": {"system": "cab"},
        "driver": {"speed_margin_mph": 2.0},
        "dwell": {"classes": {"minor": {"board": 15, "alight": 15},
                              "standard": {"board": 40, "alight": 40},
                              "busy": {"board": 100, "alight": 100},
                              "hub": {"board": 200, "alight": 200},
                              "terminal": {"board": 250, "alight": 250}},
                  "min_dwell": 60},
        "padding": {"percent": 7.0, "min_per_100km": 1.5, "final_leg_s": 120},
        "turnback_min": 20,
    },
    "hsr": {  # 300 km/h ballasted/slab HSR, ETCS L2
        "geometry": {"line_speed_kmh": 300, "max_cant_mm": 180, "design_cant_deficiency_mm": 80,
                     "min_spiral_m": 150.0, "min_reverse_tangent_m": 100.0, "min_radius_m": 500.0,
                     "group_dev_tol_m": 20.0, "corner_offset_tol_m": 150.0, "simplify_tol_m": 5.0},
        "speed": {"cant_deficiency_mm": 100, "increment_kmh": 10, "min_zone_m": 1500.0},
        "profile": {"max_grade": 0.035, "platform_grade": 0.0025, "vertical_curve_m": 800.0},
        "signalling": {"system": "etcs2"},
        "driver": {"speed_margin_kmh": 3.0},
        "dwell": {"classes": {"minor": {"board": 30, "alight": 30},
                              "standard": {"board": 80, "alight": 80},
                              "busy": {"board": 150, "alight": 150},
                              "hub": {"board": 250, "alight": 250},
                              "terminal": {"board": 300, "alight": 300}},
                  "min_dwell": 90},
        "padding": {"percent": 7.0, "min_per_100km": 1.0, "final_leg_s": 120},
        "turnback_min": 20,
    },
}


def make_driver(cfg: dict, train) -> Driver:
    d = cfg.get("driver", {})
    ato = d.get("mode", "manual") == "ato"  # e.g. on a CBTC trunk (RER NExTEO, Elizabeth line core)
    return Driver(
        brake_rate=d.get("brake_rate"),  # m/s^2; default: the train's service (timetable) rate
        speed_margin=(speed_of(d, "speed_margin", 2.0 * MPH) if not ato
                      else speed_of(d, "ato_margin", 1.0 * MPH)),
        power_fraction=float(d.get("power_fraction", 1.0)),
        dt=float(d.get("dt", 0.2)),
        stop_approach_speed=0.0 if ato else speed_of(d, "stop_approach", 0.0),
        stop_approach_dist=float(d.get("stop_approach_m", 0.0)),
    )


def _model(cfg: dict) -> CommuterDwell:
    dcfg = dict(cfg.get("dwell", {}) or {})
    classes = dcfg.pop("classes", None)
    names = {f.name for f in fields(CommuterDwell)}
    model = CommuterDwell(**{k: v for k, v in dcfg.items() if k in names and k != "classes"})
    if classes:
        for name, c in classes.items():
            model.classes[name] = StationClassLoad(float(c["board"]), float(c["alight"]))
    return model


def dwell_fn(station, train, cfg, is_terminal: bool) -> float:
    model = _model(cfg)
    dcfg = cfg.get("dwell", {}) or {}
    by_class = dcfg.get("by_class_s") or {}
    if station.dwell_override is None and station.cls in by_class:
        return float(by_class[station.cls])  # operator-set dwell by station class
    if "door_open" not in dcfg:
        model.door_open = train.door_open
    if "door_close" not in dcfg:
        model.door_close = train.door_close
    if "brake_release" not in dcfg and train.category in ("emu", "dmu"):
        model.brake_release = 2.0  # electro-pneumatic / blended brakes release quickly
    doors = max(train.doors_per_side * train.cars, 1)
    scale = float(dcfg.get("load_scale", 1.0))
    # station volumes are per train for a reference-size train; demand per train scales
    # with the train's capacity (a 260-seat interurban picks up fewer people per stop)
    cap = train.mass_load / 75.0 if train.mass_load > 0 else 1000.0
    scale *= cap / float(dcfg.get("reference_capacity", 1000))
    return model.dwell(station.cls, station.platform, doors, train.door_channels, scale,
                       station.dwell_override)


SPEC = ProgramSpec("commuter", ROOT / "data" / "rollingstock" / "commuter.yaml", DEFAULTS,
                   make_driver, dwell_fn, PRESETS)


def main(argv=None):
    return app_main(SPEC, argv)


if __name__ == "__main__":
    main()
