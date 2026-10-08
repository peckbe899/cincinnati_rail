# Calibration against real MBTA services

Both cases use the hand-drawn KMZs supplied with the project. Station coordinates come from MBTA GTFS (Fall 2025). Physical inputs come from the research notes. Nothing was fitted to the schedule except the padding policy, and the padding is chosen from published practice, not tuned.

The KMZs carry no altitudes and the sandbox could not reach USGS, so both profiles are **flat**. Real grades (Charles River tunnel ramps and the Tufts downgrade on the Orange Line; rock cuts on Needham) would add a little time.

## MBTA Orange Line (metro program)

- **Train:** CRRC #14, 6 cars.
  - Acceleration 2.75 mphps to a 16.3 mph knee, then constant power (MBTA spec VE-10-036).
  - Full-service braking 3.0 mphps; 1.1 m/s² planning rate.
- **Line speeds:** 55 mph Oak Grove–Assembly (since Aug 2025); 40 mph line maximum elsewhere.
- **Signals:** cab-signal code speeds 10/18/25/40/50/55 mph.
- **Driving:** manual (the Orange Line has no ATO), 1 mph under the code, a 4 mph creep over the last 15 m into each platform.
- **Fixed blocks:** civil speed codes change only at ~300 m track-circuit boundaries, so braking for a restriction starts at the block where the lower code arrives, and the higher code returns one block after the rear clears.
- **Dwell:** Puong (MIT) MBTA dwell model, D = 12.22 + 2.27·B + 1.82·A per door, with midday volumes by station class.

| | Model | GTFS weekday midday |
|---|---|---|
| Oak Grove → Forest Hills | 35.8 min | 35 min |
| Forest Hills → Oak Grove | 35.7 min | 35 min |

Sensitivity (`tools/sensitivity.py metro configs/metro/mbta_orange.yaml ...`):

| Variant | Trip (min) | vs schedule |
|---|---|---|
| Baseline (manual, 300 m code blocks, no padding) | 35.8 | +2.3% |
| Continuous codes (no block quantization) | 35.1 | +0.4% |
| ATO-style driving instead of manual | 32.7 | −6.6% |
| 90% load instead of 50% | 35.2 | +0.7% |
| No cab-signal code rounding (plain 5 mph steps) | 34.8 | −0.6% |

How driving is modelled matters more than load. That fits the cab-signal / manual-operation character of the line.

## MBTA Needham Line (commuter program)

- **Train:** HSP46 plus 6 bilevel coaches.
  - 289 kN starting tractive effort; about 2.85 MW at the wheel after head-end power.
  - Planning braking 0.6 m/s² with 2.5 s air-brake build-up.
- **Track:**
  - FRA cant rules: Eu = 3 in, MBTA practice Ea ≤ 4 in.
  - 60 mph line speed.
  - 30 mph through the South Station interlocking and the Forest Hills junction.
  - 40 mph through the Needham grade crossings.
  - 15 mph stub-terminal approach.
- **Platforms and dwell:** high-level platforms at the four city stations; low platforms with a mini-high elsewhere, with crew-operated doors and steps.
- **Fitted curves agree with known speeds:**
  - The Back Bay curve fits at R ≈ 180 m. At FRA cant this gives 25–30 mph; the historically posted limit is 30 mph.
  - Needham Junction comes out at 25 mph, the same as the independent research estimate.

| | Technical (running + dwell) | With padding (10% + 2 min) | Published (weekend) |
|---|---|---|---|
| South Station → Needham Heights | 33.5 min | 38.0 min | 40 min |
| Needham Heights → South Station | 33.4 min | 38.0 min | 40 min |

Current figures (after dwell capacity scaling): 34.1 min technical, 38.7 min padded, −3.3%. US commuter cab signals do not code civil speed limits (engineers obey timetable speed signs), so no block quantization applies here.

Sensitivity:

| Variant | Scheduled (min) | vs 40 |
|---|---|---|
| 10% padding (US commuter practice: SEPTA, Metro-North ≈ 10%) | 38.0 | −5% |
| + branch speed 50 mph instead of 60 | 39.1 | −2% |
| + 80% load | 38.4 | −4% |
| + braking 0.5 m/s² | 38.8 | −3% |
| No padding at all | 33.5 | −16% |

**Reading:** the published weekend schedule is about 19% above the technical minimum. That is consistent with US commuter padding (6–10%) plus terminal recovery, and with branch speed limits we could not find published (MBTA/Keolis track charts are not public). Weekday trips take 45–48 min because of meets on the single-track Needham branch. Model those with `padding.pathing: {Hersey: 300}`.

## After the simulator-survey features

- Both lines now run with `signalling: {system: cab}`. Following OSRD, cab signalling adds no lineside anticipation offsets; its effect is the code-step speed rounding. Results are unchanged: Orange Line +0.4%, Needham −5% padded.
- **Monte Carlo** (20 runs: 88–100% traction, 85–100% braking, +0–3 km/h margin, ±20% dwell):

| Line | Deterministic | p50 | p85 |
|---|---|---|---|
| Orange Line | 35.1 min | 35.7 min | 38.0 min |
| Needham | 33.5 min | 34.3 min | 36.0 min |

  The published schedules sit between the deterministic and p85 values, as expected of timetables built from observed running.
- **Eco allowance on Needham:** the 4.5 min of padding is spent cruising at ≤ 56 km/h and coasting before braking, instead of uniformly. Traction energy falls 558 → 286 kWh. That is an upper bound: it assumes a driver advisory system and a large padding share.
- **Fleet check:** the Orange Line at a 6-min headway with 4-min turnbacks needs 14 trains, close to the MBTA's peak Orange Line operation.

## After the era work

- Block quantization of cab codes (`driver.block_length_m`, metro ATC only) puts the Orange Line at +2.3%, inside the 1-minute rounding of GTFS times.
- On Cincinnati Line 6, CBTC (2010) runs 7% faster than fixed-block ATC (1995) on running time. The Jubilee line measured 6% when it moved to CBTC.

## Re-running

```bash
python -m railsim.metro configs/metro/mbta_orange.yaml
python -m railsim.commuter configs/commuter/mbta_needham.yaml
python tools/sensitivity.py commuter configs/commuter/mbta_needham.yaml "geometry.line_speed_mph=50"
```
