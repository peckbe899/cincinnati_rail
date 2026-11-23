// The line sheet's bands from section.solve@1 (claude/hub_maps/engine_port_plan.md, section 1): everything the old
// Rail Profiles page drew between the stations (profiles.html 2276-2869), from the whole solve of the draft
// (BandData.solved) and its input (BandData.solveInput):
//
//   water          the rivers: the pool line, its shading, the name and the bed it was given
//   ground works   the finished ground against the surveyed one: street re-grades and drawn ground shaded, open cuts
//                  hatched, the surveyed ground dashed (REGRADED, CUT)
//   context        other systems' structures (CUT, Norwood Central) from the Deck, grey, dashed
//   crossings      a dashed line at each crossing, the other line's structure as a box at its rail and "Line 3 box
//                  7.3 m apart, needs 6.1" (red where short)
//   locks          locked stretches shaded with "Locked"
//   over grade     a red halo over a grade past its limit
//   outlines       tunnel and box outlines by structure (roof or crown to floor or invert), the made-up bed over a
//                  sunk box, the channel over it, the legal band dashed (tube colour: the shallowest a tube may run;
//                  box colour: the deepest a box may go), the unbuildable hatch, viaducts with girders or trusses
//                  and piers
//   roads          the streets the line runs under (dotted, solid where built over the subway) and the roads it
//                  crosses (a bar on the street in the road class's colour), named where there is room
//   curve grade    grade plus curve allowance over the limit, dashed under the rail with "+15.7‰ with curve"
//   drawn ground   Ben's drawn ground lines and their points
//   shafts         a marker on the rail with "shaft"
//   issues         every finding as a triangle along the bottom of the plot, in its severity's colour
//   crossing ticks a tick on the plot's top edge at each crossing with the other line's tag ("L3", "E trunk")
//   strips         the structure band along the whole line (with the unbuildable and misfit hatch and Ben's paints
//                  marked under it), the Chronology band (year and phase), and the overview of the whole line
//
// The rail is the sheet's live one (BandData.rail): the outlines are the solve's offsets from the rail, so during a
// drag they follow the rail at once and the structure is the last solve's, as the old page drew it (LAST_T, 1339).

import type { SolvedSection } from "@cr/engine/contract";
import type { BandData, BandDef, Handle, SheetView } from "../../core/plugin.ts";
import { fmtG, SEV_COLOURS, TYPES, typeColour, valueAt } from "./drawing.ts";
import type { ProfileData } from "./model.ts";
import { stationStripBand } from "./stations.ts";
import { groundLines } from "./tools.ts";

export type ShowMode = "rail" | "railbox" | "box";

const UI_FONT = "system-ui, sans-serif";
const NUM_FONT = "ui-monospace, SFMono-Regular, Menlo, monospace";
const PAPER = "#16181d";
const INK = "#d8dbe2";
const MUTED = "#8b919e";
const GRID_MAJOR = "#4a505c";
export const WATER = "#5aa9e0";
export const WATER_FILL = "rgba(90, 169, 224, 0.16)";
export const EARTH = "#b39c72";
const WARN = SEV_COLOURS.error;
const CAUTION = SEV_COLOURS.warn;
/** Road classes, the old page's colours made lighter for the dark sheet (ROAD_COL, 450). */
export const ROAD_COLOURS: Record<string, string> = { highway: "#e0675c", major: "#e09a3a", minor: "#a0a0a0" };
/** The Chronology's phase colours (2799). */
export const PHASE_COLOURS: Record<string, string> = {
  "1": "#2f6fb3",
  "2": "#c2571a",
  "3": "#2e8b57",
  later: "#8e5bb5",
};

const TUNNEL = new Set(["shield", "deep", "cutcover", "sunk"]);

type Run<T> = readonly [T, number, number];
type Struct = SolvedSection["struct_runs"][number][0];

// ----------------------------------------------------------------------------------------------- pure helpers

/** The run holding c (runs tile the line from 0 to its length), by binary search; the last one past the end. */
export function runAt<T>(runs: readonly Run<T>[], c: number): Run<T> | null {
  if (!runs.length) return null;
  let lo = 0;
  let hi = runs.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if ((runs[mid] as Run<T>)[1] <= c) lo = mid;
    else hi = mid - 1;
  }
  return runs[lo] as Run<T>;
}

/** A value per sample (null where none) at c, by straight lines between samples. */
export function sampleAt(arr: ArrayLike<number | null> | undefined, step: number, c: number): number | null {
  if (!arr?.length) return null;
  const k = c / step;
  const i = Math.max(0, Math.min(arr.length - 1, Math.floor(k)));
  const a = arr[i];
  const b = arr[Math.min(arr.length - 1, i + 1)];
  if (a == null || !Number.isFinite(a)) return null;
  if (b == null || !Number.isFinite(b)) return a;
  return a + (b - a) * Math.min(1, Math.max(0, k - i));
}

/** The words for another line's structure at a crossing (the old label: "box", "type A tube (cast iron ...)"). */
export function structWord(s: { k: string; tube?: string } | null, tubes?: Record<string, { label: string }>): string {
  if (!s) return "";
  if ((s.k === "tube" || s.k === "bore") && s.tube && tubes?.[s.tube])
    return (tubes[s.tube] as { label: string }).label;
  return (
    (
      {
        box: "box",
        tube: "tube",
        bore: "bored tube",
        sunk: "sunk box",
        elevated: "viaduct",
        atgrade: "at grade",
        trough: "open trough",
      } as Record<string, string>
    )[s.k] ?? s.k
  );
}

/** A crossing line's tag as the old page wrote it on the top edge (2829): "L3", "CVG", "RER-B" as "RB". */
export const crossingTag = (w: string): string =>
  w
    .replace("CVG Express", "CVG")
    .replace(/^Line /, "L")
    .replace("RER-", "R");

type Flag = SolvedSection["flags"][number];

/** A finding in plain words for its tooltip and the text layer: what was found, with its numbers; its rule id. */
export function flagWords(f: Flag, m: (v: number, digits?: number) => string): string {
  return `${f.page}: ${flagBody(f, m)} (${f.rule})`;
}

/** What a finding found, with its numbers, and nothing else (the issues list puts its kind and rule apart). */
export function flagBody(f: Flag, m: (v: number, digits?: number) => string): string {
  const d = f.data as Record<string, unknown>;
  const n = (k: string) => (typeof d[k] === "number" ? (d[k] as number) : Number.NaN);
  const g = (k: string) => fmtG(n(k));
  const words: Record<string, () => string> = {
    grade_over_sustained: () =>
      `grade ${g("g")} over the ${g("lim")} limit, sustained (${g("avg")} over ${m(n("W"), 0)})`,
    grade_over_local: () => `grade ${g("g")} over the ${g("lim")} limit, local (${g("avg")} over ${m(n("W"), 0)})`,
    grade_over_straight_underground: () => `grade ${g("g")} on a straight underground stretch`,
    curve_grade_sustained: () => `grade with the curve allowance ${g("worst")} over the ${g("lim")} limit, sustained`,
    curve_grade_local: () => `grade with the curve allowance ${g("worst")} over the ${g("lim")} limit, local`,
    crossing_short: () => `${d.with}: ${m(n("clear"))} apart, needs ${m(n("need"))}`,
    crossing_level: () => `${d.with}: crosses at the same level`,
    context_short: () => `a structure of another system: ${m(n("clear"))} apart, needs ${m(n("need"))}`,
    tube_cover_short: () => `tube cover ${m(n("cv"))}, needs ${m(n("need"))}`,
    box_roof_above_ground: () => `box roof ${m(-n("cv"))} above the ground`,
    box_roof_forms_street: () => `box roof ${m(n("cv"))} under the ground: it forms the street`,
    unbuildable_cover: () => `cannot be bored: short of cover by up to ${m(n("worst"))}`,
    unbuildable_box: () => `cannot be dug: a box past its depth limit by up to ${m(n("worst"))}`,
    unbuildable_roof: () => `the station box roof stands out of the ground by up to ${m(n("worst"))}`,
    paint_misfit: () => `the ${String(d.t)} paint does not fit (${String(d.why)}, by up to ${m(n("worst"))})`,
    vertical_curve_short: () => `vertical curve ${m(n("got"), 0)} long, needs ${m(n("need"), 0)}`,
    drainage_flat: () => `a tunnel grade of ${g("g")} over ${m(n("len"), 0)}: flatter than ${g("min")} for drainage`,
    low_cover: () => `low cover over ${m(n("length_m"), 0)}, ${m(n("worst_m"))} at the least`,
    sunk_box_high: () => `the sunk box in the ${String(d.river)} stands ${m(n("over"))} too high`,
    sunk_box_low: () => `the sunk box in the ${String(d.river)} sits ${m(n("over"))} too low`,
    deep_in_shallow_canon: () => `a station ${m(n("d"))} deep in a shallow canon section`,
    stretch_unbuildable: () => `neither a box nor a bored tunnel can be built over ${m(n("length_m"), 0)}`,
    mined_in_box_stretch: () => `${String(d.station)} is a mined station inside a cut-and-cover stretch`,
    approach_runs_into_station: () => `an approach box runs into ${String(d.into)}`,
    spacing_change_in_tunnel: () => `the track spacing changes inside a tunnel (${String(d.from)} to ${String(d.to)})`,
  };
  return words[f.kind]?.() ?? f.kind.replace(/_/g, " ");
}

