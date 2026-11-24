// The Metro tunnel engine (solveTypes, profiles.html 1341-1604): the method chosen once per stretch between
// anchors, as a transit engineer decides, then the profile checked against it. P1b.
//
//   1. Anchors: box stations, portals, the sunk river box, canon box sections, a change of phase, Ben's shafts
//      (geometry.anchor.kinds, geometry.anchor.shaft_brush). A mined station is inside its drive.
//   2. Ben's decisions are final: a paint sets the method of the stretch it touches (geometry.method.paint_final);
//      a station's type is its selection (station.type.selection_else_limit).
//   3. An unpainted stretch: cut and cover where feasible (geometry.feasibility.box), a bored drive where feasible
//      (geometry.feasibility.drive, geometry.launch_box.full_cover); both: the phase's preference; neither: the
//      nearer, flagged (geometry.method.*).
//   4. Inside a stretch a violation is a flag, never a change of method (geometry.shortfall.flag_not_change).
//   5. Stations; 6. the approaches (structure.approach.spacing_change_in_box) and the tube form of each drive.
//
// The page cached the solve on the profile (VERTS._types); this is pure: the caller caches by input identity. Its
// flags are PortFlag with the page's kind in `page`, deduplicated: the page pushed "a mined station inside a
// cut-and-cover stretch" once per 2 m sample of the platform (1517); here once per station and stretch.

import type { RuleId } from "../../rules.gen.ts";
import {
  CM_PER_M,
  PORT_APPROACH_CHECK_STEP_M,
  PORT_APPROACH_END_SLACK_M,
  PORT_APPROACH_STREET_SEARCH_M,
  PORT_BAD_JOIN_M,
  PORT_CHAINAGE_EPS_M,
  PORT_COVER_TOL_M,
  PORT_SPACING_TOL_M,
  STREET_PAD_M,
} from "../../tol.ts";
import type {
  AnchorRef,
  Approach,
  CodedArray,
  LiveStation,
  Part,
  Phase,
  PhaseRecord,
  PhaseRules,
  PortFlag,
  Role,
  SectionModel,
  Sev,
  StationRole,
  Stretch,
  Structure,
  StructureParams,
  StructureTables,
  TubeForm,
  TubeKey,
  Type,
  TypeSolve,
  Unbuildable,
} from "../types.ts";
import { TYPE_CODES } from "../types.ts";
import { codes, rangesOf } from "../util.ts";
import { canonAt, groundAt, halfPlatform, isRer, railOf, riverAt, streetAtC, subwayStreet, surfaceAt } from "./at.ts";
import { overrideAt } from "./lookup.ts";
import { methodAt, phaseAt, phaseAtStation, phaseRecord, phaseRules, tubeFormAt, twinOf } from "./phase.ts";
import { absorbShort, approachLen, pointType } from "./point.ts";
import { tubeOfKey } from "./tables.ts";

/** The rules the type solve cites in a flag or a stretch. */
export const TYPES_RULES = [
  "geometry.method.per_stretch",
  "geometry.anchor.kinds",
  "geometry.anchor.shaft_brush",
  "geometry.method.paint_final",
  "geometry.method.bank_works",
  "geometry.method.canon_bored",
  "geometry.method.mined_station_forces_drive",
  "geometry.method.both_feasible_phase_prefers",
  "geometry.method.one_feasible",
  "geometry.method.neither_feasible_nearer",
  "geometry.feasibility.box",
  "geometry.feasibility.drive",
  "geometry.launch_box.full_cover",
  "geometry.shortfall.flag_not_change",
  "geometry.portal.min_open_run",
  "geometry.sliver.absorb_only_if_buildable",
  "geometry.method.tbm_from_phase_3",
  "geometry.stretch.note_every_stretch",
  "geometry.band.engine_is_the_drawing",
  "structure.cover.one_diameter_over_tubes",
  "structure.cover.low_cover_warning",
  "structure.box.roof_and_cover_under_ground",
  "structure.box.past_limit_unbuildable",
  "structure.tube_form.ends_plus_paint",
  "structure.tube_form.mined_station_twin",
  "structure.tube_form.twin_type_by_phase",
  "structure.tube_form.stacked_prefer_bore",
  "structure.tube_form.no_spacing_change_in_tunnel",
  "structure.approach.spacing_change_in_box",
  "structure.approach.outside_street_accepted",
  "structure.elevated.decided_by_soffit",
  "structure.paint.must_fit",
  "structure.paint.station_paint_running_line_only",
  "structure.paint.two_paints_one_stretch",
  "structure.sunk_box.river_beats_paint",
  "structure.sunk_box.bank_transition",
  "station.type.selection_else_limit",
  "station.type.mined_in_box_stretch_flagged",
  "station.type.box_roof_out_of_ground_unbuildable",
  "station.phase.earlier_segment",
  "station.approach.part_of_station",
  "station.approach.straight_where_no_arc",
  "platform.default.box_side",
  "platform.default.island_at_open_transfer",
  "platform.default.island_tube_into_box",
  "platform.default.mined_side",
  "era.phase.by_chronology",
  "era.grade.limit_by_phase",
  "era.grade.sustained_vs_local",
] as const satisfies readonly RuleId[];

type Rule = (typeof TYPES_RULES)[number];
type Paint = "cutcover" | "shield" | "deep";

const OPEN = new Set<Type>(["atgrade", "trough", "elevated"]);
/** A context street's name ([c0, c1, width, name, class]). */
const streetName = ([, , , name]: readonly [number, number, number, string, string]): string => name;
const isBoredT = (t: Type | undefined): boolean => t === "shield" || t === "deep";

