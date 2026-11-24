// station.facts@1 on small sections built by hand: each rule the method ports (profiles_parity.md section A), one
// at a time. The real lines are checked against the old page's outputs in tests/profiles/test_station_facts.py.

import { describe, expect, test } from "vitest";
import type { StationInput } from "../src/contract/index.ts";
import { isRuleId, METHODS, solve } from "../src/index.ts";
import { STATION_FACTS_RULES, stationFacts } from "../src/station/facts.ts";

const L = 2000;
const GROUND = 100;
const LAT0 = 39.1;
const M_LAT = 110540;
const M_LON = 111320 * Math.cos((LAT0 * Math.PI) / 180);

/** A straight path north, or an arc of radius R (metres) from chainage 0. */
function pathOf(R: number | null): [number, number, number][] {
  const out: [number, number, number][] = [];
  for (let c = 0; c <= L; c += 10) {
    const [x, y] = R === null ? [0, c] : [R - R * Math.cos(c / R), R * Math.sin(c / R)];
    out.push([c, -84.5 + x / M_LON, LAT0 + y / M_LAT]);
  }
  return out;
}

const PHASE = (cc: number, tbm: boolean, tube: "A" | "C" | "bore") => ({ cc_max_m: cc, deep_from_m: 18.29, tbm, tube });

function input(
  over: Partial<StationInput> = {},
  stations: { id: string; c: number; z: number | null }[] = [],
): StationInput {
  const sts = stations.length
    ? stations
    : [
        { id: "A", c: 300, z: 92 },
        { id: "B", c: 1200, z: 92 },
      ];
  const st: Record<string, number | null> = {};
  for (const s of sts) st[s.id] = s.z;
  const base: StationInput = {
    contract: "station_input/0",
    section: {
      contract: "section_input/0",
      section_id: "S",
      length_m: L,
      chainage_basis: "grid:26916",
      scale: 1,
      step_m: 2,
      params: { platform_m: 120, vc_radius_m: 1500, vc_min_len_m: 30.5 },
      stations: sts.map((s, order) => ({ platform_id: s.id, order, c_m: s.c, level_m: s.z, grade_permille: 0 })),
      pvi: [],
      ground: { step_m: 2, z_m: new Array(L / 2 + 1).fill(GROUND) },
    },
    route: "Line_9",
    system: "metro",
    path: pathOf(null),
    profile: { st },
    platforms: sts.map((s, order) => ({
      platform_id: s.id,
      key: s.id,
      name: `Station ${s.id}`,
      order,
      point_c_m: s.c,
      side: "side",
      side_source: "import",
      year: 1910,
      year_phase: "1",
      phase: "1",
      phase_source: "chronology",
      complex: [],
    })),
    rivers: [],
    params: {
      platform_m: 120,
      def_depth_m: 7.62,
      elev_above_m: 3,
      cover_below_m: 3,
      deck_depth_m: 1.5,
      pool_m: 138.684,
      sg_max_permille: 7.5,
      sg_max_param: "literal.ERA.sgMax.lines_1_7",
      slide_max_m: 150,
      car_len_m: 15.56,
      end_door_m: 5.4,
      plat_r_err_m: 600,
      plat_r_warn_m: 3000,
      s_err_deg: 5,
      s_warn_deg: 2,
      tol_m: 0.05,
      box_cover_m: 0.6,
      hall_end_len_m: 25,
      mezzanine_fraction: 0.6,
    },
    structure: {
      box_below_m: 1,
      box_top_m: 4.6,
      box_roof_underside_m: 4,
      island_roof_underside_m: 4.6,
      hall_clear_m: 2.75,
      hall_roof_m: 0.6,
      hall_cover_m: 0.6,
      mezzanine_clear_m: 3.5,
      tubes: {
        A: { inside: 5.1, outside: 5.5, rail_over_invert: 0.7 },
        C: { inside: 5.4, outside: 5.9, rail_over_invert: 0.7 },
        bore: { inside: 8.6, outside: 9, rail_over_invert: 2.3 },
      },
      phases: {
        "1": PHASE(12.19, false, "A"),
        "2": PHASE(16.5, false, "bore"),
        "3": PHASE(15, true, "C"),
        later: PHASE(15, true, "C"),
      },
      subway_streets: ["Central Parkway"],
    },
    streets: [],
    roads: [],
    ground_add: [],
    ground_cap: [],
    cross_ground: [],
    canon: [],
    phases_along: [{ c0: 0, c1: L, phase: "1" }],
  };
  return { ...base, ...over };
}

const at = (inp: StationInput, id = "A") => {
  const f = stationFacts(inp).stations.find((s) => s.platform_id === id);
  if (!f) throw new Error(`no ${id}`);
  return f;
};
const withLevel = (z: number) =>
  input({}, [
    { id: "A", c: 300, z },
    { id: "B", c: 1200, z: 92 },
  ]);

