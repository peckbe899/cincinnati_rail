// The platform curve (profiles.html 2008-2077): the drawn path over the platform resampled every 2 m and fitted
// with a circle by least squares, the extra platform gap for the car, and the turns inside the span (S-curves).
// Plan metres are the page's local ones (longitude times cos of the path's first latitude), so the radius is the
// one the page and tests/baseline/profiles/platforms.json give.

import type { StationParams } from "../contract/index.ts";
import { pathAt } from "../geom/path.ts";
import {
  DEG_HALF_TURN,
  DET_MIN,
  FIT_MIN_POINTS,
  KASA_QUARTER,
  M_PER_DEG_LAT,
  M_PER_DEG_LON,
  OUTSIDE_GAP_DIV,
  SPAN_EPS_M,
  SPAN_MIN_M,
  STRAIGHT_TOL_M,
} from "../tol.ts";

export type Path = readonly (readonly [number, number, number])[];

const clamp = (v: number, a: number, b: number): number => Math.max(a, Math.min(b, v));

function kx(path: Path): number {
  const lat0 = (((path[0] as readonly number[])[2] as number) * Math.PI) / DEG_HALF_TURN;
  return M_PER_DEG_LON * Math.cos(lat0);
}

function pathXY(path: Path, c: number): [number, number] {
  const [lon, lat] = pathAt(path, c);
  return [lon * kx(path), lat * M_PER_DEG_LAT];
}

const det = (M: number[][]): number => {
  const [a, b, c] = M as [number[], number[], number[]];
  return (
    (a[0] as number) * ((b[1] as number) * (c[2] as number) - (b[2] as number) * (c[1] as number)) -
    (a[1] as number) * ((b[0] as number) * (c[2] as number) - (b[2] as number) * (c[0] as number)) +
    (a[2] as number) * ((b[0] as number) * (c[1] as number) - (b[1] as number) * (c[0] as number))
  );
};

/** The radius of a least-squares (Kasa) circle through the points; Infinity when straight (fitRadius, 2011). */
export function fitRadius(pts: readonly [number, number][]): number {
  const n = pts.length;
  if (n < FIT_MIN_POINTS) return Number.POSITIVE_INFINITY;
  let mx = 0;
  let my = 0;
  for (const [x, y] of pts) {
    mx += x / n;
    my += y / n;
  }
  const P = pts.map(([x, y]) => [x - mx, y - my] as const);
  const [x0, y0] = P[0] as readonly [number, number];
  const [x1, y1] = P[n - 1] as readonly [number, number];
  const L = Math.hypot(x1 - x0, y1 - y0) || 1;
  const off = Math.max(...P.map(([x, y]) => Math.abs((x1 - x0) * (y0 - y) - (x0 - x) * (y1 - y0)) / L));
  if (off < STRAIGHT_TOL_M) return Number.POSITIVE_INFINITY;
  let Sxx = 0;
  let Sxy = 0;
  let Syy = 0;
  let Sx = 0;
  let Sy = 0;
  let Sxz = 0;
  let Syz = 0;
  let Sz = 0;
  for (const [x, y] of P) {
    const z = x * x + y * y;
    Sxx += x * x;
    Sxy += x * y;
    Syy += y * y;
    Sx += x;
    Sy += y;
    Sxz += x * z;
    Syz += y * z;
    Sz += z;
  }
  const A = [
    [Sxx, Sxy, Sx],
    [Sxy, Syy, Sy],
    [Sx, Sy, n],
  ];
  const B = [-Sxz, -Syz, -Sz];
  const dA = det(A);
  if (Math.abs(dA) < DET_MIN) return Number.POSITIVE_INFINITY;
  const col = (k: number): number[][] => A.map((r, i) => r.map((v, j) => (j === k ? (B[i] as number) : v)));
  const D = det(col(0)) / dA;
  const E = det(col(1)) / dA;
  const F = det(col(2)) / dA;
  const r2 = (D * D + E * E) / KASA_QUARTER - F;
  return r2 > 0 ? Math.sqrt(r2) : Number.POSITIVE_INFINITY;
}

/** The turn at each vertex of the path, degrees, left positive (pathTurns, 2048). */
export function pathTurns(path: Path): number[] {
  const k = kx(path);
  const xy = path.map((q) => [(q[1] as number) * k, (q[2] as number) * M_PER_DEG_LAT] as const);
  const n = xy.length;
  const dfl = new Array<number>(n).fill(0);
  for (let i = 1; i + 1 < n; i++) {
    const p = xy[i - 1] as readonly [number, number];
    const q = xy[i] as readonly [number, number];
    const r = xy[i + 1] as readonly [number, number];
    const ax = q[0] - p[0];
    const ay = q[1] - p[1];
    const bx = r[0] - q[0];
    const by = r[1] - q[1];
    dfl[i] = (Math.atan2(ax * by - ay * bx, ax * bx + ay * by) * DEG_HALF_TURN) / Math.PI;
  }
  return dfl;
}

export interface Curve {
  R_m: number | null;
  out_m: number;
  inn_m: number;
  level: "error" | "warning" | null;
  gapfill: boolean;
  turns: { pos: number; neg: number; s: "error" | "warning" | null };
}

/** The platform curve of the platform centred at c (platformCurve 2030, platformTurns 2072). */
export function platformCurve(
  path: Path,
  dfl: readonly number[],
  length: number,
  c: number,
  p: StationParams,
  gapfill: boolean,
): Curve {
  const half = p.platform_m / 2;
  const a = clamp(c - half, 0, length);
  const b = clamp(c + half, 0, length);
  const pts: [number, number][] = [];
  for (let q = a; q <= b + SPAN_EPS_M; q += 2) pts.push(pathXY(path, q));
  if (b - a > SPAN_MIN_M && (b - a) % 2 > SPAN_MIN_M) pts.push(pathXY(path, b));
  const R = path.length >= 2 ? fitRadius(pts) : Number.POSITIVE_INFINITY;
  const finite = Number.isFinite(R);
  const out = finite ? (p.car_len_m * p.car_len_m) / (OUTSIDE_GAP_DIV * R) : 0;
  const inn = finite ? (p.end_door_m * p.end_door_m) / (2 * R) : 0;
  const level = R < p.plat_r_err_m ? "error" : R < p.plat_r_warn_m ? "warning" : null;
  let pos = 0;
  let neg = 0;
  for (let k = 1; k + 1 < path.length; k++) {
    const ck = (path[k] as readonly number[])[0] as number;
    if (ck > c - half && ck < c + half) {
      const t = dfl[k] as number;
      if (t > 0) pos += t;
      else neg += t;
    }
  }
  const lo = Math.min(pos, -neg);
  const s = lo >= p.s_err_deg ? "error" : lo >= p.s_warn_deg ? "warning" : null;
  return { R_m: finite ? R : null, out_m: out, inn_m: inn, level, gapfill, turns: { pos, neg, s } };
}
