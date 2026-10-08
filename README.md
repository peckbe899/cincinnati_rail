# Cincinnati Rail running-time simulators

Physics-based running times for the alternate-history Cincinnati Metro and RER, built from
hand-drawn Google Earth KMZ alignments. Two programs share one core:

| Program | For | Dwell model | Driving model |
|---|---|---|---|
| `python -m railsim.metro` | Metro lines (CMCC fleet, MBTA-style heavy rail) | Door cycle: unlock/open, passenger flow per door, chime and close, dispatch | ATO or manual under cab signals, close to the limit; manual creeps into platforms |
| `python -m railsim.train` (alias `railsim.commuter`) | Commuter / RER / intercity / HSR (EMU, DMU, push-pull, high-speed) | Platform type: level vs low platform with steps, crew-operated doors, conductor, brake release | Engineer: margin under the limit, planned braking with air-brake delay. `preset: intercity` / `preset: hsr` switch cant rules, ETCS, allowances and dwell |

## Quick start

```bash
pip install numpy scipy matplotlib pyyaml
python -m railsim.metro configs/metro/mbta_orange.yaml          # calibration case
python -m railsim.commuter configs/commuter/mbta_needham.yaml   # calibration case
python -m railsim.metro configs/metro/cin_line_6.yaml --train CMCC_TYPE1948_10CAR
python -m railsim.batch configs/commuter --pattern "cin_rer_1*"  # whole folders
python -m railsim.metro configs/metro/cin_line_1.yaml --list-trains
python -m railsim.metro configs/metro/cin_line_6.yaml --year 1950  # operating era (fleet, signals, GoA)
python -m railsim.train configs/train/apex_transcontinental_limited.yaml --stops limited
python tools/make_cincinnati_configs.py                          # regenerate Cincinnati configs
python tools/make_apex_configs.py                                # regenerate APEx HSR configs
python tools/sensitivity.py commuter configs/commuter/mbta_needham.yaml "padding.percent=10"
```

Outputs go to `output/<config>/`:

- `summary.json`
- station CSVs and speed traces
- `profile_*.png`: speed with posted limits, elevation and grade
- `alignment.kmz`: the reconstructed alignment coloured by posted speed, with curves, structures and stations. Open it in Google Earth to check the fitted geometry.

## What the model does

1. **Track network** (`network.py`).
   - Segments may be drawn in any order and direction, and may branch or form T-junctions.
   - Routes through stations never reverse at a junction.
   - `service.route` picks a branch.
2. **Horizontal alignment** (`horizontal.py`).
   - The drawn polyline is rebuilt as tangents, spirals and circular arcs. Spirals follow AREMA (1.63·Eu·V, 62·Ea).
   - A curve drawn as many short chords is fitted as one curve.
   - A single corner gets the largest radius that stays within `corner_offset_tol_m` of the drawing.
   - Track length is the true curve length.
3. **Vertical profile** (`profile.py`).
   - Ground elevation comes from the legacy CSV, from KMZ altitudes, or from USGS 3DEP bare earth (`profile.usgs: true`; needs internet, cached).
   - A designed track profile is fitted to it: grades are bounded, platforms are near level, grade changes are smoothed, and going below ground costs more than going above it.
   - Each point is classified as at-grade, fill, viaduct, cut or tunnel.
4. **Posted speeds** (`speed.py`).
   - Curve speed is V = √(g·R·(Ea+Eu)/G), with G = 1500 mm.
   - Short spirals are capped by the rate of change of cant deficiency.
   - Limits are posted in 5 mph steps, or in cab-signal code steps.
   - Short zones are consolidated.
   - User restrictions and terminal approaches can be added.
5. **Dynamics** (`dynamics.py`).
   - Time-stepped force balance: tractive effort is limited by adhesion, maximum effort and power; resistance is the Davis equation (with a tunnel factor).
   - Grade and Röckl curve resistance are averaged over the train's length. Rotating mass is included.
   - Acceleration and braking changes are jerk-limited.
   - Braking follows a planned braking curve with brake build-up delay. On steep downgrades it is limited by brake capability.
   - A restriction holds until the rear of the train clears it.
