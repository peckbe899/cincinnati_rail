# region/core: the frozen contracts (WP0a)

Every package of increment 1 codes against these modules and nothing else of another package. The interfaces marked
with a star in section 10 of `claude/Hub_Region_Architecture.md` are here exactly as the spec names them; this file
records the conventions around them and every choice made where the spec is silent. Change a frozen interface only
through the lead, and then in every package at once.

| Module | What it holds |
|---|---|
| `view.py` | `View(layer, year, month, timeline)`, `instant()`, `token()`; partial dates as month intervals; `is_open` |
| `protocols.py` | `Store`, `Op`, `WriteResult`, `ImportRun`, `ImportReport`, `PlanCtx`, `RunCtx`, `Output`, `JobType`, `Scheduler`, `EngineClient`, `Importer`, `IdLookup`, `ValidateCtx`, `Validator`, `PathResolver`; the `Record` shape; ETags and refs |
| `errors.py` | `NotFound` 404, `PreconditionRequired` 428, `PreconditionFailed` 412, `Conflict` 409, `Invalid` 422, `EngineUnavailable` 503, `EngineError` 502; `to_problem()` gives the RFC 9457 body |
| `events.py` | the TypedDict payloads of section 5: `record`, `changeset`, `job`, `result`, `tier`, `resync`, `hello` |
| `ids.py` | `new()`, `stable(namespace, key)`, `namespace_of(id)`; namespaces from `region/ids/namespaces.yaml` |
| `features.py` | `discover()` of `region/ext/*/`; `kind_files()`; `check_kind()` against `region/kinds/_meta.schema.json` |
| `fsio.py` | `write_atomic` (WinError 5 and 32 retried), the write guard, UTF-8 reads, `canonical_json` (RFC 8785), hashes |
| `paths.py` | the repo, `var`, the merged config, data tiers, `tier://` `repo://` `var://` resolution, unsafe-path checks |
| `log.py` | JSON lines in `var/logs/hub-YYYY-MM-DD.jsonl` with `request_id` and `job_id`, kept 30 days |

## Conventions every package follows

- **Records cross boundaries in the get() shape** (`protocols.Record`): `id, kind, kv, layer, version, hash, deleted,
  origin, source, by, changeset, created, updated, geom, data`. `layer` is a slug, `geom` is WKT in EPSG:26916 snapped
  to 1 mm (or `None`), `data` is the kind's JSON. `hash` is `fsio.content_hash` of `{id, kind, kv, geom, data}` only,
  so bookkeeping never enters it (9.29).
- **A write body** is the writable part of a record, `{"data": ..., "geom": ...}`. JSON Patch paths are relative to
  it (`/data/pvi/3/z_m`), so a patch cannot reach bookkeeping. Event `fields` use dots (`data.pvi`).
- **ETags** are `"<layer>:<version>"` with the quotes (`"import:profiles:3"`); `parse_etag` splits on the last colon
  and accepts `W/`. `if_match` arguments take the value as the client sent it.
- **Refs** are `rec:<id>`, `file:<uri>`, `param:<path>`, `job:<type>/<scope>` (`ref_rec` and friends).
- **Files are named by URI**, never by absolute path: `tier://<tier>/<path>`, `repo://<path>`, `var://<path>`.
- **Every file write** goes through `fsio.write_atomic` (or `write_text`, `write_json`). Writes outside `var/`,
  `app/dist`, `region/seed/` and `region/ids/` raise `fsio.WriteRefused`; tests wrap writes in `fsio.allow_writes`
  or use the `write_root` and `hub_var` fixtures of `tests/conftest.py`.
- **Every read of text** passes `encoding="utf-8"` (ruff rule PLW1514 enforces it) or uses `fsio.read_text`.
- **Expected failures raise `errors.*`**, never bare `ValueError` or `KeyError`; the server maps them by `status`.
- **Docs and comments** are plain direct sentences, without em dashes.

## Choices made where the spec is silent

