// The line sheet's station side (claude/hub_maps/profiles_parity.md section A): the model ops each station edit
// makes, the draft's undo steps, the words the panel and bands use, and what the bands draw from station.facts@1.

import type { StationFact } from "@cr/engine/contract";
import { describe, expect, it } from "vitest";
import type { Rec } from "../../src/api/types.ts";
import { Drafts } from "../../src/core/drafts.ts";
import { applyPatch } from "../../src/core/jsonpatch.ts";
import type { BandData, SheetMark, SheetView } from "../../src/core/plugin.ts";
import { Units } from "../../src/core/units.ts";
import { makeView } from "../../src/core/view.ts";
import { platformBand, readoutLines } from "../../src/plugins/line-sheet/bands.ts";
import {
  accessShapes,
  curveWord,
  depthTag,
  drawsDHall,
  flagText,
  hallRoomText,
  openingText,
  slideText,
  streetShort,
  streetText,
  structureQuad,
  typeColour,
  typeReason,
  worstSeverity,
} from "../../src/plugins/line-sheet/drawing.ts";
import {
  easeGrade,
  factsInput,
  nudgeLevel,
  type ProfileData,
  removeStation,
  restoreStation,
  setAccess,
  setGapfill,
  setPlatformSide,
  setStationGrade,
  setStationSlide,
  setStationType,
  slideForPoint,
  stationProfile,
  sttSameAsPaint,
} from "../../src/plugins/line-sheet/model.ts";
import { fieldSource } from "../../src/plugins/line-sheet/panel.ts";
import {
  stationAccessBand,
  stationFlagsBand,
  stationStripBand,
  stationStructureBand,
} from "../../src/plugins/line-sheet/stations.ts";
import { fact } from "./fixtures/station_fact.ts";

const m = new Units("m");
const ft = new Units("ft");
const on = (data: ProfileData, ops: ReturnType<typeof setStationGrade>) =>
  (applyPatch({ data }, ops) as { data: ProfileData }).data;

