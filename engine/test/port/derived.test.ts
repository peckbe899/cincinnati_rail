// The derived members the old page wrote into each doc on save (serialize, 3213-3229, R6): per live station its name,
// centre, drawn point, rail, ground, depth below the surface and type; and the line's summary (km of each type, the
// steepest grade, the grades over the limit). section.solve@1 gives them, the same on every Metro line as the page's
// own functions on its state (the golden dump), so the hub writes them as the page did, never as Ben's edits.

import { describe, expect, test } from "vitest";
import { solveSection } from "../../src/port/model.ts";
import { TYPE_CODES } from "../../src/port/types.ts";
import { solvedJson } from "../../src/port/wire.ts";
import { fromGolden, METRO_LINES } from "./from_golden.ts";
import { integrationInput } from "./integration_input.ts";

const r2 = (v: number): number => Math.round(v * 100) / 100;

describe("derived stations and summary, as serialize() wrote them", () => {
  test.each(METRO_LINES)("%s", (line) => {
    const { dump } = fromGolden(line);
    const input = integrationInput(line);
    const j = solvedJson(input, solveSection(input));
    const want = dump.stations.map((s) => ({
      name: s.name,
      c: s.c,
      point_c: s.point_c,
      rail: s.rail,
      ground: r2(s.ground as number),
      depth: r2((s.surface as number) - (s.rail as number)),
      type: s.type,
    }));
    expect(j.derived.stations).toEqual(want);
    const sm = dump.summary as { len: Record<string, number>; maxG: number; over: { sev: string }[] };
    expect(j.derived.summary).toEqual({
      km_by_type: Object.fromEntries(TYPE_CODES.map((t) => [t, Math.round(sm.len[t] ?? 0) / 1000])),
      max_grade_permille: Math.round(sm.maxG * 10) / 10,
      grades_over_limit: sm.over.filter((o) => o.sev === "error").length,
    });
  });
});
