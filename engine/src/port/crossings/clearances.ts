// The clearances of a line against the others (profiles.html 536-541, 2213-2251): every crossing with another line
// (crossingClearancesNow 2235), every other-system structure of the context (contextClearancesNow 2219), and the hall
// over a box station the crossing check runs over (hallAt 536). P3 of claude/hub_maps/engine_port_plan.md.

import { PORT_CLEARANCE_TOL_M, PORT_CONTEXT_LEVEL_M } from "../../tol.ts";
import type { Design } from "../../vertical/design.ts";
import type {
  ContextClearance,
  CrossingClearance,
  HallSpan,
  LiveStation,
  Neighbour,
  SectionModel,
  Structure,
  Type,
  TypedModel,
  TypesModule,
} from "../types.ts";
import { bothBored, kindAt, needSep, neighbourDesign, otherRail, railOn, surfaceOn } from "./other.ts";

/** The open types: under a viaduct only a line in the open is checked; a level clash needs one (OPEN_T, 2218). */
const OPEN_T: ReadonlySet<Type> = new Set<Type>(["atgrade", "trough", "elevated"]);

/** The station whose platform covers c, half a platform either side of its centre (stationAt, 611). */
function stationOn(m: Pick<SectionModel, "stations" | "settings">, c: number): LiveStation | null {
  const half = m.settings.platform / 2;
  return m.stations.find((s) => Math.abs(c - s.c) <= half) ?? null;
}

/**
 * hallAt (536-541): the hall over chainage c, on the box roof of the station whose platform covers c (its halls from
 * station facts, stationAccess 528-531). None on the RER or without the structure record
 * (clearance.hall.checks_over_hall_roof).
 */
export function hallAt(
  m: Pick<SectionModel, "input" | "structure" | "stations" | "settings" | "halls">,
  c: number,
): HallSpan | null {
  if (m.input.system === "rer" || !m.structure) return null;
  const s = stationOn(m, c);
  if (!s) return null;
  for (const h of m.halls) if (h.station === s.index && c >= h.c0 && c <= h.c1) return h;
  return null;
}

export interface CrossingOptions {
  /**
   * Read the other line's solved structure at the crossing where the neighbour carries one, instead of guessing it
   * from its depth (clearance.crossing.other_line_guessed, unratified). Off by default: the page guessed.
   */
  readonly otherFromSolved?: boolean;
}

/**
 * crossingClearancesNow (2235-2251): each crossing with a line the hub has levels for. This line's structure at c is
 * its type's (with the hall over a box: the box and hall, its top the hall's roof), the other's is guessed from its
 * rail and this line's surveyed surface (kindAt); the upper line's floor sits over the lower line's top by the gap
 * (needSep). Two lines at grade are a level clash. A crossing with a line not marked set is pending: listed apart
 * (network.profile_set.crossings_apart). No levels for the other line: clear is null, nothing is checked.
 */
export function crossingClearances(m: TypedModel, T: TypesModule, opts: CrossingOptions = {}): CrossingClearance[] {
  const designs = new Map<string, Design>();
  const designOf = (n: Neighbour): Design => {
    let d = designs.get(n.wid);
    if (!d) {
      d = neighbourDesign(n);
      designs.set(n.wid, d);
    }
    return d;
  };
  const out: CrossingClearance[] = [];
  for (const x of m.input.crossings) {
    if (!x.wid || x.oc == null) continue;
    const n = m.input.neighbours[x.wid] ?? null;
    const z = railOn(m, x.c);
    const t0 = T.structFor(m, T.typeAt(m, x.c, z), x.c);
    const ha = t0.k === "box" ? hallAt(m, x.c) : null;
    const t: Structure = ha ? { ...t0, top: ha.top - z } : t0;
    const base = {
      c: x.c,
      wid: x.wid,
      with: x.with,
      oc: x.oc,
      z,
      t,
      pending: !n?.ready,
      source: n ? n.source : null,
      ...(ha ? { hall: ha.station } : {}),
    };
    const zo = n ? otherRail(n, x.oc, designOf(n)) : null;
    if (zo == null || !n) {
      out.push({ ...base, zo: null, clear: null, need: null, meUp: false, to: null, level: false, ok: false });
      continue;
    }
    // the other line's structure from this line's surface (surfaceAt0 704: the page's comment says the surveyed
    // ground, but S.ground0 is the finished ground once rebuildGround has run, 701; the goldens agree)
    const to = opts.otherFromSolved && n.solved ? n.solved.structure : kindAt(m, n, zo, surfaceOn(m, x.c), x.c);
    const meUp = z >= zo;
    const need = meUp ? needSep(m, to, t) : needSep(m, t, to);
    const level = t.k === "atgrade" && to.k === "atgrade";
    const clear = Math.abs(z - zo);
    out.push({
      ...base,
      zo,
      clear,
      need,
      meUp,
      to,
      level,
      ok: !level && clear >= need - PORT_CLEARANCE_TOL_M,
      rule: level
        ? "clearance.crossing.structure_sum"
        : ha
          ? "clearance.hall.checks_over_hall_roof"
          : bothBored(t, to)
            ? "clearance.crossing.bored_gap"
            : "clearance.crossing.structure_sum",
    });
  }
  return out;
}

/**
 * contextClearancesNow (2219-2234): each other-system structure of the context (the Deck's blocks at CUT and
 * Norwood) against this line at its worst point, by the crossing rule (upper floor, SEP_GAP, lower top; a track in
 * the open counts its clear height as its top). Under a viaduct or fill only a line in the open is checked. A line in
 * the open within a metre of a track at grade or in a trough is a level clash, which wins the worst point
 * (clearance.context.blocks).
 */
export function contextClearances(m: TypedModel, T: TypesModule): ContextClearance[] {
  const out: ContextClearance[] = [];
  const gap = m.literals.SEP_GAP;
  m.input.context.blocks.forEach((b, block) => {
    const to = { k: b.k, below: b.b, top: b.t };
    const viad = b.k === "viaduct" || b.k === "fill";
    const flat = b.k === "atgrade" || b.k === "trough";
    let w: Omit<ContextClearance, "block" | "ok" | "rule"> | null = null;
    for (const [c, zo] of b.p) {
      const z = railOn(m, c);
      const mt = T.typeAt(m, c, z);
      const t = T.structFor(m, mt, c);
      const meUp = z >= zo;
      if (viad && !meUp && !OPEN_T.has(mt)) continue;
      const need = meUp ? t.below + gap + b.t : b.b + gap + t.top;
      const level = OPEN_T.has(mt) && flat && Math.abs(z - zo) < PORT_CONTEXT_LEVEL_M;
      const clear = Math.abs(z - zo);
      const short = need - clear;
      if (!w || (level && !w.level) || (level === w.level && short > w.short))
        w = { c, zo, z, clear, need, meUp, t, to, level, short };
    }
    if (w)
      out.push({
        block,
        ...w,
        ok: !w.level && w.short <= PORT_CLEARANCE_TOL_M,
        rule: "clearance.context.blocks",
      });
  });
  return out;
}
