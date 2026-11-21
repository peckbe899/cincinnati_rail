// Property tests of the plan path helpers (src/geom/path.ts) against the Profiles page's own code.

import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { cumulativeLength, type PathPoint, pathAt } from "../src/index.ts";

const clamp = (v: number, a: number, b: number): number => Math.max(a, Math.min(b, v));

/** pathAt exactly as profiles.html 617 writes it: a linear scan from the start. */
function pathAtScan(path: readonly PathPoint[], c: number): [number, number] {
  let j = 1;
  while (j < path.length - 1 && (path[j] as PathPoint)[0] < c) j++;
  const a = path[j - 1] as PathPoint;
  const b = path[j] as PathPoint;
  const t = b[0] - a[0] > 0 ? clamp((c - a[0]) / (b[0] - a[0]), 0, 1) : 0;
  return [a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

const coord = fc.double({ min: -1e4, max: 1e4, noNaN: true, noDefaultInfinity: true });
// chainages that never decrease, with repeats (zero-length segments occur in the line files' joins)
const path = fc
  .array(fc.tuple(fc.oneof(fc.constant(0), fc.double({ min: 0, max: 500, noNaN: true })), coord, coord), {
    minLength: 2,
    maxLength: 60,
  })
  .map((pts) => {
    let c = 0;
    return pts.map(([dc, x, y]) => {
      c += dc;
      return [c, x, y] as PathPoint;
    });
  });

describe("geom/path", () => {
  test("pathAt by bisect equals linear scan", () => {
    fc.assert(
      fc.property(path, fc.double({ min: -100, max: 40000, noNaN: true }), (p, c) => {
        expect(pathAt(p, c)).toEqual(pathAtScan(p, c));
      }),
      { numRuns: 2000 },
    );
  });

  test("pathAt by bisect equals linear scan at every vertex chainage", () => {
    fc.assert(
      fc.property(path, (p) => {
        for (const [c] of p) expect(pathAt(p, c)).toEqual(pathAtScan(p, c));
      }),
    );
  });

  test("cumulative length starts at 0 and adds segment lengths", () => {
    const L = cumulativeLength([
      [0, 0],
      [3, 4],
      [3, 4],
      [6, 8],
    ]);
    expect(Array.from(L)).toEqual([0, 5, 5, 10]);
  });
});
