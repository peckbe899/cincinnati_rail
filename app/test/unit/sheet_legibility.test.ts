// @vitest-environment happy-dom
// The line sheet's legibility round (Ben, 23 November: "I cannot discern stations"): bold station bars apart from
// teal bend points that never sit on them, the interchange tags under the names, the names kept at a whole-line
// view, a removed station's name off the grade labels, the maximise, and the station panel's folding groups.

import type { StationFact } from "@cr/engine/contract";
import { afterEach, describe, expect, it } from "vitest";
import type { BandData, SheetMark, SheetView } from "../../src/core/plugin.ts";
import { Units } from "../../src/core/units.ts";
import {
  BANDS,
  barGeometry,
  COLORS,
  gradeBand,
  interchangeTag,
  MIN_BAR_PX,
  nameGap,
  platformBand,
  pviBand,
} from "../../src/plugins/line-sheet/bands.ts";
import { buildPanel, GROUP_ORDER, GROUPS_KEY, groupOpen, type PanelCtx } from "../../src/plugins/line-sheet/panel.ts";
import { isMaximiseKey, keepMaximised, keptMaximised, withoutMaximised } from "../../src/shell/maximise.ts";
import { fact } from "./fixtures/station_fact.ts";

function fakeContext(): CanvasRenderingContext2D {
  return new Proxy(
    {},
    {
      get(_t, k) {
        if (k === "measureText") return (s: string) => ({ width: s.length * 7 });
        return () => {};
      },
      set: () => true,
    },
  ) as unknown as CanvasRenderingContext2D;
}

function view(c0: number, c1: number, w = 1236): SheetView {
  const plot = { x: 60, y: 84, w, h: 700 };
  const sx = plot.w / (c1 - c0);
  const sy = plot.h / 100;
  return {
    c0,
    c1,
    z0: 100,
    z1: 200,
    width: w + 74,
    height: 840,
    dpr: 1,
    top: 788,
    plot,
    x: (c) => plot.x + (c - c0) * sx,
    c: (x) => c0 + (x - plot.x) / sx,
    y: (z) => plot.y + (200 - z) * sy,
    z: (y) => 200 - (y - plot.y) / sy,
    units: new Units("m"),
    cursor: null,
  };
}

/** Two stations at 150 m and bend points just past each platform end, as a design puts them. */
function data(over: Partial<BandData> = {}, facts: StationFact[] = []): BandData {
  return {
    sectionId: "S",
    input: {
      params: { platform_m: 120 },
      stations: [
        { platform_id: "A", order: 0, c_m: 1000, level_m: 150, grade_permille: 0 },
        { platform_id: "B", order: 1, c_m: 5000, level_m: 150, grade_permille: 0 },
      ],
      pvi: [
        { c_m: 1063, z_m: 150 },
        { c_m: 3000, z_m: 170 },
        { c_m: 4937, z_m: 150 },
      ],
      ground: { z_m: new Float64Array(10001).fill(163.6), step_m: 2 },
    } as unknown as BandData["input"],
    rail: { rail_m: new Float64Array(10001).fill(150), grade_permille: new Float64Array(10001), step_m: 2 },
    server: null,
    profile: null,
    selected: null,
    platformName: (id) => id,
    stopC: () => null,
    facts,
    ...over,
  };
}

const draw = (bands: typeof BANDS, v: SheetView, d: BandData): SheetMark[] => {
  const marks: SheetMark[] = [];
  const dd = { ...d, mark: (m: SheetMark) => marks.push(m) };
  for (const b of bands) b.draw(fakeContext(), v, dd);
  return marks;
};

