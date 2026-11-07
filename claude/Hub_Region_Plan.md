# The hub rebuild: the plan in full

Written 7 November 2026 on branch `hub_region`, for scrutiny as a whole. It is self-contained: everything a reviewer
needs to judge the plan is here, with numbers where they exist. The companion files hold the working detail and are
cited where they add something: `Hub_Region_Roadmap_2026-11-06.md` (architecture), `Hub_Region_Checklist.md` (the
living board with options and leans per item), `Code_Scrutiny_2026-11-06.md` (the old code, function by function),
`Hub_Region_Handoff_Review_2026-11-06.md` (the critique of the 5 November handoff), `ground/1912/SPEC.md` (the model
handoff contract), `rules/registry.yaml` (the rules), `STATUS.md` (right now).

Contents: 1 Goal. 2 Where we start. 3 Design rules. 4 The model. 5 Ground. 6 The engines. 7 The app. 8 Jobs and
cache. 9 Import and export. 10 Verification. 11 Working method. 12 Slices. 13 Status. 14 Risks. 15 Decisions.
16 Not doing. 17 Open rulings. 18 Defects that must not come back. 19 Glossary.

---

## 1. Goal

One design tool for the Cincinnati Rail project that a transit engineer would use: every Metro line, every TRI (RER)
line and branch to its termini, the other systems (APEx, ORR, Transvalley, the TRR tier, historic TRIMET) as context
and shared track, every era from 1905 to today. It is built around tests at three scales, each with a build mode,
a test, and a score drawn on the design:

| Scale | Build | Test | Score on the drawing |
|---|---|---|---|
| Line | plan and profile, structures, platforms, earthworks | the rules engine solve, then railsim on every service using the line, for the chosen era | run time per segment and end to end both ways; seconds lost per curve, grade, turnout and signal; checks; box, bore, cut and fill quantities |
| Station | halls, passages, flights, lifts, gates, entrances on their levels | a walking network loaded with peak flows, assigned by quickest path with capacity | level of service per element; transfer times; step-free routes and their penalty; decision points; digging index; platform clearing time |
| Network | services, patterns, missions, headways, eras | timetables built from the patterns; blocking time per section by signalling era | stringlines; minimum against planned headway on each trunk; junction conflicts; fleet; loads and peak load points |

"Robust and useful" (Ben, 6 November) means: one model, one copy of every rule with its ruling, inputs kept with
source and date, results derived and cached, every change versioned, every rule tested as an invariant over Ben's
real data, and the whole thing rebuildable from git plus Ben's export in one command. Every quantity an engineer
would expect (chainage everywhere, editing by numbers, standard sheets) is a requirement, not a nicety.

## 2. Where we start

### 2.1 The region

Measured 5 November 2026 in EPSG:26916: TRI drawn extent 146.9 by 143.7 km (Dayton Airport to Williamstown,
Greensburg to Wilmington); Metro 40.8 by 30.7 km; the Deck region 37.9 by 26.2 km (993 km², 4.7 % of the TRI area);
1,655.5 km of drawn line (Metro 370.8 in 33 pieces, TRI 1,284.7 in 51); 592 distinct station names, about 600
stations; 17 Metro and 55 TRI railsim configs (31 current services, 24 pre-RER). A full Line 6 run takes 2.9 s; a
TRI run from Dayton Airport to Falmouth took 141 s, nearly all of it fetching ground from the internet, and fell back
to a flat profile when the fetch failed.

### 2.2 What exists

- **The old hub** (`hub/`): a stdlib Python server on one SQLite database serving the four artifact pages unchanged
  (the Deck 2,840 lines, the Profiles 3,944, Station 3D 1,180, Chronology) through a shim that imitates the retired
  artifact runtime; ties run as batch jobs on save; the 3D rebuild runs two headless browsers for about 143 s.
- **railsim** (`railsim/`): the running-time physics, calibrated on the MBTA Orange Line (35.8 min model against 35
  scheduled) and Needham; driver profiles, signalling presets, adhesion, eco allowance, Monte Carlo. No blocking
  time, no time attribution.
- **The Profiles engine** in the page: vertical geometry, a level solver, a tunnel-method solver rewritten on 4
  November (anchors, one method per stretch, a ranked list), checks; a hand-kept Python copy of all of it
  (`metro_profile.py`, 2,309 lines) for railsim and tests.
- **The Deck**: streets, blocks and plots from the 1904 and 1922 Sanborn plates (basin 5,204 features, 32,464
  plots, 386 sheets, the 0.25 m tiles), Ben's edits keyed by id, transit lines and platforms drawn from settings.
- **Ground**: LiDAR; map 3 (the 2026 canon ground: LiDAR cleaned of buildings, canon interstates, the Embankment,
  the deck, Lunken, the Kentucky terraces, the river beds, baked once in a chat); the Deck's regrade; per-line drawn
  ground; context runs. Now also `ground/`: the canon 1912 surface (I4 method) and every canon work as a layer with
  a ledger.
