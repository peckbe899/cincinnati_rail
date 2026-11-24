// The I2.1 gate on the line sheet (claude/hub_maps/i21_plan.md 1.7 and 6, lane sheet): open Line 6, release a bend
// point drag, and the run time on the band changes within 10 s without a save; no draft run is asked between pointer
// down and pointer up; Ctrl+Z goes back to the saved numbers with no new run; after a save the saved run arrives
// over SSE and equals the draft; an idle sheet then makes no requests.
//
// It reads the band through the canvas's marks() hook: one {kind: "run", dir, trip_s, running_s, draft} per
// direction drawn. A train holding its cruising speed may not feel a change of grade, so one direction's time can
// stay as it was: the change is looked for in either direction, on a bend point with a station between its
// neighbours (where both trains start from a stop).

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

/** Both directions' trip times on the band, and whether they are a draft's. */
const tripsOf = async (page: Page): Promise<{ fwd: number; back: number; draft: boolean } | null> => {
  const m = await marks(page);
  const f = m.find((x) => x.kind === "run" && x.dir === 1) as RunMark | undefined;
  const b = m.find((x) => x.kind === "run" && x.dir === -1) as RunMark | undefined;
  return f && b ? { fwd: f.trip_s, back: b.trip_s, draft: f.draft } : null;
};

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
  const savedBack = (await runOf(page, -1)) as RunMark;
  expect(savedBack).not.toBeNull();
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
  // a bend point drawn clear of every station bar (a press on a bar would drag the station), dragged down 30 px. Of
  // those, one whose stretch between its neighbouring bend points holds a station: both trains start from a stop
  // there under full traction, where a change of grade always changes the time (a train holding its cruising speed
  // may not feel it). A drag of 60 px there made grades steep enough for one draft run to take 9 to 20 s.
  const drawn = (await marks(page)) as (Mark & {
    hidden?: boolean;
    x0?: number;
    x1?: number;
    c0?: number;
    c1?: number;
  })[];
  const bars = drawn.filter((m) => m.kind === "bar");
  const gap = (m: Mark) =>
    Math.min(...bars.map((b) => Math.min(Math.abs(m.x - (b.x0 ?? 0)), Math.abs(m.x - (b.x1 ?? 0)))));
  const stops = bars.map((b) => ((b.c0 ?? 0) + (b.c1 ?? 0)) / 2);
  const pvis = drawn.filter((m) => m.kind === "pvi").sort((p, q) => p.c - q.c);
  const startsHere = (m: Mark) => {
    const k = pvis.indexOf(m);
    const c0 = pvis[k - 1]?.c ?? 0;
    const c1 = pvis[k + 1]?.c ?? Number.POSITIVE_INFINITY;
    return stops.some((c) => c > c0 && c < c1);
  };
  const mk = pvis
    .filter((m) => !(m as { hidden?: boolean }).hidden && gap(m) >= 10 && startsHere(m))
    .sort((p, q) => gap(q) - gap(p))[0];
  expect(mk, "a bend point clear of the stations, with a station between its neighbours").toBeTruthy();
  console.log(`bend point at ${Math.round(mk?.c ?? 0)} m`);
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
    await page.mouse.move(x, y + i);
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

  // released: the draft's run time on the band within 10 s, in either direction
  try {
    await expect
      .poll(
        async () => {
          const t = await tripsOf(page);
          return !!t?.draft && (Math.abs(t.fwd - saved.trip_s) > 0.05 || Math.abs(t.back - savedBack.trip_s) > 0.05);
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
  const draftBack = (await runOf(page, -1)) as RunMark;
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
      const t = await tripsOf(page);
      return !!t && !t.draft && Math.abs(t.fwd - saved.trip_s) < 1e-6 && Math.abs(t.back - savedBack.trip_s) < 1e-6;
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
  const afterBack = (await runOf(page, -1)) as RunMark;
  expect(after.trip_s).toBeCloseTo(draft.trip_s, 1);
  expect(after.running_s).toBeCloseTo(draft.running_s, 1);
  expect(afterBack.trip_s).toBeCloseTo(draftBack.trip_s, 1);
  expect(afterBack.running_s).toBeCloseTo(draftBack.running_s, 1);

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
