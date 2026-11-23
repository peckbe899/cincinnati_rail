// P4's outputs against the old page's goldens, output by output, within the tolerances of section 6 of
// claude/hub_maps/engine_port_plan.md. Each output gives its differences; report.ts classes them.
//
// The model is the shared adapter's (typedFromGolden: the old page's own upstream values, its type solve laid in);
// P1 is reached through goldenTypes (module.test.ts runs P1's own solve too and checks the two agree). The other
// packages' outputs allIssues gathers are the golden's, as data (input.ts). The levels run on the line's input with
// P2's and P1's real functions as AlignDeps.

import {
  allIssues,
  computeSummary,
  curveAllowance,
  curveGradeRanges,
  designChecks,
  drawingFlags,
  gndChecks,
  proposeFill,
  radii,
  riverChecks,
} from "../../../src/port/checks/index.ts";
import { alignFromDoc, defaultAlign, deriveStations, reframeDoc } from "../../../src/port/levels/index.ts";
import type {
  Align,
  FillProposal,
  PortFlag,
  PortInput,
  Summary,
  TypedModel,
  TypesModule,
} from "../../../src/port/types.ts";
import type { OldAlign, OldIssue, OldPageDump } from "../../golden/old_page/load.ts";
import { fromGolden, goldenMisfits, goldenTypes, typedFromGolden } from "../from_golden.ts";
import type { Difference, OutputResult } from "../report.ts";
import {
  ALIGN_DEPS,
  goldenContext,
  goldenCrossings,
  goldenRoads,
  goldenStationFlags,
  levelInput,
  sevOf,
} from "./input.ts";

const MAX_LISTED = 20;
const MM = 1e-3;
const EPS = 1e-6;
const PERMILLE_TOL = 0.01;

function result(output: string, compared: number, differences: Difference[]): OutputResult {
  return { output, compared, differences: differences.slice(0, MAX_LISTED) };
}

const near = (a: number | null | undefined, b: number | null | undefined, tol: number): boolean => {
  if (a == null || b == null) return a == null && b == null;
  if (!Number.isFinite(a) || !Number.isFinite(b)) return a === b || (Number.isNaN(a) && Number.isNaN(b));
  return Math.abs(a - b) <= tol;
};

/** A number printed with d decimals: the port's value within half a unit of the last digit (and a hair). */
const printed = (page: number, port: number, d: number): boolean => Math.abs(page - port) <= 0.5 * 10 ** -d + 1e-9;

/** Per-sample numbers, exact (Float32 on both sides); Infinity equal to the page's null. */
function exactArray(output: string, page: readonly (number | null)[], port: Float32Array): OutputResult {
  const diffs: Difference[] = [];
  if (page.length !== port.length) diffs.push({ at: "length", page: page.length, port: port.length });
  const n = Math.min(page.length, port.length);
  for (let i = 0; i < n; i++) {
    const a = page[i] ?? Number.POSITIVE_INFINITY;
    const b = port[i] as number;
    if (!(a === b || (Number.isNaN(a) && Number.isNaN(b)))) diffs.push({ at: `${i}`, page: a, port: b });
  }
  return result(output, n, diffs);
}

/**
 * Two lists matched one to one: grouped by key, each group in order of c, compared pairwise by `same`; a group of a
 * different size is a difference.
 */
function matchLists<A, B>(
  output: string,
  page: readonly A[],
  port: readonly B[],
  keyA: (a: A) => string,
  keyB: (b: B) => string,
  cA: (a: A) => number,
  cB: (b: B) => number,
  same: (a: A, b: B) => string | null,
): OutputResult {
  const diffs: Difference[] = [];
  const group = <T>(list: readonly T[], key: (x: T) => string, c: (x: T) => number): Map<string, T[]> => {
    const m = new Map<string, T[]>();
    for (const x of list) {
      const k = key(x);
      const g = m.get(k) ?? [];
      g.push(x);
      m.set(k, g);
    }
    for (const g of m.values()) g.sort((p, q) => c(p) - c(q));
    return m;
  };
  const ga = group(page, keyA, cA);
  const gb = group(port, keyB, cB);
  for (const k of new Set([...ga.keys(), ...gb.keys()])) {
    const a = ga.get(k) ?? [];
    const b = gb.get(k) ?? [];
    if (a.length !== b.length) diffs.push({ at: `${k} count`, page: a.length, port: b.length });
    for (let i = 0; i < Math.min(a.length, b.length); i++) {
      const why = same(a[i] as A, b[i] as B);
      if (why) diffs.push({ at: `${k}[${i}] ${why}`, page: a[i], port: b[i] });
    }
  }
  return result(output, Math.max(page.length, port.length), diffs);
}

