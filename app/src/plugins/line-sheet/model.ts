// The line sheet's model: how a profile record's draft maps onto the engine's SectionInput, and the JSON Patch ops
// a table edit makes. Pure functions, so the unit tests need no canvas.
//
// The profile record (section 4, one per section) keys station levels by platform id in st, and holds the PVIs in
// pvi. The PVI shape is read from the record: [c, z] pairs (the old docs' form) or {c_m, z_m} / {c, z} objects;
// edits keep whatever shape the record has.

import type { SectionInput, SectionSolveInput, StationInput } from "@cr/engine/contract";
import type { JsonPatch } from "../../api/types.ts";
import { escapeToken } from "../../core/jsonpatch.ts";

export interface ProfileData {
  pvi?: unknown[];
  st?: Record<string, number | null>;
  sg?: Record<string, number | null>;
  so?: Record<string, number>;
  del?: string[];
  [k: string]: unknown;
}

export interface PviRow {
  index: number;
  c: number;
  z: number;
}

type Shape = { kind: "tuple" } | { kind: "object"; c: string; z: string };

/** How this record writes a PVI. An empty list takes the engine's {c_m, z_m}. */
export function pviShape(data: ProfileData): Shape {
  const first = data.pvi?.[0];
  if (Array.isArray(first)) return { kind: "tuple" };
  if (first && typeof first === "object") {
    const o = first as Record<string, unknown>;
    if ("c_m" in o || "z_m" in o) return { kind: "object", c: "c_m", z: "z_m" };
    return { kind: "object", c: "c", z: "z" };
  }
  return { kind: "object", c: "c_m", z: "z_m" };
}

/** The PVIs as rows, each read in its own shape (pvi_points in region/ext/profiles/doc.py reads them the same way). */
export function pviRows(data: ProfileData): PviRow[] {
  return (Array.isArray(data.pvi) ? data.pvi : []).map((p, index) => {
    if (Array.isArray(p)) return { index, c: Number(p[0]), z: Number(p[1]) };
    const o = (p ?? {}) as Record<string, unknown>;
    return { index, c: Number(o.c_m ?? o.c), z: Number(o.z_m ?? o.z) };
  });
}

function pviValue(shape: Shape, c: number, z: number): unknown {
  return shape.kind === "tuple" ? [c, z] : { [shape.c]: c, [shape.z]: z };
}

/** Ops that set one PVI's level (z, metres NAVD88). */
export function setPviZ(data: ProfileData, index: number, z: number): JsonPatch {
  const shape = pviShape(data);
  const path = shape.kind === "tuple" ? `/data/pvi/${index}/1` : `/data/pvi/${index}/${escapeToken(shape.z)}`;
  return [{ op: "replace", path, value: z }];
}

/** Ops that move one PVI along the section. */
export function setPviC(data: ProfileData, index: number, c: number): JsonPatch {
  const shape = pviShape(data);
  const path = shape.kind === "tuple" ? `/data/pvi/${index}/0` : `/data/pvi/${index}/${escapeToken(shape.c)}`;
  return [{ op: "replace", path, value: c }];
}

/** Ops that add a PVI, keeping the list sorted by chainage. */
export function addPvi(data: ProfileData, c: number, z: number): JsonPatch {
  const shape = pviShape(data);
  const rows = pviRows(data);
  const at = rows.findIndex((r) => r.c > c);
  const ops: JsonPatch = [];
  if (!data.pvi) ops.push({ op: "add", path: "/data/pvi", value: [] });
  ops.push({ op: "add", path: `/data/pvi/${at < 0 ? "-" : at}`, value: pviValue(shape, c, z) });
  return ops;
}

export function removePvi(index: number): JsonPatch {
  return [{ op: "remove", path: `/data/pvi/${index}` }];
}

