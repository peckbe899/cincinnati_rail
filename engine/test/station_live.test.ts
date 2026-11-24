// station.facts@1 works the canon and each station's phase out again from the live stations it is given (a
// draft's), as the old page rebuilt them on every edit (bug A of the parity prove: a draft's station type read the
// saved profile's canon until the save).

import { describe, expect, test } from "vitest";
import type { StationInput } from "../src/contract/index.ts";
import { stationFacts } from "../src/station/facts.ts";
import { liveCanon, livePhase } from "../src/station/live.ts";

const HALF = 60;

describe("liveCanon (buildCanon 876 on the live stations)", () => {
  const live = [
    { name: "St Bernard", c: 1000 },
    { name: "Genesee", c: 3000 },
  ];
  test("a section naming its ends is placed from their platform centres, whatever chainages it came with", () => {
    const [s] = liveCanon([{ m: "canal", c0: 0, c1: 1, a: "St Bernard", b: "Genesee" }], live, HALF);
    expect([s?.c0, s?.c1]).toEqual([940, 3060]);
  });
  test("an end that is not in leaves its platform out (aIn, bIn false)", () => {
    const [s] = liveCanon(
      [{ m: "deep", c0: 0, c1: 1, a: "St Bernard", b: "Genesee", a_in: false, b_in: false }],
      live,
      HALF,
    );
    expect([s?.c0, s?.c1]).toEqual([1060, 2940]);
  });
  test("running against the chainage (b before a) still covers both platforms", () => {
    const [s] = liveCanon([{ m: "canal", c0: 0, c1: 1, a: "Genesee", b: "St Bernard" }], live, HALF);
    expect([s?.c0, s?.c1]).toEqual([940, 3060]);
  });
  test("a removed end drops the section; a slid end moves it", () => {
    expect(liveCanon([{ m: "canal", c0: 0, c1: 1, a: "St Bernard", b: "Genesee" }], live.slice(0, 1), HALF)).toEqual(
      [],
    );
    const slid = [live[0] as { name: string; c: number }, { name: "Genesee", c: 3150 }];
    const [s] = liveCanon([{ m: "canal", c0: 0, c1: 1, a: "St Bernard", b: "Genesee" }], slid, HALF);
    expect(s?.c1).toBe(3210);
  });
  test("a section without names keeps its chainages", () => {
    expect(liveCanon([{ m: "shallow", c0: 5, c1: 9 }], live, HALF)).toEqual([{ m: "shallow", c0: 5, c1: 9 }]);
  });
});

describe("livePhase (phaseAt 1091 at the live centre)", () => {
  const segs = [
    { c0: 0, c1: 1000, year: 1925, phase: "1" },
    { c0: 1000, c1: 2000, year: 1955, phase: "3" },
    { c0: 2000, c1: 3000, year: null, phase: null },
  ];
  test("the earlier-opened segment either side of the platform", () => {
    expect(livePhase(segs, 1000, HALF)).toBe("1");
    expect(livePhase(segs, 1500, HALF)).toBe("3");
  });
  test("a slide across a segment end changes the phase", () => {
    expect(livePhase(segs, 1050, HALF)).toBe("1");
    expect(livePhase(segs, 1200, HALF)).toBe("3");
  });
  test("no segments, or segments with no phase: null (the platform keeps its own)", () => {
    expect(livePhase(undefined, 100, HALF)).toBeNull();
    expect(livePhase(segs, 2500, HALF)).toBeNull();
  });
});

