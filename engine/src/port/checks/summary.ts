// The summary of a line (computeSummary 1900-1949): metres of each structure type, the deepest and highest points,
// the steepest grade and the grades over the limit between bends, the sumps, the stations deeper than the shallow
// canon allows; and the river checks of the same function (the page's shallowTubes, 1921-1946).

import type { RuleId } from "../../rules.gen.ts";
import {
  LIMIT_TOL,
  PORT_CHECK_FIRST_M,
  PORT_CHECK_STEP_M,
  PORT_COVER_TOL_M,
  PORT_RIVER_JOIN_STEPS,
} from "../../tol.ts";
import { gradeSeverity, sustainedGrade } from "../structure/index.ts";
import type {
  GradeLimit,
  GradeOver,
  PortFlag,
  SectionModel,
  Summary,
  Type,
  TypedModel,
  TypesModule,
} from "../types.ts";
import { TYPE_CODES } from "../types.ts";
import { bedAt, canonAt, overrideAt, railOf, surfaceAt } from "./at.ts";
import { chordsOf, sumpsOf } from "./chords.ts";

/** gradeLimitOver (1157-1165) on the module's limit: the strictest limit over a stretch sampled every 10 m; the
 * binding point (the lowest cap, its warning limit else its limit) gives the rule quoted. */
export function gradeLimitOver(
  m: TypedModel,
  c0: number,
  c1: number,
  T: Pick<TypesModule, "gradeLimitAt">,
): GradeLimit {
  let lim = Number.POSITIVE_INFINITY;
  let cap = Number.POSITIVE_INFINITY;
  let bind: GradeLimit | null = null;
  for (let c = c0 + Math.min(PORT_CHECK_FIRST_M, (c1 - c0) / 2); c <= c1; c += PORT_CHECK_STEP_M) {
    const L = T.gradeLimitAt(m, c);
    lim = Math.min(lim, L.lim);
    const k = L.warn ?? L.lim;
    if (k < cap) {
      cap = k;
      bind = L;
    }
  }
  if (!bind) return T.gradeLimitAt(m, (c0 + c1) / 2);
  return { ...bind, lim, warn: bind.warn && bind.warn > lim ? bind.warn : null };
}

/** The steepest chord and the chords over the limit (computeSummary 1913-1920; era.grade.limit_by_phase,
 * era.grade.sustained_vs_local, era.grade.steepest_between_bends). */
export function gradesOver(
  m: TypedModel,
  T: Pick<TypesModule, "gradeLimitAt">,
): { maxG: number; maxGc: number; over: GradeOver[] } {
  let maxG = 0;
  let maxGc = 0;
  const over: GradeOver[] = [];
  for (const { a, b, g } of chordsOf(m)) {
    if (Math.abs(g) > Math.abs(maxG)) {
      maxG = g;
      maxGc = (a.c + b.c) / 2;
    }
    if (Math.abs(g) > m.settings.maxGrade + LIMIT_TOL) {
      const L = gradeLimitOver(m, a.c, b.c, T);
      if (Math.abs(g) > L.lim + LIMIT_TOL) {
        const su = sustainedGrade(m, a.c, b.c);
        over.push({ c0: a.c, c1: b.c, g, limit: L, sustained: su, sev: gradeSeverity(L, su.avg) });
      }
    }
  }
  return { maxG, maxGc, over };
}

/** The stations the canon puts in a shallow (basin or canal) section deeper than shallowMax (1908-1912), unless a
 * paint or selection decides their structure. */
export function deepShallow(m: SectionModel): Summary["deepShallow"] {
  const out: { station: number; c: number; d: number }[] = [];
  m.stations.forEach((st, i) => {
    const sec = canonAt(m, st.c);
    if (!sec || sec.m === "deep" || overrideAt(m, st.c)) return;
    const d = surfaceAt(m, st.c) - (m.align.st[i] as number);
    if (Number.isFinite(d) && d > m.settings.shallowMax) out.push({ station: i, c: st.c, d });
  });
  return out;
}

/** computeSummary (1900-1920, 1949), the numbers only: the clashes, river checks and design checks are their own
 * functions (crossings, riverChecks, designChecks). */
export function computeSummary(m: TypedModel, T: Pick<TypesModule, "typeAt" | "gradeLimitAt">): Summary {
  const L = m.grid.length;
  const dc = PORT_CHECK_STEP_M;
  const len = Object.fromEntries(TYPE_CODES.map((t) => [t, 0])) as Record<Type, number>;
  let deepest = { d: Number.NEGATIVE_INFINITY, c: 0 };
  let highest = { h: Number.NEGATIVE_INFINITY, c: 0 };
  for (let c = 0; c < L; c += dc) {
    const cm = Math.min(L, c + dc / 2);
    const z = railOf(m, cm);
    const t = T.typeAt(m, cm, z);
    len[t] += Math.min(dc, L - c);
    const s = surfaceAt(m, cm);
    if (Number.isFinite(s)) {
      const d = s - z;
      if (d > deepest.d) deepest = { d, c: cm };
      if (-d > highest.h) highest = { h: -d, c: cm };
    }
  }
  const { maxG, maxGc, over } = gradesOver(m, T);
  return { len, deepest, highest, maxG, maxGc, over, sumps: sumpsOf(m, T), deepShallow: deepShallow(m) };
}

