# Engine port plan: the rest of the old Rail Profiles page (I2.2 and the C items that need the engine)

Written 23 November 2026, branch `hub_region` (after 3ef7a38), for the lead and the four porting sessions. It answers
Ben's verdict ("The station profiles are still inferior to the old rail profile ... That's the baseline on which to
improve") for everything between the stations: the structure solver, the ground, rivers and viaducts, canon and
locks, crossings, context and roads, the checks and issues, the level solver and the doc normalisation. Standing
rule: a pane is done only at item-by-item parity with the old page, and the whole page is the baseline.

Read with: `claude/hub_maps/profiles_parity.md` (the matrix: A stations done, B later, C the rest, R1 to R65),
`claude/hub_maps/profiles.md` (the map of the old page by line), `claude/Hub_Region_Architecture.md` (sections 7 and
11), `claude/Hub_Region_Checklist.md` (I2.1, I2.2). Bare line numbers below are in `data/profile/profiles.html`.

Scope: the 16 Metro lines (Lines 1 to 14, 2b and the CVG Express; Lines 10, 11 and 13 have no saved profile). RER
lines are slice 2: every type and signature here carries what the RER needs (system, settings_rer, modes, open
types, shore rivers) so nothing has to be redesigned for it, but no RER test is in these packages.

## 0. In short

- **The golden harness is built.** `engine/test/golden/old_page/<Line>.json.gz` (16 files, 1.8 MB) hold everything
  the old page computes for each Metro line, from a scratch copy of the old hub with one harness line in its copy
  of the page. `load.ts` reads them; `engine/test/old_page.test.ts` checks them (17 tests, passing); the script is
  `engine/scripts/old_page_dump.mjs`; how to make them again is `engine/test/golden/old_page/README.md` (section 2).
- **The shared types are written.** `engine/src/port/types.ts` compiles clean and passes the source lint (no
  numeric literal, no clock): the input additions, the normalised model, every package's outputs, the solved
  additions and three module interfaces for stand-ins.
- **Four packages, built in parallel.** P1 the structure solver and type lookup, P2 ground, rivers, viaducts and
  canon, P3 crossings, context and roads, P4 checks, issues, fill and levels. Each takes data, not another
  package's functions, and every intermediate value it needs is in the goldens, so each is built and tested alone.
  P1 lands its small table functions first (P1a, a day), then P2, P3, P4 and the P1 solver (P1b) run at once.
- **One new method, run after the fast rail.** `section.solve@1` (input `section_solve_input/0`, output
  `solved_section/0`) runs in the sheet's worker after `vertical.rail@1` and `station.facts@1`, never during a drag;
  the 16 ms rail re-solve and the always-live budgets do not change (section 8).
- **Every check cites a rule id** of `rules/registry.yaml`. Two checks have no rule and are reported, not added
  (section 9); seventeen values the port reads have no param in the registry and are reported too (section 3.4).
- **Exit (I2.2):** zero unexplained differences against the goldens on the 16 Metro lines, output by output, within
  the tolerances of section 6, and every difference classed same, rule fix (with its rule id) or intended.

## 1. What is ported, what is left, and what Ben sees

Ported: `vertical.rail@1` (vertices, design, railAt, gradeAt, the 2 m rail grid: 725-828), and `station.facts@1`
(each station's provisional type, access, platform curve, street and station flags: parts of 458-535, 1246-1276,
1384-1403, 2013-2101). Everything else in 330-2275 is this plan. The side-by-side check of the last round
(`side_Line_6_full.png`, `side_Line_6_Bond_Hill.png`) maps onto it like this:

| Found side by side | What draws it | Package |
|---|---|---|
| Plot about 590 px wide against 1,230, short; a third of the names dropped at whole-line view; station bars in the bend points' pink under pink circles; the station panel scrolls | sheet page work, not the engine (tasks P2-1 to P2-6 of the sheet session) | sheet |
| The rail drawn one colour between stations, where the old page coloured it by structure | `types.type` (the solved type per 2 m) and `structBelow`, `structTop` | P1 |
| Tunnel and box outlines | `structBelow`, `structTop`, `types.tube`, `types.part` (approach boxes) | P1 |
| Dashed cover and limit lines (the legal band) | `limitTube`, `limitBox` | P1 |
| The structure band | `types.type` as runs | P1 |
| Other lines crossing, with ticks and clearance boxes | `crossings[]` with the other rail `zo`, both structures, `need`, `ok` | P3 |
| Streets and roads | `streets[]` (per station), `roads[]` and the context's streets and roads | P3 |
| Context structures at CUT and Norwood | `context[]` and the blocks | P3 |
| Water, made-up bed, channel, viaducts | `rivers[]`, `madeBed`, `spans[]` | P2 |
| The Chronology band | I2.4 (the Chronology import), not this plan | none |
| The unbuildable hatch | `types.bad`, `misfits[]` | P1 |
| Every issue marker | `flags[]` | P4 |
| Station type in a draft read a stale canon (bug A) | fixed by the sheet session with `engine/src/station/live.ts`; P2's `buildCanon` resolves the canon from the draft's live stations on every solve and replaces it | P2 |

The C items this unlocks: R14, R22 to R38, R42, R43, R47, R52, R54 to R61, R3 and R6 (reframe and derived fields),
R20's Reset this line. R44 (Chronology) is I2.4; R65 (RER junctions) is slice 2; R56's Lower and Raise and R57's
Solve levels with crossings are proposers (`regradeDrive` 3601, `solveCross` 3693): section 7.6.

## 2. The golden harness (built)

**Files.** `engine/test/golden/old_page/`: `<Line>.json.gz` for the 16 Metro lines, `index.json` (each file's
sha256 of its JSON text, size, grid size, issue count; the sha256 of every source the page read), `load.ts`,
`README.md`. `engine/test/old_page.test.ts` checks: all 16 lines; `sources.page_sha256` equals the repository's
`data/profile/profiles.html`; every file matches its index; every per-2 m list covers the grid; the solved rail of
the type solve is the rail; the ground runs are single-precision values; every issue is tied to its source list
with a range; docless lines' align is their default levels.

**How they were made.** A scratch copy of the old hub (`hub/hub.py`, `store.py`, `pipeline.py`, `seed`, `sites`,
`static`), `data/profile` and `tools/station3d/page` under the session's scratch folder; the dump script writes one
line into the copy's page (`--patch`, refusing any file in the repository) that hands the IIFE's state, 44 tables
and globals and 138 functions to the harness as `window.__P`; the old hub runs on the copy with `--no-auto`; the
script drives the page with the repository's Playwright and writes the files. About 20 s for 16 lines. Two runs give
the same bytes. Nothing in `hub/`, `data/` or the repository's page was touched, and the scratch hub was stopped.

**What is in each file** (full table in the README): the effective settings; `align` after `alignFromDoc` and
`changed()`; each station with its key, point, centre, rail, sg, so, stt, reference level, ground, type, the
solver's role and platform default, phase, year, access, platform curve and street; on the 2 m grid the rail,
grade, type, the solver's own type, tube and part, tube key, phase, pointType, paint, canon section, lock, tube
form, station, grade limit, the structure at the rail, the two limit lines and five ground layers; radii and curve
allowance on their 10 m grid; the solver's unbuildable stretches, platform defaults, roles, shafts, flags and
approaches; effOvr; the Chronology segments; the canon model; rivers with bed, bands and bridges; the sunk box;
viaduct spans; misfits; crossings with the neighbour each was read from; context clearances; roads; the other lines'
ground; ground checks; drawing flags; curve grade ranges; designChecks; computeSummary; allIssues with c, c0, c1,
severity, text, fix, clear and propose; the default levels (`defaultAlign` as alignFromDoc calls it), reframeDoc on
the saved doc, every Propose fill the issues offer (each undone at once), and Reset this line.

