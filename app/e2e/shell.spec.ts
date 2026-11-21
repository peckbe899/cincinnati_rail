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
  for (const pane of ["Jobs", "Review", "Old hub", "Inspector"]) {
    const tab = page.locator(".dv-tab", { hasText: pane });
    if (await tab.count()) await tab.first().click();
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
