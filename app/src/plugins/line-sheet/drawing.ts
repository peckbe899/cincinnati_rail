// The line sheet's drawing model: the formats, axis ticks, label thinning, grade chords and curve ticks the bands
// draw, as pure functions so the unit tests need no canvas. The formats and rules follow the old Rail Profiles
// page (data/profile/profiles.html: fmtCh, fmtG, fmtZ, niceStep, the station labels and the grade labels).

import type { DesignVertex, VerticalCurve } from "@cr/engine/contract";
import { M_PER_FT, type Units } from "../../core/units.ts";

/** The plot's margins in CSS pixels: room for the station names on top and the level axis on the left. */
export interface Margins {
  l: number;
  r: number;
  t: number;
  b: number;
}

/** The old page's margins (l 60, t 84, r 14), smaller on a narrow canvas as the old page did under 560 px. */
export function margins(width: number, height: number): Margins {
  const narrow = width < 560;
  const short = height < 300;
  // The old page took 64 at the top on a narrow (phone) page; the sheet is narrow beside the other panes, where
  // 64 cut the rotated names, so only a short sheet gives up the room.
  return { l: narrow ? 46 : 60, r: 14, t: short ? 52 : 84, b: 4 };
}

/** A chainage as the old sheet labels it: k+mmm to the metre ("2+500"); 1999.6 is 2+000, not 1+1000. */
export function fmtCh(c: number): string {
  const neg = c < 0;
  const a = Math.abs(c);
  let k = Math.floor(a / 1000 + 1e-9);
  let m = Math.round(a - k * 1000);
  if (m >= 1000) {
    k += 1;
    m -= 1000;
  }
  return `${neg && (k > 0 || m > 0) ? "−" : ""}${k}+${String(m).padStart(3, "0")}`;
}

/** A chainage for an axis label: k+mmm in metres, whole feet in feet. */
export function axisChainage(c: number, units: Units): string {
  return units.length === "ft" ? `${Math.round(c / M_PER_FT)}` : fmtCh(c);
}

/** A grade as the old sheet writes it: signed, one decimal, U+2212 for minus ("+13.6‰", "−0.2‰"). */
export function fmtG(g: number): string {
  const r = Math.abs(g) < 0.05 ? 0 : g;
  return `${r >= 0 ? "+" : "−"}${Math.abs(r).toFixed(1)}‰`;
}

/** A level in the display unit to d decimals (the old fmtZ), "–" when there is none. */
export function fmtZ(m: number | null | undefined, units: Units, d = 1): string {
  if (m === null || m === undefined || !Number.isFinite(m)) return "–";
  return (units.length === "ft" ? m / M_PER_FT : m).toFixed(d);
}

