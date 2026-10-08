# Progress tracker

Living list of what is done and what is left. Newest changes at the top of each section.

## Done

- **Repository layout**: `railsim/` package with two programs sharing one core:
  - `python -m railsim.metro <config>` for metro lines, with a door-cycle dwell model and ATO-style driving.
  - `python -m railsim.commuter <config>` for commuter and RER lines, with platform-type dwell and engineer-style driving.
  - The legacy notebooks are kept in `legacy/` (outputs stripped).
- **KMZ reading** (`kml.py`):
  - Keeps the folder hierarchy.
  - Expands MultiGeometry.
  - Reads altitudes.
  - Needs no simplekml.
- **Track network and routing** (`network.py`), which replaces the pairwise stitcher:
  - Snaps segment endpoints together.
  - Detects T-junctions.
  - Routes through stations with turn constraints, so a route never reverses through a junction.
  - Handles branched RER folders. Tested on all Cincinnati RER folders, the Orange Line and Needham.
- **Horizontal alignment reconstruction** (`horizontal.py`): turns the hand-drawn polyline into real geometry (tangents, spirals, arcs).
  - Spiral lengths follow the AREMA rules L = 1.63·Eu·V and L = 62·Ea.
  - Reverse curves get a tangent of at least 2 s of running.
  - Curves drawn with many vertices are merged and fitted at their best-fit radius. Single corners use the largest radius within an offset tolerance.
  - Removes drawing jitter (Douglas-Peucker).
  - Track length is the true curve length, not the polygon length.
- **Vertical profile design** (`profile.py`): fits a designed track profile to the ground profile.
  - Grades are bounded and platforms are level within 0.5%.
  - Vertical curves are smoothed.
  - Going below ground costs more than going above it.
  - Each point is classified as at-grade, fill, viaduct, cut or tunnel.
- **Elevation sources** (`elevation.py`):
  - The legacy CSV.
  - Altitudes stored in the KMZ.
  - USGS 3DEP bare-earth data via EPQS, with a disk cache. This needs internet; it is blocked in the build sandbox but works on a normal machine.
- **Posted speed limits** (`speed.py`):
  - Curve speeds use cant plus cant deficiency, with G = 1500 mm.
  - Short spirals are limited by the rate of change of cant deficiency.
  - A curve shorter than a car is treated as averaged over the car's length.
  - Limits are posted in 5 mph steps.
  - Short zones are consolidated into their neighbours.
  - User restrictions and terminal approaches can be added.
- **Physics engine** (`dynamics.py`): force-based and time-stepped.
  - Tractive effort is limited by adhesion, maximum effort and power.
  - Resistance uses the Davis equation, with a tunnel factor.
  - Grade and curve resistance (Röckl) are averaged over the train's length.
  - Rotating mass is included.
  - Acceleration and braking changes are jerk-limited.
  - Braking follows a braking curve that allows for brake build-up delay.
  - Restrictions hold until the rear of the train clears them.
  - Traction energy and regenerated energy are tracked.
- **Dwell models** (`dwell.py`):
  - Metro: door cycle per TCQSM.
  - Commuter: level vs low-platform boarding, crew-operated doors, conductor and brake release.
- **Timetable layer**:
  - Padding as a percentage plus a final-leg recovery time.
  - Compares against reference schedules.
  - Writes CSV, JSON, KMZ (alignment coloured by speed limit, plus curves, structures and stations) and plots.
- **Unit tests** (`tests/`): analytic run times, restrictions held over the train length, power-limited and uphill runs, jerk limit, curve recovery, routing, profile limits.
- **Research notes**: track geometry and commuter rolling stock.
- **Calibration data**: MBTA GTFS (Fall 2025) gives station coordinates and schedules for the Orange Line and Needham.

## In progress

- Metro rolling stock library: MBTA Orange Line CRRC cars, and the Cincinnati canon fleet (CMCC Types 1903 to 2005 and the long-car variant). Waiting on metro research.
- RER fleet library: Brightliner, Silverliner, Swiftliner, and the A to F sets, built from their real inspirations. Waiting on RER research.
- Calibration against the Orange Line (35 min) and Needham (40 min weekend).

## To do

- Configs for every Cincinnati Metro line and every RER service, with `service.route` for each RER branch.
- Elevation for the Cincinnati lines: run with `profile.usgs: true` on a machine with internet, or point to the legacy CSVs.
- Research how other simulators work (OpenTrack, RailSys, Open Rails, TrainRuns.jl, SYSTRA RAILSIM, Train Performance Calculators) and add the realism they model that we don't. Must cover metro through HSR.
- HSR program defaults: high cant deficiency, tilt, the aerodynamic share of resistance, tunnel pressure effects.
- Single-track meets and pathing time, for Needham weekday trips.
