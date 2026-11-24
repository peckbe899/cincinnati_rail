// The whole solve on the line sheet (claude/hub_maps/engine_port_plan.md, section 8): section.solve@1 of the draft in
// a worker of its own after the rail and the station facts, never during a drag; and what the old Rail Profiles page
// drew between the stations, drawn from it: the structure band along the whole line, the rail by structure, tunnel
// and box outlines with the legal band, crossings with their clearances, roads, the Chronology band, every issue
// marker, the overview, and Show: Rail, Rail + box, Box.

import type { APIRequestContext, Page } from "@playwright/test";
import { API, expect, openApp, profileOf, scenario, test } from "./helpers.ts";

interface Mark {
  kind: string;
  id: string;
  [k: string]: unknown;
}

async function sectionOf(request: APIRequestContext, route: string): Promise<string> {
  const r = await request.get(`${API}/legacy/section/${route}`);
  return ((await r.json()) as { id: string }).id;
}

const info = (page: Page) => page.getByTestId("solve-info");
const fullRev = async (page: Page) => Number((await info(page).getAttribute("data-full-rev")) ?? 0);
async function fullSettled(page: Page, rev: number): Promise<void> {
  await expect.poll(() => fullRev(page), { timeout: 30_000 }).toBeGreaterThan(rev);
}

async function openLine(page: Page, request: APIRequestContext, route: string, layer = "main") {
  const sid = await sectionOf(request, route);
  const prof = await profileOf(request, sid, layer);
  await openApp(page, `layer=${encodeURIComponent(layer)}&tl=canon&sel=profile:${prof.id}`);
  await expect(page.getByTestId("station-table").locator("tr[data-platform]").first()).toBeAttached();
  await fullSettled(page, 0);
  return { sid, profileId: String(prof.id) };
}

const canvas = (page: Page) => page.getByTestId("sheet-canvas");
const marks = (page: Page): Promise<Mark[]> =>
  canvas(page).evaluate(async (c) => {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return (c as HTMLCanvasElement & { marks: () => Mark[] }).marks();
  });
const setRange = (page: Page, r: [number, number]) =>
  canvas(page).evaluate(
    (c, rr) => (c as HTMLCanvasElement & { setRange: (x: [number, number]) => void }).setRange(rr),
    r,
  );
const frame = (page: Page) =>
  canvas(page).evaluate(
    (c) => (c as HTMLCanvasElement & { frame: () => { c0: number; c1: number } }).frame() as { c0: number; c1: number },
  );

test("Line 6 whole line: the old page's bands from the whole solve, every issue marked, and Show: Rail, Rail + box, Box", async ({
  page,
  request,
}) => {
  const { sid } = await openLine(page, request, "Line_6");
  await canvas(page).focus();
  await page.keyboard.press("f");
  const solveIn = (await (await request.get(`${API}/x/profiles/sections/${sid}/solve`)).json()) as {
    length: number;
    crossings: { c: number }[];
    context: { roads: unknown[] };
  };
  const m = await marks(page);
  const of = (k: string) => m.filter((x) => x.kind === k);
  // the structure band tiles the whole line, with the unbuildable and misfit hatch over it
  const band = of("band");
  expect(band[0]?.c0).toBe(0);
  expect(band.at(-1)?.c1).toBeCloseTo(solveIn.length, 6);
  for (let k = 1; k < band.length; k++) expect(band[k]?.c0).toBe(band[k - 1]?.c1);
  expect(new Set(band.map((b) => b.id))).toEqual(
    // the old page's types along Line 6 (engine/test/golden/old_page/Line_6: the solve matches it sample for sample)
    new Set(["cutcover", "shield", "deep", "sunk", "atgrade", "trough"]),
  );
  expect(of("band-hatch").length).toBeGreaterThan(0);
  // tunnel and box outlines, the legal band, the made-up bed and the channels over the two sunk boxes
  expect(of("outline").length).toBeGreaterThan(10);
  expect(of("limit").map((x) => x.id)).toEqual(["tube", "box"]);
  expect(of("river").map((x) => x.id)).toEqual(["Ohio River", "Licking River"]);
  expect(of("channel")).toHaveLength(2);
  expect(of("unbuildable").length).toBeGreaterThan(0);
  // the crossings with the lines whose levels are saved (Lines 10, 11 and 13 have none: their levels are the
  // profiles.neighbour job's, which the sheet's input does not wait for), each with its words
  const cl = of("clearance");
  expect(cl.length).toBeGreaterThanOrEqual(8);
  for (const x of cl) expect(String(x.text)).toMatch(/^Line \d+b? .+ · [\d.]+ m apart, needs [\d.]+ m$/);
  expect(cl.some((x) => x.ok === false && x.drawn)).toBe(true);
  // roads and streets, the over-grade halo, the Chronology band, the overview
  expect(of("road")).toHaveLength(solveIn.context.roads.length);
  expect(of("over").length).toBeGreaterThan(0);
  const chr = of("chronology");
  expect(chr.some((x) => String(x.label).match(/^19\d\d · P1$/))).toBe(true);
  expect(of("overview")).toHaveLength(1);
  // every issue but the stretch notes, along the bottom, each with its rule id
  const issues = of("issue");
  expect(issues.length).toBeGreaterThan(40);
  for (const x of issues) expect(String(x.rule)).toMatch(/^[a-z_]+(\.[a-z_0-9]+){1,3}$/);
  await expect(page.getByTestId("sheet-labels").locator('li[data-kind="issue"]').first()).toContainText("(");
  // Show: Rail + box by default; Rail drops the outlines; Box keeps them
  const show = page.getByTestId("sheet-show");
  await expect(show.locator('button[data-show="railbox"]')).toHaveAttribute("aria-pressed", "true");
  await show.locator('button[data-show="rail"]').click();
  expect((await marks(page)).filter((x) => x.kind === "outline")).toHaveLength(0);
  await show.locator('button[data-show="box"]').click();
  expect((await marks(page)).filter((x) => x.kind === "outline").length).toBeGreaterThan(10);
  await show.locator('button[data-show="railbox"]').click();
  // the overview: a press there centres the view on that chainage
  await setRange(page, [0, 3000]);
  const box = await canvas(page).boundingBox();
  const ov = (await marks(page)).find((x) => x.kind === "overview");
  const H = await canvas(page).evaluate((c) => c.clientHeight);
  if (!box || !ov) throw new Error("no canvas");
  const plot = await canvas(page).evaluate(
    (c) => (c as HTMLCanvasElement & { frame: () => { plot: { x: number; w: number } } }).frame().plot,
  );
  await page.mouse.click(box.x + plot.x + plot.w * 0.75, box.y + H - 18);
  const f = await frame(page);
  expect((f.c0 + f.c1) / 2).toBeCloseTo(solveIn.length * 0.75, -2);
  expect(f.c1 - f.c0).toBeCloseTo(3000, 0);
});

