// The built rail: vertical curves at every change of grade, kept off the platforms (the port of design,
// profiles.html 750-802).
//
// Curves are parabolic, half each side of the bend, of length radius x change of grade but never shorter than the
// minimum. Curves never run onto a platform: the platform level runs on past each platform end by half the curve
// length (the transition, a vertex of kind "x"), then the curve, then the grade. Where the straight grade is too
// short the curves are shortened, and the shortfall is listed in `short`.

import {
  CHORD_MIN_M,
  DESIGN_PASSES,
  EXT_MIN_M,
  GRADE_CHANGE_MIN,
  OUTWARD_MIN_M,
  PERMILLE,
  RUN_MIN_M,
  SHORT_FLAG_M,
  TRANSITION_SHARE,
} from "../tol.ts";
import type { Vertex, Vertices } from "./vertices.ts";

/** A vertex of the built line: the design vertices plus "x", the end of a platform's transition. */
export interface DesignVertex {
  readonly c: number;
  readonly z: number;
  readonly kind: Vertex["kind"] | "x";
  /** As Vertex.i; for "x", the station whose transition it ends. */
  readonly i: number;
}

/** A curve the straight grades were too short for. */
export interface ShortCurve {
  readonly c: number;
  /** The curve length the bend needs. */
  readonly need: number;
  /** The length that fits. */
  readonly got: number;
  /** The change of grade in per mille. */
  readonly dgPermille: number;
}

export interface Design {
  /** The built line's vertices, chainage not decreasing. */
  readonly dv: readonly DesignVertex[];
  /** g[k] is the grade (a ratio) from dv[k] to dv[k + 1]. */
  readonly g: readonly number[];
  /** L[k] is the vertical curve length at dv[k] (0 for none). */
  readonly L: readonly number[];
  readonly short: readonly ShortCurve[];
}

export function design(verts: Vertices): Design {
  const { rv, lmin } = verts;
  const V = verts.v;
  // curve length for a change of grade dg: radius x dg, but never shorter than the minimum (AREMA / Amtrak 100 ft),
  // so small bends are rounded too
  const curveLen = (dg: number): number => (Math.abs(dg) > GRADE_CHANGE_MIN ? Math.max(rv * Math.abs(dg), lmin) : 0);
  const n = V.length;
  const at = (k: number): Vertex => V[k] as Vertex;
  let ext: number[] = new Array<number>(n).fill(0);
  // the neighbour index beyond a platform end, or -1
  const outward = (k: number): number => {
    const v = at(k);
    if (v.kind === "pe" && k + 1 < n) {
      const w = at(k + 1);
      if (!(w.kind === "ps" && w.i === v.i) && w.c - v.c > OUTWARD_MIN_M) return k + 1;
    }
    if (v.kind === "ps" && k - 1 >= 0) {
      const w = at(k - 1);
      if (!(w.kind === "pe" && w.i === v.i) && v.c - w.c > OUTWARD_MIN_M) return k - 1;
    }
    return -1;
  };
  // level along a platform end's own grade (the transition carries the platform grade on)
  const zOn = (k: number, c: number): number => at(k).z + (at(k).gp || 0) * (c - at(k).c);
  if (rv > 0) {
    for (let it = 0; it < DESIGN_PASSES; it++) {
      const nx: number[] = new Array<number>(n).fill(0);
      for (let k = 0; k < n; k++) {
        const o = outward(k);
        if (o < 0) continue;
        const dir = o > k ? 1 : -1;
        const piv = at(k).c + dir * (ext[k] as number);
        const facing = outward(o) === k;
        const oc = at(o).c - dir * (facing ? (ext[o] as number) : 0);
        const run = Math.abs(oc - piv);
        if (run < RUN_MIN_M) continue;
        const gq = (zOn(o, oc) - zOn(k, piv)) / (oc - piv);
        nx[k] = curveLen(gq - (at(k).gp || 0)) / 2;
      }
      // the two transitions on one stretch take at most half of it
      for (let k = 0; k + 1 < n; k++) {
        const len = at(k + 1).c - at(k).c;
        const a = outward(k) === k + 1 ? (nx[k] as number) : 0;
        const b = outward(k + 1) === k ? (nx[k + 1] as number) : 0;
        if (a + b > TRANSITION_SHARE * len && a + b > 0) {
          const f = (TRANSITION_SHARE * len) / (a + b);
          if (a) nx[k] = (nx[k] as number) * f;
          if (b) nx[k + 1] = (nx[k + 1] as number) * f;
        }
      }
      ext = nx;
    }
  }
  const dv: DesignVertex[] = [];
  V.forEach((v, k) => {
    const e = ext[k] as number;
    if (v.kind === "ps" && e > EXT_MIN_M) {
      dv.push({ c: v.c - e, z: zOn(k, v.c - e), kind: "x", i: v.i });
      dv.push(v);
    } else if (v.kind === "pe" && e > EXT_MIN_M) {
      dv.push(v);
      dv.push({ c: v.c + e, z: zOn(k, v.c + e), kind: "x", i: v.i });
    } else dv.push(v);
  });
  const g: number[] = [];
  for (let k = 0; k + 1 < dv.length; k++) {
    const a = dv[k] as DesignVertex;
    const b = dv[k + 1] as DesignVertex;
    const d = b.c - a.c;
    g.push(d > CHORD_MIN_M ? (b.z - a.z) / d : 0);
  }
  const L: number[] = dv.map(() => 0);
  const need: number[] = dv.map(() => 0);
  if (rv > 0) {
    for (let k = 1; k + 1 < dv.length; k++) {
      const kind = (dv[k] as DesignVertex).kind;
      if (kind === "ps" || kind === "pe" || kind === "end") continue;
      const len = curveLen((g[k] as number) - (g[k - 1] as number));
      need[k] = len;
      L[k] = len;
    }
  }
  for (let k = 0; k + 1 < dv.length; k++) {
    const len = (dv[k + 1] as DesignVertex).c - (dv[k] as DesignVertex).c;
    const a = L[k] as number;
    const b = L[k + 1] as number;
    const h = a / 2 + b / 2;
    if (h > len && h > 0) {
      const f = len / h;
      L[k] = Math.min(a, a * f);
      L[k + 1] = Math.min(b, b * f);
    }
  }
  const short: ShortCurve[] = [];
  dv.forEach((v, k) => {
    const got = L[k] as number;
    const want = need[k] as number;
    if (want - got > SHORT_FLAG_M) {
      short.push({ c: v.c, need: want, got, dgPermille: ((g[k] as number) - (g[k - 1] as number)) * PERMILLE });
    }
  });
  return { dv, g, L, short };
}
