# Cincinnati Metro profile analyzer: handoff

What this folder holds, for the travel-time repo.

## Files

- `profile_analyzer.html`: the Cincinnati Metro Profiles page (long-section editor). Its logic is the reference: ground and river handling, the station-level solver (each station as shallow as the grade limit allows, canon levels held, solved both ways), structure typing (elevated, at grade, cut and cover, shallow shield, deep tube) with the canon sections for Lines 1-6, grade and clearance checks.
- `settings.json`: the design settings in use (page defaults; nothing saved over them).
- `lines/Line_*.json`: per line, 2 m chainage: `ground_dm` (decimetres NAVD88), `stations` (chainage `c`, ground, lon/lat), `path` ([chainage, lon, lat]), `rivers`, `crossings` (with the other line's chainage `oc`), `pieces`. `lines/index.json` lists them; `network.json` has every line's plan and the river outlines.
  - `ground_dm` is now the map 3 (alternate 2026) ground sampled from `map3_profile_dem_dm.vrt` along the whole line. The original LiDAR sampling is kept as `ground_dm_lidar`. Only Line 14's last 1.5 km, east of the LiDAR extent, keeps the original values.
- `alignments/Line_1, 2, 4, 5.json`: Ben's saved profiles from the page: station rail levels by name (`st`), bend points (`pvi`, [chainage, rail level]), painted structure overrides (`ovr`, [from, to, type]), and a derived station table and summary. Other lines have no saved profile; the solver's default applies.
- `map3_profile_dem_dm.vrt` with its four tiles `map3_profile_dem_dm_r0c0/r0c1/r1c0/r1c1.tif`: the map 3 (alternate 2026) ground over the whole LiDAR extent, E 695000-735000, N 4315000-4350000 (about -84.749 to -84.276, 38.962 to 39.268), which holds every Metro line. int16 decimetres NAVD88, nodata -32768, EPSG:26916, 2 m cells. Set `profile.dem` to the .vrt (keep the four tiles beside it) with `dem_scale: 0.1`. Contents: LiDAR, real-only works rebuilt from the 1950s USGS sheets, building and street imprint removed, canon interstates, Embankment, Mill Creek deck, Lunken levees, Kentucky terraces. Bridges and viaducts are not in it.
- The earlier single-window `map3_profile_dem_dm.tif` is superseded by the .vrt.

## Notes

- Chainage starts at each line's first path point; station keys repeat with `#index` only where a name occurs twice on a line.
- No line now crosses a raster edge (the old Line 12 step at canon I-71 is gone). The sharp steps left on the lines are real canon structures: the Embankment wall and Kentucky terraces from the 142.0 m quay up to 151.8 m where lines meet the river (Lines 1, 2, 3, 6, 8, 11), the Embankment and Lunken levee near the Little Miami (Lines 5, 13), and canon I-75 cut walls (Line 4 at 7,068 m, about 19 m; Line 10 at 3,776 m, about 8 m). A line crossing them is on a bridge or in a tunnel there.

## Prompt for the Claude Code session

> Add the Cincinnati Metro profile analyzer to this repo so travel times use real vertical profiles. Everything is in this folder (see README.md). Port the analyzer's logic from profile_analyzer.html, load the per-line ground and Ben's saved alignments, use settings.json, and set profile.dem to map3_profile_dem_dm.vrt with dem_scale 0.1. Grades and station rail levels should feed the run-time calculation.

## Rail Profiles page (`profiles.html`)

The same editor for the Metro and the RER, published as a claude.ai artifact (saved profiles live in its shared database: `alignments/<id>`, settings in `config/settings` and `config/settings_rer`). Metro behaves exactly as `profile_analyzer.html`. RER additions:

- `rer/lines/RER_*.json`: the trunk core of each RER line, two stations past each end of the drawn "Trunk" segments, cut from a representative through service (`service`) and sampled on the map 3 ground at 2 m. `route_chainage_m` is the core's place on that service; `trunks` lists the drawn trunk spans; each station has `trunk: true|false`. Built by `tools/make_rer_profile_lines.py`.
- Station mode: trunk stations start underground (12 m rail depth), the others at grade on the old railroad, with bend points every 250 m following the smoothed ground. Switch a station in its card; that re-solves the line.
- Canon (`rer/canon.json`, Ben's rulings): station modes, fixed rail levels (Union Terminal level -2 at 142.0 m; RER-3 covered way at 144 m), the RER-3 covered way and RER-5 deep bore, the boulevard deck over the Mill Creek trunk (rail at DEM - 8.5 m), and river tubes (roof the set cover below the river bed; the Little Miami crossed inside the covered way).
- RER settings (`rer/settings.json`): canon 35 per mille, 200 m platforms, 12 m station depth; starting values for the 25 m deep-bore threshold, 7 m envelope, 9 m crossing clearance, 3 m tube cover and the river bed depths in `canon.json`.
- Crossings: Metro and RER rail clearances both ways (`rer/metro_rails.json` holds every Metro line's rail for the RER side).
- Profiles now also save `sg`: each station's platform grade in per mille (rising with chainage) about its centre rail level.
- Saved RER profiles go to `rer/alignments/RER_*.json` (exported from the page's database); the RER through-service configs pick them up automatically.
