// P1's outputs against the old page's goldens, output by output, within the tolerances of section 6 of
// claude/hub_maps/engine_port_plan.md. Each output gives its differences; report.ts classes them.

import {
  effOvr,
  gradeLimitAt,
  gradeLimitOver,
  gradeSeverity,
  limitLines,
  overrideAt,
  paintMisfits,
  phaseAt,
  pointType,
  sgMaxFor,
  solveTypes,
  structArrays,
  sttFromDoc,
  sustainedGrade,
  TYPES_MODULE,
  tubeFormAt,
  tubeKeyAt,
} from "../../../src/port/structure/index.ts";
import { TYPE_CODES, type TypedModel, type TypeSolve } from "../../../src/port/types.ts";
import { valueAt } from "../../../src/port/util.ts";
import { unrle } from "../../golden/old_page/load.ts";
import { fromGolden, typedFromGolden } from "../from_golden.ts";
import type { Difference, OutputResult } from "../report.ts";

const r4 = (v: number): number => Math.round(v * 1e4) / 1e4;
const MAX_LISTED = 20;

/** Per-sample categorical comparison: the differing samples (first MAX_LISTED listed, all counted). */
function perSample<T>(output: string, page: readonly T[], port: (i: number) => T, n: number): OutputResult {
  const differences: Difference[] = [];
  let count = 0;
  for (let i = 0; i < n; i++) {
    const p = port(i);
    if (p !== page[i]) {
      count++;
      if (differences.length < MAX_LISTED) differences.push({ at: `i=${i}`, page: page[i], port: p });
    }
  }
  if (count > MAX_LISTED) differences.push({ at: `${count - MAX_LISTED} more samples`, page: null, port: null });
  return { output, compared: n, differences };
}

/** Per-sample numbers within a tolerance, NaN equal to NaN. */
function perSampleNum(output: string, page: readonly number[], port: ArrayLike<number>, tol: number): OutputResult {
  const differences: Difference[] = [];
  for (let i = 0; i < page.length; i++) {
    const a = page[i] as number;
    const b = port[i] as number;
    const same = Number.isNaN(a) ? Number.isNaN(b) : Math.abs(a - b) <= tol;
    if (!same && differences.length < MAX_LISTED) differences.push({ at: `i=${i}`, page: a, port: b });
  }
  return { output, compared: page.length, differences };
}

/** Two lists as sets of keys: what only the page has and what only the port has. */
function sets<A, B>(
  output: string,
  page: readonly A[],
  port: readonly B[],
  kp: (x: A) => string,
  kq: (x: B) => string,
): OutputResult {
  const P = new Set(page.map(kp));
  const Q = new Set(port.map(kq));
  const differences: Difference[] = [];
  for (const k of P) if (!Q.has(k)) differences.push({ at: k, page: k, port: null });
  for (const k of Q) if (!P.has(k)) differences.push({ at: k, page: null, port: k });
  return { output, compared: Math.max(P.size, Q.size), differences };
}

/** Pairwise numbers of two lists in the same order, within a tolerance. */
function pairs<A, B>(
  output: string,
  page: readonly A[],
  port: readonly B[],
  fields: [string, (x: A) => number, (x: B) => number, number][],
): OutputResult {
  const differences: Difference[] = [];
  if (page.length !== port.length) differences.push({ at: "length", page: page.length, port: port.length });
  const n = Math.min(page.length, port.length);
  for (let k = 0; k < n; k++)
    for (const [name, fa, fb, tol] of fields) {
      const a = fa(page[k] as A);
      const b = fb(port[k] as B);
      if (!(Math.abs(a - b) <= tol || (Number.isNaN(a) && Number.isNaN(b))))
        differences.push({ at: `${k}.${name}`, page: a, port: b });
    }
  return { output, compared: n, differences };
}

const flagSev = (f: { error?: true; info?: true }): string => (f.error ? "error" : f.info ? "info" : "warn");

/** The page's why text of a grade limit as the port's slug (gradeLimitAt 1150-1155). */
export function whySlug(why: string): string {
  if (why.includes("straight underground")) return "straight_underground";
  if (why.includes("straight but not underground")) return "straight_open";
  if (why.includes(": straight, up to")) return "straight";
  if (why.includes("a curve over")) return "curve_long";
  return why ? "curve" : "rer";
}