/** Ops that set a station's rail level, or clear it (null leaves it to the design). */
export function setStationLevel(data: ProfileData, platformId: string, z: number | null): JsonPatch {
  const path = `/data/st/${escapeToken(platformId)}`;
  const ops: JsonPatch = [];
  if (!data.st) ops.push({ op: "add", path: "/data/st", value: {} });
  const has = !!data.st && Object.hasOwn(data.st, platformId);
  if (z === null) {
    if (has) ops.push({ op: "remove", path });
    return ops;
  }
  ops.push({ op: has ? "replace" : "add", path, value: z });
  return ops;
}

/** A section's stops and platforms, the records the server builds its stations from (inputs.gather). */
export interface StationFrame {
  /** The stops in the server's order: by order, then c, then id. */
  stops: { id: string; c: number }[];
  /** Each stop's platforms, by id. */
  platforms: Map<string, { id: string; name: string }[]>;
}

const byId = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

/** The frame of a section from its stop and platform records, sorted as region/ext/profiles/inputs.py gather(). */
export function stationFrame(
  stops: { id: string; data: Record<string, unknown> }[],
  platforms: { id: string; data: Record<string, unknown> }[],
): StationFrame {
  const num = (v: unknown) => (typeof v === "number" ? v : 0);
  const sorted = [...stops].sort(
    (a, b) => num(a.data.order) - num(b.data.order) || num(a.data.c) - num(b.data.c) || byId(a.id, b.id),
  );
  const plats = new Map<string, { id: string; name: string }[]>();
  for (const p of [...platforms].sort((a, b) => byId(a.id, b.id))) {
    const stop = String(p.data.stop);
    const list = plats.get(stop) ?? [];
    list.push({ id: p.id, name: typeof p.data.name === "string" ? p.data.name : p.id });
    plats.set(stop, list);
  }
  return { stops: sorted.map((s) => ({ id: s.id, c: Number(s.data.c) })), platforms: plats };
}

/**
 * The frame if it holds every platform of the server's input, else null. The input's stations are the saved
 * profile's platforms on these same records, so a frame missing one was read from records that moved on (or not
 * at all), and the stations then follow the input rather than vanish.
 */
export function frameFor(frame: StationFrame | null, input: SectionInput): StationFrame | null {
  if (!frame) return null;
  const ids = new Set<string>();
  for (const list of frame.platforms.values()) for (const p of list) ids.add(p.id);
  const stops = new Set(frame.stops.map((s) => s.id));
  for (const [stop, list] of frame.platforms) if (!stops.has(stop)) for (const p of list) ids.delete(p.id);
  return input.stations.every((s) => ids.has(s.platform_id)) ? frame : null;
}

const own = (o: unknown, k: string): o is Record<string, unknown> =>
  !!o && typeof o === "object" && Object.hasOwn(o as object, k);

/**
 * The stations of a profile on its frame: the same rule as build() in region/ext/profiles/inputs.py, line for line.
 * The platforms in stop order, minus the profile's del; each at its stop's c plus its slide (so) when that is a
 * number; its level st[pid] (null when the key is absent); its grade sg[pid] (0 when the key is absent).
 * test/unit/inputs_parity.test.ts runs both on the same drafts.
 */
export function stationsOf(frame: StationFrame, data: ProfileData): SectionInput["stations"] {
  const deleted = new Set(Array.isArray(data.del) ? (data.del as unknown[]).map(String) : []);
  const st = (data.st || {}) as Record<string, unknown>;
  const sg = (data.sg || {}) as Record<string, unknown>;
  const so = (data.so || {}) as Record<string, unknown>;
  const out: SectionInput["stations"] = [];
  for (const stop of frame.stops) {
    for (const p of frame.platforms.get(stop.id) ?? []) {
      if (deleted.has(p.id)) continue;
      const slide = own(so, p.id) ? so[p.id] : undefined;
      out.push({
        platform_id: p.id,
        order: out.length,
        c_m: typeof slide === "number" ? stop.c + slide : stop.c,
        level_m: own(st, p.id) ? (st[p.id] as number | null) : null,
        grade_permille: own(sg, p.id) ? (sg[p.id] as number | null) : 0,
      });
    }
  }
  return out;
}

