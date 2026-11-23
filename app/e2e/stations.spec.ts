// The line sheet's stations against the old Profiles page (claude/hub_maps/profiles_parity.md, section A and its
// acceptance checks). The old page's values come from the seed's alignment docs (hub/seed/alignments/*.json, the
// derived stations[] the old page saved) and from its station card as Ben saw it (the numbers below are read off the
// old page on the same seed). Edits run in a scenario layer of each test's own.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { APIRequestContext, Page } from "@playwright/test";
import { API, expect, getRecord, openApp, profileOf, scenario, settled, solveRev, test } from "./helpers.ts";

const REPO = resolve(import.meta.dirname, "..", "..");
const doc = (route: string) =>
  JSON.parse(readFileSync(resolve(REPO, "hub", "seed", "alignments", `${route}.json`), "utf8")) as {
    platform_m: number;
    del: string[];
    stations: { name: string; c: number; point_c: number; rail: number; type: string }[];
  };

interface Mark {
  kind: string;
  id: string;
  [k: string]: unknown;
}

interface StationInput {
  platforms: { platform_id: string; name: string; side: string | null; point_c_m: number }[];
  profile: { del?: string[] };
  params: { platform_m: number };
}

/** A route's section id, through the legacy index. */
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

async function stationInput(request: APIRequestContext, sid: string, layer = "main"): Promise<StationInput> {
  const r = await request.get(`${API}/x/profiles/sections/${sid}/stations?layer=${encodeURIComponent(layer)}`);
  expect(r.ok()).toBeTruthy();
  return (await r.json()) as StationInput;
}

/** The station facts counter now: wait for a later one with factsSettled. */
const factsRev = async (page: Page) =>
  Number((await page.getByTestId("solve-info").getAttribute("data-facts-rev")) ?? 0);
async function factsSettled(page: Page, rev: number): Promise<void> {
  await expect.poll(() => factsRev(page)).toBeGreaterThan(rev);
  await page.waitForTimeout(60);
}

/** Open a line's sheet in a layer, with its station facts in. */
async function openLine(page: Page, request: APIRequestContext, route: string, layer: string) {
  const sid = await sectionOf(request, route);
  const prof = await profileOf(request, sid, layer);
  await openApp(page, `layer=${encodeURIComponent(layer)}&tl=canon&sel=profile:${prof.id}`);
  await expect(page.getByTestId("station-table")).toBeVisible();
  await settled(page, 0);
  await factsSettled(page, 0);
  return { sid, profileId: String(prof.id) };
}

const canvas = (page: Page) => page.getByTestId("sheet-canvas");
/** What the bands drew, after the frame in flight (a zoom or an edit draws on the next frame). */
const marks = (page: Page): Promise<Mark[]> =>
  canvas(page).evaluate(async (c) => {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return (c as HTMLCanvasElement & { marks: () => Mark[] }).marks();
  });
const frame = (page: Page) =>
  canvas(page).evaluate(async (c) => {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return (
      c as HTMLCanvasElement & {
        frame: () => {
          c0: number;
          c1: number;
          z0: number;
          z1: number;
          plot: { x: number; y: number; w: number; h: number };
        };
      }
    ).frame();
  });

/** Select a station from the table and wait for its panel. */
async function pick(page: Page, name: string): Promise<void> {
  await page.getByTestId("station-table").locator("td.name", { hasText: name }).first().click();
  await expect(page.getByTestId("station-card-name")).toHaveText(name);
}

/** A panel row's value text. */
const row = (page: Page, id: string) => page.getByTestId(`sp-${id}`).locator(".sp-val");

/** The selected station's bar mark. */
async function selectedBar(page: Page): Promise<Mark> {
  const m = await marks(page);
  const bar = m.find((x) => x.kind === "bar" && x.selected);
  if (!bar) throw new Error("no selected bar on the canvas");
  return bar;
}

/** Ctrl+Z with the focus on the canvas (the hub's undo: an unsaved step first). */
async function undo(page: Page): Promise<void> {
  const rev = await factsRev(page);
  await canvas(page).focus();
  await page.keyboard.press("Control+z");
  await factsSettled(page, rev);
}

/** Do something that edits the draft, and wait until the facts of the edit are in. */
async function edits(page: Page, run: () => Promise<unknown>): Promise<void> {
  const rev = await factsRev(page);
  await run();
  await factsSettled(page, rev);
}

