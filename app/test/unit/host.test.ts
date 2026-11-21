import { setupServer } from "msw/node";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { Api } from "../../src/api/client.ts";
import type { EventFeed, FeedMessage } from "../../src/api/events.ts";
import { AppHost, type UiMessage } from "../../src/core/host.ts";
import { discover } from "../../src/core/registry.ts";
import { createAppStore } from "../../src/core/store.ts";
import { parseUrl } from "../../src/core/url.ts";
import { unavailableEngine } from "../../src/engine/client.ts";
import { BASE, FakeHub } from "./fake_hub.ts";

const hub = new FakeHub();
const server = setupServer(...hub.handlers());
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());

function feed(): EventFeed & { push(m: FeedMessage): void } {
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
    push: (m) => {
      for (const fn of subs) fn(m);
    },
  };
}

function makeHost(url: string) {
  const events = feed();
  const host = new AppHost({
    registry: discover(),
    api: new Api({ base: BASE, clientId: "tab-host" }),
    store: createAppStore(parseUrl(url)),
    events,
    engine: unavailableEngine("not in this test"),
  });
  const ui: UiMessage[] = [];
  host.ui.on((m) => ui.push(m));
  return { host, events, ui };
}

async function until(pred: () => boolean): Promise<void> {
  for (let i = 0; i < 200 && !pred(); i++) await new Promise((r) => setTimeout(r, 5));
  expect(pred()).toBe(true);
}

describe("host", () => {
  it("resolves an old key in the URL to its record, without a history step", async () => {
    const { host } = makeHost("/w/design?route=Line_6");
    expect(host.store.getState().sel).toEqual({ legacy: { lkind: "route", key: "Line_6" } });
    host.activate();
    await until(() => JSON.stringify(host.store.getState().sel) === JSON.stringify({ kind: "section", id: "SEC6" }));
    expect(host.store.lastNav).toBe("replace");
    host.dispose();
  });

  it("warns about an old key with no record, and opens the panes that take a selection", async () => {
    const { host, ui } = makeHost("/w/design?sel=legacy/route/Line_99");
    host.activate();
    await until(() => ui.some((m) => m.type === "toast" && m.toast.text.includes("Line_99")));
    host.select({ kind: "profile", id: "P1" });
    const opened = ui.filter((m) => m.type === "open").map((m) => (m as { pane: string }).pane);
    expect(opened.sort()).toEqual(["inspector", "line-sheet"]);
    expect(host.store.getState().sel).toEqual({ kind: "profile", id: "P1" });
    host.dispose();
  });

  it("feeds events into the record cache and shows the connection in the status bar", async () => {
    const { host, events, ui } = makeHost("/w/design");
    events.push({
      type: "status",
      state: "connecting",
      reconnected: false,
      epoch: null,
      seq: null,
      engine_build: null,
    });
    expect(host.statusItems.get("core.events")?.text).toBe("events: connecting");
    events.push({ type: "event", event: { type: "resync", seq: 5, data: { reason: "epoch", seq: 5 } } });
    expect(ui.some((m) => m.type === "toast" && m.toast.text.includes("resync (epoch)"))).toBe(true);
    host.dispose();
  });
});
