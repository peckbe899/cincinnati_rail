// P2 ground, rivers, viaducts and canon (claude/hub_maps/engine_port_plan.md, section 5.2): the ground layers, the
// rivers and their sunk box band, the viaduct spans and the canon of the old Rail Profiles page
// (data/profile/profiles.html 636-712, 864-1041), and GROUND_MODULE, the functions P3 and P4 call. Not wired into a
// method: the lead's section.solve@1 does that.

import type { RuleId } from "../../rules.gen.ts";
import { TYPES_MODULE } from "../structure/index.ts";
import type { GroundModule, SectionModel, TypedModel, TypeSolve, TypesModule } from "../types.ts";
import { canonAt, lockAt } from "./canon.ts";
import { riverIndex, sampleGround } from "./layers.ts";
import { madeBedAt } from "./rivers.ts";
import { viaductSpans } from "./viaduct.ts";

export {
  applyLocks,
  buildCanon,
  canonAt,
  chainLL,
  fixedLevel,
  lockAt,
  lockedStation,
  refAt,
} from "./canon.ts";
export {
  bedOf,
  crossGround,
  drawnGround,
  type GndLine,
  type GndPoint,
  gndLevel,
  normGnd,
  parseGnd,
  rebuildGround,
  regradeGround,
  riverAtArray,
  riverIndex,
  sampleGround,
} from "./layers.ts";
export {
  alongShore,
  bedAt,
  bridgeOf,
  madeBedArray,
  madeBedAt,
  type RiverContext,
  riverBand,
  riverBridges,
  riverModels,
  sunkBox,
} from "./rivers.ts";
export { spanAt, viaductSpans } from "./viaduct.ts";

/** The rules P2's layers, bands, spans, canon and lock flags follow (each in rules/registry.yaml). */
export const GROUND_RULES = [
  "ground.layers.three",
  "ground.deck_regrades",
  "ground.drawn.tool",
  "ground.drawn.counts_across_crossing_street",
  "river.crossing.bridge_or_sunk",
  "river.sunk_box.roof_band",
  "river.sunk_box.made_up_bed",
  "river.bridge.navigation_clearance",
  "river.shore_not_crossing",
  "structure.sunk_box.dimensions_from_record",
  "structure.elevated.drawn_structure",
  "road.piers_out_of_roads",
  "geometry.method.canon_bored",
  "network.canon.locks",
  "network.canon.fixed_levels",
] as const satisfies readonly RuleId[];

/** P2's functions for P3 and P4, with P1's type lookup T for the two that need the types (spans, made bed). */
export function groundModule(T: Pick<TypesModule, "typeAt">): GroundModule {
  return {
    sampleGround,
    riverIndex: (m: SectionModel, c: number) => riverIndex(m.rivers, c),
    canonAt,
    lockAt,
    madeBedAt: (m: TypedModel, c: number, z: number) => madeBedAt(m, c, z, T),
    viaductSpans: (m: SectionModel, types: TypeSolve) => viaductSpans(m, types, T),
  };
}

/** P2's functions on P1's own type lookup. */
export const GROUND_MODULE: GroundModule = groundModule(TYPES_MODULE);
