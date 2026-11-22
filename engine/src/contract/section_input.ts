// SectionInput v0: everything vertical.rail needs about one section. Python builds it from records
// (region/ext/profiles/inputs.py); the engine never reads records.

import { z } from "zod";
import { ChainageBasis, unit } from "./common.ts";

export const SectionParams = z
  .strictObject({
    platform_m: z.number().positive().meta(unit("m", "Platform length.")),
    vc_radius_m: z.number().positive().meta(unit("m", "Vertical curve radius.")),
    vc_min_len_m: z.number().nonnegative().meta(unit("m", "Shortest vertical curve.")),
    transition_share: z
      .number()
      .positive()
      .max(1)
      .optional()
      .meta(
        unit(
          "ratio",
          "The share of a stretch the two platform transitions on it may take (absent: 0.5, profiles.html 778).",
        ),
      ),
    short_curve_flag_m: z
      .number()
      .nonnegative()
      .optional()
      .meta(unit("m", "A vertical curve shortened by more than this is flagged (absent: 0.5, profiles.html 799).")),
    design_passes: z
      .int()
      .positive()
      .optional()
      .meta(
        unit(
          "count",
          "Passes of the transition solver, each re-reading its neighbours (absent: 5, profiles.html 765).",
        ),
      ),
  })
  .meta({
    description:
      "Resolved params (settings.* or settings_rer.* by system, with the CVG overlay). The design rules after vc_min_len_m are optional: absent, each takes the Profiles page's value, so an input without them solves as before.",
  });
export type SectionParams = z.infer<typeof SectionParams>;

export const SectionStation = z
  .strictObject({
    platform_id: z.string().min(1).meta({ description: "The platform record id." }),
    order: z
      .int()
      .nonnegative()
      .meta(unit("index", "Station order along the section. Of two overlapping platforms the first wins.")),
    c_m: z.number().meta(unit("m", "Platform centre chainage: the stop's point c plus its slide.")),
    level_m: z
      .number()
      .meta(unit("m", "Rail level at the platform, metres NAVD88."))
      .nullable()
      .meta({ description: "Rail level at the platform, metres NAVD88; null leaves it to the design." }),
    grade_permille: z
      .number()
      .meta(unit("permille", "Grade through the platform."))
      .nullable()
      .meta({ description: "Grade through the platform; null leaves it to the design." }),
  })
  .meta({ description: "A platform on the section. Deleted platforms are removed before the input is built." });
export type SectionStation = z.infer<typeof SectionStation>;

export const Pvi = z
  .strictObject({
    c_m: z.number().meta(unit("m", "Chainage of the vertex.")),
    z_m: z.number().meta(unit("m", "Rail level at the vertex, metres NAVD88.")),
  })
  .meta({ description: "A point of vertical intersection set by Ben." });
export type Pvi = z.infer<typeof Pvi>;

export const GroundProfile = z
  .strictObject({
    step_m: z.number().positive().meta(unit("m", "Sample spacing from chainage 0.")),
    z_m: z.array(z.number().meta(unit("m", "Ground level, metres NAVD88."))),
  })
  .meta({ description: "Ground levels along the section on a regular grid from chainage 0." });
export type GroundProfile = z.infer<typeof GroundProfile>;

export const SectionInput = z
  .strictObject({
    contract: z.literal("section_input/0"),
    section_id: z.string().min(1).meta({ description: "The section record id." }),
    length_m: z.number().nonnegative().meta(unit("m", "Section length in the chainage basis.")),
    chainage_basis: ChainageBasis,
    scale: z
      .number()
      .positive()
      .meta(unit("ratio", "Ground distance per unit of grid chainage on this section, for railsim and quantities.")),
    step_m: z.number().positive().meta(unit("m", "Grid step of the output arrays.")),
    params: SectionParams,
    stations: z.array(SectionStation),
    pvi: z.array(Pvi),
    ground: GroundProfile.optional(),
  })
  .meta({ title: "SectionInput", description: "Contract section_input/0: the input of vertical.rail@1." });
export type SectionInput = z.infer<typeof SectionInput>;
