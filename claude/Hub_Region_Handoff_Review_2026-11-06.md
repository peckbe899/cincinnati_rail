# Review of the hub-region handoff, with changes proposed (6 November 2026)

Read for this review: `claude/Code_Handoff_Hub_Region_2026-11-05.md` (the handoff), the "Sanborn GeoTIFF deck artifact" chat
export (31 October to 5 November, where the handoff was written), and the repo files the handoff's section 3 names:
`hub/*`, `hub/static/shim.js`, `data/profile/README.md`, `profiles.html`, `railsim/*`, `tools/station3d/*`,
`stations/fountain_square/*`, `data/deck/*`, the four audits, `docs/research/simulators.md`, `docs/CALIBRATION.md`,
the roadmap r00 to r23, and the OSRD repository (schema and front-end layout). Numbers below were counted in the repo
on this branch (`claude/stoic-cray-fqf881` at d3ee3e2).

## 1. What the handoff gets right

Keep all of this: one model with stationing along sections; each rule written once; Ben's inputs as constraints that are
flagged, never overridden; one decision per stretch; tests as the product (run time, rush hour, capacity); region-wide
by default with the ground stored locally; the three loops; the conflicts in section 8 kept as data; Line 6 first.

## 2. Changes proposed

### 2.1 Build in vertical slices, not layers

The handoff's phases are horizontal: Phase 1 imports everything and lifts the engine, Phase 2 rebuilds the ground and
the job graph, and the first thing Ben can use (the Line 6 sheet with run times) is Phase 3. That is the pattern that
produced the hub: a lot of plumbing, no test at the end.

Change: slice 1 is Line 6 end to end (model, import of Line 6 only, the engine on Line 6, railsim reading the solved
section, the line sheet with run time and "where the time goes"). Every later slice widens it. Section 4 has the order.

### 2.2 Baseline the inputs, not the output

Phase 1's exit ("every saved profile reproduces its baseline rail level within 1 cm and its structure types exactly")
makes the new engine reproduce the 3,944-line page faithfully, including the defects in the four audits (two answers
from `typeAt` and `solveTypes`, four copies of the point-type rule, the per-sample thresholds).

