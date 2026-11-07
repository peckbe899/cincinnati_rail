# The hub rebuild: the plan in one place

Written 7 November 2026 on branch `hub_region`. This is the front door: what we are trying to do, why, how, where it
stands, and what comes next. The detail lives in four other files and this one points at them:

| File | What it holds |
|---|---|
| `Hub_Region_Roadmap_2026-11-06.md` | the architecture and the verification system, in full |
| `Hub_Region_Checklist.md` | the living board: every item, its options and lean, rulings, decision records |
| `Code_Scrutiny_2026-11-06.md` | what in the old code is kept, rewritten or dropped, and why |
| `STATUS.md` | what each session is doing right now and what it is blocked on |

## 1. What we are trying to do

Turn the Cincinnati Rail hub from four ported artifact pages tied together by batch jobs into one design tool a transit
engineer would use, covering the whole region (every Metro line, every TRI line to its termini, the other systems as
context, every era from 1905 to today), built around tests at three scales:

- **a line**: change a station level, a bend point, a structure, and see the run time, the seconds lost per
  restriction, the checks and the quantities on the drawing within seconds;
- **a station**: lay out halls, flights, lifts and gates, load the rush hour, and see where it jams, how long each
  transfer takes, whether every route is step-free, and what it costs to dig;
- **the network**: set services, patterns and headways by era, and see stringlines, blocking time, the minimum headway
  on every trunk, the fleet and the loads.

Underneath: one model of the railway and its ground, every rule written once with its ruling, Ben's inputs final and
flagged rather than overridden, every parameter a dated record rather than a number in code, every result derived and
cached, and the whole thing rebuildable from git plus Ben's export in one command.

## 2. Why: what went wrong before

- The first tools (the KMZ stitcher, the elevation extractor, the v9 travel-time calculator, the profile analyser)
  formed one chain, line to ground to profile to run time, with standard engineering outputs. The hub kept the building
  and the viewing and dropped the test at the end: run time never reached it, and every edit ended in a two-minute 3D
  rebuild with no score.
- The line existed three times (Deck pieces, Profiles paths, the KMZ), the rules three times (the page, a hand-kept
  Python copy, and a headless browser sampling the page), and the ground five times (LiDAR, a one-off bake, the Deck's
  regrade, per-line drawn lines, context runs), none of them dated.
- Ben's paints and selections were inputs to a stack of passes, so later passes overrode them; decisions were made per
  2 m sample on raw ground with hard thresholds; keys were made of names and coordinates, so a rename orphaned edits;
  saves wrote whole documents; derived files were committed; and timeline changes unravelled because dates lived in
  code.
- The detailed tools covered 4.7 % of the TRI region, and runs outside the core fetched ground from the internet and
  fell back to flat when it failed.

## 3. How: the design in short

**One model** (`region/model`, SQLite): nodes and sections with chainage, routes and services, stations with stops,
platforms and elements, structures as ranges on sections, bridges and earthworks as parametric objects, ground layers
by era, context, eras, rules and rulings, named versions, cached results, issues. Every record has an id that never
changes, a version that every write must carry, full history, a source, and years where it is something built. Old
keys resolve through a legacy table. Seeds for git are one file per record and merge instead of overwrite.

**Ground as a model, not a raster** (`region/ground`, built): the real 1912 surface as the base (being re-derived from
the survey sheets now), every work after it a dated layer, raster today and parametric (pad, corridor) from now on,
composed for any year and timeline with provenance per cell and cut and fill volumes. Map 3 becomes a cache.

**Two engines, one contract**: the rules (geometry, levels, structures, checks) in one pure TypeScript function that
runs in the browser for live editing and under Node for jobs, with a rule id on every stretch and flag; the analysis
(railsim, blocking time, flows, demand) in Python, reading solved sections through a versioned JSON schema and never
re-deriving a level. No browser is ever a calculator again.

**A rule registry** (`rules/registry.yaml`, built: 137 rules, 163 parameters): each rule with its text, its ruling,
its status (ratified, provisional, unratified), its rank inside a named decision so conflicts never depend on pass
order, and the parameters it reads by record path. The eleven tunnel-method rules were ratified on 6 November.

**One app** with linked panes on one URL state: region map (MapLibre, PMTiles for the static layers), line sheet,
section, station workspace (three.js), service view, tables, issues, compare; plus the street and plot editor
rebuilt as a pane with base and edits kept apart and merged on read, sidewalks, and lots that can become buildings.

