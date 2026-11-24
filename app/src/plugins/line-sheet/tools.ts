// The old page's editing tools on the profile's draft (claude/hub_maps/profiles_parity.md, section C, R7 to R11, R40,
// R50, R51, R53, R56 to R60): paint a stretch with a structure, a tube form or a shaft (paintRange 3181-3193), the
// drawn ground's points (addGroundAt 3156-3166, clampGpC 3149, removeGroundPoint 3168), the bend point's card edits,
// Profile set, Clear a misfit, and a proposal of the engine (section.propose@1) laid on the draft. Pure functions of
// the draft's data that return JSON Patch, so the unit tests need no canvas; each call is one undo step in the sheet.

import type { SectionProposal } from "@cr/engine/contract";
import type { JsonPatch } from "../../api/types.ts";
import { escapeToken } from "../../core/jsonpatch.ts";
import { type ProfileData, pviShape } from "./model.ts";

export type Tool = "move" | "paint" | "ground";

/** The structure brushes (buildBrushes 3732): Auto clears; the types but the sunk box; the shaft; the tube forms. */
export const TYPE_BRUSHES = ["elevated", "atgrade", "trough", "cutcover", "shield", "deep"] as const;
export type Brush = "auto" | (typeof TYPE_BRUSHES)[number] | "shaft" | "tf:twin" | "tf:bore" | "tf:auto";

export const BRUSH_LABELS: Record<Brush, string> = {
  auto: "Auto",
  elevated: "Elevated",
  atgrade: "At grade",
  trough: "Open trough",
  cutcover: "Cut & cover",
  shield: "Shield tunnel",
  deep: "Deep bore (TBM)",
  shaft: "Shaft",
  "tf:twin": "Twin tubes",
  "tf:bore": "Double-track bore",
  "tf:auto": "Auto tubes",
};

export const BRUSH_TIPS: Partial<Record<Brush, string>> = {
  auto: "Clear the paint: the rules decide",
  shaft: "A shaft: click on the line where a method may change (a stretch ends here); Auto over it clears it",
  "tf:twin": "Paint a bored stretch as twin single-track tubes",
  "tf:bore": "Paint a bored stretch as the double-track bore (3.90 m centres, no spacing change at a double-track box)",
  "tf:auto": "Clear the tube form: chosen by the drive's ends",
};

type Range = [number, number, string];

const rangesOf = (v: unknown): Range[] =>
  Array.isArray(v)
    ? (v as unknown[])
        .filter((o): o is unknown[] => Array.isArray(o) && o.length >= 3)
        .map((o) => [Number(o[0]), Number(o[1]), String(o[2])] as Range)
    : [];

