// P2 ground against the old page's goldens on the 16 Metro lines (claude/hub_maps/engine_port_plan.md, section 7.2):
// every output of section 6 equal within its tolerance or classed in ../classes.yaml, zero unexplained. Writes
// ../report/ground.json, the package's report.

import { afterAll, describe, expect, test } from "vitest";
import { METRO_LINES } from "../from_golden.ts";
import { classes, classify, type OutputResult, reportOf, writeReport } from "../report.ts";
import { compareLine } from "./compare.ts";

const PKG = "ground";
const byLine: Record<string, OutputResult[]> = {};

describe("P2 ground against the old page", () => {
  const list = classes();

  test.each(METRO_LINES)("%s: every output equal or classed", (line) => {
    const { results } = compareLine(line);
    const classed = results.map((r) => classify(PKG, line, r, list));
    byLine[line] = classed;
    const unexplained = classed.filter((r) => r.class === "unexplained");
    expect(unexplained.map((r) => ({ output: r.output, first: r.differences.slice(0, 3) }))).toEqual([]);
    expect(classed.map((r) => r.output)).toEqual(
      expect.arrayContaining([
        "ground.dem",
        "ground.regraded",
        "ground.finished",
        "ground.surface",
        "ground.bed",
        "gnd_cross",
        "canon.secs",
        "canon.locks",
        "rivers",
        "river_bridges",
        "sunk_box",
        "stations.ref",
        "viaduct_spans",
        "viaduct_spans.p1",
        "made_bed",
        "made_bed.p1",
      ]),
    );
  });

  afterAll(() => {
    if (Object.keys(byLine).length === METRO_LINES.length) writeReport(reportOf(PKG, byLine));
  });
});