/** Whether a finding is drawn as a marker: everything but the stretch notes, which the old page listed apart. */
export const markerShown = (f: { kind: string; sev: string }): boolean => f.kind !== "stretch";

/** The text of a crossing's clearance label, as the old page wrote it (2399). */
export function clearanceText(
  x: { with: string; to: { k: string; tube?: string } | null; clear: number | null; need: number | null },
  tubes: Record<string, { label: string }> | undefined,
  fmt: (m: number) => string,
): string {
  return `${x.with} ${structWord(x.to, tubes)} · ${fmt(x.clear ?? 0)} apart, needs ${fmt(x.need ?? 0)}`;
}

// ---------------------------------------------------------------------------------------------------- drawing

function clipPlot(g: CanvasRenderingContext2D, v: SheetView): void {
  g.beginPath();
  g.rect(v.plot.x, v.plot.y, v.plot.w, v.plot.h);
  g.clip();
}

const railOf =
  (d: BandData) =>
  (c: number): number | null =>
    d.rail ? valueAt(d.rail.rail_m, d.rail.step_m, c) : null;

const fmtM = (v: SheetView, m: number, digits = 1): string => `${v.units.format(m, "m", digits)} ${v.units.label("m")}`;

/** The pixel columns of the plot in view, with their chainage. */
function* columns(v: SheetView, stride = 1): Generator<{ x: number; c: number }> {
  const P = v.plot;
  for (let k = 0; k <= Math.ceil(P.w); k += stride) {
    const x = P.x + k;
    yield { x, c: v.c(x) };
  }
}

/** A crossing's colour on the plot: red when short of its clearance, whether or not the other line is set yet (the
 * old page, 2440: the list holds a crossing with a line not set apart, the plot never greys it). */
export function clearanceColour(x: { ok: boolean }): string {
  return x.ok ? MUTED : WARN;
}

/** Where a label w px wide may go beside a mark at (px, ym), in order: right of it at its middle, one and two lines
 * above or below, then the same on its left; only spots inside the plot. */
export function labelSpots(
  px: number,
  ym: number,
  w: number,
  P: { x: number; y: number; w: number; h: number },
): { x0: number; y0: number; x1: number; y1: number }[] {
  const out: { x0: number; y0: number; x1: number; y1: number }[] = [];
  for (const left of [false, true])
    for (const dy of [0, -16, 16, -32, 32]) {
      const x0 = left ? px - 8 - w : px + 6;
      const b = { x0, y0: ym + dy - 7, x1: x0 + w + 2, y1: ym + dy + 7 };
      if (b.x0 >= P.x && b.x1 <= P.x + P.w && b.y0 >= P.y && b.y1 <= P.y + P.h) out.push(b);
    }
  return out;
}

/** Labels kept apart: a box is drawn only where no earlier one is. */
class Placer {
  boxes: { x0: number; y0: number; x1: number; y1: number }[] = [];
  free(b: { x0: number; y0: number; x1: number; y1: number }, pad = 2): boolean {
    return !this.boxes.some((a) => a.x0 < b.x1 + pad && b.x0 < a.x1 + pad && a.y0 < b.y1 + pad && b.y0 < a.y1 + pad);
  }
  take(b: { x0: number; y0: number; x1: number; y1: number }): void {
    this.boxes.push(b);
  }
}
let placer = new Placer();

/** Keep a box clear for the later labels of this paint (the platform band's interchange tags). */
export function reserveLabel(b: { x0: number; y0: number; x1: number; y1: number }): void {
  placer.take(b);
}

