// @vitest-environment happy-dom
// @vitest-environment-options {"url": "http://hub.test/w/design"}
// I2.1 on the mounted line sheet: it asks the run of the section's route (railsim.run, scope the route named by the
// section record, priority 2 with the watch), shows the run-time card, posts a draft run of an edit once the edit's
// solve has landed and 300 ms have passed (with the draft's SectionInput, on the saved structure when the hub gave
// no whole-solve input), shows the draft with its change, and goes back to the saved run with no new request when
// the edit is undone to the record. A result event of the route's run reads it again; closing the sheet sends the
// run to the back (9).

import { readFileSync } from "node:fs";
import { URL as NodeURL } from "node:url";
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
import { mountSheet } from "../../src/plugins/line-sheet/pane.ts";
import { BASE, FakeHub } from "./fake_hub.ts";

const RAW = JSON.parse(readFileSync(new NodeURL("./fixtures/run_result_line6.json", import.meta.url), "utf-8")) as {
  key: string;
  meta: Record<string, unknown> & { directions: { trip_s: number; stations: { arrive_s: number }[] }[] };
  arrays: Record<string, string>;
};

const hub = new FakeHub();
const INPUT: SectionInput = {
  contract: "section_input/0",
  section_id: "SEC6",
  length_m: 29539.6,
  chainage_basis: "grid:26916",
  scale: 1,
  step_m: 2,
  params: { platform_m: 120, vc_radius_m: 1500, vc_min_len_m: 30 },
  stations: [
    { platform_id: "PA", order: 0, c_m: 60.5, level_m: null, grade_permille: null },
    { platform_id: "PB", order: 1, c_m: 29521.6, level_m: null, grade_permille: null },
  ],
  pvi: [{ c_m: 5000, z_m: 160 }],
};
const computes: Record<string, unknown>[] = [];
const focuses: Record<string, unknown>[] = [];
const drafts: Record<string, unknown>[] = [];
const draftAnswer = () => {
  const m = JSON.parse(JSON.stringify(RAW.meta)) as typeof RAW.meta;
  const d0 = m.directions[0] as (typeof m.directions)[number];
  d0.trip_s += 12;
  for (const s of d0.stations.slice(1)) s.arrive_s += 12;
  return {
    ...m,
    draft: true,
    key: "draft1",
    cached: false,
    ms: 300,
    types: "saved",
    base: {},
    edit_rev: 1,
    arrays: {},
  };
};
const server = setupServer(
  ...hub.handlers(),
  http.get(`${BASE}/x/profiles/sections/:id/input`, () => HttpResponse.json(INPUT)),
  // no station or whole-solve input on this fake: the draft runs on the saved structure (type_runs null)
  http.get(`${BASE}/x/profiles/sections/:id/stations`, () => HttpResponse.json({}, { status: 404 })),
  http.get(`${BASE}/x/profiles/sections/:id/solve`, () => HttpResponse.json({}, { status: 404 })),
  http.get(`${BASE}/results`, () => HttpResponse.json({ key: null })),
  http.get(`${BASE}/results/:key`, ({ params }) =>
    HttpResponse.json({
      key: params.key,
      type: "railsim.run",
      scope: "R6",
      view: "main|-|canon",
      status: "ok",
      meta: RAW.meta,
    }),
  ),
  http.get(`${BASE}/results/:key/a/:name`, ({ params }) => {
    const b64 = RAW.arrays[String(params.name)] ?? "";
    const bytes = Buffer.from(b64, "base64");
    return new HttpResponse(bytes, { headers: { "X-Dtype": "<f4", "X-Shape": String(bytes.length / 4) } });
  }),
  http.get(`${BASE}/k/:kind`, () => HttpResponse.json({ items: [], next: null })),
  http.post(`${BASE}/compute`, async ({ request }) => {
    const b = (await request.json()) as Record<string, unknown>;
    computes.push(b);
    if (b.type === "railsim.run") return HttpResponse.json({ key: RAW.key, state: "hit", job: null });
    return HttpResponse.json({ key: "k1", state: "queued", job: "j1" });
  }),
  http.post(`${BASE}/live/focus`, async ({ request }) => {
    focuses.push((await request.json()) as Record<string, unknown>);
    return HttpResponse.json({});
  }),
  http.post(`${BASE}/x/railsim/sections/:id/draft`, async ({ request }) => {
    drafts.push((await request.json()) as Record<string, unknown>);
    return HttpResponse.json(draftAnswer());
  }),
);
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(async () => {
  await new Promise((r) => setTimeout(r, 300));
  server.close();
});

