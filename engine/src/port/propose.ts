// The old page's proposers as pure functions (claude/hub_maps/profiles_parity.md, section C, R56 to R60): Lower and
// Raise (regradeDrive 3601-3660), Fix unbuildable (2985-2995), Propose fill (proposeFill 1684-1729, ported in
// checks/fill.ts), Clear (clearMisfit 3595), Solve levels with crossings (solveCross 3693-3720), Reset this line
// (3768-3775) and the paint review (plainTypes, paintRows 2953-2961).
//
// The page changed S.align in place and pushed undo; each of these returns the edit instead, keyed by platform id as
// the profile record keys it: the line sheet lays it on Ben's draft as one undo step, a preview he saves or
// discards. Nothing here words a message: the report carries the numbers and names, the sheet words them.

import type { RuleId } from "../rules.gen.ts";
import {
  CM_PER_M,
  PERMILLE,
  PORT_CHAINAGE_EPS_M,
  PORT_CROSS_TOL,
  PORT_DM_PER_M,
  PORT_FIX_ALL_ROUNDS,
  PORT_IN_PLATFORM_PAD_M,
  PORT_PAINT_SAME_SHARE,
  PORT_REGRADE_CHORD_TOL_M,
  PORT_REGRADE_END_PAD_M,
  PORT_REGRADE_MARGIN_M,
  PORT_REGRADE_MARGIN_STEP_M,
  PORT_REGRADE_MIN_BEND_M,
  PORT_REGRADE_MIN_GRADE_PERMILLE,
  PORT_REGRADE_PASSES,
  PORT_REGRADE_REACH_M,
  PORT_REGRADE_RESERVE_PERMILLE,
  PORT_REGRADE_TOL_M,
} from "../tol.ts";
import { design } from "../vertical/design.ts";
import { railAt } from "../vertical/rail.ts";
import { vertices } from "../vertical/vertices.ts";
import { proposeFill } from "./checks/fill.ts";
import { contextClearances, crossingClearances, needSep, roadsIn } from "./crossings/index.ts";
import { reframeDoc } from "./levels/doc.ts";
import { defaultAlign } from "./levels/levels.ts";
import { buildModel, type SolvedSection, solveSection } from "./model.ts";
import { groundAt, lockedStation, riverAt } from "./structure/at.ts";
import { effOvr, FIT_WHY, fitLim, phaseRules, solveTypes, TYPES_MODULE } from "./structure/index.ts";
import type { LevelNode, Misfit, PortDoc, PortInput, Structure, Type, TypedModel } from "./types.ts";
import { TYPE_CODES } from "./types.ts";

export const PROPOSE_RULES = [
  "era.regrade.straight_grades_no_curve_room",
  "structure.paint.must_fit",
  "ground.propose_fill.within_paint",
  "network.solve_crossings",
  "network.level_solver.shallow_as_grade_allows",
  "geometry.method.paint_final",
] as const satisfies readonly RuleId[];

export type ProposeRequest =
  | {
      readonly kind: "regrade";
      readonly mode: "lower" | "raise";
      readonly c0: number;
      readonly c1: number;
      /** a paint or a selection that does not fit: the rail goes to fitLim of its type and reason */
      readonly fit?: { readonly t: Type; readonly why: Misfit["why"] } | null;
    }
  | { readonly kind: "fix_all" }
  | { readonly kind: "fill"; readonly c0: number; readonly c1: number }
  | { readonly kind: "solve_cross" }
  | { readonly kind: "reset" }
  | { readonly kind: "paint_review" };

/** The edit a proposal makes to the profile, keyed by platform id. Members left out are unchanged. */
export interface ProposalEdit {
  /** the bend points, the whole list */
  pvi?: [number, number][];
  /** station levels to set */
  st?: Record<string, number>;
  /** platform grades to set (0 removes the key) */
  sg?: Record<string, number>;
  /** the drawn ground lines, the whole list */
  gnd?: [number, number][][];
  /** fields to empty (Reset this line) */
  clear?: string[];
  ready?: boolean;
  /** a profile saved in an older frame comes back whole in the current one (reframeDoc) */
  ovr?: [number, number, string][];
  tf?: [number, number, string][];
  shafts?: number[];
  so?: Record<string, number>;
  frame?: PortDoc["frame"];
}

export interface PaintRow {
  list: "ovr" | "tf" | "shafts";
  j: number;
  a: number;
  b: number;
  paint: string;
  /** what the rules give there without any paint (a type, a tube form, or null) */
  rules: string | null;
  same: boolean;
  /** metres of the paint that do not fit */
  misfit: number;
  fill: boolean;
}

