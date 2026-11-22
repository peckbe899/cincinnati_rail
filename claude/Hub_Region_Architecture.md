# The hub: the architecture we build

Adopted 21 November 2026 as the build spec for the hub (branch `hub_region`). How it was made: five readers mapped the
old hub, the Profiles engine, the Deck, railsim and the existing `region/` code; four architects each proposed a whole
hub from one angle (model, compute, product, operations); two judges scored them; this is the synthesis, with the
model proposal as the spine and the others grafted on. It supersedes the storage layout of migration 0001 (empty
everywhere, so replaced at no cost) and refines plan sections 4 to 8. Items for Ben to rule are listed at the end;
each has a default the build takes until he rules.

**Checked for this synthesis:**
- The 0001 layout is used only by `tests/test_model.py`, and `region/seed/` does not exist. Migration 0002 can therefore replace the layout at no cost.
- Node here is 22.23 and strips TypeScript types itself.
- On npm, `typescript` latest is 7.0.2, and the 6 line is at 6.0.3. openapi-typescript 7.13 peers on `typescript ^5.x`. @hey-api/openapi-ts 0.99 accepts 6.
- FastAPI 0.165.0 is on PyPI but not installed here. Starlette 1.7 and uvicorn 0.54 are installed.
- SQLite here is 3.53.1, with RTREE.
- `hub/` and `region/` are directories at the repo root, so a Linux launcher named `hub` (Proposal 4) cannot exist.
- `ground/1912/STATUS.json` says stage `contours`, `done: false`.
- `basin.json` last changed on 14 November.
- The baseline's `align` keys `st`, `sg`, `so` and `stt` by station index, and `del` by station name.

## 1. What the hub is

The hub is one local program on Ben's machine. It has four parts:
- a Python server over one SQLite truth database;
- a cache that can be deleted and rebuilt;
- a TypeScript rules engine that runs both in a Node sidecar and in the browser;
- one web app made of panes.

Every thing in the design is a versioned record in one store: a section, a profile, a platform, a param, a ruling, a street, an era. Each record sits in a layer. Imports are at the bottom, the old hub's records above them, Ben's main design above that, and scenarios on top. Every view is (layer, year, timeline). Every number on screen is a cached result of a pure job, keyed by the content it read. The tests at line, station and network scale are job types, and panes draw their results. Nothing that could be a record is fixed in code. Every way of growing the hub is a folder with a declared contract and a test that proves it.

| To add | Where | It must declare | Test that proves it |
|---|---|---|---|
| A record kind | `region/ext/<f>/kinds/<kind>.yaml` | JSON Schema for `data`, version, geometry, promoted columns, refs with `on_delete`, merge unit, rebase policy, legacy kinds, seeded or not, `x-unit` on numbers | `test_every_kind_file_is_valid`; a generic create/read/patch/delete/history round trip over every discovered kind |
| A kind version | `region/ext/<f>/upgrade/<kind>.py` | `up_<n>(data) -> data`, pure | `test_upgraders_reach_current_version` |
| An importer | `region/ext/<f>/importers.py` | `name, version, namespace, layer`, `sources()`, pure `records()` | rerun writes nothing; two databases give identical ids; inputs round trip |
| A job type | `region/ext/<f>/jobs.py` | `name, version, scope, host, priority, timeout_s`, `plan()`, pure `run()`, axes read | `test_job_type_contract` (stable key, determinism, no input writes) |
| An engine method | a row in `engine/src/methods.ts` plus zod in and out | `name@version`, contract major, rule ids it can emit | vitest golden or property test; schema drift |
| A feature API | `region/ext/<f>/router.py` | mounted under `/api/v1/x/<f>/`, writes only through the Store | OpenAPI drift test |
| A pane, map layer, sheet band or command | `app/src/plugins/<f>/index.ts` | a `Plugin` with ids; a layer's `available()` reason | registry unit test (unique ids); a Playwright smoke test per pane |
| A lane-B data tier | `configs/hub_paths.json` | name, root, manifest or index, handshake file, required, mount | `test_tiers_report_present_partial_missing` |
| A param, era, rule, ruling or scenario | records (rules: `rules/registry.yaml`) | scope, year range, ruling id | `test_a_param_change_is_one_record_edit`; the invariant tests |
| An exporter | job type `export.<fmt>` | media type of the output | a round-trip test |
| A CLI command | `region/cli/<name>.py` | `register(subparsers)` | `test_cli_lists_every_command` |

## 2. Decisions (continuing the checklist's section 9)

### 9.9 One record store (21 Nov)

- **Context.** 0001 has 26 tables, one per kind. They are empty everywhere. Layers make the key (layer, id), which breaks SQL foreign keys anyway. The maps list a dozen kinds that 0001 lacks.
- **Options.**
  - (a) Keep the per-kind tables and add a generic table (Proposals 2, 3, 4).
  - (b) One envelope table `rec`, with kinds as data files (Proposal 1).
- **Decision.** (b), in migration 0002, which drops the empty 0001 tables.
  - Promoted columns are derived from `data` by each kind's column map, so a column can never disagree with the data.
  - Read-only SQL views per kind (`v_section`) serve ad hoc queries.
  - A typed satellite table is added only when a measured query needs one.
- **Consequence.** History, events, layers, the R-tree and validation each exist once. A new kind needs no migration.

### 9.10 Layers: one copy-on-write mechanism (21 Nov)

- **Context.** Three needs are one problem:
  - the Deck's base and Ben's edits (9.5, 2.3.9);
  - imports that never overwrite Ben;
  - Fountain Square's alternatives.

  Review 2.6 objected to overlays that drop nulls and merge silently.
- **Options.**
  - Snapshots (Review 2.6).
  - Field overlays (Proposal 2).
  - Three separate tables (Proposal 3).
  - Defer the question (Proposal 4).
  - Copy-on-write at record grain (Proposal 1).
- **Decision.** Copy-on-write at record grain. Each revision is a whole record and is read whole. The layer tiers are fixed:
  - `import:*` layers are siblings. Each owns a disjoint id namespace, enforced on write. A collision between two import layers is a conflict row, never settled by stacking order.
  - Above them sits `legacy:old_hub`.
  - Above that sits `main`.
  - Scenario and proposal layers form a tree under main.
  - Named versions are tags.
- **Consequence.** There is one read path: the first revision found up the chain wins, and a tombstone hides the record. Null and absent stay distinct. Compare is two views side by side.

### 9.11 Rebase (21 Nov)

- **Context.** When a lower layer changes, Ben's copied-up revisions have a stale base. Design rule 3 says his inputs are never overridden.
- **Options.**
  - Merge everything automatically (Proposal 1).
  - Dry-run reports only (Proposal 4).
  - Mark the edits stale (Proposal 3).
- **Decision.** A three-way merge at the kind's merge unit.
  - A change below may apply on its own if it touches only fields Ben did not change, and no geometry or chainage. It is written as its own listed, revertible `rebase` changeset.
  - Two cases become a `conflict` row carrying a proposed revision. Ben's revision stays on read until he accepts.
    - Any geometry or chainage change under one of his revisions, such as a re-path, or a refit under a width edit.
    - Any overlap with fields he changed.
  - A profile is one merge unit (`atomic`), per the 1 November ruling.
- **Consequence.** A review queue pane (orphans, proposals, conflicts) is part of slice 1.

### 9.12 Kind files and feature folders (21 Nov)

- **Options.**
  - YAML holding a JSON Schema (Proposal 1).
  - A pydantic KindSpec (Proposal 3).
  - Python plus JSON (Proposals 2 and 4).
- **Decision.** One YAML file per kind: a JSON Schema 2020-12 for `data`, plus annotations.
  - Each file is validated against `region/kinds/_meta.schema.json`.
  - Python validates records with jsonschema. The app gets generated TS types.
  - There is no hand-written pydantic copy of a kind.
  - The engine contract is owned by zod, because TypeScript executes it. Pydantic models are only ever generated from it.
  - Features live in `region/ext/<feature>/` and `app/src/plugins/<feature>/`, and are found by discovery.
- **Consequence.** Each schema has one owner, and each generator has a drift test.

### 9.13 Writes and status codes (21 Nov)

- **The primary write** is a PUT of the whole record with If-Match.
- **PATCH** is RFC 6902 JSON Patch only. Ben's seed has 293 distinct null-valued key paths, and RFC 7396 merge patch would delete them.
- **Status codes.**
  - 428 for a missing If-Match.
  - 412 for a stale one, with the current record, its `by` and a diff.
  - 409 for reference, namespace, authority, rebase and revert conflicts.
  - 422 for invalid data.
- **Undo.** Every write belongs to a changeset. Undo is a revert changeset, with If-Match on what the original produced, so a later edit makes the undo a 409.
- **No amending.** A committed changeset is never amended. Drag drafts are coalesced in the client before one save.

### 9.14 Chainage basis (21 Nov, for Ben to rule)

