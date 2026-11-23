// P2 ground layers (claude/hub_maps/engine_port_plan.md, section 5.2): the finished ground of a section as the old
// Rail Profiles page builds it (data/profile/profiles.html 636-712). The surveyed ground (the DEM), the Deck's street
// re-grades added and open cuts held (regradeGround 649), then other lines' drawn ground across their street and this
// line's own drawn ground lines (drawnGround 686): ground.layers.three, ground.deck_regrades, ground.drawn.tool,
// ground.drawn.counts_across_crossing_street. The surface (the pool over a river) and the bed (the canon bed under a
// river that has one) on the grid (surfaceAt 706, bedAt 710).
//
// Pure: every function returns new values and never changes its arguments (the page's normGnd and drawnGround
// changed S.align.gnd and S.gndCross in place). The layers are Float32Array as the page holds them, so a threshold
// on the ground falls the same way; surface and bed are Float64Array, as the page's surfaceAt and bedAt return the
// pool and the canon bed in double precision.

import { gridChainage, gridSize } from "../../grid.ts";
import { CM_PER_M, PORT_GND_MIN_LEN_M, SPAN_MIN_M, STREET_PAD_M } from "../../tol.ts";
import type { Align, ContextRecord, CrossGround, GroundLayers, PortDoc, PortInput, RiverRecord } from "../types.ts";
import { clamp } from "../util.ts";

/** A drawn ground point: chainage and level. */
export interface GndPoint {
  c: number;
  z: number;
}

/** A drawn ground line as the model holds it (Align["gnd"]). */
export type GndLine = readonly { readonly c: number; readonly z: number }[];

/** The ground at c on a grid of step, linear between samples and held at the ends; a NaN sample takes its
 * neighbour's value (sampleGround, 636-643). */
export function sampleGround(g: Float32Array, step: number, c: number): number {
  // the page's g.length - 1 is -1 on an empty array; the port answers NaN there, as station/ground.ts does
  if (g.length === 0) return Number.NaN;
  const f = clamp(c / step, 0, g.length - 1);
  const i = Math.floor(f);
  const t = f - i;
  const a = g[i] as number;
  const b = g[Math.min(i + 1, g.length - 1)] as number;
  if (Number.isNaN(a)) return b;
  if (Number.isNaN(b)) return a;
  return a + (b - a) * t;
}

/** The Deck's street re-grades (add, added) and open cuts (cap, the ground held at the trough floor) on the surveyed
 * ground (regradeGround, 649-657). The DEM itself when the context has neither. */
export function regradeGround(dem: Float32Array, ctx: Pick<ContextRecord, "add" | "cap">): Float32Array {
  if (!ctx.add.length && !ctx.cap.length) return dem;
  const out = Float32Array.from(dem);
  for (const r of ctx.add)
    r.v.forEach((v, k) => {
      const i = r.i0 + k;
      if (i < out.length && !Number.isNaN(out[i] as number)) out[i] = (out[i] as number) + v;
    });
  for (const r of ctx.cap)
    r.v.forEach((v, k) => {
      const i = r.i0 + k;
      if (i < out.length && !Number.isNaN(out[i] as number) && v < (out[i] as number)) out[i] = v;
    });
  return out;
}

/** A drawn line's level at c: straight grades between its points, held past its last (gndLevel, 667). */
export function gndLevel(P: GndLine, c: number): number {
  for (let k = 1; k < P.length; k++) {
    const b = P[k] as GndPoint;
    if (c <= b.c) {
      const a = P[k - 1] as GndPoint;
      return b.c - a.c < SPAN_MIN_M ? b.z : a.z + ((b.z - a.z) * (c - a.c)) / (b.c - a.c);
    }
  }
  return (P[P.length - 1] as GndPoint).z;
}

/** Lines of points kept as the page keeps them (parseGnd, 668-671): finite points sorted by c, at least two, over
 * PORT_GND_MIN_LEN_M long; the lines sorted by their first point. */
function cleanLines(lines: readonly (readonly GndPoint[])[]): GndPoint[][] {
  return lines
    .map((L) => L.filter((p) => Number.isFinite(p.c) && Number.isFinite(p.z)).sort((a, b) => a.c - b.c))
    .filter((P) => P.length >= 2 && (P[P.length - 1] as GndPoint).c - (P[0] as GndPoint).c > PORT_GND_MIN_LEN_M)
    .sort((a, b) => (a[0] as GndPoint).c - (b[0] as GndPoint).c);
}

/** The saved gnd ([c, z] points per line) as lines of points (parseGnd, 668-671). */
export function parseGnd(raw: PortDoc["gnd"] | null | undefined): GndPoint[][] {
  const lines: GndPoint[][] = [];
  for (const L of Array.isArray(raw) ? raw : []) {
    if (!Array.isArray(L)) continue;
    const P: GndPoint[] = [];
    for (const p of L as readonly unknown[]) {
      if (!Array.isArray(p) || p.length < 2) continue;
      const c = Number(p[0]);
      const z = Number(p[1]);
      // the page's isFinite(+p[0]): a null reads as 0, as there
      if (Number.isFinite(c) && Number.isFinite(z)) P.push({ c, z });
    }
    lines.push(P);
  }
  return cleanLines(lines);
}