6. **Operations** (`operations.py`), drawn from how OSRD, Open Rails, OpenTrack and similar tools work (`docs/research/simulators.md`):
   - `signalling.system`: `lineside` (OSRD offsets of 100 m anticipation and 50 m postponement), `cab` (code steps), `cbtc` (ATO margin and supervision lag), `etcs2` (indication/permitted lag) or `lzb` (supervision deceleration table).
   - Driver profile: `power_fraction`, `brake_fraction`, `anticipation_m`, `postponement_m`, `brake_anticipation_s`, `coast_window_s`.
   - `--rail dry|wet|leaf`: Curtius-Kniffler adhesion, which also limits braking.
   - `supply.factor` and `supply.zones`: voltage sag reduces available power.
   - `neutral_sections`: traction is cut over them.
   - `restrictions` can be given as `turnout: 15` (AREMA number) or a DB turnout type.
   - Rolling stock can supply a tabulated `te_curve_kmh_kn`, a speed-dependent `brake_curve_kmh_ms2` (HSR brake fade), `power_ramp_s` (diesel spool-up) and `aux_kw`.
   - Platform stopping: by default the head stops at the far end of the platform (`stations.stop_position`).
   - `driver.block_length_m`: fixed-block transit ATC. Codes change only at block boundaries, so braking starts at the block where the lower code arrives.
   - `operating_zones`: a section with its own signalling and driver, e.g. CBTC + ATO on an RER trunk inside manually driven branches.
   - Stub terminals: a route entry `{name: X, reverse: true}` makes the train run to the buffer and reverse (minimum dwell `stations.reversal_min_s`). A route whose first and last entries are the same station runs as a loop.
   - Station dwell: `dwell.door_control` (`crew`, or driver-only `button`/`auto`), and per-station platform screen doors (`dwell.psd_classes`, `dwell.psd_stations`, `stations.info.<name>.psd`).
   - `track.finished` + `geometry.sketch_tolerance_m`: segments not listed as finished are sketches, and their curves get the largest radius within the tolerance of the drawing.
   - `track.extra` (track from other folders or KMZ/KML files), `{via: [lat, lon]}` route waypoints, `profile.structures` (tunnel/viaduct by station range, coordinates or drawn segment name).
7. **Operating eras** (`operations: data/operations/cincinnati_metro.yaml`, `--year`). The year picks the default train, signalling, Grade of Automation and door practice. Cincinnati Metro runs from gate cars (1905) through fixed-block ATO (1986) and CBTC (2006) to GoA3 (2020 onward). Sources are in `docs/research/eras.md`. RER configs carry `years:`; the pre-RER services (`cin_rer_*_pre_rer_*`, branches into Union Terminal or Times) come from the `history` block of `data/operations/cincinnati_rer.yaml`.
8. **Timetable**.
   - Padding: a percentage, a UIC-style minutes-per-100 km term, pathing time at single-track meets, and terminal recovery.
   - Results are compared with a reference schedule.
   - `padding.distribution: eco` spends the padding MARECO-style instead of uniformly: a cruising cap plus coasting before braking, and the energy saved is reported.
   - `--monte-carlo N` adds driver and dwell variability and reports p50, p85 and p95 trip times.
   - `--headway H` (or `service.headway_min`) with `turnback_min` gives the round-trip cycle time and the number of trains needed.

## Rolling stock

`data/rollingstock/metro.yaml` and `data/rollingstock/commuter.yaml` define each train physically: mass, power, tractive effort, adhesion, Davis coefficients, braking rates, jerk and doors. Every value is tagged published [P], secondary [S] or estimate [E].

- **Metro**:
  - MBTA Orange Line CRRC (VE-10-036 spec) and MBTA Blue Line.
  - CMCC Types 1903, 1925, 1948, 1985 and 2005 (48 ft, 10 cars, hill-geared for 5% grades).
  - Long-car 60 ft variants, which are barred from curves under 65 m.
- **RER**:
  - Brightliner, Silverliner and Swiftliner.
  - A to F sets, each modelled on its real inspiration (Sydney V set, MI 84, Coradia Duplex, DB 423, KISS, FLIRT).
  - Reference consists: MBTA HSP46 + bilevels, SC-44 + bilevels, Caltrain KISS.
- **HSR**:
  - Velaro D, ETR 1000, AGV and Avelia Liberty.
  - APEx Gen 6: 11-car tilting set, 250 mph, physics from CR450-class research.

## Calibration

| Case | Model | Published | Notes |
|---|---|---|---|
| MBTA Orange Line, Oak Grove to Forest Hills | 35.8 min (running + dwell) | 35 min (GTFS Fall 2025, weekday midday) | No tuning: researched car spec, line speeds, cab-signal codes on 300 m blocks, MIT dwell model (+2.3%) |
| MBTA Needham Line, weekend | 34.1 min technical; 38.7 min with 10% + 2 min padding | 40 min | −3.3%. Branch speed limits are unpublished |

See `docs/CALIBRATION.md` for details, `docs/RESEARCH.md` for sources, and `docs/PROGRESS.md` for done and to-do items.

## Config reference

See the annotated examples in `configs/metro/mbta_orange.yaml` and `configs/commuter/mbta_needham.yaml`. Each program's defaults are in `DEFAULTS` at the top of `railsim/metro.py` and `railsim/commuter.py`. A line config only overrides what differs.
