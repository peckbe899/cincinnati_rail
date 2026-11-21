// vertical.rail@1 gives the committed bytes (engine/test/golden/vertical_rail.json) for the committed inputs
// (engine/test/golden/inputs/). A change of either is accepted only through scripts/golden_update.ts with a rule id.

import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";
import type { SectionInput } from "../src/contract/index.ts";
import { isRuleId } from "../src/index.ts";
import { ROUTES } from "./fixtures.ts";
import { committed, current, goldenOf, inputFile } from "./golden_files.ts";

const STALE = "run node engine/scripts/golden_update.ts --rule <rule id> --note <why>";

describe("golden bytes", () => {
  test("the committed inputs are the fixtures, and the outputs hash as committed", async () => {
    const golden = committed();
    expect(golden, "engine/test/golden/vertical_rail.json is missing").not.toBeNull();
    const now = await current();
    for (const route of ROUTES) {
      const input = JSON.parse(readFileSync(inputFile(route), "utf8")) as SectionInput;
      expect(input, `${route}: the golden input is stale: ${STALE}`).toEqual(now.inputs.get(route));
      expect(await goldenOf(input), `${route}: the output changed: ${STALE}`).toEqual(golden?.routes[route]);
    }
    expect(Object.keys(golden?.routes ?? {}).sort()).toEqual([...ROUTES]);
    for (const change of golden?.changes ?? []) expect(isRuleId(change.rule), change.rule).toBe(true);
  });

  test("golden:update refuses to run without a rule id", () => {
    const script = fileURLToPath(new URL("../scripts/golden_update.ts", import.meta.url));
    const none = spawnSync(process.execPath, [script], { encoding: "utf8" });
    expect(none.status).toBe(2);
    expect(none.stderr).toMatch(/refused/);
    const bogus = spawnSync(process.execPath, [script, "--rule", "no.such.rule"], { encoding: "utf8" });
    expect(bogus.status).toBe(2);
    expect(bogus.stderr).toMatch(/not a rule id/);
  });
});