/** The old page's nice step: about target divisions of range, at 1, 2 or 5 times a power of ten. */
export function niceStep(range: number, target: number): number {
  const raw = Math.max(1e-9, range) / Math.max(1, target);
  const p = 10 ** Math.floor(Math.log10(raw));
  const m = raw / p;
  return (m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * p;
}

export interface Tick {
  /** The value in metres (a level or a chainage). */
  v: number;
  label: string;
}

/** The level axis: nice steps in the display unit, labelled with 0 decimals (1 under a unit step). */
export function levelTicks(z0: number, z1: number, units: Units, target: number): Tick[] {
  const k = units.length === "ft" ? 1 / M_PER_FT : 1;
  const u0 = z0 * k;
  const u1 = z1 * k;
  const step = niceStep(u1 - u0, target);
  const out: Tick[] = [];
  for (let i = Math.ceil(u0 / step); i * step <= u1 + 1e-9; i++) {
    const u = i * step;
    out.push({ v: u / k, label: u.toFixed(step < 1 ? 1 : 0) });
  }
  return out;
}

/** The chainage axis: nice steps in metres (feet in feet), labelled k+mmm. */
export function chainageTicks(c0: number, c1: number, units: Units, target: number): Tick[] {
  const k = units.length === "ft" ? 1 / M_PER_FT : 1;
  const step = niceStep((c1 - c0) * k, target) / k;
  const out: Tick[] = [];
  for (let i = Math.ceil(c0 / step); i * step <= c1 + 1e-6; i++)
    out.push({ v: i * step, label: axisChainage(i * step, units) });
  return out;
}

/** The vertical exaggeration of a plot: metres per pixel across over metres per pixel up. */
export function verticalExaggeration(plotW: number, plotH: number, c0: number, c1: number, z0: number, z1: number) {
  return plotH / Math.max(1e-9, z1 - z0) / (plotW / Math.max(1e-9, c1 - c0));
}

export function fmtVE(ve: number): string {
  return `V.E. ×${ve >= 10 ? ve.toFixed(0) : ve.toFixed(1)}`;
}

/** A label that may be drawn, at x along the axis, with how much room it needs on either side. */
export interface LabelCandidate {
  x: number;
  /** Lower draws first when there is no room for both; the selected one is always drawn. */
  priority: number;
  selected?: boolean;
}

/**
 * Which labels to draw so none is within gap pixels of another: the selected label first, then by priority, then
 * left to right. The old page kept the leftmost and dropped any within 18 px of the last one drawn; this keeps the
 * selected one and the more important ones (the ends of the line, then the rest) instead. Returns the indexes kept.
 */
export function thinLabels(items: LabelCandidate[], gap: number): Set<number> {
  const order = items
    .map((it, i) => ({ it, i }))
    .sort(
      (a, b) => Number(!!b.it.selected) - Number(!!a.it.selected) || a.it.priority - b.it.priority || a.it.x - b.it.x,
    );
  const kept: number[] = [];
  const out = new Set<number>();
  for (const { it, i } of order) {
    if (!it.selected && kept.some((x) => Math.abs(x - it.x) < gap)) continue;
    kept.push(it.x);
    out.add(i);
  }
  return out;
}

/** A straight piece of the design line between two vertices, with its grade. */
export interface Chord {
  c0: number;
  z0: number;
  c1: number;
  z1: number;
  g: number;
}

/** A vertex of the built line: the design vertices plus "x", where a platform's level runs out past its end. */
export interface BuiltVertex {
  c_m: number;
  z_m: number;
  kind: DesignVertex["kind"] | "x";
}

/**
 * The built line's vertices (the old page's design().dv, 750-802): vertical.rail@1 gives the design vertices, and
 * each platform's transition end ("x", where its level runs on past the platform end by half the curve) is the
 * vertex of a curve that is at no design vertex. Its level is on the platform's own grade line: the curve's grade
 * in past a platform end, its grade out before a platform start.
 */
export function builtVertices(dv: readonly DesignVertex[], curves: readonly VerticalCurve[] = []): BuiltVertex[] {
  const out: BuiltVertex[] = dv.map((v) => ({ c_m: v.c_m, z_m: v.z_m, kind: v.kind }));
  for (const cv of curves) {
    const c = cv.c_m;
    if (dv.some((v) => Math.abs(v.c_m - c) < 1e-6)) continue;
    let k = 0;
    while (k < dv.length && (dv[k] as DesignVertex).c_m < c) k++;
    const a = dv[k - 1];
    const b = dv[k];
    const afterEnd = a?.kind === "pe";
    const beforeStart = b?.kind === "ps";
    if (!afterEnd && !beforeStart) continue;
    const useA = afterEnd && (!beforeStart || c - (a as DesignVertex).c_m <= (b as DesignVertex).c_m - c);
    const z = useA
      ? (a as DesignVertex).z_m + (cv.g_in / 1000) * (c - (a as DesignVertex).c_m)
      : (b as DesignVertex).z_m - (cv.g_out / 1000) * ((b as DesignVertex).c_m - c);
    out.push({ c_m: c, z_m: z, kind: "x" });
  }
  return out.sort((p, q) => p.c_m - q.c_m);
}

/**
 * The chords of the built line that carry a grade label (the old page's chords(), 2642-2644): every pair of
 * neighbouring vertices except a point (no length), a flat platform (a station's own start and end at one level)
 * and a flat run to or from a transition end. With the curves, the chords run between the transition ends as the
 * old page's did, so a label reads the grade the train climbs and matches the solve's over-limit ranges.
 */
export function gradeChords(dv: readonly DesignVertex[], curves: readonly VerticalCurve[] = []): Chord[] {
  const bv = builtVertices(dv, curves);
  const out: Chord[] = [];
  for (let k = 0; k + 1 < bv.length; k++) {
    const a = bv[k] as BuiltVertex;
    const b = bv[k + 1] as BuiltVertex;
    if (b.c_m - a.c_m < 1e-6) continue;
    const flat = Math.abs(b.z_m - a.z_m) < 1e-9;
    if (flat && ((a.kind === "ps" && b.kind === "pe") || a.kind === "x" || b.kind === "x")) continue;
    out.push({ c0: a.c_m, z0: a.z_m, c1: b.c_m, z1: b.z_m, g: ((b.z_m - a.z_m) / (b.c_m - a.c_m)) * 1000 });
  }
  return out;
}

/** The chords wide enough for a label (66 px, 56 on a narrow canvas), each with its middle in view. */
export function gradeLabels(
  chords: readonly Chord[],
  x: (c: number) => number,
  left: number,
  right: number,
  minPx: number,
): { chord: Chord; xm: number; text: string }[] {
  const out: { chord: Chord; xm: number; text: string }[] = [];
  for (const chord of chords) {
    const xa = x(chord.c0);
    const xb = x(chord.c1);
    if (xb < left || xa > right || xb - xa < minPx) continue;
    const xm = (Math.max(xa, left) + Math.min(xb, right)) / 2;
    out.push({ chord, xm, text: fmtG(chord.g) });
  }
  return out;
}

/** Where each vertical curve starts and ends: PVI chainage ± L/2, for curves with a length. */
export function curveTicks(curves: readonly VerticalCurve[]): number[] {
  const out: number[] = [];
  for (const cv of curves) if (cv.L_m > 1e-6) out.push(cv.c_m - cv.L_m / 2, cv.c_m + cv.L_m / 2);
  return out;
}

/** The grade of a rail array at a chainage, by the nearest grid point; null off the grid. */
export function valueAt(arr: ArrayLike<number> | undefined, step: number, c: number): number | null {
  if (!arr) return null;
  const v = arr[Math.round(c / step)];
  return v === undefined || !Number.isFinite(v) ? null : v;
}

/** The words a station reads as in the text layer: "Bond Hill, 3+012, rail 162.7 m". */
export function stationText(name: string, c: number, z: number, units: Units): string {
  return `${name}, ${fmtCh(c)}, rail ${fmtZ(z, units)} ${units.length}`;
}

// ------------------------------------------------------------------------------------------------- stations
//
// What the station bands and panel say about a station, from station.facts@1 (engine/src/station/facts.ts). The
// words follow the old page's card and issue list (profiles.html 3024-3060, 2085-2101, 519-526), so Ben reads the
// same sentences he did there.

/** The structure types, labelled as the old page labels them (TYPES, profiles.html 256-263), in its dark colours. */
export const TYPES: Record<string, { label: string; colour: string }> = {
  elevated: { label: "Elevated", colour: "#e3a33c" },
  atgrade: { label: "At grade", colour: "#9cc24a" },
  trough: { label: "Open trough", colour: "#5cbfae" },
  cutcover: { label: "Cut & cover", colour: "#b088d6" },
  shield: { label: "Shield tunnel", colour: "#5f97d0" },
  deep: { label: "Deep bore (TBM)", colour: "#a9c8ee" },
  sunk: { label: "Sunk box", colour: "#4fc3cf" },
};

export const typeColour = (t: string | null | undefined): string => (t && TYPES[t]?.colour) || "#8b919e";
export const typeLabel = (t: string | null | undefined): string => (t && TYPES[t]?.label) || "Not known";

export const SEV_COLOURS = { error: "#f07178", warn: "#e6b450", info: "#8b919e" } as const;

/** The flag severity a station's bar is outlined in: its worst error or warning; info flags draw no outline. */
export function worstSeverity(flags: readonly { sev: string }[]): "error" | "warn" | null {
  if (flags.some((f) => f.sev === "error")) return "error";
  if (flags.some((f) => f.sev === "warn")) return "warn";
  return null;
}

/** A length in the display unit with its label: "13.6 m". */
export const fmtLen = (m: number | null | undefined, units: Units, d = 1): string =>
  `${fmtZ(m, units, d)} ${units.length}`;

/** The slide label by the drawn point: "slid −235 m" (signed, U+2212), in the display unit. */
export function slideText(slide: number, units: Units): string {
  const v = units.length === "ft" ? slide / M_PER_FT : slide;
  const r = Math.round(v);
  return `slid ${r < 0 ? "−" : "+"}${Math.abs(r)} ${units.length}`;
}

/** The depth tag under a bar: "13.6 down", "+2.1 up". depth is ground minus rail. */
export function depthTag(depth: number | null | undefined, units: Units): string | null {
  if (depth === null || depth === undefined || !Number.isFinite(depth)) return null;
  return depth >= 0 ? `${fmtZ(depth, units)} down` : `+${fmtZ(-depth, units)} up`;
}

/** A radius as the card shows it: "333 m", or "straight" (fmtR 2078). */
export const fmtR = (R: number | null | undefined): string =>
  R !== null && R !== undefined && Number.isFinite(R) ? `${Math.round(R)} m` : "straight";

/** An extra platform gap in centimetres (fmtGap 2079). */
export const fmtGap = (g: number): string => `${(g * 100).toFixed(1)} cm`;

/** The platform curve's severity word on the card: ERROR, WARNING or "exception, gap fillers" (3048). */
export function curveWord(c: { level: string | null; gapfill: boolean } | null | undefined): string | null {
  if (!c?.level) return null;
  return c.level === "error" ? (c.gapfill ? "exception, gap fillers" : "ERROR") : "WARNING";
}

/** The street line of the card (stationStreet 458). */
export function streetText(s: { text: string; street: string | null; subway: boolean; roads: string[] }): string {
  if (s.text === "under") return `under ${s.street}${s.subway ? " (built over the subway)" : ""}`;
  if (s.text === "crosses") return `crosses ${s.roads.join(", ")}`;
  if (s.text === "not_under_a_street") return "not under a street";
  return "no streets known here";
}

/** The street as the stations table shows it: the street, else the roads, else "-". */
export function streetShort(s: { text: string; street: string | null; roads: string[] }): string {
  if (s.text === "under" && s.street) return s.street;
  if (s.text === "crosses") return s.roads.join(", ");
  return "–";
}

interface Member {
  station: string;
  name: string;
  year: number | null;
}

/** The opening line of the card (3043): "1906 (Phase 1); later: Line 5 1909". */
export function openingText(a: { year: number | null; phase: string; at_open: Member[]; later: Member[] }): string {
  let t = a.year !== null ? `${a.year} (Phase ${a.phase})` : `no year set (Phase ${a.phase} assumed)`;
  if (a.at_open.length)
    t += `; interchange with ${a.at_open.map((m) => `${m.station} (${m.name}, ${m.year})`).join(", ")}`;
  if (a.later.length) t += `; later: ${a.later.map((m) => `${m.name} ${m.year}`).join(", ")}`;
  return t;
}

/** The hall room line of the card (3044): "needs 9.15 m of rail depth (island box); 13.60 here". */
export function hallRoomText(
  a: { d_hall_m: number | null; island: boolean; depth_m: number | null },
  units: Units,
): string {
  if (a.d_hall_m === null) return "–";
  return `needs ${fmtZ(a.d_hall_m, units, 2)} ${units.length} of rail depth (${a.island ? "island" : "side"} box); ${fmtZ(a.depth_m, units, 2)} here`;
}

/** Why a station has its type, in plain words (S24). */
export function typeReason(
  f: { type: string | null; type_why: string; depth_m: number | null; phase: string; cc_max_m: number | null },
  units: Units,
): string {
  const t = typeLabel(f.type);
  const d = f.depth_m;
  const lim = f.cc_max_m;
  switch (f.type_why) {
    case "selected":
      return `${t}: selected by Ben`;
    case "box_within_limit":
      return lim === null
        ? `${t}: by the rules`
        : `${t}: ${fmtLen(d, units)} down, within Phase ${f.phase}'s ${fmtLen(lim, units, 2)} limit`;
    case "mined_past_limit":
      return `${t}: ${fmtLen(d, units)} down, past Phase ${f.phase}'s ${fmtLen(lim, units, 2)} limit`;
    case "canon_box":
      return `${t}: in the canon's canal bed`;
    case "river":
      return `${t}: a river crossing`;
    case "drive_paint":
      return `${t}: its drive is painted ${t.toLowerCase()}`;
    case "open":
      return d !== null && d < 0
        ? `${t}: rail ${fmtLen(-d, units)} over the ground`
        : `${t}: ${fmtLen(d, units)} down, open by level`;
    case "no_rail":
      return "removed";
    default:
      return t;
  }
}

/** A station flag in Ben's words (designChecks 2085-2101, stationAccess 519-526, solveTypes 1401-1402, 2175). */
export function flagText(f: { kind: string; data?: unknown }, units: Units, name: (pid: string) => string): string {
  const d = (f.data ?? {}) as Record<string, unknown>;
  const n = (k: string) => (typeof d[k] === "number" ? (d[k] as number) : Number.NaN);
  const L = (k: string, dd = 1) => fmtLen(n(k), units, dd);
  const access = typeof d.access === "string" ? d.access : "";
  const who = d.source === "ben" ? "Ben" : "rule";
  const accessLabel = ACCESS_LABELS[access] ?? access;
  switch (f.kind) {
    case "platform_grade_over":
      return `Platform grade ${fmtG(n("grade_permille"))} is over the limit of ${n("limit_permille").toFixed(1)}‰ (${String(d.param)})`;
    case "platform_slide_over":
      return `Platform slid ${slideText(n("slide_m"), units).slice(5)} from its drawn point; the limit is ${L("limit_m", 0)}`;
    case "platform_overlap":
      return `Platform overlaps ${name(String(d.other))}: centres ${L("apart_m")} apart`;
    case "platform_curve": {
      const what = `Platform on a ${fmtR(n("R_m"))} curve: extra gap ${fmtGap(n("out_m"))} outside face, ${fmtGap(n("inn_m"))} inside face`;
      if (d.level === "error")
        return d.gapfill ? `${what} (exception, gap fillers)` : `${what}: needs gap fillers or a straighter line`;
      return `${what} (warning)`;
    }
    case "platform_s_curve":
      return `The platform's drawing has an S-curve (${n("pos_deg").toFixed(0)}° / ${n("neg_deg").toFixed(0)}°)`;
    case "platform_level_unset":
      return `Level not set: ground − 7.62 would put the rail at ${fmtLen(n("default_level_m"), units, 2)}`;
    case "access_crossunder":
      return `${d.island ? "An island" : "An interchange"} shallower than D_HALL (${fmtZ(n("depth_m"), units)} of ${fmtZ(n("d_hall_m"), units, 2)} ${units.length}): platform level with a crossunder; a hall needs the rail ${L("short_m")} deeper`;
    case "access_no_year":
      return `No opening year in the Chronology: the access type falls back to the line's phase (${String(d.phase)}), drawn dashed`;
    case "access_hall_too_shallow":
      return `${accessLabel} (${who}) needs the rail at least ${fmtLen(n("d_hall_m"), units, 2)} down for the hall over the box; it is ${fmtZ(n("depth_m"), units, 2)}: lower the station, or choose platform level`;
    case "access_mezzanine_clearance":
      return `${accessLabel} (${who}) needs ${fmtLen(n("need_m"), units, 2)} clear under the platform deck (the rail ${fmtLen(n("rail_over_ground_m"), units, 2)} over the ground); ${Number.isFinite(n("under_m")) ? `there is ${fmtZ(n("under_m"), units, 2)}` : "no ground here"}: raise the station`;
    case "access_not_mezzanine_on_elevated":
      return `${accessLabel} chosen for an elevated station: the platforms are reached from a mezzanine under them`;
    case "access_hall_over_mined":
      return `${accessLabel} (${who}) over a mined station: there is no box roof to build the hall on; choose a street hall`;
    case "station_tbm_before_phase_3":
      return `Bore (TBM) selected in Phase ${String(d.phase)}: boring machines come from Phase 3`;
    case "station_box_past_cc_max":
      return `Box ${L("depth_m")} down, past Phase ${String(d.phase)}'s cut and cover limit of ${fmtLen(n("cc_max_m"), units, 2)}`;
    case "station_box_roof_out_of_ground":
      return `Box roof out of the ground by up to ${L("worst_m", 2)}: it cannot be built without fill`;
    case "station_mined_in_box_stretch":
      return "Mined station in a stretch painted cut and cover";
    default:
      return f.kind.replace(/_/g, " ");
  }
}

const ACCESS_LABELS: Record<string, string> = {
  surface: "Surface station",
  platform_level: "Platform level",
  platform_level_xu: "Platform level, crossunder",
  end_halls: "End ticket halls",
  mezzanine: "Mezzanine",
  mezzanine_full: "Full-length mezzanine",
  mined_hall: "Street hall, mined station",
  deep: "Deep station",
  elevated_mezzanine: "Elevated, mezzanine under",
};

/** A station's structure outline as a quadrilateral in (c, z), tilted with the platform: the bar's ends are at
 * rail ∓ grade × half, and the outline keeps its top and bottom offsets from the rail along it. */
export function structureQuad(f: {
  c_m: number;
  half_m: number;
  rail_m: number | null;
  platform_grade_permille: number;
  structure: { top_m: number; bottom_m: number } | null;
}): [number, number][] | null {
  if (!f.structure || f.rail_m === null) return null;
  const g = f.platform_grade_permille / 1000;
  const za = f.rail_m - g * f.half_m;
  const zb = f.rail_m + g * f.half_m;
  const top = f.structure.top_m - f.rail_m;
  const bot = f.structure.bottom_m - f.rail_m;
  const a = f.c_m - f.half_m;
  const b = f.c_m + f.half_m;
  return [
    [a, za + top],
    [b, zb + top],
    [b, zb + bot],
    [a, za + bot],
  ];
}

/** One piece of a station's access drawing (stationAccess ranges, drawn as profiles.html 2549-2585 drew them). */
export interface AccessShape {
  what: "hall" | "mezzanine" | "crossunder" | "shaft";
  c0: number;
  c1: number;
  z0: number;
  z1: number;
  label: string;
  colour: string;
  dashed: boolean;
}

/** The access shapes of a station: halls on the box roof, the street mezzanine under an elevated one, the
 * crossunder (rail − 1.0 to rail − 3.75 for 3 m), the shaft from the ground to the structure's top. */
export function accessShapes(
  f: {
    c_m: number;
    rail_m: number | null;
    structure: { top_m: number } | null;
    access: {
      type: string;
      dashed: boolean;
      halls: [number, number][];
      passage: [number, number] | null;
      shaft: [number, number] | null;
      hall_bottom_m: number;
      hall_top_m: number;
      mezz: { halls: [number, number][]; bottom_m: number; top_m: number } | null;
    } | null;
  },
  groundAt: (c: number) => number | null,
): AccessShape[] {
  const a = f.access;
  if (!a || a.type === "surface" || f.rail_m === null) return [];
  const z = f.rail_m;
  const out: AccessShape[] = [];
  const cc = TYPES.cutcover?.colour as string;
  for (const [c0, c1] of a.halls)
    out.push({
      what: "hall",
      c0,
      c1,
      z0: a.hall_bottom_m,
      z1: a.hall_top_m,
      label: a.type === "end_halls" ? "ticket hall" : "mezzanine",
      colour: cc,
      dashed: a.dashed,
    });
  if (a.mezz)
    for (const [c0, c1] of a.mezz.halls)
      out.push({
        what: "mezzanine",
        c0,
        c1,
        z0: a.mezz.bottom_m,
        z1: a.mezz.top_m,
        label: "mezzanine / passthrough",
        colour: TYPES.elevated?.colour as string,
        dashed: a.dashed,
      });
  if (a.passage)
    out.push({
      what: "crossunder",
      c0: a.passage[0],
      c1: a.passage[1],
      z0: z - 3.75,
      z1: z - 1.0,
      label: "crossunder",
      colour: cc,
      dashed: a.dashed,
    });
  if (a.shaft) {
    const g = groundAt(f.c_m);
    if (g !== null)
      out.push({
        what: "shaft",
        c0: a.shaft[0],
        c1: a.shaft[1],
        z0: f.structure ? f.structure.top_m : z + 4.6,
        z1: g,
        label: a.type === "deep" ? "lifts" : "stairs",
        colour: "#8b919e",
        dashed: a.dashed,
      });
  }
  return out;
}

/** Whether a station draws the dashed D_HALL line (ground − D_HALL) over its platform: platform level stations and
 * stations with halls (2575). */
export const drawsDHall = (a: { type: string; d_hall_m: number | null; halls: unknown[] } | null): boolean =>
  !!a && a.d_hall_m !== null && (a.type === "platform_level" || a.type === "platform_level_xu" || a.halls.length > 0);
