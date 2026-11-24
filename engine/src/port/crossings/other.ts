// The other line at a crossing (profiles.html 2180-2212): its rail rebuilt from its saved profile (otherRail 2182),
// its structure guessed from its rail and this line's surveyed surface (kindAt 2197, with structFor 1202, sunkBox
// 1007 and reqCover 1215 as the page calls them with the other line's id), and the separation the two need
// (boredGap 2211, needSep 2212). P3 of claude/hub_maps/engine_port_plan.md (section 5.3).
//
// The page called structFor(t, c, id) with the other line's id: setOf(id) gave that system's settings, openTop(id)
// its clear height, phaseAt(c, id) skipped the Chronology and the pieces (the piece is '' off this line) and read
// the other line's line_phase, drivenTube was null and no tube form was painted. The river and the canon are this
// line's (riverAt(c) and alongShore read the page's own line). All of that is ported as is, for parity: reading the
// other line's solved structure instead is clearance.crossing.other_line_guessed (unratified), behind an option.

import { sampleGround } from "../../station/ground.ts";
import { type Design, design } from "../../vertical/design.ts";
import { railAt } from "../../vertical/rail.ts";
import { vertices } from "../../vertical/vertices.ts";
import { phaseRecord } from "../structure/phase.ts";
import { openTop } from "../structure/structure.ts";
import { applyMS, tubeOfKey } from "../structure/tables.ts";
import type { Neighbour, PhaseRecord, RiverModel, SectionModel, Structure, StructureTables, Type } from "../types.ts";

/** The tunnel types: under a river (not along the shore) each is the sunk box (TUNNEL, 2080). */
const TUNNEL: ReadonlySet<Type> = new Set<Type>(["cutcover", "shield", "deep", "sunk"]);
/** Bored structures: between two of them the separation is the side-by-side tubes' ground (BORED, 2210). */
const BORED: ReadonlySet<Structure["k"]> = new Set<Structure["k"]>(["tube", "bore"]);

// ------------------------------------------------------------------------------------- this line, at a chainage

/** The first river whose range holds c on this line (riverAt, 705). */
export function riverOn(m: Pick<SectionModel, "rivers">, c: number): RiverModel | null {
  for (const r of m.rivers) if (c >= r.c0 && c <= r.c1) return r;
  return null;
}

/** This line's drawn rail at c (railAt, 803). */
export const railOn = (m: Pick<SectionModel, "rail">, c: number): number => railAt(m.rail.design, c);

/** This line's finished ground at c (groundAt 645 and groundAt0 646: the same layer once the ground is built). */
export const groundOn = (m: Pick<SectionModel, "ground" | "grid">, c: number): number =>
  sampleGround(m.ground.finished, m.grid.step, c);

/** The pool over a river, else the finished ground (surfaceAt0, 704). */
export const surfaceOn = (m: Pick<SectionModel, "rivers" | "settings" | "ground" | "grid">, c: number): number =>
  riverOn(m, c) ? m.settings.pool : groundOn(m, c);

// --------------------------------------------------------------------------------------------- the other rail

/**
 * The other line's built rail (otherRail 2182-2195): its derived stations (centre, rail, platform grade by name),
 * its bend points, its platform length and vertical curve radius. The page took the vertical curve minimum from
 * this line's settings (vertices 725 reads the global settings.vcMinLen); the neighbour carries its own, which the
 * golden adapter sets to the page's value.
 */
export function neighbourDesign(n: Neighbour): Design {
  return design(
    vertices({
      length: n.length_m,
      platform: n.platform_m,
      vcRadius: n.vc_radius_m,
      vcMinLen: n.vc_min_len_m,
      stations: n.stations.map((s, i) => ({ c: s.c, z: s.rail, gradePermille: s.sg, order: i })),
      pvi: n.pvi,
    }),
  );
}

/** The other line's rail at its chainage oc (otherRail 2182): null when the hub has no levels for it. */
export function otherRail(n: Neighbour | null | undefined, oc: number, d?: Design): number | null {
  if (!n || !Number.isFinite(oc)) return null;
  return railAt(d ?? neighbourDesign(n), oc);
}

// -------------------------------------------------------------------------------------- the other structure

/** The structure record's four structures for a Metro neighbour: this line's (METRO_ST is global on the page). */
function metroTables(m: Pick<SectionModel, "tables" | "structure" | "literals">, n: Neighbour): StructureTables {
  if (m.tables) return m.tables;
  if (m.structure) return applyMS(m.structure, n.open_clear_m ?? m.literals.openClear);
  throw new Error(`kindAt: a Metro neighbour (${n.wid}) needs the structure record in this line's input`);
}

/** openTop(id) (1200): the other line's clear height in the open. */
function otherOpenTop(m: Pick<SectionModel, "tables" | "structure" | "literals">, n: Neighbour): number {
  if (n.open_clear_m !== undefined) return n.open_clear_m;
  if (n.system === "rer") throw new Error(`kindAt: the RER neighbour ${n.wid} has no open_clear_m`);
  return m.tables ? openTop(m) : metroTables(m, n).openClear;
}

