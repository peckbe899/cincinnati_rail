// Propose fill (proposeFill 1684-1729, the pure part; ground.propose_fill.within_paint): over a painted box or tube
// (the run of that paint) or a stretch the rules decided (the stretch flagged), the ground made up to the structure's
// minimum (a box's roof plus its cover, a tube's top plus one outside diameter) a little over (literal.fill_over),
// any height, sloping back to the ground at fillSlope inside the stretch; drawn as a line within the fill band above
// it with its ends on the ground. The page drew it, replaced this line's drawn ground there and pushed undo; here it
// is returned, with the lines it replaces, for the sheet to apply as an edit.

import type { RuleId } from "../../rules.gen.ts";
import {
  CM_PER_M,
  PERMILLE,
  PORT_COVER_TOL_M,
  PORT_DM_PER_M,
  PORT_FILL_MARGIN_SAMPLES,
  PORT_FILL_SEARCH,
  PORT_FILL_SLOPE_TOL,
} from "../../tol.ts";
import type { FillProposal, SectionModel, Type, TypedModel, TypesModule } from "../types.ts";
import { overrideAt, railOf, riverAt } from "./at.ts";

/** The structures Propose fill covers (FILL_KINDS, 1683). */
const FILL_KINDS = new Set<Type>(["cutcover", "shield", "deep"]);

export const FILL_RULES = [
  "ground.propose_fill.within_paint",
  "ground.paint_never_raises_ground",
] as const satisfies readonly RuleId[];

/** The regraded ground with the other lines' drawn ground across this line, without this line's own drawn lines
 * (drawnGround(S.groundReg, []), 686-696). */
export function groundWithoutOwnLines(m: Pick<SectionModel, "ground">): Float32Array {
  const step = m.ground.step;
  const out = Float32Array.from(m.ground.regraded);
  const n = out.length;
  for (const x of m.ground.cross)
    for (let i = Math.ceil(x.c0 / step); i <= Math.floor(x.c1 / step); i++)
      if (i >= 0 && i < n && !Number.isNaN(out[i] as number)) out[i] = x.z;
  return out;
}

