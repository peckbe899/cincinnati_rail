// The structure a line has at a chainage for a type (structFor 1202-1214), the cover it needs (reqCover 1215-1220),
// the clear height over a line in the open (openTop 1200) and the rail over the street under an elevated station
// (elevNeed 271). P1a.

import type { SectionModel, Structure, TubeKey, Type, TypedModel } from "../types.ts";
import { isRer, riverAt } from "./at.ts";
import { metroTube } from "./phase.ts";
import { tubeOfKey } from "./tables.ts";

/** The tunnel types: under a river (not along the shore) each is the sunk box (TUNNEL, 2080). */
const TUNNEL = new Set<Type>(["cutcover", "shield", "deep", "sunk"]);

/** openTop (1200): rail to the underside of a structure over a line in the open. */
export function openTop(m: Pick<SectionModel, "tables" | "literals">): number {
  return m.tables ? m.tables.openClear : m.literals.openClear;
}

/**
 * elevNeed (271): the platform deck under the rail plus the mezzanine's clear height (the record's
 * elevated_station.mezzanine_clear_m). The page read the Metro record on the RER too (MS is global), so an RER
 * section's input carries the record as well; without it the page's 3.5 m fallback has no param, and this throws.
 */
export function elevNeed(m: Pick<SectionModel, "settings" | "structure">): number {
  if (!m.structure) throw new Error("elevNeed: the input carries no structure record (mezzanine_clear_m)");
  return m.settings.deckDepth + m.structure.mezzanine_clear_m;
}

/** The sunk river box as a structure (sunkBox 1007, from the model). */
export function sunkStructure(m: Pick<SectionModel, "sunk">): Structure {
  return { k: "sunk", below: m.sunk.below, top: m.sunk.top };
}

/**
 * structFor (1202-1214): the structure at c for type t. Open types: the viaduct deck or the track bed, the open
 * clear height above. A tunnel under a river: the sunk box. A box off a river: the record's box. Bored: the tube
 * the solve gave the drive (`tube`, drivenTube 1126; null while solving or off the solved profile), else the
 * phase's tube with the painted form (metroTube). RER: the settings' box and bored tube.
 */
export function structFor(m: SectionModel, t: Type, c: number, tube: TubeKey | null = null): Structure {
  const st = m.settings;
  if (t === "elevated") return { k: "elevated", below: st.deckDepth, top: openTop(m) };
  if (t === "atgrade") return { k: "atgrade", below: m.literals.BED_DEPTH, top: openTop(m) };
  if (t === "trough") return { k: "trough", below: m.literals.BED_DEPTH, top: openTop(m) };
  const r = riverAt(m, c);
  if (t === "sunk" || (r && TUNNEL.has(t) && !r.alongShore)) return sunkStructure(m);
  if (isRer(m)) {
    const rer = st.rer;
    if (!rer) throw new Error("structFor: an RER section without settings.rer");
    return t === "cutcover" || r
      ? { k: "box", below: rer.invertDepth, top: rer.envelope }
      : { k: "bore", below: rer.invertDepth, top: rer.boreCrown };
  }
  const T = m.tables;
  if (!T) throw new Error("structFor: the Metro structure record is missing");
  if (t === "cutcover" && !r) return T.box;
  return tube ? tubeOfKey(T, tube) : metroTube(m, c);
}

/**
 * drivenTube (1126): the tube the last solve gave the drive at c (the solve's tube at round(c / step)), null while
 * solving (a SectionModel has no solve), off the grid, on the RER or where the solve has no tube.
 */
export function drivenTube(m: SectionModel, c: number): TubeKey | null {
  const T = (m as Partial<TypedModel>).types;
  if (!T || isRer(m) || !m.tables) return null;
  const i = Math.round(c / T.grid.step);
  if (i < 0 || i >= T.tube.codes.length) return null;
  return T.tube.table[T.tube.codes[i] as number] ?? null;
}

/** structFor as the page calls it outside the solve: with the drive's tube when the model carries a solve. */
export const drivenStruct = (m: SectionModel, t: Type, c: number): Structure => structFor(m, t, c, drivenTube(m, c));

/** reqCover (1215-1220): the cover a structure needs over its top. The sunk box: its band. RER: none over a box,
 * minCover over a tube. Metro: the box's cover, one outside diameter over every bored tube. */
export function reqCover(m: Pick<SectionModel, "input" | "settings" | "literals">, s: Structure): number {
  if (s.k === "sunk") return 0;
  if (isRer(m)) return s.k === "box" ? 0 : (m.settings.rer?.minCover ?? 0);
  if (s.k === "box") return m.literals.BOX_COVER;
  return s.od ?? 0;
}
