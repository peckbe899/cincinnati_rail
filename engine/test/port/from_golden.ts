// The port's input and model for one line as the old page had them (claude/hub_maps/engine_port_plan.md, section 2):
// every package's tests build what they need here, from a golden of engine/test/golden/old_page plus read-only
// repository files, so each package is tested on the old page's own upstream values.
//
// - the input from the line file (data/profile/lines), the seed doc (hub/seed/alignments), hub/seed/params
//   (metro_structure, station_platforms, approach_extra), context/lines.json, the registry's literal.* values and
//   the golden's settings, era, canon_record and Chronology segments;
// - the model's P2 and P4 parts from the golden: ground layers, rivers, canon, sunk box, align, eff_ovr, the curve
//   arrays, the halls; the rail from the existing vertical design on the golden's align (the golden's rail is
//   rounded to 0.1 mm; the design gives the page's own doubles, checked in test/port/structure);
// - neighbours are left empty: P3 builds them (section 3.3) in its own extension of this adapter.

import { readFileSync } from "node:fs";
import { parse } from "yaml";
import { TYPES_MODULE } from "../../src/port/structure/index.ts";
import { applyMS } from "../../src/port/structure/tables.ts";
import type {
  Align,
  ApproachExtra,
  CanonModel,
  CanonRecord,
  CanonSection,
  ChrSegment,
  CrossGround,
  CrossingRecord,
  FixedLevel,
  GroundLayers,
  HallSpan,
  LiveStation,
  Lock,
  Misfit,
  Phase,
  PortDoc,
  PortFlag,
  PortInput,
  PortLiterals,
  PortPlatform,
  PortSettings,
  Range3,
  RiverModel,
  RiverRecord,
  SectionModel,
  SelectedType,
  StructureParams,
  TubeForm,
  TubeKey,
  Type,
  TypedModel,
  TypeSolve,
  TypesModule,
  ViaductSpan,
} from "../../src/port/types.ts";
import { TYPE_CODES } from "../../src/port/types.ts";
import { codes, gridOf } from "../../src/port/util.ts";
import { design } from "../../src/vertical/design.ts";
import { railGrid } from "../../src/vertical/rail.ts";
import { vertices } from "../../src/vertical/vertices.ts";
import { ground, loadOldPage, type OldAlign, type OldPageDump, unrle } from "../golden/old_page/load.ts";

export const REPO = new URL("../../../", import.meta.url);
const readJson = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, REPO), "utf8")) as T;

/** The 16 Metro lines of the goldens. */
export const METRO_LINES = [
  "Line_1",
  "Line_2",
  "Line_2b",
  "Line_3",
  "Line_4",
  "Line_5",
  "Line_6",
  "Line_7",
  "Line_8",
  "Line_9",
  "Line_10",
  "Line_11",
  "Line_12",
  "Line_13",
  "Line_14",
  "CVG_Express",
] as const;

const FT = 0.3048;

interface LineFile {
  id: string;
  length_m: number;
  step_m: number;
  path: [number, number, number][];
  stations: { name: string; c: number; trunk?: boolean }[];
  pieces?: { name: string; c0: number; c1: number }[];
  crossings?: { c: number; wid: string; oc: number; kind: string; with: string }[];
  rivers?: { name: string; c0: number; c1: number }[];
  settings?: Record<string, number>;
}

interface SeedDoc {
  st?: Record<string, number | null>;
  sg?: Record<string, number>;
  so?: Record<string, number>;
  del?: string[];
  pvi?: [number, number][];
  ovr?: [number, number, string][];
  stt?: Record<string, string>;
  tf?: [number, number, string][];
  shafts?: number[];
  gnd?: [number, number][][];
  gapfill?: string[];
  mode?: Record<string, "under" | "surface">;
  ready?: boolean;
  length_m?: number;
}

