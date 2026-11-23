// What the checks read at a chainage from the model: the page's small lookups (stationAt 611, groundAt 645,
// groundAt0 646, riverAt 705, surfaceAt 706, bedAt 710, canonAt 1041, inStation 1042, inPlatform 3142, overrideAt
// 833, railAt 803, gradeAt 817). Private to P4: each package
// reads the model's data the same way (P1 at.ts, P2 canon.ts and layers.ts).

import { sampleGround } from "../../station/ground.ts";
import { gradeAt, railAt } from "../../vertical/rail.ts";
import type { CanonSection, LiveStation, RiverModel, SectionModel, Type } from "../types.ts";

export const isRer = (m: Pick<SectionModel, "input">): boolean => m.input.system === "rer";
export const halfPlatform = (m: Pick<SectionModel, "settings">): number => m.settings.platform / 2;

/** The rail of the drawn profile at c (railAt, 803). */
export const railOf = (m: Pick<SectionModel, "rail">, c: number): number => railAt(m.rail.design, c);
/** The grade at c, per mille (gradeAt, 817). */
export const gradeOf = (m: Pick<SectionModel, "rail">, c: number): number => gradeAt(m.rail.design, c);

/** The finished ground at c (groundAt 645; groundAt0 is the same ground once the line is loaded). */
export const groundAt = (m: Pick<SectionModel, "ground">, c: number): number =>
  sampleGround(m.ground.finished, m.ground.step, c);

/** The station whose platform covers c, half a platform either side of its centre (stationAt, 611). */
export function stationAt(
  m: Pick<SectionModel, "stations" | "settings">,
  c: number,
  tol: number = halfPlatform(m),
): LiveStation | null {
  return m.stations.find((s) => Math.abs(c - s.c) <= tol) ?? null;
}

/** inStation (1042). */
export const inStation = (m: Pick<SectionModel, "stations" | "settings">, c: number): boolean => !!stationAt(m, c);

/** Inside a platform and 2 m past its ends, for editing and the level solver's bend points (inPlatform, 3142). */
export function inPlatform(m: Pick<SectionModel, "stations" | "settings">, c: number): boolean {
  const half = halfPlatform(m);
  return m.stations.some((s) => c > s.c - half - 2 && c < s.c + half + 2);
}

/** The first river whose range holds c (riverAt, 705). */
export function riverAt(m: Pick<SectionModel, "rivers">, c: number): RiverModel | null {
  for (const r of m.rivers) if (c >= r.c0 && c <= r.c1) return r;
  return null;
}

/** The pool over a river, else the ground (surfaceAt, 706). */
export const surfaceAt = (m: Pick<SectionModel, "rivers" | "settings" | "ground">, c: number): number =>
  riverAt(m, c) ? m.settings.pool : groundAt(m, c);

/** The canon bed under a river that has one, else the ground (bedAt, 710). */
export function bedAt(m: Pick<SectionModel, "rivers" | "ground">, c: number): number {
  const r = riverAt(m, c);
  return r && r.bed != null ? r.bed : groundAt(m, c);
}

/** The canon method section at c, later sections winning (canonAt, 1041). */
export function canonAt(m: Pick<SectionModel, "canon">, c: number): CanonSection | null {
  const a = m.canon.sections;
  for (let k = a.length - 1; k >= 0; k--) {
    const s = a[k] as CanonSection;
    if (c >= s.lo && c <= s.hi) return s;
  }
  return null;
}

/** The paint the solver reads at c, the last range winning (overrideAt over effOvr, 833). */
export function overrideAt(m: Pick<SectionModel, "effOvr">, c: number): Type | null {
  const o = m.effOvr;
  for (let k = o.length - 1; k >= 0; k--) {
    const r = o[k] as (typeof o)[number];
    if (c >= r[0] && c <= r[1]) return r[2];
  }
  return null;
}
