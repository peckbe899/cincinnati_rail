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
  SEV_COLOURS,
  slideText,
  stationText,
  streetText,
  thinLabels,
  typeColour,
  typeLabel,
  valueAt,
  verticalExaggeration,
  worstSeverity,
} from "./drawing.ts";
import { stationAccessBand, stationFlagsBand, stationStripBand, stationStructureBand } from "./stations.ts";

export const COLORS = {
  ground: "#8a6d3b",
  earth: "rgba(138, 109, 59, 0.16)",
  rail: "#5aa9e6",
  server: "#7fd962",
  ink: "#d8dbe2",
  selected: "#e6b450",
  pvi: "#f07178",
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
    if (d.rail) {
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
    for (const lab of gradeLabels(gradeChords(d.dv), v.x, P.x, P.x + P.w, P.w < 500 ? 56 : 66)) {
      const z = valueAt(rail.rail_m, rail.step_m, v.c(lab.xm));
      if (z === null) continue;
      const ym = v.y(z) - 8;
      const w = g.measureText(lab.text).width + 8;
      g.globalAlpha = 0.85;
      g.fillStyle = COLORS.paper;
      g.fillRect(lab.xm - w / 2, ym - 14, w, 14);
      g.globalAlpha = 1;
      g.fillStyle = COLORS.text;
      g.fillText(lab.text, lab.xm, ym);
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
      const unset = !!f && s.level_m === null && f.default_level_m !== null;
      const z = unset ? (f?.default_level_m as number) : stationLevel(s, d.rail);
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
      const xa = v.x(s.c_m - half);
      const xb = Math.max(xa + 3, v.x(s.c_m + half));
      const ya = v.y(z - gp * half);
      const yb = v.y(z + gp * half);
      const colour = on ? COLORS.selected : COLORS.ink;
      const sev = f ? worstSeverity(f.flags) : null;
      g.save();
      clipPlot(g, v);
      g.lineCap = "butt";
      if (sev) {
        // The flag outline: a wider stroke in the severity colour under the bar, 1.5 px either side.
        g.strokeStyle = SEV_COLOURS[sev];
        g.lineWidth = 9;
        g.beginPath();
        g.moveTo(xa - 1.5, ya);
        g.lineTo(xb + 1.5, yb);
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
        g.font = `600 10px ${UI_FONT}`;
        g.textAlign = "center";
        g.textBaseline = "bottom";
        g.fillText("level not set", (xa + xb) / 2, Math.min(ya, yb) - 5);
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
      g.textBaseline = "bottom";
      g.fillStyle = COLORS.text;
      const t = d.platformName?.(f.platform_id) ?? f.name;
      g.fillText(t, x, y - 11);
      const w = g.measureText(t).width;
      g.beginPath();
      g.moveTo(x - w / 2, y - 16);
      g.lineTo(x + w / 2, y - 16);
      g.stroke();
      g.restore();
      d.mark?.({ kind: "removed", id: f.platform_id, c: f.point_c_m, x, y });
    }
    // Names: the ends of the line first, then left to right, 18 px apart as on the old page.
    const n = inp.stations.length;
    const named = thinLabels(
      items.map((it) => ({ x: it.x, priority: it.index === 0 || it.index === n - 1 ? 0 : 1, selected: it.on })),
      18,
    );
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
    pvi.forEach((p, index) => {
      if (p.c_m < v.c0 || p.c_m > v.c1) return;
      const x = v.x(p.c_m);
      const y = v.y(p.z_m);
      const sel = d.selected?.kind === "pvi" && d.selected.c === p.c_m && d.selected.z === p.z_m;
      g.strokeStyle = COLORS.pvi;
      g.lineWidth = 1.5;
      g.beginPath();
      g.arc(x, y, sel ? 6 : 5, 0, Math.PI * 2);
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

/** The readout lines at a chainage, in the old readout's order and formats. */
export function readoutLines(d: BandData, c: number, units: SheetView["units"]): string[] {
  const rail = d.rail ? valueAt(d.rail.rail_m, d.rail.step_m, c) : null;
  const grade = d.rail ? valueAt(d.rail.grade_permille, d.rail.step_m, c) : null;
  const ground = d.input?.ground ? valueAt(d.input.ground.z_m, d.input.ground.step_m, c) : null;
  const u = units.length;
  const out = [fmtCh(c)];
  if (ground !== null) out.push(`Ground  ${fmtZ(ground, units, 2)} ${u}`);
  if (rail !== null) out.push(`Rail    ${fmtZ(rail, units, 2)} ${u}`);
  if (rail !== null && ground !== null)
    out.push(
      ground >= rail
        ? `Below   ${fmtZ(ground - rail, units, 2)} ${u}`
        : `Above   ${fmtZ(rail - ground, units, 2)} ${u}`,
    );
  if (grade !== null) out.push(`Grade   ${fmtG(grade)}`);
  const half = (d.input?.params.platform_m ?? 0) / 2;
  const st = d.input?.stations.find((s) => Math.abs(s.c_m - c) <= half);
  if (st) {
    out.push(`Station ${d.platformName?.(st.platform_id) ?? st.platform_id}`);
    // Inside a platform, what the old readout added: the type with its source, the structure, the street.
    const f = d.facts?.find((x) => x.platform_id === st.platform_id && !x.deleted);
    if (f) {
      out.push(`Type    ${typeLabel(f.type)}${f.type_source === "ben" ? " (Ben)" : ""}`);
      if (f.structure) {
        const off = rail !== null && f.rail_m !== null ? rail - f.rail_m : 0;
        out.push(`Top     ${fmtZ(f.structure.top_m + off, units, 2)} ${u}`);
        out.push(`Bottom  ${fmtZ(f.structure.bottom_m + off, units, 2)} ${u}`);
      }
      out.push(`Street  ${streetText(f.street)}`);
    }
  }
  return out;
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
    const lines = readoutLines(d, c, v.units);
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
    g.textBaseline = "top";
    lines.forEach((l, i) => {
      g.fillStyle = i === 0 ? COLORS.ink : COLORS.text;
      g.fillText(l, bx + 8, by + 5 + i * 15);
    });
    g.textBaseline = "alphabetic";
  },
};

export const BANDS: BandDef[] = [
  axesBand,
  groundBand,
  stationStructureBand,
  stationAccessBand,
  railBand,
  gradeBand,
  platformBand,
  pviBand,
  stationFlagsBand,
  frameBand,
  stationStripBand,
  chainageBand,
];
