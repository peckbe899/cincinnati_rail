// Chainage on the map (plan section 7: "a chainage readout everywhere"): a section's path holds [c, lon, lat]
// points with c rising, so a chainage has a place on the map and a place on the map has the nearest chainage of
// the line. Plain geometry in a local metric (metres east and north of the point asked about), close enough for a
// readout and a marker; the section's own chainage stays the record's.

export type PathPoint = [number, number, number];

const M_PER_DEG = 111_320;

/** The lon and lat at chainage c along a path, by linear interpolation; null off the path's ends. */
export function pointAt(path: readonly PathPoint[], c: number): [number, number] | null {
  if (path.length === 0) return null;
  const first = path[0] as PathPoint;
  const last = path[path.length - 1] as PathPoint;
  if (c < first[0] || c > last[0]) return null;
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1] as PathPoint;
    const b = path[i] as PathPoint;
    if (c <= b[0]) {
      const t = b[0] === a[0] ? 0 : (c - a[0]) / (b[0] - a[0]);
      return [a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2])];
    }
  }
  return [last[1], last[2]];
}

/** The chainage of the path nearest a point, and how far the point is from the path in metres. */
export function nearestChainage(
  path: readonly PathPoint[],
  lon: number,
  lat: number,
): { c: number; off_m: number } | null {
  if (path.length === 0) return null;
  const kx = M_PER_DEG * Math.cos((lat * Math.PI) / 180);
  const ky = M_PER_DEG;
  let best: { c: number; off_m: number } | null = null;
  const local = (p: PathPoint): [number, number] => [(p[1] - lon) * kx, (p[2] - lat) * ky];
  if (path.length === 1) {
    const [x, y] = local(path[0] as PathPoint);
    return { c: (path[0] as PathPoint)[0], off_m: Math.hypot(x, y) };
  }
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1] as PathPoint;
    const b = path[i] as PathPoint;
    const [ax, ay] = local(a);
    const [bx, by] = local(b);
    const dx = bx - ax;
    const dy = by - ay;
    const len2 = dx * dx + dy * dy;
    const t = len2 === 0 ? 0 : Math.max(0, Math.min(1, -(ax * dx + ay * dy) / len2));
    const off = Math.hypot(ax + t * dx, ay + t * dy);
    if (!best || off < best.off_m) best = { c: a[0] + t * (b[0] - a[0]), off_m: off };
  }
  return best;
}

/** The line a station record belongs to, from its old key ("Line_3|Bond Hill" is on Line 3). */
export function stationLine(key: unknown): string | null {
  if (typeof key !== "string" || !key.includes("|")) return null;
  return (key.split("|")[0] as string).replace(/_/g, " ");
}