export interface Proposal {
  kind: ProposeRequest["kind"];
  changed: boolean;
  rule: RuleId;
  edit: ProposalEdit;
  report: Record<string, unknown>;
  paints?: PaintRow[];
}

// ------------------------------------------------------------------------------------------------------ helpers

const inPlatform = (m: TypedModel, c: number): boolean => {
  const half = m.settings.platform / 2;
  return m.stations.some((s) => c > s.c - half - PORT_IN_PLATFORM_PAD_M && c < s.c + half + PORT_IN_PLATFORM_PAD_M);
};

/** The built line of station levels and bend points on the model's stations (vertices 725 with the page's align). */
function railFn(
  m: TypedModel,
  st: readonly number[],
  sg: readonly number[],
  pvi: readonly { c: number; z: number }[],
): (c: number) => number {
  const S = m.settings;
  const d = design(
    vertices({
      length: m.grid.length,
      platform: S.platform,
      vcRadius: S.vcRadius,
      vcMinLen: S.vcMinLen,
      stations: m.stations.map((s, i) => {
        const z = st[i] as number;
        return { c: s.c, z: Number.isFinite(z) ? z : null, gradePermille: sg[i] ?? 0, order: i };
      }),
      pvi,
    }),
  );
  return (c) => railAt(d, c);
}

/** The design's vertices as chords (chords 828) of a set of levels and bends. */
function chordGrades(
  m: TypedModel,
  st: readonly number[],
  sg: readonly number[],
  pvi: readonly { c: number; z: number }[],
) {
  const S = m.settings;
  const d = design(
    vertices({
      length: m.grid.length,
      platform: S.platform,
      vcRadius: S.vcRadius,
      vcMinLen: S.vcMinLen,
      stations: m.stations.map((s, i) => {
        const z = st[i] as number;
        return { c: s.c, z: Number.isFinite(z) ? z : null, gradePermille: sg[i] ?? 0, order: i };
      }),
      pvi,
    }),
  );
  return { dv: d.dv, railAt: (c: number) => railAt(d, c) };
}

const docOf = (input: PortInput): PortDoc =>
  input.doc ?? {
    st: {},
    sg: {},
    so: {},
    del: [],
    pvi: [],
    ovr: [],
    stt: {},
    tf: [],
    shafts: [],
    gnd: [],
    gapfill: [],
    mode: {},
    ready: false,
    frame: null,
  };

/** The station levels that differ from the doc's, by platform id (to the cm, as the page saved them). */
function levelEdits(m: TypedModel, doc: PortDoc, st: readonly number[]): Record<string, number> {
  const out: Record<string, number> = {};
  m.stations.forEach((s, i) => {
    const z = st[i] as number;
    if (!Number.isFinite(z)) return;
    const v = Math.round(z * CM_PER_M) / CM_PER_M;
    if (doc.st[s.platform_id] !== v) out[s.platform_id] = v;
  });
  return out;
}

const pviPairs = (pvi: readonly { c: number; z: number }[]): [number, number][] =>
  pvi.map((p) => [Math.round(p.c * PORT_DM_PER_M) / PORT_DM_PER_M, p.z]);

/** The input with a doc laid in (the proposers re-solve their own edits). */
const withDoc = (input: PortInput, doc: PortDoc): PortInput => ({ ...input, doc });

/**
 * The edit of a new doc as the page stored it: the doc read back as the page's changed() reads S.align (alignFromDoc
 * with the canon locks laid in, 3141), so a lock's bend points and levels come back as the page kept them. Levels
 * that differ from the old doc's, the whole bend point list.
 */
function editOf(input: PortInput, doc0: PortDoc, doc: PortDoc): ProposalEdit {
  const { model } = buildModel(withDoc(input, doc));
  const extra: ProposalEdit = {};
  if (reframedFrom.has(doc0)) {
    // the profile was saved in an older frame: the page saved the whole profile in the current one (serialize 3213)
    extra.ovr = doc.ovr.map((o) => [o[0], o[1], o[2]]);
    extra.tf = doc.tf.map((o) => [o[0], o[1], o[2]]);
    extra.shafts = doc.shafts.slice();
    extra.gnd = doc.gnd.map((L) => L.map((q) => [q[0], q[1]] as [number, number]));
    extra.so = { ...doc.so };
    extra.frame = doc.frame;
  }
  const st: Record<string, number> = {};
  model.stations.forEach((s, i) => {
    const z = model.align.st[i] as number;
    if (!Number.isFinite(z)) return;
    const v = Math.round(z * CM_PER_M) / CM_PER_M;
    if (doc0.st[s.platform_id] !== v) st[s.platform_id] = v;
  });
  return { ...extra, pvi: pviPairs(model.align.pvi), st };
}

