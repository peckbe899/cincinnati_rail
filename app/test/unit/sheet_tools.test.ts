// @vitest-environment happy-dom
// The line sheet's tools and line panel (claude/hub_maps/profiles_parity.md, section C: R7 to R12, R16 to R20, R40,
// R46 to R64): the paint, ground, ready, clear and proposal ops on the draft (each one undo step), the issues list's
// rows and groups, the settings' units, and the exports (JSON, GeoJSON, a KMZ that unzips).

import type { SectionProposal, SolvedSection, StationFact } from "@cr/engine/contract";
import { describe, expect, it } from "vitest";
import type { Rec } from "../../src/api/types.ts";
import { Drafts } from "../../src/core/drafts.ts";
import { applyPatch } from "../../src/core/jsonpatch.ts";
import { Units } from "../../src/core/units.ts";
import { makeView } from "../../src/core/view.ts";
import {
  crc32,
  type ExportModel,
  exportGeoJson,
  exportJson,
  profileByKey,
  stationTypeAt,
  zipBytes,
} from "../../src/plugins/line-sheet/exports.ts";
import { buildLinePanel, issueRows, stationPage } from "../../src/plugins/line-sheet/linepanel.ts";
import type { ProfileData } from "../../src/plugins/line-sheet/model.ts";
import { SETTING_ROWS, shown, stored } from "../../src/plugins/line-sheet/settings.ts";
import {
  addGroundAt,
  clampGroundC,
  clearMisfit,
  clearPaints,
  cutRange,
  groundLines,
  moveGroundPoint,
  paintRange,
  proposalOps,
  removeGroundPoint,
  setPvi,
  setReady,
} from "../../src/plugins/line-sheet/tools.ts";

const rec = (data: ProfileData): Rec =>
  ({ kind: "profile", id: "P1", version: 1, layer: "main", by: "import:old_hub", data, geom: null }) as unknown as Rec;
const applied = (data: ProfileData, ops: unknown) => applyPatch({ data, geom: null }, ops as never).data as ProfileData;

describe("paintRange (3181-3193)", () => {
  it("cuts the stretch out, adds the paint rounded to the metre, and joins touching runs of one kind", () => {
    const d: ProfileData = {
      ovr: [
        [100, 300, "cutcover"],
        [400, 600, "shield"],
      ],
    };
    const r = paintRange(d, 250.4, 450.6, "cutcover");
    expect(r?.what).toBe("cutcover");
    expect(applied(d, r?.ops).ovr).toEqual([
      [100, 451, "cutcover"],
      [450.6, 600, "shield"],
    ]);
  });
  it("Auto clears the paint and the shafts inside; a paint under a metre does nothing", () => {
    const d: ProfileData = { ovr: [[100, 300, "cutcover"]], shafts: [150, 500] };
    const r = paintRange(d, 300, 120, "auto");
    expect(applied(d, r?.ops).ovr).toEqual([[100, 120, "cutcover"]]);
    expect(applied(d, r?.ops).shafts).toEqual([500]);
    expect(paintRange(d, 200, 200.5, "shield")).toBeNull();
  });
  it("the tube form brushes write tf, Auto tubes clears it", () => {
    const d: ProfileData = {};
    const r = paintRange(d, 1000, 2000, "tf:bore");
    const d2 = applied(d, r?.ops);
    expect(d2.tf).toEqual([[1000, 2000, "bore"]]);
    expect(applied(d2, paintRange(d2, 1500, 2500, "tf:auto")?.ops).tf).toEqual([[1000, 1500, "bore"]]);
  });
  it("a shaft goes at the middle of the click, replacing one within 2 m; never on the RER", () => {
    const d: ProfileData = { shafts: [1001] };
    const r = paintRange(d, 1000, 1000, "shaft");
    expect(r?.c).toBe(1000);
    expect(applied(d, r?.ops).shafts).toEqual([1000]);
    expect(paintRange(d, 1000, 1000, "shaft", false)).toBeNull();
  });
  it("cutRange keeps what is outside", () => {
    expect(cutRange([[0, 10, "a"]], 3, 5)).toEqual([
      [0, 3, "a"],
      [5, 10, "a"],
    ]);
  });
});

