// P3's outputs against the old page's goldens, output by output, within the tolerances of section 6 of
// claude/hub_maps/engine_port_plan.md: crossings (zo, z, clear, need 1 mm; meUp, level, ok exact; t.k, to.k exact,
// below and top 1e-6 m), context clearances (c exact; z 1 mm; clear, need, short 1 mm; ok, level exact), roads (the
// set of kind, severity, c exact; clear and need 1 cm, as the page printed them) and every station's street.

import {
  CROSSINGS_RULES,
  contextClearances,
  crossingClearances,
  roadChecks,
  stationStreet,
} from "../../../src/port/crossings/index.ts";
import { TYPES_MODULE } from "../../../src/port/structure/index.ts";
import type {
  ContextClearance,
  CrossingClearance,
  RoadCheck,
  StationStreet,
  Structure,
  TypedModel,
  TypesModule,
} from "../../../src/port/types.ts";
import { loadOldPage, type OldPageDump } from "../../golden/old_page/load.ts";
import { goldenTypes } from "../from_golden.ts";
import type { Difference, OutputResult } from "../report.ts";
import { crossingModel } from "./neighbours.ts";

export const MM = 1e-3;
export const STRUCT_TOL = 1e-6;
/** The page printed road clearances to the cm: a difference within half of that is the print's. */
export const ROAD_PRINT_TOL = 0.005 + 1e-9;
const MAX_LISTED = 20;

type Num = number | null | undefined;
const near = (a: Num, b: Num, tol: number): boolean =>
  a == null || b == null ? a == null && b == null : Math.abs(a - b) <= tol || (Number.isNaN(a) && Number.isNaN(b));

/** A field compared over a list of pairs: the differing items (first MAX_LISTED listed, all counted). */
function field<P, Q>(
  output: string,
  pairs: readonly (readonly [P, Q, string])[],
  same: (p: P, q: Q) => boolean,
  show: (p: P, q: Q) => [unknown, unknown],
): OutputResult {
  const differences: Difference[] = [];
  let count = 0;
  for (const [p, q, at] of pairs) {
    if (same(p, q)) continue;
    count++;
    if (differences.length < MAX_LISTED) {
      const [a, b] = show(p, q);
      differences.push({ at, page: a, port: b });
    }
  }
  if (count > MAX_LISTED) differences.push({ at: `${count - MAX_LISTED} more`, page: null, port: null });
  return { output, compared: pairs.length, differences };
}

/** Two lists of keys as multisets: what only one side has. */
function keys(output: string, page: readonly string[], port: readonly string[]): OutputResult {
  const left = new Map<string, number>();
  for (const k of page) left.set(k, (left.get(k) ?? 0) + 1);
  const differences: Difference[] = [];
  for (const k of port) {
    const n = left.get(k) ?? 0;
    if (n > 0) left.set(k, n - 1);
    else differences.push({ at: k, page: null, port: k });
  }
  for (const [k, n] of left) for (let i = 0; i < n; i++) differences.push({ at: k, page: k, port: null });
  return { output, compared: Math.max(page.length, port.length), differences };
}

interface PageStruct {
  k: string;
  below: number;
  top: number;
  label?: string;
}
type PageCrossing = OldPageDump["crossings"][number] & {
  clear: number | null;
  need?: number;
  meUp?: boolean;
  level?: boolean;
  ok?: boolean;
  t?: PageStruct;
  to?: PageStruct;
};
type PageContext = OldPageDump["context"][number] & {
  zo: number;
  z: number;
  clear: number;
  need: number;
  short: number;
  meUp: boolean;
  level: boolean;
  t: PageStruct;
  to: PageStruct;
};

const structSame = (
  a: PageStruct | undefined | null,
  b: Structure | { k: string; below: number; top: number } | null,
) => (!a || !b ? !a && !b : a.k === b.k && near(a.below, b.below, STRUCT_TOL) && near(a.top, b.top, STRUCT_TOL));
const structShow = (s: PageStruct | Structure | { k: string; below: number; top: number } | null | undefined) =>
  s ? `${s.k}|${s.below}|${s.top}` : null;

/** The page's source name for a neighbour source. */
const SOURCE: Record<string, string> = { profile: "saved", default: "default", metro_rails: "metro_rails" };