/** The rivers: shaded from the pool down, the pool line, the name and what the bed is (2337-2349). */
export const waterBand: BandDef = {
  id: "water",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    placer = new Placer();
    const ssi = d.solveInput;
    const rivers = d.solved?.rivers ?? ssi?.rivers ?? [];
    const pool = ssi?.settings.pool;
    if (!rivers.length || pool === undefined) return;
    const P = v.plot;
    g.save();
    clipPlot(g, v);
    for (const r of rivers) {
      if (r.c1 < v.c0 || r.c0 > v.c1) continue;
      const x0 = v.x(r.c0);
      const x1 = v.x(r.c1);
      const yp = v.y(pool);
      const grd = g.createLinearGradient(0, yp, 0, P.y + P.h);
      grd.addColorStop(0, "rgba(90, 169, 224, 0.30)");
      grd.addColorStop(1, "rgba(0, 0, 0, 0)");
      g.fillStyle = grd;
      g.fillRect(x0, yp, x1 - x0, P.y + P.h - yp);
      g.strokeStyle = WATER;
      g.lineWidth = 1.5;
      g.beginPath();
      g.moveTo(x0, yp);
      g.lineTo(x1, yp);
      g.stroke();
      if (x1 - x0 > 30) {
        const xm = (x0 + x1) / 2;
        g.fillStyle = WATER;
        g.beginPath();
        g.moveTo(xm - 5, yp - 9);
        g.lineTo(xm + 5, yp - 9);
        g.lineTo(xm, yp - 2);
        g.fill();
        g.font = `600 11px ${UI_FONT}`;
        g.textAlign = "center";
        g.textBaseline = "bottom";
        g.fillText(String(r.name), xm, yp - 12);
        if (x1 - x0 > 120) {
          g.font = `11px ${UI_FONT}`;
          g.textBaseline = "top";
          const bed = (r as { bed?: number | null }).bed;
          g.fillText(
            `normal pool ${fmtM(v, pool, 2)} · ${bed != null ? "bed given (no survey)" : "surveyed riverbed"}`,
            xm,
            yp + 6,
          );
        }
      }
      d.mark?.({ kind: "river", id: String(r.name), c0: r.c0, c1: r.c1, x0, x1, y: yp });
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

/** The finished ground against the surveyed one (2378-2402): raised ground shaded, cuts hatched, the survey dashed. */
export const groundWorksBand: BandDef = {
  id: "ground-works",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const s = d.solved;
    const gr = d.input?.ground;
    if (!s || !gr) return;
    const fin = s.ground.finished;
    const step = s.step_m;
    const rivers = s.rivers;
    g.save();
    clipPlot(g, v);
    let seg: [number, number, number][] = [];
    const hatch = (() => {
      const hc = document.createElement("canvas");
      hc.width = hc.height = 8;
      const hx = hc.getContext("2d");
      if (!hx) return null;
      hx.strokeStyle = EARTH;
      hx.globalAlpha = 0.6;
      hx.beginPath();
      hx.moveTo(0, 8);
      hx.lineTo(8, 0);
      hx.stroke();
      return g.createPattern(hc, "repeat");
    })();
    const flush = () => {
      if (seg.length > 1) {
        const first = seg[0] as [number, number, number];
        const cut = first[1] < first[2];
        g.globalAlpha = cut ? 1 : 0.32;
        g.fillStyle = cut && hatch ? hatch : EARTH;
        g.beginPath();
        seg.forEach(([x, f], i) => {
          if (i) g.lineTo(x, v.y(f));
          else g.moveTo(x, v.y(f));
        });
        for (let j = seg.length - 1; j >= 0; j--) {
          const p = seg[j] as [number, number, number];
          g.lineTo(p[0], v.y(p[2]));
        }
        g.closePath();
        g.fill();
        g.globalAlpha = 1;
        g.setLineDash([4, 3]);
        g.strokeStyle = EARTH;
        g.lineWidth = 1.2;
        g.beginPath();
        seg.forEach(([x, , o], i) => {
          if (i) g.lineTo(x, v.y(o));
          else g.moveTo(x, v.y(o));
        });
        g.stroke();
        g.setLineDash([]);
        if (seg.length > 60) {
          const m = seg[Math.floor(seg.length / 2)] as [number, number, number];
          g.font = `600 11px ${UI_FONT}`;
          g.textAlign = "center";
          g.textBaseline = "bottom";
          g.fillStyle = EARTH;
          g.fillText(m[1] > m[2] ? "REGRADED" : "CUT", m[0], v.y(Math.max(m[1], m[2])) - 4);
        }
      }
      seg = [];
    };
    for (const { x, c } of columns(v)) {
      if (c < 0 || c > s.length_m || rivers.some((r) => c >= r.c0 && c <= r.c1)) {
        flush();
        continue;
      }
      const f = sampleAt(fin, step, c);
      const o = valueAt(gr.z_m, gr.step_m, c);
      if (f !== null && o !== null && Math.abs(f - o) > 0.02) {
        const last = seg[seg.length - 1];
        if (last && last[1] > last[2] !== f > o) flush();
        seg.push([x, f, o]);
      } else flush();
    }
    flush();
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

/** Other systems' structures from the Deck, grey and dashed, with their label and level (2404-2436). */
export const contextBand: BandDef = {
  id: "context",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const blocks = d.solveInput?.context.blocks ?? [];
    if (!blocks.length) return;
    const bad = new Set((d.solved?.context ?? []).filter((x) => !x.ok).map((x) => x.block));
    const P = v.plot;
    g.save();
    clipPlot(g, v);
    blocks.forEach((b, bi) => {
      if (b.c1 < v.c0 || b.c0 > v.c1 || !b.p.length) return;
      const isBad = bad.has(bi);
      const hi = b.o ? 0 : b.t;
      const pp = b.p;
      const line = (off: number) => {
        g.beginPath();
        pp.forEach(([c, z], i) => {
          if (i) g.lineTo(v.x(c), v.y(z + off));
          else g.moveTo(v.x(c), v.y(z + off));
        });
      };
      g.beginPath();
      pp.forEach(([c, z], i) => {
        if (i) g.lineTo(v.x(c), v.y(z + hi));
        else g.moveTo(v.x(c), v.y(z + hi));
      });
      for (let j = pp.length - 1; j >= 0; j--) {
        const [c, z] = pp[j] as [number, number];
        g.lineTo(v.x(c), v.y(z - b.b));
      }
      g.closePath();
      g.fillStyle = INK;
      g.globalAlpha = 0.1;
      g.fill();
      g.globalAlpha = 1;
      g.strokeStyle = isBad ? WARN : MUTED;
      g.lineWidth = isBad ? 1.6 : 1;
      g.setLineDash(b.o ? [] : [5, 3]);
      g.stroke();
      g.setLineDash([]);
      if (b.o) {
        g.setLineDash([2, 3]);
        g.globalAlpha = 0.7;
        line(b.t);
        g.stroke();
        g.setLineDash([]);
        g.globalAlpha = 1;
      }
      g.strokeStyle = INK;
      g.globalAlpha = 0.55;
      g.lineWidth = 1.2;
      line(0);
      g.stroke();
      g.globalAlpha = 0.65;
      g.fillStyle = INK;
      for (const [u, w, z] of b.pl ?? []) g.fillRect(v.x(u), v.y(z) - 3, Math.max(1.5, v.x(w) - v.x(u)), 3);
      g.globalAlpha = 1;
      const xa = v.x(b.c0);
      const xb = v.x(b.c1);
      if (xb - xa > 46) {
        const zs = pp.map((q) => q[1]);
        const z0 = Math.min(...zs);
        const z1 = Math.max(...zs);
        const txt = `${b.l} · ${v.units.format(z0, "m", 1)}${z1 - z0 > 0.15 ? `–${v.units.format(z1, "m", 1)}` : ""} ${v.units.label("m")}`;
        g.font = `600 11px ${UI_FONT}`;
        g.textAlign = "center";
        g.textBaseline = "bottom";
        g.fillStyle = isBad ? WARN : MUTED;
        const xm = Math.min(P.x + P.w - 60, Math.max(P.x + 60, (Math.max(xa, P.x) + Math.min(xb, P.x + P.w)) / 2));
        g.fillText(txt, xm, v.y(z1 + (b.o ? b.t : hi)) - 3);
      }
      d.mark?.({ kind: "context", id: String(b.n), c0: b.c0, c1: b.c1, bad: isBad });
    });
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

/** Each crossing: a dashed line, the other line's structure as a box at its rail and its clearance (2438-2453). */
export const crossingsBand: BandDef = {
  id: "crossings",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const xs = d.solveInput?.crossings ?? [];
    const cl = d.solved?.crossings ?? [];
    if (!xs.length && !cl.length) return;
    const P = v.plot;
    const tubes = d.solveInput?.structure?.tubes as Record<string, { label: string }> | undefined;
    g.save();
    clipPlot(g, v);
    g.strokeStyle = GRID_MAJOR;
    g.setLineDash([3, 4]);
    g.lineWidth = 1;
    for (const x of xs) {
      if (x.c < v.c0 || x.c > v.c1) continue;
      const px = Math.round(v.x(x.c)) + 0.5;
      g.beginPath();
      g.moveTo(px, P.y);
      g.lineTo(px, P.y + P.h);
      g.stroke();
    }
    g.setLineDash([]);
    g.font = `600 11px ${UI_FONT}`;
    g.textAlign = "left";
    g.textBaseline = "middle";
    // the short ones first, so their labels win the room
    const order = [...cl].sort((a, b) => Number(a.ok) - Number(b.ok));
    for (const x of order) {
      if (x.zo == null || x.c < v.c0 || x.c > v.c1 || !x.to) continue;
      const open = x.to.k === "elevated" || x.to.k === "atgrade";
      const top = open ? 0.3 : x.to.top;
      const px = v.x(x.c);
      const y0 = v.y(x.zo + top);
      const y1 = v.y(x.zo - x.to.below);
      const colour = clearanceColour(x);
      g.fillStyle = colour;
      g.globalAlpha = 0.85;
      g.fillRect(px - 4, y0, 8, Math.max(2, y1 - y0));
      g.globalAlpha = 1;
      // one decimal kept, as the old page wrote it (2443: toFixed(1)); the hub's units trim "9.0" to "9"
      const text = clearanceText(x, tubes, (m) => `${v.units.toDisplay(m, "m").toFixed(1)} ${v.units.label("m")}`);
      const w = g.measureText(text).width;
      // beside the other line's box, else a line or two above or below it, else on its left: the old page drew
      // every clearance (over each other where they met); a label that finds no room at all is left off
      const box = labelSpots(px, (y0 + y1) / 2, w, P).find((b) => placer.free(b)) ?? null;
      const shown = box !== null;
      if (box) {
        placer.take(box);
        g.globalAlpha = 0.8;
        g.fillStyle = PAPER;
        g.fillRect(box.x0, box.y0, box.x1 - box.x0, box.y1 - box.y0);
        g.globalAlpha = 1;
        g.fillStyle = colour;
        g.fillText(text, box.x0 + 1, (box.y0 + box.y1) / 2);
      }
      d.mark?.({
        kind: "clearance",
        id: x.wid,
        c: x.c,
        ok: x.ok,
        pending: x.pending,
        text,
        drawn: shown,
        x: px,
        y0,
        y1,
      });
      d.report?.({ kind: "clearance", id: x.wid, text, c: x.c, z: x.zo, drawn: shown });
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

/** Locked stretches: shaded, edged with dashes, "Locked" along the top (2455-2462). */
export const locksBand: BandDef = {
  id: "locks",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const locks = d.solved?.canon.locks ?? [];
    if (!locks.length) return;
    const P = v.plot;
    g.save();
    clipPlot(g, v);
    for (const lk of locks) {
      if (lk.hi < v.c0 || lk.lo > v.c1) continue;
      const xa = Math.max(P.x, v.x(lk.lo));
      const xb = Math.min(P.x + P.w, v.x(lk.hi));
      g.fillStyle = INK;
      g.globalAlpha = 0.05;
      g.fillRect(xa, P.y, xb - xa, P.h);
      g.globalAlpha = 1;
      g.strokeStyle = MUTED;
      g.setLineDash([3, 3]);
      g.beginPath();
      g.moveTo(Math.round(xa) + 0.5, P.y);
      g.lineTo(Math.round(xa) + 0.5, P.y + P.h);
      g.moveTo(Math.round(xb) - 0.5, P.y);
      g.lineTo(Math.round(xb) - 0.5, P.y + P.h);
      g.stroke();
      g.setLineDash([]);
      if (xb - xa > 60) {
        g.fillStyle = MUTED;
        g.font = `11px ${NUM_FONT}`;
        g.textBaseline = "top";
        g.fillText("Locked", xa + 4, P.y + 3);
      }
      d.mark?.({ kind: "lock", id: lk.name ?? "", c0: lk.lo, c1: lk.hi });
    }
    g.restore();
    g.textBaseline = "alphabetic";
  },
};

/** A grade past its limit: a red halo along the rail (2466-2471). */
export const overGradeBand: BandDef = {
  id: "over-grade",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const over = d.solved?.over ?? [];
    const rail = railOf(d);
    if (!over.length || !d.rail) return;
    g.save();
    clipPlot(g, v);
    g.strokeStyle = WARN;
    g.globalAlpha = 0.28;
    g.lineWidth = 10;
    g.lineCap = "round";
    for (const o of over) {
      if (o.c1 < v.c0 || o.c0 > v.c1) continue;
      const a = rail(o.c0);
      const b = rail(o.c1);
      if (a === null || b === null) continue;
      g.beginPath();
      g.moveTo(v.x(o.c0), v.y(a));
      g.lineTo(v.x(o.c1), v.y(b));
      g.stroke();
      d.mark?.({ kind: "over", id: "", c0: o.c0, c1: o.c1, sev: o.sev });
    }
    g.restore();
  },
};

interface Column {
  x: number;
  c: number;
  z: number;
  t: string;
  sc: Struct;
}

/** The type and the structure at each pixel column, at the live rail. */
function railColumns(v: SheetView, d: BandData, s: SolvedSection): Column[] {
  const rail = railOf(d);
  const out: Column[] = [];
  for (const { x, c: c0 } of columns(v)) {
    const c = Math.min(s.length_m, Math.max(0, c0));
    const z = rail(c);
    const t = runAt(s.type_runs, c);
    const sc = runAt(s.struct_runs, c);
    if (z === null || !t || !sc) continue;
    out.push({ x, c, z, t: t[0], sc: sc[0] });
  }
  return out;
}

/**
 * The structures (2473-2575): each run of one tunnel type outlined from roof or crown to floor or invert and
 * filled, ends closed where it meets another; the made-up bed over a sunk box; the channel over it; the legal band;
 * the unbuildable hatch; viaduct spans with their girders or trusses and piers. None in Show: Rail.
 */
export const outlinesBand: BandDef = {
  id: "outlines",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const s = d.solved;
    if (!s || !d.rail || d.show === "rail") return;
    const show = d.show ?? "railbox";
    const rail = railOf(d);
    const P = v.plot;
    const pts = railColumns(v, d, s);
    g.save();
    clipPlot(g, v);
    // tunnel and box outlines
    const same = (a: Column, b: Column) =>
      a.t === b.t && a.sc.k === b.sc.k && a.sc.below === b.sc.below && a.sc.top === b.sc.top;
    for (let k0 = 0; k0 < pts.length - 1; ) {
      let k1 = k0;
      while (k1 + 1 < pts.length && same(pts[k1 + 1] as Column, pts[k0] as Column)) k1++;
      const p0 = pts[k0] as Column;
      if (TUNNEL.has(p0.t)) {
        const run = pts.slice(k0, Math.min(k1 + 2, pts.length));
        const eh = p0.sc.top;
        const inv = p0.sc.below;
        const colour = typeColour(p0.t);
        g.fillStyle = colour;
        g.globalAlpha = show === "box" ? 0.24 : 0.14;
        g.beginPath();
        run.forEach((p, j) => {
          if (j) g.lineTo(p.x, v.y(p.z + eh));
          else g.moveTo(p.x, v.y(p.z + eh));
        });
        for (let j = run.length - 1; j >= 0; j--) {
          const p = run[j] as Column;
          g.lineTo(p.x, v.y(p.z - inv));
        }
        g.closePath();
        g.fill();
        g.strokeStyle = colour;
        g.globalAlpha = 0.8;
        g.lineWidth = show === "box" ? 1.75 : 1.25;
        for (const off of [eh, -inv]) {
          g.beginPath();
          run.forEach((p, j) => {
            if (j) g.lineTo(p.x, v.y(p.z + off));
            else g.moveTo(p.x, v.y(p.z + off));
          });
          g.stroke();
        }
        for (const p of [k0 > 0 ? run[0] : null, k1 + 1 < pts.length ? run[run.length - 1] : null]) {
          if (!p) continue;
          g.beginPath();
          g.moveTo(p.x, v.y(p.z + eh));
          g.lineTo(p.x, v.y(p.z - inv));
          g.stroke();
        }
        g.globalAlpha = 1;
        d.mark?.({ kind: "outline", id: "", type: p0.t, k: p0.sc.k, c0: p0.c, c1: (run[run.length - 1] as Column).c });
      }
      k0 = k1 + 1;
    }
    // the made-up bed over a sunk box roof that stands above the river bed
    const bed = s.ground.bed;
    for (const mb of s.made_bed) {
      const c0 = mb.i0 * s.step_m;
      const c1 = (mb.i0 + mb.z.length - 1) * s.step_m;
      if (c1 < v.c0 || c0 > v.c1) continue;
      g.fillStyle = EARTH;
      g.globalAlpha = 0.45;
      g.beginPath();
      mb.z.forEach((z, j) => {
        const x = v.x((mb.i0 + j) * s.step_m);
        if (j) g.lineTo(x, v.y(z));
        else g.moveTo(x, v.y(z));
      });
      for (let j = mb.z.length - 1; j >= 0; j--) {
        const bj = bed[mb.i0 + j];
        const b = bj != null && Number.isFinite(bj) ? bj : (mb.z[j] ?? 0);
        g.lineTo(v.x((mb.i0 + j) * s.step_m), v.y(b));
      }
      g.closePath();
      g.fill();
      g.globalAlpha = 1;
      d.mark?.({ kind: "made-bed", id: "", c0, c1 });
    }
    // the channel over each sunk box: the shallowest water from the pool to the bed over the box (2500-2524)
    const ssi = d.solveInput;
    const pool = ssi?.settings.pool;
    if (pool !== undefined && ssi) {
      for (const r of s.rivers) {
        const band = (r as { band?: { low: number } | null }).band;
        if (
          r.c1 < v.c0 ||
          r.c0 > v.c1 ||
          !band ||
          (r as { bridge?: unknown }).bridge ||
          (r as { alongShore?: boolean }).alongShore
        )
          continue;
        let best: { c: number; w: number; top: number; made: boolean } | null = null;
        for (let i = Math.ceil(r.c0 / s.step_m); i * s.step_m <= r.c1; i++) {
          const c = i * s.step_m;
          const b = bed[i];
          if (b == null || !Number.isFinite(b) || b >= pool) continue;
          if (runAt(s.type_runs, c)?.[0] !== "sunk") continue;
          const mb = s.made_bed.find((m) => i >= m.i0 && i < m.i0 + m.z.length);
          const made = mb ? (mb.z[i - mb.i0] ?? null) : null;
          if (made === null && b > band.low + ssi.settings.riverFlatTol) continue;
          const top = made ?? b;
          const w = pool - top;
          if (!best || w < best.w) best = { c, w, top, made: made !== null };
        }
        if (!best) continue;
        const nav = !!(r as { navigable?: boolean }).navigable;
        const need = ssi.settings.riverClearWater;
        const short = nav && best.w < need - 0.005;
        const col = short ? WARN : WATER;
        g.strokeStyle = col;
        g.fillStyle = col;
        g.lineWidth = 1.25;
        if (nav) {
          const yn = v.y(pool - need);
          g.setLineDash([6, 4]);
          g.globalAlpha = 0.8;
          g.beginPath();
          g.moveTo(v.x(r.c0), yn);
          g.lineTo(v.x(r.c1), yn);
          g.stroke();
          g.setLineDash([]);
          g.font = `10px ${UI_FONT}`;
          g.textAlign = "left";
          g.textBaseline = "bottom";
          g.fillText(`navigation depth ${fmtM(v, need, 2)} (12 ft)`, v.x(r.c0) + 4, yn - 2);
          g.globalAlpha = 1;
        }
        const x = v.x(best.c);
        const y0 = v.y(pool);
        const y1 = v.y(best.top);
        g.beginPath();
        g.moveTo(x, y0);
        g.lineTo(x, y1);
        g.moveTo(x - 5, y0);
        g.lineTo(x + 5, y0);
        g.moveTo(x - 5, y1);
        g.lineTo(x + 5, y1);
        g.stroke();
        for (const [y, dd] of [
          [y0, 1],
          [y1, -1],
        ] as const) {
          g.beginPath();
          g.moveTo(x, y);
          g.lineTo(x - 3, y + 6 * dd);
          g.lineTo(x + 3, y + 6 * dd);
          g.closePath();
          g.fill();
        }
        g.font = `600 11px ${UI_FONT}`;
        g.textAlign = "left";
        g.textBaseline = "middle";
        const text = `channel over the box ${fmtM(v, best.w, 2)} (pool to the ${best.made ? "made-up bed" : "bed"})${short ? `: under ${fmtM(v, need, 2)}` : ""}`;
        g.fillText(text, x + 8, (y0 + y1) / 2);
        d.mark?.({ kind: "channel", id: String(r.name), c: best.c, w: best.w, short, text });
      }
    }
    // the legal band: the shallowest a tube may run (tube colour) and the deepest a box may go (box colour)
    const limit = (arr: ArrayLike<number | null>, colour: string, which: string) => {
      g.save();
      g.strokeStyle = colour;
      g.lineWidth = 1.3;
      g.setLineDash([6, 4]);
      g.globalAlpha = 0.9;
      g.beginPath();
      let on = false;
      const sub = Math.max(s.step_m, ((v.c1 - v.c0) / P.w) * 3);
      for (let c = Math.max(0, v.c0); c <= Math.min(s.length_m, v.c1); c += sub) {
        const i = Math.round(c / s.step_m);
        const z = arr[i];
        if (z == null || !Number.isFinite(z)) {
          on = false;
          continue;
        }
        const x = v.x(c);
        const y = v.y(z);
        if (on) g.lineTo(x, y);
        else g.moveTo(x, y);
        on = true;
      }
      g.stroke();
      g.restore();
      d.mark?.({ kind: "limit", id: which });
    };
    limit(s.limit_tube, typeColour("shield"), "tube");
    limit(s.limit_box, typeColour("cutcover"), "box");
    // unbuildable: hatched red over its structure
    const sub = Math.max(2, ((v.c1 - v.c0) / P.w) * 3);
    for (const b of s.bad) {
      if (b.c1 < v.c0 || b.c0 > v.c1) continue;
      const cs: number[] = [];
      for (let c = Math.max(b.c0, v.c0); c < Math.min(b.c1, v.c1); c += sub) cs.push(c);
      cs.push(Math.min(b.c1, v.c1));
      const zs = cs.map((c) => rail(c));
      if (zs.some((z) => z === null)) continue;
      g.save();
      g.beginPath();
      cs.forEach((c, j) => {
        const y = v.y((zs[j] as number) + 5.5);
        if (j) g.lineTo(v.x(c), y);
        else g.moveTo(v.x(c), y);
      });
      for (let j = cs.length - 1; j >= 0; j--) g.lineTo(v.x(cs[j] as number), v.y((zs[j] as number) - 1.5));
      g.closePath();
      g.fillStyle = WARN;
      g.globalAlpha = 0.16;
      g.fill();
      g.clip();
      g.globalAlpha = 0.85;
      g.strokeStyle = WARN;
      g.lineWidth = 1.2;
      g.beginPath();
      const xa = v.x(cs[0] as number) - 200;
      const xb = v.x(cs[cs.length - 1] as number);
      for (let x = xa; x < xb + 200; x += 7) {
        g.moveTo(x, P.y + P.h);
        g.lineTo(x + 200, P.y);
      }
      g.stroke();
      g.restore();
      d.mark?.({ kind: "unbuildable", id: b.why, c0: b.c0, c1: b.c1, worst: b.worst });
    }
    // viaducts: the deck and girders (or a through truss) by span, and the piers to the ground or river bed
    const ecol = typeColour("elevated");
    for (const sp of s.spans) {
      if (sp.c1 < v.c0 || sp.c0 > v.c1) continue;
      const cs: number[] = [];
      for (let c = sp.c0; c < sp.c1; c += sub) cs.push(c);
      cs.push(sp.c1);
      const zs = cs.map((c) => rail(c));
      if (zs.some((z) => z === null)) continue;
      g.fillStyle = ecol;
      g.globalAlpha = show === "box" ? 0.28 : 0.18;
      g.beginPath();
      cs.forEach((c, j) => {
        const y = v.y((zs[j] as number) + 0.3);
        if (j) g.lineTo(v.x(c), y);
        else g.moveTo(v.x(c), y);
      });
      for (let j = cs.length - 1; j >= 0; j--) g.lineTo(v.x(cs[j] as number), v.y((zs[j] as number) - sp.below));
      g.closePath();
      g.fill();
      g.globalAlpha = 0.85;
      g.strokeStyle = ecol;
      g.lineWidth = 1.25;
      g.stroke();
      if (sp.truss) {
        const top = (c: number) => v.y((rail(c) ?? 0) + sp.above);
        const bot = (c: number) => v.y(rail(c) ?? 0);
        const n = Math.max(2, Math.round(sp.L / Math.max(6, sp.above)));
        g.globalAlpha = 0.75;
        g.beginPath();
        g.moveTo(v.x(sp.c0), bot(sp.c0));
        g.lineTo(v.x(sp.c0 + sp.L / n), top(sp.c0 + sp.L / n));
        g.lineTo(v.x(sp.c1 - sp.L / n), top(sp.c1 - sp.L / n));
        g.lineTo(v.x(sp.c1), bot(sp.c1));
        for (let i = 1; i < n; i++) {
          const c = sp.c0 + (sp.L * i) / n;
          const cn = sp.c0 + (sp.L * (i + 1)) / n;
          g.moveTo(v.x(c), top(c));
          g.lineTo(v.x(c), bot(c));
          if (i + 1 < n) {
            g.moveTo(v.x(c), top(c));
            g.lineTo(v.x(cn), bot(cn));
          }
        }
        g.stroke();
      }
      g.globalAlpha = 1;
      d.mark?.({ kind: "span", id: "", c0: sp.c0, c1: sp.c1, truss: sp.truss });
    }
    const pw = Math.max(2, Math.min(8, 1.6 / ((v.c1 - v.c0) / P.w)));
    g.fillStyle = ecol;
    g.globalAlpha = 0.55;
    const seen = new Set<number>();
    const fin = s.ground.finished;
    for (const sp of s.spans)
      for (const c of [sp.c0, sp.c1]) {
        if (c < v.c0 || c > v.c1 || seen.has(c)) continue;
        seen.add(c);
        const river = s.rivers.find((r) => c >= r.c0 && c <= r.c1);
        const g0 = sampleAt(fin, s.step_m, c);
        const gz = river
          ? g0 !== null && pool !== undefined && g0 < pool
            ? g0
            : (sampleAt(bed, s.step_m, c) ?? g0)
          : g0;
        const z = rail(c);
        if (gz === null || z === null) continue;
        const below = Math.max(...s.spans.filter((q) => q.c0 === c || q.c1 === c).map((q) => q.below));
        const zt = z - below;
        if (zt <= gz) continue;
        g.fillRect(v.x(c) - pw / 2, v.y(zt), pw, v.y(gz) - v.y(zt));
      }
    g.restore();
  },
};

/** The streets the line runs under (dotted; solid where built over the subway) and the roads it crosses (2577-2600). */
export const roadsBand: BandDef = {
  id: "roads",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const ssi = d.solveInput;
    if (!ssi) return;
    const fin = d.solved?.ground.finished;
    const step = d.solved?.step_m ?? ssi.step;
    const gr = d.input?.ground;
    const groundAt = (c: number) => sampleAt(fin, step, c) ?? (gr ? valueAt(gr.z_m, gr.step_m, c) : null);
    const subway = (name: string) =>
      (ssi.structure?.subway_streets ?? []).some((k) => name.toLowerCase().includes(k.toLowerCase()));
    const P = v.plot;
    g.save();
    clipPlot(g, v);
    g.font = `600 10px ${UI_FONT}`;
    g.textBaseline = "bottom";
    const sub = Math.max(2, ((v.c1 - v.c0) / P.w) * 3);
    for (const r of ssi.context.streets) {
      if (r[1] < v.c0 || r[0] > v.c1) continue;
      const a = Math.max(r[0], v.c0);
      const b = Math.min(r[1], v.c1);
      const over = subway(r[3]);
      const col = ROAD_COLOURS[r[4]] ?? (ROAD_COLOURS.minor as string);
      g.strokeStyle = col;
      g.lineWidth = over ? 2 : 1.2;
      g.setLineDash(over ? [] : [2, 3]);
      g.globalAlpha = 0.9;
      g.beginPath();
      let pen = false;
      for (let c = a; c <= b + 1e-9; c += sub) {
        const z = groundAt(c);
        if (z === null) {
          pen = false;
          continue;
        }
        const x = v.x(c);
        const y = v.y(z) - 3;
        if (pen) g.lineTo(x, y);
        else g.moveTo(x, y);
        pen = true;
      }
      g.stroke();
      g.setLineDash([]);
      g.globalAlpha = 1;
      if (v.x(b) - v.x(a) > 90) {
        const gm = groundAt((a + b) / 2);
        if (gm !== null) {
          const text = `under ${r[3]}${over ? " (built over the subway)" : ""}`;
          const w = g.measureText(text).width;
          const xm = (v.x(a) + v.x(b)) / 2;
          const box = { x0: xm - w / 2, y0: v.y(gm) - 17, x1: xm + w / 2, y1: v.y(gm) - 5 };
          if (placer.free(box)) {
            placer.take(box);
            g.fillStyle = col;
            g.textAlign = "center";
            g.fillText(text, xm, v.y(gm) - 5);
          }
        }
      }
    }
    for (const r of ssi.context.roads) {
      if (r[2] < v.c0 || r[1] > v.c1) continue;
      const z = groundAt(r[0]);
      if (z === null) continue;
      const x0 = v.x(Math.max(r[1], v.c0));
      const x1 = v.x(Math.min(r[2], v.c1));
      const y = v.y(z);
      const col = ROAD_COLOURS[r[5]] ?? (ROAD_COLOURS.minor as string);
      g.fillStyle = col;
      g.fillRect(x0, y - 2.5, Math.max(2, x1 - x0), 4);
      let shown = false;
      if (r[5] !== "minor" || x1 - x0 > 24) {
        const w = g.measureText(r[4]).width;
        const xm = (x0 + x1) / 2;
        const box = { x0: xm - w / 2, y0: y - 17, x1: xm + w / 2, y1: y - 5 };
        if (placer.free(box)) {
          placer.take(box);
          g.textAlign = "center";
          g.fillText(r[4], xm, y - 5);
          shown = true;
        }
      }
      d.mark?.({ kind: "road", id: r[4], c: r[0], cls: r[5], drawn: shown });
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

/** Grade plus curve allowance over the limit: dashed under the rail, "+15.7‰ with curve" above it (2634-2648). */
export const curveGradeBand: BandDef = {
  id: "curve-grade",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const list = d.solved?.curve_grade ?? [];
    const rail = railOf(d);
    if (!list.length || !d.rail) return;
    const P = v.plot;
    g.save();
    clipPlot(g, v);
    g.lineWidth = 2;
    g.font = `500 11px ${NUM_FONT}`;
    for (const r of list) {
      const xa = v.x(r.c0 - 5);
      const xb = v.x(r.c1 + 5);
      if (xb < P.x || xa > P.x + P.w) continue;
      const col = r.sustained ? WARN : CAUTION;
      g.strokeStyle = col;
      g.setLineDash([5, 4]);
      g.beginPath();
      let pen = false;
      for (let x = Math.max(xa, P.x); x <= Math.min(xb, P.x + P.w); x += 3) {
        const z = rail(v.c(x));
        if (z === null) continue;
        if (pen) g.lineTo(x, v.y(z) + 7);
        else g.moveTo(x, v.y(z) + 7);
        pen = true;
      }
      g.stroke();
      g.setLineDash([]);
      const xm = (Math.max(xa, P.x) + Math.min(xb, P.x + P.w)) / 2;
      const text = `${fmtG(r.worst)} with curve`;
      const w = g.measureText(text).width + 8;
      const ys = [xm - w / 2, xm, xm + w / 2].map((x) => rail(v.c(x))).filter((z): z is number => z !== null);
      if (!ys.length) continue;
      const ym = Math.min(...ys.map((z) => v.y(z))) - 26;
      const box = { x0: xm - w / 2, y0: ym - 14, x1: xm + w / 2, y1: ym };
      if (placer.free(box)) {
        placer.take(box);
        g.globalAlpha = 0.85;
        g.fillStyle = PAPER;
        g.fillRect(box.x0, box.y0, w, 14);
        g.globalAlpha = 1;
        g.fillStyle = col;
        g.textAlign = "center";
        g.textBaseline = "bottom";
        g.fillText(text, xm, ym);
      }
      d.mark?.({ kind: "curve-grade", id: "", c0: r.c0, c1: r.c1, worst: r.worst, sustained: r.sustained });
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

/** The drawn ground's points as last drawn (CSS pixels), for the Ground tool's hit test. */
let lastGround: { x: number; y: number; l: number; k: number; c: number; z: number }[] = [];
let groundTool = false;

/** Ben's drawn ground (its lines and points, and in Ground its grades) and the shafts (2702-2716). The lines come
 * from the draft as it is now, so a point dragged in Ground moves at once; the solve's lines without a draft. */
export const drawnGroundBand: BandDef = {
  id: "drawn-ground",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    lastGround = [];
    groundTool = d.tool === "ground";
    const s = d.solved;
    const lines = d.draft ? groundLines(d.draft as ProfileData).map((x) => x.pts) : (s?.ground.lines ?? []);
    const rail = railOf(d);
    const sel = d.selected?.kind === "gp" ? { l: Number(d.selected.id), k: d.selected.index } : null;
    g.save();
    clipPlot(g, v);
    lines.forEach((L, l) => {
      g.strokeStyle = EARTH;
      g.lineWidth = groundTool ? 2 : 1.2;
      g.beginPath();
      L.forEach((p, k) => {
        if (k) g.lineTo(v.x(p.c), v.y(p.z));
        else g.moveTo(v.x(p.c), v.y(p.z));
      });
      g.stroke();
      L.forEach((p, k) => {
        const x = v.x(p.c);
        const y = v.y(p.z);
        lastGround.push({ x, y, l, k, c: p.c, z: p.z });
        if (p.c < v.c0 || p.c > v.c1) return;
        const on = !!sel && sel.l === l && sel.k === k;
        const r = on ? 5 : groundTool ? 4 : 3;
        g.beginPath();
        g.rect(x - r, y - r, 2 * r, 2 * r);
        if (on || k === 0 || k === L.length - 1) {
          g.fillStyle = EARTH;
          g.fill();
        }
        g.lineWidth = 1.5;
        g.strokeStyle = EARTH;
        g.stroke();
        d.mark?.({ kind: "ground-point", id: "", l, k, c: p.c, z: p.z, x, y, selected: on });
        // in Ground, the grade of each piece over it where there is room
        const q = L[k - 1];
        if (groundTool && q) {
          const xa = v.x(q.c);
          if (x - xa > 56 && p.c - q.c > 1e-6) {
            g.font = `600 10px ${UI_FONT}`;
            g.textAlign = "center";
            g.textBaseline = "bottom";
            g.fillStyle = EARTH;
            g.fillText(fmtG(((p.z - q.z) / (p.c - q.c)) * 1000), (xa + x) / 2, Math.min(v.y(q.z), y) - 6);
          }
        }
      });
    });
    const shafts =
      d.draft && Array.isArray(d.draft.shafts) ? (d.draft.shafts as unknown[]).map(Number) : (s?.shafts ?? []);
    for (const c of shafts) {
      if (!Number.isFinite(c) || c < v.c0 || c > v.c1) continue;
      const z = rail(c);
      if (z === null) continue;
      const x = v.x(c);
      const y = v.y(z);
      g.strokeStyle = MUTED;
      g.lineWidth = 2;
      g.beginPath();
      g.moveTo(x, y - 14);
      g.lineTo(x, y + 14);
      g.moveTo(x - 5, y - 14);
      g.lineTo(x + 5, y - 14);
      g.stroke();
      g.font = `600 10px ${UI_FONT}`;
      g.textAlign = "center";
      g.textBaseline = "bottom";
      g.fillStyle = MUTED;
      g.fillText("shaft", x, y - 16);
      d.mark?.({ kind: "shaft", id: "", c });
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
  // only in Ground: a point within 8 px (hitTest 3409), the last drawn first
  hit(x, y) {
    if (!groundTool) return null;
    for (let i = lastGround.length - 1; i >= 0; i--) {
      const q = lastGround[i] as (typeof lastGround)[number];
      if (Math.hypot(q.x - x, q.y - y) <= 8)
        return { band: "drawn-ground", kind: "gp", index: q.k, id: String(q.l), c: q.c, z: q.z };
    }
    return null;
  },
};

/** A paint being dragged: the stretch in the brush's colour over the plot's height (2720-2723). */
export const paintPreviewBand: BandDef = {
  id: "paint-preview",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const p = d.paintPreview;
    if (!p) return;
    const a = Math.min(p.c0, p.c1);
    const b = Math.max(p.c0, p.c1);
    const P = v.plot;
    g.save();
    clipPlot(g, v);
    g.fillStyle = p.colour;
    g.globalAlpha = 0.18;
    g.fillRect(v.x(a), P.y, Math.max(1, v.x(b) - v.x(a)), P.h);
    g.restore();
    d.mark?.({ kind: "paint-preview", id: "", c0: a, c1: b });
  },
};

let lastIssues: { x: number; y: number; i: number; c: number; text: string }[] = [];

/** The words of the issue marker under a point, as last drawn (the sheet's tooltip). */
export function issueAt(x: number, y: number): string | null {
  const hits = lastIssues.filter((q) => Math.abs(x - q.x) <= 5 && Math.abs(y - q.y) <= 6);
  return hits.length ? hits.map((q) => q.text).join("\n") : null;
}

/** Every finding of the solve as a triangle along the bottom of the plot, in its severity's colour (2729-2733). */
export const issuesBand: BandDef = {
  id: "issues",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    lastIssues = [];
    const flags = d.solved?.flags ?? [];
    if (!flags.length) return;
    const P = v.plot;
    g.save();
    clipPlot(g, v);
    const rank = { info: 0, warn: 1, error: 2 } as const;
    // the worst on top
    const order = flags
      .map((f, i) => ({ f, i }))
      .filter(({ f }) => markerShown(f) && f.c >= v.c0 && f.c <= v.c1)
      .sort((a, b) => rank[a.f.sev] - rank[b.f.sev]);
    for (const { f, i } of order) {
      const px = v.x(f.c);
      g.fillStyle = f.sev === "error" ? WARN : f.sev === "warn" ? CAUTION : MUTED;
      g.beginPath();
      g.moveTo(px, P.y + P.h - 9);
      g.lineTo(px - 4, P.y + P.h - 1);
      g.lineTo(px + 4, P.y + P.h - 1);
      g.closePath();
      g.fill();
      const text = flagWords(f, (m, digits = 1) => fmtM(v, m, digits));
      lastIssues.push({ x: px, y: P.y + P.h - 5, i, c: f.c, text });
      d.mark?.({ kind: "issue", id: f.kind, c: f.c, sev: f.sev, rule: f.rule, page: f.page, x: px });
      d.report?.({ kind: "issue", text, c: f.c, x: px, y: P.y + P.h - 5, drawn: true });
    }
    g.restore();
  },
  hit(x, y) {
    for (const q of lastIssues)
      if (Math.abs(x - q.x) <= 5 && Math.abs(y - q.y) <= 6)
        return { band: "issues", kind: "issue", index: q.i, c: q.c };
    return null;
  },
};

/** A tick on the plot's top edge at each crossing, with the other line's tag ("L3", "E trunk") where there is room
 * (2823-2832); a station's own interchange tags (the platform band) keep their place. */
export const crossingTicksBand: BandDef = {
  id: "crossing-ticks",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const xs = d.solveInput?.crossings ?? [];
    if (!xs.length) return;
    const P = v.plot;
    g.save();
    clipPlot(g, v);
    g.font = `500 10px ${NUM_FONT}`;
    g.textAlign = "center";
    g.textBaseline = "top";
    let lastTag = Number.NEGATIVE_INFINITY;
    // a station tagged with its interchanges (the platform band) stands for the crossings at it
    const tagged = (d.facts ?? []).filter((f) => !f.deleted && (f.interchanges ?? []).length > 0);
    const atTagged = (c: number) => tagged.some((f) => Math.abs(c - f.c_m) <= f.half_m + 20);
    for (const x of [...xs].sort((a, b) => a.c - b.c)) {
      if (x.c < v.c0 || x.c > v.c1 || atTagged(x.c)) continue;
      const px = v.x(x.c);
      const tag = crossingTag(x.with);
      g.fillStyle = x.kind.startsWith("rer") ? MUTED : INK;
      g.beginPath();
      g.moveTo(px - 4, P.y + 1);
      g.lineTo(px + 4, P.y + 1);
      g.lineTo(px, P.y + 6);
      g.fill();
      const w = g.measureText(tag).width;
      const box = { x0: px - w / 2 - 2, y0: P.y + 7, x1: px + w / 2 + 2, y1: P.y + 19 };
      const shown = px - w / 2 > lastTag + 4 && placer.free(box, 0);
      if (shown) {
        g.globalAlpha = 0.85;
        g.fillStyle = PAPER;
        g.fillRect(box.x0, box.y0, box.x1 - box.x0, 12);
        g.globalAlpha = 1;
        g.fillStyle = x.kind.startsWith("rer") ? MUTED : INK;
        g.fillText(tag, px, P.y + 8);
        lastTag = px + w / 2;
      }
      d.mark?.({ kind: "xtick", id: x.wid, c: x.c, text: tag, drawn: shown });
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

// ----------------------------------------------------------------------------------------------------- strips

/** The structure band along the whole line (2777-2792): each run of one type in its colour, named where it fits;
 * the unbuildable stretches and the paints that do not fit hatched red over it; Ben's paints marked under it. */
export const structureStripBand: BandDef = {
  id: "structure-strip",
  height: 18,
  axis: "strip",
  draw(g, v, d) {
    const s = d.solved;
    if (!s) {
      stationStripBand.draw(g, v, d);
      return;
    }
    const P = v.plot;
    const top = v.top + 1;
    const H = 14;
    g.fillStyle = "#23262e";
    g.fillRect(P.x, top, P.w, H);
    g.save();
    g.beginPath();
    g.rect(P.x, top, P.w, H + 3);
    g.clip();
    g.font = `600 10px ${UI_FONT}`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    for (const [t, c0, c1] of s.type_runs) {
      if (c1 < v.c0 || c0 > v.c1) continue;
      const xa = Math.max(P.x, v.x(c0));
      const xb = Math.min(P.x + P.w, v.x(c1));
      g.fillStyle = typeColour(t);
      g.fillRect(xa, top, Math.max(1, xb - xa), H);
      const label = (TYPES[t]?.label ?? t).toUpperCase();
      if (xb - xa > 70 && g.measureText(label).width + 8 < xb - xa) {
        g.fillStyle = PAPER;
        g.fillText(label, (xa + xb) / 2, top + H / 2 + 0.5);
      }
      d.mark?.({ kind: "band", id: t, c0, c1 });
    }
    for (const b of [...s.bad, ...s.misfits]) {
      const xa = Math.max(P.x, v.x(b.c0));
      const xb = Math.min(P.x + P.w, v.x(b.c1));
      if (xb <= xa) continue;
      g.save();
      g.beginPath();
      g.rect(xa, top, Math.max(2, xb - xa), H);
      g.clip();
      g.fillStyle = WARN;
      g.globalAlpha = 0.55;
      g.fillRect(xa, top, Math.max(2, xb - xa), H);
      g.globalAlpha = 1;
      g.strokeStyle = "#fff";
      g.lineWidth = 1;
      g.beginPath();
      for (let x = xa - H; x < xb; x += 6) {
        g.moveTo(x, top + H);
        g.lineTo(x + H, top);
      }
      g.stroke();
      g.restore();
      d.mark?.({ kind: "band-hatch", id: b.why, c0: b.c0, c1: b.c1 });
    }
    // each station's type as station.facts@1 gives it, for the tests and the readers (the strip it stood for)
    for (const f of d.facts ?? []) {
      if (f.deleted || !f.type) continue;
      const x0 = v.x(f.c_m - f.half_m);
      const x1 = Math.max(x0 + 2, v.x(f.c_m + f.half_m));
      d.mark?.({ kind: "strip", id: f.platform_id, type: f.type, x0, x1, solved: runAt(s.type_runs, f.c_m)?.[0] });
    }
    // Ben's paints, marked under the band
    g.fillStyle = INK;
    for (const o of d.solveInput?.doc?.ovr ?? []) {
      const xa = v.x(o[0]);
      const xb = v.x(o[1]);
      if (xb < P.x || xa > P.x + P.w) continue;
      g.fillRect(Math.max(xa, P.x), top + H + 1, Math.min(xb, P.x + P.w) - Math.max(xa, P.x), 2);
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

/** The Chronology band (2793-2803): each segment's opening year and phase, in the phase's colour, "not set" faint. */
export const chronologyStripBand: BandDef = {
  id: "chronology-strip",
  height: 17,
  axis: "strip",
  draw(g, v, d) {
    const ssi = d.solveInput;
    const segs = chronologyOf(ssi);
    if (!segs.length) return;
    const P = v.plot;
    const top = v.top + 2;
    const H = 13;
    g.save();
    g.beginPath();
    g.rect(P.x, top, P.w, H);
    g.clip();
    g.font = `600 10px ${UI_FONT}`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    for (const sg of segs) {
      const xa = Math.max(P.x, v.x(sg.c0));
      const xb = Math.min(P.x + P.w, v.x(sg.c1));
      if (xb <= xa) continue;
      g.fillStyle = sg.phase ? (PHASE_COLOURS[sg.phase] ?? MUTED) : "#2a2e37";
      g.globalAlpha = sg.set ? 0.9 : 0.35;
      g.fillRect(xa + 0.5, top, xb - xa - 1, H);
      g.globalAlpha = 1;
      const label = sg.set
        ? `${sg.year ?? ""}${sg.year != null && sg.phase ? " · " : ""}${sg.phase ? (sg.phase === "later" ? "later" : `P${sg.phase}`) : ""}`
        : "not set";
      if (xb - xa > g.measureText(label).width + 8) {
        g.fillStyle = sg.set ? "#fff" : MUTED;
        g.fillText(label, (xa + xb) / 2, top + H / 2 + 0.5);
      }
      d.mark?.({ kind: "chronology", id: sg.key, c0: sg.c0, c1: sg.c1, year: sg.year, phase: sg.phase, label });
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

/** chrSegments (1077) from the solve input: the segments between the route's stations at their drawn points. */
export function chronologyOf(
  ssi: BandData["solveInput"],
): { key: string; c0: number; c1: number; year: number | null; phase: string | null; set: boolean }[] {
  const t = ssi?.chronologyTable;
  if (!ssi || !t) return [];
  const st = [...ssi.platforms].sort((a, b) => a.point_c - b.point_c || a.order - b.order);
  const ofYear = (y: number | null) => {
    if (y == null) return null;
    for (const [a, b, p] of t.phase_years) if (y >= a && y <= b) return p;
    return null;
  };
  const out = [];
  for (let i = 0; i + 1 < st.length; i++) {
    const a = st[i] as (typeof st)[number];
    const b = st[i + 1] as (typeof st)[number];
    const [x, y] = [a.name, b.name].sort();
    const key = t.sys === "metro" ? `metro|${ssi.route}|${x}|${y}` : `${t.sys}|${x}|${y}`;
    const e = t.segments[key] ?? {};
    const yr = e.year == null || e.year === "" ? null : Number(e.year);
    const phase = (e.phase as string | null | undefined) || ofYear(yr);
    out.push({
      key,
      c0: i ? a.point_c : 0,
      c1: i + 2 < st.length ? b.point_c : ssi.length,
      year: yr,
      phase,
      set: !!(e.phase || yr != null),
    });
  }
  return out;
}

let overviewMap: { x0: number; w: number; L: number; top: number; h: number } | null = null;

/** The whole line, small (drawOverview 2856): ground, rivers, the rail, the stations, and the view as a box. A press
 * there moves the view to that chainage. */
export const overviewBand: BandDef = {
  id: "overview",
  height: 40,
  axis: "strip",
  draw(g, v, d) {
    const inp = d.input;
    overviewMap = null;
    if (!inp) return;
    const P = v.plot;
    const top = v.top + 4;
    const H = 34;
    const L = inp.length_m;
    g.fillStyle = PAPER;
    g.fillRect(P.x, top, P.w, H);
    const X = (c: number) => P.x + (c / L) * P.w;
    const gr = inp.ground;
    let lo = Number.POSITIVE_INFINITY;
    let hi = Number.NEGATIVE_INFINITY;
    const stride = gr ? Math.max(1, Math.floor(gr.z_m.length / P.w)) : 1;
    if (gr)
      for (let i = 0; i < gr.z_m.length; i += stride) {
        const z = gr.z_m[i];
        if (z !== undefined && Number.isFinite(z)) {
          lo = Math.min(lo, z);
          hi = Math.max(hi, z);
        }
      }
    const rail = d.rail;
    if (rail)
      for (let i = 0; i < rail.rail_m.length; i += stride) {
        const z = rail.rail_m[i];
        if (z !== undefined && Number.isFinite(z)) {
          lo = Math.min(lo, z);
          hi = Math.max(hi, z);
        }
      }
    if (!Number.isFinite(lo)) return;
    const Y = (z: number) => top + 3 + ((hi - z) / (hi - lo || 1)) * (H - 6);
    g.save();
    g.beginPath();
    g.rect(P.x, top, P.w, H);
    g.clip();
    if (gr) {
      g.fillStyle = "rgba(179, 156, 114, 0.25)";
      g.beginPath();
      g.moveTo(X(0), top + H);
      for (let i = 0; i < gr.z_m.length; i += stride) {
        const z = gr.z_m[i];
        if (z !== undefined && Number.isFinite(z)) g.lineTo(X(i * gr.step_m), Y(z));
      }
      g.lineTo(X(L), top + H);
      g.closePath();
      g.fill();
    }
    for (const r of d.solveInput?.rivers ?? []) {
      g.fillStyle = WATER_FILL;
      g.fillRect(X(r.c0), top, Math.max(2, X(r.c1) - X(r.c0)), H);
    }
    if (rail) {
      g.strokeStyle = INK;
      g.lineWidth = 1.5;
      g.beginPath();
      for (let i = 0; i < rail.rail_m.length; i += stride) {
        const z = rail.rail_m[i];
        if (z === undefined || !Number.isFinite(z)) continue;
        if (i) g.lineTo(X(i * rail.step_m), Y(z));
        else g.moveTo(X(i * rail.step_m), Y(z));
      }
      g.stroke();
    }
    g.fillStyle = INK;
    for (const s of inp.stations) g.fillRect(X(s.c_m) - 0.5, top + H - 6, 1, 6);
    const xa = X(Math.max(0, v.c0));
    const xb = X(Math.min(L, v.c1));
    g.fillStyle = "#2fb8a8";
    g.globalAlpha = 0.14;
    g.fillRect(xa, top, Math.max(3, xb - xa), H);
    g.globalAlpha = 1;
    g.strokeStyle = "#2fb8a8";
    g.lineWidth = 1.5;
    g.strokeRect(xa + 0.5, top + 0.75, Math.max(3, xb - xa) - 1, H - 1.5);
    g.restore();
    overviewMap = { x0: P.x, w: P.w, L, top, h: H };
    d.mark?.({ kind: "overview", id: "", x0: xa, x1: xb });
  },
  hit(x, y): Handle | null {
    const m = overviewMap;
    if (!m || y < m.top || y > m.top + m.h || x < m.x0 || x > m.x0 + m.w) return null;
    return { band: "overview", kind: "overview", index: 0, c: ((x - m.x0) / m.w) * m.L };
  },
};

/** The rail coloured by the solve's structure (2602-2611), 3 px; in Show: Box the tunnels' rail is left to the
 * outline. Null when there is no solve: the plain rail stands. */
export function drawTypedRail(g: CanvasRenderingContext2D, v: SheetView, d: BandData): boolean {
  const s = d.solved;
  if (!s || !d.rail) return false;
  const pts = railColumns(v, d, s);
  g.lineWidth = 3;
  g.lineJoin = "round";
  let k0 = 0;
  for (let k = 1; k <= pts.length; k++) {
    const p0 = pts[k0] as Column | undefined;
    if (!p0) break;
    if (k === pts.length || (pts[k] as Column).t !== p0.t) {
      if (!(d.show === "box" && TUNNEL.has(p0.t))) {
        g.strokeStyle = typeColour(p0.t);
        g.beginPath();
        for (let j = k0; j < Math.min(k + 1, pts.length); j++) {
          const p = pts[j] as Column;
          if (j === k0) g.moveTo(p.x, v.y(p.z));
          else g.lineTo(p.x, v.y(p.z));
        }
        g.stroke();
      }
      k0 = k;
    }
  }
  return true;
}

/** The over-grade colour of a grade chord: red where sustained, amber where local, null where within its limit. */
export function overColour(d: BandData, c0: number, c1: number): string | null {
  const o = d.solved?.over.find((q) => Math.abs(q.c0 - c0) < 0.01 && Math.abs(q.c1 - c1) < 0.01);
  if (!o) return null;
  return o.sev === "error" ? WARN : CAUTION;
}
