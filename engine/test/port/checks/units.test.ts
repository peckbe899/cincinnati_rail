// P4's functions on small cases the goldens do not reach: the drawn ground's limits (no seed line breaks them), the
// level solver's unset station (the page wrote 0 m), the reframe's pairing and slides, the live stations, the curve
// arrays on a drawn circle, the drawing checks, the order and repeats of allIssues, and the RER's surface bend points
// (slice 2: ported, not golden-tested).

import { describe, expect, test } from "vitest";
import type { PathPoint } from "../../../src/geom/path.ts";
import {
  allIssues,
  curveAllowance,
  drawingFlags,
  gndChecks,
  proposeFill,
  radii,
} from "../../../src/port/checks/index.ts";
import {
  alignFromDoc,
  defaultAlign,
  deriveStations,
  reframeDoc,
  resetLine,
  surfacePvis,
} from "../../../src/port/levels/index.ts";
import type { IssueParts, LevelModel, PortDoc, PortFlag, SectionModel, TypeSolve } from "../../../src/port/types.ts";
import { fromGolden, goldenTypes, typedFromGolden } from "../from_golden.ts";
import { ALIGN_DEPS, levelInput } from "./input.ts";

const M_PER_DEG_LAT = 110540;

describe("gndChecks: the drawn ground's limits (ground.drawn.limits)", () => {
  const base = fromGolden("Line_6").model;
  const withGnd = (
    gnd: { c: number; z: number }[][],
  ): Pick<SectionModel, "align" | "settings" | "grid" | "ground"> => ({
    ...base,
    align: { ...base.align, gnd },
    ground: { ...base.ground, cross: [] },
  });

  test("an end slope steeper than fillSlope, and a grade between steeper than groundMax, are errors", () => {
    // fillSlope 500 per mille, groundMax 150 per mille on the Metro
    const P = [
      { c: 1000, z: 200 },
      { c: 1010, z: 206 }, // 600 per mille at the end
      { c: 1110, z: 222 }, // 160 per mille between
      { c: 1210, z: 222 },
      { c: 1230, z: 214 }, // 400 per mille at the end: within fillSlope
    ];
    const f = gndChecks(withGnd([P]));
    expect(f.map((x) => [x.kind, x.sev, x.c0, x.c1])).toEqual([
      ["ground_end_slope", "error", 1000, 1010],
      ["ground_steep", "error", 1010, 1110],
      // the 100 m windows from 1+010 to 1+046 average over 100 per mille: the run ends 100 m past the last
      ["ground_sustained", "warn", 1010, 1146],
    ]);
    expect(f.every((x) => x.rule === "ground.drawn.limits")).toBe(true);
  });

  test("a grade over groundWarn sustained over groundSustain is one warning, its steepest average kept", () => {
    const P = [
      { c: 0, z: 100 },
      { c: 100, z: 100 },
      { c: 400, z: 133 }, // 110 per mille for 300 m
      { c: 500, z: 133 },
      { c: 510, z: 130 },
    ];
    const f = gndChecks(withGnd([P]));
    expect(f).toHaveLength(1);
    expect(f[0]?.kind).toBe("ground_sustained");
    expect(((f[0]?.data ?? {}) as { g?: number }).g).toBeCloseTo(110, 6);
  });

  test("the other lines' ground across this line is a note (ground.drawn.counts_across_crossing_street)", () => {
    const m = {
      ...base,
      ground: {
        ...base.ground,
        cross: [{ c0: 10, c1: 25, z: 150, wid: "Line_2", with: "Line 2", street: null, w: 15 }],
      },
    };
    const f = gndChecks(m);
    expect(f.map((x) => [x.kind, x.sev, x.c, x.rule])).toEqual([
      ["ground_from_crossing", "info", 17.5, "ground.drawn.counts_across_crossing_street"],
    ]);
  });
});

