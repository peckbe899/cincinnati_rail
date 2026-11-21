// The line sheet's first bands (section 8): ground and rail, platform and PVI marks, and the chainage ruler with
// the cursor readout. Profile bands share the sheet's chainage and level axes; strip bands get their own rows below.

import type { BandData, BandDef, Handle, SheetView } from "../../core/plugin.ts";
import { formatChainage } from "../../core/units.ts";

const COLORS = {
  ground: "#8a6d3b",
  groundFill: "rgba(138, 109, 59, 0.25)",
  rail: "#5aa9e6",
  server: "#7fd962",
  platform: "#e6b450",
  pvi: "#f07178",
  grid: "#2f333d",
  text: "#8b919e",
  cursor: "#d8dbe2",
};

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

let lastPvis: { x: number; y: number; index: number; c: number; z: number }[] = [];
let lastPlatforms: { x0: number; x1: number; y: number; index: number; c: number; z: number }[] = [];

export const groundBand: BandDef = {
  id: "ground",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const gr = d.input?.ground;
    if (!gr) return;
    g.strokeStyle = COLORS.ground;
    g.lineWidth = 1;
    polyline(g, v, gr.z_m, gr.step_m);
  },
};

export const railBand: BandDef = {
  id: "rail",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
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
      g.lineWidth = 1.5;
      polyline(g, v, d.rail.rail_m, d.rail.step_m);
    }
  },
};

export const platformBand: BandDef = {
  id: "platforms",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const inp = d.input;
    lastPlatforms = [];
    if (!inp) return;
    const half = inp.params.platform_m / 2;
    const rail = d.rail;
    g.strokeStyle = COLORS.platform;
    g.lineWidth = 4;
    g.fillStyle = COLORS.text;
    g.font = "11px system-ui, sans-serif";
    inp.stations.forEach((s, index) => {
      if (s.c_m + half < v.c0 || s.c_m - half > v.c1) return;
      const z = s.level_m ?? (rail ? (rail.rail_m[Math.round(s.c_m / rail.step_m)] ?? null) : null);
      if (z === null || !Number.isFinite(z)) return;
      const x0 = v.x(s.c_m - half);
      const x1 = v.x(s.c_m + half);
      const y = v.y(z) - 4;
      g.beginPath();
      g.moveTo(x0, y);
      g.lineTo(x1, y);
      g.stroke();
      // Names only when there is room: a platform at least 40 px wide.
      if (x1 - x0 >= 40) g.fillText(s.platform_id.split("|").pop() ?? s.platform_id, x0, y - 4);
      lastPlatforms.push({ x0, x1, y, index, c: s.c_m, z });
    });
  },
  hit(x, y) {
    const p = lastPlatforms.find((q) => x >= q.x0 - 3 && x <= q.x1 + 3 && Math.abs(y - q.y) < 7);
    return p ? { band: "platforms", kind: "station", index: p.index, c: p.c, z: p.z } : null;
  },
};

export const pviBand: BandDef = {
  id: "pvi",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    lastPvis = [];
    const pvi = d.input?.pvi ?? [];
    g.lineWidth = 1;
    pvi.forEach((p, index) => {
      if (p.c_m < v.c0 || p.c_m > v.c1) return;
      const x = v.x(p.c_m);
      const y = v.y(p.z_m);
      const sel = d.selected?.kind === "pvi" && d.selected.index === index;
      g.strokeStyle = COLORS.pvi;
      g.fillStyle = sel ? COLORS.pvi : "transparent";
      g.beginPath();
      g.arc(x, y, sel ? 5 : 4, 0, Math.PI * 2);
      g.fill();
      g.stroke();
      lastPvis.push({ x, y, index, c: p.c_m, z: p.z_m });
    });
  },
  hit(x, y) {
    let best: Handle | null = null;
    let bestD = 64;
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

function niceStep(span: number, px: number): number {
  const raw = (span / px) * 90;
  const p = 10 ** Math.floor(Math.log10(raw));
  for (const m of [1, 2, 5, 10]) if (m * p >= raw) return m * p;
  return 10 * p;
}

/** The value of a grid array at a chainage, by the nearest grid point. */
function at(arr: ArrayLike<number> | undefined, step: number, c: number): number | null {
  if (!arr) return null;
  const v = arr[Math.round(c / step)];
  return v === undefined || !Number.isFinite(v) ? null : v;
}

export const chainageBand: BandDef = {
  id: "chainage",
  height: 34,
  axis: "strip",
  draw(g, v, d: BandData) {
    const top = v.top;
    g.fillStyle = "#1e2128";
    g.fillRect(0, top, v.width, 34);
    const step = niceStep(v.c1 - v.c0, v.width);
    g.strokeStyle = COLORS.grid;
    g.fillStyle = COLORS.text;
    g.font = "11px system-ui, sans-serif";
    g.lineWidth = 1;
    for (let c = Math.ceil(v.c0 / step) * step; c <= v.c1; c += step) {
      const x = v.x(c);
      g.beginPath();
      g.moveTo(x, top);
      g.lineTo(x, top + 6);
      g.stroke();
      g.fillText(formatChainage(c, v.units), x + 2, top + 16);
    }
    if (v.cursor !== null) {
      const c = v.cursor;
      const x = v.x(c);
      g.strokeStyle = COLORS.cursor;
      g.beginPath();
      g.moveTo(x, 0);
      g.lineTo(x, top);
      g.stroke();
      const rail = d.rail ? at(d.rail.rail_m, d.rail.step_m, c) : null;
      const grade = d.rail ? at(d.rail.grade_permille, d.rail.step_m, c) : null;
      const ground = d.input?.ground ? at(d.input.ground.z_m, d.input.ground.step_m, c) : null;
      const parts = [`c ${formatChainage(c, v.units)}`];
      if (rail !== null) parts.push(`rail ${v.units.format(rail, "m")} ${v.units.label("m")}`);
      if (ground !== null) parts.push(`ground ${v.units.format(ground, "m")} ${v.units.label("m")}`);
      if (rail !== null && ground !== null)
        parts.push(`depth ${v.units.format(ground - rail, "m")} ${v.units.label("m")}`);
      if (grade !== null) parts.push(`grade ${grade.toFixed(2)} ‰`);
      g.fillStyle = COLORS.cursor;
      g.fillText(parts.join("   "), 6, top + 30);
    }
  },
};

export const BANDS: BandDef[] = [groundBand, railBand, platformBand, pviBand, chainageBand];