type MetroStructureFile = Omit<StructureParams, "line_phase" | "piece_phase" | "mezzanine_clear_m"> & {
  line_phase: Record<string, Phase>;
  piece_phase: Record<string, Record<string, Phase>>;
  elevated_station?: { mezzanine_clear_m?: number };
  mezzanine_clear_m?: number;
};

const cache = new Map<string, unknown>();
function once<T>(key: string, make: () => T): T {
  if (!cache.has(key)) cache.set(key, make());
  return cache.get(key) as T;
}

export const lineFile = (line: string): LineFile =>
  once(`line:${line}`, () => readJson<LineFile>(`data/profile/lines/${line}.json`));

export function seedDoc(line: string): SeedDoc | null {
  return once(`seed:${line}`, () => {
    try {
      return readJson<SeedDoc>(`hub/seed/alignments/${line}.json`);
    } catch {
      return null;
    }
  });
}

/** The registry's param values by path (rules/registry.yaml, read only). */
export function registryParams(): Map<string, unknown> {
  return once("registry", () => {
    const r = parse(readFileSync(new URL("rules/registry.yaml", REPO), "utf8")) as {
      params: { path: string; value: unknown }[];
    };
    return new Map(r.params.map((p) => [p.path, p.value]));
  });
}

/**
 * The literals from the registry's literal.* values. Where the registry has no param, or holds an expression or a
 * sentence (the plan's section 3.4, reported to the lead), the page's own value, named here.
 */
export function literals(): PortLiterals {
  const reg = registryParams();
  const num = (path: string, page: number): number => {
    const v = reg.get(path);
    return typeof v === "number" ? v : page;
  };
  return {
    MIN_RUN: num("literal.MIN_RUN", 20),
    BOX_COVER: num("literal.BOX_COVER", 0.6),
    SEP_GAP: num("literal.SEP_GAP", 0.5),
    BED_DEPTH: num("literal.BED_DEPTH", 0.8),
    VIA_SPAN: num("literal.VIA_SPAN", 25),
    VIA_CLEAR: num("literal.VIA_CLEAR", 7),
    RIVER_SPAN: num("literal.RIVER_SPAN", 120),
    GIRDER_MAX: num("literal.GIRDER_MAX", 40),
    girder: { ratio: 10, add: 0.8 }, // literal.girder_soffit is the expression "span / 10 + 0.8"
    trussRatio: 8, // literal.truss_depth is "span / 8"
    DECK_ON: 5, // no param (864)
    GND_W: num("literal.GND_W", 15),
    SLIDE_M: num("literal.SLIDE_M", 150),
    CAR_LEN: num("literal.CAR_LEN", 15.56),
    END_DOOR: num("literal.END_DOOR", 5.4),
    PLAT_R_ERR: num("literal.PLAT_R_ERR", 600),
    PLAT_R_WARN: num("literal.PLAT_R_WARN", 3000),
    DRAW: {
      single: num("literal.DRAW.single", 5),
      nb: 2, // no param
      kink: num("literal.DRAW.kink", 10),
      kinkSeg: 10, // no param
      back: num("literal.DRAW.back", 90),
      sErr: num("literal.DRAW.sErr", 5),
      sWarn: 2, // no param
    },
    openClear: num("literal.OPEN_CLEAR.metro", 4.2),
    bridgeAbovePool: num("literal.bridge_above_pool", 1),
    autoTypeRailTol: num("literal.autoType_rail_tol", 0.3),
    drainageMinLen: num("literal.drainage_min_len", 60),
    radii: { step: 10, h: num("literal.radii_window", 40) / 10 },
    approachHold: num("literal.approach_K_window", 40),
    coverHardFallback: num("literal.cover_hard_fallback", 0.5),
    minDriveFallback: num("literal.min_drive_fallback", 300),
    minRadiusFallback: num("literal.min_radius_fallback", 40),
    portalMinFallback: num("literal.portal_min_fallback", 100),
    approachFallback: 40, // no param (1293)
    tubeStreetNoteLen: num("literal.tube_street_note_len", 50),
    fillOver: num("literal.fill_over", 0.02),
    fillBand: { above: num("literal.fill_band", 0.3), below: 0.5 }, // below: no param (1715)
    platformOverlap: 0.5, // literal.platform_overlap holds a sentence; the page's 0.5 (2101)
    limitTol: num("literal.station_limit_tol", 0.05),
    lowCoverMinShort: num("literal.low_cover_min_short", 0.05),
    hall: {
      endHallsLen: num("literal.hall.end_halls_len", 25),
      mezzanineFraction: num("literal.hall.mezzanine_fraction", 0.6),
    },
  };
}

