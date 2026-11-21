# Old hub: server, store, pipeline, seeds (map for the new hub)

Read only. Files: `hub/hub.py` (319 lines), `hub/store.py` (278), `hub/pipeline.py` (401), `hub/README.md` (58), `hub/test_hub.js` (65), `hub/static/{shim.js 100, events_worker.js 18, home.html 19,956 B, chronology_rules.js 10,857 B, vendor/ three 608 KB, jsts 500 KB, OrbitControls, GLTFExporter}`. The last code commit to them was f678889 (4 Nov). The last seed commit was 708099b "Full hub export" (5 Nov).

## 1. Server (`hub/hub.py`)

`ThreadingHTTPServer` on 127.0.0.1:8765 (l.306). CLI: `serve|export`, `--port`, `--db` (default `hub/hub.db`, gitignored), `--no-auto`, `--no-browser` (l.289-315).

**Startup** (`Hub.__init__` l.107-133), in order:
1. `store.merge_dir(hub/seed, git_versions=git_seed_versions)`. Git versions come from `git log -n 40` plus `git show` per seed file (l.59-72).
2. `params/metro_structure`: written from `data/profile/metro_structure.json` if missing. Otherwise `fill_missing` adds keys new to the default, recursively, and keeps Ben's values (l.47-56, 114-119).
3. `chronology/segments` and `params/station_types` are written from `data/profile/chronology.json` and `station_types.json` if missing.
4. A seed report is printed and logged as a `seed` run. Conflicting seed files are copied to `hub/work/seed_conflicts/` (l.84-103).
5. If `deck/layout` changed, `deck_tie` is scheduled. Otherwise, if a changed path has a trigger, `3d` is scheduled. On first start, `3d` is scheduled if `snapshots/region` is missing.

**API surface** (l.171-285):

| Method, path | Does | Returns |
|---|---|---|
| GET `/api/doc?p=` | `store.get` | `{path,data,version,updated(epoch s),by}` or `null` |
| GET `/api/coll?c=` | every record whose `coll` equals c (exact parent), ordered by path | list of the same |
| GET `/api/history?p=` | metadata only | `[{version,updated,by}]` |
| GET `/api/runs` | last 20 runs, log tail 4,000 chars | `{runs,current,pending}` |
| GET `/api/events` | SSE (below) | |
| PUT `/api/doc?p=` | `set`; `If-Match: <int>` optional (`*` or empty means none); `X-By` header, default `page` | 200 `{version}` / 409 `{error:'conflict',version,by}` |
| PATCH `/api/doc?p=` | `update`: shallow key merge, `{"__delete__":true}` removes a key; **no If-Match** | `{version}` |
| DELETE `/api/doc?p=` | **no If-Match** | 204 |
| POST `/api/run?job=` | only `platform_tie|deck_tie|3d`, delay 0 | `{scheduled}` |
| POST `/api/restore?p=&v=` | history version re-`set` by `hub`, no If-Match | `{version}` |
| POST `/api/export` | `export_dir` + `export_derived` + `write_timeline` | `{records,files}` |

A missing `p`, `c` or `job` raises `KeyError` inside the handler. No JSON error is sent; the connection drops.

**Static serving** (l.185-217):
- `/` serves `static/home.html`. `/hub/<x>` serves `hub/static/<x>`.
- `SITES` (l.29-35): `/deck/` serves `hub/sites/deck`, `/profiles/` serves the whole `data/profile` folder (6.3 MB, 17 entries), `/3d/` serves `tools/station3d/page`, and `/chronology/` and `/access/` serve `hub/sites/*`.
- A file under `hub/work/derived/<site>/<rel>` is served in place of the site's copy (today only `deck/viaducts.json`).
- On the page HTML, four CDN URLs are rewritten to `/hub/vendor/*` (l.37-42) and `<script src="/hub/shim.js">` is injected after `<head>`.
- Every response: `open(f,'rb').read()` whole, `Cache-Control: no-store`, no ETag, Range or gzip.
- Containment is `abspath(f).startswith(ROOT)` (l.204-206). It is a prefix test against the repo root, not the site folder, so `/hub/../hub.db` and `/deck/../../.git/config` pass for a raw (non-normalising) client.

## 2. Store (`hub/store.py`)

