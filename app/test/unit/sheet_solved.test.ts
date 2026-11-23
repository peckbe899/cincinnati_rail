// The line sheet's bands from section.solve@1 (app/src/plugins/line-sheet/solved.ts) and the draft swap of its input
// (model.ts solveInputOf): the lookups, the words, the Chronology segments, and what each band draws from a solve.

import type { SectionSolveInput, SolvedSection } from "@cr/engine/contract";
import { describe, expect, it } from "vitest";
import type { BandData, SheetMark, SheetView } from "../../src/core/plugin.ts";
import { Units } from "../../src/core/units.ts";
import { readoutLines } from "../../src/plugins/line-sheet/bands.ts";
import { valueAt } from "../../src/plugins/line-sheet/drawing.ts";
import { hasDesign, solveInputOf } from "../../src/plugins/line-sheet/model.ts";
import {
  chronologyOf,
  clearanceColour,
  clearanceText,
  crossingsBand,
  crossingTag,
  curveGradeBand,
  flagWords,
  issuesBand,
  issueText,
  labelSpots,
  outlinesBand,
  roadsBand,
  runAt,
  sampleAt,
  structureStripBand,
  structWord,
  typeAtSample,
  waterBand,
  wordsIn,
} from "../../src/plugins/line-sheet/solved.ts";

describe("lookups", () => {
  const runs = [
    ["shield", 0, 100],
    ["cutcover", 100, 250],
    ["elevated", 250, 300],
  ] as const;
  it("runAt finds the run holding c, the last past the end", () => {
    expect(runAt(runs, 0)?.[0]).toBe("shield");
    expect(runAt(runs, 99.9)?.[0]).toBe("shield");
    expect(runAt(runs, 100)?.[0]).toBe("cutcover");
    expect(runAt(runs, 300)?.[0]).toBe("elevated");
    expect(runAt([], 3)).toBeNull();
  });
  it("sampleAt interpolates and keeps nulls as gaps", () => {
    expect(sampleAt([1, 3, null], 2, 1)).toBe(2);
    expect(sampleAt([1, 3, null], 2, 4)).toBeNull();
    expect(sampleAt([1, null], 2, 1)).toBe(1);
  });
});

describe("words", () => {
  it("tags a crossing line as the old page did", () => {
    expect(crossingTag("Line 3")).toBe("L3");
    expect(crossingTag("CVG Express")).toBe("CVG");
    expect(crossingTag("E trunk")).toBe("E trunk");
  });
  it("names the other structure and writes the clearance", () => {
    const tubes = { A: { label: "type A tube (cast iron, bench walls)" } };
    expect(structWord({ k: "tube", tube: "A" }, tubes)).toBe("type A tube (cast iron, bench walls)");
    expect(structWord({ k: "box" }, tubes)).toBe("box");
    const t = clearanceText(
      { with: "Line 3", to: { k: "box" }, clear: 7.31, need: 6.1 },
      tubes,
      (m) => `${m.toFixed(1)} m`,
    );
    expect(t).toBe("Line 3 box · 7.3 m apart, needs 6.1 m");
  });
  it("words a finding as the old page did, with its numbers and its rule", () => {
    const f = {
      kind: "crossing_short",
      page: "Clearance",
      sev: "error",
      c0: 7752.1,
      c1: 7752.1,
      c: 7752.1,
      rule: "clearance.crossing.structure_sum",
      data: { with: "Line 8", clear: 2.6236, need: 6.1, meUp: false, t: { k: "box" }, to: { k: "box" } },
    } as SolvedSection["flags"][number];
    const w = wordsIn(new Units("m"));
    expect(flagWords(f, w)).toBe(
      "Clearance: 2.62 m under Line 8 at 7+752; needs 6.10 m (box over box) (clearance.crossing.structure_sum)",
    );
    // in feet, as the old page with its units in feet (toU)
    expect(issueText(f, wordsIn(new Units("ft")))).toBe("8.61 ft under Line 8 at 7+752; needs 20.01 ft (box over box)");
    // a box station's crossing is checked over its hall (2241); an RER bored tube has no tube key (structFor 1214)
    expect(issueText({ ...f, data: { ...f.data, hall: 3, to: { k: "bore" } } }, w)).toBe(
      "2.62 m under Line 8 at 7+752; needs 6.10 m (bored tube over box and hall)",
    );
    expect(flagWords({ ...f, kind: "something_new", data: {} }, w)).toBe(
      "Clearance: something new (clearance.crossing.structure_sum)",
    );
  });
});

