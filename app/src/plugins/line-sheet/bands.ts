// The line sheet's first bands (section 8): ground and rail, platform and PVI marks, and the chainage ruler with
// the cursor readout. Profile bands share the sheet's chainage and level axes; strip bands get their own rows below.

import type { BandData, BandDef, Handle, SheetView } from "../../core/plugin.ts";
import { formatChainage } from "../../core/units.ts";
import {
  chainageTicks,
  curveTicks,
  depthTag,
  fmtCh,
  fmtG,
  fmtVE,
  fmtZ,
  gradeChords,
  gradeLabels,
  levelTicks,
  nameLabels,
  SEV_COLOURS,
  slideText,
  stationText,
  streetText,
  thinLabels,
  typeColour,
  typeLabel,
  unsetTags,
  valueAt,
  verticalExaggeration,
  worstSeverity,
} from "./drawing.ts";
import {
  chronologyStripBand,
  contextBand,
  crossingsBand,
  crossingTicksBand,
  curveGradeBand,
  drawnGroundBand,
  drawTypedRail,
  groundWorksBand,
  issuesBand,
  locksBand,
  outlinesBand,
  overColour,
  overGradeBand,
  overviewBand,
  paintPreviewBand,
  type ReadoutRow,
  readoutRows,
  reserveLabel,
  roadsBand,
  sampleAt,
  structureStripBand,
  waterBand,
} from "./solved.ts";
import { stationAccessBand, stationFlagsBand, stationStructureBand } from "./stations.ts";

export const COLORS = {
  ground: "#8a6d3b",
  earth: "rgba(138, 109, 59, 0.16)",
  rail: "#5aa9e6",
  server: "#7fd962",
  ink: "#d8dbe2",
  selected: "#e6b450",
  /** Bend points in the old page's teal (its dark theme's accent), apart from the stations' ink and the flags' red. */
  pvi: "#2fb8a8",
  /** The station bars: bold, in the brightest ink, on a dark halo so a bar reads over the rail, ground and box. */
  bar: "#f2f5f6",
  grid: "#2a2e37",
  gridMajor: "#4a505c",
  frame: "#3a3f4a",
  text: "#8b919e",
  paper: "#16181d",
  cursor: "#d8dbe2",
};

const UI_FONT = "system-ui, sans-serif";
const NUM_FONT = "ui-monospace, SFMono-Regular, Menlo, monospace";

/** Clip drawing to the plot. */
function clipPlot(g: CanvasRenderingContext2D, v: SheetView): void {
  g.beginPath();
  g.rect(v.plot.x, v.plot.y, v.plot.w, v.plot.h);
  g.clip();
}

/** Draw y = f(i) for an array on a grid from chainage 0, only the part in view, decimated to the pixel. */
function polyline(g: CanvasRenderingContext2D, v: SheetView, ys: ArrayLike<number>, step: number): void {
  const n = ys.length;
  if (!n) return;
  const i0 = Math.max(0, Math.floor(v.c0 / step) - 1);
  const i1 = Math.min(n - 1, Math.ceil(v.c1 / step) + 1);
  const per = Math.max(1, Math.floor((i1 - i0) / (v.width * 2)));
  g.beginPath();
  let pen = false;
  for (let i = i0; i <= i1; i += per) {
    const z = ys[i];
    if (z === undefined || !Number.isFinite(z)) {
      pen = false;
      continue;
    }
    const x = v.x(i * step);
    const y = v.y(z);
    if (pen) g.lineTo(x, y);
    else g.moveTo(x, y);
    pen = true;
  }
  g.stroke();
}

interface DrawnPlatform {
  x0: number;
  x1: number;
  y0: number;
  y1: number;
  index: number;
  id: string;
  c: number;
  z: number;
  /** The name label's anchor (top margin) and length along its 45° line, when it was drawn. */
  label: { x: number; y: number; len: number } | null;
}

let lastPvis: { x: number; y: number; index: number; c: number; z: number }[] = [];
let lastPlatforms: DrawnPlatform[] = [];
/** The grade labels' boxes as last drawn (CSS pixels): a removed station's name keeps clear of them. */
let lastGradeBoxes: Box[] = [];

interface Box {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}
const overlaps = (a: Box, b: Box, pad = 1) =>
  a.x0 < b.x1 + pad && b.x0 < a.x1 + pad && a.y0 < b.y1 + pad && b.y0 < a.y1 + pad;

/** The narrowest a bar is drawn (CSS px): at a whole-line view a 120 m platform is 4 or 5 px, too thin to read. */
export const MIN_BAR_PX = 6;

/** Where a station's bar is drawn: its platform at the level, tilted by the grade, at least MIN_BAR_PX wide about
 * its centre. The PVI band reads it too, to keep its circles off the bars. */
export function barGeometry(
  v: SheetView,
  s: { c_m: number; grade_permille: number | null },
  z: number,
  half: number,
): { xa: number; xb: number; ya: number; yb: number } {
  const gp = (s.grade_permille ?? 0) / 1000;
  let xa = v.x(s.c_m - half);
  let xb = v.x(s.c_m + half);
  if (xb - xa < MIN_BAR_PX) {
    const mid = (xa + xb) / 2;
    xa = mid - MIN_BAR_PX / 2;
    xb = mid + MIN_BAR_PX / 2;
  }
  return { xa, xb, ya: v.y(z - gp * half), yb: v.y(z + gp * half) };
}