describe("the level solver: a station with no bound (network.level_solver.shallow_as_grade_allows)", () => {
  test("no ground and no canon level: NaN and flagged, where the page wrote 0 m (rule fix)", () => {
    const { model } = fromGolden("Line_2b");
    const dem = new Float32Array(model.ground.finished.length).fill(Number.NaN);
    const m: LevelModel = { ...model, ground: { ...model.ground, finished: dem } };
    const lv = defaultAlign(m, null, [], null);
    expect(lv.unset).toEqual([0, 1, 2, 3, 4]);
    expect(lv.st.every((v) => Number.isNaN(v))).toBe(true);
    expect(lv.flags.map((f) => [f.kind, f.sev, f.rule])).toEqual(
      new Array(5).fill(["station_level_unbounded", "warn", "network.level_solver.shallow_as_grade_allows"]),
    );
  });

  test("one bounded station holds the others to the grade limit both ways", () => {
    const { model } = fromGolden("Line_2b");
    const dem = new Float32Array(model.ground.finished.length).fill(Number.NaN);
    const m: LevelModel = {
      ...model,
      ground: { ...model.ground, finished: dem },
      canon: { ...model.canon, fixed: { 2: { abs: 150, src: "test" } } },
    };
    const lv = defaultAlign(m, null, [], null);
    expect(lv.unset).toEqual([]);
    expect(lv.st[2]).toBe(150);
    // an upper and a lower bound at the fixed station: the others are within the grade limit of it, not 0
    expect(lv.st.every((v) => Number.isFinite(v) && v !== 0)).toBe(true);
  });

  test("alignFromDoc keeps a saved level over an unset default and flags only stations still unset", () => {
    const input = levelInput("Line_2b");
    const r = alignFromDoc({ ...input, dem: new Float32Array(input.dem.length).fill(Number.NaN) }, ALIGN_DEPS);
    // every Line 2b station has a saved level
    expect(r.align.st.every((v) => Number.isFinite(v))).toBe(true);
    expect(r.flags.filter((f) => f.kind === "station_level_unbounded")).toEqual([]);
    const reset = alignFromDoc(
      { ...input, doc: null, dem: new Float32Array(input.dem.length).fill(Number.NaN) },
      ALIGN_DEPS,
    );
    expect(reset.flags.filter((f) => f.kind === "station_level_unbounded")).toHaveLength(5);
  });
});

describe("reframeDoc (platform.tie.saved_profile_own_frame, platform.tie.centre_kept)", () => {
  const input = levelInput("Line_6");
  const doc = input.doc as PortDoc;

  test("no frame, or a frame at the current points: unchanged", () => {
    expect(reframeDoc({ ...doc, frame: null }, input.platforms, input.length).changed).toBe(false);
    expect(reframeDoc(doc, input.platforms, input.length).changed).toBe(false);
  });

  test("a frame 100 m shorter at its far end: bends mapped, each platform centre kept, slides to 0.5 m", () => {
    const point_c: Record<string, number> = {};
    for (const p of input.platforms) point_c[p.platform_id] = p.point_c * 0.99;
    const saved: PortDoc = { ...doc, frame: { length_m: input.length * 0.99, point_c } };
    const r = reframeDoc(saved, input.platforms, input.length);
    expect(r.changed).toBe(true);
    // a bend at a saved point lands on the current point (to 0.1 m)
    const first = input.platforms.find((p) => !doc.del.includes(p.platform_id) && p.point_c > 1000);
    expect(first).toBeDefined();
    const at = reframeDoc(
      { ...saved, pvi: [[point_c[first?.platform_id as string] as number, 200]] },
      input.platforms,
      input.length,
    );
    expect(at.doc.pvi[0]?.[0]).toBeCloseTo(first?.point_c as number, 1);
    // North Avondale slid -229.9 m in the saved frame: its centre (point plus slide) is kept, to 0.5 m
    const na = input.platforms.find((p) => p.name === "North Avondale");
    const so = r.doc.so[na?.platform_id as string] as number;
    const centreSaved = (point_c[na?.platform_id as string] as number) - 229.9;
    expect(Math.abs((na?.point_c as number) + so - centreSaved / 0.99)).toBeLessThanOrEqual(0.25 + 1e-9);
    // removed stations are not paired
    expect(Object.keys(r.doc.so).some((k) => doc.del.includes(k))).toBe(false);
    // the new doc carries the frame it was mapped to: idempotent
    expect(reframeDoc(r.doc, input.platforms, input.length).changed).toBe(false);
  });
});

describe("deriveStations (717-723)", () => {
  const input = levelInput("Line_6");
  test("removed by platform id, slid by an array by live index or a record by platform id", () => {
    const all = deriveStations(input, []);
    expect(all).toHaveLength(input.platforms.length);
    const live = deriveStations(input, ["Lytle Park", "Greenlee"]);
    expect(live).toHaveLength(input.platforms.length - 2);
    expect(live.map((s) => s.index)).toEqual(live.map((_, i) => i));
    const byKey = deriveStations(input, ["Lytle Park", "Greenlee"], { Forest: -235.4 });
    const byIdx = deriveStations(
      input,
      ["Lytle Park", "Greenlee"],
      live.map((s) => (s.platform_id === "Forest" ? -235.4 : 0)),
    );
    expect(byKey).toEqual(byIdx);
    const forest = byKey.find((s) => s.name === "Forest");
    expect(forest && forest.c - forest.point_c).toBeCloseTo(-235.4, 9);
  });
});

