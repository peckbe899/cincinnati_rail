// station.facts@1: everything the line sheet shows and sets about each station of one section, as data with rule
// ids (claude/hub_maps/profiles_parity.md 0.2). The rail comes from the section's design (vertical.rail@1's own
// geometry, so the two agree); the rest ports the Profiles page:
//
// - the station type, provisional: the station-only part of solveTypes (profiles.html 1384-1403) and pointType
//   (1246-1276). Ben's selection wins; else open by level (elevated, at grade, trough); else a box within the
//   phase's cut-and-cover limit; else mined by the phase's method. The full solver (canon sections, drives) is I2.2;
//   a station inside the canon's canal bed or a drive the solver changed can differ (the tests list each);
// - the access (stationAccess 503-535), the platform curve (2030-2077), the street (458);
// - the station flags of designChecks (2085-2101), stationAccess (519-526) and solveTypes (1401-1402, 2175).
//
// No text for Ben here: kinds, numbers and rule ids. The sheet words them.

import type { AccessType, Flag, StationFact, StationInput, StationPlatform, StationType } from "../contract/index.ts";
import type { RuleId } from "../rules.gen.ts";
import {
  ACCESS_TOL_M,
  BRIDGE_ABOVE_POOL_M,
  LIMIT_TOL,
  OVERLAP_MARGIN_M,
  PASSAGE_M,
  PERMILLE,
  SHAFT_HALF_M,
  STREET_PAD_M,
} from "../tol.ts";
import { sectionDesign } from "../vertical/method.ts";
import { gradeAt, railAt, railGrid } from "../vertical/rail.ts";
import { pathTurns, platformCurve } from "./curve.ts";
import { finishedGround, sampleGround } from "./ground.ts";
import { liveCanon, livePhase } from "./live.ts";

/** The rules station.facts@1 can cite in a flag or a fact. */
export const STATION_FACTS_RULES = [
  "station.type.selection_else_limit",
  "station.type.box_roof_out_of_ground_unbuildable",
  "station.type.mined_in_box_stretch_flagged",
  "station.type.elevated_mezzanine",
  "geometry.method.tbm_from_phase_3",
  "platform.grade.limit_by_era",
  "platform.curvature.gapfill",
  "platform.curvature.no_s_curve",
  "platform.slide.limit_never_clamped",
  "platform.length.by_system",
  "access.type.one_per_station",
  "access.type.elevated",
  "access.type.surface",
  "access.type.mined_hall_or_deep",
  "access.type.shallower_than_d_hall",
  "access.type.halls_by_phase",
  "access.year.fallback_to_line_phase",
  "network.level_solver.shallow_as_grade_allows",
  "road.station.street_known",
] as const satisfies readonly RuleId[];

type Rule = (typeof STATION_FACTS_RULES)[number];
type StationFlag = Flag & { rule: Rule };

/** StationFacts v0 without the two members the host adds. */
export interface StationFactsBody {
  contract: "station_facts/0";
  stations: StationFact[];
  flags: StationFlag[];
  summary: { live: number; removed: number; errors: number; warnings: number };
}

/** A street's name and a road's name, by destructuring (context/lines.json: streets [c0, c1, width, name, class],
 * roads [c, c0, c1, width, name, class]). */
const streetName = ([, , , name]: readonly [number, number, number, string, string]): string => name;
const roadName = ([, , , , name]: readonly [number, number, number, number, string, string]): string => name;

const OPEN = new Set<StationType>(["atgrade", "trough", "elevated"]);
const SELECTABLE = new Set(["cutcover", "shield", "deep", "elevated"]);
const ACCESS_TYPES = new Set<string>([
  "surface",
  "platform_level",
  "platform_level_xu",
  "end_halls",
  "mezzanine",
  "mezzanine_full",
  "mined_hall",
  "deep",
  "elevated_mezzanine",
]);
const HALL_TYPES = new Set<AccessType>(["end_halls", "mezzanine", "mezzanine_full"]);

interface Base {
  t: StationType | null;
  role: "open" | "river" | "box" | "tunnel";
  paint?: string | null;
}