/** The golden's effective settings as PortSettings (the pool once in metres). */
export function settingsOf(d: OldPageDump): PortSettings {
  const s = d.settings;
  const g = (k: string): number => {
    const v = s[k];
    if (typeof v !== "number") throw new Error(`${d.line}: setting ${k} missing`);
    return v;
  };
  return {
    maxGrade: g("maxGrade"),
    platform: g("platform"),
    defDepth: g("defDepth"),
    elevAbove: g("elevAbove"),
    coverBelow: g("coverBelow"),
    deepBelow: g("deepBelow"),
    shallowMax: g("shallowMax"),
    deckDepth: g("deckDepth"),
    pool: g("poolFt") * FT,
    vcRadius: g("vcRadius"),
    vcMinLen: g("vcMinLen"),
    drainMin: g("drainMin"),
    curveK: g("curveK"),
    stationMaxGrade: g("stationMaxGrade"),
    fillSlope: g("fillSlope"),
    groundWarn: g("groundWarn"),
    groundSustain: g("groundSustain"),
    groundMax: g("groundMax"),
    sustainedLen: g("sustainedLen"),
    riverRoof: g("riverRoof"),
    riverSink: g("riverSink"),
    riverRise: g("riverRise"),
    riverFlatTol: g("riverFlatTol"),
    riverClearWater: g("riverClearWater"),
    riverCap: g("riverCap"),
    roadClearHighway: g("roadClearHighway"),
    roadClearMajor: g("roadClearMajor"),
    roadClearMinor: g("roadClearMinor"),
  };
}

/** hub/seed/params/metro_structure.json resolved for one route, as structure_of does. */
export function structureOf(line: string): StructureParams {
  const f = once("ms", () => readJson<MetroStructureFile>("hub/seed/params/metro_structure.json"));
  return {
    box: f.box,
    island_box: f.island_box,
    tubes: f.tubes,
    phases: f.phases,
    approach_m: f.approach_m,
    portal_min_m: f.portal_min_m,
    min_radius: f.min_radius,
    cost: f.cost,
    grades: f.grades,
    hall: f.hall,
    mezzanine_clear_m: f.elevated_station?.mezzanine_clear_m ?? f.mezzanine_clear_m ?? 3.5,
    open_clear_height: f.open_clear_height,
    subway_streets: f.subway_streets,
    line_phase: f.line_phase[line] ?? null,
    piece_phase: f.piece_phase[line] ?? {},
  };
}

interface ContextLine {
  streets?: [number, number, number, string, string][];
  roads?: [number, number, number, number, string, string][];
  blocks?: PortInput["context"]["blocks"];
  add?: { i0: number; v: number[] }[];
  cap?: { i0: number; v: number[] }[];
}

function contextOf(line: string): PortInput["context"] {
  const all = once("ctx", () => readJson<{ lines: Record<string, ContextLine> }>("data/profile/context/lines.json"));
  const c = all.lines[line] ?? {};
  return { streets: c.streets ?? [], roads: c.roads ?? [], blocks: c.blocks ?? [], add: c.add ?? [], cap: c.cap ?? [] };
}

