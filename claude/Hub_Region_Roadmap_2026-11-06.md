# Hub rebuild roadmap: one design tool for the whole region (6 November 2026)

Branch `hub_region`. This supersedes the phase list in `Code_Handoff_Hub_Region_2026-11-05.md` section 9 and the
draft in `Hub_Region_Handoff_Review_2026-11-06.md` section 4. The handoff's goal, design rules (section 5) and the
conflicts kept as data (section 8) still apply. Ben's words: "I don't want cheap and easy, I want robust and useful."

## 1. What "robust and useful" means here

- **Useful**: a transit engineer opens one app, picks a line, a station or a service, changes something, and sees
  the score of that change (run time, rush-hour level of service, headway and loads) on the drawing within seconds.
  Every drawing is a standard engineering output: plan and profile on one stationing axis, cross-section, train
  performance chart, stringlines, blocking-time stairs, pedestrian level of service, quantities.
- **Robust**: one model, one copy of every rule, every input kept with its source and date, every result derived and
  cached by its inputs, every change versioned, every rule tested as an invariant over Ben's real data, and the whole
  thing rebuildable from git plus Ben's export in one command.
- **Streamlined**: built in vertical slices, each one usable on its own, each one retiring an old page, nothing built
  twice, nothing waiting minutes in the background.

## 2. Architecture

### 2.1 Layout of the repository

```
region/            Python: the model, the ground, the importers and exporters, the job graph, the API server
  model/           schema (numbered SQL migrations), entity classes, ids, versions, seeds
  ground/          the topography by year (built; this roadmap's slice 0)
  importers/       Deck, Profiles, hub export, KMZ, chronology, operations, rolling stock, Fountain Square, ...
  exporters/       seeds, KMZ, LandXML, CSV, railsim configs, glTF, sheets
  jobs/            the dependency graph, hashing, cache, workers, progress
  analysis/        railsim adapter, capacity, service and fleet, station flows, demand
  api/             FastAPI app: records, queries, SSE, tiles, downloads
engine/            TypeScript: the rules engine (geometry, levels, structures, checks); builds for the browser and Node
app/               TypeScript + Vite: the one web app (panes as modules)
rules/             registry.yaml: every rule with its ruling, status and priority
ground/            the ground layers (data) and reports
data/              the sources as today (kmz, deck, profile, operations, rollingstock, reference)
hub/               the old hub, kept running until every page is retired (slice 8), then removed
railsim/           the running-time physics (kept; its inputs change in slice 1)
tests/             Python tests; engine/tests for the TypeScript; app/tests for the browser
```

### 2.2 Storage

