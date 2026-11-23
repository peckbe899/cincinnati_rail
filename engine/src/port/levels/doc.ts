// The saved profile as the solve reads it: the live stations (deriveStations 717-723), a profile saved in an older
// frame mapped onto the current station points (reframeDoc 1839-1868), and the normalised profile with its ground,
// canon and rivers (alignFromDoc 1869-1897). New values only: the page mutated the saved doc and S; here every
// result is returned, and the functions of other packages come in as AlignDeps.

import type { RuleId } from "../../rules.gen.ts";
import { PORT_DM_PER_M, PORT_RANGE3_LEN, PORT_REFRAME_TOL_M } from "../../tol.ts";
import { applyMS } from "../structure/tables.ts";
import type {
  Align,
  AlignDeps,
  CanonModel,
  GroundLayers,
  LevelModel,
  LiveStation,
  PortDoc,
  PortFlag,
  PortInput,
  PortPlatform,
  Range3,
  Reframe,
  RiverModel,
  SelectedType,
  TubeForm,
  Type,
} from "../types.ts";
import { TYPE_CODES } from "../types.ts";
import { gridOf } from "../util.ts";
import { defaultAlign, defaultMode } from "./levels.ts";

export const DOC_RULES = [
  "platform.tie.saved_profile_own_frame",
  "platform.tie.centre_kept",
  "platform.slide.limit_never_clamped",
  "network.canon.locks",
  "network.level_solver.shallow_as_grade_allows",
] as const satisfies readonly RuleId[];

type Slides = readonly number[] | Readonly<Record<string, number>>;

/**
 * The live stations (deriveStations, 717-723): the platforms in station order, the removed ones (by platform id)
 * left out, each slid by its offset (an array by live index, as the page's align.so, or a record by platform id, as
 * the saved profile's so). Not clamped: a slide past the limit is flagged by station.facts, never moved.
 */
export function deriveStations(
  input: Pick<PortInput, "platforms">,
  del: readonly string[],
  so: Slides = [],
): LiveStation[] {
  const gone = new Set(del);
  const kept = input.platforms
    .map((p, k) => [p, k] as const)
    .sort((a, b) => a[0].order - b[0].order || a[1] - b[1])
    .map(([p]) => p)
    .filter((p) => !gone.has(p.platform_id));
  const slideOf = (p: PortPlatform, i: number): number => {
    const v = Array.isArray(so)
      ? (so as readonly number[])[i]
      : (so as Readonly<Record<string, number>>)[p.platform_id];
    return typeof v === "number" && Number.isFinite(v) ? v : 0;
  };
  return kept.map((p, i) => ({
    index: i,
    platform_id: p.platform_id,
    key: p.key,
    name: p.name,
    point_c: p.point_c,
    c: p.point_c + slideOf(p, i),
    side: p.side,
    year: p.year,
    transferAtOpen: p.transferAtOpen,
    trunk: p.trunk,
  }));
}

/** The piecewise linear map from the saved frame's points onto the current ones, ends held (reframeDoc 1851-1852). */
export function frameMap(
  pairs: readonly (readonly [saved: number, now: number])[],
  L0: number,
  L: number,
): (c: number) => number {
  const sorted = pairs.slice().sort((a, b) => a[0] - b[0]);
  const xs = [0, ...sorted.map((p) => p[0]), L0];
  const ys = [0, ...sorted.map((p) => p[1]), L];
  return (c: number): number => {
    let i = 1;
    while (i < xs.length - 1 && (xs[i] as number) < c) i++;
    const x0 = xs[i - 1] as number;
    const x1 = xs[i] as number;
    const t = x1 === x0 ? 0 : (c - x0) / (x1 - x0);
    const y0 = ys[i - 1] as number;
    return y0 + t * ((ys[i] as number) - y0);
  };
}

const r1 = (v: number): number => Math.round(v * PORT_DM_PER_M) / PORT_DM_PER_M;

