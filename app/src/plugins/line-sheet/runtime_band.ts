// The run-time band (I2.1, claude/hub_maps/i21_plan.md 4.2): a strip under the structure strip, on the sheet's
// chainage axis, with the speed the train runs at along the line in both directions, the posted limit as a stepped
// line, a thin line at each station, the run time of each leg, and a header with the trip times. A draft's curves
// are drawn over the saved run's (faint), with the change after each trip time. Speeds in km/h, or mph when the sheet
// is in feet. The hover readout gives both speeds at the pointer, the limit and its reason, and when the front
// passes. It folds away on a line with no run.

import type { BandData, BandDef, SheetMark, SheetText, SheetView } from "../../core/plugin.ts";
import {
  formatChainage,
  formatChange,
  formatDuration,
  formatSpeed,
  KMH_PER_MPH,
  speedLabel,
} from "../../core/units.ts";
import { directionOf, type Run, type RunDirection, type RunDirs } from "./runs.ts";

export const RUNTIME_H = 110;
/** Room kept at the right of the header for the direction toggle (Both, Forward, Back) the sheet lays over it. */
export const RUN_TOGGLE_W = 160;

const UI_FONT = "system-ui, sans-serif";
const NUM_FONT = "ui-monospace, SFMono-Regular, Menlo, monospace";
export const RUN_COLORS = {
  fwd: "#5aa9e6",
  rev: "#e6b450",
  limit: "#8b919e",
  station: "#4a505c",
  removed: "#6b7280",
  ink: "#d8dbe2",
  text: "#8b919e",
  error: "#e5534b",
  paper: "#1b1d23",
  lit: "rgba(230, 180, 80, 0.16)",
};
const KMH = 3.6;

/** The train's short name ("Type 2005"), from the rolling stock's name. */
const trainShort = (name: string): string => /Type \w+/.exec(name)?.[0] ?? name.split(" (")[0] ?? name;

/** "2026, GoA3, Type 2005": the run's year, its era's grade of automation and its train, in short. */
export function eraShort(r: Run): string {
  const m = r.meta;
  const parts = [m.year !== null ? String(m.year) : null, m.era?.goa != null ? `GoA${m.era.goa}` : null];
  parts.push(trainShort(m.train?.name ?? ""));
  return parts.filter(Boolean).join(", ");
}

const dirsOf = (dirs: RunDirs): (1 | -1)[] => (dirs === "fwd" ? [1] : dirs === "rev" ? [-1] : [1, -1]);

/** The band's header: "Towne to Beechgrove 52:00 (running 37:31, dwell 14:29); back 51:49", and with a draft the
 * change after each trip time. */
export function runHeader(
  run: Run,
  saved: Run | null,
  _units: SheetView["units"],
  dirs: RunDirs,
  draft: boolean,
): string {
  const out: string[] = [];
  const change = (d: RunDirection) => {
    if (!draft || !saved) return "";
    const s = directionOf(saved, d.dir);
    return s ? ` (${formatChange(d.trip_s - s.trip_s)})` : "";
  };
  const ds = dirsOf(dirs)
    .map((k) => directionOf(run, k))
    .filter((d): d is RunDirection => !!d);
  ds.forEach((d, i) => {
    if (i === 0)
      out.push(
        `${d.label} ${formatDuration(d.trip_s)}${change(d)} (running ${formatDuration(d.running_s)}, dwell ${formatDuration(d.dwell_s)})`,
      );
    else out.push(`back ${formatDuration(d.trip_s)}${change(d)}`);
  });
  return out.join("; ");
}

/** The header as drawn: the trip times, then what the band shows (draft, updating, a note, an error), then the era
 * and train, cut from the end so it stays left of the toggle: the era goes first, then the running and dwell split,
 * then the rest is cut short with an ellipsis. */
export function fitHeader(
  g: CanvasRenderingContext2D,
  main: string,
  status: string[],
  era: string,
  maxW: number,
): string {
  const short = main.replace(/ \(running [^)]*\)/, "");
  const tries = [
    [main, ...status, era],
    [main, ...status],
    [short, ...status],
  ].map((p) => p.filter(Boolean).join(" · "));
  for (const t of tries) if (g.measureText(t).width <= maxW) return t;
  let t = tries[tries.length - 1] ?? "";
  while (t.length > 1 && g.measureText(`${t}…`).width > maxW) t = t.slice(0, -1);
  return `${t.trimEnd()}…`;
}