function canonRecordOf(d: OldPageDump): CanonRecord {
  const r = (d.canon_record ?? {}) as Partial<{
    sections: {
      a: string;
      b: string;
      aIn?: boolean;
      bIn?: boolean;
      m: CanonRecord["sections"][number]["m"];
      src: string;
    }[];
    fixed: Record<string, FixedLevel>;
    bridges: CanonRecord["bridges"];
    decks: CanonRecord["decks"];
    locked: CanonRecord["locked"];
    modes: CanonRecord["modes"];
  }>;
  return {
    sections: (r.sections ?? []).map((s) => ({
      a: s.a,
      b: s.b,
      aIn: s.aIn !== false,
      bIn: s.bIn !== false,
      m: s.m,
      src: s.src,
    })),
    fixed: r.fixed ?? {},
    modes: r.modes ?? {},
    locked: r.locked ?? [],
    bridges: r.bridges ?? {},
    decks: r.decks ?? [],
  };
}

const SELECTED = new Set(["cutcover", "shield", "deep", "elevated"]);

function docOf(line: string): PortDoc | null {
  const s = seedDoc(line);
  if (!s) return null;
  return {
    st: s.st ?? {},
    sg: s.sg ?? {},
    so: s.so ?? {},
    del: s.del ?? [],
    pvi: s.pvi ?? [],
    ovr: (s.ovr ?? []) as Range3[],
    stt: s.stt ?? {},
    tf: (s.tf ?? []) as Range3[],
    shafts: s.shafts ?? [],
    gnd: s.gnd ?? [],
    gapfill: s.gapfill ?? [],
    mode: s.mode ?? {},
    ready: !!s.ready,
    frame: null,
  };
}

/** The golden's align as the model's Align. */
export function alignOf(a: OldAlign): Align {
  return {
    st: a.st,
    sg: a.sg,
    so: a.so,
    del: a.del,
    pvi: a.pvi,
    ovr: a.ovr.map(([c0, c1, t]) => [c0, c1, t as Type] as const),
    stt: a.stt.map((t) => (SELECTED.has(t) ? (t as SelectedType) : "")),
    tf: (a.tf ?? []).map(([c0, c1, t]) => [c0, c1, t as TubeForm] as const),
    shafts: a.shafts ?? [],
    gnd: a.gnd,
    gapfill: a.gapfill ?? [],
    ready: !!a.ready,
  };
}

/** The opening year's transfer with another Metro line (platDef 1584), from the golden's complex members. */
function transferAtOpen(d: OldPageDump, s: OldPageDump["stations"][number]): boolean {
  const others = (s.access.others ?? []) as { sys: string; line: string; year: number | null }[];
  const yr = s.year;
  return yr != null && others.some((m) => m.sys === "metro" && m.line !== d.line && m.year != null && m.year <= yr);
}

function platformsOf(d: OldPageDump): { platforms: PortPlatform[]; stations: LiveStation[] } {
  const sides = once("plat", () =>
    readJson<Record<string, Record<string, "side" | "island">>>("hub/seed/params/station_platforms.json"),
  );
  const lf = lineFile(d.line);
  const side = (key: string, name: string): "side" | "island" =>
    sides[d.line]?.[key] ?? sides[d.line]?.[name] ?? "side";
  const live = new Map(d.stations.map((s) => [s.key, s]));
  const platforms: PortPlatform[] = d.stations_file.map((f) => {
    const s = live.get(f.key);
    return {
      platform_id: f.key,
      key: f.key,
      name: f.name,
      order: f.i,
      point_c: f.c,
      side: side(f.key, f.name),
      year: s ? s.year : null,
      yearPhase: null,
      transferAtOpen: s ? transferAtOpen(d, s) : false,
      trunk: !!lf.stations[f.i]?.trunk,
    };
  });
  const stations: LiveStation[] = d.stations.map((s) => ({
    index: s.i,
    platform_id: s.key,
    key: s.key,
    name: s.name,
    point_c: s.point_c,
    c: s.c,
    side: side(s.key, s.name),
    year: s.year,
    transferAtOpen: transferAtOpen(d, s),
    trunk: !!(s as { trunk?: boolean | null }).trunk,
  }));
  return { platforms, stations };
}

