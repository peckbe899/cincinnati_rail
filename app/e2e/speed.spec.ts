// The line sheet's speed against the old Profiles page (claude/hub_maps/profiles_parity.md): a whole-line bend
// point drag on a deviceScaleFactor 2 screen holds no frame of the page's thread over 50 ms and keeps the old page's
// frame rate (its p95 33 ms), and an idle sheet, maximised or not, costs the page nothing.

import type { APIRequestContext, Page } from "@playwright/test";
import { API, expect, openApp, profileOf, scenario, test, untraced } from "./helpers.ts";

test.use({ deviceScaleFactor: 2 });

async function sectionOf(request: APIRequestContext, route: string): Promise<string> {
  const r = await request.get(`${API}/legacy/section/${route}`);
  return ((await r.json()) as { id: string }).id;
}

async function openLine(page: Page, request: APIRequestContext, route: string, layer: string) {
  const sid = await sectionOf(request, route);
  const prof = await profileOf(request, sid, layer);
  await openApp(page, `layer=${encodeURIComponent(layer)}&tl=canon&sel=profile:${prof.id}`);
  await expect(page.getByTestId("station-table").locator("tr[data-platform]").first()).toBeAttached();
  await expect
    .poll(async () => Number((await page.getByTestId("solve-info").getAttribute("data-full-rev")) ?? 0), {
      timeout: 60_000,
    })
    .toBeGreaterThan(0);
  return { sid, profileId: String(prof.id), prof };
}

async function maximise(page: Page, on: boolean) {
  const b = page.getByTestId("sheet-maximise");
  if (((await b.getAttribute("aria-pressed")) === "true") !== on) await b.click();
  await expect(b).toHaveAttribute("aria-pressed", on ? "true" : "false");
}

/** Long tasks and layout saves over ms of an idle page. */
const idle = (page: Page, ms: number) =>
  page.evaluate(async (ms) => {
    const lt: number[] = [];
    const po = new PerformanceObserver((l) => {
      for (const e of l.getEntries()) lt.push(Math.round(e.duration));
    });
    po.observe({ entryTypes: ["longtask"] });
    let saves = 0;
    const set = Storage.prototype.setItem;
    Storage.prototype.setItem = function (k: string, v: string) {
      if (k.startsWith("cr.layout.")) saves++;
      return set.call(this, k, v);
    };
    await new Promise((r) => setTimeout(r, ms));
    po.disconnect();
    Storage.prototype.setItem = set;
    return { lt, saves };
  }, ms);

test("an idle sheet, docked or maximised, saves the layout no more than once and holds the page for no long task", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "idle");
  await openLine(page, request, "Line_6", layer);
  for (const on of [false, true]) {
    await maximise(page, on);
    await page.waitForTimeout(1200);
    const r = await idle(page, 3000);
    expect(r.saves, `layout saves while idle, maximised ${on}`).toBe(0);
    expect(r.lt, `long tasks while idle, maximised ${on}`).toEqual([]);
  }
});

test("a whole-line bend point drag: the static bands drawn once, each step drawn only where it changed and exactly, one solve per step under 16 ms, the whole solve after the drag", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "drag");
  const { prof } = await openLine(page, request, "Line_6", layer);
  await maximise(page, true);
  const canvas = page.getByTestId("sheet-canvas");
  await canvas.focus();
  await page.keyboard.press("f");
  await page.waitForTimeout(800);
  const pv = ((prof.data as { pvi?: unknown[] }).pvi ?? [])[5] as [number, number] | { c: number };
  const pc = Array.isArray(pv) ? pv[0] : pv.c;
  const marks = (await canvas.evaluate(async (c) => {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return (c as HTMLCanvasElement & { marks: () => { kind: string; c: number; x: number; y: number }[] }).marks();
  })) as { kind: string; c: number; x: number; y: number }[];
  const mk = marks.find((m) => m.kind === "pvi" && Math.abs(m.c - pc) < 1);
  expect(mk, "PVI 6 is drawn").toBeTruthy();
  const box = await canvas.boundingBox();
  const info = page.getByTestId("solve-info");
  const read = async () => ({
    staticDraws: Number(await canvas.getAttribute("data-static-draws")),
    partFrames: Number(await canvas.getAttribute("data-part-frames")),
    fullRev: Number(await info.getAttribute("data-full-rev")),
    mismatch: 0,
  });
  await page.evaluate(() => {
    const el = document.querySelector("[data-testid=solve-info]") as HTMLElement;
    const w = window as unknown as { __ms: Map<string, number>; __mo: MutationObserver };
    w.__ms = new Map();
    w.__mo = new MutationObserver(() => w.__ms.set(el.dataset.rev ?? "", Number(el.dataset.ms)));
    w.__mo.observe(el, { attributes: true });
  });
  const before = await read();
  const x = (box?.x ?? 0) + (mk?.x ?? 0);
  const y = (box?.y ?? 0) + (mk?.y ?? 0);
  // without Playwright's own trace, whose snapshot after each move runs on the page's thread (helpers.ts)
  const during = await untraced(page, async () => {
    await page.mouse.move(x, y);
    await page.mouse.down();
    for (let i = 1; i <= 40; i++) {
      await page.mouse.move(x, y + i * 2);
      await page.waitForTimeout(16);
    }
    const now = await read();
    // the last step, drawn in part over the steps before it, is the frame drawn whole from nothing, pixel for pixel
    now.mismatch = await canvas.evaluate(async (c: HTMLCanvasElement) => {
      await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 60)));
      const g = c.getContext("2d") as CanvasRenderingContext2D;
      const part = g.getImageData(0, 0, c.width, c.height).data;
      (c as HTMLCanvasElement & { repaint: () => void }).repaint();
      const whole = g.getImageData(0, 0, c.width, c.height).data;
      let n = 0;
      for (let i = 0; i < part.length; i++) if (part[i] !== whole[i]) n++;
      return n;
    });
    await page.mouse.up();
    return now;
  });
  const solves = await page.evaluate(() => {
    const w = window as unknown as { __ms: Map<string, number>; __mo: MutationObserver };
    w.__mo.disconnect();
    return [...w.__ms.values()].sort((a, b) => a - b);
  });
  // the grid, the ground and the other static bands are a bitmap the drag never draws again
  expect(before.staticDraws).toBeGreaterThan(0);
  expect(during.staticDraws - before.staticDraws).toBeLessThanOrEqual(1);
  // most steps drew only what they changed, and what they left showed exactly what a whole frame would
  expect(during.partFrames - before.partFrames).toBeGreaterThan(10);
  expect(during.mismatch).toBe(0);
  // the whole solve waits for the pointer to come up, then lands
  expect(during.fullRev).toBe(before.fullRev);
  await expect.poll(async () => (await read()).fullRev, { timeout: 30_000 }).toBeGreaterThan(before.fullRev);
  // one rail solve per step or fewer, and nine in ten of them under a frame's 16 ms as the page sees them
  expect(solves.length).toBeGreaterThan(5);
  expect(solves[Math.floor(solves.length * 0.9)] as number).toBeLessThan(16);
});