**A job graph** keyed by input hash and engine version, so an edit re-solves only what it touches and nothing waits
minutes.

**Verification as a system**: unit, golden and invariant tests (every rule over every route on Ben's export),
calibration gates with real tolerances (built), round trips for every importer, browser tests, performance budgets,
rule coverage, and a one-command rebuild that must come out byte-identical.

## 4. How we work

Two lanes that own disjoint paths and meet only through written contracts:

- **Lane A, build**: cloud sessions on `hub_region`, one slice at a time, each with a brief naming inputs, outputs,
  exit tests and the paths it may touch. Owns `region/`, `engine/`, `app/`, `rules/`, `tests/`, `ground/` code.
- **Lane B, use**: Ben and local sessions on his machine (anything that needs his files): the 1912 ground, the
  Sanborn plates, profile and Deck edits, canon rulings. Owns `hub/seed`, `data/`, `hub/sites/deck`, `tools/sanborn`,
  `data/sanborn`, `design/`.

Rules: a spec before every handoff (`ground/1912/SPEC.md` is the pattern); done means pushed and reported with
numbers; no page is retired until its replacement has done a real task; Ben's data is never overwritten; rulings are
batched and become records the same day; `STATUS.md` is updated by whichever session finishes.

## 5. The slices (what, when, why then)

| # | Slice | Why in this place | Retires |
|---|---|---|---|
| 0 | Foundations and ground: the ground model, the 1912 surface, the baseline, the gates, the registry, the schema, the bridges as records, the app shell | everything later reads these; the baseline can only be captured before the engine moves | nothing |
| 1 | Metro: the engine lifted to TypeScript, the contract, railsim on solved sections, the line sheet, every Metro line imported, invariant tests, the Deck adapter | the first usable loop, on one line first and then all 17; proves engine, contract and sheet together | the Profiles page for Metro; `metro_profile.py` |
| 2 | TRI, region-wide, offline: corridor and region ground tiers, outer sections with seams at the Deck-region edge, all 31 services with no internet | the slowest, least reliable thing in the old setup, fixed right after Metro and before any new feature | the Profiles page |
| 3 | Region map, eras, structures, issues, tables; the street and plot editor rebuilt | needs the model full; both later loops draw on this map | Chronology, Access, the old Deck |
| 4 | Network loop: services, timetables, blocking time, headways, fleet, stringlines | needs run times on every service and the map; no new input from Ben | nothing |
| 5 | Station loop: elements, Fountain Square, flows, level of service, NFPA 130, digging index; 3D rebuilt from the model | needs the demand tables; the 3D is rebuilt once from a finished model | Station 3D, the headless sync |
| 6 | Demand and statistics: the ridership model by era and scenario, loads on the network, the compare pane | last engine, everything it feeds exists; its inputs are the least certain | nothing |
| 7 | Hardening and retirement: exporters, budgets, the one-command rebuild, the old hub removed | nothing is removed until replaced and used | the old hub |

Each slice ends with its exit tests, a plain report with the numbers, a log row, a push, and a stop.

## 6. Where it stands (7 November)

Done in slice 0: `ground/` consolidated and map 3 moved; `region.ground` (compositor, parametric works, sampling,
tests, the whole-extent check and the change catalogue); dates, layers and zones as data; the roadmap, checklist,
scrutiny and this plan; the baseline (41 routes every 5 m, 17 Metro run times, the old 3D issues); the calibration
gates as tests; the rule registry with the tunnel-method rules ratified; the model schema with tests (96 tests
pass). Rulings taken this week are in the checklist, section 5.

In flight, lane B: the real 1912 surface (registration done on 48 sheets, rms 2.06 m; contours in progress); the
Sanborn plates (tiles back, pipeline and picks in the repo, the complete control set read, the joined fit chosen,
the apply in progress). Open there: the Deck tie failed on Ben's hub (log awaited); the 1912 session has not pushed
in a day.

Next in lane A: the engine package and the geometry port with golden tests against the baseline; the Metro importers;
the API and the line sheet on one line.

## 7. What we decided not to do

Buy or borrow an alignment engine (none covers canon, eras and the tunnel-method rules; LandXML export covers
drawings); re-derive the Sanborn streets (frozen as data; the pipeline adds plates); power-supply load flow and full
ETCS curves in railsim; animated walkers; money in the digging index; a 3D globe; keeping the Python copy of the rules.

## 8. Open rulings

Listed with leans in the checklist, section 6. None blocks the current work.
