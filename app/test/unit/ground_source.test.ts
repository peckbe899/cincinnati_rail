// @vitest-environment happy-dom
// I2.1: the ground the profiles read is the param ground.source (the line file's survey, or the ground model at the
// view's year and timeline). The hub says which in the header X-CR-Ground of the section's input; the client keeps
// it per section and view, and the station panel's "Ground at centre" row names it where it already said "survey".

import { describe, expect, it } from "vitest";
import { Api } from "../../src/api/client.ts";
import { Units } from "../../src/core/units.ts";
import { makeView } from "../../src/core/view.ts";
import { buildPanel, groundSourceText, type PanelCtx } from "../../src/plugins/line-sheet/panel.ts";
import { fact } from "./fixtures/station_fact.ts";

const BASE = "http://hub.test/api/v1";
/** A hub answering the section input with the given X-CR-Ground (none when null). */
let ground: string | null = null;
const fetchStub = (async (url: string) => {
  expect(String(url)).toContain(`${BASE}/x/profiles/sections/S1/input`);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (ground !== null) headers["X-CR-Ground"] = ground;
  return new Response(JSON.stringify({ contract: "section_input/0", section_id: "S1" }), { status: 200, headers });
}) as unknown as typeof fetch;
const answer = (g: string | null) => {
  ground = g;
};

describe("the ground source over the API", () => {
  it("is kept per section and view from the section input's header", async () => {
    const api = new Api({ base: BASE, clientId: "tab-g", fetch: fetchStub });
    const main = makeView({ layer: "main" });
    const tryV = makeView({ layer: "try" });
    expect(api.groundSource("S1", main)).toBeNull();
    answer("line_file");
    await api.sectionInput("S1", main);
    expect(api.groundSource("S1", main)).toBe("line_file");
    expect(api.groundSource("S1", tryV)).toBeNull();
    answer("region");
    await api.sectionInput("S1", tryV);
    expect(api.groundSource("S1", tryV)).toBe("region");
    expect(api.groundSource("S1", main)).toBe("line_file");
    // a hub that does not say (an older one): unknown, not a guess
    answer(null);
    await api.sectionInput("S1", main);
    expect(api.groundSource("S1", main)).toBeNull();
  });
});

describe("the ground source in plain words", () => {
  it("names the survey, the ground model, a pending model and gaps filled from it", () => {
    expect(groundSourceText(null, false).text).toBe("survey");
    expect(groundSourceText("line_file", false).text).toBe("survey");
    expect(groundSourceText("line_file", true).text).toBe("finished ground");
    expect(groundSourceText("region", false).text).toBe("ground model");
    expect(groundSourceText("region", true).text).toBe("finished ground, ground model");
    expect(groundSourceText("line_file (region pending)", false).text).toBe("survey (ground model pending)");
    expect(groundSourceText("line_file (gaps from region)", false).text).toBe("survey, gaps from ground model");
    for (const s of [null, "line_file", "region", "line_file (region pending)", "line_file (gaps from region)"]) {
      const t = groundSourceText(s, false);
      expect(t.title).toBeTruthy();
      expect(`${t.text} ${t.title}`).not.toMatch(/\u2014/); // no long dashes in UI text
    }
    expect(groundSourceText("region", false).title).toMatch(/year and timeline/);
    expect(groundSourceText("line_file", false).title).toMatch(/line file/);
  });

  const ctx = (groundSource?: string | null): PanelCtx => ({
    units: new Units("m"),
    pid: "P1",
    name: "Towne",
    line: "Line 6",
    index: 0,
    count: 2,
    half: 60,
    fact: fact({}),
    params: null,
    paramPrefix: "settings",
    metro: true,
    draft: {},
    saved: {},
    savedBy: "import:old_hub",
    point: 1000,
    centre: 1000,
    rail: 150,
    ground: 163.6,
    groundDem: 163.6,
    groundSource,
    gradeIn: 0,
    gradeOut: 0,
    side: { now: "side", was: "side", source: "old hub" },
    canEdit: true,
    canEditSide: true,
    readOnly: null,
    act: new Proxy({}, { get: () => () => {} }) as PanelCtx["act"],
  });
  const groundRow = (p: HTMLElement) => p.querySelector("[data-testid=sp-ground] .sp-src") as HTMLElement;

  it("the station panel's ground row says which ground it is", () => {
    expect(groundRow(buildPanel(ctx())).textContent).toBe("survey");
    expect(groundRow(buildPanel(ctx("line_file"))).textContent).toBe("survey");
    const r = groundRow(buildPanel(ctx("region")));
    expect(r.textContent).toBe("ground model");
    expect(r.title).toMatch(/year and timeline/);
  });
});
