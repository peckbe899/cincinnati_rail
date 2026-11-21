# Notes from wave 1 of increment 1 (21 Nov): what the store, engine, jobs, app and ops packages tell the server, the importers and integration

Collected from each package's build and review reports. The reports themselves are summarised in the commit message of 9732648.


## WP1 store, build report

### Public interfaces as built
```
region.model.open_store(path, *, cache=None, kinds_paths=None, validators=None, backup_dir=None, create=True) -> SqliteStore
region.model.migrate.migrate(con, *, backup_dir=None, folder=None, target=None) -> list[int]
region.model.backup.backup(db, dest, reason) -> Path
region.model.backup.restore(src, db, *, backup_dir=None) -> None
region.model.backup.{prune(dest), auto(db, dest, *, now=None), quick_check(path|con)}
region.model.seed.export(store, out=region/seed) -> dict
region.model.seed.import_seed(store, seed=region/seed, *, layer=None, by="seed") -> dict
region.model.kinds.load(paths=None) -> KindRegistry
region.model.legacy.IdLookupImpl(store, *, layer, namespace, ledger_dir=None)
    .id_for(lkind, key, *, kind, match=None) -> str
    .flush()
```

`SqliteStore` implements `region.core.protocols.Store` (an `isinstance` test passes):
- **Protocol methods:** `get`, `list`, `write`, `put`, `patch`, `delete`, `revert`, `history`, `restore`, `hash_of`, `events_since`, `legacy`, `apply_import`.
- **Extra keyword arguments:**
  - `get(..., at=, tag=)` and `list(..., tag=)`;
  - `apply_import(..., ids=IdLookupImpl)`;
  - `put`, `patch`, `delete`, `restore` and `revert` also take `client=` (and `message=`).
- **Extra methods:**
  - layers: `layers()`, `layer(slug)`, `chain(view)`, `create_layer(...)`, `promote(slug, *, by, message, client)`, `set_layer_state`, `tag(slug, name, *, by, note)`, `tags`, `diff_layers(slug, against=None)`
  - changesets: `changesets(by, since, layer, kind, limit)`, `changeset(id)` (includes the records it wrote)
  - conflicts and rebase: `conflicts(state, layer, import_run)`, `resolve_conflict(id, take, body, *, by)`, `rebase(lower=None)`, `flip_authority(kind, *, by, ruling)`
  - refs and legacy: `refs_to(id, view)`, `legacy_keys(id)`, `legacy_record(lkind, key)`, `add_legacy(...)`, `id_lookup(...)`
  - imports: `import_run(id)`, `layer_records(layer, kind)`
  - outbox and database: `last_seq()`, `min_seq()`, `data_version()`, `meta()`, `subscribe(fn) -> unsubscribe`, `checkpoint()`, `quick_check()`, `check_data()`, `backup(reason, dest)`, `diff(kind, id, view, from_version, to_version)`, `close()` (also a context manager)

CLI: `crhub model migrate|export|import|backup|restore|check|info|kinds|schema`. `python -m region.model <action>` runs the same actions.

### What WP2 must know
- **Readers and writer:** the store is thread-safe, with one reader connection per thread and one shared writer thread per DB file. Serve should use `open_store(db, create=False, cache=...)`. Migration backs up to `<db folder>/backups` before running.
- **Errors** are `region.core.errors`. A 412 carries `current`, `by`, `diff` and `stale`.
- **SSE:** `subscribe(fn)` is called with the seq after each in-process commit. `data_version()` changes after commits by other processes. `events_since` returns events whose `data` includes `seq`. Use `min_seq()` to detect pruning. `meta()["epoch"]` changes on restore.
- **Route mapping:**
  - `/k/{kind}` ETag: `last_seq()`; `format=geojson`: `geom.to_geojson(wkt)` gives EPSG:26916 coordinates, and the 4326 reprojection is yours
  - `/history` and `/diff`: `history()` and `diff()`; `/refs/{id}`: `refs_to()`; `/legacy/{lkind}/{key}`: `legacy_record()`
  - `/changesets`: `write`, `changesets`, `revert`
  - `/layers`: `create_layer`, `promote`, `tag`, `diff_layers`
  - `/conflicts`: `conflicts`, `resolve_conflict`; `/imports/{run}`: `import_run()`
  - `/export`: `seed.export`; `/backup`: `store.backup("manual")`; `/meta`: `kinds[k].describe()` and `layers()`

### What WP5 must know
- **Import runner:**
  1. `ids = store.id_lookup(layer=imp.layer, namespace=imp.namespace)`
  2. `recs = list(imp.records(src, ids))`
  3. `store.apply_import(run, recs, dry_run=..., ids=ids)`

  The legacy index and the ledger `region/ids/<ns>.tsv` are flushed in the import's own transaction; a dry run persists nothing. In tests, pass `ledger_dir`.
