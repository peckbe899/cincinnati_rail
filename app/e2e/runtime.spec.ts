// The I2.1 gate on the line sheet (claude/hub_maps/i21_plan.md 1.7 and 6, lane sheet): open Line 6, release a bend
// point drag, and the run time on the band changes within 10 s without a save; no draft run is asked between pointer
// down and pointer up; Ctrl+Z goes back to the saved numbers with no new run; after a save the saved run arrives
// over SSE and equals the draft; an idle sheet then makes no requests.
//
// It reads the band through the canvas's marks() hook: one {kind: "run", dir, trip_s, running_s, draft} per
// direction drawn.

import type { APIRequestContext, Page, Request } from "@playwright/test";
import { API, expect, openApp, profileOf, scenario, test } from "./helpers.ts";

interface RunMark {
  kind: string;
  dir: number;
  trip_s: number;
  running_s: number;
  draft: boolean;
}
interface Mark {
  kind: string;
  c: number;
  x: number;
  y: number;
}

async function sectionOf(request: APIRequestContext, route: string): Promise<string> {
  const r = await request.get(`${API}/legacy/section/${route}`);
  return ((await r.json()) as { id: string }).id;
}

const marks = (page: Page) =>
  page.getByTestId("sheet-canvas").evaluate(async (c) => {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return (c as HTMLCanvasElement & { marks: () => unknown[] }).marks();
  }) as Promise<(Mark & RunMark)[]>;

const runOf = async (page: Page, dir = 1): Promise<RunMark | null> =>
  ((await marks(page)).find((m) => m.kind === "run" && m.dir === dir) as RunMark | undefined) ?? null;

