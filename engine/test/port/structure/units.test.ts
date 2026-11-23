// What the seed never exercises, on a golden line with Ben's tools used: a shaft, two paints in one stretch, a
// snapped paint, a painted bore through a mined station, a TBM selection before Phase 3; the selections'
// options; the shared helpers; the RER branches of structFor and reqCover.

import { describe, expect, test } from "vitest";
import {
  absorbShort,
  applyMS,
  effOvr,
  elevNeed,
  gradeLimitArrays,
  gradeLimitAt,
  gradeSeverity,
  reqCover,
  solveTypes,
  straightUnder,
  structFor,
  sttFromDoc,
  TYPES_MODULE,
  TYPES_RULES,
  tubeOf,
} from "../../../src/port/structure/index.ts";
import type { Align, PortDoc, SectionModel, Type } from "../../../src/port/types.ts";
import { codes, cutRange, gridOf, nearestIndex, rangesOf, runs, valueAt } from "../../../src/port/util.ts";
import { RULE_IDS } from "../../../src/rules.gen.ts";
import { fromGolden, structureOf } from "../from_golden.ts";

/** A golden line with its align changed as Ben's tools would, the effective paints rebuilt. */
function withAlign(m: SectionModel, patch: Partial<Align>): SectionModel {
  const align = { ...m.align, ...patch };
  return { ...m, align, effOvr: effOvr(m.stations, align, m.canon.locks, m.settings.platform, true) };
}

describe("Ben's tools on Line 6", () => {
  const { model } = fromGolden("Line_6");

  test("a shaft ends a stretch (geometry.anchor.shaft_brush)", () => {
    const base = solveTypes(model);
    const T = solveTypes(withAlign(model, { shafts: [6500] }));
    expect(T.shafts).toEqual([6500]);
    expect(T.stretches.length).toBe(base.stretches.length + 1);
    const after = T.stretches.find((s) => s.c0 === 6500);
    expect(after?.from).toEqual({ kind: "box" });
    expect(T.stretches.find((s) => s.c1 === 6498)).toBeTruthy();
    // a shaft off the tunnel is not one
    expect(solveTypes(withAlign(model, { shafts: [1084.2] })).shafts).toEqual([]);
  });

  test("two paints in one stretch: the larger takes it, flagged", () => {
    const m = withAlign(model, {
      ovr: [...model.align.ovr, [4800, 5000, "shield"], [5200, 5300, "deep"]],
    });
    const T = solveTypes(m);
    const f = T.flags.find((x) => x.kind === "two_paints_one_stretch");
    expect(f?.rule).toBe("structure.paint.two_paints_one_stretch");
    expect(f?.data).toMatchObject({ taken: "shield" });
    const s = T.stretches.find((x) => x.c0 <= 4800 && x.c1 >= 5300);
    expect(s).toMatchObject({
      method: "bored",
      why: "painted_bored",
      cls: "shield",
      rule: "geometry.method.paint_final",
    });
  });

  test("a paint over part of a stretch is snapped to its anchors", () => {
    const T = solveTypes(withAlign(model, { ovr: [...model.align.ovr, [4800, 4900, "cutcover"]] }));
    expect(T.flags.some((x) => x.kind === "paint_snapped" && x.sev === "info")).toBe(true);
    const s = T.stretches.find((x) => x.c0 <= 4800 && x.c1 >= 4900);
    expect(s).toMatchObject({ method: "box", why: "painted_cutcover" });
  });

  test("a painted bore through a mined station is flagged; the station keeps twin platform tunnels", () => {
    const T = solveTypes(withAlign(model, { tf: [[6700, 6900, "bore"]] }));
    const f = T.flags.filter((x) => x.kind === "bore_through_mined_station");
    expect(f.map((x) => x.data.station)).toEqual(["Oak"]);
    expect(f[0]?.rule).toBe("structure.tube_form.mined_station_twin");
  });

  test("a TBM selection before Phase 3 is flagged at the station (geometry.method.tbm_from_phase_3)", () => {
    const i = model.stations.findIndex((s) => s.name === "Bond Hill");
    const stt = model.align.stt.slice();
    stt[i] = "deep";
    const T = solveTypes(withAlign(model, { stt }));
    expect(T.stRole["Bond Hill"]).toBe("mined");
    expect(T.flags.find((x) => x.kind === "tbm_before_phase_3")?.data).toMatchObject({
      station: "Bond Hill",
      phase: "1",
    });
  });

  test("straightUnder is the grade limit's straight case where the line is underground", () => {
    const typed = { ...model, types: solveTypes(model), spans: [] };
    const { lim, warn } = gradeLimitArrays(typed);
    for (let i = 0; i < model.grid.n; i += 7) {
      const c = model.grid.c[i] as number;
      const L = gradeLimitAt(typed, c);
      const under = ["shield", "deep", "cutcover"].includes(TYPES_MODULE.typeAt(typed, c));
      expect(straightUnder(typed, c)).toBe((L.why === "straight_underground" || L.why === "straight") && under);
      expect(Number.isNaN(warn[i] as number)).toBe(gradeLimitAt(typed, c).warn === null);
      expect(lim[i]).toBe(gradeLimitAt(typed, c).lim);
    }
  });

  test("elevNeed: the deck and the mezzanine's clear height; no record, no answer", () => {
    expect(elevNeed(model)).toBe(model.settings.deckDepth + 3.5);
    expect(() => elevNeed({ ...model, structure: null })).toThrow(/mezzanine_clear_m/);
  });

  test("every rule the solve cites is a registry rule, and every flag cites one of TYPES_RULES", () => {
    const ids = new Set<string>(RULE_IDS);
    for (const r of TYPES_RULES) expect(ids.has(r), r).toBe(true);
    const mine = new Set<string>(TYPES_RULES);
    for (const f of solveTypes(model).flags) expect(mine.has(f.rule), f.kind).toBe(true);
    for (const s of solveTypes(model).stretches) expect(mine.has(s.rule)).toBe(true);
  });

  test("the solve is pure: the model is not changed and two runs are equal", () => {
    const before = JSON.stringify(model.align) + JSON.stringify(model.effOvr);
    const a = solveTypes(model);
    const b = solveTypes(model);
    expect(JSON.stringify(model.align) + JSON.stringify(model.effOvr)).toBe(before);
    expect(Array.from(a.type)).toEqual(Array.from(b.type));
    expect(a.flags).toEqual(b.flags);
  });
});

