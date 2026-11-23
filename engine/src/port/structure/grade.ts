// The grade limit by building phase (straightUnder 1134-1140, gradeLimitAt 1142-1155, gradeLimitOver 1157-1165)
// and sustained against localized (sustainedGrade 1167-1179, gradeSeverity 1180-1184). P1b: the limit is the
// phase's. It reads the curve allowance on its 10 m grid (the model's curve arrays, P4's) and the solved type.

import {
  PERMILLE,
  PORT_CHAINAGE_EPS_M,
  PORT_GRADE_LIMIT_FIRST_M,
  PORT_GRADE_LIMIT_STEP_M,
  PORT_GRADE_SEV_TOL,
  PORT_SUSTAINED_INNER_M,
  PORT_SUSTAINED_STEP_M,
} from "../../tol.ts";
import { gradeAt, railAt } from "../../vertical/rail.ts";
import type { GradeLimit, GradeOver, SectionModel, Type, TypedModel } from "../types.ts";
import { clamp } from "../util.ts";
import { isRer } from "./at.ts";
import { typeAt } from "./lookup.ts";
import { phaseAt, phaseRecord } from "./phase.ts";

/** Underground for the grade limit: bored or box, not a trough (UNDER_T, 1133). */
const UNDER_T = new Set<Type>(["shield", "deep", "cutcover"]);

/** The curve allowance at c, per mille, on its 10 m grid (allowanceAt 1985). */
export function allowanceAt(m: Pick<SectionModel, "curve">, c: number): number {
  const v = m.curve.allowance;
  return v[clamp(Math.round(c / m.curve.step), 0, v.length - 1)] as number;
}

/** straightUnder (1134-1140): straight (train-averaged radius at least the record's straight radius) and
 * underground. */
export function straightUnder(m: TypedModel, c: number): boolean {
  const S = m.structure;
  if (!S || isRer(m)) return false;
  const add = allowanceAt(m, c);
  return (!(add > 0) || m.settings.curveK / add >= S.grades.straight_radius) && UNDER_T.has(typeAt(m, c));
}

/**
 * gradeLimitAt (1142-1155), era.grade.limit_by_phase: the phase's limit everywhere; a straight stretch underground
 * up to the straight limit as a warning where the phase warns; straight up to it where it does not; a curve over
 * the phase's curve radius up to its curve limit. `why` names the case for the sheet to word.
 */
export function gradeLimitAt(m: TypedModel, c: number): GradeLimit {
  const base = m.settings.maxGrade;
  const S = m.structure;
  if (!S || isRer(m)) return { lim: base, warn: null, why: "rer", phase: null, R: Number.POSITIVE_INFINITY };
  const ph = phaseAt(m, c);
  const p = phaseRecord(m, ph);
  const add = allowanceAt(m, c);
  const R = add > 0 ? m.settings.curveK / add : Number.POSITIVE_INFINITY;
  const mx = p?.grade_max ?? base;
  const st = p?.grade_straight ?? S.grades.straight_underground_max ?? mx;
  if (R >= S.grades.straight_radius) {
    if (p?.straight_warn ?? true) {
      const u = UNDER_T.has(typeAt(m, c));
      return { lim: mx, warn: u ? st : null, why: u ? "straight_underground" : "straight_open", phase: ph, R };
    }
    return { lim: st, warn: null, why: "straight", phase: ph, R };
  }
  if (p?.grade_curve && R > p.curve_radius) return { lim: p.grade_curve, warn: null, why: "curve_long", phase: ph, R };
  return { lim: mx, warn: null, why: "curve", phase: ph, R };
}

/** gradeLimitOver (1157-1165): the strictest limit over a stretch, sampled every 10 m; the binding point (the
 * lowest cap, its warning limit else its limit) gives the rule quoted. */
export function gradeLimitOver(m: TypedModel, c0: number, c1: number): GradeLimit {
  let lim = Number.POSITIVE_INFINITY;
  let cap = Number.POSITIVE_INFINITY;
  let bind: GradeLimit | null = null;
  for (let c = c0 + Math.min(PORT_GRADE_LIMIT_FIRST_M, (c1 - c0) / 2); c <= c1; c += PORT_GRADE_LIMIT_STEP_M) {
    const L = gradeLimitAt(m, c);
    lim = Math.min(lim, L.lim);
    const k = L.warn ?? L.lim;
    if (k < cap) {
      cap = k;
      bind = L;
    }
  }
  if (!bind) return gradeLimitAt(m, (c0 + c1) / 2);
  return { ...bind, lim, warn: bind.warn && bind.warn > lim ? bind.warn : null };
}

/**
 * sustainedGrade (1167-1179), era.grade.sustained_vs_local: the grade averaged over sustainedLen at its steepest
 * over the windows touching [c0, c1]; with comp, the grade plus the curve allowance averaged every 10 m.
 */
export function sustainedGrade(m: SectionModel, c0: number, c1: number, comp = false): GradeOver["sustained"] {
  const L = m.grid.length;
  const W = Math.min(L, m.settings.sustainedLen || 2 * m.settings.platform);
  const d = m.rail.design;
  let best = 0;
  let at = c0;
  const lo = Math.max(0, c0 - W);
  const hi = Math.max(lo, Math.min(L - W, c1));
  for (let c = lo; c <= hi + PORT_CHAINAGE_EPS_M; c += PORT_SUSTAINED_STEP_M) {
    let g: number;
    if (!comp) g = (Math.abs(railAt(d, c + W) - railAt(d, c)) / W) * PERMILLE;
    else {
      let sum = 0;
      let k = 0;
      for (let q = c; q <= c + W; q += PORT_SUSTAINED_INNER_M) {
        sum += Math.abs(gradeAt(d, q)) + allowanceAt(m, q);
        k++;
      }
      g = sum / k;
    }
    if (g > best) {
      best = g;
      at = c + W / 2;
    }
  }
  return { avg: best, at, W };
}

/** gradeSeverity (1180-1184): local where the sustained grade is within the limit, straight within the warning
 * limit, else an error. */
export function gradeSeverity(L: Pick<GradeLimit, "lim" | "warn">, sus: number): GradeOver["sev"] {
  if (sus <= L.lim + PORT_GRADE_SEV_TOL) return "local";
  if (L.warn && sus <= L.warn + PORT_GRADE_SEV_TOL) return "straight";
  return "error";
}

/** gradeLimitAt at every sample (PortSolved.gradeLimit): the limit, and the warning limit (NaN where none). */
export function gradeLimitArrays(m: TypedModel): { lim: Float32Array; warn: Float32Array } {
  const { n } = m.grid;
  const lim = new Float32Array(n);
  const warn = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const L = gradeLimitAt(m, m.grid.c[i] as number);
    lim[i] = L.lim;
    warn[i] = L.warn ?? Number.NaN;
  }
  return { lim, warn };
}
