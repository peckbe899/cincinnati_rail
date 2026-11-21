// VerticalRail v0: the output of vertical.rail@1, the rail level and grade on a regular grid over one section.

import { z } from "zod";
import { Sha256, unit } from "./common.ts";
import { Flag } from "./flags.ts";

export const Grid = z
  .strictObject({
    c0: z.literal(0).meta(unit("m", "The grid starts at chainage 0.")),
    step_m: z.number().positive().meta(unit("m", "Grid step.")),
    n: z.int().positive().meta(unit("count", "Number of grid points, the length of every array.")),
  })
  .meta({ description: "The chainage grid of the arrays: point i is at c0 + i * step_m." });
export type Grid = z.infer<typeof Grid>;

export const DvKind = z
  .enum(["ps", "pe", "pvi", "end"])
  .meta({ description: "ps platform start, pe platform end, pvi a vertex, end a section end." });
export type DvKind = z.infer<typeof DvKind>;

export const DesignVertex = z
  .strictObject({
    c_m: z.number().meta(unit("m", "Chainage.")),
    z_m: z.number().meta(unit("m", "Rail level, metres NAVD88.")),
    kind: DvKind,
  })
  .meta({ description: "A vertex of the design line, sorted by (c, kind rank, order)." });
export type DesignVertex = z.infer<typeof DesignVertex>;

export const VerticalCurve = z
  .strictObject({
    c_m: z.number().meta(unit("m", "Chainage of the curve's vertex.")),
    g_in: z.number().meta(unit("permille", "Grade in.")),
    g_out: z.number().meta(unit("permille", "Grade out.")),
    L_m: z.number().nonnegative().meta(unit("m", "Curve length.")),
  })
  .meta({ description: "A parabolic vertical curve." });
export type VerticalCurve = z.infer<typeof VerticalCurve>;

export const VerticalRail = z
  .strictObject({
    contract: z.literal("vertical_rail/0"),
    engine_build: Sha256.meta({ description: "sha256 of engine/src/** and engine/package.json." }),
    input_hash: Sha256.meta({ description: "sha256 of the canonical JSON (RFC 8785) of the SectionInput." }),
    grid: Grid,
    rail_m: z.array(z.number().meta(unit("m", "Rail level, metres NAVD88."))),
    grade_permille: z.array(z.number().meta(unit("permille", "Grade."))),
    dv: z.array(DesignVertex),
    curves: z.array(VerticalCurve),
    flags: z.array(Flag),
  })
  .superRefine((v, ctx) => {
    for (const key of ["rail_m", "grade_permille"] as const) {
      if (v[key].length !== v.grid.n) {
        ctx.addIssue({
          code: "custom",
          path: [key],
          message: `${key} has ${v[key].length} values, grid.n is ${v.grid.n}`,
        });
      }
    }
  })
  .meta({ title: "VerticalRail", description: "Contract vertical_rail/0: the output of vertical.rail@1." });
export type VerticalRail = z.infer<typeof VerticalRail>;