/** Docs this module put in the current frame (reframeDoc): their edits carry every reframed field and the frame. */
const reframedFrom = new WeakSet<PortDoc>();

/** The input with its doc in the current frame (reframeDoc 1839), as the page held S.align after load. */
function current(input: PortInput): PortInput {
  if (!input.doc) return input;
  const r = reframeDoc(input.doc, input.platforms, input.length);
  if (!r.changed) return input;
  const gone = new Set(r.doc.del);
  const doc: PortDoc = {
    ...r.doc,
    frame: {
      length_m: input.length,
      point_c: Object.fromEntries(
        input.platforms.filter((p) => !gone.has(p.platform_id)).map((p) => [p.platform_id, p.point_c]),
      ),
    },
  };
  reframedFrom.add(doc);
  return withDoc(input, doc);
}

/** The doc with levels and bends from arrays on the model's stations. */
function docWith(
  m: TypedModel,
  doc: PortDoc,
  st: readonly number[],
  pvi: readonly { c: number; z: number }[],
): PortDoc {
  return { ...doc, st: { ...doc.st, ...levelEdits(m, doc, st) }, pvi: pviPairs(pvi) };
}

// ------------------------------------------------------------------------------------------ Lower and Raise

export interface RegradeReport {
  mode: "lower" | "raise";
  /** nothing to do */
  nothing: boolean;
  /** a station held by the canon or a lock was in the way: nothing changed */
  blocked: { platform_id: string; name: string } | null;
  c0: number;
  c1: number;
  worst: number;
  lowered: { platform_id: string; name: string; by: number }[];
  under: string[];
  short: { by: number; c: number } | null;
}

/**
 * regradeDrive (3601-3660): the rail over c0..c1 moved to its bound (one tube diameter of cover under the ground to
 * Lower, within the phase's cut-and-cover limit to Raise, or fitLim of a paint that does not fit) plus a margin, as
 * straight grades at most the limit less a reserve, between the platform ends either side; a station in the way
 * moves with its rail at its own grade unless the canon or a lock holds it (then nothing changes). Mutates st and
 * pvi (the arrays of the model's stations) and returns what it did.
 */