/** How far apart station names are kept (px along the axis): the old page's 18, and its 15 on a narrow plot (its
 * canvas under 560 px, 2302); 15 also on a plot wide enough to show a whole line (900 px and more). */
export const nameGap = (plotW: number): number => (plotW >= 900 || plotW < 500 ? 15 : 18);

/** A line's name as the old page tagged its crossings: "Line 3" is L3, "CVG Express" CVG; an RER route keeps its
 * short name ("E trunk"). */
export function interchangeTag(names: readonly string[]): string {
  return names.map((n) => n.replace(/^CVG Express$/, "CVG").replace(/^Line /, "L")).join(" ");
}

/** The level of each live station as drawn (its own, else ground − default depth when unset, else the rail). */
function drawnLevel(s: { platform_id: string; c_m: number; level_m: number | null }, d: BandData) {
  const f = d.facts?.find((x) => x.platform_id === s.platform_id);
  const unset = !!f && s.level_m === null && f.default_level_m !== null;
  return { z: unset ? (f?.default_level_m as number) : stationLevel(s, d.rail), unset, f };
}

/** The station's rail level: its own, else the solved rail at its centre. */
export function stationLevel(s: { c_m: number; level_m: number | null }, rail: BandData["rail"]): number | null {
  if (s.level_m !== null && Number.isFinite(s.level_m)) return s.level_m;
  return rail ? valueAt(rail.rail_m, rail.step_m, s.c_m) : null;
}

/** The plot's background, the level grid with its labels and title, and the chainage grid lines. */
export const axesBand: BandDef = {
  id: "axes",
  height: 0,
  axis: "profile",
  draw(g, v) {
    const P = v.plot;
    g.fillStyle = COLORS.paper;
    g.fillRect(P.x, P.y, P.w, P.h);
    g.lineWidth = 1;
    g.font = `11px ${NUM_FONT}`;
    g.textAlign = "right";
    g.textBaseline = "middle";
    for (const t of levelTicks(v.z0, v.z1, v.units, P.h < 220 ? 4 : 8)) {
      const y = Math.round(v.y(t.v)) + 0.5;
      if (y < P.y || y > P.y + P.h) continue;
      g.strokeStyle = COLORS.grid;
      g.beginPath();
      g.moveTo(P.x, y);
      g.lineTo(P.x + P.w, y);
      g.stroke();
      g.fillStyle = COLORS.text;
      g.fillText(t.label, P.x - 6, y);
    }
    g.save();
    g.translate(12, P.y + P.h / 2);
    g.rotate(-Math.PI / 2);
    g.textAlign = "center";
    g.font = `11px ${UI_FONT}`;
    g.fillStyle = COLORS.text;
    g.fillText(`Elevation, ${v.units.length} NAVD 88`, 0, 0);
    g.restore();
    for (const t of chainageTicks(v.c0, v.c1, v.units, Math.max(2, Math.floor(P.w / 110)))) {
      const x = Math.round(v.x(t.v)) + 0.5;
      if (x < P.x || x > P.x + P.w) continue;
      g.strokeStyle = COLORS.grid;
      g.beginPath();
      g.moveTo(x, P.y);
      g.lineTo(x, P.y + P.h);
      g.stroke();
    }
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

export const groundBand: BandDef = {
  id: "ground",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const gr = d.input?.ground;
    if (!gr) return;
    g.save();
    clipPlot(g, v);
    // Earth under the ground line, down to the bottom of the plot, as the old sheet shaded it.
    const n = gr.z_m.length;
    const i0 = Math.max(0, Math.floor(v.c0 / gr.step_m) - 1);
    const i1 = Math.min(n - 1, Math.ceil(v.c1 / gr.step_m) + 1);
    const per = Math.max(1, Math.floor((i1 - i0) / (v.width * 2)));
    const bottom = v.plot.y + v.plot.h;
    g.fillStyle = COLORS.earth;
    let run: [number, number][] = [];
    const flush = () => {
      if (run.length > 1) {
        g.beginPath();
        g.moveTo((run[0] as [number, number])[0], bottom);
        for (const [x, y] of run) g.lineTo(x, y);
        g.lineTo((run[run.length - 1] as [number, number])[0], bottom);
        g.closePath();
        g.fill();
      }
      run = [];
    };
    for (let i = i0; i <= i1; i += per) {
      const z = gr.z_m[i];
      if (z === undefined || !Number.isFinite(z)) {
        flush();
        continue;
      }
      run.push([v.x(i * gr.step_m), v.y(z)]);
    }
    flush();
    g.strokeStyle = COLORS.ground;
    g.lineWidth = 1.2;
    polyline(g, v, gr.z_m, gr.step_m);
    g.restore();
  },
};

export const railBand: BandDef = {
  id: "rail",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    g.save();
    clipPlot(g, v);
    if (d.server) {
      g.save();
      g.strokeStyle = COLORS.server;
      g.lineWidth = 3;
      g.globalAlpha = 0.55;
      polyline(g, v, d.server.rail_m, d.server.step_m);
      g.restore();
    }
    // coloured by the whole solve's structure once it has landed (the old page's rail), else the plain rail
    if (d.rail && !drawTypedRail(g, v, d)) {
      g.strokeStyle = COLORS.rail;
      g.lineWidth = 2;
      polyline(g, v, d.rail.rail_m, d.rail.step_m);
    }
    g.restore();
  },
};

