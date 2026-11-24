// The line sheet's station bands (claude/hub_maps/profiles_parity.md A.1): each station's structure in its type
// colour, its access (halls, mezzanine, crossunder, shaft, the D_HALL line), its flags as triangles along the bottom
// of the plot, and a strip under the plot in the type colour over each platform. All of it comes from
// station.facts@1 of the draft (BandData.facts), so an edit redraws them with the rail.

import type { StationFact } from "@cr/engine/contract";
import type { BandData, BandDef, Handle, SheetView } from "../../core/plugin.ts";
import { accessShapes, drawsDHall, SEV_COLOURS, structureQuad, typeColour, typeLabel, valueAt } from "./drawing.ts";

const UI_FONT = "system-ui, sans-serif";
const PAPER = "#16181d";
const INK = "#d8dbe2";
const MUTED = "#8b919e";
const SELECTED = "#e6b450";

function clipPlot(g: CanvasRenderingContext2D, v: SheetView): void {
  g.beginPath();
  g.rect(v.plot.x, v.plot.y, v.plot.w, v.plot.h);
  g.clip();
}

const live = (d: BandData): StationFact[] => (d.facts ?? []).filter((f) => !f.deleted);
const inView = (v: SheetView, c0: number, c1: number) => c1 >= v.c0 && c0 <= v.c1;
const isSelected = (d: BandData, id: string) => d.selected?.kind === "station" && d.selected.id === id;

/** The ground at a chainage from the sheet's input, null off it. */
export function groundOf(d: BandData): (c: number) => number | null {
  const gr = d.input?.ground;
  return (c) => (gr ? valueAt(gr.z_m, gr.step_m, c) : null);
}

/**
 * The structure of each station over its platform, tilted with the bar: a box from rail − 1.0 to rail + 4.6 (5.2
 * for an island), the phase's tube, or the elevated deck, filled at 25 % in the type colour with a 1.5 px edge. At
 * grade and open trough stations have no outline. The running line between stations is not drawn here (I2.2).
 */
export const stationStructureBand: BandDef = {
  id: "station-structure",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const fs = live(d);
    if (!fs.length) return;
    g.save();
    clipPlot(g, v);
    for (const f of fs) {
      if (!inView(v, f.c_m - f.half_m, f.c_m + f.half_m)) continue;
      // The quad from the draft's own level and grade, so a drag moves the outline with the bar at once.
      const q = structureQuad(f);
      if (!q) continue;
      const colour = typeColour(f.type);
      const pts = q.map(([c, z]) => [v.x(c), v.y(z)] as [number, number]);
      g.beginPath();
      for (const [i, [x, y]] of pts.entries()) {
        if (i) g.lineTo(x, y);
        else g.moveTo(x, y);
      }
      g.closePath();
      g.globalAlpha = 0.25;
      g.fillStyle = colour;
      g.fill();
      g.globalAlpha = 1;
      g.strokeStyle = colour;
      g.lineWidth = isSelected(d, f.platform_id) ? 2 : 1.5;
      g.stroke();
      d.mark?.({
        kind: "structure",
        id: f.platform_id,
        type: f.type,
        what: f.structure?.kind ?? null,
        top_m: f.structure?.top_m ?? null,
        bottom_m: f.structure?.bottom_m ?? null,
        colour,
      });
    }
    g.restore();
  },
};

/**
 * Each Metro station's access, with the old page's sizes and labels: ticket halls or a mezzanine on the box roof,
 * the street mezzanine under an elevated station, the crossunder, the stair or lift shaft, and the dashed D_HALL line
 * at ground − D_HALL over the platform. All dashed when the station has no opening year in the Chronology.
 */