test("Line 6: a bend point drag's run time on the band within 10 s, never during the drag; undo and save", async ({
  page,
  request,
}) => {
  test.setTimeout(240_000);
  const layer = await scenario(request, "runtime");
  const sid = await sectionOf(request, "Line_6");
  const prof = await profileOf(request, sid, layer);
  await openApp(page, `layer=${encodeURIComponent(layer)}&tl=canon&sel=profile:${prof.id}`);
  await expect(page.getByTestId("station-table").locator("tr[data-platform]").first()).toBeAttached();
  // the saved run: the hub runs the route's chain once (the fit, the assemble, the run) on a fresh database
  await expect.poll(async () => (await runOf(page))?.trip_s ?? 0, { timeout: 150_000 }).toBeGreaterThan(0);
  const saved = (await runOf(page)) as RunMark;
  expect(saved.draft).toBe(false);
  expect(await runOf(page, -1)).not.toBeNull();
  await expect(page.getByTestId("run-table")).toContainText("Towne to Beechgrove");
  // the whole solve of the record has landed before the drag (it gives the draft its structure types)
  await expect
    .poll(async () => Number((await page.getByTestId("solve-info").getAttribute("data-full-rev")) ?? 0), {
      timeout: 60_000,
    })
    .toBeGreaterThan(0);

  const canvas = page.getByTestId("sheet-canvas");
  await canvas.focus();
  await page.keyboard.press("f");
  await page.waitForTimeout(600);
  // a bend point drawn clear of every station bar (a press on a bar would drag the station), dragged down 60 px
  const drawn = (await marks(page)) as (Mark & { hidden?: boolean; x0?: number; x1?: number })[];
  const bars = drawn.filter((m) => m.kind === "bar");
  const gap = (m: Mark) =>
    Math.min(...bars.map((b) => Math.min(Math.abs(m.x - (b.x0 ?? 0)), Math.abs(m.x - (b.x1 ?? 0)))));
  const mk = drawn.filter((m) => m.kind === "pvi" && !m.hidden).sort((p, q) => gap(q) - gap(p))[0];
  expect(mk, "a bend point is drawn clear of the stations").toBeTruthy();
  const box = await canvas.boundingBox();
  const x = (box?.x ?? 0) + (mk?.x ?? 0);
  const y = (box?.y ?? 0) + (mk?.y ?? 0);

  const drafts: { at: number; url: string }[] = [];
  const computes: { at: number; body: string }[] = [];
  const onReq = (r: Request) => {
    if (r.url().includes("/x/railsim/") && r.url().includes("/draft")) drafts.push({ at: Date.now(), url: r.url() });
    if (r.url().endsWith(`${API}/compute`) && r.method() === "POST")
      computes.push({ at: Date.now(), body: r.postData() ?? "" });
  };
  page.on("request", onReq);
  // what each draft answered, for the report when the band does not change
  const answers: string[] = [];
  page.on("response", async (r) => {
    if (r.url().includes("/x/railsim/") && r.url().includes("/draft"))
      answers.push(`${r.status()} ${r.status() >= 400 ? (await r.text().catch(() => "")).slice(0, 300) : ""}`);
  });
  await page.mouse.move(x, y);
  const down = Date.now();
  await page.mouse.down();
  for (let i = 1; i <= 30; i++) {
    await page.mouse.move(x, y + i * 2);
    await page.waitForTimeout(30);
  }
  // held still a while: still no draft while the pointer is down
  await page.waitForTimeout(1500);
  const up = Date.now();
  await page.mouse.up();
  expect(
    drafts.filter((d) => d.at >= down && d.at <= up),
    "no draft run between pointer down and up",
  ).toEqual([]);

  // released: the draft's run time on the band within 10 s
  try {
    await expect
      .poll(
        async () => {
          const r = await runOf(page);
          return !!r?.draft && Math.abs(r.trip_s - saved.trip_s) > 0.05;
        },
        { timeout: 10_000, intervals: [100] },
      )
      .toBe(true);
  } catch (e) {
    const card = (await page.getByTestId("run-table").textContent())?.slice(0, 300);
    const state = await canvas.evaluate((c) => (c as HTMLCanvasElement & { runs: () => unknown }).runs());
    const info = await page.getByTestId("solve-info").evaluate((el) => ({ ...(el as HTMLElement).dataset }));
    console.log(JSON.stringify({ state, info }));
    throw new Error(
      `${(e as Error).message}\ndrafts answered: ${JSON.stringify(answers)}\nrun card: ${card}\nruns: ${JSON.stringify(state)}\nsolves: ${JSON.stringify(info)}`,
    );
  }
  const changedIn = Date.now() - up;
  const draft = (await runOf(page)) as RunMark;
  test.info().annotations.push({ type: "release to new trip time", description: `${changedIn} ms` });
  console.log(`release to the draft's trip time on the band: ${changedIn} ms`);
  expect(changedIn).toBeLessThan(10_000);
  await expect(page.getByTestId("run-table")).toContainText("draft");

  // Ctrl+Z: back to the saved numbers, with no new run asked
  const nDrafts = drafts.length;
  const nRuns = computes.filter((c) => c.body.includes('"railsim.run"')).length;
  await canvas.focus();
  await page.keyboard.press("Control+z");
  await expect
    .poll(async () => {
      const r = await runOf(page);
      return !!r && !r.draft && Math.abs(r.trip_s - saved.trip_s) < 1e-6;
    })
    .toBe(true);
  await page.waitForTimeout(800);
  expect(drafts.length).toBe(nDrafts);
  expect(computes.filter((c) => c.body.includes('"railsim.run"')).length).toBe(nRuns);

  // Ctrl+Shift+Z puts the edit back; Save: the saved run arrives over SSE and equals the draft
  await page.keyboard.press("Control+Shift+z");
  await expect.poll(async () => (await runOf(page))?.draft ?? false, { timeout: 10_000 }).toBe(true);
  const savedAt = Date.now();
  await page.getByTestId("sheet-save").click();
  await expect(page.getByTestId("sheet-save")).toBeDisabled();
  await expect
    .poll(
      async () => {
        const r = await runOf(page);
        return !!r && !r.draft;
      },
      // the saved chain runs again on the hub (the rail, the structure, the assemble, the run)
      { timeout: 120_000 },
    )
    .toBe(true);
  console.log(`save to the saved run over SSE: ${Date.now() - savedAt} ms`);
  const after = (await runOf(page)) as RunMark;
  expect(after.trip_s).toBeCloseTo(draft.trip_s, 1);
  expect(after.running_s).toBeCloseTo(draft.running_s, 1);

  // idle: after 5 s, no requests at all
  await page.waitForTimeout(5000);
  const quiet: string[] = [];
  const onQuiet = (r: Request) => quiet.push(r.url());
  page.on("request", onQuiet);
  await page.waitForTimeout(3000);
  page.off("request", onQuiet);
  page.off("request", onReq);
  expect(quiet).toEqual([]);
});