// ------------------------------------------------------------------------------------------------ curve arrays

function compareCurve(d: OldPageDump, input: PortInput): { results: OutputResult[]; R: Float32Array; A: Float32Array } {
  const R = radii(input.path, input.length, input.literals);
  const A = curveAllowance(R, input.settings);
  return { results: [exactArray("radii", d.ten.radii, R), exactArray("allowance", d.ten.allowance, A)], R, A };
}

// ------------------------------------------------------------------------------------------------ drawing

const DRAW_KIND = (text: string): string =>
  text.startsWith("Path doubles back")
    ? "path_doubles_back"
    : text.startsWith("Kink")
      ? "path_kink"
      : "single_angle_corner";

function compareDrawing(d: OldPageDump, port: readonly PortFlag[]): OutputResult {
  return matchLists(
    "drawing",
    d.drawing,
    port,
    (a) => `${DRAW_KIND(a.text)}|${a.warn ? "warn" : "error"}`,
    (b) => `${b.kind}|${b.sev}`,
    (a) => a.c,
    (b) => b.c,
    (a, b) => {
      if (!near(a.c, b.c, EPS)) return "c";
      const m = /\((\d+)°\)| of (\d+)°/.exec(a.text);
      const ang = Number(m?.[1] ?? m?.[2]);
      return Math.abs(ang - Number((b.data as { angle: number }).angle)) <= 0.5 ? null : "angle";
    },
  );
}

// ------------------------------------------------------------------------------------------------ ground checks

function compareGround(d: OldPageDump, port: readonly PortFlag[]): OutputResult {
  return matchLists(
    "gnd_checks",
    d.gnd_checks,
    port,
    (a) => sevOf(a.sev),
    (b) => b.sev,
    (a) => a.c,
    (b) => b.c,
    (a, b) => (near(a.c, b.c, MM) ? null : "c"),
  );
}

// ------------------------------------------------------------------------------------------------ curve grade

interface PageCurveGrade {
  c0: number;
  c1: number;
  worst: number;
  g: number;
  add: number;
  L: { lim: number };
  su: { avg: number; at: number; W: number };
  sustained: boolean;
}

function compareCurveGrade(d: OldPageDump, m: TypedModel, T: TypesModule): OutputResult {
  const port = curveGradeRanges(m, T);
  return matchLists(
    "curve_grade",
    d.curve_grade as PageCurveGrade[],
    port,
    () => "r",
    () => "r",
    (a) => a.c0,
    (b) => b.c0,
    (a, b) => {
      if (a.c0 !== b.c0 || a.c1 !== b.c1) return "c0, c1";
      if (!near(a.worst, b.worst, PERMILLE_TOL) || !near(a.g, b.g, PERMILLE_TOL) || !near(a.add, b.add, PERMILLE_TOL))
        return "worst, g, add";
      if (a.L.lim !== b.limit.lim) return "limit";
      if (a.sustained !== b.isSustained || !near(a.su.avg, b.sustained.avg, PERMILLE_TOL)) return "sustained";
      return null;
    },
  );
}

// ------------------------------------------------------------------------------------------------ design checks

/** The page's design check kinds the port keeps in designChecks (the station ones are station.facts', Drawing its
 * own function). */
const DESIGN_PAGE = new Set(["Vertical curve", "Drainage", "Curve grade", "Cover", "Thin cover"]);

const designKey = (kind: string, text: string, warn: boolean): string => {
  if (kind === "Cover") return text.startsWith("Box roof") ? "box_roof_above_ground" : "tube_cover_short";
  if (kind === "Curve grade") return warn ? "curve_grade_local" : "curve_grade_sustained";
  return (
    { "Vertical curve": "vertical_curve_short", Drainage: "drainage_flat", "Thin cover": "box_roof_forms_street" }[
      kind
    ] ?? kind
  );
};

const nums = (text: string): number[] =>
  [...text.replace(/−/g, "-").matchAll(/-?\d+(?:\.\d+)?/g)].map((x) => Number(x[0]));