/**
 * reframeDoc (1839-1868; platform.tie.saved_profile_own_frame, platform.tie.centre_kept): a profile saved against
 * other station points has its bends, paints, tube forms, shafts and drawn ground mapped station by station onto the
 * current points (to 0.1 m), and each slide recomputed so every platform centre (saved point plus slide) is kept (to
 * 0.5 m). Stations are paired by platform id through the frame record, the live ones only; a slide of a station not
 * in the frame is dropped, as the page's. The new doc carries the current frame, so a second reframe changes nothing
 * (the page kept the old points and mapped again: see the port's report).
 */
export function reframeDoc(doc: PortDoc, platforms: readonly PortPlatform[], length: number): Reframe {
  const f = doc.frame;
  if (!f) return { changed: false, doc };
  const gone = new Set(doc.del);
  const live = platforms.filter((p) => !gone.has(p.platform_id));
  const pairs: [number, number][] = [];
  for (const p of live) {
    const saved = f.point_c[p.platform_id];
    if (typeof saved === "number") pairs.push([saved, p.point_c]);
  }
  if (!pairs.length || !pairs.some(([a, b]) => Math.abs(a - b) > PORT_REFRAME_TOL_M)) return { changed: false, doc };
  const L0 = Number.isFinite(f.length_m) ? f.length_m : length;
  const m = frameMap(pairs, L0, length);
  const so: Record<string, number> = {};
  for (const p of live) {
    const saved = f.point_c[p.platform_id];
    if (typeof saved !== "number") continue;
    const centre = m(saved + (Number(doc.so[p.platform_id]) || 0)); // the point plus the slide, as saved
    const v = Math.round((centre - p.point_c) * 2) / 2;
    if (Math.abs(v) > PORT_REFRAME_TOL_M) so[p.platform_id] = v;
  }
  const point_c: Record<string, number> = { ...f.point_c };
  for (const p of live) if (typeof f.point_c[p.platform_id] === "number") point_c[p.platform_id] = p.point_c;
  const range = <T extends string>(o: Range3<T>): Range3<T> => [r1(m(+o[0])), r1(m(+o[1])), o[2]] as const;
  return {
    changed: true,
    doc: {
      ...doc,
      pvi: doc.pvi.map(([c, z]) => [r1(m(+c)), z] as const),
      ovr: doc.ovr.map(range),
      tf: doc.tf.map(range),
      shafts: doc.shafts.map((c) => r1(m(+c))),
      gnd: doc.gnd.map((L) => L.map(([c, z]) => [r1(m(+c)), z] as const)),
      so,
      frame: { length_m: length, point_c },
    },
  };
}

type Pt = { c: number; z: number };

/** The saved drawn ground as lines (parseGnd, 668-671): finite points sorted by c, at least two, over 1 m long. */
function parseGnd(raw: PortDoc["gnd"] | null): Pt[][] {
  const out: Pt[][] = [];
  for (const L of raw ?? []) {
    const P = L.filter((p) => p.length >= 2 && Number.isFinite(+p[0]) && Number.isFinite(+p[1]))
      .map(([c, z]) => ({ c: +c, z: +z }))
      .sort((a, b) => a.c - b.c);
    if (P.length >= 2 && (P[P.length - 1] as Pt).c - (P[0] as Pt).c > 1) out.push(P);
  }
  return out.sort((a, b) => (a[0] as Pt).c - (b[0] as Pt).c);
}

const TYPES = new Set<string>(TYPE_CODES);

/**
 * Whose design the solve drew: Ben's ("saved"), the level solver's for a profile with no saved level and no bend point
 * ("default": the old page had no doc for such a line and drew defaultAlign's design, 1756), or Ben's with the level
 * solver's level at each station he has not set ("partial").
 */
export type DesignSource = "saved" | "default" | "partial";