/** proposeFill (1684-1729) over [c0, c1]: the drawn line to add, or null where the structure has its cover. */
export function proposeFill(
  m: TypedModel,
  c0: number,
  c1: number,
  T: Pick<TypesModule, "typeAt" | "structFor" | "reqCover">,
): FillProposal {
  const step = m.ground.step;
  const base = groundWithoutOwnLines(m);
  const n = base.length;
  const o = overrideAt(m, (c0 + c1) / 2);
  const painted = !!o && FILL_KINDS.has(o);
  const drop = (m.settings.fillSlope / PERMILLE) * step;
  const kindAt = (c: number): Type | null => {
    const t = painted ? (o as Type) : T.typeAt(m, c);
    return FILL_KINDS.has(t) ? t : null;
  };
  const b = (i: number): number => base[i] as number;
  const needAt = (i: number): number => {
    const c = i * step;
    const k = kindAt(c);
    if (!k || Number.isNaN(b(i)) || riverAt(m, c)) return Number.NEGATIVE_INFINITY;
    const sc = T.structFor(m, k, c);
    return railOf(m, c) + sc.top + T.reqCover(m, sc) + m.literals.fillOver;
  };
  let i0 = Math.max(0, Math.floor(c0 / step));
  let i1 = Math.min(n - 1, Math.ceil(c1 / step));
  if (painted) {
    // the slope inside the paint
    while (i0 > 0 && overrideAt(m, (i0 - 1) * step) === o) i0--;
    while (i1 < n - 1 && overrideAt(m, (i1 + 1) * step) === o) i1++;
  } else {
    // a stretch the rules decided: its side slopes beyond it, so the whole stretch has its cover
    let top = 0;
    for (let i = i0; i <= i1; i++) top = Math.max(top, needAt(i) - b(i));
    const ext = Math.ceil(Math.max(0, top) / drop) + PORT_FILL_MARGIN_SAMPLES;
    i0 = Math.max(0, i0 - ext);
    i1 = Math.min(n - 1, i1 + ext);
  }
  const M = i1 - i0 + 1;
  const g = (k: number): number => b(i0 + k);
  const t = new Float64Array(M);
  for (let k = 0; k < M; k++) {
    const v = needAt(i0 + k);
    t[k] = v > g(k) + PORT_COVER_TOL_M ? v : Number.NEGATIVE_INFINITY; // the slope starts only where the ground is raised
  }
  if (!painted) {
    // the fill for the stretch flagged
    const k0 = Math.floor(c0 / step) - i0;
    const k1 = Math.ceil(c1 / step) - i0;
    for (let k = 0; k < M; k++) if (k < k0 || k > k1) t[k] = Number.NEGATIVE_INFINITY;
  }
  const tRaw = Float64Array.from(t); // the structure's own minimum, before the slopes
  for (let k = 1; k < M; k++) t[k] = Math.max(t[k] as number, (t[k - 1] as number) - drop);
  for (let k = M - 2; k >= 0; k--) t[k] = Math.max(t[k] as number, (t[k + 1] as number) - drop);
  const e0 = b(i0);
  const e1 = b(i1);
  const TT = new Float64Array(M);
  for (let k = 0; k < M; k++) {
    const gk = g(k);
    const lim = Math.min(
      Number.isNaN(e0) ? Number.POSITIVE_INFINITY : e0 + drop * k,
      Number.isNaN(e1) ? Number.POSITIVE_INFINITY : e1 + drop * (M - 1 - k),
    );
    TT[k] = Number.isNaN(gk) ? Number.NaN : Math.max(gk, Math.min(t[k] as number, lim));
  }
  const Tk = (k: number): number => TT[k] as number;
  // the fill at the structure's minimum (not a side slope)
  const need = (k: number): boolean =>
    Number.isFinite(tRaw[k] as number) && Tk(k) >= (tRaw[k] as number) - PORT_COVER_TOL_M;
  let r0 = -1;
  let r1 = -1;
  let q0 = -1;
  let q1 = -1;
  let top = 0;
  for (let k = 0; k < M; k++) {
    if (Tk(k) > g(k) + PORT_COVER_TOL_M) {
      if (r0 < 0) r0 = k;
      r1 = k;
      top = Math.max(top, Tk(k) - g(k));
      if (need(k)) {
        if (q0 < 0) q0 = k;
        q1 = k;
      }
    }
  }
  if (r0 < 0) return { c0: i0 * step, c1: i1 * step, line: null, replaces: [], top: 0 };
  if (q0 < 0) {
    q0 = r0;
    q1 = r1;
  }
  // the side slopes: one straight grade from the end on the ground up to the full fill, at most fillSlope
  const slope = drop / step;
  const endFrom = (q: number, dir: number, lim: number): number => {
    let e = q;
    for (let k = q + dir; dir < 0 ? k >= lim : k <= lim; k += dir) {
      const ok =
        Number.isFinite(g(k)) && Math.abs(Tk(q) - g(k)) / (Math.abs(q - k) * step) <= slope + PORT_FILL_SLOPE_TOL;
      e = k;
      if (ok && (k <= r0 - 1 || dir > 0) && (k >= r1 + 1 || dir < 0)) break;
    }
    return e;
  };
  const a = endFrom(q0, -1, 0);
  const bEnd = endFrom(q1, 1, M - 1);
  // between them as few points as keep the line within the fill band above the fill where the structure needs it, and
  // between the ground (fill_band.below under it at most) and the band above the fill where the ground is already high
  const B = m.literals.fillBand;
  const lo = (k: number): number => (need(k) ? Tk(k) - PORT_COVER_TOL_M : Math.min(Tk(k), g(k)) - B.below);
  const hi = (k: number): number => Tk(k) + B.above;
  const idx = [q0];
  for (let s0 = q0; s0 < q1; ) {
    let best = s0 + 1;
    for (let e = s0 + 1; e <= q1; e++) {
      let ok = !Number.isNaN(Tk(e));
      for (let k = s0 + 1; k < e && ok; k++) {
        if (Number.isNaN(Tk(k))) continue;
        const z = Tk(s0) + ((Tk(e) - Tk(s0)) * (k - s0)) / (e - s0);
        if (z < lo(k) || z > hi(k)) ok = false;
      }
      if (ok) best = e;
      else if (e - best > PORT_FILL_SEARCH) break;
    }
    idx.push(best);
    s0 = best;
  }
  const P = [a, ...idx, bEnd]
    .filter((k, j, arr) => j === 0 || k !== arr[j - 1])
    .map((k) => ({
      c: Math.round((i0 + k) * step * PORT_DM_PER_M) / PORT_DM_PER_M,
      z: k === a || k === bEnd ? Math.round(g(k) * CM_PER_M) / CM_PER_M : Math.ceil(Tk(k) * CM_PER_M) / CM_PER_M,
    }));
  const first = (P[0] as { c: number }).c;
  const last = (P[P.length - 1] as { c: number }).c;
  const replaces: number[] = [];
  m.align.gnd.forEach((Q, j) => {
    const q0c = (Q[0] as { c: number }).c;
    const q1c = (Q[Q.length - 1] as { c: number }).c;
    if (!(q1c < first || q0c > last)) replaces.push(j);
  });
  return { c0: first, c1: last, line: P, replaces, top };
}