export function compareCrossings(d: OldPageDump, port: readonly CrossingClearance[]): OutputResult[] {
  const page = d.crossings as PageCrossing[];
  const key = (x: { c: number; wid: string; oc: number }): string => `${x.c}|${x.wid}|${x.oc}`;
  const out: OutputResult[] = [keys("crossings.list", page.map(key), port.map(key))];
  // in order, as the page listed them (the same order: both sort the linked list by chainage)
  const pairs: [PageCrossing, CrossingClearance, string][] = page
    .map((p, i) => [p, port[i] as CrossingClearance, key(p)] as [PageCrossing, CrossingClearance, string])
    .filter(([p, q]) => q && key(p) === key(q));
  out.push(
    field(
      "crossings.source",
      pairs,
      (p, q) => p.source === (q.source ? SOURCE[q.source] : null),
      (p, q) => [p.source, q.source],
    ),
    field(
      "crossings.zo",
      pairs,
      (p, q) => near(p.zo, q.zo, MM),
      (p, q) => [p.zo, q.zo],
    ),
    field(
      "crossings.z",
      pairs,
      (p, q) => near(p.z as number, q.z, MM),
      (p, q) => [p.z, q.z],
    ),
    field(
      "crossings.clear",
      pairs,
      (p, q) => near(p.clear, q.clear, MM),
      (p, q) => [p.clear, q.clear],
    ),
    field(
      "crossings.need",
      pairs,
      (p, q) => near(p.need, q.need, MM),
      (p, q) => [p.need, q.need],
    ),
    field(
      "crossings.meUp",
      pairs,
      (p, q) => !!p.meUp === q.meUp,
      (p, q) => [p.meUp, q.meUp],
    ),
    field(
      "crossings.level",
      pairs,
      (p, q) => !!p.level === q.level,
      (p, q) => [p.level, q.level],
    ),
    field(
      "crossings.ok",
      pairs,
      (p, q) => !!p.ok === q.ok,
      (p, q) => [p.ok, q.ok],
    ),
    field(
      "crossings.t",
      pairs,
      (p, q) => structSame(p.t, q.t),
      (p, q) => [structShow(p.t), structShow(q.t)],
    ),
    field(
      "crossings.to",
      pairs,
      (p, q) => structSame(p.to, q.to),
      (p, q) => [structShow(p.to), structShow(q.to)],
    ),
    field(
      "crossings.hall",
      pairs,
      (p, q) => (p.t?.label === "box and hall") === (q.hall !== undefined),
      (p, q) => [p.t?.label, q.hall ?? null],
    ),
  );
  // the listing: a clash with a line not marked set is listed apart (allIssues 2154, grp pending)
  const clashes = pairs.filter(([p]) => p.clear != null && !p.ok);
  const grpOf = new Map<number, string | null>();
  for (const is of d.issues) if (is.kind === "Clearance") grpOf.set(is.c, is.grp);
  out.push(
    field(
      "crossings.pending",
      clashes,
      (p, q) => (grpOf.get(p.c) === "pending") === q.pending,
      (p, q) => [grpOf.get(p.c), q.pending],
    ),
  );
  out.push(
    field(
      "crossings.rule",
      pairs,
      (_p, q) => !q.rule || (CROSSINGS_RULES as readonly string[]).includes(q.rule),
      (_p, q) => [null, q.rule],
    ),
  );
  return out;
}

export function compareContext(d: OldPageDump, port: readonly ContextClearance[]): OutputResult[] {
  const page = d.context as PageContext[];
  const out: OutputResult[] = [
    keys(
      "context.list",
      page.map((p) => `${p.block}|${p.c}`),
      port.map((q) => `${q.block}|${q.c}`),
    ),
  ];
  const pairs: [PageContext, ContextClearance, string][] = page
    .map((p, i) => [p, port[i] as ContextClearance, `block ${p.block}`] as [PageContext, ContextClearance, string])
    .filter(([p, q]) => q && p.block === q.block);
  out.push(
    field(
      "context.c",
      pairs,
      (p, q) => p.c === q.c,
      (p, q) => [p.c, q.c],
    ),
    field(
      "context.zo",
      pairs,
      (p, q) => near(p.zo, q.zo, MM),
      (p, q) => [p.zo, q.zo],
    ),
    field(
      "context.z",
      pairs,
      (p, q) => near(p.z, q.z, MM),
      (p, q) => [p.z, q.z],
    ),
    field(
      "context.clear",
      pairs,
      (p, q) => near(p.clear, q.clear, MM),
      (p, q) => [p.clear, q.clear],
    ),
    field(
      "context.need",
      pairs,
      (p, q) => near(p.need, q.need, MM),
      (p, q) => [p.need, q.need],
    ),
    field(
      "context.short",
      pairs,
      (p, q) => near(p.short, q.short, MM),
      (p, q) => [p.short, q.short],
    ),
    field(
      "context.meUp",
      pairs,
      (p, q) => p.meUp === q.meUp,
      (p, q) => [p.meUp, q.meUp],
    ),
    field(
      "context.level",
      pairs,
      (p, q) => p.level === q.level,
      (p, q) => [p.level, q.level],
    ),
    field(
      "context.ok",
      pairs,
      (p, q) => p.ok === q.ok,
      (p, q) => [p.ok, q.ok],
    ),
    field(
      "context.t",
      pairs,
      (p, q) => structSame(p.t, q.t),
      (p, q) => [structShow(p.t), structShow(q.t)],
    ),
    field(
      "context.to",
      pairs,
      (p, q) => structSame(p.to, q.to),
      (p, q) => [structShow(p.to), structShow(q.to)],
    ),
  );
  return out;
}

