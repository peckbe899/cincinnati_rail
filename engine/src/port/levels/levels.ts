// The level solver (defaultAlign 1756-1807; network.level_solver.shallow_as_grade_allows): each station as shallow
// as the grade limit allows, at most defDepth under the ground, canon levels held (network.canon.fixed_levels), a
// selected elevated station at its mezzanine height, solved both ways so a steep descent goes deeper instead of
// popping out; the river tubes' bands and the canon bridges are extra nodes at their banks. And the RER's bend points
// on the old railroad between two at-grade stations (surfacePvis 1810-1836; slice 2, ported, not tested).

import type { RuleId } from "../../rules.gen.ts";
import { sampleGround } from "../../station/ground.ts";
import {
  CM_PER_M,
  PERMILLE,
  PORT_DM_PER_M,
  PORT_MM_PER_M,
  PORT_SURF_MIN_STEPS,
  PORT_SURF_PASSES,
  PORT_SURF_SMOOTH_DIV,
} from "../../tol.ts";
import { elevNeed } from "../structure/index.ts";
import type {
  FixedLevel,
  LevelModel,
  LevelNode,
  LevelSolution,
  PortFlag,
  SectionModel,
  SelectedType,
} from "../types.ts";
import { clamp } from "../util.ts";

export const LEVELS_SOLVER_RULES = [
  "network.level_solver.shallow_as_grade_allows",
  "network.canon.fixed_levels",
] as const satisfies readonly RuleId[];

type Mode = "under" | "surface";

const isRer = (m: Pick<SectionModel, "input">): boolean => m.input.system === "rer";
/** The ground the level solver reads (groundAt0, 646): the finished ground. */
const groundAt0 = (m: Pick<LevelModel, "ground">, c: number): number =>
  sampleGround(m.ground.finished, m.ground.step, c);
const riverAt = (m: Pick<LevelModel, "rivers">, c: number): boolean => m.rivers.some((r) => c >= r.c0 && c <= r.c1);
/** The pool over a river, else the ground (surfaceAt0, 704). */
const surfaceAt0 = (m: Pick<LevelModel, "ground" | "rivers" | "settings">, c: number): number =>
  riverAt(m, c) ? m.settings.pool : groundAt0(m, c);
/** A fixed level: absolute, or an offset from the ground (fixedLevel, 909). */
const fixedLevel = (f: FixedLevel, gr: number): number => (f.abs != null ? f.abs : gr + Number(f.off));

/** An RER station's mode: the canon's, else under on a drawn trunk and surface elsewhere (defaultMode, 1039). */
export function defaultMode(m: Pick<LevelModel, "canon" | "stations">, i: number): Mode {
  const f = m.canon.modes[i];
  if (f) return f;
  return m.stations[i]?.trunk ? "under" : "surface";
}

/** inPlatform (3142): inside a platform and 2 m past its ends. */
const inPlatform = (m: Pick<LevelModel, "stations" | "settings">, c: number): boolean => {
  const half = m.settings.platform / 2;
  return m.stations.some((s) => c > s.c - half - 2 && c < s.c + half + 2);
};

interface Node {
  c: number;
  st: boolean;
  i: number;
  ub: number;
  lb: number;
}

/**
 * defaultAlign (1756-1807): the default station levels (to the cm) and the river bend points (c to 0.1 m, z to the
 * mm) of the stations as they are in the model (slid). Where the page wrote 0 m for a station with no bound (1775)
 * the level is NaN, the station is listed in `unset` and flagged: never 0.
 */
