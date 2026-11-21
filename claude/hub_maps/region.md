# region/, rules, tests, ground: what exists and the gaps (read-only survey, branch hub_region at cf8d295)

## 0. Test run
`python -m pytest -q`: 97 collected (test_core 66, test_ground 10, test_hub 9, test_model 6, test_rules_registry 4, test_calibration 2). **96 passed, 1 failed, 1 warning, 73.6 s.**
- Failed: `tests/test_core.py::test_rer_routes_follow_deck` (assert at :705). The routes' paths agree with the Deck (path drift 0.02 m). What fails is station drift: platform centres are off their Deck platforms, e.g. Line_6 North Avondale 3452.7 against 3682.6 m and Forest 4652.8 against 4888.2 m; Line_1 Gray, Winton Place and Burnet North.
- This is pre-existing. `tests/baseline/issues.json` (5 Nov snapshot) already lists "Line 1: 15 platforms off their Deck platform's centre (Gray +2 m, Winton Place +6 m, Burnet North +20 m…)". `git diff f1a6383 HEAD` over `tools/rer_deck_routes.py`, `data/deck`, `data/profile`, `hub/seed`, `railsim` and `tests/test_core.py` is empty, so the plan's "96 passing" almost certainly included this failure.
- Warning: "131 rules without an invariant test yet" (`test_rules_registry.py:32-36`, warn only).
- The calibration tests write `output/<stem>/summary.json`, which is gitignored; the tree stayed clean.

## 1. region/model (what exists)
- `migrations/0001_init.sql` (171 lines): 26 tables plus 5 R-tree virtual tables (node, section, station, context, earthwork) and `rtree_map`.
  - 18 versioned tables (id, version, created, updated, source): node, section, track, route, service, station, stop, platform, station_element, structure, bridge, earthwork, ground_layer, context_feature, yard, era, ruling, snapshot.
  - Not versioned: route_section, rule, result, issue, legacy_key, history, schema_version.
  - 10 tables have `geom` (WKB, EPSG:26916), but only 5 have an R-tree (`db.py:27`). platform, station_element, bridge, yard and ground_layer are not indexed.
  - No CHECK constraints and no triggers. Every vocabulary (node.kind, structure.method/origin, earthwork.kind/timeline/mode, issue.severity, system) is an SQL comment only.
- `db.py` (189 lines): `open_db` (WAL, foreign_keys ON, migrate), `put(con, table, rec, if_version, source)`, `get`, `history`, `add_legacy`/`legacy`, `within(bbox)`, `rows(where)`, `tables`.
  - Record = dict. Columns are taken from the dict; everything else goes into `data` JSON (sort_keys); `geom` is a Shapely object.
  - Ids: ULID via `python-ulid` 4.1.0 (`str(ULID())`, 26-char Crockford, e.g. `01M7Z958359VN68MTZ9RR96YKG`). Only millisecond-sortable.
  - There is no delete, supersede, restore, list-by-prefix, event hook or bulk-write API.
- `seed.py` (104 lines): export writes one JSON file per row to `region/seed/<table>/<id>.json` (sorted keys, indent 1, WKT to 3 dp). `DERIVED = {result, issue, history, rtree_map, schema_version}`. Import is a three-way merge against `seed_base(tbl, id, record)`, a table created lazily outside the migrations (`seed.py:39-40`). Conflicts go to `region/seed_conflicts/`.
- `__main__.py`: `python -m region.model export|import|migrate --db region.db` (default path relative to cwd).
- `region/seed/` does not exist. No importer exists, so the model holds no data. Ben's DB is still fed only by `hub/seed/` (alignments, chronology, data, deck, params, roadmap).

