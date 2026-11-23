// P3's functions one by one: the branches the goldens do not reach (an RER level crossing on a minor street, a
// neighbour with no levels, the other line read from its solved structure), the rule ids, and the module.

import { describe, expect, test } from "vitest";
import {
  boredGap,
  CROSSINGS_MODULE,
  CROSSINGS_RULES,
  contextClearances,
  crossingClearances,
  crossingsModule,
  hallAt,
  kindAt,
  needSep,
  otherRail,
  otherStruct,
  roadChecks,
  roadClear,
  roadsIn,
  stationStreet,
  streetAtC,
  subwayStreet,
} from "../../../src/port/crossings/index.ts";
import { TYPES_MODULE } from "../../../src/port/structure/index.ts";
import type { Neighbour, Structure, TypedModel } from "../../../src/port/types.ts";
import { RULE_IDS } from "../../../src/rules.gen.ts";
import { loadOldPage } from "../../golden/old_page/load.ts";
import { goldenTypes } from "../from_golden.ts";
import { crossingModel, neighbourOf } from "./neighbours.ts";

const L6 = (): TypedModel => crossingModel("Line_6");
const metroN = (m: TypedModel): Neighbour => m.input.neighbours.Line_3 as Neighbour;
const rerN = (m: TypedModel): Neighbour => m.input.neighbours.RER_E_trunk as Neighbour;

describe("separation", () => {
  test("between two bored tunnels the bored gap, else SEP_GAP (clearance.crossing.bored_gap)", () => {
    const m = L6();
    const s = m.structure;
    if (!s || !m.tables) throw new Error("Line 6 has the record");
    const gap = Math.max(s.tubes.A.spacing - s.tubes.A.outside, s.tubes.C.spacing - s.tubes.C.outside);
    expect(boredGap(m)).toBeCloseTo(gap, 12);
    const tube = m.tables.tube;
    const box = m.tables.box;
    expect(needSep(m, tube, tube)).toBeCloseTo(tube.below + gap + tube.top, 12);
    expect(needSep(m, box, tube)).toBeCloseTo(tube.below + m.literals.SEP_GAP + box.top, 12);
    expect(boredGap({ structure: null, literals: m.literals })).toBe(m.literals.SEP_GAP);
  });
});

describe("kindAt: the other line's structure guessed from its depth", () => {
  const m = L6();
  const g = 200;
  const cOff = 1000; // Line 6 has no river at 1+000
  test("over the ground by elevAbove a viaduct; within coverBelow at grade; no ground at grade", () => {
    const n = metroN(m);
    expect(kindAt(m, n, g + n.settings.elevAbove, g, cOff).k).toBe("elevated");
    expect(kindAt(m, n, g - 1, g, cOff).k).toBe("atgrade");
    expect(kindAt(m, n, g - 1, Number.NaN, cOff).k).toBe("atgrade");
  });
  test("a Metro line shallower than the box a trough, the RER never", () => {
    const top = m.tables?.box.top as number;
    expect(kindAt(m, metroN(m), g - (top - 0.1), g, cOff).k).toBe("trough");
    expect(kindAt(m, rerN(m), g - (top - 0.1), g, cOff).k).toBe("box");
  });
  test("bored where the tube has its cover, the box where it lacks it", () => {
    const n = metroN(m);
    const tube = otherStruct(m, n, "shield", cOff);
    const deepEnough = tube.top + (tube.od ?? 0) + 1;
    expect(kindAt(m, n, g - deepEnough, g, cOff)).toEqual(tube);
    expect(kindAt(m, n, g - (tube.top + 0.5), g, cOff).k).toBe("box");
  });
  test("the RER's bore and box from its settings", () => {
    const n = rerN(m);
    const rer = n.settings.rer;
    if (!rer) throw new Error("the RER neighbour carries settings.rer");
    expect(kindAt(m, n, g - 40, g, cOff)).toEqual({ k: "bore", below: rer.invertDepth, top: rer.boreCrown });
    expect(otherStruct(m, n, "cutcover", cOff)).toEqual({ k: "box", below: rer.invertDepth, top: rer.envelope });
    expect(otherStruct(m, n, "atgrade", cOff).top).toBe(n.open_clear_m);
  });
  test("in a river: a bridge over the pool, else the sunk box", () => {
    const r = m.rivers[0];
    if (!r) throw new Error("Line 6 crosses the Ohio");
    const c = (r.c0 + r.c1) / 2;
    const pool = m.settings.pool;
    expect(kindAt(m, metroN(m), pool + m.literals.bridgeAbovePool, g, c).k).toBe("elevated");
    const sunk = kindAt(m, metroN(m), pool - 20, g, c);
    expect(sunk).toEqual({ k: "sunk", below: m.sunk.below, top: m.sunk.top });
  });
  test("a neighbour missing what the guess needs throws, never guesses a value", () => {
    const n = rerN(m);
    const bare: Neighbour = { ...n, settings: { ...n.settings, rer: undefined } };
    expect(() => otherStruct(m, bare, "shield", cOff)).toThrow(/settings.rer/);
    const noClear: Neighbour = { ...n, open_clear_m: undefined };
    expect(() => otherStruct(m, noClear, "atgrade", cOff)).toThrow(/open_clear_m/);
  });
});

