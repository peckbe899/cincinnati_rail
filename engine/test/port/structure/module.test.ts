// TYPES_MODULE on the port's own solve and goldenTypes (the old page's solve laid in) agree at every sample and
// between samples (plan section 5.5: the other packages' tests run both and must agree), and the module answers
// off the grid as the page does: typeAt within autoTypeRailTol of the solved rail reads the solve, else the point.

import { describe, expect, test } from "vitest";
import { solveTypes, TYPES_MODULE } from "../../../src/port/structure/index.ts";
import type { Type, TypedModel } from "../../../src/port/types.ts";
import { fromGolden, goldenTypes, METRO_LINES } from "../from_golden.ts";

describe("TYPES_MODULE and goldenTypes agree", () => {
  test.each(METRO_LINES)("%s", (line) => {
    const { dump, model } = fromGolden(line);
    const port: TypedModel = { ...model, types: solveTypes(model), spans: [] };
    const G = goldenTypes(dump);
    const T = TYPES_MODULE;
    const { n } = model.grid;
    let checked = 0;
    for (let i = 0; i < n; i += 3) {
      for (const c of [model.grid.c[i] as number, (model.grid.c[i] as number) + 0.7]) {
        if (c > model.grid.length) continue;
        const z = model.rail.z[i] as number;
        expect(T.typeAt(port, c), `typeAt ${c}`).toBe(G.typeAt(model as TypedModel, c));
        expect(T.typeAt(port, c, z + 1)).toBe(G.typeAt(model as TypedModel, c, z + 1));
        expect(T.tubeKeyAt(port, c)).toBe(G.tubeKeyAt(model as TypedModel, c));
        const t = T.typeAt(port, c) as Type;
        expect(T.structFor(port, t, c)).toEqual(G.structFor(model, t, c));
        expect(T.gradeLimitAt(port, c)).toEqual(G.gradeLimitAt(model as TypedModel, c));
        expect(T.phaseAt(port, c)).toBe(G.phaseAt(model, c));
        checked++;
      }
    }
    expect(checked).toBeGreaterThan(n / 2);
  });
});