describe("station edits as JSON Patch on the profile draft (0.3)", () => {
  it("platform grade: rounded to 0.1, zero written as a removal", () => {
    let d: ProfileData = { st: { A: 150 } };
    d = on(d, setStationGrade(d, "A", 12.04));
    expect(d.sg).toEqual({ A: 12 });
    d = on(d, setStationGrade(d, "A", 0.02));
    expect(d.sg).toEqual({});
  });
  it("slide: clamped to 150 m, rounded to 0.5 m, zero removed; the card's point field and buttons", () => {
    let d: ProfileData = {};
    d = on(d, setStationSlide(d, "A", 237));
    expect(d.so).toEqual({ A: 150 });
    d = on(d, setStationSlide(d, "A", -20.26));
    expect(d.so).toEqual({ A: -20.5 });
    d = on(d, setStationSlide(d, "A", 0.1));
    expect(d.so).toEqual({});
    // Point from platform start 10 on a 121.92 m platform: so = half - 10 (check 25)
    expect(slideForPoint(10, 60.96)).toBeCloseTo(50.96);
    expect(slideForPoint(500, 60.96)).toBeCloseTo(-60.96);
  });
  it("remove keeps the station's own values; restore takes the key out of del only", () => {
    let d: ProfileData = { st: { A: 150 }, sg: { A: 2 }, so: { A: 5 }, stt: { A: "shield" } };
    d = on(d, removeStation(d, "A"));
    expect(d.del).toEqual(["A"]);
    expect(d.st).toEqual({ A: 150 });
    d = on(d, removeStation(d, "A"));
    expect(d.del).toEqual(["A"]);
    d = on(d, restoreStation(d, "A"));
    expect(d.del).toEqual([]);
    expect(d.stt).toEqual({ A: "shield" });
  });
  it("station type: Rules removes the key; Elevated raises a lower rail to ceil(ground + need, 0.1)", () => {
    let d: ProfileData = { st: { A: 150 } };
    d = on(d, setStationType(d, "A", "elevated", 158.33, 150));
    expect(d.stt).toEqual({ A: "elevated" });
    expect(d.st).toEqual({ A: 158.4 });
    d = on(d, setStationType(d, "A", null));
    expect(d.stt).toEqual({});
    d = on(d, setStationType(d, "A", "elevated", 150, 160));
    expect(d.st).toEqual({ A: 158.4 });
  });
  it("gap fillers toggle and access choice keep Ben's saved stages", () => {
    let d: ProfileData = { access: { A: { type: "end_halls", stages: [{ year: 1930 }] } } };
    d = on(d, setGapfill(d, "A", true));
    expect(d.gapfill).toEqual(["A"]);
    d = on(d, setGapfill(d, "A", false));
    expect(d.gapfill).toEqual([]);
    d = on(d, setAccess(d, "A", "mezzanine"));
    expect(d.access).toEqual({ A: { type: "mezzanine", stages: [{ year: 1930 }] } });
    d = on(d, setAccess(d, "A", null));
    expect(d.access).toEqual({});
    d = on(d, setAccess(d, "B", "platform_level"));
    expect(d.access).toEqual({ B: { type: "platform_level" } });
  });
  it("side is an op on the platform record", () => {
    expect(setPlatformSide({ side: null }, "island")).toEqual([{ op: "replace", path: "/data/side", value: "island" }]);
    expect(setPlatformSide({}, "side")).toEqual([{ op: "add", path: "/data/side", value: "side" }]);
  });
  it("ease: the mean of the grades either side, clamped to the limit", () => {
    const dv = [
      { c_m: 0, z_m: 100, kind: "pvi" },
      { c_m: 940, z_m: 110, kind: "ps" },
      { c_m: 1060, z_m: 110, kind: "pe" },
      { c_m: 2000, z_m: 100, kind: "pvi" },
    ];
    // in +10.6‰, out -10.6‰: the mean is 0
    expect(easeGrade(dv, 1000, 60, 7.5)).toBe(0);
    const up = dv.map((v) => (v.kind === "pvi" && v.c_m === 2000 ? { ...v, z_m: 130 } : v));
    expect(easeGrade(up, 1000, 60, 7.5)).toBe(7.5);
    expect(easeGrade(dv, 500, 60, 7.5)).toBeNull();
    // A platform at a line end: its end vertex is clamped to the line (vertices 731), so Towne (c 60.9, half 61)
    // and Beechgrove on Line 6 ease as on the old page, toward the one grade they have.
    const ends = [
      { c_m: 0, z_m: 100, kind: "ps" },
      { c_m: 121.9, z_m: 100, kind: "pe" },
      { c_m: 1000, z_m: 110, kind: "pvi" },
      { c_m: 1878.1, z_m: 100, kind: "ps" },
      { c_m: 2000, z_m: 100, kind: "pe" },
    ];
    expect(easeGrade(ends, 60.9, 61, 7.5)).toBe(7.5);
    expect(easeGrade(ends, 1939.1, 61, 7.5)).toBe(-7.5);
  });
  it("arrow nudges keep the level's centimetres and step in the display unit (S46: 0.1, Shift 1)", () => {
    // Line 2 Holmes is at 152.02: Arrow Up on the old page gave 152.12, not 152.1 (3537, rounded to 0.01 m).
    expect(nudgeLevel(152.02, 1, false, "m")).toBe(152.12);
    expect(nudgeLevel(152.02, -1, true, "m")).toBe(151.02);
    // In feet a step is 0.1 ft (0.03 m), as the old page's fromU(0.1).
    expect(nudgeLevel(152.02, 1, false, "ft")).toBe(152.05);
    expect(nudgeLevel(152.02, 1, true, "ft")).toBe(152.32);
  });
  it("a selection equal to the paint over the centre is noted (S62: the old page showed it as Rules)", () => {
    // Line 2 Broerman: stt cutcover under a cutcover paint; St Bernard: cutcover with no paint over it.
    const data: ProfileData = {
      ovr: [
        [1783.5, 2667.7, "cutcover"],
        [2000, 2100, "shield"],
        [5000, 5200, "bored"],
      ],
      stt: { A: "cutcover", B: "cutcover", C: "shield", D: "elevated" },
    };
    expect(sttSameAsPaint(data, "A", 1900)).toBe(true);
    expect(sttSameAsPaint(data, "A", 2050)).toBe(false); // the later paint wins
    expect(sttSameAsPaint(data, "B", 3000)).toBe(false);
    expect(sttSameAsPaint(data, "C", 5100)).toBe(true); // "bored" is the shield paint
    expect(sttSameAsPaint({ ovr: [[0, 100, "elevated"]], stt: { D: "elevated" } }, "D", 50)).toBe(false);
    expect(sttSameAsPaint({}, "A", 1900)).toBe(false);
  });
  it("the facts input: the draft's station fields as the server reads them, sides from the drafts", () => {
    const data: ProfileData = {
      pvi: [[0, 100]],
      st: { A: 150, B: null },
      sg: { A: 2, B: null as unknown as number },
      ovr: [[0, 10, "bored"]],
      attrs: { x: 1 },
    };
    expect(stationProfile(data)).toEqual({ st: { A: 150, B: null }, sg: { A: 2 }, ovr: [[0, 10, "shield"]] });
    const si = {
      section: { pvi: [], stations: [], params: { platform_m: 120 } },
      platforms: [{ platform_id: "A", side: "side", side_source: "import" }],
      profile: {},
    } as unknown as Parameters<typeof factsInput>[0];
    const out = factsInput(si, data, null, (pid) => (pid === "A" ? { side: "island", source: "ben" } : null));
    expect(out.platforms[0]).toMatchObject({ side: "island", side_source: "ben" });
    expect(out.section.pvi).toEqual([{ c_m: 0, z_m: 100 }]);
  });
});

