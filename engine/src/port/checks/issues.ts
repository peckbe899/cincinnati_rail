// Every finding of a line with its chainage, sorted along the line (allIssues 2143-2178): the grades over the limit,
// the clashes with other lines and with the context, the river checks, the road checks, the station flags, the
// stations deeper than the shallow canon, the design and drawing checks, the drawn ground, the structure solve's
// findings, the paints that cannot be built and the unbuildable stretches. As data with a rule id each (flags as
// data, 2.1.17): the sheet words them. Stable sort by c, as the page; exact repeats removed (the page pushed some
// solve flags once per 2 m sample, 1517).

import type { RuleId } from "../../rules.gen.ts";
import type {
  ContextClearance,
  CrossingClearance,
  GradeOver,
  IssueParts,
  Misfit,
  PortFlag,
  RoadCheck,
  Unbuildable,
} from "../types.ts";

/** Lower or Raise for each misfit reason (FIT_WHY, 1617). */
const FIT_WHY: Record<Misfit["why"], "lower" | "raise"> = {
  roof: "lower",
  above: "lower",
  high: "lower",
  cover: "lower",
  dig: "raise",
  buried: "raise",
};

/** A grade over the limit as its finding (allIssues 2146-2153; era.grade.limit_by_phase, sustained_vs_local). */
export function gradeFlag(o: GradeOver): PortFlag {
  const kind =
    o.sev === "local"
      ? "grade_over_local"
      : o.sev === "straight"
        ? "grade_over_straight_underground"
        : "grade_over_sustained";
  // the straight-underground warning is the phase's (limit_by_phase), localized is sustained_vs_local; the grade
  // checked is the chord between bends (era.grade.steepest_between_bends, in data)
  const rule: RuleId = o.sev === "local" ? "era.grade.sustained_vs_local" : "era.grade.limit_by_phase";
  return {
    kind,
    page: "Grade",
    sev: o.sev === "error" ? "error" : "warn",
    c0: o.c0,
    c1: o.c1,
    c: (o.c0 + o.c1) / 2,
    rule,
    data: {
      g: o.g,
      lim: o.limit.lim,
      warn: o.limit.warn,
      why: o.limit.why,
      phase: o.limit.phase,
      avg: o.sustained.avg,
      W: o.sustained.W,
      len: o.c1 - o.c0,
      chord_rule: "era.grade.steepest_between_bends",
    },
  };
}

/** A crossing that is not clear as its finding (2154-2156): listed apart (pending) when the other line is not set. */
export function crossingFlag(x: CrossingClearance): PortFlag {
  return {
    kind: x.level ? "crossing_level" : "crossing_short",
    page: "Clearance",
    sev: "error",
    c0: x.c,
    c1: x.c,
    c: x.c,
    rule: x.pending ? "network.profile_set.crossings_apart" : (x.rule ?? "clearance.crossing.structure_sum"),
    data: {
      wid: x.wid,
      with: x.with,
      clear: x.clear,
      need: x.need,
      meUp: x.meUp,
      t: x.t,
      to: x.to,
      source: x.source,
      ...(x.hall != null ? { hall: x.hall } : {}),
    },
    ...(x.pending ? { pending: true } : {}),
  };
}

/** A context block that is not clear as its finding (2154-2156). */
export function contextFlag(x: ContextClearance): PortFlag {
  return {
    kind: x.level ? "context_level" : "context_short",
    page: "Context",
    sev: "error",
    c0: x.c,
    c1: x.c,
    c: x.c,
    rule: x.rule ?? "clearance.context.blocks",
    data: { block: x.block, clear: x.clear, need: x.need, meUp: x.meUp, t: x.t, to: x.to, short: x.short },
  };
}

const ROAD_RULE: Record<RoadCheck["kind"], RuleId> = {
  level_crossing: "road.level_crossing",
  trough_under_road: "road.trough_under_road_bridge",
  clearance_over_road: "road.clearance.by_class",
  pier_in_road: "road.piers_out_of_roads",
};

/** A road check as its finding (2165). */
export function roadFlag(x: RoadCheck): PortFlag {
  return {
    kind: x.kind,
    page: "Road",
    sev: x.sev,
    c0: x.c,
    c1: x.c,
    c: x.c,
    rule: x.rule ?? ROAD_RULE[x.kind],
    data: {
      road: x.road,
      ...(x.clear != null ? { clear: x.clear } : {}),
      ...(x.need != null ? { need: x.need } : {}),
      ...(x.truss != null ? { truss: x.truss } : {}),
    },
  };
}

/**
 * A station the canon puts in a shallow section deeper than shallowMax (2167). No rule says it: the registry lists
 * "Canon (warning)" under network.canon.fixed_levels, which is cited here; the missing rule is reported to the lead
 * (claude/hub_maps/engine_port_plan.md, section 9: suggested network.canon.shallow_section_depth).
 */
export function deepShallowFlag(f: IssueParts["deepShallow"][number], half: number): PortFlag {
  return {
    kind: "deep_in_shallow_canon",
    page: "Canon",
    sev: "warn",
    c0: f.c - half,
    c1: f.c + half,
    c: f.c,
    rule: "network.canon.fixed_levels",
    data: { station: f.station, d: f.d, missing_rule: "network.canon.shallow_section_depth" },
  };
}

