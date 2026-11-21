// The typed params accessor: the resolved params of a SectionInput under the names the ported code reads.
//
// Python resolves every param (settings.* or settings_rer.* by system, then the line's overlay, then Ben's main
// revisions) and sends only the values; the engine never reads the registry or a record. The names on the left are
// the page's settings keys (profiles.html 277, 286), so a port reads as the page did.

import type { SectionParams } from "./contract/index.ts";

export interface VerticalParams {
  /** settings.platform: platform length, m. */
  readonly platform: number;
  /** settings.vcRadius: vertical curve radius, m; 0 builds no curves. */
  readonly vcRadius: number;
  /** settings.vcMinLen: shortest vertical curve, m. */
  readonly vcMinLen: number;
}

/** The params vertical.rail reads, from a SectionInput's params. */
export function verticalParams(p: SectionParams): VerticalParams {
  return { platform: p.platform_m, vcRadius: p.vc_radius_m, vcMinLen: p.vc_min_len_m };
}