/** The numbers each design check's text prints, against the port's data, within the printed precision. */
function designNumbers(kind: string, text: string, f: PortFlag): string | null {
  const x = f.data as Record<string, number>;
  const t = text.replace(/−/g, "-");
  if (kind === "vertical_curve_short") {
    const m = /Bend of ([-+]?[\d.]+)‰ at .* needs a (\d+) m curve; only (\d+) m fits/.exec(t);
    if (!m) return "text";
    return printed(Number(m[1]), x.dg as number, 1) &&
      printed(Number(m[2]), x.need as number, 0) &&
      printed(Number(m[3]), x.got as number, 0)
      ? null
      : "dg, need, got";
  }
  if (kind === "drainage_flat") {
    const m = /^([-+]?[\d.]+)‰ in tunnel for (\d+) m/.exec(t);
    if (!m) return "text";
    return printed(Number(m[1]), x.g as number, 1) && printed(Number(m[2]), x.len as number, 0) ? null : "g, len";
  }
  if (kind === "tube_cover_short") {
    const m = /cover down to ([-\d.]+) m from .* needs ([-\d.]+) m/.exec(t);
    if (!m) return "text";
    return printed(Number(m[1]), x.cv as number, 1) && printed(Number(m[2]), x.need as number, 2) ? null : "cv, need";
  }
  if (kind === "box_roof_above_ground") {
    const m = /^Box roof ([-\d.]+) m above ground/.exec(t);
    if (!m) return "text";
    return printed(Number(m[1]), -(x.cv as number), 1) ? null : "cv";
  }
  if (kind === "box_roof_forms_street") {
    const m = /cover down to ([-\d.]+) m from .* \(under ([-\d.]+) m\)/.exec(t);
    if (!m) return "text";
    return printed(Number(m[1]), x.cv as number, 2) && printed(Number(m[2]), x.need as number, 1) ? null : "cv, need";
  }
  return null;
}

function compareDesign(d: OldPageDump, port: { flags: PortFlag[]; sumps: number }): OutputResult[] {
  const page = d.design.checks.filter((x) => DESIGN_PAGE.has(x.kind));
  const checks = matchLists(
    "design.checks",
    page,
    port.flags,
    (a) => `${designKey(a.kind, a.text, !!a.warn)}|${a.warn ? "warn" : "error"}`,
    (b) => `${b.kind}|${b.sev}`,
    (a) => a.c,
    (b) => b.c,
    (a, b) => (near(a.c, b.c, EPS) ? designNumbers(b.kind, a.text, b) : "c"),
  );
  const sumps = result(
    "design.sumps",
    1,
    d.design.sumps === port.sumps ? [] : [{ at: "sumps", page: d.design.sumps, port: port.sumps }],
  );
  return [checks, sumps];
}

// ------------------------------------------------------------------------------------------------ summary

interface PageOver {
  c0: number;
  c1: number;
  g: number;
  L: { lim: number; warn: number | null };
  su: { avg: number; at: number; W: number };
  sev: string;
}

function compareSummary(d: OldPageDump, s: Summary): OutputResult[] {
  const ps = d.summary as unknown as {
    len: Record<string, number>;
    deepest: { d: number; c: number };
    highest: { h: number; c: number };
    maxG: number;
    maxGc: number;
    over: PageOver[];
    deepShallow: { name: string; c: number; d: number }[];
  };
  const out: OutputResult[] = [];
  const lenDiff: Difference[] = [];
  for (const t of Object.keys(s.len)) {
    const a = ps.len[t] ?? 0;
    const b = s.len[t as keyof Summary["len"]];
    if (!near(a, b, EPS)) lenDiff.push({ at: t, page: a, port: b });
  }
  out.push(result("summary.len", Object.keys(s.len).length, lenDiff));
  const ex: Difference[] = [];
  if (!near(ps.deepest.d, s.deepest.d, MM) || ps.deepest.c !== s.deepest.c)
    ex.push({ at: "deepest", page: ps.deepest, port: s.deepest });
  if (!near(ps.highest.h, s.highest.h, MM) || ps.highest.c !== s.highest.c)
    ex.push({ at: "highest", page: ps.highest, port: s.highest });
  if (!near(ps.maxG, s.maxG, PERMILLE_TOL) || !near(ps.maxGc, s.maxGc, EPS))
    ex.push({ at: "maxG", page: [ps.maxG, ps.maxGc], port: [s.maxG, s.maxGc] });
  out.push(result("summary.extremes", 3, ex));
  out.push(
    matchLists(
      "summary.over",
      ps.over,
      s.over,
      (a) => a.sev,
      (b) => b.sev,
      (a) => a.c0,
      (b) => b.c0,
      (a, b) => {
        if (!near(a.c0, b.c0, EPS) || !near(a.c1, b.c1, EPS)) return "c0, c1";
        if (!near(a.g, b.g, PERMILLE_TOL)) return "g";
        if (a.L.lim !== b.limit.lim || (a.L.warn ?? null) !== (b.limit.warn ?? null)) return "limit";
        return near(a.su.avg, b.sustained.avg, PERMILLE_TOL) && near(a.su.at, b.sustained.at, EPS) ? null : "sustained";
      },
    ),
  );
  out.push(
    matchLists(
      "summary.deepShallow",
      ps.deepShallow,
      s.deepShallow,
      () => "s",
      () => "s",
      (a) => a.c,
      (b) => b.c,
      (a, b) => (near(a.c, b.c, EPS) && near(a.d, b.d, MM) ? null : "c, d"),
    ),
  );
  return out;
}

