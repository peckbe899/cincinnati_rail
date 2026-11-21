// The rail level and grade at any chainage (the ports of railAt and gradeAt, profiles.html 803-826), and railGrid:
// both on a regular grid in one merge sweep.
//
// railAt finds the design vertices on either side of c by bisection, then reads the parabola of a curve at either
// of them, else the straight grade between them. The design vertices never decrease in chainage, so the pair the
// bisection finds is the last vertex at or before c and the one after it; railGrid walks that pair forward once
// over the grid instead of bisecting at every point, and evaluates each point with the same function, so the grid
// holds exactly the values railAt gives.

import { gridChainage, gridSize } from "../grid.ts";
import { CHORD_MIN_M, CURVE_MIN_M, PERMILLE } from "../tol.ts";
import type { Design, DesignVertex } from "./design.ts";

const vx = (d: Design, k: number): DesignVertex => d.dv[k] as DesignVertex;

/** The bracketing pair (lo, hi = lo + 1) of c, for c strictly inside the design's span. */
function bracket(d: Design, c: number): number {
  let lo = 0;
  let hi = d.dv.length - 1;
  while (hi - lo > 1) {
    const m = (lo + hi) >> 1;
    if (vx(d, m).c <= c) lo = m;
    else hi = m;
  }
  return lo;
}

/** The curve index (lo or hi) whose parabola holds c, or -1. */
function curveAt(d: Design, lo: number, c: number): number {
  for (const k of [lo, lo + 1]) {
    const Lk = d.L[k] as number;
    if (Lk > CURVE_MIN_M && Math.abs(c - vx(d, k).c) < Lk / 2) return k;
  }
  return -1;
}

function railIn(d: Design, lo: number, c: number): number {
  const k = curveAt(d, lo, c);
  if (k >= 0) {
    const Lk = d.L[k] as number;
    const g1 = d.g[k - 1] as number;
    const g2 = d.g[k] as number;
    const x = c - (vx(d, k).c - Lk / 2);
    return vx(d, k).z - (g1 * Lk) / 2 + g1 * x + ((g2 - g1) * x * x) / (2 * Lk);
  }
  const a = vx(d, lo);
  const b = vx(d, lo + 1);
  const span = b.c - a.c;
  return span <= CHORD_MIN_M ? b.z : a.z + ((b.z - a.z) * (c - a.c)) / span;
}

function gradeIn(d: Design, lo: number, c: number): number {
  const k = curveAt(d, lo, c);
  if (k >= 0) {
    const Lk = d.L[k] as number;
    const g1 = d.g[k - 1] as number;
    const g2 = d.g[k] as number;
    const x = c - (vx(d, k).c - Lk / 2);
    return (g1 + ((g2 - g1) * x) / Lk) * PERMILLE;
  }
  return (d.g[lo] as number) * PERMILLE;
}

/** Rail level at chainage c; held level beyond the ends. */
export function railAt(d: Design, c: number): number {
  const hi = d.dv.length - 1;
  if (c <= vx(d, 0).c) return vx(d, 0).z;
  if (c >= vx(d, hi).c) return vx(d, hi).z;
  return railIn(d, bracket(d, c), c);
}

/** Grade in per mille at chainage c (rising with chainage); 0 at and beyond the ends. */
export function gradeAt(d: Design, c: number): number {
  const hi = d.dv.length - 1;
  if (c <= vx(d, 0).c || c >= vx(d, hi).c) return 0;
  return gradeIn(d, bracket(d, c), c);
}

/** True when the design vertices never decrease in chainage (what the merge sweep relies on). */
export function monotone(d: Design): boolean {
  for (let k = 1; k < d.dv.length; k++) if (vx(d, k).c < vx(d, k - 1).c) return false;
  return true;
}

export interface RailGrid {
  readonly n: number;
  readonly step: number;
  readonly c: Float64Array;
  readonly rail: Float64Array;
  readonly grade: Float64Array;
}

/**
 * Rail and grade at c_i = min(i * step, length) for i in 0 .. floor(length / step), by one merge sweep over the
 * design vertices. Equal to railAt and gradeAt at every point (test/golden.vertical.test.ts checks it on every
 * route); a design whose vertices are out of order falls back to bisection.
 */
export function railGrid(d: Design, length: number, step: number): RailGrid {
  const n = gridSize(length, step);
  const c = new Float64Array(n);
  const rail = new Float64Array(n);
  const grade = new Float64Array(n);
  const last = d.dv.length - 1;
  const c0 = vx(d, 0).c;
  const c1 = vx(d, last).c;
  const sweep = monotone(d);
  let lo = 0;
  for (let i = 0; i < n; i++) {
    const ci = gridChainage(i, step, length);
    c[i] = ci;
    if (ci <= c0 || ci >= c1) {
      rail[i] = ci <= c0 ? vx(d, 0).z : vx(d, last).z;
      grade[i] = 0;
      continue;
    }
    if (sweep) {
      while (lo + 1 < last && vx(d, lo + 1).c <= ci) lo++;
    } else lo = bracket(d, ci);
    rail[i] = railIn(d, lo, ci);
    grade[i] = gradeIn(d, lo, ci);
  }
  return { n, step, c, rail, grade };
}