export function regradeArrays(
  m: TypedModel,
  st: number[],
  sg: readonly number[],
  pvi: { c: number; z: number }[],
  c0: number,
  c1: number,
  mode: "lower" | "raise",
  lim: ((c: number) => number) | null,
): RegradeReport {
  const S = m.settings;
  const L = m.grid.length;
  const sgn = mode === "raise" ? -1 : 1;
  const T = TYPES_MODULE;
  const bound = (c: number): number => {
    const g = groundAt(m, c);
    if (!Number.isFinite(g)) return Number.POSITIVE_INFINITY;
    if (lim) return sgn * lim(c);
    if (sgn > 0) {
      const sc = T.structFor(m, "shield", c);
      return g - sc.top - (sc.od ?? 0);
    }
    return -(g - phaseRules(m, c).ccMax);
  };
  const step = m.grid.step;
  const n = m.grid.n;
  const reserve = m.literals.regradeReserve ?? PORT_REGRADE_RESERVE_PERMILLE;
  const gm = (Math.max(PORT_REGRADE_MIN_GRADE_PERMILLE, S.maxGrade - reserve) / PERMILLE) * step;
  const half = S.platform / 2;
  const base = { pvi: pvi.map((p) => ({ ...p })), st: st.slice() };
  let margin = m.literals.regradeMargin ?? PORT_REGRADE_MARGIN_M;
  let rail = railFn(m, st, sg, pvi);
  const reset = () => {
    pvi.splice(0, pvi.length, ...base.pvi.map((p) => ({ ...p })));
    st.splice(0, st.length, ...base.st);
    rail = railFn(m, st, sg, pvi);
  };
  const skip = (c: number): boolean => !!riverAt(m, c) || (sgn > 0 && !lim && inPlatform(m, c));
  const iLo = Math.ceil(c0 / step);
  const iHi = Math.min(n - 1, Math.floor(c1 / step));
  const shortOf = (): { by: number; c: number | null } => {
    let short = 0;
    let at: number | null = null;
    for (let i = iLo; i <= iHi; i++) {
      const c = i * step;
      if (skip(c)) continue;
      const v = sgn * rail(c) - bound(c);
      if (v > short) {
        short = v;
        at = c;
      }
    }
    return { by: short, c: at };
  };
  const report: RegradeReport = {
    mode,
    nothing: true,
    blocked: null,
    c0,
    c1,
    worst: 0,
    lowered: [],
    under: [],
    short: null,
  };
  for (let pass = 0; pass < PORT_REGRADE_PASSES; pass++) {
    reset();
    const z = new Float64Array(n);
    const f = new Float64Array(n).fill(Number.POSITIVE_INFINITY);
    for (let i = 0; i < n; i++) z[i] = sgn * rail(Math.min(i * step, L));
    for (let i = iLo; i <= iHi; i++) {
      const c = i * step;
      if (skip(c)) continue; // a box station too deep is raised with its platform
      const bd = bound(c);
      if (Number.isFinite(bd)) f[i] = bd - margin;
    }
    const clampF = () => {
      for (let i = 1; i < n; i++) f[i] = Math.min(f[i] as number, (f[i - 1] as number) + gm);
      for (let i = n - 2; i >= 0; i--) f[i] = Math.min(f[i] as number, (f[i + 1] as number) + gm);
    };
    clampF();
    let i0 = -1;
    let i1 = -1;
    let worst = 0;
    const span = () => {
      i0 = -1;
      i1 = -1;
      for (let i = 0; i < n; i++)
        if ((f[i] as number) < (z[i] as number) - PORT_REGRADE_TOL_M) {
          if (i0 < 0) i0 = i;
          i1 = i;
          worst = Math.max(worst, (z[i] as number) - (f[i] as number));
        }
    };
    span();
    if (i0 < 0) break;
    // a station in the way goes down with the rail (its platform kept at its grade), unless canon or locked
    const lowered: RegradeReport["lowered"] = [];
    for (let k = 0; k < m.stations.length; k++) {
      const s = m.stations[k] as (typeof m.stations)[number];
      const gp = (sg[k] ?? 0) / PERMILLE;
      const a = Math.max(0, Math.ceil((s.c - half) / step));
      const b = Math.min(n - 1, Math.floor((s.c + half) / step));
      let lo = Number.POSITIVE_INFINITY;
      for (let i = a; i <= b; i++) lo = Math.min(lo, (f[i] as number) - sgn * gp * (i * step - s.c));
      if (!(lo < sgn * (st[k] as number) - PORT_REGRADE_TOL_M)) continue;
      if (m.canon.fixed[k] || lockedStation(m, k)) {
        reset();
        return { ...report, nothing: false, blocked: { platform_id: s.platform_id, name: s.name } };
      }
      lowered.push({ platform_id: s.platform_id, name: s.name, by: sgn * (st[k] as number) - lo });
      st[k] = sgn * (Math.floor(lo * CM_PER_M) / CM_PER_M);
      // the rail beyond the lowered platform comes down to it too
      for (let i = a; i <= b; i++) f[i] = Math.min(f[i] as number, sgn * ((st[k] as number) + gp * (i * step - s.c)));
    }
    if (lowered.length) {
      clampF();
      span();
    }
    // the bend points from the platform end before to the one after (at most REACH past the lowered part), so the
    // grades run straight; none on a platform
    const ends = m.stations.flatMap((s) => [s.c - half - PORT_REGRADE_END_PAD_M, s.c + half + PORT_REGRADE_END_PAD_M]);
    const before = Math.max(i0 * step - PORT_REGRADE_REACH_M, ...ends.filter((e) => e < i0 * step));
    const after = Math.min(i1 * step + PORT_REGRADE_REACH_M, ...ends.filter((e) => e > i1 * step));
    const a = Math.max(0, Math.round(before / step));
    const b = Math.min(n - 1, Math.round(after / step));
    const zz = (i: number): number => Math.min(z[i] as number, f[i] as number);
    const keep = new Set<number>([a, b]);
    // the lower hull of the lowered line between platforms: straight grades that never rise above it
    const cuts = [a, b];
    for (const e of ends) {
      const i = Math.round(e / step);
      if (i > a && i < b) cuts.push(i);
    }
    cuts.sort((x, y) => x - y);
    for (const i of cuts) keep.add(i);
    for (let k = 0; k + 1 < cuts.length; k++) {
      const u = cuts[k] as number;
      const v = cuts[k + 1] as number;
      if (inPlatform(m, ((u + v) / 2) * step)) continue;
      const H: number[] = [];
      for (let i = u; i <= v; i++) {
        while (H.length >= 2) {
          const p = H[H.length - 2] as number;
          const q = H[H.length - 1] as number;
          if ((zz(q) - zz(p)) * (i - p) >= (zz(i) - zz(p)) * (q - p)) H.pop();
          else break;
        }
        H.push(i);
      }
      for (const i of H) keep.add(i);
    }
    // no two bends closer than MIN_BEND (a vertical curve needs room): drop one where the chord over it stays under
    for (let again = true; again; ) {
      again = false;
      const K = [...keep].sort((x, y) => x - y);
      for (let k = 1; k + 1 < K.length; k++) {
        const p = K[k - 1] as number;
        const q = K[k + 1] as number;
        const mid = K[k] as number;
        if ((mid - p) * step >= PORT_REGRADE_MIN_BEND_M && (q - mid) * step >= PORT_REGRADE_MIN_BEND_M) continue;
        let ok = true;
        for (let i = p + 1; i < q; i++) {
          const t = zz(p) + ((zz(q) - zz(p)) * (i - p)) / (q - p);
          if (t > zz(i) + PORT_REGRADE_CHORD_TOL_M) {
            ok = false;
            break;
          }
        }
        if (ok) {
          keep.delete(mid);
          again = true;
          break;
        }
      }
    }
    const pts = [...keep]
      .sort((x, y) => x - y)
      .map((i) => ({
        c: Math.round(Math.min(i * step, L) * PORT_DM_PER_M) / PORT_DM_PER_M,
        z: Math.round(sgn * zz(i) * CM_PER_M) / CM_PER_M,
      }))
      .filter((p) => !inPlatform(m, p.c));
    const kept = pvi.filter((p) => p.c < a * step - 1 || p.c > b * step + 1);
    pvi.splice(0, pvi.length, ...[...kept, ...pts].sort((x, y) => x.c - y.c));
    rail = railFn(m, st, sg, pvi);
    const short = shortOf();
    const names = new Set<string>();
    for (const [a0, a1, , name] of m.input.context.streets) if (a1 >= i0 * step && a0 <= i1 * step) names.add(name);
    for (const k of roadsIn(m, i0 * step, i1 * step)) {
      const r = m.input.context.roads[k];
      if (r) {
        const [, , , , name] = r;
        names.add(name);
      }
    }
    Object.assign(report, {
      nothing: false,
      c0: i0 * step,
      c1: i1 * step,
      worst,
      lowered,
      under: [...names],
      short: short.by > PORT_REGRADE_TOL_M ? { by: short.by, c: short.c ?? i0 * step } : null,
    });
    if (short.by <= PORT_REGRADE_TOL_M) break;
    margin += short.by + PORT_REGRADE_MARGIN_STEP_M;
  }
  return report;
}