export function defaultAlign(
  m: LevelModel,
  modes: readonly (Mode | null | undefined)[] | null,
  extra: readonly LevelNode[],
  stt: readonly (SelectedType | "")[] | null,
): LevelSolution {
  const S = m.settings;
  const g = S.maxGrade / PERMILLE;
  const P = S.platform + Math.max(S.vcRadius * g, S.vcMinLen);
  const n = m.stations.length;
  const ub: number[] = [];
  const lb: number[] = [];
  const md: Mode[] | null = isRer(m) ? m.stations.map((_, i) => modes?.[i] || defaultMode(m, i)) : null;
  m.stations.forEach((s, i) => {
    const gr = groundAt0(m, s.c);
    const f = m.canon.fixed[i];
    if (f && (Number.isFinite(gr) || f.abs != null)) ub[i] = lb[i] = fixedLevel(f, gr);
    else if (stt && stt[i] === "elevated" && Number.isFinite(gr)) ub[i] = lb[i] = gr + elevNeed(m);
    else if (md && md[i] === "surface" && Number.isFinite(gr)) ub[i] = lb[i] = gr;
    else {
      ub[i] = Number.isFinite(gr) ? gr - S.defDepth : Number.POSITIVE_INFINITY;
      lb[i] = Number.NEGATIVE_INFINITY;
    }
  });
  // riverTubes (1037) then riverBridges (993): the bands of the rivers crossed in a tube, the bridges' levels
  const tubes: { c0: number; c1: number; ub: number; lb: number }[] = [
    ...m.rivers
      .filter((r) => !r.bridge && r.band)
      .map((r) => ({ c0: r.c0, c1: r.c1, ub: r.band?.ub as number, lb: r.band?.lb as number })),
    ...m.rivers
      .filter((r) => r.bridge && !r.bridge.fixed && r.bridgeBand)
      .map((r) => ({ c0: r.c0, c1: r.c1, ub: r.bridgeBand?.ub as number, lb: r.bridgeBand?.lb as number })),
  ];
  const nodes: Node[] = m.stations.map((s, i) => ({ c: s.c, st: true, i, ub: ub[i] as number, lb: lb[i] as number }));
  const banks = tubes.length > 0 || extra.length > 0;
  if (banks) {
    const e = (S.vcRadius * g) / 2;
    const half = S.platform / 2;
    const L = m.grid.length;
    for (const t of tubes) {
      // half a curve beyond each bank, but never closer than a transition to a platform
      const before = m.stations.filter((q) => q.c + half <= t.c0).map((q) => q.c + half + e);
      const after = m.stations.filter((q) => q.c - half >= t.c1).map((q) => q.c - half - e);
      const a = Math.min(t.c0, Math.max(0, t.c0 - e, ...before));
      const b = Math.max(t.c1, Math.min(L, t.c1 + e, ...after));
      const u = t.ub ?? Number.POSITIVE_INFINITY;
      const l = t.lb ?? Number.NEGATIVE_INFINITY;
      nodes.push({ c: a, st: false, i: -1, ub: u, lb: l }, { c: b, st: false, i: -1, ub: u, lb: l });
    }
    for (const x of extra)
      nodes.push({
        c: x.c,
        st: false,
        i: -1,
        ub: x.ub ?? Number.POSITIVE_INFINITY,
        lb: x.lb ?? Number.NEGATIVE_INFINITY,
      });
    nodes.sort((p, q) => p.c - q.c); // stable, as the page's
  }
  // the platforms between two nodes, each with its transitions, take no grade (stations only, 1768 and 1790)
  const cnt: number[] = [];
  let k = 0;
  for (const nd of nodes) {
    cnt.push(k);
    if (nd.st) k++;
  }
  const N = nodes.length;
  const run = banks
    ? (a: number, b: number): number => {
        const [x, y] = a < b ? [a, b] : [b, a];
        const X = nodes[x] as Node;
        const Y = nodes[y] as Node;
        const between = (cnt[y] as number) - (cnt[x] as number) - (X.st ? 1 : 0);
        return Math.max(0, Y.c - X.c - P * between - (X.st ? P / 2 : 0) - (Y.st ? P / 2 : 0));
      }
    : (a: number, b: number): number =>
        Math.max(0, Math.abs((nodes[b] as Node).c - (nodes[a] as Node).c) - P * Math.abs(b - a));
  const z = nodes.map((_, a) => {
    let r = Number.POSITIVE_INFINITY;
    for (let b = 0; b < N; b++) r = Math.min(r, (nodes[b] as Node).ub + g * run(a, b));
    return r;
  });
  for (let a = 0; a < N; a++) {
    let lo = Number.NEGATIVE_INFINITY;
    for (let b = 0; b < N; b++) {
      const l = (nodes[b] as Node).lb;
      if (Number.isFinite(l)) lo = Math.max(lo, l - g * run(a, b));
    }
    z[a] = Math.max(z[a] as number, lo);
  }
  const st = new Array<number>(n).fill(Number.NaN);
  const pvi: { c: number; z: number }[] = [];
  const unset: number[] = [];
  nodes.forEach((nd, a) => {
    const v = z[a] as number;
    if (nd.st) {
      if (Number.isFinite(v)) st[nd.i] = Math.round(v * CM_PER_M) / CM_PER_M;
      else unset.push(nd.i);
    } else if (Number.isFinite(v) && !inPlatform(m, nd.c))
      // bend points at the extra nodes, except inside platforms (those constrain the station level)
      pvi.push({
        c: Math.round(nd.c * PORT_DM_PER_M) / PORT_DM_PER_M,
        z: Math.round(v * PORT_MM_PER_M) / PORT_MM_PER_M,
      });
  });
  unset.sort((a, b) => a - b);
  const flags: PortFlag[] = unset.map((i) => {
    const s = m.stations[i];
    const c = s ? s.c : 0;
    return {
      kind: "station_level_unbounded",
      page: "Level solver",
      sev: "warn",
      c0: c - S.platform / 2,
      c1: c + S.platform / 2,
      c,
      rule: "network.level_solver.shallow_as_grade_allows",
      data: { station: i },
    };
  });
  const all = (md ? surfacePvis(m, st, md) : []).concat(pvi).sort((p, q) => p.c - q.c);
  return { st, pvi: all, unset, flags };
}