One SQLite file, WAL, one connection shared across threads under an `RLock`, commit per write (l.20-36). Tables:
- `docs(path PK, coll, data TEXT json, version int, updated real, by)`, index on `coll`
- `history(path, version, data, updated, by, PK(path,version))`
- `seed_base(path PK, data)`
- `runs(id autoinc, job, state running|ok|failed, started, finished, reason, log)`. The log is appended (`log || ?`) and never pruned.

Behaviours:
- **`set`** (l.53-71) serialises compactly.
  - If `if_version` is given and the current version (0 if absent) differs, it returns `None` and the server answers 409.
  - Identical text is a no-op: no version bump, no event.
  - Otherwise version+1. The old row goes to history, except paths under `snapshots/`, which keep none (`NO_HISTORY`). History is pruned to the last `HISTORY_KEEP=50`.
  - It emits `{'t':'doc','p','v','by'}` unless `quiet`.
- **`update`** reads and writes under one lock (l.73-83). `delete` keeps the last version in history and emits `v:null`.
- **`merge_dir`** (l.173-258) is a three-way merge per record against a base.
  - Base: `seed_base`, else the local copy if `by=='seed'`, else the record's `by='seed'` history, else a git version of the seed file that matches local or history.
  - Missing here: added. Unchanged here: replaced. Seed unchanged: kept.
  - No base: kept, conflict noted once, and the seed becomes the base.
  - `alignments/*` changed on both sides: kept whole as a conflict (1 Nov ruling).
  - Others changed on both sides: merged key by key two levels deep (top key, then entry id, e.g. `streets.SB0089`). An entry changed differently on both sides keeps local and is a conflict. A list (e.g. `plotOps`) is atomic.
  - A seed file that cannot be read (git conflict markers) is skipped with a conflict note.
- **`export_dir`** (l.260-278) writes every non-`snapshots/` record to `<root>/<path>.json` (indent 1, UTF-8), sets `seed_base`, and **deletes every other `.json` under hub/seed**.
- Record paths are never validated. `export_dir` and the conflict copy build `os.path.join(root, *p.split('/'))`, so a path such as `../../x` escapes `hub/seed`.

## 3. Events and shim

**SSE** (`hub.py` l.219-241):
- Each subscriber gets an unbounded `queue.Queue` and holds one server thread forever.
- Frames are `data: <json>`. `: hello` on open, `: ping` every 20 s.
- No `id:`, no `Last-Event-ID`, no replay.
- Event types: `doc{p,v,by}` (store), `run{id,job,state}` (store run_start/run_end), `files{site}` (pipeline, for `profiles`, `chronology`, `deck`).

**`events_worker.js`**: one `SharedWorker` keeps one `EventSource` and relays `{kind:'open'|'msg'|'error'}` to every tab (the 29 Oct six-connection fix). A port is removed on a `'bye'` sent from `pagehide`.

**`shim.js`** (window.claude stand-in):
- Surface: `claude.use('db'|'user'|'downloads')`.
  - `db.doc(p)` gives `{get,set(data,{ifVersion,force}),update,delete,onSnapshot,version}`.
  - `db.collection(c)` gives `{doc(id),get,onSnapshot}`. **There is no `add`.**
  - `user` returns `{id:'local', me:{id,name:'Ben'}, can:true, canEdit:true}`.
  - `downloads.save` uses a Blob anchor.
- The doc snapshot is Firestore-like: `{id,ref,exists,version,data(),metadata}`.
- `set` sends `If-Match` = `opts.ifVersion`, else `VER.get(p)`. `VER` is the version the shim last *fetched*, not the one the page applied. A missing doc has no VER, so its first write is blind.
- On a 409 it refetches and throws `{code:'conflict',version,by}`.
- On every `doc` event, `fireDoc` re-GETs the whole record for doc listeners, and `fireColl` re-GETs the **whole collection** for collection listeners.
- `run` events drive the bottom bar ("updating", "failed"). A `files` event for the current site shows "New data: reload" unless the page sends `hub-files-handled`. Every event is re-dispatched as a window `hub-event`.
- On reconnect, `onOpen` only redraws the bar; there is no resync.
- The shim never sends `X-By`, so every page write is `by='page'`.

## 4. What the pages call (record paths)