/** Three stations 16 m down on flat ground (a box within no limit: mined by the rules), a canal from A to B. */
function input(profile: StationInput["profile"]): StationInput {
  const L = 3000;
  const sts = [
    { id: "A", c: 500 },
    { id: "B", c: 1500 },
    { id: "C", c: 2500 },
  ];
  const phase = (cc: number, tbm: boolean, tube: "A" | "C" | "bore") => ({
    cc_max_m: cc,
    deep_from_m: 18.29,
    tbm,
    tube,
  });
  return {
    contract: "station_input/0",
    section: {
      contract: "section_input/0",
      section_id: "S",
      length_m: L,
      chainage_basis: "grid:26916",
      scale: 1,
      step_m: 2,
      params: { platform_m: 120, vc_radius_m: 1500, vc_min_len_m: 30.5 },
      stations: sts.map((s, order) => ({ platform_id: s.id, order, c_m: s.c, level_m: 84, grade_permille: 0 })),
      pvi: [],
      ground: { step_m: 2, z_m: new Array(L / 2 + 1).fill(100) },
    },
    route: "Line_3",
    system: "metro",
    path: Array.from({ length: L / 10 + 1 }, (_, i) => [i * 10, -84.5, 39.1 + (i * 10) / 110540]),
    profile: { st: { A: 84, B: 84, C: 84 }, ...profile },
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
        "1": phase(12.19, false, "A"),
        "2": phase(16.5, false, "bore"),
        "3": phase(15, true, "C"),
        later: phase(15, true, "C"),
      },
      subway_streets: [],
    },
    streets: [],
    roads: [],
    ground_add: [],
    ground_cap: [],
    cross_ground: [],
    // as the server places it from the saved profile (A and C live): the canal from A to C
    canon: [{ m: "canal", c0: 440, c1: 2560, a: "Station A", b: "Station C" }],
    chron_segments: [
      { c0: 0, c1: 1000, year: 1925, phase: "1" },
      { c0: 1000, c1: 3000, year: 1960, phase: "3" },
    ],
    phases_along: [
      { c0: 0, c1: 1000, phase: "1" },
      { c0: 1000, c1: 3000, phase: "3" },
    ],
  };
}

const typeOf = (inp: StationInput, id: string) => {
  const f = stationFacts(inp).stations.find((s) => s.platform_id === id);
  return [f?.type, f?.type_why];
};

describe("station.facts@1 on a draft (bug A)", () => {
  test("seed: B inside the canal is a box whatever its depth", () => {
    expect(typeOf(input({}), "B")).toEqual(["cutcover", "canon_box"]);
  });
  test("removing an end of the canal takes the canal away at once; restoring it brings it back", () => {
    expect(typeOf(input({ del: ["C"] }), "B")).toEqual(["deep", "mined_past_limit"]);
    expect(typeOf(input({ del: [] }), "B")).toEqual(["cutcover", "canon_box"]);
  });
  test("a canal end saved as removed comes back with a draft that restores it", () => {
    const inp = input({ del: [] });
    expect(typeOf({ ...inp, profile: { ...inp.profile, del: ["A"] } }, "B")).toEqual(["deep", "mined_past_limit"]);
  });
  test("sliding an end moves the canal: a station it now reaches is a box", () => {
    // a canal from B to C as saved (1440 to 2560); B slid back to 550 (past the limit: it is flagged, not clamped)
    const base = { ...input({}), canon: [{ m: "canal" as const, c0: 1440, c1: 2560, a: "Station B", b: "Station C" }] };
    expect(typeOf(base, "A")).toEqual(["shield", "mined_past_limit"]);
    const slid = { ...base, profile: { ...base.profile, so: { B: -950 } } };
    expect(typeOf(slid, "A")).toEqual(["cutcover", "canon_box"]);
  });
  test("a slide across a Chronology segment end gives the phase of the segment it reaches", () => {
    const f0 = stationFacts(input({ del: ["C"] })).stations.find((s) => s.platform_id === "A");
    expect([f0?.phase, f0?.type]).toEqual(["1", "shield"]);
    const f1 = stationFacts(input({ del: ["C"], so: { A: 150 } })).stations.find((s) => s.platform_id === "A");
    // A at 650: still the 1925 segment either side; at 1000 it reads the earlier of 1925 and 1960
    expect(f1?.phase).toBe("1");
    const f2 = stationFacts(input({ del: ["C"], so: { B: -150 } })).stations.find((s) => s.platform_id === "B");
    // B at 1350: 1290 and 1411 both in the 1960 segment, Phase 3: a TBM bore at 15 m
    expect([f2?.phase, f2?.type]).toEqual(["3", "deep"]);
  });
});
