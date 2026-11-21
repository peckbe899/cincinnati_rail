import { setupServer } from "msw/node";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { Api, type ApiError } from "../../src/api/client.ts";
import type { Rec } from "../../src/api/types.ts";
import { type Draft, Drafts } from "../../src/core/drafts.ts";
import { RecordCache } from "../../src/core/records.ts";
import { save } from "../../src/core/save.ts";
import { UndoStack } from "../../src/core/undo.ts";
import { makeView } from "../../src/core/view.ts";
import { BASE, FakeHub } from "./fake_hub.ts";

const hub = new FakeHub();
const server = setupServer(...hub.handlers());
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());

function app() {
  const api = new Api({ base: BASE, clientId: "tab-mine" });
  const drafts = new Drafts();
  const records = new RecordCache(api);
  const undo = new UndoStack(api, (recs, view) => {
    for (const r of recs) records.set(r, view);
  });
  return { api, drafts, records, undo };
}

describe("drafts, undo and the 412 flow", () => {
  it("undo reverts; 412 offers keep or take", async () => {
    const v1 = hub.seed({
      kind: "profile",
      id: "L6",
      data: {
        pvi: [
          [100, 200],
          [900, 210],
        ],
        st: { P1: 205 },
      },
    });
    const deps = app();
    const view = makeView({ layer: "main" });
    const rec = await deps.records.get("profile", "L6", view);

    // Two keystrokes in the table coalesce into one draft and one patch.
    deps.drafts.edit(rec, view, [{ op: "replace", path: "/data/pvi/1/1", value: 211 }]);
    const d = deps.drafts.edit(rec, view, [{ op: "replace", path: "/data/pvi/1/1", value: 212.5 }]) as Draft;
    expect(deps.drafts.ops(d)).toEqual([{ op: "replace", path: "/data/pvi/1/1", value: 212.5 }]);
    const saved = await save(deps, d.key, "PVI level");
    expect(saved.status).toBe("saved");
    const v2 = (saved as { rec: { version: number; data: unknown } }).rec;
    expect(v2.version).toBe(2);
    expect(deps.drafts.all()).toEqual([]);
    expect(deps.records.peek("profile", "L6", view)?.version).toBe(2);
    expect(deps.undo.peek()?.label).toBe("PVI level");

    // Undo posts a revert of that changeset: version 3 equals version 1.
    const r = await deps.undo.undo();
    expect(r?.records[0]?.version).toBe(3);
    expect(r?.records[0]?.data).toEqual(v1.data);
    expect(deps.records.peek("profile", "L6", view)?.version).toBe(3);
    expect(hub.log.filter((l) => l.url.includes("/revert")).length).toBe(1);
    // Redo reverts the revert: version 4 equals version 2.
    const again = await deps.undo.redo();
    expect(again?.records[0]?.version).toBe(4);
    expect(again?.records[0]?.data).toEqual(v2.data);

    // Someone else edits; my undo of version 4 is now a 409 and the stack keeps the entry.
    hub.write(
      "main",
      "profile",
      "L6",
      {
        pvi: [
          [100, 199],
          [900, 210],
        ],
        st: { P1: 205 },
      },
      "other",
    );
    const refused = await deps.undo.undo().catch((e: unknown) => e);
    expect((refused as ApiError).status).toBe(409);
    expect((refused as ApiError).code).toBe("conflict_revert");
    expect(deps.undo.canUndo).toBe(true);

    // A draft started from version 4 is stale now: save offers Keep mine or Take theirs.
    const v4 = deps.records.peek("profile", "L6", view) as Rec;
    expect(v4.version).toBe(4);
    deps.drafts.edit(v4, view, [{ op: "replace", path: "/data/st/P1", value: 207 }]);
    const key = deps.drafts.key("profile", "L6", view);
    const out = await save(deps, key);
    expect(out.status).toBe("stale");
    const offer = (out as { offer: import("../../src/core/save.ts").StaleOffer }).offer;
    expect(offer.theirs.version).toBe(5);
    expect(offer.by).toBe("other");
    expect(typeof offer.keepMine).toBe("function");
    expect(typeof offer.takeTheirs).toBe("function");

    // Keep mine: my change lands on top of theirs, with If-Match on theirs.
    const kept = await offer.keepMine();
    expect(kept.version).toBe(6);
    expect(kept.data).toEqual({
      pvi: [
        [100, 200],
        [900, 212.5],
      ],
      st: { P1: 207 },
    });
    expect(hub.log.filter((l) => l.method === "PATCH").at(-1)?.headers["if-match"]).toBe('"main:5"');
    expect(deps.drafts.all()).toEqual([]);

    // Take theirs: a second stale draft is dropped and their record shown.
    hub.write(
      "main",
      "profile",
      "L6",
      {
        pvi: [
          [100, 198],
          [900, 210],
        ],
        st: {},
      },
      "other",
    );
    deps.drafts.edit(kept, view, [{ op: "replace", path: "/data/pvi/0/1", value: 250 }]);
    const out2 = await save(deps, key);
    expect(out2.status).toBe("stale");
    const theirs = (out2 as { offer: import("../../src/core/save.ts").StaleOffer }).offer.takeTheirs();
    expect(theirs.version).toBe(7);
    expect(deps.drafts.all()).toEqual([]);
    expect(deps.records.peek("profile", "L6", view)?.data).toEqual({
      pvi: [
        [100, 198],
        [900, 210],
      ],
      st: {},
    });
  });

  it("a second save while the first is in flight waits for it and sends only the newer edits", async () => {
    hub.seed({ kind: "profile", id: "L7", data: { pvi: [[100, 200]], st: {} } });
    const deps = app();
    const view = makeView({ layer: "main" });
    const rec = await deps.records.get("profile", "L7", view);
    deps.drafts.edit(rec, view, [{ op: "replace", path: "/data/pvi/0/1", value: 201 }]);
    const key = deps.drafts.key("profile", "L7", view);
    // Enter in the cell starts a save; a keystroke and Ctrl+S follow before it answers.
    const first = save(deps, key);
    deps.drafts.edit(rec, view, [{ op: "add", path: "/data/st/PA", value: 199 }]);
    const second = save(deps, key);
    const [a, b] = await Promise.all([first, second]);
    expect(a.status).toBe("saved");
    expect(b.status).toBe("saved");
    const patches = hub.log.filter((l) => l.method === "PATCH" && l.url.includes("/k/profile/L7"));
    expect(patches.map((l) => [l.status, l.headers["if-match"]])).toEqual([
      [200, '"main:1"'],
      [200, '"main:2"'],
    ]);
    expect((b as { rec: Rec }).rec.data).toEqual({ pvi: [[100, 201]], st: { PA: 199 } });
    expect(deps.drafts.all()).toEqual([]);
    // Nothing left to send: a third save is clean.
    expect((await save(deps, key)).status).toBe("clean");
  });

  it("drops a draft whose edits are undone by hand", () => {
    const drafts = new Drafts();
    const view = makeView();
    const rec = hub.seed({ kind: "note", id: "N1", data: { text: "a" } });
    drafts.edit(rec, view, [{ op: "replace", path: "/data/text", value: "b" }]);
    expect(drafts.all().length).toBe(1);
    drafts.edit(rec, view, [{ op: "replace", path: "/data/text", value: "a" }]);
    expect(drafts.all().length).toBe(0);
  });
});