test("seeing: every station drawn as the old page drew it, at its true length, level, point and type (checks 1, 3-6, 10, 20)", async ({
  page,
  request,
  watch,
}) => {
  // The types the hub gives differently from the old doc's stations[], each for a reason the parity doc names:
  // the doc's type is older than the old page's 5 November baseline, which agrees with the hub.
  const known: Record<string, string> = {
    "Line_3 Bond Hill": "doc older than the baseline: open trough at 4.9 m",
    "Line_6 North Avondale": "doc older than the baseline: shield past Phase 1's limit",
    "Line_6 Forest": "the seed's level differs from the baseline's (open at grade)",
  };
  for (const route of ["Line_3", "Line_6"]) {
    const { sid } = await openLine(page, request, route, "main");
    const si = await stationInput(request, sid);
    const d = doc(route);
    const half = si.params.platform_m / 2;
    const name = new Map(si.platforms.map((p) => [p.platform_id, p.name]));
    const del = new Set(si.profile.del ?? []);
    await canvas(page).focus();
    await page.keyboard.press("f");
    await page.waitForTimeout(150);
    const m = await marks(page);
    const bars = m.filter((x) => x.kind === "bar");
    // 1: one bar per platform, the stations minus del
    expect(new Set(bars.map((b) => b.id))).toEqual(
      new Set(si.platforms.filter((p) => !del.has(p.platform_id)).map((p) => p.platform_id)),
    );
    for (const s of d.stations) {
      const bar = bars.find((b) => name.get(b.id) === s.name && Math.abs((b.c0 as number) + half - s.c) < 0.06);
      expect(bar, `${route} ${s.name} has a bar`).toBeTruthy();
      if (!bar) continue;
      // 3: the bar runs c - half to c + half at the rail, tilted by sg
      expect((bar.c1 as number) - (bar.c0 as number)).toBeCloseTo(2 * half, 2);
      expect(((bar.z0 as number) + (bar.z1 as number)) / 2).toBeCloseTo(s.rail, 1);
      // 4: the drawn point at the stop
      const pt = m.find((x) => x.kind === "point" && x.id === bar.id);
      expect(pt?.c as number).toBeCloseTo(s.point_c, 1);
      // 5: the type, in the strip and the outline
      const strip = m.find((x) => x.kind === "strip" && x.id === bar.id);
      if (!known[`${route} ${s.name}`]) expect(strip?.type, `${route} ${s.name} type`).toBe(s.type);
      // 6: a box from rail - 1.0 to rail + 4.6 (5.2 on an island)
      const st = m.find((x) => x.kind === "structure" && x.id === bar.id);
      if (st?.what === "box") {
        const island = si.platforms.find((p) => p.platform_id === bar.id)?.side === "island";
        const rail = ((bar.z0 as number) + (bar.z1 as number)) / 2;
        expect(st.top_m as number).toBeCloseTo(rail + (island ? 5.2 : 4.6), 2);
        expect(st.bottom_m as number).toBeCloseTo(rail - 1.0, 2);
      }
    }
    // 10 and 20: the removed stations, a struck-through mark on the sheet and a row with Restore
    const removed = m.filter((x) => x.kind === "removed").map((x) => name.get(x.id));
    const list = page.getByTestId("removed-list").locator("td.name");
    const expected = route === "Line_3" ? ["Goverment Center"] : ["Greenlee", "Lytle Park"];
    expect(removed.sort()).toEqual(expected);
    expect((await list.allTextContents()).sort()).toEqual(expected);
    // S82: the line summary
    await expect(page.getByTestId("station-summary")).toContainText(`31 stations, ${expected.length} removed`);
  }
  expect(watch.consoleErrors).toEqual([]);
});

test("seeing: names, type squares and the selected one always named (check 2), depth tags and the strip", async ({
  page,
  request,
}) => {
  await openLine(page, request, "Line_6", "main");
  await pick(page, "Bond Hill");
  const labels = page.getByTestId("sheet-labels");
  await canvas(page).focus();
  await page.keyboard.press("f");
  await expect(labels.locator('li[data-kind="station"][data-selected="1"]')).toHaveAttribute("data-drawn", "1");
  const m = await marks(page);
  const names = m.filter((x) => x.kind === "name");
  expect(names.filter((x) => x.drawn).length).toBeGreaterThan(10);
  // every drawn name has its type colour square
  expect(names.filter((x) => x.drawn).every((x) => typeof x.colour === "string")).toBe(true);
  // zoomed to about 2+000 to 6+000 every station in view is named
  for (let i = 0; i < 6; i++) await page.keyboard.press("+");
  await expect.poll(async () => (await marks(page)).filter((x) => x.kind === "name" && !x.drawn).length).toBe(0);
});