describe("the drawn ground (addGroundAt 3156, clampGpC 3149, removeGroundPoint 3168)", () => {
  const base = () => 200;
  it("a double-click away from a line starts one of three points, its ends on the ground, 25 m either side", () => {
    const d: ProfileData = {};
    const r = addGroundAt(d, 1000.4, 203.27, base, 5000);
    if ("refused" in r) throw new Error(r.refused);
    expect(r.started).toBe(true);
    expect(applied(d, r.ops).gnd).toEqual([
      [
        [975, 200],
        [1000, 203.3],
        [1025, 200],
      ],
    ]);
    expect(r.sel).toEqual({ l: 0, k: 1 });
  });
  it("on a line it adds a point at the line's level; no room says so", () => {
    const d: ProfileData = {
      gnd: [
        [
          [900, 200],
          [1000, 210],
        ],
      ],
    };
    const r = addGroundAt(d, 950, 999, base, 5000);
    if ("refused" in r) throw new Error(r.refused);
    expect(applied(d, r.ops).gnd).toEqual([
      [
        [900, 200],
        [950, 205],
        [1000, 210],
      ],
    ]);
    const tight: ProfileData = {
      gnd: [
        [
          [0, 1],
          [998, 1],
        ],
        [
          [1002, 1],
          [1500, 1],
        ],
      ],
    };
    expect(addGroundAt(tight, 1000, 5, base, 5000)).toEqual({ refused: "No room for a ground line here" });
  });
  it("a point moves within its neighbours; an end keeps its level; Remove takes a point or the line", () => {
    const d: ProfileData = {
      gnd: [
        [
          [900, 200],
          [950, 205],
          [1000, 210],
        ],
      ],
    };
    expect(
      clampGroundC(
        groundLines(d).map((x) => x.pts),
        0,
        1,
        2000,
        5000,
      ),
    ).toBe(999);
    const m = applied(d, moveGroundPoint(d, { l: 0, k: 1 }, 960.4, 207.123, 5000));
    expect(m.gnd).toEqual([
      [
        [900, 200],
        [960, 207.12],
        [1000, 210],
      ],
    ]);
    const e = applied(d, moveGroundPoint(d, { l: 0, k: 0 }, 890, 300, 5000));
    expect((e.gnd as number[][][])[0]?.[0]).toEqual([890, 200]);
    expect(applied(d, removeGroundPoint(d, { l: 0, k: 1 })).gnd).toEqual([
      [
        [900, 200],
        [1000, 210],
      ],
    ]);
    expect(applied(d, removeGroundPoint(d, { l: 0, k: 1 }, true)).gnd).toEqual([]);
  });
});

