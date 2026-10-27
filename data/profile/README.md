# Cincinnati Metro profile analyzer: handoff

What this folder holds, for the travel-time repo.

## Files

- `profile_analyzer.html`: the Cincinnati Metro Profiles page (long-section editor). Its logic is the reference: ground and river handling, the station-level solver (each station as shallow as the grade limit allows, canon levels held, solved both ways), structure typing (elevated, at grade, cut and cover, shallow shield, deep tube) with the canon sections for Lines 1-6, grade and clearance checks.
- `settings.json`: the design settings in use (page defaults; nothing saved over them).
- `lines/CVG_Express.json`: the CVG Express (Union Terminal to CVG), built by `tools/make_cvg_profile_line.py` from `data/kmz/CVG_Express.kmz` in the same format (piece 5 'Today' by default; pass `Original` for the first route). Run `tools/make_rer_profile_lines.py` afterwards for its RER crossings.
- `lines/Line_*.json`: per line, 2 m chainage: `ground_dm` (decimetres NAVD88), `stations` (chainage `c`, ground, lon/lat), `path` ([chainage, lon, lat]), `rivers`, `crossings` (with the other line's chainage `oc`), `pieces`. `lines/index.json` lists them; `network.json` has every line's plan and the river outlines.
  - `ground_dm` is now the map 3 (alternate 2026) ground sampled from `map3_profile_dem_dm.vrt` along the whole line. The original LiDAR sampling is kept as `ground_dm_lidar`. Only Line 14's last 1.5 km, east of the LiDAR extent, keeps the original values.
- `alignments/Line_1, 2, 4, 5.json`: Ben's saved profiles from the page: station rail levels by name (`st`), bend points (`pvi`, [chainage, rail level]), painted structure overrides (`ovr`, [from, to, type]), and a derived station table and summary. Other lines have no saved profile; the solver's default applies.
- `map3_profile_dem_dm.vrt` with its four tiles `map3_profile_dem_dm_r0c0/r0c1/r1c0/r1c1.tif`: the map 3 (alternate 2026) ground over the whole LiDAR extent, E 695000-735000, N 4315000-4350000 (about -84.749 to -84.276, 38.962 to 39.268), which holds every Metro line. int16 decimetres NAVD88, nodata -32768, EPSG:26916, 2 m cells. Set `profile.dem` to the .vrt (keep the four tiles beside it) with `dem_scale: 0.1`. Contents: LiDAR, real-only works rebuilt from the 1950s USGS sheets, building and street imprint removed, canon interstates, Embankment, Mill Creek deck, Lunken levees, Kentucky terraces. Bridges and viaducts are not in it.
- The earlier single-window `map3_profile_dem_dm.tif` is superseded by the .vrt.
- 2026-10-09: the tiles hold the canon riverbed in the Ohio and Licking (handoff). `map3_profile_dem_dm_water.tif` is the water surface over those beds (the earlier tiles' values there, nodata elsewhere): `railsim.elevation.from_dem` uses it by default so ground-following route profiles cross on bridges at water level; the profile line tools read the bed (`water=False`). Metro `lines/*.json` take the riverbed from the handoff files; Lines 1 and 2 (whose handoff line files were not uploaded) were re-sampled from the tiles in the river spans only, about 1 m off near the banks.

## Notes

- Chainage starts at each line's first path point; station keys repeat with `#index` only where a name occurs twice on a line.
- No line now crosses a raster edge (the old Line 12 step at canon I-71 is gone). The sharp steps left on the lines are real canon structures: the Embankment wall and Kentucky terraces from the 142.0 m quay up to 151.8 m where lines meet the river (Lines 1, 2, 3, 6, 8, 11), the Embankment and Lunken levee near the Little Miami (Lines 5, 13), and canon I-75 cut walls (Line 4 at 7,068 m, about 19 m; Line 10 at 3,776 m, about 8 m). A line crossing them is on a bridge or in a tunnel there.

## Prompt for the Claude Code session

> Add the Cincinnati Metro profile analyzer to this repo so travel times use real vertical profiles. Everything is in this folder (see README.md). Port the analyzer's logic from profile_analyzer.html, load the per-line ground and Ben's saved alignments, use settings.json, and set profile.dem to map3_profile_dem_dm.vrt with dem_scale 0.1. Grades and station rail levels should feed the run-time calculation.

## Rail Profiles page (`profiles.html`)

The same editor for the Metro and the RER, published as a claude.ai artifact (saved profiles live in its shared database: `alignments/<id>`, settings in `config/settings` and `config/settings_rer`). Metro behaves exactly as `profile_analyzer.html`. RER additions:

- `rer/lines/RER_*.json`: the trunk core of each RER line, two stations past each end of the drawn "Trunk" segments, cut from a representative through service (`service`) and sampled on the map 3 ground at 2 m. `route_chainage_m` is the core's place on that service; `trunks` lists the drawn trunk spans; each station has `trunk: true|false`. Built by `tools/make_rer_profile_lines.py`.
- Station mode: trunk stations start underground (12 m rail depth), the others at grade on the old railroad, with bend points every 250 m following the smoothed ground. Switch a station in its card; that re-solves the line.
- Canon (`rer/canon.json`, Ben's rulings): station modes, fixed rail levels (the Union Terminal TRI box one level for A, B and D at 135.7 m, 2026-10-26; RER-3 covered way at 144 m; B/D on the north viaduct: Northside / Spring Grove 162.5 m, Arlington 165.9 m, Camp Washington 165.2 m, into the Straight box at 151.64 m, 2026-10-26, replacing the yard-level deck), the RER-3 covered way and RER-5 deep bore, and river tubes (roof the set cover below the river bed; the Little Miami crossed inside the covered way). RER-5 keeps its old Union Terminal level (142.0 m) and Norwood Central at grade until Ben sets them on the page.
- RER settings (`rer/settings.json`): canon 35 per mille, 670 ft (204.2 m) platforms (2026-10-26; was 200 m), 12 m station depth; starting values for the 25 m deep-bore threshold, 7 m envelope, 9 m crossing clearance, 3 m tube cover and the river bed depths in `canon.json`.
- Crossings: Metro and RER rail clearances both ways (`rer/metro_rails.json` holds every Metro line's rail for the RER side).
- Profiles now also save `sg`: each station's platform grade in per mille (rising with chainage) about its centre rail level.
- `gapfill`: keys of Metro stations named as platform-curvature exceptions with gap fillers (radius under 600 m allowed).
- `so`: platform offset in metres (platform centre = drawn point + so, within half a platform, so the point stays on the platform); `del`: keys of removed stations (left out of the solve, the checks and the run times; the service's terminals stay). Each `stations` entry carries `point_c`, the drawn point.
- Saved RER profiles go to `rer/alignments/RER_*.json` (exported from the page's database); the RER through-service configs pick them up automatically.

## CUT and Norwood Central context (2026-10-26)

Ben's rulings, applied to the page (version 33) and to `railsim/metro_profile.py`:

- `context/lines.json`: for each line, the other systems' structures at CUT and Norwood Central as chainage blocks, and the Deck's street re-grades and open cuts as ground runs. Built by `tools/make_profile_context.py` from a snapshot of the Mill Creek Deck's published files in `data/deck/` (version 1793028977-4bc6, layout 2461). Rebuild it when the Deck changes.
  - Blocks: the CUT lower level (-2, rail 144.0 m) and its south throats; the lower pairs' tunnel from the Findlay portals and their open cut from Bank to Findlay; the intercity (CS) and C&O pairs (tunnel, trough, viaduct); the CUT platform deck and approach viaduct, the north arch viaduct and the trunk fill (APEx arch viaduct levels by street); the Norwood Central ORR, Transvalley and APEx tracks in their cut with the trench. Each has the other system's rail level along it (`p`), its heights below / above its rail (`b`, `t`; box 1.0 / 6.6, trough and at grade 0.8 / 5.8 clear, viaduct 1.6 / 5.8 clear), its platforms (`pl`) and its source (`s`).
  - Ground runs: `add` (W 8th and Horne raised up to 5 m, Findlay +2.0 m, Bank -2.0 m; crossing streets take the larger re-grade) and `cap` (ground held at the trough floor in open cuts and troughs). Indices into the 2 m `ground_dm` array.
  - Lower-pair levels are rebuilt from the Deck's dive figures (160.1 m over Bank, 2.72% to 150.2 m under Findlay, to 146.0 m at Sherman, 0.5% to 144.0 m) until the Deck publishes a level per point. Norwood: from the ground at s 3,220 (174.8 m), 2% to 170.0 m, 1.39% to 178.0 m at s 4,036, level through the station (approximate, from the ground data). Drawing values: the W 8th ramp ends and the 60 m ramps on Bank and Findlay.
- Ground in three layers: the raster; plus the Deck re-grades and cuts (the ground the level solver uses); plus, over painted cut and cover, the ground filled to the box roof plus cover (Metro 4.6 + 0.6 m above the rail, RER the box height) sloping back at `fillTaper` (50 per mille, a drawing value) past the ends. Structure type and cover are judged on the finished ground.
- Clearance: every block against the line at its worst point with the crossing rule (upper floor + 0.5 m + lower top; a track in the open counts its clear height, Metro 4.2 m, RER 5.8 m). Under a viaduct only a line in the open is checked (arches to the street, no footing check). `MetroProfile.context_clearances()`; `summary()["context_clashes"]`; run logs list each clash as a warning.
- CVG Express: Union Terminal at platform M on the CUT platform deck, 160.3 m (was track level 154.0 m).
- Metro platforms 400 ft (121.92 m, Ben 2026-10-23) in `settings.json` and the port's defaults.
- Line 3: its Norwood end follows the Deck route to Ben's terminus (`tools/repath_line3_norwood.py`; chainages past the rejoin -140.9 m). Crossings and rails tables updated.
- Saved profiles exported from the page database (2026-10-26): `alignments/` Line 1, 2, 3, 4, 5, 6, 8, CVG Express; `rer/alignments/` RER-1, RER-2. The Line 3, 6 and 8 and RER-1 and RER-2 configs now name them.

## Structure types, the upper deck and the B/D re-path (2026-10-27)

Ben's rulings, in `tools/make_profile_context.py` (`structure_types()`, `upper_deck()`), `railsim/metro_profile.py` and the RER data:

- Structure types at CUT (`st` on each block, `k` kept as `viaduct` / `fill` / `box` for the page):
  - the fan from W 9th to W Liberty (the CUT platform deck, the approach north of W 9th and the north viaduct south of W Liberty): an embankment with a bridge over each of its 11 streets;
  - arch viaducts only on the wide multi-track stretches, each arch spanning a street: the south approach from W 9th to the Cardinal crossing (Budd, W 7th, W 8th) and the north arch viaduct; the north trunk fill is an embankment;
  - the rest are normal viaducts on piers: the south approach past the Cardinal crossing, the intercity, C&O and TRIMET viaducts. The intercity and C&O descents, where the rail is under 6.5 m above the ground, are embankments with blind arches.
  - Street openings: `gaps` on each block, `[c0, c1, street]` on the line's chainage.
- Clearance (`context_clearances()`): under an embankment or an arch viaduct a line in the open can pass only through a street opening; outside one it is a clash (`blocked`), whatever the heights. Tests: `tests/test_core.py::test_context_street_openings`.
- Upper deck: the Indianapolis APEx pair and RER D run on an upper deck over the north arch viaduct at the minimum height over the lower deck (the crossing rule, 7.9 m over its highest rail: 174.5 m), climbing at 2.5% from the Deck's s 3,644, held to the hillside, then in the Floridian hillside tunnel at a constant grade to the portal at 39.157114 N, 84.566833 W, about 186 m. Blocks `Indianapolis and D upper deck` and `Floridian hillside tunnel`; the north arch viaduct ends at the hillside.
- `rer/alignments/RER_4.json`: RER-4's profile north of Camp Washington on that upper deck and tunnel (`tools/make_rer4_upper.py`; not saved in the page). The RER-4 configs name it.
- RER-2 and RER-4 from the trunk to Union Terminal follow the Mill Creek Deck's B/D route (`tools/repath_rer_bd_trunk.py`, from `data/deck/context.json`): the old KMZ line ran up to 237 m west of it. RER-2 c 7,040-11,570 became 4,717 m (+187.2 m past it), RER-4 c 6,966-12,842 became 6,061 m (+185.9 m). Arlington, Camp Washington, Straight, Western and (RER-4) Union Terminal at the Deck's station points; ground re-sampled; crossings recomputed (A now crosses B/D twice at the box); the saved RER-2 profile shifted. `rer/repath_bd_trunk.json` holds the chainage map. The configs still follow the KMZ track, so the designed core now covers about 2% less of each RER-2 / RER-4 route (the re-pathed stretch is more than 30 m from the KMZ line). Rerunning `tools/make_rer_profile_lines.py` would undo the re-path.

## Update prompt (2026-10-26)

> Pull the profiles-cut-norwood-context branch. data/profile was brought to the Rail Profiles page's state (README "CUT and Norwood Central context"): new context/lines.json, canon and settings changes, Line 3's Norwood end re-pathed, saved profiles re-exported. metro_profile.py now reads the context (Deck re-grades in the ground, painted cut-and-cover fill, context_clearances()). Run the tests and the Metro and RER configs, and report the run-time changes and the context clashes.
