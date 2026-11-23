// P3 crossings, context and roads (claude/hub_maps/engine_port_plan.md, section 5.3): the other lines at crossings,
// the other-system structures of the context, the streets and roads of the old Rail Profiles page
// (data/profile/profiles.html 446-462, 536-541, 2180-2275), and CROSSINGS_MODULE, the functions P4 calls. Not wired
// into a method: the lead's section.solve@1 does that.

import type { RuleId } from "../../rules.gen.ts";
import { TYPES_MODULE } from "../structure/index.ts";
import type { CrossingsModule, TypesModule } from "../types.ts";
import { contextClearances, crossingClearances } from "./clearances.ts";
import { roadChecks, stationStreet } from "./roads.ts";

export { type CrossingOptions, contextClearances, crossingClearances, hallAt } from "./clearances.ts";
export {
  boredGap,
  bothBored,
  groundOn,
  kindAt,
  needSep,
  neighbourDesign,
  otherCover,
  otherRail,
  otherStruct,
  otherSunk,
  railOn,
  riverOn,
  surfaceOn,
} from "./other.ts";
export { roadChecks, roadClear, roadsIn, stationStreet, streetAtC, subwayStreet } from "./roads.ts";

/** Every rule P3's checks cite (each output's `rule`, and the rules the guess and the listing follow). */
export const CROSSINGS_RULES = [
  "clearance.crossing.structure_sum",
  "clearance.crossing.bored_gap",
  "clearance.crossing.other_line_guessed",
  "clearance.hall.checks_over_hall_roof",
  "clearance.open.clear_height",
  "clearance.context.blocks",
  "network.profile_set.crossings_apart",
  "road.level_crossing",
  "road.trough_under_road_bridge",
  "road.clearance.by_class",
  "road.piers_out_of_roads",
  "road.station.street_known",
  "road.subway_streets",
] as const satisfies readonly RuleId[];

/** P3's functions for P4 on a TypesModule (P1's by default). */
export function crossingsModule(T: TypesModule = TYPES_MODULE): CrossingsModule {
  return {
    crossings: (m) => crossingClearances(m, T),
    context: (m) => contextClearances(m, T),
    roadChecks: (m) => roadChecks(m, T),
    stationStreet,
  };
}

/** P3's functions for P4, on P1's TYPES_MODULE. */
export const CROSSINGS_MODULE: CrossingsModule = crossingsModule();