/** Where each speed array comes down to a stand: between two samples where the front took far longer than its speed
 * gives (a stop and its dwell), and just past each end of the run. railsim's own plot drew the speed to zero at every
 * stop; on the 10 m grid the samples either side of a stop are still moving. Chainages, rising. */
const standsKept = new WeakMap<Float64Array, number[]>();
function standsOf(a: Float64Array, t: Float64Array | undefined, step: number): number[] {
  const kept = standsKept.get(a);
  if (kept) return kept;
  const out: number[] = [];
  let first = -1;
  let last = -1;
  for (let i = 0; i < a.length; i++) {
    const v0 = a[i] as number;
    if (!Number.isFinite(v0)) continue;
    if (first < 0) first = i;
    last = i;
    const v1 = a[i + 1];
    const t0 = t?.[i];
    const t1 = t?.[i + 1];
    if (v1 === undefined || !Number.isFinite(v1) || t0 === undefined || t1 === undefined) continue;
    if (!Number.isFinite(t0) || !Number.isFinite(t1)) continue;
    const pass = step / Math.max((v0 + v1) / 2, 0.3);
    if (Math.abs(t1 - t0) > 2 * pass + 8) {
      const e = v0 * v0 + v1 * v1;
      out.push(i * step + (e > 0 ? (step * v0 * v0) / e : step / 2));
    }
  }
  if (first >= 0) {
    // braking or starting at about 1 m/s2 from the first and last speeds the grid saw, within a sample
    const end = (v: number) => Math.min(step, (v * v) / 2);
    out.unshift(first * step - end(a[first] as number));
    out.push(last * step + end(a[last] as number));
  }
  standsKept.set(a, out);
  return out;
}

/** Where the front is at chainage c on a 10 m grid array (linear between samples; null outside the run). */
function at(a: Float64Array, step: number, c: number): number | null {
  const f = c / step;
  const i = Math.floor(f);
  const v0 = a[i];
  const v1 = a[i + 1];
  if (v0 === undefined || !Number.isFinite(v0)) return null;
  if (v1 === undefined || !Number.isFinite(v1)) return v0;
  return v0 + (v1 - v0) * (f - i);
}

interface Frame {
  x0: number;
  x1: number;
  y0: number;
  y1: number;
  vmax: number;
  y(kmh: number): number;
}

function curve(
  g: CanvasRenderingContext2D,
  v: SheetView,
  f: Frame,
  a: Float64Array,
  t: Float64Array | undefined,
  step: number,
): void {
  const n = a.length;
  if (!n) return;
  const i0 = Math.max(0, Math.floor(v.c0 / step) - 1);
  const i1 = Math.min(n - 1, Math.ceil(v.c1 / step) + 1);
  const per = Math.max(1, Math.floor((i1 - i0) / (v.width * 2)));
  const stands = standsOf(a, t, step);
  let k = stands.findIndex((c) => c >= (i0 - 1) * step);
  if (k < 0) k = stands.length;
  g.beginPath();
  let pen = false;
  const to = (x: number, y: number) => {
    if (pen) g.lineTo(x, y);
    else g.moveTo(x, y);
    pen = true;
  };
  for (let i = i0; i <= i1; i += per) {
    // the stands before this sample, at zero speed
    for (; k < stands.length && (stands[k] as number) < i * step; k++) to(v.x(stands[k] as number), f.y1);
    const ms = a[i];
    if (ms === undefined || !Number.isFinite(ms)) {
      pen = false;
      continue;
    }
    to(v.x(i * step), f.y(ms * KMH));
  }
  for (; k < stands.length && (stands[k] as number) <= (i1 + 1) * step; k++) to(v.x(stands[k] as number), f.y1);
  g.stroke();
}

function limitLine(g: CanvasRenderingContext2D, v: SheetView, f: Frame, r: Run): void {
  g.beginPath();
  let first = true;
  for (const z of r.meta.speed_zones) {
    if (z.c1_m < v.c0 || z.c0_m > v.c1) continue;
    const xa = Math.max(f.x0, v.x(z.c0_m));
    const xb = Math.min(f.x1, v.x(z.c1_m));
    const y = f.y(z.kmh);
    if (first) g.moveTo(xa, y);
    else g.lineTo(xa, y);
    g.lineTo(xb, y);
    first = false;
  }
  g.stroke();
}

/** The zone of the posted limit at c. */
const zoneAt = (r: Run, c: number) => r.meta.speed_zones.find((z) => z.c0_m <= c && c <= z.c1_m) ?? null;

