// Plan paths with chainage: cumulative length and lookup by bisection (the port of pathAt, profiles.html 617).
//
// A path is a list of points [c, x, y] whose chainage c does not decrease along it, as the line files hold them
// ([c, lon, lat]). The page found the segment of a chainage by scanning from the start; pathAt here bisects and
// gives the same point (test/property.test.ts checks the two agree on random paths).

/** A path point: chainage, then the two plan coordinates. */
export type PathPoint = readonly [c: number, x: number, y: number];

const clamp = (v: number, a: number, b: number): number => Math.max(a, Math.min(b, v));

/** The cumulative planar length at each vertex of a polyline of [x, y] points, starting at 0. */
export function cumulativeLength(xy: readonly (readonly [number, number])[]): Float64Array {
  const out = new Float64Array(xy.length);
  for (let i = 1; i < xy.length; i++) {
    const a = xy[i - 1] as readonly [number, number];
    const b = xy[i] as readonly [number, number];
    out[i] = (out[i - 1] as number) + Math.hypot(b[0] - a[0], b[1] - a[1]);
  }
  return out;
}

/**
 * The first index j in [lo, hi] with key(j) >= c, or hi when there is none: what the page's scan
 * `while (j < hi && key(j) < c) j++` stops at, found by bisection. key must not decrease over [lo, hi].
 */
export function lowerBound(key: (j: number) => number, c: number, lo: number, hi: number): number {
  let a = lo;
  let b = hi;
  while (a < b) {
    const m = (a + b) >> 1;
    if (key(m) < c) a = m + 1;
    else b = m;
  }
  return a;
}

/** The segment index j (1 to n - 1) the page's pathAt reads for chainage c: path[j - 1] to path[j]. */
export function segmentAt(path: readonly PathPoint[], c: number): number {
  return lowerBound((j) => (path[j] as PathPoint)[0], c, 1, path.length - 1);
}

/** The plan position [x, y] at chainage c on a path of [c, x, y], held at the ends (pathAt, profiles.html 617). */
export function pathAt(path: readonly PathPoint[], c: number): [number, number] {
  if (path.length === 0) throw new RangeError("pathAt needs a path of at least one point");
  if (path.length === 1) {
    const p = path[0] as PathPoint;
    return [p[1], p[2]];
  }
  const j = segmentAt(path, c);
  const a = path[j - 1] as PathPoint;
  const b = path[j] as PathPoint;
  const t = b[0] - a[0] > 0 ? clamp((c - a[0]) / (b[0] - a[0]), 0, 1) : 0;
  return [a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}