## 2. Migration 0001 against plan §4.2, and against what scenarios, changesets and alternatives need
Every §4.2 table is present: node, section, track, route, route_section, service, station, stop, platform, station_element, structure, bridge, earthwork, ground_layer, context_feature, yard, era, rule, ruling, snapshot, result, issue, plus legacy_key and history. Demand is deferred (slice 6) and absent. Where the schema falls short:
- **service** (`:50-53`) has no route or pattern column, only `era_id` (no FK). The plan's "section edit → services crossing it" invalidation can't be a join.
- **route_section** (`:45-48`) has no id or version, so route membership edits get no If-Match and no history.
- **earthwork** (`:97-102`):
  - It has no order column, but the ledger's order is the order of application.
  - Its kind vocabulary (pad|corridor|freeform|raster) does not match the ledger's `apply.kind` (target_mode, map3_footprint, map3_zones, raster, model, none).
  - There is no link to the section or structure that generates line works.
  - The compositor never reads this table.
- **ground_layer** (`:104-107`) has no timeline, confidence or cover fields and is unused by `region/ground`.
- **structure** (`:84-90`) mixes inputs (paint, selection, canon, ruling) with derived rows (`origin='solved'`). The seed export does not exclude solved rows, so derived structures would be committed.
- **result** (`:136-139`) has `key, engine, engine_version, scope, created, ms, output TEXT`. It lacks an inputs manifest (record ids and versions, file hashes), status, size and last-used, and has no blob or file pointer for GLB or rasters.
- **issue** (`:141-144`) has no scenario or era, no status (open, waived by a ruling) and no dedupe key.
- **rule** (`:124-126`) has no version or history. Nothing loads `rules/registry.yaml` into it (not found). There is no `param` table and no rule→ruling link (the registry embeds rulings; the `ruling` table is separate).
- **context_feature** (`:109-112`) is one row per feature with `source` only. The street base-and-edits model from plan §7 is **not in the schema**: no `origin` (plate and pipeline run vs authored), no plate id, no edits or overlay table, no changeset table, no per-feature conflict list.
- **Scenarios and alternatives**: not found.
  - No `scenario` table and no `scenario_id` on any record.
  - `snapshot` (`:132-134`) is a frozen JSON copy of records, not a branch, so two live alternatives (stacked vs spread Fountain Square) can't both be edited and scored.
  - Station flows also need a walking graph (element-to-element links); no table holds one.