- One SQLite database `region.db` (WAL), schema in numbered migrations (`region/model/migrations/0001_*.sql` ...),
  applied on start, with a `schema_version` table. Geometry as WKB in EPSG:26916 with an R-tree index per spatial
  table (SQLite's `rtree` module, no spatialite). Shapely for geometry in Python.
- Every entity has an immutable ULID id, a `created`/`updated`, a `source` (file, chat, ruling id) and a `phase`
  and years where it is something built. Names are fields. A `legacy_key` table maps every old key (Deck station
  keys, profile station keys, chronology segment keys, Deck street ids) to the new id, so old records and Ben's old
  hub still resolve.
- Every write carries the version it was built on (`If-Match`); a stale write is refused, never merged silently.
  History is kept per record (not 50 versions: all, compacted monthly).
- Seeds for git: `region/seed/<table>/<id>.json`, sorted keys, one file per entity, derived tables never exported.
  `python -m region export` and `python -m region import --seed` are the only paths between git and the database.
  Ben's own database is never overwritten: import is a three-way merge against the last seed base, conflicts listed.

### 2.3 The model (entities)

| Entity | Holds |
|---|---|
| `node` | a junction, line end or stop point; one level shared by every section through it |
| `section` | one track section between two nodes: plan polyline, fitted plan elements (tangent, curve, spiral), track count and spacing, built phase and years, system, source; vertical controls keyed by offset from the section start and anchored to the nearest station or node |
| `track` | a track within a section (for shared trunks and station throats) |
| `route` | an ordered list of sections with directions (a Metro line, a TRI trunk or branch, an APEx route) |
| `service` | a route pair through the trunk, stopping pattern, mission code, headways by period, era, fleet |
| `station`, `stop`, `platform` | the complex; its stop per route; each platform's length, island or side, offset, grade, level, gap filler, selection |
| `station_element` | hall, passage, flight, lift, gate, entrance: level, outline, width, phase |
| `structure` | a range on a section with method and form (box, twin tube, bore, trough, viaduct, embankment, bridge), either solved by the engine (derived) or set by a ruling or paint (input) |
| `bridge` | a river or valley crossing as a parametric object (spans, piers, rail level, truss form), from the bridges page |
| `earthwork` | a pad, corridor or freeform work with years, timeline tag, or a raster layer from `ground/` |
| `ground_layer` | base surfaces by era and tier (1912 survey, today's LiDAR core, corridor, region) |
| `context` | other systems' tracks and structures, roads with class and level, rivers, Deck streets, blocks and plots (Deck-owned ids) |
| `era` | year ranges with fleet, signalling, rules and platform standards |
| `yard` | depots and leads with roles |
| `demand` | zones, population and jobs by era, trip tables, scenarios |
| `rule` | id, text, ruling (date, words, source), status ratified or unratified, priority (mirrors `rules/registry.yaml`) |
| `ruling` | a dated decision by Ben, the objects it governs |
| `version` | a named snapshot of the input records of a route, station or service plan, with a note |
| `result` | engine, input hash, engine version, output, time |
| `issue` | a check failure: rule id, severity, location (section and offset, or station and element), message |

### 2.4 Two engines, one contract

- **Rules engine (TypeScript, `engine/`)**: plan geometry fitting, vertical geometry (PVIs, vertical curves), the
  level solver, the structure solver (one method per stretch between anchors, Ben's inputs final), clearances and
  checks. One pure function `solve(input: SectionInput): SolvedSection`; no globals, no I/O, no DOM. Precomputed
  arrays on the 2 m grid. Every stretch and flag carries the rule ids it applied. Built with Vite for the browser and
  as a Node CLI (`node engine/dist/cli.js job.json`) for the hub's jobs and tests. Ported from the 4 November
  `solveTypes`, not written from zero.
- **Analysis engine (Python, `region/analysis/`)**: railsim (running time), capacity (blocking time, minimum
  headway, junction conflicts), service and fleet, station flows and level of service, demand. It reads solved
  sections and never re-derives a level or a structure.
- **Contract**: `SolvedSection` and `SectionInput` as TypeScript types, JSON schemas generated from them
  (`engine/schema/*.json`), validated in Python with pydantic models generated from the same schemas. Versioned;
  the engine version is part of every result's cache key.
- `railsim/metro_profile.py` (2,309 lines) is deleted in slice 2. The headless Chromium sync is deleted in slice 6.

### 2.5 Ground (built, slice 0)

`region/ground`: the canon 1912 ground is the base, every work after it a dated layer (raster today, parametric
`Pad` and `Corridor` from now on), composed on demand for a year and a timeline, with provenance per cell and cut
and fill volumes. See `ground/README.md`. Still to come in slice 0: the catalogue of post-1912 changes outside the
recorded works (the 615 km² where map 3 and 1912 differ by 0.94 m on average), the river level by era, corridor and
region tiers for the TRI, and the tile build for the map.

### 2.6 Jobs and cache

A dependency graph in `region/jobs/`: each job declares its inputs (record ids and versions, file hashes, engine
version) and its outputs. Keys are content hashes, so unchanged work is reused. A section edit re-solves that
section, then the services crossing it, then the trunk's capacity, then its issues; a platform edit re-solves that
station's flows; an era edit re-runs the services it touches. Workers run in threads with progress over SSE. Long
jobs (a ground tier build, a full demand run, a tile build) run in the background and never block editing. Budgets:
a profile edit re-solves in the page with no visible wait; a saved edit updates run times within 10 s; the region
map opens in under 5 s.

### 2.7 The app

One Vite + TypeScript app served by the hub. One selection, one era, one scenario, all in the URL
(`#route=B_trunk&s=12400&year=1985&scen=canon`). Panes:

| Pane | Shows | Edits |
|---|---|---|
| Region map (MapLibre) | every system with layers by system, structure, era and result; hillshade and 3D terrain from the ground tiles; the era slider; search | picks; draws and re-paths sections; draws earthworks; imports KMZ |
| Line sheet (canvas) | plan strip, profile with ground source, rail, structures, platforms, context and roads; curvature and speed limit; railsim speed curve and times; run-time table; where the time goes; issues; both directions | station levels, bend points, paints, locks, platform slides, drawn ground |
| Section | the cross-section at the cursor: ground, structure, clearance envelope, earthwork slopes | slopes, widths, walls by number |
| Station workspace (three.js) | plan per level, section, 3D of the station and the structures round it; flows as heatmaps; transfers; step-free routes; digging index | halls, passages, flights sized from their rise, lifts, gates, entrances |
| Service view | stringlines, blocking-time stairs, minimum headway per section, junction conflicts, fleet and cycle times, loads | patterns, headways by period, missions |
| Tables | stations, sections, structures, earthworks with volumes, yards, services, rulings, statistics; CSV | inline fields |
| Issues | every check failure in the region with severity, rule and ruling; click to go there | none |
| Compare | two versions side by side with every score diffed | none |

Usability: edits where you see them; every edit shows its score change; undo and redo; named versions; nothing runs
silently for minutes; units switch m and ft; Ben's terms throughout; a chainage readout everywhere; editing by
numbers (R 450 m, 3.5 %).

### 2.8 Tiles

Static layers (Deck streets, blocks and plots, Sanborn imagery, OSM extract, canon highways, rivers, terrain) are
built into PMTiles by a hub job (tippecanoe for vectors, a Python writer for raster terrain-RGB) and served with HTTP
range requests. Live model layers come from the API as GeoJSON by bbox and era.

### 2.9 Import and export

Importers, each with a round-trip test: the Deck layout and files; Profiles alignments, lines, `rer/*` and the
context; Ben's hub export; the KMZ (outside the Deck region and for re-paths, with levels carried across by
geometry); chronology, operations and rolling stock; the Fountain Square model; the `Elevation\` profiles; APEx, ORR
and TRIMET; highways and rivers; the ridership tables; the bridges page parameters.

Exporters: seeds; KMZ with levels and structures; LandXML alignments; CSV; railsim configs; glTF and PNG;
plan-and-profile sheets as PDF or PNG.

### 2.10 Verification, as a system

- **Unit tests** for every engine function and every importer (Python: pytest; TypeScript: vitest).
- **Golden tests**: every saved route on Ben's export solved under Node and compared with committed goldens; a
  change in a golden must cite the rule id and ruling that changed it.
- **Invariant tests**: every rule in the registry run over every route on Ben's export and on the repo seed
  (paints final, one method per stretch, box roof and cover, tube cover, platform standards, clearances, grades by
  era, street openings, side platforms on bored stretches, shared-stretch levels, branch clashes, yard overlaps).
- **Calibration gates**: the MBTA Orange Line (35.8 min model against 35 min scheduled) and Needham (38.0 against
  40) as tests with a ±1 % regression tolerance on the model's own baseline, and a reported ±3 % per segment against
  the published times.
- **Round-trip tests** for every importer and exporter.
- **Browser tests** (Playwright): each pane loads, a selection in one pane moves the others, an edit shows its score.
- **Performance budgets** as tests: page open, re-solve, run-time update, map open.
- **Rule coverage**: a test fails on any engine branch that emits no rule id.
- **Reproducibility**: `python -m region rebuild` from git plus Ben's export gives byte-identical seeds and goldens.

## 3. Working practice

- Before any session's build: Ben runs `python hub\hub.py export` (old hub) or `python -m region export` (new) and
  pushes; the session works from that. His database is never overwritten; imports merge with a backup.
- Every slice ends with: exit tests passing, a report in plain language with numbers, the rulings used (provisional
  ones listed), a log row in `claude/Hub_Region_Log.md`, and a push. Then stop.
- Rulings come from chat as records in `rules/registry.yaml` and the `ruling` table, through the seed.
- Canon is never changed by code. A rule's meaning never changes without a ruling; a changed effect is reported.
- `tools/sanborn`, `data/sanborn` and the Deck's tiles and street data stay untouched while the Sanborn run is open.
- Project skills in `.claude/skills/` (export before build, rebuild and compare, take a handoff from chat) and a hook
  that runs the invariant tests on engine or schema changes.

## 4. Slices

Each slice: what it builds, what Ben can use at its end, the exit tests, the rulings it needs. Sizes are in Claude
Code sessions of the kind run so far.

### Slice 0: foundations and topography (in progress; 2 to 3 sessions)

Built so far: `ground/` consolidated, map 3 moved, `region/ground` with the compositor, parametric works, sampling,
CLI, tests and the whole-extent check.

Remaining:
- `region/model`: the schema migrations for every entity in 2.3, ids, versions, seeds, the legacy-key table.
- `rules/registry.yaml`: every rule in `data/profile/README.md` and the code, each with its ruling or "unratified"
  and a priority; the rulings so far as records.
- The baseline: every route's solved rail level every 5 m and structure types from the current page, every railsim
  run time, the 3D issues, committed under `tests/baseline/`.
- The calibration gates as tests on today's railsim.
- Topography: the catalogue of post-1912 changes outside the recorded works (patches over 2 m and 1 ha, each with
  area, mean change, location, a candidate name and era); the river level by era; the bridges page's geometry as
  `bridge` and `earthwork` records (the C&O and Cincinnati Southern bridges, the quad-track viaduct, the Covington
  approach, with the wall-below-the-track fix); the corridor and region ground tiers from Ben's local DEMs;
  terrain tiles for the map.
- The app shell: Vite project, the API server skeleton (FastAPI), SSE, the URL state, one empty pane.

Usable at the end: the ground for any year as rasters, samples and volumes; the catalogue to rule on.

Exit: migrations apply to an empty database and to a seeded one; the registry lists every rule the page applies
and every rule has a test stub; the baseline is committed; the gates pass; the catalogue is committed with a report;
the bridges reproduce the page's facts table from the records.

Rulings needed: the catalogue threshold; the 1912 river level; which river bed is canon; the undated works.

### Slice 1: Line 6 end to end (3 to 4 sessions)

- Import Line 6 only: Deck pieces, the Profiles doc, the line file, the ground (now from `region.ground`).
- The engine lifted to TypeScript on Line 6: geometry, level solver, structure solver from the 4 November engine,
  checks with rule ids. The contract schemas. Node CLI. Golden test on Line 6.
- railsim reads the solved section (a new `railsim/route_from_solved.py`), with a "where the time goes" table
  (marginal seconds per restriction, the phase split) and the calibration gates unchanged.
- The job graph for section → solve → run time → issues, with the cache.
- The line sheet pane: plan strip, profile, structures, speed against limit, run-time table, where the time goes,
  issues, both directions; edit a station level or a bend point and see the time change.
- Line 6's cuttings and embankments generated as corridor earthworks from the solved section (phase-dated), visible
  on the ground and in the volumes.

Usable at the end: Line 6 designed and scored in the new app, on the real ground model.

Exit: inputs lossless (every field Ben set survives import and export); output diff against the baseline with zero
unexplained differences (rule fixes listed with ids); Line 6 run time within 1 % of the baseline or explained; an
edit updates the run time within 10 s; the gates pass; browser test of the edit loop.

Rulings needed: the TypeScript engine and FastAPI confirmed (ruled 6 November by the branch choice; confirm); any
rule the diff report shows as changed.

### Slice 2: every Metro line; the Deck adapter; the Profiles page retired for Metro (3 sessions)

- Import the 17 Metro routes, Lines 10, 11 and 13 from their defaults, CVG Express; stations as complexes with
  stops; platforms with the era standards (400 ft Metro); the chronology as phases and years on sections and
  stations; the context (CUT, Norwood, roads) as context records.
- The invariant tests over every Metro line on Ben's export.
- The `deck/layout` two-way adapter: platform moves and station cards reach the model and back; every Deck street id
  survives.
- `metro_profile.py` deleted; railsim reads solved sections for every Metro config.
- The Profiles page retired for Metro; the old hub keeps running for TRI and the Deck.
- Line-to-line crossing clearances from solved types, not depth guesses.

Exit: every Metro line has a sheet both ways; every rule holds as an invariant over every line or is listed as a
flagged exception; the Deck's platform moves round-trip; the baseline diff for every line has zero unexplained
differences; 3D snapshot issues from the old build are reproduced or explained.

Rulings needed: the rule fixes the diffs show; the tunnel-method rules' ratification (the registry shows each as
unratified until then).

### Slice 3: the TRI region (3 to 4 sessions)

- Corridor (2 m, ±250 m) and region (10 m) ground tiers from Ben's USGS DEMs and LiDAR, built once, local, as
  COGs; no internet in any run.
- Outer sections from the KMZ beyond the Deck region, nodes at the Deck-region seams (seam report at 5 m), shared
  trunks as nodes with one level (r07), the D/E lettering as data (section 8 of the handoff).
- The 25 lettered TRI routes and the 31 current services (and the 24 pre-RER) as routes and services; platforms at
  670 ft; the RER canon locks as rulings.
- The Profiles page retired; the old hub serves only the Deck.

Exit: every TRI service runs with no internet and no flat fallback; every seam listed; the RER sheets both ways;
run times within 1 % of the baseline or explained.

Rulings needed: the region box (lean: TRI extent plus 5 km); the D/E lettering; the Union Terminal dive-under (r06)
and Line 14 at Norwood (r08) stay design work for Ben in the sheet.

### Slice 4: the region map, eras, structures, issues, tables (3 sessions)

- MapLibre with the PMTiles build (Deck streets and plots, Sanborn, OSM, highways, rivers, terrain) and the live
  model layers; the era slider; search; draw and re-path sections; draw earthworks (pad, corridor) on the map with
  the Section pane for slopes and the 3D view for the result.
- Structures region-wide: viaducts, bridges (the bridges page's objects, the viaduct fix), embankments, boxes,
  tubes, with the structure sizes and costs by phase from `metro_structure.json`; quantities (box, bore, fill metres,
  cut and fill volumes) in the tables.
- The issues pane and the tables; the Chronology and Access pages retired (the era slider and the station table
  take their jobs); the Deck keeps streets and plots only.

Exit: the region opens under 5 s; any year 1905 to 2026 draws the network and the ground as built; every check
failure is listed and links to its place; an earthwork drawn on the map changes the profile, the section, the 3D
view and the volumes.

Rulings needed: the Deck's role confirmed (streets and plots only); the catalogue's works dated.

### Slice 5: the network loop (3 sessions)

- Services, patterns, missions and headways by period; timetables generated from them.
- Blocking time per section from the signalling era (fixed block: approach, occupation, release; CBTC and moving
  block from braking distance); minimum headway per section; junction conflicts from overlapping blocking times;
  fleet and cycle times.
- The service view: stringlines, blocking-time stairs, headway against planned headway on each trunk (A/D, B/D, the
  B/C/E CVG stretch, CUT), fleet.

Exit: the trunk headway check runs for every trunk in every era; the fleet per line and era is tabled; the Orange
Line and Needham gates still pass.

Rulings needed: the signalling by era where `data/operations` is silent; the mission codes.

### Slice 6: the station loop (4 sessions)

- Station elements; Fountain Square imported from `fs_model.py`; the walking graph (from `fs_reach.py`),
  reachability, step-free routes, decision points.
- Peak flows from the v17 tables Ben supplies, assigned by quickest path with capacity penalties; level of service
  per element from the Fruin thresholds as printed in TCQSM (looked up and cited in the registry); the digging index
  from the earthwork volumes and the structure costs; NFPA 130 platform clearing (4 and 6 minutes, the standard's
  egress rates).
- The station workspace: plan per level, section, 3D of the station and the structures round it rebuilt from the
  model; the headless sync and `tools/station3d/sync.py` deleted; the old 3D page retired.
- Then CUT, then every station with a complex.

Exit: stacked, spread and half-stacked layouts at Fountain Square compared on one screen with every score; the
Fountain Square reachability check reproduces `fs_reach.py`'s result; the 3D view agrees with the sheet on every
line within 1 cm.

Rulings needed: the Fountain Square platform length (500 ft in the model against 400 ft in the editors); the stacking
decision itself, on the evidence.

### Slice 7: demand and statistics (3 sessions)

- The ridership model in the repo: the v17 scripts recovered, or rebuilt from the project docs to v17's totals
  (8,120,167 rail trips a weekday, canon); run by era and scenario; loads to the network loop; flows to the
  station loop.
- The statistics tables (r22) and the compare pane across versions and scenarios.

Exit: v17's weekday totals reproduced within 0.5 %; loads on the map and the stringlines; every pane compares two
versions.

Rulings needed: the scenarios to keep (canon, Paris-region).

### Slice 8: hardening and retirement (2 sessions)

- The old hub removed; `hub/` deleted except what the Deck still needs, which moves under `region/`.
- Exporters complete (KMZ, LandXML, CSV, sheets as PDF, glTF).
- Performance budgets as tests; the reproducibility test (`python -m region rebuild`); the project skills and hooks;
  the README rewritten for the new tool; a migration note for Ben's machine.

Exit: a fresh clone plus Ben's export rebuilds everything byte-identical; every budget passes; no page left from the
artifacts.

## 5. Roadmap r00 to r23 against the slices

| Roadmap item | Slice |
|---|---|
| r00, r01 | replaced by the model and the job graph (1) |
| r02 shared parameters, r03 anchored profiles, r04 normalised tables, r09 phase on everything, r15 extension phases | 1 and 2 |
| r07 shared-stretch levels, r11 CVG Express not in the Deck, r12 lines past the Deck region | 3 |
| r05 branch clashing, r14 side platforms on bored stretches, r16 box roof at Evans, r17 yard flags, r13 platform lengths | checks in 2 and 3, listed in 4 |
| r06 Union Terminal dive-under, r08 Line 14 at Norwood | Ben's design work in the sheet from 3 |
| r10 phase slider | 4 |
| r18 fact tracker canon update | a chat session; the conflicts stay as data |
| r19 railsim tab, r23 run times on the Profiles | 1 |
| r20 service plan and fleet | 5 |
| r21 ridership model, r22 statistics | 7 |

## 6. Risks and how each is handled

| Risk | Handling |
|---|---|
| The engine port drifts from the page's behaviour where Ben's lines depend on it | the baseline diff per route with zero unexplained differences; goldens; rule ids on every change |
| Ben's edits in his old hub diverge from the model during the transition | one source at a time: a page is retired only when its pane replaces it, and the old hub's export is the import until then |
| The Sanborn migration and the rebuild collide on the Deck | the Deck's files and ids are read-only to the rebuild; only `deck/layout` platforms and station cards cross the adapter |
| Rasters outgrow git | the ground tiers for the TRI live outside git with a manifest; the core layers stay in git under 25 MiB per file |
| Memory and time on big composites | tiles of 1 km, jobs keyed by hash, background builds with progress |
| Standards figures (Fruin, NFPA 130) wrong from memory | looked up and cited in the registry before use; shown as unratified until Ben confirms |
| Scope: eight slices is a long road | each slice is usable and retires a page; the order can change after any slice without rework |

## 7. Rulings so far (6 November)

- Branch `hub_region`; map 3 moved to `ground/2026/`; the 1912 ground, works, zones and ledger under `ground/`.
- The ledger's missing years stay `null`.
- The river bridges page and the C&O and intercity viaducts are part of the implementation; the viaduct's walls are
  drawn above the track and must be below it.
- Open: the catalogue threshold; the 1912 river level; which river bed is canon; the undated-works default; the
  handoff's section 11 leans (region box, D/E lettering, geometry master, the Deck's role, the engine language, now
  TypeScript).
