import { describe, expect, it } from "vitest";
import type { Meta } from "../../src/api/types.ts";
import { nearestChainage, type PathPoint, pointAt, stationLine } from "../../src/plugins/map/chainage.ts";
import { eraFilter, LAYERS, pickRecord, sectionsLayer, timeFiltered } from "../../src/plugins/map/layers.ts";
import { guessOrder, legacyKinds } from "../../src/plugins/palette/lookup.ts";

describe("map layers", () => {
  it("filter by era on the features' month intervals (region.core.view.is_open)", () => {
    // At the present only unclosed things show; at an instant, opened by then and not closed by then.
    expect(eraFilter(null)).toEqual(["==", ["to-number", ["coalesce", ["get", "close_lo"], 1e9]], 1e9]);
    expect(eraFilter(23180)).toEqual([
      "all",
      ["<=", ["to-number", ["coalesce", ["get", "open_lo"], 1e9]], 23180],
      [">", ["to-number", ["coalesce", ["get", "close_lo"], 1e9]], 23180],
    ]);
  });

  it("pick records from features, and style with the local font only", () => {
    expect(pickRecord("section")({ properties: { id: "S1" }, layer: "x" })).toEqual({ kind: "section", id: "S1" });
    expect(pickRecord("section")({ id: "S2", properties: { kind: "route" }, layer: "x" })).toEqual({
      kind: "route",
      id: "S2",
    });
    expect(pickRecord("section")({ properties: {}, layer: "x" })).toBeNull();
    const specs = sectionsLayer.style({ source: "src", prefix: "sections-", font: ["dejavu-sans"], selected: "S1" });
    expect(specs.map((s) => s.id)).toEqual(["sections-line", "sections-label"]);
    expect(JSON.stringify(specs)).toContain('"text-font":["dejavu-sans"]');
    // Base layers come first so the network draws over them.
    expect(LAYERS.map((l) => l.group)).toEqual(["base", "base", "network", "network"]);
  });
});

describe("Ctrl+K lookup order", () => {
  it("tries the likely legacy kinds for a key's shape first, and falls back when /meta declares none", () => {
    const lk = ["street", "route", "alignment_station", "deck_station"];
    expect(guessOrder("Line_8", lk)[0]).toBe("route");
    expect(guessOrder("Line_8|Cincinnati State#2", lk)[0]).toBe("alignment_station");
    expect(guessOrder("metro:Syacmore:715445:4331182", lk)[0]).toBe("deck_station");
    expect(guessOrder("SB0089", lk)[0]).toBe("street");
    expect(new Set(guessOrder("anything", lk))).toEqual(new Set(lk));
    const meta = {
      kinds: { profile: { kind: "profile", version: 1, schema: {}, legacy: ["route_profile"] } },
    } as unknown as Meta;
    expect([...legacyKinds(meta).keys()]).toEqual(["route_profile"]);
    expect(legacyKinds({ kinds: {} } as unknown as Meta).has("route")).toBe(true);
  });
});

describe("jobs pane in Ben's terms", () => {
  it("names a job's scope by the job, not by its package", async () => {
    const { scopeKind, jobText } = await import("../../src/plugins/jobs/index.ts");
    expect(scopeKind("profiles.solve_section")).toBe("section");
    expect(scopeKind("profiles.golden_diff")).toBeNull();
    expect(jobText("profiles.solve_section")).toBe("solve section (profiles)");
  });
});

describe("the map at a year, and chainage on the map", () => {
  it("filters a layer by date only when its features carry dates (usability-7)", () => {
    // Sections and stations have no dates: every feature has open_lo null, and the server shows them at any year.
    const undated = { features: [{ properties: { id: "S1", open_lo: null, close_lo: null } }] };
    expect(timeFiltered(undated)).toBe(false);
    expect(timeFiltered({ features: [] })).toBe(false);
    expect(
      timeFiltered({ features: [...undated.features, { properties: { id: "F", open_lo: 23000, close_lo: null } }] }),
    ).toBe(true);
  });

  it("places a chainage on a section's path and reads the nearest chainage back (usability-9)", () => {
    const path: PathPoint[] = [
      [0, -84.5, 39.1],
      [1000, -84.5, 39.109],
      [2000, -84.49, 39.109],
    ];
    expect(pointAt(path, 500)).toEqual([-84.5, 39.1045]);
    expect(pointAt(path, 2500)).toBeNull();
    const near = nearestChainage(path, -84.5001, 39.1045);
    expect(near?.c).toBeCloseTo(500, 0);
    expect(near?.off_m).toBeLessThan(10);
    expect(stationLine("Line_3|Bond Hill")).toBe("Line 3");
    expect(stationLine("Bond Hill")).toBeNull();
  });
});
