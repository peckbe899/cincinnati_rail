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
  untraced,
} from "./helpers.ts";

/** Open the Line 6 sheet in a layer; returns the section and profile ids. */
async function openSheet(page: Page, layer: string, sectionId: string, profileId: string): Promise<void> {
  await openApp(page, `layer=${encodeURIComponent(layer)}&tl=canon&sel=profile:${profileId}`);
  await expect(page.getByTestId("pvi-table")).toBeVisible();
  await settled(page, 0);
  // The sheet shows the section by name ("Line 6"), keeping its id only as data.
  const title = page.locator(".sheet-bar strong");
  await expect(title).toHaveAttribute("data-section", sectionId);
  await expect(title).toHaveText("Line 6");
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
  // The station rows name their stations, and a station's level is in view without scrolling sideways; the sheet has
  // the column's height, so its table shows more than a handful of rows.
  await expect(page.getByTestId("station-table").locator("td.name").first()).toHaveText("Towne");
  const pane = await page.locator('.pane-root[data-pane="line-sheet"]').boundingBox();
  const level = await page.getByLabel("Station Bond Hill level").boundingBox();
  expect((level?.x ?? 0) + (level?.width ?? 0)).toBeLessThanOrEqual((pane?.x ?? 0) + (pane?.width ?? 0));
  const shown = await page.locator(".sheet-table").evaluate((t) => {
    const bottom = t.getBoundingClientRect().bottom;
    return [...t.querySelectorAll('[data-testid="pvi-table"] tr')].filter(
      (r) => r.getBoundingClientRect().bottom <= bottom,
    ).length;
  });
  expect(shown).toBeGreaterThan(10);
  expect(watch.consoleErrors).toEqual([]);
});

