// P4 on P1's own type solve (claude/hub_maps/engine_port_plan.md, section 5.5: "the tests run both and must agree"):
// the model with P1's solveTypes laid in and P1's TYPES_MODULE give the same outputs as the golden-fed run
// (goldenTypes on the old page's own solve), on all 16 Metro lines.

import { describe, expect, test } from "vitest";
import { solveTypes, TYPES_MODULE } from "../../../src/port/structure/index.ts";
import type { TypedModel } from "../../../src/port/types.ts";
import { fromGolden, METRO_LINES, typedFromGolden } from "../from_golden.ts";
import { classes, classify } from "../report.ts";
import { compareLine, runLine } from "./compare.ts";

describe("P4 on P1's solve and TYPES_MODULE", () => {
  const list = classes();
  test.each(METRO_LINES)("%s: the same outputs as on the old page's solve", (line) => {
    const { model } = fromGolden(line);
    const golden = typedFromGolden(line);
    const m: TypedModel = { ...model, types: solveTypes(model), spans: golden.spans };
    const p1 = runLine(line, m, TYPES_MODULE);
    const unexplained = p1.results
      .map((r) => classify("checks", line, r, list))
      .filter((r) => r.class === "unexplained");
    expect(unexplained.map((r) => ({ output: r.output, first: r.differences.slice(0, 2) }))).toEqual([]);
    const g = compareLine(line);
    expect(p1.summary).toEqual(g.summary);
    // the findings agree but for the solve's own: P1's carry their slugs where the golden adapter has "page"
    const strip = (fs: typeof g.issues) => fs.map((f) => [f.page, f.sev, f.c0, f.c1, f.c]);
    expect(strip(p1.issues)).toEqual(strip(g.issues));
  });
});
