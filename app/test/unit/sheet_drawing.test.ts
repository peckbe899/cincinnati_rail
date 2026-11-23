// The line sheet's drawing model (app/src/plugins/line-sheet/drawing.ts): the old sheet's formats, axis ticks,
// label thinning, grade chords and curve ticks, and what the station band draws and reports.

import type { DesignVertex } from "@cr/engine/contract";
import { describe, expect, it } from "vitest";
import type { BandData, SheetText, SheetView } from "../../src/core/plugin.ts";
import { Units } from "../../src/core/units.ts";
import { platformBand, readoutLines } from "../../src/plugins/line-sheet/bands.ts";
import {
  axisChainage,
  chainageTicks,
  curveTicks,
  fmtCh,
  fmtG,
  fmtVE,
  fmtZ,
  gradeChords,
  gradeLabels,
  levelTicks,
  margins,
  niceStep,
  thinLabels,
  verticalExaggeration,
} from "../../src/plugins/line-sheet/drawing.ts";

describe("formats", () => {
  it("writes chainage as k+mmm, rounding 1999.6 to 2+000", () => {
    expect(fmtCh(2500)).toBe("2+500");
    expect(fmtCh(1999.6)).toBe("2+000");
    expect(fmtCh(12)).toBe("0+012");
    // A platform start just before 0 (a station at 60.9 m, half 61.0) rounds to 0+000, not "−0+000".
    expect(fmtCh(-0.04)).toBe("0+000");
    expect(fmtCh(-0.4)).toBe("0+000");
    expect(fmtCh(-61)).toBe("−0+061");
    expect(axisChainage(3048, new Units("ft"))).toBe("10000");
  });
  it("writes grades signed to one decimal with a true minus", () => {
    expect(fmtG(13.64)).toBe("+13.6‰");
    expect(fmtG(-0.2)).toBe("−0.2‰");
    expect(fmtG(-0.01)).toBe("+0.0‰");
  });
  it("writes levels in the display unit", () => {
    expect(fmtZ(162.71, new Units("m"))).toBe("162.7");
    expect(fmtZ(30.48, new Units("ft"))).toBe("100.0");
    expect(fmtZ(null, new Units("m"))).toBe("–");
  });
  it("writes the vertical exaggeration", () => {
    expect(fmtVE(21.3)).toBe("V.E. ×21");
    expect(fmtVE(4.25)).toBe("V.E. ×4.3");
    expect(verticalExaggeration(1000, 500, 0, 4000, 150, 250)).toBeCloseTo(20);
  });
});

describe("axes", () => {
  it("steps at 1, 2 or 5 times a power of ten", () => {
    expect(niceStep(100, 8)).toBe(10);
    expect(niceStep(4000, 10)).toBe(500);
    expect(niceStep(3, 8)).toBe(0.5);
  });
  it("labels the level axis in whole units, with a decimal under a unit step", () => {
    const t = levelTicks(158, 252, new Units("m"), 8);
    expect(t.map((x) => x.label)).toEqual(["160", "170", "180", "190", "200", "210", "220", "230", "240", "250"]);
    expect(levelTicks(100, 102, new Units("m"), 8)[1]?.label).toBe("100.2");
  });
  it("labels the level axis in feet when the units are feet, with the value kept in metres", () => {
    const t = levelTicks(150, 250, new Units("ft"), 8);
    expect(Number(t[0]?.label) % 50).toBe(0);
    expect(t[0]?.v).toBeCloseTo(Number(t[0]?.label) * 0.3048);
  });
  it("labels the chainage axis k+mmm", () => {
    expect(chainageTicks(2000, 6000, new Units("m"), 8).map((t) => t.label)).toEqual([
      "2+000",
      "2+500",
      "3+000",
      "3+500",
      "4+000",
      "4+500",
      "5+000",
      "5+500",
      "6+000",
    ]);
  });
  it("keeps the old margins, smaller on a narrow or short sheet", () => {
    expect(margins(1200, 600)).toEqual({ l: 60, r: 14, t: 84, b: 4 });
    expect(margins(500, 600).l).toBe(46);
    // A narrow plot (the sheet beside the map, the inspector and the station panel) keeps the full top margin, so
    // a rotated name such as "Fountain Square" is not cut off at the top (parity review, 23 November).
    expect(margins(500, 600).t).toBe(84);
    expect(margins(1200, 250).t).toBe(52);
  });
});

