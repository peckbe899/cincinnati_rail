# Hub rebuild: the living checklist

Started 6 November 2026. This is the working board for the rebuild, kept current by whichever session finishes work.
The roadmap (`Hub_Region_Roadmap_2026-11-06.md`) says why; this says what, in what order, with the ways each thing
could be done. Edit it freely: tick boxes, change leans, add options, strike items. History is in git.

Marks: `[ ]` not started, `[~]` in progress (say who), `[x]` done (commit), `[-]` dropped (say why). Lane A = build
(cloud sessions, branch `hub_region`), lane B = use (Ben, local sessions, chats; branch `main`, merged into
`hub_region` at checkpoints). "Lean" is the option to take unless Ben says otherwise; it is a starting guess, not a
ruling, and for large items the first guess is often not the best one.

## 0. How projects of this scale are laid out (and what we take from it)

Read on 6 November (sources at the end):

- **First slice, then widen** ("walking skeleton"): one thin path through every layer, usable, before any layer is
  built out. We do this as Metro-on-one-line inside slice 1, and again at every slice (one route, one station, one
  trunk first).
- **Decision records**: every significant choice written as context, options, decision, consequences, dated. We keep
  them in section 9 here (short) and in `rules/registry.yaml` where a decision is a rule.
- **One repository, owned paths**: a single repo is right for one person and one product, provided each lane owns
  its paths so merges are mechanical. Ownership is in section 1.
- **Big data outside git, pointers inside**: rasters and scans stay out of git; the repo holds manifests with
  checksums and the scripts that rebuild derived files. Where a derived raster must be in git for the cloud session
  to read it, it is tiled under 25 MiB. Options for the big inputs are in 2.0.6.
- **A spec before a handoff**: whenever work moves between sessions or lanes, the format, grid, ids, limits and
  handshake are written first (`ground/1912/SPEC.md` is the pattern).
- **Definition of done**: tests passing, report with numbers, log row, STATUS updated, pushed. Nothing counts that
  is only on one machine or in one chat.
- **Strangler pattern for the old hub**: the old pages keep running; each is retired only after its replacement has
  done a real task. Nothing is removed before it is replaced.

## 1. Path ownership

| Lane A (build) | Lane B (use) | Shared, by contract only |
|---|---|---|
| `region/`, `engine/`, `app/`, `rules/`, `tests/`, `ground/` (code and derived layers), `claude/Hub_Region_*` | `hub/seed/`, `data/`, `hub/sites/deck/`, `tools/sanborn/`, `data/sanborn/`, `design/`, `ground/1912/` (while the local session runs) | `ground/works_ledger.json` and `ground/zones/` (Ben's rulings, A's reader), `configs/*_paths.json` |

## 2. Lane A: the slices

### Slice 0: foundations and ground

- [x] 2.0.1 `ground/` consolidated; map 3 moved to `ground/2026/`; readers repointed (6 Nov, 0e30d75).
- [x] 2.0.2 `region/ground`: compositor by year, parametric Pad and Corridor, sampling, CLI, tests (251f79e).
- [x] 2.0.3 Dates, layers, zones as data; riverworks split by work; per-zone years (3a29715).
- [x] 2.0.4 Change catalogue and map, 2026 against 1912 outside the works (eec3c86).
- [~] 2.0.5 **The real 1912 surface** (lane B, local session, to `ground/1912/SPEC.md`). Then lane A: swap the base,
  rerun check and catalogue, update tests. Options for the surface itself are in the spec; the open method choice
  is thin-plate (smooth, slow on 270 km²) against TIN with breaklines (fast, faithful to the contours, needs
  breaklines to look right on ridges). Lean: TIN for the surface, thin-plate only to label.
- [ ] 2.0.6 **Big inputs outside git**. Options: (a) manifests with checksums and local paths, nothing in git but
  derived tiles under 25 MiB (what we do now); (b) DVC with a remote on Ben's machine or a cloud bucket, pointer
  files in git, `dvc repro` for the pipelines; (c) GitHub releases as a file store for the raw inputs the cloud
  session needs; (d) git LFS. Lean: (a) now, (c) when the cloud session needs a raw input, (b) only if the number
  of derived rasters grows past what (a) can track by hand. (d) is out: no chunked access, egress cost on history.