/** The model's arrays the proposers edit: levels, grades and bends as the page's align holds them. */
function arraysOf(m: TypedModel) {
  return {
    st: m.align.st.slice() as number[],
    sg: m.align.sg.slice() as number[],
    pvi: m.align.pvi.map((p) => ({ c: p.c, z: p.z })),
  };
}

const typedOf = (s: SolvedSection): TypedModel => s.model;

/** Lower or Raise over one stretch, as the issue's button does. */
export function proposeRegrade(input: PortInput, req: Extract<ProposeRequest, { kind: "regrade" }>): Proposal {
  const s = solveSection(input);
  const m = typedOf(s);
  const a = arraysOf(m);
  const lim = req.fit ? fitLim(m, req.fit.t, req.fit.why) : null;
  const r = regradeArrays(m, a.st, a.sg, a.pvi, req.c0, req.c1, req.mode, lim);
  const changed = !r.nothing && !r.blocked;
  const doc = docOf(input);
  return {
    kind: "regrade",
    changed,
    rule: req.fit ? "structure.paint.must_fit" : "era.regrade.straight_grades_no_curve_room",
    edit: changed ? editOf(input, doc, docWith(m, doc, a.st, a.pvi)) : {},
    report: { ...r },
  };
}

// ----------------------------------------------------------------------------------------- Fix unbuildable

/** Fix unbuildable (2985-2995): Lower or Raise every unbuildable stretch and every paint that does not fit, one after
 * the other, up to three rounds (a fix can make the next one); what is left is reported. */
export function proposeFixAll(input: PortInput): Proposal {
  let cur = input;
  const doc0 = docOf(input);
  type Todo = { c0: number; c1: number; mode: "lower" | "raise"; fit: { t: Type; why: Misfit["why"] } | null };
  const todo = (s: SolvedSection): Todo[] => [
    ...s.types.bad.map((b) => ({
      c0: b.c0,
      c1: b.c1,
      mode: (b.why === "cover" ? "lower" : "raise") as "lower" | "raise",
      fit: null,
    })),
    ...s.misfits.map((x) => ({ c0: x.c0, c1: x.c1, mode: FIT_WHY[x.why], fit: { t: x.t, why: x.why } })),
  ];
  let s = solveSection(cur);
  let left = todo(s);
  const n0 = left.length;
  const blocked: { platform_id: string; name: string }[] = [];
  let doc = doc0;
  for (let round = 0; round < PORT_FIX_ALL_ROUNDS && left.length; round++) {
    const sig = JSON.stringify(left);
    for (const x of left) {
      const m = typedOf(s);
      const a = arraysOf(m);
      const r = regradeArrays(m, a.st, a.sg, a.pvi, x.c0, x.c1, x.mode, x.fit ? fitLim(m, x.fit.t, x.fit.why) : null);
      if (r.blocked) blocked.push(r.blocked);
      if (r.nothing || r.blocked) continue;
      doc = docWith(m, doc, a.st, a.pvi);
      cur = withDoc(input, doc);
      s = solveSection(cur);
    }
    left = todo(s);
    if (JSON.stringify(left) === sig) break;
  }
  const m = typedOf(s);
  const changed = doc !== doc0;
  return {
    kind: "fix_all",
    changed,
    rule: "era.regrade.straight_grades_no_curve_room",
    edit: changed ? editOf(input, doc0, doc) : {},
    report: { found: n0, left: left.length, blocked, stations: m.stations.length },
  };
}