/** What alignFromDoc gives: the profile, the stations, ground, canon and rivers it read, and its findings. */
export interface AlignResult {
  readonly align: Align;
  readonly stations: LiveStation[];
  readonly ground: GroundLayers;
  readonly canon: CanonModel;
  readonly rivers: RiverModel[];
  readonly reframed: boolean;
  readonly flags: PortFlag[];
  /** whose design this is (DesignSource) */
  readonly design: DesignSource;
  /** the live stations (platform ids) whose level is the level solver's, not a saved one */
  readonly defaulted: readonly string[];
}

/**
 * alignFromDoc (1869-1897) with the page's changed() after it (3141): the saved profile (null: Reset this line) read
 * onto the live stations. The drawn ground first (the level solver works on it); the default levels on the platform
 * centres as slid (defaultAlign), then the saved levels, grades, slides, bends, paints (a legacy 'bored' read as
 * shield), tube forms, shafts and selections over them; the canon's locks put back. A station with neither a saved
 * level nor a bound keeps NaN (flagged), never 0. The RER junction bend points (ensureJunctionPvis 375) are slice 2.
 */
export function alignFromDoc(input: PortInput, deps: AlignDeps): AlignResult {
  const doc0 = input.doc;
  const rer = input.system === "rer";
  const del = doc0 ? doc0.del.filter((k) => typeof k === "string") : [];
  const grid = gridOf(input.length, input.step);
  const unslid = deriveStations(input, del);
  const canon0 = deps.buildCanon(input, unslid, grid);
  const flags: PortFlag[] = [];
  let modes: ("under" | "surface")[] | null = null;
  if (doc0 && rer && Object.keys(doc0.mode).length)
    modes = unslid.map((s, i) => doc0.mode[s.platform_id] ?? defaultMode({ canon: canon0, stations: unslid }, i));
  let doc = doc0;
  let reframed = false;
  if (doc) {
    const r = reframeDoc(doc, input.platforms, input.length);
    doc = r.doc;
    reframed = r.changed;
    if (reframed)
      flags.push({
        kind: "profile_reframed",
        page: "Reframe",
        sev: "info",
        c0: 0,
        c1: input.length,
        c: 0,
        rule: "platform.tie.saved_profile_own_frame",
        data: { from_length: doc0?.frame?.length_m ?? null, to_length: input.length },
      });
  }
  // the drawn ground first: the level solver works on it
  const ground = deps.rebuildGround(input, parseGnd(doc ? doc.gnd : null), input.rivers);
  const gnd = ground.lines.map((P) => P.map((p) => ({ c: p.c, z: p.z })));
  const so0 = unslid.map((s) => Number(doc?.so[s.platform_id]) || 0);
  const slid = deriveStations(input, del, so0);
  const docOvr: Range3[] = (doc?.ovr ?? []).map(([a, b, t]) => [+a, +b, t] as const);
  const stt = deps.sttFromDoc(doc, slid, docOvr);
  const sunk = deps.sunkBox(input);
  const rivers0 = deps.riverModels(input, ground, canon0, sunk);
  const riverAt = new Int16Array(grid.n);
  for (let i = 0; i < grid.n; i++) {
    const c = grid.c[i] as number;
    riverAt[i] = rivers0.findIndex((r) => c >= r.c0 && c <= r.c1);
  }
  // the default levels on the platform centres as slid (4 November), with the canon of the unslid stations
  const lm: LevelModel = {
    input,
    grid,
    settings: input.settings,
    literals: input.literals,
    structure: input.structure,
    tables: input.structure ? applyMS(input.structure, input.literals.openClear) : null,
    stations: slid,
    ground,
    rivers: rivers0,
    riverAt,
    canon: canon0,
    sunk,
  };
  const lv = defaultAlign(lm, modes, [], stt);
  const n = unslid.length;
  let align: Align = {
    st: lv.st.slice(),
    sg: new Array<number>(n).fill(0),
    so: new Array<number>(n).fill(0),
    del,
    pvi: lv.pvi.slice(),
    ovr: [],
    stt: stt.slice() as (SelectedType | "")[],
    tf: [],
    shafts: [],
    gnd,
    gapfill: [],
    ready: false,
    ...(modes || rer ? { mode: lm.stations.map((_, i) => modes?.[i] ?? defaultMode(lm, i)) } : {}),
  };
  let stations = unslid;
  let canon = canon0;
  // a live station with a saved level, and a saved bend point: without either the profile holds no design, as the
  // old page's missing doc, and the level solver's bend points (the river tubes') stay with its levels
  const savedAt = (s: LiveStation): boolean => !!doc && typeof doc.st[s.platform_id] === "number";
  const hasDesign = !!doc && (doc.pvi.length > 0 || unslid.some(savedAt));
  const defaulted = unslid.filter((s) => !savedAt(s)).map((s) => s.platform_id);
  const design: DesignSource = !hasDesign ? "default" : defaulted.length ? "partial" : "saved";
  if (doc) {
    const st = align.st.slice();
    unslid.forEach((s, i) => {
      const v = doc.st[s.platform_id];
      if (typeof v === "number") st[i] = v;
    });
    const pvi = hasDesign
      ? doc.pvi.filter((p) => Array.isArray(p) && p.length >= 2).map(([c, z]) => ({ c: +c, z: +z }))
      : align.pvi.slice();
    const ovr = doc.ovr
      .filter((o) => Array.isArray(o) && o.length >= PORT_RANGE3_LEN)
      .map(([a, b, t]) => [+a, +b, t === "bored" ? "shield" : t] as const)
      .filter((o): o is Range3<Type> => TYPES.has(o[2]));
    const tf = doc.tf
      .filter((o) => Array.isArray(o) && o.length >= PORT_RANGE3_LEN && (o[2] === "twin" || o[2] === "bore"))
      .map(([a, b, t]) => [+a, +b, t as TubeForm] as const);
    align = {
      ...align,
      so: so0, // not clamped: a slide past the limit is flagged (Platform slide), never moved
      st,
      gapfill: doc.gapfill.filter((k) => typeof k === "string"),
      sg: unslid.map((s) => (typeof doc.sg[s.platform_id] === "number" ? (doc.sg[s.platform_id] as number) : 0)),
      pvi,
      ovr,
      ready: !!doc.ready,
      shafts: rer ? [] : doc.shafts.map((c) => +c).filter((c) => Number.isFinite(c)),
      tf,
    };
    stations = deriveStations(input, del, align.so);
    canon = deps.buildCanon(input, stations, grid);
    const locked = deps.applyLocks(align, canon, stations);
    align = locked.align;
    const lf = (locked as { flags?: readonly PortFlag[] }).flags;
    if (lf) flags.push(...lf);
  }
  const rivers = canon === canon0 ? rivers0 : deps.riverModels(input, ground, canon, sunk);
  // a station with no saved level and no bound: the level solver's flag (never 0)
  for (const f of lv.flags) {
    const i = (f.data as { station: number }).station;
    if (!Number.isFinite(align.st[i] as number)) {
      const s = stations[i];
      flags.push(
        s ? { ...f, c: s.c, c0: s.c - input.settings.platform / 2, c1: s.c + input.settings.platform / 2 } : f,
      );
    }
  }
  return { align, stations, ground, canon, rivers, reframed, flags, design, defaulted };
}

/**
 * Reset this line (the button, 3768-3773, then changed() 3141): the level solver's default profile on the
 * unslid stations with nothing removed, no paints, selections, bends of Ben's or drawn ground, and the canon's locks
 * put back (network.canon.locks). alignFromDoc(null) is the same less the locks (the dump's levels.reset).
 */
export function resetLine(input: PortInput, deps: AlignDeps): AlignResult {
  const r = alignFromDoc({ ...input, doc: null }, deps);
  const locked = deps.applyLocks(r.align, r.canon, r.stations);
  const lf = (locked as { flags?: readonly PortFlag[] }).flags ?? [];
  return { ...r, align: locked.align, flags: [...r.flags, ...lf] };
}
