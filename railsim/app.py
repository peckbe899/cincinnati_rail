"""Shared runner for the metro and commuter programs.

A program supplies: its rolling-stock library, design defaults (curves, profile, speed
policy), a driver model and a dwell function. This module builds the route, runs both
directions, applies timetable padding and writes the reports.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np
import yaml

from dataclasses import replace

from .dynamics import Driver, RunResult, Simulator, Stop
from .operations import apply_driver_config, eco_driver, load_era, monte_carlo
from .geo import INCH, KMH, MPH
from .horizontal import CurveDesign
from .line import Route, StationInfo, build_route, length_of, speed_of
from .profile import ProfileDesign
from .rollingstock import Train, load_library
from .speed import SpeedPolicy


@dataclass
class ProgramSpec:
    name: str  # "metro" | "commuter"
    library: Path
    defaults: dict  # nested defaults merged under each line config
    make_driver: Callable[[dict, Train], Driver]
    dwell_fn: Callable[[StationInfo, Train, dict, bool], float]  # (station, train, cfg, is_terminal)
    presets: Dict[str, dict] = field(default_factory=dict)  # named default overlays (config: preset)


_UNIT_SUFFIXES = ("_mph", "_kmh", "_ms", "_in", "_mm", "_ft", "_m")


def _unit_base(k: str):
    for suf in _UNIT_SUFFIXES:
        if k.endswith(suf):
            return k[: -len(suf)]
    return None


def deep_merge(base: dict, over: dict) -> dict:
    """Recursive merge. Unit-suffixed keys are one setting: an overlay giving
    line_speed_kmh replaces a base line_speed_mph (and vice versa)."""
    out = dict(base)
    for k in (over or {}):
        b = _unit_base(k)
        if b is not None:
            for suf in _UNIT_SUFFIXES:
                other = b + suf
                if other != k and other in out and not isinstance(out[other], dict):
                    del out[other]
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def curve_design_from(cfg: dict, train: Train) -> CurveDesign:
    g = cfg["geometry"]
    return CurveDesign(
        line_speed=speed_of(g, "line_speed"),
        max_cant=length_of(g, "max_cant"),
        max_cant_deficiency=length_of(g, "design_cant_deficiency"),
        min_spiral=float(g.get("min_spiral_m", 20.0)),
        min_reverse_tangent=float(g.get("min_reverse_tangent_m", 30.0)),
        min_radius=float(g.get("min_radius_m", 25.0)),
        group_dev_tol=float(g.get("group_dev_tol_m", 10.0)),
        corner_offset_tol=float(g.get("corner_offset_tol_m", 40.0)),
        simplify_tol=float(g.get("simplify_tol_m", 3.0)),
    )


def speed_policy_from(cfg: dict, train: Train) -> SpeedPolicy:
    sp = cfg["speed"]
    # the railroad's permitted cant deficiency; stock qualified for more (tilting trains)
    # only uses it where the line config allows it
    eu = length_of(sp, "cant_deficiency")
    if train.cant_deficiency is not None and sp.get("use_train_cant_deficiency", False):
        eu = train.cant_deficiency
    inc = speed_of(sp, "increment", 5 * MPH)
    steps = tuple(float(x) * MPH for x in sp.get("code_steps_mph", []) or [])
    steps += tuple(float(x) * KMH for x in sp.get("code_steps_kmh", []) or [])
    tilt = sp.get("allow_tilt", True)
    return SpeedPolicy(
        tilt_cant_deficiency=train.tilt_cant_deficiency if tilt else 0.0,
        tilt_max_speed=train.tilt_max_speed if tilt else 0.0,
        steps=tuple(sorted(steps)),
        line_speed=min(speed_of(cfg["geometry"], "line_speed"), train.max_speed),
        cant_deficiency=eu,
        increment=inc,
        min_zone_length=float(sp.get("min_zone_m", 200.0)),
        max_deficiency_rate=float(sp.get("max_deficiency_rate_mm_s", 55.0)) / 1000.0,
    )


def profile_design_from(cfg: dict) -> ProfileDesign:
    p = cfg["profile"]
    return ProfileDesign(
        max_grade=float(p.get("max_grade", 0.03)),
        platform_grade=float(p.get("platform_grade", 0.005)),
        vertical_curve_length=float(p.get("vertical_curve_m", 120.0)),
        below_ground_weight=float(p.get("below_ground_weight", 4.0)),
        allow_tunnels=bool(p.get("allow_tunnels", False)),
        viaduct_height=float(p.get("viaduct_height_m", 6.0)),
    )


# ----------------------------------------------------------------------------- running

@dataclass
class DirectionResult:
    label: str
    stations: List[StationInfo]  # in travel order (chainage in this direction)
    stop_s: List[float]
    dwell: List[float]
    run: RunResult
    reverse: bool = False
    padded_arrivals: List[float] = field(default_factory=list)
    padded_departures: List[float] = field(default_factory=list)


def _stops_for(route: Route, train: Train, reverse: bool, dwell_of, stop_position: str = "far_end",
               dwell_mult: float = 1.0, reversal_min_s: float = 240.0) -> tuple:
    L = route.length
    seq = [s for s in route.stations if s.stop]
    if reverse:
        seq = seq[::-1]
    stop_s, dwell, jumps = [], [], []
    for k, st in enumerate(seq):
        c = (L - st.s) if reverse else st.s
        terminal = k == 0 or k == len(seq) - 1
        if st.reverse and not terminal:
            # stub terminal: the head stops 3 m short of the buffer; after the driver changes
            # ends the old rear leads, so the front moves a train length on the unfolded route
            stop_s.append(c - 3.0)
            jumps.append(train.length + 6.0)
            dwell.append(max(dwell_of(st) * dwell_mult, reversal_min_s))
            continue
        jumps.append(0.0)
        if stop_position == "far_end":
            # head stops at the stop marker near the far end of the platform (5 m short),
            # so a short train on a long platform runs further in than its centre point
            half = max(st.platform_length, train.length) / 2
            front = c + half - (5.0 if st.platform_length > train.length + 10 else 0.0)
        else:
            front = c + train.length / 2  # train centred on the platform placemark
        front = min(front, L - 3.0)  # never past the end of track
        stop_s.append(front)
        dwell.append(0.0 if terminal else dwell_of(st) * dwell_mult)
    return seq, stop_s, dwell, jumps


def run_direction(route: Route, train: Train, driver: Driver, dwell_of, reverse: bool,
                  ds: float = 2.0, stop_position: str = "far_end",
                  dwell_mult: float = 1.0, zone_drivers=None,
                  reversal_min_s: float = 240.0) -> DirectionResult:
    td = route.track_data(ds)
    if reverse:
        td = td.reversed()
    seq, stop_s, dwell, jumps = _stops_for(route, train, reverse, dwell_of, stop_position,
                                           dwell_mult, reversal_min_s)
    sim = Simulator(train, td, driver, zone_drivers)
    res = sim.run([Stop(s, st.name, d, j) for s, st, d, j in zip(stop_s, seq, dwell, jumps)])
    label = f"{seq[0].name} -> {seq[-1].name}"
    return DirectionResult(label, seq, stop_s, dwell, res, reverse)


def apply_padding(dr: DirectionResult, pad: dict):
    """Timetable padding: percentage of running time on every leg, plus fixed seconds
    before the final stop (terminal recovery margin, as US commuter timetables do)."""
    pct = float(pad.get("percent", 0.0)) / 100.0
    final = float(pad.get("final_leg_s", 0.0))
    per_100km = float(pad.get("min_per_100km", 0.0)) * 60.0  # UIC 451-1 distance term
    pathing = pad.get("pathing", {}) or {}  # {station: s} scheduled waits (single-track meets)
    legs = dr.run.leg_times()
    arr = [0.0]
    dep = [dr.dwell[0]]
    t = dep[0]
    for k, leg in enumerate(legs):
        dist = dr.stop_s[k + 1] - dr.stop_s[k]
        leg_p = (leg * (1 + pct) + per_100km * dist / 100000.0
                 + float(pathing.get(dr.stations[k + 1].name, 0.0))
                 + (final if k == len(legs) - 1 else 0.0))
        t += leg_p
        arr.append(t)
        t += dr.dwell[k + 1]
        dep.append(t)
    dr.padded_arrivals, dr.padded_departures = arr, dep


def fmt_mmss(t: float) -> str:
    t = max(t, 0.0)
    return f"{int(t // 60)}:{int(round(t % 60)):02d}" if round(t % 60) < 60 else f"{int(t // 60) + 1}:00"


def parse_ref(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) * 60.0
    m, s = str(v).split(":") if ":" in str(v) else (str(v), "0")
    return float(m) * 60 + float(s)


def station_table(dr: DirectionResult, ref: Optional[dict] = None) -> str:
    lines = []
    hdr = (f"{'Station':32} {'km':>7} {'run':>6} {'dwell':>6} {'arr':>7} {'dep':>7} "
           f"{'sched':>7} {'ref':>7} {'diff':>6} {'vmax':>6}")
    lines.append(hdr)
    lines.append("-" * len(hdr))
    run = dr.run
    s0 = dr.stop_s[0]
    for k, st in enumerate(dr.stations):
        km = (dr.stop_s[k] - s0) / 1000
        if k == 0:
            leg, vmax = 0.0, 0.0
        else:
            leg = run.arrivals[k] - run.departures[k - 1]
            m = (run.t >= run.departures[k - 1]) & (run.t <= run.arrivals[k])
            vmax = float(run.v[m].max()) if m.any() else 0.0
        arr = run.arrivals[k]
        dep = run.departures[k]
        sched = dr.padded_arrivals[k] if dr.padded_arrivals else arr
        r = parse_ref((ref or {}).get(st.name))
        diff = f"{(sched - r) / 60:+.1f}" if r is not None else ""
        lines.append(f"{st.name[:32]:32} {km:7.2f} {fmt_mmss(leg):>6} {dr.dwell[k]:6.0f} "
                     f"{fmt_mmss(arr):>7} {fmt_mmss(dep):>7} {fmt_mmss(sched):>7} "
                     f"{fmt_mmss(r) if r is not None else '':>7} {diff:>6} "
                     f"{vmax / MPH:5.0f}m")
    return "\n".join(lines)


def summary_dict(route: Route, train: Train, dr: DirectionResult) -> dict:
    run = dr.run
    total = run.arrivals[-1]
    dist = dr.stop_s[-1] - dr.stop_s[0]
    moving = sum(run.leg_times())
    return {
        "direction": dr.label,
        "train": train.name,
        "distance_km": round(dist / 1000, 3),
        "stops": len(dr.stations),
        "running_time_min": round(moving / 60, 2),
        "dwell_total_min": round(sum(dr.dwell[1:-1]) / 60, 2),
        "trip_time_min": round(total / 60, 2),
        "scheduled_time_min": round(dr.padded_arrivals[-1] / 60, 2) if dr.padded_arrivals else None,
        "average_speed_kmh": round(dist / max(total, 1) * 3.6, 1),
        "max_speed_kmh": round(float(run.v.max()) * 3.6, 1),
        "energy_traction_kwh": round(run.energy_traction_kwh, 1),
        "energy_regen_kwh": round(run.energy_regen_kwh, 1),
        "stations": [
            {"name": st.name, "km": round((dr.stop_s[k] - dr.stop_s[0]) / 1000, 3),
             "arrive_s": round(run.arrivals[k], 1), "depart_s": round(run.departures[k], 1),
             "dwell_s": round(dr.dwell[k], 1),
             "scheduled_arrive_s": round(dr.padded_arrivals[k], 1) if dr.padded_arrivals else None}
            for k, st in enumerate(dr.stations)
        ],
    }


def main(spec: ProgramSpec, argv=None):
    ap = argparse.ArgumentParser(prog=f"railsim.{spec.name}",
                                 description=f"{spec.name} running-time simulator")
    ap.add_argument("config", help="line config YAML")
    ap.add_argument("--train", help="rolling stock key (overrides config)")
    ap.add_argument("--load", type=float, help="load factor 0..1 of the reference passenger load")
    ap.add_argument("--direction", choices=["forward", "reverse", "both"], default="both")
    ap.add_argument("--rail", choices=["dry", "wet", "leaf"],
                    help="rail condition (adhesion): dry (default), wet, leaf-fall")
    ap.add_argument("--out", help="output directory (default: output/<config name>)")
    ap.add_argument("--no-plots", action="store_true")
    ap.add_argument("--monte-carlo", type=int, default=0, metavar="N",
                    help="also run N randomised runs (driver/dwell variability): p50/p85 trip times")
    ap.add_argument("--headway", type=float, help="service headway (min): report fleet needed")
    ap.add_argument("--year", type=int, help="operating year (with an `operations:` era file)")
    ap.add_argument("--stops", help="stopping pattern: all, a pattern name (e.g. limited, express) "
                                    "from service.patterns")
    ap.add_argument("--list-trains", action="store_true")
    args = ap.parse_args(argv)

    lib = load_library(spec.library)
    if args.list_trains:
        for k, t in lib.items():
            print(f"{k:28} {t.name:45} {t.length:6.0f} m  {t.max_speed / MPH:4.0f} mph")
        return
    cfg_path = Path(args.config).resolve()
    user_cfg = yaml.safe_load(cfg_path.read_text())
    preset = user_cfg.get("preset")
    if preset and preset not in spec.presets:
        raise SystemExit(f"unknown preset '{preset}' (available: {', '.join(spec.presets)})")
    cfg = deep_merge(deep_merge(spec.defaults, spec.presets.get(preset, {})), user_cfg)
    base = _repo_root(cfg_path)
    era_note = ""
    era_train = None
    if cfg.get("operations"):
        era, era_train, year = load_era(base / cfg["operations"], args.year or cfg.get("year"))
        # defaults < preset < era < line config
        cfg = deep_merge(deep_merge(deep_merge(spec.defaults, spec.presets.get(preset, {})),
                                    era.get("overlay", {})), user_cfg)
        era_note = f" | {year}: {era['name']}"
        valid = cfg.get("years")
        if valid and not (valid[0] <= year <= valid[1]):
            raise SystemExit(f"{cfg.get('name', cfg_path.stem)} only ran in {valid[0]}-{valid[1]}; "
                             f"pick --year in that range")
    if args.stops:
        cfg.setdefault("service", {})["stops"] = args.stops
    key = args.train or cfg.get("train") or era_train
    if not key:
        raise SystemExit("no train: set `train:` in the config or use --train")
    if key not in lib:
        raise SystemExit(f"unknown train '{key}'. Use --list-trains.")
    train = lib[key].with_load(args.load if args.load is not None else float(cfg.get("load_factor", 0.5)),
                               args.rail or cfg.get("rail_condition", "dry"))

    print(f"== {spec.name.upper()} | {cfg.get('name', cfg_path.stem)} | {train.name} "
          f"(load {train.load_factor:.0%}, {train.mass / 1000:.0f} t, {train.rail_condition} rail)"
          f"{era_note}")
    route = build_route(cfg, base, curve_design_from(cfg, train), speed_policy_from(cfg, train),
                        profile_design_from(cfg))
    if train.min_curve_radius > 0:
        tight = [c for c in route.horizontal.curves if c.radius < train.min_curve_radius]
        if tight:
            route.warnings.append(
                f"{train.name} is not cleared for this route: {len(tight)} curve(s) tighter than "
                f"{train.min_curve_radius:.0f} m (tightest {min(c.radius for c in tight):.0f} m at km "
                f"{min(tight, key=lambda c: c.radius).s_ts / 1000:.2f})")
    far = [s for s in route.stations if 100 < s.offset and "routed to the nearest" not in
           " ".join(w for w in route.warnings if s.name in w)]
    for s in far:
        route.warnings.append(f"station '{s.name}' is {s.offset:.0f} m from the track; check its placemark")
    for w in route.warnings:
        print(f"  WARNING: {w}")
    driver = apply_driver_config(spec.make_driver(cfg, train), cfg)
    zone_drivers = []
    for oz in cfg.get("operating_zones", []) or []:
        zcfg = deep_merge(cfg, {"signalling": oz.get("signalling", cfg.get("signalling", {})),
                                "driver": oz.get("driver", {})})
        zone_drivers.append(apply_driver_config(spec.make_driver(zcfg, train), zcfg))
    stop_pos = (cfg.get("stations", {}) or {}).get("stop_position", "far_end")
    # driver changes ends at a stub terminal: walk the train, set up the cab, brake test
    rev_min = float((cfg.get("stations", {}) or {}).get("reversal_min_s", 240.0))

    def dwell_of(st):
        return spec.dwell_fn(st, train, cfg, False)

    out_dir = Path(args.out) if args.out else base / "output" / cfg_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    dirs = {"forward": [False], "reverse": [True], "both": [False, True]}[args.direction]
    results = []
    refs = cfg.get("reference", {}) or {}
    pad = cfg.get("padding", {}) or {}
    for rev in dirs:
        dr = run_direction(route, train, driver, dwell_of, rev, stop_position=stop_pos,
                           zone_drivers=zone_drivers, reversal_min_s=rev_min)
        apply_padding(dr, pad)
        technical_trip = dr.run.arrivals[-1] / 60.0
        eco_info = None
        if pad.get("distribution", "uniform") == "eco":
            # spend the padding as cruising below the limit + coasting (MARECO-like)
            target = sum(dr.run.leg_times()) + (dr.padded_arrivals[-1] - dr.run.arrivals[-1])
            drv_eco, dr_eco = eco_driver(
                lambda d: run_direction(route, train, d, dwell_of, rev, stop_position=stop_pos,
                                        zone_drivers=zone_drivers, reversal_min_s=rev_min),
                driver, target)
            eco_info = {"cruise_cap_kmh": round(min(drv_eco.cruise_cap, 999) * 3.6, 1),
                        "energy_uniform_kwh": round(dr.run.energy_traction_kwh, 1),
                        "energy_eco_kwh": round(dr_eco.run.energy_traction_kwh, 1)}
            dr_eco.padded_arrivals = list(dr_eco.run.arrivals)
            dr_eco.padded_departures = list(dr_eco.run.departures)
            dr = dr_eco
        ref = refs.get("reverse" if rev else "forward")
        print(f"\n-- {dr.label}")
        print(station_table(dr, ref))
        sd = summary_dict(route, train, dr)
        print(f"   running {sd['running_time_min']:.1f} min + dwell {sd['dwell_total_min']:.1f} min "
              f"= {sd['trip_time_min']:.1f} min; scheduled (padded) {sd['scheduled_time_min']:.1f} min; "
              f"avg {sd['average_speed_kmh']:.1f} km/h; traction energy {sd['energy_traction_kwh']:.0f} kWh")
        if eco_info:
            sd["eco"] = eco_info
            saved = 1 - eco_info["energy_eco_kwh"] / max(eco_info["energy_uniform_kwh"], 1e-6)
            print(f"   eco allowance: padding spent cruising <= {eco_info['cruise_cap_kmh']:.0f} km/h "
                  f"and coasting; traction energy {eco_info['energy_uniform_kwh']:.0f} -> "
                  f"{eco_info['energy_eco_kwh']:.0f} kWh ({saved:.0%} saved)")
        if args.monte_carlo:
            mc = monte_carlo(lambda d, m: run_direction(route, train, d, dwell_of, rev,
                                                        stop_position=stop_pos, dwell_mult=m,
                                                        zone_drivers=zone_drivers,
                                                        reversal_min_s=rev_min),
                             driver, args.monte_carlo)
            sd["monte_carlo_trip_min"] = {k: round(v, 2) for k, v in mc.items()}
            print(f"   Monte Carlo ({mc['runs']} runs, technical driving): trip p50 {mc['p50']:.1f} min, "
                  f"p85 {mc['p85']:.1f}, p95 {mc['p95']:.1f} (deterministic {technical_trip:.1f})")
        results.append((dr, sd))
    turn = float(cfg.get("turnback_min", 0) or 0)
    if len(results) == 2:
        cycle = sum(r[1]["scheduled_time_min"] for r in results) + 2 * turn
        msg = f"\n   round trip (scheduled + {turn:.0f} min turnback at each end): {cycle:.1f} min"
        hw = args.headway or (cfg.get("service", {}) or {}).get("headway_min")
        if hw:
            msg += f"; at a {hw:g}-min headway this needs {math.ceil(cycle / float(hw))} trains"
        print(msg)

    from . import report
    summary = {"program": spec.name, "line": cfg.get("name", cfg_path.stem), "train": key,
               "warnings": route.warnings, "directions": [sd for _, sd in results],
               "curves": [{"radius_m": round(c.radius, 1), "spiral_m": round(c.spiral, 1),
                           "start_km": round(c.s_ts / 1000, 3), "end_km": round(c.s_st / 1000, 3)}
                          for c in route.horizontal.curves],
               "speed_zones": report.zone_list(route)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    for dr, _ in results:
        report.write_csv(out_dir, dr)
    report.write_kml(out_dir / "alignment.kmz", route)
    if not args.no_plots:
        for dr, _ in results:
            report.plot_run(out_dir, route, dr, train)
    print(f"\nOutputs in {out_dir}")
    return route, results


def _repo_root(p: Path) -> Path:
    for parent in [p.parent] + list(p.parents):
        if (parent / "railsim").is_dir() and (parent / "data").is_dir():
            return parent
    return p.parent
