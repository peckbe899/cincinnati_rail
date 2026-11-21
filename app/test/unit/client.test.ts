import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { Api, ApiError, etagOf } from "../../src/api/client.ts";
import { normaliseList, normaliseMeta } from "../../src/api/normalise.ts";
import { makeView } from "../../src/core/view.ts";
import { BASE, FakeHub } from "./fake_hub.ts";

const hub = new FakeHub();
const server = setupServer(...hub.handlers());
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => server.resetHandlers(...hub.handlers()));
afterAll(() => server.close());

describe("API transport", () => {
  it("If-Match sent and 304 used", async () => {
    hub.seed({ kind: "profile", id: "P1", data: { pvi: [[0, 200]], st: {} } });
    const api = new Api({ base: BASE, clientId: "tab-abcd" });
    const view = makeView({ layer: "main" });

    // First read: 200 with the ETag; second: If-None-Match goes out, the 304 reuses the body.
    const a = await api.getRecord("profile", "P1", view);
    const b = await api.getRecord("profile", "P1", view);
    expect(b).toEqual(a);
    const gets = hub.log.filter((l) => l.method === "GET" && l.url.includes("/k/profile/P1"));
    expect(gets.map((g) => g.status)).toEqual([200, 304]);
    expect(gets[0]?.headers["if-none-match"]).toBeUndefined();
    expect(gets[1]?.headers["if-none-match"]).toBe('"main:1"');
    // Every request names the tab.
    expect(gets.every((g) => g.headers["x-cr-client"] === "tab-abcd")).toBe(true);

    // A write sends If-Match, X-CR-Client and the JSON Patch content type.
    const saved = await api.patch(
      "profile",
      "P1",
      [{ op: "replace", path: "/data/pvi/0/1", value: 201 }],
      view,
      etagOf(a),
    );
    expect(saved.version).toBe(2);
    const patch = hub.log.find((l) => l.method === "PATCH");
    expect(patch?.headers["if-match"]).toBe('"main:1"');
    expect(patch?.headers["content-type"]).toBe("application/json-patch+json");
    expect(patch?.headers["x-cr-client"]).toBe("tab-abcd");

    // The next read sees the new version (the old ETag no longer matches, so 200 again).
    const c = await api.getRecord("profile", "P1", view);
    expect(c.version).toBe(2);
    expect(hub.log.filter((l) => l.method === "GET" && l.url.includes("/k/profile/P1")).at(-1)?.status).toBe(200);

    // A stale If-Match is a 412 ApiError carrying the problem body; a missing one is 428.
    const stale = await api.patch("profile", "P1", [], view, '"main:1"').catch((e: unknown) => e);
    expect(stale).toBeInstanceOf(ApiError);
    expect((stale as ApiError).status).toBe(412);
    expect((stale as ApiError).problem.current?.version).toBe(2);
    expect((stale as ApiError).requestId).toBe("req-412");
    const missing = await api
      .send("PATCH", "/k/profile/P1", { json: [], contentType: "application/json-patch+json" })
      .catch((e: unknown) => e);
    expect((missing as ApiError).status).toBe(428);
    expect((missing as ApiError).code).toBe("precondition_required");
  });

  it("maps a 404 legacy key to null and a dead server to a network error", async () => {
    const api = new Api({ base: BASE });
    expect(await api.legacy("route", "Line_6")).toEqual({ kind: "section", id: "SEC6" });
    expect(await api.legacy("route", "Line_99")).toBeNull();
    const dead = new Api({ base: BASE, fetch: () => Promise.reject(new TypeError("fetch failed")) });
    const e = (await dead.health().catch((x: unknown) => x)) as ApiError;
    expect(e.status).toBe(0);
    expect(e.code).toBe("network");
  });

  it("normalises the server's container shapes", () => {
    expect(normaliseList([{ id: "a" }]).items.length).toBe(1);
    expect(normaliseList({ items: [{ id: "a" }], next: "a" })).toEqual({ items: [{ id: "a" }], next: "a" });
    expect(normaliseList({ records: [], after: null }).next).toBeNull();
    const m = normaliseMeta({
      kinds: [{ kind: "note", version: 1, schema: { type: "object" }, legacy: ["note_key"] }],
      layers: ["main", "import:profiles", "try"],
      engine: { hello: { engine_build: "x" } },
      epoch: "e1",
    });
    expect(Object.keys(m.kinds)).toEqual(["note"]);
    expect(m.kinds.note?.legacy).toEqual(["note_key"]);
    expect(m.layers.map((l) => l.tier)).toEqual(["main", "import", "scenario"]);
    expect(m.engine?.engine_build).toBe("x");
    expect(m.old_hub).toBe("http://127.0.0.1:8765");
    const m2 = normaliseMeta({
      kinds: { profile: { version: 2, spec: { schema: { type: "object" }, title: "Profile" } } },
    });
    expect(m2.kinds.profile?.title).toBe("Profile");
  });
});