describe("station.facts@1", () => {
  test("is a method of the table, its rules are registry ids, and solve() stamps and checks it", async () => {
    expect(METHODS.map((m) => `${m.name}@${m.version}`)).toContain("station.facts@1");
    for (const r of STATION_FACTS_RULES) expect(isRuleId(r)).toBe(true);
    const out = (await solve("station.facts", input())) as { contract: string; input_hash: string };
    expect(out.contract).toBe("station_facts/0");
    expect(out.input_hash).toMatch(/^[0-9a-f]{64}$/);
  });

  test("the type by level: elevated, at grade, trough, a box within the limit, mined past it", () => {
    expect(at(withLevel(105)).type).toBe("elevated"); // 105 - 1.5 - 100 = 3.5 over the ground
    expect(at(withLevel(99)).type).toBe("atgrade"); // 1 m down
    expect(at(withLevel(95)).type).toBe("trough"); // 5 m: under the box's roof and cover (5.2)
    const box = at(withLevel(92));
    expect([box.type, box.role, box.type_why, box.type_source]).toEqual([
      "cutcover",
      "box",
      "box_within_limit",
      "rule",
    ]);
    const mined = at(withLevel(85));
    expect([mined.type, mined.role, mined.type_why]).toEqual(["shield", "mined", "mined_past_limit"]);
  });

  test("a subway street takes the roof without cover; the canal bed is a box at any depth", () => {
    const streets: StationInput["streets"] = [[200, 400, 30, "Central Parkway", "major"]];
    expect(at({ ...withLevel(95.1), streets }).type).toBe("cutcover");
    const canal = at({ ...withLevel(85), canon: [{ m: "canal", c0: 200, c1: 400 }] });
    expect([canal.type, canal.type_why]).toEqual(["cutcover", "canon_box"]);
    expect(canal.flags.map((f) => f.kind)).toContain("station_box_past_cc_max");
  });

  test("Ben's selection wins; Bore before Phase 3 is flagged", () => {
    const inp = withLevel(92);
    inp.profile.stt = { A: "deep" };
    const f = at(inp);
    expect([f.type, f.type_source, f.selected]).toEqual(["deep", "ben", "deep"]);
    expect(f.flags.find((x) => x.kind === "station_tbm_before_phase_3")?.rule).toBe("geometry.method.tbm_from_phase_3");
  });

  test("a mined station takes its drive's painted method", () => {
    const inp = withLevel(85);
    inp.section.pvi = [{ c_m: 800, z_m: 80 }];
    inp.profile.ovr = [[400, 1100, "deep"]];
    const f = at(inp);
    expect([f.type, f.type_why]).toEqual(["deep", "drive_paint"]);
  });

  test("platform grade, slide (never clamped) and overlap flags", () => {
    const inp = input({}, [
      { id: "A", c: 300, z: 92 },
      { id: "B", c: 380, z: 92 },
    ]);
    inp.profile.sg = { A: 9 };
    inp.profile.so = { B: 0 };
    const out = stationFacts(inp);
    const a = out.stations[0];
    expect(a?.flags.find((x) => x.kind === "platform_grade_over")?.rule).toBe("platform.grade.limit_by_era");
    expect(a?.rail_ends_m).toEqual([92 - 0.009 * 60, 92 + 0.009 * 60]);
    expect(out.stations[1]?.flags.find((x) => x.kind === "platform_overlap")?.sev).toBe("error");
    const slid = input();
    slid.profile.so = { A: -160 };
    const f = at(slid);
    expect([f.slide_m, f.c_m, f.point_c_m]).toEqual([-160, 140, 300]);
    expect(f.flags.find((x) => x.kind === "platform_slide_over")?.rule).toBe("platform.slide.limit_never_clamped");
  });

  test("a removed station is listed with its values and no rail; the summary counts it", () => {
    const inp = input();
    inp.profile.del = ["B"];
    inp.section.stations = inp.section.stations.filter((s) => s.platform_id !== "B");
    const out = stationFacts(inp);
    const b = out.stations.find((s) => s.platform_id === "B");
    expect([b?.deleted, b?.rail_m, b?.level_m, b?.index]).toEqual([true, null, 92, null]);
    expect(out.summary).toMatchObject({ live: 1, removed: 1 });
  });

  test("a station with no level is flagged and offered the default depth", () => {
    const f = at(
      input({}, [
        { id: "A", c: 300, z: null },
        { id: "B", c: 1200, z: 92 },
      ]),
    );
    expect(f.level_set).toBe(false);
    expect(f.default_level_m).toBeCloseTo(GROUND - 7.62, 6);
    expect(f.flags.map((x) => x.kind)).toContain("platform_level_unset");
  });

  test("a station with no level on a line with no design is read at the default depth, as it is drawn", () => {
    // Lines 10, 11 and 13 have no saved profile: the old page put each station at ground - 7.62 (defaultAlign).
    // The sheet draws the dashed bar there, so the type, depth, access and outline must be read there too, not at a
    // rail of 0 m (226 m down, a deep bore with lifts).
    const f = at(
      input({}, [
        { id: "A", c: 300, z: null },
        { id: "B", c: 1200, z: null },
      ]),
    );
    expect(f.rail_m).toBeCloseTo(GROUND - 7.62, 6);
    expect(f.depth_m).toBeCloseTo(7.62, 6);
    expect([f.type, f.role]).toEqual(["cutcover", "box"]);
    expect(f.access).toMatchObject({ type: "platform_level", rule: "platform_level" });
    expect(f.structure?.top_m).toBeCloseTo(GROUND - 7.62 + 4.6, 6);
  });

  test("the platform curve: straight, a tight curve as an error, gap fillers make it a warning", () => {
    expect(at(input()).curve).toMatchObject({ R_m: null, level: null, out_m: 0 });
    const curved = input({ path: pathOf(400) });
    const f = at(curved);
    expect(f.curve?.R_m).toBeCloseTo(400, -1);
    expect(f.curve?.out_m).toBeCloseTo((15.56 * 15.56) / (8 * 400), 3);
    expect(f.flags.find((x) => x.kind === "platform_curve")?.sev).toBe("error");
    curved.profile.gapfill = ["A"];
    expect(at(curved).flags.find((x) => x.kind === "platform_curve")?.sev).toBe("warn");
  });

  test("access by phase, depth, side and type, with the drawn ranges", () => {
    const deepBox = at(withLevel(90)); // 10 m down, side box: D_HALL 8.55
    expect(deepBox.access).toMatchObject({ type: "end_halls", rule: "end_halls", source: "rule" });
    expect(deepBox.access?.d_hall_m).toBeCloseTo(8.55, 9);
    expect(deepBox.access?.halls).toEqual([
      [240, 265],
      [335, 360],
    ]);
    const shallow = withLevel(93);
    (shallow.platforms[0] as StationInput["platforms"][number]).side = "island";
    const xu = at(shallow);
    expect(xu.access).toMatchObject({ type: "platform_level_xu", passage: [240, 243] });
    expect(xu.access?.d_hall_m).toBeCloseTo(9.15, 9);
    expect(xu.structure).toEqual({ kind: "box", top_m: 93 + 5.2, bottom_m: 92 });
    expect(xu.flags.find((x) => x.kind === "access_crossunder")?.sev).toBe("info");
    const deep = at(withLevel(75));
    expect(deep.access).toMatchObject({ type: "deep", shaft: [297, 303] });
    expect(deep.structure?.kind).toBe("A");
    const ben = withLevel(93);
    ben.profile.access = { A: { type: "end_halls", source: "Ben" } };
    const f = at(ben);
    expect(f.access).toMatchObject({ type: "end_halls", rule: "platform_level", source: "ben" });
    expect(f.flags.find((x) => x.kind === "access_hall_too_shallow")?.sev).toBe("error");
    const noYear = withLevel(90);
    (noYear.platforms[0] as StationInput["platforms"][number]).year = null;
    const ny = at(noYear);
    expect(ny.access?.dashed).toBe(true);
    expect(ny.flags.find((x) => x.kind === "access_no_year")?.rule).toBe("access.year.fallback_to_line_phase");
  });

  test("the finished ground: the Deck's re-grades and caps, then the drawn ground", () => {
    const inp = withLevel(92);
    inp.ground_add = [{ i0: 150, v: [2, 2] }];
    expect(at(inp).ground_m).toBeCloseTo(GROUND + 2, 4);
    expect(at(inp).ground_dem_m).toBeCloseTo(GROUND, 4);
    const cap = withLevel(92);
    cap.ground_cap = [{ i0: 150, v: [97] }];
    expect(at(cap).ground_m).toBeCloseTo(97, 4);
    const drawn = withLevel(92);
    drawn.profile.gnd = [
      [
        [250, 0],
        [300, 104],
        [350, 0],
      ],
    ];
    expect(at(drawn).ground_m).toBeCloseTo(104, 4);
  });

  test("the street a station is under, or the roads across it", () => {
    const under = at({ ...withLevel(92), streets: [[200, 400, 30, "Vine Street", "minor"]] });
    expect(under.street).toEqual({ text: "under", street: "Vine Street", subway: false, roads: [] });
    const across = at({ ...withLevel(92), roads: [[300, 290, 310, 20, "Elm Street", "minor"]] });
    expect(across.street).toMatchObject({ text: "crosses", roads: ["Elm Street"] });
    expect(at(withLevel(92)).street.text).toBe("no_streets_known");
  });

  test("an elevated selection needs the mezzanine's height", () => {
    const inp = withLevel(92);
    inp.profile.stt = { A: "elevated" };
    const f = at(inp);
    expect(f.access?.rule).toBe("elevated_mezzanine");
    expect(f.elevated_rail_min_m).toBeCloseTo(GROUND + 5, 6);
    expect(f.flags.find((x) => x.kind === "access_mezzanine_clearance")?.rule).toBe("station.type.elevated_mezzanine");
  });
});
