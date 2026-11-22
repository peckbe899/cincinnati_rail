// The typed params accessor: the resolved params of a SectionInput under the names the ported code reads.
//
// Python resolves every param (settings.* or settings_rer.* by system, then the line's overlay, then Ben's main
// revisions) and sends only the values; the engine never reads the registry or a record. The names on the left are
// the page's settings keys (profiles.html 277, 286), so a port reads as the page did.

import type { SectionParams } from "./contract/index.ts";
import { DESIGN_PASSES, SHORT_FLAG_M, TRANSITION_SHARE } from "./tol.ts";

/** The design rules of the transition solver and the short-curve flag (design.ts reads them). */
export interface DesignRules {
  /** The share of a stretch its two platform transitions may take. */
  readonly transitionShare: number;
  /** A curve shortened by more than this, m, is flagged. */
  readonly shortFlag: number;
  /** Passes of the transition solver. */
  readonly passes: number;
}

/** The Profiles page's design rules, for an input that does not send its own. */
export const PAGE_RULES: DesignRules = {
  transitionShare: TRANSITION_SHARE,
  shortFlag: SHORT_FLAG_M,
  passes: DESIGN_PASSES,
};

export interface VerticalParams extends DesignRules {
  /** settings.platform: platform length, m. */
  readonly platform: number;
  /** settings.vcRadius: vertical curve radius, m; 0 builds no curves. */
  readonly vcRadius: number;
  /** settings.vcMinLen: shortest vertical curve, m. */
  readonly vcMinLen: number;
}

/** The params vertical.rail reads, from a SectionInput's params; an absent design rule takes the page's value. */
export function verticalParams(p: SectionParams): VerticalParams {
  return {
    platform: p.platform_m,
    vcRadius: p.vc_radius_m,
    vcMinLen: p.vc_min_len_m,
    transitionShare: p.transition_share ?? PAGE_RULES.transitionShare,
    shortFlag: p.short_curve_flag_m ?? PAGE_RULES.shortFlag,
    passes: p.design_passes ?? PAGE_RULES.passes,
  };
}