describe("the curve arrays (radii 1952, curveAllowance 1975)", () => {
  /** A path along a circle of radius R m (local metres to degrees), 2 m between points. */
  const circle = (R: number, L: number): PathPoint[] => {
    const lat0 = 39.1;
    const kx = 111320 * Math.cos((lat0 * Math.PI) / 180);
    const out: PathPoint[] = [];
    for (let c = 0; c <= L; c += 2) {
      const a = c / R;
      out.push([c, (R * Math.sin(a)) / kx - 84.5, lat0 + (R - R * Math.cos(a)) / M_PER_DEG_LAT]);
    }
    return out;
  };
  const lit = { radii: { step: 10, h: 4 } };

  test("a drawn circle gives its radius away from the ends, Infinity within h steps of them", () => {
    const R = radii(circle(400, 1000), 1000, lit);
    expect(R.length).toBe(101);
    expect(R[0]).toBe(Number.POSITIVE_INFINITY);
    expect(R[100]).toBe(Number.POSITIVE_INFINITY);
    for (let i = 4; i <= 96; i++) expect(Math.abs((R[i] as number) - 400)).toBeLessThan(0.5);
  });

  test("the allowance is curveK over the radius in a long curve, 0 on a straight", () => {
    const A = curveAllowance(radii(circle(400, 1000), 1000, lit), { curveK: 800, platform: 121.92 });
    expect(A[50]).toBeCloseTo(2, 2);
    const S = curveAllowance(new Float32Array(20).fill(Number.POSITIVE_INFINITY), { curveK: 800, platform: 121.92 });
    expect([...S].every((v) => v === 0)).toBe(true);
  });
});

describe("drawingFlags (network.drawing.corner_checks)", () => {
  const lat0 = 39.1;
  const kx = 111320 * Math.cos((lat0 * Math.PI) / 180);
  const P = (c: number, x: number, y: number): PathPoint => [c, x / kx - 84.5, lat0 + y / M_PER_DEG_LAT];
  const DRAW = { single: 5, nb: 2, kink: 10, kinkSeg: 10, back: 90, sErr: 5, sWarn: 2 };

  test("a single-angle corner is a warning; doubling back an error; a short kink an error", () => {
    const deg = Math.PI / 180;
    const corner = [P(0, 0, 0), P(100, 100, 0), P(200, 100 + 100 * Math.cos(8 * deg), 100 * Math.sin(8 * deg))];
    expect(drawingFlags(corner, [], { DRAW }).map((f) => [f.kind, f.sev, f.c])).toEqual([
      ["single_angle_corner", "warn", 100],
    ]);
    const back = [P(0, 0, 0), P(100, 100, 0), P(200, 0, 10)];
    expect(drawingFlags(back, [], { DRAW }).map((f) => f.kind)).toEqual(["path_doubles_back"]);
    const kink = [
      P(0, 0, 0),
      P(100, 100, 0),
      P(105, 100 + 5 * Math.cos(20 * deg), 5 * Math.sin(20 * deg)),
      P(205, 205, 40),
    ];
    expect(drawingFlags(kink, [], { DRAW }).map((f) => [f.kind, f.sev])[0]).toEqual(["path_kink", "error"]);
  });
});