const ssi = {
  contract: "section_solve_input/0",
  section_id: "S",
  route: "Line_9",
  system: "metro",
  length: 3000,
  step: 2,
  platforms: [
    {
      platform_id: "P1",
      key: "A",
      name: "A",
      order: 0,
      point_c: 100,
      side: "side",
      year: 1920,
      yearPhase: "1",
      transferAtOpen: false,
      trunk: false,
    },
    {
      platform_id: "P2",
      key: "B",
      name: "B",
      order: 1,
      point_c: 1500,
      side: "side",
      year: null,
      yearPhase: null,
      transferAtOpen: false,
      trunk: false,
    },
    {
      platform_id: "P3",
      key: "C",
      name: "C",
      order: 2,
      point_c: 2900,
      side: "island",
      year: null,
      yearPhase: null,
      transferAtOpen: false,
      trunk: false,
    },
  ],
  doc: {
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
    frame: { length_m: 3000, point_c: { P1: 100 } },
  },
  settings: { pool: 138.68, riverFlatTol: 1, riverClearWater: 3.66 },
  structure: { tubes: { A: { label: "type A tube" } }, subway_streets: [] },
  chronologyTable: { sys: "metro", segments: { "metro|Line_9|A|B": { year: 1920 } }, phase_years: [[1900, 1930, "1"]] },
} as unknown as SectionSolveInput;

describe("the Chronology band", () => {
  it("runs between the route's stations at their drawn points, the phase from the year", () => {
    expect(chronologyOf(ssi)).toEqual([
      { key: "metro|Line_9|A|B", c0: 0, c1: 1500, year: 1920, phase: "1", set: true },
      { key: "metro|Line_9|B|C", c0: 1500, c1: 3000, year: null, phase: null, set: false },
    ]);
  });
});

describe("solveInputOf: the draft's profile into the solve", () => {
  it("swaps in the draft's fields, keyed by platform id, and a side from its draft", () => {
    const out = solveInputOf(
      ssi,
      {
        section: "S",
        st: { P1: 150.2, P2: null, P3: "x" },
        sg: { P1: 2 },
        pvi: [[500, 160], { c_m: 900, z_m: 158 }],
        ovr: [[10, 20, "bored"]],
        del: ["P2"],
        access: { P1: { type: "end_halls" } },
        tf: [[0, 50, "twin"]],
        shafts: [700],
      } as never,
      (pid) => (pid === "P3" ? { side: "side", source: "ben" } : null),
    );
    expect(out.doc?.st).toEqual({ P1: 150.2, P2: null });
    expect(out.doc?.pvi).toEqual([
      [500, 160],
      [900, 158],
    ]);
    expect(out.doc?.ovr).toEqual([[10, 20, "shield"]]);
    expect(out.doc?.del).toEqual(["P2"]);
    expect(out.doc?.frame).toEqual({ length_m: 3000, point_c: { P1: 100 } });
    expect(out.access).toEqual({ P1: "end_halls" });
    expect(out.platforms[2]).toMatchObject({ side: "side", sideSet: true });
  });
});

// a small solve: a shield run, a box run, a crossing short of clearance, two findings
const solved = {
  length_m: 300,
  step_m: 2,
  n: 151,
  type_runs: [
    ["shield", 0, 100],
    ["cutcover", 100, 300],
  ],
  struct_runs: [
    [{ k: "tube", below: 1.0, top: 4.6, tube: "A" }, 0, 100],
    [{ k: "box", below: 1.0, top: 4.6 }, 100, 300],
  ],
  limit_tube: Array(151).fill(140),
  limit_box: Array(151).fill(130),
  ground: {
    finished: Array(151).fill(160),
    surface: Array(151).fill(160),
    bed: Array(151).fill(160),
    lines: [],
    cross: [],
  },
  made_bed: [],
  rivers: [],
  canon: { sections: [], locks: [], piers: [] },
  spans: [],
  bad: [{ why: "cover", c0: 20, c1: 40, worst: 1.2 }],
  misfits: [],
  crossings: [
    {
      c: 150,
      wid: "Line_3",
      with: "Line 3",
      zo: 141,
      z: 145,
      clear: 2,
      need: 6.1,
      t: { k: "box", below: 1, top: 4.6 },
      to: { k: "box", below: 1, top: 4.6 },
      ok: false,
      pending: false,
    },
  ],
  flags: [
    {
      kind: "crossing_short",
      page: "Clearance",
      sev: "error",
      c0: 150,
      c1: 150,
      c: 150,
      rule: "clearance.crossing.structure_sum",
      data: { with: "Line 3", clear: 2, need: 6.1 },
    },
    {
      kind: "stretch",
      page: "Tunnel method",
      sev: "info",
      c0: 0,
      c1: 100,
      c: 50,
      rule: "geometry.stretch.note_every_stretch",
      data: {},
    },
  ],
} as unknown as SolvedSection;