interface Typed {
  t: StationType;
  role: "box" | "mined" | "open";
  why: string;
  /** The drive a mined station is in, when a paint on it decides its method. */
  drive: { method: "box" | "bored"; paint: string; c0: number; c1: number } | null;
}

/** A list of [c0, c1, kind] with [a, b] cut out of it (cutRange, profiles.html 615). */
function cutRange(list: [number, number, string][], a: number, b: number): [number, number, string][] {
  const out: [number, number, string][] = [];
  for (const o of list) {
    if (o[1] <= a || o[0] >= b) {
      out.push(o);
      continue;
    }
    if (o[0] < a) out.push([o[0], a, o[2]]);
    if (o[1] > b) out.push([b, o[1], o[2]]);
  }
  return out;
}

interface Live {
  p: StationPlatform;
  c: number;
  so: number;
  index: number;
}

const fin = (v: number): number | null => (Number.isFinite(v) ? v : null);

export function stationFacts(inp: StationInput): StationFactsBody {
  const sec = inp.section;
  const prm = inp.params;
  const ms = inp.structure;
  const half = prm.platform_m / 2;
  const prof = inp.profile;
  const del = new Set(prof.del ?? []);
  const so = prof.so ?? {};
  const st = prof.st ?? {};
  const sg = prof.sg ?? {};
  const stt = prof.stt ?? {};
  const gapfill = new Set(prof.gapfill ?? []);
  const access = prof.access ?? {};
  const plats = [...inp.platforms].sort((a, b) => a.order - b.order);
  const live: Live[] = [];
  for (const p of plats) {
    if (del.has(p.platform_id)) continue;
    const v = so[p.platform_id];
    const slide = typeof v === "number" ? v : 0;
    live.push({ p, c: p.point_c_m + slide, so: slide, index: live.length });
  }
  // the canon and each station's phase from the live stations, as the old page rebuilt them on every edit (live.ts)
  const canon = liveCanon(
    inp.canon,
    live.map((x) => ({ name: x.p.name, c: x.c })),
    half,
  );
  const phaseOfP = new Map<string, { phase: string; source: string }>();
  for (const x of live) {
    const ph = livePhase(inp.chron_segments, x.c, half);
    phaseOfP.set(
      x.p.platform_id,
      ph ? { phase: ph, source: "chronology" } : { phase: x.p.phase, source: x.p.phase_source },
    );
  }
  const phaseP = (p: StationPlatform): string => phaseOfP.get(p.platform_id)?.phase ?? p.phase;
  const { design: d } = sectionDesign(sec);
  const ground = finishedGround(inp);
  const gAt = (c: number): number => (ground ? sampleGround(ground.fin, ground.step, c) : Number.NaN);
  const demAt = (c: number): number => (ground ? sampleGround(ground.dem, ground.step, c) : Number.NaN);
  const riverAt = (c: number) => inp.rivers.find((r) => c >= r.c0 && c <= r.c1) ?? null;
  const surfaceAt = (c: number): number => (riverAt(c) ? prm.pool_m : gAt(c));
  const dfl = pathTurns(inp.path);
  const streetAt = (c: number) => inp.streets.find((r) => c >= r[0] - STREET_PAD_M && c <= r[1] + STREET_PAD_M);
  const subway = (name: string): boolean =>
    !!ms && ms.subway_streets.some((k) => name.toLowerCase().includes(k.toLowerCase()));
  const phaseOf = (ph: string) => (ms ? (ms.phases[ph] ?? ms.phases.later ?? null) : null);
  const boxTop = (island: boolean): number =>
    ms ? (island ? ms.island_roof_underside_m + (ms.box_top_m - ms.box_roof_underside_m) : ms.box_top_m) : 0;
  const elevNeed = (): number => prm.deck_depth_m + (ms ? ms.mezzanine_clear_m : 0);
  const allFlags: StationFlag[] = [];
  const facts: StationFact[] = [];
  const isMetro = ms !== null;

  // the station types first (one per platform, solveTypes 1384-1392), then the running line's roles, so a mined
  // station takes its drive's method (1505-1515)
  const ccMaxOf = (ph: string): number => phaseOf(ph)?.cc_max_m ?? prm.def_depth_m;
  const canonAt = (c: number) => {
    for (let k = canon.length - 1; k >= 0; k--) {
      const sec = canon[k] as StationInput["canon"][number];
      if (c >= sec.c0 && c <= sec.c1) return sec;
    }
    return null;
  };
  const boxNeed = (c: number): number => {
    const st0 = streetAt(c);
    return boxTop(false) + (st0 && subway(streetName(st0)) ? 0 : prm.box_cover_m);
  };
  // base (1371-1383): a sample on its own, open, a river, a canon box, or tunnel with its paint
  const baseOf = (c: number, z: number, paintAt: (c: number) => string | null): Base => {
    const r = riverAt(c);
    if (r)
      return z >= prm.pool_m + BRIDGE_ABOVE_POOL_M ? { t: "elevated", role: "open" } : { t: "sunk", role: "river" };
    const sec = canonAt(c);
    const g0 = gAt(c);
    if (!Number.isFinite(g0)) return { t: "atgrade", role: "open" };
    if (z - prm.deck_depth_m - g0 >= prm.elev_above_m) return { t: "elevated", role: "open" };
    if (g0 - z < prm.cover_below_m) return { t: "atgrade", role: "open" };
    if (isMetro && g0 - z < boxNeed(c)) return { t: "trough", role: "open" };
    const o = paintAt(c);
    if (o && OPEN.has(o as StationType)) return { t: o as StationType, role: "open" };
    if (sec && sec.m === "canal") return { t: "cutcover", role: "box" };
    return { t: null, role: "tunnel", paint: o === "cutcover" || o === "shield" || o === "deep" ? o : null };
  };
  // the paints as the solver reads them on the Metro (effOvr, 838): a platform takes only its station's selection
  let paints: [number, number, string][] = (prof.ovr ?? []).map((o) => [o[0], o[1], o[2]] as [number, number, string]);
  if (isMetro) for (const x of live) paints = cutRange(paints, x.c - half, x.c + half);
  paints.sort((a, b) => a[0] - b[0]);
  const paintAt = (c: number): string | null => {
    for (let k = paints.length - 1; k >= 0; k--) {
      const o = paints[k] as [number, number, string];
      if (c >= o[0] && c <= o[1]) return o[2];
    }
    return null;
  };
  // A station with no level is read where the sheet draws it, at ground - the default depth (the old page gave it a
  // level from defaultAlign); the design's rail there only when there is no ground. On a line with no design the rail
  // is 0 m, which made a docless line's stations deep bores 220 m down.
  const unsetLevel = (c: number): number => {
    const g = gAt(c);
    return Number.isFinite(g) ? g - prm.def_depth_m : railAt(d, c);
  };
  const types = new Map<string, Typed>();
  for (const x of live) {
    const pid0 = x.p.platform_id;
    const lv0 = st[pid0];
    const z0 = typeof lv0 === "number" ? lv0 : unsetLevel(x.c);
    const s0 = typeof stt[pid0] === "string" && SELECTABLE.has(stt[pid0] as string) ? (stt[pid0] as string) : null;
    // the RER reads the paint at the centre (1384); the Metro the selection
    const o = isMetro ? s0 : paintAt(x.c);
    const q = baseOf(x.c, z0, isMetro ? () => null : paintAt);
    const g0 = gAt(x.c);
    const ds0 = Number.isFinite(g0) ? g0 - z0 : 0;
    const ph0 = phaseOf(phaseP(x.p));
    let ty: Typed;
    if (o === "cutcover" || o === "elevated" || o === "atgrade" || o === "trough")
      ty = { t: o, role: o === "cutcover" ? "box" : "open", why: "selected", drive: null };
    else if (o === "shield" || o === "deep") ty = { t: o, role: "mined", why: "selected", drive: null };
    else if (q.role !== "tunnel")
      ty = {
        t: q.t as StationType,
        role: q.role === "river" ? "open" : (q.role as "box" | "open"),
        why: q.role === "river" ? "river" : q.role === "box" ? "canon_box" : "open",
        drive: null,
      };
    else if (!isMetro || ds0 <= ccMaxOf(phaseP(x.p)))
      ty = { t: "cutcover", role: "box", why: "box_within_limit", drive: null };
    else ty = { t: ph0?.tbm ? "deep" : "shield", role: "mined", why: "mined_past_limit", drive: null };
    types.set(pid0, ty);
  }
  if (isMetro && sec.length_m > 0) {
    const grid = railGrid(d, sec.length_m, 2);
    const role: string[] = new Array(grid.n);
    const paint: (string | null)[] = new Array(grid.n).fill(null);
    const ph: string[] = new Array(grid.n);
    const phaseRun = (c: number): string => inp.phases_along.find((r) => c >= r.c0 && c <= r.c1)?.phase ?? "later";
    for (let i = 0; i < grid.n; i++) {
      const c = grid.c[i] as number;
      const b = baseOf(c, grid.rail[i] as number, paintAt);
      role[i] = b.role;
      paint[i] = b.paint ?? null;
      ph[i] = phaseRun(c);
    }
    for (const x of live) {
      const ty = types.get(x.p.platform_id) as Typed;
      for (
        let i = Math.max(0, Math.ceil((x.c - half) / 2));
        i <= Math.min(grid.n - 1, Math.floor((x.c + half) / 2));
        i++
      ) {
        role[i] = ty.role;
        paint[i] = null;
        ph[i] = phaseP(x.p);
      }
    }
    for (const x of live) {
      const ty = types.get(x.p.platform_id) as Typed;
      if (ty.role !== "mined" || ty.why === "selected") continue;
      const at = Math.max(0, Math.min(grid.n - 1, Math.round(x.c / 2)));
      const inRun = (i: number): boolean => role[i] === "tunnel" || role[i] === "mined";
      let a = at;
      let b = at;
      while (a > 0 && inRun(a - 1) && ph[a - 1] === ph[at]) a--;
      while (b < grid.n - 1 && inRun(b + 1) && ph[b + 1] === ph[at]) b++;
      const count = new Map<string, number>();
      let tun = 0;
      for (let i = a; i <= b; i++) {
        if (role[i] !== "tunnel") continue;
        tun++;
        const k = paint[i];
        if (k) count.set(k, (count.get(k) ?? 0) + 1);
      }
      if (!tun) continue;
      let best: string | null = null;
      for (const [k, v] of count) if (best === null || v > (count.get(best) as number)) best = k;
      const span0: [number, number] = [grid.c[a] as number, grid.c[b] as number];
      if (best === "cutcover")
        types.set(x.p.platform_id, { ...ty, drive: { method: "box", paint: best, c0: span0[0], c1: span0[1] } });
      else if (best)
        types.set(x.p.platform_id, {
          ...ty,
          t: best as StationType,
          why: "drive_paint",
          drive: { method: "bored", paint: best, c0: span0[0], c1: span0[1] },
        });
    }
  }

  for (const p of plats) {
    const pid = p.platform_id;
    const L = live.find((x) => x.p.platform_id === pid) ?? null;
    const flags: StationFlag[] = [];
    const slideV = so[pid];
    const slide = typeof slideV === "number" ? slideV : 0;
    const c = p.point_c_m + slide;
    const lv = st[pid];
    const levelSet = typeof lv === "number";
    const island = p.side === "island";
    const sel = typeof stt[pid] === "string" && SELECTABLE.has(stt[pid] as string) ? (stt[pid] as string) : null;
    const street = streetAt(c);
    const roads = inp.roads.filter((r) => r[2] >= c - half && r[1] <= c + half);
    const known = inp.streets.length > 0 || inp.roads.length > 0;
    const streetFact = {
      text: street ? "under" : roads.length ? "crosses" : known ? "not_under_a_street" : "no_streets_known",
      street: street ? streetName(street) : null,
      subway: street ? subway(streetName(street)) : false,
      roads: roads.map(roadName),
    };
    const sgV = sg[pid];
    const grade = typeof sgV === "number" ? sgV : 0;
    const base = {
      platform_id: pid,
      key: p.key,
      name: p.name,
      order: p.order,
      point_c_m: p.point_c_m,
      slide_m: slide,
      c_m: c,
      half_m: half,
      level_set: levelSet,
      level_m: levelSet ? (lv as number) : null,
      platform_grade_permille: grade,
      grade_limit_permille: prm.sg_max_permille,
      grade_limit_param: prm.sg_max_param,
      selected: sel,
      phase: phaseP(p),
      phase_source: phaseOfP.get(pid)?.source ?? p.phase_source,
      side: island ? ("island" as const) : ("side" as const),
      side_source: p.side_source,
      street: streetFact,
      gapfill: gapfill.has(pid),
      interchanges: [...new Set(p.complex.map((m) => m.name))],
    };
    if (!L) {
      facts.push({
        ...base,
        deleted: true,
        index: null,
        rail_m: null,
        rail_ends_m: null,
        default_level_m: fin(gAt(p.point_c_m) - prm.def_depth_m),
        ground_m: fin(gAt(p.point_c_m)),
        ground_dem_m: fin(demAt(p.point_c_m)),
        depth_m: null,
        grade_in_permille: null,
        grade_out_permille: null,
        type: null,
        type_source: sel ? "ben" : "rule",
        type_why: "no_rail",
        role: null,
        cc_max_m: null,
        structure: null,
        elevated_rail_min_m: null,
        access: null,
        curve: null,
        flags: [],
      });
      continue;
    }
    const z = levelSet ? (lv as number) : unsetLevel(c);
    const g = gAt(c);
    const sf = surfaceAt(c);
    const depth = sf - z;
    const pPhase = phaseP(p);
    const ph = phaseOf(pPhase);
    const ccMax = ph ? ph.cc_max_m : prm.def_depth_m;
    const ds = Number.isFinite(g) ? g - z : 0;
    const { t, role, why, drive } = types.get(pid) as Typed;
    const span: [number, number] = [c - half, c + half];
    const flag = (kind: string, sev: Flag["sev"], rule: Rule, data: Record<string, unknown>): void => {
      flags.push({ kind, sev, c0: span[0], c1: span[1], rule, data: { platform_id: pid, ...data } });
    };
    if (isMetro && sel === "deep" && ph && !ph.tbm)
      flag("station_tbm_before_phase_3", "warn", "geometry.method.tbm_from_phase_3", { phase: pPhase });
    if (drive && drive.method === "box")
      flag("station_mined_in_box_stretch", "warn", "station.type.mined_in_box_stretch_flagged", { ...drive });
    if (isMetro && role === "box" && ds > ccMax + LIMIT_TOL)
      flag("station_box_past_cc_max", "warn", "station.type.selection_else_limit", {
        depth_m: ds,
        cc_max_m: ccMax,
        phase: pPhase,
      });
    if (isMetro && t === "cutcover" && ground) {
      let worst = Number.NEGATIVE_INFINITY;
      for (let i = Math.max(0, Math.ceil(span[0] / ground.step)); i <= Math.floor(span[1] / ground.step); i++) {
        const ci = i * ground.step;
        if (ci > sec.length_m) break;
        const di = gAt(ci) - railAt(d, ci);
        if (di < boxTop(false) - LIMIT_TOL) worst = Math.max(worst, boxTop(false) - di);
      }
      if (worst > 0)
        flag("station_box_roof_out_of_ground", "error", "station.type.box_roof_out_of_ground_unbuildable", {
          worst_m: worst,
          box_top_m: boxTop(false),
        });
    }
    if (!levelSet)
      flag("platform_level_unset", "warn", "network.level_solver.shallow_as_grade_allows", {
        default_level_m: fin(g - prm.def_depth_m),
      });
    if (Math.abs(grade) > prm.sg_max_permille + LIMIT_TOL)
      flag("platform_grade_over", "error", "platform.grade.limit_by_era", {
        grade_permille: grade,
        limit_permille: prm.sg_max_permille,
        param: prm.sg_max_param,
      });
    if (Math.abs(slide) > prm.slide_max_m + LIMIT_TOL)
      flag("platform_slide_over", "error", "platform.slide.limit_never_clamped", {
        slide_m: slide,
        limit_m: prm.slide_max_m,
      });
    const prev = live[L.index - 1];
    if (prev && Math.abs(c - prev.c) < prm.platform_m - OVERLAP_MARGIN_M && prev.p.point_c_m !== p.point_c_m)
      flag("platform_overlap", "error", "platform.length.by_system", {
        other: prev.p.platform_id,
        apart_m: Math.abs(c - prev.c),
      });
    // the platform curve (Metro)
    const curve = isMetro ? platformCurve(inp.path, dfl, sec.length_m, c, prm, gapfill.has(pid)) : null;
    if (curve) {
      if (curve.turns.s)
        flag("platform_s_curve", curve.turns.s === "error" ? "error" : "warn", "platform.curvature.no_s_curve", {
          pos_deg: curve.turns.pos,
          neg_deg: -curve.turns.neg,
        });
      if (curve.level)
        flag(
          "platform_curve",
          curve.level === "error" && !curve.gapfill ? "error" : "warn",
          "platform.curvature.gapfill",
          { R_m: curve.R_m, out_m: curve.out_m, inn_m: curve.inn_m, level: curve.level, gapfill: curve.gapfill },
        );
    }
    // the structure outline
    let structure: StationFact["structure"] = null;
    if (ms && t === "cutcover") structure = { kind: "box", top_m: z + boxTop(island), bottom_m: z - ms.box_below_m };
    else if (ms && (t === "shield" || t === "deep")) {
      const key = ph?.tube ?? "A";
      const tb = ms.tubes[key];
      if (tb) {
        const lining = (tb.outside - tb.inside) / 2;
        structure = {
          kind: key,
          top_m: z + tb.inside - tb.rail_over_invert + lining,
          bottom_m: z - (tb.rail_over_invert + lining),
        };
      }
    } else if (t === "elevated") structure = { kind: "deck", top_m: z, bottom_m: z - prm.deck_depth_m };
    // access (Metro): stationAccess 503-535
    let acc: StationFact["access"] = null;
    if (ms && ph) {
      const dHall = boxTop(island) + ms.hall_clear_m + ms.hall_roof_m + ms.hall_cover_m;
      const dd = Number.isFinite(g) ? g - z : Number.NaN;
      const year = p.year;
      const phase = year !== null ? (p.year_phase ?? pPhase) : pPhase;
      const atOpen = p.complex.filter((m) => m.year !== null && year !== null && m.year <= year);
      const later = p.complex.filter((m) => m.year !== null && year !== null && m.year > year);
      let rule: AccessType;
      let ruleId: Rule;
      if (t === "elevated") {
        rule = "elevated_mezzanine";
        ruleId = "access.type.elevated";
      } else if (OPEN.has(t)) {
        rule = "surface";
        ruleId = "access.type.surface";
      } else if (t === "shield" || t === "deep" || t === "sunk") {
        rule = dd >= ph.deep_from_m ? "deep" : "mined_hall";
        ruleId = "access.type.mined_hall_or_deep";
      } else if (!Number.isFinite(dd)) {
        rule = "platform_level";
        ruleId = "access.type.shallower_than_d_hall";
      } else if (dd < dHall) {
        rule = !island && !atOpen.length ? "platform_level" : "platform_level_xu";
        ruleId = "access.type.shallower_than_d_hall";
      } else {
        rule =
          phase === "1"
            ? "end_halls"
            : phase === "2"
              ? atOpen.length
                ? "mezzanine_full"
                : "mezzanine"
              : "mezzanine_full";
        ruleId = "access.type.halls_by_phase";
      }
      const ov = access[pid];
      const ben = !!ov && ACCESS_TYPES.has(ov.type);
      const type: AccessType = ben ? (ov as { type: AccessType }).type : rule;
      const aflag = (kind: string, sev: Flag["sev"], r: Rule, data: Record<string, unknown>): void =>
        flag(kind, sev, r, { access: type, source: ben ? "ben" : "rule", ...data });
      if (rule === "platform_level_xu" && !ben)
        aflag("access_crossunder", "info", "access.type.shallower_than_d_hall", {
          island,
          interchange: atOpen.length > 0,
          depth_m: dd,
          d_hall_m: dHall,
          short_m: dHall - dd,
        });
      if (year === null && !OPEN.has(t))
        aflag("access_no_year", "warn", "access.year.fallback_to_line_phase", { phase });
      const hall = HALL_TYPES.has(type);
      if (hall && Number.isFinite(dd) && dd < dHall - ACCESS_TOL_M)
        aflag("access_hall_too_shallow", "error", "access.type.halls_by_phase", { depth_m: dd, d_hall_m: dHall });
      const under = Number.isFinite(g) ? z - prm.deck_depth_m - g : Number.NaN;
      if (
        type === "elevated_mezzanine" &&
        (t !== "elevated" || !(under >= elevNeed() - prm.deck_depth_m - ACCESS_TOL_M))
      )
        aflag("access_mezzanine_clearance", "error", "station.type.elevated_mezzanine", {
          need_m: elevNeed() - prm.deck_depth_m,
          under_m: fin(under),
          rail_over_ground_m: elevNeed(),
        });
      if (type !== "elevated_mezzanine" && t === "elevated" && ben)
        aflag("access_not_mezzanine_on_elevated", "warn", "access.type.elevated", {});
      if (hall && (t === "shield" || t === "deep"))
        aflag("access_hall_over_mined", "error", "access.type.mined_hall_or_deep", {});
      const plat = prm.platform_m;
      const mf = prm.mezzanine_fraction / 2;
      const mezzHalls: [number, number][] =
        type === "elevated_mezzanine" && Number.isFinite(g) ? [[c - mf * plat, c + mf * plat]] : [];
      const halls: [number, number][] =
        type === "end_halls"
          ? [
              [c - half, c - half + prm.hall_end_len_m],
              [c + half - prm.hall_end_len_m, c + half],
            ]
          : type === "mezzanine"
            ? [[c - mf * plat, c + mf * plat]]
            : type === "mezzanine_full"
              ? [[c - half, c + half]]
              : [];
      const hallBottom = z + boxTop(island);
      acc = {
        type,
        rule,
        source: ben ? "ben" : "rule",
        rule_id: ben ? "access.type.one_per_station" : ruleId,
        d_hall_m: dHall,
        depth_m: fin(dd),
        island,
        year,
        phase,
        dashed: year === null,
        at_open: atOpen,
        later,
        halls,
        passage: type === "platform_level_xu" ? [c - half, c - half + PASSAGE_M] : null,
        shaft: type === "mined_hall" || type === "deep" ? [c - SHAFT_HALF_M, c + SHAFT_HALF_M] : null,
        hall_bottom_m: hallBottom,
        hall_top_m: hallBottom + ms.hall_clear_m + ms.hall_roof_m,
        mezz: mezzHalls.length
          ? { halls: mezzHalls, bottom_m: g, top_m: Math.min(z - prm.deck_depth_m, g + elevNeed() - prm.deck_depth_m) }
          : null,
        stages: ben ? ((ov as { stages?: unknown[] }).stages ?? []) : [],
      };
    }
    facts.push({
      ...base,
      deleted: false,
      index: L.index,
      rail_m: z,
      rail_ends_m: [z - (grade * half) / PERMILLE, z + (grade * half) / PERMILLE],
      default_level_m: fin(g - prm.def_depth_m),
      ground_m: fin(g),
      ground_dem_m: fin(demAt(c)),
      depth_m: fin(depth),
      grade_in_permille: gradeAt(d, c - half - 1),
      grade_out_permille: gradeAt(d, c + half + 1),
      type: t,
      type_source: why === "selected" ? "ben" : "rule",
      type_why: why,
      role,
      cc_max_m: isMetro ? ccMax : null,
      structure,
      elevated_rail_min_m: isMetro && Number.isFinite(g) ? g + elevNeed() : null,
      access: acc,
      curve,
      flags,
    });
    allFlags.push(...flags);
  }
  allFlags.sort((a, b) => a.c0 - b.c0 || a.c1 - b.c1);
  return {
    contract: "station_facts/0",
    stations: facts,
    flags: allFlags,
    summary: {
      live: live.length,
      removed: plats.length - live.length,
      errors: allFlags.filter((f) => f.sev === "error").length,
      warnings: allFlags.filter((f) => f.sev === "warn").length,
    },
  };
}