/**
 * The input the browser solves: the server's SectionInput with the draft's PVIs and stations in place of the saved
 * ones, so the browser and the server solve the same rail for the same profile. With the section's frame the
 * stations are rebuilt from the draft as the server builds them (del, so, sg, st). Without one (the stops could not
 * be read) each station the server sent takes the draft's level and grade by the same rule: a key the draft does
 * not have is null and 0, never the level the input was built with. PVIs are sorted by chainage, as the table shows
 * them; the engine takes them in any order.
 */
/**
 * Whether the profile has a design to draw: a bend point or a station level. Without one (Lines 10, 11 and 13 before
 * Ben sets any level) vertical.rail@1 gives a rail at 0 m, which is no design at all: the sheet draws no rail then,
 * and keeps it out of the level range, instead of a rail 150 m under the ground squashing the whole plot.
 */
export function hasDesign(input: Pick<SectionInput, "pvi" | "stations"> | null | undefined): boolean {
  if (!input) return false;
  return input.pvi.length > 0 || input.stations.some((s) => s.level_m !== null && s.level_m !== undefined);
}

export function localInput(
  input: SectionInput,
  data: ProfileData | null,
  frame: StationFrame | null = null,
): SectionInput {
  if (!data) return input;
  const pvi = pviRows(data).map((r) => ({ c_m: r.c, z_m: r.z }));
  let stations: SectionInput["stations"];
  if (frame) stations = stationsOf(frame, data);
  else {
    const st = (data.st || {}) as Record<string, unknown>;
    const sg = (data.sg || {}) as Record<string, unknown>;
    stations = input.stations.map((s) => ({
      ...s,
      level_m: own(st, s.platform_id) ? (st[s.platform_id] as number | null) : null,
      grade_permille: own(sg, s.platform_id) ? (sg[s.platform_id] as number | null) : 0,
    }));
  }
  return { ...input, pvi: [...pvi].sort((a, b) => a.c_m - b.c_m), stations };
}

/**
 * The input the sheet's worker solves on each keystroke: localInput without the ground profile. vertical.rail@1
 * carries ground but does not read it (engine/src/vertical/method.ts), and leaving its 15,000 levels out of each
 * message saves the copy, the validation and the input hash. The rail is the same; only input_hash differs, and the
 * sheet never uses it.
 */
export function solveInput(
  input: SectionInput,
  data: ProfileData | null,
  frame: StationFrame | null = null,
): SectionInput {
  const { ground: _ground, ...rest } = localInput(input, data, frame);
  return rest;
}

/** The largest difference between two rail arrays (metres), over the shorter length. */
export function maxDiff(a: ArrayLike<number>, b: ArrayLike<number>): number {
  let m = 0;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) m = Math.max(m, Math.abs((a[i] ?? 0) - (b[i] ?? 0)));
  return m;
}

/** Float64 values of a result array, whatever dtype the server stored (X-Dtype f8, f4, <f8...). */
export function toFloat64(dtype: string, buf: ArrayBuffer): Float64Array {
  const d = dtype.replace(/^[<|=]/, "").toLowerCase();
  if (d === "f4" || d === "float32") return Float64Array.from(new Float32Array(buf));
  if (d === "i2" || d === "int16") return Float64Array.from(new Int16Array(buf));
  if (d === "i4" || d === "int32") return Float64Array.from(new Int32Array(buf));
  return new Float64Array(buf);
}

// ------------------------------------------------------------------------------------- station edits (0.3)
//
// Each op is JSON Patch on the profile record's draft (or, for the side, on the platform record's), made from the
// data as it is now. A value of zero is written as a removal, as the old page saved only nonzero sg and so
// (profiles.html 3213-3229). Rounding and the slide clamp follow the old page: sg to 0.1 per mille (setSg 3576), so
// to 0.5 m within the slide limit (setSo 3545).