- **Changesets and undo**: per-record `history` only. Nothing groups several writes into one change (author, message, undo unit) and there is no restore.
- **Deletion and supersede** (plan: "a replaced record is superseded"): no column or API, except `platform.deleted` (Ben's deletion flag).
- The comment at `0001_init.sql:12` says the R-tree is "kept in step by triggers". There are none: only `db.put` maintains it, so any direct SQL bypasses it.

## 3. region/ground (what exists)
- `layers.py` (66 lines) holds code constants:
  - `PRESENT=2026` (:16), `STEP=2.0`, `ND=-32768`.
  - Base paths `CANON_1912` (:19), `SURVEY_COVER`, `MAP3`, `MAP3_WATER` (:22, unused), `RIVERWORKS_1912_DELTA`.
  - `SRC` codes 0 to 3 (:26).
  - `load_ledger` builds `Work(id, name, built_from, built_by, kind, files, timeline, source, note, code=10+i, part_value)`.
- `raster.py`: `Target` (bbox snapped to the 2 m lattice), `read` (windowed, nearest), `write` (tiled deflate GeoTIFF).
- `compose.py` (188 lines): `compose(year, bbox, timeline, step, extra_works) → Grid(z float32 m, src uint8, applied, skipped)`.
  - Order: 1912 base, then the real-timeline delta, then map3 filling every base gap, then ledger works in order, then extra parametric works.
- `earthworks.py`: `Pad` (polygon, level or plane, slopes, mode, stats with fill/cut m³) and `Corridor` (xyz centreline, half width, slopes).
- `sample.py`: bilinear `sample(year, xy)`.
- `cli.py`: `works`, `compose`, `check`.
- `split_riverworks.py`: a one-shot script that wrote `works/riverworks_2026_part.tif`.
- Timings measured here:
  - compose 2026: 0.50 s per 1 km tile, 0.79 s per 4 km tile; 1930 over 4 km: 0.37 s.
  - `sample` along a 10 km diagonal (2,000 points): 5.1 s.

## 4. Ground data and contracts
- `ground/` is 122 MB in git (1912 39 MB, 2026 65 MB, works 13 MB).
  - 1912 base: 16,701×13,701 cells at 2 m, E 697,252-730,654, N 4,321,822-4,349,224.
  - map3: 20,000×17,500 cells, E 695,000-735,000, N 4,315,000-4,350,000.
  - Bed rasters are 4 m. Nothing exists beyond the LiDAR box; the TRI extent is 147×144 km.
- `works_ledger.json`: `{about, conflicts[], works[11]}`.
  - Work keys: id, name, built_from, built_by, timeline (canon 10, both 1), source, note, apply{kind, target|mode|delta|raster|zones|minus|part|years, part_value}.
  - Apply kinds: target_mode 6, map3_footprint 2, map3_zones 1, model 1 (`metro_tri_line_works`, skipped), none 1.
  - `ohio_bed_canon` is undated, so it is applied only at 2026.
- `ground/zones/zone_years.json` has `zones: {}` (no zone dated yet).
- The river level 139.62 m exists only as registry param `literal.ground.river_level_all_years` (`literal_in_code`). The compositor applies no water surface.
- `ground/1912/SPEC.md` (the contract for lane B):
  - Delivers `surface/real_1912_ground_dm.vrt` (tiles `_r<R>c<C>`, at most 8,000² cells, int16 dm, nodata where sheets are blank, never LiDAR-filled).
  - Also `surface/real_1912_confidence.tif` (uint8 0-100, nodata 255), `surface/real_1912_cover.tif`, `contours/<sheet>.geojson`, `georef/<sheet>.json`, `report/fit_report.json` (targets: lidar rms < 1.0 m, seam rms < 0.5 m, labelled share > 0.9).
  - Handshake: `STATUS.json`; consumers act only when `"done": true`.
  - §6 tells the cloud side to change the `CANON_1912` constant to `REAL_1912` and delete the real-delta step. That is a code edit.
- Current `STATUS.json`: stage `contours`, done false, updated 2026-11-06 (15 days stale); 48 sheets, 1,709 controls, rms 2.06 m.
- `configs/ground_paths.json` (profile `ben-desktop`, absolute Windows paths) is read only by `ground/1912/rebuild/*.py`. `configs/sanborn_paths.json` is read only by `tools/sanborn/_ws.py`.
- `region/` reads neither config, nor anything under `data/sanborn` (62 entries) or `hub/sites/deck` (tiles12, tiles_22, tiles_b, tiles_n, plots.json, deck.json and others). A search of region/ for sanborn, deck and street readers found none.

## 5. rules/registry.yaml and region/rules.py
- Layout: 3,555 lines. `params:` at lines 1-164 (flow style); `rules:` from line 165.
- **Params, 163**:
  - Status: recorded 87, literal_in_code 76.
  - Prefixes: metro_structure 60, literal 50, settings 28, settings_rer 16, canon 6, context 2, chronology 1.
  - Fields: path, value, unit, meaning, source (`file:line`), status. Units: m 127, permille 16, and others.
  - 26 params are referenced by no rule.
  - Recorded values duplicate `data/profile/*.json`: 59 match, 1 differs in form (`metro_structure.line_phase`), 18 paths are not resolvable mechanically. No test keeps the two copies in step.
- **Rules, 137**:
  - Status: ratified 38, provisional 91, unratified 8, superseded 0.
  - Fields: id, domain, text, status, ruling{date, by, words, source}, decision, rank, params[], applies_to[], flags[], tests[], history[], notes.
  - 11 domains. 8 ranked decisions (method_per_stretch 7, access_type 5, platform_default 4, grade_limit 4, station_type 3, platform_position 3, crossing_separation 3, ground_layers 3); 105 rules have no decision.
  - `ruling.by`: Ben 130, Claude 7.
- **How a rule names a test**: free strings in `tests:`; the intended form is `tests/<file>.py::<name>`. 6 rules have tests:
  - 3 resolve.
  - 1 names the wrong file: `platform.tie.saved_profile_own_frame` points to test_core, but the test is `tests/test_hub.py:129`.
  - 2 are prose ("hub/test_hub.js (…)", "a test … (planned)").
  - The validator does not check test references.
- `flags` are UI label strings ("Painted (snapped, note)"), not the structured `{kind, sev, c0, c1, data}` the plan specifies.
- `rules.py` (149 lines): `load()` gives a `Registry` with `rule`, `decision` (rank order), `decisions`, `unratified`, `by_domain` and `validate`. `validate` checks status values, ratified-needs-dated-words, superseded_by, decision with rank, unique ranks, applies_to ⊂ SYSTEMS, param paths exist, and no number with a unit in rule text.

## 6. Tests and baseline
- `test_model` (6): migrations, version conflict, legacy, R-tree, seed round trip, merge.
- `test_ground` (10): 1912 equality, real vs canon, works by year, 2026 vs map3 > 95 % within 5 cm, Pad, Corridor, extra works, date-as-data, per-zone years.
- `test_rules_registry` (4).
- `test_calibration` (2): Orange and Needham within ±1 % of `calibration.json`; per-station ±3 % reported only.
- `test_hub` (9): old store and pipeline.
- `test_core` (66): railsim physics, plus about 30 tests (from :302) on `railsim/metro_profile.py`, the Python copy slated for deletion, and the Deck tie. These are today's de facto rule invariants.
- **`tests/baseline/`**:
  - `profiles/*.json`: 41 files, 144,113 samples. Shape `{route, saved, c0, step_m:5, n, rail_m[], type: RLE[[v, n]], tube: RLE, align}`.
    - `align` holds the old station-indexed doc: st, sg, so, stt (lists by station order); del (station names); pvi `[{c, z}]`; ovr `[[c0, c1, type]]`; gnd, tf, shafts, gapfill, ready.
    - No ground samples and no route geometry are stored, so a ground change can't be separated from an engine change.
  - `runtimes.json` (572 KB): 73 entries (17 metro, 56 commuter) keyed by config stem. Shape `{kind, line, train, warnings, directions[{direction, distance_km, running_time_min, dwell_total_min, trip_time_min, scheduled_time_min, stations[{name, km, arrive_s, scheduled_arrive_s}]}]}`.
  - `calibration.json`: `{mbta_orange, mbta_needham: {kind, published_min, published_note, directions}}`.
  - `platforms.json` (41 routes), `approaches.json`, `issues.json` (57 issues, synced 2026-11-05T16:27:44Z).

## 7. Defects (verified by experiment in scratch unless marked)
**Model and seed**
1. **Every record added or taken by a seed import later raises a false conflict.**
   - The cause: `db.put` inserts ignore the incoming version, created and updated (`db.py:137-138`), and updates bump them (`:148`), while `seed.py:78-87` compares whole serialized records, bookkeeping fields included.
   - Verified: after a "take", a second change made only in the seed was reported as a conflict.
   - A record imported at version 7 became version 1.
   - `test_model.py:61-92` passes only because everything happens within one clock second.
2. **Export crashes once any route_section row exists.** `seed.py:53-55` keys files and `seed_base` by `id or legacy`, so route_section writes `None.json` and then hits IntegrityError (NOT NULL `seed_base.id`).
3. **Legacy keys are lost on export.** legacy_key's `id` is the target record, so all legacy keys of one record collapse into one file and one row (verified: 2 keys in, 1 after the round trip).
4. **Import into an empty DB fails.** `seed.py:67` imports table directories alphabetically with foreign keys ON; `platform` comes before `stop` (and `route_section` before `section`), giving `FOREIGN KEY constraint failed`. Each record is its own transaction (`db.py:132`), so the DB is left partial. No backup is taken, although the plan requires one.
5. **A partial `put` wipes `data`** (`db.py:85-88`): data is rebuilt only from the keys passed, while omitted columns keep their values. There is no patch or delete-key semantics; the old store had `__delete__`.
6. **Unchanged writes still create versions.** A no-op put bumps the version and writes history (`db.py:148`); the old store skipped unchanged writes (`test_hub.py:15`).
7. **History rows are raw, not records** (`db.py:145-147`): `data` is stored as a JSON string and `geom` as hex WKB, not the record shape `get` returns.
8. **The R-tree can go stale.** It is updated only when geom is not None (`db.py:152-153`); setting geom to None left a stale hit.
9. **Unversioned tables get no protection.** `put` on `rule` overwrote the status with no version check and no history (verified). `put` cannot write route_section or legacy_key at all (no `id` column; behaviour read from code, not run).
10. Table names are interpolated with `%` (`db.py:118, 134, 140, 179, 185`); they need a whitelist before any API passes them through.
11. **A crash can strand a migration** (code reading): `migrate` COMMITs the script before inserting `schema_version` (`db.py:65-66`). A crash between the two leaves the migration applied but unrecorded, and the next start re-runs its CREATE TABLE statements and fails.
12. **Packaging and git hygiene** (from config files, not run):
    - `python-ulid` is undeclared, and pyproject packages only `railsim`.
    - `region.db*` and `region/seed_conflicts/` are not gitignored.
    - There is no `.gitattributes`, so Windows `write_text` exports CRLF and the "byte-identical seed" claim fails across machines.

**Ground**
13. **The base surface is code, not data.** It is a constant (`layers.py:19`, `compose.py:132`); the 1912 swap is a code edit (SPEC §6), and the `ground_layer` table is unused.
14. **The new 1912 surface's holes would be filled silently** (code reading). Every base nodata cell is filled from map3 (`compose.py:141-145`), so SPEC §4.4's honest nodata would get 2026 ground, labelled only by `src=3`. The confidence and cover rasters are not read.
15. **Zone feathering depends on the bbox** (`compose.py:117-122, 171-173`): 42 cells differed by up to 0.0625 m between two bboxes overlapping a zone edge. 1 km cached tiles will show seams.
16. **Pads ignore slopes that cross a tile edge.** A Pad whose footprint lies just outside the tile changes nothing even where its slopes reach in (`earthworks.py:49-51`): 100.0 m vs 108.0 m.
17. **Earthworks invent ground in no-data cells.** `np.fmax`/`np.fmin` ignore NaN (`earthworks.py:58-65, 102-109`): all 30,000 NaN cells got values, one 150 m away at -69.8 m.
18. **Provenance codes are unstable** (code reading).
    - Codes are 10 + the ledger index (`layers.py:61`), so inserting a work renumbers every cached `src` raster.
    - All Pads share code 200 and all Corridors 201 (`earthworks.py:39, 81`).
    - `src` is uint8, so at most 255 codes.
19. **No alternative ledger can be composed** (code reading). `compose` takes no `ledger=` (`compose.py:125, 148`); a scenario ledger can't be composed without editing the file. `test_ground.py:97` builds `g30` and never asserts on it.
20. **Sampling a long route is infeasible** (scaling inferred from the measured timing). `sample` composes the whole bbox of all points (`sample.py:22`). A TRI-scale route bbox at 2 m is about 5×10⁹ cells; a 10 km diagonal already takes 5.1 s.
21. Zone geometry is cached at module level (`compose.py:68-80`) and never invalidated; a long-running server would serve stale zones (code reading).
22. The `compose` function shadows the module `region.ground.compose` (`__init__.py:11`); the tests resort to importlib (`test_ground.py:103`).
23. `split_riverworks.py:9` says the levee crest is 155.8 m; the code at `:47` uses 152.5. Its geometry thresholds (E 721,000; 300 m; 50 m) are also in code.

**Rules, tests and baseline**
24. **Mixed date types.** `ruling.date` loads as `datetime.date` for 126 rules and as a string for 11; `json.dumps` fails on the raw registry.
25. **System vocabularies disagree.** `SYSTEMS = {metro, tri, apex}` (`rules.py:27`), while the schema allows `orr | tv | other`.
26. **The baseline capture is not deterministic.** `capture.py:12` claims it is, but `:92` writes `date.today()` into README.md.

## 8. Solid and reusable as the hub's core
- The write path's shape: ULIDs, If-Match with `Conflict`, full history, the legacy_key table with `(kind, legacy)`, thin columns plus JSON `data`, the R-tree bbox query, numbered migrations.
- The seed idea: one file per record and a three-way merge with a conflict folder. It needs bookkeeping fields excluded from the comparison, FK-ordered import, and stable keys for keyless tables.
- The ground: the compositor's rule and ledger-as-data (dates, files and kinds are one record edit, proven by a test), per-cell provenance, the Pad/Corridor daylight formula with volumes, the `check` report against map3, and the 1912 SPEC as a contract pattern.
- The registry: ids, statuses, ranked decisions, rulings with words and source, params with source line, and the validator.
- The tests: the baseline (41 routes every 5 m, 73 run times, platforms, approaches, issues) and the calibration gates.

## 9. Missing for the hub (none of these were found)
- **API**: no `region/api`; FastAPI not installed (pydantic 2.13 is).
- **Jobs and cache**: no `region/jobs`, no queue table, no input manifests, no ground tile cache.
- **Engine host**: no `engine/` or `app/`, no contract schemas (Node v22 is present).
- **Scenarios, changesets and overlays.**
- **Validation per kind**: no CHECK constraints, no JSON schemas, no validators.
- **Events**: no outbox or listener in `db.py`.
- **Importers and exporters**: none.
- **Registry and params in the DB**: no mirror into the `rule` table, no `param` table.
- **Lane B consumption**: no reader for STATUS.json, the 1912 surface or confidence, the Sanborn and Deck outputs, or the path configs.

## What the new hub must support from this part
- A records layer that keeps ULIDs, If-Match, history and legacy keys. It must also add:
  - true PATCH (with key deletion) and no-op detection;
  - delete/supersede;
  - restore;
  - multi-record transactions and changesets (author, message, undo unit);
  - versioned membership tables (route_section) or membership in the parent's data;
  - R-trees on every geometry table.
- Scenarios and alternatives as overlays on a base: `scenario_id`, with edits merged on read. The same mechanism should serve stacked/spread Fountain Square, era and service plans, and street/plot base-vs-authored edits (origin, plate, import run, per-feature conflict list; imports never move authored features).
- A seed merge that:
  - ignores version, created and updated when comparing, or carries them faithfully;
  - imports in FK order inside one transaction with a backup;
  - has stable keys for keyless tables (legacy_key by kind+legacy);
  - writes LF-normalised files;
  - excludes derived rows (`structure.origin='solved'`);
  - reconciles `region/seed` with today's `hub/seed` path.
- Per-kind validation (vocabularies, JSON schemas for `data`, units) enforced on write and on import, generated from the contract.
- An event outbox (record path, version, changed sections) for SSE and job invalidation.
- A job graph with a cache keyed by input record versions, file hashes and engine version; `result` extended with an inputs manifest, status and an artifact pointer. Services need a route/pattern column so invalidation can join.
- A ground service:
  - the base and tiers chosen from `ground_layer` records, not constants;
  - consume the real 1912 surface, confidence and cover when `STATUS.json` says done, keeping nodata honest;
  - tile-independent composition (feather and slopes computed with a halo);
  - stable provenance codes per work id;
  - a ledger or scenario passed in;
  - corridor or tiled sampling for long routes;
  - an on-disk tile cache;
  - the river surface as a param.
- Ledger works, zones, parametric earthworks and line works in one earthwork model with an explicit order, years, timeline and source.
- The registry and params as records (YAML as seed) with:
  - a single source of each value, with drift tests against `data/profile/*.json` until those files retire;
  - normalised dates;
  - structured flag kinds;
  - test references validated as pytest node ids;
  - a shared system vocabulary across rules and the model.
- Baseline diffing (same, rule fix with id, or unexplained) as a first-class job, with calibration gates kept. The roughly 30 `test_core` tests on `metro_profile.py` and the Deck tie should be re-homed as engine invariants before that file is deleted.
- Packaging and paths: declare `region` and its deps (python-ulid, shapely, rasterio, pyproj, scipy); gitignore `region.db*` and `seed_conflicts`; read the machine paths from `configs/*_paths.json` (a Windows-first CLI).

Scratch probes (not in the repo): `/tmp/claude-0/-home-user-cincinnati-rail/388de07f-a9eb-500e-a913-639254f5ddc4/scratchpad/exp_model2.py`, `exp_ground.py`, `exp_ground2.py`.
