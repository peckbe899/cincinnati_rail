import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { Relay } from "../../src/api/relay.ts";
import { SseParser } from "../../src/api/sse.ts";
import { EventClient, type FeedMessage } from "../../src/api/stream.ts";
import type { HubEvent } from "../../src/api/types.ts";
import { BASE, FakeHub } from "./fake_hub.ts";

let hub = new FakeHub();
const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  hub.closeStreams();
  server.resetHandlers();
});
afterAll(() => server.close());

async function until(pred: () => boolean, ms = 3000): Promise<void> {
  const t0 = Date.now();
  while (!pred()) {
    if (Date.now() - t0 > ms) throw new Error("timed out waiting");
    await new Promise((r) => setTimeout(r, 5));
  }
}

function collect(client: EventClient) {
  const events: HubEvent[] = [];
  const statuses: FeedMessage[] = [];
  client.subscribe((m) => (m.type === "event" ? events.push(m.event) : statuses.push(m)));
  return { events, statuses };
}

const rec = (data: Record<string, unknown>) => ({ kind: "profile", id: "P1", data });

describe("SSE client", () => {
  it("SSE client replays and resyncs", async () => {
    hub = new FakeHub();
    server.use(...hub.handlers());
    hub.seed(rec({ pvi: [] }));
    const client = new EventClient({
      url: `${BASE}/events`,
      clientId: "tab-test",
      minDelayMs: 5,
      maxDelayMs: 20,
      random: () => 0.5,
    });
    const { events, statuses } = collect(client);
    client.start();
    await until(() => hub.openStreams === 1 && statuses.some((s) => s.type === "status" && s.state === "open"));

    // Live events arrive in order, with their seq.
    hub.write("main", "profile", "P1", { pvi: [1] });
    hub.write("main", "profile", "P1", { pvi: [2] });
    await until(() => events.filter((e) => e.type === "record").length === 2);
    expect(events.filter((e) => e.type === "record").map((e) => e.seq)).toEqual([1, 2]);
    // The first connect sent no Last-Event-ID; the client header went with it.
    expect(hub.log[0]?.headers["last-event-id"]).toBeUndefined();
    expect(hub.log[0]?.headers["x-cr-client"]).toBe("tab-test");

    // A drop: an edit lands while the client is away; it reconnects with Last-Event-ID and gets it exactly once,
    // although the server replays from the event it already had.
    hub.closeStreams();
    hub.write("main", "profile", "P1", { pvi: [3] });
    await until(() => events.filter((e) => e.type === "record").length === 3);
    const reconnect = hub.log.filter((l) => l.url.endsWith("/events"))[1];
    expect(reconnect?.headers["last-event-id"]).toBe("2");
    expect(events.filter((e) => e.type === "record").map((e) => e.seq)).toEqual([1, 2, 3]);
    expect(
      statuses
        .filter((s) => s.type === "status" && s.state === "open")
        .map((s) => (s as { reconnected: boolean }).reconnected),
    ).toEqual([false, true]);
    expect(events.some((e) => e.type === "resync")).toBe(false);

    // Ephemeral events pass straight through.
    hub.broadcast(
      `event: job\ndata: ${JSON.stringify({ id: "j1", type: "noop", scope: "s", state: "running", progress: 0.5, msg: "" })}\n\n`,
    );
    await until(() => events.some((e) => e.type === "job"));

    // A server restart: a new epoch in the hello means the cursor is meaningless: one resync, reason epoch.
    hub.restart();
    await until(() => events.some((e) => e.type === "resync"));
    const resync = events.find((e) => e.type === "resync");
    expect(resync?.data).toEqual({ reason: "epoch", seq: 3 });
    expect(client.status().epoch).toBe("epoch-2");

    // Events the server pruned: it answers the stale Last-Event-ID with resync pruned, passed on once.
    hub.write("main", "profile", "P1", { pvi: [4] });
    await until(() => events.filter((e) => e.type === "record").length === 4);
    hub.pruned = 10;
    hub.write("main", "profile", "P1", { pvi: [5] });
    await until(() => events.filter((e) => e.type === "record").length === 5);
    hub.closeStreams();
    await until(() => events.filter((e) => e.type === "resync").length === 2);
    expect(events.filter((e) => e.type === "resync").map((e) => (e.data as { reason: string }).reason)).toEqual([
      "epoch",
      "pruned",
    ]);
    expect(client.seq).toBe(5);
    client.stop();
    expect(client.status().state).toBe("closed");
  });

  it("backs off while the server is down and folds a second resync into the first", async () => {
    hub = new FakeHub();
    let fails = 3;
    const { http, HttpResponse } = await import("msw");
    server.use(
      http.get(`${BASE}/events`, () => {
        if (fails-- > 0) return new HttpResponse(null, { status: 503 });
        return undefined;
      }),
      ...hub.handlers(),
    );
    const client = new EventClient({
      url: `${BASE}/events`,
      minDelayMs: 5,
      maxDelayMs: 40,
      random: () => 0.5,
      epoch: "epoch-0",
      lastEventId: 0,
    });
    const { events, statuses } = collect(client);
    client.start();
    await until(() => statuses.some((s) => s.type === "status" && s.state === "open"));
    expect(statuses.filter((s) => s.type === "status" && s.error).length).toBe(3);
    // The hello's epoch differs from the one the tab knew: one resync, and a server resync right after is folded.
    hub.broadcast(`event: resync\ndata: ${JSON.stringify({ reason: "pruned", seq: 0 })}\n\n`);
    await new Promise((r) => setTimeout(r, 30));
    expect(events.filter((e) => e.type === "resync").length).toBe(1);
    client.stop();
  });
});