/** Everything the band draws but the readout: the header, the axis, the stations, the limit, the curves, the legs. */
function paintBand(g: CanvasRenderingContext2D, v: SheetView, d: BandData): void {
  const rb = d.run;
  if (!rb) return;
  const P = v.plot;
  const top = v.top;
  const H = RUNTIME_H;
  const run = rb.draft ?? rb.saved;
  g.fillStyle = RUN_COLORS.paper;
  g.fillRect(0, top, v.width, H);
  d.mark?.({ kind: "runtime-band", id: "", y0: top, y1: top + H });
  const u = v.units;
  // ---- the header
  let head: string;
  let shown: string;
  g.font = `600 11px ${UI_FONT}`;
  const room = P.w - RUN_TOGGLE_W - 8;
  if (!run) {
    head = rb.error ? `Run times: ${rb.error}` : `Run times: ${rb.updating ? "updating" : "not run yet"}`;
    shown = fitHeader(g, head, [], "", room);
  } else {
    const main = runHeader(run, rb.saved, u, rb.dirs, !!rb.draft);
    const status = [rb.draft ? "draft" : "", rb.updating ? "updating" : "", rb.note ?? "", rb.error ?? ""];
    head = [main, eraShort(run), ...status].filter(Boolean).join(" · ");
    shown = fitHeader(g, main, status, eraShort(run), room);
  }
  g.textBaseline = "alphabetic";
  g.textAlign = "start";
  g.fillStyle = rb.error ? RUN_COLORS.error : RUN_COLORS.ink;
  g.fillText(shown, P.x, top + 12);
  d.report?.({ kind: "run", text: head, c: v.c0, drawn: true });
  if (!run) return;

  // ---- the frame: speed from 0 to 1.1 times the highest limit
  const zmax = Math.max(1, ...run.meta.speed_zones.map((z) => z.kmh));
  const frame: Frame = {
    x0: P.x,
    x1: P.x + P.w,
    y0: top + 28,
    y1: top + H - 14,
    vmax: zmax * 1.1,
    y: (kmh) => frame.y1 - (Math.max(0, kmh) / frame.vmax) * (frame.y1 - frame.y0),
  };
  const ft = u.length === "ft";
  const tick = ft ? 10 * KMH_PER_MPH : 20;
  g.font = `10px ${NUM_FONT}`;
  g.textAlign = "right";
  g.textBaseline = "middle";
  g.lineWidth = 1;
  for (let k = tick; k < frame.vmax; k += tick) {
    const y = Math.round(frame.y(k)) + 0.5;
    g.strokeStyle = "#2a2e37";
    g.beginPath();
    g.moveTo(frame.x0, y);
    g.lineTo(frame.x1, y);
    g.stroke();
    g.fillStyle = RUN_COLORS.text;
    g.fillText(formatSpeed(k, u), P.x - 6, y);
  }
  g.fillText(speedLabel(u), P.x - 6, frame.y0 - 6);
  g.textAlign = "start";
  g.textBaseline = "alphabetic";

  g.save();
  g.beginPath();
  g.rect(frame.x0, top + 14, frame.x1 - frame.x0, H - 14);
  g.clip();

  // ---- a leg lit from the table
  if (rb.lit) {
    const dd = directionOf(run, rb.lit.dir);
    const a = dd?.stations[rb.lit.k - 1]?.c_m;
    const b = dd?.stations[rb.lit.k]?.c_m;
    if (a != null && b != null) {
      g.fillStyle = RUN_COLORS.lit;
      const xa = v.x(Math.min(a, b));
      g.fillRect(xa, frame.y0, v.x(Math.max(a, b)) - xa, frame.y1 - frame.y0);
    }
  }
  // ---- the stations: a thin line at each live one, the removed ones faint and dashed
  const fwd = directionOf(run, 1) ?? run.meta.directions[0] ?? null;
  g.strokeStyle = RUN_COLORS.station;
  for (const s of fwd?.stations ?? []) {
    if (s.c_m == null) continue;
    const x = Math.round(v.x(s.c_m)) + 0.5;
    if (x < P.x - 1 || x > P.x + P.w + 1) continue;
    g.beginPath();
    g.moveTo(x, frame.y0);
    g.lineTo(x, frame.y1);
    g.stroke();
    d.mark?.({ kind: "station-line", id: s.platform_id ?? s.name, c: s.c_m, x });
  }
  g.save();
  g.setLineDash([3, 3]);
  g.strokeStyle = RUN_COLORS.removed;
  g.globalAlpha = 0.6;
  for (const r of rb.removed) {
    const x = Math.round(v.x(r.c)) + 0.5;
    if (x < P.x - 1 || x > P.x + P.w + 1) continue;
    g.beginPath();
    g.moveTo(x, frame.y0);
    g.lineTo(x, frame.y1);
    g.stroke();
    d.mark?.({ kind: "removed-line", id: r.name, c: r.c, x });
  }
  g.restore();

  // ---- the posted limit, stepped
  g.strokeStyle = RUN_COLORS.limit;
  g.lineWidth = 1;
  limitLine(g, v, frame, run);

  // ---- the speed curves: the saved run faint under a draft
  const step = run.meta.grid?.step_m ?? 10;
  const show = dirsOf(rb.dirs);
  const dim = rb.updating ? 0.5 : 1;
  const curves = (r: Run, alpha: number) => {
    for (const k of show) {
      g.save();
      g.globalAlpha = alpha;
      g.lineWidth = 1.6;
      g.strokeStyle = k === 1 ? RUN_COLORS.fwd : RUN_COLORS.rev;
      if (k === -1) g.setLineDash([5, 3]);
      curve(
        g,
        v,
        frame,
        k === 1 ? r.arrays.v_fwd_ms : r.arrays.v_rev_ms,
        k === 1 ? r.arrays.t_fwd_s : r.arrays.t_rev_s,
        r.meta.grid?.step_m ?? step,
      );
      g.restore();
    }
  };
  if (rb.draft && rb.saved) curves(rb.saved, 0.28);
  curves(run, dim);
  g.restore();

  for (const k of show) {
    const dd = directionOf(run, k);
    if (dd)
      d.mark?.({
        kind: "run",
        id: "",
        dir: k,
        trip_s: dd.trip_s,
        running_s: dd.running_s,
        draft: !!rb.draft,
      });
  }

  // ---- the leg times: forward above the curves, back below, thinned as the other labels are
  g.font = `10px ${NUM_FONT}`;
  g.textAlign = "center";
  for (const k of show) {
    const dd = directionOf(run, k);
    if (!dd) continue;
    const y = k === 1 ? frame.y0 - 3 : frame.y1 + 11;
    let lastRight = Number.NEGATIVE_INFINITY;
    const legs = dd.stations
      .map((s, i) => ({ s, prev: dd.stations[i - 1] }))
      .filter((x) => x.prev && x.s.leg && x.s.c_m != null && x.prev.c_m != null)
      .map((x) => {
        const a = x.prev?.c_m as number;
        const b = x.s.c_m as number;
        return { from: x.prev?.name ?? "", to: x.s.name, c: (a + b) / 2, run_s: x.s.leg?.run_s ?? 0 };
      })
      .sort((p, q) => p.c - q.c);
    for (const l of legs) {
      const text = formatDuration(l.run_s);
      const x = v.x(l.c);
      const w = g.measureText(text).width;
      const inView = x >= P.x && x <= P.x + P.w;
      const drawn = inView && x - w / 2 > lastRight + 4;
      if (drawn) {
        g.fillStyle = k === 1 ? RUN_COLORS.fwd : RUN_COLORS.rev;
        g.fillText(text, x, y);
        lastRight = x + w / 2;
        d.mark?.({ kind: "leg", id: `${l.from}|${l.to}`, dir: k, from: l.from, to: l.to, run_s: l.run_s, x });
      }
      d.report?.({ kind: "leg", text: `${l.from} to ${l.to} ${text}`, c: l.c, drawn });
    }
  }
  g.textAlign = "start";
}