const subs = new Set<(m: FeedMessage) => void>();
function feed(): EventFeed {
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
const emit = (type: string, scope: string, key: string, view = "main|-|canon") => {
  for (const fn of subs)
    fn({
      type: "event",
      event: { type: "result", seq: null, data: { key, type, scope, view, status: "ok", changed: [] } },
    });
};

function makeHost(url: string) {
  return new AppHost({
    registry: discover(),
    api: new Api({ base: BASE, clientId: "tab-runs" }),
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

const ctxOf = (host: AppHost): PaneContext => ({
  host,
  params: {},
  state: undefined,
  setTitle: () => {},
  onResize: () => ({ dispose: () => {} }),
});
async function until(pred: () => boolean, ms = 3000): Promise<void> {
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

describe("run times on the mounted sheet", () => {
  it("asks the route's run, shows it, runs a draft of an edit and goes back to the saved run on undo", async () => {
    hub.seed({ kind: "section", id: "SEC6", data: { route: "R6", length_m: 29539.6, step_m: 2 } });
    const prof = hub.seed({ kind: "profile", id: "PR6", data: { section: "SEC6", pvi: [[5000, 160]] } });
    const host = makeHost("/w/design?layer=main&sel=profile:PR6");
    const el = document.createElement("div");
    document.body.append(el);
    mounted = await mountSheet(el, ctxOf(host));
    const card = () => el.querySelector('[data-testid="sheet-runs"]') as HTMLElement;
    await until(() => !!card()?.textContent?.includes("Towne to Beechgrove"));
    const ask = computes.find((c) => c.type === "railsim.run");
    expect(ask).toMatchObject({ scope: "R6", view: "main|-|canon", priority: 2, watch_s: 600 });
    expect(card().querySelector('[data-testid="run-totals"]')?.textContent).toContain("Trip 50:35");
    expect(drafts).toHaveLength(0);

    // an edit: the draft run goes once its rail solve has landed and the 300 ms have passed
    const view = host.view();
    host.drafts.edit(prof, view, [{ op: "replace", path: "/data/pvi/0/1", value: 162 }]);
    await tick(150);
    expect(drafts).toHaveLength(0);
    await until(() => drafts.length === 1);
    const body = drafts[0] as { section_input: { section_id: string; pvi: unknown[] }; type_runs: unknown };
    expect(body.section_input.section_id).toBe("SEC6");
    expect(body.section_input.pvi).toEqual([{ c_m: 5000, z_m: 162 }]);
    expect(body.type_runs).toBeNull();
    await until(() => !!card().textContent?.includes("Trip 50:47 (+0:12)"));
    expect(card().textContent).toContain("draft");

    // undone to the record: the saved run, no new run asked
    const n = computes.length;
    host.drafts.drop(host.drafts.key("profile", "PR6", view));
    await until(() => !card().textContent?.includes("+0:12"), 3000);
    expect(card().querySelector('[data-testid="run-totals"]')?.textContent).toContain("Trip 50:35");
    expect(drafts).toHaveLength(1);
    expect(computes.filter((c) => c.type === "railsim.run").length).toBe(
      computes.slice(0, n).filter((c) => c.type === "railsim.run").length,
    );

    // a new saved run arrives over SSE; another route's is not read
    emit("railsim.run", "R9", "other");
    emit("railsim.run", "R6", "run2");
    await tick(100);
    mounted.dispose();
    mounted = null;
    await until(() => focuses.some((f) => f.type === "railsim.run" && f.priority === 9));
    host.dispose();
  });
});