test("access drawing: halls, crossunder, shaft and mezzanine with the old labels (check 7)", async ({
  page,
  request,
}) => {
  const expectAccess = async (route: string, station: string, what: string, label: string, source: string) => {
    await openLine(page, request, route, "main");
    await pick(page, station);
    await canvas(page).focus();
    await page.keyboard.press("+");
    const bar = await selectedBar(page);
    const shapes = (await marks(page)).filter((x) => x.kind === "access" && x.id === bar.id);
    expect(
      shapes.map((x) => [x.what, x.label]),
      `${route} ${station}`,
    ).toContainEqual([what, label]);
    await expect(page.getByTestId("sp-access").locator(".sp-src")).toContainText(source);
  };
  // Ben's choices (imported from the old hub) and the rules
  await expectAccess("Line_3", "Genesee", "hall", "ticket hall", "old hub");
  await expectAccess("Line_6", "Taft Theater", "shaft", "lifts", "rule");
  await expectAccess("Line_1", "Liberty", "crossunder", "crossunder", "old hub");
  await expectAccess("Line_1", "Winton Place", "mezzanine", "mezzanine / passthrough", "rule");
  await expect(page.getByLabel("Winton Place access")).toHaveValue("");
});

test("the panel shows the old card's values with their sources and rules (checks 11-17)", async ({ page, request }) => {
  await openLine(page, request, "Line_3", "main");
  await pick(page, "Genesee");
  await expect(row(page, "chainage")).toHaveText("14+982");
  await expect(row(page, "platform")).toHaveText("14+921 to 15+043");
  await expect(page.getByLabel("Genesee rail level")).toHaveValue("153.20");
  await expect(page.getByLabel("Genesee rail below ground")).toHaveValue("13.60");
  await expect(row(page, "ground")).toHaveText("166.80 m");
  await expect(row(page, "grades")).toHaveText("−0.7‰ / −0.4‰");
  await expect(page.getByLabel("Genesee point from platform start")).toHaveValue("61.0");
  await expect(page.getByLabel("Genesee platform grade")).toHaveValue("0.0");
  await expect(row(page, "type")).toContainText("Cut & cover");
  await expect(row(page, "street")).toHaveText(
    "under Central Parkway (Ludlow to Reading Road) (built over the subway)",
  );
  await expect(row(page, "opening")).toHaveText("1906 (Phase 1); later: Line 5 1909");
  await expect(row(page, "hallroom")).toHaveText("needs 9.15 m of rail depth (island box); 13.60 here");
  await expect(row(page, "curve")).toHaveText("straight");
  await expect(row(page, "gaps")).toHaveText("0.0 cm / 0.0 cm");
  await expect(page.getByLabel("Genesee side or island")).toHaveValue("island");
  await expect(page.getByLabel("Genesee access")).toHaveValue("end_halls");
  // every row says where its value comes from; the rule ids are the registry's
  await expect(page.getByTestId("sp-level").locator(".sp-src")).toHaveText("old hub");
  await expect(page.getByTestId("sp-stt").locator(".sp-src")).toContainText("station.type.selection_else_limit");
  await expect(page.getByTestId("sp-lim-grade").locator(".sp-src")).toHaveText("literal.ERA.sgMax.lines_1_7");
  // Ross: the curve and its gaps as the old card read them
  await pick(page, "Ross");
  await expect(row(page, "chainage")).toHaveText("0+912 (point 0+913)");
  await expect(row(page, "curve")).toHaveText("333 m · ERROR");
  await expect(row(page, "gaps")).toHaveText("9.1 cm / 4.4 cm");
  await expect(row(page, "street")).toHaveText("under Section Avenue");
  await expect(row(page, "opening")).toHaveText("1922 (Phase 1)");
  await expect(row(page, "hallroom")).toHaveText("needs 8.55 m of rail depth (side box); 9.00 here");
  await expect(page.getByLabel("Ross point from platform start")).toHaveValue("61.4");
  // and in feet
  await page.getByTestId("units").click();
  await expect(page.getByLabel("Ross rail level")).toHaveValue((178 / 0.3048).toFixed(2));
  await page.getByTestId("units").click();
  // the table: type chip, street, depth (19)
  const tr = page.getByTestId("station-table").locator('tr:has(td.name:text-is("Genesee"))');
  await expect(tr.locator("td.street")).toHaveText("Central Parkway (Ludlow to Reading Road)");
  await expect(tr.locator(".type-chip")).toHaveAttribute("data-type", "cutcover");
  await expect(tr.locator("td.num")).toHaveText("13.6");
});