| Page | Subscribes / reads | Writes | Files fetched |
|---|---|---|---|
| Deck `hub/sites/deck/index.html` (365 KB; 2817-2840, 2486-2521) | `deck/layout` (snapshot ignored while dirty, saving or dragging); `params/{metro_structure,station_types,station_platform_default,tube_points}` | `deck/layout` whole document (about 325 KB) with `{ifVersion:S.docVer}`, 800 ms debounce. On a conflict: `mergeEdits(base,mine,theirs)` per entry and per platform `s.<pid>`, then saves again | deck.json, basin.json (2.35 MB), plots.json (3.3 MB), context, tracks, structures, hwy, norwood, airport, yard, sheets, relief.*, viaducts, tiles12/_22/_b/_n index and overview |
| Profiles `data/profile/profiles.html` (352 KB; 3250-3300, 415, 3235) | `alignments` (collection), `config/settings`, `config/settings_rer`, `params/{metro_structure,station_platforms,approach_extra,station_complexes,station_access}`, `chronology/segments`; `hub-event files/profiles` → `refetchRoutes` | `alignments/<id>` with ifVersion, including linked routes via `propagateLinks`; a conflict shows the "Keep mine / Take theirs" banner. `config/settings*` and `params/station_access` without ifVersion | lines/index.json, rer/lines/*, rer/network.json, rer/metro_rails.json, rer/links.json, context/lines.json |
| Station 3D `tools/station3d/page/index.html` (1125-1175, 800-826) | `snapshots/region`, then each `snapshots/region/parts/<p>` by GET; `views` (collection); `data/users/local/camera_region` | camera via `collection('data/users/'+me).doc('camera_region').set`; `views` via `collection('views').add(...)`, **which fails under the shim** (no `add`), so no views exist in the seed; delete `views/<id>` | snapshot.json fallback |
| Chronology `hub/sites/chronology/index.html` (225, 299-308) | `chronology/segments` | whole record `set`, page undo of 100 | `/profiles/chronology_lines.json`, `/profiles/chronology.json` (Reset) |
| Access `hub/sites/access/index.html` (59, 112-116) | `params/station_access_rule`, `params/station_access` | `params/station_access` | |
| Home `hub/static/home.html` (76-171) | `deck/layout`, `alignments`, `snapshots/region`, `params/registry`, `params/metro_structure`, `roadmap` (collection); polls `/api/runs` every 15 s | `params/metro_structure` set (while `msDirty` the snapshot is ignored, so the shim's VER makes the save effectively blind); `roadmap/<id>` via PATCH update, set, delete; `/api/run`, `/api/export` | |

`hub/test_hub.js` (Playwright, hub running):
1. Profiles loads `alignments/Line_8`.
2. A PUT with `X-By:test` reaches the open Profiles live.
3. A Chronology phase change reaches the Profiles' `phaseAt`.
4. The Deck shows "Saved".
5. 3D shows `syncedAt`.
6. No page errors.

`tests/test_hub.py` has 9 tests (store versions, history and events; seed round trip; triggers; merge of a pulled seed; unreadable seed; profile kept whole; chronology months; platform tie trigger; profile frame).

## 5. Pipeline (`hub/pipeline.py`)

**Triggers** (`trigger_for` l.56-63):

| Path | Job |
|---|---|
| `deck/layout` | `deck_tie` |
| `alignments/*` | `platform_tie` |
| `config/*`, `params/metro_structure`, `chronology/segments` | `3d` |

Events with `by` in `pipeline|test` are ignored (l.77).

**Scheduling** (l.83-109):
- One daemon worker. `pending[job]=(due,reason)`, debounce 4 s, and a burst extends the due time (max).
- Order: `platform_tie`, then `deck_tie`, else the earliest due.
- A successful `deck_tie` schedules `3d` at once.
- Runs are recorded in `runs`. A failure is logged and does not stop the hub.
- Subprocesses have no timeout (`sh` l.125-133).

**`prepare()`** (l.135-173), every run:
- Lays out `hub/work/` as the sync cache. It symlinks, or on Windows without Developer Mode **copies**, `hub/sites/deck` (16 MB) and each `data/profile` entry.
- Dumps `alignments` and `config` to `db/profiles_db/`, `deck` to `db/deck_db/`, and `params` and `chronology` (including the 2 MB tube_points) to `db/params_db/`.
- Writes `db/versions.json`, the versions the job started from.

**Jobs:**

- **`platform_tie`** (l.175-209)
  - Inputs: `deck/layout`, `alignments/*`, `params/platform_sync`, and `hub/work/rer_routes.geojson`. The geojson is re-exported via the harness if it is older than the layout or has no `"pid"` in its first 200 KB.
  - Runs `tools/platform_tie.py --docs --layout --times --sync --out`, which returns `{layout, moves[{done,conflict,route,station,why}]}`.
  - Writes `deck/layout` by `pipeline` with If-Match, then `deck_tie`; otherwise `3d`.
- **`deck_tie`** (l.217-264)
  1. `node tools/station3d/harness.js WORK deck_job.json deck_out.json` (Chromium boots the Deck). The six `DECK_LAYERS` go to `hub/work/rer_routes.geojson`.
  2. `tools/rer_deck_routes.py --db --sync` (exit 0 means in step); then `--apply`. This **writes git-tracked** `data/profile/rer/lines/*`, `lines/index.json`, `rer/network.json`, `network.json`, `rer/canon.json`, `rer/links.json`.
  3. Changed alignments are written back against the start versions; a profile saved meanwhile is kept and the tie is re-queued.
  4. `make_rer_profile_lines.metro_rails()` writes `data/profile/rer/metro_rails.json`.
  5. `make_profile_context.py` writes `data/profile/context/lines.json`.
  6. `chronology.py` writes `data/profile/chronology_lines.json` (and `chronology.json` if absent).
  7. Emits `files` events for profiles and chronology.
  8. `platform_tie.py --snapshot` writes `params/platform_sync` (quiet).
- **`3d`** (l.266-327)
  1. `tools/station3d/sync.py --cache WORK --out WORK/snapshot.json` writes `db_out/meta.json` plus parts. Parts are chunks of ≤200 KB from `lines, tracks, unlevelled, stations, platforms, streets, blocks, context, gtiles`, plus `ground-0`, each `{json:"<stringified {key,items|value}>", synced_at}` (sync.py l.495-532).
  2. The parts go to `snapshots/region/parts/<key>-<n>` (quiet) and stale parts are deleted. Then `snapshots/region` `{json,parts,synced_at}` is written (event). It was 39 parts, 7.5 MB in the 31 Oct audit.
  3. `params/registry`: `registry()` regex-parses `METRO_DEFAULTS` and `RER_DEFAULTS` out of profiles.html and measures Deck platform lengths from the geojson.
  4. `tools/viaduct_parts.py harness_out.json` writes `hub/work/derived/deck/viaducts.json`, then a `files` deck event.
  5. `params/station_platforms`, `params/approach_extra`.
  6. `tools/station_access_report.py --out` writes `params/station_access_rule`. It reads `hub/seed/alignments` by default, not the live records.
  7. `params/station_complexes {auto, marked}`, `params/tube_points`, `params/station_platform_default`, `params/station_types`. A change to the types or defaults re-runs `3d` once (the `_types_rerun` guard).
- **Run times:** about 143 s for `3d` (Plan l.49, Station_3D_Log l.148; README "about two minutes"). No measured times for `deck_tie` or `platform_tie` were found in the repo. The deck export is 22-27 MB (Code_Scrutiny l.81).
- **Export** (`export_derived` l.38-50):
  - copies `rer_routes.geojson` to `data/deck/`
  - copies `viaducts.json` to `hub/sites/deck/`
  - writes three params records to `data/profile/{station_platforms,station_complexes,approach_extra}.json` (`open(dst,'w')` with no encoding: a latent Windows cp1252 risk; no non-cp1252 characters are in the seed today)
  - `write_timeline` runs `node tools/chronology_timeline.js`, which writes `data/profile/chronology_timeline.md`.

## 6. Seed (`hub/seed/`, 3.3 MB, 81 files; path = record path + `.json`)

| Collection / kind | Files | Size | Shape |
|---|---|---|---|
| `alignments/<RouteId>` | 43 (13 Metro: `Line_1..9,12,14,2b`, `CVG_Express`; 30 RER: `RER_A..E_<branch\|trunk>`; Line_10, 11 and 13 have none) | 173 KB | `v`(1), `system`, `line`, `length_m`, `platform_m`, `st{name:rail z}`, `pvi[[c,z]]`, `ovr[[c0,c1,type]]`, `sg{name:‰}`, `so{name:m}`, `gapfill[]`, `del[name]`, `stations[{name,c,point_c,rail,ground,depth,type}]`, `summary{km_by_type,max_grade_permille,grades_over_limit}`, `updated` ISO; optional `mode{name:surface\|under}` (30), `route_chainage_m` (30), `ready` (12, all false), `tf[[c0,c1,'twin']]` (9), `reframed` (8), `gnd[[[c,z]]]` (7), `stt{name:type}` (6), `shafts` (1) |
| `deck/layout` | 1 | 325 KB | the edit layer over base `deck.json` (`layout:'deck.json'`, `updated`). `streets` 324: `c` coords UTM16N, `k`, `w`, `wv[]`, `jo{i:m}`, `n`, `note`, `del`, `into`, `mg{ids,pre}`; 120 deleted, 196 with geometry. `blocks` 56: `lk` date, `t`, `u`, `n`. `transit` 14: `c`, `k`. `stations` 100: `s{pid:{o,t}}`, `del`, `complex`. `plots` 163: `u`. `plotOps` 266: `t` s 129 / m 120 / f 13 / d 4, with `id`, `ids`, `l`, `q`, `n`, `a`, `to` |
| `chronology/segments` | 1 | 72 KB | `segments` 556 `{year,src,month?,note?,phase?,services?}`, `stations` 2, `phase_years` `[[1800,1933,'1'],[1934,1949,'2'],[1950,1979,'3'],[1980,2200,'later']]`, `core` (5 lines, no longer read), `notes`, `about` |
| `params/*` | 11 | 2.55 MB | `metro_structure` (9 KB, 28 keys: car, envelope, tubes A/C/bore, box, island_box, phases, line_phase, piece_phase, grades, hall, cost, …); `station_access` (Ben's choices `{line:{st:{type,source}}}`, 10 entries); `platform_sync` (36 KB, `offsets` 532, `slides` 13 routes); derived ones: `registry` (25 rows, 9 tie_issues, 10 checks), `station_access_rule` (277 KB, 430 stations × 18 fields), `station_complexes` (133 KB, `auto` 435 `{id,name,x,y,members[{sys,line,station,c,x,y}]}`, `marked` 1), `station_types` / `station_platforms` (436 each), `station_platform_default` (408), `tube_points` (**2.05 MB**, 16 lines, 508-3,613 points `[E,N,tube,half]`), `approach_extra` |
| `roadmap/<id>` | 24 | 7 KB | `{phase,status todo\|doing\|done,title,detail,order}`; 22 todo, 2 done |
| `data/users/local/camera_region` | 1 | 152 B | `{pos[3],target[3],exag,station}` |

Not in the seed: `config/settings` and `config/settings_rer` (never committed, so they exist only in Ben's DB if he saved settings), `views/*`, and `snapshots/*` (excluded by design). `data/profile/alignments/` holds a third, older copy (8 files; Line_8 differs from the seed). The README's "Deck layout version 2463, 38 saved profiles" is stale.

**Ids and keys:**
- Route ids: `Line_8`, `RER_A_trunk`.
- Profiles station keys: the name, or `name#n` for a repeat (2 in the seed: `Cincinnati State#2`, `#3`).
- Deck station keys: `sys:Name:E:N` (86 metro, 10 rer, 4 cvx; carry typos such as `metro:Syacmore:…`).
- Deck pieces: `M-L<n>-E-N` and `R-<letter>-E-N`, plus `CVX` (27 distinct pids).
- Platform keys: `<stationKey>|<pid>`.
- Chronology keys: `metro|Line_x|A|B` (415), `tri|A|B` (136), `cvx|A|B` (5); stations `sys|Name`.
- Complexes: `name:x:y` and `marked:<slug>`.
- Streets: `S###`, `SB####`, `SM####`, `SMV####`, `SE`, `SN`, `SO`, `SV`. Blocks: `B###`, `SBB####`, `FB###`. Plots: `SBB0843-103`, `.1`, `~a`.
- Roadmap: `r00..r23`, new ones `i<base36 ms>`.
- `metro_structure.line_phase` and `piece_phase` are keyed by line id and Deck piece name.

## 7. Import into region/model

`region/model` 0001_init.sql has `legacy_key(legacy, kind, tbl, id, note, PK(kind,legacy))` and `seed.py` (three-way merge, `region/seed_conflicts/`).

Truth to import, by legacy key:
- `alignments/*` → route, section and stop data (`st/pvi/sg/so/ovr/tf/gnd/del/mode/ready/shafts`). Kinds: `route`, `profile_station` (`Route|name#n`).
- `deck/layout`. Kinds: `deck_station`, `deck_piece`, `deck_platform`, `street`, `block`, `plot`. The edit layer must stay separate from base `deck.json`.
- `chronology/segments` → section and station `year_open`/phase, with month and note in `data`. Kinds: `chron_segment`, `chron_station`. `phase_years` → `era`.
- `params/metro_structure` → era, rule and params.
- `params/station_access` → station_element or a ruling.
- `station_complexes.marked` → station.
- `config/settings*`, only from Ben's DB.
- `roadmap/*`, `views/*`, camera.
- `platform_sync` is a sync baseline that is only needed while there are two platform key schemes.

Derived (regenerate, do not import as truth): `registry`, `station_access_rule`, `station_platforms`, `station_platform_default`, `station_types`, `tube_points`, `approach_extra`, `station_complexes.auto`, `snapshots/*`.

Not found in 0001_init.sql: tables for roadmap items, saved views and cameras, job runs, or a generic document store for UI state.

Ben's DB is the authority for anything newer than 708099b. The import must read his `hub.db` (or a fresh `hub.py export`), not only git.

## What the new hub must support from this part

- One record API with a version on every record. Every write (PUT, PATCH, DELETE, restore) carries If-Match and gets a 409 with `{version, by}`. Writes record `by` (page, pipeline, seed, test). Identical writes are no-ops.
- Bounded, browsable history with restore, and a diff, not metadata only. Derived records keep no history.
- A seed in git, one file per record, with a three-way merge on start against `seed_base`, git-version fallback bases, a conflicts folder and a report. Profiles and other "one design" records are kept whole; layout-like records merge per entry. Records are finer-grained (one per street, block, station or platform) so the merge happens per record.
- **Never delete or overwrite pulled seed files on export without merging first.** The old CLI `export` (l.297-304) does not run `merge_dir`, so an export after `git pull` without starting the hub reverts the session's changes and deletes new files.
- Path and id validation: records addressed by id, never a raw path into the filesystem. Static serving contained per folder by real-path comparison.
- One SSE stream per browser through a SharedWorker (keep), with event ids and replay (`Last-Event-ID`) and a resync on reconnect. Events carry `{kind,id,version,by,changed sections}` so clients patch rather than refetch whole collections or all 39 parts.
- Static and derived assets with ETag, Range, gzip and long cache for vendor files and tiles. Streamed, not read whole. The 2 MB tube_points and 7.5 MB snapshot become chunked binary or per-section GLB.
- Job runs as first-class records (job, state, reason, inputs, timing, log), pruned, with progress over SSE. Debounce and coalescing; a dependency order (platform tie → deck tie → 3D); writes only against the start versions, with a re-run when Ben saved meanwhile; outputs in one transaction; no writes to git-tracked files except on explicit export; subprocess timeouts.
- An adapter (strangler) so the old five pages keep running until replaced: the `window.claude` surface (`doc`, `collection` with **`add`**, `onSnapshot`, `version`, `ifVersion`, `user`, `downloads`), the CDN rewrite, `hub-event` and `hub-files-handled`, and the bottom bar.
- The legacy-key kinds listed in section 6, populated at import and resolvable both ways. That includes the coordinate-bearing Deck keys and the `name#n` profile keys.
- Records for what the old hub kept that has no table yet: roadmap items, saved views and cameras per user, UI settings (`config/settings*`), and Ben's access choices and complex marks. The defaults-on-start behaviour (`fill_missing` on metro_structure) becomes versioned migrations.
- Windows-safe I/O: explicit UTF-8, no symlink dependence, no 16 MB copy per run.
- Base and edits kept apart for the Deck: `deck/layout` is an edit layer over base `deck.json`. Its fields (`streets c,k,w,wv,jo,n,note,del,into,mg`; `blocks lk,t,u,n`; `transit c,k`; `stations s.{pid}.{o,t},del,complex`; `plots u`; `plotOps t,id,ids,l,q,n,a,to`) must survive import unchanged.
