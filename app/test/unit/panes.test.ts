// @vitest-environment happy-dom
// @vitest-environment-options {"url": "http://hub.test/w/design"}
// The inspector and line sheet panes against the fake hub: what Ben's clicks and keystrokes write.

import type { SectionInput } from "@cr/engine/contract";
import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { Api } from "../../src/api/client.ts";
import type { EventFeed, FeedMessage } from "../../src/api/events.ts";
import { AppHost } from "../../src/core/host.ts";
import type { MountedPane, PaneContext } from "../../src/core/plugin.ts";
import { discover } from "../../src/core/registry.ts";
import { createAppStore } from "../../src/core/store.ts";
import { parseUrl } from "../../src/core/url.ts";
import { createEngine } from "../../src/engine/client.ts";
import { mountInspector } from "../../src/plugins/inspector/pane.ts";
import { mountSheet } from "../../src/plugins/line-sheet/pane.ts";
import { BASE, FakeHub } from "./fake_hub.ts";

const hub = new FakeHub();
const computes: unknown[] = [];
const INPUT: SectionInput = {
  contract: "section_input/0",
  section_id: "SEC6",
  length_m: 1000,
  chainage_basis: "grid:26916",
  scale: 1,
  step_m: 2,
  params: { platform_m: 120, vc_radius_m: 1500, vc_min_len_m: 30 },
  stations: [
    { platform_id: "PA", order: 0, c_m: 100, level_m: null, grade_permille: null },
    { platform_id: "PB", order: 1, c_m: 900, level_m: null, grade_permille: null },
  ],
  pvi: [
    { c_m: 300, z_m: 200 },
    { c_m: 500, z_m: 205 },
    { c_m: 700, z_m: 210 },
  ],
};
const server = setupServer(
  ...hub.handlers(),
  http.get(`${BASE}/x/profiles/sections/:id/input`, () => HttpResponse.json(INPUT)),
  http.get(`${BASE}/results`, () => HttpResponse.json({ key: null })),
  // The sheet reads the section's stops and platforms and main's authority records; this fake has none of them.
  http.get(`${BASE}/k/:kind`, () => HttpResponse.json({ items: [], next: null })),
  http.post(`${BASE}/compute`, async ({ request }) => {
    computes.push(await request.json());
    return HttpResponse.json({ key: "k1", state: "queued", job: "j1" });
  }),
);
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
// Names are read in the background (host.names) and may still be on their way when a test ends: let them land
// before the fake hub goes, so none of them reaches the real network.
afterAll(async () => {
  await new Promise((r) => setTimeout(r, 300));
  server.close();
});

function feed(): EventFeed {
  const subs = new Set<(m: FeedMessage) => void>();
  return {
    shared: false,
    subscribe: (fn) => {
      subs.add(fn);
      return () => subs.delete(fn);
    },
    status: () => ({ type: "status", state: "open", reconnected: false, epoch: "e", seq: 0, engine_build: null }),
    reconnect: () => {},
    close: () => {},
  };
}

function makeHost(url: string) {
  return new AppHost({
    registry: discover(),
    api: new Api({ base: BASE, clientId: "tab-panes" }),
    store: createAppStore(parseUrl(url)),
    events: feed(),
    engine: createEngine({
      makeWorker: () => null,
      inline: async () => ({
        hello: async () => ({ engine_version: "0", methods: ["vertical.rail@1"], contracts: {} }),
        solve: async () => ({ result: { rail_m: [], grade_permille: [], grid: { c0: 0, step_m: 2, n: 0 } }, ms: 0 }),
      }),
    }),
  });
}

function ctxOf(host: AppHost): PaneContext {
  return { host, params: {}, state: undefined, setTitle: () => {}, onResize: () => ({ dispose: () => {} }) };
}

async function until(pred: () => boolean, ms = 2000): Promise<void> {
  const t0 = Date.now();
  while (!pred()) {
    if (Date.now() - t0 > ms) throw new Error("timed out waiting");
    await new Promise((r) => setTimeout(r, 5));
  }
}

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms));