// ------------------------------------------------------------------------------------------------ rivers

interface PageTube {
  kind: string;
  name: string;
  c0: number;
  c1: number;
  c: number;
  over: number;
}

function compareRivers(d: OldPageDump, port: readonly PortFlag[]): OutputResult {
  const page = ((d.summary as unknown as { shallowTubes?: PageTube[] }).shallowTubes ?? []) as PageTube[];
  return matchLists(
    "summary.rivers",
    page,
    port,
    (a) => `${a.kind}|${a.name}`,
    (b) => {
      const x = b.data as { check: string; river: string };
      return `${x.check}|${x.river}`;
    },
    (a) => a.c0,
    (b) => b.c0,
    (a, b) =>
      near(a.c0, b.c0, EPS) &&
      near(a.c1, b.c1, EPS) &&
      near(a.c, b.c, EPS) &&
      near(a.over, (b.data as { over: number }).over, MM)
        ? null
        : "c0, c1, c, over",
  );
}

// ------------------------------------------------------------------------------------------------ issues

/** The key of an issue for removing the page's repeats: a solve flag by what it says (the page pushed the same one
 * per 2 m sample, 1517); any other by its source too (two stations at one point are two findings). */
export const issueKey = (x: OldIssue): string =>
  JSON.stringify([x.kind, x.sev, x.c0, x.c1, x.text, x.src?.[0] === "solve.flags" ? null : x.src]);

