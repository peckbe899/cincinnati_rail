// Flags: what an engine method reports about a chainage range, always citing the rule that raised it.

import { z } from "zod";
import { unit } from "./common.ts";

/**
 * A rule id of rules/registry.yaml (the same pattern as region/rules.py ID_RE): two to four dotted lowercase parts,
 * e.g. "geometry.method.per_stretch". The engine's src/rules.gen.ts narrows this to the registry's ids and a test
 * keeps the two in step.
 */
export const RuleId = z
  .string()
  .regex(/^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,3}$/)
  .meta({ description: "A rule id of rules/registry.yaml, e.g. geometry.method.per_stretch." });
export type RuleId = z.infer<typeof RuleId>;

export const Severity = z.enum(["info", "warn", "error"]);
export type Severity = z.infer<typeof Severity>;

export const Flag = z
  .strictObject({
    kind: z.string().min(1).meta({ description: "What was found, a stable slug (grade_over_limit)." }),
    sev: Severity,
    c0: z.number().meta(unit("m", "Start chainage of the range.")),
    c1: z.number().meta(unit("m", "End chainage of the range (equal to c0 for a point).")),
    rule: RuleId,
    data: z.unknown().meta({ description: "The numbers behind the flag, shaped by its kind." }),
  })
  .meta({ title: "Flag", description: "A finding over a chainage range, citing the rule that raised it." });
export type Flag = z.infer<typeof Flag>;