let mounted: MountedPane | null = null;
afterEach(() => {
  mounted?.dispose();
  mounted = null;
  document.body.replaceChildren();
});

describe("inspector pane", () => {
  it("draws the form once, and redraws at once after a structural edit from a focused button", async () => {
    hub.kinds.note = {
      kind: "note",
      version: 1,
      schema: { type: "object", properties: { tags: { type: "array", items: { type: "string" } } } },
    };
    hub.seed({ kind: "note", id: "N9", data: { tags: ["a", "b", "c"] } });
    const host = makeHost("/w/design?layer=main&sel=note:N9");
    // Another pane has read the record already, so the inspector finds it in the cache.
    await host.records.get("note", "N9", host.view());
    const el = document.createElement("div");
    document.body.append(el);
    mounted = await mountInspector(el, ctxOf(host));
    await until(() => el.querySelectorAll(".form").length > 0);
    await tick(50);
    expect(el.querySelectorAll(".form").length).toBe(1);

    // Remove the first tag: the clicked button keeps the focus, and the form must still follow the draft, so the
    // next click removes what it shows.
    const minus = () => [...el.querySelectorAll("button")].filter((b) => b.textContent === "−");
    const first = minus()[0] as HTMLButtonElement;
    first.focus();
    first.click();
    await until(() => minus().length === 2, 1000);
    const draft = host.drafts.get("note", "N9", host.view());
    expect(draft?.body.data).toEqual({ tags: ["b", "c"] });
    const second = minus()[1] as HTMLButtonElement;
    second.focus();
    second.click();
    await until(() => minus().length === 1, 1000);
    expect(host.drafts.get("note", "N9", host.view())?.body.data).toEqual({ tags: ["b"] });
    host.dispose();
  });
});

describe("line sheet pane", () => {
  it("edits the PVI it shows, keeps every station level typed, and asks the hub to solve", async () => {
    hub.seed({
      kind: "profile",
      id: "PR6",
      data: {
        section: "SEC6",
        pvi: [
          [300, 200],
          [500, 205],
          [700, 210],
        ],
      },
    });
    const host = makeHost("/w/design?layer=main&sel=profile:PR6");
    const el = document.createElement("div");
    document.body.append(el);
    mounted = await mountSheet(el, ctxOf(host));
    const cell = (label: string) => el.querySelector(`input[aria-label="${label}"]`) as HTMLInputElement | null;
    await until(() => cell("PVI 3 level") !== null);
    // Opening the section asks for its solve in this view.
    await until(() => computes.length > 0);
    expect(computes[0]).toMatchObject({ type: "profiles.solve_section", scope: "SEC6", view: "main|-|canon" });

    // Remove the first PVI with the button focused: the table rebuilds, so row 2 is now the old third PVI.
    const rm = el.querySelector('tr[data-index="0"] button') as HTMLButtonElement;
    rm.focus();
    rm.click();
    await until(() => cell("PVI 3 level") === null);
    const z2 = cell("PVI 2 level") as HTMLInputElement;
    expect(z2.value).toBe("210");
    z2.focus();
    z2.value = "211";
    z2.dispatchEvent(new Event("input"));
    const key = host.drafts.key("profile", "PR6", host.view());
    expect(host.drafts.byKey(key)?.body.data.pvi).toEqual([
      [500, 205],
      [700, 211],
    ]);

    // Two station levels typed one after the other (the table is not rebuilt while a cell has the focus): the
    // second must not drop the first.
    const pa = cell("Station PA level") as HTMLInputElement;
    pa.focus();
    pa.value = "201";
    pa.dispatchEvent(new Event("input"));
    const pb = cell("Station PB level") as HTMLInputElement;
    pb.focus();
    pb.value = "202";
    pb.dispatchEvent(new Event("input"));
    expect(host.drafts.byKey(key)?.body.data.st).toEqual({ PA: 201, PB: 202 });
    // Clearing a level typed in this draft takes it out again.
    pb.value = "";
    pb.dispatchEvent(new Event("input"));
    expect(host.drafts.byKey(key)?.body.data.st).toEqual({ PA: 201 });
    host.dispose();
  });
});
