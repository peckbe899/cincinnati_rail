// P1 types (claude/hub_maps/engine_port_plan.md, section 5.1): the structure solver and type lookup of the old
// Rail Profiles page (data/profile/profiles.html 833-861, 1063-1676, 2525-2532), and TYPES_MODULE, the functions
// P2 to P4 call at a chainage off the grid. Not wired into a method: the lead's section.solve@1 does that.

import type { SectionModel, Structure, TubeKey, Type, TypesModule } from "../types.ts";
import { gradeLimitAt } from "./grade.ts";
import { tubeKeyAt, typeAt } from "./lookup.ts";
import { phaseAt, phaseRules } from "./phase.ts";
import { drivenTube, reqCover, structFor } from "./structure.ts";

export { limitLines, structArrays } from "./band.ts";
export { FIT_WHY, fitLim, fitOf, paintMisfits } from "./fit.ts";
export {
  allowanceAt,
  gradeLimitArrays,
  gradeLimitAt,
  gradeLimitOver,
  gradeSeverity,
  straightUnder,
  sustainedGrade,
} from "./grade.ts";
export {
  autoType,
  effOvr,
  overrideAt,
  SELECTABLE,
  type SttOptions,
  solvedType,
  sttFromDoc,
  tubeKeyAt,
  typeArray,
  typeAt,
} from "./lookup.ts";
export { methodAt, metroTube, phaseAt, phaseRecord, phaseRules, tubeFormAt, twinOf } from "./phase.ts";
export { absorbShort, approachExtra, approachLen, minRadiusAt, pointType, pointTypeOf } from "./point.ts";
export { openTypes, solveTypes, TYPES_RULES } from "./solve.ts";
export { drivenStruct, drivenTube, elevNeed, openTop, reqCover, structFor, sunkStructure } from "./structure.ts";
export { applyMS, keyOfTube, sgMaxFor, tubeOf, tubeOfKey } from "./tables.ts";

/** P1's functions for P2 to P4, at a chainage off the grid. structFor without a tube reads the drive's tube from the
 * model's solve (a TypedModel), as the page's structFor does outside the solve. */
export const TYPES_MODULE: TypesModule = {
  typeAt,
  structFor: (m: SectionModel, t: Type, c: number, tube?: TubeKey | null): Structure =>
    structFor(m, t, c, tube === undefined ? drivenTube(m, c) : tube),
  reqCover,
  phaseAt,
  phaseRules,
  gradeLimitAt,
  tubeKeyAt,
};
