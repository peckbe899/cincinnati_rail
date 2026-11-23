// The structure record as the four structures the page keeps (applyMS, profiles.html 1063-1071), and the platform
// grade limit by era (sgMaxFor 1227). P1a of claude/hub_maps/engine_port_plan.md.

import { TUBE_IS_BORE_INSIDE_M } from "../../tol.ts";
import type { SectionModel, Structure, StructureParams, StructureTables, TubeKey, TubeRecord } from "../types.ts";

/**
 * tubeOf (1063): a bored tube at the rail. below = rail over the invert plus the lining, top = inside less rail over
 * the invert plus the lining, its cover one outside diameter. The page calls a tube wider inside than 7 m the bore.
 */
export function tubeOf(t: TubeRecord, key: TubeKey): Structure {
  const lining = (t.outside - t.inside) / 2;
  return {
    k: t.inside > TUBE_IS_BORE_INSIDE_M ? "bore" : "tube",
    below: t.rail_over_invert + lining,
    top: t.inside - t.rail_over_invert + lining,
    od: t.outside,
    tube: key,
  };
}

/**
 * applyMS (1065-1071): the box (the record's below and top), the type A and C tubes, the bore, and the clear height
 * over a line in the open (the record's open_clear_height, else literal.OPEN_CLEAR.metro).
 */
export function applyMS(s: StructureParams, openClear: number): StructureTables {
  return {
    box: { k: "box", below: s.box.below, top: s.box.top },
    tube: tubeOf(s.tubes.A, "A"),
    tubeC: tubeOf(s.tubes.C, "C"),
    bore: tubeOf(s.tubes.bore, "bore"),
    openClear: s.open_clear_height ?? openClear,
  };
}

/** The structure of a tube key (tubeOfKey, 620). */
export function tubeOfKey(t: StructureTables, k: TubeKey | null | undefined): Structure {
  return k === "bore" ? t.bore : k === "C" ? t.tubeC : t.tube;
}

/** The key of a tube structure (the page compares against METRO_ST.bore and .tubeC, 1122). */
export function keyOfTube(t: StructureTables, s: Structure): TubeKey {
  return s === t.bore || s.tube === "bore" ? "bore" : s === t.tubeC || s.tube === "C" ? "C" : "A";
}

/** sgMaxFor (1227): the era's platform grade limit on the Metro, the settings' on the RER. */
export function sgMaxFor(m: Pick<SectionModel, "input" | "settings">): number {
  return m.input.system !== "rer" && m.input.era ? m.input.era.sgMax : m.settings.stationMaxGrade;
}