/** The readout at the pointer, drawn live over the band (the rest may come from the bitmap). */
function readoutAt(g: CanvasRenderingContext2D, v: SheetView, d: BandData): void {
  const rb = d.run;
  const run = rb ? (rb.draft ?? rb.saved) : null;
  if (!rb || !run) return;
  const P = v.plot;
  const top = v.top;
  const H = RUNTIME_H;
  const u = v.units;
  const show = dirsOf(rb.dirs);
  const step = run.meta.grid?.step_m ?? 10;
  // ---- the readout at the pointer, while it is over the band
  const pt = v.pointer;
  if (!pt || pt.y < top || pt.y > top + H || pt.x < P.x || pt.x > P.x + P.w) return;
  const c = v.c(pt.x);
  const rows: { text: string; colour: string }[] = [{ text: `c ${formatChainage(c, u)}`, colour: RUN_COLORS.ink }];
  const sl = speedLabel(u);
  for (const k of show) {
    const vs = at(k === 1 ? run.arrays.v_fwd_ms : run.arrays.v_rev_ms, step, c);
    const ts = at(k === 1 ? run.arrays.t_fwd_s : run.arrays.t_rev_s, step, c);
    if (vs === null) continue;
    rows.push({
      text: `${k === 1 ? "Forward" : "Back"} ${formatSpeed(vs * KMH, u)} ${sl}${ts !== null ? `, passes at ${formatDuration(ts)}` : ""}`,
      colour: k === 1 ? RUN_COLORS.fwd : RUN_COLORS.rev,
    });
  }
  const z = zoneAt(run, c);
  if (z) rows.push({ text: `Limit ${formatSpeed(z.kmh, u)} ${sl}: ${z.reason}`, colour: RUN_COLORS.limit });
  g.font = `11px ${NUM_FONT}`;
  const w = Math.max(...rows.map((r) => g.measureText(r.text).width)) + 16;
  const h = rows.length * 15 + 8;
  let bx = pt.x + 14;
  if (bx + w > P.x + P.w) bx = pt.x - 14 - w;
  // under the header line, so the direction toggle laid over the header never covers a row
  const by = top + 16;
  g.globalAlpha = 0.94;
  g.fillStyle = "#23262e";
  g.fillRect(bx, by, w, h);
  g.globalAlpha = 1;
  d.mark?.({ kind: "readout", id: "run", x0: bx, y0: by, x1: bx + w, y1: by + h });
  g.textBaseline = "top";
  rows.forEach((r, i) => {
    g.fillStyle = r.colour;
    g.fillText(r.text, bx + 8, by + 5 + i * 15);
    d.report?.({ kind: "run-readout", text: r.text, c, drawn: true });
  });
  g.textBaseline = "alphabetic";
}