function rerOf(n: Neighbour): NonNullable<Neighbour["settings"]["rer"]> {
  const r = n.settings.rer;
  if (!r) throw new Error(`kindAt: the RER neighbour ${n.wid} has no settings.rer`);
  return r;
}

/** sunkBox(id) (1007-1012): the RER's box by its settings; the Metro's from the record's box plus riverRoof. */
export function otherSunk(m: Pick<SectionModel, "structure">, n: Neighbour): Structure {
  if (n.system === "rer") {
    const r = rerOf(n);
    return { k: "sunk", below: r.invertDepth, top: r.envelope };
  }
  const s = m.structure;
  const roof = n.settings.riverRoof;
  if (!s || roof === undefined)
    throw new Error(`kindAt: the Metro neighbour ${n.wid} needs the structure record and settings.riverRoof`);
  return { k: "sunk", below: s.box.below, top: s.box.roof_underside + roof };
}

/**
 * structFor(t, c, id) (1202-1214) for the other line at this line's chainage c. Its phase is its line_phase, else
 * later (phaseAt with another id, 1105), and its tube that phase's (metroTube 1108 with no tube form painted).
 */
export function otherStruct(m: SectionModel, n: Neighbour, t: Type, c: number): Structure {
  const st = n.settings;
  if (t === "elevated") return { k: "elevated", below: st.deckDepth, top: otherOpenTop(m, n) };
  if (t === "atgrade" || t === "trough") return { k: t, below: m.literals.BED_DEPTH, top: otherOpenTop(m, n) };
  const r = riverOn(m, c);
  if (t === "sunk" || (r && TUNNEL.has(t) && !r.alongShore)) return otherSunk(m, n);
  if (n.system === "rer") {
    const rer = rerOf(n);
    return t === "cutcover" || r
      ? { k: "box", below: rer.invertDepth, top: rer.envelope }
      : { k: "bore", below: rer.invertDepth, top: rer.boreCrown };
  }
  const T = metroTables(m, n);
  if (t === "cutcover" && !r) return T.box;
  const rec = phaseRecord(m, n.phase ?? "later") as PhaseRecord;
  return tubeOfKey(T, rec.tube);
}

/** reqCover(sc, topZ, id) (1215-1220) for the other line: the sunk box none, the RER minCover over a tube, the Metro
 * box its cover, a Metro tube one outside diameter. */
export function otherCover(m: Pick<SectionModel, "literals">, n: Neighbour, s: Structure): number {
  if (s.k === "sunk") return 0;
  if (n.system === "rer") return s.k === "box" ? 0 : rerOf(n).minCover;
  if (s.k === "box") return m.literals.BOX_COVER;
  return s.od ?? 0;
}

/**
 * kindAt (2197-2205): the other line's structure at a crossing from its rail z and this line's surveyed surface gr.
 * In a river range: a bridge over the pool (literal.bridge_above_pool), else the sunk box. No ground: at grade.
 * Over the ground by elevAbove: a viaduct; within coverBelow under it: at grade; a Metro line shallower than the box:
 * a trough; else bored (deep from deepBelow), or the box where the tube would lack its cover.
 */
export function kindAt(m: SectionModel, n: Neighbour, z: number, gr: number, c: number): Structure {
  const st = n.settings;
  if (riverOn(m, c))
    return otherStruct(m, n, z >= m.settings.pool + m.literals.bridgeAbovePool ? "elevated" : "sunk", c);
  if (!Number.isFinite(gr)) return otherStruct(m, n, "atgrade", c);
  if (z - gr >= st.elevAbove) return otherStruct(m, n, "elevated", c);
  const d = gr - z;
  if (d < st.coverBelow) return otherStruct(m, n, "atgrade", c);
  if (n.system !== "rer" && d < metroTables(m, n).box.top) return otherStruct(m, n, "trough", c);
  const sc = otherStruct(m, n, d >= st.deepBelow ? "deep" : "shield", c);
  return d - sc.top < otherCover(m, n, sc) ? otherStruct(m, n, "cutcover", c) : sc;
}

// ------------------------------------------------------------------------------------------------ separation

/** boredGap (2211): the ground of side-by-side tubes, the larger of type A's and type C's running gap; SEP_GAP
 * without the record (clearance.crossing.bored_gap). */
export function boredGap(m: Pick<SectionModel, "structure" | "literals">): number {
  const s = m.structure;
  if (!s) return m.literals.SEP_GAP;
  return Math.max(s.tubes.A.spacing - s.tubes.A.outside, s.tubes.C.spacing - s.tubes.C.outside);
}

/** needSep (2212): the upper floor, the gap (bored gap between two bored tunnels, else SEP_GAP), the lower top
 * (clearance.crossing.structure_sum). */
export function needSep(m: Pick<SectionModel, "structure" | "literals">, lo: Structure, up: Structure): number {
  return up.below + (BORED.has(lo.k) && BORED.has(up.k) ? boredGap(m) : m.literals.SEP_GAP) + lo.top;
}

/** Both structures bored: the separation is the bored gap. */
export const bothBored = (a: Structure, b: Structure): boolean => BORED.has(a.k) && BORED.has(b.k);