/** The page's road finding as (kind, the numbers it printed). */
export function pageRoad(r: OldPageDump["roads"][number]): { kind: RoadCheck["kind"]; clear?: number; need?: number } {
  if (r.pier) return { kind: "pier_in_road" };
  if (r.text.startsWith("level crossing with")) return { kind: "level_crossing" };
  const trough =
    /needs a bridge over it, ([\d.]+) m from the rail to the street .* and the rail is ([\d.-]+) down/.exec(r.text);
  if (trough) return { kind: "trough_under_road", need: Number(trough[1]), clear: Number(trough[2]) };
  const over = /^([\d.-]+) m over .* needs ([\d.]+):/.exec(r.text);
  if (over) return { kind: "clearance_over_road", clear: Number(over[1]), need: Number(over[2]) };
  throw new Error(`a road finding the comparison cannot read: ${r.text}`);
}

export function compareRoads(d: OldPageDump, m: TypedModel, port: readonly RoadCheck[]): OutputResult[] {
  const sev = (s: string): string => (s === "note" ? "info" : s);
  const page = d.roads.map((r) => ({ r, ...pageRoad(r) }));
  const key = (kind: string, s: string, c: number): string => `${kind}|${s}|${c}`;
  const out: OutputResult[] = [
    keys(
      "roads.set",
      page.map((p) => key(p.kind, sev(p.r.sev), p.r.c)),
      port.map((q) => key(q.kind, q.sev, q.c)),
    ),
  ];
  const roads = m.input.context.roads;
  const pairs: [(typeof page)[number], RoadCheck, string][] = page
    .map((p, i) => [p, port[i] as RoadCheck, `${p.kind} at ${p.r.c}`] as [(typeof page)[number], RoadCheck, string])
    .filter(([p, q]) => q && p.kind === q.kind && p.r.c === q.c);
  out.push(
    field(
      "roads.road",
      pairs,
      (p, q) => JSON.stringify(p.r.road) === JSON.stringify(roads[q.road]),
      (p, q) => [p.r.road, roads[q.road]],
    ),
    field(
      "roads.clear",
      pairs,
      (p, q) => near(p.clear, q.clear, ROAD_PRINT_TOL),
      (p, q) => [p.clear, q.clear],
    ),
    field(
      "roads.need",
      pairs,
      (p, q) => near(p.need, q.need, ROAD_PRINT_TOL),
      (p, q) => [p.need, q.need],
    ),
  );
  return out;
}

/** The page's words for a station's street (stationStreet 461), from the port's indexes: the sheet's to word. */
export function streetText(m: TypedModel, s: StationStreet): string {
  const ctx = m.input.context;
  const st = s.street >= 0 ? ctx.streets[s.street] : undefined;
  if (st) return `under ${st[3]}${s.subway ? " (built over the subway)" : ""}`;
  if (s.roads.length) return `crosses ${s.roads.map((i) => ctx.roads[i]?.[4]).join(", ")}`;
  return s.known ? "not under a street" : "no streets known here";
}

export function compareStreets(d: OldPageDump, m: TypedModel, port: readonly StationStreet[]): OutputResult[] {
  const ctx = m.input.context;
  const pairs = d.stations.map((s, i) => [s.street, port[i] as StationStreet, s.key] as const);
  return [
    field(
      "streets.street",
      pairs,
      (p, q) => JSON.stringify(p.street) === JSON.stringify(q.street >= 0 ? ctx.streets[q.street] : null),
      (p, q) => [p.street, q.street],
    ),
    field(
      "streets.roads",
      pairs,
      (p, q) => JSON.stringify(p.roads) === JSON.stringify(q.roads.map((i) => ctx.roads[i])),
      (p, q) => [p.roads, q.roads],
    ),
    field(
      "streets.text",
      pairs,
      (p, q) => p.text === streetText(m, q),
      (p, q) => [p.text, streetText(m, q)],
    ),
  ];
}

export interface LineCompare {
  results: OutputResult[];
  crossings: CrossingClearance[];
  context: ContextClearance[];
  roads: RoadCheck[];
  streets: StationStreet[];
}

/** Every P3 output of one line against its golden, on a typed model and a TypesModule. */
export function compareLine(line: string, solve: "golden" | "p1" = "golden", T?: TypesModule): LineCompare {
  const d = loadOldPage(line);
  const m = crossingModel(line, solve);
  const types = T ?? (solve === "golden" ? goldenTypes(d) : TYPES_MODULE);
  const crossings = crossingClearances(m, types);
  const context = contextClearances(m, types);
  const roads = roadChecks(m, types);
  const streets = m.stations.map((s) => stationStreet(m, s));
  return {
    results: [
      ...compareCrossings(d, crossings),
      ...compareContext(d, context),
      ...compareRoads(d, m, roads),
      ...compareStreets(d, m, streets),
    ],
    crossings,
    context,
    roads,
    streets,
  };
}