- **Records** a run yields are `{kind, id, data, geom, source?, kv?}`; an id twice in one run is refused (422).
- **Layers:** open_store creates the layers of every non-test namespace. Tests must create `import:test` themselves (`create_layer("import:test", namespace="test")`).
- **Kind files:**
  - Give each schema an `examples` list; the generic round-trip test over every discovered kind uses it.
  - Refs may name only kinds in the loaded set.
  - Use `columns` for `parent` and `c0`, `dates` for the era filter, `merge.unit: atomic` for profile, `merge.guard` for chainage pointers, and `x-conflict: authority_divergence` on param.
- **Authority records:** use id `ids.stable("old_hub", "authority:<kind>")`, written into `legacy:old_hub`. The legacy importer is exempt from the authority check, which is enforced as an import into a legacy layer. `flip_authority` copies the legacy revisions into main as one `legacy` changeset.
- **Validators:** a feature's `VALIDATORS` are found automatically and run against the changeset's final state through `ValidateCtx`.

`engine/PROTOCOL.md` also shows as modified in the working tree; that was not me.


## WP1 store, review report

### Left open (not fixed)

- **Legacy tombstones hide import records (WP5 must know).** A legacy import tombstones a copy-up it no longer yields. That tombstone hides the import layer's record underneath, in main as well.
- **Missing proposal parent breaks export.** If a proposal's `_layer.json` names a parent scenario that is missing on the importing machine, the whole seed import fails, and export with it.
- **`crhub model check` and `info` change the database.** They open the store, which migrates (after a backup) and rewrites the `kind` table.
- **Legacy-owned kinds in main.** Resolving a conflict as "theirs" in main is refused with 409 authority; "ours" works.
- **Two gaps in conflict detection.** A full `rebase()` with no lower layer does not look for dangling refs, and a dry-run import does not predict rebase conflicts.
- **Frozen contract gaps** (as the builder reported):
  - `ConflictReason` should list `exists`, `layer` and `seed`.
  - `ImportReport.changes` should document the `rebase` entries.
  - `Idempotency-Key` storage is not in the store.

I agree with the builder's other deviations: geometry stored as text, revert comparing content rather than version, and the GROUP BY list query.

### What WP2 and WP5 must know

- **The review queue gains two reasons from upper layers:** `dangling_ref` and `invalid` conflicts, each carrying `proposed`.
- **A record can have two open conflicts:** one from a seed import and one from the rebase planner. Export refuses while any seed conflict is open.
- **`IdLookupImpl` should be one instance per run.** It caches the orphans until `write_ledger` or `flush`.
- **Point 3 above** changes what the old_hub importer will see when import:profiles changes under legacy copy-ups.


## WP4 engine, build report

### Public interfaces as built
**TypeScript (`engine/src/index.ts`):**
- `solve(method: string, input: unknown, opts?: { engineBuild?: string; progress?: (f: number, stage: string) => void; checkOutput?: boolean }): Promise<unknown>`. It throws `EngineFault` with `code` set to `bad_request`, `unknown_method`, `invalid_input` or `internal`.
- `METHODS: readonly MethodDef[]`, `ENGINE_VERSION = "0.0.0"`, `METHOD_REFS`, `UNKNOWN_BUILD`, `findMethod(m)`, `methodRef(row)`, `hello(engineBuild)`, `inputHash(p)`, `sha256Hex(s)`.
- The geometry for the app: `vertices`, `design`, `railAt(d, c)`, `gradeAt(d, c)`, `railGrid(d, length, step)` (returns Float64Arrays `c`, `rail`, `grade`), `sectionDesign(input)`, `verticalRail(input)`, `pathAt`, `segmentAt`, `lowerBound`, `cumulativeLength`, `gridSize`, `gridChainage`, `gridIndex`, `RULE_IDS`, `RULE_STATUS`, `isRuleId`.
- Methods served: `vertical.rail@1` and `engine.echo@1`.
- Commands: `node engine/src/sidecar.ts` and `node engine/src/cli.ts <method> <input.json|->`.

**Python (`region.enginehost`):**
- `Pool(size=2, timeout_s=30.0, *, node=None, argv=None, cwd=None, env=None, hello_timeout_s=15.0, backoff_s=(0.1, 5.0))`, with:
  - `.call(method, params, *, timeout_s=None, key=None, progress=None)`
  - `.hello()`, `.start()`, `.close()`, `.slot_of(key)`, `.pids()`
  - `size=None` and `timeout_s=None` read `pools.engine` and `engine.timeout_s` from the config.
- `OneShot(timeout_s=30.0, *, node=None, cwd=None, env=None)` with `.call(method, params, *, timeout_s=None)` and `.hello()`.
- `Fake(responses=None, *, hello=None, validate=False)` with `.call(method, params, *, timeout_s=30.0)` and `.calls`. A response is a result, a callable of the params, or an exception to raise.
- `engine_build(engine_dir=None) -> str`.
- In `build`: `build_files`, `find_node`, `check_node`, `node_version`, `check_hello`, `known_contracts`, `engine_version`.
- `python -m region.enginehost.codegen [--check]`; `region.contract.gen` exports `SectionInput`, `VerticalRail`, `Flag`, `Hello`, `Request`, `Response`, `CONTRACTS`, `SCHEMA_VERSION`.