**View.** A month needs a year; months are 1 to 12; `timeline` is `canon` or `real`; a layer slug matches
`^[a-z][a-z0-9_-]{0,63}(:[a-z0-9][a-z0-9_.-]{0,63})?$`; a year is -9999 to 9999, so `token()` always parses back.
Month indices count months since year 0 (`year * 12 + month - 1`).
`instant()` is the last month the view covers and `None` at the present (`year=None`). `token()` is
`layer|when|timeline` with `when` one of `-`, `1931`, `1931-09` (the spec's example `"main|-|canon"`); `View.parse`
inverts it. `is_open(instant, opened, closed)` is the one statement of the 9.16 rule: open when the opening interval
starts at or before the instant and the closing interval has not started by then; undated openings count only at
the present. `key_axes(declared)` gives only the declared axes for a cache key; the layer is never an axis.

**Ids.** `new()` is a ULID made here (not by python-ulid, which is only used by tests to cross-check), monotonic
within a process so ids minted in one millisecond still sort in order. `stable()` hashes `"<namespace>:<key>"` with
the key NFC-normalised. Each namespace's epoch is a distinct day in `region/ids/namespaces.yaml`, all before 2020-01-04,
so every imported id sorts before every authored id, and `namespace_of(id)` reads the namespace back from the time
part: that is how the store enforces an import layer's namespace on write. A `test` namespace exists for tests.

**Errors.** `Conflict(reason=...)` gives the problem code `conflict_<reason>`. `EngineError` (502, an `ok: false`
reply) is added beside the six named errors, because a timeout or crash (`EngineUnavailable`) and an engine that
answered with an error need different handling. Problem `type` URIs are
`https://cincinnati-rail.invalid/problems/<code>` (a reserved domain that never resolves).

**Events.** Durable record events carry `op` in `create | put | patch | delete | restore`. `changeset` events may also
carry `kind`, `message` and `client`; `job` events may carry `view`, `key` and `error`. `BULK_THRESHOLD = 200`.

**Protocols.** `WriteResult(changeset, records, seq)`: `changeset` and `seq` are `None` when every op was a no-op.
`ImportRun(importer, version, layer, namespace, sources, by, id)` with `sources` as `{name: {uri, sha256}}` and `by`
defaulting to `import:<importer>`. `ImportReport` carries `counts` (`created, updated, unchanged, deleted,
conflicts`), `by_kind`, `changes`, `conflicts`, `changeset`, `errors`. `Output`'s four members default to empty, in
the spec's order. `Store.write` takes `ops: list[Op]` (spelt `Ops`, because the protocol's own `list` method would
shadow the builtin for type checkers). `Scheduler.watch_goal` defaults `priority=5` and `ttl_s=None`. Job and
importer `version` is a string (`"1"`), matching `keys.key(version: str)`. `Importer.sources(paths)` receives the
`region.core.paths` module (it satisfies `PathResolver`) and returns `{name: uri}`; the runner resolves and hashes
them and calls `records(src, ids)` with `{name: local Path}`. `ValidateCtx` and `Validator` define what a feature's
`validators.py` exports. `RunCtx.engine` is always an `EngineClient`; a non-engine job may get one that raises
`EngineUnavailable`. All protocols are `runtime_checkable`.

**Feature folders.** The exports are `IMPORTERS`, `JOB_TYPES`, `router`, `VALIDATORS` and `SOURCES` (the last: the
data files and tiers a feature reads, as `{name: uri}`, for doctor). A feature folder name is a lowercase identifier;
names starting with `_` or `.` are ignored; any other name is `Invalid`. `discover()` imports nothing; a feature
outside `region/ext` (a test's temporary root) is imported through a synthetic namespace package, so relative imports
inside it work. `region/ext/` itself is created by WP5 and may be a namespace package (no `__init__.py`).

**Kind files.** The meta-schema adds to the spec's list: `title`, `description`, `dates` (pointers to the open and
close partial dates), `refs[].role` and `refs[].required`, and `merge.guard` (pointers, such as chainage, whose change
below always becomes a proposal, as geometry does). `columns` may promote only `name, system, parent, c0, c1, ord,
phase`. Any subschema whose `type` admits numbers must carry `x-unit`, checked recursively by the meta-schema;
`check_kind` also checks every `x-unit` is a unit of `_vocab.yaml` (feet are not: they live only at the edges) and
every `x-vocab` names one of its lists. WP1's `kinds.load` should call `check_kind_file` for each file.

**Canonical JSON.** One canonical form for the whole hub: RFC 8785 (JCS), the same bytes in Python
(`fsio.canonical_json`) and TypeScript (`canonicalJson` in `engine/src/contract/common.ts`), checked against the same
vectors in `engine/test/contract.jcs.json` by both test suites. Integers beyond 2**53, NaN and infinity are refused.
Content hashes, job keys and the engine's `input_hash` all use it.

**Config and var.** `configs/hub.json`, then `configs/hub_paths.json`, then `configs/local.json` (gitignored), merged
in that order; `local.json` moves a tier with `{"tiers": {"<name>": {"root": "..."}}}`. `var` is, in order: the
environment variable `CRHUB_VAR`, `"var"` in local.json, `"var"` in hub.json, the platform default
(`%LOCALAPPDATA%\CincinnatiRail\hub` on Windows, `<repo>/var` elsewhere). Relative values are relative to the repo.

