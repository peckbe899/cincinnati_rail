// The design the sheet draws where the profile holds none (claude/hub_maps/profiles_parity.md S57, S66, S84;
// app/src/plugins/line-sheet/design.ts): Lines 10, 11 and 13 on their default design, a default level for a station
// with none, Line 2b on the current stops. It is drawn and solved, never written, until Ben's first edit takes it
// into the draft in the same undo step.

import type { SectionInput } from "@cr/engine/contract";
import { describe, expect, it } from "vitest";
import type { Rec } from "../../src/api/types.ts";
import { Drafts } from "../../src/core/drafts.ts";
import { makeView } from "../../src/core/view.ts";
import {
  designNote,
  designOps,
  editOps,
  keepsDesign,
  laidIn,
  type SheetDesign,
} from "../../src/plugins/line-sheet/design.ts";
import { unsetTags } from "../../src/plugins/line-sheet/drawing.ts";
import {
  hasDesign,
  localInput,
  type ProfileData,
  setPviZ,
  setStationLevel,
  stationFrame,
} from "../../src/plugins/line-sheet/model.ts";

const design = (over: Partial<SheetDesign> = {}): SheetDesign => ({
  source: "default",
  note: "default design (not saved)",
  pvi: [
    { c: 400, z: 140 },
    { c: 900, z: 138.5 },
  ],
  st: { A: 150.2, B: 147.9, C: 152 },
  so: {},
  defaulted: ["A", "B", "C"],
  reframed: false,
  reframe: null,
  ...over,
});

/** A three-station section: the server's input of a profile with nothing saved (Line 10's record). */
const frame = stationFrame(
  [
    { id: "s1", data: { order: 0, c: 100 } },
    { id: "s2", data: { order: 1, c: 700 } },
    { id: "s3", data: { order: 2, c: 1200 } },
  ],
  [
    { id: "A", data: { stop: "s1", name: "Alpha" } },
    { id: "B", data: { stop: "s2", name: "Beta" } },
    { id: "C", data: { stop: "s3", name: "Gamma" } },
  ],
);
const input = {
  section_id: "sec",
  length_m: 1300,
  pvi: [],
  stations: [
    { platform_id: "A", order: 0, c_m: 100, level_m: null, grade_permille: 0 },
    { platform_id: "B", order: 1, c_m: 700, level_m: null, grade_permille: 0 },
    { platform_id: "C", order: 2, c_m: 1200, level_m: null, grade_permille: 0 },
  ],
} as unknown as SectionInput;

describe("a profile with no saved level and no bend point is drawn on its default design", () => {
  const empty: ProfileData = { pvi: [], st: {}, so: {}, del: [] };

  it("lays the default levels and bend points in, so the sheet draws and solves a rail", () => {
    expect(hasDesign(localInput(input, empty, frame))).toBe(false);
    const shown = laidIn(empty, design());
    const li = localInput(input, shown, frame);
    expect(hasDesign(li)).toBe(true);
    expect(li.stations.map((s) => s.level_m)).toEqual([150.2, 147.9, 152]);
    expect(li.pvi).toEqual([
      { c_m: 400, z_m: 140 },
      { c_m: 900, z_m: 138.5 },
    ]);
    // the record is untouched: laidIn works on a copy
    expect(empty).toEqual({ pvi: [], st: {}, so: {}, del: [] });
    expect(designNote(empty, design())).toBe("default design (not saved)");
  });

  it("lays nothing once the profile holds the design (the draft took it), and says nothing", () => {
    const shown = laidIn(empty, design());
    expect(designOps(shown, design())).toEqual([]);
    expect(laidIn(shown, design())).toBe(shown);
    expect(designNote(shown, design())).toBeNull();
  });

  it("a station with no level on a line with some takes the default level, Ben's levels and bends stay", () => {
    const d = design({ source: "partial", note: "default level (not saved) where no level is set", defaulted: ["B"] });
    const mine: ProfileData = { pvi: [[300, 141]], st: { A: 151, C: 153 } };
    const shown = laidIn(mine, d);
    expect(shown.st).toEqual({ A: 151, C: 153, B: 147.9 });
    expect(shown.pvi).toEqual([[300, 141]]);
    expect(designNote(mine, d)).toBe("default level (not saved) where no level is set");
  });

  it("a saved design in its own frame lays nothing and is not kept", () => {
    const saved = design({ source: "saved", note: "saved", defaulted: [] });
    expect(designOps({ pvi: [[1, 2]], st: { A: 1 } }, saved)).toEqual([]);
    expect(keepsDesign(saved)).toBe(false);
    expect(keepsDesign(design())).toBe(true);
    expect(designOps(empty, null)).toEqual([]);
  });
});