describe("selections", () => {
  const { model } = fromGolden("Line_2");
  const doc = (stt: Record<string, string>, ovr: PortDoc["ovr"]): PortDoc => ({
    st: {},
    sg: {},
    so: {},
    del: [],
    pvi: [],
    ovr,
    stt,
    tf: [],
    shafts: [],
    gnd: [],
    gapfill: [],
    mode: {},
    ready: false,
    frame: null,
  });
  const s0 = model.stations[3];
  if (!s0) throw new Error("Line_2 has stations");
  const paint: PortDoc["ovr"] = [[s0.c - 10, s0.c + 10, "shield"]];

  test("the page drops a selection equal to the paint at the centre (the 2 November migration); the hub keeps it", () => {
    const d = doc({ [s0.platform_id]: "shield" }, paint);
    expect(sttFromDoc(d, model.stations, paint)[3]).toBe("");
    expect(sttFromDoc(d, model.stations, paint, { dropMigrated: false })[3]).toBe("shield");
  });

  test("elevated is never dropped; an unknown value and a profile with no stt give none; the RER none", () => {
    const up: PortDoc["ovr"] = [[s0.c - 10, s0.c + 10, "elevated"]];
    expect(sttFromDoc(doc({ [s0.platform_id]: "elevated" }, up), model.stations, up)[3]).toBe("elevated");
    expect(sttFromDoc(doc({ [s0.platform_id]: "bored" }, []), model.stations, [])[3]).toBe("");
    expect(sttFromDoc(null, model.stations, []).every((x) => x === "")).toBe(true);
    expect(sttFromDoc(doc({ [s0.platform_id]: "deep" }, []), model.stations, [], { metro: false })[3]).toBe("");
  });

  test("effOvr: a paint across a station paints the running line; the selection the platform; a lock keeps its paint", () => {
    const half = model.settings.platform / 2;
    const align = {
      ovr: [[s0.c - 200, s0.c + 200, "cutcover"]] as Align["ovr"],
      stt: model.stations.map((_, i) => (i === 3 ? "deep" : "")) as Align["stt"],
    };
    const list = effOvr(model.stations, align, [], model.settings.platform, true);
    expect(list).toEqual([
      [s0.c - 200, s0.c - half, "cutcover"],
      [s0.c - half, s0.c + half, "deep"],
      [s0.c + half, s0.c + 200, "cutcover"],
    ]);
    const lock = { c0: 0, c1: 1, lo: 0, hi: 1, st: { [s0.name]: 150 }, pvi: [], ovr: [], src: "test" };
    expect(effOvr(model.stations, align, [lock], model.settings.platform, true)).toEqual([
      [s0.c - 200, s0.c + 200, "cutcover"],
    ]);
    expect(effOvr(model.stations, align, [], model.settings.platform, false)).toEqual(align.ovr);
  });
});

