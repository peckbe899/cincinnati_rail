// A server restart gives a new epoch in the stream's hello; the app must treat its cursor as gone and re-read.
// This test starts and restarts its own hub on a copy of the fixture database (CRHUB_E2E_DB), in a var folder of
// its own, so it never disturbs the hub the other tests use.

import { type ChildProcess, spawn } from "node:child_process";
import { copyFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { serveCommand } from "./env.ts";
import { expect, test } from "./helpers.ts";

const REPO = resolve(fileURLToPath(new URL("../../", import.meta.url)));

async function waitHealthy(url: string, ms = 60_000): Promise<void> {
  const t0 = Date.now();
  for (;;) {
    try {
      const r = await fetch(`${url}/api/v1/health`);
      if (r.ok) return;
    } catch {
      /* not up yet */
    }
    if (Date.now() - t0 > ms) throw new Error(`the hub at ${url} did not come up within ${ms} ms`);
    await new Promise((r) => setTimeout(r, 250));
  }
}

function start(db: string, port: number, varDir: string): ChildProcess {
  const [cmd, ...args] = serveCommand(db, port);
  return spawn(cmd as string, args, {
    cwd: REPO,
    env: { ...process.env, CRHUB_VAR: varDir, PYTHONUTF8: "1" },
    stdio: "inherit",
  });
}

async function stop(p: ChildProcess): Promise<void> {
  if (p.exitCode !== null) return;
  const done = new Promise<void>((r) => p.once("exit", () => r()));
  p.kill();
  await done;
}

test("server restart triggers resync", async ({ page }) => {
  const fixture = process.env.CRHUB_E2E_DB;
  expect(fixture, "set CRHUB_E2E_DB to a fixture region.db: this test starts and restarts its own hub").toBeTruthy();
  const dir = mkdtempSync(join(tmpdir(), "cr-e2e-restart-"));
  const db = join(dir, "region.db");
  copyFileSync(fixture as string, db);
  const port = Number(process.env.CRHUB_E2E_RESTART_PORT ?? 8798);
  const url = `http://127.0.0.1:${port}`;
  let hub = start(db, port, join(dir, "var"));
  try {
    await waitHealthy(url);
    await page.goto(`${url}/w/design?layer=main&tl=canon`);
    const events = page.locator('[data-status="core.events"]');
    await expect(events).toHaveText("events: live");
    const epoch1 = await page.evaluate(
      () =>
        (window as unknown as { __cr: { host: { events: { status(): { epoch: string } } } } }).__cr.host.events.status()
          .epoch,
    );

    await stop(hub);
    await expect(events).not.toHaveText("events: live");
    hub = start(db, port, join(dir, "var"));
    await waitHealthy(url);

    // The stream comes back with a new epoch, and the app says it re-read.
    await expect(events).toHaveText("events: live", { timeout: 30_000 });
    const epoch2 = await page.evaluate(
      () =>
        (window as unknown as { __cr: { host: { events: { status(): { epoch: string } } } } }).__cr.host.events.status()
          .epoch,
    );
    expect(epoch2).not.toBe(epoch1);
    await expect(page.locator(".toast", { hasText: "resync (epoch)" })).toBeVisible();
  } finally {
    await stop(hub);
    rmSync(dir, { recursive: true, force: true });
  }
});