test("drags and keys: level, arrows, Alt drag, slide limit, point field and buttons, each one undo step (checks 21-26, 37)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "stdrag");
  await openLine(page, request, "Line_3", layer);
  await pick(page, "Genesee");
  await canvas(page).focus();
  for (let i = 0; i < 6; i++) await page.keyboard.press("+");
  const box = await canvas(page).boundingBox();
  if (!box) throw new Error("no canvas");
  const level = page.getByLabel("Genesee rail level");
  const point = page.getByLabel("Genesee point from platform start");
  // 21: Shift + drag the bar up about a metre: st + 1.0
  let bar = await selectedBar(page);
  let f = await frame(page);
  const pxPerM = f.plot.h / (f.z1 - f.z0);
  const x = box.x + ((bar.x0 as number) + (bar.x1 as number)) / 2;
  const y = box.y + (bar.y0 as number);
  await edits(page, async () => {
    await page.keyboard.down("Shift");
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x, y - pxPerM * 0.4, { steps: 4 });
    await page.mouse.move(x, y - pxPerM * 0.7, { steps: 4 });
    await page.mouse.up();
    await page.keyboard.up("Shift");
  });
  await expect(level).toHaveValue("154.00");
  await expect(page.getByTestId("sp-level").locator(".sp-src")).toHaveText("Ben, not saved");
  await expect(page.getByTestId("sp-level")).toContainText("was 153.20");
  // 37: the whole drag is one step
  await undo(page);
  await expect(level).toHaveValue("153.20");
  // 22: Arrow Up three times, Shift + Arrow Up once: + 1.3
  await canvas(page).focus();
  for (const k of ["ArrowUp", "ArrowUp", "ArrowUp", "Shift+ArrowUp"]) await edits(page, () => page.keyboard.press(k));
  await expect(level).toHaveValue("154.50");
  for (let i = 0; i < 4; i++) await undo(page);
  await expect(level).toHaveValue("153.20");
  // 23: Alt + drag the bar 20 m right: so + 20 in 0.5 m steps, the drawn point stays
  bar = await selectedBar(page);
  f = await frame(page);
  const pxPerC = f.plot.w / (f.c1 - f.c0);
  const before = (await marks(page)).find((m) => m.kind === "point" && m.id === bar.id);
  await edits(page, async () => {
    await page.keyboard.down("Alt");
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + pxPerC * 10, y, { steps: 4 });
    await page.mouse.move(x + pxPerC * 20, y, { steps: 4 });
    await page.mouse.up();
    await page.keyboard.up("Alt");
  });
  await expect(row(page, "chainage")).toContainText("(point 14+982)");
  const so = 61 - Number(await point.inputValue());
  expect(so).toBeGreaterThan(18);
  expect(so).toBeLessThan(22);
  expect(Math.round(so * 2)).toBe(so * 2);
  const after = (await marks(page)).find((m) => m.kind === "point" && m.id === bar.id);
  expect(after?.c).toBeCloseTo(before?.c as number, 3);
  await undo(page);
  await expect(point).toHaveValue("61.0");
  // 24: Alt + drag far past 150 m: held at 150
  await edits(page, async () => {
    await page.keyboard.down("Alt");
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + pxPerC * 400, y, { steps: 6 });
    await page.mouse.up();
    await page.keyboard.up("Alt");
  });
  await expect(point).toHaveValue((61 - 150).toFixed(1));
  await undo(page);
  // 25: 10 in Point from platform start: so = half - 10, rounded to 0.5 m
  await edits(page, async () => {
    await point.fill("10");
  });
  await expect(row(page, "chainage")).toContainText("15+033");
  await page.keyboard.press("Escape");
  await undo(page);
  await expect(point).toHaveValue("61.0");
  // 26: Point at start, Centred, Point at end
  for (const [label, value] of [
    ["Point at start", "0.0"],
    ["Point at end", "122.0"],
    ["Centred", "61.0"],
  ] as const) {
    await edits(page, () => page.getByRole("button", { name: label, exact: true }).click());
    await expect(point).toHaveValue(value);
  }
  // Alt + Right slides 0.5 m
  await canvas(page).focus();
  await edits(page, () => page.keyboard.press("Alt+ArrowRight"));
  await expect(point).toHaveValue("60.5");
});

