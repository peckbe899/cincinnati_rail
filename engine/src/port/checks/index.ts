// P4 checks (claude/hub_maps/engine_port_plan.md, section 5.4): the plan curvature and curve allowance, the drawing
// checks, the summary and river checks, the design checks, the drawn ground checks, the issues and Propose fill of
// the old Rail Profiles page (data/profile/profiles.html 1684-1754, 1900-2178). Not wired into a method: the lead's
// section.solve@1 does that.

import type { RuleId } from "../../rules.gen.ts";
import { CURVE_RULES } from "./curve.ts";
import { DESIGN_RULES } from "./design.ts";
import { FILL_RULES } from "./fill.ts";
import { ISSUES_RULES } from "./issues.ts";
import { RIVER_RULES } from "./summary.ts";

export { type Chord, chordsOf, sumpsOf, TUNNEL } from "./chords.ts";
export {
  allowanceAt,
  curveAllowance,
  curveGradeFlag,
  curveGradeRanges,
  radii,
  radiusAt,
} from "./curve.ts";
export { designChecks, hallAt } from "./design.ts";
export { drawingFlags } from "./drawing.ts";
export { groundWithoutOwnLines, proposeFill } from "./fill.ts";
export { gndChecks, gndLevel } from "./ground_checks.ts";
export {
  allIssues,
  contextFlag,
  crossingFlag,
  deepShallowFlag,
  gradeFlag,
  misfitFlag,
  roadFlag,
  unbuildableFlag,
} from "./issues.ts";
export { computeSummary, deepShallow, gradesOver, riverChecks } from "./summary.ts";

/** Every rule P4's checks cite. */
export const CHECKS_RULES = [
  ...new Set<RuleId>([
    ...CURVE_RULES,
    ...DESIGN_RULES,
    ...FILL_RULES,
    ...ISSUES_RULES,
    ...RIVER_RULES,
    "network.drawing.corner_checks",
    "ground.drawn.limits",
    "ground.drawn.counts_across_crossing_street",
  ]),
] as readonly RuleId[];
