// Station names at the whole-line view (claude/hub_maps/profiles_parity.md, S4, S89): docked or maximised, the sheet
// names at least as many stations as the old page did at the same plot width, by the old page's rule (2770-2786:
// left to right, none within 18 px of the last name drawn), and names both ends of the line.

import { describe, expect, it } from "vitest";
import { fromGolden, METRO_LINES } from "../../../engine/test/port/from_golden.ts";
import { nameGap } from "../../src/plugins/line-sheet/bands.ts";
import { nameLabels } from "../../src/plugins/line-sheet/drawing.ts";

/** The old page's names at a plot width: left to right, 18 px apart (15 when its canvas was under 560 px). */
function oldNames(xs: readonly number[], canvasW: number): number {
  const gap = canvasW < 560 ? 15 : 18;
  let last = Number.NEGATIVE_INFINITY;
  let n = 0;
  for (const x of xs) {
    if (x - last < gap) continue;
    last = x;
    n++;
  }
  return n;
}

describe("names at the whole-line view, docked and maximised", () => {
  // the plot widths of the sheet docked beside the map (about 590 px) and maximised (1,195 px) at 1,600 px, and a
  // narrow dock; the old page's canvas is its plot plus 60 px of axis
  for (const w of [420, 480, 540, 590, 760, 1195]) {
    for (const line of METRO_LINES) {
      it(`${line} at a ${w} px plot`, () => {
        const { dump } = fromGolden(line);
        const L = dump.L;
        const xs = dump.stations.map((s) => 60 + (s.point_c / L) * w);
        const kept = nameLabels(
          xs.map((x) => ({ x })),
          nameGap(w),
        );
        expect(kept.size).toBeGreaterThanOrEqual(oldNames(xs, w + 60));
        expect(kept.has(0)).toBe(true);
        expect(kept.has(xs.length - 1)).toBe(true);
      });
    }
  }
  it("the selected station is always named, and never given up for the line's end", () => {
    const xs = [0, 30, 40, 45].map((x) => ({ x, selected: x === 40 }));
    expect([...nameLabels(xs, 18)].sort()).toEqual([0, 1, 2]);
    // the line's end takes the place of the name before it: as many names, both ends named
    expect(
      [
        ...nameLabels(
          [0, 30, 40, 45].map((x) => ({ x })),
          18,
        ),
      ].sort(),
    ).toEqual([0, 3]);
  });
});