- **Context.** Today's stationing is UTM 16N grid length, not ground distance.
  - Line 6 ends at 29,539.6 m, which is its grid length. The geodesic length is 29,534.8 m.
  - The UTM scale error is +170 ppm at Fountain Square, about +313 at Dayton and +516 at Wilmington.
  - The 0001 comment and plan section 4.2 say "ground distance", which is wrong.
- **Options.**
  - Keep grid and declare it.
  - Switch to ground distance. This would move Line 6's controls by about 5 m and break the baseline.
- **Decision.** Every section declares `chainage_basis: "grid:26916"`. Stationing stays as Ben drew it. The engine input carries a `scale` per section, for railsim and quantities.
- **Consequence.** A later low-distortion CRS becomes a declared, migrated change. WP0 corrects the plan text.

### 9.15 Heights (21 Nov)

- **Units in the model.** Every level is metres NAVD88.
- **Declared per ground layer.** A `ground_layer` record declares `vdatum`, `units` and the transform it came in by. That is either `navd88_m`, or the 1912 city datum with its fitted offset and a confidence path.
- **Per field.** Every level field carries `x-unit`.
- **Feet** appear only at the import and display edges.

### 9.16 Time and the view (21 Nov)

- **The view** is `View(layer, year, month, timeline)`. Timeline is canon or real, as `region/ground` already has.
- **Dates** are partial ISO (`1931`, `1931-09`), stored as month intervals.
  - A view instant is the end of its year, or of its month.
  - A record is open when its opening interval starts at or before the instant, and it has not closed by then.
  - A year-only date seen in a month view shows with an uncertain-date mark.
- **Undated** built records count only at the present, as the ground compositor does (6 November ruling).
- **Eras** are records, never layers.
- **Cache keys.** A job declares which axes it reads, and only those axes enter its key, so canon and real results never collide.

### 9.17 Ids: match before mint (21 Nov)

- **Context.** Two machines must mint the same id for the same source. Old keys carry names and ordinals (`Line_8|Cincinnati State#2`, `metro:Syacmore:715445:4331182`), so hashing them would re-key a record on a rename.
- **Decision.** `IdLookup.id_for(lkind, key)` tries three things in order:
  1. the persisted legacy index;
  2. a declared rename match (geometry, chainage, neighbours);
  3. only then `ids.stable(namespace, key)`, which is a fixed epoch per namespace plus 80 bits of sha256.
- **The id ledger.** New keys and aliases are appended to `region/ids/<namespace>.tsv` in git: sorted, one line per key. Two sessions running the same import append the same lines, so git merges them cleanly.
- **Authored records** get random ULIDs.

### 9.18 Truth, cache and blobs (21 Nov)

- **`region.db`** holds the truth: records, layers, changesets, the outbox, conflicts, import runs, seed bases and Ben's waivers.
- **`cache.db`** is attached and can be rebuilt. It holds jobs, results, dependencies, goals and issues. It is never backed up.
- **Blobs** (arrays and GLBs) are content-addressed files under `var/cache/blobs/`.
- **The outbox stays in the truth DB**, because SQLite does not make one transaction atomic across attached WAL databases.
- **One writer thread per database file.**

### 9.19 Jobs (21 Nov)

- **The key** is a hash over the content hashes of what `plan` read, never record versions:
  - records as resolved in the view;
  - file sha256s;
  - resolved params;
  - upstream output hashes;
  - the job module's source hash;
  - the engine build and contract majors;
  - the axes the job declared.
- **Early cutoff.** An upstream result enters a key by its output hash, so a note edit never reruns railsim.
- **Dependencies** are exactly the plan's reads, stored in `result_dep`. Goals say what to keep fresh.
- **Jobs never write input tables.** `run` is pure and returns outputs. The scheduler re-plans and writes the outputs only if the key is unchanged; otherwise it marks the result stale and re-queues the job.
- **Crash recovery** is by leases with a heartbeat.

### 9.20 Engine host (21 Nov)

- **Options.** Binary frames (Proposal 2), NDJSON (Proposals 1, 3, 4), one CLI process per call, or embedded V8.
- **Decision.** A pool of Node sidecars speaking NDJSON over stdio, behind `EngineClient`.
  - `EngineClient` has three implementations: `Pool`, `OneShot` and `Fake`.
  - A hello handshake carries `engine_build` and the contract majors.
  - One method table serves the sidecar, the CLI and the browser worker.
  - Node runs the `.ts` source directly (`erasableSyntaxOnly`), so there is no dist for Node. Vite bundles the same source for the browser.
  - `engine_build` is the sha256 of `engine/src/**` plus `engine/package.json`.
  - Node 22.18 or later is required, 24 LTS recommended.
  - Children exit on stdin EOF, because Windows does not kill orphan processes.
  - Binary frames come in only if a budget test fails.

### 9.21 Toolchains (21 Nov)

- **TypeScript 6.0.x is pinned.**
  - openapi-typescript peers on `^5`, and TS 7 has no classic compiler API.
  - `tsgo` is optional, for fast checks.
- **API types** come from FastAPI's committed OpenAPI file, through `@hey-api/openapi-ts` (types only).
  - They sit behind a hand-written transport of about 200 lines.
  - The generated files are committed with drift tests.
- **npm workspaces** (`engine`, `app`) with one root `package-lock.json`. The root's playwright stays, for the old hub.
- **Python** uses uv, with a universal `uv.lock` and `.python-version` 3.12. Ben's machine runs python.org 3.12.10.
  - An exported `requirements.lock` keeps a plain `pip install -r requirements.lock -e .` working.
  - Ben approves uv before it is installed on his machine.
- **Lint** is ruff (with the unspecified-encoding rule) and Biome.
- **Exact versions** are whatever the locks resolve on the day.

### 9.22 Launcher, start-up and `var` (21 Nov)

