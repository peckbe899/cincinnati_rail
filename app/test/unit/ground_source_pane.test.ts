// @vitest-environment happy-dom
// @vitest-environment-options {"url": "http://hub.test/w/design"}
// I2.1: while the hub is still sampling the ground model for a line whose ground.source is region, the section's
// input says "line_file (region pending)". The sheet then reads its input again when the ground.profile result of
// that section in its view lands (and so does a line on the ground model, whose ground can change with a works file);
// a result for another line or view, or a line on the line file's ground, reads nothing.

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

const hub = new FakeHub();
const INPUT: SectionInput = {
  contract: "section_input/0",
  section_id: "SEC7",
  length_m: 1000,
  chainage_basis: "grid:26916",
  scale: 1,
  step_m: 2,
  params: { platform_m: 120, vc_radius_m: 1500, vc_min_len_m: 30 },
  stations: [
    { platform_id: "PA", order: 0, c_m: 100, level_m: null, grade_permille: null },
    { platform_id: "PB", order: 1, c_m: 900, level_m: null, grade_permille: null },
  ],
  pvi: [{ c_m: 500, z_m: 205 }],
};
let ground = "line_file (region pending)";
let reads = 0;
const server = setupServer(
  ...hub.handlers(),
  http.get(`${BASE}/x/profiles/sections/:id/input`, () => {
    reads += 1;
    return HttpResponse.json(INPUT, { headers: { "X-CR-Ground": ground } });
  }),
  http.get(`${BASE}/results`, () => HttpResponse.json({ key: null })),
  http.get(`${BASE}/k/:kind`, () => HttpResponse.json({ items: [], next: null })),
  http.post(`${BASE}/compute`, () => HttpResponse.json({ key: "k1", state: "queued", job: "j1" })),
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
const emit = (type: string, scope: string, view = "main|-|canon") => {
  for (const fn of subs)
    fn({
      type: "event",
      event: { type: "result", seq: null, data: { key: "g1", type, scope, view, status: "ok", changed: [] } },
    });
};

function makeHost(url: string) {
  return new AppHost({
    registry: discover(),
    api: new Api({ base: BASE, clientId: "tab-ground" }),
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

describe("the line sheet and a pending ground model", () => {
  it("reads its input again when its section's ground lands, and not otherwise", async () => {
    hub.seed({ kind: "profile", id: "PR7", data: { section: "SEC7", pvi: [[500, 205]] } });
    const host = makeHost("/w/design?layer=main&sel=profile:PR7");
    const el = document.createElement("div");
    document.body.append(el);
    mounted = await mountSheet(el, ctxOf(host));
    await until(() => reads > 0 && host.api.groundSource("SEC7", host.view()) !== null);
    await tick(50);
    const first = reads;
    // another line's ground, this line's ground in another view, another job: nothing read
    emit("ground.profile", "SEC9");
    emit("ground.profile", "SEC7", "try|-|canon");
    emit("profiles.station_facts", "SEC7");
    await tick(100);
    expect(reads).toBe(first);
    // this line's ground in this view: the input again, now on the ground model
    ground = "region";
    emit("ground.profile", "SEC7");
    await until(() => reads > first);
    await until(() => host.api.groundSource("SEC7", host.view()) === "region");
    // on the ground model a newer ground (a works file changed) is read again too; back on the line file, with
    // its ground as it was, a ground result reads nothing
    ground = "line_file";
    emit("ground.profile", "SEC7");
    await until(() => host.api.groundSource("SEC7", host.view()) === "line_file");
    await tick(50);
    const third = reads;
    emit("ground.profile", "SEC7");
    await tick(100);
    expect(reads).toBe(third);
    host.dispose();
  });
});
