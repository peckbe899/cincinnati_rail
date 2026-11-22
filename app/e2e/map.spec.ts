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

/** The map's MapLibre handle, once its sources hold features. */
async function mapReady(page: import("@playwright/test").Page, source: string): Promise<void> {
  await page.waitForFunction((src) => {
    const m = (document.querySelector('[data-testid="map"]') as unknown as { __map?: MapHandle } | null)?.__map;
    return !!m && m.loaded() && m.isStyleLoaded() && m.querySourceFeatures(src).length > 0;
  }, source);
}

test("a year keeps the undated network on the map, as the server lists it", async ({ page, watch }) => {
  // Sections and stations carry no dates: the server lists them at any year, so the map must draw them too.
  await openApp(page, "layer=main&tl=canon&year=2030&map=12/39.15/-84.48");
  await mapReady(page, "src-sections");
  await expect
    .poll(() =>
      page.evaluate(() => {
        const m = (document.querySelector('[data-testid="map"]') as unknown as { __map: MapHandle }).__map;
        return m.queryRenderedFeatures().filter((f) => f.layer.id === "sections-line").length;
      }),
    )
    .toBeGreaterThan(0);
  expect(watch.consoleErrors).toEqual([]);
});

test("a click on two stations at one place asks which, and the line's chainage reads under the mouse", async ({
  page,
  request,
}) => {
  // Bond Hill: the Line 3 and Line 6 station records sit 0.2 m apart.
  const hits = (await (await request.get(`${API}/k/station?q=Bond%20Hill&layer=main`)).json()) as {
    items: { id: string; data: { lon: number; lat: number; key: string } }[];
  };
  expect(hits.items.length).toBeGreaterThanOrEqual(2);
  const six = hits.items.find((s) => s.data.key === "Line_6|Bond Hill");
  if (!six) throw new Error("Line 6's Bond Hill station is not in the fixture database");
  const sec = ((await (await request.get(`${API}/legacy/section/Line_6`)).json()) as { id: string }).id;
  const { lon, lat } = six.data;
  await openApp(page, `layer=main&tl=canon&sel=section:${sec}&map=17/${lat}/${lon}`);
  await mapReady(page, "src-stations");
  await page.waitForTimeout(500);
  const at = await page.evaluate(
    ([x, y]) => {
      const el = document.querySelector('[data-testid="map"]') as HTMLElement & {
        __map: { project(p: [number, number]): { x: number; y: number } };
      };
      const p = el.__map.project([x as number, y as number]);
      const r = el.getBoundingClientRect();
      return { x: r.left + p.x, y: r.top + p.y };
    },
    [lon, lat],
  );
  await page.mouse.click(at.x, at.y);
  const chooser = page.locator(".map-chooser button");
  // The selected line's station first.
  await expect(chooser).toHaveText(["Bond Hill, Line 6", "Bond Hill, Line 3"]);
  await chooser.first().click();
  await expect(page).toHaveURL(new RegExp(`sel=station:${six.id}`));
  // The chainage of Line 6 under the mouse, in the status bar.
  await page.mouse.move(at.x + 3, at.y + 3);
  await expect(page.locator('[data-status="map.chainage"]')).toHaveText(/^map: c 1\+0\d\d\.\d on Line 6$/);
});
