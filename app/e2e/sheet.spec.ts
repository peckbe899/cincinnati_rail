import type { Browser, Page } from "@playwright/test";
import {
  API,
  expect,
  firstPviLevel,
  getRecord,
  line6Section,
  openApp,
  profileOf,
  scenario,
  settled,
  solveRev,
  test,
} from "./helpers.ts";

/** Open the Line 6 sheet in a layer; returns the section and profile ids. */
async function openSheet(page: Page, layer: string, sectionId: string, profileId: string): Promise<void> {
  await openApp(page, `layer=${encodeURIComponent(layer)}&tl=canon&sel=profile:${profileId}`);
  await expect(page.getByTestId("pvi-table")).toBeVisible();
  await settled(page, 0);
  await expect(page.locator(".sheet-bar strong")).toContainText(sectionId);
}

/** Type a level into the first PVI's cell, one keystroke at a time, as Ben does. */
async function typeLevel(page: Page, value: string): Promise<void> {
  const cell = firstPviLevel(page);
  await cell.click();
  await cell.fill("");
  await cell.pressSequentially(value);
}

async function newPage(browser: Browser): Promise<Page> {
  const ctx = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    viewport: { width: 1600, height: 1000 },
  });
  return ctx.newPage();
}

test("Line 6 sheet shows ground and rail", async ({ page, watch, request }) => {
  const sid = await line6Section(request);
  const prof = await profileOf(request, sid, "main");
  await openSheet(page, "main", sid, String(prof.id));
  // The canvas has drawn: the ground (brown) and the rail (blue) both appear in its pixels.
  const colours = await page.getByTestId("sheet-canvas").evaluate((c: HTMLCanvasElement) => {
    const g = c.getContext("2d") as CanvasRenderingContext2D;
    const d = g.getImageData(0, 0, c.width, c.height).data;
    let ground = 0;
    let rail = 0;
    for (let i = 0; i < d.length; i += 4) {
      const [r, gg, b] = [d[i] as number, d[i + 1] as number, d[i + 2] as number];
      if (Math.abs(r - 0x8a) < 30 && Math.abs(gg - 0x6d) < 30 && Math.abs(b - 0x3b) < 30) ground++;
      if (Math.abs(r - 0x5a) < 30 && Math.abs(gg - 0xa9) < 30 && Math.abs(b - 0xe6) < 30) rail++;
    }
    return { ground, rail };
  });
  expect(colours.ground).toBeGreaterThan(200);
  expect(colours.rail).toBeGreaterThan(200);
  expect(await page.getByTestId("station-table").locator("tr").count()).toBeGreaterThan(5);
  expect(watch.consoleErrors).toEqual([]);
});

test("PVI level edit re-solves locally under 16 ms and saves version 2", async ({ page, request }) => {
  const sid = await line6Section(request);
  const layer = await scenario(request, "edit");
  const prof = await profileOf(request, sid, layer);
  const v1 = await getRecord(request, "profile", String(prof.id), layer);
  await openSheet(page, layer, sid, String(prof.id));
  const before = await solveRev(page);

  // Each keystroke re-solves in the worker (keystrokes that land during a solve coalesce into the next one); the
  // solve of the final value takes well under a frame.
  const z = Number(await firstPviLevel(page).inputValue()) + 1.25;
  await typeLevel(page, z.toFixed(3));
  const ms = await settled(page, before);
  expect(ms).toBeLessThan(16);
  await expect(firstPviLevel(page)).toHaveValue(z.toFixed(3));

  // Save: a PATCH with If-Match, one new version, the server's result back over SSE.
  await page.keyboard.press("Control+s");
  await expect
    .poll(async () => (await getRecord(request, "profile", String(prof.id), layer)).version)
    .toBe(Number(v1.version) + 1);
  // The spec's "version 2" assumes the fixture's profile is at version 1 below the new scenario; the check is the
  // step of one version, written to the scenario.
  const v2 = await getRecord(request, "profile", String(prof.id), layer);
  expect(v2.version).toBe(Number(v1.version) + 1);
  expect(v2.layer).toBe(layer);
  // The whole number: "max diff 0.685 m" (the result from before the save, against the new local rail) must not pass.
  await expect(page.getByTestId("server-info")).toHaveText(/, max diff 0 m$/, { timeout: 15_000 });
});

test("second context updates within 1 s", async ({ page, browser, request }) => {
  const sid = await line6Section(request);
  const layer = await scenario(request, "two");
  const prof = await profileOf(request, sid, layer);
  const other = await newPage(browser);
  await openSheet(page, layer, sid, String(prof.id));
  await openSheet(other, layer, sid, String(prof.id));
  const z = Number(await firstPviLevel(page).inputValue()) + 2;
  await typeLevel(page, z.toFixed(3));
  await page.keyboard.press("Enter");
  const t0 = Date.now();
  // The other tab's table shows the saved level (formatted its own way) within a second of the save.
  await expect.poll(async () => Number(await firstPviLevel(other).inputValue()), { timeout: 1000 }).toBeCloseTo(z, 3);
  expect(Date.now() - t0).toBeLessThan(1000);
  await other.context().close();
});