Counts on the seed: 2,172 issues over the 16 lines (Tunnel method 947, Platform curve 178, Clearance 143, Thin cover
122, Road 81, Cover 80, Painted 78, Drainage 73, Unbuildable 70, Access 69, Approach box 69, Low cover 69, Drawing 48,
Vertical curve 40, Curve grade 35, Canon 24, Grade 16, Platform grade 7, Platform slide 7, Tube form 7, River 4,
Ground 3, Context 2); 430 crossings (395 read the other line's saved profile, 35 the stale `rer/metro_rails.json`);
118 Propose fill proposals; Line 2b the one Metro line reframed on load.

**How the port uses it.** Each package's tests build their input from a golden plus read-only repository files,
through one shared adapter, `engine/test/port/from_golden.ts` (P1 writes it first, section 7.1):

```ts
/** The port's input and model for one line, as the old page had them: the input from the line file, the seed
 * doc, hub/seed/params (metro_structure, station_platforms, station_complexes, approach_extra), context/lines.json,
 * the golden's canon_record (until the canon kind lands) and the neighbours' seed docs (all read only); the
 * model's P2 and P4 parts from the golden (ground layers, canon, rivers, align, curve arrays), so a package is
 * tested on the old page's own upstream. */
export function fromGolden(line: string): { dump: OldPageDump; input: PortInput; model: SectionModel };
/** The model with the old page's type solve laid in (grid.solved, solve.*): what P2's spans, P3 and P4 read. */
export function typedFromGolden(line: string): TypedModel;
/** TypesModule answered from the golden: typeAt(c) is the solved type at round(c / 2), as autoType reads it within
 * 0.3 m of the solved rail; structFor, reqCover, phaseAt, phaseRules from P1a once it lands. */
export function goldenTypes(dump: OldPageDump): TypesModule;
```

**The report.** Each package writes `engine/test/port/report/<package>.json` per line and output: equal, or each
difference with where it is and its class (`same` within tolerance, `rule_fix` with a rule id, `intended` with the
parity matrix item, `unexplained`). The class of a known difference lives in `engine/test/port/classes.yaml`
(line, output, range, class, rule, note) and is reviewed like a golden update: no rule id, no class. The test fails
on any `unexplained`.

## 3. The input additions

### 3.1 `PortInput` (in `types.ts`), member by member

`SectionInput` (vertical.rail@1) and `StationInput` (station.facts@1) stay as they are; `section.solve@1` takes a
`section_solve_input/0` built from the same records plus these. "exists" means Python already reads it for
`station_input` (region/ext/profiles/inputs.py).

| Member | Type | The page read | From records | Status |
|---|---|---|---|---|
| `section_id`, `route`, `system`, `length`, `step`, `path` | scalars, `PathPoint[]` | `S.data` | `section` (id, key, system, length_m, step_m, path) | exists |
| `pieces` | `{name, c0, c1}[]` | `d.pieces` (pieceAt 2059, piece_phase) | `section.pieces` | exists in the record; new in the input |
| `dem` | `Float32Array` | `groundOf` 3373 | `ground_profile` (ground_dm / 10) | exists |
| `platforms` | `PortPlatform[]` (key, point, side, year, year phase, transfer at opening, trunk) | `S.data.stations`, ST_PLAT, CHR, ST_CPLX | `stop`, `platform` (side), `chronology`, `station_complex` | exists (as `StationInput.platforms`); `transferAtOpen` and `trunk` new |
| `doc` | `PortDoc` | `S.saved[id]` | `profile` v2: st, sg, so, del, pvi, ovr, stt, tf, shafts, gnd, gapfill, mode, ready, frame | exists in the record; pvi, tf, shafts, frame new in the input |
| `settings` | `PortSettings` | `settings` (277, 585) | params `settings.*` by section scope, CVG overlay param | exists (`params_of`, `STATION_PARAMS`); the rest of the 28 keys new |
| `literals` | `PortLiterals` | named and unnamed literals | params `literal.*` (section 3.4) | partly exists (`LITERALS`) |
| `structure` | `StructureParams` | MS (applyMS 1065) | params `metro_structure.*`, else `hub/seed/params/metro_structure.json` as `structure_of` does | exists (`structure_of`); line_phase and piece_phase resolved for the route, cost, grades, approach_m, portal_min_m, min_radius, box inside and spacing, island spacing, tube spacing new |
| `era` | `Era` | ERA 1186 | params `literal.ERA.sgMax.*`; the shield only matters without the record (never on the Metro) | exists (sgMax) |
| `canon` | `CanonRecord` | CANON 293-323, RER_CANON | **new kind `canon`** (section 3.2) | new |
| `rivers` | `RiverRecord[]` | `d.rivers`, RIVERS (rer/canon.json rivers) | `section.rivers` plus params `canon.rivers.<name>.*` | ranges exist; properties partly in the registry (section 3.4) |
| `context` | `ContextRecord` | CONTEXT.lines[id] | `section_context` (streets, roads, add, cap) and **blocks** (today in `attrs`) | blocks promoted to a field, kind v2 (section 3.2) |
| `crossings` | `CrossingRecord[]` | `d.crossings`, linkRerCrossings 3395 | `section.crossings` (c, wid, oc, kind, with, other) | exists |
| `neighbours` | `Record<wid, Neighbour>` | `S.saved`, `S.defaultDocs`, `S.metroRails` (otherRail 2182) | built by Python per crossing (section 3.3) | new |
| `chronology` | `ChrSegment[]` | chrSegments 1077 | `chronology` (`Chronology.line_segments`) | exists (`chron_segments`) |
| `approachExtra` | `ApproachExtra[]` | APX_EXTRA 1293 | `hub/seed/params/approach_extra.json` (Lines 5 and 13) as a new param `station.approach_extra` scoped to the route, imported by `old_hub` | new |

The halls the cover and crossing checks run over (`hallAt` 536) are not an input: they come from station facts on
the solved types (`SectionModel.halls`, section 8).

### 3.2 New and changed records

- **`canon` v1 (new kind, region/ext/profiles/kinds/canon.yaml).** One record per route, parent the route, merge
  unit `field`. Data: `sections` [{a, b, aIn, bIn, m, src}], `fixed` {station name: {abs | off, ref?, src}},
  `modes` {name: {mode, src}}, `locked` [{c0, c1, st, pvi, ovr, src, name?}], `bridges` {river: {fixed?, clear?,
  src}}, `decks` [{name, pvi [[lon, lat, z]], piers [[lon, lat]], src}]. The `old_hub` importer writes the Metro
  ones from a transcription of 293-323 kept beside the importer (it is code in the page, not a file; the
  transcription carries each `src` and is checked against the golden's `canon_record`), and later the RER ones from
  `data/profile/rer/canon.json` (slice 2). `inputs.py CANON_SECTIONS` then goes. Ben edits canon only through a
  draft on his layer, with If-Match; a lock or fixed level never overrides his record silently: it is applied in the
  solve (applyLocks) and the difference is a flag, as `network.canon.locks` says.
- **`section_context` v2.** `blocks` becomes a field (the `ContextBlock` shape: n, l, k, st, c0, c1, p, b, t, o,
  pl, s, gaps), additive; the upgrader moves it out of `attrs`.
- **`profile` v2** already carries every field. The port reads `frame` (reframeDoc) and `ready` (crossings apart).
- **Params.** `station.approach_extra` (route scope) and the missing literals and canon river params of 3.4, each
  added to the registry by the lead with a ruling, never by a porting session.

### 3.3 Neighbours

For each crossing whose `other` section is in the hub, Python builds a `Neighbour` from that section's records:
its live stations (stops plus slides, deleted ones out), their levels (`st`, else the neighbour's own default
levels), platform grades, `pvi`, drawn ground lines, streets (its `section_context`), `ready`, `line_phase`, the
settings `kindAt` reads, and its platform length and vertical curve params. The other line's default levels come
from its own `section.solve@1` result (`levels.st`), which does not depend on crossings (`defaultAlign` with no
extra nodes), so there is no cycle; the neighbour result's hash goes into this section's cache key, so a change on
Line 3 re-solves the lines crossing it and nothing else. `solved` (its solved type and structure at the crossing)
is sent when the neighbour has a result; whether the check reads it or guesses from depth, as the page does, is
`clearance.crossing.other_line_guessed` (unratified): P3 ports the guess first, for parity, and the switch is a
later rule change classed as a rule fix. For parity on the 35 crossings with Lines 10, 11 and 13, the golden
adapter builds those neighbours from `data/profile/rer/metro_rails.json` (`source: "metro_rails"`); production
never reads that stale file.

### 3.4 Literals and params

Each value the port reads comes from a param (decision 9.25); a number the lint allows in the engine is a sampling
step or a tolerance, named in `src/tol.ts`.

| `PortLiterals` member | Page | Param |
|---|---|---|
| MIN_RUN, BOX_COVER, SEP_GAP, BED_DEPTH, VIA_SPAN, VIA_CLEAR, RIVER_SPAN, GIRDER_MAX, GND_W, SLIDE_M, CAR_LEN, END_DOOR, PLAT_R_ERR, PLAT_R_WARN | 1298, 1185, 953, 664, 1838, 2008 | `literal.<name>` |
| DRAW.single, kink, back, sErr | 2047 | `literal.DRAW.*` |
| openClear | 1199, 1070 | `literal.OPEN_CLEAR.metro` / `.rer`, `metro_structure.open_clear_height` |
| bridgeAbovePool, autoTypeRailTol, drainageMinLen, approachHold, coverHardFallback, minDriveFallback, minRadiusFallback, portalMinFallback, tubeStreetNoteLen, fillOver, fillBand.above, platformOverlap, limitTol, lowCoverMinShort, hall.* | 1255, 1607, 2107, 1474, 1475, 1241, 1292, 1392, 1550, 1708, 1715, 2101, 1401, 1535, 528 | `literal.bridge_above_pool`, `autoType_rail_tol`, `drainage_min_len`, `approach_K_window`, `cover_hard_fallback`, `min_drive_fallback`, `min_radius_fallback`, `portal_min_fallback`, `tube_street_note_len`, `fill_over`, `fill_band`, `platform_overlap`, `station_limit_tol`, `low_cover_min_short`, `hall.end_halls_len`, `hall.mezzanine_fraction` |
| radii.h | 1952 | `literal.radii_window` (40 m, so h = 40 / step) |

**Missing from the registry (reported, not added):**

1. `literal.DECK_ON` (5 m: a deck pier within this of the path puts the line on the bridge, 864).
2. `literal.DRAW.nb` (2), `literal.DRAW.kinkSeg` (10 m), `literal.DRAW.sWarn` (2; `inputs.py` falls back to 2).
3. `literal.girder_soffit` is the expression `span / 10 + 0.8`: it needs two numbers (ratio 10, add 0.8), and
   `literal.truss_depth` the same (ratio 8).
4. `literal.approach_m` fallback (40) and `literal.fill_band.below` (0.5 m under the ground, 1715).
5. `canon.rivers.Licking River.*` and `canon.rivers.Ohio River.in_covered_way`, `bed_below_pool_m` (null: the bed
   from the ground): the Licking is crossed by Lines 6 and 11 and has no params at all.
6. The road bridge deck over a trough (0.8 m, 2269), the context level-crossing tolerance (1.0 m, 2229), the
   approach box street search (300 m, 1540), the bridge pier search (400 m, 972), the pier-before-crossing rule
   (`VIA_SPAN * 1.6` and 3 m, 982), the sumps' flat grade (0.5 per mille, 2112): design values written as numbers.

Sampling steps that are not design values go to `src/tol.ts`, named, each with its page line: the 10 m check grid
(1159, 1901, 1989, 2118), 5 m sustained step and its 10 m inner step (1168, 1175), the 20 m join of ranges (2116,
1995), the 2 m platform resample (2033), Propose fill's 60-sample search and 2-sample margin (1719, 1700), the 0.5,
0.05, 0.02, 0.005 and 1e-6 tolerances.

## 4. The solved additions

`PortSolved` (in `types.ts`) is what `section.solve@1` gives, as contract `solved_section/0`. Arrays on the grid
travel as typed arrays inside the worker (structured clone) and as run-length lists or number arrays in JSON to and
from Python; categorical arrays carry their table.

| Member | What | The page | Draws (parity item) |
|---|---|---|---|
| `align`, `stations` | the normalised profile and live stations | S.align, S.stations | everything |
| `rail` | the existing design and its arrays | VERTS, railAt | the rail |
| `ground` | dem, regraded, finished, surface, bed (Float32), drawn lines, other lines' ground | 636-712 | R23, R24, R40 |
| `types.type`, `.tube`, `.part`, `.phase`, `.role` | the solved type, tube, approach and station parts, phase per 2 m | stretchTypes 1597 | R28, R30, R43, the structure band |
| `structBelow`, `structTop` | the structure at the rail per 2 m (structFor of the type) | 2462-2484 | R14, R30, tunnel and box outlines |
| `limitTube`, `limitBox` | the legal band: shallowest tube, deepest box | 2525-2532 | R33 |
| `types.bad`, `misfits` | unbuildable stretches; paints and selections that cannot be built | 1558, 1637 | R34, the hatch |
| `types.approaches`, `.platDef`, `.stRole`, `.shafts`, `.stretches` | approach boxes; platform defaults; roles; shafts; one decision per stretch | 1431, 1574, 1520 | S7, S63, R61 |
| `madeBed`, `rivers` | made-up bed; river bands, bridge bands, navigable level | 1017, 1032, 993 | R22, R31, R32 |
| `spans` | viaduct spans: girder or truss, soffit, ends | 954 | R36 |
| `canon` | sections, fixed levels, locks, piers | 876 | R27, R61 |
| `gradeLimit.lim`, `.warn` | the grade limit per 2 m | 1142 | R29, R37 |
| `radii`, `allowance` | plan radius and curve allowance, 10 m | 1952, 1975 | R38, R47 |
| `crossings`, `context`, `roads`, `streets` | clearances with both structures; context blocks; road checks; each station's street | 2235, 2219, 2263, 458 | R25, R26, R35 |
| `summary` | metres by type, deepest, highest, steepest, grades over, sumps, deep stations in shallow canon | 1900 | R52, R6 |
| `flags` | every finding with its rule id, fix, propose and clear | 2143 | R42, R54, R55, R56 to R59 |
| `levels` | the level solver's station levels and river bend points; unset stations flagged | 1756 | S55, S57, R20 |

The old doc's derived `stations` and `summary` (serialize 3213) are made from `stations`, `types` and `summary` by
the exporter, never stored (profile record, section 4 of the architecture).

## 5. The module split and the signatures

```
engine/src/port/
  types.ts                 shared types (done)
  util.ts                  P1   rangesOf, cutRange, rle, codes, clamp (shared helpers; signatures below)
  structure/               P1   tables.ts phase.ts structure.ts grade.ts point.ts solve.ts lookup.ts fit.ts
  ground/                  P2   layers.ts rivers.ts viaduct.ts canon.ts
  crossings/               P3   other.ts clearances.ts roads.ts
  checks/                  P4   curve.ts drawing.ts summary.ts design.ts issues.ts fill.ts ground_checks.ts
  levels/                  P4   levels.ts doc.ts
  model.ts                 lead buildModel(input, facts): SectionModel  (the build order of section 8)
  solve.ts                 lead solveSection(input): PortSolved; the section.solve@1 row in methods.ts
```

Every function is pure: it reads its arguments and returns new values; nothing is cached on an argument (the page
cached on `VERTS._types`, `d._R`, `MEMO`); the orchestrator caches by input identity. Each package exports a
`<PKG>_RULES` list (`as const satisfies readonly RuleId[]`), as `station/facts.ts` does, and every flag it raises
cites one of them.

### 5.0 Shared helpers (P1, day 1)

```ts
export const clamp: (v: number, a: number, b: number) => number;                                       // 602
export function rangesOf<T>(arr: readonly T[], a: number, b: number, pred: (x: T, i: number) => boolean): [number, number][]; // 613
export function cutRange<T extends string>(list: readonly Range3<T>[], a: number, b: number): Range3<T>[]; // 615 (exists in station/facts.ts: moves here)
export function codes<T>(table: readonly T[], values: readonly T[]): CodedArray<T>;
export function valueAt<T>(a: CodedArray<T>, i: number): T;
export function runs<T>(a: CodedArray<T>): [T, number, number][];                                       // [value, i0, i1] for drawing and the band
export function gridOf(length: number, step: number): Grid;                                             // src/grid.ts gridSize, gridChainage
export function nearestIndex(g: Grid, c: number): number;                                               // Math.round(c / step) held to the grid, as autoType (JS rounds halves up)
```

### 5.1 P1 types (`structure/`)

```ts
// tables.ts
export function applyMS(s: StructureParams, openClear: number): StructureTables;                       // 1063-1071 (tubeOf 1063)
export function sgMaxFor(m: SectionModel): number;                                                      // 1227 (ERA 1186 arrives as input.era)
// phase.ts
export function phaseAt(m: SectionModel, c: number): Phase;                                             // 1091-1106: a station's platform the earlier-opened segment either side; else the segment; else piece_phase, line_phase, later
export function phaseRules(m: SectionModel, c: number, ph?: Phase): PhaseRules;                        // 1239-1243
export function methodAt(m: SectionModel, c: number): "shield" | "deep";                                // 1245
export function tubeFormAt(m: SectionModel, c: number): TubeForm | null;                               // 1124 (last tf range wins)
export function twinOf(ph: Phase): "A" | "C";                                                           // 1117
export function metroTube(m: SectionModel, c: number): Structure;                                       // 1108-1116
// structure.ts
export function structFor(m: SectionModel, t: Type, c: number, tube?: TubeKey | null): Structure;      // 1202-1214; tube is the solve's (drivenTube 1126), absent during the solve
export function reqCover(m: SectionModel, s: Structure): number;                                        // 1215-1220
export function openTop(m: SectionModel): number;                                                       // 1200
export function elevNeed(m: SectionModel): number;                                                      // 271
// grade.ts
export function straightUnder(m: TypedModel, c: number): boolean;                                       // 1134-1140
export function gradeLimitAt(m: TypedModel, c: number): GradeLimit;                                     // 1142-1155
export function gradeLimitOver(m: TypedModel, c0: number, c1: number): GradeLimit;                      // 1157-1165
export function sustainedGrade(m: SectionModel, c0: number, c1: number, comp?: boolean): GradeOver["sustained"]; // 1167-1179
export function gradeSeverity(L: GradeLimit, sus: number): GradeOver["sev"];                            // 1180-1184
// point.ts
export function pointType(m: SectionModel, c: number, z: number): PointType;                            // 1246-1276 (a platform point takes its centre's)
export function approachExtra(m: SectionModel, info: Pick<Approach, "station" | "side" | "c">): number; // 1293
export function approachLen(m: SectionModel, shift: number, c: number, info: Pick<Approach, "station" | "side" | "c"> | null): number; // 1294
export function absorbShort<P extends { c: number; t: Type | undefined }>(P: P[], step: number, minRun: number,
  free: (p: P) => boolean, edgeOk?: (q: P) => boolean, canTake?: (p: P, t: Type) => boolean): void;    // 1299-1317 (mutates its own work array only)
// solve.ts
export function solveTypes(m: SectionModel): TypeSolve;                                                 // 1360-1604
export function openTypes(m: SectionModel): TypeSolve;                                                  // 1319-1331, RER (slice 2; signature only)
// lookup.ts
export function effOvr(stations: readonly LiveStation[], align: Align, locks: readonly Lock[], platform: number, metro: boolean): Range3<Type>[]; // 837-850
export function overrideAt(m: SectionModel, c: number): Type | null;                                    // 833 (last range wins)
export function sttFromDoc(doc: PortDoc | null, stations: readonly LiveStation[], ovr: readonly Range3[]): (SelectedType | "")[]; // 852-861
export function autoType(m: TypedModel, c: number, z: number): Type;                                    // 1605-1610
export function typeAt(m: TypedModel, c: number, z?: number): Type;                                     // 1669-1676
export function typeArray(m: TypedModel): Codes;                                                        // typeAt at every c_i: the drawn band
export function tubeKeyAt(m: TypedModel, c: number): TubeKey | null;                                    // 1119-1123
export const TYPES_MODULE: TypesModule;                                                                 // the functions above, for P2 to P4
// fit.ts
export function fitLim(m: TypedModel, t: Type, why: Misfit["why"]): (c: number) => number;              // 1624
export function fitOf(m: TypedModel, t: Type, c: number, z: number, stn: boolean): { why: Misfit["why"]; by: number } | null; // 1627-1636
export function paintMisfits(m: TypedModel): Misfit[];                                                  // 1637-1665
```

Notes for the port:
- `solveTypes` runs on a work array of samples `{c, z, ph, R, t, role, d, paint, canon, stn, appr, bank, tube,
  shaftAt}` and returns the arrays; its flags become `PortFlag` (section 9) and are deduplicated (each "mined station
  inside a cut-and-cover stretch" flag is pushed once per 2 m sample on the page, 61 copies per station).
- `structFor` during the solve has no tube (the page's `SOLVING` makes `drivenTube` null); after it, the solve's
  tube. `typeAt` reads the solve at `round(c / 2)` only within `autoTypeRailTol` of the solved rail, else
  `pointType`, exactly as 1605-1610 (`geometry.band.engine_is_the_drawing`).
- Ground, radii and curve allowance are Float32 as on the page, so every comparison falls the same way.
- `gradeLimitAt` reads `m.curve.allowance` (P4's arrays, in the model) and `typeAt`; it is P1's because the limit is
  the phase's.
- `sttFromDoc` keeps the page's rule (a saved selection equal to the paint at the centre is dropped) behind a flag:
  the hub's import keeps such selections (S62, intended) and the solve reads them as Ben's.

### 5.2 P2 ground, rivers, viaducts, canon (`ground/`)

```ts
// layers.ts
export function sampleGround(g: Float32Array, step: number, c: number): number;                        // 636-643 (moves from station/ground.ts, which re-exports it)
export function regradeGround(dem: Float32Array, ctx: Pick<ContextRecord, "add" | "cap">): Float32Array; // 649-657
export function parseGnd(raw: PortDoc["gnd"] | null): { c: number; z: number }[][];                     // 668-671
export function gndLevel(P: readonly { c: number; z: number }[], c: number): number;                    // 667
export function normGnd(lines: readonly (readonly { c: number; z: number }[])[], regraded: Float32Array, step: number): { c: number; z: number }[][]; // 672 (new lines, ends on the regraded ground)
export function crossGround(input: PortInput, gndW: number): CrossGround[];                             // 674-685 (from input.neighbours)
export function drawnGround(base: Float32Array, lines: readonly (readonly { c: number; z: number }[])[], cross: readonly CrossGround[], step: number): Float32Array; // 686-696
export function rebuildGround(input: PortInput, gnd: Align["gnd"], rivers: readonly RiverRecord[]): GroundLayers; // 697-712 (surface: pool over rivers; bed: the canon bed)
export function riverIndex(rivers: readonly { c0: number; c1: number }[], c: number): number;           // 705 (first match)
// rivers.ts
export function bedOf(r: RiverRecord, pool: number): number | null;                                     // 709
export function sunkBox(input: PortInput): SunkBox;                                                     // 1007-1012
export function alongShore(m: Pick<SectionModel, "canon" | "input">, r: RiverRecord): boolean;          // 1015
export function riverBand(m: LevelModel, r: RiverRecord): RiverModel["band"];                          // 1017-1031
export function riverBridges(m: LevelModel): { name: string; c0: number; c1: number; lb: number; ub: number }[]; // 993-997
export function riverModels(input: PortInput, ground: GroundLayers, canon: CanonModel, sunk: SunkBox): RiverModel[];
export function madeBedAt(m: TypedModel, c: number, z: number, T: TypesModule): number;                // 1032-1036
export function madeBedArray(m: TypedModel, T: TypesModule): Float32Array;
// viaduct.ts
export function viaductSpans(m: SectionModel, types: TypeSolve, T: TypesModule): ViaductSpan[];         // 954-991
export function spanAt(spans: readonly ViaductSpan[], c: number): ViaductSpan | null;                   // 992
// canon.ts
export function chainLL(path: readonly PathPoint[], lon: number, lat: number, tol: number): number | null; // 866-875
export function buildCanon(input: PortInput, stations: readonly LiveStation[], grid: Grid): CanonModel; // 876-908 (sections from live stations: replaces station/live.ts liveCanon)
export function fixedLevel(f: FixedLevel, ground: number): number;                                      // 909
export function canonAt(m: Pick<SectionModel, "canon" | "grid">, c: number): CanonSection | null;       // 1041 (later sections win)
export function lockAt(m: Pick<SectionModel, "canon">, c: number): Lock | null;                         // 911 (0.5 m either side)
export function lockedStation(m: SectionModel, i: number): Lock | null;                                 // 912
export function applyLocks(align: Align, canon: CanonModel, stations: readonly LiveStation[]): { align: Align; changed: boolean }; // 915-929
export function refAt(m: SectionModel, i: number): number;                                              // 930
export const GROUND_MODULE: GroundModule;
```

Notes: the bridge deck lock (`decks`) needs every pier within `DECK_ON` of the path (Line 1's L&N bridge, 896-905).
`viaductSpans` and `madeBedAt` are the only P2 functions that need the types: their tests use `goldenTypes`.

### 5.3 P3 crossings, context, roads (`crossings/`)

```ts
// other.ts
export function otherRail(n: Neighbour, oc: number): number | null;                                     // 2182-2196 (vertical vertices and design on the neighbour's stations)
export function kindAt(m: SectionModel, n: Neighbour, z: number, gr: number, c: number, T: TypesModule): Structure; // 2197-2210 (the other line's phase and settings)
export function boredGap(m: SectionModel): number;                                                      // 2211
export function needSep(m: SectionModel, lo: Structure, up: Structure): number;                         // 2212
// clearances.ts
export function hallAt(m: SectionModel, c: number): HallSpan | null;                                    // 536-541
export function crossingClearances(m: TypedModel, T: TypesModule): CrossingClearance[];                 // 2235-2251
export function contextClearances(m: TypedModel, T: TypesModule): ContextClearance[];                   // 2219-2234
// roads.ts
export function subwayStreet(m: SectionModel, name: string): boolean;                                   // 456
export function streetAtC(m: SectionModel, c: number): number;                                          // 452 (index, -1)
export function roadsIn(m: SectionModel, c0: number, c1: number): number[];                             // 453
export function stationStreet(m: SectionModel, s: LiveStation): StationStreet;                          // 458-462
export function roadChecks(m: TypedModel, T: TypesModule, spans: readonly ViaductSpan[]): RoadCheck[];  // 2263-2275
export const CROSSINGS_MODULE: CrossingsModule;
```

Notes: the other line's structure is guessed from its rail and this line's surveyed surface (`surfaceAt0`), with its
phase from its `line_phase` (the page calls `phaseAt` with the other id, which skips the Chronology and the pieces);
port it as is. A crossing with a line not set is `pending` (`network.profile_set.crossings_apart`).

### 5.4 P4 checks, issues, fill, levels and docs (`checks/`, `levels/`)

```ts
// checks/curve.ts
export function radii(path: readonly PathPoint[], length: number, lit: PortLiterals): Float32Array;       // 1952-1970
export function curveAllowance(R: Float32Array, s: PortSettings): Float32Array;                         // 1975-1984
export function radiusAt(m: SectionModel, c: number): number;                                           // 1971
export function allowanceAt(m: SectionModel, c: number): number;                                        // 1985
export function curveGradeRanges(m: TypedModel, T: TypesModule): CurveGradeRange[];                     // 1987-2006
// checks/drawing.ts
export function drawingFlags(path: readonly PathPoint[], pieces: PortInput["pieces"], lit: PortLiterals): PortFlag[]; // 2048-2071 (pathTurns exists in station/curve.ts)
// checks/summary.ts
export function computeSummary(m: TypedModel, T: TypesModule): Summary;                                 // 1900-1920, 1949
export function gradesOver(m: TypedModel, T: TypesModule): GradeOver[];                                 // 1914-1919
export function riverChecks(m: TypedModel, T: TypesModule): PortFlag[];                                 // 1921-1946 (the page's shallowTubes)
// checks/design.ts
export function designChecks(m: TypedModel, T: TypesModule): { flags: PortFlag[]; sumps: number };      // 2081-2135 (platform grade, curve, slide, overlap come from station.facts: not again)
// checks/ground_checks.ts
export function gndChecks(m: SectionModel): PortFlag[];                                                 // 1731-1754
// checks/issues.ts
export function allIssues(parts: IssueParts): PortFlag[];                                               // 2143-2178 (stable sort by c, deduplicated)
// checks/fill.ts
export function proposeFill(m: TypedModel, c0: number, c1: number, T: TypesModule): FillProposal;      // 1684-1729, the pure part (no undo, no tool change)
// levels/levels.ts
export function defaultAlign(m: LevelModel, modes: readonly ("under" | "surface")[] | null, extra: readonly LevelNode[], stt: readonly (SelectedType | "")[] | null): LevelSolution; // 1756-1807
export function surfacePvis(m: LevelModel, st: readonly number[], md: readonly ("under" | "surface")[]): { c: number; z: number }[]; // 1810-1836 (RER; signature now, tests slice 2)
// levels/doc.ts
export function deriveStations(input: PortInput, del: readonly string[], so: Readonly<Record<string, number>>): LiveStation[]; // 717-723
export function reframeDoc(doc: PortDoc, platforms: readonly PortPlatform[], length: number): Reframe;  // 1839-1868 (frame.point_c by platform id)
export function alignFromDoc(input: PortInput, deps: AlignDeps): { align: Align; stations: LiveStation[]; ground: GroundLayers; canon: CanonModel; rivers: RiverModel[]; reframed: boolean; flags: PortFlag[] }; // 1869-1897
```

Notes: `defaultAlign` keeps its two-pass envelope (O(N squared) on stations and banks is a few hundred nodes, a
fraction of a millisecond); where the page wrote 0 m for a station with no bound (1775) the port flags it
(`network.level_solver.shallow_as_grade_allows`) and the golden comparison skips those stations, classed as a rule
fix. `reframeDoc` pairs saved points with live stops by platform id (the frame record), not by name and place.

### 5.5 Which depend on P1, and how P2 to P4 run in parallel

| Function | Needs from P1 | Needs from others |
|---|---|---|
| P2 layers, rivers (bed, band, bridges, sunk box), canon, locks, refAt | nothing | the input |
| P2 `viaductSpans`, `madeBedAt` | `typeAt` | the context's roads and the crossings (input) |
| P3 all | `typeAt`, `structFor`, `reqCover`, `phaseRules` (kindAt) | P2 `spans` (roads), the halls from station facts |
| P4 `radii`, `curveAllowance`, `drawingFlags`, `deriveStations`, `reframeDoc`, `gndChecks` | nothing | the input |
| P4 `defaultAlign`, `surfacePvis` | `elevNeed` | P2 rivers and canon (LevelModel) |
| P4 `alignFromDoc` | `sttFromDoc` (AlignDeps) | P2 `buildCanon`, `rebuildGround`, `riverModels`, `sunkBox`, `applyLocks` (AlignDeps) |
| P4 summary, design checks, curve grade, fill, allIssues | `typeAt`, `structFor`, `reqCover`, `gradeLimitAt`, `gradeLimitOver`, `sustainedGrade`, `phaseRules`, the TypeSolve | P3 clearances and roads, station facts' flags |
| P1 `solveTypes` | (itself) | P2 ground, canon, rivers, sunk box; P4 align and curve arrays: all as data in `SectionModel` |

So: P1a (tables, phase, structure: about 150 lines) lands first, in a day, with `util.ts` and `from_golden.ts`.
From then P1b (the solver, lookups, fit), P2, P3 and P4 are built at once: each reads `SectionModel` or
`TypedModel` built by `fromGolden` / `typedFromGolden` from the old page's own upstream values, and calls P1 at
points off the grid through `TypesModule` (`goldenTypes` until P1b lands, then `TYPES_MODULE`; the tests run both
and must agree). No package imports another's files except P1a's, `util.ts` and `types.ts`.

## 6. Tolerances per output

Against the goldens, per line. "Exact" means equal values (numbers equal in double precision where both are
computed the same way; categorical values equal at every sample). A difference outside tolerance is reported with
its range and needs a class (section 2).

| Output | Tolerance |
|---|---|
| align (st, sg, so, pvi, ovr, stt, tf, shafts, gnd, gapfill, del) | exact; pvi c to 0.1 m as saved |
| stations: c, point_c, rail, ref | 1e-9 m |
| rail, grade per 2 m (vertical, already ported) | 1 mm, 0.01 per mille |
| ground: dem, regraded, finished | exact (Float32) |
| surface, bed, made bed | 1e-6 m |
| type, solved type, tube, tube key, part, phase, pointType, paint, canon section, lock, tube form, station per 2 m | exact at every sample; the count of differing samples per line reported, zero unexplained |
| struct (k, below, top) per 2 m | k exact; below, top 1e-6 m |
| limit tube, limit box per 2 m | 1e-4 m (the dump's rounding) |
| grade limit per 2 m | exact (lim and warn are param values) |
| radii, allowance (10 m) | exact (Float32); null equals Infinity |
| solve.bad | same set of (why, c0, c1) exact; worst 1 mm |
| solve.approaches | station, kind, side exact; c 1e-6 m; shift 1e-9; len 0.01 m (rounded to the cm) |
| solve.platDef, stRole, shafts | exact |
| solve.flags | the set of (kind, c0, c1) after deduplication exact; numbers in data within the text's printed precision |
| eff_ovr, canon (secs lo/hi, fixed, modes, locks, piers) | lo, hi 1e-6 m; the rest exact |
| rivers: bed, band ub, lb, low, nav; river bridges lb, ub | 1 mm |
| sunk box | exact |
| viaduct spans | same count; c0, c1 exact (0.1 m rounding); L, below, above 1e-6 m; truss, ends exact |
| misfits | same set of (t, why, c0, c1, si) exact; worst 1 mm |
| crossings | zo, z, clear, need 1 mm; meUp, level, ok exact; t.k, to.k exact, below and top 1e-6 m |
| context clearances | c exact (block points); z 1 mm; clear, need, short 1 mm; ok, level exact |
| roads | same set of (kind, sev, c) exact; clear, need 1 cm |
| gnd cross, gnd checks | c0, c1, z 1 mm; set of (sev, c) exact |
| drawing flags | set of (kind, sev, c) exact; angle 0.5 degree |
| curve grade ranges | c0, c1 exact (10 m grid); worst, g, add 0.01 per mille; sustained exact |
| design checks: vertical curve, drainage, cover, thin cover, curve grade | set of (kind, sev, c) exact (c on the 10 m grid or the chord middle); the numbers within the printed precision (0.01 m, 0.1 per mille) |
| summary | len per type exact (10 m bins); deepest, highest 1 mm and their c exact; maxG 0.01 per mille, maxGc exact; over: set of (c0, c1, sev) exact; sumps exact; deepShallow exact set |
| issues | per line the multiset of (kind, sev) equal after deduplication; each flag's c0, c1 within 1e-6 m where `range_from` is source or platform, within 1 m where text, c exact where point |
| default levels (defaultAlign) | st 0.005 m (the page rounds to the cm); tube pvi c 0.05 m, z 0.0005 m |
| reframe | changed exact; pvi, ovr, tf, shafts, gnd c 0.05 m (rounded to 0.1 m); so 0.25 m (rounded to 0.5 m) |
| propose fill | each proposal's points: c 0.05 m, z 0.005 m; nothing to fill exact |
| reset (alignFromDoc(null)) | as default levels |

## 7. The work packages

Each package: its files only, its tests in `engine/test/port/<package>/`, its report, its rule list; no change to
`src/vertical`, `src/station` (except the moves named), `src/contract` (the lead writes the zod of the two new
contracts from `types.ts`), `hub/`, `data/`, `region/ground`, `rules/registry.yaml`. A finding needing a rule or
param goes to the lead.

### 7.1 P1 types (the structure solver and type lookup)

- **Port:** pointType, approachLen, absorbShort, stretchTypes (as `solveTypes` with the caller's cache), solveTypes,
  autoType, fitOf, paintMisfits, typeAt, overrideAt, effOvr, sttFromDoc, structFor, reqCover, phaseAt, metroTube,
  gradeLimitAt, sustainedGrade, phaseRules, ERA (as `input.era` and `sgMaxFor`), applyMS; plus `util.ts`,
  `from_golden.ts`, `TYPES_MODULE`.
- **P1a first (day 1):** util.ts, tables.ts, phase.ts, structure.ts, from_golden.ts. Exit: phase and the
  structure at the rail per 2 m (structFor of the golden's type, with the golden's solved tube) exact on 16 lines,
  and metroTube equal to the golden's tube key wherever the solve has no tube.
- **P1b:** point.ts, solve.ts, lookup.ts, fit.ts, grade.ts. Exit: type, solved type, tube, part per 2 m; bad;
  approaches; platDef; stRole; shafts; flags; misfits; limit lines: all within section 6 on 16 lines, zero
  unexplained. Bench: `solveTypes` on Line 6 under 30 ms median in process (the page: 35 ms).
- **Depends on:** types.ts only; the goldens for every upstream value.
- **Size:** about 900 lines of source.

### 7.2 P2 ground, rivers, viaducts, canon

- **Port:** sampleGround to rebuildGround (regradeGround, parseGnd, normGnd, gndLevel, crossGround, drawnGround),
  river, bed and surface, viaductSpansNow, riverBridges, sunkBox, riverBand, madeBedAt, canonAt, chainLL,
  buildCanon, applyLocks, refAt; `GROUND_MODULE`. `station/ground.ts` and `station/live.ts` become thin re-exports
  (station.facts@1 and its goldens unchanged).
- **Exit:** ground layers exact; surface, bed, made bed; rivers (band, bridge); sunk box; canon model and locks;
  viaduct spans; refAt per station: within section 6 on 16 lines. Line 1's L&N bridge (a deck lock and its piers)
  and Line 6's Ohio and Licking crossings named in the tests.
- **Depends on:** P1a (none of its functions, only types), `goldenTypes` for spans and made bed.
- **Size:** about 450 lines.

### 7.3 P3 crossings, context, roads

- **Port:** otherRail, kindAt, needSep (with boredGap), context (contextClearancesNow), crossings
  (crossingClearancesNow), roadChecksNow, stationStreet (with subwayStreet, streetAtC, roadsIn), hallAt;
  `CROSSINGS_MODULE`.
- **Exit:** the 430 crossings, the 10 context clearances, the 81 road findings and every station's street: within
  section 6, zero unexplained. Neighbours from the seed docs (395) and `metro_rails.json` (35) in the adapter.
- **Depends on:** P1a (structFor, reqCover, phaseRules), `goldenTypes` for typeAt; P2's spans as data (the golden's).
- **Size:** about 300 lines.

### 7.4 P4 checks and levels

- **Port:** computeSummary, radii, curveAllowance, drawingFlags, designChecks, allIssues, proposeFill (the pure
  part), defaultAlign, surfacePvis, reframeDoc, alignFromDoc, plus curveGradeRangesNow, gndChecks,
  deriveStations and the river checks of computeSummary.
- **Exit:** radii and allowance exact; drawing flags; curve grade; design checks; summary; the issues of every kind
  (after deduplication) with ranges; default levels on 16 lines (Lines 10, 11 and 13 are the level solver's whole
  answer); reframe on Line 2b; the 118 fill proposals; reset: within section 6, zero unexplained.
- **Depends on:** P1a; `goldenTypes`; the golden's P3 outputs as data for allIssues and the summary's clashes;
  AlignDeps stand-ins from the golden for alignFromDoc (the real P1 and P2 functions once they land).
- **Size:** about 800 lines.

### 7.5 The lead: integration (after P1 to P4)

`model.ts` (the build order of section 8), `solve.ts`, the `section.solve@1` row, the zod of
`section_solve_input/0` and `solved_section/0` from `types.ts` with the schema export, Python's input builder
(`region/ext/profiles/inputs.py section_solve_input`: the records of section 3), the `canon` kind and importer, the
`section_context` v2 upgrade, the neighbour assembly, the server job, the worker pipeline. Exit: `section.solve@1`
on each golden line's real input (built from records, not from the golden) gives the same answers as the packages
did on the golden-fed model, and the end-to-end report has zero unexplained differences.

### 7.6 Not in these packages

The proposers `regradeDrive` (Lower, Raise, Fix unbuildable: 3601) and `solveCross` (Solve levels with crossings:
3693) are 2.1.15's engine proposers; they return edits (PVIs) and never touch undo. Their signatures for the next
round: `regradeDrive(m: TypedModel, c0: number, c1: number, mode: "lower" | "raise", lim?: number): { pvi:
Align["pvi"]; flags: PortFlag[] }` and `solveCross(m: TypedModel, x: readonly CrossingClearance[]): LevelSolution`.
Their goldens are not dumped yet; `old_page_dump.mjs` gains a `--proposers` pass when they are planned. The
station-side items of B that need the solver (S7, S61 full, S63 default, S64, S75, S76) read P1's outputs through
station.facts (section 8) and need no package of their own.

## 8. Integration, the build order and the budgets

**Build order of one solve** (`model.ts`): deriveStations (P4) from the input; buildCanon (P2) on the live stations;
reframeDoc and alignFromDoc (P4, which calls sttFromDoc P1, rebuildGround, riverModels, sunkBox, applyLocks P2, and
defaultAlign P4 for unset stations); the rail (the existing vertical design); radii and curve allowance (P4, path
only, cached by path); `SectionModel`. Then solveTypes (P1); spans and made bed (P2); station facts on the solved
types (station.facts reads `stRole` and the type at each centre, so the station type is the full solver's; the halls
go into the model); crossings, context, roads (P3); summary, checks, issues, levels (P4); `PortSolved`.

**In the sheet's worker, progressive.** On every edit: `vertical.rail@1` first (the 16 ms local re-solve, unchanged)
and the sheet redraws the rail at once; then `station.facts@1` (the provisional station pass, unchanged); then
`section.solve@1`, which the sheet draws when it lands. During a drag only the first two run, and the bands of the
structure, crossings and issues are the last solve's with the live rail over them, as the page did (`LAST_T`, 1339);
the full solve runs on pointer up or after 150 ms without an edit, and a newer edit cancels an older solve by its
generation number, so it never blocks the drag. The worker caches by input identity, as the page cached on `VERTS`:
the ground layers only when gnd, the context or a neighbour's ground change; the curve arrays only when the path
does; the type solve only when the rail, the ground, the paints, the selections or the records change.

**On the server.** `profiles.solve_structure` is its own job, after `profiles.solve_section`, at a lower priority,
with its own result and SSE event; the rail result is sent as now, so the always-live budgets (`tests/live`,
`app/e2e/live.spec.ts`: a saved line file in the open sheet in 2.4 to 2.5 s) hold. Its cache key adds the neighbour
results' hashes (section 3.3).

**Budgets (new bench tests).** `section.solve@1` Line 6 under 60 ms median in process, every Metro line under 120 ms
(the old page took 35 ms for its type solve and 50 to 70 ms for the summary and checks on Lines 5, 6 and 14,
measured on the scratch copy); the existing `vertical.rail@1` bench (Line 6 under 20 ms) and the sheet's 16 ms local
re-solve unchanged. A package that cannot meet its share reports it; the drag never waits for it.

## 9. Rule ids for every check

Every `PortFlag` cites a rule of `rules/registry.yaml`; each package's rule list is checked by the existing RuleId
test. The page's kind on the left (allIssues 2143-2178 and its sources), the new slug and severity, the rule.

| Page kind (lines) | Slug, sev | Rule ids |
|---|---|---|
| Grade (1914-1919, 2146-2153) | `grade_over_sustained` error, `grade_over_local` warn, `grade_over_straight_underground` warn | era.grade.limit_by_phase, era.grade.sustained_vs_local, era.grade.steepest_between_bends |
| Curve grade (1987, 2122) | `curve_grade_sustained` error, `curve_grade_local` warn | era.grade.curve_allowance_train_averaged, era.grade.sustained_vs_local |
| Clearance (2235, 2154) | `crossing_level` error, `crossing_short` error (pending when the other line is not set) | clearance.crossing.structure_sum, clearance.crossing.bored_gap, clearance.hall.checks_over_hall_roof, clearance.crossing.other_line_guessed, network.profile_set.crossings_apart |
| Context (2219) | `context_short`, `context_level` error | clearance.context.blocks, clearance.open.clear_height, clearance.context.street_openings |
| Cover (2118-2124) | `tube_cover_short` error, `box_roof_above_ground` error | structure.cover.one_diameter_over_tubes, structure.box.thin_cover_warning |
| Thin cover (2125) | `box_roof_forms_street` warn | structure.box.thin_cover_warning, road.subway_streets |
| River (1921-1946) | `sunk_box_high`, `sunk_box_low`, `sunk_box_nav`, `river_above_water`, `bridge_below_clearance` error | river.sunk_box.roof_band, river.sunk_box.made_up_bed, river.ohio.navigable_12ft, river.crossing.bridge_or_sunk, river.bridge.navigation_clearance |
| Tunnel method, stretch notes (1520) | `stretch` info | geometry.stretch.note_every_stretch, with the deciding rule in `data.rule`: geometry.method.paint_final, geometry.method.bank_works, geometry.method.canon_bored, geometry.method.mined_station_forces_drive, geometry.method.both_feasible_phase_prefers, geometry.method.one_feasible |
| Tunnel method, neither feasible (1514) | `stretch_unbuildable` error | geometry.method.neither_feasible_nearer |
| Tunnel method, short open run (1411) | `open_run_not_portal` info | geometry.portal.min_open_run |
| Tunnel method, stations (1401-1402, 1517) | `tbm_before_phase_3` warn, `box_station_past_limit` warn, `mined_in_box_stretch` warn (once per station) | geometry.method.tbm_from_phase_3, station.type.mined_in_box_stretch_flagged, station.type.selection_else_limit |
| Low cover (1532-1536) | `low_cover` warn, propose | structure.cover.low_cover_warning, geometry.shortfall.flag_not_change |
| Tube form (1416, 1550-1556) | `bore_through_mined_station` warn, `twin_under_narrow_street` info, `spacing_change_in_tunnel` warn, `bore_lacks_cover` warn | structure.tube_form.mined_station_twin, structure.tube_form.stacked_prefer_bore, structure.tube_form.no_spacing_change_in_tunnel, structure.tube_form.ends_plus_paint |
| Approach box (1444, 1547) | `approach_runs_into_station` warn, `approach_leaves_street` info | station.approach.part_of_station, structure.approach.spacing_change_in_box, structure.approach.outside_street_accepted |
| Painted (1468-1470, 1526, 2172) | `two_paints_one_stretch` warn, `paint_snapped` info, `paint_box_carries_on` info, `paint_misfit` error with fix, clear, propose | structure.paint.two_paints_one_stretch, geometry.method.paint_final, geometry.launch_box.full_cover, structure.paint.must_fit |
| Unbuildable (2173-2175) | `unbuildable_cover`, `unbuildable_box`, `unbuildable_roof` error with fix, propose | structure.cover.one_diameter_over_tubes, structure.box.past_limit_unbuildable, station.type.box_roof_out_of_ground_unbuildable |
| Vertical curve (2087) | `vertical_curve_short` error | era.vertical_curve.radius_and_min_length |
| Drainage (2104-2113) | `drainage_flat` warn | era.drainage.warning_only, river.covered_way.flat_ok |
| Drawing (2060-2071) | `path_doubles_back`, `path_kink` error, `single_angle_corner` warn | network.drawing.corner_checks |
| Ground (1731-1754) | `ground_end_slope`, `ground_steep` error, `ground_sustained` warn, `ground_from_crossing` info | ground.drawn.limits, ground.drawn.counts_across_crossing_street |
| Road (2263-2275) | `level_crossing`, `trough_under_road`, `clearance_over_road` error, `pier_in_road` warn | road.level_crossing, road.trough_under_road_bridge, road.clearance.by_class, road.piers_out_of_roads |
| Access, Platform grade, curve, slide (station.facts@1) | as now | access.*, platform.grade.limit_by_era, platform.curvature.gapfill, platform.curvature.no_s_curve, platform.slide.limit_never_clamped |
| Canon (1907-1912) | `deep_in_shallow_canon` warn | **none** (see below) |
| Platform overlap (2101) | `platform_overlap` error | **none**; station.facts@1 cites platform.length.by_system |
| Level solver (1775), reframe, locks, fixed levels, spans, made bed, fill | `station_level_unbounded` warn; facts with their rule | network.level_solver.shallow_as_grade_allows, platform.tie.saved_profile_own_frame, platform.tie.centre_kept, network.canon.locks, network.canon.fixed_levels, structure.elevated.drawn_structure, structure.elevated.decided_by_soffit, river.sunk_box.made_up_bed, ground.propose_fill.within_paint, ground.paint_never_raises_ground |
| Types, phases, platform defaults | facts with their rule | structure.box.roof_and_cover_under_ground, structure.sunk_box.river_beats_paint, structure.sunk_box.dimensions_from_record, structure.sunk_box.bank_transition, era.phase.by_chronology, station.phase.earlier_segment, geometry.sliver.absorb_only_if_buildable, geometry.anchor.kinds, geometry.anchor.shaft_brush, geometry.feasibility.box, geometry.feasibility.drive, geometry.band.engine_is_the_drawing, platform.default.box_side, platform.default.island_at_open_transfer, platform.default.island_tube_into_box, platform.default.mined_side |

**Missing rules (reported to the lead; not added):**

1. The canon depth warning: a station the canon puts in a shallow (basin or canal) section but deeper than
   `settings.shallowMax` (1907-1912, page kind Canon, 24 on the seed). The param's meaning names it; no rule does.
   Suggested id `network.canon.shallow_section_depth`.
2. The platform overlap error: two platforms whose centres are closer than the platform length less
   `literal.platform_overlap`, with different drawn points; the first in order keeps its level (732, 2101).
   Suggested id `platform.overlap.first_wins`. station.facts@1 cites `platform.length.by_system` for it today, which
   is not what that rule says.

## 10. Known faults of the old page, and how each difference is classed

| Fault | Class |
|---|---|
| "is a mined station inside a cut-and-cover stretch" pushed once per 2 m sample (1517): 1,154 stretch flags on 16 lines, 674 distinct | rule fix, station.type.mined_in_box_stretch_flagged (compared after deduplication) |
| A station with no bound gets 0 m (1775) | rule fix, network.level_solver.shallow_as_grade_allows (flagged, never 0) |
| Crossings with Lines 10, 11 and 13 read the stale `rer/metro_rails.json` | parity first with the same neighbours; the switch to the neighbour's own default levels is a rule fix, clearance.crossing.other_line_guessed |
| The other line's structure guessed from depth with this line's surface and the other line's line_phase | ported as is; reading its solved type later is a rule fix, clearance.crossing.other_line_guessed |
| A saved selection equal to the paint at the centre dropped on load (sttFromDoc 852) | intended (S62 of the matrix) |
| The vertices comparator (739) | already handled by vertical.rail@1 (sort by c, rank, order) |
| Line 2b reframed on load; the new hub did not reframe | none once P4 lands: reframeDoc is ported |
| The seed docs' derived `stations[].type` stale on 29 of 351 stations | not a golden: the dump is |
| Paints with the legacy value `bored` | already read as shield on import (inputs.py) |
| Caches keyed by object identity (VERTS._types, d._R, MEMO) | not ported: pure functions, cached by the orchestrator |

## 11. RER, not blocked

`system` is in every input; `PortSettings.rer` carries envelope, boreCrown, invertDepth, minCover, surfStep;
structFor and reqCover take the RER branch from it; `CanonRecord.modes` and `RiverRecord.inCoveredWay` with
`alongShore` cover the RER canon and shore rivers; `openTypes` and `surfacePvis` have signatures; `Neighbour.system`
allows Metro by RER crossings (they are in the Metro goldens: the B CVG and E trunk crossings). RER junctions and
shared stretches (330-444) become network constraints in slice 2, not copy-on-save: nothing here writes another
line's profile.

## 12. Order and gate

1. Done: the goldens, the harness, `types.ts`, this plan.
2. P1a, with `util.ts` and `from_golden.ts` (one day).
3. P1b, P2, P3, P4 at once, each to zero unexplained on its outputs.
4. The lead's integration (section 7.5), the records (canon kind, context v2, params), the bench tests.
5. The sheet draws `PortSolved` (the C items of section 1), each checked side by side with the old page at the same
   view and size, as the station round was.

Gate for I2.2: on the 16 Metro lines, every output of section 6 within tolerance or classed, zero unexplained; every
flag with a registry rule id; the two missing rules and the missing params ruled or listed as open; the budgets of
section 8; vertical.rail@1 and station.facts@1 goldens unchanged.