- **Launchers.** `crhub.cmd` (CRLF, runs under PowerShell's Restricted policy) and `crhub` (sh).
- **`crhub setup`** installs dependencies, builds the app, migrates and runs the first imports.
- **`crhub serve`** never runs npm and never touches the network. In order, it:
  - takes the single-instance lock;
  - runs `quick_check`;
  - backs up before any pending migration, then migrates;
  - imports pulled seeds and prints a report;
  - scans the data tiers;
  - serves on 127.0.0.1:8766 (set in config).

  It refuses to create an empty database. It shows a banner when `app/dist` is older than its source.
- **Where `var` lives.** On Windows the default is `%LOCALAPPDATA%\CincinnatiRail\hub`, not the repo under Documents, which OneDrive often syncs. `configs/local.json` can override it. Doctor refuses a synced folder.

### 9.23 Strangler (21 Nov)

- **Options.**
  - Re-implement the old API in the new server (Proposal 3, stage S1).
  - Two processes, with authority per kind (Proposal 4).
  - An old-hub layer (Proposal 1).
- **Decision.** Two processes and two databases, with no change to the old hub (Review 2.11).
  - `legacy:old_hub` is built from `hub/seed/`, or from a backup-API snapshot of `hub\hub.db`, never the live file.
  - Authority is a record per kind: `authority {kind, owner: legacy|model, ruling}`.
  - While legacy owns a kind, main and legacy refuse writes to it (409 authority), and promote is refused.
  - Scenarios stay writable, so Ben can try designs in the new hub without forking the truth.
  - Flipping a kind to model squashes its legacy revisions into main as one changeset.
  - New-to-old writes go only through the old hub's HTTP API with If-Match, and only for Deck platforms (2.1.10).

### 9.24 Branches and seeds (21 Nov, for Ben to confirm)

- **Branches.** Merge `hub_region` into `main` at the end of increment 1; lane A's paths are disjoint from lane B's.
  - After that, Ben runs `crhub` from `main`.
  - Before that, he can try it in a worktree: `git worktree add ..\cr_hub hub_region`.
- **Seeds are per layer.**
  - `region/seed/main/` is written only by Ben's export, and belongs to lane B.
  - A cloud session writes a proposal layer to `region/seed/proposals/<slug>/`, which belongs to lane A. Ben's hub imports it as a proposal layer, and he promotes it with its conflict list.
  - Import and legacy layers are never seeded; they rebuild from their sources.

### 9.25 One owner for each rule value (21 Nov)

- **`rules/registry.yaml`** is the `import:registry` layer.
- **Ben's change** to a value is a main-layer `param` revision that cites a ruling.
- **If the registry later changes a value Ben overrode,** that is an `authority_divergence` conflict, never a silent change.
- **The flow back.** A lane A session folds ratified overrides into the YAML. The main revision is then listed as redundant.
- **Resolution.** Params resolve by the most specific scope (section, then route, then system), then by year range.

### 9.26 Lane-B inputs (21 Nov)

- **Data tiers.** Files outside git are tiers in `configs/hub_paths.json`. Records name them as `tier://<tier>/<path>`, never by absolute path.
- **Missing tiers** show as status chips and as a layer's `available()` reason, never as errors.
- **Changed sources** produce a dry-run import report, and apply is an explicit step. Examples: a new Sanborn batch, `basin.json`, the line files.
- **Versioned base sets.** Each import run records its source sha256s, so every base set is versioned.
- **The 1912 surface.** When its handshake says done with targets met, the `real_1912` ground layer record becomes available. Making it the base is one record edit.
- **Recompute after a base change** runs at background priority, with a pending mark per section and an estimate. At today's 5.1 s per 10 km, ground sampling alone for 1,656 km takes about 14 minutes, before any solves.

### 9.27 Section geometry during the strangler (21 Nov)

- **Context.** `data/profile/lines/*.json` are Deck-tie output, written with the Windows `fn.split('/')` bug at line 665. Ben's copies can differ from git.
- **Decision.**
  - Plan geometry has legacy authority until the Deck adapter lands.
  - The line files are read from git, and each import run records their sha256.
  - A re-path that moves chainage under Ben's profile becomes a proposal carrying the ported `reframeDoc` result (9.11).

### 9.28 Writers outside the server, and bulk writes (21 Nov)

- **SSE tails the outbox by `seq`.**
  - An in-process notify only wakes it.
  - A 500 ms check of `PRAGMA data_version` catches writes from the CLI, scripts and seed imports.
- **CLI writes** go through HTTP while a server holds the lock. Otherwise the CLI takes the lock itself.
- **Imports** diff by hash outside the write lock, then commit in one short transaction.
- **Big changesets.** A changeset of more than 200 records emits one summary event instead of one event per record.

### 9.29 Seeds that rebuild byte for byte (21 Nov)

- **A seed file** is `{id, kind, kv, geom WKT, data}`, with sorted keys and LF line endings.
- **Bookkeeping** (version, created, updated, by, changeset) is left out of seeds and out of the content hash.
- **Geometry** is snapped to 1 mm at write time.
- **`.gitattributes`** covers only lane A paths and `region/seed/**`, so lane B's 61 CRLF files are not renormalised.
- **Export** imports pulled seeds first, and refuses while unmerged seed changes remain.

### 9.30 Maps offline (21 Nov)

- **A local MapLibre style**, with glyph PBFs and a sprite committed under `app/public/map/`. Without them, labels fail silently offline.
- **Editable data** always comes as full GeoJSON from the API, never as vector tiles.
- **Static layers** are PMTiles from a tile job.
- **Era filtering** runs on the client.
- **A Playwright test** runs with every non-local request aborted.

## 3. Layout

```
crhub.cmd, crhub                 launchers (9.22)
configs/hub.json                 port, var root, pool sizes;  hub_paths.json tiers;  local.example.json
region/
  __main__.py                    CLI; discovers region/cli/*.py
  core/                          frozen shared contracts (WP0)
    view.py                      View(layer, year, month, timeline)
    protocols.py                 Store, Op, JobType, PlanCtx, RunCtx, Output, Scheduler, EngineClient, Importer, IdLookup
    errors.py                    NotFound, PreconditionRequired, PreconditionFailed, Conflict, Invalid, EngineUnavailable
    events.py                    event payload TypedDicts
    ids.py                       new(), stable(namespace, key)
    features.py                  discover(): region/ext/*/ kinds, importers, jobs, router, validators, sources
    fsio.py                      write_atomic (WinError 5/32 retry), utf-8 reads, write guard
    paths.py                     repo, var, tier:// resolution
    log.py                       JSONL per day, request_id context
  cli/                           setup, doctor, serve, rec, model, imports, rebuild, jobs
  model/                         the store (WP1)
    db.py                        connections, pragmas, writer thread, attach cache.db
    migrate.py                   .sql/.py migrations, one transaction each with schema_version
    migrations/0002_store.{py,sql}
    schema.sql                   committed schema snapshot (drift test)
    kinds.py                     load and validate kind YAML, upgraders
    store.py                     Store: get, list, write, put, patch, delete, restore, history
    layers.py                    chain resolution, copy-up, promote, tags, diff
    changesets.py                atomic batches, revert, outbox rows
    merge.py                     merge3 per merge unit; rebase planner (auto or proposal)
    refs.py                      ref extraction, integrity, reverse lookups
    legacy.py                    legacy index, IdLookup, id ledger
    imports.py                   apply_import: hash diff, dry run, report, import_run
    seed.py                      seed v2 per layer
    backup.py                    online backup, quick_check, retention, restore
  kinds/                         _meta.schema.json, _vocab.yaml, authority, waiver, feature, note
  api/                           FastAPI (WP2): app, security, problem, meta, records, layers, changesets,
                                 imports, jobs, events (SSE), files (mounts), ops, lock; openapi.json
  jobs/                          (WP3) keys, plan, scheduler, hosts, cache, goals, registry,
                                 migrations/0001_cache.sql, types/{noop,seed}.py
  enginehost/                    (WP4) client.py (Pool, OneShot, Fake), build.py (engine_build)
  contract/gen/                  pydantic generated from engine/schema (WP4)
  ext/                           features (WP5)
    network/                     kinds node, section, route, track, ground_profile; importer profile_lines
    stations/                    kinds station, stop, platform; validators
    profiles/                    kind profile; inputs.py; jobs solve_section, golden_diff; router
    rules/                       kinds rule, ruling, param, era; importer registry
    legacy/                      kinds roadmap_item, camera, view; importer old_hub; authority defaults
  analysis/                      railsim adapter (increment 2)
  ground/  rules.py              built, unchanged
  seed/main/  seed/proposals/    seeds (9.24)
  ids/                           namespaces.yaml, <namespace>.tsv id ledger
engine/                          @cr/engine (WP4; contract by WP0)
  PROTOCOL.md                    NDJSON protocol
  src/contract/                  zod: common, section_input, vertical_rail, flags
  src/index.ts methods.ts        METHODS, ENGINE_VERSION
  src/grid.ts params.ts tol.ts   grid helpers; typed params accessor; the only numeric tolerances
  src/geom/path.ts               cumulative length, bisect (port of pathAt 617)
  src/vertical/                  vertices.ts, design.ts, rail.ts (port of 725-828)
  src/rules.gen.ts               RuleId union generated from rules/registry.yaml
  src/sidecar.ts cli.ts          stdio host; one-shot CLI
  schema/v0/*.json               generated, committed
  test/                          golden, property, determinism, lint, sidecar, contract
app/                             (WP6)
  src/core/                      plugin.ts, registry.ts, url.ts, store.ts, units.ts, drafts.ts, undo.ts
  src/api/                       gen/ (committed), client.ts, events.ts, events.worker.ts (SharedWorker)
  src/engine/worker.ts           Comlink worker over @cr/engine
  src/plugins/                   map, line-sheet, inspector, jobs, review, palette, legacy
  public/map/                    style.json, glyphs/, sprite
  test/unit/  e2e/
.github/workflows/hub.yml        CI
```

## 4. Model additions

### Migration 0002

`0002_store.py` runs first, in the same transaction. It asserts that every 0001 table is empty; the SQL then drops them. Enums are validated in Python, not by SQL CHECKs, so adding a value needs no table rebuild.

```sql
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);       -- db_id, epoch, last_backup, last_export
CREATE TABLE kind (name TEXT PRIMARY KEY, version INT NOT NULL, feature TEXT, geometry TEXT, sha256 TEXT, spec TEXT);
CREATE TABLE layer (id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL, tier TEXT NOT NULL,   -- import|legacy|main|scenario|proposal
  parent INT REFERENCES layer(id), namespace TEXT, state TEXT DEFAULT 'open', title TEXT, note TEXT, created TEXT, by TEXT);
CREATE TABLE rec (rid INTEGER PRIMARY KEY, layer INT NOT NULL REFERENCES layer(id), id TEXT NOT NULL, kind TEXT NOT NULL,
  kv INT NOT NULL, version INT NOT NULL, hash TEXT NOT NULL, base_hash TEXT, deleted INT NOT NULL DEFAULT 0,
  origin TEXT NOT NULL, source TEXT, by TEXT NOT NULL, changeset TEXT NOT NULL, import_run INT, created TEXT, updated TEXT,
  name TEXT, system TEXT, parent TEXT, c0 REAL, c1 REAL, ord TEXT, phase TEXT,
  open_lo INT, open_hi INT, close_lo INT, close_hi INT,                -- months since year 0; NULL = undated
  x0 REAL, y0 REAL, x1 REAL, y1 REAL, geom BLOB, data TEXT NOT NULL, UNIQUE (layer, id));
CREATE INDEX rec_id ON rec(id);  CREATE INDEX rec_kind ON rec(kind, layer);  CREATE INDEX rec_parent ON rec(parent, c0);
CREATE VIRTUAL TABLE rec_rtree USING rtree(rid, x0, x1, y0, y1, +layer, +kind);
-- triggers: AFTER INSERT/UPDATE OF x0,y0,x1,y1/DELETE keep rec_rtree in step (raw SQL included; fixes defect 8);
-- BEFORE UPDATE OF version: RAISE(ABORT) unless new.version = old.version + 1
CREATE TABLE rec_hist (layer INT, id TEXT, version INT, hash TEXT, changeset TEXT, at TEXT, by TEXT, row TEXT NOT NULL,
  PRIMARY KEY (layer, id, version));                                   -- row in get() shape (defect 7)
CREATE TABLE ref (layer INT, src TEXT, role TEXT, dst TEXT, PRIMARY KEY (layer, src, role, dst));  CREATE INDEX ref_dst ON ref(dst);
CREATE TABLE legacy (lkind TEXT, key TEXT, id TEXT NOT NULL, status TEXT DEFAULT 'current', PRIMARY KEY (lkind, key));
CREATE TABLE changeset (id TEXT PRIMARY KEY, layer INT, by TEXT, client TEXT, message TEXT,
  kind TEXT,                                                           -- edit|import|seed|revert|rebase|promote|migration|legacy
  reverts TEXT, created TEXT, count INT);
CREATE TABLE event (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, type TEXT, layer INT, kind TEXT, id TEXT,
  version INT, hash TEXT, op TEXT, changeset TEXT, by TEXT, client TEXT, fields TEXT, bbox TEXT);
CREATE TABLE conflict (id TEXT PRIMARY KEY, layer INT, rec_id TEXT, kind TEXT,
  reason TEXT,                                                         -- both_changed|geometry_under_edit|orphan|dangling_ref|invalid|namespace|authority_divergence
  ours_hash TEXT, theirs_hash TEXT, base_hash TEXT, proposed TEXT, fields TEXT, state TEXT DEFAULT 'open',
  import_run INT, created TEXT, resolved_by TEXT, resolution TEXT);
CREATE TABLE import_run (id INTEGER PRIMARY KEY, importer TEXT, version TEXT, layer INT, sources TEXT, dry_run INT,
  state TEXT, counts TEXT, report TEXT, changeset TEXT, started TEXT, finished TEXT);
CREATE TABLE tag (layer INT, name TEXT, seq INT NOT NULL, note TEXT, created TEXT, by TEXT, PRIMARY KEY (layer, name));
CREATE TABLE seed_base (layer INT, id TEXT, hash TEXT NOT NULL, PRIMARY KEY (layer, id));
-- seeded rows: layer main; legacy:old_hub; import:profiles, import:registry (namespaces from region/ids/namespaces.yaml)
```

### cache.db (`region/jobs/migrations/0001_cache.sql`)

`job` (with a unique index on `(type, key)` for queued and running jobs, plus lease and heartbeat), `job_log`, `result` (key, type, scope, view, status, output_hash, meta, arrays, engine_build, last_used, pinned), `result_dep(key, ref, ref_hash)` indexed by ref, `goal`, `issue` (dedupe unique), `blob`, `file_hash(path, size, mtime_ns, sha256)`, `cursor`.

### Semantics

- **Read.** The chain is the view's layer, its ancestors up to main, then legacy, then every import layer. The first revision found wins, and a tombstone hides the record. A list is one window-function query over the chain, with the R-tree and the time columns as filters.
- **Write.** A write goes only to `view.layer`, and If-Match is checked against the resolved revision. The ETag is `"<layer>:<version>"`. The first write to a record held below copies it up, with `base_hash` set. A copy-up into a scenario or proposal continues the record's version lineage (base version + 1), so the versions Ben sees in one view only rise; copy-ups into main, legacy and import layers start at 1. Undoing a scenario's first edit writes a new version equal in content to the base (ruled by the lead, 21 Nov, during integration).
- **Changeset.** It is atomic, and every operation is validated before any is written. A changeset of more than 200 records gets a summary event. Revert writes the prior content under If-Match.
- **Promote.** A scenario's revisions go to its parent as one changeset, with If-Match against the parent's current revisions. Conflicts are listed, and the layer becomes `promoted`.
- **Tag.** A tag reads its layer as of an event `seq`, reconstructed from `rec_hist`.
- **Authority.** While legacy owns a kind, writes to main and legacy refuse it, except from the legacy importer.
- **Results** are never records.

### Validation, per kind

Validation runs on every write, import and seed import, and in `doctor --data`. The steps, in order:
1. The kind is known, and the data is upgraded to the current `kv`.
2. The JSON Schema passes. It is strict for fields engines read, with an open `attrs` bag for import provenance.
3. Columns are derived from `data`, and dates are parsed into intervals.
4. Geometry type and validity are checked, coordinates are snapped to 1 mm, and the bbox is set.
5. Refs resolve in the chain, applying `on_delete` as restrict, cascade or nullify.
6. The namespace (for import layers) and authority are checked.
7. The feature's validator runs, for example: every profile platform key belongs to a stop on its section.

Errors abort the whole changeset.

### Profile record

- **One record per section**, merge unit `atomic`.
- **Keyed by platform id:** `st`, `sg`, `so`, `del`, `stt` and `gapfill`.
- **Keyed by chainage:** `pvi`, `ovr`, `tf`, `shafts` and `gnd`.
- **Also carried:** `mode`, `ready`, `frame`.
- **Derived, not stored:** the old doc's `stations`, `summary` and `updated`.

## 5. API (`/api/v1`, FastAPI, 127.0.0.1)

Every read takes `layer`, `year`, `month` and `tl` (timeline). Every write requires `X-CR-Client` and a JSON content type.

| Method | Path | Purpose | Headers |
|---|---|---|---|
| GET | `/meta` | kinds with schemas, features, importers, job types, layers, engine hello, schema version, server epoch | |
| GET | `/health` | liveness | |
| GET | `/k/{kind}` | list: `bbox, parent, ref, ids, q, fields, limit, after, format=geojson, crs=4326` | ETag `"seq:N"`, 304 |
| POST | `/k/{kind}` | create | `Idempotency-Key`; 201, Location, ETag |
| GET | `/k/{kind}/{id}` | one record; `at=version` | ETag `"layer:version"` |
| PUT | `/k/{kind}/{id}` | replace | If-Match (428, 412) |
| PATCH | `/k/{kind}/{id}` | `application/json-patch+json` | If-Match |
| DELETE | `/k/{kind}/{id}` | tombstone | If-Match |
| GET | `/k/{kind}/{id}/history`, `/history/{v}`, `/diff?from&to` | history and RFC 6902 diff | |
| POST | `/k/{kind}/{id}/restore?version=` | restore as a new version | If-Match |
| GET | `/refs/{id}` | what references this record | |
| GET | `/legacy/{lkind}/{key}` | old key to `{kind, id}` | |
| POST | `/changesets` | `{layer, message, ops[]}`, atomic | 412 lists every stale op |
| GET | `/changesets` | `by, since, layer` | |
| POST | `/changesets/{id}/revert` | undo | 409 with diff |
| GET, POST | `/layers` | list; create a scenario or proposal | |
| POST | `/layers/{slug}/promote`, `/layers/{slug}/tags` | promote; tag | |
| GET | `/layers/{slug}/diff?against=` | record diff | |
| GET | `/conflicts` | review queue | |
| POST | `/conflicts/{id}/resolve` | `{take: ours\|theirs\|merged, body}` | |
| GET | `/importers` | list | |
| POST | `/imports` | `{importer, dry_run: true}`, run as a job | |
| GET | `/imports/{run}` | report | |
| POST | `/imports/{run}/apply` | apply a dry run | |
| POST | `/compute` | `{type, scope, view, priority}` -> `{key, state, job}` | |
| GET | `/results?type&scope&view` | latest key for a goal | |
| GET | `/results/{key}`, `/results/{key}/a/{name}` | meta; array bytes (`X-Dtype`, `X-Shape`) | immutable, ETag = key, Range |
| GET | `/jobs`, `/jobs/{id}`, `/jobs/{id}/log` | jobs | |
| POST | `/jobs/{id}/cancel` | cancel | |
| GET | `/events` | SSE | `Last-Event-ID` |
| GET | `/events/poll?since=` | fallback for SSE | |
| POST | `/export`, `/backup`, `/client-log` | ops | |
| GET | `/tiers` | tier status | |
| GET | `/data/{tier}/{path}`, `/assets/*`, `/` | files, app | Range, ETag, gzip (not webp or pmtiles) |
| GET | `/x/profiles/sections/{id}/input` | SectionInput v0 | |
| GET | `/x/profiles/routes/{id}/doc` | old alignment doc rebuilt from records | |

Errors are RFC 9457 `application/problem+json`, carrying `code`, `request_id` and `conflicts`.

### Events

Each event goes out as SSE: `id: <seq>`, then `event: <type>`, then `data: <json>`. Record and changeset events are durable rows in the outbox and replay from `Last-Event-ID`. Job, result and tier events are ephemeral; after a reconnect the client re-reads `/jobs?active=1`.

```json
record    {"seq":18342,"op":"patch","kind":"profile","id":"01K…","layer":"main","version":8,"hash":"…",
           "by":"ben","client":"tab-3f2c","changeset":"01K…","fields":["data.pvi"],"bbox":[713100,4330200,716900,4341800]}
changeset {"seq":18400,"id":"01K…","layer":"import:profiles","by":"import:profile_lines","count":2140,
           "kinds":{"platform":1900,"stop":240},"bbox":[…],"summary":true}
job       {"id":"…","type":"profiles.solve_section","scope":"01K…","state":"running","progress":0.4,"msg":"vertical"}
result    {"key":"…","type":"profiles.solve_section","scope":"01K…","view":"main|-|canon","status":"ok","changed":[[3200,4100]]}
tier      {"tier":"ground_1912_real","status":"missing|partial|present","detail":"stage contours"}
resync    {"reason":"pruned|epoch|overflow","seq":18400}
hello     {"epoch":"…","seq":18400,"engine_build":"…"}
```

## 6. Jobs and cache

**Job types in increment 1:**
- `noop` (tests);
- `seed.import` and `seed.export`;
- `import.<name>` (dry run, then apply);
- `profiles.solve_section` (engine `vertical.rail`);
- `profiles.golden_diff`.

**Job types later:**
- `ground.profile` (cached per section, year and timeline);
- `route.assemble`, `railsim.run` and `railsim.attribution`;
- `crossings.check(pair)` and `checks.issues`;
- `capacity.blocking`;
- `station.graph` and `station.flows`;
- `tiles.build` and `glb.section`;
- `export.<fmt>`;
- `tiers.scan` and `maint.prune`.

**Key composition.**
- `key = sha256(canonical_json({t, tv, code, e, c, axes, in}))`, where:
  - `t` is the type and `tv` its version;
  - `code` is the sha256 of the job module, plus railsim's source for railsim jobs;
  - `e` is `engine_build`, for engine jobs;
  - `c` is the contract majors;
  - `axes` holds only the declared year, month and timeline;
  - `in` is a sorted list of `[ref, hash]` pairs.
- Refs come in four forms:
  - `rec:<id>`: the resolved content hash, so a layer enters the key only through content;
  - `file:<uri>`: the sha256, cached by size and mtime;
  - `param:<path>`: the resolved value;
  - `job:<type>/<scope>`: the upstream `output_hash`.

**Invalidation.**
1. The scheduler tails the outbox past `cursor('invalidator')`.
2. It looks each changed `rec:`, `file:` or `param:` ref up in `result_dep`.
3. It re-plans the affected goals.
4. On a cache hit it moves `goal.latest_key` and emits `result`. On a miss it enqueues the job.

**Scheduling.**
- **Priorities:** 0 for the focused pane, 1 for open panes, 5 for goals, 9 for maintenance.
- **Coalescing:** one pending job per (type, scope, view), and the newest wins.
- **Superseded work:** a running thread job is cancelled by token. A process or engine job is killed after 1 s.
- **Hosts:**
  - `inline` for work under 50 ms;
  - `thread` for I/O;
  - `process` for railsim (a spawn pool, `max_tasks_per_child`);
  - `engine` for the Node sidecar pool.
- **Progress** is reported at least every 2 s. A per-type timeout applies.
- **Leases:** 30 s, with a heartbeat every 5 s. An expired running job is re-queued at most twice.

**Commit.** `run` receives only what `plan` read, so it is pure. After the run, the scheduler re-plans and compares keys:
- if the key is unchanged, the result, its dependencies and its issues are written in one cache.db transaction;
- otherwise the result is stored as `stale` and the job re-queued.

**Blobs** are written to `tmp/`, fsynced and renamed before their row is written. Orphans are swept at start. LRU eviction by `last_used` spares pinned goals.

**Result events** carry `changed` chainage ranges, diffed between the old and new arrays.

**Budgets** (`tests/perf`, marked slow, warn-only on CI):
- an RPC round trip under 5 ms;
- Line 6 `vertical.rail` under 20 ms;
- edit to result SSE under 1 s;
- later, edit to railsim times under 10 s.

## 7. Engine

**Contract v0** (zod in `engine/src/contract/`, exported by `z.toJSONSchema` to `engine/schema/v0/`):

```ts
SectionInput  = { contract: "section_input/0", section_id: string, length_m: number, chainage_basis: "grid:26916",
  scale: number, step_m: number,
  params: { platform_m: number, vc_radius_m: number, vc_min_len_m: number },
  stations: { platform_id: string, order: number, c_m: number /* point c + slide */, level_m: number | null,
              grade_permille: number | null }[],          // deleted platforms removed
  pvi: { c_m: number, z_m: number }[], ground?: { step_m: number, z_m: number[] } }
VerticalRail  = { contract: "vertical_rail/0", engine_build: string, input_hash: string,
  grid: { c0: 0, step_m: number, n: number }, rail_m: number[], grade_permille: number[],
  dv: { c_m: number, z_m: number, kind: "ps" | "pe" | "pvi" | "end" }[],
  curves: { c_m: number, g_in: number, g_out: number, L_m: number }[], flags: Flag[] }
Flag          = { kind: string, sev: "info" | "warn" | "error", c0: number, c1: number, rule: RuleId, data: unknown }
```

Python builds the input; the engine never reads records.

**Protocol** (`engine/PROTOCOL.md`): NDJSON over stdio, one object per line. On start the sidecar writes:

`{"hello":{"engine_version","engine_build","contracts":{"section_input":0,"vertical_rail":0},"methods":["vertical.rail@1"]}}`

| Direction | Message |
|---|---|
| Request | `{"id":7,"method":"vertical.rail","params":{…}}` |
| Progress | `{"id":7,"progress":0.5,"stage":"design"}` |
| Reply | `{"id":7,"ok":true,"result":{…}}` |
| Error | `{"id":7,"ok":false,"error":{"code":"invalid_input","message":"…","stack":"…"}}` |

Logs go to stderr only. Python refuses a contract major it does not know.

**Calling it from Python.** `Pool(size=2)` gives each job a sidecar by consistent hash of section id. It handles timeout, kill and respawn with backoff, and puts the stderr tail into the job log. `OneShot` runs `node engine/src/cli.ts`. `Fake` serves tests.

**First ports** (`profiles.html` 617 and 725 to 828):
- `path.ts`: cumulative length and bisect;
- `vertices`;
- `design`;
- `railAt`, `gradeAt`;
- `railGrid`: the arrays on the 2 m grid, by one merge sweep.

Two details of the port:
- The comparator at line 739 is not antisymmetric. The port sorts by (c, kind rank, order).
- The page keeps the first of two overlapping platforms, so station order is meaning. It travels as `order`.

**Golden test** (`engine/test/golden.vertical.test.ts`):
- Inputs come from `engine/test/fixtures.ts`:
  - `tests/baseline/profiles/<route>.json` `align`;
  - the line file's stations, minus `del` names, plus `so`, in order;
  - params from `rules/registry.yaml` (`settings.*` or `settings_rer.*` by system, with the CVG overlay).
- Rail every 5 m must match `rail_m` within 1 mm on 41 of 41 routes.
- A separate test feeds the `hub/seed` docs straight in. That separates normalisation (`reframeDoc`, `defaultAlign`) from geometry.
- `npm run golden:update` refuses to run without a rule id.

## 8. App

**Shell.** React 19 hosts dockview. Panes mount on a DOM node, so the framework is a choice per pane.

```ts
interface Plugin { id: string; panes?: PaneDef[]; layers?: LayerDef[]; bands?: BandDef[]; commands?: CommandDef[];
  keymap?: KeyBinding[]; urlParams?: UrlParamDef[]; kinds?: KindUiDef[]; activate?(h: Host): Disposable | void }
interface PaneDef { id: string; title: string; accepts?(sel: Selection): boolean;
  mount(el: HTMLElement, ctx: PaneContext): Promise<{ dispose(): void; serialize?(): unknown }> }
interface LayerDef { id: string; group: string; source: Source; style(ctx): LayerSpecification[];
  time?: "intervals" | "none"; pick?(f): RecordRef | null; available(): Promise<true | string> }
interface BandDef { id: string; height: number; draw(g: CanvasRenderingContext2D, view: SheetView, data: BandData): void;
  hit?(x: number, y: number): Handle | null }
```

**Shared machinery.**
- **Plugins** are found by `import.meta.glob('../plugins/*/index.ts')`. Duplicate ids fail a unit test.
- **URL state:** `/w/design?layer=main&year=1985&tl=canon&sel=profile:01K…&c=12400.0&lay=+relief,-plots&map=14/39.10/-84.51`.
  - A zustand vanilla store mirrors the URL. `replaceState` is used while typing and `pushState` on navigation.
- **Records** are cached by TanStack query-core under (kind, id, view).
- **Events.** One SharedWorker EventSource patches the cache by (kind, id, version). The `client` field skips the tab's own echo.
- **Drafts** are shared across panes before a save.
- **Undo** is a stack of server changesets. A 412 offers Keep mine or Take theirs.
- **Units** switch between m and ft.
- **Ctrl+K** resolves legacy keys.

**First panes.**
- **Map.** The 16 Metro sections and stations from `/k/section?format=geojson`, with a local style, glyphs, and relief and Sanborn overviews as image sources.
- **Line sheet.** Canvas 2D bands for ground and rail, platform and PVI marks, and a chainage readout.
  - A numeric table edits PVI and station levels.
  - The engine worker re-solves on each keystroke.
  - On save, a PATCH goes to the server, a job runs, and SSE brings the result back.
- **Inspector.** A form generated from the kind schema, which writes JSON Patch and knows units. It is our own code of about 400 lines, because per-field patches and `x-unit` widgets fight rjsf's whole-form model.
- **Jobs and status bar.**
- **Review queue.** Read-only in this increment.
- **Legacy.** Links to the old pages on 8765.

## 9. Ops

**Windows PowerShell.** `winget install` needs Ben's go-ahead.

```powershell
winget install --id astral-sh.uv -e      # once, after Ben approves
git pull
.\crhub setup        # uv sync --locked; npm ci; npm run build -w app; migrate (backup first); first imports; doctor
.\crhub              # serve: lock, quick_check, backup, migrate, seed report, tiers, http://127.0.0.1:8766
.\crhub doctor
.\crhub export       # before commit; merges pulled seeds first
.\crhub backup       # .\crhub restore <file>;  .\crhub rebuild --compare
# without uv:  py -3.12 -m venv .venv; .venv\Scripts\pip install -r requirements.lock -e .; .venv\Scripts\python -m region serve
```

**Linux:** `./crhub setup && ./crhub serve --no-browser`.

**`crhub.cmd`** sets `PYTHONUTF8=1`, then runs `uv run --locked python -m region %*`. It falls back to `.venv` when uv is absent.

**Lockfiles.**
- `uv.lock` (universal), `requirements.lock` (exported) and the root `package-lock.json`.
- CI runs `uv lock --check` and `npm ci`.
- A monthly update PR must pass CI.

**Database.**
- One writer thread, with `BEGIN IMMEDIATE`.
- Pragmas: WAL, `synchronous=NORMAL`, `busy_timeout=5000`, `foreign_keys=ON`.
- `wal_checkpoint(TRUNCATE)` on shutdown and after imports.
- Each migration is one transaction that includes its `schema_version` row (defect 11).
- Upgrades are tested from fixture databases at every prior version.

**Backups.**
- The online backup API, then `quick_check` on the copy.
- Retention: pre-migrate kept forever; pre-import the last 10; daily 14; weekly 8; manual all.
- `crhub restore` backs up the current database first.
- `rebuild` builds into `var/rebuild/` and compares, and never touches the live database.

**Files.**
- Every write goes through `fsio.write_atomic`: a temp file, fsync, then `os.replace` with a retry on WinError 5 and 32.
- A write guard allows only `var/`, `app/dist`, `region/seed/` and `region/ids/`.
- Subprocesses take argument lists; there is no `shell=True`.

**CI** (`.github/workflows/hub.yml`):
- **`py`:** Ubuntu, Python 3.12 and 3.13, ruff, `pytest -m "not slow and not local"`.
- **`engine`:** Node 22.18 and 24, `tsc --noEmit`, vitest, schema drift.
- **`e2e`:** Playwright Chromium against a fixture database.
- **`windows`:** checked out into the folder `cr test`. Runs the core, model, API and engine-host tests and an end-to-end smoke test.
- **`hygiene`:**
  - no file over 25 MiB;
  - no `*.db`, `var`, `dist` or `node_modules` in git;
  - LF in `region/seed`.
- `test_rer_routes_follow_deck` is strict xfail through `tests/known_failures.txt`.

**Logging.**
- JSON lines in `var/logs/hub-YYYY-MM-DD.jsonl`, kept 30 days, with `request_id` and `job_id`.
- Browser errors reach the same file through `/client-log`.
- Problem responses carry the `request_id`, and toasts show it.

**Security.**
- The server binds to 127.0.0.1 only, behind a TrustedHost allowlist (localhost, 127.0.0.1, [::1]).
- Writes need a JSON content type and `X-CR-Client`. A foreign Origin gets 403. There is no CORS.
- Paths are contained by realpath plus commonpath per mount. These are rejected:
  - `..` and `%5c`;
  - drive letters and UNC paths;
  - `:` (alternate data streams);
  - reserved names (`CON`, `NUL`);
  - trailing dots and spaces.
- Kinds and ULIDs are validated. Bodies are capped at 32 MB. CSP is `default-src 'self'; worker-src 'self' blob:; img-src 'self' blob: data:`.

## 10. First build increment (this session)

### Gate for the increment

- From a fresh clone, `crhub setup` then `crhub serve` brings up the map and the Line 6 sheet.
- A PVI level edited in scenario `try` re-solves locally, saves, and the server result arrives over SSE.
- `crhub export` run twice in a row gives byte-identical output.
- The old hub and its tests are untouched.
- `crhub doctor` passes on Ben's Windows machine (3.12.10). Its SQLite rtree build is unverified until then.

### Order

1. WP0a lands first: the frozen interfaces, marked ★.
2. WP1, WP3, WP4 and WP6 then run in parallel.
3. WP2 and WP5 start against fakes and integrate on WP1, WP3 and WP4.
4. WP6's end-to-end tests come last.
5. Dependency changes go through the lead, who owns every `package.json`, `pyproject.toml` and lock.

### WP0. Contracts and packaging (the lead)

- **0a, blocking: paths.**
  - Edit: `pyproject.toml` (package `region`, every dependency of this increment, `requires-python >=3.12`), root `package.json` (workspaces), `.gitignore`.
  - Create: `uv.lock`, `requirements.lock`, `.python-version`, `package-lock.json`, `engine/package.json`, `engine/tsconfig.json`, `app/package.json`, `app/tsconfig.json`, `biome.json`, `.gitattributes`, `crhub.cmd`, `crhub`, `configs/hub.json`, `configs/hub_paths.json`, `configs/local.example.json`.
  - Create: `region/core/*.py`, `region/__main__.py`, `region/cli/__init__.py`, `region/kinds/_meta.schema.json`, `region/kinds/_vocab.yaml`, `region/ids/namespaces.yaml`.
  - Create: `engine/PROTOCOL.md`, `engine/src/contract/*.ts`, `engine/schema/v0/*.json`, `engine/scripts/gen_schema.ts`.
  - Create: `tests/conftest.py`, `tests/known_failures.txt`, `tests/core/test_core.py`.
- **0b, parallel: paths.**
  - `region/cli/{setup,doctor}.py`, `region/tiers/**`, `.github/workflows/hub.yml`, `region/README.md` (Ben's runbook), `tests/ops/**`.
  - `claude/Hub_Region_Checklist.md` (records 9.9 to 9.30) and `claude/Hub_Region_Plan.md` (4.2: chainage basis).
- **Exposes ★:**

```python
@dataclass(frozen=True)
class View: layer: str = "main"; year: int | None = None; month: int | None = None; timeline: str = "canon"
    # instant() -> int | None ; token() -> str
def ids.new() -> str ;  def ids.stable(namespace: str, key: str) -> str
@dataclass
class Op: op: Literal["create","put","patch","delete"]; kind: str; id: str | None; if_match: str | None
          body: dict | None = None; patch: list[dict] | None = None
class Store(Protocol):
    def get(self, kind: str, id: str, view: View, *, at: int | None = None) -> dict
    def list(self, kind: str, view: View, *, bbox=None, parent=None, ref=None, ids=None, q=None,
             limit: int = 500, after: str | None = None) -> tuple[list[dict], str | None]
    def write(self, ops: list[Op], view: View, *, by: str, message: str, client: str | None = None) -> WriteResult
    def put(self, rec: dict, view: View, *, if_match: str | None, by: str) -> dict
    def patch(self, kind: str, id: str, patch: list[dict], view: View, *, if_match: str, by: str) -> dict
    def delete(self, kind: str, id: str, view: View, *, if_match: str, by: str) -> dict
    def revert(self, changeset: str, *, by: str) -> WriteResult
    def history(self, kind: str, id: str, view: View) -> list[dict]
    def restore(self, kind: str, id: str, version: int, view: View, *, if_match: str, by: str) -> dict
    def hash_of(self, ref: str, view: View) -> str | None
    def events_since(self, seq: int, limit: int = 1000) -> list[dict]
    def legacy(self, lkind: str, key: str) -> str | None
    def apply_import(self, run: ImportRun, records: Iterable[dict], *, dry_run: bool) -> ImportReport
class PlanCtx(Protocol):   # view; read(kind,id); list(kind, **f); param(path, scope=None); file(uri) -> Path;
                           # need(job_type, scope_id) -> Ref; axis("year"|"month"|"timeline")
class RunCtx(Protocol):    # engine: EngineClient; progress(f, msg=""); cancelled() -> bool; upstream(ref) -> Output
@dataclass
class Output: meta: dict; arrays: dict[str, np.ndarray]; blobs: dict[str, bytes]; issues: list[dict]
class JobType(Protocol):   # name, version, scope, host, priority, timeout_s; plan(ctx, scope_id) -> Any; run(inputs, rt) -> Output
class Scheduler(Protocol): # submit(type, scope, view, priority=1) -> dict; result(type, scope, view) -> str | None
                           # watch_goal(type, scope, view, priority, ttl_s); cancel(job_id); jobs(active=True) -> list[dict]
class EngineClient(Protocol): # hello() -> dict; call(method, params, *, timeout_s=30.0) -> dict; close()
class Importer(Protocol):  # name, version, namespace, layer; sources(paths) -> dict[str, str]; records(src, ids: IdLookup) -> Iterable[dict]
class IdLookup(Protocol):  # id_for(lkind, key, *, kind, match: Callable[[list[dict]], str | None] | None = None) -> str
```

  Plus: the errors, the event TypedDicts (section 5), the feature folder convention, the kind meta-schema, SectionInput and VerticalRail v0, the NDJSON protocol, and the routes in section 5.
- **Exit tests.**
  - `tests/core/test_core.py`:
    - `test_view_instant_and_token`
    - `test_ids_stable_is_deterministic_sortable_ulid`
    - `test_write_atomic_survives_open_reader`
    - `test_write_guard_refuses_outside_roots`
    - `test_reserved_windows_names_rejected`
    - `test_tier_uri_resolves_and_missing_tier_reports`
    - `test_features_discover_folders`
    - `test_cli_lists_every_command`
  - `engine/test/contract.test.ts`: "schemas regenerate with no diff".
  - `uv lock --check` and `npm ci` are clean, and the existing suite passes with the known failure strict-xfailed.
  - 0b: `tests/ops/test_doctor.py::{test_doctor_passes_here, test_doctor_refuses_synced_var, test_doctor_reports_rtree_and_node}`, `tests/ops/test_tiers.py::test_tiers_report_present_partial_missing`, and CI green on Ubuntu and Windows.
- **Must not touch:** `region/model`, `region/api`, `region/jobs`, `region/enginehost`, `region/ext`, `engine/src` outside `contract/`, `app/src`.

### WP1. Store v2

- **Paths.**
  - `region/model/**`: rewrite `db.py`, `seed.py`, `__main__.py`; add the modules of section 3, `schema.sql` and `migrations/0002_store.{py,sql}`.
  - `region/kinds/{authority,waiver,feature,note}.yaml`, `region/cli/model.py`, `tests/model/**`.
  - Delete `tests/test_model.py`.
- **Depends on:** WP0.
- **Exposes.**
  - `open_store(path: Path, *, cache: Path | None = None, kinds_paths: list[Path] | None = None) -> SqliteStore`
  - `migrate(con, *, backup_dir: Path | None) -> list[int]`
  - `backup(db: Path, dest: Path, reason: str) -> Path`, `restore(src: Path, db: Path) -> None`
  - `seed.export(store, out: Path) -> dict`, `seed.import_seed(store, seed: Path) -> dict`
  - `kinds.load(paths) -> KindRegistry`, `legacy.IdLookupImpl`
- **Exit tests (in `tests/model/`).**
  - `test_migrate.py`:
    - `test_0002_applies_to_empty_and_0001_db`
    - `test_injected_failure_leaves_schema_unchanged`
    - `test_backup_checked_before_migrate`
    - `test_schema_snapshot_matches`
  - `test_store.py`:
    - `test_identical_write_is_noop` (no version, no event)
    - `test_missing_if_match_428_error`
    - `test_stale_if_match_412_error`
    - `test_json_patch_keeps_nulls`
    - `test_tombstone_keeps_data_hides_on_read`
    - `test_restore_is_new_version`
    - `test_history_rows_have_get_shape`
    - `test_rtree_follows_geom_including_none`
    - `test_raw_sql_cannot_skip_versions`
  - `test_layers.py`:
    - `test_scenario_shadows_main_and_copies_up`
    - `test_import_namespaces_disjoint`
    - `test_list_10k_resolves_under_200ms`
    - `test_promote_one_changeset_with_if_match`
    - `test_tag_reads_as_of`
    - `test_authority_legacy_refuses_main_allows_scenario`
  - `test_merge.py`:
    - `test_disjoint_field_rebase_is_listed_changeset`
    - `test_geometry_under_edit_becomes_proposal`
    - `test_overlap_conflict_keeps_ours`
    - `test_orphans_listed`
    - `test_merge3_laws` (hypothesis: merge(b,x,x)=x; merge(b,b,y)=y; no field changed on one side is lost)
  - `test_changesets.py`:
    - `test_one_invalid_op_writes_nothing`
    - `test_revert_after_later_edit_conflicts`
    - `test_event_in_same_transaction`
    - `test_bulk_changeset_summary_event`
  - `test_seed.py`:
    - `test_round_trip_byte_identical_two_dbs`
    - `test_crlf_input_reads_same`
    - `test_out_of_order_refs_one_transaction`
    - `test_failed_import_leaves_db_unchanged`
    - `test_bookkeeping_not_in_seed_or_hash`
    - `test_take_then_seed_only_change_no_conflict`
    - `test_only_main_and_proposals_seeded`
  - `test_imports.py`:
    - `test_dry_run_counts`
    - `test_rerun_writes_nothing`
    - `test_removal_is_import_tombstone`
    - `test_duplicate_ids_refused`
  - `test_legacy.py`:
    - `test_match_before_mint_keeps_id_on_rename`
    - `test_ledger_append_deterministic`
    - `test_legacy_both_ways`
  - `test_kinds.py`:
    - `test_every_kind_file_is_valid`
    - `test_upgraders_reach_current_version`
  - `test_backup.py`:
    - `test_backup_restore_round_trip`
    - `test_retention_tiers`
- **Must not touch:** `region/ground`, `region/rules.py`, `region/api`, `region/jobs`, `region/ext`.

### WP2. Server and events

- **Paths:** `region/api/**`, `region/cli/{serve,rec}.py`, `tests/api/**`.
- **Depends on:** WP0, using fakes in `tests/api/fakes.py` until WP1 and WP3 land.
- **Exposes.**
  - `create_app(store: Store, jobs: Scheduler, engine: EngineClient | None, cfg: dict) -> FastAPI`
  - `lock.acquire(var: Path, port: int) -> Lock`
  - the routes of section 5;
  - `region/api/openapi.json`.
- **Exit tests (in `tests/api/`).**
  - `test_records_api.py`:
    - `test_put_without_if_match_428`
    - `test_stale_412_body_current_by_diff`
    - `test_get_304`
    - `test_unknown_kind_404`
    - `test_patch_needs_json_patch_type`
    - `test_create_idempotency_key`
  - `test_changesets_api.py`:
    - `test_changeset_lists_every_conflict`
    - `test_revert_conflict_409`
  - `test_events_api.py`:
    - `test_sse_replays_from_last_event_id`
    - `test_resync_after_prune_or_new_epoch`
    - `test_out_of_process_write_reaches_sse_within_1s`
  - `test_security.py`:
    - `test_bad_host_400`
    - `test_write_without_client_header_403`
    - `test_foreign_origin_403`
    - `test_containment_fuzz_404`
    - `test_body_cap_413`
    - `test_csp_header`
  - `test_files.py`:
    - `test_range_206`
    - `test_etag_304`
    - `test_gzip_json_not_webp`
  - `test_serve.py`:
    - `test_refuses_missing_db`
    - `test_second_instance_names_first`
    - `test_health_within_2s`
    - `test_shutdown_truncates_wal`
    - `test_openapi_drift`
- **Must not touch:** `region/model`, `region/jobs`, `region/ext`, `app/`.

### WP3. Jobs and cache

- **Paths:** `region/jobs/**`, `region/cli/jobs.py`, `tests/jobs/**`.
- **Depends on:** WP0, using a fake store and a fake engine until WP1 and WP4 land.
- **Exposes.**
  - `Scheduler(store, cache_path: Path, engine: EngineClient | None, *, threads=4, processes=2)`, with `start()` and `stop()`.
  - `keys.key(type: str, version: str, code: str, refs: list[tuple[str, str]], axes: dict, engine_build: str | None, contracts: dict) -> str`
  - `cache.read_array(key: str, name: str) -> np.ndarray`
- **Exit tests (in `tests/jobs/`).**
  - `test_keys.py`:
    - `test_key_stable_across_dbs`
    - `test_key_ignores_bookkeeping`
    - `test_axes_only_when_declared`
  - `test_scheduler.py`:
    - `test_edit_invalidates_exact_dependants`
    - `test_early_cutoff`
    - `test_coalesce_burst`
    - `test_supersede_cancels`
    - `test_priority_order`
    - `test_failure_does_not_stop_scheduler`
    - `test_timeout_kills_process_job`
    - `test_lease_expiry_requeues`
    - `test_jobs_cannot_write_inputs`
    - `test_moved_inputs_mark_stale_and_requeue`
  - `test_cache.py`:
    - `test_equal_scenario_content_shares_result`
    - `test_undo_is_hit`
    - `test_lru_spares_pinned`
    - `test_cache_db_wipe_recomputes`
- **Must not touch:** `region/model`, `region/api`, `region/ext`.

### WP4. Engine and engine host

- **Paths:**
  - `engine/**`, except the WP0 files (`src/contract`, `schema`, `package.json`, `tsconfig.json`);
  - `region/enginehost/**`, `region/contract/gen/**`, `tests/enginehost/**`.
- **Depends on:** WP0.
- **Exposes.**
  - The method `vertical.rail@1`.
  - `METHODS`, `ENGINE_VERSION` and `solve(method, input)` from `engine/src/index.ts`.
  - `node engine/src/sidecar.ts` and `node engine/src/cli.ts <method> <input.json>`.
  - `Pool(size=2, timeout_s=30)`, `OneShot()`, `Fake(responses)` and `engine_build() -> str`.
- **Exit tests.**
  - vitest:
    - "41 of 41 routes rail every 5 m within 1 mm"
    - "pathAt by bisect equals linear scan"
    - "same bytes across runs and PVI permutations"
    - "no Date, Math.random or performance in src; no numeric literal outside tol.ts"
    - "RuleId matches registry"
    - "hello then echo over NDJSON"
    - "Line 6 under 20 ms" (bench)
  - `tests/enginehost/test_client.py`:
    - `test_pool_matches_golden_bytes`
    - `test_warm_round_trip_under_5ms`
    - `test_killed_worker_respawns_job_fails_cleanly`
    - `test_timeout_kills_and_respawns`
    - `test_contract_major_mismatch_refused`
    - `test_oneshot_equals_pool`
    - `test_build_hash_matches_hello`
    - `test_no_node_raises_engine_unavailable`
- **Must not touch:** `app/`, `region/jobs`, `region/ext`.

### WP5. Metro import and the profiles feature

- **Paths:** `region/ext/{network,stations,profiles,rules,legacy}/**`, `region/cli/{imports,rebuild}.py`, `region/ids/*.tsv`, `tests/importers/**`, `tests/profiles/**`.
- **Depends on:** WP0.
  - The importers are pure and are tested first, with no store.
  - WP1 is needed for integration.
  - WP3 and WP4 are needed for the solve. The joint test lands last.
- **Exposes.**
  - Importers:
    - `profile_lines@1` (`import:profiles`: 16 Metro routes, sections, nodes, stations, stops, platforms, `ground_profile`, empty profiles);
    - `registry@1` (`import:registry`: 137 rules, 163 params);
    - `old_hub@1` (`legacy:old_hub`: 13 Metro docs as profile revisions, 24 roadmap items, the camera; `--hub-db PATH` read through a backup snapshot).
  - Job types `profiles.solve_section@1` and `profiles.golden_diff@1`.
  - `inputs.section_input(ctx: PlanCtx, section_id: str) -> dict`.
  - The two `/x/profiles` routes.
- **Exit tests.**
  - `tests/importers/test_profile_lines.py`:
    - `test_16_metro_routes_import`
    - `test_lines_10_11_13_flagged_no_doc`
    - `test_rerun_writes_nothing`
    - `test_two_fresh_dbs_identical_ids`
    - `test_legacy_keys_both_ways`
  - `test_old_hub.py`:
    - `test_13_docs_round_trip_value_for_value` (excluding `stations`, `summary`, `updated`)
    - `test_hub_db_read_via_snapshot`
    - `test_seed_field_change_updates_one_record`
    - `test_authority_defaults_legacy`
  - `test_registry_import.py`:
    - `test_rules_and_params_import`
    - `test_override_divergence_listed`
  - `tests/profiles/test_solve.py`:
    - `test_golden_diff_zero_unexplained` (12 exact; Line_2b, 10, 11 and 13 classed `pending_port:reframeDoc|defaultAlign`)
    - `test_record_inputs_equal_engine_fixtures`
    - `test_seed_doc_direct_golden`
  - `test_router.py::test_doc_export_equals_seed_doc`
  - `test_rebuild.py::test_rebuild_leaves_git_clean_and_byte_identical`
- **Must not touch:** `region/model`, `region/api`, `region/jobs`, `engine/`, `app/`, `hub/`.

### WP6. App

- **Paths:** `app/**`, except `app/package.json` and `app/tsconfig.json`.
- **Depends on:** WP0.
  - Until WP2 lands it uses MSW mocks of section 5. The drift test turns on when `openapi.json` lands.
  - It takes the WP4 source through the workspace.
- **Exposes:** `Plugin`, `PaneDef`, `LayerDef`, `BandDef`, `CommandDef`, `Host` (section 8), and the URL codec.
- **Exit tests.**
  - vitest:
    - "URL round trips and accepts legacy aliases"
    - "duplicate ids fail"
    - "SSE client replays and resyncs"
    - "undo reverts; 412 offers keep or take"
    - "If-Match sent and 304 used"
  - Playwright, against `python -m region serve --db <fixture>`:
    - "map draws 16 Metro sections offline, no glyph 404"
    - "Line 6 sheet shows ground and rail"
    - "PVI level edit re-solves locally under 16 ms and saves version 2"
    - "second context updates within 1 s"
    - "Ctrl+Z gives version 3 equal to version 1"
    - "stale tab gets 412 banner"
    - "server restart triggers resync"
    - "fixture plugin adds a tab"
    - "browser rail bytes equal Node's on Line 6"
    - "no console errors"
  - The first chunk is under 400 KB gzipped.
- **Must not touch:** `region/`, `engine/`.

## 11. After this increment, in order

1. **Close the loop** (2.1.1, 2.1.6, 2.1.8). The gate of slice 1 is: edit a Line 6 PVI, and see the run time change within 10 s, with Line 6 within 1 % of `runtimes.json`.
   - `ground.profile` from `region.ground`. The line-file ground stays as a declared fallback through param `ground.source`.
   - The railsim adapter over `TrackData`: `route.assemble`, `railsim.run` and `railsim.attribution`.
   - The run-time band and table.
   - Drag handles.
   - The review pane made writable.
2. **Engine ports** (2.1.2, 2.1.3, 2.1.5, 2.1.13, 2.1.17).
   - `reframeDoc` and `defaultAlign` (golden b).
   - The level solver rewritten.
   - The structure solver from the registry, with rule ids.
   - All quantities as arrays; flags as data.
   - Exit: zero unexplained differences on the 16 Metro routes.
3. **Chronology** (2.1.4). Import the 556 segments with partial dates (the 54 TRI placeholders flagged), eras, operations, rolling stock and services.
4. **Metro truth moves to the model** (2.1.9 to 2.1.12, 2.1.14 to 2.1.16).
   - Invariant tests per rule.
   - The Deck platform adapter.
   - Metro alignment authority flipped to model.
   - `metro_profile.py` deleted, and railsim configs generated.
   - Line works as corridors.
   - The horizontal fit, the proposer, and quantities.
   - The Profiles page retired for Metro.
5. **Slice 0, as lane B lands its parts.**
   - The 1912 base swap as a record edit (2.0.5).
   - Bridges and the C&O viaduct as records, with the viaduct fix (2.0.12, 2.0.13).
   - Corridor and region tiers (2.0.14).
   - The STATUS board and skills (2.0.16).
6. **Slice 2** (2.2.x). The same importers over `data/profile/rer`; seams as nodes; shared trunks with one level.
7. **Slice 3** (2.3.x).
   - PMTiles and the era slider.
   - The Deck base as `import:deck` runs with versioned base sets, and an orphan queue.
   - terra-draw editing; plot ops with fractional order; sidewalks; lots with heights.
   - Structures, issues and tables.
8. **Slices 4 to 7.**
   - Capacity jobs.
   - Fountain Square stacked, spread and half-stacked as scenarios with station flows.
   - Demand on DuckDB.
   - Exporters and budgets.
   - The old hub retired.

### For Ben to rule

- Chainage basis (9.14).
- Merging `hub_region` into `main` after increment 1 (9.24).
- Installing uv (9.21).
- `var` under `%LOCALAPPDATA%` (9.22).
- Port 8766.