- [ ] 2.0.7 **Model schema** (`region/model`). Options: (a) hand-written numbered SQL migrations on SQLite, WKB
  geometry, R-tree indexes, dataclasses in Python; (b) SQLAlchemy plus Alembic, typed models, migrations
  generated; (c) SQLite with SpatiaLite for real spatial SQL; (d) DuckDB with the spatial extension, columnar, fast
  analytics, weaker for many small writes. Lean: (a): fewest moving parts, every migration readable, and the
  geometry work happens in Shapely anyway. Revisit (d) for the analysis tables in slice 6.
- [ ] 2.0.8 **Ids and legacy keys**. Options: (a) ULIDs everywhere plus a `legacy_key` table; (b) keep the old
  natural keys as ids and add a display name; (c) UUIDv7. Lean: (a) (sortable, no collisions, old keys still
  resolve).
- [ ] 2.0.9 **Rule registry** (`rules/registry.yaml`). Options for shape: (a) one YAML file, one entry per rule
  with id, text, ruling, status, priority, tests; (b) a table in the model with the YAML as its seed; (c) rules as
  code annotations harvested into a file. Lean: (a) now, (b) when the UI shows "unratified" chips (slice 3).
- [ ] 2.0.10 **Baseline capture** under `tests/baseline/`: every route's rail every 5 m and structure types from
  the current page (headless once, the last time a browser is used), every railsim run time, the 3D issues.
  Options: (a) run the old harness once and commit the samples; (b) commit the old snapshot parts from Ben's
  `hub/work`. Lean: (a), with (b) as a cross-check.
- [ ] 2.0.11 **Calibration gates as tests** on today's railsim: Orange Line 35.8 against 35 scheduled, Needham 38.0
  against 40; ±1 % regression on the model's own numbers, ±3 % per segment reported. One way: pytest with the
  configs' `reference:` minutes.
- [ ] 2.0.12 **Bridges and the C&O quad-track viaduct as records** from the bridges page and the KMZs; the RER B
  level on the viaduct checked against Ben's export (needs `hub_work.zip` to reproduce the scene). Options for the
  frame: (a) derive the C&O frame from the Bridge Spans KMZ line (origin at the line's midpoint, x along it);
  (b) ask the chat that built the page for its transform. Lean: (a), checked against (b) if available.
- [ ] 2.0.13 **Viaduct fix** (walls below the track). The fault is structural (a line's level and its structure
  are independent records). Options: (a) in the model, a section on a structure takes the structure's rail; a
  track below its structure is an issue; (b) a quick patch in the old 3D page's context build to clamp the arcade
  to the line's level. Lean: (a) in slice 3 with the structures; (b) only if Ben needs the old page right now.
- [ ] 2.0.14 **Corridor and region ground tiers** from Ben's USGS DEMs and LiDAR (lane B local session, to a spec
  like the 1912 one). Options: (a) COGs per tier, read by window; (b) one Zarr store with pyramids; (c) PMTiles
  terrain-RGB for the map plus COGs for sampling. Lean: (a) plus the terrain-RGB PMTiles in slice 3.
- [ ] 2.0.15 **App shell and API skeleton**. Options: (a) FastAPI plus Vite/React; (b) Starlette plus Vite/Svelte
  (lighter, smaller ecosystem for map and 3D bindings); (c) a single Python server with HTMX and canvas, no
  front-end build (fewest tools, but the engine must run in the browser for live editing, which rules it out).
  Lean: (a). Decision record 9.3.
- [ ] 2.0.16 `claude/STATUS.md` board and `claude/Hub_Region_Working_Method.md`; project skills in
  `.claude/skills/` (export before build, rebuild and compare, take a handoff); a hook running the ground and
  engine tests on change.

Exit for slice 0: migrations apply to empty and seeded databases; the registry lists every rule the page applies;
the baseline and gates are committed and pass; the 1912 surface meets its spec or its misses are listed; the
bridges reproduce the page's facts table from records.

