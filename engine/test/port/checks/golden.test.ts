// P4 checks and levels against the old page's goldens on the 16 Metro lines (claude/hub_maps/engine_port_plan.md,
// section 7.4): every output of section 6 equal within its tolerance or classed in ../classes.yaml, zero
// unexplained. Writes ../report/checks.json, the package's report.

import { afterAll, describe, expect, test } from "vitest";
import { reframeDoc } from "../../../src/port/levels/index.ts";
import type { PortDoc } from "../../../src/port/types.ts";
import { loadOldPage } from "../../golden/old_page/load.ts";
import { fromGolden, METRO_LINES } from "../from_golden.ts";
import { classes, classify, type OutputResult, reportOf, writeReport } from "../report.ts";
import { compareLine, distinctIssues, issueKey } from "./compare.ts";
import { levelInput } from "./input.ts";

const PKG = "checks";
const byLine: Record<string, OutputResult[]> = {};

/** The outputs the plan names for P4 (section 7.4), each compared on every line. */
const OUTPUTS = [
  "radii",
  "allowance",
  "drawing",
  "gnd_checks",
  "curve_grade",
  "design.checks",
  "design.sumps",
  "summary.len",
  "summary.extremes",
  "summary.over",
  "summary.deepShallow",
  "summary.rivers",
  "issues.kinds",
  "issues.ranges",
  "issues.raw_count",
  "levels.default_align",
  "align",
  "levels.reset",
  "stations",
  "levels.reframe",
  "propose_fill",
];

describe("P4 checks and levels against the old page", () => {
  const list = classes();

  test.each(METRO_LINES)("%s: every output equal or classed", (line) => {
    const { results } = compareLine(line);
    const classed = results.map((r) => classify(PKG, line, r, list));
    byLine[line] = classed;
    const unexplained = classed.filter((r) => r.class === "unexplained");
    expect(unexplained.map((r) => ({ output: r.output, first: r.differences.slice(0, 3) }))).toEqual([]);
    expect(classed.map((r) => r.output)).toEqual(OUTPUTS);
  });

  afterAll(() => {
    if (Object.keys(byLine).length === METRO_LINES.length) writeReport(reportOf(PKG, byLine));
  });
});

describe("the plan's counts", () => {
  test("2,172 issues on the page, 118 Propose fill proposals; the port lists each finding once", () => {
    let page = 0;
    let distinct = 0;
    let port = 0;
    let fills = 0;
    for (const line of METRO_LINES) {
      const d = loadOldPage(line);
      page += d.issues.length;
      distinct += distinctIssues(d).length;
      fills += d.levels.propose_fill.length;
      port += compareLine(line).issues.length;
    }
    expect([page, fills]).toEqual([2172, 118]);
    expect(port).toBe(distinct);
  });

  test("every port finding cites a registry rule and carries its page kind", () => {
    for (const line of METRO_LINES) {
      const { issues } = compareLine(line);
      for (const f of issues) {
        expect(f.rule, `${line} ${f.kind}`).toMatch(/^[a-z_]+(\.[a-z0-9_]+)+$/);
        expect(f.page.length).toBeGreaterThan(0);
      }
    }
  });
});

describe("the known differences, named", () => {
  test("issues raw count: the page listed the mined-station flag per 2 m sample (Lines 4, 6 and 12)", () => {
    // rule fix station.type.mined_in_box_stretch_flagged (profiles.html 1517, 2171)
    const differ: string[] = [];
    for (const line of METRO_LINES) {
      const d = loadOldPage(line);
      const raw =
        byLine[line]?.find((r) => r.output === "issues.raw_count") ??
        compareLine(line).results.find((r) => r.output === "issues.raw_count");
      if (raw?.differences.length) {
        differ.push(line);
        const repeats = d.issues.length - distinctIssues(d).length;
        expect(repeats).toBeGreaterThan(0);
        // every repeat is the mined-station note of the solve
        const seen = new Set<string>();
        for (const x of d.issues) {
          const k = issueKey(x);
          if (seen.has(k)) expect(x.text).toContain("is a mined station inside a cut-and-cover stretch");
          seen.add(k);
        }
      }
    }
    expect(differ).toEqual(["Line_4", "Line_6", "Line_12"]);
  });

  test("Line 2b reframe: the dump reframed a doc already reframed on load; the port's reframe is idempotent", () => {
    // rule fix platform.tie.saved_profile_own_frame (profiles.html 1839-1868, 1873)
    const input = levelInput("Line_2b");
    const doc = input.doc as PortDoc;
    const once = reframeDoc(doc, input.platforms, input.length);
    expect(once.changed).toBe(true);
    // once: the page's align on load (Line 2b's first bend 242 m saved, 244.5 m on the current points)
    const { dump } = fromGolden("Line_2b");
    expect(once.doc.pvi.map(([c]) => c)).toEqual(dump.align.pvi.map((p) => p.c));
    expect(once.doc.ovr).toEqual(dump.align.ovr);
    // the port's second call changes nothing: the doc carries the frame it was mapped to
    expect(reframeDoc(once.doc, input.platforms, input.length).changed).toBe(false);
    // the page's second call: the old points kept, so it maps again, which is what the dump holds
    const twice = reframeDoc({ ...once.doc, frame: doc.frame }, input.platforms, input.length);
    const want = dump.levels.reframe as unknown as { pvi: [number, number][]; ovr: [number, number, string][] };
    expect(twice.doc.pvi).toEqual(want.pvi);
    expect(twice.doc.ovr).toEqual(want.ovr);
  });
});