### For integration (WP2, WP3, WP5, WP6)
- **Server and scheduler (WP2, WP3):**
  - Call `Pool.start()` at server start-up, `Pool.close()` at shutdown, and expose `Pool.hello()` in `/meta`.
  - Build job keys from `hello()["engine_build"]`, the build actually running. `engine_build()` hashes the files, and the Pool does not restart sidecars when files change.
  - `EngineUnavailable` (503) and `EngineError` (502) both carry `.stderr_tail` as an attribute, never in the problem body; put it in the job log. `EngineError` also has `.engine_code` and `.issues` (zod's).
  - Calls route by `params["section_id"]`, or by `key=`. Progress callbacks are `(f, stage)`.
- **Profiles feature (WP5):**
  - `test_record_inputs_equal_engine_fixtures` can compare against `engine/test/golden/inputs/*.json`, ignoring `section_id`, `platform_id` and `scale`.
  - Those inputs are built from the page's normalised `align`. Record inputs built from the seed docs will differ on the 18 normalised routes, with the causes listed under Results.
  - Params: `platform_m` comes from `settings.platform` or `settings_rer.platform`, with the line file's `settings` on top (CVG Express 204.216). `vc_radius_m` comes from `vcRadius`. `vc_min_len_m` comes from `settings.vcMinLen` for both systems.
- **App (WP6):**
  - Use `import { solve } from "@cr/engine"` and pass `{ engineBuild }` taken from the server's hello, or "browser rail bytes equal Node's" fails.
  - `checkOutput: false` cuts Line 6 from about 6 ms to about 2 ms.
  - The browser needs `crypto.subtle`, which 127.0.0.1 provides as a secure context.
  - `src/serve.ts`, `src/sidecar.ts`, `src/cli.ts` and `src/build.ts` are Node only; `index.ts` and `host.ts` import no Node modules.


## WP4 engine, review report

### Left open
- **Job log (WP3):** WP3 never reads `EngineUnavailable.stderr_tail` or `EngineError.stderr_tail`/`.issues`, so the spec's "stderr tail into the job log" is not done yet.
- **Contract change for the lead:** `EngineError` in `region/core/errors.py` has no `stderr_tail` or `issues` parameters, so the client sets them as attributes. Proposed signature: `EngineError(detail, *, engine_code, stack, stderr_tail: str = "", issues: list | None = None)`.
- **For the lead:** add to `engine/package.json` `"gen:rules": "node scripts/gen_rules.ts"` and `"golden:update": "node scripts/golden_update.ts"`. Until then `npm run golden:update` does not exist; its exit test runs the script directly.
- **No grid-size guard.** A tiny `step_m` on a long section would make the sidecar run out of memory or time out. The job fails and the sidecar respawns, so no data is lost. A cap in `tol.ts` answered with `invalid_input` would close this if wanted.
- **A timeout kills the whole sidecar.** The protocol has no cancel, so other calls in flight on it fail with reason "timeout" and a detail naming the other call.
- **Progress callbacks run on the reader thread**, so a slow callback delays replies on that sidecar.
- **`Fake(validate=True)` is laxer than the engine.** It uses pydantic's lax mode, which takes "1.5" strings where zod refuses them.
- **The seed-doc test hard-codes counts** (20 matching, and Line_10, 11, 13 with no doc). Ben's next `hub/seed` export will fail it until it is updated. That is the intended alarm, but it is coupled to `hub/seed`.
- **Input order can matter in two edge cases:** two stations with the same `order`, or two PVIs at the same chainage. WP5's records are keyed by chainage, so neither occurs from them.
- **A correction to the builder's report:** for a null `st` the page computes `null + gp*(...)`, which puts the platform at level about 0 (sea level), not NaN. The port leaves that platform out and flags it.

### For integration (WP2, WP3, WP5)
- **WP2:** at shutdown call `Pool.close()` (it now always closes every slot). An `EngineUnavailable(reason="contract")` whose detail says "restart the hub" means the engine source changed under a running hub. Show it to Ben as such.
- **WP3:** build job keys from `hello()["engine_build"]`. Caching it is now safe, because the pool never answers from another build. Log `stderr_tail` (on both errors) and `EngineError.issues` into the job log.
- **WP5:** the RER `vc_min_len_m` falls back to `settings.vcMinLen` (30.5), because the registry has no `settings_rer.vcMinLen`. Line-file `settings` override the registry (CVG Express 204.216).

The 3.12 env (`venv312`) and the clean copy were in the shared scratchpad, `/tmp/claude-0/-home-user-cincinnati-rail/388de07f-a9eb-500e-a913-639254f5ddc4/scratchpad/`. I first wrote `stress.py` and `stress2.py` at its root before moving them to `wp4review/`. If another agent had a `stress.py` there, mine overwrote it.


## WP3 jobs, build report

### Public interfaces as built

```python
Scheduler(store, cache_path: Path, engine: EngineClient | None, *, threads=4, processes=2,
          registry: Registry | None = None, params: ParamResolver | None = None,
          on_event: Callable[[str, dict], None] | None = None, blobs_dir: Path | None = None,
          engine_slots: int | None = None, lease_s=None, heartbeat_s=None, max_requeue=None,
          poll_s=0.5, kill_grace_s=1.0, max_tasks_per_child=50)
  .start() -> Scheduler; .stop(timeout=10.0)          # also a context manager
  # the Scheduler protocol
  .submit(type, scope, view, priority=1) -> {"key", "state": "hit"|"queued"|"running", "job"}
  .result(type, scope, view) -> str | None
  .watch_goal(type, scope, view, priority=5, ttl_s=None, *, pinned=None)
  .cancel(job_id); .jobs(active=True, limit=500) -> list[dict]
  # extras
  .job(id); .job_log(id); .result_meta(key); .read_array(key, name)
  .array_bytes(key, name) -> (bytes, dtype, shape); .read_blob(key, name)
  .subscribe(fn) -> unsubscribe; .notify(); .invalidate(refs); .replan_all()
  .pin(type, scope, view, on=True); .unwatch(...); .evict(max_bytes) -> {"results", "blobs", "bytes"}
  .wait_idle(timeout=30.0) -> bool; .wait_job(id, timeout=30.0) -> dict
  .registry, .cache, .planner

keys.key(type: str, version: str, code: str, refs: list[tuple[str, str]], axes: dict,
         engine_build: str | None, contracts: dict) -> str
    # = sha256(canonical_json({t, tv, code, e, c, axes, in})); in = refs, deduplicated and sorted
keys.key_body(...); keys.code_hash(job_type)

cache.read_array(key: str, name: str, *, cache_path: Path | None = None) -> np.ndarray
cache.default_cache_path() -> var/cache/cache.db      # blobs default to var/cache/blobs/<sha[:2]>/<sha>
cache.migrate(path) -> int; cache.attach(con, path, schema="cache"); cache.Cache(path, *, blobs_dir=None)
cache.encode_output(output); cache.output_hash(output); cache.wipe(path)

plan.Planner; plan.PlanContext (PlanCtx); plan.ReadOnlyStore; plan.JobWriteRefused(PermissionError)
plan.resolve_param(store, view, path, scope=None)
hosts.RunContext (RunCtx); hosts.NoEngine
registry.Registry; registry.default_registry(); registry.check_job_type(jt) -> list[str]
registry.find(module, name)
contract.check_contract(job_type, store, scope_id, view=None, *, engine=None, registry=None, params=None)
```

The CLI is `crhub jobs [--cache PATH] list|show|types|stats|prune --max-mb N|wipe --yes|run TYPE SCOPE [--layer --year --month --tl --db]`.

### What integration must know

**WP2 (server):**
- **Order at start-up:**
  1. Call `region.jobs.cache.migrate(cache_path)`, or construct the Scheduler, before `open_store(db, cache=cache_path)`. WP1's `attach_cache` fails ("unable to open database") when the `cache/` folder does not exist yet.
  2. Then `sched = Scheduler(store, default_cache_path(), engine, threads=cfg.pools.threads, processes=cfg.pools.processes).start()`.
  3. Call `stop()` at shutdown.
- **Routes:**
  - `/compute` → `submit`; `/results?…` → `result`; `/results/{key}` → `result_meta`.
  - `/results/{key}/a/{name}` → `array_bytes`, which gives the raw little-endian C-order bytes plus dtype and shape for `X-Dtype` and `X-Shape`.
  - `/jobs` → `jobs(active=…)`; `/jobs/{id}` → `job`; `/jobs/{id}/log` → `job_log`; `/jobs/{id}/cancel` → `cancel`.
  - `/meta` job types → `sched.registry.describe()`.
- **Events and invalidation:**
  - `subscribe(fn)` delivers `("job" | "result", payload)` from scheduler threads, so hand payloads to the event loop thread-safely.
  - Call `notify()` after each write. The invalidator also polls every `poll_s`, 0.5 s by default.
  - Call `replan_all()` on a new epoch or after a restore.
- **Errors:** `submit` raises `NotFound` for an unknown type, and `EngineUnavailable` for an engine job when there is no engine.

**WP5 (job types):**
- Job types are module-level objects in `JOB_TYPES`. Process-host types must be importable by module and name.
- Return an `Output` whose meta and issues are plain JSON: no NaN, no integer over 2**53.
- For chainage `changed` ranges, put `grid: {c0, step_m}` in meta, with 1-D arrays on that grid.
- Engine jobs use `host = "engine"` and call `rt.engine.call("vertical.rail", input)`. The key includes `engine_build` and the contract majors from `engine.hello()`.
- `ctx.need(type, scope)` returns a ref; `rt.upstream(ref)` gives that upstream's `Output`.
- `ctx.param`'s default resolver expects `param` records with `{path, value, scope?, years?}`. Pass `Scheduler(params=...)` if the rules feature's shape differs.
- Use `region.jobs.contract.check_contract(jt, store, scope, view, engine=...)` for `test_job_type_contract`.

**Lead:** `crhub jobs run` and `crhub jobs wipe` must only run while no server holds the cache; nothing checks the server lock.

No new dependencies.


## WP3 jobs, review report

### Left open
- **WP1 holds cache.db's write lock on every truth write.** `region/model/db.py` attaches cache.db to its writer connection, and SQLite's `BEGIN IMMEDIATE` takes the write lock on every attached database. I confirmed this here: the cache writer is blocked while the truth writer's transaction is open. So every truth write also locks cache.db, and the scheduler waits on it (busy timeout 5 s). WP1 should attach the cache on its readers only (`writer_for(path, cache=None)`).
- **`seed.export` as a cached job can miss proposal edits.** A plan reads one view, but `region.model.seed.export` writes every seeded layer, so a change made only in a proposal leaves a main export's key unchanged. WP2's `/export` should call `region.model.seed.export` directly, as `crhub model export` does, or submit in the proposal's view. A real fix needs a layer-listing read in `PlanCtx`, which the lead would have to add.
- **The key formula has no scope.** Any job type whose inputs carry the scope id beyond what it read shares one result between scopes. WP5 must not echo the scope. `check_contract`'s probe catches this, and could flag a WP5 type such as a golden diff that reads every section and also returns its scope.
- **Two schedulers on one cache are unsafe.** While the server runs, `crhub jobs run` would run the server's queued jobs, and its start-up sweep can delete a blob the server has just committed. Something must check the server lock; the builder flagged this too.
- **Contract changes the builder asked for still stand:**
  - an `EngineClient` cancel;
  - `Store.last_seq`/`min_seq` and an epoch in the protocol. Without an epoch, a restore followed by new writes before the next poll is missed.
  - a `JobState` `waiting`, if wanted;
  - documentation of the optional `JobType` members.
- **Not hardened:** a plan can still reach the real store through bound callbacks, for example `ctx._PlanContext__planner.engine_info.__self__.store`. Python cannot fully sandbox this; the protection is against accidental writes.

### For integration
- **WP2:** the start-up order and routes are as the builder reported.
  - A result row whose blob is lost now heals: a downstream job recomputes its upstream.
  - `array_bytes` still raises `NotFound` for a direct read of a lost blob.
  - Call `notify()` after writes. Before the server lock exists, keep `crhub jobs run/wipe` from running while the server runs.
- **WP5:**
  - Run `check_contract` for each job type; it now includes the scope probe.
  - A job whose scope is a record id must read that record, and plans must not copy `scope_id` into their inputs.
  - Process-host types must live in an importable module (`region/ext/<f>/jobs.py`), not in a test-only synthetic package.


## WP6 app, build report

### Public interfaces as built
In `app/src/core/plugin.ts`:
```ts
interface Plugin { id: string; panes?: PaneDef[]; layers?: LayerDef[]; bands?: BandDef[]; commands?: CommandDef[];
  keymap?: KeyBinding[]; urlParams?: UrlParamDef[]; kinds?: KindUiDef[]; activate?(h: Host): Disposable | undefined }
interface PaneDef { id: string; title: string; accepts?(sel: Selection): boolean;
  mount(el: HTMLElement, ctx: PaneContext): Promise<{ dispose(): void; serialize?(): unknown }> }
interface PaneContext { host: Host; params: Record<string, unknown>; state: unknown; setTitle(t: string): void; onResize(fn: () => void): Disposable }
interface LayerDef { id: string; group: string; title?: string; defaultOn?: boolean; source: Source;
  style(ctx: LayerStyleContext): LayerSpecification[]; time?: "intervals" | "none"; pick?(f: PickedFeature): RecordRef | null;
  available(): Promise<true | string> }
type Source = { type: "records"; kind: string; query?: Record<string, string> } | { type: "image"; tier: string; image: string; corners: string }
  | { type: "geojson"; url: string } | { type: "pmtiles"; url: string }
interface BandDef { id: string; height: number; axis?: "profile" | "strip"; draw(g: CanvasRenderingContext2D, view: SheetView, data: BandData): void;
  hit?(x: number, y: number): Handle | null }
interface CommandDef { id: string; title: string; run(host: Host, arg?: unknown): void | Promise<void>; when?(host: Host): boolean }
interface KeyBinding { key: string; command: string }
interface UrlParamDef { name: string; aliases?: string[] }
interface KindUiDef { kind: string; label?(rec: Rec): string; hidden?: string[] }
type Selection = RecordRef | { legacy: { lkind: string; key: string } } | null
interface Host { api: Api; store: AppStore; records: RecordCache; events: EventFeed; drafts: Drafts; undo: UndoStack; units: Units;
  engine: EngineHandle; registry: Registry; view(): View; select(sel: Selection, opts?: { c?: number }): void;
  openPane(id: string, params?: Record<string, unknown>): void; runCommand(id: string, arg?: unknown): Promise<void>;
  toast(t: Toast | string): void; problem(e: unknown): void; status(item: StatusItem | { id: string; remove: true }): void;
  meta(): Promise<Meta>; oldHub(): string }
```

URL codec, in `app/src/core/url.ts`:
- `parseUrl(href, { params? }) -> UrlState` and `formatUrl(UrlState) -> "/w/<ws>?layer&year&month&tl&sel&c&lay&map&<extras>"`.
- `UrlState = { workspace, layer, year, month, tl, sel, c, lay: Record<string, boolean>, map: { z, lat, lon } | null, extra }`.
- `CORE_PARAMS` and `OLD_COLLECTIONS`.

Store, in `store.ts`:
- `createAppStore`, a zustand vanilla store, with `update(patch, nav?)`.
- `bindUrl(store, window, params)`: pushState for sel, layer, year, month, tl and workspace; replaceState for c, map and lay.

Other modules:
- **Registry:** `Registry.add/remove/fromModules`, `discover()` (`import.meta.glob("../plugins/*/index.ts", { eager: true })`), `DuplicateId`.
- **Transport:** `Api` has `send`, `get`, `getRecord`, `list`, `geojson`, `create`, `put`, `patch`, `remove`, `history`, `restore`, `legacy`, `changeset`, `revert`, `layers`, `createLayer`, `conflicts`, `compute`, `latestResult`, `result`, `resultArray`, `jobs`, `cancelJob`, `tiers`, `sectionInput`, `clientLog`. Errors are `ApiError` carrying the problem; `etagOf(rec)` builds the ETag.
- **Events:** `EventClient` (in `stream.ts`); `connectEvents(o) -> EventFeed`, a SharedWorker with an in-tab fallback.
- **Engine:** `createEngine(o) -> EngineHandle` with `state`, `reason`, `hello`, `ready`, `solve`, `onChange`, `dispose`; `unavailableEngine(why)`.
- **Drafts and saving:** `Drafts`; `save(deps, key) -> {clean} | {saved, rec} | {stale, offer: {keepMine(), takeTheirs(), theirs, by, diff}}`; `UndoStack.undo/redo` revert server changesets.

### What integration must know

**WP2 (server)**
- **Static files.**
  - Serve all of `app/dist` at its own paths: `/` and `/w/*` go to `index.html`, plus `/assets/*` and `/map/**`.
  - `.mjs` must be served as `text/javascript`: the MapLibre worker and our module workers need it.
  - `.pbf` should be `application/x-protobuf`.
  - Under the spec's CSP the build needs no inline script or style, no eval and no blob.
- **Headers.**
  - Every request, GETs and the SSE fetch included, carries `X-CR-Client`.
  - Writes are `application/json`; PATCH is `application/json-patch+json`; POST create sends `Idempotency-Key`.
  - Reads send `If-None-Match` and reuse the body on 304.
- **SSE.**
  - The client sends `Last-Event-ID` and `Accept: text/event-stream`.
  - Every connection must start with `event: hello {epoch, seq, engine_build}`.
  - Durable events need `id: <seq>`.
  - The client reconnects after 60 s of silence, so send a comment keepalive at least every 30 s.
  - Poll fallback: either `[{seq, type, data}]` or `{events, epoch, seq}`.
- **Response shapes the app accepts.**
  - Lists: a bare array, or `{items|records|data|results, next|after|cursor}`.
  - `/meta`: kinds as an array or a map, each with `kind` (or `name`), `version`, `title`, `schema`, `legacy[]`; plus `layers`, `epoch`, `engine` (the hello), and `old_hub` at top level or as `config.old_hub`.
  - 412: needs `current` (get() shape) and `by`; without them the app GETs the record itself.
  - `/results?type&scope&view`: `{key}` or a bare string. Please answer `{key: null}` with 200 rather than 404, because Chromium logs every 4xx as a console error. The e2e specs tolerate 404 here and on `/legacy/`.
  - `/results/{key}/a/rail_m`: bytes with `X-Dtype` (`f8`, `<f8` or `f4`) and `X-Shape`. `/results/{key}` should carry `meta.step_m`.
  - `/tiers`: a list of `{name, status, mount, detail}`, or a map from name to status.
- **GeoJSON** (`format=geojson&crs=4326`). Features need properties `id`, `kind`, `name`, `system`. For the client-side era filter, add `open_lo/open_hi/close_lo/close_hi` (month indices); without them the filter is off.
- **Old-hub URL.** The legacy pane links to `/`, `/deck/`, `/profiles/profiles.html#Line_6`, `/3d/`, `/chronology/` and `/access/` on `old_hub`.

**WP5 (features)**
- **Profile and section.** The sheet finds a profile's section through `data.section` (or `section_id` or `parent`), and a section's profile through `/k/profile?parent=<section id>` (then `ref=`).
- **Profile data.** `st` is keyed by the same `platform_id`s as `SectionInput.stations`. `pvi` may be `[c, z]` pairs or `{c_m, z_m}` objects; edits keep the record's own shape.
- **Solve results.** Job type `profiles.solve_section`, scope is the section id, view is `View.token()`, and the result array is named `rail_m`.
- **Legacy lookups.** Ctrl+K takes its legacy kinds from each kind's `legacy` list in `/meta`, with a fallback list. URL aliases assume lkind `route` for route ids; please confirm or tell me the real lkind names. The e2e finds Line 6 through `/legacy/{section|route|line}/Line_6`, then `/k/section?q=Line_6`.
- **Map data.** The map spec expects exactly 16 features with `system: metro` in `main`.

**WP4 (engine)**
- Please make `@cr/engine` CSP-safe by calling `z.config({ jitless: true })` itself, or by exporting a hook for it. Then the app can drop its direct `zod` import. Otherwise the lead should add `zod` to `app/package.json`.

**WP1 (store)**
- Copy-up version numbering decides whether the spec's literal "version 2/3" holds; the specs only check the steps.

**Lead**
- After WP2 writes `region/api/openapi.json`, run `npm run gen:api -w app` and commit `app/src/api/gen`. Until then the drift test is skipped; once the file exists it fails until the generated types are committed.
- The default e2e ports are 8799 (shared hub) and 8798 (the restart test).


## WP6 app, review report

### Left open, decisions for the lead
- **Keep mine replaces the whole record.** It overwrites "theirs" with my whole working copy, so their edits to fields I did not touch are reverted (the unit test asserts exactly this). That fits the profile's `atomic` merge unit (9.11). If Ben wants per-field kinds rebased instead, this needs a ruling.
- **Echo skipping is by version, not by the event's `client` field** (builder deviation 2). This is safe: at worst it costs an extra GET.
- **`zod` is not declared in `app/package.json`.** It comes hoisted from `@cr/engine` for the CSP-safe `jitless` setting. The lead should add it, or WP4 should set `jitless` itself.
- **`npm run gen:api` deletes `src/api/gen/README.md`**, because the generator cleans the folder (the README says so).
- **The sheet blanks on a reload with no selection** and does not reopen the section it saved in its layout state. This is a minor UX gap.

### What integration must know (beyond the builder's list)
- **WP2:**
  - The app now POSTs `/compute` whenever a sheet opens a section and after every new profile revision. That route must answer 200 with `{key, state, job}`, `state` being one of `hit`, `queued` or `running`. A 4xx shows as a console error and fails "no console errors".
  - The map now lists with the view's `year` and `month`. A future "every era" list option would let it filter on the client only, as 9.30 intends.
- **WP2/WP3:** a goal for each scenario is no longer needed for the gate, but a watched goal is still welcome.
- **The `resync.spec` restart test:** on Windows it stops the hub with `TerminateProcess`, so the second start depends on WP2's lock not being a stale PID file.


## WP0b ops, build report

### Public interfaces as built

**`region.tiers`**
- `scan(cfg: Mapping | None = None) -> dict[str, TierReport]`, in config order.
- `scan_tier(tier: paths.Tier) -> TierReport`
- `as_json(reports, *, at=None) -> {"at", "counts", "tiers": [...]}`: this is the body for `GET /tiers`.
- `changes(before: Mapping | None, after) -> list[TierEvent]`
- `counts(reports) -> {"missing", "partial", "present"}`
- `required_missing(reports) -> list[TierReport]`
- `clear_cache()`, `STATUSES`
- `TierReport(name, status, detail, root, about, lane, required, mount, findings: tuple[Finding, ...], handshake: dict | None)`
  - `.uri` is a property giving `tier://<name>/`.
  - `.event() -> TierEvent` and `.as_dict()`.
- `Finding(what, file, ok, detail)`

The tier rules:
- **missing:** the root is absent, or the tier's config entry cannot be read.
- **partial:** the manifest or index is absent or unreadable, a source named in a VRT index is absent, a directory index is empty, the handshake file is absent, unreadable or not done, or a tier that declares no manifest, index or handshake has an empty root.
- **present:** otherwise.

The detail for the 1912 tier is `"stage contours"`. A handshake's `blocked_on` shows as `"blocked on X"`.

**`region.cli.doctor`**
- `run_checks(cfg=None, *, data=False, runner=None, env=None) -> list[Check]`
- `Check(name, status: "ok"|"info"|"skip"|"warn"|"fail", detail, hint)`
- `render(checks, *, header=None) -> str`, `exit_code(checks) -> int`, `failed(checks)`
- `synced_folder(path, env=None) -> str | None`, `network_folder(path) -> str | None`
- `app_build(repo) -> {source, built, built_at, newest, newest_at, stale}`
- `identify(host, port) -> "hub" | "old hub" | None`, `listening(host, port)`, `bind_error(host, port)`
- One function per check: `check_python`, `check_packages`, `check_uv`, `check_sqlite(connect=...)`, `check_node(cfg, runner)`, `check_npm(repo, runner)`, `check_var(cfg, env)`, `check_repo`, `check_hub_port`, `check_old_hub_port`, `check_tiers`, `check_sources`, `check_app`, `check_database(cfg, *, data)`.
- `Runner = Callable[[Sequence[str]], tuple[int, str]]`

Doctor exits 1 only when a row FAILs. What fails and what only warns:
- **Fails:** Python older than 3.12 or 32-bit; a missing runtime package; SQLite older than 3.38 or without JSON or window functions; no R-tree; Node missing, older than 22.18, or not stripping types; `node_modules` missing or a workspace linked to another checkout; `var` in a synced folder or on a network share; `var` not writable; port 8766 held by another program or by the old hub; a missing required tier; `app/dist` missing while `app/src` exists; a database that fails `quick_check`.
- **Only warns:** stale packages, stale `node_modules`, a stale `app/dist`, a missing optional tier, a repo inside a synced folder.
- **Information only:** a partial optional tier, port 8765, uv.

The write probe in `var` is deleted afterwards, along with any folder it had to create.

**`region.cli.setup`**
- `plan(args, *, repo=None, environ=None, which=shutil.which, prefix=None) -> Plan`
- `execute(plan, *, runner=run_command, environ=None) -> int`
- `Step(name, about, argv, action, skip, hint)`
- `Plan(repo, steps, env_dir, reexec)`
- `migrate_db(cfg=None) -> int`, `first_imports(cfg=None) -> int`, `hub_serving(cfg=None) -> str | None`, `run_doctor()`
- Helpers: `venv_python`, `uv_env_dir`, `has_pip`, `same_env`, `python_steps`, `npm_steps`, `child_env`, `run_command`

The steps:
1. **Python packages:**
   - with uv: `uv sync --locked --inexact`;
   - without uv: create `.venv` with this Python (adding pip with `ensurepip` if a uv-made `.venv` has none), then `.venv` python `-m pip install -r requirements.lock -e .`.
2. `npm ci`
3. `npm run build -w app`, skipped with a message while `app/src` is absent.
4. The database:
   - creates `var/region.db`, or runs `region.model.migrate.migrate(con, backup_dir=var/backups)`, which backs up first;
   - skipped with a message while `region.model` cannot be loaded.
5. First imports, skipped with a message until the hook exists.
6. Doctor; setup's exit code is the doctor's.

When setup runs under a Python other than the environment step 1 installed into, it runs steps 4 to 6 again in that environment's Python. It refuses to start while a hub is serving on the configured port.

### What integration must know
**WP2 (server):**
- `GET /tiers` is `region.tiers.as_json(region.tiers.scan())`. Send tier events from `region.tiers.changes(prev, now)` after each scan.
- The serve banner can use `region.cli.doctor.app_build(repo)["stale"]`.
- `/api/v1/health` must answer 200 with JSON. Doctor and setup use it to recognise a running hub, because I don't know WP2's lock format. If `lock` gets a reader, `setup.hub_serving` could use it instead.
- CI assumes serve takes `--no-browser`, `--db` and `--port`.
- **Every `region/cli/*.py` must import third-party packages inside its functions, not at module top.** `build_parser` imports every CLI module at start-up. On Windows a loaded `.pyd` (pydantic_core, numpy) then stops pip or uv from replacing it in setup's step 1.

**WP5 (imports):**
- Provide `setup_imports(db) -> int` in `region/cli/imports.py`.
- The runbook documents `crhub rebuild --compare`.
- Features' `SOURCES` get doctor rows automatically.

**WP1 (store), for the lead to keep stable:**
- Setup uses `region.model.db.connect` and `migrate.migrate`, `current_version`, `discover` and `pending`.
- Doctor uses `backup.quick_check`, and `open_store(db, create=False)` as a context manager with `.check_data()`.


## WP0b ops, review report

### Left open
- **CI has never run on GitHub,** because nothing was pushed. The Windows job is unverified.
- **Read-only opens leave `region.db-wal` and `region.db-shm` in `var`** (from `quick_check` and the backup). This is SQLite's normal behaviour, not a data change; the main file stays byte-identical.
- **Setup detects a running hub only by HTTP** (`/api/v1/health` on the configured port). A hub started with `--port` elsewhere is not seen. `BEGIN IMMEDIATE` in `apply_one` still keeps migrations safe. Once WP2's lock has a reader, `setup.hub_serving` should use it.
- **WP1 change needed (outside my paths):**
  - `crhub model check` (where doctor's `records` hint sends Ben) uses `open_store` on the live file, so it also migrates and rewrites the `kind` table.
  - Suggestion: give `open_store` a `readonly=True` mode that skips `migrate`, `ensure_namespace_layers` and `_sync_kinds`; `doctor --data` could then drop the copy.
- **The 1912 handshake:** spec section 7 of `ground/1912/SPEC.md` (and 9.26) also asks that the report's targets are met. The tier scan reports present on `done: true` alone; the targets gate belongs with the `real_1912` layer record (later).
- **Builder deviations accepted as reasonable:** the Checklist and Plan docs were not touched; the engine CI matrix is `22.18` and `24`; the runbook uses `crhub model export|backup|restore`; the e2e job is a placeholder.

### Public interfaces added by this review
- `region.cli.doctor.module_absent(name: str) -> bool`
- `region.cli.doctor.windows_unc(path: str) -> tuple[bool, str]`
- `region.cli.doctor.check_sources(cfg: Mapping | None = None) -> list[Check]`

Everything else is as the builder reported.

### What integration must know (WP2, WP5)
- **WP2:**
  - `GET /tiers` is `region.tiers.as_json(region.tiers.scan())`, and tier events come from `tiers.changes(prev, now)`. The scan never raises, even for a malformed `local.json`.
  - `/api/v1/health` must answer 200 with JSON; doctor and setup recognise the hub by it.
  - Every `region/cli/*.py` must import third-party packages inside its functions, not at top level.
- **WP5:**
  - Provide `region/cli/imports.py` with `setup_imports(db) -> int`.
  - Once that file exists, an import error in it stops `crhub setup` instead of being skipped.
