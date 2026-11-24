// Shared helpers of the port (claude/hub_maps/engine_port_plan.md, section 5.0): written by P1, read by every
// package. Each is the page's own helper (data/profile/profiles.html, line in the comment), pure, or a small coded
// array helper the port's outputs travel in.

import { gridChainage, gridSize } from "../grid.ts";
import type { CodedArray, Grid, Range3 } from "./types.ts";

/** clamp (602). */
export const clamp = (v: number, a: number, b: number): number => Math.max(a, Math.min(b, v));

/** The ranges [i0, i1] of consecutive indexes in [a, b] where pred(item, i) holds (rangesOf, 613). */
export function rangesOf<T>(
  arr: readonly T[],
  a: number,
  b: number,
  pred: (x: T, i: number) => boolean,
): [number, number][] {
  const out: [number, number][] = [];
  let s = -1;
  for (let i = a; i <= b + 1; i++) {
    const on = i <= b && pred(arr[i] as T, i);
    if (on && s < 0) s = i;
    if (!on && s >= 0) {
      out.push([s, i - 1]);
      s = -1;
    }
  }
  return out;
}

/** A list of [c0, c1, kind] with [a, b] cut out of it (cutRange, 615). */
export function cutRange<T extends string>(list: readonly Range3<T>[], a: number, b: number): Range3<T>[] {
  const out: Range3<T>[] = [];
  for (const o of list) {
    if (o[1] <= a || o[0] >= b) {
      out.push(o);
      continue;
    }
    if (o[0] < a) out.push([o[0], a, o[2]]);
    if (o[1] > b) out.push([b, o[1], o[2]]);
  }
  return out;
}

/** Values as codes into a table (the table in first-seen order unless one is given; a value not in a given table is
 * added to its end). */
export function codes<T>(table: readonly T[], values: readonly T[]): CodedArray<T> {
  const t = table.slice();
  const at = new Map<T, number>(t.map((v, k) => [v, k]));
  const out = new Uint8Array(values.length);
  values.forEach((v, i) => {
    let k = at.get(v);
    if (k === undefined) {
      k = t.length;
      t.push(v);
      at.set(v, k);
    }
    out[i] = k;
  });
  return { table: t, codes: out };
}

/** The value of sample i. */
export function valueAt<T>(a: CodedArray<T>, i: number): T {
  return a.table[a.codes[i] as number] as T;
}

/** The runs of a coded array: [value, i0, i1] (for the band and the outlines). */
export function runs<T>(a: CodedArray<T>): [T, number, number][] {
  const out: [T, number, number][] = [];
  const n = a.codes.length;
  let s = 0;
  for (let i = 1; i <= n; i++) {
    if (i === n || a.codes[i] !== a.codes[s]) {
      out.push([valueAt(a, s), s, i - 1]);
      s = i;
    }
  }
  return out;
}

/** The grid of a section: n = floor(L / step) + 1 points at c_i = min(i * step, L) (src/grid.ts). */
export function gridOf(length: number, step: number): Grid {
  const n = gridSize(length, step);
  const c = new Float64Array(n);
  for (let i = 0; i < n; i++) c[i] = gridChainage(i, step, length);
  return { n, step, length, c };
}

/** Math.round(c / step) held to the grid, as autoType and drivenTube read the solve (JS rounds halves up). */
export function nearestIndex(g: Grid, c: number): number {
  return clamp(Math.round(c / g.step), 0, g.n - 1);
}
