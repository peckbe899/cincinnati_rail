// vertical.rail@1: the rail level and grade of one section on its grid, from its platforms and PVIs.
//
// The geometry is the Profiles page's (vertices, design, railAt, gradeAt); this file only maps SectionInput v0 in
// and VerticalRail v0 out. The section's ground, scale and chainage basis are carried by the input but not read by
// this version.

import type { Flag, SectionInput } from "../contract/index.ts";
import { verticalParams } from "../params.ts";
import type { RuleId } from "../rules.gen.ts";
import { CURVE_MIN_M, PERMILLE } from "../tol.ts";
import { type Design, design } from "./design.ts";
import { railGrid } from "./rail.ts";
import { type Vertices, vertices } from "./vertices.ts";

/** The rules vertical.rail@1 can cite in a flag. */
export const VERTICAL_RAIL_RULES = [
  "era.vertical_curve.radius_and_min_length",
  "platform.length.by_system",
  "network.level_solver.shallow_as_grade_allows",
] as const satisfies readonly RuleId[];

type VerticalRule = (typeof VERTICAL_RAIL_RULES)[number];

/** VerticalRail v0 without the two members the host adds (engine_build, input_hash). */
export interface VerticalRailBody {
  contract: "vertical_rail/0";
  grid: { c0: 0; step_m: number; n: number };
  rail_m: number[];
  grade_permille: number[];
  dv: { c_m: number; z_m: number; kind: "ps" | "pe" | "pvi" | "end" }[];
  curves: { c_m: number; g_in: number; g_out: number; L_m: number }[];
  flags: (Flag & { rule: VerticalRule })[];
}

/** The design of a section: its vertices and the built line, for callers that want more than the arrays. */
export function sectionDesign(input: SectionInput): { verts: Vertices; design: Design } {
  const p = verticalParams(input.params);
  const verts = vertices({
    length: input.length_m,
    platform: p.platform,
    vcRadius: p.vcRadius,
    vcMinLen: p.vcMinLen,
    stations: input.stations.map((s) => ({
      c: s.c_m,
      z: s.level_m,
      gradePermille: s.grade_permille,
      order: s.order,
    })),
    pvi: input.pvi.map((q) => ({ c: q.c_m, z: q.z_m })),
  });
  return { verts, design: design(verts, p) };
}

function flagsOf(input: SectionInput, verts: Vertices, d: Design): VerticalRailBody["flags"] {
  const half = input.params.platform_m / 2;
  const flags: VerticalRailBody["flags"] = [];
  for (const k of verts.unset) {
    const s = input.stations[k];
    if (!s) continue;
    flags.push({
      kind: "platform_level_unset",
      sev: "warn",
      c0: s.c_m - half,
      c1: s.c_m + half,
      rule: "network.level_solver.shallow_as_grade_allows",
      data: { platform_id: s.platform_id },
    });
  }
  for (const k of verts.overlapped) {
    const s = input.stations[k];
    if (!s) continue;
    flags.push({
      kind: "platform_overlap",
      sev: "warn",
      c0: s.c_m - half,
      c1: s.c_m + half,
      rule: "platform.length.by_system",
      data: { platform_id: s.platform_id },
    });
  }
  for (const x of d.short) {
    flags.push({
      kind: "vertical_curve_short",
      sev: "error",
      c0: x.c,
      c1: x.c,
      rule: "era.vertical_curve.radius_and_min_length",
      data: { need_m: x.need, got_m: x.got, dg_permille: x.dgPermille, radius_m: verts.rv },
    });
  }
  return flags.sort((a, b) => a.c0 - b.c0 || a.c1 - b.c1);
}

export function verticalRail(input: SectionInput): VerticalRailBody {
  const { verts, design: d } = sectionDesign(input);
  const grid = railGrid(d, input.length_m, input.step_m);
  const curves: VerticalRailBody["curves"] = [];
  d.dv.forEach((v, k) => {
    const Lk = d.L[k] as number;
    if (Lk > CURVE_MIN_M) {
      curves.push({
        c_m: v.c,
        g_in: (d.g[k - 1] as number) * PERMILLE,
        g_out: (d.g[k] as number) * PERMILLE,
        L_m: Lk,
      });
    }
  });
  return {
    contract: "vertical_rail/0",
    grid: { c0: 0, step_m: input.step_m, n: grid.n },
    rail_m: Array.from(grid.rail),
    grade_permille: Array.from(grid.grade),
    dv: verts.v.map((v) => ({ c_m: v.c, z_m: v.z, kind: v.kind })),
    curves,
    flags: flagsOf(input, verts, d),
  };
}
