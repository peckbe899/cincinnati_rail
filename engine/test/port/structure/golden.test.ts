// P1 types against the old page's goldens on the 16 Metro lines (claude/hub_maps/engine_port_plan.md, section 7.1):
// every output of section 6 equal within its tolerance or classed in ../classes.yaml, zero unexplained. Writes
// ../report/types.json, the package's report.

import { afterAll, describe, expect, test } from "vitest";
import { loadOldPage } from "../../golden/old_page/load.ts";
import { METRO_LINES } from "../from_golden.ts";
import { classes, classify, type OutputResult, reportOf, writeReport } from "../report.ts";
import { compareLine } from "./compare.ts";

const PKG = "types";
const byLine: Record<string, OutputResult[]> = {};

describe("P1 types against the old page", () => {
  const list = classes();

  test.each(METRO_LINES)("%s: every output equal or classed", (line) => {
    const { results } = compareLine(line);
    const classed = results.map((r) => classify(PKG, line, r, list));
    byLine[line] = classed;
    const unexplained = classed.filter((r) => r.class === "unexplained");
    expect(unexplained.map((r) => ({ output: r.output, first: r.differences.slice(0, 3) }))).toEqual([]);
    // the outputs the plan names are all compared, and every per-sample one covers the grid
    expect(classed.map((r) => r.output)).toEqual(
      expect.arrayContaining([
        "solved.t",
        "solved.tube",
        "solved.part",
        "solve.bad",
        "solve.approaches",
        "solve.flags",
        "misfits",
        "limit_tube",
        "limit_box",
        "struct",
        "type",
      ]),
    );
  });

  afterAll(() => {
    if (Object.keys(byLine).length === METRO_LINES.length) writeReport(reportOf(PKG, byLine));
  });
});

describe("the known differences, named", () => {
  test("mined station inside a cut-and-cover stretch: once per station, where the page pushed it per 2 m sample", () => {
    // rule fix station.type.mined_in_box_stretch_flagged (profiles.html 1517)
    let page = 0;
    let port = 0;
    let distinct = 0;
    for (const line of METRO_LINES) {
      const d = loadOldPage(line);
      const s = d.solve;
      if (!s) continue;
      const mined = s.flags.filter((f) => f.text.includes("is a mined station inside a cut-and-cover stretch"));
      page += mined.length;
      distinct += new Set(mined.map((f) => `${f.c0}|${f.c1}`)).size;
      const { solve } = compareLine(line);
      port += solve.flags.filter((f) => f.kind === "mined_in_box_stretch").length;
    }
    expect(port).toBe(distinct);
    expect(page).toBeGreaterThan(port);
    // only the raw count differs: on every line the set of (kind, c0, c1, severity) is equal (the test above)
    for (const line of METRO_LINES) {
      const raw = byLine[line]?.find((r) => r.output === "solve.flags.raw_count");
      if (raw?.differences.length) expect(raw.class).toBe("rule_fix");
    }
  });

  test("the plan's counts: 1,154 stretch flags on the page, 674 once each", () => {
    let page = 0;
    let distinct = 0;
    for (const line of METRO_LINES) {
      const s = loadOldPage(line).solve;
      if (!s) continue;
      page += s.flags.length;
      distinct += new Set(s.flags.map((f) => `${f.kind}|${f.c0}|${f.c1}|${f.text}`)).size;
    }
    expect([page, distinct]).toEqual([1154, 674]);
  });
});