- **Design data**: 43 saved alignments, the chronology (556 segments), operations and rolling stock by era, canon
  records, the Fountain Square model (halls, flights, lifts as Python), the river bridges page (parametric C&O and
  Cincinnati Southern bridges, the quad-track viaduct, the Covington approach).

### 2.3 What went wrong (the faults the plan is built against)

1. The chain lost its end: run time, the point of the first tools, never reached the hub; every edit ended in a
   two-minute rebuild with no score.
2. The line was three things (Deck pieces, Profiles paths, KMZ), joined by chainage maps that broke on re-paths.
3. The rules existed three times (page, Python copy, headless sampling), kept in step by hand; four disagreeing
   "what structure is this point" rules inside one page; about 200 numeric literals in the solver.
4. Ben's inputs were inputs to a stack of about fifteen passes, so later passes overrode paints and selections;
   decisions were per 2 m sample on raw ground with hard thresholds; stations decided apart from their line.
5. Keys made of names and coordinates (`metro:Syacmore:715445:4331182` carries its own typo); plot ids that depend
   on replay order; whole-document saves; derived files committed; events that refetch everything.
6. Dates in code, so a timeline change unravelled; the ground a frozen bake nobody could rebuild; the "1912"
   surface actually LiDAR at every scale above 30 m (measured: correlation 1.00, zero shift).
7. Verification checked page-against-port parity, not Ben's rules over his data; Ben's live profiles were never
   under test.
8. Everything beyond the Deck region (95 % of the TRI area) was a KMZ with fetched ground.

## 3. Design rules

1. **One model.** Every line, station, structure, work and ruling exists once; every view and engine reads it;
   derived files are generated from it and never committed.
2. **Each rule once,** in one engine, cited by id; no hand-kept parity between copies.
3. **Ben's inputs are constraints.** Paints, selections, locks, canon levels, drawn ground, his street and plot
   edits: never overridden by a later pass or an import. A disagreement is flagged on the drawing and in the issues.
4. **Ratified rules with a stated priority.** Every rule cites a ruling (date, words, source) or is marked
   unratified and shown as such; conflicts are settled by rank inside a named decision, never by pass order.
5. **Decide per stretch, not per sample,** between anchors, on smoothed ground; a station is decided with its line.
6. **Tests are the product.** Every edit can be scored at once at its scale.
7. **Region-wide by default,** detail where it exists, the source of every object's ground and geometry visible.
8. **Everything has a time and a source.** Phase, opening and closing years, provenance, on every record.
9. **Every parameter is data.** No date, level, layer, geometry, threshold or name in code; ledgers, registries and
   records with per-item years; a change is one record edit and everything downstream recomputes.
10. **Results are derived,** cached by input hash and engine version, never stored as truth.
11. **Verify against Ben's real data:** his export, every rule as an invariant over every route.
12. **Ben's workflow stays:** KMZ in and out for Google Earth, rulings from chat as records, seeds for git.

## 4. The model

### 4.1 Storage

SQLite (`region.db`, WAL), schema in numbered SQL migrations applied on start, a `schema_version` table. Geometry as
WKB in EPSG:26916 metres with an R-tree per spatial table kept by the write path (no SpatiaLite). The schema is thin
on purpose: columns are what we query by; each record's other fields live in a `data` JSON column, validated by the
importers and the contract schemas, so a record round-trips whole. Built: `region/model/migrations/0001_init.sql`,
`region/model/db.py`, `region/model/seed.py`, 6 tests.

Every record: `id` (ULID, never reused or renamed; a replaced record is superseded), `version` (+1 per write; a write
carries the version it built on and a stale one is refused with a conflict, never merged silently), `created`,
`updated`, `source`, and `phase`, `year_open`, `year_close` where it is something built. Every previous version is
kept in `history`. A `legacy_key` table maps every old key (Deck station keys, profile station keys `name#2`,
chronology keys `system|line|a|b`, Deck street and plot ids) to the new id, so Ben's old records and his old hub's
exports still resolve.

### 4.2 Entities

