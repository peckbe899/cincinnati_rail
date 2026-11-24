// Plan curvature and the curve allowance on their 10 m grid (radii 1952-1970, radiusAt 1971, curveAllowance
// 1975-1984, allowanceAt 1985), and the stretches where grade plus curve allowance passes the limit
// (curveGradeRangesNow 1987-2006). Float32 as the page, so every threshold falls the same way.

import type { PathPoint } from "../../geom/path.ts";
import { pathAt } from "../../geom/path.ts";
import type { RuleId } from "../../rules.gen.ts";
import {
  DEG_HALF_TURN,
  LIMIT_TOL,
  M_PER_DEG_LAT,
  M_PER_DEG_LON,
  PORT_ALLOWANCE_WINDOW_DIV_M,
  PORT_CHECK_FIRST_M,
  PORT_CHECK_JOIN_M,
  PORT_CHECK_STEP_M,
  PORT_CURVE_ADD_MIN,
  PORT_RADII_AREA_MIN,
} from "../../tol.ts";
import { sustainedGrade } from "../structure/index.ts";
import type {
  CurveGradeRange,
  PortFlag,
  PortLiterals,
  PortSettings,
  SectionModel,
  Type,
  TypedModel,
  TypesModule,
} from "../types.ts";
import { clamp } from "../util.ts";
import { gradeOf, inStation, isRer } from "./at.ts";

/**
 * The plan radius every lit.radii.step metres (radii, 1952-1970): a circle through the path points h steps either
 * side, in the page's local plan metres (longitude times the cosine of the first point's latitude); Infinity where
 * the three points are in line and within h steps of either end.
 */
export function radii(path: readonly PathPoint[], length: number, lit: Pick<PortLiterals, "radii">): Float32Array {
  const step = lit.radii.step;
  const h = lit.radii.h;
  const n = Math.floor(length / step) + 1;
  const R = new Float32Array(n).fill(Number.POSITIVE_INFINITY);
  if (!path.length) return R;
  const lat0 = ((path[0] as PathPoint)[2] * Math.PI) / DEG_HALF_TURN;
  const kx = M_PER_DEG_LON * Math.cos(lat0);
  const xs = new Float64Array(n);
  const ys = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const [lon, lat] = pathAt(path, i * step);
    xs[i] = lon * kx;
    ys[i] = lat * M_PER_DEG_LAT;
  }
  for (let i = h; i < n - h; i++) {
    const ax = xs[i - h] as number;
    const ay = ys[i - h] as number;
    const bx = xs[i] as number;
    const by = ys[i] as number;
    const cx = xs[i + h] as number;
    const cy = ys[i + h] as number;
    const ab = Math.hypot(bx - ax, by - ay);
    const bc = Math.hypot(cx - bx, cy - by);
    const ca = Math.hypot(ax - cx, ay - cy);
    const area2 = Math.abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax));
    if (area2 > PORT_RADII_AREA_MIN) R[i] = (ab * bc * ca) / (2 * area2);
  }
  return R;
}

/**
 * The curve allowance on the radii's grid (curveAllowance, 1975-1984; era.grade.curve_allowance_train_averaged):
 * curveK times the curvature averaged over a train length (the platform), so a real curve counts in full and a kink
 * of a few tens of metres in the drawing does not.
 */
export function curveAllowance(R: Float32Array, s: Pick<PortSettings, "curveK" | "platform">): Float32Array {
  const n = R.length;
  const w = Math.max(1, Math.round(s.platform / PORT_ALLOWANCE_WINDOW_DIV_M));
  const cum = new Float64Array(n + 1);
  for (let i = 0; i < n; i++) {
    const r = R[i] as number;
    cum[i + 1] = (cum[i] as number) + (Number.isFinite(r) && r > 0 ? 1 / r : 0);
  }
  const v = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const a = Math.max(0, i - w);
    const b = Math.min(n, i + w + 1);
    v[i] = (s.curveK * ((cum[b] as number) - (cum[a] as number))) / (b - a);
  }
  return v;
}

/** The plan radius at c (radiusAt, 1971). */
export function radiusAt(m: Pick<SectionModel, "curve">, c: number): number {
  const R = m.curve.radii;
  return R[clamp(Math.round(c / m.curve.step), 0, R.length - 1)] as number;
}

