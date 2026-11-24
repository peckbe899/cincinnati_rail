// P4 levels (claude/hub_maps/engine_port_plan.md, section 5.4): the level solver and the saved profile as the solve
// reads it (defaultAlign 1756-1807, surfacePvis 1810-1836, deriveStations 717-723, reframeDoc 1839-1868,
// alignFromDoc 1869-1897 of data/profile/profiles.html). Not wired into a method: the lead's model.ts does that.

import type { RuleId } from "../../rules.gen.ts";
import { DOC_RULES } from "./doc.ts";
import { LEVELS_SOLVER_RULES } from "./levels.ts";

export { type AlignResult, alignFromDoc, deriveStations, frameMap, reframeDoc, resetLine } from "./doc.ts";
export { defaultAlign, defaultMode, surfacePvis } from "./levels.ts";

/** Every rule P4's levels cite. */
export const LEVELS_RULES = [...new Set<RuleId>([...LEVELS_SOLVER_RULES, ...DOC_RULES])] as readonly RuleId[];