Change: two separate tests.
- Inputs lossless: every field Ben set (`st`, `pvi`, `sg`, `so`, `del`, `ovr`, `stt`, `tf`, `shafts`, `gnd`, `gapfill`,
  `mode`, the Deck's platform moves and station cards) survives the import and the export back, value for value.
- Outputs by diff: for every route, a report of rail level and structure type against the baseline, each difference
  classed as "same", "rule fix" with the rule id and ruling, or "unexplained". Unexplained must be zero before the
  slice closes. Ben reads the rule-fix list once and signs it off.

### 2.3 Every entity gets an id that never changes

Today the joins are names and coordinates: Deck stations `metro:Syacmore:715445:4331182` (the typo is in the key),
profile levels keyed `Cincinnati State#2`, chronology segments `metro|Line_1|8th|Lincoln Court`. A rename or a move
breaks the join, which is why the Chronology lists "orphans" and why r03 exists.

Change: immutable ids (ULIDs) on sections, nodes, stations, platforms and elements; names are fields. The importer
writes a legacy-key table (old key to new id) so Ben's hub records and future exports from his old hub still resolve.
Street and plot ids from the Deck are frozen as they are (the Sanborn pipeline depends on them).

### 2.4 The rules engine: TypeScript, one pure function, grid arrays, no globals

The handoff says "one JavaScript module". Sharpen it, because the page's rule code (profiles.html 601 to 2275) is
DOM-free but reads the globals `S`, `settings`, `MS`, `CANON`, `CONTEXT`, `LINKS`, `METRO_ST` and caches by object
identity (`VERTS._types`, `memo`/`MODEL_V`).

- `solve(input: SectionInput): SolvedSection`, with everything it reads passed in. Deterministic. No I/O.
- TypeScript: the Python copy's samples are "dicts with string keys and sentinels; nothing checks spelling" (Code Audit).
  Types fix that for free, and the contract JSON schema is generated from the same types.
- Precomputed arrays on the 2 m grid (`rail`, `grade`, `phase`, `type`, `struct`, `tube`) instead of per-sample
  functions (the audit's improvement 4).
- Start from the 4 November engine (`solveTypes` 1360 to 1604, anchors and one method per stretch), not from zero.
  It is the only part of the page that already works the way the handoff wants.
- Run under Node from Python (`node engine/cli.js job.json`), replacing both `metro_profile.py` and the headless
  browsers. `metro_profile.py` (2,309 lines) is deleted at the end of slice 2, not kept as a wrapper.
- Golden tests: every saved route on Ben's export, solved under Node, compared with committed goldens.

### 2.5 The rule registry is code, not a document

Drive_Selection root causes 1 and 2 (no ratified rule; inputs overridden by pass order) do not go away by writing
rules in a markdown table.

Change: `rules/registry.yaml`, one entry per rule: id, text, ruling (date, Ben's words, source), status ratified or
unratified, priority. The engine tags every stretch and every flag with the rule ids it applied (the 4 November engine
already writes a "note" per stretch; make it ids). A test fails on any engine branch that emits no rule id. The UI
shows an "unratified" chip on any result that depends on one. Ratifying a rule is then a one-line edit by a chat
session, through `hub/seed`.

### 2.6 Versions are input snapshots, not copy-on-write overlays

Section 6.1's `scenario` as "a named overlay (copy on write) on any record" is the hardest part of the schema to get
right, and the hub's existing merge already has edge cases (it drops null-valued keys; conflicts keep the local value
silently).

Change: a version is a snapshot of the input records of one route, station or service plan (a few hundred KB at most),
with a name and a note. Results are cached by the hash of the inputs plus the engine version. "Compare" runs both and
diffs the scores. This gives stacked against spread at Fountain Square, and Line 6 before and after a regrade, with no
overlay semantics.

### 2.7 One job graph, keyed by content hash and engine version

As in the handoff, with two additions: the engine version is part of every cache key (so an engine fix invalidates
exactly what it should), and results are stored per section, so editing one section of a 30-section TRI trunk
re-solves one section and re-runs only the services that cross it.

### 2.8 Ground: local only, as cloud-optimised GeoTIFFs; the map's terrain as PMTiles

railsim still fetches from the internet by default: USGS EPQS point queries, the AWS Terrarium tiles and the USGS
LiDAR S3 listing (`railsim/elevation.py` 37, 170, 250). The B line took 141 s and fell back to flat for that reason.

Change: one ground service in the hub with three tiers as in section 6.4, stored as COGs (rasterio reads windows), and
a `ground.sample(section)` call that every engine input goes through. Internet sources stay only behind an explicit
`--online` flag for building the tiers. For the map, the region tier is also written once as terrain-RGB raster tiles in
one PMTiles file for MapLibre hillshade and 3D terrain.

### 2.9 Map: PMTiles for the heavy static layers, plain GeoJSON for the live model

The Deck pulls about 10 MB of JSON on open (`basin.json` 2.2 MB, `plots.json` 3.3 MB, `context.json` 1.9 MB, plus the
rest). Region-wide the live model layers (1,656 km of line, about 600 stations, structures) are a few MB and change on
every edit, so they stay as GeoJSON from the API, filtered by bbox and era. The static layers (Deck streets, blocks and
plots, Sanborn imagery, OSM extract, canon highways, rivers) are built into PMTiles once per change by a hub job
(tippecanoe, or the Python `pmtiles` writer) and read by MapLibre with HTTP range requests. Then the region opens in
under 5 s without a tile server.

This needs the hub to answer HTTP Range requests, which the stdlib handler does not (see 2.10).

### 2.10 Server and front end

- Server: Python, SQLite with a versioned schema, but move from the stdlib `BaseHTTPRequestHandler` to a small ASGI
  framework (FastAPI or Starlette with uvicorn): SSE, Range requests, request validation from the contract schemas
  and an OpenAPI description for the front end come built in. The dependency is small next to rasterio and shapely,
  which the hub already needs.
- Front end: one Vite + TypeScript app, panes as modules, the engine as a shared package. No more single 360 KB
  files served through a shim that imitates the artifact runtime.
- Live updates carry the record, not just its path: today each SSE event makes every open tab refetch the doc and its
  whole collection (`shim.js` 56 to 59).

### 2.11 Run the old hub beside the new one; one adapter, not five

Section 6.6 has the new hub serve every old record (`alignments/<id>`, `deck/layout`, `config/*`, `chronology/*`,
`params/*`, `snapshots/region`) as generated views, with writes translated back. That is five adapters to write and
test before anything new works.

Change: the new hub is a second process on its own port (`region.db`), loaded from Ben's export. The old hub keeps
running on `hub.db` until each page is retired. Only `deck/layout` gets a two-way adapter, because the Deck stays as
the street and plot editor and its platform moves must reach the model. The Profiles, 3D, Chronology and Access pages
are read-only references until their replacement pane exists, then switched off.

### 2.12 railsim: calibration gates that exist, time attribution, blocking time

Section 7 says the Orange Line and Needham runs "are kept as reference services" and that a change "beyond their
tolerance fails the tests". Today there is no tolerance and no test: `docs/CALIBRATION.md` has no pass/fail, and
`tests/test_core.py` has no Orange or Needham check. The survey's "about ±3% per segment" is marked [K]/[EST] there,
not verified.

Change:
- Gates as tests: Orange Line 35.8 min model against the GTFS 35 min, Needham padded 38.0 against 40; regression
  tolerance ±1% on the model's own baseline, and a reported (not failing) ±3% per segment against the published times.
- "Where the time goes": marginal seconds per restriction, computed by re-running the route with each curve, grade,
  turnout or signal restriction relaxed, plus the phase split (accelerating, cruising, braking) the survey recommends.
- Blocking time per section from the era's signalling record (`data/operations/*.yaml` already has lineside, cab with
  300 m blocks, CBTC, GoA3): fixed block as approach plus occupation plus release; moving block from the braking
  distance. Minimum headway per section follows from the stairs; junction conflicts from overlapping blocking times.
- railsim's route comes from the solved sections: the KMZ reader, `LocalProjection` and the horizontal re-fit stay
  only for the import job.

### 2.13 The station loop: static assignment, standard thresholds

A flow model, not walkers (as the 26 October chat concluded): a walking graph from the elements, peak-hour trips
assigned by quickest path with capacity penalties and a few iterations. Level of service per element from the Fruin
thresholds as printed in TCQSM 3rd edition (the exact numbers were not reachable from this session; look them up and
cite them in the registry, as the handoff asks). NFPA 130: platform cleared within 4 minutes, point of safety within
6 minutes, with the standard's egress rates per unit width (same note). Reuse `fs_reach.py`'s graph build and checks.

### 2.14 Export for git

`hub/seed` today exports derived records too (`params/tube_points` 2 MB, `station_access_rule` 290 KB, `registry`).
Change: one file per entity id, sorted keys, derived records never exported, so a diff on GitHub reads as what Ben
changed.

### 2.15 Project skills and hooks for later sessions

`.claude/skills/` for "export the hub before a build", "rebuild and compare", "take a handoff from chat", and a hook
that runs the invariant tests when the engine or the schema changes. Cheap, and it puts the rules where every session
reads them.

## 3. Corrections to the handoff's facts

- Section 7 and Phase 2 exit: there is no calibration tolerance or test today (2.12 above). Write one in slice 1.
- Section 2.4: the ±3% validation figure is the survey's own estimate ([K]/[EST]), not something it verified.
- Section 2.2: `profiles.html` is 3,944 lines now; the 31 October audit counted 3,250. The 4 November rewrite
  removed the cost sums, pockets, leftover conversion and the dead band, so the engine to port is smaller and cleaner
  than the audits describe.
- The railjson structure in OSRD (checked in the repo): track sections carry a length and ranges for slopes, curves
  and loading gauge; operational points are parts positioned by offset on a track section; routes are lists of
  waypoints; signals and speed sections are positioned objects. That is the section/node/offset model of section 6.1,
  so the handoff's lean is sound. Its front end has `SpaceTimeChartWrapper`, `SpeedDistanceDiagram`, `Chronogram` and
  `SimulationResultsMap` as the four result views: the same four the line sheet and service view should give.

## 4. Draft gameplan (vertical slices; each ends with exit tests, a commit, a push and a report)

| Slice | Builds | Exit |
|---|---|---|
| 0. Baseline and scaffolding | Branch; Ben's export committed; baseline captured (rail every 5 m per route from the current page, every railsim run time, the 3D issues); `region/` package skeleton with the schema and migrations; `rules/registry.yaml` from `data/profile/README.md` and the code, each rule ratified or unratified; the rulings table with the section 11 leans marked provisional; calibration gates written as tests on today's railsim | All committed; the registry lists every rule the page applies; the gates pass on today's code |
| 1. Line 6 end to end | Section, node, route, station, platform, era and ruling tables; import Line 6 (Deck pieces, Profiles doc, line file, ground); the engine lifted to TypeScript solving Line 6; the solved-section contract; railsim reading it; the new app shell with the line sheet (plan strip, profile, speed against limit, run-time table, where the time goes, issues); one PVI edit shows its time change | Inputs lossless; output diff report with zero unexplained; Line 6 run time within 1% of baseline or explained; an edit updates the run time within 10 s; gates pass |
| 2. All Metro lines; the Deck adapter | Import the 17 Metro routes; invariant tests over every line on Ben's export; `deck/layout` two-way adapter for platforms and station cards; `metro_profile.py` deleted; the Profiles page retired for Metro | Every Metro line has a sheet both ways; every rule tested as an invariant over every line; the Deck's platform moves reach the model and back |
| 3. The TRI region | Corridor and region ground built locally as COGs; outer sections imported from the KMZ with nodes at the Deck-region seams (seam report at 5 m); shared trunks as nodes with one level; all 31 current services run offline; the Profiles page retired | No internet access during any run; no flat fallback; every seam listed; the RER sheets both ways |
| 4. Region map, eras, issues, tables | MapLibre with PMTiles for the static layers and GeoJSON for the model; era slider; the issues pane with links; the tables with CSV; the Chronology and Access pages retired; the Deck keeps streets and plots | Region opens under 5 s; any year 1905 to 2026 draws the network as built; every check failure listed and linked |
| 5. The network loop | Services, patterns, missions, headways by period; timetables; stringlines; blocking time by signalling era; minimum headways; junction conflicts; fleet and cycle times | Trunk headway checks for A/D, B/D, the CVG stretch and CUT in each era; fleet per line and era tabled |
| 6. The station loop | Station elements; Fountain Square imported from `fs_model.py`; walking graph, reachability, step-free, decision points; peak flows from the v17 tables; LOS, digging index, NFPA 130; 3D rebuilt from the model; the headless sync retired; then CUT | Stacked, spread and half-stacked Fountain Square compared on one screen with every score |
| 7. Demand and statistics | The ridership model in the repo by era and scenario; loads to the network loop, flows to the station loop; statistics tables | v17 weekday totals within 0.5%; loads on the map and the stringlines |

Each slice is one to three Claude Code sessions. Slices 5 and 6 can swap if Fountain Square matters more than headways.
The Sanborn migration (`tools/sanborn`, `data/sanborn`, `hub/sites/deck` tiles and street data) is untouched throughout.

## 5. Decisions needed before slice 0

1. Branch. The handoff says `hub-region`; this session is bound to `claude/stoic-cray-fqf881`. Either name is fine;
   say which.
2. The baseline rule in 2.2 (inputs lossless, outputs by signed-off diff) in place of the 1 cm reproduction.
3. TypeScript for the engine and a Vite app for the front end (2.4, 2.10), and FastAPI or Starlette for the server.
4. Two hubs side by side with one adapter (2.11), instead of generated views of every old record.
5. The five open rows in the handoff's section 11 (region box, D/E lettering, geometry master, the Deck's role, the
   engine language). The leans there are all fine; row 5 becomes TypeScript.
6. Slice order: Line 6 first, as the handoff leans, then Metro, TRI, map, network, station, demand.