/** The page's issues with the solve's exact repeats removed. */
export function distinctIssues(d: OldPageDump): OldIssue[] {
  const seen = new Set<string>();
  return d.issues.filter((x) => {
    const k = issueKey(x);
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

function compareIssues(d: OldPageDump, port: readonly PortFlag[]): OutputResult[] {
  const page = distinctIssues(d);
  const ms: Difference[] = [];
  const count = (list: readonly { k: string }[]): Map<string, number> => {
    const m = new Map<string, number>();
    for (const x of list) m.set(x.k, (m.get(x.k) ?? 0) + 1);
    return m;
  };
  const a = count(page.map((x) => ({ k: `${x.kind}|${sevOf(x.sev)}` })));
  const b = count(port.map((x) => ({ k: `${x.page}|${x.sev}` })));
  for (const k of new Set([...a.keys(), ...b.keys()]))
    if ((a.get(k) ?? 0) !== (b.get(k) ?? 0)) ms.push({ at: k, page: a.get(k) ?? 0, port: b.get(k) ?? 0 });
  const multiset = result("issues.kinds", page.length, ms);
  const ranges = matchLists(
    "issues.ranges",
    page,
    port,
    (x) => `${x.kind}|${sevOf(x.sev)}`,
    (x) => `${x.page}|${x.sev}`,
    (x) => x.c * 1e3 + x.c0 * 1e-3,
    (x) => x.c * 1e3 + x.c0 * 1e-3,
    (x, f) => {
      if (!near(x.c, f.c, EPS)) return "c";
      const tol = x.range_from === "text" ? 1 : EPS;
      if (!near(x.c0, f.c0, tol) || !near(x.c1, f.c1, tol)) return "c0, c1";
      if (!!x.fix !== !!f.fix || (x.fix && f.fix && x.fix.mode !== f.fix.mode)) return "fix";
      if (!!x.propose !== !!f.propose || !!x.clear !== !!f.clear) return "propose, clear";
      if (x.kind === "Clearance" && (x.grp === "pending") !== !!f.pending) return "pending";
      return null;
    },
  );
  const raw = result(
    "issues.raw_count",
    1,
    d.issues.length === port.length ? [] : [{ at: "count", page: d.issues.length, port: port.length }],
  );
  return [multiset, ranges, raw];
}

// ------------------------------------------------------------------------------------------------ levels

function compareLevels(
  output: string,
  page: Pick<OldAlign, "st" | "pvi">,
  port: { st: readonly number[]; pvi: readonly { c: number; z: number }[] },
): OutputResult {
  const diffs: Difference[] = [];
  if (page.st.length !== port.st.length) diffs.push({ at: "st length", page: page.st.length, port: port.st.length });
  page.st.forEach((v, i) => {
    if (!near(v, port.st[i], 0.005 + 1e-9)) diffs.push({ at: `st[${i}]`, page: v, port: port.st[i] });
  });
  if (page.pvi.length !== port.pvi.length)
    diffs.push({ at: "pvi length", page: page.pvi.length, port: port.pvi.length });
  page.pvi.forEach((p, i) => {
    const q = port.pvi[i];
    if (!q || !near(p.c, q.c, 0.05) || !near(p.z, q.z, 0.0005 + 1e-9))
      diffs.push({ at: `pvi[${i}]`, page: p, port: q });
  });
  return result(output, page.st.length + page.pvi.length, diffs);
}

/** The align of alignFromDoc against the page's S.align, member by member, exact (levels from the solver 0.005 m). */
function compareAlign(output: string, page: OldAlign, port: Align): OutputResult {
  const diffs: Difference[] = [];
  const eq = (k: string, a: unknown, b: unknown): void => {
    if (JSON.stringify(a) !== JSON.stringify(b)) diffs.push({ at: k, page: a, port: b });
  };
  const lv = compareLevels(output, page, port);
  diffs.push(...lv.differences);
  eq("sg", page.sg, port.sg);
  eq("so", page.so, port.so);
  eq("del", page.del, port.del);
  eq("ovr", page.ovr, port.ovr);
  eq("stt", page.stt, port.stt);
  eq("tf", page.tf ?? [], port.tf);
  eq("shafts", page.shafts ?? [], port.shafts);
  eq("gnd", page.gnd, port.gnd);
  eq("gapfill", page.gapfill ?? [], port.gapfill);
  eq("ready", !!page.ready, port.ready);
  return result(output, page.st.length + page.pvi.length + 9, diffs);
}

// ------------------------------------------------------------------------------------------------ propose fill

function compareFill(
  d: OldPageDump,
  m: TypedModel,
  T: TypesModule,
): { result: OutputResult; proposals: FillProposal[] } {
  const diffs: Difference[] = [];
  const proposals: FillProposal[] = [];
  for (const [k, p] of d.levels.propose_fill.entries()) {
    const f = proposeFill(m, p.c0, p.c1, T);
    proposals.push(f);
    const nothing = p.msg.startsWith("Nothing to fill");
    if (nothing !== (f.line == null)) {
      diffs.push({ at: `${k} nothing`, page: p.msg, port: f });
      continue;
    }
    const n = nums(p.msg.replace(/(\d+)\+(\d{3})/g, (_, a, b) => String(Number(a) * 1000 + Number(b))));
    if (nothing) {
      if (!printed(n[0] as number, f.c0, 0) || !printed(n[1] as number, f.c1, 0))
        diffs.push({ at: `${k} range`, page: p.msg, port: [f.c0, f.c1] });
      continue;
    }
    const line = f.line ?? [];
    const added = p.added[0] ?? [];
    if (!printed(n[2] as number, f.top, 1) || n[3] !== line.length)
      diffs.push({ at: `${k} top, points`, page: p.msg, port: [f.top, line.length] });
    if (p.added.length !== 1 || added.length !== line.length)
      diffs.push({ at: `${k} added`, page: p.added, port: line });
    else
      added.forEach((q, j) => {
        const r = line[j] as { c: number; z: number };
        if (!near(q.c, r.c, 0.05) || !near(q.z, r.z, 0.005 + 1e-9))
          diffs.push({ at: `${k} point ${j}`, page: q, port: r });
      });
  }
  return { result: result("propose_fill", d.levels.propose_fill.length, diffs), proposals };
}

// ------------------------------------------------------------------------------------------------ one line

export interface LineRun {
  results: OutputResult[];
  issues: PortFlag[];
  summary: Summary;
  /** the levels of every run, for the named tests */
  reframe: ReturnType<typeof reframeDoc> | null;
  input: PortInput;
}

/** Every output of one line on the golden-fed model (the old page's own type solve, through goldenTypes). */
export function compareLine(line: string): LineRun {
  return runLine(line, typedFromGolden(line));
}

/** Every output of one line on a model and a type lookup (module.test.ts: P1's own solve and TYPES_MODULE). */
export function runLine(line: string, m: TypedModel, T0?: TypesModule): LineRun {
  const dump = fromGolden(line).dump;
  const T = T0 ?? goldenTypes(dump);
  const input = levelInput(line);
  const results: OutputResult[] = [];
  const curve = compareCurve(dump, input);
  results.push(...curve.results);
  const metro = input.system !== "rer";
  const drawing = metro ? drawingFlags(input.path, input.pieces, input.literals) : [];
  results.push(compareDrawing(dump, drawing));
  const ground = gndChecks(m);
  results.push(compareGround(dump, ground));
  results.push(compareCurveGrade(dump, m, T));
  const design = designChecks(m, T);
  results.push(...compareDesign(dump, design));
  const summary = computeSummary(m, T);
  results.push(...compareSummary(dump, summary));
  const rivers = riverChecks(m, T);
  results.push(compareRivers(dump, rivers));
  const issues = allIssues(
    {
      over: summary.over,
      crossings: goldenCrossings(dump),
      context: goldenContext(dump),
      rivers,
      roads: goldenRoads(dump, m.input),
      stations: goldenStationFlags(dump),
      deepShallow: summary.deepShallow,
      checks: [...design.flags, ...drawing],
      ground,
      types: m.types,
      misfits: goldenMisfits(dump),
    },
    { half: m.settings.platform / 2 },
  );
  results.push(...compareIssues(dump, issues));
  // the level solver on the live, slid stations, with the line's selections (alignFromDoc's call)
  const da = defaultAlign(
    m,
    null,
    [],
    dump.align.stt.map((t) => (t === "" ? "" : (t as Align["stt"][number]))),
  );
  results.push(compareLevels("levels.default_align", dump.levels.default_align, da));
  // the saved profile read (alignFromDoc and changed()), and Reset this line (alignFromDoc(null))
  const read = alignFromDoc(input, ALIGN_DEPS);
  results.push(compareAlign("align", dump.align, read.align));
  const reset = alignFromDoc({ ...input, doc: null }, ALIGN_DEPS);
  results.push(compareAlign("levels.reset", dump.levels.reset, reset.align));
  const live = deriveStations(input, dump.align.del, dump.align.so);
  const st: Difference[] = [];
  if (live.length !== dump.stations.length) st.push({ at: "count", page: dump.stations.length, port: live.length });
  dump.stations.forEach((s, i) => {
    const q = live[i];
    if (!q || q.key !== s.key || !near(q.c, s.c, 1e-9) || !near(q.point_c, s.point_c, 1e-9))
      st.push({ at: `${i}`, page: s, port: q });
  });
  results.push(result("stations", dump.stations.length, st));
  // reframe: the page's dump applied it to a doc it had already reframed on load (see the named test)
  const reframe = input.doc ? reframeDoc(input.doc, input.platforms, input.length) : null;
  const rf: Difference[] = [];
  const pr = dump.levels.reframe;
  if ((pr?.changed ?? false) !== (reframe?.changed ?? false))
    rf.push({ at: "changed", page: pr?.changed, port: reframe?.changed });
  else if (pr?.changed && reframe) {
    const want = pr as unknown as {
      pvi: [number, number][];
      ovr: [number, number, string][];
      so: Record<string, number>;
    };
    const got = reframe.doc;
    if (JSON.stringify(want.pvi) !== JSON.stringify(got.pvi)) rf.push({ at: "pvi", page: want.pvi, port: got.pvi });
    if (JSON.stringify(want.ovr) !== JSON.stringify(got.ovr)) rf.push({ at: "ovr", page: want.ovr, port: got.ovr });
    if (JSON.stringify(want.so) !== JSON.stringify(got.so)) rf.push({ at: "so", page: want.so, port: got.so });
  }
  results.push(result("levels.reframe", 1, rf));
  results.push(compareFill(dump, m, T).result);
  return { results, issues, summary, reframe, input };
}