describe("the other edits", () => {
  it("Profile set, a bend point's chainage and level in its own shape, Clear a misfit or a selection", () => {
    expect(applied({}, setReady({}, true)).ready).toBe(true);
    expect(applied({ pvi: [[10, 1]] }, setPvi({ pvi: [[10, 1]] }, 0, 12, 2)).pvi).toEqual([[12, 2]]);
    expect(applied({ pvi: [{ c_m: 10, z_m: 1 }] }, setPvi({ pvi: [{ c_m: 10, z_m: 1 }] }, 0, 12, 2)).pvi).toEqual([
      { c_m: 12, z_m: 2 },
    ]);
    const d: ProfileData = { ovr: [[100, 300, "cutcover"]], stt: { P7: "shield" } };
    expect(applied(d, clearMisfit(d, { c0: 150, c1: 200 })).ovr).toEqual([
      [100, 149.5, "cutcover"],
      [200.5, 300, "cutcover"],
    ]);
    expect(applied(d, clearMisfit(d, { c0: 0, c1: 0, station: "P7" })).stt).toEqual({});
  });
  it("the paint review's Clear: one paint by its value, or all", () => {
    const d: ProfileData = {
      ovr: [
        [100, 300, "bored"],
        [400, 500, "cutcover"],
      ],
      tf: [[0, 50, "twin"]],
    };
    expect(applied(d, clearPaints(d, [{ list: "ovr", a: 100, b: 300, paint: "shield" }])).ovr).toEqual([
      [400, 500, "cutcover"],
    ]);
    const all = applied(d, clearPaints(d, "all"));
    expect([all.ovr, all.tf]).toEqual([[], []]);
  });
  it("a proposal is one draft edit: bends in the record's shape, levels set, grades zeroed out, one undo step", () => {
    const d: ProfileData = { pvi: [{ c: 1, z: 2 }], st: { A: 150, B: 151 }, sg: { A: 3 } };
    const p = {
      contract: "section_proposal/0",
      engine_build: "x",
      input_hash: "y",
      kind: "solve_cross",
      changed: true,
      rule: "network.solve_crossings",
      edit: { pvi: [[100, 140]], st: { A: 149 }, sg: { A: 0 } },
      report: {},
    } as unknown as SectionProposal;
    const drafts = new Drafts();
    const view = makeView({ layer: "s1" });
    drafts.edit(rec(d), view, proposalOps(d, p), { label: "Solve levels with crossings" });
    const w = drafts.get("profile", "P1", view)?.body.data as ProfileData;
    expect(w.pvi).toEqual([{ c: 100, z: 140 }]);
    expect(w.st).toEqual({ A: 149, B: 151 });
    expect(w.sg).toEqual({});
    expect(drafts.peekStep("s1")?.label).toBe("Solve levels with crossings");
    drafts.stepBack("s1");
    expect(drafts.get("profile", "P1", view)).toBeNull();
  });
  it("Reset empties the profile's fields and sets the default levels", () => {
    const d: ProfileData = {
      st: { A: 1 },
      ovr: [[0, 1, "cutcover"]],
      del: ["B"],
      ready: true,
      access: { A: { type: "mezzanine" } },
    };
    const p = {
      kind: "reset",
      changed: true,
      edit: { st: { A: 140, B: 141 }, pvi: [], clear: ["st", "ovr", "del", "pvi"], ready: false },
      report: {},
    } as unknown as SectionProposal;
    const w = applied(d, proposalOps(d, p));
    expect(w).toMatchObject({ st: { A: 140, B: 141 }, ovr: [], del: [], ready: false, pvi: [] });
    expect(w.access).toEqual({ A: { type: "mezzanine" } });
  });
});

