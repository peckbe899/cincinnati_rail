// section.solve@1 (claude/hub_maps/engine_port_plan.md, section 7.5): the contract's input to PortInput, the whole
// solve (model.ts), and the solve to solved_section/0. SECTION_SOLVE_RULES is every rule its findings can cite.

import type { SectionProposal, SectionProposeInput } from "../contract/section_propose.ts";
import type { SectionSolveInput } from "../contract/section_solve.ts";
import type { RuleId } from "../rules.gen.ts";
import { CHECKS_RULES } from "./checks/index.ts";
import { CROSSINGS_RULES } from "./crossings/index.ts";
import { GROUND_RULES } from "./ground/index.ts";
import { LEVELS_RULES } from "./levels/index.ts";
import { solveSection } from "./model.ts";
import { PROPOSE_RULES, propose } from "./propose.ts";
import { TYPES_RULES } from "./structure/index.ts";
import { jsonSafe, portInputOf, solvedJson } from "./wire.ts";

export const SECTION_SOLVE_RULES: readonly RuleId[] = [
  ...new Set<RuleId>([...TYPES_RULES, ...GROUND_RULES, ...CROSSINGS_RULES, ...CHECKS_RULES, ...LEVELS_RULES]),
];

/** section.solve@1 on the contract's JSON. */
export function sectionSolve(j: SectionSolveInput): ReturnType<typeof solvedJson> {
  const input = portInputOf(j);
  return solvedJson(input, solveSection(input));
}

export const SECTION_PROPOSE_RULES: readonly RuleId[] = [
  ...new Set<RuleId>([...SECTION_SOLVE_RULES, ...PROPOSE_RULES]),
];

/** section.propose@1 on the contract's JSON: the request's proposer on the input, as data. */
export function sectionPropose(j: SectionProposeInput): Omit<SectionProposal, "engine_build" | "input_hash"> {
  const { request, ...rest } = j;
  const input = portInputOf({ ...rest, contract: "section_solve_input/0" });
  const p = propose(input, request);
  return jsonSafe({ contract: "section_proposal/0", ...p }) as Omit<SectionProposal, "engine_build" | "input_hash">;
}