test("Ctrl+Z gives version 3 equal to version 1", async ({ page, request }) => {
  const sid = await line6Section(request);
  const layer = await scenario(request, "undo");
  const prof = await profileOf(request, sid, layer);
  const v1 = await getRecord(request, "profile", String(prof.id), layer);
  await openSheet(page, layer, sid, String(prof.id));
  await typeLevel(page, (Number(await firstPviLevel(page).inputValue()) - 0.5).toFixed(3));
  await page.keyboard.press("Enter");
  await expect
    .poll(async () => (await getRecord(request, "profile", String(prof.id), layer)).version)
    .toBe(Number(v1.version) + 1);
  // Ctrl+Z outside a text field is the app's undo: a revert changeset.
  await page.locator(".sheet-bar strong").click();
  await page.keyboard.press("Control+z");
  await expect
    .poll(async () => (await getRecord(request, "profile", String(prof.id), layer)).version)
    .toBe(Number(v1.version) + 2);
  const v3 = await getRecord(request, "profile", String(prof.id), layer);
  expect(v3.version).toBe(Number(v1.version) + 2);
  expect(v3.data).toEqual(v1.data);
  // The sheet follows: the first PVI shows version 1's level again.
  const p0 = (v1.data as { pvi: unknown[] }).pvi[0] as number[] | Record<string, number>;
  const z1 = Array.isArray(p0) ? (p0[1] as number) : ((p0.z_m ?? p0.z) as number);
  await expect.poll(async () => Number(await firstPviLevel(page).inputValue())).toBeCloseTo(z1, 3);
});

test("stale tab gets 412 banner", async ({ page, browser, request }) => {
  const sid = await line6Section(request);
  const layer = await scenario(request, "stale");
  const prof = await profileOf(request, sid, layer);
  const other = await newPage(browser);
  await openSheet(page, layer, sid, String(prof.id));
  await openSheet(other, layer, sid, String(prof.id));
  // This tab starts a draft; the other tab saves first.
  await typeLevel(page, (Number(await firstPviLevel(page).inputValue()) + 3).toFixed(3));
  await typeLevel(other, (Number(await firstPviLevel(other).inputValue()) + 4).toFixed(3));
  const v1 = (await getRecord(request, "profile", String(prof.id), layer)).version as number;
  await other.keyboard.press("Enter");
  await expect.poll(async () => (await getRecord(request, "profile", String(prof.id), layer)).version).toBe(v1 + 1);
  // Saving the stale draft gets 412: the banner offers Keep mine and Take theirs.
  await page.keyboard.press("Control+s");
  const banner = page.getByTestId("stale-banner");
  await expect(banner).toBeVisible();
  await expect(banner.getByRole("button", { name: "Keep mine" })).toBeVisible();
  await expect(banner.getByRole("button", { name: "Take theirs" })).toBeVisible();
  const before = (await getRecord(request, "profile", String(prof.id), layer)).version as number;
  await banner.getByRole("button", { name: "Keep mine" }).click();
  await expect(banner).toBeHidden();
  await expect.poll(async () => (await getRecord(request, "profile", String(prof.id), layer)).version).toBe(before + 1);
  await other.context().close();
});

test("browser rail bytes equal Node's on Line 6", async ({ page, request }) => {
  const sid = await line6Section(request);
  await openApp(page, "layer=main&tl=canon");
  const input = await (await request.get(`${API}/x/profiles/sections/${sid}/input?layer=main`)).json();
  // Node's answer: the server's solve job (the engine sidecar), as its rail_m array.
  const view = "main|-|canon";
  const compute = await request.post(`${API}/compute`, {
    data: { type: "profiles.solve_section", scope: sid, view, priority: 0 },
    headers: { "X-CR-Client": "e2e", "Content-Type": "application/json" },
  });
  expect(compute.ok()).toBeTruthy();
  let key = ((await compute.json()) as { key?: string }).key ?? null;
  await expect
    .poll(
      async () => {
        const r = await request.get(
          `${API}/results?type=profiles.solve_section&scope=${sid}&view=${encodeURIComponent(view)}`,
        );
        if (!r.ok()) return null;
        const body = (await r.json()) as { key?: string } | string;
        key = typeof body === "string" ? body : (body.key ?? null);
        if (!key) return null;
        const meta = (await (await request.get(`${API}/results/${key}`)).json()) as { status?: string };
        return meta.status;
      },
      { timeout: 30_000 },
    )
    .toBe("ok");
  const arr = await request.get(`${API}/results/${key}/a/rail_m`);
  expect(arr.headers()["x-dtype"]).toMatch(/f8|float64/);
  const node = Buffer.from(await arr.body()).toString("base64");
  // The browser's answer: the same input through the app's engine worker.
  const browser = await page.evaluate(async (inp) => {
    const host = (
      window as unknown as {
        __cr: { host: { engine: { solve(m: string, i: unknown): Promise<{ result: { rail_m: number[] } }> } } };
      }
    ).__cr.host;
    const out = await host.engine.solve("vertical.rail", inp);
    const bytes = new Uint8Array(Float64Array.from(out.result.rail_m).buffer);
    let s = "";
    for (const b of bytes) s += String.fromCharCode(b);
    return btoa(s);
  }, input);
  expect(browser.length).toBeGreaterThan(1000);
  expect(browser).toBe(node);
});