describe("the issues list (renderIssues 2928-2950)", () => {
  const units = new Units();
  const solved = {
    stations: [{ platform_id: "P1" }],
    flags: [
      {
        kind: "unbuildable_cover",
        page: "Unbuildable",
        sev: "error",
        c0: 10,
        c1: 20,
        c: 15,
        rule: "structure.cover.one_diameter_over_tubes",
        data: { why: "cover", worst: 1.2 },
        fix: { mode: "lower", c0: 10, c1: 20 },
        propose: { c0: 10, c1: 20 },
      },
      {
        kind: "paint_misfit",
        page: "Painted",
        sev: "error",
        c0: 30,
        c1: 40,
        c: 35,
        rule: "structure.paint.must_fit",
        data: { t: "cutcover", why: "roof", worst: 0.5, si: 0 },
        fix: { mode: "lower", c0: 30, c1: 40 },
        clear: { c0: 30, c1: 40, si: 0 },
      },
      {
        kind: "crossing_short",
        page: "Clearance",
        sev: "error",
        c0: 5,
        c1: 5,
        c: 5,
        rule: "clearance.crossing.structure_sum",
        data: { with: "Line 3", clear: 2, need: 6 },
      },
      {
        kind: "crossing_short",
        page: "Clearance",
        sev: "warn",
        c0: 6,
        c1: 6,
        c: 6,
        rule: "network.profile_set.crossings_apart",
        data: { with: "Line 9", clear: 2, need: 6 },
        pending: true,
      },
      { kind: "stretch", page: "Tunnel method", sev: "info", c0: 0, c1: 1, c: 0, rule: "x", data: {} },
    ],
  } as unknown as SolvedSection;
  const facts = [
    {
      platform_id: "P1",
      deleted: false,
      c_m: 50,
      flags: [
        {
          kind: "platform_grade_over",
          sev: "error",
          rule: "platform.grade.limit_by_era",
          data: { grade_permille: 9, limit_permille: 7.5, param: "x" },
        },
      ],
    },
  ] as unknown as StationFact[];
  it("lists every finding and station flag in the old page's groups, with its fixes; the stretch notes as notes", () => {
    const rows = issueRows(solved, facts, units, (p) => (p === "P1" ? "Bond Hill" : p));
    expect(rows.map((r) => [r.page, r.grp])).toEqual([
      ["Unbuildable", "own"],
      ["Painted", "own"],
      ["Clearance", "cross"],
      ["Clearance", "pending"],
      ["Tunnel method", "own"],
      ["Platform grade", "own"],
    ]);
    expect(rows[0]?.fix).toEqual({ mode: "lower", c0: 10, c1: 20, fit: null });
    expect(rows[1]?.fix?.fit).toEqual({ t: "cutcover", why: "roof" });
    expect(rows[1]?.clear).toEqual({ c0: 30, c1: 40, station: "P1" });
    expect(rows[4]?.sev).toBe("note");
    expect(rows[5]?.text).toContain("Bond Hill");
    expect(stationPage("access_hall_too_shallow")).toBe("Access");
  });
  it("the panel counts by severity, filters by severity and kind, and groups the crossings", () => {
    const el = buildLinePanel({
      units,
      line: "Line 6",
      length: 29539.6,
      liveStations: 31,
      removed: 2,
      solved,
      ssi: null,
      facts,
      name: (p) => p,
      ready: false,
      canEdit: true,
      busy: null,
      paints: null,
      check: null,
      checkNote: null,
      act: new Proxy({}, { get: () => () => undefined }) as never,
    });
    expect(el.querySelector("[data-testid=issue-counts]")?.textContent).toBe(
      "4 errors · 0 warnings · 1 notes · 1 crossings with lines not set yet",
    );
    expect([...el.querySelectorAll("[data-testid=issue-kind-filters] .iss-chip")].map((b) => b.textContent)).toEqual([
      "Unbuildable 1",
      "Painted 1",
      "Clearance 1",
      "Tunnel method 1",
      "Platform grade 1",
    ]);
    expect(el.querySelectorAll("[data-testid=fix-regrade]").length).toBe(2);
    expect(el.querySelectorAll("[data-testid=fix-fill]").length).toBe(1);
    expect(el.querySelectorAll("[data-testid=fix-clear]").length).toBe(1);
    expect(el.querySelector("[data-testid=line-ready]")).not.toBeNull();
  });
});

describe("the settings rows (R20)", () => {
  it("are the old page's 28 Metro rows; lengths follow the unit, the pool shows in feet", () => {
    expect(SETTING_ROWS.length).toBe(28);
    const u = new Units();
    expect(shown("ft", 138.684, u)).toBeCloseTo(455, 6);
    expect(stored("ft", 455, u)).toBeCloseTo(138.684, 6);
    u.toggle();
    expect(shown("len", 121.92, u)).toBeCloseTo(400, 6);
    expect(stored("len", 400, u)).toBeCloseTo(121.92, 6);
  });
});

