// I2.1: the param ground.source set to region in a scenario. The sheet's first read of the section's input finds the
// ground model not sampled yet ("line_file (region pending)"), so the hub samples it; on its result event the sheet
// reads the input again and the station panel's ground row names the ground model. Main stays on the line file's
// survey.

import type { APIRequestContext, Page } from "@playwright/test";
import { API, expect, openApp, profileOf, scenario, test } from "./helpers.ts";

async function sectionOf(request: APIRequestContext, route: string): Promise<string> {
  const r = await request.get(`${API}/legacy/section/${route}`);
  if (r.ok()) {
    const hit = (await r.json()) as { kind: string; id: string };
    if (hit.kind === "section") return hit.id;
  }
  const rt = (await (await request.get(`${API}/legacy/route/${route}`)).json()) as { id: string };
  const s = (await (await request.get(`${API}/k/section?parent=${rt.id}`)).json()) as { items: { id: string }[] };
  return s.items[0]?.id as string;
}

async function setGroundSource(request: APIRequestContext, layer: string, value: string): Promise<void> {
  const r = await request.post(`${API}/k/param?layer=${encodeURIComponent(layer)}`, {
    data: { data: { path: "ground.source", value, unit: "enum", scope: null, years: null }, geom: null },
    headers: { "X-CR-Client": "e2e", "Content-Type": "application/json", "Idempotency-Key": `gs-${Date.now()}` },
  });
  expect(r.ok(), `writing ground.source: ${r.status()} ${await r.text()}`).toBeTruthy();
}

const groundSource = (page: Page) => page.getByTestId("sp-ground").locator(".sp-src");

async function openFirstStation(page: Page, request: APIRequestContext, sid: string, layer: string): Promise<void> {
  const prof = await profileOf(request, sid, layer);
  await openApp(page, `layer=${encodeURIComponent(layer)}&tl=canon&sel=profile:${prof.id}`);
  await expect(page.getByTestId("station-table")).toBeVisible();
  await page.getByTestId("station-table").locator("td.name").first().click();
  await expect(page.getByTestId("sp-ground")).toBeVisible();
}

test("ground.source region: the ground model arrives on the sheet and the panel names it", async ({
  page,
  request,
}) => {
  test.setTimeout(120_000);
  const sid = await sectionOf(request, "Line_2b");
  const layer = await scenario(request, "groundsrc");
  const before = await request.get(`${API}/x/profiles/sections/${sid}/input?layer=${layer}`);
  expect(before.headers()["x-cr-ground"]).toBe("line_file");
  await setGroundSource(request, layer, "region");
  await openFirstStation(page, request, sid, layer);
  // pending at first (or already sampled when the hub was quick), then the ground model
  await expect(groundSource(page)).toHaveText(/ground model/);
  await expect(groundSource(page)).toHaveText("ground model", { timeout: 60_000 });
  const after = await request.get(`${API}/x/profiles/sections/${sid}/input?layer=${layer}`);
  expect(after.headers()["x-cr-ground"]).toBe("region");
  // main is untouched by the scenario's choice
  const main = await request.get(`${API}/x/profiles/sections/${sid}/input?layer=main`);
  expect(main.headers()["x-cr-ground"]).toBe("line_file");
});