describe("stations and bend points (item 2)", () => {
  it("bend points are teal, apart from the stations' ink and the flags' red", () => {
    expect(COLORS.pvi).toBe("#2fb8a8");
    expect(COLORS.bar).not.toBe(COLORS.pvi);
  });
  it("the bend points are drawn under the station bars", () => {
    const ids = BANDS.map((b) => b.id);
    expect(ids.indexOf("pvi")).toBeLessThan(ids.indexOf("platforms"));
  });
  it("a bar is at least MIN_BAR_PX wide about its centre at a whole-line view", () => {
    const v = view(0, 30000);
    const b = barGeometry(v, { c_m: 1000, grade_permille: 0 }, 150, 60);
    expect(b.xb - b.xa).toBeCloseTo(MIN_BAR_PX);
    expect((b.xa + b.xb) / 2).toBeCloseTo(v.x(1000));
    const z = barGeometry(view(900, 1100), { c_m: 1000, grade_permille: 0 }, 150, 60);
    expect(z.xb - z.xa).toBeCloseTo(view(900, 1100).x(1060) - view(900, 1100).x(940));
  });
  it("at a whole-line view a circle that would sit on a bar is left out, and cannot be grabbed", () => {
    const whole = draw([pviBand, platformBand], view(0, 30000), data());
    const pv = whole.filter((m) => m.kind === "pvi");
    expect(pv.map((m) => [m.c, m.hidden])).toEqual([
      [1063, true],
      [3000, false],
      [4937, true],
    ]);
    const atA = whole.find((m) => m.kind === "bar" && m.id === "A") as unknown as { x0: number; y0: number };
    expect(pviBand.hit?.(atA.x0 + 3, atA.y0)).toBeNull();
    // zoomed in they are all there, clear of the bars
    const near = draw([pviBand, platformBand], view(800, 1300), data());
    expect(near.filter((m) => m.kind === "pvi").map((m) => m.hidden)).toEqual([false]);
  });
  it("a selected bend point is drawn even on a bar", () => {
    const sel = { band: "pvi", kind: "pvi", index: 0, c: 1063, z: 150 };
    const marks = draw([pviBand], view(0, 30000), data({ selected: sel }));
    expect(marks.find((m) => m.kind === "pvi" && m.c === 1063)?.hidden).toBe(false);
  });
});

describe("interchange tags under the names (item 2)", () => {
  it("the old page's short names", () => {
    expect(interchangeTag(["Line 3"])).toBe("L3");
    expect(interchangeTag(["Line 4", "Line 5", "A trunk"])).toBe("L4 L5 A trunk");
    expect(interchangeTag(["CVG Express", "Line 2b"])).toBe("CVG L2b");
  });
  it("a tag for each station with interchanges, kept apart, the selected one always", () => {
    const facts = [
      fact({ platform_id: "A", c_m: 1000, interchanges: ["Line 3"] }),
      fact({ platform_id: "B", index: 1, c_m: 5000, point_c_m: 5000, interchanges: ["Line 13", "E trunk"] }),
    ];
    const tags = draw([platformBand], view(0, 30000), data({}, facts)).filter((m) => m.kind === "xtag");
    expect(tags.map((m) => [m.id, m.text, m.drawn])).toEqual([
      ["A", "L3", true],
      ["B", "L13 E trunk", true],
    ]);
    // two stations 20 m apart: the second tag is left out unless it is selected
    const close = data({}, [facts[0] as StationFact, { ...(facts[1] as StationFact), c_m: 1100, point_c_m: 1100 }]);
    ((close.input as { stations: { c_m: number }[] }).stations[1] as { c_m: number }).c_m = 1100;
    const a = draw([platformBand], view(0, 30000), close).filter((m) => m.kind === "xtag");
    expect(a.map((m) => m.drawn)).toEqual([true, false]);
    const sel = { band: "platforms", kind: "station", index: 1, id: "B", c: 1100 };
    const b = draw([platformBand], view(0, 30000), { ...close, selected: sel }).filter((m) => m.kind === "xtag");
    expect(b.find((m) => m.id === "B")?.drawn).toBe(true);
  });
});

describe("names at a whole-line view (item 3)", () => {
  it("15 px apart on a plot 900 px wide and more (the old page's narrow gap), 18 below", () => {
    expect(nameGap(1236)).toBe(15);
    expect(nameGap(590)).toBe(18);
  });
  it("29 stations every 1,000 m on a 1,236 px plot: every name drawn (the old page drew 29 of Line 6's 31)", () => {
    const stations = Array.from({ length: 29 }, (_, i) => ({
      platform_id: `S${i}`,
      order: i,
      c_m: 500 + i * 1000,
      level_m: 150,
      grade_permille: 0,
    }));
    const d = data();
    (d.input as { stations: unknown[] }).stations = stations;
    const names = draw([platformBand], view(0, 30000), d).filter((m) => m.kind === "name");
    expect(names.filter((m) => m.drawn).length).toBe(29);
  });
});

describe("a removed station's name keeps off the grade labels (item 6)", () => {
  it("the struck-through name is placed where no grade label is", () => {
    const facts = [fact({ platform_id: "C", deleted: true, index: null, point_c_m: 3000, c_m: 3000, rail_m: null })];
    const dv = [
      { c_m: 0, z_m: 150, kind: "end" },
      { c_m: 6000, z_m: 150, kind: "end" },
    ] as unknown as BandData["dv"];
    for (const [c0, c1] of [
      [2500, 3500],
      [0, 6000],
      [2900, 3100],
    ] as const) {
      const marks = draw([gradeBand, platformBand], view(c0, c1), data({ dv }, facts));
      const grades = marks.filter((m) => m.kind === "grade") as unknown as {
        x0: number;
        x1: number;
        y0: number;
        y1: number;
      }[];
      const removed = marks.find((m) => m.kind === "removed") as unknown as {
        label: { x0: number; x1: number; y0: number; y1: number };
      };
      expect(grades.length).toBeGreaterThan(0);
      for (const g of grades) {
        const apart =
          removed.label.x1 <= g.x0 || g.x1 <= removed.label.x0 || removed.label.y1 <= g.y0 || g.y1 <= removed.label.y0;
        expect(apart).toBe(true);
      }
    }
  });
});

