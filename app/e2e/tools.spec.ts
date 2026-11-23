// The old page's editing tools and panels on the line sheet (claude/hub_maps/profiles_parity.md, section C: R1, R7 to
// R12, R16 to R20, R40, R46 to R64), against a running hub on the fixture. Every edit goes into the profile's draft
// (or a param's), is one Ctrl+Z step, and nothing is saved: each test runs on a scenario layer of its own and never
// saves, so Ben's records are never touched.

import type { APIRequestContext, Page } from "@playwright/test";
import { API, expect, openApp, profileOf, scenario, settled, test } from "./helpers.ts";

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
/** Wait for a whole solve later than rev. */
async function fullSettled(page: Page, rev: number): Promise<number> {
  await expect.poll(() => fullRev(page), { timeout: 30_000 }).toBeGreaterThan(rev);
  await page.waitForTimeout(200);
  return fullRev(page);
}

async function openLine(page: Page, request: APIRequestContext, route: string, layer: string) {
  const sid = await sectionOf(request, route);
  const prof = await profileOf(request, sid, layer);
  await openApp(page, `layer=${encodeURIComponent(layer)}&tl=canon&sel=profile:${prof.id}`);
  await expect(page.getByTestId("station-table")).toBeVisible();
  await settled(page, 0);
  await fullSettled(page, 0);
  return { sid, profileId: String(prof.id) };
}

const canvas = (page: Page) => page.getByTestId("sheet-canvas");
const marks = (page: Page): Promise<Mark[]> =>
  canvas(page).evaluate(async (c) => {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return (c as HTMLCanvasElement & { marks: () => Mark[] }).marks();
  });
const frame = (page: Page) =>
  canvas(page).evaluate(async (c) => {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return (
      c as HTMLCanvasElement & {
        frame: () => {
          c0: number;
          c1: number;
          z0: number;
          z1: number;
          plot: { x: number; y: number; w: number; h: number };
        };
      }
    ).frame();
  });
const setRange = (page: Page, r: [number, number]) =>
  canvas(page).evaluate(
    (c, rr) => (c as HTMLCanvasElement & { setRange: (x: [number, number]) => void }).setRange(rr),
    r,
  );

/** The profile's draft data in this tab (null when there is none). */
const draft = (page: Page, profileId: string) =>
  page.evaluate((id) => {
    const host = (
      window as unknown as {
        __cr: { host: { drafts: { all(): { kind: string; id: string; body: { data: Record<string, unknown> } }[] } } };
      }
    ).__cr.host;
    return host.drafts.all().find((d) => d.kind === "profile" && d.id === id)?.body.data ?? null;
  }, profileId);
const paramDrafts = (page: Page) =>
  page.evaluate(() => {
    const host = (
      window as unknown as {
        __cr: { host: { drafts: { all(): { kind: string; body: { data: Record<string, unknown> } }[] } } };
      }
    ).__cr.host;
    return host.drafts
      .all()
      .filter((d) => d.kind === "param")
      .map((d) => d.body.data);
  });

/** Pixel positions of a chainage and level on the page, in the frame the sheet last drew. */
async function xy(page: Page) {
  const box = await canvas(page).boundingBox();
  const f = await frame(page);
  if (!box || !f) throw new Error("no canvas");
  return {
    px: (c: number) => box.x + f.plot.x + ((c - f.c0) / (f.c1 - f.c0)) * f.plot.w,
    py: (z: number) => box.y + f.plot.y + ((f.z1 - z) / (f.z1 - f.z0)) * f.plot.h,
    box,
  };
}

