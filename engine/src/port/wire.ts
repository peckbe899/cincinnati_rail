// The JSON sides of section.solve@1: the input as the contract carries it (section_solve_input/0) to PortInput, and
// the solve to solved_section/0 (engine/src/contract/section_solve.ts). Arrays on the grid travel as number arrays
// with null where a value is not a number, rounded to the millimetre; categorical arrays as runs [value, c0, c1]
// that tile the line (c1 is the next run's c0, the last run's the line's end).

import type { SectionSolveInput, SolvedSection as SolvedJson } from "../contract/section_solve.ts";
import { PORT_MM_PER_M } from "../tol.ts";
import type { SolvedSection } from "./model.ts";
import type { CodedArray, Grid, PortInput, Type } from "./types.ts";

/** PortInput of the contract's JSON: the surveyed ground in single precision, NaN where none. */
export function portInputOf(j: SectionSolveInput): PortInput {
  const { contract: _c, dem, ...rest } = j;
  return {
    ...(rest as unknown as Omit<PortInput, "dem">),
    dem: Float32Array.from(dem, (v) => (v == null ? Number.NaN : v)),
  };
}

const mm = (v: number): number | null => (Number.isFinite(v) ? Math.round(v * PORT_MM_PER_M) / PORT_MM_PER_M : null);
const arr = (a: ArrayLike<number>): (number | null)[] => Array.from(a, mm);

/** Runs [value, c0, c1] of a value per sample, tiling 0 to the line's end. */
export function runsOf<T>(
  g: Grid,
  at: (i: number) => T,
  same: (a: T, b: T) => boolean = Object.is,
): [T, number, number][] {
  const out: [T, number, number][] = [];
  for (let i = 0; i < g.n; i++) {
    const v = at(i);
    const last = out[out.length - 1];
    if (last && same(last[0], v)) continue;
    if (last) last[2] = g.c[i] as number;
    out.push([v, g.c[i] as number, g.length]);
  }
  return out;
}

const coded =
  <T>(a: CodedArray<T>) =>
  (i: number): T =>
    a.table[a.codes[i] as number] as T;

/** A value with every non-finite number as null and every typed array as a plain array (JSON's own form). */
export function jsonSafe(v: unknown): unknown {
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (ArrayBuffer.isView(v))
    return Array.from(v as unknown as ArrayLike<number>, (x) => (Number.isFinite(x) ? x : null));
  if (Array.isArray(v)) return v.map(jsonSafe);
  if (v && typeof v === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, x] of Object.entries(v)) if (x !== undefined) out[k] = jsonSafe(x);
    return out;
  }
  return v;
}

/** The sheet's and the server's view of a solve (solved_section/0, less the stamps the host adds). */
export function solvedJson(input: PortInput, s: SolvedSection): Omit<SolvedJson, "engine_build" | "input_hash"> {
  const g = s.grid;
  const madeBed: { i0: number; z: number[] }[] = [];
  for (let i = 0; i < g.n; i++) {
    const v = s.madeBed[i] as number;
    if (!Number.isFinite(v)) continue;
    const last = madeBed[madeBed.length - 1];
    const z = mm(v) as number;
    if (last && last.i0 + last.z.length === i) last.z.push(z);
    else madeBed.push({ i0: i, z: [z] });
  }
  const sameStruct = (a: SolvedSection["struct"][number], b: SolvedSection["struct"][number]) =>
    a.k === b.k && a.below === b.below && a.top === b.top && a.tube === b.tube;
  const t = s.types;
  return jsonSafe({
    contract: "solved_section/0",
    section_id: input.section_id,
    length_m: input.length,
    step_m: input.step,
    n: g.n,
    stations: s.stations.map((st, i) => ({
      index: st.index,
      platform_id: st.platform_id,
      key: st.key,
      name: st.name,
      point_c: st.point_c,
      c: st.c,
      level: s.align.st[i] as number,
      sg: s.align.sg[i] ?? 0,
      type: s.drawn[Math.max(0, Math.min(g.n - 1, Math.round(st.c / g.step)))] as Type,
      role: t.stRole[st.key] ?? null,
      plat_def: t.platDef[st.key] ?? null,
      street: s.streets[i],
    })),
    type_runs: runsOf(g, (i) => s.drawn[i] as Type),
    struct_runs: runsOf(g, (i) => s.struct[i] as SolvedSection["struct"][number], sameStruct),
    tube_runs: runsOf(g, coded(t.tube)),
    part_runs: runsOf(g, coded(t.part)),
    phase_runs: runsOf(g, coded(t.phase)),
    grade_limit_runs: runsOf(
      g,
      (i) => [s.gradeLimit.lim[i] as number, s.gradeLimit.warn[i] as number] as const,
      (a, b) => a[0] === b[0] && (a[1] === b[1] || (Number.isNaN(a[1]) && Number.isNaN(b[1]))),
    ).map(([[lim, warn], c0, c1]) => [lim, warn, c0, c1]),
    limit_tube: arr(s.limitTube),
    limit_box: arr(s.limitBox),
    ground: {
      finished: arr(s.ground.finished),
      surface: arr(s.ground.surface),
      bed: arr(s.ground.bed),
      lines: s.ground.lines,
      cross: s.ground.cross,
    },
    made_bed: madeBed,
    rivers: s.rivers,
    canon: {
      sections: s.canon.sections,
      locks: s.canon.locks.map((lk) => ({ lo: lk.lo, hi: lk.hi, name: lk.name ?? null, src: lk.src })),
      piers: s.canon.piers,
    },
    spans: s.spans,
    bad: t.bad,
    misfits: s.misfits,
    approaches: t.approaches,
    shafts: t.shafts,
    stretches: t.stretches,
    crossings: s.crossings,
    context: s.context,
    roads: s.roads,
    over: s.summary.over.map((o) => ({ c0: o.c0, c1: o.c1, g: o.g, sev: o.sev })),
    curve_grade: s.curveGrade.map((r) => ({ c0: r.c0, c1: r.c1, worst: r.worst, sustained: r.isSustained })),
    summary: {
      len: s.summary.len,
      deepest: s.summary.deepest,
      highest: s.summary.highest,
      maxG: s.summary.maxG,
      maxGc: s.summary.maxGc,
      sumps: s.summary.sumps,
      deepShallow: s.summary.deepShallow,
    },
    flags: s.flags,
    levels: { st: s.levels.st, unset: s.levels.unset },
  }) as Omit<SolvedJson, "engine_build" | "input_hash">;
}

/** The contract's JSON of a PortInput (the ground as numbers, null where none). */
export function inputJson(input: PortInput): SectionSolveInput {
  return { contract: "section_solve_input/0", ...(jsonSafe(input) as Omit<SectionSolveInput, "contract">) };
}