/** The record's map field (st, sg, so, stt, access) as an object, or null when it is absent. */
const mapOf = (data: ProfileData, field: string): Record<string, unknown> | null => {
  const v = data[field];
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
};

/** Set one key of a map field to a value, or remove it (value undefined). */
function setKey(data: ProfileData, field: string, key: string, value: unknown): JsonPatch {
  const m = mapOf(data, field);
  const path = `/data/${field}/${escapeToken(key)}`;
  const has = !!m && Object.hasOwn(m, key);
  if (value === undefined) return has ? [{ op: "remove", path }] : [];
  const ops: JsonPatch = [];
  if (!m) ops.push({ op: "add", path: `/data/${field}`, value: {} });
  ops.push({ op: has ? "replace" : "add", path, value });
  return ops;
}

/** A list field (del, gapfill) with a key in it or out of it. */
function setMember(data: ProfileData, field: "del" | "gapfill", key: string, on: boolean): JsonPatch {
  const list = Array.isArray(data[field]) ? (data[field] as unknown[]).map(String) : null;
  const has = !!list && list.includes(key);
  if (on === has) return [];
  if (on)
    return list
      ? [{ op: "add", path: `/data/${field}/-`, value: key }]
      : [{ op: "add", path: `/data/${field}`, value: [key] }];
  return [{ op: "remove", path: `/data/${field}/${(list as string[]).indexOf(key)}` }];
}

export const roundGrade = (v: number): number => Math.round(v * 10) / 10;
export const roundSlide = (v: number, max: number): number => Math.round(Math.max(-max, Math.min(max, v)) * 2) / 2;

/** The platform grade, per mille rising with chainage, tilted about the centre (sg); 0 removes the key. */
export function setStationGrade(data: ProfileData, pid: string, permille: number): JsonPatch {
  const v = roundGrade(permille);
  return setKey(data, "sg", pid, v === 0 ? undefined : v);
}

/** The platform's slide off its drawn point (so), clamped to the limit and rounded to 0.5 m; 0 removes the key. */
export function setStationSlide(data: ProfileData, pid: string, slide: number, max = 150): JsonPatch {
  const v = roundSlide(slide, max);
  return setKey(data, "so", pid, v === 0 ? undefined : v);
}

/** The slide that puts the drawn point `fromStart` metres from the platform start (the card's "Point from platform
 * start": so = half - value, the value clamped to the platform; 3080). */
export const slideForPoint = (fromStart: number, half: number): number =>
  half - Math.max(0, Math.min(2 * half, fromStart));

/** Remove a station: its key goes into del. Its level, grade, slide and type stay, so Restore brings them back. */
export const removeStation = (data: ProfileData, pid: string): JsonPatch => setMember(data, "del", pid, true);

/** Restore a removed station: its key leaves del, and its own values (if any) come back with it. */
export const restoreStation = (data: ProfileData, pid: string): JsonPatch => setMember(data, "del", pid, false);

/** A Metro station type Ben can select (stt, profiles.html 269); null is "Rules". */
export type SelectableType = "cutcover" | "shield" | "deep" | "elevated";
export const STT_LABELS: Record<SelectableType, string> = {
  cutcover: "Cut & cover (box)",
  shield: "Shield (mined)",
  deep: "Bore (TBM, mined)",
  elevated: "Elevated, mezzanine under",
};

/**
 * The station type selection, and for Elevated the rail raised to the mezzanine's height over the ground when it is
 * lower (setStt 3568-3575: ceil to 0.1 m). `raise` is ground + deck + mezzanine clear height, null when there is no
 * ground; `level` the rail now.
 */
export function setStationType(
  data: ProfileData,
  pid: string,
  t: SelectableType | null,
  raise: number | null = null,
  level: number | null = null,
): JsonPatch {
  const ops = setKey(data, "stt", pid, t ?? undefined);
  if (t === "elevated" && raise !== null && (level === null || level < raise)) {
    ops.push(...setStationLevel(data, pid, Math.ceil(raise * 10) / 10));
  }
  return ops;
}

