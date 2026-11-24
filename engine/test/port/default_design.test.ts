// The default design of a line with no saved design (Lines 10, 11 and 13): the old page had no doc for them and drew
// defaultAlign's design (1756), its station levels and its river bend points. The hub keeps an empty profile record
// for each, so the solve gets a doc with no level and no bend point: it must solve the same default design, say so
// ("default design (not saved)"), and give it (levels and bend points) to whoever draws or crosses the line.

import { describe, expect, test } from "vitest";
import { solveSection } from "../../src/port/model.ts";
import type { PortDoc } from "../../src/port/types.ts";
import { solvedJson } from "../../src/port/wire.ts";
import { fromGolden } from "./from_golden.ts";
import { integrationInput } from "./integration_input.ts";

const EMPTY: PortDoc = {
  st: {},
  sg: {},
  so: {},
  del: [],
  pvi: [],
  ovr: [],
  stt: {},
  tf: [],
  shafts: [],
  gnd: [],
  gapfill: [],
  mode: {},
  ready: false,
  frame: null,
};

describe("a line with no saved design solves on its default design", () => {
  test.each(["Line_10", "Line_11", "Line_13"])("%s: an empty profile is the old page's no doc", (line) => {
    const { dump } = fromGolden(line);
    expect(dump.had_doc).toBe(false);
    const input = integrationInput(line);
    const none = solveSection({ ...input, doc: null });
    const empty = solveSection({ ...input, doc: EMPTY });
    // the old page's default levels and bend points (the river tubes' on Line 10)
    const want = dump.levels.default_align as { st: number[]; pvi: { c: number; z: number }[] };
    expect(empty.align.st).toEqual(want.st);
    expect(empty.align.pvi).toEqual(want.pvi);
    expect(empty.align.pvi).toEqual(none.align.pvi);
    expect(empty.drawn).toEqual(none.drawn);
    const j = solvedJson(input, empty);
    expect(j.design.source).toBe("default");
    expect(j.design.note).toBe("default design (not saved)");
    expect(j.design.pvi).toEqual(want.pvi);
    expect(j.design.defaulted).toEqual(input.platforms.map((p) => p.platform_id));
  });

  test("a saved design is Ben's: its bend points, none of the default's", () => {
    const input = integrationInput("Line_6");
    const out = solveSection(input);
    const j = solvedJson(input, out);
    expect(j.design.source).toBe("saved");
    expect(j.design.defaulted).toEqual([]);
    expect(j.design.pvi.length).toBe(input.doc?.pvi.length);
  });

  test("one level set on a line with no design: the rest stay default, and the design is partly default", () => {
    const input = integrationInput("Line_11");
    const first = input.platforms[0]?.platform_id as string;
    const out = solveSection({ ...input, doc: { ...EMPTY, st: { [first]: 150 } } });
    const j = solvedJson(input, out);
    expect(j.design.source).toBe("partial");
    expect(j.design.defaulted).not.toContain(first);
    expect(j.design.defaulted.length).toBe(input.platforms.length - 1);
  });
});

describe("a profile saved in an older frame (Line 2b) gives its design in the current one", () => {
  test("the reframed paints and frame come with the design, and laid in they solve the same rail", () => {
    const input = integrationInput("Line_2b");
    const out = solveSection(input);
    const j = solvedJson(input, out);
    expect(j.design.reframed).toBe(true);
    const rf = j.design.reframe;
    expect(rf).toBeTruthy();
    if (!rf || !input.doc) return;
    const doc = input.doc;
    expect(rf.frame.length_m).toBe(input.length);
    for (const p of input.platforms) expect(rf.frame.point_c[p.platform_id]).toBe(p.point_c);
    // the paints moved with the stations, as the bend points did
    expect(rf.ovr.length).toBe(doc.ovr.length);
    expect(rf.ovr).not.toEqual(doc.ovr.map((o) => [o[0], o[1], o[2]]));
    // the draft Ben's first edit makes: the design's bend points, slides and levels with the reframed fields
    const laid = solveSection({
      ...input,
      doc: {
        ...doc,
        pvi: j.design.pvi.map((p) => [p.c, p.z] as const),
        so: j.design.so,
        st: { ...doc.st, ...j.design.st },
        ovr: rf.ovr,
        tf: rf.tf,
        shafts: rf.shafts,
        gnd: rf.gnd,
        frame: rf.frame,
      },
    });
    const k = solvedJson(input, laid);
    expect(k.design.reframed).toBe(false);
    expect(k.design.reframe).toBeNull();
    expect(k.design.pvi).toEqual(j.design.pvi);
    expect(laid.drawn).toEqual(out.drawn);
  });

  test("a profile in its own frame has no reframe", () => {
    const input = integrationInput("Line_6");
    expect(solvedJson(input, solveSection(input)).design.reframe).toBeNull();
  });
});