describe("allIssues (2143-2178)", () => {
  const types = typedFromGolden("Line_2b").types;
  const flag = (page: string, c: number, extra: Partial<PortFlag> = {}): PortFlag => ({
    kind: page.toLowerCase(),
    page,
    sev: "warn",
    c0: c,
    c1: c,
    c,
    rule: "ground.drawn.limits",
    data: {},
    ...extra,
  });
  const parts = (p: Partial<IssueParts>): IssueParts => ({
    over: [],
    crossings: [],
    context: [],
    rivers: [],
    roads: [],
    stations: [],
    deepShallow: [],
    checks: [],
    ground: [],
    types: { ...types, flags: [], bad: [] } as TypeSolve,
    misfits: [],
    ...p,
  });

  test("stable by c, the page's order at a tie; exact repeats once", () => {
    const out = allIssues(
      parts({
        stations: [flag("Access", 50), flag("Platform curve", 50)],
        checks: [flag("Drainage", 50), flag("Vertical curve", 50), flag("Drawing", 10)],
        ground: [flag("Ground", 50), flag("Ground", 50)],
        deepShallow: [{ station: 0, c: 50, d: 15 }],
      }),
      { half: 60 },
    );
    expect(out.map((f) => f.page)).toEqual([
      "Drawing",
      "Access",
      "Canon",
      "Vertical curve",
      "Platform curve",
      "Drainage",
      "Ground",
    ]);
    const canon = out.find((f) => f.page === "Canon");
    expect([canon?.c0, canon?.c1, canon?.rule]).toEqual([-10, 110, "network.canon.fixed_levels"]);
  });

  test("a crossing with no clearance is not listed; one with a line not set is pending", () => {
    const t = { k: "box" as const, below: 1, top: 4.6 };
    const x = {
      c: 100,
      wid: "Line_3",
      with: "Line 3",
      oc: 5,
      zo: 1,
      z: 2,
      clear: 1,
      need: 6,
      meUp: true,
      t,
      to: t,
      level: false,
      ok: false,
      pending: true,
      source: null,
    };
    const out = allIssues(parts({ crossings: [x, { ...x, c: 200, clear: null }, { ...x, c: 300, ok: true }] }));
    expect(out.map((f) => [f.kind, f.c, f.pending, f.rule])).toEqual([
      ["crossing_short", 100, true, "network.profile_set.crossings_apart"],
    ]);
  });
});

describe("Propose fill (ground.propose_fill.within_paint)", () => {
  test("where the structure has its cover there is nothing to fill", () => {
    const m = typedFromGolden("Line_6");
    const T = goldenTypes(fromGolden("Line_6").dump);
    // a deep bored stretch of Line 6 (well under the ground)
    const f = proposeFill(m, 15500, 15600, T);
    expect(f.line).toBeNull();
    expect(f.replaces).toEqual([]);
  });
});

describe("surfacePvis (RER, slice 2: ported, not golden-tested)", () => {
  test("between two surface stations, bend points every surfStep held to the grade limit", () => {
    const { model } = fromGolden("Line_2b");
    const m: LevelModel = {
      ...model,
      settings: { ...model.settings, rer: { envelope: 6.6, boreCrown: 8, invertDepth: 1, minCover: 6, surfStep: 100 } },
    };
    const st = model.stations.map(() => 160);
    const pv = surfacePvis(m, st, ["surface", "surface", "under", "under", "under"]);
    expect(pv.length).toBeGreaterThan(0);
    const a = model.stations[0]?.c as number;
    const b = model.stations[1]?.c as number;
    expect(pv.every((p) => p.c > a && p.c < b)).toBe(true);
    for (let k = 1; k < pv.length; k++) {
      const g = Math.abs(
        ((pv[k]?.z as number) - (pv[k - 1]?.z as number)) / ((pv[k]?.c as number) - (pv[k - 1]?.c as number)),
      );
      expect(g).toBeLessThanOrEqual(model.settings.maxGrade / 1000 + 0.0002);
    }
  });
});

describe("Reset this line (3768-3773 then changed(); network.canon.locks)", () => {
  test("the dump's reset (alignFromDoc(null)) with the canon's locks put back: Line 1's L&N bridge deck", () => {
    const { dump } = fromGolden("Line_1");
    const r = resetLine(levelInput("Line_1"), ALIGN_DEPS);
    const lock = r.canon.locks[0];
    expect(lock).toBeDefined();
    const lo = lock?.lo as number;
    const hi = lock?.hi as number;
    const outside = (ps: readonly { c: number; z: number }[]) => ps.filter((p) => p.c < lo || p.c > hi);
    expect(outside(r.align.pvi)).toEqual(outside(dump.levels.reset.pvi));
    expect(r.align.pvi.filter((p) => p.c >= lo && p.c <= hi)).toEqual(lock?.pvi.map(([c, z]) => ({ c, z })));
    expect(r.align.ovr).toEqual(lock?.ovr);
    expect(r.flags.map((f) => [f.kind, f.rule])).toContainEqual(["lock_kept", "network.canon.locks"]);
  });

  test("a line with no lock: the dump's reset exactly", () => {
    const { dump } = fromGolden("Line_6");
    const r = resetLine(levelInput("Line_6"), ALIGN_DEPS);
    expect(r.align.st).toEqual(dump.levels.reset.st);
    expect(r.align.pvi).toEqual(dump.levels.reset.pvi);
  });
});