export const stationAccessBand: BandDef = {
  id: "station-access",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    const fs = live(d);
    if (!fs.length) return;
    const groundAt = groundOf(d);
    g.save();
    clipPlot(g, v);
    g.font = `600 10px ${UI_FONT}`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    for (const f of fs) {
      if (!f.access || !inView(v, f.c_m - f.half_m, f.c_m + f.half_m)) continue;
      const dash = f.access.dashed ? [4, 3] : [];
      for (const sh of accessShapes(f, groundAt)) {
        const x0 = v.x(sh.c0);
        const x1 = Math.max(x0 + 3, v.x(sh.c1));
        const y0 = v.y(Math.max(sh.z0, sh.z1));
        const y1 = v.y(Math.min(sh.z0, sh.z1));
        g.setLineDash(dash);
        g.globalAlpha = sh.what === "crossunder" ? 0.35 : sh.what === "shaft" ? 0.25 : 0.22;
        g.fillStyle = sh.colour;
        g.fillRect(x0, y0, x1 - x0, y1 - y0);
        g.globalAlpha = 0.9;
        g.strokeStyle = sh.colour;
        g.lineWidth = 1;
        if (sh.what !== "crossunder") g.strokeRect(x0, y0, x1 - x0, y1 - y0);
        g.globalAlpha = 1;
        g.setLineDash([]);
        const w = x1 - x0;
        if (sh.what === "shaft") {
          g.save();
          g.fillStyle = MUTED;
          g.translate((x0 + x1) / 2, (y0 + y1) / 2);
          g.rotate(-Math.PI / 2);
          if (y1 - y0 > 30) g.fillText(sh.label, 0, 0);
          g.restore();
        } else if (sh.what === "crossunder") {
          g.fillStyle = MUTED;
          g.textBaseline = "top";
          if (w > 3) g.fillText(sh.label, (x0 + x1) / 2, y1 + 2);
          g.textBaseline = "middle";
        } else if (w > (sh.what === "mezzanine" ? 80 : 54)) {
          g.fillStyle = INK;
          g.fillText(sh.label, (x0 + x1) / 2, (y0 + y1) / 2);
        }
        d.mark?.({
          kind: "access",
          id: f.platform_id,
          what: sh.what,
          c0: sh.c0,
          c1: sh.c1,
          z0: sh.z0,
          z1: sh.z1,
          label: sh.label,
          dashed: sh.dashed,
        });
      }
      if (drawsDHall(f.access)) {
        const dh = f.access.d_hall_m as number;
        g.setLineDash([3, 3]);
        g.strokeStyle = typeColour("cutcover");
        g.globalAlpha = 0.7;
        g.lineWidth = 1;
        g.beginPath();
        let k = 0;
        for (let c = Math.max(f.c_m - f.half_m, v.c0); c <= Math.min(f.c_m + f.half_m, v.c1); c += 4) {
          const gz = groundAt(c);
          if (gz === null) continue;
          if (k++) g.lineTo(v.x(c), v.y(gz - dh));
          else g.moveTo(v.x(c), v.y(gz - dh));
        }
        g.stroke();
        g.globalAlpha = 1;
        g.setLineDash([]);
        d.mark?.({ kind: "dhall", id: f.platform_id, d_hall_m: dh });
      }
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};

let lastFlags: { x: number; y: number; id: string; c: number; index: number }[] = [];

/** The station flags as triangles along the bottom of the plot, red, amber or grey, at the platform centre; one per
 * station and severity, the worst in front. Hover reads the flag; a click selects its station. */
export const stationFlagsBand: BandDef = {
  id: "station-flags",
  height: 0,
  axis: "profile",
  draw(g, v, d) {
    lastFlags = [];
    const fs = live(d);
    const P = v.plot;
    const order = { info: 0, warn: 1, error: 2 } as const;
    g.save();
    clipPlot(g, v);
    for (const f of fs) {
      if (!f.flags.length) continue;
      const c = f.c_m;
      if (c < v.c0 || c > v.c1) continue;
      const sevs = [...new Set(f.flags.map((x) => x.sev))].sort((a, b) => order[a] - order[b]);
      const x = v.x(c);
      const y = P.y + P.h - 3;
      sevs.forEach((sev, i) => {
        const dx = (i - (sevs.length - 1) / 2) * 5;
        g.fillStyle = SEV_COLOURS[sev];
        g.beginPath();
        g.moveTo(x + dx, y - 9);
        g.lineTo(x + dx + 5, y);
        g.lineTo(x + dx - 5, y);
        g.closePath();
        g.fill();
      });
      lastFlags.push({ x, y: y - 4, id: f.platform_id, c, index: f.index ?? 0 });
      for (const fl of f.flags)
        d.mark?.({ kind: "flag", id: f.platform_id, flag: fl.kind, sev: fl.sev, rule: fl.rule, x, y: y - 4 });
    }
    g.restore();
  },
  hit(x, y) {
    for (const t of lastFlags)
      if (Math.abs(x - t.x) <= 7 && Math.abs(y - t.y) <= 7)
        return { band: "station-flags", kind: "flag", index: t.index, id: t.id, c: t.c } satisfies Handle;
    return null;
  },
};

/** A 16 px strip under the plot: each live platform in its type colour with its type's name when it fits; the
 * running line between stations stays one colour until the structure solver is in (I2.2). */
export const stationStripBand: BandDef = {
  id: "station-strip",
  height: 18,
  axis: "strip",
  draw(g, v, d) {
    const P = v.plot;
    const top = v.top + 1;
    g.fillStyle = "#23262e";
    g.fillRect(P.x, top, P.w, 16);
    const fs = live(d);
    g.save();
    g.beginPath();
    g.rect(P.x, top, P.w, 16);
    g.clip();
    g.font = `600 10px ${UI_FONT}`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    for (const f of fs) {
      if (!f.type || !inView(v, f.c_m - f.half_m, f.c_m + f.half_m)) continue;
      const x0 = v.x(f.c_m - f.half_m);
      const x1 = Math.max(x0 + 2, v.x(f.c_m + f.half_m));
      g.fillStyle = typeColour(f.type);
      g.fillRect(x0, top, x1 - x0, 16);
      if (isSelected(d, f.platform_id)) {
        g.strokeStyle = SELECTED;
        g.lineWidth = 2;
        g.strokeRect(x0 + 1, top + 1, x1 - x0 - 2, 14);
      }
      const label = typeLabel(f.type).toUpperCase();
      if (g.measureText(label).width + 8 < x1 - x0) {
        g.fillStyle = PAPER;
        g.fillText(label, (x0 + x1) / 2, top + 8.5);
      }
      d.mark?.({ kind: "strip", id: f.platform_id, type: f.type, x0, x1 });
    }
    g.restore();
    g.textAlign = "start";
    g.textBaseline = "alphabetic";
  },
};
