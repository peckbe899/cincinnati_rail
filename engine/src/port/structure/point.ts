// One chainage on its own (pointType 1246-1276), the station approaches' length (approachExtra 1293, approachLen
// 1294) and the sliver absorber (absorbShort 1299-1317). P1b.

import {
  PORT_ABSORB_PASSES,
  PORT_APPROACH_EXTRA_MATCH_M,
  PORT_REVERSE_CURVE_FACTOR,
  PORT_STATION_POINT_M,
} from "../../tol.ts";
import type { Approach, PointType, SectionModel, Type } from "../types.ts";
import { canonAt, groundAt, isRer, railOf, riverAt, stationAt, surfaceAt } from "./at.ts";
import { methodAt, metroTube, phaseAt, phaseRecord, phaseRules } from "./phase.ts";
import { drivenStruct, reqCover } from "./structure.ts";

/**
 * pointType (1246-1276): the type of one chainage on its own, or for a Metro tunnel point outside the canon its
 * class: C too shallow to bore, E either, B past the cut-and-cover limit. Every point of a platform takes the
 * platform centre's (a station is one type, station.type.selection_else_limit). A river: bridged when the rail
 * stands bridgeAbovePool over the pool, else the sunk box (structure.sunk_box.river_beats_paint). Read after a
 * solve, the shield's structure is the drive's tube (drivenTube), as on the page.
 */
export function pointType(m: SectionModel, c: number, z: number): PointType {
  const S = m.settings;
  const lit = m.literals;
  {
    const st = stationAt(m, c);
    if (st && Math.abs(c - st.c) > PORT_STATION_POINT_M) {
      const q = pointType(m, st.c, railOf(m, st.c));
      return "cls" in q ? { ...q } : { ...q, stn: true };
    }
  }
  const bridged = (): boolean => z >= S.pool + lit.bridgeAbovePool;
  const r = riverAt(m, c);
  if (r && !r.alongShore) return { t: bridged() ? "elevated" : "sunk" };
  const sec0 = canonAt(m, c);
  if (sec0 && sec0.m === "covered") {
    const s0 = surfaceAt(m, c);
    return { t: Number.isFinite(s0) && z - s0 >= S.elevAbove ? "elevated" : "cutcover" };
  }
  if (r) return { t: bridged() ? "elevated" : "deep" };
  const g = groundAt(m, c);
  if (!Number.isFinite(g)) return { t: "atgrade" };
  if (z - g >= S.elevAbove) return { t: "elevated" };
  const d = g - z;
  if (d < S.coverBelow) return { t: "atgrade" };
  // portal ramps: rail less than a box height down is an open trough
  const boxTop = isRer(m) ? (S.rer?.envelope ?? 0) : (m.tables?.box.top ?? 0);
  if (d < boxTop) return { t: "trough" };
  const sec = canonAt(m, c);
  if (!sec && !isRer(m) && m.structure) {
    const ph = phaseAt(m, c);
    const R = phaseRules(m, c, ph);
    const tube = metroTube(m, c);
    const shieldFrom = tube.top + (tube.od ?? 0);
    const st = stationAt(m, c);
    if (st) {
      // a station by its depth at the platform centre against the cut-and-cover limit
      const gs = groundAt(m, st.c);
      const ds = Number.isFinite(gs) ? gs - railOf(m, st.c) : d;
      return { t: ds <= R.ccMax ? "cutcover" : methodAt(m, c, ph), stn: true };
    }
    return { cls: d < shieldFrom ? "C" : d > R.ccMax ? "B" : "E", d, deep: d >= R.deepFrom, ph, R, shieldFrom };
  }
  const meth = sec ? sec.m : d >= S.deepBelow ? "deep" : "shallow";
  if (meth === "canal") return { t: "cutcover" };
  // too shallow to bore: built cut and cover
  if (isRer(m)) {
    const rer = S.rer;
    if (rer && d < rer.boreCrown + rer.minCover) return { t: "cutcover" };
  } else {
    const sc = drivenStruct(m, meth === "deep" ? "deep" : "shield", c);
    if (d - sc.top < reqCover(m, sc)) return { t: "cutcover" };
  }
  if (meth === "deep") return { t: "deep" };
  return { t: stationAt(m, c) ? "cutcover" : "shield" };
}

