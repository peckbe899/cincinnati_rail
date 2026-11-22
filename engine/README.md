# @cr/engine

The hub's rules engine (decision 9.20): pure TypeScript that Node runs directly (type stripping, Node 22.18 or later)
in the sidecar and the CLI, and that Vite bundles for the browser worker. The wire protocol is `PROTOCOL.md`; the
contract (zod) is `src/contract/`, exported to `schema/v0/`.

## Layout

| Path | What it holds |
|---|---|
| `src/index.ts` | `solve(method, input, opts)`, `METHODS`, `ENGINE_VERSION`, `hello()`, and the geometry for the app |
| `src/methods.ts` | the method table: name, version, contracts, the rules its flags cite, the function |
| `src/vertical/` | `vertices.ts`, `design.ts`, `rail.ts` (railAt, gradeAt, railGrid): the Profiles page, lines 725 to 828; `method.ts`: vertical.rail@1 |
| `src/geom/path.ts` | cumulative length and pathAt by bisection (the page's line 617) |
| `src/grid.ts`, `src/params.ts` | the output grid; the params under the page's names, with the design rules (transition share, short-curve flag, solver passes) from the input's params when it sends them |
| `src/tol.ts` | every numeric constant, named; the lint allows no other number but 0, 1 and 2. The three design rules here are only the defaults for an input that does not send `params.transition_share`, `short_curve_flag_m` or `design_passes` |
| `src/rules.gen.ts` | the registry's rule ids (generated, committed) |
| `src/host.ts`, `src/serve.ts`, `src/sidecar.ts`, `src/cli.ts`, `src/build.ts` | the NDJSON host, the sidecar loop and entry, the one-shot CLI, engine_build (Node only) |
| `test/fixtures.ts` | the 41 golden inputs, from `tests/baseline/profiles`, the line files and `rules/registry.yaml` |
| `test/golden/` | committed inputs (2 m grid) and output hashes; Python's engine host tests read them too |

## Commands

```sh
npm test                                         # the engine tests (vitest run, from engine/)
npm run typecheck                                # types
npm run gen:schema                               # schema/v0 from the zod contract
npm run gen:rules                                # src/rules.gen.ts from rules/registry.yaml
npm run golden:update -- --rule <id> --note "why"   # accept an output change under a rule id
```

From the repo root add `-w engine` (`npm run golden:update -w engine -- --rule <id>`). Each script is the matching
`node scripts/<name>.ts`, which also works on its own. `golden:update` refuses to run without a rule id of the registry. It never touches `tests/baseline/`, which holds
the Profiles page's own output and is compared within 1 mm by `test/golden.vertical.test.ts`.