describe("SSE poll fallback", () => {
  it("polls when the stream has no body, and a new epoch while polling is a resync", async () => {
    const answers = [
      { epoch: "p1", seq: 5, events: [] },
      { epoch: "p1", seq: 6, events: [{ seq: 6, type: "record", data: { kind: "profile", id: "P1", version: 2 } }] },
      { epoch: "p2", seq: 1, events: [] },
    ];
    const polled: string[] = [];
    const fetchFn = (async (url: string) => {
      if (url.endsWith("/events")) return new Response(null, { status: 200 });
      polled.push(url);
      return Response.json(answers[Math.min(polled.length - 1, answers.length - 1)]);
    }) as unknown as typeof fetch;
    const client = new EventClient({ url: `${BASE}/events`, fetch: fetchFn, pollMs: 5, minDelayMs: 5 });
    const { events } = collect(client);
    client.start();
    await until(() => events.some((e) => e.type === "resync"));
    client.stop();
    expect(events.filter((e) => e.type === "record").map((e) => e.seq)).toEqual([6]);
    expect(events.find((e) => e.type === "resync")?.data).toEqual({ reason: "epoch", seq: 1 });
    expect(polled[0]).toMatch(/\/events\/poll\?since=0$/);
    expect(polled[1]).toMatch(/since=5$/);
    expect(client.status().epoch).toBe("p2");
  });
});

describe("SSE parser", () => {
  it("handles any chunking, CRLF, comments, multi-line data and ids", () => {
    const text =
      ': hi\r\nid: 7\r\nevent: record\r\ndata: {"a":\r\ndata: 1}\r\n\r\nretry: 900\nevent: job\ndata: {}\n\n';
    for (const size of [1, 2, 3, 7, text.length]) {
      const p = new SseParser();
      const out = [];
      for (let i = 0; i < text.length; i += size) out.push(...p.push(text.slice(i, i + size)));
      expect(out).toEqual([
        { id: "7", event: "record", data: '{"a":\n1}' },
        { id: "7", event: "job", data: "{}" },
      ]);
      expect(p.retry).toBe(900);
    }
  });
});

describe("SharedWorker relay", () => {
  it("shares one client, greets late tabs with the status, and stops with the last tab", () => {
    const made: { started: number; stopped: number; sub: ((m: FeedMessage) => void) | null }[] = [];
    const relay = new Relay(() => {
      const fake = { started: 0, stopped: 0, sub: null as ((m: FeedMessage) => void) | null };
      made.push(fake);
      return {
        subscribe: (fn: (m: FeedMessage) => void) => {
          fake.sub = fn;
          return () => {};
        },
        start: () => fake.started++,
        stop: () => fake.stopped++,
        reconnect: () => {},
      } as unknown as EventClient;
    });
    const port = () => {
      const got: unknown[] = [];
      return { got, postMessage: (m: unknown) => got.push(m), onmessage: null as ((e: MessageEvent) => void) | null };
    };
    const a = port();
    const b = port();
    relay.connect(a);
    relay.receive(a, { type: "start", options: { url: "/api/v1/events" } });
    const status: FeedMessage = {
      type: "status",
      state: "open",
      reconnected: false,
      epoch: "e",
      seq: 1,
      engine_build: null,
    };
    made[0]?.sub?.(status);
    relay.connect(b);
    relay.receive(b, { type: "start", options: { url: "/api/v1/events" } });
    expect(made.length).toBe(1);
    expect(b.got[0]).toEqual(status);
    const ev: FeedMessage = {
      type: "event",
      event: { type: "tier", seq: null, data: { tier: "deck", status: "present", detail: "" } },
    };
    made[0]?.sub?.(ev);
    expect(a.got).toContainEqual(ev);
    expect(b.got).toContainEqual(ev);
    relay.receive(a, { type: "bye" });
    expect(made[0]?.stopped).toBe(0);
    // A tab back from the back/forward cache says start again on the same port, and gets events again.
    relay.receive(a, { type: "start", options: { url: "/api/v1/events" } });
    const again: FeedMessage = {
      type: "event",
      event: { type: "tier", seq: null, data: { tier: "deck", status: "missing", detail: "" } },
    };
    made[0]?.sub?.(again);
    expect(a.got).toContainEqual(again);
    expect(made.length).toBe(1);
    relay.receive(a, { type: "bye" });
    relay.receive(b, { type: "bye" });
    expect(made[0]?.stopped).toBe(1);
  });
});
