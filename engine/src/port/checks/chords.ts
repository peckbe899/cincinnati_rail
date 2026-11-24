// The straight grades of the built line between its design vertices (chords 828), as the summary and the design
// checks read them (computeSummary 1915, designChecks 2083), and the sumps at the low points in tunnel (2111-2113).

import { PERMILLE, PORT_CHAINAGE_EPS_M, PORT_LEVEL_EQ_M, PORT_SUMP_FLAT } from "../../tol.ts";
import type { DesignVertex } from "../../vertical/design.ts";
import type { SectionModel, Type, TypedModel, TypesModule } from "../types.ts";

/** In tunnel for drainage, sumps and cover (TUNNEL, 2080). */
export const TUNNEL = new Set<Type>(["cutcover", "shield", "deep", "sunk"]);

/** A chord of the built line between two design vertices (designChecks 2083). */
export interface Chord {
  readonly a: DesignVertex;
  readonly b: DesignVertex;
  /** per mille */
  readonly g: number;
  /** a platform, or a platform's level transition */
  readonly plat: boolean;
}

/** The straight grades between the built line's vertices (chords 828; designChecks 2083). */
export function chordsOf(m: Pick<SectionModel, "rail">): Chord[] {
  const CV = m.rail.design.dv;
  const out: Chord[] = [];
  for (let k = 0; k < CV.length - 1; k++) {
    const a = CV[k] as DesignVertex;
    const b = CV[k + 1] as DesignVertex;
    if (!(b.c - a.c > PORT_CHAINAGE_EPS_M)) continue;
    const plat =
      (a.kind === "ps" && b.kind === "pe" && a.i === b.i) ||
      ((a.kind === "x" || b.kind === "x") && Math.abs(b.z - a.z) < PORT_LEVEL_EQ_M);
    out.push({ a, b, g: ((b.z - a.z) / (b.c - a.c)) * PERMILLE, plat });
  }
  return out;
}

/** The low points in tunnel that need a sump: a falling chord then a rising one (designChecks 2111-2113). */
export function sumpsOf(m: TypedModel, T: Pick<TypesModule, "typeAt">): number {
  let sumps = 0;
  let lastSign = 0;
  let lastC = 0;
  for (const sg of chordsOf(m)) {
    const sign = Math.abs(sg.g) < PORT_SUMP_FLAT ? 0 : Math.sign(sg.g);
    if (!sign) continue;
    if (lastSign < 0 && sign > 0 && TUNNEL.has(T.typeAt(m, (lastC + sg.a.c) / 2))) sumps++;
    lastSign = sign;
    lastC = sg.a.c;
  }
  return sumps;
}