describe("a profile saved in an older frame is drawn on the current stops (Line 2b, reframeDoc)", () => {
  const old: ProfileData = {
    pvi: [
      [242, 154.5],
      [425, 153.9],
    ],
    st: { A: 153, B: 176.1, C: 198.7 },
    ovr: [[1014, 1355, "cutcover"]],
    so: {},
    frame: { length_m: 1290, point_c: { A: 100, B: 690, C: 1190 } },
  };
  const rf = design({
    source: "saved",
    note: "saved",
    defaulted: [],
    reframed: true,
    pvi: [
      { c: 243.1, z: 154.5 },
      { c: 427.3, z: 153.9 },
    ],
    st: { A: 153, B: 176.1, C: 198.7 },
    so: { B: -0.5 },
    reframe: {
      ovr: [[1020.2, 1362.4, "cutcover"]],
      tf: [],
      shafts: [],
      gnd: [],
      frame: { length_m: 1300, point_c: { A: 100, B: 700, C: 1200 } },
    },
  });

  it("lays the mapped bend points, slides, paints and the current frame in; Ben's levels stay", () => {
    expect(keepsDesign(rf)).toBe(true);
    const shown = laidIn(old, rf);
    expect(shown.pvi).toEqual([
      [243.1, 154.5],
      [427.3, 153.9],
    ]);
    expect(shown.so).toEqual({ B: -0.5 });
    expect(shown.ovr).toEqual([[1020.2, 1362.4, "cutcover"]]);
    expect(shown.frame).toEqual({ length_m: 1300, point_c: { A: 100, B: 700, C: 1200 } });
    expect(shown.st).toEqual(old.st);
    // the stations stand at their centres as slid on the current stops
    expect(localInput(input, shown, frame).stations.map((s) => s.c_m)).toEqual([100, 699.5, 1200]);
    expect(designNote(old, rf)).toBe("drawn on the current stops (not saved)");
    // once in the current frame, nothing more is laid in
    expect(designOps(shown, rf)).toEqual([]);
  });
});

describe("the design is written only with Ben's first edit, as one undo step", () => {
  const view = makeView({ layer: "try" });
  const rec: Rec = {
    kind: "profile",
    id: "p10",
    layer: "try",
    version: 1,
    data: { section: "sec", pvi: [], st: {}, so: {}, del: [] },
    geom: null,
  } as unknown as Rec;

  it("opening and viewing write nothing", () => {
    const drafts = new Drafts();
    // what the sheet does to show the line: read and lay in, never edit
    const held = drafts.view(rec, view).data as ProfileData;
    const shown = laidIn(held, design());
    expect(hasDesign(localInput(input, shown, frame))).toBe(true);
    expect(drafts.all()).toEqual([]);
    expect(rec.data).toEqual({ section: "sec", pvi: [], st: {}, so: {}, del: [] });
  });

  it("the first edit takes the design with it; one Ctrl+Z puts the untouched record back", () => {
    const drafts = new Drafts();
    const held = drafts.view(rec, view).data as ProfileData;
    const shown = laidIn(held, design());
    // Ben drags the first bend point down 2 m
    const ops = editOps(held, design(), setPviZ(shown, 0, 138));
    expect(ops).not.toBeNull();
    drafts.edit(rec, view, ops ?? [], { step: "drag-1" });
    const d = drafts.get("profile", "p10", view);
    expect(d?.body.data).toMatchObject({
      pvi: [
        [400, 138],
        [900, 138.5],
      ],
      st: { A: 150.2, B: 147.9, C: 152 },
    });
    // the rest of the drag is the same step, with nothing more laid in
    const held2 = drafts.view(rec, view).data as ProfileData;
    expect(designOps(held2, design())).toEqual([]);
    drafts.edit(rec, view, editOps(held2, design(), setPviZ(held2, 0, 137.5)) ?? [], { step: "drag-1" });
    drafts.stepBack();
    expect(drafts.all()).toEqual([]);
    expect(drafts.view(rec, view).data).toEqual(rec.data);
  });

  it("an edit that changes nothing writes nothing, the design included", () => {
    const held = { pvi: [], st: {} } as ProfileData;
    const shown = laidIn(held, design());
    expect(editOps(held, design(), setStationLevel(shown, "A", 150.2))).toBeNull();
    expect(editOps(held, design(), [])).toBeNull();
    // with nothing to lay in, the edit's ops go as they are
    expect(editOps(shown, design(), setStationLevel(shown, "A", 151))).toEqual(setStationLevel(shown, "A", 151));
  });
});

describe("'level not set' tags never pile up", () => {
  it("keeps one tag where several would overlap, and every tag that stands clear", () => {
    const w = 60;
    // two platforms of one stop (same place), a third 20 px on, a fourth far off
    const kept = unsetTags([
      { x: 100, y: 200, w },
      { x: 100, y: 200, w },
      { x: 120, y: 202, w },
      { x: 400, y: 200, w },
    ]);
    expect([...kept].sort()).toEqual([0, 3]);
  });
  it("the selected station's tag first; a tag over another at another height stands", () => {
    const kept = unsetTags([
      { x: 100, y: 200, w: 60 },
      { x: 110, y: 200, w: 60, selected: true },
      { x: 100, y: 260, w: 60 },
      { x: Number.NaN, y: Number.NaN, w: 0 },
    ]);
    expect([...kept].sort()).toEqual([1, 2]);
  });
  it("a whole line of 29 unset stations 8 px apart draws a handful, never 29", () => {
    const items = Array.from({ length: 29 }, (_, i) => ({ x: 100 + i * 8, y: 300 + (i % 3) * 4, w: 58 }));
    const kept = unsetTags(items);
    expect(kept.size).toBeLessThan(6);
    expect(kept.size).toBeGreaterThan(1);
  });
});
