// P3 crossings, context and roads against the old page's goldens on the 16 Metro lines (claude/hub_maps/
// engine_port_plan.md, section 7.3): the 430 crossings, the 10 context clearances, the 81 road findings and every
// station's street within the tolerances of section 6, zero unexplained, on the old page's own type solve (goldenTypes)
// and on P1's (TYPES_MODULE on solveTypes), which must agree. Writes ../report/crossings.json.

import { readFileSync } from "node:fs";
import { afterAll, describe, expect, test } from "vitest";
import { crossingClearances } from "../../../src/port/crossings/index.ts";
import { loadOldPage } from "../../golden/old_page/load.ts";
import { goldenTypes, METRO_LINES, REPO } from "../from_golden.ts";
import { classes, classify, type OutputResult, reportOf, writeReport } from "../report.ts";
import { compareLine, MM } from "./compare.ts";
import { crossingInput, crossingModel, linkedCrossings, neighbourOf } from "./neighbours.ts";

const PKG = "crossings";
/** Equal rails: the same doc gives the same doubles. */
const SAME_M = 1e-6;
/** The largest difference the mixed frames make on the seed, to the cm. */
const WORST_M = 1.04;
const byLine: Record<string, OutputResult[]> = {};

const OUTPUTS = [
  "crossings.list",
  "crossings.source",
  "crossings.zo",
  "crossings.z",
  "crossings.clear",
  "crossings.need",
  "crossings.meUp",
  "crossings.level",
  "crossings.ok",
  "crossings.t",
  "crossings.to",
  "crossings.hall",
  "crossings.pending",
  "context.list",
  "context.c",
  "context.clear",
  "context.need",
  "context.short",
  "context.level",
  "context.ok",
  "roads.set",
  "roads.road",
  "roads.clear",
  "roads.need",
  "streets.street",
  "streets.roads",
  "streets.text",
];

describe("P3 crossings against the old page", () => {
  const list = classes();

  test.each(METRO_LINES)("%s: every output equal or classed (the page's type solve)", (line) => {
    const { results } = compareLine(line, "golden");
    const classed = results.map((r) => classify(PKG, line, r, list));
    byLine[line] = classed;
    const unexplained = classed.filter((r) => r.class === "unexplained");
    expect(unexplained.map((r) => ({ output: r.output, first: r.differences.slice(0, 3) }))).toEqual([]);
    expect(classed.map((r) => r.output)).toEqual(expect.arrayContaining(OUTPUTS));
  });

  test.each(METRO_LINES)("%s: the same on P1's own type solve, and the two agree", (line) => {
    const p1 = compareLine(line, "p1");
    const unexplained = p1.results.map((r) => classify(PKG, line, r, list)).filter((r) => r.class === "unexplained");
    expect(unexplained.map((r) => ({ output: r.output, first: r.differences.slice(0, 3) }))).toEqual([]);
    const page = compareLine(line, "golden");
    expect(p1.crossings).toEqual(page.crossings);
    expect(p1.context).toEqual(page.context);
    expect(p1.roads).toEqual(page.roads);
    expect(p1.streets).toEqual(page.streets);
  });

  test("the plan's counts: 430 crossings (395 saved profiles, 35 metro_rails), 10 context, 81 roads", () => {
    let crossings = 0;
    let saved = 0;
    let rails = 0;
    let context = 0;
    let roads = 0;
    let stations = 0;
    for (const line of METRO_LINES) {
      const r = compareLine(line, "golden");
      crossings += r.crossings.length;
      saved += r.crossings.filter((x) => x.source === "profile").length;
      rails += r.crossings.filter((x) => x.source === "metro_rails").length;
      context += r.context.length;
      roads += r.roads.length;
      stations += r.streets.length;
      expect(r.streets.length).toBe(loadOldPage(line).stations.length);
    }
    expect({ crossings, saved, rails, context, roads }).toEqual({
      crossings: 430,
      saved: 395,
      rails: 35,
      context: 10,
      roads: 81,
    });
    expect(stations).toBeGreaterThan(0);
  });

  afterAll(() => {
    if (Object.keys(byLine).length === METRO_LINES.length) writeReport(reportOf(PKG, byLine));
  });
});