test("tools and keys: M, P and G; a paint drag with its preview, one undo step (R7 to R12, R62 to R64)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "paint");
  const { profileId } = await openLine(page, request, "Line_6", layer);
  await canvas(page).focus();
  for (const [k, t] of [
    ["p", "paint"],
    ["g", "ground"],
    ["m", "move"],
  ] as const) {
    await page.keyboard.press(k);
    await expect(canvas(page)).toHaveAttribute("data-tool", t);
    await expect(page.getByTestId(`tool-${t}`)).toHaveAttribute("aria-pressed", "true");
  }
  // the brushes: the types but the sunk box, the shaft, the tube forms
  await expect(page.getByTestId("sheet-brushes").locator("button")).toHaveCount(11);
  await setRange(page, [19000, 23000]);
  await page.getByTestId("brush-shield").click();
  await expect(canvas(page)).toHaveAttribute("data-tool", "paint");
  const before = ((await draft(page, profileId)) ?? null) as null;
  expect(before).toBeNull();
  const { px, py } = await xy(page);
  const rev = await fullRev(page);
  await page.mouse.move(px(20000), py(230));
  await page.mouse.down();
  await page.mouse.move(px(20600), py(230), { steps: 4 });
  // the preview over the stretch in the brush's colour while the pointer is down
  const preview = (await marks(page)).filter((m) => m.kind === "paint-preview");
  expect(preview.length).toBe(1);
  await page.mouse.move(px(21000), py(230), { steps: 4 });
  await page.mouse.up();
  const d = await draft(page, profileId);
  const ovr = (d?.ovr ?? []) as [number, number, string][];
  expect(ovr.some((o) => o[2] === "shield" && Math.abs(o[0] - 20000) < 30 && Math.abs(o[1] - 21000) < 30)).toBe(true);
  await fullSettled(page, rev);
  // one Ctrl+Z takes the paint back: the draft goes
  await canvas(page).focus();
  await page.keyboard.press("Control+z");
  await expect.poll(() => draft(page, profileId)).toBeNull();
  // a click with the shaft brush puts a shaft there
  await page.getByTestId("brush-shaft").click();
  await page.mouse.click(px(21800), py(230));
  await expect.poll(async () => ((await draft(page, profileId))?.shafts as number[] | undefined)?.length).toBe(1);
});

test("Ground: a double-click starts a line, its card, a drag moves a point, Del removes one (R40, R51)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "ground");
  const { profileId } = await openLine(page, request, "Line_6", layer);
  await setRange(page, [21500, 22500]);
  await canvas(page).focus();
  await page.keyboard.press("g");
  const { px, py } = await xy(page);
  await page.mouse.dblclick(px(22200), py(255));
  await expect(page.getByTestId("ground-card")).toBeVisible();
  const gnd = (await draft(page, profileId))?.gnd as number[][][];
  expect(gnd.length).toBe(1);
  const [a, m, b] = (gnd[0] ?? []).map((p) => p[0] as number);
  // three points, 25 m either side of the pointer, the middle at its level to 0.1 m
  expect([Math.abs((m as number) - 22200) < 3, (m as number) - (a as number), (b as number) - (m as number)]).toEqual([
    true,
    25,
    25,
  ]);
  expect(Math.abs((gnd[0]?.[1]?.[1] as number) - 255)).toBeLessThan(0.3);
  // the card: chainage, level, over the ground below, grades meeting, the line
  await expect(page.getByTestId("ground-card")).toContainText(/\d+\+\d{3} to \d+\+\d{3}, 3 points/);
  const pts = (await marks(page)).filter((m) => m.kind === "ground-point");
  expect(pts.length).toBe(3);
  const mid = pts.find((p) => p.k === 1) as Mark & { x: number; y: number; z: number };
  const box = await canvas(page).boundingBox();
  if (!box) throw new Error("no canvas");
  await page.mouse.move(box.x + mid.x, box.y + mid.y);
  await page.mouse.down();
  await page.mouse.move(box.x + mid.x, py(257), { steps: 5 });
  await page.mouse.up();
  await expect
    .poll(async () =>
      Math.abs(((((await draft(page, profileId))?.gnd ?? []) as number[][][])[0]?.[1]?.[1] as number) - 257),
    )
    .toBeLessThan(0.3);
  // the card's field: a typed level is one edit
  await page.getByTestId("ground-z").fill("256.5");
  await page.getByTestId("ground-z").press("Enter");
  await expect.poll(async () => (((await draft(page, profileId))?.gnd ?? []) as number[][][])[0]?.[1]?.[1]).toBe(256.5);
  // Del removes the point: a line of two points is left
  await canvas(page).focus();
  await page.keyboard.press("Delete");
  await expect.poll(async () => (((await draft(page, profileId))?.gnd ?? []) as number[][][])[0]?.length).toBe(2);
  // in Move, the ground points are not grabbed
  await page.keyboard.press("m");
  expect((await marks(page)).filter((m) => m.kind === "ground-point").length).toBe(2);
});

