// Generate the API types in app/src/api/gen from region/api/openapi.json (FastAPI's committed OpenAPI, WP2) with
// @hey-api/openapi-ts, types only (decision 9.21). Run: npm run gen:api -w app, then commit src/api/gen.
// Until openapi.json exists this prints a note and changes nothing. test/unit/api_drift.test.ts regenerates into a
// temporary folder and compares, so a stale src/api/gen fails the unit tests once the file exists.

import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
export const APP = resolve(here, "..");
export const SPEC = resolve(APP, "../region/api/openapi.json");
export const GEN = resolve(APP, "src/api/gen");

/** Write the generated types for spec into out (a folder; replaced whole). */
export async function generate(spec: string = SPEC, out: string = GEN): Promise<void> {
  const { createClient } = await import("@hey-api/openapi-ts");
  await createClient({
    input: spec,
    output: { path: out, clean: true },
    plugins: ["@hey-api/typescript"],
    logs: { level: "silent", file: false },
  } as Parameters<typeof createClient>[0]);
}

const same = (a: string, b: string) => (process.platform === "win32" ? a.toLowerCase() === b.toLowerCase() : a === b);
const isMain = process.argv[1] !== undefined && same(resolve(process.argv[1]), fileURLToPath(import.meta.url));
if (isMain) {
  if (!existsSync(SPEC)) {
    console.log(`gen:api: ${SPEC} does not exist yet (WP2 writes it); src/api/gen left as it is.`);
  } else {
    await generate();
    console.log(`gen:api: wrote ${GEN} from ${SPEC}`);
  }
}