test("panel edits: grade, ease, depth, type, access, gap fillers; one changeset on Save, Ctrl+Z reverts it (checks 27-34, 37)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "stedit");
  const { sid, profileId } = await openLine(page, request, "Line_3", layer);
  const v0 = await getRecord(request, "profile", profileId, layer);
  await pick(page, "Genesee");
  const sg = page.getByLabel("Genesee platform grade");
  // 27: 12 per mille: the platform grade error, with the old numbers
  await edits(page, () => sg.fill("12"));
  await expect(page.getByTestId("sp-flag-platform_grade_over")).toContainText(
    "Platform grade +12.0‰ is over the limit of 7.5‰",
  );
  // 28: Ease the bends: back within the limit, the error gone, one step
  await page.keyboard.press("Escape");
  await edits(page, () => page.getByTestId("sp-ease").click());
  await expect(canvas(page)).toHaveAttribute("data-easing", "0");
  await expect.poll(async () => Math.abs(Number(await sg.inputValue()))).toBeLessThanOrEqual(7.5);
  await expect(page.getByTestId("sp-flag-platform_grade_over")).toHaveCount(0);
  await undo(page);
  await expect(sg).toHaveValue("12.0");
  await undo(page);
  await expect(sg).toHaveValue("0.0");
  // 30: 10 in Rail below ground: st = ground - 10
  await edits(page, () => page.getByLabel("Genesee rail below ground").fill("10"));
  await expect(page.getByLabel("Genesee rail level")).toHaveValue("156.80");
  await undo(page);
  // 31: Elevated on a station under ground: stt elevated and the rail raised over the ground for the mezzanine
  await edits(page, () => page.getByLabel("Genesee station type").selectOption("elevated"));
  const raised = Number(await page.getByLabel("Genesee rail level").inputValue());
  expect(raised).toBeGreaterThanOrEqual(166.8 + 5.0);
  await expect(row(page, "type")).toContainText("Elevated: selected by Ben");
  // 32: back to the rules: the key goes (the level stays Ben's, as on the old page)
  await edits(page, () => page.getByLabel("Genesee station type").selectOption(""));
  await expect(page.getByLabel("Genesee station type")).toHaveValue("");
  await undo(page);
  await undo(page);
  await expect(page.getByLabel("Genesee rail level")).toHaveValue("153.20");
  // 33: End ticket halls on a station shallower than D_HALL: the hall too shallow error
  await pick(page, "Warner");
  await edits(page, () => page.getByLabel("Warner access").selectOption("end_halls"));
  await expect(page.getByTestId("sp-flag-access_hall_too_shallow")).toContainText(
    "End ticket halls (Ben) needs the rail at least 8.55 m down",
  );
  // 34: gap fillers on Ross (R 333 m): the curve flag goes from error to warning
  await pick(page, "Ross");
  await expect(page.getByTestId("sp-flag-platform_curve").locator(".sp-sev")).toHaveText("error");
  await edits(page, () => page.getByTestId("sp-gapfill").click());
  await expect(page.getByTestId("sp-flag-platform_curve").locator(".sp-sev")).toHaveText("warning");
  await expect(row(page, "curve")).toHaveText("333 m · exception, gap fillers");
  // the Save button counts the stations changed; one save is one changeset
  await expect(page.getByTestId("sheet-save")).toHaveText("Save (2 stations)");
  await page.keyboard.press("Control+s");
  await expect
    .poll(async () => Number((await getRecord(request, "profile", profileId, layer)).version))
    .toBe(Number(v0.version) + 1);
  const v1 = (await getRecord(request, "profile", profileId, layer)).data as Record<string, Record<string, unknown>>;
  const ids = (await stationInput(request, sid, layer)).platforms;
  const warner = ids.find((p) => p.name === "Warner")?.platform_id as string;
  const ross = ids.find((p) => p.name === "Ross")?.platform_id as string;
  expect(v1.access?.[warner]).toEqual({ type: "end_halls" });
  expect(v1.gapfill).toContain(ross);
  // after the save Ctrl+Z is the hub's undo of that changeset
  await canvas(page).focus();
  await page.keyboard.press("Control+z");
  await expect
    .poll(async () => Number((await getRecord(request, "profile", profileId, layer)).version))
    .toBe(Number(v0.version) + 2);
  const v2 = (await getRecord(request, "profile", profileId, layer)).data as Record<string, unknown>;
  expect(v2).toEqual(v0.data);
});