// -------------------------------------------------------------------------------------------- Propose fill

/** Propose fill (1684-1729): the drawn line the structure's cover needs, in place of the drawn lines it overlaps. */
export function proposeFillEdit(input: PortInput, c0: number, c1: number): Proposal {
  const s = solveSection(input);
  const m = typedOf(s);
  const f = proposeFill(m, c0, c1, TYPES_MODULE);
  if (!f.line)
    return {
      kind: "fill",
      changed: false,
      rule: "ground.propose_fill.within_paint",
      edit: {},
      report: { c0: f.c0, c1: f.c1, top: 0, points: 0 },
    };
  const first = (f.line[0] as { c: number }).c;
  const last = (f.line[f.line.length - 1] as { c: number }).c;
  const kept = m.align.gnd.filter((Q) => {
    const q0 = (Q[0] as { c: number }).c;
    const q1 = (Q[Q.length - 1] as { c: number }).c;
    return q1 < first || q0 > last;
  });
  const lines = [...kept, f.line].sort((p, q) => (p[0] as { c: number }).c - (q[0] as { c: number }).c);
  return {
    kind: "fill",
    changed: true,
    rule: "ground.propose_fill.within_paint",
    edit: { gnd: lines.map((P) => P.map((p) => [p.c, p.z] as [number, number])) },
    report: { c0: first, c1: last, top: f.top, points: f.line.length, line: lines.indexOf(f.line) },
  };
}

// ----------------------------------------------------------------------------- Solve levels with crossings

/** This line's structure at a crossing from a rail z and the surface (kindAt 2197 with this line's own id). */
function ownKindAt(m: TypedModel, z: number, gr: number, c: number): Structure {
  const S = m.settings;
  const T = TYPES_MODULE;
  const metro = m.input.system !== "rer";
  if (riverAt(m, c)) return T.structFor(m, z >= S.pool + m.literals.bridgeAbovePool ? "elevated" : "sunk", c);
  if (!Number.isFinite(gr)) return T.structFor(m, "atgrade", c);
  if (z - gr >= S.elevAbove) return T.structFor(m, "elevated", c);
  const d = gr - z;
  if (d < S.coverBelow) return T.structFor(m, "atgrade", c);
  if (metro && m.tables && d < m.tables.box.top) return T.structFor(m, "trough", c);
  const sc = T.structFor(m, d >= S.deepBelow ? "deep" : "shield", c);
  return d - sc.top < T.reqCover(m, sc) ? T.structFor(m, "cutcover", c) : sc;
}

/**
 * solveCross (3693-3720): the level solver again with each crossing held at the separation it needs, under the
 * other line where the plain solution is lower and over it where higher (the other side when that fails), one
 * crossing at a time, keeping only those that leave every grade within the limit and the river levels the plain
 * solution met. The station levels and the river bend points are the solver's; the platform grades go to level.
 */
