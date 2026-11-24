// The finished ground of a section on its 2 m grid, as the Profiles page builds it (profiles.html 636-700): the
// surveyed ground, the Deck's street re-grades added (add) and open cuts held (cap), then the other lines' drawn
// ground across their streets and this profile's own drawn ground lines (gnd).

import type { StationInput } from "../contract/index.ts";
import { CM_PER_M, SPAN_MIN_M } from "../tol.ts";

export interface Ground {
  readonly step: number;
  /** The surveyed ground (the section's ground profile), in single precision as the page holds it. */
  readonly dem: Float32Array;
  /** The finished ground, the same. */
  readonly fin: Float32Array;
}

const clamp = (v: number, a: number, b: number): number => Math.max(a, Math.min(b, v));

/** The ground at c on a grid of step, linear between samples and held at the ends (sampleGround, 636). */
export function sampleGround(g: Float32Array, step: number, c: number): number {
  if (g.length === 0) return Number.NaN;
  const f = clamp(c / step, 0, g.length - 1);
  const i = Math.floor(f);
  const t = f - i;
  const a = g[i] as number;
  const b = g[Math.min(i + 1, g.length - 1)] as number;
  if (Number.isNaN(a)) return b;
  if (Number.isNaN(b)) return a;
  return a + (b - a) * t;
}

interface Pt {
  c: number;
  z: number;
}

/** gnd lines as the page parses them (parseGnd, 667): finite points sorted by c, at least two, over 1 m long. */
export function parseGnd(raw: StationInput["profile"]["gnd"]): Pt[][] {
  const out: Pt[][] = [];
  for (const L of raw ?? []) {
    const P = L.filter((p) => Number.isFinite(p[0]) && Number.isFinite(p[1]))
      .map(([c, z]) => ({ c, z }))
      .sort((a, b) => a.c - b.c);
    const first = P[0];
    const last = P[P.length - 1];
    if (first && last && P.length >= 2 && last.c - first.c > 1) out.push(P);
  }
  return out.sort((a, b) => (a[0] as Pt).c - (b[0] as Pt).c);
}

function gndLevel(P: Pt[], c: number): number {
  for (let k = 1; k < P.length; k++) {
    const a = P[k - 1] as Pt;
    const b = P[k] as Pt;
    if (c <= b.c) return b.c - a.c < SPAN_MIN_M ? b.z : a.z + ((b.z - a.z) * (c - a.c)) / (b.c - a.c);
  }
  return (P[P.length - 1] as Pt).z;
}

export function finishedGround(inp: StationInput): Ground | null {
  const g = inp.section.ground;
  if (!g || g.z_m.length === 0) return null;
  const step = g.step_m;
  // Float32Array as the page's S.ground (regradeGround 651): a depth exactly at a limit compares as it does there
  const dem = Float32Array.from(g.z_m);
  const reg = Float32Array.from(dem);
  for (const r of inp.ground_add)
    r.v.forEach((v, k) => {
      const i = r.i0 + k;
      if (i < reg.length && !Number.isNaN(reg[i] as number)) reg[i] = (reg[i] as number) + v;
    });
  for (const r of inp.ground_cap)
    r.v.forEach((v, k) => {
      const i = r.i0 + k;
      if (i < reg.length && !Number.isNaN(reg[i] as number) && v < (reg[i] as number)) reg[i] = v;
    });
  const lines = parseGnd(inp.profile.gnd);
  // normGnd (668): each line's two ends sit on the ground below it, to the centimetre
  for (const P of lines)
    for (const p of [P[0] as Pt, P[P.length - 1] as Pt]) {
      const b = sampleGround(reg, step, p.c);
      if (Number.isFinite(b)) p.z = Math.round(b * CM_PER_M) / CM_PER_M;
    }
  const fin = Float32Array.from(reg);
  const n = fin.length;
  const set = (i: number, z: number): void => {
    if (i >= 0 && i < n && !Number.isNaN(fin[i] as number)) fin[i] = z;
  };
  const own = (c: number): boolean => lines.some((P) => c >= (P[0] as Pt).c && c <= (P[P.length - 1] as Pt).c);
  for (const x of inp.cross_ground)
    for (let i = Math.ceil(x.c0 / step); i <= Math.floor(x.c1 / step); i++) if (!own(i * step)) set(i, x.z);
  for (const P of lines)
    for (let i = Math.ceil((P[0] as Pt).c / step); i <= Math.floor((P[P.length - 1] as Pt).c / step); i++)
      set(i, gndLevel(P, i * step));
  return { step, dem, fin };
}