/** The curve allowance at c, per mille (allowanceAt, 1985). */
export function allowanceAt(m: Pick<SectionModel, "curve">, c: number): number {
  const v = m.curve.allowance;
  return v[clamp(Math.round(c / m.curve.step), 0, v.length - 1)] as number;
}

/** Underground for the grade limit: bored or box, not a trough (UNDER_T, 1133). */
const UNDER_T = new Set<Type>(["shield", "deep", "cutcover"]);

/** straightUnder (1134-1140) on the module's type lookup: straight and underground, where the grade rule governs. */
export function straightUnder(m: TypedModel, c: number, T: Pick<TypesModule, "typeAt">): boolean {
  const S = m.structure;
  if (!S || isRer(m)) return false;
  const add = allowanceAt(m, c);
  return (!(add > 0) || m.settings.curveK / add >= S.grades.straight_radius) && UNDER_T.has(T.typeAt(m, c));
}

/**
 * The stretches where the grade plus the curve allowance passes the limit (curveGradeRangesNow, 1987-2006), every
 * 10 m from 5 m, outside stations, not where the grade rule covers a straight underground, and not where the phase
 * allows it; samples within 20 m join; each range's sustained average is the grade with curve over the sustained
 * length (era.grade.curve_allowance_train_averaged, era.grade.sustained_vs_local).
 */
export function curveGradeRanges(m: TypedModel, T: Pick<TypesModule, "typeAt" | "gradeLimitAt">): CurveGradeRange[] {
  const out: {
    c0: number;
    c1: number;
    worst: number;
    g: number;
    add: number;
    limit: ReturnType<TypesModule["gradeLimitAt"]>;
  }[] = [];
  const S = m.settings;
  if (!(S.curveK > 0)) return [];
  let on: (typeof out)[number] | null = null;
  for (let c = PORT_CHECK_FIRST_M; c < m.grid.length; c += PORT_CHECK_STEP_M) {
    if (inStation(m, c)) continue;
    const add = allowanceAt(m, c);
    const g = Math.abs(gradeOf(m, c));
    if (!(add > PORT_CURVE_ADD_MIN && g + add > S.maxGrade + LIMIT_TOL)) continue;
    if (straightUnder(m, c, T)) continue;
    const L = T.gradeLimitAt(m, c);
    if (g + add <= L.lim + LIMIT_TOL) continue;
    if (on && c - on.c1 <= PORT_CHECK_JOIN_M) {
      on.c1 = c;
      if (g + add > on.worst) Object.assign(on, { worst: g + add, g, add, limit: L });
    } else {
      on = { c0: c, c1: c, worst: g + add, g, add, limit: L };
      out.push(on);
    }
  }
  return out.map((r) => {
    const su = sustainedGrade(m, r.c0, r.c1, true);
    return { ...r, sustained: su, isSustained: su.avg > r.limit.lim + LIMIT_TOL };
  });
}

/** The rules of the curve grade flags. */
export const CURVE_RULES = [
  "era.grade.curve_allowance_train_averaged",
  "era.grade.sustained_vs_local",
] as const satisfies readonly RuleId[];

/** A curve grade range as its finding (designChecks 2122): an error where sustained, else a warning. */
export function curveGradeFlag(r: CurveGradeRange): PortFlag {
  return {
    kind: r.isSustained ? "curve_grade_sustained" : "curve_grade_local",
    page: "Curve grade",
    sev: r.isSustained ? "error" : "warn",
    c0: r.c0,
    c1: r.c1,
    c: (r.c0 + r.c1) / 2,
    rule: r.isSustained ? "era.grade.curve_allowance_train_averaged" : "era.grade.sustained_vs_local",
    data: {
      worst: r.worst,
      g: r.g,
      add: r.add,
      lim: r.limit.lim,
      why: r.limit.why,
      phase: r.limit.phase,
      // the binding limit's train-averaged radius ("a 582 m curve" in the old words); Infinity on a straight
      R: r.limit.R,
      avg: r.sustained.avg,
      W: r.sustained.W,
    },
  };
}
