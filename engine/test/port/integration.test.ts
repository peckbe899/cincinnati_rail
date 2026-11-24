// The integration (claude/hub_maps/engine_port_plan.md, section 7.5): solveSection, the whole build order on the
// input alone (no golden intermediate laid in), gives the old page's answers on all 16 Metro lines. The input is the
// golden adapter's (the records as the page read them: the line file, the seed doc with its frame, the linked
// crossings and the neighbours as the page held them); everything downstream is computed here.
//
// Compared per line: the drawn type and the structure at every sample, the halls, the crossings, context and road
// findings, the summary's grades over, and the issues (as a multiset of page kind and severity, after the page's
// repeats are removed, less the station facts' own kinds, which station.facts@1 lists).

import { readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { chronologyOf, solveSection } from "../../src/port/model.ts";
import { unrle } from "../golden/old_page/load.ts";
import { distinctIssues } from "./checks/compare.ts";
import { sevOf } from "./checks/input.ts";
import { fromGolden, METRO_LINES, REPO } from "./from_golden.ts";
import { integrationInput } from "./integration_input.ts";

const STATION_KINDS = new Set(["Access", "Platform grade", "Platform curve", "Platform slide", "Platform overlap"]);

describe("section.solve on the input alone", () => {
  test.each(METRO_LINES)("%s: the old page's answers", (line) => {
    const { dump } = fromGolden(line);
    const out = solveSection(integrationInput(line));
    // the drawn type at every sample
    const want = unrle(dump.grid.type);
    const typeDiff = out.drawn.reduce((n, t, i) => n + (t === want[i] ? 0 : 1), 0);
    expect(typeDiff).toBe(0);
    // the structure at the rail
    const ws = unrle(dump.grid.struct);
    const structDiff = out.struct.reduce((n, s, i) => {
      const [k, b, t] = String(ws[i]).split("|");
      return n + (s.k === k && Math.abs(s.below - Number(b)) < 1e-6 && Math.abs(s.top - Number(t)) < 1e-6 ? 0 : 1);
    }, 0);
    expect(structDiff).toBe(0);
    // the halls
    const halls = dump.stations.flatMap((s) =>
      ((s.access as { halls?: [number, number][] }).halls ?? []).map(
        ([c0, c1]) => `${s.i}:${c0.toFixed(3)}:${c1.toFixed(3)}`,
      ),
    );
    expect(out.model.halls.map((h) => `${h.station}:${h.c0.toFixed(3)}:${h.c1.toFixed(3)}`)).toEqual(halls);
    // crossings, context, roads
    expect(out.crossings.map((x) => [x.c, x.ok, x.level])).toEqual(
      dump.crossings.map((x) => [x.c, !!(x as { ok?: boolean }).ok, !!(x as { level?: boolean }).level]),
    );
    expect(out.context.length).toBe(dump.context.length);
    expect(out.roads.length).toBe(dump.roads.length);
    // the summary's grades over
    expect(out.summary.over.map((o) => [o.c0, o.c1, o.sev])).toEqual(
      (dump.summary.over as { c0: number; c1: number; sev: string }[]).map((o) => [o.c0, o.c1, o.sev]),
    );
    // the issues, less the station facts' kinds
    const count = (keys: string[]): Record<string, number> => {
      const m: Record<string, number> = {};
      for (const k of keys) m[k] = (m[k] ?? 0) + 1;
      return m;
    };
    const page = distinctIssues(dump)
      .filter((x) => !STATION_KINDS.has(x.kind))
      .map((x) => `${x.kind}|${sevOf(x.sev)}`);
    const port = out.flags.filter((f) => !out.docFlags.includes(f)).map((f) => `${f.page}|${f.sev}`);
    expect(count(port)).toEqual(count(page));
  });
});

describe("the Chronology segments from the table", () => {
  const chr = JSON.parse(readFileSync(new URL("hub/seed/chronology/segments.json", REPO), "utf8")) as {
    segments: Record<string, { year?: number | null; phase?: string | null }>;
    phase_years: [number, number, string][];
  };
  test.each(METRO_LINES)("%s: chrSegments as the page", (line) => {
    const { dump, input } = fromGolden(line);
    const sys = line === "CVG_Express" ? "cvx" : "metro";
    const got = chronologyOf({ ...input, chronologyTable: { sys, ...chr } });
    expect(got).toEqual(dump.chr_segments);
  });
});