/** The input of one line. */
export function inputOf(d: OldPageDump): PortInput {
  const lf = lineFile(d.line);
  const lit = literals();
  const S = settingsOf(d);
  const g = ground(d);
  const extra = once("apx", () => readJson<Record<string, ApproachExtra[]>>("hub/seed/params/approach_extra.json"));
  const crossings: CrossingRecord[] = (lf.crossings ?? []).map((x) => ({ ...x, other: x.wid }));
  const rivers: RiverRecord[] = d.rivers.map((r) => ({
    name: r.name,
    c0: r.c0,
    c1: r.c1,
    bedBelowPool: r.bed == null ? null : S.pool - r.bed,
    navigable: r.navigable,
    inCoveredWay: false,
  }));
  return {
    section_id: d.line,
    route: d.line,
    system: d.line === "CVG_Express" ? "cvx" : "metro",
    length: d.L,
    step: d.step,
    path: lf.path,
    pieces: (lf.pieces ?? []).map((p) => ({ name: p.name, c0: p.c0, c1: p.c1 })),
    dem: g.dem,
    platforms: platformsOf(d).platforms,
    doc: docOf(d.line),
    settings: S,
    literals: lit,
    structure: structureOf(d.line),
    era: d.era ? { shield: d.era.shield as "tube" | "bore", sgMax: d.era.sgMax } : null,
    canon: canonRecordOf(d),
    rivers,
    context: contextOf(d.line),
    crossings,
    neighbours: {},
    chronology: chronologyOf(d),
    approachExtra: (extra[d.line] ?? []).map((e) => ({
      station: e.station ?? null,
      side: e.side,
      c: e.c,
      extra: e.extra,
    })),
  };
}

const chronologyOf = (d: OldPageDump): ChrSegment[] =>
  d.chr_segments.map((s) => ({
    key: s.key,
    c0: s.c0,
    c1: s.c1,
    year: s.year,
    phase: s.phase as Phase | null,
    set: s.set,
  }));

function canonModelOf(d: OldPageDump, n: number, cAt: (i: number) => number): CanonModel {
  const secs = (d.canon.secs as (CanonSection & { lo: number; hi: number })[]).map((s) => ({
    m: s.m,
    lo: s.lo,
    hi: s.hi,
    a: s.a,
    b: s.b,
    src: s.src,
  }));
  const locks = d.canon.locks as Lock[];
  const sectionAt = new Int16Array(n);
  const lockAt = new Int16Array(n);
  for (let i = 0; i < n; i++) {
    const c = cAt(i);
    let k = -1;
    for (let j = secs.length - 1; j >= 0; j--) {
      const s = secs[j] as CanonSection;
      if (c >= s.lo && c <= s.hi) {
        k = j;
        break;
      }
    }
    sectionAt[i] = k;
    lockAt[i] = locks.findIndex((lk) => c >= lk.lo - 0.5 && c <= lk.hi + 0.5);
  }
  const fixed: Record<number, FixedLevel> = {};
  for (const [k, v] of Object.entries(d.canon.fixed)) fixed[Number(k)] = v as FixedLevel;
  const modes: Record<number, "under" | "surface"> = {};
  for (const [k, v] of Object.entries(d.canon.modes)) modes[Number(k)] = (v as { mode: "under" | "surface" }).mode;
  return { sections: secs, fixed, modes, locks, piers: d.canon.piers, sectionAt, lockAt };
}

function riversOf(d: OldPageDump): RiverModel[] {
  return d.rivers.map((r) => {
    const br = d.river_bridges.find((b) => b.name === r.name);
    const band = r.band as { ub: number; lb: number; low: number; nav: number | null } | null;
    return {
      name: r.name,
      c0: r.c0,
      c1: r.c1,
      bed: r.bed,
      navigable: r.navigable,
      alongShore: r.along_shore,
      bridge: (r.bridge ?? null) as RiverModel["bridge"],
      band: band ? { ub: band.ub, lb: band.lb, low: band.low, nav: band.nav } : null,
      bridgeBand: br ? { lb: br.lb, ub: br.ub } : null,
    };
  });
}