describe("maximise (item 1)", () => {
  const ev = (o: Partial<KeyboardEvent> & { target?: unknown }) =>
    ({ key: "F", shiftKey: true, ctrlKey: false, altKey: false, metaKey: false, target: null, ...o }) as Parameters<
      typeof isMaximiseKey
    >[0];
  it("Shift+F, never in a text field, never with Ctrl or Alt", () => {
    expect(isMaximiseKey(ev({}))).toBe(true);
    expect(isMaximiseKey(ev({ shiftKey: false, key: "f" }))).toBe(false);
    expect(isMaximiseKey(ev({ ctrlKey: true }))).toBe(false);
    expect(isMaximiseKey(ev({ target: document.createElement("input") }))).toBe(false);
    expect(isMaximiseKey(ev({ target: document.createElement("canvas") }))).toBe(true);
  });
  it("kept for the session, and never in the saved layout", () => {
    const m = new Map<string, string>();
    const store = {
      getItem: (k: string) => m.get(k) ?? null,
      setItem: (k: string, v: string) => void m.set(k, v),
      removeItem: (k: string) => void m.delete(k),
    };
    keepMaximised("design", "line-sheet", store);
    expect(keptMaximised("design", store)).toBe("line-sheet");
    keepMaximised("design", null, store);
    expect(keptMaximised("design", store)).toBeNull();
    const layout = { grid: { root: 1, maximizedNode: { location: [0] } }, panels: {} };
    expect(withoutMaximised(layout)).toEqual({ grid: { root: 1 }, panels: {} });
    expect(withoutMaximised({ grid: { root: 1 } })).toEqual({ grid: { root: 1 } });
  });
});

describe("the station panel's groups (item 5)", () => {
  afterEach(() => localStorage.clear());
  const ctx = (f: StationFact): PanelCtx => ({
    units: new Units("m"),
    pid: f.platform_id,
    name: f.name,
    line: "Line 3",
    index: 0,
    count: 2,
    half: 60,
    fact: f,
    params: null,
    paramPrefix: "settings",
    metro: true,
    draft: {},
    saved: {},
    savedBy: "import:old_hub",
    point: 1000,
    centre: 1000,
    rail: 150,
    ground: 163.6,
    groundDem: 163.6,
    gradeIn: 0,
    gradeOut: 0,
    side: { now: "side", was: "side", source: "old hub" },
    canEdit: true,
    canEditSide: true,
    readOnly: null,
    act: new Proxy({}, { get: () => () => {} }) as PanelCtx["act"],
  });
  it("the most used first: level, structure, flags, then the rest", () => {
    const p = buildPanel(ctx(fact({})));
    const ids = [...p.querySelectorAll<HTMLElement>("details.sp-group")].map((d) =>
      (d.dataset.testid ?? "").replace("sp-group-", ""),
    );
    expect(ids).toEqual(GROUP_ORDER.filter((g) => ids.includes(g)));
    expect(ids.slice(0, 3)).toEqual(["level", "structure", "flags"]);
  });
  it("level and structure open; flags open only with an error or warning; the rest folded with a digest", () => {
    const quiet = buildPanel(ctx(fact({})));
    const open = (p: HTMLElement, id: string) =>
      (p.querySelector(`[data-testid=sp-group-${id}]`) as HTMLDetailsElement).open;
    expect(["level", "structure", "flags", "place", "access", "limits"].map((g) => open(quiet, g))).toEqual([
      true,
      true,
      false,
      false,
      false,
      false,
    ]);
    expect(quiet.querySelector("[data-testid=sp-group-place] .sp-digest")?.textContent).toBe("1+000");
    const flagged = fact({
      flags: [
        { kind: "platform_grade_over", sev: "error", c0: 0, c1: 1, rule: "platform.grade.limit_by_era", data: {} },
      ],
    });
    expect(open(buildPanel(ctx(flagged)), "flags")).toBe(true);
  });
  it("Ben's choice is kept across stations", () => {
    expect(groupOpen("place", null)).toBe(false);
    localStorage.setItem(GROUPS_KEY, JSON.stringify({ place: true, level: false }));
    expect(groupOpen("place", null)).toBe(true);
    const p = buildPanel(ctx(fact({})));
    expect((p.querySelector("[data-testid=sp-group-level]") as HTMLDetailsElement).open).toBe(false);
  });
});