describe("crossings", () => {
  test("a crossing with a line the hub has no levels for: nothing checked, listed apart", () => {
    const m = L6();
    const x = m.input.crossings[0];
    if (!x) throw new Error("Line 6 has crossings");
    const lone = { ...m, input: { ...m.input, crossings: [x], neighbours: {} } };
    const [r] = crossingClearances(lone, TYPES_MODULE);
    expect(r).toMatchObject({ zo: null, clear: null, need: null, to: null, ok: false, pending: true, source: null });
    expect(otherRail(null, x.oc)).toBeNull();
  });

  test("the other line read from its solved structure (clearance.crossing.other_line_guessed), off by default", () => {
    const m = L6();
    const x = m.input.crossings[0];
    if (!x) throw new Error("Line 6 has crossings");
    const n = m.input.neighbours[x.wid] as Neighbour;
    const solvedBox: Structure = { k: "box", below: 9, top: 9 };
    const withSolved = {
      ...m,
      input: {
        ...m.input,
        crossings: [x],
        neighbours: { [x.wid]: { ...n, solved: { type: "cutcover" as const, structure: solvedBox, rail: 0 } } },
      },
    };
    const [guessed] = crossingClearances(withSolved, TYPES_MODULE);
    const [read] = crossingClearances(withSolved, TYPES_MODULE, { otherFromSolved: true });
    expect(guessed?.to).not.toEqual(solvedBox);
    expect(read?.to).toEqual(solvedBox);
  });

  test("the hall over a box station: the check runs over its roof (clearance.hall.checks_over_hall_roof)", () => {
    const m = crossingModel("Line_4");
    const x = crossingClearances(m, TYPES_MODULE).find((q) => q.c === 15868);
    const h = hallAt(m, 15868);
    expect(h).not.toBeNull();
    expect(x?.hall).toBe(h?.station);
    expect(x?.t.top).toBeCloseTo((h?.top as number) - (x?.z as number), 9);
    expect(x?.rule).toBe("clearance.hall.checks_over_hall_roof");
    expect(hallAt({ ...m, input: { ...m.input, system: "rer" } }, 15868)).toBeNull();
    expect(hallAt({ ...m, structure: null }, 15868)).toBeNull();
  });

  test("every check cites a rule of the registry, from CROSSINGS_RULES", () => {
    const ids = new Set<string>(RULE_IDS);
    for (const r of CROSSINGS_RULES) expect(ids.has(r)).toBe(true);
    const rules = new Set<string>(CROSSINGS_RULES);
    for (const line of ["Line_4", "Line_6", "CVG_Express"]) {
      const m = crossingModel(line);
      for (const x of crossingClearances(m, TYPES_MODULE))
        if (x.clear != null) expect(rules.has(x.rule as string)).toBe(true);
      for (const x of contextClearances(m, TYPES_MODULE)) expect(rules.has(x.rule as string)).toBe(true);
      for (const x of roadChecks(m, TYPES_MODULE)) expect(rules.has(x.rule as string)).toBe(true);
    }
  });
});

