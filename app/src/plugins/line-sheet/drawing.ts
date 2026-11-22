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
  return { l: narrow ? 46 : 60, r: 14, t: short ? 52 : narrow ? 64 : 84, b: 4 };
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
  return `${neg ? "−" : ""}${k}+${String(m).padStart(3, "0")}`;
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

/**
 * The chords of the design line that carry a grade label: every pair of neighbouring vertices except a point
 * (no length) and a flat platform (a station's own start and end at one level), as the old page skipped them.
 */
export function gradeChords(dv: readonly DesignVertex[]): Chord[] {
  const out: Chord[] = [];
  for (let k = 0; k + 1 < dv.length; k++) {
    const a = dv[k] as DesignVertex;
    const b = dv[k + 1] as DesignVertex;
    if (b.c_m - a.c_m < 1e-6) continue;
    if (a.kind === "ps" && b.kind === "pe" && Math.abs(b.z_m - a.z_m) < 1e-9) continue;
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