/** A level nudged by an arrow key (S46, 3537): 0.1 or, with Shift, 1 in the display unit (metres or feet), rounded
 * to the centimetre, so a level Ben typed as 152.02 steps to 152.12 and keeps its centimetres. */
export function nudgeLevel(z: number, dir: 1 | -1, coarse: boolean, unit: "m" | "ft"): number {
  const step = (coarse ? 1 : 0.1) * (unit === "ft" ? 0.3048 : 1);
  return Math.round((z + dir * step) * 100) / 100;
}

/** The paint over chainage c: the last one covering it ("bored" is the shield paint), as sttFromDoc reads it (852). */
export function paintAt(data: ProfileData, c: number): string | null {
  const ovr = Array.isArray(data.ovr) ? (data.ovr as unknown[][]) : [];
  for (let k = ovr.length - 1; k >= 0; k--) {
    const o = ovr[k];
    if (Array.isArray(o) && o.length >= 3 && c >= Number(o[0]) && c <= Number(o[1]))
      return o[2] === "bored" ? "shield" : String(o[2]);
  }
  return null;
}

/** S62: a saved selection equal to the paint over the station's centre. The old page took it for its 2 November
 * migration and showed Rules (sttFromDoc 852-861, elevated aside); the hub keeps it as Ben's and notes it. */
export function sttSameAsPaint(data: ProfileData, pid: string, centre: number): boolean {
  const stt = data.stt as Record<string, unknown> | undefined;
  const v = stt && Object.hasOwn(stt, pid) ? stt[pid] : undefined;
  return typeof v === "string" && v !== "elevated" && paintAt(data, centre) === v;
}

/** Gap fillers (the named exception for a curved platform): the key in gapfill or out of it. */
export const setGapfill = (data: ProfileData, pid: string, on: boolean): JsonPatch =>
  setMember(data, "gapfill", pid, on);

/** The access types and their labels and notes, as the old page has them (ACCESS, profiles.html 467-477). */
export const ACCESS: Record<string, { label: string; note: string }> = {
  surface: { label: "Surface station", note: "at grade or elevated: a station house, no underground hall" },
  platform_level: {
    label: "Platform level",
    note: "side platforms, fare control at the platform ends, a stair from each end to its sidewalk (Kendall 1912)",
  },
  platform_level_xu: {
    label: "Platform level, crossunder",
    note: "platform level plus a passage under the tracks at one end (Republic 1907)",
  },
  end_halls: {
    label: "End ticket halls",
    note: "a ticket hall over the box at each end, stairs down to the platforms (Fountain Square 1905)",
  },
  mezzanine: { label: "Mezzanine", note: "one hall over the middle of the box, one fare line (IND 1932)" },
  mezzanine_full: { label: "Full-length mezzanine", note: "a hall over the whole platform (IND 42nd St 1932)" },
  mined_hall: {
    label: "Street hall, mined station",
    note: "a ticket hall at street level, stairs (escalators later) down to the platform tunnels",
  },
  deep: { label: "Deep station", note: "a hall at the street, lift shafts, a passage at platform level" },
  elevated_mezzanine: {
    label: "Elevated, mezzanine under",
    note: "platforms on the viaduct; under them at street level a mezzanine (fare control, stairs up to each platform) that is also a public passthrough across the line",
  },
};

/** Ben's access choice (profile.access, kind profile v2), or back to the rules (null). Later stages he saved stay. */
export function setAccess(data: ProfileData, pid: string, type: string | null): JsonPatch {
  if (type === null) return setKey(data, "access", pid, undefined);
  const cur = mapOf(data, "access")?.[pid] as { stages?: unknown[] } | undefined;
  return setKey(data, "access", pid, cur?.stages ? { type, stages: cur.stages } : { type });
}

/** Side platforms or an island, on the platform record (platform.side). */
export function setPlatformSide(platform: Record<string, unknown>, side: "side" | "island"): JsonPatch {
  return [{ op: Object.hasOwn(platform, "side") ? "replace" : "add", path: "/data/side", value: side }];
}

