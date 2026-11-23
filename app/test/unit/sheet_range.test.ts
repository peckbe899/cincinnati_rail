// The level range at the whole-line view takes in what the old page's did (yRangeFor 2286-2297; profiles_parity.md
// R21): the ground, the rail, and (levelExtent) the deepest structure under and over each bend point and platform
// end, the river from the pool, the crossing lines' boxes and the context's structures, so no outline's bottom is
// clipped. Checked against the old page's own range on the 13 lines with saved levels (the parity prove of 23
// November: old_c.json, yr at the whole line); Lines 10, 11 and 13 have no saved levels (the old page solved them).

import type { SolvedSection } from "@cr/engine/contract";
import { describe, expect, it } from "vitest";
import { solveSection } from "../../../engine/src/port/model.ts";
import { inputJson, solvedJson } from "../../../engine/src/port/wire.ts";
import { integrationInput } from "../../../engine/test/port/integration_input.ts";
import { levelExtent } from "../../src/plugins/line-sheet/solved.ts";

/** The old page's level range at the whole line (ymin, ymax), from the prove. */
const OLD: Record<string, [number, number]> = {
  Line_6: [103.72, 299.18],
  Line_3: [106.224, 276.976],
  Line_1: [112.427, 289.728],
  Line_2: [108.12, 268.78],
  Line_2b: [121.203, 264.159],
  Line_4: [112.175, 297.265],
  Line_5: [104.808, 290.292],
  Line_7: [112.488, 293.912],
  Line_8: [100.456, 282.344],
  Line_9: [137.096, 292.734],
  Line_12: [126.416, 276.984],
  Line_14: [120.872, 282.228],
  CVG_Express: [111.54, 293.66],
};

describe("the level range takes in the structures under the bend points and the crossing lines' boxes", () => {
  for (const [line, [ymin, ymax]] of Object.entries(OLD)) {
    it(`${line}: the old page's range at the whole line`, () => {
      const inp = integrationInput(line);
      const out = solveSection(inp) as ReturnType<typeof solveSection> & {
        model?: { rail?: { design: { dv: readonly { c: number; z: number }[] }; z: Float64Array } };
      };
      const solved = solvedJson(inp, out) as unknown as SolvedSection;
      const rail = out.model?.rail ?? (out as unknown as { rail: NonNullable<typeof out.model>["rail"] }).rail;
      const L = inp.length;
      // the ground as the old range read it (groundIdx 712: the bed in a river, else the finished ground) and the
      // rail at the view's ends
      let lo = Number.POSITIVE_INFINITY;
      let hi = Number.NEGATIVE_INFINITY;
      const bed = solved.ground.bed;
      solved.ground.finished.forEach((g, i) => {
        const z = bed[i] ?? g;
        if (z != null && Number.isFinite(z)) [lo, hi] = [Math.min(lo, z), Math.max(hi, z)];
      });
      const rz = rail?.z as Float64Array;
      for (const z of [rz[0] as number, rz[rz.length - 1] as number]) [lo, hi] = [Math.min(lo, z), Math.max(hi, z)];
      // the design's vertices as vertical.rail@1 hands them to the sheet (dv: c_m, z_m)
      const dv = (rail?.design.dv ?? []).map((v) => ({ c_m: v.c, z_m: v.z }));
      const ext = levelExtent({ dv, solved, solveInput: inputJson(inp) }, 0, L);
      expect(ext).not.toBeNull();
      lo = Math.min(lo, ext?.lo ?? lo);
      hi = Math.max(hi, ext?.hi ?? hi);
      const pad = Math.max(3, (hi - lo) * 0.08);
      expect(lo - pad).toBeCloseTo(ymin, 1);
      expect(hi + pad).toBeCloseTo(ymax, 1);
    });
  }
});
