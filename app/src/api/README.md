# The API transport and its types

- `client.ts`: the transport (`Api`), with the ETag, If-Match and problem handling of section 5.
- `stream.ts`, `events.ts`, `events.worker.ts`, `relay.ts`, `sse.ts`: the SSE client, shared between tabs through a
  SharedWorker.
- `types.ts` and `normalise.ts`: the hand-written shapes the app reads, and the normalising of the containers the
  server may use.
- `gen/`: the generated types (below).

## Generated API types (`gen/`)

`gen/` holds the TypeScript types that `@hey-api/openapi-ts` generates from `region/api/openapi.json` (FastAPI's
committed OpenAPI). Do not edit it by hand. After the server's routes change:

1. `python -m region.api.openapi --write` (rewrites `region/api/openapi.json`);
2. `npm run gen:api -w app` (rewrites `gen/`);
3. commit both.

Generation replaces the whole `gen/` folder, so nothing hand-written may live there: this note is kept here for that
reason. The drift test `test/unit/api_drift.test.ts` fails when `gen/` differs from a fresh generation, file for
file.
