// The line sheet's legibility against the old Profiles page (Ben, 23 November: "I cannot discern stations"): the
// sheet maximised fills the window with a plot as wide as the old page's, the stations read as bold bars apart from
// the teal bend points, the whole line keeps the old page's names and interchange tags, a draft's station types
// follow its live stations at once (bug A), the station panel fits a 1,000 px window, and a removed station's name
// keeps off the grade labels.

import type { APIRequestContext, Page } from "@playwright/test";
import { API, expect, openApp, profileOf, scenario, test } from "./helpers.ts";

interface Mark {
  kind: string;
  id: string;
  [k: string]: unknown;
}
interface Box {
  x0: number;
  x1: number;
  y0: number;
  y1: number;
}

async function sectionOf(request: APIRequestContext, route: string): Promise<string> {
  const r = await request.get(`${API}/legacy/section/${route}`);
  return ((await r.json()) as { id: string }).id;
}

const factsRev = async (page: Page) =>
  Number((await page.getByTestId("solve-info").getAttribute("data-facts-rev")) ?? 0);
async function factsSettled(page: Page, rev: number): Promise<void> {
  await expect.poll(() => factsRev(page)).toBeGreaterThan(rev);
  await page.waitForTimeout(60);
}

async function openLine(page: Page, request: APIRequestContext, route: string, layer = "main") {
  const sid = await sectionOf(request, route);
  const prof = await profileOf(request, sid, layer);
  await openApp(page, `layer=${encodeURIComponent(layer)}&tl=canon&sel=profile:${prof.id}`);
  // attached, not visible: a sheet maximised earlier in the session has its tables folded away
  await expect(page.getByTestId("station-table").locator("tr[data-platform]").first()).toBeAttached();
  await factsSettled(page, 0);
  return { sid, profileId: String(prof.id) };
}

const canvas = (page: Page) => page.getByTestId("sheet-canvas");
const marks = (page: Page): Promise<Mark[]> =>
  canvas(page).evaluate(async (c) => {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return (c as HTMLCanvasElement & { marks: () => Mark[] }).marks();
  });
const plot = (page: Page) =>
  canvas(page).evaluate(async (c) => {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return (c as HTMLCanvasElement & { frame: () => { plot: { w: number; h: number } } }).frame().plot;
  });
const apart = (a: Box, b: Box) => a.x1 <= b.x0 || b.x1 <= a.x0 || a.y1 <= b.y0 || b.y1 <= a.y0;

async function maximise(page: Page) {
  await page.getByTestId("sheet-maximise").click();
  await expect(page.getByTestId("sheet-maximise")).toHaveAttribute("aria-pressed", "true");
}

/** Select a station from the table (unfolding the tables for it when they are folded away). */
async function pick(page: Page, name: string) {
  const folded = (await page.getByTestId("sheet-tables").getAttribute("aria-pressed")) === "false";
  if (folded) await page.getByTestId("sheet-tables").click();
  await page.getByTestId("station-table").locator("td.name", { hasText: name }).first().click();
  await expect(page.getByTestId("station-card-name")).toHaveText(name);
  if (folded) await page.getByTestId("sheet-tables").click();
}

test("maximise: the sheet fills the window, the plot 1,200 px wide and the full height; button, Shift+F and the tab's double-click; kept for the session only (item 1)", async ({
  page,
  request,
  browser,
}) => {
  await openLine(page, request, "Line_6");
  const docked = await plot(page);
  expect(await page.locator(".dv-groupview").count()).toBeGreaterThan(1);
  await maximise(page);
  const p = await plot(page);
  // the old page drew 1,230 px at 1,600; the tables fold away so the plot takes the sheet's height
  expect(p.w).toBeGreaterThanOrEqual(1200);
  expect(p.h).toBeGreaterThan(docked.h + 250);
  await expect(page.getByTestId("station-table")).toBeHidden();
  await expect(page.locator('[data-pane="map"]')).toBeHidden();
  // the tables come back on the button, and fold again
  await page.getByTestId("sheet-tables").click();
  await expect(page.getByTestId("station-table")).toBeVisible();
  await page.getByTestId("sheet-tables").click();
  await expect(page.getByTestId("station-table")).toBeHidden();
  // kept across a reload in this session
  await page.reload();
  await expect(page.getByTestId("sheet-maximise")).toHaveAttribute("aria-pressed", "true");
  expect((await plot(page)).w).toBeGreaterThanOrEqual(1200);
  // Shift+F on the canvas puts it back (F alone still shows the whole line), the tab's double-click maximises
  await canvas(page).focus();
  await page.keyboard.press("Shift+F");
  await expect(page.getByTestId("sheet-maximise")).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator('[data-pane="map"]')).toBeVisible();
  await page.locator(".dv-tab", { hasText: "Line 6" }).dblclick();
  await expect(page.getByTestId("sheet-maximise")).toHaveAttribute("aria-pressed", "true");
  // Shift+F typed in a field types an F
  const field = page.locator('input[placeholder="now"]');
  await field.focus();
  await page.keyboard.press("Shift+F");
  await expect(field).toHaveValue("F");
  await expect(page.getByTestId("sheet-maximise")).toHaveAttribute("aria-pressed", "true");
  await field.fill("");
  // a new session starts docked
  const other = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const p2 = await other.newPage();
  await openLine(p2, request, "Line_6");
  await expect(p2.getByTestId("sheet-maximise")).toHaveAttribute("aria-pressed", "false");
  await other.close();
});