const rec = (data: Record<string, unknown>): Rec => ({
  id: "P",
  kind: "profile",
  kv: 1,
  layer: "s1",
  version: 1,
  hash: "",
  deleted: false,
  origin: "",
  source: null,
  by: "import:old_hub",
  changeset: "",
  created: "",
  updated: "",
  geom: null,
  data,
});

describe("draft steps (0.4)", () => {
  it("each edit is one step; a run with one step id is one; back past the start drops the draft", () => {
    const drafts = new Drafts();
    const view = makeView({ layer: "s1" });
    const r = rec({ st: { A: 150 } });
    drafts.edit(r, view, [{ op: "replace", path: "/data/st/A", value: 151 }], { label: "A level" });
    for (const z of [152, 153, 154])
      drafts.edit(r, view, [{ op: "replace", path: "/data/st/A", value: z }], { step: "drag:1", label: "A level" });
    drafts.edit(r, view, [{ op: "add", path: "/data/sg", value: { A: 3 } }], { label: "A grade" });
    const body = () => drafts.get("profile", "P", view)?.body.data as ProfileData | undefined;
    expect(body()).toEqual({ st: { A: 154 }, sg: { A: 3 } });
    expect(drafts.stepBack("s1")?.label).toBe("A grade");
    expect(body()).toEqual({ st: { A: 154 } });
    drafts.stepBack("s1");
    expect(body()).toEqual({ st: { A: 151 } });
    drafts.stepBack("s1");
    expect(body()).toBeUndefined();
    expect(drafts.stepBack("s1")).toBeNull();
    drafts.stepForward("s1");
    expect(body()).toEqual({ st: { A: 151 } });
    drafts.stepForward("s1");
    expect(body()).toEqual({ st: { A: 154 } });
    // a step in another layer is not this layer's to take back
    expect(drafts.peekStep("s2")).toBeNull();
    // Discard forgets them
    drafts.drop(drafts.key("profile", "P", view));
    expect(drafts.peekStep("s1")).toBeNull();
  });
  it("a save forgets the draft's steps, so the next Ctrl+Z is the hub's undo", () => {
    const drafts = new Drafts();
    const view = makeView({ layer: "s1" });
    const r = rec({ st: { A: 150 } });
    const d = drafts.edit(r, view, [{ op: "replace", path: "/data/st/A", value: 151 }]);
    drafts.saved(d?.key as string, { ...r, version: 2, data: { st: { A: 151 } } }, d?.rev as number);
    expect(drafts.peekStep("s1")).toBeNull();
  });
});

