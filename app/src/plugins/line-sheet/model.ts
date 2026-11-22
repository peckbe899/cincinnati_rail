// The line sheet's model: how a profile record's draft maps onto the engine's SectionInput, and the JSON Patch ops
// a table edit makes. Pure functions, so the unit tests need no canvas.
//
// The profile record (section 4, one per section) keys station levels by platform id in st, and holds the PVIs in
// pvi. The PVI shape is read from the record: [c, z] pairs (the old docs' form) or {c_m, z_m} / {c, z} objects;
// edits keep whatever shape the record has.

import type { SectionInput } from "@cr/engine/contract";
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