function fakeCtx(): CanvasRenderingContext2D {
  return new Proxy({} as Record<string, unknown>, {
    get: (t, k) => (k in t ? t[k as string] : k === "measureText" ? () => ({ width: 40 }) : () => {}),
    set: (t, k, v) => {
      t[k as string] = v;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
}
const view: SheetView = {
  c0: 0,
  c1: 300,
  z0: 120,
  z1: 170,
  width: 360,
  height: 300,
  dpr: 1,
  top: 200,
  plot: { x: 30, y: 10, w: 300, h: 180 },
  x: (c) => 30 + c,
  c: (x) => x - 30,
  y: (z) => 10 + (170 - z) * 3.6,
  z: (y) => 170 - (y - 10) / 3.6,
  units: {
    format: (m: number, _u: string, d = 1) => m.toFixed(d),
    toDisplay: (m: number) => m,
    label: () => "m",
    length: "m",
  } as never,
  cursor: null,
};
const draw = (bands: { draw: BandDef["draw"] }[], d: Partial<BandData>): SheetMark[] => {
  const marks: SheetMark[] = [];
  const bd = {
    sectionId: "S",
    input: null,
    server: null,
    profile: null,
    selected: null,
    mark: (m: SheetMark) => marks.push(m),
    ...d,
  } as BandData;
  for (const b of bands) b.draw(fakeCtx(), view, bd);
  return marks;
};
type BandDef = import("../../src/core/plugin.ts").BandDef;
const rail = { rail_m: Array(151).fill(145), grade_permille: Array(151).fill(0), step_m: 2 };

describe("the readout between stations (3495-3503), in the old readout's words", () => {
  const units = { format: (m: number, _u: string, d = 1) => m.toFixed(d), label: () => "m", length: "m" } as never;
  const d = {
    solved,
    rail,
    solveInput: { ...ssi, context: { streets: [[0, 120, 18, "Vine Street", "major"]], roads: [], blocks: [] } },
    input: { ground: { z_m: Array(151).fill(158), step_m: 2 }, params: { platform_m: 120 }, stations: [] },
    draft: { ovr: [[100, 300, "cutcover"]] },
  } as unknown as BandData;
  it("gives the finished ground with its fill, the structure's top and cover, its bottom, the type and the street", () => {
    expect(readoutLines(d, 50, units)).toEqual([
      "0+050",
      "Ground  160.00 m",
      "Fill    2.00 m from surveyed 158.00",
      "Rail    145.00 m",
      "Below   15.00 m",
      "Top     149.60 m · cover 10.4",
      "Bottom  144.00 m · type A tube",
      "Grade   +0.0‰",
      "Shield tunnel",
      "under Vine Street (major, 18 m)",
    ]);
  });
  it("marks a painted type", () => {
    expect(readoutLines(d, 200, units)).toContain("Cut & cover (painted)");
  });
});

describe("the type at a chainage as the old typeAt read it", () => {
  it("is the nearest sample's: a run starting at 12+416 holds 12+415 (round(c / 2) = 6208)", () => {
    const sv = {
      step_m: 2,
      type_runs: [
        ["cutcover", 0, 12416],
        ["deep", 12416, 13000],
      ],
    } as unknown as SolvedSection;
    expect(typeAtSample(sv, 12415)).toBe("deep");
    expect(typeAtSample(sv, 12414.9)).toBe("cutcover");
    expect(typeAtSample(null, 1)).toBeNull();
  });
});

describe("the rail at a bend point off the 2 m grid (the bend card's Rail at the bend, 3123)", () => {
  it("is read between the samples, as the old railAt: Line 6 at 4+485.3 reads 211.11, not the nearest sample's 211.18", () => {
    // the old page's bend: 210.2 m, +22.3 to +167.6 per mille, a 50 m curve
    const [c0, z0, gi, go, L] = [4485.3, 210.2, 22.3, 167.6, 50];
    const rail = (c: number): number => {
      const a = c0 - L / 2;
      if (c <= a) return z0 + (gi / 1000) * (c - c0);
      if (c >= c0 + L / 2) return z0 + (go / 1000) * (c - c0);
      return z0 + (gi / 1000) * (c - c0) + ((go - gi) / 1000 / (2 * L)) * (c - a) ** 2;
    };
    const grid = Array.from({ length: 4000 }, (_, i) => rail(i * 2));
    expect(rail(c0).toFixed(2)).toBe("211.11");
    expect((sampleAt(grid, 2, c0) as number).toFixed(2)).toBe("211.11");
    expect(Math.abs((valueAt(grid, 2, c0) as number) - rail(c0))).toBeGreaterThan(0.05);
  });
});

describe("the roads a line crosses (2589-2595)", () => {
  it("two roads at one crossing are both named, the second a line higher (Inner Ring and Inner Ring North)", () => {
    const two = {
      ...ssi,
      context: {
        streets: [],
        roads: [
          [150, 130, 170, 45.72, "Inner Ring (OH-562 boulevard)", "major"],
          [150, 130, 170, 45.72, "Inner Ring North (OH-562 boulevard)", "highway"],
        ],
        blocks: [],
      },
    };
    const m = draw([waterBand, roadsBand], {
      solved,
      rail,
      solveInput: two as never,
      input: { ground: { z_m: Array(151).fill(158), step_m: 2 } } as never,
    }).filter((x) => x.kind === "road");
    expect(m.map((x) => [x.id, x.drawn])).toEqual([
      ["Inner Ring (OH-562 boulevard)", true],
      ["Inner Ring North (OH-562 boulevard)", true],
    ]);
  });
});

describe("the curve grade labels (2654-2664)", () => {
  it("every one is drawn, as on the old page: one that meets another goes a line higher, none is left off", () => {
    const two = {
      ...solved,
      curve_grade: [
        { c0: 100, c1: 110, worst: 52.04, sustained: false },
        { c0: 104, c1: 112, worst: 51.3, sustained: true },
        { c0: 106, c1: 108, worst: 50.6, sustained: false },
      ],
    } as unknown as SolvedSection;
    const low = { ...rail, rail_m: Array(151).fill(135) };
    const m = draw([waterBand, curveGradeBand], { solved: two, rail: low, solveInput: ssi }).filter(
      (x) => x.kind === "curve-grade",
    );
    expect(m.map((x) => x.drawn)).toEqual([true, true, true]);
    // stacked, each clear of the one under it
    const ys = m.map((x) => x.y as number);
    expect(new Set(ys).size).toBe(3);
  });
});

describe("clearance labels find room", () => {
  it("a second crossing beside the first is labelled above or below it, not left off", () => {
    const two = {
      ...solved,
      crossings: [
        solved.crossings[0],
        { ...solved.crossings[0], c: 152, wid: "Line_1", with: "Line 1", clear: 12.6, ok: true },
      ],
    } as unknown as SolvedSection;
    const m = draw([waterBand, crossingsBand], { solved: two, rail, solveInput: ssi }).filter(
      (x) => x.kind === "clearance",
    );
    expect(m.map((x) => [x.id, x.drawn])).toEqual([
      ["Line_3", true],
      ["Line_1", true],
    ]);
  });
  it("a short crossing is red on the plot even while the other line is not set (pending), as the old page drew it", () => {
    expect(clearanceColour({ ok: false, pending: true } as never)).toBe(clearanceColour({ ok: false } as never));
    expect(clearanceColour({ ok: true, pending: true } as never)).not.toBe(clearanceColour({ ok: false } as never));
  });
  it("spots stay inside the plot", () => {
    const P = { x: 0, y: 0, w: 200, h: 100 };
    const spots = labelSpots(150, 50, 40, P);
    expect(spots.length).toBeGreaterThan(0);
    expect(spots.every((b) => b.x0 >= 0 && b.x1 <= 200 && b.y0 >= 0 && b.y1 <= 100)).toBe(true);
    // no room on the right at x 150 for a 80 px label: only the left
    expect(labelSpots(150, 50, 80, P).every((b) => b.x1 < 150)).toBe(true);
  });
});

describe("the bands draw the solve", () => {
  it("outlines each tunnel run, the legal band and the unbuildable hatch; none in Show: Rail", () => {
    const m = draw([outlinesBand], { solved, rail, show: "railbox", solveInput: ssi });
    expect(m.filter((x) => x.kind === "outline").map((x) => [x.type, x.k])).toEqual([
      ["shield", "tube"],
      ["cutcover", "box"],
    ]);
    expect(m.filter((x) => x.kind === "limit").map((x) => x.id)).toEqual(["tube", "box"]);
    expect(m.filter((x) => x.kind === "unbuildable")).toHaveLength(1);
    expect(draw([outlinesBand], { solved, rail, show: "rail" })).toEqual([]);
  });
  it("draws the clearance box and its words at the crossing", () => {
    const m = draw([crossingsBand], { solved, rail, solveInput: ssi });
    expect(m).toEqual([
      expect.objectContaining({ kind: "clearance", c: 150, ok: false, text: "Line 3 box · 2.0 m apart, needs 6.1 m" }),
    ]);
  });
  it("writes each clearance to one decimal in the display unit, as the old page did (2443: toFixed(1))", () => {
    // the hub's Units trims trailing zeros ("9 m"); the old label kept them ("9.0 m apart, needs 10.0")
    const real = { ...view, units: new Units("m") };
    const one = {
      ...solved,
      crossings: [{ ...solved.crossings[0], clear: 9, need: 10 }],
    } as unknown as SolvedSection;
    const marks: SheetMark[] = [];
    crossingsBand.draw(fakeCtx(), real, {
      sectionId: "S",
      input: null,
      server: null,
      profile: null,
      selected: null,
      mark: (x: SheetMark) => marks.push(x),
      solved: one,
      rail,
      solveInput: ssi,
    } as unknown as BandData);
    expect(marks.find((x) => x.kind === "clearance")?.text).toBe("Line 3 box · 9.0 m apart, needs 10.0 m");
    const ft = { ...view, units: new Units("ft") };
    const mf: SheetMark[] = [];
    crossingsBand.draw(fakeCtx(), ft, {
      sectionId: "S",
      input: null,
      server: null,
      profile: null,
      selected: null,
      mark: (x: SheetMark) => mf.push(x),
      solved: one,
      rail,
      solveInput: ssi,
    } as unknown as BandData);
    expect(mf.find((x) => x.kind === "clearance")?.text).toBe("Line 3 box · 29.5 ft apart, needs 32.8 ft");
  });
  it("names an open trough as the old page did (structFor 1206: 'open trough')", () => {
    expect(structWord({ k: "trough" })).toBe("open trough");
  });
  it("marks every finding but the stretch notes along the bottom", () => {
    const m = draw([issuesBand], { solved, rail });
    expect(m.map((x) => [x.kind, x.id, x.sev])).toEqual([["issue", "crossing_short", "error"]]);
  });
  it("draws the structure band along the whole line with its hatch", () => {
    const m = draw([structureStripBand], { solved, rail, solveInput: ssi });
    const band = m.filter((x) => x.kind === "band");
    expect(band.map((x) => [x.id, x.c0, x.c1])).toEqual([
      ["shield", 0, 100],
      ["cutcover", 100, 300],
    ]);
    expect(m.filter((x) => x.kind === "band-hatch")).toHaveLength(1);
  });
});

describe("a line with no design yet (Lines 10, 11 and 13: no saved levels)", () => {
  // vertical.rail@1 of an empty profile is a rail at 0 m: drawn, it squashed the whole plot down to 0 m (the y range
  // took it in: Line 10 from -22 m to 298 m) and hung the outlines, crossings and channel words on it
  const base = { pvi: [], stations: [{ platform_id: "P1", level_m: null }] } as never;
  it("has no design until a bend point or a station level is set", () => {
    expect(hasDesign(base)).toBe(false);
    expect(hasDesign({ pvi: [{ c_m: 10, z_m: 150 }], stations: [] } as never)).toBe(true);
    expect(hasDesign({ pvi: [], stations: [{ platform_id: "P1", level_m: 150.2 }] } as never)).toBe(true);
    expect(hasDesign(null)).toBe(false);
  });
});
