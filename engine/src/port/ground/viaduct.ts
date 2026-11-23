// P2 viaducts (claude/hub_maps/engine_port_plan.md, section 5.2): the minimum structure an elevated run needs, as the
// old Rail Profiles page draws it (viaductSpansNow, data/profile/profiles.html 954-991; structure.elevated.drawn_structure,
// road.piers_out_of_roads). Piers every VIA_SPAN along each elevated run, kept VIA_CLEAR either side of a line
// crossing under it and out of the roads; over a river, equal spans of at most RIVER_SPAN between the banks, or a
// canon bridge's own piers (the L&N). A span up to GIRDER_MAX is a girder under the deck, rail to soffit by the
// girder rule (literal.girder_soffit); a longer one a through truss over the rail (literal.truss_depth), with the
// deck under it.

import {
  PORT_VIA_BANK_GAP_M,
  PORT_VIA_BEFORE_MIN_M,
  PORT_VIA_BEFORE_SPANS,
  PORT_VIA_PIER_PER_M,
  PORT_VIA_PIER_SEARCH_M,
  PORT_VIA_RUN_MIN_M,
  PORT_VIA_SPAN_MIN_M,
} from "../../tol.ts";
import type { SectionModel, TypedModel, TypeSolve, TypesModule, ViaductSpan } from "../types.ts";

/** A stretch with no pier of the run's own: a river (its own piers) or a crossing line or road (none). */
type Keep = readonly [u: number, v: number, river: boolean];

/**
 * The viaduct spans of every elevated run (viaductSpansNow, 954-991). The type at each 2 m from 0 is P1's typeAt
 * on the solve given (T), at the drawn rail, as the page's typeAt(c).
 */
export function viaductSpans(m: SectionModel, types: TypeSolve, T: Pick<TypesModule, "typeAt">): ViaductSpan[] {
  const tm: TypedModel = { ...m, types, spans: [] };
  const lit = m.literals;
  const L = m.grid.length;
  const step = m.grid.step;
  const runs: [number, number][] = [];
  let a: number | null = null;
  for (let c = 0; c <= L + step; c += step) {
    const on = c <= L && T.typeAt(tm, c) === "elevated";
    if (on && a == null) a = c;
    if (!on && a != null) {
      runs.push([a, c - step]);
      a = null;
    }
  }
  const spans: ViaductSpan[] = [];
  for (const [c0, c1] of runs) {
    if (c1 - c0 < PORT_VIA_RUN_MIN_M) continue;
    const keep: Keep[] = [];
    for (const r of m.rivers) if (r.c1 > c0 && r.c0 < c1) keep.push([Math.max(c0, r.c0), Math.min(c1, r.c1), true]);
    for (const x of m.input.crossings)
      if (x.c > c0 && x.c < c1) keep.push([x.c - lit.VIA_CLEAR, x.c + lit.VIA_CLEAR, false]);
    // piers kept off the roads (Ben)
    for (const r of m.input.context.roads) if (r[2] > c0 && r[1] < c1) keep.push([r[1], r[2], false]);
    keep.sort((u, v) => u[0] - v[0]);
    const piers: number[] = [c0];
    let c = c0;
    const blocked = (q: number): Keep | undefined => keep.find(([u, v]) => q > u && q < v);
    while (c < c1) {
      let q = Math.min(c1, c + lit.VIA_SPAN);
      const k = blocked(q);
      if (k) {
        if (k[2]) {
          // a river: its own equal spans, piers at the banks; a canon bridge (the L&N) on its own piers
          const own = m.canon.piers.filter(
            (v) =>
              v >= k[0] - PORT_VIA_PIER_SEARCH_M && v <= k[1] + PORT_VIA_PIER_SEARCH_M && v > c + PORT_VIA_SPAN_MIN_M,
          );
          if (own.length >= 2) {
            for (const v of own) piers.push(v);
            q = Math.min(c1, Math.max(k[1], own[own.length - 1] as number));
          } else {
            if (k[0] - c > PORT_VIA_BANK_GAP_M) piers.push(k[0]);
            const n = Math.max(1, Math.ceil((k[1] - k[0]) / lit.RIVER_SPAN));
            for (let i = 1; i <= n; i++) piers.push(k[0] + ((k[1] - k[0]) * i) / n);
            q = k[1];
          }
        } else {
          // a pier before or after the crossing
          q = k[1] - c > lit.VIA_SPAN * PORT_VIA_BEFORE_SPANS && k[0] - c > PORT_VIA_BEFORE_MIN_M ? k[0] : k[1];
        }
      }
      if (q - c > PORT_VIA_SPAN_MIN_M) piers.push(q);
      c = q;
    }
    const ps = [...new Set(piers.map((v) => Math.round(v * PORT_VIA_PIER_PER_M) / PORT_VIA_PIER_PER_M))].sort(
      (u, v) => u - v,
    );
    for (let i = 0; i + 1 < ps.length; i++) {
      const len = (ps[i + 1] as number) - (ps[i] as number);
      if (len < PORT_VIA_SPAN_MIN_M) continue;
      const truss = len > lit.GIRDER_MAX;
      spans.push({
        c0: ps[i] as number,
        c1: ps[i + 1] as number,
        L: len,
        truss,
        below: truss ? m.settings.deckDepth : len / lit.girder.ratio + lit.girder.add,
        above: truss ? len / lit.trussRatio : 0,
        ends: [i === 0, i + 2 === ps.length],
      });
    }
  }
  return spans;
}

/** The span over c (spanAt, 992). */
export function spanAt(spans: readonly ViaductSpan[], c: number): ViaductSpan | null {
  return spans.find((s) => c >= s.c0 && c <= s.c1) ?? null;
}