describe("tables and structures", () => {
  test("applyMS: the record's box, tubes A and C, the bore, the open clear height", () => {
    const T = applyMS(structureOf("Line_6"), 4.2);
    expect(T.box).toMatchObject({ k: "box", below: 1, top: 4.6 });
    expect(T.tube).toMatchObject({ k: "tube", od: 5.5, tube: "A" });
    expect(T.tube.below).toBeCloseTo(0.9, 12);
    expect(T.tube.top).toBeCloseTo(4.6, 12);
    expect(T.bore).toMatchObject({ k: "bore", od: 9, tube: "bore" });
    expect(T.openClear).toBe(4.57);
    expect(tubeOf({ inside: 7.5, outside: 8, rail_over_invert: 1, spacing: 4, label: "x" }, "C").k).toBe("bore");
  });

  test("the RER: the settings' box and bored tube, minCover over a tube, none over a box", () => {
    const { model } = fromGolden("Line_6");
    const rer = { envelope: 6.6, boreCrown: 7.5, invertDepth: 1, minCover: 8.5, surfStep: 250 };
    const m: SectionModel = {
      ...model,
      input: { ...model.input, system: "rer" },
      settings: { ...model.settings, rer },
    };
    const box = structFor(m, "cutcover", 500);
    const bore = structFor(m, "shield", 500);
    expect(box).toEqual({ k: "box", below: 1, top: 6.6 });
    expect(bore).toEqual({ k: "bore", below: 1, top: 7.5 });
    expect(reqCover(m, box)).toBe(0);
    expect(reqCover(m, bore)).toBe(8.5);
    expect(structFor(m, "shield", 10800)).toEqual({ k: "sunk", below: 1, top: 5 }); // under the Ohio
  });

  test("gradeSeverity: local within the limit, straight within the warning limit, else an error", () => {
    expect(gradeSeverity({ lim: 50, warn: null }, 50.05)).toBe("local");
    expect(gradeSeverity({ lim: 50, warn: 60 }, 55)).toBe("straight");
    expect(gradeSeverity({ lim: 50, warn: null }, 50.06)).toBe("error");
  });
});

describe("shared helpers", () => {
  test("rangesOf, cutRange", () => {
    expect(rangesOf([0, 1, 1, 0, 1], 0, 4, (x) => x === 1)).toEqual([
      [1, 2],
      [4, 4],
    ]);
    expect(cutRange([[0, 10, "a"]], 3, 5)).toEqual([
      [0, 3, "a"],
      [5, 10, "a"],
    ]);
    expect(cutRange([[0, 3, "a"]], 3, 5)).toEqual([[0, 3, "a"]]);
  });

  test("codes, valueAt, runs", () => {
    const a = codes<string | null>([null], ["x", "x", null, "y"]);
    expect(a.table).toEqual([null, "x", "y"]);
    expect(valueAt(a, 3)).toBe("y");
    expect(runs(a)).toEqual([
      ["x", 0, 1],
      [null, 2, 2],
      ["y", 3, 3],
    ]);
  });

  test("gridOf and nearestIndex (halves round up, held to the grid)", () => {
    const g = gridOf(9.5, 2);
    expect(g.n).toBe(5);
    expect(Array.from(g.c)).toEqual([0, 2, 4, 6, 8]);
    expect(nearestIndex(g, 1)).toBe(1);
    expect(nearestIndex(g, 3)).toBe(2);
    expect(nearestIndex(g, 99)).toBe(4);
    expect(nearestIndex(g, -5)).toBe(0);
  });

  test("absorbShort: a sliver takes the longer neighbour's type, never where it cannot be built", () => {
    const mk = (ts: Type[]) => ts.map((t, i) => ({ c: i * 2, t: t as Type | undefined }));
    const P = mk(["atgrade", "atgrade", "atgrade", "trough", "cutcover", "cutcover"]);
    absorbShort(P, 2, 20, () => true);
    expect(P.map((p) => p.t)).toEqual(["atgrade", "atgrade", "atgrade", "atgrade", "cutcover", "cutcover"]);
    const Q = mk(["atgrade", "trough", "cutcover", "cutcover", "cutcover"]);
    absorbShort(
      Q,
      2,
      20,
      () => true,
      () => true,
      (_p, t) => t !== "cutcover",
    );
    expect(Q.map((p) => p.t)).toEqual(["atgrade", "atgrade", "cutcover", "cutcover", "cutcover"]);
  });
});