interface StationDecision {
  s: LiveStation;
  si: number;
  t: Type;
  role: StationRole;
  selected: boolean;
  painted: boolean;
  ds: number;
  island: boolean;
}

/** One sample of the solve's work array (the page's P[i]). d is NaN where the page left it undefined, so every
 * comparison with it falls the same way. */
interface Sample {
  /** the grid index */
  i: number;
  c: number;
  z: number;
  /** the solve's phase (a station's over its platform) */
  ph: Phase;
  /** phaseAt of the sample's own chainage (what the page's phaseTube and twinAt read) */
  pc: Phase;
  R: PhaseRules;
  t: Type | undefined;
  role: Role;
  d: number;
  paint: Paint | null;
  canon: boolean;
  stn: StationDecision | null;
  appr: boolean;
  bank: boolean;
  tube: TubeKey | null;
  shaftAt: boolean;
}

interface Anchor {
  kind: "end" | "side" | "island" | "box" | "river";
  station?: string;
  river?: string;
  sp: number;
  edge: number;
  double?: boolean;
}

const flag = (
  kind: string,
  page: string,
  sev: Sev,
  c0: number,
  c1: number,
  rule: Rule,
  data: Record<string, unknown> = {},
  extra: Partial<Pick<PortFlag, "propose">> = {},
): PortFlag => ({ kind, page, sev, c0, c1, c: (c0 + c1) / 2, rule, data, ...extra });

/** The Metro structure record and its tables, or a throw: the solver is the Metro's. */
function record(m: SectionModel): { MS: StructureParams; T: StructureTables } {
  if (!m.structure || !m.tables || isRer(m)) throw new Error("solveTypes: the Metro solve needs the structure record");
  return { MS: m.structure, T: m.tables };
}