describe("faults of the old page the adapter keeps, named", () => {
  test("the page read 53 neighbours with their bend points reframed and their stations not (S.saved mutated)", () => {
    // refreshDefaultDocs (3385) ran alignFromDoc on every RER line's saved profile, and a Metro line's load on its own:
    // reframeDoc (1839) mapped the saved object's bend points into the route's current frame in place, but not its
    // derived stations, which otherRail (2185) reads. The adapter reproduces that doc (reframedAsThePageHeldIt). With
    // the profile as saved (one frame) the other rail differs on these crossings; production builds the neighbour in
    // one frame (its live stations and its bend points by its frame record), so the hub's answer will differ here.
    let mixed = 0;
    let overMm = 0;
    let okChanged = 0;
    let worst = 0;
    const wids = new Set<string>();
    for (const line of METRO_LINES) {
      const d = loadOldPage(line);
      const m = crossingModel(line);
      const asSaved = { ...crossingInput(line), neighbours: { ...crossingInput(line).neighbours } };
      for (const wid of Object.keys(asSaved.neighbours)) {
        const n = neighbourOf(d, wid, true);
        if (n) asSaved.neighbours[wid] = n;
      }
      const T = goldenTypes(d);
      const held = crossingClearances(m, T);
      const saved = crossingClearances({ ...m, input: asSaved }, T);
      held.forEach((x, i) => {
        const y = saved[i];
        if (!y || x.zo == null || y.zo == null) return;
        const diff = Math.abs(x.zo - y.zo);
        if (diff > SAME_M) {
          mixed++;
          wids.add(x.wid);
          worst = Math.max(worst, diff);
          if (diff > MM) overMm++;
          if (x.ok !== y.ok) okChanged++;
        }
      });
    }
    // 53 crossings, 46 of them by more than the 1 mm tolerance, up to 1.04 m; the check's verdict changes on 1
    expect({ mixed, overMm, okChanged, worst: Math.round(worst * 100) / 100 }).toEqual({
      mixed: 53,
      overMm: 46,
      okChanged: 1,
      worst: WORST_M,
    });
    expect([...wids].every((w) => w.startsWith("RER_") || w === "Line_2b")).toBe(true);
  });

  test("35 crossings with Lines 10, 11 and 13 read the stale rer/metro_rails.json, never marked set", () => {
    let n = 0;
    for (const line of METRO_LINES)
      for (const x of compareLine(line, "golden").crossings)
        if (x.source === "metro_rails") {
          n++;
          expect(["Line_10", "Line_11", "Line_13"]).toContain(x.wid);
          expect(x.pending).toBe(true);
        }
    expect(n).toBe(35);
  });

  test("no line is marked set on the seed: every crossing is listed apart (network.profile_set.crossings_apart)", () => {
    for (const line of METRO_LINES) for (const x of compareLine(line, "golden").crossings) expect(x.pending).toBe(true);
  });

  test("214 RER crossings are not in the Metro line files: the page linked them from the RER files (3395)", () => {
    // the hub's section records hold the line file's crossings only: the lead's input builder must link these
    let linked = 0;
    let rer = 0;
    for (const line of METRO_LINES) {
      const all = linkedCrossings(line);
      rer += all.filter((x) => x.wid.startsWith("RER_")).length;
      linked += all.length - crossingsInFile(line);
    }
    expect(rer).toBe(214);
    expect(linked).toBe(214);
  });
});

function crossingsInFile(line: string): number {
  return ((loadLineFile(line).crossings ?? []) as { wid?: string; oc?: number }[]).filter((x) => x.wid && x.oc != null)
    .length;
}

function loadLineFile(line: string): { crossings?: unknown[] } {
  return JSON.parse(readFileSync(new URL(`data/profile/lines/${line}.json`, REPO), "utf8")) as {
    crossings?: unknown[];
  };
}