/** The band as last drawn, as a bitmap with what it marked and reported: a frame that changes nothing the band
 * reads (a drag step: the run, the range, the width and the units stay) copies it, so a drag pays a blit, not two
 * curves of 3,000 points and sixty labels. */
let kept: { key: string; canvas: HTMLCanvasElement; marks: SheetMark[]; texts: SheetText[] } | null = null;

function fromBitmap(g: CanvasRenderingContext2D, v: SheetView, d: BandData): boolean {
  const rb = d.run;
  if (!rb || typeof document === "undefined") return false;
  const key = JSON.stringify([
    rb.saved?.key,
    rb.draft?.key,
    rb.updating,
    rb.error,
    rb.note,
    rb.dirs,
    rb.lit,
    rb.removed,
    v.c0,
    v.c1,
    v.width,
    v.top,
    v.plot.x,
    v.plot.w,
    v.dpr,
    v.units.length,
  ]);
  if (kept?.key !== key) {
    const canvas = kept?.canvas ?? document.createElement("canvas");
    const W = Math.max(1, Math.round(v.width * v.dpr));
    const H = Math.max(1, Math.round(RUNTIME_H * v.dpr));
    if (canvas.width !== W) canvas.width = W;
    if (canvas.height !== H) canvas.height = H;
    const bg = canvas.getContext("2d");
    if (!bg) return false;
    bg.setTransform(1, 0, 0, 1, 0, 0);
    bg.clearRect(0, 0, W, H);
    bg.setTransform(v.dpr, 0, 0, v.dpr, 0, -v.top * v.dpr);
    const marks: SheetMark[] = [];
    const texts: SheetText[] = [];
    paintBand(bg, v, { ...d, mark: (m) => marks.push(m), report: (t) => texts.push(t) });
    kept = { key, canvas, marks, texts };
  }
  g.drawImage(kept.canvas, 0, v.top, v.width, RUNTIME_H);
  for (const m of kept.marks) d.mark?.(m);
  for (const t of kept.texts) d.report?.(t);
  return true;
}

export const runtimeBand: BandDef = {
  id: "runtime",
  height: RUNTIME_H,
  axis: "strip",
  heightFor: (d) => (d.run ? RUNTIME_H : 0),
  draw(g, v, d: BandData) {
    if (!d.run) return;
    if (!fromBitmap(g, v, d)) paintBand(g, v, d);
    readoutAt(g, v, d);
  },
};
