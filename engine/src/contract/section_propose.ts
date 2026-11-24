// SectionProposeInput v0 and SectionProposal v0: the input and output of section.propose@1, the old page's proposers
// (Lower, Raise, Fix unbuildable, Propose fill, Solve levels with crossings, Reset this line, the paint review) as
// one method (engine/src/port/propose.ts). The input is a SectionSolveInput (the draft's profile laid in, as the
// sheet's worker lays it for section.solve@1) and the request; the output is the edit to lay on the draft, keyed by
// platform id, and a report of numbers and names the sheet words. Nothing is saved: the sheet puts the edit on Ben's
// draft as one undo step.

import { z } from "zod";
import { unit } from "./common.ts";
import { RuleId } from "./flags.ts";
import { SectionSolveInput } from "./section_solve.ts";

const TypeName = z.enum(["elevated", "atgrade", "trough", "cutcover", "shield", "deep", "sunk"]);
const Why = z.enum(["roof", "above", "high", "cover", "dig", "buried"]);
const c = (d: string) => z.number().meta(unit("m", d));

export const ProposeRequest = z
  .discriminatedUnion("kind", [
    z.object({
      kind: z.literal("regrade"),
      mode: z.enum(["lower", "raise"]),
      c0: c("Start of the stretch."),
      c1: c("End of the stretch."),
      fit: z.object({ t: TypeName, why: Why }).nullable().optional(),
    }),
    z.object({ kind: z.literal("fix_all") }),
    z.object({ kind: z.literal("fill"), c0: c("Start of the stretch."), c1: c("End of the stretch.") }),
    z.object({ kind: z.literal("solve_cross") }),
    z.object({ kind: z.literal("reset") }),
    z.object({ kind: z.literal("paint_review") }),
  ])
  .meta({ description: "Which proposer to run, and where." });
export type ProposeRequest = z.infer<typeof ProposeRequest>;

export const SectionProposeInput = SectionSolveInput.extend({
  contract: z.literal("section_propose_input/0"),
  request: ProposeRequest,
}).meta({
  title: "SectionProposeInput",
  description: "A section's whole-solve input with the draft's profile, and the proposer to run on it.",
});
export type SectionProposeInput = z.infer<typeof SectionProposeInput>;

const Pair = z.tuple([z.number(), z.number()]);

export const SectionProposal = z
  .object({
    contract: z.literal("section_proposal/0"),
    engine_build: z.string(),
    input_hash: z.string(),
    kind: z.enum(["regrade", "fix_all", "fill", "solve_cross", "reset", "paint_review"]),
    changed: z.boolean(),
    rule: RuleId,
    edit: z
      .object({
        pvi: z.array(Pair).optional().meta({ description: "The bend points, the whole list." }),
        st: z.record(z.string(), z.number()).optional().meta({ description: "Station levels to set, by platform id." }),
        sg: z
          .record(z.string(), z.number())
          .optional()
          .meta({ description: "Platform grades to set, by platform id; 0 removes the key." }),
        gnd: z.array(z.array(Pair)).optional().meta({ description: "The drawn ground lines, the whole list." }),
        clear: z.array(z.string()).optional().meta({ description: "Profile fields to empty (Reset this line)." }),
        ready: z.boolean().optional(),
        ovr: z
          .array(z.tuple([z.number(), z.number(), z.string()]))
          .optional()
          .meta({ description: "A profile saved in an older frame: its paints in the current one." }),
        tf: z.array(z.tuple([z.number(), z.number(), z.string()])).optional(),
        shafts: z.array(z.number()).optional(),
        so: z.record(z.string(), z.number()).optional(),
        frame: z
          .object({ length_m: z.number(), point_c: z.record(z.string(), z.number()) })
          .nullable()
          .optional()
          .meta({ description: "The frame the profile is now saved in (reframeDoc)." }),
      })
      .meta({ description: "The edit to lay on the draft; members left out are unchanged." }),
    report: z.record(z.string(), z.unknown()).meta({ description: "Numbers and names for the sheet to word." }),
    paints: z
      .array(
        z.object({
          list: z.enum(["ovr", "tf", "shafts"]),
          j: z.int().nonnegative(),
          a: z.number(),
          b: z.number(),
          paint: z.string(),
          rules: z.string().nullable(),
          same: z.boolean(),
          misfit: z.number(),
          fill: z.boolean(),
        }),
      )
      .optional()
      .meta({ description: "The paint review: each paint with what the rules give there without it." }),
  })
  .meta({
    title: "SectionProposal",
    description: "What a proposer of section.propose@1 would change on the draft, with its rule and a report.",
  });
export type SectionProposal = z.infer<typeof SectionProposal>;
