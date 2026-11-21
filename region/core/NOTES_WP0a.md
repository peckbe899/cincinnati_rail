### What later packages must know
- **WP1 (store, kinds, ids):**
  - **Remove the region/model ruff excludes:** the lead must drop the four `region/model/...` lines from `pyproject.toml` `extend-exclude` when WP1 lands.
  - `kinds.load` should call `features.check_kind_file`.
  - Records cross boundaries in the `protocols.Record` get() shape: `geom` is WKT and `hash` is `content_hash({id, kind, kv, geom, data})`.
  - JSON Patch paths are relative to `{data, geom}`. ETags are `'"layer:version"'`.
  - An import layer's namespace is enforced by `ids.namespace_of(id)`: each namespace has a distinct epoch, all before 2020-01-04, so imported ids sort before authored ones.
  - Namespaces `profiles`, `registry`, `old_hub` and `test` are declared. Tests can use `test`, or monkeypatch `region.core.ids.namespaces`.
  - `stable("profiles","Line_6")` is pinned to `01DXF6DT00G2RN476ZR8N14PM3`.
- **Writes:** all go through `fsio.write_atomic`. Tests use the `write_root` or `hub_var` fixtures; `hub_var` sets `CRHUB_VAR`.
- **WP0b (tiers):** `paths` only finds roots (`TierMissing` or `available()`). The missing/partial/present scan, from manifest, index and handshake `{file, done, detail}`, is `region/tiers`. `hub_paths.json` is a list of tiers; `local.json` overrides a root by name.
- **WP4 (engine):**
  - **Lint exemption needed:** the "no numeric literal outside tol.ts" lint must exempt `src/contract/`, which holds contract majors, `c0: 0` and progress bounds.
  - `RuleId` in the contract is the registry's id pattern; `rules.gen.ts` can narrow it.
  - PROTOCOL.md fixes the `engine_build` recipe: files sorted by POSIX path under `engine/`, each fed as `path\n` then its bytes.
  - `input_hash` is sha256 of the RFC 8785 JSON. Python and TS share the vectors in `engine/test/contract.jcs.json`.
  - The CLI replies with `id: 0`. Bad lines get `id: null` and code `bad_request`.
  - `@cr/engine` exports `"."` pointing to `src/index.ts`, which WP4 must create.
- **WP6 (app):** `app/tsconfig.json` includes `src`, `test`, `e2e` and `*.config.ts`. Until `app/src` exists, `tsc -p app` reports no inputs. A probe confirmed that every app dependency and `@cr/engine/contract` resolve.
- **CLI:** each `region/cli/<name>.py` must add a subparser named exactly `<name>`, or it shows as unavailable and the CLI test fails. With no command, `serve` runs once it exists.
- **Tests:** every new `tests/<area>/` needs an `__init__.py`.
- **This machine:**
  - The repo's `.venv` is a copy of Ben's Windows venv. Set `UV_PROJECT_ENVIRONMENT` before running `./crhub`, or uv will replace it. I used a scratch env, and `./crhub info` works through uv.
  - Dependencies were installed into the system Python 3.13 with `pip install -r requirements.lock -e .`. That needed `--ignore-installed pyparsing==3.3.3` first, because of a Debian package. pip warns that the system `conan` wants python-dateutil<3; this is harmless here.
- **Routes:** the section 5 routes stay as written in the spec. No code artifact for them was made in WP0a; WP2's `openapi.json` will be their record.

### Left open, for the lead
- **Possibly missing dependencies.** These are not in `pyproject.toml`, and adding one needs a re-lock:
  - a JSON Patch library such as `jsonpatch`, for WP1's RFC 6902 apply and diff;
  - a pydantic generator such as `datamodel-code-generator`, for WP4's `region/contract/gen`.
- **Writers outside the four write roots.** Anything that generates `region/api/openapi.json` or `region/contract/gen/**` through `fsio` will be refused unless it uses `fsio.allow_writes`.
- **The `.venv` fallback depends on the working folder.** It runs `python -m region`, which finds `region` from the current folder only until Ben reinstalls with `pip install -e .` (his current editable finder maps only `railsim`). Running `.\crhub` from the repo root works either way.
- **Root playwright was moved from 1.64.1 to 1.63.0.** On Ben's machine `hub/test_hub.js` needs `npx playwright install chromium` once after `npm ci`, which `hub/README.md` already says to run.
- **`npm audit`:** 4 high-severity advisories in `js-yaml`, reached through the dev-only `@hey-api/openapi-ts`.
- **Placeholder scripts:** `npm run typecheck -w app` reports no inputs until WP6 creates `app/src`, and `@cr/engine`'s `"."` export points at `src/index.ts`, which WP4 creates.
- **`python-ulid` is a runtime dependency** but only the tests use it.
- **`crhub setup` (WP0b) will remove Ben's extra packages.** It runs `uv sync --locked`, which removes packages the lock does not list from `.venv`; `uv run` does not.


### Lead's notes after WP0a (21 Nov)
- jsonpatch (runtime) and datamodel-code-generator (dev) are now in pyproject.toml, uv.lock and requirements.lock, and installed here.
- Generated files outside the write roots (region/api/openapi.json, region/contract/gen/**, engine/schema) are written by
  generator scripts/tests inside an fsio.allow_writes(...) block for that exact path, never by the running hub.
- crhub setup must not remove Ben's extra packages: use `uv sync --locked --inexact`.
- The repo's .venv in this container is a stale copy of Ben's Windows venv: never let uv or pip modify it here
  (set UV_PROJECT_ENVIRONMENT to a scratch folder if you use uv); the system python3 here has every dependency.
