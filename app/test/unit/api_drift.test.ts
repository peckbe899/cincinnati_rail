// The generated API types match region/api/openapi.json (decision 9.21). The server (WP2) writes that file; until
// it exists there is nothing to compare and this test is skipped. Once it exists, a stale src/api/gen fails here:
// run `npm run gen:api -w app` and commit src/api/gen.

import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { GEN, generate, SPEC } from "../../scripts/gen_api.ts";

const SMALL = fileURLToPath(new URL("./fixtures/openapi_small.json", import.meta.url));

const tsFiles = (dir: string) =>
  existsSync(dir)
    ? readdirSync(dir)
        .filter((f) => f.endsWith(".ts"))
        .sort()
    : [];

describe.skipIf(!existsSync(SPEC))("API types", () => {
  it("src/api/gen matches a fresh generation from region/api/openapi.json", async () => {
    const out = mkdtempSync(join(tmpdir(), "cr-gen-"));
    try {
      await generate(SPEC, out);
      const fresh = tsFiles(out);
      expect(fresh.length).toBeGreaterThan(0);
      expect(tsFiles(GEN)).toEqual(fresh);
      for (const f of fresh) expect(readFileSync(join(GEN, f), "utf-8")).toBe(readFileSync(join(out, f), "utf-8"));
    } finally {
      rmSync(out, { recursive: true, force: true });
    }
  }, 60_000);
});

describe("API type generation", () => {
  it("generates types only, the same bytes twice, from a small OpenAPI file", async () => {
    const a = mkdtempSync(join(tmpdir(), "cr-gen-a-"));
    const b = mkdtempSync(join(tmpdir(), "cr-gen-b-"));
    try {
      await generate(SMALL, a);
      await generate(SMALL, b);
      expect(tsFiles(a)).toEqual(["index.ts", "types.gen.ts"]);
      for (const f of tsFiles(a)) expect(readFileSync(join(a, f), "utf-8")).toBe(readFileSync(join(b, f), "utf-8"));
      const types = readFileSync(join(a, "types.gen.ts"), "utf-8");
      expect(types).toContain("export type Health = {");
      // Types only: no client code, no fetch.
      expect(types).not.toMatch(/fetch\(/);
    } finally {
      rmSync(a, { recursive: true, force: true });
      rmSync(b, { recursive: true, force: true });
    }
  }, 60_000);
});