test("whole line maximised: at least the old page's names (L3 29, L6 29, L1 27), bold bars over the teal bend points, the interchange tags (items 2 and 3)", async ({
  page,
  request,
}) => {
  const OLD_NAMES: Record<string, number> = { Line_3: 29, Line_6: 29, Line_1: 27 };
  let first = true;
  for (const [route, old] of Object.entries(OLD_NAMES)) {
    await openLine(page, request, route);
    if (first) await maximise(page);
    first = false;
    await expect(page.getByTestId("sheet-maximise")).toHaveAttribute("aria-pressed", "true");
    const m = await marks(page);
    const names = m.filter((x) => x.kind === "name" && x.drawn);
    expect(names.length, `${route}: names drawn`).toBeGreaterThanOrEqual(old);
    const bars = m.filter((x) => x.kind === "bar") as unknown as (Box & { id: string })[];
    // every bar at least 6 px, and no bend point circle drawn on one
    for (const b of bars) expect(b.x1 - b.x0).toBeGreaterThanOrEqual(5.9);
    const shown = m.filter((x) => x.kind === "pvi" && !x.hidden) as unknown as { x: number; y: number }[];
    expect(m.some((x) => x.kind === "pvi" && x.hidden)).toBe(true);
    for (const p of shown)
      for (const b of bars) {
        const bar = { x0: b.x0 - 3, x1: b.x1 + 3, y0: Math.min(b.y0, b.y1) - 9, y1: Math.max(b.y0, b.y1) + 9 };
        expect(
          apart({ x0: p.x - 4, x1: p.x + 4, y0: p.y - 4, y1: p.y + 4 }, bar),
          `${route}: a circle on ${b.id}`,
        ).toBe(true);
      }
    const tags = m.filter((x) => x.kind === "xtag");
    expect(tags.length).toBeGreaterThan(5);
    if (route === "Line_6") {
      const si = (await (
        await request.get(`${API}/x/profiles/sections/${await sectionOf(request, route)}/stations`)
      ).json()) as {
        platforms: { platform_id: string; name: string }[];
      };
      const id = (n: string) => si.platforms.find((p) => p.name === n)?.platform_id;
      expect(tags.find((t) => t.id === id("Bond Hill"))).toMatchObject({ text: "L3", drawn: true });
      expect(tags.find((t) => t.id === id("Times"))?.text).toBe("L4 L5 A trunk");
    }
  }
});