/** Each line sorted, its two ends on the regraded ground below them to the centimetre (normGnd, 672). New lines. */
export function normGnd(lines: readonly GndLine[], regraded: Float32Array, step: number): GndPoint[][] {
  return lines.map((L) => {
    const P = L.map((p) => ({ c: p.c, z: p.z })).sort((a, b) => a.c - b.c);
    if (!P.length) return P;
    for (const p of [P[0] as GndPoint, P[P.length - 1] as GndPoint]) {
      const b = sampleGround(regraded, step, p.c);
      if (Number.isFinite(b)) p.z = Math.round(b * CM_PER_M) / CM_PER_M;
    }
    return P;
  });
}

/**
 * Other lines' drawn ground where they cross this line (crossGround, 674-685): for each crossing whose neighbour has
 * a drawn line over the crossing, that line's level at the crossing across the neighbour's Deck street (gndW where
 * it has none), centred on the crossing (ground.drawn.counts_across_crossing_street).
 */
export function crossGround(
  input: Pick<PortInput, "crossings" | "neighbours" | "section_id" | "route">,
  gndW: number,
): CrossGround[] {
  const out: CrossGround[] = [];
  for (const cr of input.crossings) {
    if (!cr.wid || cr.oc == null || cr.wid === input.route || (cr.other != null && cr.other === input.section_id))
      continue;
    const n = input.neighbours[cr.wid];
    if (!n?.gnd.length) continue;
    for (const P of cleanLines(n.gnd)) {
      if (cr.oc < (P[0] as GndPoint).c || cr.oc > (P[P.length - 1] as GndPoint).c) continue;
      const st = n.streets.find((r) => cr.oc >= r[0] - STREET_PAD_M && cr.oc <= r[1] + STREET_PAD_M);
      const [, , width, name] = st ?? [];
      const w = st ? (width as number) : gndW;
      out.push({
        c0: cr.c - w / 2,
        c1: cr.c + w / 2,
        z: gndLevel(P, cr.oc),
        wid: cr.wid,
        with: cr.with,
        street: st ? (name as string) : null,
        w,
      });
    }
  }
  return out;
}

/**
 * The finished ground (drawnGround, 686-696): the regraded ground with the other lines' drawn ground across their
 * street where this line has no drawn line of its own, then this line's drawn lines, each between its ends. NaN
 * samples (no survey) stay NaN. The base itself when there is nothing drawn.
 */
export function drawnGround(
  base: Float32Array,
  lines: readonly GndLine[],
  cross: readonly CrossGround[],
  step: number,
): Float32Array {
  if (!lines.length && !cross.length) return base;
  const out = Float32Array.from(base);
  const n = out.length;
  const set = (i: number, z: number): void => {
    if (i >= 0 && i < n && !Number.isNaN(out[i] as number)) out[i] = z;
  };
  const own = (c: number): boolean =>
    lines.some((P) => c >= (P[0] as GndPoint).c && c <= (P[P.length - 1] as GndPoint).c);
  for (const x of cross)
    for (let i = Math.ceil(x.c0 / step); i <= Math.floor(x.c1 / step); i++) if (!own(i * step)) set(i, x.z);
  for (const P of lines)
    for (let i = Math.ceil((P[0] as GndPoint).c / step); i <= Math.floor((P[P.length - 1] as GndPoint).c / step); i++)
      set(i, gndLevel(P, i * step));
  return out;
}

/** The first river whose range holds c, -1 for none (riverAt, 705). */
export function riverIndex(rivers: readonly { readonly c0: number; readonly c1: number }[], c: number): number {
  for (let k = 0; k < rivers.length; k++) {
    const r = rivers[k] as { c0: number; c1: number };
    if (c >= r.c0 && c <= r.c1) return k;
  }
  return -1;
}

/** riverIndex at every grid sample (SectionModel.riverAt). */
export function riverAtArray(
  rivers: readonly { readonly c0: number; readonly c1: number }[],
  length: number,
  step: number,
): Int16Array {
  const n = gridSize(length, step);
  const out = new Int16Array(n);
  for (let i = 0; i < n; i++) out[i] = riverIndex(rivers, gridChainage(i, step, length));
  return out;
}

/** The canon bed under a river, the pool less its bed depth where it has one, else null: the bed is the ground
 * (bedOf, 709). */
export function bedOf(r: Pick<RiverRecord, "bedBelowPool">, pool: number): number | null {
  return r.bedBelowPool != null ? pool - r.bedBelowPool : null;
}

/**
 * Every ground layer of a section from its input and the drawn lines (rebuildGround, 697-712, with alignFromDoc's
 * normGnd and drawnGround, 1875): dem, regraded, finished as long as the ground profile (one sample more than the
 * grid on most lines: sampleGround holds the last); surface and bed on the grid, from the first river at each c.
 */
export function rebuildGround(input: PortInput, gnd: Align["gnd"], rivers: readonly RiverRecord[]): GroundLayers {
  const step = input.step;
  const dem = input.dem;
  const regraded = regradeGround(dem, input.context);
  const lines = normGnd(gnd, regraded, step);
  const cross = crossGround(input, input.literals.GND_W);
  const finished = drawnGround(regraded, lines, cross, step);
  const n = gridSize(input.length, step);
  const pool = input.settings.pool;
  const surface = new Float64Array(n);
  const bed = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const c = gridChainage(i, step, input.length);
    const k = riverIndex(rivers, c);
    const g = sampleGround(finished, step, c);
    surface[i] = k >= 0 ? pool : g;
    const b = k >= 0 ? bedOf(rivers[k] as RiverRecord, pool) : null;
    bed[i] = b != null ? b : g;
  }
  return { step, dem, regraded, finished, surface, bed, lines, cross };
}