/** The rules of the river checks. */
export const RIVER_RULES = [
  "river.sunk_box.roof_band",
  "river.sunk_box.made_up_bed",
  "river.ohio.navigable_12ft",
  "river.crossing.bridge_or_sunk",
  "river.bridge.navigation_clearance",
] as const satisfies readonly RuleId[];

type RiverKind = "high" | "low" | "nav" | "bridge" | "clearance";
const RIVER_FLAG: Record<RiverKind, { kind: string; rule: (typeof RIVER_RULES)[number] }> = {
  high: { kind: "sunk_box_high", rule: "river.sunk_box.roof_band" },
  low: { kind: "sunk_box_low", rule: "river.sunk_box.roof_band" },
  nav: { kind: "sunk_box_nav", rule: "river.ohio.navigable_12ft" },
  bridge: { kind: "river_above_water", rule: "river.crossing.bridge_or_sunk" },
  clearance: { kind: "bridge_below_clearance", rule: "river.bridge.navigation_clearance" },
};

interface RiverHit {
  kind: RiverKind;
  name: string;
  c0: number;
  c1: number;
  c: number;
  over: number;
}

/**
 * The river checks (computeSummary 1921-1946): under water the sunk box inside its band (its roof at most riverRise
 * over the bed; at least riverSink into it on the flat bottom), the made-up bed over it clear of the navigable
 * channel, no crossing above the water (one finding for the whole river: its ramps are part of it); and a canon
 * bridge's rail at its navigation clearance level.
 */
export function riverChecks(m: TypedModel, T: Pick<TypesModule, "typeAt">): PortFlag[] {
  const S = m.settings;
  const step = m.grid.step;
  const pool = S.pool;
  const top = m.sunk.top;
  const list: RiverHit[] = [];
  for (const r of m.rivers) {
    if (r.bridge) continue;
    const B = r.band;
    if (!B) continue;
    const on: Partial<Record<RiverKind, RiverHit>> = {};
    const n0 = list.length;
    const hit = (k: RiverKind, c: number, v: number): void => {
      const o = on[k];
      if (o && c - o.c1 <= step * PORT_RIVER_JOIN_STEPS) {
        o.c1 = c;
        if (v > o.over) {
          o.over = v;
          o.c = c;
        }
      } else {
        const x: RiverHit = { kind: k, name: r.name, c0: c, c1: c, c, over: v };
        on[k] = x;
        list.push(x);
      }
    };
    for (let i = Math.ceil(r.c0 / step); i * step <= r.c1; i++) {
      const c = i * step;
      const b = bedAt(m, c);
      const z = railOf(m, c);
      const t = T.typeAt(m, c, z);
      if (!Number.isFinite(b) || b >= pool) continue; // under water only
      if (t === "elevated") {
        hit("bridge", c, z - pool);
        continue;
      }
      const hi = b - top + S.riverRise;
      if (z > hi + PORT_COVER_TOL_M) hit("high", c, z - hi);
      const lo = b - top - S.riverSink;
      if (b <= B.low + S.riverFlatTol && z < lo - PORT_COVER_TOL_M) hit("low", c, lo - z);
      const mb = z + top + S.riverCap;
      const ceil = pool - S.riverClearWater;
      if (B.nav != null && mb > b && mb > ceil + PORT_COVER_TOL_M) hit("nav", c, mb - ceil);
    }
    // a crossing on a bridge is one issue (its ramps down to the water are part of it)
    const br = on.bridge;
    if (br) {
      list.length = n0;
      list.push({ ...br, c0: r.c0, c1: r.c1 });
    }
  }
  for (const r of m.rivers) {
    const b = r.bridgeBand;
    if (!r.bridge || r.bridge.fixed || !b) continue;
    let lo = Number.POSITIVE_INFINITY;
    let lc = r.c0;
    for (let c = r.c0; c <= r.c1; c += step) {
      const z = railOf(m, c);
      if (z < lo) {
        lo = z;
        lc = c;
      }
    }
    if (lo < b.lb - LIMIT_TOL)
      list.push({ kind: "clearance", name: r.name, c: lc, c0: r.c0, c1: r.c1, over: b.lb - lo });
  }
  return list.map((x) => ({
    kind: RIVER_FLAG[x.kind].kind,
    page: "River",
    sev: "error",
    c0: x.c0,
    c1: x.c1,
    c: x.c,
    rule: RIVER_FLAG[x.kind].rule,
    data: { river: x.name, over: x.over, check: x.kind },
  }));
}