// Ease all platforms on Line 6 in the old page on the seed (parity review, 23 November, read off S.align.sg): each
// platform eased three times before the next, the line-end platforms toward their one grade.
const OLD_EASE_ALL_LINE_6: Record<string, number> = {
  Towne: 7.5,
  "Bond Hill": -7.5,
  Chalet: 6.9,
  "North Avondale": -1.5,
  Forest: 7.5,
  "UC Medical/Corryville": -0.2,
  Oak: -7.5,
  Burnet: -7.5,
  McGregor: -7.5,
  Dorchester: -7.5,
  Elsinore: -7.5,
  Pendleton: -7.5,
  Times: -7.5,
  "Taft Theater": -7.5,
  "Public Landing": -7.5,
  Taylor: 7.5,
  MacArthur: 7.5,
  Tibbatts: -7.5,
  Lowell: -7.5,
  Eastside: 7.5,
  Westside: -2,
  Bullock: 7.5,
  Arlington: 7.5,
  "Kyles Lane": 7.5,
  "Fort Mitchell": 2.7,
  "South Fort Mitchell": 7.5,
  "Crestview Hills/Thomas More": -0.8,
  Dudley: -2,
  Stevenson: -1.4,
  Brightleaf: -5.1,
  Beechgrove: 2.9,
};

test("the plot keeps room to tell stations apart beside the panel: at least 580 px wide (490 before), names not cut at the top", async ({
  page,
  request,
}) => {
  // a fresh browser context: the default layout
  await openLine(page, request, "Line_1", "main");
  await pick(page, "Fountain Square");
  const f = await frame(page);
  expect(f.plot.w).toBeGreaterThanOrEqual(580);
  expect(f.plot.y).toBeGreaterThanOrEqual(84);
});

test("Alt + Left or Right never reaches the browser (Back on Windows), even read only on main", async ({
  page,
  request,
}) => {
  await openLine(page, request, "Line_3", "main");
  await pick(page, "Ross");
  await page.evaluate(() => {
    (window as unknown as { altKeys: boolean[] }).altKeys = [];
    window.addEventListener("keydown", (e) => {
      if (e.altKey && e.key.startsWith("Arrow"))
        (window as unknown as { altKeys: boolean[] }).altKeys.push(e.defaultPrevented);
    });
  });
  await canvas(page).focus();
  await page.keyboard.press("Alt+ArrowLeft");
  await page.keyboard.press("Alt+ArrowRight");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Alt+ArrowLeft");
  expect(await page.evaluate(() => (window as unknown as { altKeys: boolean[] }).altKeys)).toEqual([true, true, true]);
});

test("ease all platforms is one step and gives the old page's grades (check 29)", async ({ page, request }) => {
  const layer = await scenario(request, "stease");
  const { sid, profileId } = await openLine(page, request, "Line_6", layer);
  const v0 = await getRecord(request, "profile", profileId, layer);
  await page.getByTestId("ease-all").click();
  await expect(canvas(page)).toHaveAttribute("data-easing", "0", { timeout: 60_000 });
  await expect(page.getByTestId("sheet-save")).toContainText("stations");
  await expect.poll(() => page.locator(".toast", { hasText: "Platforms sloped" }).count(), { timeout: 30_000 }).toBe(1);
  const before = await factsRev(page);
  await factsSettled(page, before - 1);
  await pick(page, "Bond Hill");
  expect(Math.abs(Number(await page.getByLabel("Bond Hill platform grade").inputValue()))).toBeLessThanOrEqual(7.5);
  await undo(page);
  await expect(page.getByTestId("sheet-save")).toHaveText("Save");
  // again, saved, against the old page's numbers
  await page.getByTestId("ease-all").click();
  await expect(canvas(page)).toHaveAttribute("data-easing", "0", { timeout: 60_000 });
  await canvas(page).focus();
  await page.keyboard.press("Control+s");
  await expect
    .poll(async () => Number((await getRecord(request, "profile", profileId, layer)).version))
    .toBe(Number(v0.version) + 1);
  const sg = ((await getRecord(request, "profile", profileId, layer)).data as { sg?: Record<string, number> }).sg ?? {};
  const name = new Map((await stationInput(request, sid, layer)).platforms.map((p) => [p.platform_id, p.name]));
  const got = Object.fromEntries([...name].map(([pid, n]) => [n, sg[pid] ?? 0]));
  for (const [n, want] of Object.entries(OLD_EASE_ALL_LINE_6))
    expect(Math.abs((got[n] ?? 0) - want), n).toBeLessThanOrEqual(0.05);
});

