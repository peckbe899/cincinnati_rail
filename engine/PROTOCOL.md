# The engine protocol: NDJSON over stdio (decision 9.20)

Python talks to the TypeScript engine through `EngineClient` (`region/core/protocols.py`), which has three
implementations in `region/enginehost/client.py`: `Pool` (a pool of long-lived sidecars), `OneShot` (one CLI process
per call) and `Fake` (tests). This file is the contract between them and the engine. The message shapes are zod in
`engine/src/contract/protocol.ts`, exported to `engine/schema/v0/{hello,request,response}.json`.

## Processes

- **Sidecar:** `node engine/src/sidecar.ts`. Node runs the `.ts` source directly (type stripping, `erasableSyntaxOnly`),
  so there is no build step for Node. Node 22.18 or later is required, 24 LTS recommended.
- **CLI:** `node engine/src/cli.ts <method> <input.json>`. It reads the input file, makes one call, writes one reply
  line (the same shape as a sidecar reply, with `"id": 0`) to stdout, and exits 0 when `ok` is true and 1 otherwise.
  `-` as the input reads stdin.
- Python starts both with an argument list, never through a shell, with the repo root as the working directory.

## Framing

- Each message is one JSON object on one line, UTF-8, ended by `\n` (LF, also on Windows). `JSON.stringify` never
  writes a raw newline inside a value, so a line is always a whole message.
- stdout carries protocol lines only. Logs, warnings and stack traces go to stderr; Python keeps the last lines of
  stderr and puts them in the job log when a call fails.
- A sidecar exits when its stdin reaches EOF. Python closes stdin to stop it (Windows does not kill orphans). A sidecar
  never exits on its own otherwise.

## Hello

The first line a sidecar writes, before reading any request:

```json
{"hello":{"engine_version":"0.0.0","engine_build":"<sha256>","contracts":{"section_input":0,"vertical_rail":0},"methods":["vertical.rail@1"]}}
```

- `engine_version` is the `version` of `engine/package.json`.
- `engine_build` is the sha256 of `engine/src/**` and `engine/package.json`: the files sorted by their POSIX path
  relative to `engine/`, and for each one the line `<path>\n` followed by its bytes, all hashed in one stream. Python
  computes the same value from the files (`region/enginehost/build.py`) and a test checks the two agree. It enters
  the cache key of every engine job (9.19).
- `contracts` maps each contract name to its major (`engine/schema/v0/contracts.json`). Python refuses to use an
  engine whose majors it does not know, with `EngineUnavailable(reason="contract")`.
- `methods` lists `name@version` for every method the engine serves.

## Messages

| Direction | Message |
|---|---|
| Request | `{"id":7,"method":"vertical.rail","params":{...}}` |
| Progress | `{"id":7,"progress":0.5,"stage":"design"}` |
| Reply | `{"id":7,"ok":true,"result":{...}}` |
| Error | `{"id":7,"ok":false,"error":{"code":"invalid_input","message":"...","stack":"..."}}` |

- **`id`** is a positive integer chosen by Python, unique among the requests open on one connection. Replies carry
  the id of their request and may arrive in any order; a client must not assume order.
- **`method`** is `name` or `name@version`. A bare name takes the version the hello lists; a version the engine does
  not serve is `unknown_method`.
- **`params`** is the method's input contract (`SectionInput` for `vertical.rail`). The engine validates it with zod
  and answers `invalid_input` (with zod's `issues`) when it fails.
- **Progress** lines are optional. `progress` runs from 0 to 1. The engine keeps no clock, so it thins them by
  amount instead of time: a line goes out only when progress has moved by at least 0.05 since the last one for
  that request, or reaches 1 (`PROGRESS_STEP` in `src/tol.ts`).
- **Error codes:** `bad_request` (the line is not a JSON request; `id` is `null` when it could not be read),
  `unknown_method`, `invalid_input`, `internal` (the method threw; `stack` holds the trace). Python raises
  `EngineError` with the code.
- There is no cancel message. To cancel or time out, Python kills the process and starts a new one (with backoff);
  the open request fails with `EngineUnavailable(reason="timeout")` or `("crashed")`.

## Methods

| Method | Params | Result | Rules its flags cite |
|---|---|---|---|
| `vertical.rail@1` | `SectionInput` v0 | `VerticalRail` v0 | `era.vertical_curve.radius_and_min_length`, `platform.length.by_system`, `network.level_solver.shallow_as_grade_allows` |
| `engine.echo@1` | anything | the params, unchanged | none |

`engine.echo` is a health check and the probe of the round-trip budget (section 6: under 5 ms warm). The method table
is `engine/src/methods.ts`; the sidecar, the CLI and the browser worker all serve it.

## Results

- Methods are pure: the same params give the same bytes, on every run and platform. Engine source uses no `Date`,
  `Math.random` or `performance`, and every numeric tolerance lives in `engine/src/tol.ts`.
- Every output contract carries `engine_build` and `input_hash`. `input_hash` is the sha256 hex of the RFC 8785
  (JCS) canonical JSON of `params`: keys sorted by UTF-16 code units, no whitespace, numbers as `JSON.stringify`
  writes them. `engine/src/contract/common.ts` `canonicalJson` and `region/core/fsio.py` `canonical_json` give the
  same bytes; `engine/test/contract.jcs.json` holds the vectors both test against.
- In the browser, `solve(method, params, { engineBuild })` takes `engine_build` from the server's hello (a bundle
  cannot hash its own source); without it outputs carry 64 zeros, which no real build hashes to.
- Numbers are plain JSON numbers. Arrays are on the grid the output declares (`grid.c0`, `grid.step_m`, `grid.n`).
  Binary frames come in only if a budget test fails (9.20).

## Versions

- A method's version (`vertical.rail@1`) rises whenever its outputs change meaning; a contract's major (`v0`) rises
  whenever its shape changes incompatibly, with a new folder `engine/schema/v<major>/`.
- `node engine/scripts/gen_schema.ts` regenerates `engine/schema/v0/*.json` from the zod source; the vitest "schemas
  regenerate with no diff" fails on a stale file.
