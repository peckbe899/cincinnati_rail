import { API, expect, openApp, test } from "./helpers.ts";

type MapHandle = {
  loaded(): boolean;
  isStyleLoaded(): boolean;
  querySourceFeatures(s: string): { properties: Record<string, unknown> }[];
  queryRenderedFeatures(o?: unknown): { layer: { id: string } }[];
  fitBounds(b: [[number, number], [number, number]], o?: unknown): void;
  jumpTo(o: unknown): void;
  once(ev: string, fn: () => void): void;
  areTilesLoaded(): boolean;
};

test("map draws 16 Metro sections offline, no glyph 404", async ({ page, watch, request }) => {
  const fc = (await (await request.get(`${API}/k/section?format=geojson&crs=4326&layer=main`)).json()) as {
    features: { properties: Record<string, unknown>; geometry: { coordinates: unknown } }[];
  };
  const metro = new Set(
    fc.features.filter((f) => (f.properties.system ?? "metro") === "metro").map((f) => String(f.properties.id)),
  );
  expect(metro.size).toBe(16);

  await openApp(page, "layer=main&tl=canon&map=11/39.12/-84.51");
  const map = page.getByTestId("map");
  await expect(map).toBeVisible();
  await page.waitForFunction(() => {
    const m = (document.querySelector('[data-testid="map"]') as unknown as { __map?: MapHandle }).__map;
    return !!m && m.loaded() && m.isStyleLoaded() && m.querySourceFeatures("src-sections").length > 0;
  });

  // Every Metro section is in the map's source, and they draw.
  const drawn = await page.evaluate(() => {
    const m = (document.querySelector('[data-testid="map"]') as unknown as { __map: MapHandle }).__map;
    const ids = new Set(
      m
        .querySourceFeatures("src-sections")
        .filter((f) => (f.properties.system ?? "metro") === "metro")
        .map((f) => String(f.properties.id)),
    );
    return { ids: [...ids], rendered: m.queryRenderedFeatures().filter((f) => f.layer.id === "sections-line").length };
  });
  expect(new Set(drawn.ids)).toEqual(metro);
  expect(drawn.rendered).toBeGreaterThan(0);

  // Zoom in so the section and station labels place: their glyphs come from /map/glyphs, all with 200.
  await page.evaluate(() => {
    const m = (document.querySelector('[data-testid="map"]') as unknown as { __map: MapHandle }).__map;
    m.jumpTo({ center: [-84.512, 39.103], zoom: 14 });
  });
  await page.waitForFunction(() => {
    const m = (document.querySelector('[data-testid="map"]') as unknown as { __map: MapHandle }).__map;
    return (
      m.loaded() &&
      m.areTilesLoaded() &&
      m.queryRenderedFeatures().some((f) => f.layer.id.endsWith("label") || f.layer.id === "stations-icon")
    );
  });
  const glyphs = await page.evaluate(
    () => performance.getEntriesByType("resource").filter((e) => e.name.includes("/map/glyphs/")).length,
  );
  expect(glyphs).toBeGreaterThan(0);
  expect(watch.failed.filter((f) => f.url.includes("/map/"))).toEqual([]);
  expect(watch.aborted).toEqual([]);
  expect(watch.consoleErrors).toEqual([]);
});