export interface LineRun {
  results: OutputResult[];
  solve: TypeSolve;
  typed: TypedModel;
}

/** Every P1 output of one line against its golden. */
export function compareLine(line: string): LineRun {
  const { dump: d, model: m, input } = fromGolden(line);
  const n = m.grid.n;
  const c = (i: number): number => m.grid.c[i] as number;
  const results: OutputResult[] = [];
  const g = d.grid;
  const s = d.solve;
  if (!s || !g.solved) throw new Error(`${line}: the golden has no solve`);

  // the adapter's rail (the vertical design on the golden's align) is the golden's, rounded to 0.1 mm
  results.push(perSampleNum("rail", g.rail, m.rail.z, 0.5e-4 + 1e-9));
  // P1a: phase; the structure at the rail of the golden's type with the golden's tube; metroTube
  results.push(perSample("phase", unrle(g.phase), (i) => phaseAt(m, c(i)), n));
  const gt = typedFromGolden(line);
  const gType = unrle(g.type);
  const gStruct = unrle(g.struct);
  results.push(
    perSample(
      "struct_of_golden_type",
      gStruct,
      (i) => {
        const sc = TYPES_MODULE.structFor(gt, gType[i] as never, c(i));
        return `${sc.k}|${r4(sc.below)}|${r4(sc.top)}`;
      },
      n,
    ),
  );
  // the type solve
  const T = solveTypes(m);
  const typed: TypedModel = { ...m, types: T, spans: [] };
  results.push(perSample("solved.t", unrle(g.solved.t), (i) => TYPE_CODES[T.type[i] as number], n));
  results.push(perSample("solved.tube", unrle(g.solved.tube), (i) => valueAt(T.tube, i), n));
  results.push(perSample("solved.part", unrle(g.solved.part), (i) => valueAt(T.part, i), n));
  results.push(
    sets(
      "solve.bad",
      s.bad,
      T.bad,
      (b) => `${b.why}|${b.c0}|${b.c1}`,
      (b) => `${b.why}|${b.c0}|${b.c1}`,
    ),
  );
  results.push(pairs("solve.bad.worst", s.bad, T.bad, [["worst", (b) => b.worst, (b) => b.worst, 1e-3]]));
  results.push(
    sets(
      "solve.approaches",
      s.approaches,
      T.approaches,
      (a) => `${a.station}|${a.kind}|${a.side}|${a.river ?? ""}`,
      (a) => `${a.station}|${a.kind}|${a.side}|${a.river ?? ""}`,
    ),
  );
  results.push(
    pairs("solve.approaches.numbers", s.approaches, T.approaches, [
      ["c", (a) => a.c, (a) => a.c, 1e-6],
      ["shift", (a) => a.shift, (a) => a.shift, 1e-9],
      ["len", (a) => a.len, (a) => a.len, 0.01],
    ]),
  );
  const rec = (o: Record<string, string>): string[] => Object.entries(o).map(([k, v]) => `${k}=${v}`);
  results.push(
    sets(
      "solve.platDef",
      rec(s.platDef),
      rec(T.platDef),
      (x) => x,
      (x) => x,
    ),
  );
  results.push(
    sets(
      "solve.stRole",
      rec(s.stRole),
      rec(T.stRole),
      (x) => x,
      (x) => x,
    ),
  );
  results.push(sets("solve.shafts", s.shafts, T.shafts, String, String));
  results.push(
    sets(
      "solve.flags",
      s.flags,
      T.flags,
      (f) => `${f.kind}|${f.c0}|${f.c1}|${flagSev(f)}`,
      (f) => `${f.page}|${f.c0}|${f.c1}|${f.sev}`,
    ),
  );
  results.push({
    output: "solve.flags.raw_count",
    compared: 1,
    differences: s.flags.length === T.flags.length ? [] : [{ at: "count", page: s.flags.length, port: T.flags.length }],
  });
  // the lookups on the port's own solve
  const sa = structArrays(typed);
  results.push(perSample("type", gType, (i) => sa.type[i], n));
  results.push(
    perSample(
      "struct",
      gStruct,
      (i) => {
        const sc = sa.struct[i];
        return sc ? `${sc.k}|${r4(sc.below)}|${r4(sc.top)}` : "";
      },
      n,
    ),
  );
  results.push(perSample("tube_key", unrle(g.tube_key), (i) => tubeKeyAt(typed, c(i)), n));
  results.push(
    perSample(
      "point",
      unrle(g.point),
      (i) => {
        const q = pointType(typed, c(i), m.rail.z[i] as number);
        return "t" in q ? (q.stn ? `${q.t}*` : q.t) : `cls:${q.cls}`;
      },
      n,
    ),
  );
  results.push(
    perSample(
      "grade_limit",
      unrle(g.grade_limit),
      (i) => {
        const L = gradeLimitAt(typed, c(i));
        return `${L.lim}|${L.warn ?? ""}`;
      },
      n,
    ),
  );
  const ll = limitLines(typed, sa.type);
  results.push(perSampleNum("limit_tube", g.limit_tube, ll.limitTube, 1e-4));
  results.push(perSampleNum("limit_box", g.limit_box, ll.limitBox, 1e-4));
  results.push(
    perSample(
      "sgMax",
      d.stations.map((x) => x.sgMax),
      () => sgMaxFor(m),
      d.stations.length,
    ),
  );
  // paints
  const eo = effOvr(m.stations, m.align, m.canon.locks, m.settings.platform, true);
  results.push(
    sets(
      "eff_ovr",
      d.eff_ovr,
      eo,
      (o) => o.join("|"),
      (o) => o.join("|"),
    ),
  );
  results.push(perSample("ovr", unrle(g.ovr), (i) => overrideAt(m, c(i)), n));
  results.push(perSample("tf", unrle(g.tf), (i) => tubeFormAt(m, c(i)), n));
  const stt = sttFromDoc(input.doc, m.stations, input.doc?.ovr ?? []);
  results.push(perSample("stt", d.align.stt, (i) => stt[i], d.align.stt.length));
  const mis = paintMisfits(m);
  const km = (x: { t: string; why: string; c0: number; c1: number; si?: number }): string =>
    `${x.t}|${x.why}|${x.c0}|${x.c1}|${x.si ?? ""}`;
  results.push(sets("misfits", d.misfits, mis, km, km));
  results.push(pairs("misfits.worst", d.misfits, mis, [["worst", (x) => x.worst, (x) => x.worst, 1e-3]]));
  // the grade rules the summary and the curve grade read (gradeLimitOver, sustainedGrade, gradeSeverity)
  const over = d.summary.over as {
    c0: number;
    c1: number;
    L: { lim: number; warn: number | null; why: string };
    su: { avg: number; at: number; W: number };
    sev: string;
  }[];
  const overPort = over.map((o) => {
    const L = gradeLimitOver(typed, o.c0, o.c1);
    const su = sustainedGrade(m, o.c0, o.c1);
    return { L, su, sev: gradeSeverity(L, su.avg) };
  });
  results.push(
    sets(
      "summary.over.limit",
      over,
      overPort,
      (o) => `${o.L.lim}|${o.L.warn}|${whySlug(o.L.why)}|${o.sev}`,
      (o) => `${o.L.lim}|${o.L.warn}|${o.L.why}|${o.sev}`,
    ),
  );
  results.push(
    pairs("summary.over.sustained", over, overPort, [
      ["avg", (o) => o.su.avg, (o) => o.su.avg, 1e-9],
      ["at", (o) => o.su.at, (o) => o.su.at, 1e-9],
      ["W", (o) => o.su.W, (o) => o.su.W, 0],
    ]),
  );
  const cg = d.curve_grade as { c0: number; c1: number; su: { avg: number; at: number; W: number } }[];
  results.push(
    pairs(
      "curve_grade.sustained",
      cg,
      cg.map((r) => sustainedGrade(m, r.c0, r.c1, true)),
      [
        ["avg", (r) => r.su.avg, (r) => r.avg, 1e-6],
        ["at", (r) => r.su.at, (r) => r.at, 1e-9],
      ],
    ),
  );
  return { results, solve: T, typed };
}