**Tiers.** `configs/hub_paths.json` holds a list of tiers, each with `name, about, lane, root, manifest, index,
handshake {file, done, detail} or null, required, mount`. `paths` only finds roots: `resolve()` raises `TierMissing`
(a 404 `NotFound` with a plain `reason`) for an unknown tier or an absent root, and `available()` returns `True` or
that reason. The full scan (missing, partial, present from the manifest, index and handshake) is `region/tiers`
(WP0b). `mount` is a boolean: mounted tiers are served at `/api/v1/data/<name>/<path>`.

**Unsafe paths.** `check_relpath` refuses `..`, `.`, empty segments, backslashes, any leftover percent escape
(`%5c`, `%2e`), absolute and UNC paths, drive letters, `:`, `<>"|?*`, control characters, reserved device names
(`CON`, `PRN`, `AUX`, `NUL`, `COM0-9`, `LPT0-9`, `CONIN$`, `CONOUT$`, with any extension and in any case) and names
ending in a dot or space. `UnsafePath` is a `NotFound`, so the server answers 404 without saying why.

**Logs.** One JSON object per line: `at` (local time with offset), `level`, `logger`, `msg`, `request_id`, `job_id`,
`exc`, plus any `extra`. Files roll over by local date; files older than 30 days are deleted at setup and rollover.
Browser entries from `/client-log` go to logger `region.client` with their members prefixed `client_`.

**CLI.** `python -m region` builds one argparse parser from `region/cli/*.py` (each module's `register(subparsers)`
must add a subparser named after its file and set `func(args) -> int | None`). A module that fails to import is shown
as unavailable and exits 2 when run, so one broken command never takes the others down. With no command, `serve`
runs once it exists (9.22); until then the help is printed. `info` is the first command: it reports the repo, Python,
`var` and where it came from, configs, tiers, features and commands (`--json` for one object). The console script
`crhub` (from `pyproject.toml`) runs the same `region.cli:main`.

**Tests.** `tests/` and `tests/core/` are packages, so modules import as `tests.core.test_core` and do not clash with
the top-level `tests/test_core.py`. Every new `tests/<area>/` needs an `__init__.py`; shared helpers import as
`from tests.<area>.fakes import ...`. Known failures are listed in `tests/known_failures.txt` and run as strict xfail.

## Packaging

- **One distribution** in `pyproject.toml`, still named `railsim` (so Ben's existing editable install upgrades in
  place), now shipping the packages `railsim` and `region`. Runtime dependencies are all core, so `uv sync` and
  `pip install -r requirements.lock -e .` give a working hub; the old `[hub]` extra still exists and still works.
  Dependency groups: `test` (pytest, httpx, hypothesis) and `dev` (test plus ruff), synced by default.
- **`uv.lock`** is universal (`requires-python >=3.12`); every binary wheel it pins has a cp312 `win_amd64` build.
  `requirements.lock` is exported from it with
  `uv export --format requirements.txt --no-hashes --no-emit-project --locked -o requirements.lock`; hashes are left
  out because pip refuses `-e .` beside a hashed file. Re-export after every `uv lock`.
- **`.python-version` is 3.12.** uv found the system 3.12.3 here, so the lock was resolved with 3.12 and a 3.12
  environment was built from it; the suite was also run under the cloud's 3.13 (`pip install -r requirements.lock -e .`).
- **ruff** lints lane-A code only (the old tree is excluded in `pyproject.toml`), with PLW1514 (unspecified encoding)
  on through `preview` with `explicit-preview-rules`. The four files of the 0001 store in `region/model` are excluded
  until WP1 rewrites them; the lead removes those lines then.
- **npm workspaces** `engine` and `app` share the root `package-lock.json`. TypeScript is pinned `~6.0.3` (9.21).
  The root `playwright` devDependency (the old hub's `hub/test_hub.js`) is pinned to `1.63.0`, the same version as the
  app's `@playwright/test`, so there is one Playwright and it uses the Chromium preinstalled here (revision 1243). On
  Ben's machine the old hub test needs `npx playwright install chromium` once after this change, as `hub/README.md`
  already says.
- **Biome** checks `engine/**` and `app/**` (not the generated `engine/schema`, `app/src/api/gen`, `app/dist`).
- **Launchers.** `crhub.cmd` (CRLF; `.gitattributes` keeps it CRLF) and `crhub` (sh, executable) set `PYTHONUTF8=1`
  and run `uv run --locked --project <repo> python -m region`, or `.venv`'s Python when uv is absent. On this cloud
  machine the repo's `.venv` is a copy of Ben's Windows venv and is not usable here; set `UV_PROJECT_ENVIRONMENT` to a
  scratch folder before running `./crhub` so uv does not replace it.