/**
 * surfacePvis (1810-1836), RER: between two at-grade stations the rail follows the old railroad, a bend point every
 * surfStep on the ground smoothed over two steps, then held to the grade limit both ways (four passes).
 */
export function surfacePvis(m: LevelModel, st: readonly number[], md: readonly Mode[]): { c: number; z: number }[] {
  const S = m.settings;
  const step = S.rer?.surfStep;
  if (!(step && step > 0)) return [];
  const g = S.maxGrade / PERMILLE;
  const L = m.grid.length;
  const out: { c: number; z: number }[] = [];
  const half = S.platform / 2 + Math.max(S.vcRadius * g, S.vcMinLen) / 2; // clear of the platform transitions
  const smooth = (c: number): number => {
    let a = 0;
    let k = 0;
    for (let d = -step; d <= step; d += step / PORT_SURF_SMOOTH_DIV) {
      const v = surfaceAt0(m, clamp(c + d, 0, L));
      if (Number.isFinite(v)) {
        a += v;
        k++;
      }
    }
    return k ? a / k : Number.NaN;
  };
  const runs: [number, number, number | null, number | null][] = [];
  const n = m.stations.length;
  const sc = (i: number): number => (m.stations[i] as { c: number }).c;
  // the stretch before the first station and after the last count as surface when that station is
  if (n && md[0] === "surface") runs.push([0, sc(0) - half - 2, null, st[0] as number]);
  for (let i = 0; i + 1 < n; i++)
    if (md[i] === "surface" && md[i + 1] === "surface")
      runs.push([sc(i) + half + 2, sc(i + 1) - half - 2, st[i] as number, st[i + 1] as number]);
  if (n && md[n - 1] === "surface") runs.push([sc(n - 1) + half + 2, L, st[n - 1] as number, null]);
  for (const [a, b, za, zb] of runs) {
    if (b - a < step * PORT_SURF_MIN_STEPS) continue;
    const k = Math.floor((b - a) / step);
    const pts: { c: number; z: number }[] = [];
    for (let j = 1; j < k; j++) {
      const c = a + ((b - a) * j) / k;
      const z = smooth(c);
      if (Number.isFinite(z)) pts.push({ c: Math.round(c), z });
    }
    if (!pts.length) continue;
    const first = pts[0] as { z: number };
    const last = pts[pts.length - 1] as { z: number };
    const chain = [
      { c: a, z: za ?? first.z, fixed: za != null },
      ...pts.map((p) => ({ ...p, fixed: false })),
      { c: b, z: zb ?? last.z, fixed: zb != null },
    ];
    for (let it = 0; it < PORT_SURF_PASSES; it++) {
      for (let j = 1; j < chain.length; j++) {
        const q = chain[j] as (typeof chain)[number];
        const p = chain[j - 1] as (typeof chain)[number];
        if (!q.fixed) {
          const d = g * (q.c - p.c);
          q.z = clamp(q.z, p.z - d, p.z + d);
        }
      }
      for (let j = chain.length - 2; j >= 0; j--) {
        const q = chain[j] as (typeof chain)[number];
        const p = chain[j + 1] as (typeof chain)[number];
        if (!q.fixed) {
          const d = g * (p.c - q.c);
          q.z = clamp(q.z, p.z - d, p.z + d);
        }
      }
    }
    // the chain's own points (the page kept the pts objects, moved by the passes)
    for (let j = 1; j < chain.length - 1; j++) {
      const q = chain[j] as (typeof chain)[number];
      out.push({ c: q.c, z: Math.round(q.z * CM_PER_M) / CM_PER_M });
    }
  }
  return out.sort((x, y) => x.c - y.c);
}