### Slice 1: Metro (engine, railsim, the line sheet, the Deck adapter; Profiles retired for Metro)

- [ ] 2.1.1 **First route end to end** (any line with a saved profile; Line 6 or 1). Import, solve, run, sheet,
  one edit scored in under 10 s. This is the walking skeleton; it is not a milestone of its own.
- [ ] 2.1.2 **The rules engine lifted**. Options: (a) port `solveTypes` (4 Nov) and the geometry to TypeScript as one
  pure function, built for browser and Node; (b) write the engine in Python and run it in the browser through
  Pyodide (one language, but a 10 MB runtime and slow first load); (c) Rust compiled to WASM for both sides
  (fastest, slowest to iterate, two toolchains); (d) Python only with a drag preview that draws straight grades.
  Lean: (a); keep (c) for hot loops later if profiling says so. Decision record 9.2.
- [ ] 2.1.3 **The contract** `SectionInput` / `SolvedSection`: TypeScript types, JSON schema generated, pydantic
  models generated, versioned. One way; the only choice is the schema generator (zod or typebox). Lean: zod.
- [ ] 2.1.4 **Import of every Metro route**: Deck pieces inside the region, Profiles paths outside, the saved doc
  fields (st, pvi, sg, so, del, ovr, stt, tf, shafts, gnd, gapfill), stations as complexes, platforms with era
  standards, chronology as phases. Round-trip test: inputs lossless.
- [ ] 2.1.5 **Baseline diff per route**: every difference classed same / rule fix with id / unexplained; zero
  unexplained before the slice closes. Options for the report: (a) a markdown table per route; (b) a JSON report
  rendered in the issues pane later. Lean: both, JSON as the source.
- [ ] 2.1.6 **railsim reads solved sections**: a route builder from the contract; the KMZ reader kept only for
  import. "Where the time goes": options (a) marginal re-runs with each restriction relaxed; (b) phase attribution
  (accelerating, cruising, braking) per segment; (c) both. Lean: (c), (b) is nearly free.
- [ ] 2.1.7 **The line sheet pane**: plan strip, profile with ground source, structures, platforms, context, roads,
  curvature and speed limit, speed curve, run-time table, where the time goes, issues, both directions. Options
  for the drawing: (a) one canvas with hand-written layers (fast, full control, as the old page); (b) an SVG/D3
  stack (easier to style, slow past a few thousand elements); (c) WebGL via regl or PixiJS (fastest, more code).
  Lean: (a), with (c) if the TRI trunks make it stutter.
- [ ] 2.1.8 **Job graph and cache** keyed by content hash plus engine version; SSE progress. Options: (a) a small
  in-process graph in Python with a SQLite-backed queue; (b) a task library (Prefect, Dagster: heavy for a local
  tool); (c) Make-style file rules. Lean: (a).
- [ ] 2.1.9 **Invariant tests** over every Metro line on Ben's export, one per registry rule.
- [ ] 2.1.10 **The Deck adapter** (two-way for platforms and station cards; every street id survives).
- [ ] 2.1.11 `metro_profile.py` deleted; railsim configs generated from the model; the Profiles page retired for
  Metro (the old hub keeps TRI and the Deck).
- [ ] 2.1.12 Line works as corridor earthworks from the solved section (phase-dated), in the volumes.
- [ ] 2.1.13 **Arrays, not functions** (scrutiny 6 Nov, item 1): every engine quantity a typed array on the 2 m
  grid computed once per edit; drawing, checks and exports index them.
