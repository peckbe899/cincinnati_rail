// The parts of the sheet a drag step changes (speed). A bend point or a station level dragged moves the rail only
// between the bend points either side, so a frame of the drag draws again only there: the rail's changed stretch
// with a margin for its labels, the strips under the plot, the readout at the pointer and the cursor line. The
// rest of the canvas keeps the last frame's pixels. Each such frame checks itself: every mark or text a band
// reported that changed must lie inside the regions drawn, else the frame is drawn whole (a label thinned away far
// off, a readout that grew).

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** The first and last index where two rails differ by more than eps, or null when they are the same. */
export function railSpan(a: ArrayLike<number>, b: ArrayLike<number>, eps = 1e-9): [number, number] | null {
  if (a.length !== b.length) return [0, Math.max(a.length, b.length) - 1];
  let i0 = -1;
  let i1 = -1;
  for (let i = 0; i < a.length; i++) {
    const x = a[i] as number;
    const y = b[i] as number;
    if (Math.abs(x - y) > eps || Number.isNaN(x) !== Number.isNaN(y)) {
      if (i0 < 0) i0 = i;
      i1 = i;
    }
  }
  return i0 < 0 ? null : [i0, i1];
}

/** A rect grown by m on every side, cut to the canvas and to whole pixels (no half-covered pixel at its edge). */
export function grow(r: Rect, m: number, w: number, h: number): Rect | null {
  const x0 = Math.max(0, Math.floor(r.x - m));
  const y0 = Math.max(0, Math.floor(r.y - m));
  const x1 = Math.min(w, Math.ceil(r.x + r.w + m));
  const y1 = Math.min(h, Math.ceil(r.y + r.h + m));
  return x1 > x0 && y1 > y0 ? { x: x0, y: y0, w: x1 - x0, h: y1 - y0 } : null;
}

/** The smallest rect holding them all: one plain rect clips cheaply (a union of rects made Skia's software raster
 * three times slower than drawing the frame whole), so a frame draws its regions as one box. */
export function bbox(rects: readonly Rect[]): Rect | null {
  if (!rects.length) return null;
  const x0 = Math.min(...rects.map((r) => r.x));
  const y0 = Math.min(...rects.map((r) => r.y));
  const x1 = Math.max(...rects.map((r) => r.x + r.w));
  const y1 = Math.max(...rects.map((r) => r.y + r.h));
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}

const inside = (x0: number, x1: number, y0: number, y1: number, rects: readonly Rect[]) =>
  rects.some((r) => x0 >= r.x && x1 <= r.x + r.w && y0 >= r.y && y1 <= r.y + r.h);

/** Where an item a band reported lies (CSS px), from its own box or point, else from its chainage; null when it
 * says neither. A text's label may run past its anchor (a name is drawn rotated up to the right), so a text whose
 * words, place or showing changed is taken TEXT_REACH wide (a station's rotated name; any other label LABEL_REACH,
 * a grade or a clearance written level at its place); one whose level alone changed, at its anchor. */
export const TEXT_REACH = 240;
export const LABEL_REACH = 60;
function boxOf(
  o: Record<string, unknown>,
  xOf: (c: number) => number,
  text: boolean,
): [number, number, number, number] | null {
  const n = (k: string) => (typeof o[k] === "number" && Number.isFinite(o[k] as number) ? (o[k] as number) : null);
  const reach = o.kind === "station" ? TEXT_REACH : LABEL_REACH;
  const label = o.label as Record<string, unknown> | undefined;
  if (label && typeof label === "object") {
    const inner = boxOf(label, xOf, false);
    if (inner) return inner;
  }
  let x0 = n("x0");
  let x1 = n("x1");
  if (x0 === null || x1 === null) {
    const x = n("x");
    if (x !== null) [x0, x1] = text ? [x - reach, x + reach] : [x - 12, x + 12];
    else {
      const c0 = n("c0") ?? n("c");
      const c1 = n("c1") ?? n("c");
      if (c0 === null || c1 === null) return null;
      [x0, x1] = [Math.min(xOf(c0), xOf(c1)) - (text ? reach : 12), Math.max(xOf(c0), xOf(c1)) + (text ? reach : 12)];
    }
  }
  const y0 = n("y0") ?? (n("y") !== null ? (n("y") as number) - (text ? reach : 12) : null);
  const y1 = n("y1") ?? (n("y") !== null ? (n("y") as number) + 12 : null);
  return [x0, x1, y0 ?? Number.NEGATIVE_INFINITY, y1 ?? Number.POSITIVE_INFINITY];
}

/**
 * Whether a frame drawn only in rects shows what the bands reported: the same items in the same order, and every
 * one that changed (in either frame) inside the rects. Items without a place are taken as changed anywhere.
 */
export function heldInside(
  before: readonly object[],
  after: readonly object[],
  rects: readonly Rect[],
  xOf: (c: number) => number,
  text: boolean,
): boolean {
  if (before.length !== after.length) return false;
  for (let i = 0; i < after.length; i++) {
    const a = before[i] as Record<string, unknown>;
    const b = after[i] as Record<string, unknown>;
    if (a === b) continue;
    if (JSON.stringify(a) === JSON.stringify(b)) continue;
    // a text whose level alone moved (its words may carry the level; its leader, bar and level tag move, its label
    // stays where it was) is a point at its anchor
    const levelOnly =
      text && a.drawn === b.drawn && a.selected === b.selected && a.x === b.x && a.c === b.c && a.kind === b.kind;
    for (const o of [a, b]) {
      const box = boxOf(o, xOf, text && !levelOnly);
      if (!box) return false;
      const [x0, x1, y0, y1] = box;
      // an item with no height (a chainage only) must lie inside a rect the canvas's whole height
      if (!inside(x0, x1, Number.isFinite(y0) ? y0 : 0, Number.isFinite(y1) ? y1 : 0, rects)) return false;
    }
  }
  return true;
}