| Table | Holds | Replaces |
|---|---|---|
| `node` | junction, line end, stop point, region seam; one rail level shared by every section through it | `rer/links.json` junctions |
| `section` | one track section between two nodes: plan polyline and fitted elements, length as ground distance, track count and spacing, phase, and in `data` the vertical controls keyed by offset from the section start (station levels `st`, bend points `pvi`, platform grades `sg`, slides `so`, deletions `del`, locks, drawn ground `gnd`), the paints (`ovr`, `tf`, `shafts`), `mode`, `ready` | Profiles `lines/*.json` paths and alignment docs, Deck pieces, KMZ pieces, `rer/lines/*`, shared stretches |
| `track` | a track within a section, for shared trunks and throats | |
| `route`, `route_section` | an ordered list of sections with directions: a Metro line, a TRI trunk or branch, an APEx route | Profiles route ids, railsim `track.folder` |
| `service` | a route pair through the trunk, stopping pattern, mission, headways by period, era, fleet | railsim `configs/*` (generated from here), the mission codes |
| `station`, `stop`, `platform` | the complex; its stop per route at an offset on a section; each platform's kind, length, width, slide, grade, level, Ben's selection, gap filler, deletion | Deck `stations`, Profiles station fields, the access type |
| `station_element` | hall, passage, flight, lift, gate, entrance with levels, outline, width, phase | `fs_model.py` PARTS, FLIGHTS, LIFTS |
| `structure` | a range on a section with method (box, twin, bore, trough, at grade, embankment, viaduct, bridge, ramp, mined station), form, origin (solved, paint, selection, canon, ruling) and the rule ids applied | the solver's output; paints; the Deck's viaduct parts |
| `bridge` | a crossing as a parametric object (spans, piers, rail, form) | the bridges page |
| `earthwork` | a pad, corridor, freeform work or raster layer, with timeline tag, mode and years | `ground/` works, the Deck's regrade, `gnd` lines |
| `ground_layer` | base surfaces by era and tier (survey 1912, core 2026, corridor, region) with path and checksum | map 3, `Elevation\` |
| `context_feature` | other systems' tracks and structures, roads with class and level, rivers; Deck streets, blocks and plots by reference (their ids are the Deck's) | `context/lines.json`, `data/deck/*`, highway KMZs, OSM |
| `yard` | depots and leads with roles | yard flags |
| `era` | year ranges with fleet, signalling, rules and platform standards | `data/operations/*.yaml`, `metro_structure.json`, the params records |
| `rule`, `ruling` | the registry mirrored; a dated decision by Ben and what it governs | `data/profile/README.md`'s rule list, `rer/canon.json` |
| `snapshot` | a named version: the input records of a route, station or service plan, with a note | none today |
| `result`, `issue` | derived outputs keyed by input hash and engine version; check failures with rule, severity and place | `cache/`, snapshot parts, free-text issues |

Demand (zones, population and jobs by era, trip tables) is added in slice 6, as tables beside these; DuckDB is an
option for it if the grid outgrows SQLite.

### 4.3 Seeds

`python -m region.model export` writes one JSON file per record (sorted keys, geometry as WKT) under `region/seed/`,
derived tables never; `import` is a three-way merge against the seed as last exported or imported here: unchanged
here and changed in the seed, take the seed; changed here only, keep ours; changed on both, keep ours and write the
seed's copy to `region/seed_conflicts/`; new, add; gone, keep ours and list. Ben's database is never overwritten.
Tested, including the both-sides-changed case.

## 5. Ground

### 5.1 The model (built: `region/ground`)

The ground for any year and timeline is composed, not stored: a base surface, then every work in the ledger whose
year is at or before the year, in ledger order, each applied by its own kind: target-and-mode rasters as the
riverworks were made (mode 1 forces the target, mode 2 only raises); the 2026 canon ground inside a delta's
footprint (the interstates, whose delta was made against LiDAR the repo does not hold); the 2026 ground inside the
kept-works zones, each zone with its own years, feathered 16 m; a bed surface where it has values. Every cell
carries the code of the layer that set it. Undated works count only at 2026 and are listed as skipped before.

Everything the compositor needs is in `ground/works_ledger.json` (years, timeline tag, apply block) and
`ground/zones/zone_years.json`; the code holds no dates, layers or geometry, and a test proves a date change is one
record edit. Rulings of 6 November are in the ledger: the Mill Creek deck done by 1913, Lunken 1937 to 1941, the
interstates about 1940 to 1965, the kept-works zones fluid, the river at 139.62 m for every year, map 3's river bed
canon. The combined 2026 riverworks raster was split by work so each carries its own years.

Checked over the whole 40 by 35 km extent (25 tiles): inside the recorded works the composite reproduces map 3
(interstates 100 % within 5 cm, terraces 99.95 %, Embankment and deck 99.0 %, kept zones 89.8 %); outside them,
map 3 differs from the 1912 surface by 0.94 m on average over 615 km², with 82 km² over 2 m and 20 km² over 5 m,
catalogued as 2,151 patches over 1 ha (`ground/reports/`), which is the change since 1912 that no work records.

### 5.2 Parametric earthworks (built)

A new work is a `Pad` (polygon at a level or on a plane, with cut and fill slopes or walls), a `Corridor` (a centre
line with levels, a formation half width, slopes) or a freeform patch. Per cell, with Z the design level at the
nearest point of the work's edge and d the distance to it: `proposed = clip(existing, Z − fill_slope·d,
Z + cut_slope·d)`; inside the footprint the cell takes Z; the daylight line is found, not drawn; cut and fill volumes
fall out of the same pass. Tiles of 1 km recompute only where a footprint touches. The railway's own cuttings and
embankments are generated from the solved section as corridors (phase-dated) and cached.

### 5.3 The real 1912 surface (in progress, lane B, `ground/1912/SPEC.md`)

The current "1912" surface is LiDAR shape with 1912 texture, so the early-phase tunnels sit on today's cuts and
fills. It is being re-derived from the 1912 City Topographic Survey sheets: sheets registered jointly on unchanged
street intersections (done: 48 sheets, 1,709 controls, rms 2.06 m, seams continuous), every 5 ft contour vectorised
with its label and confidence, a surface through the contours and breaklines only, LiDAR used for registration, the
datum fit and checks but never for shape, nodata where the sheet is blank, a confidence raster, a fit report with
targets (hilltop rms under 1 m, every seam under 0.5 m), and a one-command rebuild with the raw inputs listed by
checksum. The spec fixes every path, grid, field and the handshake file so the cloud session consumes it without
guessing. When it lands, it becomes the base for both timelines and the catalogue is rerun.

### 5.4 Tiers for the region (slice 2)

Core 2 m (map 3 and the 1912 surface), corridor 2 m (±250 m along every section from Ben's USGS DEMs and LiDAR, at
most 414 MB before compression), region 10 m (the TRI box, about 480 MB), as COGs read by window; the region tier
also as terrain-RGB PMTiles for the map. Internet sources only behind an explicit flag for building the tiers; no
run fetches ground.

## 6. The engines

### 6.1 The rules engine (TypeScript, `engine/`)

One pure function `solve(input: SectionInput): SolvedSection`: plan geometry (fitted tangents, curves, spirals,
with cant and design speed), vertical geometry (PVIs, parabolic vertical curves, level transitions), the level solver
and defaults, the structure solver, clearances and checks. No globals, no I/O, no DOM. Every quantity is a typed
array on the 2 m grid computed once per edit (`rail`, `grade`, `phase`, `type`, `struct`, `tube`, `street`, `canon`,
`river`); drawing, checks and exports index them. Every stretch and flag carries the rule ids it applied; flags are
data `{kind, sev, c0, c1, data}` rendered by the UI. Built with Vite for the browser (live editing at full fidelity,
no preview copy) and as a Node CLI for the hub's jobs and tests. Ported, not rewritten, where the old code is sound
(the vertical geometry, the ground layering, canon and locks, the fill and misfit maths, access, road clearance, the
design checks); rewritten from the registry where it is not (the level solver, the phase and grade-limit lookups,
the structure solver, crossing clearances, RER junctions), with the 4 November `solveTypes` as the reference.
Why TypeScript and not Python, Pyodide, or Rust-to-WASM: live editing needs the engine in the browser; Pyodide
costs a 10 MB runtime and a slow first load; Rust doubles the toolchains for a gain profiling has not yet asked for
(it stays an option for hot loops). Decision record 9.2 in the checklist.

Three things the old engine never had, added here: a real horizontal alignment (radii and speed limits derived from
geometry rather than three-point circles on drawn corners); a profile proposer beside the solver (a QP or LP over the
grid with station levels, cover, clearances, river bands, grade and vertical-curve limits as constraints and cut,
fill, box and bore as cost; never overriding Ben; Regrade and Solve-crossings become constraints in it); quantities
from the ground model and the structure solve.

### 6.2 The rule registry (built: `rules/registry.yaml`, `region/rules.py`)

137 rules and 163 parameters mined from the dated rule list, the logs, the handoffs, the settings and the solver
code. Each rule: a dotted stable id, domain, text (numbers only by parameter path), status (ratified 38 with a dated
quotation of Ben's, provisional 91, unratified 8), ruling (date, by, words, source), decision and rank, params,
systems, flags, tests, history. Of the parameters, 76 are still literals in the page's code with no record; each is
named with its line so the port turns it into a parameter or deletes it. The eleven tunnel-method rules were checked
line by line against the code and ratified by Ben on 6 November (two texts corrected to what the code does). A
validator and four tests hold the registry well formed; a test will fail on any engine branch without a rule id and
on any rule without a test once the engine exists.

### 6.3 The contract

`SectionInput` and `SolvedSection` as TypeScript types; JSON schemas generated from them (zod); pydantic models
generated from the schemas for Python; versioned, and the engine version is part of every result's cache key. The
solved section carries rail and grade by offset, vertical curves, structure ranges with method, form and rule ids,
platform extents and levels, speed-relevant geometry (curvature, cant, turnouts), and issues.

### 6.4 The analysis engine (Python, `region/analysis/`)

railsim reads solved sections through a new route builder (the KMZ reader and `LocalProjection` kept only for
import). Added: "where the time goes" (marginal seconds per restriction by re-running with it relaxed, and the
accelerating, cruising, braking split per segment); blocking time per section from the era's signalling (fixed
block: approach, occupation, release; CBTC and moving block from braking distance), minimum headway per section,
junction conflicts from overlapping blocking times; service and fleet; station flows (static assignment by
quickest path with capacity penalties, iterated; a time-sliced queue model if platform surges matter for NFPA 130)
with Fruin level of service as printed in TCQSM and NFPA 130's 4 and 6 minute criteria, looked up and cited before
use; demand by era and scenario. Calibration gates are tests (built): Orange Line 35.82 / 35.74 min and Needham
34.29 / 33.94 technical held within ±1 %, station differences reported.

## 7. The app

One Vite + TypeScript app served by the hub (FastAPI: Range, ETag, SSE, If-Match on every write, a real
path-containment check; the old server read whole files into memory with `no-store` on everything and served
`/hub/../hub.db`). One selection, one era, one scenario, all in the URL, so any view links to any other.

| Pane | Shows | Edits |
|---|---|---|
| Region map (MapLibre; PMTiles for Deck streets and plots, Sanborn, OSM, highways, rivers, terrain; GeoJSON by bbox and era for the live model) | every system with layers by system, structure, era and result; hillshade and 3D terrain; the era slider; search | picks; draws and re-paths sections; draws earthworks; imports KMZ |
| Line sheet (canvas) | plan strip, profile with ground source, rail, structures, platforms, context, roads; curvature and speed limit; railsim speed curve and times; run-time table; where the time goes; issues; both directions | station levels, bend points, paints, locks, platform slides, drawn ground; editing by numbers |
| Section | the cross-section at the cursor: ground, structure, clearance envelope, earthwork slopes | slopes, widths, walls |
| Station workspace (three.js) | plan per level, section, 3D of the station and the structures round it (GLB per section built server-side, instanced piers and equipment, exaggeration in the shader, the old page's camera, presets, cutaway and exports kept) | halls, passages, flights sized from their rise, lifts, gates, entrances |
| Service view | stringlines, blocking-time stairs, minimum headway per section, junction conflicts, fleet and cycle times, loads | patterns, headways by period, missions |
| Street and plot editor (Ben, 6 November: rebuilt, not kept) | streets with sidewalks and kerbs, blocks, lots with Sanborn attributes and an optional height so they can become buildings; every layer with visibility, opacity and year range | draws new streets the plate passes missed; edits anything; the ported `applyOps` and `rebuildPlots` in a Web Worker; terra-draw tools on MapLibre |
| Tables | stations, sections, structures, earthworks with volumes, yards, services, rulings, statistics; CSV | inline fields |
| Issues | every check failure with severity, rule and ruling; click to go there | none |
| Compare | two versions side by side with every score diffed | none |

**Base and edits kept apart, merged on read** (the Deck's lesson): every street, block and plot carries an origin
(plate and pipeline run, or authored by Ben) and a stable id; the Sanborn pipeline writes only derived features of
its own plate set; Ben's edits and authored features are a separate table; the view is derived with edits applied on
top; an import for a plate adds new features, keeps unchanged ones, lists changed ones against the edits that touch
them, and never moves or removes an authored feature. Changesets with per-feature versions and a conflict list.

Usability rules: edits where you see them; every edit shows its score change; undo and redo and named versions;
nothing runs silently for minutes; units switch m and ft; Ben's terms; a chainage readout everywhere.

## 8. Jobs and cache

A dependency graph in `region/jobs/`: each job declares its inputs (record ids and versions, file hashes, engine
version) and outputs; keys are content hashes, so unchanged work is reused and results are stored per section. A
section edit re-solves that section, then the services crossing it, then the trunk's capacity, then its issues; a
platform or element edit re-solves that station's flows; an era or service edit re-runs the services it touches.
Workers in threads with progress over SSE (events carry the record path, version and changed sections; the old
shim refetched a whole collection per event). Long jobs (a ground tier, a demand run, a tile build) run in the
background. Budgets, as tests: a profile edit re-solves in the page with no visible wait; a saved edit updates run
times within 10 s; the region map opens in under 5 s. An in-process graph on a SQLite-backed queue; no task
framework.

## 9. Import and export

Importers, each with a round-trip test: the Deck layout and files (frozen as base v1, ids kept, an alias table);
Profiles alignments, lines, `rer/*`, the context; Ben's hub export; the KMZ (outside the Deck region and for
re-paths, with levels, stations and bend points carried across by geometry); chronology, operations and rolling
stock; the Fountain Square model; the `Elevation\` profiles; APEx, ORR and TRIMET; highways and rivers; the ridership
tables; the bridges page parameters; the ground ledger and zones.

Exporters: seeds; KMZ with levels and structures (from `tools/export_profile_kmz.py`); LandXML alignments (for
Civil 3D and OpenRail drawings); CSV; railsim configs; glTF and PNG; plan-and-profile sheets as PDF or PNG.

The Sanborn pipeline stays a separate importer in lane B (nothing re-derived: streets, plots and tiles frozen as
data; the pipeline adds plates one batch at a time, each fitted by thin-plate spline on its complete hand-read
crossings, solved jointly with its neighbours, re-bent and composited, with a seam report). Its current state is
in section 13.

## 10. Verification

- **Unit tests** for every engine function and importer (pytest; vitest for TypeScript).
- **Baseline** (built, `tests/baseline/`): every route's rail every 5 m, structure types and tube forms as the page
  solved them on 5 November, the saved alignments, platforms, approaches, the 57 old 3D issues, and the Metro run
  times. The rebuild compares every route against it; each difference is classed same, rule fix with its id and
  ruling, or unexplained, which must be zero before a slice closes. Inputs must survive import and export value
  for value (lossless), separately from outputs, so the new engine is not made to reproduce known defects.
- **Golden tests**: every saved route solved under Node against committed goldens; a golden changes only with a
  rule id.
- **Invariant tests**: every registry rule over every route on Ben's export and on the repo seed.
- **Calibration gates** (built): Orange and Needham within ±1 % of the model's own baseline; per-segment ±3 %
  against published times reported.
- **Round trips** for every importer and exporter; **browser tests** (Playwright) for each pane and the edit loop;
  **performance budgets** as tests; **rule coverage** (no engine branch without a rule id, no rule without a test);
  **reproducibility** (`python -m region rebuild` from git plus Ben's export is byte-identical).

## 11. Working method

Two lanes that own disjoint paths and meet only through written contracts:

- **Lane A, build**: cloud sessions on `hub_region`, one slice at a time; each session's brief names its inputs,
  outputs, exit tests and the paths it may touch. Owns `region/`, `engine/`, `app/`, `rules/`, `tests/`, `ground/`
  code and derived layers.
- **Lane B, use**: Ben and local sessions on his machine, for anything that needs his files or his judgement: the
  1912 ground, the Sanborn plates, profile and Deck edits, canon rulings, line design. Owns `hub/seed`, `data/`,
  `hub/sites/deck`, `tools/sanborn`, `data/sanborn`, `design/`, `ground/1912/` while its session runs. Works on
  `main`; lane A merges `main` into `hub_region` at checkpoints.

Rules: a spec before every handoff; done means tests passing, a plain report with numbers, a log row, `STATUS.md`
updated, pushed; nothing counts that lives only on one machine or in one chat; no page is retired until lane B has
done a real task in its replacement; Ben's data is never overwritten and imports merge with a backup; rulings are
collected with leans, ruled in batches, and become records the same day; canon is never changed by code and a rule's
meaning never changes without a ruling; the Sanborn paths and the Deck's tiles and street data are read-only to the
rebuild. A checkpoint at every slice or lane-B batch: Ben exports and pushes, lane A merges, reruns every test on
the export, reports differences.

Lessons applied from this week's Sanborn work: a guard is set after seeing what the data can do, not before, and it
tests the measure that matters (held-out error and seams, not corners nobody uses); a fitting pass that fails its
guard is a result to decide on, not a reason for another pass.

## 12. Slices

Each slice is usable on its own and retires an old page; order can change at any checkpoint without rework.
Estimates are sessions of the kind run so far.

| # | Slice | Builds | Exit tests | Needs from Ben | Est. |
|---|---|---|---|---|---|
| 0 | Foundations and ground | ground model; the 1912 surface (lane B); baseline; gates; registry; schema; bridges and the C&O viaduct as records (RER B on the deck north of Northside, a ramp viaduct south of Camp Washington, walls below the track); app shell and API skeleton | migrations apply; registry lists every rule the page applies; baseline and gates committed and passing; 1912 meets its spec or misses listed; bridges reproduce the page's facts from records | rulings as diffs raise them | 2 to 3 (most done) |
| 1 | Metro | the engine lifted (one route end to end first); the contract; railsim on solved sections with where-the-time-goes; the job graph; the line sheet; every Metro route imported with stations, platforms, phases, context; invariant tests; the Deck adapter; `metro_profile.py` deleted; horizontal alignment and the proposer | inputs lossless; output diff per route with zero unexplained; Line 6 within 1 % of baseline; an edit updates run time within 10 s; gates pass; every rule holds as an invariant or is a flagged exception; the Deck's platform moves round-trip | ratify the rules the diffs change; the tunnel-method ratification done | 5 to 7 |
| 2 | TRI, offline | corridor and region tiers; outer sections from the KMZ with seams at the Deck-region edge (report at 5 m); shared trunks as nodes; the 25 routes and 55 services; RER canon locks as rulings | every TRI service runs with no internet and no flat fallback; seams listed; sheets both ways; the TRI run-time baseline captured on real ground | region box (lean: TRI extent plus 5 km); D/E lettering as the Deck has it | 3 to 4 |
| 3 | Map, eras, structures, editor | MapLibre and the tile build; era slider; draw sections and earthworks; structures region-wide with sizes and costs by phase; quantities; the viaduct fix; the issues pane; tables; the street and plot editor pane with merge-on-read, sidewalks, lots | region opens under 5 s; any year 1905 to 2026 draws network and ground as built; every check failure listed and linked; an earthwork drawn on the map changes profile, section, 3D and volumes; a plate import merges without moving an authored street | the catalogue's works dated; batch rulings | 4 to 5 |
| 4 | Network loop | services, patterns, missions, headways; timetables; blocking time by era; minimum headways; junction conflicts; fleet; the service view | the trunk headway check for A/D, B/D, the CVG stretch and CUT in each era; fleet per line and era tabled; gates still pass | signalling by era where the records are silent; mission codes | 3 |
| 5 | Station loop | elements; Fountain Square imported; walking graph, reachability, step-free, decision points; flows from the v17 tables; level of service, digging index, NFPA 130; 3D rebuilt from the model; the headless sync deleted; then CUT | stacked, spread and half-stacked Fountain Square compared on one screen with every score; the reachability check reproduces `fs_reach.py`; 3D agrees with the sheet within 1 cm | Fountain Square platforms (400 ft); the stacking decision on the evidence | 4 |
| 6 | Demand and statistics | the ridership model recovered or rebuilt to v17's totals (8,120,167 weekday trips); loads to the network, flows to the stations; statistics; compare everywhere | v17 within 0.5 %; loads on the map and stringlines; every pane compares two versions | the scenarios to keep | 3 |
| 7 | Hardening | exporters complete; budgets as tests; one-command rebuild; the old hub removed; README; migration note | a fresh clone plus Ben's export rebuilds everything byte-identical; every budget passes; no artifact page left | none | 2 |

Line 6 (or any line with a saved profile) is the first route inside slice 1, not a milestone of its own (Ben, 6
November).

## 13. Status (7 November)

**Done** (all on `hub_region`, tests 96 passing): `ground/` consolidated, map 3 moved and every reader repointed;
`region.ground` with the compositor, parametric works, sampling, CLI, the whole-extent check and the change
catalogue (2,151 patches, 5,611 ha); dates, layers and zones as data with a test; the roadmap, checklist, scrutiny,
review and this plan; `node_modules` and `.venv` out of git; the baseline (41 routes, 17 Metro run times, issues);
calibration gates; the rule registry (137 rules, 163 params; 11 ratified on 6 November); the model schema with
versions, history, legacy keys, R-tree and seeds. Rulings taken: branch `hub_region`; map 3 to `ground/2026`; deck
by 1913; Lunken 1937 to 1941; interstates about 1940 to 1965; zones fluid; river 139.62 m all years; map 3's bed
canon; bridges and the viaduct in scope; 1912 re-derived; Sanborn not re-derived, spline on complete controls;
slice order as listed; RER B on the north viaduct's deck and off it on a ramp viaduct; the Deck rebuilt as an
editor; all section 6 leans of 6 November.

**In flight, lane B**: the 1912 surface, at the contour stage, no push for about a day (state to confirm); the
Sanborn apply of the chosen models (complete-control fit for 19 plates, the curl fit for 37L and 37R), state to
confirm; the Deck tie on Ben's hub failed (log awaited). TRI run times were captured but are a pre-ground record
(they will be replaced in slice 2).

**Next, lane A**: the engine package and the geometry port with golden tests against the baseline; the Metro
importers; the API and the line sheet on one route.

## 14. Risks

| Risk | Handling |
|---|---|
| The engine port drifts from the page where Ben's lines depend on it | the per-route baseline diff with zero unexplained; goldens; rule ids on every change; inputs tested lossless separately from outputs |
| Ben's edits in the old hub diverge from the model during the transition | one source at a time: a page is retired only when its pane replaces it; until then the old hub's export is the import; the `deck/layout` adapter for platforms |
| The Sanborn pipeline and the rebuild collide on the Deck | the Deck's files and ids are read-only to the rebuild; base v1 frozen with an alias table and a golden replay test |
| The 1912 surface is late or misses its targets | the compositor reads whichever base is present; the misses are listed in its report and ruled on, not hidden |
| Rasters outgrow git | core layers tiled under 25 MiB in git; corridor and region tiers outside git with manifests; PMTiles for the map; DVC only if hand-tracking fails |
| Memory and time on big composites and solves | 1 km tiles; jobs keyed by hash; background builds with progress; arrays not per-sample functions |
| Standards figures (Fruin, NFPA 130) wrong from memory | looked up and cited in the registry before use; shown as unratified until Ben confirms |
| Scope: eight slices is a long road | each slice usable and retiring a page; order changeable at any checkpoint |
| Guards set before the data is understood (this week's Sanborn lesson) | guards after a first fit, on the measure that matters; a failed guard is a decision point |

## 15. Decisions (context, options, decision, consequence)

1. **Ground as a model, not a raster** (6 Nov). Five layers of different ages, two frozen bakes. Options: more
   rasters per era; parametric works on a base. Decision: parametric works on the real 1912 base, rasters as caches.
   Consequence: the 1912 re-derivation.
2. **Rules engine in TypeScript** (6 Nov, provisional pending slice 1). Options: TypeScript; Python via Pyodide;
   Rust-to-WASM; Python with a drag preview. Decision: TypeScript. Consequence: Node in the toolchain; Python never
   re-derives a level.
3. **FastAPI plus Vite/React** (6 Nov). Options: stdlib server; Starlette/Svelte; HTMX with no front-end build.
   Decision: FastAPI and React, for Range, SSE, validation and the map and 3D bindings.
4. **SQLite with hand-written migrations** (6 Nov). Options: SQLAlchemy/Alembic; SpatiaLite; DuckDB. Decision:
   SQLite, WKB plus R-tree, thin columns plus JSON data. DuckDB kept for demand.
5. **The Deck rebuilt as an editor** (Ben, 6 Nov; replaced the lean to keep it). Decision: rebuilt in slice 3 with
   base and edits apart; the old Deck runs until the pane has done a real task.
6. **Dates, layers and zones as data** (Ben, 6 Nov). Decision: no date, layer, level or geometry in code.
7. **Sanborn frozen, not re-derived** (Ben, 6 Nov); **spline on the complete hand-read controls** (Ben, 6 Nov);
   dense automatic controls shelved after the locator failed (a Sanborn street is full of ink; 1,511 named crossings
   exist in all); lot corners from the county parcel layer as a later option.
8. **No outside engine** (6 Nov, scrutiny). Civil 3D and OpenRail do geometry only and are not scriptable; OSRD runs
   trains and does not design vertical alignments. Decision: port the sound parts, rewrite the solvers from the
   registry, add what no tool had.
9. **Line 6 not a milestone** (Ben, 6 Nov): the first route inside the Metro slice.
10. **Ids as ULIDs with a legacy-key table** (7 Nov). Options: keep natural keys; UUIDv7. Decision: ULIDs.

## 16. Not doing

An outside alignment engine; re-deriving the Sanborn streets; power-supply load flow and full ETCS braking curves in
railsim; animated walkers; money in the digging index; a 3D globe; keeping the Python copy of the rules; the TRI
run-time baseline before real ground.

## 17. Open rulings (with leans, none blocking)

Region box (TRI extent plus 5 km); the tunnel-method rules beyond the eleven (ratify from the diff reports);
Fountain Square platforms (400 ft); signalling by era where records are silent; the scenarios to keep; the
catalogue's works to date once the 1912 surface is in; the spine side of plates 33 and 38 if the curl option is
offered to every plate.

## 18. Defects that must not come back

Two or three copies of a rule; the drawn band and the engine giving two answers; a method chosen per 2 m sample from
thresholds; later passes overriding Ben's inputs; a launch box swallowing boreable ground; "deep" meaning four
things; a ground dip inside a tunnel becoming a portal; a box without its roof and cover under the ground; clamped
slides; tube form not moving with re-paths; saves without a version; crossings guessing the other line's structure
from depth; regrades building bends their vertical curves cannot fit; a paint raising the ground; one shortfall
reported as three issues; rules not tested as invariants; keys made of names and coordinates; whole-document saves;
derived files in git; a browser as a calculator; a date in code; a raster nobody can rebuild; a handoff without a
spec; a result that lives only in one chat or on one machine.

## 19. Glossary

Canon: the alternate history's facts, Ben's to rule. Map 2 and map 3: the canon ground in 1912 and 2026. I4: the
old 1912 surface method (LiDAR shape with 1912 texture). Deck: the Mill Creek Deck page and, as a structure, the
Mill Creek deck. TRI / RER: the regional rail system. APEx: the intercity system through CUT. Stretch: the run of
tunnel between two anchors. Anchor: a box station, portal, the sunk box, a canon box, a phase change or a painted
shaft. Paint: Ben's structure override on a range. Selection: Ben's structure choice at a station. Tie: a crossing
two plates share. Seam: the disagreement between two copies of a crossing. Held-out error: the fit's error on
controls left out of the fit, the honest measure. Slice: a usable increment that retires a page. Lane: a stream of
work owning its paths.