/** A paint or selection that cannot be built (2172): Lower or Raise, Clear, and Propose fill for a roof or cover. */
export function misfitFlag(m: Misfit): PortFlag {
  const mode = FIT_WHY[m.why];
  return {
    kind: "paint_misfit",
    page: "Painted",
    sev: "error",
    c0: m.c0,
    c1: m.c1,
    c: (m.c0 + m.c1) / 2,
    rule: "structure.paint.must_fit",
    data: { t: m.t, why: m.why, worst: m.worst, ...(m.si != null ? { si: m.si } : {}) },
    fix: { mode, c0: m.c0, c1: m.c1 },
    clear: { c0: m.c0, c1: m.c1, ...(m.si != null ? { si: m.si } : {}) },
    ...(m.why === "roof" || m.why === "cover" ? { propose: { c0: m.c0, c1: m.c1 } } : {}),
  };
}

const BAD_RULE: Record<Unbuildable["why"], RuleId> = {
  cover: "structure.cover.one_diameter_over_tubes",
  box: "structure.box.past_limit_unbuildable",
  roof: "station.type.box_roof_out_of_ground_unbuildable",
};

/** An unbuildable stretch (2173-2175): Raise for a box past its limit, else Lower and Propose fill. */
export function unbuildableFlag(b: Unbuildable): PortFlag {
  return {
    kind: `unbuildable_${b.why}`,
    page: "Unbuildable",
    sev: "error",
    c0: b.c0,
    c1: b.c1,
    c: (b.c0 + b.c1) / 2,
    rule: BAD_RULE[b.why],
    data: { why: b.why, worst: b.worst },
    fix: { mode: b.why === "box" ? "raise" : "lower", c0: b.c0, c1: b.c1 },
    ...(b.why !== "box" ? { propose: { c0: b.c0, c1: b.c1 } } : {}),
  };
}

/** The rules allIssues itself cites (the parts carry their own). */
export const ISSUES_RULES = [
  "era.grade.limit_by_phase",
  "era.grade.sustained_vs_local",
  "era.grade.steepest_between_bends",
  "clearance.crossing.structure_sum",
  "network.profile_set.crossings_apart",
  "clearance.context.blocks",
  "road.level_crossing",
  "road.trough_under_road_bridge",
  "road.clearance.by_class",
  "road.piers_out_of_roads",
  "network.canon.fixed_levels",
  "structure.paint.must_fit",
  "structure.cover.one_diameter_over_tubes",
  "structure.box.past_limit_unbuildable",
  "station.type.box_roof_out_of_ground_unbuildable",
] as const satisfies readonly RuleId[];

const keyOf = (f: PortFlag): string =>
  JSON.stringify([f.kind, f.page, f.sev, f.c0, f.c1, f.c, f.data, f.fix ?? null, f.clear ?? null, f.propose ?? null]);

/** The station flags the page pushed from designChecks, by its kind, in its order there (2087-2101). */
const PLATFORM_ORDER = ["Platform grade", "Platform curve", "Drawing", "Platform slide", "Platform overlap"] as const;

/**
 * allIssues (2143-2178) in the page's order, stable sorted by c, exact repeats removed. `half` is half a platform:
 * the range of a station's finding (the shallow canon). The clashes are the crossings with a clearance that are not
 * clear and the context blocks that are not clear (1920).
 */
export function allIssues(parts: IssueParts, opts: { readonly half: number } = { half: 0 }): PortFlag[] {
  const out: PortFlag[] = [];
  for (const o of parts.over) out.push(gradeFlag(o));
  for (const x of parts.crossings) if (x.clear != null && !x.ok) out.push(crossingFlag(x));
  for (const x of parts.context) if (!x.ok) out.push(contextFlag(x));
  out.push(...parts.rivers);
  for (const x of parts.roads) out.push(roadFlag(x));
  out.push(...parts.stations.filter((f) => f.page === "Access"));
  for (const f of parts.deepShallow) out.push(deepShallowFlag(f, opts.half));
  // the design checks with the station checks and the drawing checks where the page had them (2086-2101)
  const station = (page: string): PortFlag[] => [
    ...parts.stations.filter((f) => f.page === page),
    ...parts.checks.filter((f) => f.page === page),
  ];
  out.push(...parts.checks.filter((f) => f.page === "Vertical curve"));
  for (const p of PLATFORM_ORDER) out.push(...station(p));
  const placed = new Set<string>(["Vertical curve", ...PLATFORM_ORDER]);
  out.push(...parts.stations.filter((f) => f.page !== "Access" && !placed.has(f.page)));
  out.push(...parts.checks.filter((f) => !placed.has(f.page)));
  out.push(...parts.ground);
  for (const f of parts.types.flags) out.push({ ...f, c: (f.c0 + f.c1) / 2 });
  for (const m of parts.misfits) out.push(misfitFlag(m));
  for (const b of parts.types.bad) out.push(unbuildableFlag(b));
  const seen = new Set<string>();
  const kept = out.filter((f) => {
    const k = keyOf(f);
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  return kept
    .map((f, i) => [f, i] as const)
    .sort((a, b) => a[0].c - b[0].c || a[1] - b[1])
    .map(([f]) => f);
}
