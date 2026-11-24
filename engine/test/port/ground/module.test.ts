// GROUND_MODULE (P2 on P1's own type solve) and groundModule(goldenTypes) (P2 on the old page's solve) agree on every
// Metro line (plan section 5.5: the packages' tests run both and must agree), and both answer the module's lookups
// as the page does at every sample and between samples.

import { describe, expect, test } from "vitest";
import {
  applyLocks,
  buildCanon,
  GROUND_MODULE,
  groundModule,
  rebuildGround,
  riverIndex,
  riverModels,
  sunkBox,
} from "../../../src/port/ground/index.ts";
import { solveTypes } from "../../../src/port/structure/index.ts";
import type { AlignDeps, TypedModel } from "../../../src/port/types.ts";
import { goldenTypes, METRO_LINES, typedFromGolden } from "../from_golden.ts";
import { buildP2 } from "./compare.ts";

describe("GROUND_MODULE and groundModule(goldenTypes) agree", () => {
  test.each(METRO_LINES)("%s", (line) => {
    const { model: m, dump } = buildP2(line);
    const own = solveTypes(m);
    const page = typedFromGolden(line).types;
    const G = groundModule(goldenTypes(dump));
    const P = GROUND_MODULE;
    expect(P.viaductSpans(m, own)).toEqual(G.viaductSpans(m, page));
    const tp: TypedModel = { ...m, types: own, spans: [] };
    const tg: TypedModel = { ...m, types: page, spans: [] };
    for (let i = 0; i < m.grid.n; i += 5) {
      const c = m.grid.c[i] as number;
      const z = m.rail.z[i] as number;
      const a = P.madeBedAt(tp, c, z);
      const b = G.madeBedAt(tg, c, z);
      expect(Number.isNaN(a) ? Number.NaN : a, `madeBedAt ${c}`).toEqual(Number.isNaN(b) ? Number.NaN : b);
      for (const q of [c, c + 0.9]) {
        expect(P.riverIndex(m, q)).toBe(riverIndex(m.rivers, q));
        expect(P.canonAt(m, q)).toBe(G.canonAt(m, q));
        expect(P.lockAt(m, q)).toBe(G.lockAt(m, q));
        expect(P.sampleGround(m.ground.finished, m.grid.step, q)).toBe(
          G.sampleGround(m.ground.finished, m.grid.step, q),
        );
      }
      expect(m.riverAt[i]).toBe(riverIndex(m.rivers, c));
      const k = m.canon.sectionAt[i] as number;
      expect(k >= 0 ? m.canon.sections[k] : null).toBe(P.canonAt(m, c));
      const l = m.canon.lockAt[i] as number;
      expect(l >= 0 ? m.canon.locks[l] : null).toBe(P.lockAt(m, c));
    }
  });
});

test("P2's functions are the AlignDeps P4's alignFromDoc takes (plan section 5.4)", () => {
  const deps: Omit<AlignDeps, "sttFromDoc"> = { buildCanon, rebuildGround, riverModels, sunkBox, applyLocks };
  expect(Object.keys(deps)).toHaveLength(5);
});
