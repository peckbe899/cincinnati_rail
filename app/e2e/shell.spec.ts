import { EXPECTED_MISSES, expect, line6Section, openApp, profileOf, test } from "./helpers.ts";

test("fixture plugin adds a tab", async ({ page, watch }) => {
  await openApp(page, "layer=main&tl=canon");
  // A plugin added at run time contributes a pane, a command and a key, exactly as a folder under src/plugins does.
  await page.evaluate(() => {
    const cr = (
      window as unknown as {
        __cr: { addPlugin(p: unknown): void; host: { openPane(id: string): void } };
      }
    ).__cr;
    cr.addPlugin({
      id: "e2e-fixture",
      panes: [
        {
          id: "e2e-fixture",
          title: "Fixture",
          async mount(el: HTMLElement) {
            el.textContent = "The fixture pane is mounted.";
            return { dispose() {} };
          },
        },
      ],
      commands: [
        {
          id: "e2e-fixture.open",
          title: "Open the fixture pane",
          run: (h: { openPane(id: string): void }) => h.openPane("e2e-fixture"),
        },
      ],
    });
    cr.host.openPane("e2e-fixture");
  });
  await expect(page.locator(".dv-tab", { hasText: "Fixture" })).toBeVisible();
  await expect(page.getByText("The fixture pane is mounted.")).toBeVisible();
  // Its command is in the palette.
  await page.keyboard.press("Control+k");
  await page.getByLabel("Command or old key").fill("fixture");
  await expect(page.locator(".palette li", { hasText: "Open the fixture pane" })).toBeVisible();
  await page.keyboard.press("Escape");
  expect(watch.consoleErrors).toEqual([]);
});

test("no console errors", async ({ page, watch, request }) => {
  const sid = await line6Section(request);
  const prof = await profileOf(request, sid, "main");
  // Every first pane, the palette with an old key, the units switch and a layer toggle: no console error, no request
  // that leaves this machine, no 404.
  await openApp(page, `layer=main&tl=canon&sel=profile:${prof.id}&map=12/39.12/-84.51`);
  await expect(page.getByTestId("pvi-table")).toBeVisible();
  await expect(page.getByTestId("map")).toBeVisible();
  // Every first pane is in the layout and draws: a pane that fails to register or to mount fails here.
  const drawn: Record<string, RegExp> = {
    Jobs: /^jobs: /,
    Review: /^Review: |^The review queue/,
    "Old hub": /^The old hub/,
    Inspector: /^(Select a record|Loading|Profile: )/,
  };
  for (const [pane, text] of Object.entries(drawn)) {
    const tab = page.locator(".dv-tab", { hasText: pane });
    await expect(tab, `the ${pane} tab`).toHaveCount(1);
    await tab.click();
    const root = page.locator(`.pane-root[data-pane="${pane === "Old hub" ? "legacy" : pane.toLowerCase()}"]`);
    await expect(root.locator("h3, p").first()).toHaveText(text);
  }
  await page.keyboard.press("Control+k");
  await page.getByLabel("Command or old key").fill("Line_6");
  await page.waitForTimeout(600);
  await page.keyboard.press("Escape");
  await page.getByTestId("units").click();
  await page.getByTestId("units").click();
  await page.waitForTimeout(500);
  expect(watch.consoleErrors).toEqual([]);
  expect(watch.aborted).toEqual([]);
  expect(watch.failed.filter((f) => f.status === 404 && !EXPECTED_MISSES.some((re) => re.test(f.url)))).toEqual([]);
});

test("Ctrl+K finds Line 6 by its name, and Enter right after typing opens it", async ({ page }) => {
  await openApp(page, "layer=main&tl=canon");
  await page.keyboard.press("Control+k");
  const box = page.getByLabel("Command or old key");
  // By name, however it is typed; a station shows its line.
  for (const q of ["Line 6", "line6"]) {
    await box.fill(q);
    await expect(page.locator(".palette li").first()).toContainText("Line 6");
  }
  await box.fill("Bond Hill");
  await expect(page.locator(".palette li", { hasText: "Bond Hill (Line 6)" }).first()).toBeVisible();
  await box.fill("zzqq");
  await expect(page.locator(".palette-empty")).toHaveText('No line, station, command or old key matches "zzqq".');
  // The old key typed at speed and Enter at once: the search is waited for, and Line 6 opens.
  await box.fill("");
  await box.pressSequentially("Line_6", { delay: 40 });
  await page.keyboard.press("Enter");
  await expect(page.locator(".sheet-bar strong")).toHaveText("Line 6");
});