test("bug A: a draft's station types follow its live stations at once: remove, restore and slide give what the saved profile gives (item 4)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "bug-a");
  await openLine(page, request, "Line_3", layer);
  // the type strip of the whole line (F shows it all)
  const strip = async () => {
    await canvas(page).focus();
    await page.keyboard.press("f");
    return Object.fromEntries((await marks(page)).filter((x) => x.kind === "strip").map((x) => [x.id, x.type]));
  };
  const si = (await (
    await request.get(`${API}/x/profiles/sections/${await sectionOf(request, "Line_3")}/stations`)
  ).json()) as { platforms: { platform_id: string; name: string }[] };
  const genesee = si.platforms.find((p) => p.name === "Genesee")?.platform_id as string;
  const stBernard = si.platforms.find((p) => p.name === "St Bernard")?.platform_id as string;
  const seed = await strip();
  // remove St Bernard, the start of the canon's canal bed (St Bernard to Genesee): the canal is gone, and Genesee,
  // 13 m down past Phase 1's 12.19 m, is a shield station at once (the old page rebuilt its canon on every edit)
  await pick(page, "St Bernard");
  await page.getByTestId("sp-remove").click();
  let rev = await factsRev(page);
  await page.getByTestId("sp-remove").click();
  await factsSettled(page, rev);
  const removed = await strip();
  expect([seed[genesee], removed[genesee]]).toEqual(["cutcover", "shield"]);
  // what the server gives once that is saved
  await page.getByTestId("sheet-save").click();
  await expect(page.getByTestId("sheet-save")).toBeDisabled();
  await openLine(page, request, "Line_3", layer);
  expect(await strip()).toEqual(removed);
  // restore: back to the seed's types at once
  rev = await factsRev(page);
  await page.getByTestId("removed-list").locator(`tr[data-platform="${stBernard}"] button`).click();
  await factsSettled(page, rev);
  expect(await strip()).toEqual(seed);
  // slide St Bernard's platform so its drawn point is at the platform's end: the canal's start moves with it
  await pick(page, "St Bernard");
  await page.getByTestId("sp-group-place").locator("summary").click();
  rev = await factsRev(page);
  await page.getByRole("button", { name: "Point at end" }).click();
  await factsSettled(page, rev);
  const slid = await strip();
  await page.getByTestId("sheet-save").click();
  await expect(page.getByTestId("sheet-save")).toBeDisabled();
  await openLine(page, request, "Line_3", layer);
  expect(await strip()).toEqual(slid);
});

test("the station panel fits a 1,000 px window without scrolling, docked and maximised; its groups fold and stay as Ben leaves them (item 5)", async ({
  page,
  request,
}) => {
  const fits = async () => {
    // no scrolling either way: a long digest once widened the column past the panel
    const c = await page
      .getByTestId("station-card")
      .evaluate((e) => ({ sh: e.scrollHeight, ch: e.clientHeight, sw: e.scrollWidth, cw: e.clientWidth }));
    return c.sh <= c.ch + 1 && c.sw <= c.cw + 1;
  };
  for (const [route, stations] of [
    ["Line_6", ["Forest", "Bond Hill", "Times"]],
    ["Line_3", ["Genesee", "Ross", "Bruckman"]],
  ] as const) {
    await openLine(page, request, route);
    for (const max of [false, true]) {
      if (max !== ((await page.getByTestId("sheet-maximise").getAttribute("aria-pressed")) === "true"))
        await page.getByTestId("sheet-maximise").click();
      for (const n of stations) {
        await pick(page, n);
        expect(await fits(), `${route} ${n}${max ? " maximised" : ""}`).toBe(true);
      }
    }
  }
  // the most used first; a group Ben opens stays open on the next station
  const groups = await page
    .locator("details.sp-group")
    .evaluateAll((ds) => ds.map((d) => (d as HTMLElement).dataset.testid));
  expect(groups.slice(0, 2)).toEqual(["sp-group-level", "sp-group-structure"]);
  await expect(page.getByTestId("sp-group-place")).not.toHaveAttribute("open", "");
  await page.getByTestId("sp-group-place").locator("summary").click();
  await expect(page.getByTestId("sp-point")).toBeVisible();
  await pick(page, "Ross");
  await expect(page.getByTestId("sp-point")).toBeVisible();
});

test("a removed station's struck-through name keeps off the grade labels, at the whole line and zoomed in (item 6)", async ({
  page,
  request,
}) => {
  for (const route of ["Line_3", "Line_6"]) {
    await openLine(page, request, route);
    for (const zoom of [0, 3, 6]) {
      await canvas(page).focus();
      await page.keyboard.press("f");
      const m0 = await marks(page);
      const rm = m0.filter((x) => x.kind === "removed");
      expect(rm.length).toBeGreaterThan(0);
      if (zoom) {
        // zoom about the first removed station
        const x = rm[0]?.x as number;
        const box = await canvas(page).boundingBox();
        for (let i = 0; i < zoom; i++) {
          await page.mouse.move((box?.x ?? 0) + x, (box?.y ?? 0) + 300);
          await page.mouse.wheel(0, -300);
        }
      }
      const m = await marks(page);
      const grades = m.filter((x) => x.kind === "grade") as unknown as Box[];
      for (const r of m.filter((x) => x.kind === "removed"))
        for (const g of grades) expect(apart(r.label as Box, g), `${route} ${r.id} zoom ${zoom}`).toBe(true);
    }
  }
});
