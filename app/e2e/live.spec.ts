// Always live (checklist I2.0): a line file saved on disk reaches the open line sheet in under 3 s, in place (no
// reload, the selection kept), with a toast in plain words and the Sources chip and pane following; Undo this import
// puts it back; Pause live holds a change until Resume.
//
// This test starts its own hub on a copy of the fixture database (CRHUB_E2E_DB), in a var folder of its own, with
// the line files' tier moved to a copy it may write (CRHUB_CONFIG), so it never touches data/profile.

import { type ChildProcess, spawn } from "node:child_process";
import { copyFileSync, cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { type Page, request as pwRequest } from "@playwright/test";
import { serveCommand } from "./env.ts";
import { expect, line6Section, test } from "./helpers.ts";

const REPO = resolve(fileURLToPath(new URL("../../", import.meta.url)));

async function waitHealthy(url: string, ms = 90_000): Promise<void> {
  const t0 = Date.now();
  for (;;) {
    try {
      const r = await fetch(`${url}/api/v1/live`);
      if (r.ok && ((await r.json()) as { enabled: boolean }).enabled) return;
    } catch {
      /* not up yet */
    }
    if (Date.now() - t0 > ms) throw new Error(`the hub at ${url} did not come up within ${ms} ms`);
    await new Promise((r) => setTimeout(r, 250));
  }
}

async function stop(p: ChildProcess): Promise<void> {
  if (p.exitCode !== null) return;
  const done = new Promise<void>((r) => p.once("exit", () => r()));
  p.kill();
  await done;
}

interface LineFile {
  stations: { name: string; c: number }[];
}

function editLine(file: string, fn: (d: LineFile) => void): void {
  const d = JSON.parse(readFileSync(file, "utf-8")) as LineFile;
  fn(d);
  writeFileSync(file, JSON.stringify(d));
}

const stationLabels = (page: Page) => page.getByTestId("sheet-labels").locator('li[data-kind="station"]');

test("a saved line file reaches the open sheet in under 3 s, in place, and Undo puts it back", async ({ page }) => {
  test.setTimeout(180_000);
  const fixture = process.env.CRHUB_E2E_DB;
  expect(fixture, "set CRHUB_E2E_DB to a fixture region.db: this test starts its own live hub").toBeTruthy();
  const dir = mkdtempSync(join(tmpdir(), "cr-e2e-live-"));
  const db = join(dir, "region.db");
  copyFileSync(fixture as string, db);
  const profile = join(dir, "profile");
  cpSync(join(REPO, "data", "profile"), profile, { recursive: true });
  const config = join(dir, "config.json");
  writeFileSync(config, JSON.stringify({ tiers: { profile_lines: { root: profile } }, live: { old_hub_db: null } }));
  const port = Number(process.env.CRHUB_E2E_LIVE_PORT ?? 8797);
  const url = `http://127.0.0.1:${port}`;
  const [cmd, ...args] = serveCommand(db, port);
  const hub = spawn(cmd as string, args, {
    cwd: REPO,
    env: { ...process.env, CRHUB_VAR: join(dir, "var"), CRHUB_CONFIG: config, PYTHONUTF8: "1" },
    stdio: "inherit",
  });
  try {
    await waitHealthy(url);
    const api = await pwRequest.newContext({ baseURL: url });
    const sid = await line6Section(api);
    await api.dispose();
    await page.goto(`${url}/w/design?layer=main&tl=canon&sel=section:${sid}`);
    await expect(page.locator('[data-status="core.events"]')).toHaveText("events: live");
    const chip = page.locator('[data-status="sources"]');
    await expect(chip).toHaveText(/^live/);
    // Ben has a station selected; the update must keep it
    await expect(page.getByTestId("station-table").locator("td.name", { hasText: "Bond Hill" })).toBeVisible({
      timeout: 30_000,
    });
    await page.getByTestId("station-table").locator("td.name", { hasText: "Bond Hill" }).click();
    await expect(page.getByTestId("station-card-name")).toHaveText("Bond Hill");
    const file = join(profile, "lines", "Line_6.json");
    const name = (JSON.parse(readFileSync(file, "utf-8")) as LineFile).stations[2]?.name ?? "";
    const third = stationLabels(page)
      .filter({ hasText: `${name},` })
      .first();
    await expect(third).toBeAttached();
    const before = (await third.textContent()) ?? "";
    await page.evaluate(() => {
      (window as unknown as { __noReload: boolean }).__noReload = true;
    });

    // Save Line 6's file with its third station 25 m further on
    const t0 = Date.now();
    editLine(file, (d) => {
      const s = d.stations[2];
      if (s) s.c += 25;
    });
    await expect
      .poll(async () => (await third.textContent()) ?? "", { timeout: 10_000, intervals: [50] })
      .not.toBe(before);
    const ms = Date.now() - t0;
    console.log(`line file saved -> open sheet updated in ${ms} ms`);
    expect(ms).toBeLessThan(3000);
    // in place: no reload, the selection kept, a toast in plain words, the chip says when
    expect(await page.evaluate(() => (window as unknown as { __noReload?: boolean }).__noReload)).toBe(true);
    await expect(page.getByTestId("station-card-name")).toHaveText("Bond Hill");
    const toast = page.locator(".toast", { hasText: "Line 6 updated from the line files: 1 station moved" });
    await expect(toast).toBeVisible();
    await expect(chip).toHaveText(/^live, updated \d\d:\d\d$/);

    // The Sources pane lists the change; Undo this import puts the station back
    await chip.click();
    const pane = page.getByTestId("sources-pane");
    await expect(pane).toBeVisible();
    const row = pane.locator('tr[data-source="import:profile_lines"]');
    await expect(row).toContainText("Line 6 updated from the line files");
    await row.locator('button[data-action="undo"]').click();
    await expect.poll(async () => (await third.textContent()) ?? "", { timeout: 10_000 }).toBe(before);
    await expect(row).toHaveAttribute("data-state", "held");

    // Pause live: a new save waits; Resume takes it in
    await pane.getByTestId("live-toggle").click();
    await expect(chip).toHaveText(/^live: paused/);
    editLine(file, (d) => {
      const s = d.stations[2];
      if (s) s.c += 40;
    });
    // the line files and the old hub (whose profiles hang on the line files) both wait
    await expect(chip).toHaveText(/^live: paused, [12] waiting/, { timeout: 10_000 });
    expect((await third.textContent()) ?? "").toBe(before);
    await pane.getByTestId("live-toggle").click();
    await expect.poll(async () => (await third.textContent()) ?? "", { timeout: 10_000 }).not.toBe(before);
    await expect(chip).toHaveText(/^live, updated/);
  } finally {
    await stop(hub);
    rmSync(dir, { recursive: true, force: true });
  }
});
