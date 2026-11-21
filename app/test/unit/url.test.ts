import { describe, expect, it } from "vitest";
import { bindUrl, createAppStore, type UrlWindow, urlState } from "../../src/core/store.ts";
import { DEFAULT_STATE, formatUrl, parseUrl, type UrlState } from "../../src/core/url.ts";
import { utmToLonLat } from "../../src/core/utm.ts";

const SPEC =
  "/w/design?layer=main&year=1985&tl=canon&sel=profile:01K9ZQ8X4V3T2S1R0QPNMKJHGF&c=12400.0&lay=+relief,-plots&map=14/39.10/-84.51";

describe("URL codec", () => {
  it("URL round trips and accepts legacy aliases", () => {
    // The spec's example parses to what it says, and formats back to itself.
    const s = parseUrl(SPEC);
    expect(s).toMatchObject({
      workspace: "design",
      layer: "main",
      year: 1985,
      month: null,
      tl: "canon",
      sel: { kind: "profile", id: "01K9ZQ8X4V3T2S1R0QPNMKJHGF" },
      c: 12400,
      lay: { relief: true, plots: false },
      map: { z: 14, lat: 39.1, lon: -84.51 },
    });
    expect(formatUrl(s)).toBe(SPEC);

    // A state at URL precision survives format then parse, extras and legacy selections included.
    const states: UrlState[] = [
      { ...DEFAULT_STATE, lay: {}, extra: {} },
      {
        workspace: "station",
        layer: "proposal:2026-11-21-pvi",
        year: 1931,
        month: 9,
        tl: "real",
        sel: { legacy: { lkind: "alignment_station", key: "Line_8|Cincinnati State#2" } },
        c: 0.5,
        lay: { sanborn: true, relief: false, sections: true },
        map: { z: 15.25, lat: 39.10123, lon: -84.51234 },
        extra: { band: "ground,rail", debug: "1" },
      },
      {
        ...DEFAULT_STATE,
        layer: "try",
        year: -50,
        sel: { kind: "section", id: "01DXF6DT00G2RN476ZR8N14PM3" },
        c: 29539.6,
        lay: {},
        extra: {},
      },
    ];
    for (const st of states) {
      const url = formatUrl(st);
      expect(parseUrl(url)).toEqual(st);
      expect(formatUrl(parseUrl(url))).toBe(url);
    }

    // Legacy aliases: query names, year-month, the old hub's record paths, and the old pages' hashes.
    expect(
      parseUrl(
        "/w/design?scenario=try&timeline=real&y=1931&m=9&chainage=100.04&layers=relief,-plots&select=section:S1",
      ),
    ).toMatchObject({
      layer: "try",
      tl: "real",
      year: 1931,
      month: 9,
      c: 100,
      lay: { relief: true, plots: false },
      sel: { kind: "section", id: "S1" },
    });
    expect(parseUrl("/?year=1931-09").month).toBe(9);
    expect(parseUrl("/?route=Line_6").sel).toEqual({ legacy: { lkind: "route", key: "Line_6" } });
    expect(parseUrl("/?sel=alignments/Line_8").sel).toEqual({ legacy: { lkind: "route", key: "Line_8" } });
    expect(parseUrl("/profiles.html#Line_8").sel).toEqual({ legacy: { lkind: "route", key: "Line_8" } });
    expect(parseUrl("/#13.5/39.1/-84.5").map).toEqual({ z: 13.5, lat: 39.1, lon: -84.5 });
    // The Deck's #E,N,scale: the centre in EPSG:26916 and pixels per metre.
    const deck = parseUrl("/#714000,4330000,0.5").map;
    const [lon, lat] = utmToLonLat(714000, 4330000);
    expect(deck?.lat).toBeCloseTo(lat, 4);
    expect(deck?.lon).toBeCloseTo(lon, 4);
    expect(deck?.z).toBeGreaterThan(14);
    expect(deck?.z).toBeLessThan(16);
    // A + turned into a space by a form encoder still reads as +.
    expect(parseUrl("/?lay=%20relief,-plots").lay).toEqual({ relief: true, plots: false });
    // Bad values fall back to the defaults instead of throwing.
    expect(parseUrl("/?layer=Bad Layer&year=x&tl=other&map=1/2&c=abc")).toMatchObject({
      layer: "main",
      year: null,
      tl: "canon",
      map: null,
      c: null,
    });
    // A plugin's parameter alias maps to its name.
    expect(parseUrl("/?b=ground", { params: [{ name: "band", aliases: ["b"] }] }).extra).toEqual({ band: "ground" });
  });

  it("mirrors the store into the URL: pushState on navigation, replaceState while typing", () => {
    const calls: [string, string][] = [];
    const listeners: (() => void)[] = [];
    const win: UrlWindow = {
      location: { href: "http://hub.test/w/design?layer=main&tl=canon&c=5.0" },
      history: {
        pushState: (_d, _u, url) => {
          calls.push(["push", String(url)]);
          win.location.href = `http://hub.test${url}`;
        },
        replaceState: (_d, _u, url) => {
          calls.push(["replace", String(url)]);
          win.location.href = `http://hub.test${url}`;
        },
      },
      addEventListener: (_t, fn) => listeners.push(fn),
      removeEventListener: () => {},
    };
    const store = createAppStore();
    const unbind = bindUrl(store, win);
    expect(store.getState().c).toBe(5);
    store.getState().update({ c: 12.3 });
    store.getState().update({ sel: { kind: "profile", id: "P1" } });
    store.getState().update({ map: { z: 12, lat: 39.1, lon: -84.5 } });
    expect(calls.map((c) => c[0])).toEqual(["replace", "push", "replace"]);
    expect(calls[1]?.[1]).toContain("sel=profile:P1");
    // Back: the URL changes and popstate brings the store along.
    win.location.href = "http://hub.test/w/design?layer=try&tl=real";
    for (const fn of listeners) fn();
    expect(urlState(store.getState())).toMatchObject({ layer: "try", tl: "real", sel: null, c: null });
    unbind();
  });
});