/** The type a point class is drawn as off the solved profile (autoType 1608): B bored by the phase's method, else
 * cut and cover. */
export function pointTypeOf(m: SectionModel, c: number, q: PointType): Type {
  if ("t" in q) return q.t;
  return q.cls === "B" ? methodAt(m, c) : "cutcover";
}

/** The phase's minimum radius at c (minRadiusAt 1292). */
export function minRadiusAt(m: SectionModel, c: number): number {
  const p = phaseRecord(m, phaseAt(m, c));
  return p?.min_radius || m.structure?.min_radius || m.literals.minRadiusFallback;
}

/** approachExtra (1293): a straight after a platform or box end where no arc fits, from approach_extra
 * (station.approach.straight_where_no_arc). */
export function approachExtra(m: SectionModel, info: Pick<Approach, "station" | "side" | "c">): number {
  const e = m.input.approachExtra.find(
    (x) =>
      x.side === info.side &&
      (info.station ? x.station === info.station : !x.station && Math.abs(x.c - info.c) < PORT_APPROACH_EXTRA_MATCH_M),
  );
  return e ? e.extra : 0;
}

/** approachLen (1294): L = max(approach_m, sqrt(4 x min_radius x shift per track)), plus the straight where no
 * arc fits (structure.approach.spacing_change_in_box). */
export function approachLen(
  m: SectionModel,
  shift: number,
  c: number,
  info: Pick<Approach, "station" | "side" | "c"> | null,
): number {
  const am = m.structure?.approach_m || m.literals.approachFallback;
  return (
    Math.max(am, Math.sqrt(PORT_REVERSE_CURVE_FACTOR * minRadiusAt(m, c) * Math.abs(shift))) +
    (info ? approachExtra(m, info) : 0)
  );
}

/**
 * absorbShort (1299-1317): no stretch shorter than minRun between two others; it takes the type of the longer
 * neighbour (both the same: that one), when every sample of it is free, both neighbours' edges may give their type
 * and every sample can take it (else the other neighbour's; geometry.sliver.absorb_only_if_buildable). Four passes.
 * Mutates its own work array only.
 */
export function absorbShort<P extends { c: number; t: Type | undefined }>(
  P: P[],
  step: number,
  minRun: number,
  free: (p: P) => boolean,
  edgeOk: (q: P) => boolean = () => true,
  canTake: (p: P, t: Type | undefined) => boolean = () => true,
): void {
  for (let pass = 0; pass < PORT_ABSORB_PASSES; pass++) {
    const R: [number, number][] = [];
    let a = 0;
    for (let i = 1; i <= P.length; i++)
      if (i === P.length || (P[i] as P).t !== (P[a] as P).t) {
        R.push([a, i - 1]);
        a = i;
      }
    let changed = false;
    for (let k = 1; k + 1 < R.length; k++) {
      const [x, y] = R[k] as [number, number];
      const L = (y - x + 1) * step;
      if (L >= minRun) continue;
      const part = P.slice(x, y + 1);
      if (!part.every(free)) continue;
      const [px, py] = R[k - 1] as [number, number];
      const [nx, ny] = R[k + 1] as [number, number];
      const prev = (P[px] as P).t;
      const next = (P[nx] as P).t;
      if (!edgeOk(P[py] as P) || !edgeOk(P[nx] as P)) continue;
      let t = prev === next ? prev : py - px >= ny - nx ? prev : next;
      if (!part.every((p) => canTake(p, t))) {
        t = t === prev ? next : prev;
        if (prev === next || !part.every((p) => canTake(p, t))) continue;
      }
      for (let i = x; i <= y; i++) (P[i] as P).t = t;
      changed = true;
    }
    if (!changed) break;
  }
}