describe("station words (A.3, A.6)", () => {
  it("formats as the old card did", () => {
    expect(slideText(-235, m)).toBe("slid −235 m");
    expect(depthTag(13.6, m)).toBe("13.6 down");
    expect(depthTag(-2.1, m)).toBe("+2.1 up");
    expect(depthTag(13.6, ft)).toBe("44.6 down");
    expect(curveWord({ level: "error", gapfill: false })).toBe("ERROR");
    expect(curveWord({ level: "error", gapfill: true })).toBe("exception, gap fillers");
    expect(curveWord({ level: "warning", gapfill: false })).toBe("WARNING");
    const st = { text: "under", street: "Central Parkway", subway: true, roads: [] };
    expect(streetText(st)).toBe("under Central Parkway (built over the subway)");
    expect(streetShort(st)).toBe("Central Parkway");
    // The old table's dash for "none" is an en dash, as in every other empty cell.
    expect(streetShort({ text: "not_under_a_street", street: null, roads: [] })).toBe("–");
    expect(streetText({ text: "crosses", street: null, subway: false, roads: ["Vine", "Elm"] })).toBe(
      "crosses Vine, Elm",
    );
    expect(streetText({ text: "not_under_a_street", street: null, subway: false, roads: [] })).toBe(
      "not under a street",
    );
    expect(
      openingText({
        year: 1906,
        phase: "1",
        at_open: [],
        later: [{ station: "Genesee", name: "Line 5", year: 1909 }],
      }),
    ).toBe("1906 (Phase 1); later: Line 5 1909");
    expect(openingText({ year: null, phase: "2", at_open: [], later: [] })).toBe("no year set (Phase 2 assumed)");
    expect(hallRoomText({ d_hall_m: 9.15, island: true, depth_m: 13.6 }, m)).toBe(
      "needs 9.15 m of rail depth (island box); 13.60 here",
    );
    expect(
      typeReason({ type: "cutcover", type_why: "box_within_limit", depth_m: 9.2, phase: "1", cc_max_m: 12.19 }, m),
    ).toBe("Cut & cover: 9.2 m down, within Phase 1's 12.19 m limit");
    expect(
      typeReason({ type: "shield", type_why: "mined_past_limit", depth_m: 13.6, phase: "1", cc_max_m: 12.19 }, m),
    ).toBe("Shield tunnel: 13.6 m down, past Phase 1's 12.19 m limit");
    expect(
      flagText(
        {
          kind: "platform_grade_over",
          data: { grade_permille: 12, limit_permille: 7.5, param: "literal.ERA.sgMax.lines_1_7" },
        },
        m,
        (x) => x,
      ),
    ).toBe("Platform grade +12.0‰ is over the limit of 7.5‰ (literal.ERA.sgMax.lines_1_7)");
    expect(flagText({ kind: "platform_slide_over", data: { slide_m: -235, limit_m: 150 } }, m, (x) => x)).toBe(
      "Platform slid −235 m from its drawn point; the limit is 150 m",
    );
    expect(worstSeverity([{ sev: "info" }, { sev: "warn" }])).toBe("warn");
    expect(worstSeverity([{ sev: "info" }])).toBeNull();
    expect(typeColour("cutcover")).toBe("#b088d6");
  });
  it("a value's source: Ben's unsaved draft, the saved record's writer, else the rule", () => {
    const saved: ProfileData = { st: { A: 150 } };
    expect(fieldSource({ st: { A: 151 } }, saved, "import:old_hub", "st", "A").text).toBe("Ben, not saved");
    expect(fieldSource(saved, saved, "import:old_hub", "st", "A").text).toBe("old hub");
    expect(fieldSource(saved, saved, "import:profile_lines", "st", "A").text).toBe("line file");
    expect(fieldSource(saved, saved, "ben", "sg", "A", "platform.grade.limit_by_era").text).toBe("rule");
  });
  it("a level of the default design laid in (S57) is the design's, not Ben's and not saved", () => {
    const held: ProfileData = { st: {} };
    const shown: ProfileData = { st: { A: 150.2 } };
    const src = fieldSource(shown, held, "import:profile_lines", "st", "A", undefined, held);
    expect(src.text).toBe("default design, not saved");
    expect(src.changed).toBe(false);
    // once the draft took it (Ben's first edit), it is his unsaved value
    expect(fieldSource(shown, held, "import:profile_lines", "st", "A", undefined, shown).text).toBe("Ben, not saved");
  });
});

/** A station fact with the fields the bands read. */