/** A list of [c0, c1, kind] with [a, b] cut out of it (cutRange 615). */
export function cutRange(list: readonly Range[], a: number, b: number): Range[] {
  const out: Range[] = [];
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

const setField = (data: ProfileData, field: string, value: unknown): JsonPatch => [
  { op: Object.hasOwn(data, field) ? "replace" : "add", path: `/data/${escapeToken(field)}`, value },
];

/**
 * paintRange (3181-3193): a brush over [a, b] (chainages, any order). A structure or tube form brush cuts [a, b] out
 * of its list, adds itself (rounded to the metre) unless it is Auto, and joins touching runs of one kind; Auto also
 * clears the shafts inside (Metro). The shaft brush puts one shaft at the middle, replacing any within 2 m. A paint
 * shorter than a metre does nothing. Returns the ops and what it did (for the toast), or null for nothing.
 */
export function paintRange(
  data: ProfileData,
  a0: number,
  b0: number,
  brush: Brush,
  metro = true,
): { ops: JsonPatch; what: string; c?: number } | null {
  const a = Math.min(a0, b0);
  const b = Math.max(a0, b0);
  if (brush === "shaft") {
    if (!metro) return null;
    const c = Math.round((a + b) / 2);
    const shafts = (Array.isArray(data.shafts) ? (data.shafts as unknown[]) : [])
      .map(Number)
      .filter((x) => Number.isFinite(x) && Math.abs(x - c) > 2);
    return {
      ops: setField(
        data,
        "shafts",
        [...shafts, c].sort((x, y) => x - y),
      ),
      what: "shaft",
      c,
    };
  }
  if (b - a < 1) return null;
  const ops: JsonPatch = [];
  if (brush === "auto" && metro && Array.isArray(data.shafts)) {
    const left = (data.shafts as unknown[]).map(Number).filter((x) => x < a || x > b);
    if (left.length !== (data.shafts as unknown[]).length) ops.push(...setField(data, "shafts", left));
  }
  const tf = brush.startsWith("tf:");
  const key = tf ? "tf" : "ovr";
  const kind = tf ? (brush === "tf:auto" ? "auto" : brush.slice(3)) : brush;
  const out = cutRange(rangesOf(data[key]), a, b);
  if (kind !== "auto") out.push([Math.round(a), Math.round(b), kind]);
  out.sort((x, y) => x[0] - y[0]);
  const merged: Range[] = [];
  for (const o of out) {
    const m = merged[merged.length - 1];
    if (m && m[2] === o[2] && o[0] - m[1] < 1) m[1] = Math.max(m[1], o[1]);
    else merged.push([o[0], o[1], o[2]]);
  }
  const before = JSON.stringify(rangesOf(data[key]));
  if (JSON.stringify(merged) !== before || !Object.hasOwn(data, key)) ops.push(...setField(data, key, merged));
  return ops.length ? { ops, what: kind === "auto" ? "cleared" : kind } : null;
}

// ------------------------------------------------------------------------------------------- the drawn ground

export type GroundLine = { c: number; z: number }[];

/** The draft's drawn ground lines as the page read them (parseGnd 667): points sorted by chainage, lines of at least
 * two points over a metre, sorted by their start. Each keeps its index in the record (`at`) for the edits. */
export function groundLines(data: ProfileData | null): { at: number; pts: GroundLine }[] {
  const raw = data && Array.isArray(data.gnd) ? (data.gnd as unknown[]) : [];
  return raw
    .map((L, at) => ({
      at,
      pts: (Array.isArray(L) ? L : [])
        .filter(
          (p): p is unknown[] => Array.isArray(p) && p.length >= 2 && Number.isFinite(+p[0]) && Number.isFinite(+p[1]),
        )
        .map((p) => ({ c: +(p[0] as number), z: +(p[1] as number) }))
        .sort((p, q) => p.c - q.c),
    }))
    .filter(
      (x) => x.pts.length >= 2 && (x.pts[x.pts.length - 1] as { c: number }).c - (x.pts[0] as { c: number }).c > 1,
    )
    .sort((x, y) => (x.pts[0] as { c: number }).c - (y.pts[0] as { c: number }).c);
}

/** The level of a drawn line at c (gndLevel 666). */
export function gndLevel(P: GroundLine, c: number): number {
  for (let k = 1; k < P.length; k++) {
    const b = P[k] as { c: number; z: number };
    if (c <= b.c) {
      const a = P[k - 1] as { c: number; z: number };
      return b.c - a.c < 1e-6 ? b.z : a.z + ((b.z - a.z) * (c - a.c)) / (b.c - a.c);
    }
  }
  return (P[P.length - 1] as { z: number }).z;
}

const pairs = (lines: readonly GroundLine[]): [number, number][][] =>
  lines.map((P) => P.map((p) => [Math.round(p.c * 10) / 10, Math.round(p.z * 100) / 100] as [number, number]));

/** A selected ground point: its line (in the sorted order of groundLines) and its index on it. */
export interface GroundPoint {
  l: number;
  k: number;
}

/**
 * addGroundAt (3156-3166): a double-click in Ground. On a drawn line: a point on it there, at its level. Elsewhere:
 * a new line of three points, 25 m either side (short of the lines either side), its ends on the ground below
 * (`base`), its middle at the pointer's level to 0.1 m. Null with a reason when there is no room.
 */
export function addGroundAt(
  data: ProfileData,
  c0: number,
  z: number,
  base: (c: number) => number | null,
  length: number,
): { ops: JsonPatch; sel: GroundPoint; started: boolean } | { refused: string } {
  const c = Math.round(c0);
  const L = groundLines(data).map((x) => x.pts.map((p) => ({ ...p })));
  const l = L.findIndex((P) => c > (P[0] as { c: number }).c && c < (P[P.length - 1] as { c: number }).c);
  if (l >= 0) {
    const P = L[l] as GroundLine;
    if (P.some((p) => Math.abs(p.c - c) < 1)) return { refused: "A ground point is already there" };
    P.push({ c, z: Math.round(gndLevel(P, c) * 100) / 100 });
    P.sort((p, q) => p.c - q.c);
    return { ops: setField(data, "gnd", pairs(L)), sel: { l, k: P.findIndex((p) => p.c === c) }, started: false };
  }
  let a = Math.max(0, c - 25);
  let b = Math.min(length, c + 25);
  for (const P of L) {
    const first = (P[0] as { c: number }).c;
    const last = (P[P.length - 1] as { c: number }).c;
    if (last < c) a = Math.max(a, last + 1);
    if (first > c) b = Math.min(b, first - 1);
  }
  if (b - c < 2 || c - a < 2) return { refused: "No room for a ground line here" };
  const za = base(a);
  const zb = base(b);
  if (za === null || zb === null) return { refused: "No surveyed ground here to start a line on" };
  const P: GroundLine = [
    { c: a, z: za },
    { c, z: Math.round(z * 10) / 10 },
    { c: b, z: zb },
  ];
  L.push(P);
  L.sort((p, q) => (p[0] as { c: number }).c - (q[0] as { c: number }).c);
  return { ops: setField(data, "gnd", pairs(L)), sel: { l: L.indexOf(P), k: 1 }, started: true };
}

/** clampGpC (3149): a ground point's chainage between its neighbours, and the lines either side. */
export function clampGroundC(lines: readonly GroundLine[], l: number, k: number, c: number, length: number): number {
  const P = lines[l] as GroundLine;
  const prev = lines[l - 1];
  const next = lines[l + 1];
  const lo = k > 0 ? (P[k - 1] as { c: number }).c + 1 : prev ? (prev[prev.length - 1] as { c: number }).c + 1 : 0;
  const hi = k < P.length - 1 ? (P[k + 1] as { c: number }).c - 1 : next ? (next[0] as { c: number }).c - 1 : length;
  return Math.max(lo, Math.min(hi, c));
}

/** Move a ground point (a drag, the card, an arrow key): its chainage within its neighbours (to the metre), its
 * level to the cm. An end point keeps its level: it stays on the ground below (normGnd 668). */
export function moveGroundPoint(
  data: ProfileData,
  sel: GroundPoint,
  c: number,
  z: number | null,
  length: number,
): JsonPatch {
  const L = groundLines(data).map((x) => x.pts.map((p) => ({ ...p })));
  const P = L[sel.l];
  const p = P?.[sel.k];
  if (!P || !p) return [];
  p.c = clampGroundC(L, sel.l, sel.k, Math.round(c), length);
  const end = sel.k === 0 || sel.k === P.length - 1;
  if (!end && z !== null && Number.isFinite(z)) p.z = Math.round(z * 100) / 100;
  return setField(data, "gnd", pairs(L));
}

/** removeGroundPoint (3168): the point, or its whole line (or the line when only two points would be left). */
export function removeGroundPoint(data: ProfileData, sel: GroundPoint, all = false): JsonPatch {
  const L = groundLines(data).map((x) => x.pts.map((p) => ({ ...p })));
  const P = L[sel.l];
  if (!P) return [];
  if (all || P.length <= 2) L.splice(sel.l, 1);
  else P.splice(sel.k, 1);
  return setField(data, "gnd", pairs(L));
}

// ------------------------------------------------------------------------------------------------- other edits

/** Profile set (ready, 3689): this line's weaving is set, so other lines count their crossings with it. */
export const setReady = (data: ProfileData, on: boolean): JsonPatch => setField(data, "ready", on);

/**
 * Clear (clearMisfit 3595): a station's selection back to the rules (its platform id), or the paint cut out over the
 * misfit, half a metre past each end.
 */
export function clearMisfit(data: ProfileData, x: { c0: number; c1: number; station?: string | null }): JsonPatch {
  if (x.station) {
    const stt = data.stt as Record<string, unknown> | undefined;
    return stt && Object.hasOwn(stt, x.station) ? [{ op: "remove", path: `/data/stt/${escapeToken(x.station)}` }] : [];
  }
  return setField(data, "ovr", cutRange(rangesOf(data.ovr), x.c0 - 0.5, x.c1 + 0.5));
}

/** The paint review's Clear: one paint (by its value, the record's own entry), the ones that repeat the rules, or all
 * (renderPaints 2964-2983). */
export function clearPaints(
  data: ProfileData,
  which: { list: "ovr" | "tf" | "shafts"; a: number; b: number; paint: string }[] | "all",
): JsonPatch {
  if (which === "all") {
    const ops: JsonPatch = [];
    for (const f of ["ovr", "tf", "shafts"])
      if (Array.isArray(data[f]) && (data[f] as unknown[]).length) ops.push(...setField(data, f, []));
    return ops;
  }
  const ops: JsonPatch = [];
  for (const list of ["ovr", "tf", "shafts"] as const) {
    const gone = which.filter((w) => w.list === list);
    if (!gone.length || !Array.isArray(data[list])) continue;
    const near = (x: number, y: number) => Math.abs(x - y) < 0.06;
    const kept = (data[list] as unknown[]).filter((o) => {
      if (list === "shafts") return !gone.some((w) => near(Number(o), w.a));
      const r = o as unknown[];
      const t = r[2] === "bored" ? "shield" : r[2];
      return !gone.some((w) => near(Number(r[0]), w.a) && near(Number(r[1]), w.b) && t === w.paint);
    });
    if (kept.length !== (data[list] as unknown[]).length) ops.push(...setField(data, list, kept));
  }
  return ops;
}

/** Ops that set a bend point's chainage and level together (the card's fields). */
export function setPvi(data: ProfileData, index: number, c: number, z: number): JsonPatch {
  const p = (data.pvi ?? [])[index];
  if (Array.isArray(p)) return [{ op: "replace", path: `/data/pvi/${index}`, value: [c, z] }];
  const o = (p ?? {}) as Record<string, unknown>;
  const ck = "c_m" in o ? "c_m" : "c";
  const zk = "z_m" in o ? "z_m" : "z";
  return [{ op: "replace", path: `/data/pvi/${index}`, value: { ...o, [ck]: c, [zk]: z } }];
}

/**
 * A proposal of section.propose@1 as JSON Patch on the draft: the whole bend point list in the record's own shape,
 * the station levels and grades it sets, the drawn ground, the fields Reset empties, Profile set, and (for a profile
 * saved in an older frame) every reframed field with the frame. One draft edit, one undo step.
 */
export function proposalOps(data: ProfileData, p: SectionProposal): JsonPatch {
  const e = p.edit;
  const ops: JsonPatch = [];
  const work: Record<string, unknown> = { ...data };
  const set = (field: string, value: unknown) => {
    ops.push({ op: Object.hasOwn(work, field) ? "replace" : "add", path: `/data/${escapeToken(field)}`, value });
    work[field] = value;
  };
  for (const f of e.clear ?? []) if (Object.hasOwn(work, f)) set(f, Array.isArray(work[f]) ? [] : {});
  if (e.pvi) {
    // the record's own shape: [c, z] pairs, or {c_m, z_m} / {c, z} objects (an empty list takes the pairs the
    // old docs and the engine's edit use)
    const shape = data.pvi?.length ? pviShape(data) : ({ kind: "tuple" } as const);
    set(
      "pvi",
      e.pvi.map(([c, z]) => (shape.kind === "tuple" ? [c, z] : { [shape.c]: c, [shape.z]: z })),
    );
  }
  const mapEdit = (field: "st" | "sg", values: Record<string, number> | undefined, dropZero: boolean) => {
    if (!values || !Object.keys(values).length) return;
    const cur = { ...((work[field] as Record<string, unknown> | undefined) ?? {}) };
    for (const [k, v] of Object.entries(values)) {
      if (dropZero && v === 0) delete cur[k];
      else cur[k] = v;
    }
    set(field, cur);
  };
  mapEdit("st", e.st, false);
  mapEdit("sg", e.sg, true);
  if (e.gnd) set("gnd", e.gnd);
  if (e.ready !== undefined && (e.ready || Object.hasOwn(work, "ready"))) set("ready", e.ready);
  if (e.ovr) set("ovr", e.ovr);
  if (e.tf) set("tf", e.tf);
  if (e.shafts) set("shafts", e.shafts);
  if (e.so) set("so", Object.fromEntries(Object.entries(e.so).filter(([, v]) => v)));
  if (e.frame) set("frame", e.frame);
  return ops;
}
