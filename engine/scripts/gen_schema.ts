// Export engine contract v0 (zod, src/contract) to JSON Schema 2020-12 files in schema/v0/.
//
//   node engine/scripts/gen_schema.ts          (or: npm run gen:schema)
//
// The files are committed. engine/test/contract.test.ts regenerates them in memory and fails on any difference, so
// a contract change without a regenerated schema cannot land. Output is deterministic: two-space JSON, LF, a final
// newline, the same bytes on every platform.

import { mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { z } from "zod";
import { CONTRACTS, SCHEMA_VERSION, SCHEMAS } from "../src/contract/index.ts";

export const SCHEMA_DIR = new URL(`../schema/${SCHEMA_VERSION}/`, import.meta.url);
const ID_BASE = `https://cincinnati-rail.invalid/engine/schema/${SCHEMA_VERSION}/`;

function text(value: unknown): string {
  return `${JSON.stringify(value, null, 2)}\n`;
}

/** Every file of schema/v0 as it should be: file name to content. */
export function generate(): Map<string, string> {
  const out = new Map<string, string>();
  for (const [name, schema] of Object.entries(SCHEMAS)) {
    const { $schema, ...rest } = z.toJSONSchema(schema, { target: "draft-2020-12", unrepresentable: "throw" });
    out.set(`${name}.json`, text({ $schema, $id: `${ID_BASE}${name}.json`, ...rest }));
  }
  out.set(
    "contracts.json",
    text({
      about: "The contract majors of this engine build and the schema file of each message. Generated.",
      contracts: CONTRACTS,
      schemas: Object.keys(SCHEMAS).map((name) => `${name}.json`),
    }),
  );
  return out;
}

/** Write the files and delete any stale .json in the folder. Returns the names written. */
export function write(dir: URL = SCHEMA_DIR): string[] {
  const files = generate();
  mkdirSync(dir, { recursive: true });
  for (const old of readdirSync(dir)) {
    if (old.endsWith(".json") && !files.has(old)) rmSync(new URL(old, dir));
  }
  for (const [name, content] of files) writeFileSync(new URL(name, dir), content, "utf8");
  return [...files.keys()];
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  const names = write();
  console.log(`wrote ${names.length} files to ${fileURLToPath(SCHEMA_DIR)}`);
}