describe("station drawing from station.facts@1 (A.1)", () => {
  it("the structure quad tilts with the platform and keeps the box's offsets", () => {
    const q = structureQuad(fact({ platform_grade_permille: 10 })) as [number, number][];
    expect(q[0]).toEqual([940, expect.closeTo(149.4 + 5.2, 6)]);
    expect(q[1]).toEqual([1060, expect.closeTo(150.6 + 5.2, 6)]);
    expect(q[2]?.[1]).toBeCloseTo(150.6 - 1.0, 6);
    expect(structureQuad(fact({ structure: null }))).toBeNull();
  });
  it("access shapes: end halls on the roof, the crossunder 1.0 to 3.75 under the rail, the shaft to the ground", () => {
    const base = {
      type: "end_halls",
      dashed: true,
      halls: [
        [940, 965],
        [1035, 1060],
      ] as [number, number][],
      passage: null,
      shaft: null,
      hall_bottom_m: 155.2,
      hall_top_m: 158.55,
      mezz: null,
    };
    const halls = accessShapes(fact({ access: base as StationFact["access"] }), () => 163.6);
    expect(halls.map((h) => [h.what, h.label, h.dashed])).toEqual([
      ["hall", "ticket hall", true],
      ["hall", "ticket hall", true],
    ]);
    const xu = accessShapes(
      fact({
        access: {
          ...base,
          type: "platform_level_xu",
          halls: [],
          passage: [940, 943],
        } as unknown as StationFact["access"],
      }),
      () => 163.6,
    );
    expect(xu[0]).toMatchObject({ what: "crossunder", z0: 146.25, z1: 149, label: "crossunder" });
    const deep = accessShapes(
      fact({ access: { ...base, type: "deep", halls: [], shaft: [997, 1003] } as unknown as StationFact["access"] }),
      () => 163.6,
    );
    expect(deep[0]).toMatchObject({ what: "shaft", z0: 155.2, z1: 163.6, label: "lifts" });
    expect(drawsDHall({ type: "platform_level", d_hall_m: 8.55, halls: [] })).toBe(true);
    expect(drawsDHall({ type: "mined_hall", d_hall_m: 8.55, halls: [] })).toBe(false);
  });
});

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

function view(c0: number, c1: number): SheetView {
  const plot = { x: 60, y: 84, w: 530, h: 300 };
  const sx = plot.w / (c1 - c0);
  const sy = plot.h / 100;
  return {
    c0,
    c1,
    z0: 100,
    z1: 200,
    width: 604,
    height: 440,
    dpr: 1,
    top: 388,
    plot,
    x: (c) => plot.x + (c - c0) * sx,
    c: (x) => c0 + (x - plot.x) / sx,
    y: (z) => plot.y + (200 - z) * sy,
    z: (y) => 200 - (y - plot.y) / sy,
    units: new Units("m"),
    cursor: null,
  };
}