/** solveTypes (1360-1604): the structure of every 2 m sample of the drawn rail, and its findings. */
export function solveTypes(m: SectionModel): TypeSolve {
  const { MS, T } = record(m);
  const S = m.settings;
  const lit = m.literals;
  const { n, step } = m.grid;
  const half = halfPlatform(m);
  const minRun = lit.MIN_RUN;
  const tol = lit.limitTol;
  const P: Sample[] = [];
  const flags: PortFlag[] = [];
  const approaches: Approach[] = [];
  const stretches: Stretch[] = [];
  const runs = (a: number, b: number, f: (p: Sample, i: number) => boolean): [number, number][] => rangesOf(P, a, b, f);
  const at = (i: number): Sample => P[i] as Sample;
  const len = (a: number, b: number): number => at(b).c - at(a).c + step;
  const stIdx = (c: number): number => Math.max(0, Math.min(n - 1, Math.round(c / step)));
  const ccOk = (p: Sample): boolean => p.d <= p.R.ccMax + PORT_CHAINAGE_EPS_M;
  const phaseRec = (ph: Phase): PhaseRecord => phaseRecord(m, ph) as PhaseRecord;
  // phaseAt at a station centre, asked by several steps
  const phaseMemo = new Map<number, Phase>();
  const phaseOf = (c: number): Phase => {
    let v = phaseMemo.get(c);
    if (v === undefined) {
      v = phaseAt(m, c);
      phaseMemo.set(c, v);
    }
    return v;
  };
  const approachM = MS.approach_m || lit.approachFallback;
  // the street at each grid sample, the first in the context's order (streetAtC 452, swept once for the grid)
  const sts = m.input.context.streets;
  const streetIdx = new Int16Array(n).fill(-1);
  sts.forEach((r, k) => {
    const i0 = Math.max(0, Math.ceil((r[0] - STREET_PAD_M) / step));
    const i1 = Math.min(n - 1, Math.floor((r[1] + STREET_PAD_M) / step) + 1);
    for (let i = i0; i <= i1; i++) {
      const c = m.grid.c[i] as number;
      if (streetIdx[i] === -1 && c >= r[0] - STREET_PAD_M && c <= r[1] + STREET_PAD_M) streetIdx[i] = k;
    }
  });
  // the station whose platform covers each grid sample, the first in station order (stationAt 611, swept once)
  const stationIdx = new Int16Array(n).fill(-1);
  m.stations.forEach((s, k) => {
    const i0 = Math.max(0, Math.ceil((s.c - half) / step) - 1);
    const i1 = Math.min(n - 1, Math.floor((s.c + half) / step) + 1);
    for (let i = i0; i <= i1; i++)
      if (stationIdx[i] === -1 && Math.abs((m.grid.c[i] as number) - s.c) <= half) stationIdx[i] = k;
  });
  const streetAtI = (i: number) => (streetIdx[i] === -1 ? undefined : sts[streetIdx[i] as number]);
  // the least depth for a box: its roof plus its cover, the roof alone under a street built over the subway (1367)
  const subway = new Map<string, boolean>();
  const boxNeedOf = (st: (typeof sts)[number] | null | undefined): number => {
    if (!st) return T.box.top + lit.BOX_COVER;
    const [, , , name] = st;
    let sw = subway.get(name);
    if (sw === undefined) {
      sw = subwayStreet(m, name);
      subway.set(name, sw);
    }
    return T.box.top + (sw ? 0 : lit.BOX_COVER);
  };
  /** at grid sample i (its chainage), else at c */
  const boxNeed = (c: number, i = -1): number => boxNeedOf(i >= 0 ? streetAtI(i) : streetAtC(m, c));
  // 1. every sample on its own (1370-1385): an anchor or a tunnel point with its depth and any paint; elevated by
  // the soffit (structure.elevated.decided_by_soffit)
  type Base = Pick<Sample, "t" | "role" | "d" | "paint" | "canon">;
  const mk = (t: Type | undefined, role: Role, d: number, paint: Paint | null, canon: boolean): Base => ({
    t,
    role,
    d,
    paint,
    canon,
  });
  const NaN_ = Number.NaN;
  const base = (c: number, z: number, i = -1): Base => {
    const r = riverAt(m, c);
    if (r && !r.alongShore)
      return z >= S.pool + lit.bridgeAbovePool
        ? mk("elevated", "open", NaN_, null, false)
        : mk("sunk", "river", NaN_, null, false);
    const sec = canonAt(m, c);
    if (sec && sec.m === "covered") {
      const s0 = surfaceAt(m, c);
      return Number.isFinite(s0) && z - S.deckDepth - s0 >= S.elevAbove
        ? mk("elevated", "open", NaN_, null, false)
        : mk("cutcover", "box", NaN_, null, false);
    }
    const g = groundAt(m, c);
    if (!Number.isFinite(g)) return mk("atgrade", "open", NaN_, null, false);
    if (z - S.deckDepth - g >= S.elevAbove) return mk("elevated", "open", NaN_, null, false);
    const d = g - z;
    if (d < S.coverBelow) return mk("atgrade", "open", NaN_, null, false);
    if (d < boxNeed(c, i)) return mk("trough", "open", NaN_, null, false);
    const o = overrideAt(m, c);
    if (o && OPEN.has(o)) return mk(o, "open", NaN_, null, false);
    if (sec && sec.m === "canal") return mk("cutcover", "box", d, null, false);
    const paint = o === "cutcover" || o === "shield" || o === "deep" ? o : null;
    return mk(undefined, "tunnel", d, paint, !!(r || (sec && (sec.m === "shallow" || sec.m === "deep"))));
  };
  // the phase's rules do not depend on the chainage once the phase is known
  const rulesMemo = new Map<Phase, PhaseRules>();
  const rulesOf = (c: number, ph: Phase): PhaseRules => {
    let R = rulesMemo.get(ph);
    if (!R) {
      R = phaseRules(m, c, ph);
      rulesMemo.set(ph, R);
    }
    return R;
  };
  for (let i = 0; i < n; i++) {
    const c = m.grid.c[i] as number;
    const z = m.rail.z[i] as number;
    const k = stationIdx[i] as number;
    const ph = phaseAtStation(m, c, k >= 0 ? (m.stations[k] ?? null) : null);
    const b = base(c, z, i);
    P.push({
      i,
      c,
      z,
      ph,
      pc: ph,
      R: rulesOf(c, ph),
      t: b.t,
      role: b.role,
      d: b.d,
      paint: b.paint,
      canon: b.canon,
      stn: null,
      appr: false,
      bank: false,
      tube: null,
      shaftAt: false,
    });
  }
  // stations (1387-1403): one type for the whole platform; the selection, else a box within the limit, else mined
  const stOf: StationDecision[] = [];
  m.stations.forEach((s, si) => {
    const zc = railOf(m, s.c);
    const q = base(s.c, zc);
    const o = overrideAt(m, s.c);
    const R = rulesOf(s.c, phaseOf(s.c));
    const g = groundAt(m, s.c);
    const ds = Number.isFinite(g) ? g - zc : 0;
    let st: Pick<StationDecision, "t" | "role" | "selected" | "painted">;
    if (o === "cutcover" || (o && OPEN.has(o)))
      st = { t: o, role: o === "cutcover" ? "box" : "open", selected: true, painted: false };
    else if (o === "shield" || o === "deep") st = { t: o, role: "mined", painted: true, selected: true };
    else if (q.role !== "tunnel")
      st = {
        t: q.t as Type,
        role: q.role === "river" ? "open" : (q.role as StationRole),
        selected: false,
        painted: false,
      };
    else if (ds <= R.ccMax) st = { t: "cutcover", role: "box", selected: false, painted: false };
    else st = { t: methodAt(m, s.c, phaseOf(s.c)), role: "mined", selected: false, painted: false };
    const sd: StationDecision = { s, si, ...st, ds, island: st.role === "box" && s.side === "island" };
    stOf.push(sd);
    const ph = phaseOf(s.c);
    for (
      let i = Math.max(0, Math.ceil((s.c - half) / step));
      i <= Math.min(n - 1, Math.floor((s.c + half) / step));
      i++
    )
      Object.assign(at(i), { t: st.t, role: st.role, stn: sd, ph, R });
    const phc = at(stIdx(s.c)).ph;
    if (o === "deep" && !R.tbm)
      flags.push(
        flag(
          "tbm_before_phase_3",
          "Tunnel method",
          "warn",
          s.c - half,
          s.c + half,
          "geometry.method.tbm_from_phase_3",
          {
            station: s.name,
            phase: phc,
          },
        ),
      );
    if (sd.role === "box" && ds > R.ccMax + tol)
      flags.push(
        flag(
          "box_station_past_limit",
          "Tunnel method",
          "warn",
          s.c - half,
          s.c + half,
          "station.type.selection_else_limit",
          {
            station: s.name,
            depth_m: ds,
            cc_max_m: R.ccMax,
            phase: phc,
          },
        ),
      );
  });
  // an open run inside a tunnel shorter than portal_min_m is part of the stretch (1405-1413)
  const portalMin = MS.portal_min_m ?? lit.portalMinFallback;
  for (const [x, y] of runs(0, n - 1, (p) => p.role === "open" && !p.stn)) {
    if (len(x, y) >= portalMin || x === 0 || y === n - 1) continue;
    const a = at(x - 1).role;
    const b = at(y + 1).role;
    if ((a === "tunnel" || a === "mined") && (b === "tunnel" || b === "mined")) {
      for (let i = x; i <= y; i++)
        Object.assign(at(i), {
          role: "tunnel",
          t: undefined,
          d: groundAt(m, at(i).c) - at(i).z,
          paint: null,
          canon: false,
        });
      if (len(x, y) >= minRun)
        flags.push(
          flag("open_run_not_portal", "Tunnel method", "info", at(x).c, at(y).c, "geometry.portal.min_open_run", {
            length_m: len(x, y),
            portal_min_m: portalMin,
          }),
        );
    }
  }
  // shafts Ben painted: a stretch ends there (1415-1417)
  const shafts = m.align.shafts.map((c) => stIdx(+c)).filter((i) => P[i] && at(i).role === "tunnel");
  for (const i of shafts) at(i).shaftAt = true;
  // phaseTube and twinAt (1418-1419) at a sample's own chainage
  const phaseTube = (p: Sample): TubeKey => phaseRec(p.pc).tube;
  const twinAt = (p: Sample): TubeKey => {
    const t = phaseTube(p);
    return t === "bore" ? twinOf(p.pc) : t;
  };
  const boreNeed = T.bore.top + (T.bore.od ?? 0);
  const isTun = (p: Sample | undefined): boolean => !!p && p.role === "tunnel";
  // an anchor next to a stretch: its kind, its track spacing and the edge the approach starts from (1424-1430)
  const anchorAt = (j: number, dir: number): Anchor => {
    const p = P[j];
    if (!p) return { kind: "end", sp: 0, edge: 0 };
    if (p.stn)
      return p.role === "box"
        ? {
            kind: p.stn.island ? "island" : "side",
            station: p.stn.s.name,
            sp: p.stn.island ? MS.island_box.spacing : MS.box.spacing,
            edge: p.stn.s.c + dir * half,
            double: !p.stn.island,
          }
        : { kind: "box", sp: MS.box.spacing, edge: p.c, double: true };
    if (p.role === "river")
      return { kind: "river", river: riverAt(m, p.c)?.name ?? "", sp: MS.box.spacing, edge: p.c, double: true };
    return { kind: "box", sp: MS.box.spacing, edge: p.c, double: true };
  };
  // the approaches (1434-1447): at a drive's end meeting a box, the box carries on until the tracks reach the tubes'
  // spacing; at the river at least approach_m
  const approachAt = (i: number, dir: number): Approach | null => {
    let j = i + dir;
    while (P[j] && at(j).t === "cutcover" && isTun(P[j])) j += dir;
    if (!P[j] || at(j).role === "mined") return null;
    const an = anchorAt(j, -dir);
    if (an.kind === "end") return null;
    const tk = at(i).tube;
    const tb = tk ? MS.tubes[tk] : undefined;
    const shift = ((tb ? tb.spacing : MS.box.spacing) - an.sp) / 2;
    if (Math.abs(shift) < PORT_SPACING_TOL_M && an.kind !== "river") return null;
    const info = {
      station: an.station ?? null,
      kind: an.kind as Approach["kind"],
      ...(an.river !== undefined ? { river: an.river } : {}),
      side: -dir,
      shift,
      c: an.edge,
    };
    const Lm = approachLen(m, shift, at(i).c, info);
    let k = j - dir;
    let last: number | null = null;
    for (; P[k] && Math.abs(at(k).c - an.edge) < Lm + step - PORT_CHAINAGE_EPS_M && isTun(P[k]); k -= dir) {
      const p = at(k);
      p.t = "cutcover";
      p.appr = true;
      if (an.kind === "river") p.bank = true;
      last = k;
    }
    const pk = P[k];
    if (pk && pk.role === "mined" && Math.abs(pk.c - an.edge) < Lm - PORT_CHAINAGE_EPS_M)
      flags.push(
        flag(
          "approach_runs_into_station",
          "Approach box",
          "warn",
          Math.min(an.edge, pk.c),
          Math.max(an.edge, pk.c),
          "station.approach.part_of_station",
          { from: an.station ?? null, into: pk.stn?.s.name ?? null, after_m: Math.abs(pk.c - an.edge), needs_m: Lm },
        ),
      );
    if (last == null) return null;
    const a: Approach = { ...info, len: Math.round(Math.abs(at(last).c - an.edge) * CM_PER_M) / CM_PER_M };
    approaches.push(a);
    return a;
  };
  // tubeKey (1448) at a sample's own chainage (the page reads P[stIdx(c)] for c = p.c, the sample itself)
  const tubeKey = (p: Sample): TubeKey => {
    if (p.tube) return p.tube;
    const f = tubeFormAt(m, p.c);
    return f === "bore" ? "bore" : f === "twin" ? twinAt(p) : phaseTube(p);
  };
  // 3. the stretches (1450-1452): each run of tunnel between anchors, split where the phase changes and at a shaft
  const spans: [number, number][] = [];
  for (const [a0, b0] of runs(0, n - 1, (p) => p.role === "tunnel" || p.role === "mined")) {
    let s = a0;
    for (let i = a0 + 1; i <= b0 + 1; i++)
      if (i > b0 || at(i).ph !== at(s).ph || at(i).shaftAt) {
        spans.push([s, i - 1]);
        s = i;
      }
  }
  const hardF = MS.cost?.cover_hard ?? lit.coverHardFallback;
  const prefOf = (ph: Phase): "cutcover" | "bored" => phaseRec(ph).prefer || (ph === "1" ? "cutcover" : "bored");
  const anchorRef = (j: number, dir: number): AnchorRef => {
    const an = j >= 0 && j < n ? anchorAt(j, dir) : ({ kind: "end", sp: 0, edge: 0 } as Anchor);
    if (an.kind === "end") return { kind: "end" };
    if (an.station) return { kind: "station", station: an.station };
    if (an.kind === "river") return { kind: "river", river: an.river || "river" };
    const p = P[j];
    if (p?.shaftAt) return { kind: "shaft" };
    if (p && p.role === "open") return { kind: "portal" };
    return { kind: "box" };
  };
  for (const [a, b] of spans) {
    const R = at(a).R;
    const span = P.slice(a, b + 1);
    const tun = span.filter(isTun);
    const ph = at(a).ph;
    if (!tun.length) continue; // a mined station alone between anchors
    const mined = span.some((p) => p.role === "mined");
    const canon = tun.some((p) => p.canon);
    // the paint, snapped to the anchors (1462-1466)
    const pc = new Map<Paint, number>();
    for (const p of tun) if (p.paint) pc.set(p.paint, (pc.get(p.paint) ?? 0) + 1);
    const pk = [...pc.keys()].sort((x, y) => (pc.get(y) ?? 0) - (pc.get(x) ?? 0));
    const paint = pk[0] ?? null;
    const painted = paint ? (pc.get(paint) ?? 0) : 0;
    if (pk.length > 1)
      flags.push(
        flag("two_paints_one_stretch", "Painted", "warn", at(a).c, at(b).c, "structure.paint.two_paints_one_stretch", {
          paints: Object.fromEntries(pk.map((k) => [k, (pc.get(k) ?? 0) * step])),
          taken: paint,
        }),
      );
    else if (paint && painted * step < len(a, b) - minRun)
      flags.push(
        flag("paint_snapped", "Painted", "info", at(a).c, at(b).c, "geometry.method.paint_final", {
          paint,
          painted_m: painted * step,
          length_m: len(a, b),
          from: anchorRef(a - 1, 1),
          to: anchorRef(b + 1, -1),
        }),
      );
    // the tube form (1467-1479)
    const L: Anchor = a > 0 ? anchorAt(a - 1, 1) : { kind: "end", sp: 0, edge: 0, double: true };
    const Rt: Anchor = b < n - 1 ? anchorAt(b + 1, -1) : { kind: "end", sp: 0, edge: 0, double: true };
    const ends2 = L.double !== false && Rt.double !== false;
    let form: TubeForm = ends2 && !mined ? "bore" : "twin";
    for (const p of span)
      if (p.role === "mined" && p.stn && tubeFormAt(m, p.c) === "bore" && p.c >= p.stn.s.c - 1 && p.c < p.stn.s.c + 1)
        flags.push(
          flag(
            "bore_through_mined_station",
            "Tube form",
            "warn",
            p.stn.s.c - half,
            p.stn.s.c + half,
            "structure.tube_form.mined_station_twin",
            { station: p.stn.s.name },
          ),
        );
    if (form === "bore") {
      let u = a;
      let v = b;
      const ok = (p: Sample): boolean =>
        p.role === "mined" || !!tubeFormAt(m, p.c) || p.d >= boreNeed - PORT_COVER_TOL_M;
      while (u <= v && !ok(at(u)) && ccOk(at(u))) u++;
      while (v >= u && !ok(at(v)) && ccOk(at(v))) v--;
      if (!(u <= v && len(u, v) >= (u - a + b - v) * step && P.slice(u, v + 1).every(ok))) form = "twin";
    }
    const key = (p: Sample): TubeKey => {
      const f = tubeFormAt(m, p.c) || form;
      return f === "bore" ? "bore" : twinAt(p);
    };
    const tubeOf = (p: Sample): Structure => tubeOfKey(T, key(p));
    const need = (p: Sample): number => {
      const tb = tubeOf(p);
      return tb.top + (tb.od ?? 0);
    };
    const hard = (p: Sample): number => {
      const tb = tubeOf(p);
      return tb.top + (tb.od ?? 0) * hardF;
    };
    // feasibility as drawn (1480-1490)
    const K = Math.max(1, Math.round((MS.approach_m || lit.approachHold) / step));
    const holds = (i: number, dir: number): boolean => {
      for (let k = 0; k <= K; k++) {
        const p = P[i + k * dir];
        if (!p || !isTun(p)) return true;
        if (p.d < need(p) - PORT_COVER_TOL_M) return false;
      }
      return true;
    };
    let u = a;
    let v = b;
    while (u <= v && isTun(P[u]) && !holds(u, 1)) u++;
    while (v >= u && isTun(P[v]) && !holds(v, -1)) v--;
    const launch = P.slice(a, u).concat(P.slice(v + 1, b + 1));
    const launchOk = launch.every((p) => !isTun(p) || ccOk(p));
    const drive = P.slice(u, v + 1).filter(isTun);
    const boxOk = !mined && !canon && tun.every(ccOk);
    const boreOk =
      u <= v && launchOk && (len(u, v) >= R.minDrive || mined) && drive.every((p) => p.d >= hard(p) - PORT_COVER_TOL_M);
    const river = L.kind === "river" || Rt.kind === "river";
    // the decision, in rank order (1491-1506)
    let method: "box" | "bored";
    let why: string;
    let rule: Rule;
    const extra: Record<string, unknown> = {};
    if (paint === "cutcover") {
      method = "box";
      why = "painted_cutcover";
      rule = "geometry.method.paint_final";
    } else if (paint) {
      method = "bored";
      why = "painted_bored";
      rule = "geometry.method.paint_final";
    } else if (river && !mined && len(a, b) < R.minDrive) {
      method = "box";
      why = "bank_works";
      rule = "geometry.method.bank_works";
      for (const p of tun) p.bank = true;
    } else if (canon) {
      method = "bored";
      why = "canon_bored";
      rule = "geometry.method.canon_bored";
    } else if (mined && !boxOk) {
      method = "bored";
      why = "through_mined_station";
      rule = "geometry.method.mined_station_forces_drive";
    } else if (boxOk && boreOk) {
      method = prefOf(ph) === "cutcover" ? "box" : "bored";
      why = "both_feasible_phase_prefers";
      rule = "geometry.method.both_feasible_phase_prefers";
    } else if (boxOk) {
      method = "box";
      why =
        u > v
          ? "too_shallow_for_a_tube"
          : !launchOk
            ? "launch_boxes_past_limit"
            : len(u, v) < R.minDrive
              ? "drive_too_short"
              : "tube_lacks_half_cover";
      if (why === "drive_too_short") Object.assign(extra, { drive_m: len(u, v), min_drive_m: R.minDrive });
      rule = "geometry.method.one_feasible";
    } else if (boreOk) {
      method = "bored";
      why = mined ? "through_mined_station" : "deeper_than_limit";
      rule = "geometry.method.one_feasible";
    } else {
      // neither: the nearer to feasible, flagged
      const boxBad = tun.filter((p) => !ccOk(p)).length;
      const boreBad =
        u > v
          ? tun.length
          : drive.filter((p) => p.d < hard(p) - PORT_COVER_TOL_M).length +
            launch.filter((p) => isTun(p) && !ccOk(p)).length;
      method = mined || boreBad < boxBad || (boreBad === boxBad && prefOf(ph) === "bored") ? "bored" : "box";
      why = "neither_feasible";
      rule = "geometry.method.neither_feasible_nearer";
      Object.assign(extra, { box_bad_m: boxBad * step, bore_bad_m: boreBad * step });
      flags.push(
        flag("stretch_unbuildable", "Tunnel method", "error", at(a).c, at(b).c, rule, {
          length_m: len(a, b),
          from: anchorRef(a - 1, 1),
          to: anchorRef(b + 1, -1),
          method,
          ...extra,
        }),
      );
    }
    let cls: Type | null = null;
    if (method === "box") {
      for (const p of tun) p.t = "cutcover";
      const seen = new Set<number>();
      for (const p of span)
        if (p.role === "mined" && p.stn && !seen.has(p.stn.si)) {
          seen.add(p.stn.si);
          flags.push(
            flag(
              "mined_in_box_stretch",
              "Tunnel method",
              "warn",
              p.stn.s.c - half,
              p.stn.s.c + half,
              "station.type.mined_in_box_stretch_flagged",
              { station: p.stn.s.name },
            ),
          );
        }
    } else {
      if (u > v) {
        u = a;
        v = b;
      }
      cls = paint && paint !== "cutcover" ? paint : methodAt(m, at(a).c, phaseOf(at(a).c));
      for (let i = a; i < u; i++) at(i).t = "cutcover";
      for (let i = v + 1; i <= b; i++) at(i).t = "cutcover";
      for (const p of P.slice(u, v + 1)) {
        if (isTun(p) || (p.role === "mined" && !p.stn?.painted)) p.t = cls;
        p.tube = key(p);
      }
      approachAt(u, -1);
      approachAt(v, 1);
    }
    const boxes: [number, number] = method !== "box" && (u > a || v < b) ? [(u - a) * step, (b - v) * step] : [0, 0];
    const from = anchorRef(a - 1, 1);
    const to = anchorRef(b + 1, -1);
    stretches.push({ c0: at(a).c, c1: at(b).c, a, b, phase: ph, method, why, rule, cls, form, boxes, from, to });
    flags.push(
      flag("stretch", "Tunnel method", "info", at(a).c, at(b).c, "geometry.stretch.note_every_stretch", {
        length_m: len(a, b),
        from,
        to,
        method,
        cls,
        boxes,
        why,
        rule,
        phase: ph,
        ...extra,
      }),
    );
  }
  for (const p of P) if (!p.t) p.t = "cutcover";
  // a painted tube where the box carries on: a note (1524-1526)
  for (const [x, y] of runs(0, n - 1, (p) => {
    const o = overrideAt(m, p.c);
    return (o === "shield" || o === "deep") && p.t === "cutcover" && !p.stn && !riverAt(m, p.c);
  }))
    if (len(x, y) >= minRun)
      flags.push(
        flag("paint_box_carries_on", "Painted", "info", at(x).c, at(y).c, "geometry.launch_box.full_cover", {
          paint: overrideAt(m, at(x).c),
          length_m: len(x, y),
          because: at(x).appr ? "approach" : at(x).bank ? "bank_works" : "until_cover",
        }),
      );
  // no open-track or box sliver shorter than MIN_RUN (1529-1530)
  {
    const TUN = new Set<Type | undefined>(["shield", "deep", "sunk"]);
    absorbShort(
      P,
      step,
      minRun,
      (p) => !p.stn && !p.appr && !TUN.has(p.t),
      (q) => !TUN.has(q.t),
      (p, t) => t !== "cutcover" || groundAt(m, p.c) - p.z >= boxNeed(p.c, p.i) - PORT_CHAINAGE_EPS_M,
    );
  }
  const bored = (p: Sample): boolean => isBoredT(p.t) && !p.stn;
  const tubeOfP = (p: Sample): Structure => tubeOfKey(T, tubeKey(p));
  // the low-cover warnings (1534-1536), on what is still bored
  for (let k = flags.length - 1; k >= 0; k--) if ((flags[k] as PortFlag).propose) flags.splice(k, 1);
  {
    const short = (p: Sample): number => {
      if (!isBoredT(p.t) || riverAt(m, p.c)) return 0;
      const tb = tubeOfP(p);
      const d = groundAt(m, p.c) - p.z;
      return d < tb.top + (tb.od ?? 0) * hardF - tol ? 0 : tb.top + (tb.od ?? 0) - d;
    };
    for (const [x, y] of runs(0, n - 1, (p) => short(p) > lit.lowCoverMinShort)) {
      const worst = Math.max(...P.slice(x, y + 1).map(short));
      flags.push(
        flag(
          "low_cover",
          "Low cover",
          "warn",
          at(x).c,
          at(y).c,
          "structure.cover.low_cover_warning",
          { length_m: len(x, y), worst_m: worst },
          { propose: { c0: at(x).c, c1: at(y).c } },
        ),
      );
    }
  }
  // approach boxes under the street (1539-1548): accepted where they leave it or are wider, a note
  const wall = MS.box.inside - MS.box.spacing;
  const streetAt = (c: number) => sts.find((r) => c >= r[0] - STREET_PAD_M && c <= r[1] + STREET_PAD_M);
  for (const a of approaches) {
    const c0 = a.c;
    const c1 = a.c + a.side * a.len;
    const lo = Math.min(c0, c1);
    const hi = Math.max(c0, c1);
    if (!sts.some((r) => r[0] - PORT_APPROACH_STREET_SEARCH_M <= hi && r[1] + PORT_APPROACH_STREET_SEARCH_M >= lo))
      continue;
    const oS = (a.kind === "island" ? MS.island_box.spacing : MS.box.spacing) / 2;
    const oR = oS + a.shift;
    let off = 0;
    let wide: { w: number; st: (typeof sts)[number] } | null = null;
    for (let c = lo; c <= hi + PORT_APPROACH_END_SLACK_M; c += PORT_APPROACH_CHECK_STEP_M) {
      const w = 2 * (oS + (oR - oS) * Math.min(1, Math.abs(c - c0) / a.len)) + wall;
      const st = streetAt(c);
      if (!st) off += PORT_APPROACH_CHECK_STEP_M;
      else if (w > st[2] + PORT_SPACING_TOL_M && (!wide || w - st[2] > wide.w - wide.st[2])) wide = { w, st };
    }
    if (off || wide)
      flags.push(
        flag("approach_leaves_street", "Approach box", "info", lo, hi, "structure.approach.outside_street_accepted", {
          station: a.station,
          off_m: off,
          ...(wide ? { width_m: wide.w, street: streetName(wide.st), street_width_m: wide.st[2] } : {}),
        }),
      );
  }
  // twin tubes under a street narrower than their footprint (1550-1551): a note
  const narrow = (p: Sample): boolean => {
    if (!(bored(p) && p.tube && p.tube !== "bore")) return false;
    const s = streetAtI(p.i);
    const tb = MS.tubes[p.tube];
    return !!s && s[2] < tb.spacing + tb.outside;
  };
  for (const [x, y] of runs(0, n - 1, narrow))
    if (len(x, y) >= lit.tubeStreetNoteLen) {
      const s = streetAtI(x);
      const tb = MS.tubes[at(x).tube as TubeKey];
      flags.push(
        flag(
          "twin_under_narrow_street",
          "Tube form",
          "info",
          at(x).c,
          at(y).c,
          "structure.tube_form.stacked_prefer_bore",
          {
            street: s ? streetName(s) : null,
            street_width_m: s?.[2] ?? null,
            footprint_m: tb.spacing + tb.outside,
          },
        ),
      );
    }
  // a change of track spacing inside the tunnel (1553-1554)
  {
    const spK = (p: Sample): TubeKey | null => (isBoredT(p.t) && !p.appr ? p.tube : null);
    for (let i = 1; i < n; i++) {
      const a = spK(at(i - 1));
      const b = spK(at(i));
      if (a && b && Math.abs(MS.tubes[a].spacing - MS.tubes[b].spacing) > PORT_SPACING_TOL_M)
        flags.push(
          flag(
            "spacing_change_in_tunnel",
            "Tube form",
            "warn",
            at(i - 1).c,
            at(i).c,
            "structure.tube_form.no_spacing_change_in_tunnel",
            { from: a, to: b },
          ),
        );
    }
  }
  for (const [x, y] of runs(
    0,
    n - 1,
    (p) =>
      tubeFormAt(m, p.c) === "bore" &&
      bored(p) &&
      !riverAt(m, p.c) &&
      groundAt(m, p.c) - p.z < boreNeed - PORT_COVER_TOL_M,
  ))
    if (len(x, y) >= minRun)
      flags.push(
        flag("bore_lacks_cover", "Tube form", "warn", at(x).c, at(y).c, "structure.tube_form.ends_plus_paint", {
          need_m: boreNeed,
        }),
      );
  // A. never draw what cannot be built (1558-1572): a tube under half a diameter of cover, a box past its limit,
  // a box station with its roof out of the ground
  const bad: Unbuildable[] = [];
  {
    const why = P.map((p): Unbuildable["why"] | null => {
      if (riverAt(m, p.c)) return null;
      const t = p.t;
      const d = groundAt(m, p.c) - p.z;
      if (!Number.isFinite(d)) return null;
      if (isBoredT(t)) {
        const tb = tubeOfP(p);
        if (d < tb.top + (tb.od ?? 0) * hardF - tol) return "cover";
      }
      if (t === "cutcover" && !p.bank) {
        const sec = canonAt(m, p.c);
        if (!(sec && (sec.m === "canal" || sec.m === "covered")) && d > p.R.ccMax + tol) return "box";
        if (p.stn && d < T.box.top - tol) return "roof";
      }
      return null;
    });
    const excess = (p: Sample, w: Unbuildable["why"]): number => {
      const d = groundAt(m, p.c) - p.z;
      if (w === "cover") {
        const tb = tubeOfP(p);
        return tb.top + (tb.od ?? 0) - d;
      }
      return w === "roof" ? T.box.top - d : d - p.R.ccMax;
    };
    for (const w of ["cover", "box", "roof"] as const)
      for (const [x, y] of runs(0, n - 1, (_p, i) => why[i] === w)) {
        const prev = bad[bad.length - 1];
        const worst = Math.max(...P.slice(x, y + 1).map((p) => excess(p, w)));
        if (prev && prev.why === w && at(x).c - prev.c1 <= PORT_BAD_JOIN_M) {
          bad[bad.length - 1] = { ...prev, c1: at(y).c, worst: Math.max(prev.worst, worst) };
          continue;
        }
        bad.push({ why: w, c0: at(x).c, c1: at(y).c, worst });
      }
    bad.sort((a, b) => a.c0 - b.c0);
  }
  // the default platform type (1574-1600): a box station side, an island at a transfer open when it opens or where a
  // tube runs straight into it; a mined station side
  const platDef: Record<string, "side" | "island"> = {};
  for (const sd of stOf) {
    const s = sd.s;
    if (sd.role === "mined") {
      platDef[s.key] = "side";
      continue;
    }
    if (sd.role !== "box") continue;
    const reach = approachM + minRun;
    const transfer = s.year != null && s.transferAtOpen;
    let tube = false;
    for (const dir of [-1, 1]) {
      for (let i = stIdx(s.c + dir * half), k = 0; P[i] && k * step <= reach; i += dir, k++) {
        const p = at(i);
        if (p.stn && p.stn.si === sd.si) {
          k = -1;
          continue;
        }
        if (isBoredT(p.t) && !p.stn) {
          tube = true;
          break;
        }
        if (p.t !== "cutcover" || p.stn) break;
      }
    }
    platDef[s.key] = transfer || tube ? "island" : "side";
  }
  const typeCodes = new Uint8Array(n);
  P.forEach((p, i) => {
    typeCodes[i] = TYPE_CODES.indexOf(p.t as Type);
  });
  return {
    grid: m.grid,
    type: typeCodes,
    z: Float64Array.from(m.rail.z),
    tube: codes<TubeKey | null>(
      [null, "A", "C", "bore"],
      P.map((p) => (isBoredT(p.t) && p.tube) || null),
    ),
    part: codes<Part>(
      ["", "a", "S"],
      P.map((p) => (p.appr ? "a" : p.stn ? "S" : "")),
    ),
    phase: codes<Phase>(
      ["1", "2", "3", "later"],
      P.map((p) => p.ph),
    ),
    role: codes<Role>(
      ["open", "river", "box", "tunnel", "mined"],
      P.map((p) => p.role),
    ),
    bad,
    approaches,
    platDef,
    stRole: Object.fromEntries(stOf.map((sd) => [sd.s.key, sd.role])),
    shafts: shafts.map((i) => at(i).c),
    stretches,
    flags,
  };
}

