import { describe, expect, it } from "vitest";
import type { Meta } from "../../src/api/types.ts";
import { eraFilter, LAYERS, pickRecord, sectionsLayer } from "../../src/plugins/map/layers.ts";
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
