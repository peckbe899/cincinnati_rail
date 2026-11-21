// Config for `npm run gen:api -w app` (the openapi-ts CLI): the same settings as scripts/gen_api.ts, which the drift
// test uses. Types only, from FastAPI's committed region/api/openapi.json (decision 9.21).

import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "../region/api/openapi.json",
  output: { path: "src/api/gen", clean: true },
  plugins: ["@hey-api/typescript"],
  logs: { level: "silent", file: false },
});