/** Grade labels between the design line's vertices: "+13.6‰" on a paper box 8 px above the rail at mid-chord. */
export const gradeBand: BandDef = {
  id: "grades",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    if (!d.dv || !d.rail) return;
    const P = v.plot;
    const rail = d.rail;
    g.save();
    clipPlot(g, v);
    g.font = `500 11px ${NUM_FONT}`;
    g.textAlign = "center";
    g.textBaseline = "bottom";
    lastGradeBoxes = [];
    for (const lab of gradeLabels(gradeChords(d.dv, d.curves ?? []), v.x, P.x, P.x + P.w, P.w < 500 ? 56 : 66)) {
      const z = valueAt(rail.rail_m, rail.step_m, v.c(lab.xm));
      if (z === null) continue;
      const ym = v.y(z) - 8;
      const w = g.measureText(lab.text).width + 8;
      g.globalAlpha = 0.85;
      g.fillStyle = COLORS.paper;
      g.fillRect(lab.xm - w / 2, ym - 14, w, 14);
      g.globalAlpha = 1;
      // red where the grade is over its limit and sustained, amber where it is local (2627-2631)
      g.fillStyle = overColour(d, lab.chord.c0, lab.chord.c1) ?? COLORS.text;
      g.fillText(lab.text, lab.xm, ym);
      const box = { x0: lab.xm - w / 2, y0: ym - 14, x1: lab.xm + w / 2, y1: ym };
      lastGradeBoxes.push(box);
      d.mark?.({ kind: "grade", id: "", text: lab.text, ...box });
      d.report?.({ kind: "grade", text: lab.text, c: v.c(lab.xm), drawn: true });
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

/**
 * The stations as the old sheet drew them, and clearer: a 6 px bar over the platform at its rail level, tilted by its
 * grade, with end ticks, outlined red or amber when the station has an error or a warning; a hollow triangle at the
 * drawn point, always, and when the platform is slid off it a thin line to the centre with "slid −235 m"; the name
 * rotated 45° in the top margin after a square in its type colour, with a dotted leader down to the bar; the rail
 * level and the depth under the bar. A station with no level is a dashed hollow bar at ground − 7.62 m, marked
 * "level not set"; a removed one a faint tick at its drawn point with its name struck through. Names and levels are
 * thinned so none runs into the next; the selected station is always named, in the selection colour.
 */
export const platformBand: BandDef = {
  id: "platforms",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const inp = d.input;
    lastPlatforms = [];
    if (!inp) return;
    const P = v.plot;
    const half = inp.params.platform_m / 2;
    const narrow = P.w < 500;
    const facts = new Map((d.facts ?? []).map((f) => [f.platform_id, f]));
    const items: {
      x: number;
      y: number;
      z: number;
      index: number;
      on: boolean;
      name: string;
      colour: string | null;
      depth: string | null;
      unset: boolean;
    }[] = [];
    inp.stations.forEach((s, index) => {
      const f = facts.get(s.platform_id);
      const { z, unset } = drawnLevel(s, d);
      if (z === null) return;
      const on = d.selected?.kind === "station" && (d.selected.id ?? null) === s.platform_id;
      const name = d.platformName?.(s.platform_id) ?? s.platform_id;
      const visible = s.c_m + half >= v.c0 && s.c_m - half <= v.c1;
      if (!visible) {
        d.report?.({
          kind: "station",
          id: s.platform_id,
          text: stationText(name, s.c_m, z, v.units),
          c: s.c_m,
          z,
          drawn: false,
          selected: on,
        });
        return;
      }
      const gp = (s.grade_permille ?? 0) / 1000;
      const { xa, xb, ya, yb } = barGeometry(v, s, z, half);
      const colour = on ? COLORS.selected : COLORS.bar;
      const sev = f ? worstSeverity(f.flags) : null;
      g.save();
      clipPlot(g, v);
      g.lineCap = "butt";
      // A dark halo under the bar, so it reads over the rail, the ground and its own box (the old page's bold bar).
      g.strokeStyle = COLORS.paper;
      g.lineWidth = 11;
      g.beginPath();
      g.moveTo(xa - 2, ya);
      g.lineTo(xb + 2, yb);
      g.stroke();
      if (sev) {
        // The flag outline: a thin box in the severity colour around the bar, clear of it, so a flagged station
        // still reads as a station (a wide red stroke looked like the bend points' circles).
        g.strokeStyle = SEV_COLOURS[sev];
        g.lineWidth = 1.5;
        g.beginPath();
        g.moveTo(xa - 3.5, ya - 7);
        g.lineTo(xb + 3.5, yb - 7);
        g.lineTo(xb + 3.5, yb + 7);
        g.lineTo(xa - 3.5, ya + 7);
        g.closePath();
        g.stroke();
      }
      g.strokeStyle = colour;
      g.fillStyle = colour;
      if (unset) {
        // Hollow and dashed: the rail here is not Ben's, only where ground − 7.62 m would put it.
        g.lineWidth = 1.2;
        g.setLineDash([4, 3]);
        g.beginPath();
        g.moveTo(xa, ya - 3);
        g.lineTo(xb, yb - 3);
        g.lineTo(xb, yb + 3);
        g.lineTo(xa, ya + 3);
        g.closePath();
        g.stroke();
        g.setLineDash([]);
        // its "level not set" tag follows with the names, thinned so the tags never pile up (unsetTags)
      } else {
        g.lineWidth = 6;
        g.beginPath();
        g.moveTo(xa, ya);
        g.lineTo(xb, yb);
        g.stroke();
      }
      g.fillRect(xa, ya - 7, 1.5, 10);
      g.fillRect(Math.max(xa + 1.5, xb - 1.5), yb - 7, 1.5, 10);
      // The drawn point, always: a hollow triangle on the tilted level; a slid platform hangs off it by a thin line.
      const c0 = d.stopC?.(s.platform_id) ?? f?.point_c_m ?? s.c_m;
      const xp = v.x(c0);
      const yp = v.y(z + gp * (c0 - s.c_m));
      const slide = s.c_m - c0;
      if (Math.abs(slide) > 0.5) {
        const xc = v.x(s.c_m);
        g.strokeStyle = colour;
        g.lineWidth = 1;
        g.globalAlpha = 0.8;
        g.beginPath();
        g.moveTo(xp, yp + 4);
        g.lineTo(xp, yp + 12);
        g.lineTo(xc, yp + 12);
        g.stroke();
        g.globalAlpha = 1;
        g.font = `500 10px ${NUM_FONT}`;
        g.textAlign = "center";
        g.textBaseline = "top";
        g.fillStyle =
          sev === "error" && f?.flags.some((x) => x.kind === "platform_slide_over") ? SEV_COLOURS.error : colour;
        // The note only where the slide line can carry it (or on the selected station): at a whole-line view the
        // notes ran over the next stations.
        const note = slideText(slide, v.units);
        if (on || Math.abs(xc - xp) >= g.measureText(note).width + 4) {
          g.fillText(note, (xp + xc) / 2, yp + 14);
          d.mark?.({ kind: "tag", id: s.platform_id, what: "slide" });
        }
      }
      g.fillStyle = COLORS.paper;
      g.strokeStyle = colour;
      g.beginPath();
      g.moveTo(xp, yp - 3);
      g.lineTo(xp + 4, yp + 3);
      g.lineTo(xp - 4, yp + 3);
      g.closePath();
      g.fill();
      g.lineWidth = 1.2;
      g.stroke();
      g.restore();
      d.mark?.({
        kind: "bar",
        id: s.platform_id,
        c0: s.c_m - half,
        c1: s.c_m + half,
        z0: z - gp * half,
        z1: z + gp * half,
        x0: xa,
        x1: xb,
        y0: ya,
        y1: yb,
        unset,
        sev,
        selected: on,
      });
      d.mark?.({ kind: "point", id: s.platform_id, c: c0, z: z + gp * (c0 - s.c_m), x: xp, y: yp, slide });
      const x = v.x(c0);
      items.push({
        x,
        y: Math.min(ya, yb),
        z,
        index,
        on,
        name,
        colour: f ? typeColour(f.type) : null,
        depth: f && !unset ? depthTag(f.depth_m, v.units) : null,
        unset,
      });
      lastPlatforms.push({ x0: xa, x1: xb, y0: ya, y1: yb, index, id: s.platform_id, c: s.c_m, z, label: null });
    });
    // Removed stations: a faint tick at the drawn point and the name struck through, so Ben sees where one was.
    for (const f of d.facts ?? []) {
      if (!f.deleted || f.point_c_m < v.c0 || f.point_c_m > v.c1) continue;
      const zr = d.rail ? valueAt(d.rail.rail_m, d.rail.step_m, f.point_c_m) : null;
      if (zr === null) continue;
      const x = v.x(f.point_c_m);
      const y = v.y(zr);
      g.save();
      clipPlot(g, v);
      g.globalAlpha = 0.55;
      g.strokeStyle = COLORS.text;
      g.lineWidth = 1.5;
      g.beginPath();
      g.moveTo(x, y - 9);
      g.lineTo(x, y + 9);
      g.stroke();
      g.font = `10px ${UI_FONT}`;
      g.textAlign = "center";
      g.textBaseline = "middle";
      const t = d.platformName?.(f.platform_id) ?? f.name;
      const w = g.measureText(t).width;
      // The struck-through name on a paper box, under the rail where the grade labels are not (they sit over it),
      // else over it, else further off: never on a grade label.
      const box = (cy: number): Box => ({ x0: x - w / 2 - 3, y0: cy - 7, x1: x + w / 2 + 3, y1: cy + 7 });
      const spots = [y + 18, y - 18, y + 34, y - 34, y + 50];
      const cy = spots.find((q) => !lastGradeBoxes.some((b) => overlaps(box(q), b))) ?? (spots[0] as number);
      const bx = box(cy);
      g.globalAlpha = 0.85;
      g.fillStyle = COLORS.paper;
      g.fillRect(bx.x0, bx.y0, bx.x1 - bx.x0, bx.y1 - bx.y0);
      g.globalAlpha = 0.7;
      g.fillStyle = COLORS.text;
      g.fillText(t, x, cy);
      g.beginPath();
      g.moveTo(x - w / 2, cy);
      g.lineTo(x + w / 2, cy);
      g.stroke();
      g.restore();
      d.mark?.({ kind: "removed", id: f.platform_id, c: f.point_c_m, x, y, label: bx });
    }
    // Names: left to right, 18 px apart as on the old page (nameLabels), the line's last station named as well; on a
    // plot wide enough to show a whole line (900 px and more) 15 px, the old page's narrow gap: rotated 45 degrees,
    // neighbours are still 10.6 px apart across the text, clear of a 12 px name's letters.
    const named = nameLabels(
      items.map((it) => ({ x: it.x, selected: it.on })),
      nameGap(P.w),
    );
    // "level not set" over each dashed bar, one per station, left out where it would run into another
    g.font = `600 10px ${UI_FONT}`;
    const unsetW = g.measureText("level not set").width;
    const unsetShown = unsetTags(
      items.map((it, k) => {
        const p = lastPlatforms[k] as DrawnPlatform;
        return it.unset
          ? { x: (p.x0 + p.x1) / 2, y: Math.min(p.y0, p.y1) - 5, w: unsetW, selected: it.on }
          : { x: Number.NaN, y: Number.NaN, w: 0 };
      }),
    );
    g.save();
    clipPlot(g, v);
    g.textAlign = "center";
    g.textBaseline = "bottom";
    for (const k of unsetShown) {
      const it = items[k];
      const p = lastPlatforms[k] as DrawnPlatform;
      const s0 = it ? inp.stations[it.index] : undefined;
      if (!it || !s0) continue;
      g.fillStyle = it.on ? COLORS.selected : COLORS.bar;
      g.fillText("level not set", (p.x0 + p.x1) / 2, Math.min(p.y0, p.y1) - 5);
      d.mark?.({ kind: "unset-tag", id: s0.platform_id });
    }
    g.restore();
    // Levels: a tag under each bar (the level, and the depth under it), kept apart by its own width.
    g.font = `500 10px ${NUM_FONT}`;
    const levelW = g.measureText("00.0 down").width + 6;
    // Only under a bar wide enough to read as a platform (12 px), or the selected one: at a whole-line view the
    // tags ran over the rail and the next stations' bars.
    const roomy = items.map((it, k) => {
      const p = lastPlatforms[k] as DrawnPlatform;
      return it.on || p.x1 - p.x0 >= 12;
    });
    const levelled = thinLabels(
      items.map((it, k) => ({ x: roomy[k] ? it.x : Number.NaN, priority: 0, selected: it.on })),
      levelW,
    );
    g.save();
    g.beginPath();
    g.rect(P.x - 8, 0, P.w + 16, P.y + P.h);
    g.clip();
    g.font = `600 ${narrow ? 11 : 12}px ${UI_FONT}`;
    g.textBaseline = "middle";
    items.forEach((it, k) => {
      const plat = lastPlatforms[k] as DrawnPlatform;
      g.strokeStyle = it.on ? COLORS.selected : COLORS.gridMajor;
      g.lineWidth = 1;
      g.setLineDash([2, 3]);
      g.beginPath();
      g.moveTo(Math.round(it.x) + 0.5, P.y - 4);
      g.lineTo(Math.round(it.x) + 0.5, Math.max(P.y - 4, it.y - 8));
      g.stroke();
      g.setLineDash([]);
      const show = named.has(k);
      if (show) {
        g.save();
        g.translate(it.x, P.y - 6);
        g.rotate(-Math.PI / 4);
        g.textAlign = "left";
        let off = 2;
        if (it.colour) {
          // The type square before the name: the station's structure at a glance.
          g.fillStyle = it.colour;
          g.fillRect(2, -3, 6, 6);
          off = 11;
        }
        g.fillStyle = it.on ? COLORS.selected : COLORS.ink;
        g.fillText(it.name, off, 0);
        const len = g.measureText(it.name).width + off;
        g.restore();
        plat.label = { x: it.x, y: P.y - 6, len };
      }
      const s0 = inp.stations[it.index];
      if (s0) d.mark?.({ kind: "name", id: s0.platform_id, drawn: show, colour: it.colour });
      const showLevel = roomy[k] && levelled.has(k) && it.y + 22 < P.y + P.h && !it.unset;
      if (showLevel) {
        if (s0) d.mark?.({ kind: "tag", id: s0.platform_id, what: "level" });
        g.save();
        g.font = `500 10px ${NUM_FONT}`;
        g.textAlign = "center";
        g.textBaseline = "top";
        const txt = fmtZ(it.z, v.units);
        const ty = Math.max(plat.y0, plat.y1) + 6;
        const lines = it.depth && it.y + 36 < P.y + P.h ? [txt, it.depth] : [txt];
        const w = Math.max(...lines.map((l) => g.measureText(l).width)) + 6;
        g.globalAlpha = 0.85;
        g.fillStyle = COLORS.paper;
        g.fillRect(it.x - w / 2, ty - 1, w, 13 * lines.length);
        g.globalAlpha = 1;
        lines.forEach((l, i) => {
          g.fillStyle = i === 0 ? (it.on ? COLORS.selected : COLORS.ink) : COLORS.text;
          g.fillText(l, it.x, ty + i * 12);
        });
        g.restore();
      }
      const s = inp.stations[it.index];
      if (s)
        d.report?.({
          kind: "station",
          id: s.platform_id,
          text: stationText(it.name, s.c_m, it.z, v.units),
          c: s.c_m,
          z: it.z,
          x: it.x,
          y: it.y,
          drawn: show,
          selected: it.on,
        });
    });
    g.restore();
    // Names left out for room: say so, and how to read them all (the old page left them out without a word).
    if (named.size < items.length) {
      const hint = `${named.size} of ${items.length} names shown: ${P.w < 900 ? "maximise (Shift+F) for more, " : ""}zoom in for all`;
      g.save();
      g.font = `500 11px ${UI_FONT}`;
      g.textAlign = "left";
      g.textBaseline = "bottom";
      const w = g.measureText(hint).width + 10;
      g.globalAlpha = 0.85;
      g.fillStyle = COLORS.paper;
      g.fillRect(P.x + 2, P.y + P.h - 32, w, 16);
      g.globalAlpha = 1;
      g.fillStyle = COLORS.text;
      g.fillText(hint, P.x + 7, P.y + P.h - 18);
      g.restore();
      d.mark?.({ kind: "names-hint", id: "", text: hint, shown: named.size, of: items.length });
      d.report?.({ kind: "hint", text: hint, c: v.c0, drawn: true });
    }
    // Interchanges: under each station's name, a tick on the plot's top edge and the other lines it is one station
    // with ("L3", "L4 L5 A trunk"), as the old page tagged its crossings; kept apart left to right, the selected one
    // always.
    g.save();
    clipPlot(g, v);
    g.font = `500 10px ${NUM_FONT}`;
    g.textAlign = "center";
    g.textBaseline = "top";
    let lastRight = Number.NEGATIVE_INFINITY;
    const tagged = items
      .map((it) => ({ it, s: inp.stations[it.index], f: facts.get(inp.stations[it.index]?.platform_id ?? "") }))
      .filter((q) => q.s && (q.f?.interchanges ?? []).length > 0)
      .sort((a, b) => a.it.x - b.it.x);
    for (const { it, s, f } of tagged) {
      const text = interchangeTag(f?.interchanges ?? []);
      const w = g.measureText(text).width;
      // kept inside the plot: a tag at the line's end would be cut by its edge
      const tx = Math.min(P.x + P.w - w / 2 - 3, Math.max(P.x + w / 2 + 3, it.x));
      const show = it.on || tx - w / 2 > lastRight + 4;
      g.fillStyle = it.on ? COLORS.selected : COLORS.ink;
      g.beginPath();
      g.moveTo(it.x - 4, P.y + 1);
      g.lineTo(it.x + 4, P.y + 1);
      g.lineTo(it.x, P.y + 6);
      g.closePath();
      g.fill();
      if (show) {
        g.globalAlpha = 0.85;
        g.fillStyle = COLORS.paper;
        g.fillRect(tx - w / 2 - 2, P.y + 7, w + 4, 12);
        g.globalAlpha = 1;
        g.fillStyle = it.on ? COLORS.selected : COLORS.ink;
        g.fillText(text, tx, P.y + 8);
        lastRight = Math.max(lastRight, tx + w / 2);
        reserveLabel({ x0: tx - w / 2 - 2, y0: P.y + 7, x1: tx + w / 2 + 2, y1: P.y + 19 });
      }
      d.mark?.({ kind: "xtag", id: s?.platform_id ?? "", text, drawn: show, x: it.x, x0: tx - w / 2, x1: tx + w / 2 });
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
  hit(x, y) {
    for (const p of lastPlatforms) {
      const t = p.x1 > p.x0 ? Math.min(1, Math.max(0, (x - p.x0) / (p.x1 - p.x0))) : 0;
      const yb = p.y0 + (p.y1 - p.y0) * t;
      // The old page's reach: the platform's span, at least ±6 px, plus 3 px; within 9 px of the bar (3407-3413).
      const mid = (p.x0 + p.x1) / 2;
      const reach = Math.max((p.x1 - p.x0) / 2, 6) + 3;
      const onBar = Math.abs(x - mid) <= reach && Math.abs(y - yb) <= 9;
      let onLabel = false;
      if (p.label) {
        // Along the 45° line up and to the right of the anchor, within half a line of text either side.
        const dx = x - p.label.x;
        const dy = p.label.y - y;
        const along = (dx + dy) / Math.SQRT2;
        const across = (dx - dy) / Math.SQRT2;
        onLabel = along >= -4 && along <= p.label.len + 4 && Math.abs(across) <= 9;
      }
      if (onBar || onLabel) return { band: "platforms", kind: "station", index: p.index, id: p.id, c: p.c, z: p.z };
    }
    return null;
  },
};

/** PVI handles, hollow, filled when selected, and the start and end ticks of each vertical curve. */
export const pviBand: BandDef = {
  id: "pvi",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    lastPvis = [];
    g.save();
    clipPlot(g, v);
    if (d.curves && d.rail) {
      g.strokeStyle = COLORS.pvi;
      g.lineWidth = 1.5;
      for (const c of curveTicks(d.curves)) {
        if (c < v.c0 || c > v.c1) continue;
        const z = valueAt(d.rail.rail_m, d.rail.step_m, c);
        if (z === null) continue;
        const x = v.x(c);
        const y = v.y(z);
        g.beginPath();
        g.moveTo(x, y - 6);
        g.lineTo(x, y + 6);
        g.stroke();
      }
    }
    const pvi = d.input?.pvi ?? [];
    // The station bars as the platform band draws them (after this band, over the circles): a circle that would
    // sit on a bar is left out (a whole-line view puts the bend points either side of a platform on it), so a
    // station is never hidden under bend points; it is drawn again as soon as there is room, or when selected.
    const half = (d.input?.params.platform_m ?? 0) / 2;
    const bars: Box[] = [];
    for (const s of d.input?.stations ?? []) {
      if (s.c_m + half < v.c0 || s.c_m - half > v.c1) continue;
      const { z } = drawnLevel(s, d);
      if (z === null) continue;
      const b = barGeometry(v, s, z, half);
      bars.push({ x0: b.xa - 3, x1: b.xb + 3, y0: Math.min(b.ya, b.yb) - 9, y1: Math.max(b.ya, b.yb) + 9 });
    }
    pvi.forEach((p, index) => {
      if (p.c_m < v.c0 || p.c_m > v.c1) return;
      const x = v.x(p.c_m);
      const y = v.y(p.z_m);
      const sel = d.selected?.kind === "pvi" && d.selected.c === p.c_m && d.selected.z === p.z_m;
      const r = sel ? 6 : 4;
      const hidden = !sel && bars.some((b) => overlaps(b, { x0: x - r, x1: x + r, y0: y - r, y1: y + r }, 0));
      d.mark?.({ kind: "pvi", id: "", c: p.c_m, z: p.z_m, x, y, hidden });
      if (hidden) return;
      g.strokeStyle = COLORS.pvi;
      g.lineWidth = 1.5;
      g.beginPath();
      g.arc(x, y, r, 0, Math.PI * 2);
      if (sel) {
        g.fillStyle = COLORS.pvi;
        g.fill();
      }
      g.stroke();
      lastPvis.push({ x, y, index, c: p.c_m, z: p.z_m });
    });
    g.restore();
  },
  hit(x, y) {
    let best: Handle | null = null;
    let bestD = 81;
    for (const p of lastPvis) {
      const d2 = (p.x - x) ** 2 + (p.y - y) ** 2;
      if (d2 < bestD) {
        bestD = d2;
        best = { band: "pvi", kind: "pvi", index: p.index, c: p.c, z: p.z };
      }
    }
    return best;
  },
};

/** The plot's frame and the vertical exaggeration at its bottom right. */
export const frameBand: BandDef = {
  id: "frame",
  height: 0,
  axis: "profile",
  draw(g, v) {
    const P = v.plot;
    g.strokeStyle = COLORS.frame;
    g.lineWidth = 1;
    g.strokeRect(P.x + 0.5, P.y + 0.5, P.w - 1, P.h - 1);
    const txt = fmtVE(verticalExaggeration(P.w, P.h, v.c0, v.c1, v.z0, v.z1));
    g.font = `500 11px ${NUM_FONT}`;
    g.textAlign = "right";
    g.textBaseline = "bottom";
    const w = g.measureText(txt).width + 10;
    g.globalAlpha = 0.85;
    g.fillStyle = COLORS.paper;
    g.fillRect(P.x + P.w - w - 2, P.y + P.h - 20, w, 16);
    g.globalAlpha = 1;
    g.fillStyle = COLORS.text;
    g.fillText(txt, P.x + P.w - 7, P.y + P.h - 6);
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

/** The readout rows at a chainage, in the old readout's order, words and colours (3495-3503): from the whole solve
 * (solved.ts readoutRows), the rail and grade read between samples as the old railAt and gradeAt; before the whole
 * solve lands, the surveyed ground, the rail and its grade, and inside a platform the station's facts. */
export function readoutRowsAt(d: BandData, c: number, units: SheetView["units"]): ReadoutRow[] {
  const rail = d.rail ? sampleAt(d.rail.rail_m, d.rail.step_m, c) : null;
  const grade = d.rail ? sampleAt(d.rail.grade_permille, d.rail.step_m, c) : null;
  const half = (d.input?.params.platform_m ?? 0) / 2;
  const st = d.input?.stations.find((s) => Math.abs(s.c_m - c) <= half);
  const solved = readoutRows(d, c, units, rail, grade);
  if (solved) {
    if (st) solved.push({ text: `Station ${d.platformName?.(st.platform_id) ?? st.platform_id}` });
    return solved;
  }
  const dem = d.input?.ground ? valueAt(d.input.ground.z_m, d.input.ground.step_m, c) : null;
  const u = units.length;
  const out: ReadoutRow[] = [{ text: fmtCh(c) }];
  if (dem !== null) out.push({ text: `Ground  ${fmtZ(dem, units, 2)} ${u}` });
  if (rail !== null) out.push({ text: `Rail    ${fmtZ(rail, units, 2)} ${u}` });
  if (rail !== null && dem !== null)
    out.push({
      text: dem >= rail ? `Below   ${fmtZ(dem - rail, units, 2)} ${u}` : `Above   ${fmtZ(rail - dem, units, 2)} ${u}`,
    });
  if (grade !== null) out.push({ text: `Grade   ${fmtG(grade)}` });
  if (st) {
    out.push({ text: `Station ${d.platformName?.(st.platform_id) ?? st.platform_id}` });
    const f = d.facts?.find((x) => x.platform_id === st.platform_id && !x.deleted);
    if (f) {
      out.push({ text: `${typeLabel(f.type)}${f.type_source === "ben" ? " (Ben)" : ""}`, colour: typeColour(f.type) });
      if (f.structure) {
        const off = rail !== null && f.rail_m !== null ? rail - f.rail_m : 0;
        out.push({ text: `Top     ${fmtZ(f.structure.top_m + off, units, 2)} ${u}` });
        out.push({ text: `Bottom  ${fmtZ(f.structure.bottom_m + off, units, 2)} ${u}` });
      }
      out.push({ text: streetText(f.street) });
    }
  }
  return out;
}

/** The readout's rows as text (the tests and the text layer read these). */
export function readoutLines(d: BandData, c: number, units: SheetView["units"]): string[] {
  return readoutRowsAt(d, c, units).map((r) => r.text);
}

/** The chainage ruler in k+mmm under the plot, the hairline, a readout box at the pointer and a line in the strip. */
export const chainageBand: BandDef = {
  id: "chainage",
  height: 34,
  axis: "strip",
  draw(g, v, d: BandData) {
    const top = v.top;
    const P = v.plot;
    g.fillStyle = "#1e2128";
    g.fillRect(0, top, v.width, 34);
    g.strokeStyle = COLORS.gridMajor;
    g.fillStyle = COLORS.text;
    g.font = `11px ${NUM_FONT}`;
    g.lineWidth = 1;
    g.textAlign = "center";
    for (const t of chainageTicks(v.c0, v.c1, v.units, Math.max(2, Math.floor(P.w / 110)))) {
      const x = v.x(t.v);
      if (x < P.x - 1 || x > P.x + P.w + 1) continue;
      g.beginPath();
      g.moveTo(x, top);
      g.lineTo(x, top + 5);
      g.stroke();
      g.fillText(t.label, x, top + 16);
    }
    g.textAlign = "start";
    if (v.cursor === null) return;
    const c = v.cursor;
    const x = v.x(c);
    if (x >= P.x && x <= P.x + P.w) {
      g.strokeStyle = COLORS.cursor;
      g.globalAlpha = 0.6;
      g.beginPath();
      g.moveTo(Math.round(x) + 0.5, P.y);
      g.lineTo(Math.round(x) + 0.5, top);
      g.stroke();
      g.globalAlpha = 1;
    }
    const rail = d.rail ? valueAt(d.rail.rail_m, d.rail.step_m, c) : null;
    const grade = d.rail ? valueAt(d.rail.grade_permille, d.rail.step_m, c) : null;
    const ground = d.input?.ground ? valueAt(d.input.ground.z_m, d.input.ground.step_m, c) : null;
    const parts = [`c ${formatChainage(c, v.units)}`];
    if (rail !== null) parts.push(`rail ${v.units.format(rail, "m")} ${v.units.label("m")}`);
    if (ground !== null) parts.push(`ground ${v.units.format(ground, "m")} ${v.units.label("m")}`);
    if (rail !== null && ground !== null)
      parts.push(`depth ${v.units.format(ground - rail, "m")} ${v.units.label("m")}`);
    if (grade !== null) parts.push(`grade ${fmtG(grade)}`);
    g.fillStyle = COLORS.cursor;
    g.font = `11px ${UI_FONT}`;
    g.fillText(parts.join("   "), 6, top + 30);
    // The box at the pointer, as on the old sheet, while the pointer is over the plot.
    const pt = v.pointer;
    if (!pt || pt.y < P.y || pt.y > P.y + P.h) return;
    const rows = readoutRowsAt(d, c, v.units);
    const lines = rows.map((r) => r.text);
    g.font = `11px ${NUM_FONT}`;
    const w = Math.max(...lines.map((l) => g.measureText(l).width)) + 16;
    const h = lines.length * 15 + 8;
    let bx = pt.x + 14;
    if (bx + w > P.x + P.w) bx = pt.x - 14 - w;
    let by = pt.y + 14;
    if (by + h > P.y + P.h) by = Math.max(P.y, pt.y - 14 - h);
    g.globalAlpha = 0.94;
    g.fillStyle = "#23262e";
    g.fillRect(bx, by, w, h);
    g.globalAlpha = 1;
    g.strokeStyle = COLORS.frame;
    g.strokeRect(bx + 0.5, by + 0.5, w - 1, h - 1);
    // where the box is: a drag step draws it again there (dirty.ts)
    d.mark?.({ kind: "readout", id: "", x0: bx, y0: by, x1: bx + w, y1: by + h });
    g.textBaseline = "top";
    lines.forEach((l, i) => {
      g.fillStyle = i === 0 ? COLORS.ink : (rows[i]?.colour ?? COLORS.text);
      g.fillText(l, bx + 8, by + 5 + i * 15);
    });
    g.textBaseline = "alphabetic";
  },
};

export const BANDS: BandDef[] = [
  axesBand,
  waterBand,
  groundBand,
  groundWorksBand,
  contextBand,
  crossingsBand,
  locksBand,
  overGradeBand,
  outlinesBand,
  stationStructureBand,
  stationAccessBand,
  roadsBand,
  railBand,
  gradeBand,
  curveGradeBand,
  drawnGroundBand,
  pviBand,
  platformBand,
  crossingTicksBand,
  stationFlagsBand,
  issuesBand,
  paintPreviewBand,
  frameBand,
  structureStripBand,
  chainageBand,
  chronologyStripBand,
  overviewBand,
];