function groundOf(d: OldPageDump, align: Align): GroundLayers {
  const g = ground(d);
  return {
    step: d.step,
    dem: g.dem,
    regraded: g.regraded,
    finished: g.finished,
    surface: Float64Array.from(g.surface),
    bed: Float64Array.from(g.bed),
    lines: align.gnd,
    cross: d.gnd_cross as CrossGround[],
  };
}

function hallsOf(d: OldPageDump): HallSpan[] {
  const out: HallSpan[] = [];
  for (const s of d.stations) {
    const a = s.access as unknown as { halls?: [number, number][]; hallTop?: number };
    for (const [c0, c1] of a.halls ?? []) out.push({ station: s.i, c0, c1, top: a.hallTop ?? Number.NaN });
  }
  return out;
}

export interface GoldenLine {
  dump: OldPageDump;
  input: PortInput;
  model: SectionModel;
}

/** The port's input and model for one line, as the old page had them. */
export function fromGolden(line: string): GoldenLine {
  return once(`fg:${line}`, () => {
    const dump = loadOldPage(line);
    const input = inputOf(dump);
    const grid = gridOf(dump.L, dump.step);
    const align = alignOf(dump.align);
    const { stations } = platformsOf(dump);
    const S = input.settings;
    const verts = vertices({
      length: dump.L,
      platform: S.platform,
      vcRadius: S.vcRadius,
      vcMinLen: S.vcMinLen,
      stations: stations.map((s, i) => ({ c: s.c, z: align.st[i] ?? null, gradePermille: align.sg[i] ?? 0, order: i })),
      pvi: align.pvi,
    });
    const dsg = design(verts);
    const rg = railGrid(dsg, dump.L, dump.step);
    const rivers = riversOf(dump);
    const riverAt = new Int16Array(grid.n);
    for (let i = 0; i < grid.n; i++) {
      const c = grid.c[i] as number;
      riverAt[i] = rivers.findIndex((r) => c >= r.c0 && c <= r.c1);
    }
    const sb = dump.sunk_box;
    const model: SectionModel = {
      input,
      grid,
      settings: S,
      literals: input.literals,
      structure: input.structure,
      stations,
      align,
      rail: { design: dsg, z: rg.rail, grade: rg.grade },
      ground: groundOf(dump, align),
      rivers,
      riverAt,
      canon: canonModelOf(dump, grid.n, (i) => grid.c[i] as number),
      sunk: { below: sb.below, top: sb.top, inside: sb.inside ?? Number.NaN, spacing: sb.spacing ?? Number.NaN },
      effOvr: dump.eff_ovr.map(([a, b, t]) => [a, b, t as Type] as const),
      chronology: input.chronology,
      tables: input.structure ? applyMS(input.structure, input.literals.openClear) : null,
      curve: {
        step: 10,
        radii: Float32Array.from(dump.ten.radii, (v) => (v == null ? Number.POSITIVE_INFINITY : v)),
        allowance: Float32Array.from(dump.ten.allowance),
      },
      halls: hallsOf(dump),
    };
    return { dump, input, model };
  });
}

const ROLE_OF: Record<Type, TypeSolve["role"]["table"][number]> = {
  elevated: "open",
  atgrade: "open",
  trough: "open",
  cutcover: "box",
  shield: "tunnel",
  deep: "tunnel",
  sunk: "river",
};

/**
 * The old page's type solve as a TypeSolve. The dump has no per-sample role and no stretch list: role is rebuilt
 * from the type (open, river, box, tunnel; mined over a mined station's platform) and stretches is empty. Flags keep
 * their page kind and text in data; their slug is "page" (P1's own flags carry the real slugs).
 */
