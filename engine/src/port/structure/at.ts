// What the structure solver reads at a chainage from the normalised model: the page's small lookups (stationAt 611,
// groundAt 645, riverAt 705, surfaceAt 706, canonAt 1041, streetAtC 452, subwayStreet 456, pieceAt 2059,
// lockedStation 912, railAt 803). Private to P1: the other packages have their own (P2 owns canonAt and riverIndex,
// P3 the streets), and these read the model's data the same way.

import { sampleGround } from "../../station/ground.ts";
import { PORT_PIECE_PAD_M, STREET_PAD_M } from "../../tol.ts";
import { railAt } from "../../vertical/rail.ts";
import type { CanonSection, LiveStation, Lock, RiverModel, SectionModel, Street } from "../types.ts";

export const isRer = (m: Pick<SectionModel, "input">): boolean => m.input.system === "rer";
export const halfPlatform = (m: Pick<SectionModel, "settings">): number => m.settings.platform / 2;

/** The rail of the drawn profile at c (railAt, 803). */
export const railOf = (m: Pick<SectionModel, "rail">, c: number): number => railAt(m.rail.design, c);

/** The finished ground at c (groundAt, 645). */
export const groundAt = (m: Pick<SectionModel, "ground" | "grid">, c: number): number =>
  sampleGround(m.ground.finished, m.grid.step, c);

/** The station whose platform covers c, half a platform either side of its centre (stationAt, 611). */
export function stationAt(
  m: Pick<SectionModel, "stations" | "settings">,
  c: number,
  tol: number = halfPlatform(m),
): LiveStation | null {
  return m.stations.find((s) => Math.abs(c - s.c) <= tol) ?? null;
}

/** The first river whose range holds c (riverAt, 705). */
export function riverAt(m: Pick<SectionModel, "rivers">, c: number): RiverModel | null {
  for (const r of m.rivers) if (c >= r.c0 && c <= r.c1) return r;
  return null;
}

/** The pool over a river, else the ground (surfaceAt, 706). */
export const surfaceAt = (m: Pick<SectionModel, "rivers" | "settings" | "ground" | "grid">, c: number): number =>
  riverAt(m, c) ? m.settings.pool : groundAt(m, c);

/** The canon method section at c, later sections winning (canonAt, 1041). */
export function canonAt(m: Pick<SectionModel, "canon">, c: number): CanonSection | null {
  const a = m.canon.sections;
  for (let k = a.length - 1; k >= 0; k--) {
    const s = a[k] as CanonSection;
    if (c >= s.lo && c <= s.hi) return s;
  }
  return null;
}

/** A locked stretch that holds a level for station i (lockedStation, 912). */
export function lockedStation(m: Pick<SectionModel, "canon" | "stations">, i: number): Lock | null {
  const s = m.stations[i];
  if (!s) return null;
  return m.canon.locks.find((lk) => typeof lk.st[s.name] === "number") ?? null;
}

/** The context street the line runs along at c, 5 m past its ends (streetAtC, 452). */
export function streetAtC(m: Pick<SectionModel, "input">, c: number): Street | null {
  return m.input.context.streets.find((r) => c >= r[0] - STREET_PAD_M && c <= r[1] + STREET_PAD_M) ?? null;
}

/** A street built over the subway (subwayStreet, 456): its name holds one of the record's subway_streets. */
export function subwayStreet(m: Pick<SectionModel, "structure">, name: string): boolean {
  const s = m.structure;
  if (!s) return false;
  const low = String(name).toLowerCase();
  return s.subway_streets.some((k) => low.includes(String(k).toLowerCase()));
}

/** The drawn piece at c, 5 m past its ends, '' for none (pieceAt, 2059). */
export function pieceAt(m: Pick<SectionModel, "input">, c: number): string {
  return m.input.pieces.find((q) => c >= q.c0 - PORT_PIECE_PAD_M && c <= q.c1 + PORT_PIECE_PAD_M)?.name ?? "";
}
