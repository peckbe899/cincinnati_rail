import { describe, expect, it } from "vitest";
import { Api } from "../../src/api/client.ts";
import type { HubEvent, Rec } from "../../src/api/types.ts";
import { applyPatch, diff, PatchError } from "../../src/core/jsonpatch.ts";
import { RecordCache } from "../../src/core/records.ts";
import { formatChainage, M_PER_FT, Units } from "../../src/core/units.ts";
import { lonLatToUtm, utmToLonLat } from "../../src/core/utm.ts";
import { isOpen, makeView, viewInstant, viewQuery, viewToken } from "../../src/core/view.ts";

describe("view", () => {
  it("gives the same token, query and instant as region.core.view", () => {
    expect(viewToken(makeView())).toBe("main|-|canon");
    expect(viewToken(makeView({ layer: "try", year: 1931, timeline: "real" }))).toBe("try|1931|real");
    expect(viewToken(makeView({ year: 1931, month: 9 }))).toBe("main|1931-09|canon");
    expect(viewQuery(makeView({ layer: "try", year: 1931, month: 9, timeline: "real" }))).toEqual({
      layer: "try",
      year: "1931",
      month: "9",
      tl: "real",
    });
    expect(viewInstant(makeView({ year: 1931 }))).toBe(1931 * 12 + 11);
    expect(viewInstant(makeView({ year: 1931, month: 9 }))).toBe(23180);
    expect(isOpen(null, null, null)).toBe(true);
    expect(isOpen(23180, null, null)).toBe(false);
    expect(isOpen(23180, [23172, 23183], null)).toBe(true);
    expect(isOpen(23180, [23172, 23183], [23180, 23180])).toBe(false);
    expect(() => makeView({ layer: "Bad" })).toThrow();
  });
});

describe("units", () => {
  it("shows metres or feet and parses typed units", () => {
    const store = new Map<string, string>();
    const u = new Units("m", { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => void store.set(k, v) });
    expect(u.format(210.1234, "m")).toBe("210.123");
    expect(u.label("permille")).toBe("‰");
    u.set("ft");
    expect(store.get("cr.units")).toBe("ft");
    expect(u.format(M_PER_FT * 100, "m")).toBe("100");
    expect(u.label("m")).toBe("ft");
    expect(u.parse("100", "m")).toBeCloseTo(30.48, 9);
    expect(u.parse("30.48 m", "m")).toBeCloseTo(30.48, 9);
    expect(u.parse("12.5", "permille")).toBe(12.5);
    expect(u.parse("abc", "m")).toBeNull();
    expect(new Units("m", { getItem: () => "ft", setItem: () => {} }).length).toBe("ft");
    expect(formatChainage(12400, new Units())).toBe("12+400.0");
    expect(formatChainage(5.25, new Units())).toBe("0+005.3");
    expect(formatChainage(12999.97, new Units())).toBe("13+000.0");
    expect(formatChainage(29539.6, new Units())).toBe("29+539.6");
  });
});

describe("utm", () => {
  it("round trips EPSG:26916 to within a millimetre", () => {
    for (const [e, n] of [
      [714000, 4330000],
      [706560, 4329472],
      [740000, 4380000],
    ] as const) {
      const [lon, lat] = utmToLonLat(e, n);
      const [e2, n2] = lonLatToUtm(lon, lat);
      expect(Math.abs(e2 - e)).toBeLessThan(0.001);
      expect(Math.abs(n2 - n)).toBeLessThan(0.001);
    }
    // pyproj gives (-84.52555323925543, 39.09289265504694) for (714000, 4330000).
    const [lon, lat] = utmToLonLat(714000, 4330000);
    expect(lon).toBeCloseTo(-84.525553239, 8);
    expect(lat).toBeCloseTo(39.092892655, 8);
  });
});

describe("JSON Patch", () => {
  it("applies RFC 6902 and keeps nulls", () => {
    const doc = { data: { a: null, pvi: [[0, 1]], st: { "x/y": 1 } }, geom: null };
    const out = applyPatch(doc, [
      { op: "replace", path: "/data/pvi/0/1", value: 2 },
      { op: "add", path: "/data/pvi/-", value: [5, 6] },
      { op: "add", path: "/data/st/x~1z", value: null },
      { op: "remove", path: "/data/st/x~1y" },
      { op: "test", path: "/data/a", value: null },
      { op: "copy", from: "/data/pvi/1", path: "/data/c" },
      { op: "move", from: "/data/c", path: "/data/d" },
    ]);
    expect(out).toEqual({
      data: {
        a: null,
        pvi: [
          [0, 2],
          [5, 6],
        ],
        st: { "x/z": null },
        d: [5, 6],
      },
      geom: null,
    });
    expect(doc.data.pvi).toEqual([[0, 1]]);
    expect(() => applyPatch(doc, [{ op: "replace", path: "/data/nope", value: 1 }])).toThrow(PatchError);
    expect(() => applyPatch(doc, [{ op: "test", path: "/data/a", value: 0 }])).toThrow(PatchError);
  });

  it("diffs into a patch that rebuilds the target", () => {
    const a = {
      data: {
        pvi: [
          [0, 1],
          [2, 3],
        ],
        st: { p: 1, q: null },
        keep: "x",
      },
      geom: null,
    };
    const b = {
      data: {
        pvi: [
          [0, 1],
          [2, 4],
        ],
        st: { p: 1, r: 2 },
        keep: "x",
      },
      geom: "POINT (1 2)",
    };
    const p = diff(a, b);
    expect(applyPatch(a, p)).toEqual(b);
    expect(p).toContainEqual({ op: "replace", path: "/data/pvi/1/1", value: 4 });
    expect(diff(a, a)).toEqual([]);
    const c = { data: { pvi: [[0, 1]] } };
    expect(diff(a.data, c.data).find((o) => o.path === "/pvi")?.op).toBe("replace");
  });
});

describe("record cache", () => {
  const rec = (layer: string, version: number): Rec =>
    ({
      id: "P1",
      kind: "profile",
      layer,
      version,
      data: {},
      kv: 1,
      hash: "h",
      deleted: false,
      origin: "x",
      source: null,
      by: "b",
      changeset: "c",
      created: "",
      updated: "",
      geom: null,
    }) as Rec;

  it("patches by (kind, id, version): skips echoes, invalidates the rest", () => {
    const cache = new RecordCache(new Api({ base: "http://hub.test/api/v1" }));
    const main = makeView();
    const tryView = makeView({ layer: "try" });
    cache.set(rec("main", 3), main);
    cache.set(rec("main", 3), tryView);
    const ev = (layer: string, version: number, client: string | null = null): HubEvent =>
      ({
        type: "record",
        seq: 1,
        data: {
          seq: 1,
          op: "patch",
          kind: "profile",
          id: "P1",
          layer,
          version,
          hash: "h",
          by: "b",
          client,
          changeset: "c",
          fields: [],
          bbox: null,
        },
      }) as HubEvent;
    // The echo of version 3 on main changes nothing.
    expect(cache.apply(ev("main", 3, "tab-me"))).toBe(0);
    // Version 4 on main invalidates both views of the record.
    expect(cache.apply(ev("main", 4))).toBe(2);
    // A copy-up to try invalidates both (the try view must re-resolve; the main view keeps a cheap 304).
    cache.set(rec("main", 4), main);
    cache.set(rec("main", 4), tryView);
    expect(cache.apply(ev("try", 5))).toBe(2);
    // A resync invalidates everything.
    expect(cache.apply({ type: "resync", seq: 9, data: { reason: "epoch", seq: 9 } })).toBe(2);
  });
});
