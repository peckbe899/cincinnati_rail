// The drawing checks on the drawn path (drawingFlags 2048-2071, network.drawing.corner_checks): the KMZ is straight
// segments with corners, and a finished curve is drawn as a run of vertices each turning a little. Flagged: a path
// doubling back (a turn over DRAW.back), a join kink (a turn of DRAW.kink or more beside a segment under
// DRAW.kinkSeg, where drawn pieces do not meet), and a single-angle corner (a bend drawn as one vertex turning
// DRAW.single or more with no neighbour turning the same way by DRAW.nb). The page runs it on the Metro only (2097).

import type { PathPoint } from "../../geom/path.ts";
import { pathTurns } from "../../station/curve.ts";
import { DEG_HALF_TURN, M_PER_DEG_LAT, M_PER_DEG_LON, PORT_PIECE_PAD_M } from "../../tol.ts";
import type { PortFlag, PortInput, PortLiterals } from "../types.ts";

/** The length of each segment of the path in the page's local plan metres (pathTurns seg, 2052). */
function segments(path: readonly PathPoint[]): number[] {
  const lat0 = ((path[0] as PathPoint)[2] * Math.PI) / DEG_HALF_TURN;
  const kx = M_PER_DEG_LON * Math.cos(lat0);
  const out: number[] = [];
  for (let i = 0; i + 1 < path.length; i++) {
    const a = path[i] as PathPoint;
    const b = path[i + 1] as PathPoint;
    out.push(Math.hypot(b[1] * kx - a[1] * kx, b[2] * M_PER_DEG_LAT - a[2] * M_PER_DEG_LAT));
  }
  return out;
}

/** The drawn piece at c, 5 m past its ends, '' for none (pieceAt, 2059). */
const pieceAt = (pieces: PortInput["pieces"], c: number): string =>
  pieces.find((q) => c >= q.c0 - PORT_PIECE_PAD_M && c <= q.c1 + PORT_PIECE_PAD_M)?.name ?? "";

/** drawingFlags (2060-2071): each flagged vertex with its turn, the shorter segment beside it and its place. */
export function drawingFlags(
  path: readonly PathPoint[],
  pieces: PortInput["pieces"],
  lit: Pick<PortLiterals, "DRAW">,
): PortFlag[] {
  const out: PortFlag[] = [];
  if (!path.length) return out;
  const D = lit.DRAW;
  const dfl = pathTurns(path);
  const seg = segments(path);
  const last = path.length - 1;
  for (let i = 1; i < last; i++) {
    const p = path[i] as PathPoint;
    const t = dfl[i] as number;
    const a = Math.abs(t);
    const c = p[0];
    const near = Math.min(seg[i - 1] as number, seg[i] as number);
    const data = { angle: a, turn: t, lon: p[1], lat: p[2], piece: pieceAt(pieces, c) };
    const flag = (kind: string, sev: PortFlag["sev"], extra: Record<string, unknown> = {}): PortFlag => ({
      kind,
      page: "Drawing",
      sev,
      c0: c,
      c1: c,
      c,
      rule: "network.drawing.corner_checks",
      data: { ...data, ...extra },
    });
    if (a > D.back) out.push(flag("path_doubles_back", "error"));
    else if (a >= D.kink && near < D.kinkSeg) out.push(flag("path_kink", "error", { seg: near }));
    else if (
      a >= D.single &&
      [i - 1, i + 1].every((j) => {
        if (j <= 0 || j >= last) return true;
        const u = dfl[j] as number;
        return !(Math.abs(u) >= D.nb && Math.sign(u) === Math.sign(t));
      })
    )
      out.push(flag("single_angle_corner", "warn"));
  }
  return out;
}