test("Line 6 sheet draws the station names and levels, and a station click selects it", async ({ page, request }) => {
  const sid = await line6Section(request);
  const prof = await profileOf(request, sid, "main");
  await openSheet(page, "main", sid, String(prof.id));
  // The whole line: the sheet's text layer lists every station with its level, and the ends are named on the canvas.
  const labels = page.getByTestId("sheet-labels");
  await expect(labels.locator('li[data-kind="station"]').first()).toBeAttached();
  const stations = await labels
    .locator('li[data-kind="station"]')
    .evaluateAll((ls) =>
      ls.map((l) => ({ text: l.textContent ?? "", drawn: (l as HTMLElement).dataset.drawn === "1" })),
    );
  expect(stations.length).toBeGreaterThan(5);
  expect(stations[0]?.text).toMatch(/^Towne, \d+\+\d{3}, rail \d+\.\d m$/);
  expect(stations[0]?.drawn).toBe(true);
  expect(stations.at(-1)?.drawn).toBe(true);
  const canvas = page.getByTestId("sheet-canvas");
  const box = await canvas.boundingBox();
  if (!box) throw new Error("no canvas");
  // Select Bond Hill from the table: the sheet names it in the selection colour and shows its card.
  await page.getByTestId("station-table").locator("td.name", { hasText: "Bond Hill" }).click();
  await expect(page.getByTestId("station-card-name")).toHaveText("Bond Hill");
  await expect(page.getByTestId("station-card")).toContainText("platform");
  await expect(page.getByLabel("Bond Hill rail level")).toBeVisible();
  const selectedLabel = labels.locator('li[data-kind="station"][data-selected="1"]');
  await expect(selectedLabel).toHaveAttribute("data-drawn", "1");
  await expect(selectedLabel).toContainText("Bond Hill, ");
  // Centred on it at most 2,500 m across (S16), as Ben looks at a stretch: every station in view is named.
  await canvas.focus();
  await expect.poll(() => labels.locator('li[data-kind="station"][data-x]').count()).toBeGreaterThan(2);
  expect(await labels.locator('li[data-kind="station"][data-x][data-drawn="0"]').count()).toBe(0);
  // Esc clears the selection; a click on the station's bar on the canvas selects it again.
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("station-panel-hint")).toBeVisible();
  const bond = labels.locator('li[data-kind="station"]', { hasText: "Bond Hill, " }).first();
  const x = Number(await bond.getAttribute("data-x"));
  const y = Number(await bond.getAttribute("data-y"));
  await page.mouse.click(box.x + x, box.y + y + 3);
  await expect(page.getByTestId("station-card-name")).toHaveText("Bond Hill");
  // Grades are labelled between the vertices in the old format.
  await expect(labels.locator('li[data-kind="grade"]').first()).toHaveText(/^[+−]\d+\.\d‰$/);
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
  const ms = await untraced(page, async () => {
    await typeLevel(page, z.toFixed(3));
    return settled(page, before);
  });
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
  // The other tab's table shows the saved level (formatted its own way) within a second of the save. It is looked at
  // every 25 ms: at the poll's default steps (0, 0.1, 0.35 and 0.85 s) a level shown at 0.9 s failed the 1 s budget.
  await expect
    .poll(async () => Number(await firstPviLevel(other).inputValue()), { timeout: 1000, intervals: [25] })
    .toBeCloseTo(z, 3);
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
  // Enter saved and left the cell, so the very next Ctrl+Z is the app's undo (a revert changeset), never the
  // browser's undo of one keystroke in the cell.
  await expect(firstPviLevel(page)).not.toBeFocused();
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
  // It names the line and the field both tabs changed, in Ben's terms.
  await expect(banner).toContainText("Line 6 profile was saved by");
  await expect(banner.getByTestId("stale-both")).toContainText("PVI 1 level");
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

test("Line 10 is drawn on its default design, written only with the first edit, which one Ctrl+Z takes back", async ({
  page,
  request,
  watch,
}) => {
  const sec = (await (await request.get(`${API}/legacy/section/Line_10`)).json()) as { id: string };
  const layer = await scenario(request, "default-design");
  const prof = await profileOf(request, sec.id, layer);
  const pid = String(prof.id);
  const v1 = await getRecord(request, "profile", pid, layer);
  // Line 10 has no saved level and no bend point (the hub's /design says it is drawn on the default design)
  expect((v1.data as { pvi?: unknown[] }).pvi ?? []).toEqual([]);
  // every write the page sends
  const writes: string[] = [];
  page.on("request", (r) => {
    if (r.method() !== "GET" && /\/api\/v1\/(k|records|changesets|layers)\b/.test(r.url()))
      writes.push(`${r.method()} ${r.url()}`);
  });
  await openApp(page, `layer=${encodeURIComponent(layer)}&tl=canon&sel=profile:${pid}`);
  const note = page.getByTestId("design-note");
  await expect(note).toHaveText("default design (not saved)", { timeout: 30_000 });
  await expect(note).toBeVisible();
  const canvas = page.getByTestId("sheet-canvas");
  await expect(page.getByTestId("solve-info")).toHaveAttribute("data-design-rev", /[1-9]/);
  await settled(page, 0);
  // the rail is drawn (the old page's defaultAlign: its river bend points), every station at a level, no
  // "level not set" tag, and the old page's 4 "with curve" labels
  type Mark = { kind: string; what?: string; unset?: boolean; drawn?: boolean };
  const marks = async () =>
    canvas.evaluate(async (c) => {
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      return (c as HTMLCanvasElement & { marks(): unknown[] }).marks();
    }) as Promise<Mark[]>;
  await expect
    .poll(async () => (await marks()).filter((m) => m.kind === "curve-grade" && m.drawn !== false).length, {
      timeout: 20_000,
    })
    .toBe(4);
  const m = await marks();
  expect(m.filter((x) => x.kind === "bar").length).toBe(29);
  expect(m.filter((x) => x.kind === "bar" && x.unset).length).toBe(0);
  expect(m.filter((x) => x.kind === "unset-tag").length).toBe(0);
  expect(m.filter((x) => x.kind === "pvi").length).toBe(2);
  const rail = await canvas.evaluate((c) => (c as HTMLCanvasElement & { rail(): { rail_m: number[] } | null }).rail());
  expect(rail?.rail_m.length).toBeGreaterThan(10_000);
  expect(Math.min(...(rail?.rail_m ?? [0]))).toBeGreaterThan(100);
  await expect(page.getByLabel("PVI 1 level")).toHaveValue(/^126\.9/);
  // exporting writes nothing either
  const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("export-geojson").click()]);
  expect(dl.suggestedFilename()).toBe("Line_10_profile.geojson");
  // opening, viewing and exporting wrote nothing: no draft, no request, the record as it was
  await expect(page.getByTestId("sheet-save")).toBeDisabled();
  await expect(page.getByTestId("sheet-discard")).toBeDisabled();
  expect(writes).toEqual([]);
  expect((await getRecord(request, "profile", pid, layer)).version).toBe(v1.version);
  // the first edit takes the design into the draft with it
  const cell = page.getByLabel("PVI 1 level");
  await cell.click();
  await cell.fill("");
  await cell.pressSequentially("125.9");
  await expect(page.getByTestId("sheet-discard")).toBeEnabled();
  await expect(note).toBeHidden();
  const draft = await page.evaluate(
    ([k, id, l]) =>
      (
        window as unknown as {
          __cr: { host: { drafts: { get(k: string, i: string, v: unknown): { body: { data: unknown } } | null } } };
        }
      ).__cr.host.drafts.get(k, id, { layer: l, year: null, month: null, timeline: "canon" })?.body.data as {
        pvi: number[][];
        st: Record<string, number>;
      },
    ["profile", pid, layer] as const,
  );
  expect(draft.pvi.length).toBe(2);
  expect(draft.pvi[0]?.[1]).toBeCloseTo(125.9, 6);
  expect(Object.keys(draft.st).length).toBe(29);
  // one Ctrl+Z: the untouched profile again, drawn on its default design, nothing written
  await page.keyboard.press("Tab");
  await canvas.focus();
  await page.keyboard.press("Control+z");
  await expect(page.getByTestId("sheet-discard")).toBeDisabled();
  await expect(note).toHaveText("default design (not saved)");
  await expect(page.getByLabel("PVI 1 level")).toHaveValue(/^126\.9/);
  expect(writes).toEqual([]);
  const v2 = await getRecord(request, "profile", pid, layer);
  expect(v2.version).toBe(v1.version);
  expect(v2.data).toEqual(v1.data);
  expect(watch.consoleErrors).toEqual([]);
});