describe("label thinning", () => {
  it("keeps labels at least gap apart, left to right", () => {
    const kept = thinLabels(
      [0, 10, 20, 40].map((x) => ({ x, priority: 1 })),
      18,
    );
    expect([...kept].sort()).toEqual([0, 2, 3]);
  });
  it("always keeps the selected label and drops its crowded neighbours", () => {
    const kept = thinLabels(
      [
        { x: 0, priority: 1 },
        { x: 10, priority: 1, selected: true },
        { x: 20, priority: 1 },
      ],
      18,
    );
    expect([...kept]).toEqual([1]);
  });
  it("prefers the ends of the line to the stations between", () => {
    const kept = thinLabels(
      [
        { x: 0, priority: 1 },
        { x: 10, priority: 0 },
      ],
      18,
    );
    expect([...kept]).toEqual([1]);
  });
});

describe("grade chords and curve ticks", () => {
  const dv: DesignVertex[] = [
    { c_m: 0, z_m: 100, kind: "end" },
    { c_m: 940, z_m: 113.6, kind: "pvi" },
    { c_m: 1000, z_m: 114, kind: "ps" },
    { c_m: 1120, z_m: 114, kind: "pe" },
    { c_m: 2120, z_m: 113.8, kind: "end" },
  ];
  it("skips flat platforms and gives each chord its grade", () => {
    const ch = gradeChords(dv);
    expect(ch).toHaveLength(3);
    expect(fmtG(ch[0]?.g ?? 0)).toBe("+14.5‰");
    expect(fmtG(ch[2]?.g ?? 0)).toBe("−0.2‰");
  });
  it("labels only chords at least minPx wide, in view", () => {
    const x = (c: number) => c / 10;
    const labs = gradeLabels(gradeChords(dv), x, 0, 150, 66);
    expect(labs.map((l) => l.text)).toEqual(["+14.5‰", "−0.2‰"]);
    expect(labs[0]?.xm).toBeCloseTo(47);
    // A chord running out of view is labelled in the middle of its part in view.
    expect(labs[1]?.xm).toBeCloseTo(131);
    expect(gradeLabels(gradeChords(dv), x, 0, 150, 120)).toEqual([]);
  });
  it("runs the chords between the platforms' transition ends, as the old page's chords() (Line 6 Towne)", () => {
    // vertical.rail@1's vertices of Line 6 from Towne to Bond Hill, and the curves at the two transition ends (x)
    const l6: DesignVertex[] = [
      { c_m: 0, z_m: 159.9, kind: "ps" },
      { c_m: 121.5, z_m: 159.9, kind: "pe" },
      { c_m: 357, z_m: 168.5, kind: "pvi" },
      { c_m: 574, z_m: 173.2, kind: "pvi" },
      { c_m: 1023.2, z_m: 163.07, kind: "ps" },
      { c_m: 1145.2, z_m: 162.33, kind: "pe" },
    ];
    const curves = [
      { c_m: 153.1, g_in: 0, g_out: 42.2, L_m: 63.2 },
      { c_m: 357, g_in: 42.2, g_out: 21.7, L_m: 30.7 },
      { c_m: 574, g_in: 21.7, g_out: -23.1, L_m: 67.2 },
      { c_m: 1008, g_in: -23.1, g_out: -6.07, L_m: 30.4 },
      { c_m: 1160.4, g_in: -6.07, g_out: 1.6, L_m: 30.4 },
    ];
    const ch = gradeChords(l6, curves);
    // the old page labels +42.2‰ from the transition end, not +36.5‰ from the platform end
    expect(ch.map((x) => fmtG(x.g))).toEqual(["+42.2‰", "+21.7‰", "−23.1‰", "−6.1‰", "−6.1‰", "−6.1‰"]);
    expect(ch[0]?.c0).toBeCloseTo(153.1);
    expect(ch[2]?.c1).toBeCloseTo(1008);
    // without the curves, the vertices alone
    expect(gradeChords(l6).map((x) => fmtG(x.g))[0]).toBe("+36.5‰");
  });
  it("ticks each curve at its start and end", () => {
    expect(
      curveTicks([
        { c_m: 940, g_in: 14, g_out: 6, L_m: 100 },
        { c_m: 50, g_in: 0, g_out: 0, L_m: 0 },
      ]),
    ).toEqual([890, 990]);
  });
});

