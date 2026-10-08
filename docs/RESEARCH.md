# Research notes

Values in the rolling-stock libraries and program defaults come from these notes. Each number in them is tagged:

- **[P]**: published by a manufacturer, agency or regulation.
- **[S] / [P-2]**: secondary source.
- **[F]**: fan or forum source.
- **[E]**: estimate or derivation.

The sandbox's network policy blocked direct page fetches, so most web figures come from search-result extracts of the cited URLs. Treat even [P] values as worth re-checking against the original document.

| File | Covers |
|---|---|
| [research/geometry.md](research/geometry.md) | Curve speed (G = 1500 mm), cant and cant deficiency (FRA, transit, EN 13803), spirals, reverse curves, grades, vertical curves, curve resistance, curve fitting from polylines, elevation datasets (3DEP vs SRTM/Copernicus) |
| [research/metro.md](research/metro.md) | MBTA Orange/Red/Blue, BART, R211, WMATA 7000, MP14 specs; metro Davis and tunnel factors; door cycle and dwell (TCQSM, Puong MIT model); Orange Line GTFS, speeds and cab-signal codes; IRT Steinway hill gearing; R46 curve ban; magnetic track brakes; steep-grade traction |
| [research/commuter.md](research/commuter.md) | FLIRT, KISS, Mireo, Coradia, M9, SC-44, ALP-45DP, HSP46, F40PH, bilevels; Davis/Sauthoff/Strahl resistance; tractive effort and adhesion; FRA track classes and cant rules; commuter dwell; UIC 451-1 padding; Needham Line GTFS data |
| [research/simulators.md](research/simulators.md) | How OpenTrack, RailSys, RAILSIM, RTC, Open Rails, TrainRuns.jl, OSRD, SUMO, FBS and Network Rail SRT model running times; the 14 realism features we lacked, ranked by impact; validation practice. Open Rails, TrainRuns.jl, OSRD and SUMO were read from source |
| [research/rer_fleet.md](research/rer_fleet.md) | Real inspirations for the TRI RER fleet: Pioneer Zephyr, Silverliner, Z 5100/5300, DB 420, V set, MI 84, Coradia Duplex, Regio 2N, DB 423, KISS, FLIRT; door cycles and bilevel boarding penalties |

**Calibration data**: MBTA GTFS (Fall 2025), read from the copy in [transitmatters/regional-rail-schedule-generator](https://github.com/transitmatters/regional-rail-schedule-generator) (`data/gtfs-present`), plus the Needham Line Spring/Summer 2026 public timetable.
