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

export function pviRows(data: ProfileData): PviRow[] {
  const shape = pviShape(data);
  return (data.pvi ?? []).map((p, index) => {
    if (shape.kind === "tuple") {
      const t = p as number[];
      return { index, c: Number(t[0]), z: Number(t[1]) };
    }
    const o = p as Record<string, number>;
    return { index, c: Number(o[shape.c]), z: Number(o[shape.z]) };
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

/**
 * The input the browser solves: the server's SectionInput with the draft's PVIs and station levels in place of the
 * saved ones. PVIs are sorted by chainage, as the engine expects them in any order but the table shows them sorted.
 */
export function localInput(input: SectionInput, data: ProfileData | null): SectionInput {
  if (!data) return input;
  const pvi = data.pvi ? pviRows(data).map((r) => ({ c_m: r.c, z_m: r.z })) : input.pvi;
  const st = data.st;
  const stations = st
    ? input.stations.map((s) => (Object.hasOwn(st, s.platform_id) ? { ...s, level_m: st[s.platform_id] ?? null } : s))
    : input.stations;
  return { ...input, pvi: [...pvi].sort((a, b) => a.c_m - b.c_m), stations };
}

/**
 * The input the sheet's worker solves on each keystroke: localInput without the ground profile. vertical.rail@1
 * carries ground but does not read it (engine/src/vertical/method.ts), and leaving its 15,000 levels out of each
 * message saves the copy, the validation and the input hash. The rail is the same; only input_hash differs, and the
 * sheet never uses it.
 */
export function solveInput(input: SectionInput, data: ProfileData | null): SectionInput {
  const { ground: _ground, ...rest } = localInput(input, data);
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