test("remove and restore: two clicks or two Deletes; Restore brings Ben's own level back (check 35)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "stdel");
  await openLine(page, request, "Line_3", layer);
  await pick(page, "Genesee");
  const bar = await selectedBar(page);
  await page.getByTestId("sp-remove").click();
  await expect(page.getByTestId("sp-remove")).toHaveText("Click again to remove");
  await edits(page, () => page.getByTestId("sp-remove").click());
  await expect(page.getByTestId("station-panel-hint")).toBeVisible();
  expect((await marks(page)).some((m) => m.kind === "bar" && m.id === bar.id)).toBe(false);
  const removed = page.getByTestId("removed-list").locator(`tr[data-platform="${bar.id}"]`);
  await expect(removed).toBeVisible();
  await edits(page, () => removed.getByRole("button", { name: "Restore" }).click());
  await pick(page, "Genesee");
  await expect(page.getByLabel("Genesee rail level")).toHaveValue("153.20");
  // Delete twice on the canvas does the same
  await canvas(page).focus();
  await page.keyboard.press("Delete");
  await edits(page, () => page.keyboard.press("Delete"));
  await expect(removed).toBeVisible();
  await undo(page);
  await expect(removed).toBeHidden();
});

test("a station with no level is a dashed bar marked level not set, with the default offered (check 9)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "stunset");
  await openLine(page, request, "Line_3", layer);
  await pick(page, "Ross");
  await edits(page, () => page.getByLabel("Ross rail level").fill(""));
  await expect.poll(async () => (await selectedBar(page)).unset).toBe(true);
  await expect(page.getByTestId("sp-flag-platform_level_unset")).toBeVisible();
  await page.keyboard.press("Escape");
  await edits(page, () => page.getByTestId("sp-set-default").click());
  await expect(page.getByLabel("Ross rail level")).toHaveValue((187 - 7.62).toFixed(2));
  expect((await selectedBar(page)).unset).toBe(false);
});

test("side or island: the box, D_HALL and the hall room follow it; saved on the platform record (S63)", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "stside");
  const { sid } = await openLine(page, request, "Line_3", layer);
  await pick(page, "Genesee");
  await edits(page, () => page.getByLabel("Genesee side or island").selectOption("side"));
  await expect(row(page, "hallroom")).toHaveText("needs 8.55 m of rail depth (side box); 13.60 here");
  const bar = await selectedBar(page);
  const box = (await marks(page)).find((m) => m.kind === "structure" && m.id === bar.id);
  expect(box?.top_m as number).toBeCloseTo((bar.z0 as number) + 4.6, 2);
  await page.keyboard.press("Control+s");
  await expect
    .poll(async () => (await stationInput(request, sid, layer)).platforms.find((p) => p.platform_id === bar.id)?.side)
    .toBe("side");
});

test("double-click inside a platform adds no bend point and says why (check 36)", async ({ page, request }) => {
  const layer = await scenario(request, "stdbl");
  await openLine(page, request, "Line_3", layer);
  await pick(page, "Genesee");
  const pvis = await page.getByTestId("pvi-table").locator("tr[data-index]").count();
  const bar = await selectedBar(page);
  const box = await canvas(page).boundingBox();
  if (!box) throw new Error("no canvas");
  await page.mouse.dblclick(box.x + ((bar.x0 as number) + (bar.x1 as number)) / 2, box.y + (bar.y0 as number) + 30);
  await expect(page.locator(".toast", { hasText: "Bend points go between platforms." })).toBeVisible();
  expect(await page.getByTestId("pvi-table").locator("tr[data-index]").count()).toBe(pvis);
});