export function proposeSolveCross(input: PortInput): Proposal {
  const s = solveSection(input);
  const m = typedOf(s);
  const S = m.settings;
  const stt = m.align.stt;
  const zeros = m.stations.map(() => 0);
  const solveWith = (cons: readonly LevelNode[]) => defaultAlign(m, null, cons, stt);
  const plain = solveWith([]);
  const vb = chordGrades(m, plain.st, zeros, plain.pvi);
  const xs: { c: number; zo: number; to: Structure }[] = [
    ...crossingClearances(m, TYPES_MODULE)
      .filter((x) => x.zo != null && x.to)
      .map((x) => ({ c: x.c, zo: x.zo as number, to: x.to as Structure })),
    ...contextClearances(m, TYPES_MODULE)
      .filter((x) => {
        const k = m.input.context.blocks[x.block]?.k;
        return k !== "viaduct" && k !== "fill";
      })
      .map((x) => ({ c: x.c, zo: x.zo, to: x.to as unknown as Structure })),
  ];
  const doc = docOf(input);
  if (!xs.length)
    return {
      kind: "solve_cross",
      changed: false,
      rule: "network.solve_crossings",
      edit: {},
      report: { held: 0, of: 0 },
    };
  const ok = (lv: { st: readonly number[]; pvi: readonly { c: number; z: number }[] }, cons: readonly LevelNode[]) => {
    const g = chordGrades(m, lv.st, zeros, lv.pvi);
    const v = g.dv;
    for (let k = 0; k < v.length - 1; k++) {
      const a = v[k] as { c: number; z: number };
      const b = v[k + 1] as { c: number; z: number };
      const d = b.c - a.c;
      if (d > PORT_CHAINAGE_EPS_M && (Math.abs(b.z - a.z) / d) * PERMILLE > S.maxGrade + PORT_CROSS_TOL) return false;
    }
    return cons.every((x) => {
      const z = g.railAt(x.c);
      return (
        (!Number.isFinite(x.ub) || z <= x.ub + PORT_CROSS_TOL) && (!Number.isFinite(x.lb) || z >= x.lb - PORT_CROSS_TOL)
      );
    });
  };
  // the river levels the plain solution already meets must stay met
  const tubeC: LevelNode[] = [];
  for (const r of m.rivers) {
    if (!r.bridge && r.band)
      for (const c of [r.c0, r.c1])
        if (vb.railAt(c) <= r.band.ub + PORT_CROSS_TOL) tubeC.push({ c, ub: r.band.ub, lb: Number.NEGATIVE_INFINITY });
    if (r.bridge && !r.bridge.fixed && r.bridgeBand)
      for (const c of [r.c0, r.c1])
        if (vb.railAt(c) >= r.bridgeBand.lb - PORT_CROSS_TOL)
          tubeC.push({ c, ub: Number.POSITIVE_INFINITY, lb: r.bridgeBand.lb });
  }
  let cons: LevelNode[] = [];
  let held = 0;
  for (const x of xs) {
    const z0 = vb.railAt(x.c);
    const gr = riverAt(m, x.c) ? S.pool : groundAt(m, x.c);
    const k0 = ownKindAt(m, z0, gr, x.c);
    const mine = k0.k === "atgrade" || k0.k === "elevated" ? TYPES_MODULE.structFor(m, "cutcover", x.c) : k0;
    const under: LevelNode = { c: x.c, ub: x.zo - needSep(m, mine, x.to), lb: Number.NEGATIVE_INFINITY };
    const over: LevelNode = {
      c: x.c,
      ub: Number.POSITIVE_INFINITY,
      lb: x.zo + needSep(m, x.to, z0 > gr ? TYPES_MODULE.structFor(m, "elevated", x.c) : k0),
    };
    for (const side of z0 <= x.zo ? [under, over] : [over, under]) {
      const trial = [...cons, side];
      if (ok(solveWith(trial), [...trial, ...tubeC])) {
        cons = trial;
        held++;
        break;
      }
    }
  }
  const fresh = solveWith(cons);
  const sg: Record<string, number> = {};
  for (const s0 of m.stations) if (doc.sg[s0.platform_id]) sg[s0.platform_id] = 0;
  return {
    kind: "solve_cross",
    changed: true,
    rule: "network.solve_crossings",
    edit: { ...editOf(input, doc, { ...docWith(m, doc, fresh.st, fresh.pvi), sg: {} }), sg },
    report: { held, of: xs.length, maxGrade: S.maxGrade, unset: fresh.unset.length },
  };
}

// ----------------------------------------------------------------------------------------------- Reset

/** Reset this line (3768-3775): every station back (no removals, no slides), at the level solver's levels, level
 * platforms, no paints, tube forms, shafts, drawn ground or gap fillers; Ben's access choices stay (they lived
 * outside the old doc). */
export function proposeReset(input: PortInput): Proposal {
  const doc0 = docOf(input);
  const bare: PortDoc = {
    ...doc0,
    st: {},
    sg: {},
    so: {},
    del: [],
    pvi: [],
    ovr: [],
    stt: {},
    tf: [],
    shafts: [],
    gnd: [],
    gapfill: [],
    ready: false,
  };
  // the level solver read the finished ground as it stood, the drawn ground still in it (the page reset S.align and
  // rebuilt the ground after, in changed())
  const { model: m } = buildModel(withDoc(input, { ...bare, gnd: doc0.gnd }));
  const lv = defaultAlign(m, null, [], null);
  const fresh: PortDoc = { ...bare, st: {}, pvi: pviPairs(lv.pvi) };
  m.stations.forEach((x, i) => {
    const z = lv.st[i] as number;
    if (Number.isFinite(z)) (fresh.st as Record<string, number>)[x.platform_id] = Math.round(z * CM_PER_M) / CM_PER_M;
  });
  const e = editOf(input, bare, fresh);
  return {
    kind: "reset",
    changed: true,
    rule: "network.level_solver.shallow_as_grade_allows",
    edit: {
      ...e,
      clear: ["st", "sg", "so", "del", "pvi", "ovr", "stt", "tf", "shafts", "gnd", "gapfill"],
      ready: false,
    },
    report: { stations: m.stations.length, unset: lv.unset.length },
  };
}