test("progressive: the rail and the facts during a drag, the whole solve only once the pointer is up, on the draft", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "full-drag");
  await openLine(page, request, "Line_3", layer);
  const name = "Genesee";
  const folded = (await page.getByTestId("sheet-tables").getAttribute("aria-pressed")) === "false";
  if (folded) await page.getByTestId("sheet-tables").click();
  await page.getByTestId("station-table").locator("td.name", { hasText: name }).first().click();
  await expect(page.getByTestId("station-card-name")).toHaveText(name);
  const before = await marks(page);
  const bar = before.find((x) => x.kind === "bar" && x.selected);
  if (!bar) throw new Error("no selected bar");
  const sel = await setRangeAround(page, Number(bar.c0), Number(bar.c1));
  const b2 = (await marks(page)).find((x) => x.kind === "bar" && x.selected) as Mark;
  const box = await canvas(page).boundingBox();
  if (!box || !sel) throw new Error("no canvas");
  const x = box.x + ((b2.x0 as number) + (b2.x1 as number)) / 2;
  const y = box.y + (b2.y0 as number);
  const rev0 = await fullRev(page);
  const railRev0 = Number((await info(page).getAttribute("data-rev")) ?? 0);
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x, y + 60, { steps: 6 });
  await page.mouse.move(x, y + 140, { steps: 8 });
  // mid-drag: the rail has solved at each step, the whole solve has not run
  await expect.poll(async () => Number((await info(page).getAttribute("data-rev")) ?? 0)).toBeGreaterThan(railRev0);
  await page.waitForTimeout(500);
  expect(await fullRev(page)).toBe(rev0);
  // the outlines and the band during the drag are the last solve's, over the live rail
  expect((await marks(page)).some((x) => x.kind === "outline")).toBe(true);
  await page.mouse.up();
  await fullSettled(page, rev0);
  // the solve is of the draft: the station lowered by some 20 m reads deeper, and the band changes there
  const after = await marks(page);
  const bandAt = (ms: Mark[], c: number) =>
    ms.find((q) => q.kind === "band" && (q.c0 as number) <= c && c < (q.c1 as number))?.id;
  const mid = ((bar.c0 as number) + (bar.c1 as number)) / 2;
  const levelAfter = (after.find((q) => q.kind === "bar" && q.selected) as Mark).z0 as number;
  expect(levelAfter).toBeLessThan((bar.z0 as number) - 5);
  expect(bandAt(after, mid)).toBeDefined();
  const ms = Number(await info(page).getAttribute("data-full-engine-ms"));
  expect(ms).toBeGreaterThan(0);
});

/** Zoom the view onto a station so a drag moves it by metres, not tens of metres. */
async function setRangeAround(page: Page, c0: number, c1: number): Promise<boolean> {
  const mid = (c0 + c1) / 2;
  await setRange(page, [mid - 800, mid + 800]);
  return true;
}
