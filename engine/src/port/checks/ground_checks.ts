// The drawn ground against its limits, and the crossing lines' ground on this line (gndChecks 1731-1754;
// ground.drawn.limits, ground.drawn.counts_across_crossing_street): a side slope at either end at most fillSlope (an
// embankment), a grade between at most groundMax (a street), groundWarn sustained over groundSustain a warning; and
// a note for each other line's drawn ground laid across this line.

import {
  LIMIT_TOL,
  PERMILLE,
  PORT_CHAINAGE_EPS_M,
  PORT_GND_SLOPE_TOL,
  PORT_GND_SUSTAIN_MIN_POINTS,
} from "../../tol.ts";
import type { PortFlag, SectionModel } from "../types.ts";

type Pt = { readonly c: number; readonly z: number };

/** The level of a drawn line at c, straight between its points, held past its ends (gndLevel, 667). */
export function gndLevel(P: readonly Pt[], c: number): number {
  for (let k = 1; k < P.length; k++) {
    const b = P[k] as Pt;
    if (c <= b.c) {
      const a = P[k - 1] as Pt;
      return b.c - a.c < PORT_CHAINAGE_EPS_M ? b.z : a.z + ((b.z - a.z) * (c - a.c)) / (b.c - a.c);
    }
  }
  return (P[P.length - 1] as Pt).z;
}

/** gndChecks (1731-1754) on the model's drawn lines (align.gnd) and the other lines' ground across it. */
export function gndChecks(m: Pick<SectionModel, "align" | "settings" | "grid" | "ground">): PortFlag[] {
  const out: PortFlag[] = [];
  const S = m.settings;
  const step = m.grid.step;
  const slope = S.fillSlope;
  const flag = (
    kind: string,
    sev: PortFlag["sev"],
    c0: number,
    c1: number,
    data: Record<string, unknown>,
  ): PortFlag => ({
    kind,
    page: "Ground",
    sev,
    c0,
    c1,
    c: (c0 + c1) / 2,
    rule: kind === "ground_from_crossing" ? "ground.drawn.counts_across_crossing_street" : "ground.drawn.limits",
    data,
  });
  m.align.gnd.forEach((P, line) => {
    for (let k = 1; k < P.length; k++) {
      const a = P[k - 1] as Pt;
      const b = P[k] as Pt;
      const L = b.c - a.c;
      if (L < PORT_CHAINAGE_EPS_M) continue;
      const g = ((b.z - a.z) / L) * PERMILLE;
      const end = k === 1 || k === P.length - 1;
      if (end && Math.abs(g) > slope + PORT_GND_SLOPE_TOL)
        out.push(flag("ground_end_slope", "error", a.c, b.c, { line, g, limit: slope }));
      else if (!end && Math.abs(g) > S.groundMax + LIMIT_TOL)
        out.push(flag("ground_steep", "error", a.c, b.c, { line, g, limit: S.groundMax }));
    }
    // sustained: between the end slopes, averaged over groundSustain
    if (P.length < PORT_GND_SUSTAIN_MIN_POINTS) return;
    const c0 = (P[1] as Pt).c;
    const c1 = (P[P.length - 2] as Pt).c;
    const Ls = S.groundSustain;
    if (c1 - c0 < Ls) return;
    let run: { a: number; b: number; g: number } | null = null;
    const flush = (): void => {
      if (run)
        out.push(flag("ground_sustained", "warn", run.a, run.b, { line, g: run.g, over: Ls, limit: S.groundWarn }));
      run = null;
    };
    for (let c = c0; c + Ls <= c1 + PORT_CHAINAGE_EPS_M; c += step) {
      const g = ((gndLevel(P, c + Ls) - gndLevel(P, c)) / Ls) * PERMILLE;
      if (Math.abs(g) > S.groundWarn + LIMIT_TOL) {
        const r = run as { a: number; b: number; g: number } | null;
        if (r && c <= r.b) {
          r.b = c + Ls;
          if (Math.abs(g) > Math.abs(r.g)) r.g = g;
        } else {
          flush();
          run = { a: c, b: c + Ls, g };
        }
      }
    }
    flush();
  });
  for (const x of m.ground.cross)
    out.push(
      flag("ground_from_crossing", "info", x.c0, x.c1, {
        z: x.z,
        wid: x.wid,
        with: x.with,
        street: x.street,
        w: x.w,
      }),
    );
  return out;
}