// ------------------------------------------------------------------------------------------ the paint review

const FILL_KINDS = new Set(["cutcover", "shield", "deep"]);

/** plainTypes and paintRows (2953-2961): every paint with what the rules would give there without any paint, and
 * whether it only repeats them (the type over more than 95 % of it); the metres of it that do not fit. */
export function paintReview(input: PortInput): Proposal {
  const s = solveSection(input);
  const m = typedOf(s);
  // the page cleared S.align's paints and tube forms (a lock's paints too, as applyLocks had laid them in) and solved
  const metro = m.input.system !== "rer";
  const bareAlign = { ...m.align, ovr: [], tf: [] };
  const pm = {
    ...m,
    align: bareAlign,
    effOvr: effOvr(m.stations, bareAlign, m.canon.locks, m.settings.platform, metro),
  };
  const plain = metro ? solveTypes(pm) : null;
  const step = m.grid.step;
  const major = (a: number, b: number, f: (i: number) => string | null) => {
    if (!plain) return { k: null as string | null, share: 0 };
    const n: Record<string, number> = {};
    for (let i = Math.max(0, Math.ceil(a / step)); i <= Math.min(plain.type.length - 1, Math.floor(b / step)); i++) {
      const k = f(i);
      if (k) n[k] = (n[k] ?? 0) + 1;
    }
    const e = Object.entries(n).sort((x, y) => y[1] - x[1]);
    const tot = e.reduce((t, x) => t + x[1], 0);
    return e.length
      ? { k: (e[0] as [string, number])[0], share: (e[0] as [string, number])[1] / tot }
      : { k: null, share: 0 };
  };
  const typeName = (i: number): string | null => (plain ? (TYPE_CODES[plain.type[i] as number] ?? null) : null);
  const tubeName = (i: number): string | null => {
    if (!plain) return null;
    const t = plain.tube.table[plain.tube.codes[i] as number];
    return t ? (t === "bore" ? "bore" : "twin") : null;
  };
  const misfitIn = (a: number, b: number, t: string): number =>
    s.misfits
      .filter((x) => x.si == null && x.t === t && x.c1 >= a && x.c0 <= b)
      .reduce((L, x) => L + Math.min(b, x.c1) - Math.max(a, x.c0) + step, 0);
  const rows: PaintRow[] = [];
  // the paints as the page listed them (S.align: a lock's paints laid in)
  m.align.ovr.forEach((o, j) => {
    const t = o[2] as string;
    const mj = major(o[0], o[1], typeName);
    rows.push({
      list: "ovr",
      j,
      a: o[0],
      b: o[1],
      paint: t,
      rules: mj.k,
      same: mj.k === t && mj.share > PORT_PAINT_SAME_SHARE,
      misfit: misfitIn(o[0], o[1], t),
      fill: FILL_KINDS.has(t),
    });
  });
  m.align.shafts.forEach((c, j) => {
    rows.push({ list: "shafts", j, a: c, b: c, paint: "shaft", rules: null, same: false, misfit: 0, fill: false });
  });
  m.align.tf.forEach((o, j) => {
    const mj = major(o[0], o[1], tubeName);
    rows.push({
      list: "tf",
      j,
      a: o[0],
      b: o[1],
      paint: o[2],
      rules: mj.k,
      same: mj.k === o[2] && mj.share > PORT_PAINT_SAME_SHARE,
      misfit: 0,
      fill: false,
    });
  });
  rows.sort((x, y) => x.a - y.a);
  return {
    kind: "paint_review",
    changed: false,
    rule: "geometry.method.paint_final",
    edit: {},
    report: { same: rows.filter((r) => r.same).length },
    paints: rows,
  };
}

/** One request on one input. */
export function propose(input0: PortInput, req: ProposeRequest): Proposal {
  const input = current(input0);
  switch (req.kind) {
    case "regrade":
      return proposeRegrade(input, req);
    case "fix_all":
      return proposeFixAll(input);
    case "fill":
      return proposeFillEdit(input, req.c0, req.c1);
    case "solve_cross":
      return proposeSolveCross(input);
    case "reset":
      return proposeReset(input);
    case "paint_review":
      return paintReview(input);
  }
}