describe("roads and streets", () => {
  test("an RER line at grade across a minor street is a warning, across a major road an error", () => {
    const m = crossingModel("Line_9");
    const rer = { ...m, input: { ...m.input, system: "rer" as const } };
    const T = goldenTypes(loadOldPage("Line_9"));
    const atGrade = { ...T, typeAt: () => "atgrade" as const };
    const metro = roadChecks(m, atGrade).filter((r) => r.kind === "level_crossing");
    const onRer = roadChecks(rer, atGrade).filter((r) => r.kind === "level_crossing");
    expect(metro.every((r) => r.sev === "error")).toBe(true);
    for (const r of onRer) expect(r.sev).toBe(m.input.context.roads[r.road]?.[5] === "minor" ? "warn" : "error");
    expect(onRer.some((r) => r.sev === "warn")).toBe(true);
  });

  test("a viaduct pier in a road is one warning per road; with no span the deck sets the underside", () => {
    const m = crossingModel("Line_9");
    const road = m.input.context.roads[0];
    if (!road) throw new Error("Line 9 crosses roads");
    const mid = (road[1] + road[2]) / 2;
    const spans = [
      { c0: mid - 25, c1: mid, L: 25, truss: false, below: 3, above: 0, ends: [false, false] as const },
      { c0: mid, c1: mid + 25, L: 25, truss: false, below: 3, above: 0, ends: [false, false] as const },
    ];
    const T = { ...TYPES_MODULE, typeAt: () => "elevated" as const };
    const piers = roadChecks(m, T, spans).filter((r) => r.kind === "pier_in_road");
    expect(piers).toHaveLength(1);
    expect(piers[0]).toMatchObject({ c: mid, road: 0, sev: "warn", rule: "road.piers_out_of_roads" });
    const over = roadChecks(m, T, []).filter((r) => r.kind === "clearance_over_road");
    for (const r of over) expect(r.need).toBe(roadClear(m, m.input.context.roads[r.road]?.[5] as string));
  });

  test("streets: the street 5 m past its ends, the roads across the platform, unknown with no context", () => {
    const m = crossingModel("Line_6");
    const st = m.input.context.streets[0];
    if (!st) throw new Error("Line 6 has streets");
    expect(streetAtC(m, st[1] + 5)).toBe(0);
    expect(streetAtC(m, st[1] + 5.01)).not.toBe(0);
    const r = m.input.context.roads[0];
    if (r) expect(roadsIn(m, r[2], r[2] + 1)).toContain(0);
    const s = m.stations[0];
    if (!s) throw new Error("Line 6 has stations");
    const none = { ...m, input: { ...m.input, context: { ...m.input.context, streets: [], roads: [] } } };
    expect(stationStreet(none, s)).toEqual({ street: -1, subway: false, roads: [], known: false });
    expect(subwayStreet(m, "Central Parkway")).toBe(true);
    expect(subwayStreet(m, "Paddock Road")).toBe(false);
    expect(subwayStreet({ structure: null }, "Central Parkway")).toBe(false);
  });
});

describe("module", () => {
  test("CROSSINGS_MODULE is P3's functions on P1's TYPES_MODULE; crossingsModule takes another", () => {
    const m = crossingModel("Line_4");
    expect(CROSSINGS_MODULE.crossings(m)).toEqual(crossingClearances(m, TYPES_MODULE));
    expect(CROSSINGS_MODULE.context(m)).toEqual(contextClearances(m, TYPES_MODULE));
    expect(CROSSINGS_MODULE.roadChecks(m)).toEqual(roadChecks(m, TYPES_MODULE));
    const T = goldenTypes(loadOldPage("Line_4"));
    expect(crossingsModule(T).crossings(m)).toEqual(crossingClearances(m, T));
  });

  test("the neighbour the adapter builds is what otherRail reads (Line 6, Line 3 at 1+084)", () => {
    const d = loadOldPage("Line_6");
    const n = neighbourOf(d, "Line_3");
    expect(n?.source).toBe("profile");
    expect(otherRail(n, 2728.8)).toBeCloseTo(170, 6);
  });
});