export function goldenSolve(d: OldPageDump, model: SectionModel): TypeSolve {
  const s = d.solve;
  const g = d.grid.solved;
  if (!s || !g) throw new Error(`${d.line}: no solve in the golden`);
  const t = unrle(g.t) as Type[];
  const stRole = s.stRole;
  const half = model.settings.platform / 2;
  const role = t.map((x, i) => {
    const c = model.grid.c[i] as number;
    const st = model.stations.find((q) => Math.abs(c - q.c) <= half);
    return st && stRole[st.key] === "mined" ? "mined" : ROLE_OF[x];
  });
  const flags: PortFlag[] = s.flags.map((f) => ({
    kind: "page",
    page: f.kind,
    sev: f.error ? "error" : f.info ? "info" : "warn",
    c0: f.c0,
    c1: f.c1,
    c: (f.c0 + f.c1) / 2,
    rule: "geometry.stretch.note_every_stretch",
    data: { text: f.plain },
    ...(f.propose ? { propose: { c0: f.c0, c1: f.c1 } } : {}),
  }));
  return {
    grid: model.grid,
    type: codes<Type>([...TYPE_CODES], t).codes,
    z: model.rail.z,
    tube: codes<TubeKey | null>([null, "A", "C", "bore"], unrle(g.tube) as (TubeKey | null)[]),
    part: codes(["", "a", "S"], unrle(g.part) as ("" | "a" | "S")[]),
    phase: codes<Phase>(["1", "2", "3", "later"], unrle(d.grid.phase) as Phase[]),
    role: codes<TypeSolve["role"]["table"][number]>(["open", "river", "box", "tunnel", "mined"], role),
    bad: s.bad,
    approaches: s.approaches as TypeSolve["approaches"],
    platDef: s.platDef,
    stRole: s.stRole,
    shafts: s.shafts,
    stretches: [],
    flags,
  };
}

/** The model with the old page's type solve laid in: what P2's spans, P3 and P4 read. */
export function typedFromGolden(line: string): TypedModel {
  return once(`typed:${line}`, () => {
    const { dump, model } = fromGolden(line);
    return { ...model, types: goldenSolve(dump, model), spans: dump.viaduct_spans as ViaductSpan[] };
  });
}

/** The golden's misfits as Misfit (paintMisfits 1637). */
export const goldenMisfits = (d: OldPageDump): Misfit[] =>
  d.misfits.map((x) => ({
    c0: x.c0,
    c1: x.c1,
    t: x.t as Type,
    why: x.why as Misfit["why"],
    worst: x.worst,
    ...(x.si != null ? { si: x.si } : {}),
  }));

/**
 * TypesModule answered from the golden: the old page's own type solve laid into whatever model is passed, so
 * typeAt(c) is the solved type at round(c / 2) within autoTypeRailTol of the solved rail, else the point on its own
 * (autoType 1605); structFor reads the solve's tube (drivenTube); phaseAt and phaseRules are P1a's.
 */
export function goldenTypes(dump: OldPageDump): TypesModule {
  const types = typedFromGolden(dump.line).types;
  const lay = <M extends SectionModel>(m: M): TypedModel => ({
    ...m,
    types,
    spans: (m as Partial<TypedModel>).spans ?? [],
  });
  return {
    typeAt: (m, c, z) => TYPES_MODULE.typeAt(lay(m), c, z),
    structFor: (m, t, c, tube) => TYPES_MODULE.structFor(lay(m), t, c, tube),
    reqCover: TYPES_MODULE.reqCover,
    phaseAt: TYPES_MODULE.phaseAt,
    phaseRules: TYPES_MODULE.phaseRules,
    gradeLimitAt: (m, c) => TYPES_MODULE.gradeLimitAt(lay(m), c),
    tubeKeyAt: (m, c) => TYPES_MODULE.tubeKeyAt(lay(m), c),
  };
}