test("the bend point card: chainage, level, depth, grades meeting, curve length, Remove (R50)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "bend");
  const { profileId } = await openLine(page, request, "Line_6", layer);
  await setRange(page, [21000, 22000]);
  const pv = (await marks(page)).find((m) => m.kind === "pvi" && !m.hidden) as Mark & {
    x: number;
    y: number;
    c: number;
  };
  const box = await canvas(page).boundingBox();
  if (!box || !pv) throw new Error("no bend point in view");
  await page.mouse.click(box.x + pv.x, box.y + pv.y);
  const card = page.getByTestId("bend-card");
  await expect(card).toBeVisible();
  await expect(page.getByTestId("bend-grades")).toHaveText(/^[+−]\d+\.\d‰ \/ [+−]\d+\.\d‰$/);
  await expect(page.getByTestId("bend-curve")).toContainText(" m, ");
  await page.getByTestId("bend-z").fill("262");
  await page.getByTestId("bend-z").press("Enter");
  await expect
    .poll(async () => {
      const p = ((await draft(page, profileId))?.pvi ?? []) as [number, number][];
      return p.some((q) => Math.abs(q[0] - pv.c) < 0.5 && q[1] === 262);
    })
    .toBe(true);
  const n = (((await draft(page, profileId))?.pvi ?? []) as unknown[]).length;
  await page.getByTestId("bend-remove").click();
  await expect.poll(async () => (((await draft(page, profileId))?.pvi ?? []) as unknown[]).length).toBe(n - 1);
});

test("the issues: counts, filters, groups; Raise, Propose fill and Clear as previews in the draft (R42, R54 to R56)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "issues");
  const { profileId } = await openLine(page, request, "Line_6", layer);
  const counts = page.getByTestId("issue-counts");
  await expect(counts).toHaveText(/^\d+ errors · \d+ warnings · \d+ notes/);
  // a kind filter hides its issues and says how many
  const chip = page.getByTestId("issue-kind-filters").locator(".iss-chip").first();
  const kind = (await chip.textContent())?.replace(/\s\d+$/, "") ?? "";
  await chip.click();
  await expect(page.getByTestId("issues")).toContainText("hidden by the filters above");
  await expect(page.getByTestId("issues").locator(`li.iss[data-page="${kind}"]`)).toHaveCount(0);
  await page.getByTestId("issue-kind-filters").locator(".iss-chip").first().click();
  // Raise on Bond Hill's unbuildable stretch: the old page's words, Bond Hill moved, a draft Ctrl+Z takes back
  const raise = page.getByTestId("issues").getByTestId("fix-regrade").filter({ hasText: "Raise" }).first();
  await raise.click();
  await expect(
    page.getByText(/^Raised the rail by up to 3\.7 m from 0\+932 to 1\+204, with Bond Hill 2\.9 m higher/),
  ).toBeVisible();
  const d = await draft(page, profileId);
  expect(d?.pvi).toBeTruthy();
  await canvas(page).focus();
  await page.keyboard.press("Control+z");
  await expect.poll(() => draft(page, profileId)).toBeNull();
  // Propose fill draws a ground line and turns to Ground with its point selected
  const fill = page.getByTestId("issues").getByTestId("fix-fill").first();
  await fill.click();
  await expect(page.getByText(/^Fill drawn from /)).toBeVisible();
  await expect(canvas(page)).toHaveAttribute("data-tool", "ground");
  expect((((await draft(page, profileId))?.gnd ?? []) as unknown[]).length).toBeGreaterThan(0);
  await page.keyboard.press("Control+z");
  await expect.poll(() => draft(page, profileId)).toBeNull();
  // Clear a paint that does not fit
  const clear = page.getByTestId("issues").getByTestId("fix-clear").first();
  await clear.click();
  await expect.poll(async () => (await draft(page, profileId))?.ovr !== undefined).toBe(true);
});