describe("station bands mark what they drew", () => {
  const facts = [
    fact({}),
    fact({
      platform_id: "B",
      name: "B",
      index: 1,
      point_c_m: 2000,
      c_m: 1765,
      slide_m: -235,
      level_m: null,
      level_set: false,
      type: "shield",
      structure: { kind: "A", top_m: 150, bottom_m: 144.5 },
      flags: [
        {
          kind: "platform_slide_over",
          sev: "error",
          c0: 1705,
          c1: 1825,
          rule: "platform.slide.limit_never_clamped",
          data: {},
        },
      ],
    }),
    fact({
      platform_id: "C",
      name: "C",
      deleted: true,
      index: null,
      point_c_m: 2500,
      c_m: 2500,
      rail_m: null,
      structure: null,
    }),
  ];
  const data = (): BandData => ({
    sectionId: "S",
    input: {
      params: { platform_m: 120 },
      stations: [
        { platform_id: "A", order: 0, c_m: 1000, level_m: 150, grade_permille: 0 },
        { platform_id: "B", order: 1, c_m: 1765, level_m: null, grade_permille: 0 },
      ],
      pvi: [],
      ground: { z_m: new Float64Array(2000).fill(163.6), step_m: 2 },
    } as unknown as BandData["input"],
    rail: { rail_m: new Float64Array(2000).fill(152), grade_permille: new Float64Array(2000), step_m: 2 },
    server: null,
    profile: null,
    selected: { band: "platforms", kind: "station", index: 1, id: "B", c: 1765 },
    platformName: (id) => id,
    stopC: (id) => (id === "B" ? 2000 : id === "A" ? 1000 : null),
    facts,
  });
  it("bars, drawn points, slides, unset levels, removed stations, outlines, flags and the strip", () => {
    const marks: SheetMark[] = [];
    const d = { ...data(), mark: (x: SheetMark) => marks.push(x) };
    const g = fakeContext();
    const v = view(0, 3000);
    for (const b of [stationStructureBand, stationAccessBand, platformBand, stationFlagsBand, stationStripBand])
      b.draw(g, v, d);
    const bar = (id: string) => marks.find((x) => x.kind === "bar" && x.id === id) as Record<string, unknown>;
    expect(bar("A")).toMatchObject({ c0: 940, c1: 1060, z0: 150, z1: 150, unset: false, sev: null });
    // B has no level: a dashed bar at ground − 7.62 (the fact's default), outlined red for its slide error.
    expect(bar("B")).toMatchObject({ unset: true, z0: 156, sev: "error", selected: true });
    expect(marks.find((x) => x.kind === "point" && x.id === "B")).toMatchObject({ c: 2000, slide: -235 });
    expect(marks.find((x) => x.kind === "point" && x.id === "A")).toMatchObject({ c: 1000, slide: 0 });
    expect(marks.find((x) => x.kind === "removed")).toMatchObject({ id: "C", c: 2500 });
    expect(marks.filter((x) => x.kind === "structure").map((x) => [x.id, x.type, x.what])).toEqual([
      ["A", "cutcover", "box"],
      ["B", "shield", "A"],
    ]);
    expect(marks.filter((x) => x.kind === "flag")).toEqual([
      expect.objectContaining({ id: "B", flag: "platform_slide_over", sev: "error" }),
    ]);
    expect(marks.filter((x) => x.kind === "strip").map((x) => x.type)).toEqual(["cutcover", "shield"]);
    // a click on the flag triangle is a flag handle for B
    const f = marks.find((x) => x.kind === "flag") as unknown as { x: number; y: number };
    expect(stationFlagsBand.hit?.(f.x, f.y)).toMatchObject({ kind: "flag", id: "B" });
  });
  it("level tags and slide notes only where there is room: none at the whole-line view, the selected one always", () => {
    // At the whole line (20 km in 530 px a platform is 3 px) the tags and "slid" notes ran into each other and over
    // the next stations' bars downtown (parity review, 23 November). Zoomed in they come back.
    const tags = (c1: number, sel: BandData["selected"]) => {
      const marks: SheetMark[] = [];
      platformBand.draw(fakeContext(), view(c1 > 3000 ? 0 : 500, c1), {
        ...data(),
        selected: sel,
        mark: (x: SheetMark) => marks.push(x),
      });
      return marks
        .filter((x) => x.kind === "tag")
        .map((x) => `${x.id} ${x.what}`)
        .sort();
    };
    expect(tags(20000, null)).toEqual([]);
    expect(tags(2000, null)).toEqual(["A level", "B slide"]);
    expect(tags(20000, { band: "platforms", kind: "station", index: 0, id: "A", c: 1000 })).toEqual(["A level"]);
    expect(tags(20000, { band: "platforms", kind: "station", index: 1, id: "B", c: 1765 })).toEqual(["B slide"]);
  });
  it("'level not set' tags: one per station at most, none over another, at any zoom (S57)", () => {
    // 20 stations with no level, 150 m apart (two platforms at each stop): at the whole line the tags piled into
    // one smudge (Line 10 before its default design was drawn, parity3 shots)
    const n = 20;
    const stations = Array.from({ length: n * 2 }, (_, i) => ({
      platform_id: `U${i}`,
      order: i,
      c_m: 1000 + Math.floor(i / 2) * 150,
      level_m: null,
      grade_permille: 0,
    }));
    const fs = stations.map((s, i) =>
      fact({ platform_id: s.platform_id, name: s.platform_id, index: i, point_c_m: s.c_m, c_m: s.c_m, slide_m: 0 }),
    );
    const unsetTags = (c0: number, c1: number) => {
      const marks: SheetMark[] = [];
      platformBand.draw(fakeContext(), view(c0, c1), {
        ...data(),
        input: { ...(data().input as object), stations } as unknown as BandData["input"],
        facts: fs.map((f) => ({ ...f, level_m: null, level_set: false })),
        selected: null,
        mark: (x: SheetMark) => marks.push(x),
      });
      return marks.filter((x) => x.kind === "unset-tag").map((x) => x.id);
    };
    const whole = unsetTags(0, 20000);
    expect(new Set(whole).size).toBe(whole.length);
    expect(whole.length).toBeGreaterThan(0);
    expect(whole.length).toBeLessThan(n);
    // zoomed in on four stops, each stop's tag is drawn, once
    const near = unsetTags(950, 1500);
    expect(near.length).toBe(4);
  });
  it("the readout inside a platform reads its type, structure and street", () => {
    const lines = readoutLines(data(), 1000, new Units("m"));
    expect(lines).toEqual(
      expect.arrayContaining(["Station A", "Cut & cover", "under Central Parkway (built over the subway)"]),
    );
  });
});