// ----------------------------------------------------------------------------------- station.facts@1 input

/** The profile's station fields as station.facts@1 reads them: region/ext/profiles/inputs.py station_profile. */
export const STATION_PROFILE_FIELDS = [
  "st",
  "sg",
  "so",
  "del",
  "stt",
  "gapfill",
  "access",
  "mode",
  "ovr",
  "gnd",
] as const;

export function stationProfile(data: ProfileData): StationInput["profile"] {
  const out: Record<string, unknown> = {};
  for (const f of STATION_PROFILE_FIELDS) {
    if (!Object.hasOwn(data, f)) continue;
    let v: unknown = JSON.parse(JSON.stringify(data[f]));
    if (f === "ovr" && Array.isArray(v))
      v = (v as unknown[][])
        .filter((o) => Array.isArray(o) && o.length >= 3)
        .map((o) => [Number(o[0]), Number(o[1]), o[2] === "bored" ? "shield" : o[2]]);
    if (f === "gnd" && Array.isArray(v))
      v = (v as unknown[][]).map((L) =>
        (Array.isArray(L) ? L : [])
          .filter((p) => Array.isArray(p) && p.length >= 2)
          .map((p) => [Number((p as unknown[])[0]), Number((p as unknown[])[1])]),
      );
    if (f === "st" && v && typeof v === "object")
      v = Object.fromEntries(Object.entries(v).filter(([, x]) => x === null || typeof x === "number"));
    if ((f === "sg" || f === "so") && v && typeof v === "object")
      v = Object.fromEntries(Object.entries(v).filter(([, x]) => typeof x === "number"));
    out[f] = v;
  }
  return out as StationInput["profile"];
}

/**
 * The input the sheet's worker hands station.facts@1 after each solve: the server's StationInput with three swaps
 * (the records and engine report): the section from the draft (localInput, ground kept), the profile's station
 * fields from the draft, and each platform's side from its own draft.
 */
export function factsInput(
  si: StationInput,
  data: ProfileData | null,
  frame: StationFrame | null,
  sides: (pid: string) => { side: "side" | "island"; source: "ben" } | null = () => null,
): StationInput {
  const section = localInput(si.section, data, frame);
  return {
    ...si,
    section,
    profile: data ? stationProfile(data) : si.profile,
    platforms: si.platforms.map((p) => {
      const s = sides(p.platform_id);
      return s ? { ...p, side: s.side, side_source: s.source } : p;
    }),
  };
}

/**
 * Ease the bends (easePlatform, profiles.html 3579-3592): the platform grade that is the mean of the straight grades
 * either side of it (from the design line's vertices next to its start and end, when over 1 m away), clamped to the
 * limit; null when there is no grade either side. One pass; the old page ran three, re-solving between them.
 */
export function easeGrade(
  dv: readonly { c_m: number; z_m: number; kind: string }[],
  c: number,
  half: number,
  limit: number,
): number | null {
  const near = (x: number, y: number) => Math.abs(x - y) < 1e-6;
  // The platform's end vertices are clamped to the line (vertices 731): the last vertex is at the line's length.
  const len = dv.length ? (dv[dv.length - 1] as { c_m: number }).c_m : c + half;
  const a = dv.findIndex((v) => v.kind === "ps" && near(v.c_m, Math.max(0, c - half)));
  const b = dv.findIndex((v) => v.kind === "pe" && near(v.c_m, Math.min(len, c + half)));
  if (a < 0 || b < 0) return null;
  const va = dv[a] as { c_m: number; z_m: number };
  const vb = dv[b] as { c_m: number; z_m: number };
  const pa = dv[a - 1];
  const nb = dv[b + 1];
  const gs: number[] = [];
  if (pa && va.c_m - pa.c_m > 1) gs.push(((va.z_m - pa.z_m) / (va.c_m - pa.c_m)) * 1000);
  if (nb && nb.c_m - vb.c_m > 1) gs.push(((nb.z_m - vb.z_m) / (nb.c_m - vb.c_m)) * 1000);
  if (!gs.length) return null;
  const m = gs.reduce((p, q) => p + q, 0) / gs.length;
  return roundGrade(Math.max(-limit, Math.min(limit, m)));
}