test("the line's buttons: Solve levels with crossings, Fix unbuildable, Profile set, Reset this line (R53, R57 to R59)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "line");
  const { profileId } = await openLine(page, request, "Line_6", layer);
  await page.getByTestId("line-solve-cross").click();
  await expect(page.getByText(/^Cleared \d+ of \d+ crossings within 50‰/)).toBeVisible({ timeout: 20_000 });
  expect(Object.keys(((await draft(page, profileId))?.st ?? {}) as object).length).toBeGreaterThan(0);
  await canvas(page).focus();
  await page.keyboard.press("Control+z");
  await expect.poll(() => draft(page, profileId)).toBeNull();
  await page.getByTestId("line-fix-all").click();
  await expect(page.getByText(/unbuildable stretch(es)? left|All \d+ fixed/)).toBeVisible({ timeout: 30_000 });
  await page.keyboard.press("Control+z");
  await expect.poll(() => draft(page, profileId)).toBeNull();
  // Profile set
  await page.getByTestId("line-ready").check();
  await expect.poll(async () => (await draft(page, profileId))?.ready).toBe(true);
  await page.keyboard.press("Control+z");
  // Reset this line: two clicks in the settings
  await page.getByTestId("settings-open").click();
  await page.getByTestId("settings-reset-line").click();
  await expect(page.getByTestId("settings-reset-line")).toHaveText("Click again to reset");
  await page.getByTestId("settings-reset-line").click();
  await expect(page.getByText(/reset to the level solver's default profile/)).toBeVisible({ timeout: 20_000 });
  const d = await draft(page, profileId);
  expect(d?.del).toEqual([]);
  expect(d?.ovr).toEqual([]);
});

test("the settings as params, Restore defaults; the help; the exports; the line picker; the paint review (R1, R16 to R20, R49, R60)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "settings");
  await openLine(page, request, "Line_6", layer);
  await page.getByTestId("settings-open").click();
  const panel = page.getByTestId("settings-panel");
  await expect(panel.locator("input[data-key]")).toHaveCount(28);
  await expect(page.getByTestId("setting-maxGrade")).toHaveValue("50");
  await page.getByTestId("setting-maxGrade").fill("45");
  await page.getByTestId("setting-maxGrade").press("Enter");
  await expect
    .poll(async () => (await paramDrafts(page)).map((p) => [p.path, p.value]))
    .toEqual([["settings.maxGrade", 45]]);
  // the whole solve previews it: a later solve lands
  const rev = await fullRev(page);
  await fullSettled(page, rev);
  await page.getByTestId("settings-defaults").click();
  await expect.poll(async () => (await paramDrafts(page)).length).toBe(0);
  // the help
  await page.getByTestId("help-open").click();
  await expect(page.getByTestId("editing-help")).toContainText("Propose fill");
  await page.getByTestId("help-open").click();
  await expect(page.getByTestId("editing-help")).toHaveCount(0);
  // the exports
  for (const [id, name] of [
    ["export-json", "Line_6_alignment.json"],
    ["export-geojson", "Line_6_profile.geojson"],
    ["export-kmz", "Line_6_profile.kmz"],
    ["export-png", "Line_6_profile.png"],
  ] as const) {
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId(id).click()]);
    expect(dl.suggestedFilename()).toBe(name);
  }
  // the paint review
  await page.locator('details[data-group="paints"] > summary').click();
  await expect(page.getByTestId("paint-review").locator(".paint-row")).toHaveCount(4, { timeout: 20_000 });
  await expect(page.getByTestId("paint-review")).toContainText("rules: At grade");
  // the line picker: every line with its km; picking one shows it
  const opts = await page.getByTestId("line-picker").locator("option").allTextContents();
  expect(opts.length).toBeGreaterThanOrEqual(16);
  expect(opts).toContain("Line 6 · 29.5 km");
  const line3 = await page.getByTestId("line-picker").locator("option", { hasText: "Line 3 ·" }).getAttribute("value");
  await page.getByTestId("line-picker").selectOption(line3 as string);
  await expect(page.locator(".sheet-bar strong").first()).toHaveText("Line 3");
});

test("Check all lines: every Metro line's unbuildable km, misfits, errors and paints (R59)", async ({
  page,
  request,
}) => {
  test.setTimeout(180_000);
  const layer = await scenario(request, "check");
  await openLine(page, request, "Line_6", layer);
  await page.getByTestId("line-check-all").click();
  const rows = page.getByTestId("check-out").locator("tbody tr");
  await expect(page.getByTestId("check-out")).toContainText("Metro lines checked", { timeout: 150_000 });
  expect(await rows.count()).toBeGreaterThanOrEqual(16);
  await expect(rows.filter({ hasText: "Line 6" })).toHaveCount(1);
});