/**
 * openTypes (1319-1331), for the RER and any line without the Metro rules: the point types with the short stretches
 * absorbed, and a short cut-and-cover transition between the sunk box and a bored tunnel at each river bank
 * (structure.sunk_box.bank_transition). Slice 2: ported, not yet checked against a golden.
 */
export function openTypes(m: SectionModel): TypeSolve {
  const { n, step } = m.grid;
  const P: { c: number; z: number; t: Type | undefined }[] = [];
  for (let i = 0; i < n; i++) {
    const c = m.grid.c[i] as number;
    const z = m.rail.z[i] as number;
    const q = pointType(m, c, z);
    P.push({ c, z, t: "t" in q ? q.t : q.cls === "B" ? (q.deep ? "deep" : "shield") : "cutcover" });
  }
  absorbShort(P, step, m.literals.MIN_RUN, (p) => !m.stations.some((s) => Math.abs(p.c - s.c) <= halfPlatform(m)));
  const reach = m.structure?.approach_m || m.literals.approachFallback;
  for (const r of m.rivers)
    for (const [edge, dir] of [
      [r.c0, -1],
      [r.c1, 1],
    ] as const) {
      let i = Math.max(0, Math.min(n - 1, Math.round(edge / step)));
      while (P[i] && riverAt(m, (P[i] as (typeof P)[number]).c)) i += dir;
      const prev = P[i - dir];
      if (prev?.t !== "sunk") continue;
      const c0 = prev.c;
      for (
        ;
        P[i] && isBoredT((P[i] as (typeof P)[number]).t) && Math.abs((P[i] as (typeof P)[number]).c - c0) <= reach;
        i += dir
      )
        (P[i] as (typeof P)[number]).t = "cutcover";
    }
  const empty = <T>(table: T[], v: T): CodedArray<T> =>
    codes(
      table,
      P.map(() => v),
    );
  return {
    grid: m.grid,
    type: Uint8Array.from(P, (p) => TYPE_CODES.indexOf(p.t as Type)),
    z: Float64Array.from(P, (p) => p.z),
    tube: empty<TubeKey | null>([null], null),
    part: empty<Part>([""], ""),
    phase: empty<Phase>(["later"], "later"),
    role: empty<Role>(["open"], "open"),
    bad: [],
    approaches: [],
    platDef: {},
    stRole: {},
    shafts: [],
    stretches: [],
    flags: [],
  };
}