// ----------------------------------------------------------------------------------- section.solve@1 input

/**
 * The input the sheet's worker hands section.solve@1 once the rail and the station facts have run: the server's
 * SectionSolveInput with the draft's profile in place of the record's (every field the solve reads, keyed by
 * platform id as the record keys them) and each platform's side from its own draft. The neighbours, the canon, the
 * context and the params stay the server's: the draft edits only this line's profile and platforms.
 */
export function solveInputOf(
  ssi: SectionSolveInput,
  data: ProfileData | null,
  sides: (pid: string) => { side: "side" | "island"; source: "ben" } | null = () => null,
): SectionSolveInput {
  const platforms = ssi.platforms.map((p) => {
    const s = sides(p.platform_id);
    return s ? { ...p, side: s.side, sideSet: true } : p;
  });
  if (!data) return { ...ssi, platforms };
  const num = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
  const rec = <T>(v: unknown, keep: (x: unknown) => x is T): Record<string, T> =>
    v && typeof v === "object" && !Array.isArray(v)
      ? (Object.fromEntries(Object.entries(v).filter(([, x]) => keep(x))) as Record<string, T>)
      : {};
  const ranges = (v: unknown): [number, number, string][] =>
    Array.isArray(v)
      ? (v as unknown[])
          .filter((o): o is unknown[] => Array.isArray(o) && o.length >= 3)
          .map((o) => [Number(o[0]), Number(o[1]), String(o[2])] as [number, number, string])
      : [];
  const pvi = (Array.isArray(data.pvi) ? data.pvi : []).flatMap((p: unknown): [number, number][] => {
    if (Array.isArray(p) && p.length >= 2) return [[Number(p[0]), Number(p[1])]];
    if (p && typeof p === "object" && "c_m" in p && "z_m" in p)
      return [[Number((p as { c_m: number }).c_m), Number((p as { z_m: number }).z_m)]];
    return [];
  });
  const gnd = (Array.isArray(data.gnd) ? (data.gnd as unknown[]) : []).map((L) =>
    (Array.isArray(L) ? L : [])
      .filter((q): q is unknown[] => Array.isArray(q) && q.length >= 2)
      .map((q) => [Number(q[0]), Number(q[1])] as [number, number]),
  );
  const strs = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : []);
  type Frame = NonNullable<SectionSolveInput["doc"]>["frame"];
  const frame = (data as { frame?: unknown }).frame as Frame | undefined;
  const access = rec(
    data.access,
    (x): x is { type: string } => !!x && typeof (x as { type?: unknown }).type === "string",
  );
  return {
    ...ssi,
    platforms,
    doc: {
      st: rec(data.st, (x): x is number | null => x === null || num(x)),
      sg: rec(data.sg, num),
      so: rec(data.so, num),
      del: strs(data.del),
      pvi,
      ovr: ranges(data.ovr).map(([a, b, t]) => [a, b, t === "bored" ? "shield" : t] as [number, number, string]),
      stt: rec(data.stt, (x): x is string => typeof x === "string"),
      tf: ranges((data as { tf?: unknown }).tf),
      shafts: (Array.isArray((data as { shafts?: unknown }).shafts)
        ? (data as { shafts: unknown[] }).shafts
        : []
      ).filter(num),
      gnd,
      gapfill: strs(data.gapfill),
      mode: rec(data.mode, (x): x is "under" | "surface" => x === "under" || x === "surface"),
      ready: !!(data as { ready?: unknown }).ready,
      frame: frame && typeof frame === "object" ? frame : (ssi.doc?.frame ?? null),
    },
    access: Object.fromEntries(Object.entries(access).map(([k, a]) => [k, a.type])),
  };
}