describe("the exports (R16 to R19)", () => {
  it("a station's type is the old export's: the drawn type on the rail, its own type off it (Line 6 Forest)", () => {
    // Forest: level 219.7, the drawn rail 215.8 at its centre (a box), the station at its own level at grade
    expect(stationTypeAt(219.7, 215.8, "cutcover", "atgrade")).toBe("atgrade");
    expect(stationTypeAt(162.7, 162.71, "cutcover", "shield")).toBe("cutcover");
    expect(stationTypeAt(null, 162.7, "cutcover", null)).toBe("cutcover");
  });
  const m: ExportModel = {
    id: "Line_X",
    line: "Line X",
    system: "metro",
    length: 100,
    platform: 20,
    path: [
      [0, -84.5, 39.1],
      [100, -84.4, 39.2],
    ],
    railAt: (c) => 150 + c / 100,
    groundAt: () => 160,
    surveyedAt: () => 160,
    typeAt: (c) => (c < 50 ? "cutcover" : "shield"),
    stations: [{ name: "A", c: 50, point_c: 50, rail: 150.5, ground: 160, depth: 9.5, type: "cutcover", sg: 0 }],
    profile: { st: { A: 150.5 } },
    summary: null,
  };
  it("JSON carries the profile, the stations and a sample every 10 m", () => {
    const j = JSON.parse(exportJson(m, "2026-11-23T00:00:00Z"));
    expect(j.st).toEqual({ A: 150.5 });
    expect(j.samples_every_10m.rows.length).toBe(11);
    expect(j.samples_every_10m.rows[5]).toEqual([50, 160, 150.5, "shield", 160]);
  });
  it("JSON keys the stations by name, as the old page's doc did, never by the hub's platform ids", () => {
    // the profile record keys st, sg, so, stt, access, del and gapfill by platform id (01DXF6...): the exported
    // alignment is the old doc format (serialize 3213-3229), keyed by the station key (name, or name#idx)
    const keyOf = (pid: string) => ({ P1: "Bond Hill", P2: "Cincinnati State#2" })[pid] ?? null;
    const p = profileByKey(
      {
        st: { P1: 162.7, P2: 150 },
        sg: { P1: -6 },
        so: { P2: -0.5 },
        stt: { P1: "cutcover" },
        access: { P1: { type: "end_halls", source: "Ben" } },
        del: ["P2"],
        gapfill: ["P1"],
        pvi: [[10, 150]],
      },
      keyOf,
    );
    expect(p).toEqual({
      st: { "Bond Hill": 162.7, "Cincinnati State#2": 150 },
      sg: { "Bond Hill": -6 },
      so: { "Cincinnati State#2": -0.5 },
      stt: { "Bond Hill": "cutcover" },
      access: { "Bond Hill": { type: "end_halls", source: "Ben" } },
      del: ["Cincinnati State#2"],
      gapfill: ["Bond Hill"],
      pvi: [[10, 150]],
    });
    // a key the line does not know is kept as it is
    expect(profileByKey({ st: { X9: 1 } }, keyOf)).toEqual({ st: { X9: 1 } });
  });
  it("GeoJSON has the rail by structure and the stations in 3D", () => {
    const g = JSON.parse(exportGeoJson(m, "now"));
    const kinds = g.features.map(
      (f: { properties: { kind: string; type?: string } }) => f.properties.type ?? f.properties.kind,
    );
    expect(kinds).toEqual(["cutcover", "shield", "station"]);
    expect(g.features[2].geometry.coordinates).toEqual([-84.45, 39.15, 150.5]);
  });
  it("a KMZ is a stored zip whose one file's CRC is right", () => {
    const bytes = new TextEncoder().encode("hello");
    expect(crc32(bytes)).toBe(0x3610a686);
    const z = zipBytes("doc.kml", bytes);
    const dv = new DataView(z.buffer);
    expect(dv.getUint32(0, true)).toBe(0x04034b50);
    expect(dv.getUint32(14, true)).toBe(0x3610a686);
    expect(new TextDecoder().decode(z.slice(30 + 7, 30 + 7 + 5))).toBe("hello");
    expect(dv.getUint32(z.length - 22, true)).toBe(0x06054b50);
  });
});