/** A canvas context that records the text drawn. */
function fakeContext(): { g: CanvasRenderingContext2D; texts: string[] } {
  const texts: string[] = [];
  const g = new Proxy(
    {},
    {
      get(_t, k) {
        if (k === "fillText") return (s: string) => texts.push(s);
        if (k === "measureText") return (s: string) => ({ width: s.length * 7 });
        return () => {};
      },
      set: () => true,
    },
  ) as unknown as CanvasRenderingContext2D;
  return { g, texts };
}

function view(c0: number, c1: number): SheetView {
  const plot = { x: 60, y: 84, w: 530, h: 300 };
  const sx = plot.w / (c1 - c0);
  const sy = plot.h / 100;
  return {
    c0,
    c1,
    z0: 150,
    z1: 250,
    width: 604,
    height: 420,
    dpr: 1,
    top: 388,
    plot,
    x: (c) => plot.x + (c - c0) * sx,
    c: (x) => c0 + (x - plot.x) / sx,
    y: (z) => plot.y + (250 - z) * sy,
    z: (y) => 250 - (y - plot.y) / sy,
    units: new Units("m"),
    cursor: null,
  };
}

function data(names: [string, number, number | null][]): BandData {
  return {
    sectionId: "S",
    input: {
      params: { platform_m: 120 },
      stations: names.map(([id, c, z], order) => ({ platform_id: id, order, c_m: c, level_m: z, grade_permille: 0 })),
      pvi: [],
    } as unknown as BandData["input"],
    rail: { rail_m: new Float64Array(5000).fill(170), grade_permille: new Float64Array(5000), step_m: 2 },
    server: null,
    profile: null,
    selected: null,
    platformName: (id) => id.replace("P_", ""),
  };
}

describe("station band", () => {
  it("names every station in view at a 4 km window, with its level, and reports it", () => {
    const d = data([
      ["P_Chalet", 2400, 163.6],
      ["P_North Avondale", 3500, null],
      ["P_Forest", 4700, 219.7],
    ]);
    const report: SheetText[] = [];
    d.report = (t) => report.push(t);
    const { g, texts } = fakeContext();
    platformBand.draw(g, view(2000, 6000), d);
    expect(texts).toEqual(expect.arrayContaining(["Chalet", "North Avondale", "Forest", "163.6", "170.0", "219.7"]));
    expect(report.map((r) => r.text)).toEqual([
      "Chalet, 2+400, rail 163.6 m",
      "North Avondale, 3+500, rail 170.0 m",
      "Forest, 4+700, rail 219.7 m",
    ]);
    expect(report.every((r) => r.drawn)).toBe(true);
  });
  it("thins crowded names when zoomed out but keeps the selected one", () => {
    const d = data([
      ["P_A", 1000, 170],
      ["P_B", 1300, 170],
      ["P_C", 1600, 170],
      ["P_D", 29000, 170],
    ]);
    d.selected = { band: "platforms", kind: "station", index: 1, id: "P_B", c: 1300 };
    const report: SheetText[] = [];
    d.report = (t) => report.push(t);
    const { g } = fakeContext();
    platformBand.draw(g, view(0, 30000), d);
    const drawn = report.filter((r) => r.drawn).map((r) => r.id);
    expect(drawn).toContain("P_B");
    expect(drawn).toContain("P_D");
    expect(drawn).not.toContain("P_A");
  });
  it("hits a station on its bar and on its name", () => {
    const d = data([["P_Forest", 4000, 200]]);
    const { g } = fakeContext();
    const v = view(2000, 6000);
    platformBand.draw(g, v, d);
    expect(platformBand.hit?.(v.x(4000), v.y(200))?.id).toBe("P_Forest");
    // 20 px along the name's 45° line from its anchor at the top of the plot.
    expect(platformBand.hit?.(v.x(4000) + 14, v.plot.y - 6 - 14)?.id).toBe("P_Forest");
    expect(platformBand.hit?.(v.x(5000), v.y(200))).toBeNull();
  });
});

describe("readout", () => {
  it("reads chainage, ground, rail, depth and grade in the old formats", () => {
    const d = data([]);
    (d.input as unknown as { ground: unknown }).ground = { z_m: new Float64Array(5000).fill(181.24), step_m: 2 };
    expect(readoutLines(d, 2313, new Units("m"))).toEqual([
      "2+313",
      "Ground  181.24 m",
      "Rail    170.00 m",
      "Below   11.24 m",
      "Grade   +0.0‰",
    ]);
  });
});