- [ ] 2.1.14 **Horizontal alignment as real geometry** (arcs, spirals, cant, design speed) with the plan strip editable
  by R and spiral length; radii and speed limits derived. Options: (a) write it in the engine (standard formulas,
  a few hundred lines); (b) fit from the polyline first (railsim's `fit_horizontal` ported) and let Ben edit the
  fit; (c) LandXML import of alignments drawn in Civil 3D. Lean: (b) then (a): fit once, edit as geometry.
- [ ] 2.1.15 **Profile proposer** beside the solver, never overriding Ben. Options: (a) QP with OSQP (smooth, fast,
  needs convex cost); (b) LP/MIP with HiGHS (method choice as integers, slower); (c) dynamic programming over the
  grid (simple, handles any cost, coarse); (d) the current Regrade and Solve-crossings heuristics kept as they are.
  Lean: (a) for levels with (c) for method choice; (d) only as the fallback during slice 1.
- [ ] 2.1.16 **Quantities** (cut, fill, box, bore, lining metres) from the ground model and the structure solve.
- [ ] 2.1.17 **Flags as data** with rule ids; no UI text in any engine (scrutiny item 5).

### Slice 2: TRI, region-wide, offline

- [ ] 2.2.1 Corridor and region tiers in the ground service (2.0.14 landed); no internet in any run (railsim's
  fetchers behind `--online`).
- [ ] 2.2.2 Outer sections from the KMZ; nodes at the Deck-region seams; seam report at 5 m. Options for the
  seam: (a) split at the region edge and join with a node whose level is shared; (b) extend the inner section
  outward and drop the outer overlap; (c) re-draw the seam stretch in Google Earth. Lean: (a), flag where the
  paths differ by more than 5 m.
- [ ] 2.2.3 Shared trunks as nodes with one level (r07); the D/E lettering as data; the 25 lettered routes and 31
  services (plus 24 pre-RER); platforms 670 ft; the RER canon locks as rulings.
- [ ] 2.2.4 Every TRI service runs offline, run times within 1 % of baseline or explained; the Profiles page
  retired entirely.

### Slice 3: the region map, eras, structures, issues, tables

- [ ] 2.3.1 **Map engine and tiles**. Options: (a) MapLibre with PMTiles for the static layers and GeoJSON for the
  live model (hillshade and 3D terrain built in); (b) deck.gl over MapLibre for very large live layers and 3D
  extrusions (more power, more code); (c) CesiumJS for a true 3D globe (heaviest, overkill at 150 km); (d) Leaflet
  (simplest, no terrain, no vector tiles). Lean: (a), with deck.gl layers only if the live layers outgrow it.
- [ ] 2.3.2 Tile build job: tippecanoe for vectors (or the Python `pmtiles` writer if tippecanoe is awkward on
  Windows), terrain-RGB for the region tier; served with HTTP Range by the API.
- [ ] 2.3.3 Era slider; draw and re-path sections; draw earthworks (Pad, Corridor) with the Section pane for
  slopes and the 3D view for the result.
- [ ] 2.3.4 Structures region-wide (viaducts, bridges, embankments, boxes, tubes) with sizes and costs by phase;
  quantities in the tables; the viaduct fix (2.0.13 option a).
- [ ] 2.3.5 Issues pane and tables; Chronology and Access retired; the Deck keeps streets and plots only (decision
  record 9.5).

- [ ] 2.3.6 **The Deck's editor logic ported unchanged into a Web Worker**, rendering on MapLibre, layout saved as
  append-only operations with ids, base files frozen as base v1 with an alias table and a golden replay test
  (scrutiny item 6). One platform id shared by the Deck, the Profiles and the model (item 7).
- [ ] 2.3.8 **The street and plot editor rebuilt as a pane** (Ben, 6 Nov: "fully editable and more powerful";
  replaces the lean in 9.5). Requirements: draw new streets the plate passes missed; edit any street, block or plot;
  additions from the pipeline merge into the hub instead of overwriting it; smoother layers; sidewalks and kerbs;
  a lot model that can later become buildings in 3D. Options for the editor: (a) MapLibre with terra-draw (or
  maplibre-gl-draw) for the drawing tools and the ported `applyOps`/`rebuildPlots` logic in a Web Worker; (b) an
  iD-style editor (OSM's) adapted to the model (the richest editing model, most code); (c) keep the canvas editor
  and only swap its rendering. Lean: (a).
- [ ] 2.3.9 **Base and edits kept apart, merged on read** (Ben, 6 Nov: the hub separate from the importer, so an
  import merges instead of covering). Model: every street, block and plot carries `origin` (plate id and pipeline
  run, or `authored` by Ben) and a stable id; the pipeline writes only `derived` features of its own plate set; Ben's
  edits and authored features are a separate table; the view is derived with edits applied on top. An import
  re-runs for a plate: new derived features appear, unchanged ones stay, changed ones are listed with the edit
  that touches them, and an authored feature is never moved or removed by an import. Options for the merge: (a)
  three-way per feature with the last import as base (as the hub's seed merge does today, per record); (b)
  OSM-style changesets with per-feature versions and a conflict list; (c) CRDT per feature (overkill for one
  user). Lean: (b), which is (a) with history and a reviewable list.
- [ ] 2.3.10 **Street model for sidewalks and kerbs**: a street is a centreline with a carriageway width, sidewalk
  widths and kerb lines derived (options: widths by distance along the line, or per segment); blocks and plots
  snap to the kerb line; the Sanborn plate gives printed widths as the default source.
- [ ] 2.3.11 **Lots that can become buildings**: plots keep their Sanborn attributes (use, storeys, material where
  printed) and an optional footprint and height so the station workspace and the region map can extrude them later
  (3D buildings from lots). Options for the 3D: (a) MapLibre fill-extrusion from the plot layer (free, flat roofs);
  (b) three.js meshes in the station workspace from the same records; (c) both from one record. Lean: (c).
- [ ] 2.3.12 **Layer rendering**: every Deck layer (Sanborn sheets by year, relief, streets, blocks, plots, lots,
  transit, structures) as a MapLibre source with its own visibility, opacity and year range; the heavy static ones
  as PMTiles (2.3.2).
- [ ] 2.3.7 Two old-hub bugs logged: `rer_deck_routes.py:665` `fn.split('/')` never matches on Windows (junction
  points never update); `station_access_report.py` reports on stale repo profiles. Fix the first in the old hub if
  Ben keeps using the tie before slice 3 retires it.

### Slice 4: the network loop

- [ ] 2.4.1 Services, patterns, missions, headways by period; timetables generated.
- [ ] 2.4.2 **Blocking time**. Options: (a) classic blocking-time stairs from the railsim speed profile and the era's
  signalling (approach, occupation, release; CBTC from braking distance); (b) a full event simulation of trains on
  the network (more faithful, much more work, a second simulator); (c) analytic headway formulas per block type
  (cheapest, coarse at junctions). Lean: (a), which is what OpenTrack and RailSys do for capacity.
- [ ] 2.4.3 Minimum headway per section, junction conflicts, fleet and cycle times; the service view (stringlines,
  stairs, loads).

### Slice 5: the station loop

- [ ] 2.5.1 Station elements; Fountain Square imported from `fs_model.py`; walking graph from `fs_reach.py`;
  reachability, step-free, decision points.
- [ ] 2.5.2 **Flows**. Options: (a) static assignment, quickest path with capacity penalties, iterated; (b) a
  time-sliced queueing model per element (captures surges, still no agents); (c) agent simulation (what the games
  do; the most work, the most to tune). Lean: (a) first, (b) if platform surges matter for NFPA 130.
- [ ] 2.5.3 Level of service from Fruin as printed in TCQSM 3rd ed. (looked up and cited), NFPA 130 clearing (4
  and 6 minutes, the standard's rates), the digging index from earthwork volumes and structure costs.
- [ ] 2.5.4 The station workspace: plan per level, section, 3D rebuilt from the model (three.js; Babylon is the
  alternative with no advantage here); the headless sync deleted; the old 3D page retired. Then CUT.

- [ ] 2.5.5 **3D rebuilt from GLBs per section** built server-side once and cached; exaggeration in the vertex
  shader (`y = g + (z − g)·k`); instanced piers, columns and equipment; stencil caps on cutaways; the camera, presets,
  level filter and exports kept from the old page (scrutiny item 8).

### Slice 6: demand and statistics

- [ ] 2.6.1 The ridership model recovered (v17 scripts) or rebuilt from the docs to v17's totals (8,120,167 weekday
  trips, canon), by era and scenario. Options if the scripts are gone: (a) rebuild from the project docs in Python;
  (b) re-implement in SQL over the model's demand tables (DuckDB). Lean: (a), unless (b) is faster for the grid.
- [ ] 2.6.2 Loads to the stringlines, flows to the stations, the statistics tables, the compare pane everywhere.

### Slice 7: hardening and retirement

- [ ] 2.7.1 Exporters: KMZ with levels and structures, LandXML, CSV, sheets as PDF/PNG, glTF.
- [ ] 2.7.2 Performance budgets as tests; the one-command rebuild; byte-identical seeds and goldens.
- [ ] 2.7.3 The old hub removed; README rewritten; Ben's migration note.

## 3. Lane B: the tracks that run alongside

### 3.1 The 1912 ground (local session, `ground/1912/SPEC.md`)

- [~] Registration, contours, surface, checks, done (STATUS.json). Scope: whole survey unless Ben says core first.

### 3.2 Sanborn (local session; nothing re-derived)

- [ ] 3.2.1 Check `Maps\Topography_Export` and `Maps\MCD_Tiles_Snapshot` exist.
- [ ] 3.2.2 Tiles back into `hub/sites/deck/tiles_*` (out of git, checked against the manifest).
- [ ] 3.2.3 Pipeline and picks into the repo (section 3 layout of the migration plan), paths repointed, no rebuild.
- [ ] 3.2.4 Read-only seam report over the existing plates.
- [ ] 3.2.5 New plates one batch at a time, each with its ruling first (Price Hill; Northside and Spring Grove;
  Camp Washington; east and Norwood; basin). Existing streets never move unless the batch's ruling says so.

### 3.3 Bridges and viaducts

- [ ] 3.3.1 Ben's export and `hub_work.zip` for the RER B level on the north viaduct.
- [ ] 3.3.2 The Newport riverfront approach (RER-4 south) still to draw in Google Earth.

### 3.4 Rulings and canon

- [ ] 3.4.1 Tunnel-method rules ratified (the registry shows each as unratified until then).
- [ ] 3.4.2 Fact tracker canon update (r18): the deck dates, the Embankment dates, D/E lettering.
- [ ] 3.4.3 The change catalogue reviewed once the 1912 surface is in: real works dated, errors dropped.

### 3.5 Design work in the tool (once the line sheet exists)

- [ ] RER A dive-under at Union Terminal (r06); Line 14 at Norwood Central (r08); the stacking question at Fountain
  Square (slice 5).

## 4. Checkpoints

A checkpoint when a slice or a lane-B batch lands: Ben exports and pushes `main`; lane A merges `main` into
`hub_region`, reruns every test on the export, reports differences, updates STATUS. Between checkpoints the lanes
do not touch each other's paths.

## 5. Rulings so far

6 November: branch `hub_region`; map 3 to `ground/2026`; ledger years stay `null` where not ruled; the deck done by
1913; Lunken 1937-1941; the interstates about 1940-1965; the kept-works zones fluid with per-zone years; the river at
139.62 m for every year; map 3's river bed is canon; the river bridges page and the C&O/intercity viaduct are part of
the implementation (walls below the track); the 1912 ground re-derived from the sheets as a true 1912 surface;
Sanborn not re-derived; slice order as listed; Line 6 not a milestone of its own; all section 6 leans taken on 6
November (the Deck as street editor now superseded by 9.5); RER B follows the north arch viaduct's deck north of
Northside (the straight grade goes) and leaves it south of Camp Washington on a ramp viaduct of its own, walls below
the track, to the tunnel that meets RER A; the Deck rebuilt as an editor with base and edits kept apart.

## 6. Open rulings (with leans)

- 1912 scope: whole survey (lean) or core first.
- Tunnel-method rules: ratify the ranked list from `Drive_Selection_Root_Causes_2026-11-04.md` as amended on 4
  November (lean: ratify as the engine now has it, then refine from the diff reports).
- D/E lettering: as the Deck and KMZ have it (lean) or as tracker 2M.
- Region box: TRI extent plus 5 km (lean).
- Fountain Square platforms: 400 ft as the editors (lean) or the model's 500 ft.
- `node_modules` out of git (lean: yes, one commit).

## 7. Risks being watched

Engine port drift (baseline diff, goldens); lane B edits during a cutover (checkpoint rule, importers never
overwrite); the Sanborn pipeline's absolute paths (the paths file); rasters outgrowing git (2.0.6); standards figures
from memory (cited before use); the length of the road (each slice usable; order can change at any checkpoint).

## 8. Things deliberately not done

Power-supply load flow and full ETCS braking curves in railsim; animated walkers in the station loop; money in the
digging index; a 3D globe; re-deriving the Sanborn streets; keeping the Python copy of the rules.

- 9.8 **No outside engine** (6 Nov, scrutiny). Context: Ben asked whether to find or code a new engine. Options:
  Civil 3D / OpenRail (geometry only, not scriptable, no canon); OSRD (runs trains, no vertical design); port the
  page; rewrite from the registry. Decision: port the geometry and checks, rewrite the solvers from the registry with
  the 4 Nov code as reference, add what no tool had (horizontal alignment, proposer, quantities). See
  `Code_Scrutiny_2026-11-06.md`.

## 9. Decision records (context, options, decision, consequences)

- 9.1 **Ground as a model, not a raster** (6 Nov). Context: five layers of different ages, two frozen bakes. Options:
  more rasters per era; parametric works composed on a base. Decision: parametric works on the real 1912 base,
  rasters as caches. Consequence: the 1912 surface must be true; the re-derivation.
- 9.2 **Rules engine in TypeScript** (6 Nov, provisional). Options: 2.1.2 a-d. Decision: (a). Consequence: Node in
  the toolchain; Python never re-derives a level.
- 9.3 **FastAPI plus Vite/React** (6 Nov, provisional). Options: 2.0.15 a-c. Decision: (a). Consequence: a
  front-end build step; Range and SSE for free.
- 9.4 **SQLite with hand-written migrations** (6 Nov, provisional). Options: 2.0.7 a-d. Decision: (a).
- 9.5 **The Deck is rebuilt as the street and plot pane in slice 3** (Ben, 6 Nov; replaces the earlier lean to keep
  it). Options: keep as is; fold into the map as a viewer; rebuild as an editor with its data model designed for
  sidewalks and lots. Decision: rebuild, with base and edits kept apart and merged on read (2.3.8 to 2.3.12). The
  old Deck keeps running until the pane has done a real task; the Sanborn pipeline stays a separate importer.
- 9.6 **Dates, layers and zones as data** (6 Nov, Ben). Context: the old hub unravelled on timeline changes.
  Decision: no date, layer, level or geometry in code; ledgers and zone files with per-item years. Consequence: a
  test that a date change is one record edit.
- 9.7 **Sanborn frozen, not re-derived** (6 Nov, Ben). Decision: existing streets, plots and tiles are data; the
  pipeline is kept for new plates only.

## Sources read for section 0

- Walking skeleton and first slice: [hanssamios.com, how to work on the big architectural initiative](https://hanssamios.com/dokuwiki/_export/xhtml/how_do_we_work_on_the_big_architectural_initiative); [Conffab, One does not simply rebuild a product](https://conffab.com/presentation/one-does-not-simply-rebuild-a-product/).
- Decision records: [Docsie, Architectural Decision Record](https://www.docsie.io/blog/glossary/architectural-decision-record/); [OPG Sirius architecture decisions](https://docs.sirius.opg.service.justice.gov.uk/documentation/architecture-decisions).
- Monorepo ownership: [Platzi, monorepos](https://platzi.com/cursos/software-avanzado/monorepos-con-pantsbuild-en-proyectos-re/); [dotclaude decisions wiki](https://github.com/xsyetopz/dotclaude/wiki/Decisions-Architecture).
- Big geospatial data and git: [DVC for geospatial training data](https://geospatialannotation-com.pages.dev/dataset-versioning-spatial-data-sync/implementing-dvc-for-geospatial-training-data/); [versioning large imagery](https://geospatialannotation-com.pages.dev/dataset-versioning-spatial-data-sync/implementing-dvc-for-geospatial-training-data/how-to-version-control-large-satellite-imagery-datasets/); [Hacker News thread](https://example-ecru-phi.vercel.app/item/41888937). These are secondary sources; the practice (manifests, pointers, derived tiles under the size limit) is what we already do.