test("on main, where the old hub owns the profile, every station input is disabled and a drag on a bar pans (check 38)", async ({
  page,
  request,
}) => {
  await openLine(page, request, "Line_3", "main");
  await pick(page, "Genesee");
  for (const label of ["rail level", "platform grade", "point from platform start", "station type", "access"])
    await expect(page.getByLabel(`Genesee ${label}`)).toBeDisabled();
  await expect(page.getByTestId("sp-remove")).toBeDisabled();
  await canvas(page).focus();
  for (let i = 0; i < 4; i++) await page.keyboard.press("+");
  const bar = await selectedBar(page);
  const box = await canvas(page).boundingBox();
  if (!box) throw new Error("no canvas");
  const x = box.x + ((bar.x0 as number) + (bar.x1 as number)) / 2;
  const y = box.y + (bar.y0 as number);
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 120, y + 40, { steps: 5 });
  await page.mouse.up();
  const moved = await selectedBar(page);
  expect((moved.x0 as number) - (bar.x0 as number)).toBeGreaterThan(80);
  expect(moved.z0).toBe(bar.z0);
  await expect(page.getByTestId("sheet-save")).toBeDisabled();
});

test("flags: the seed's slide errors, rule ids in the registry, and a click on a triangle selects its station (checks 39-42)", async ({
  page,
  request,
}) => {
  const registry = readFileSync(resolve(REPO, "rules", "registry.yaml"), "utf8");
  const slides: string[] = [];
  for (const route of ["Line_3", "Line_4", "Line_6", "Line_7"]) {
    const { sid } = await openLine(page, request, route, "main");
    const si = await stationInput(request, sid);
    const name = new Map(si.platforms.map((p) => [p.platform_id, p.name]));
    await canvas(page).focus();
    await page.keyboard.press("f");
    await page.waitForTimeout(150);
    const flags = (await marks(page)).filter((m) => m.kind === "flag");
    for (const f of flags) expect(registry, `rule ${f.rule}`).toContain(`id: ${f.rule}`);
    for (const f of flags) if (f.flag === "platform_slide_over") slides.push(`${route} ${name.get(f.id)}`);
    if (route === "Line_6") {
      // 42: a click on Forest's triangle selects Forest and centres on it, at most 1,500 m across
      const forest = si.platforms.find((p) => p.name === "Forest")?.platform_id;
      const t = flags.find((f) => f.id === forest) as Mark;
      const box = await canvas(page).boundingBox();
      if (!box) throw new Error("no canvas");
      await page.mouse.click(box.x + (t.x as number), box.y + (t.y as number));
      await expect(page.getByTestId("station-card-name")).toHaveText("Forest");
      const fr = await frame(page);
      expect(fr.c1 - fr.c0).toBeLessThanOrEqual(1500.5);
      await expect(page.getByTestId("sp-flag-platform_slide_over")).toContainText("Platform slid");
      await expect(page.getByTestId("sp-flag-platform_slide_over").getByRole("button")).toHaveText(
        "Slide back to 150 m",
      );
    }
  }
  // 40: the seed's platform slide errors
  expect(slides.sort()).toEqual(
    [
      "Line_3 Bruckman",
      "Line_4 Alliance Academy",
      "Line_4 Hoyes",
      "Line_6 Forest",
      "Line_6 North Avondale",
      "Line_6 Oak",
      "Line_7 Bank",
    ].sort(),
  );
});

test("keys: [ and ] step through the stations, Page Up tilts, E eases; the local solve stays under 16 ms", async ({
  page,
  request,
}) => {
  const layer = await scenario(request, "stkeys");
  await openLine(page, request, "Line_6", layer);
  await pick(page, "Bond Hill");
  await canvas(page).focus();
  await page.keyboard.press("]");
  await expect(page.getByTestId("station-card-name")).toHaveText("Chalet");
  await page.keyboard.press("[");
  await expect(page.getByTestId("station-card-name")).toHaveText("Bond Hill");
  const sg = page.getByLabel("Bond Hill platform grade");
  const sg0 = Number(await sg.inputValue());
  const rev = await solveRev(page);
  await edits(page, () => page.keyboard.press("PageUp"));
  const ms = await settled(page, rev);
  expect(ms).toBeLessThan(16);
  await expect(sg).toHaveValue((sg0 + 0.5).toFixed(1));
  await edits(page, () => page.keyboard.press("e"));
  await expect(canvas(page)).toHaveAttribute("data-easing", "0");
  await expect.poll(async () => sg.inputValue()).not.toBe((sg0 + 0.5).toFixed(1));
});
