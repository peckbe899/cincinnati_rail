"""METRO program: heavy/light rapid transit.

Differences from the commuter program:
  * dwell = full door cycle (unlock/open, passenger flow per door channel, chime + close,
    re-open allowance, dispatch) driven by station class,
  * ATO-like driving: runs close to the limit, brakes at the service rate with comfort jerk,
  * steeper permitted grades (Cincinnati canon: motors sized for 50 per mille),
  * short station spacing, so acceleration, jerk and door times dominate.

Usage:
    python -m railsim.metro configs/metro/mbta_orange.yaml
    python -m railsim.metro configs/metro/cincinnati_line6.yaml --train CMCC_TYPE2005_48FT_10CAR
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from .app import ProgramSpec, main as app_main
from .dwell import MetroDwell, StationClassLoad
from .dynamics import Driver
from .geo import KMH, MPH
from .line import speed_of

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "load_factor": 0.5,
    "geometry": {
        "line_speed_mph": 55,
        "max_cant_in": 6.0,  # 150 mm (TCRP 155 / transit criteria)
        "design_cant_deficiency_in": 3.0,  # 75 mm design (TCRP 57)
        "min_spiral_m": 20.0,
        "min_reverse_tangent_m": 30.0,
        "min_radius_m": 25.0,
        "group_dev_tol_m": 10.0,
        "corner_offset_tol_m": 30.0,
    },
    "speed": {
        "cant_deficiency_in": 3.0,  # running Eu; transit allows 3-4.5 in
        "increment_mph": 5,
        "min_zone_m": 150.0,
        "max_deficiency_rate_mm_s": 55.0,
    },
    "profile": {
        "max_grade": 0.04,
        "platform_grade": 0.005,
        "vertical_curve_m": 80.0,
        "below_ground_weight": 4.0,
        "allow_tunnels": False,
        "viaduct_height_m": 6.0,
        "sources": ["csv", "kmz", "usgs", "terrain"],
    },
    "driver": {
        "mode": "ato",  # ato | manual
        "power_fraction": 1.0,
    },
    "dwell": {},
    "padding": {"percent": 3.0, "final_leg_s": 0.0},
}


def make_driver(cfg: dict, train) -> Driver:
    d = cfg.get("driver", {})
    manual = d.get("mode", "ato") == "manual"
    # operators run ~1 mph under the code; ATO ~2 mph under (signalling presets such as
    # cbtc set their own margin unless the config gives one)
    margin = (speed_of(d, "speed_margin", 1.0 * MPH) if manual
              else speed_of(d, "ato_margin", 2.0 * MPH))
    brake = d.get("brake_rate")  # m/s^2; default: the train's service rate
    if brake is None and manual:
        brake = 0.85 * train.service_brake  # operators brake more gently than ATO
    # manual operators creep the last metres into the platform (stopping-mark accuracy)
    creep = speed_of(d, "stop_approach", (4.0 if manual else 0.0) * MPH)
    creep_dist = float(d.get("stop_approach_m", 15.0 if manual else 0.0))
    return Driver(brake_rate=brake, speed_margin=margin,
                  power_fraction=float(d.get("power_fraction", 1.0)), dt=float(d.get("dt", 0.2)),
                  stop_approach_speed=creep, stop_approach_dist=creep_dist)


def _metro_dwell_model(cfg: dict) -> MetroDwell:
    dcfg = dict(cfg.get("dwell", {}) or {})
    classes = dcfg.pop("classes", None)
    model = MetroDwell(**{k: v for k, v in dcfg.items() if k in {f.name for f in fields(MetroDwell)}
                          and k != "classes"})
    if classes:
        for name, c in classes.items():
            model.classes[name] = StationClassLoad(float(c["board"]), float(c["alight"]))
    return model


def dwell_fn(station, train, cfg, is_terminal: bool) -> float:
    model = _metro_dwell_model(cfg)
    # door timing from the rolling stock unless the line config overrides it
    dcfg = cfg.get("dwell", {}) or {}
    if "door_open" not in dcfg:
        model.door_open = train.door_open
    if "door_close" not in dcfg:
        model.door_close = train.door_close
    doors = max(train.doors_per_side * train.cars, 1)
    scale = float(dcfg.get("load_scale", 1.0))
    # station volumes are per train for a reference-size train; demand per train scales
    # with the train's capacity (a 260-seat interurban picks up fewer people per stop)
    cap = train.mass_load / 75.0 if train.mass_load > 0 else 640.0
    scale *= cap / float(dcfg.get("reference_capacity", 640))
    return model.dwell(station.cls, doors, train.door_channels, scale, station.dwell_override,
                       psd=has_psd(station, dcfg))


def has_psd(station, dcfg: dict) -> bool:
    """Platform screen doors at this station: per-station `stations.info.<name>.psd`, else
    `dwell.psd_stations` (names) or `dwell.psd_classes` (station classes); with neither
    list, every station has them whenever `psd_overhead` is set."""
    if station.psd is not None:
        return station.psd
    names = dcfg.get("psd_stations")
    classes = dcfg.get("psd_classes")
    if names is None and classes is None:
        return True
    return station.name in (names or []) or station.cls in (classes or [])


SPEC = ProgramSpec("metro", ROOT / "data" / "rollingstock" / "metro.yaml", DEFAULTS, make_driver,
                   dwell_fn)


def main(argv=None):
    return app_main(SPEC, argv)


if __name__ == "__main__":
    main()
