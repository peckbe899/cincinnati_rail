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

    // The offer says what each side changed from my base: they moved both PVIs, I changed P1's level.
    expect(offer.changes.mine.map((c) => [c.path, c.before, c.after])).toEqual([["/data/st/P1", 205, 207]]);
    expect(offer.changes.theirs.map((c) => [c.path, c.before, c.after])).toEqual([
      ["/data/pvi/0/1", 200, 199],
      ["/data/pvi/1/1", 212.5, 210],
    ]);
    expect(offer.changes.both).toEqual([]);

    // Keep mine: my change lands on top of theirs, with If-Match on theirs. Their PVIs, which I never touched,
    // stay as they saved them (a whole-document save would have put my base's PVIs back).
    const kept = await offer.keepMine();
    expect(kept.version).toBe(6);
    expect(kept.data).toEqual({
      pvi: [
        [100, 199],
        [900, 210],
      ],
      st: { P1: 207 },
    });
    expect(hub.log.filter((l) => l.method === "PATCH").at(-1)?.status).toBe(200);
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

  it("Keep mine sends only my changes, keeps their other fields, and names the fields both changed", async () => {
    // Two tabs on Line 6's profile: tab B types PVI 10's level, tab A saves PVI 11's level first (usability-1).
    const pvi = Array.from({ length: 12 }, (_, i) => [i * 500, 190 + i]);
    hub.seed({ kind: "profile", id: "L9", data: { pvi, st: { P1: 150 } } });
    const deps = app();
    const view = makeView({ layer: "main" });
    const rec = await deps.records.get("profile", "L9", view);
    deps.drafts.edit(rec, view, [{ op: "replace", path: "/data/pvi/9/1", value: 232 }]);
    const theirs = structuredClone(pvi);
    (theirs[10] as number[])[1] = 191.5;
    hub.write("main", "profile", "L9", { pvi: theirs, st: { P1: 150 } }, "ben-tab-a");
    const key = deps.drafts.key("profile", "L9", view);
    const out = await save(deps, key);
    expect(out.status).toBe("stale");
    const offer = (out as { offer: import("../../src/core/save.ts").StaleOffer }).offer;
    expect(offer.changes.mine.map((c) => c.path)).toEqual(["/data/pvi/9/1"]);
    expect(offer.changes.theirs.map((c) => [c.path, c.after])).toEqual([["/data/pvi/10/1", 191.5]]);
    expect(offer.changes.both).toEqual([]);
    const kept = await offer.keepMine();
    // The patch carried my one field only; tab A's 191.5 stays.
    const sent = hub.log.filter((l) => l.method === "PATCH" && l.url.includes("/k/profile/L9")).at(-1);
    expect(sent?.status).toBe(200);
    expect((kept.data.pvi as number[][])[9]).toEqual([4500, 232]);
    expect((kept.data.pvi as number[][])[10]).toEqual([5000, 191.5]);

    // A note changed in two places at once (data-12, spec-4): their title stays, my text goes on top.
    hub.seed({ kind: "note", id: "N7", data: { text: "a", title: "old title" } });
    const note = await deps.records.get("note", "N7", view);
    deps.drafts.edit(note, view, [{ op: "replace", path: "/data/text", value: "my edit" }]);
    hub.write("main", "note", "N7", { text: "a", title: "new title" }, "crhub rec");
    const o2 = (await save(deps, deps.drafts.key("note", "N7", view))) as {
      offer: import("../../src/core/save.ts").StaleOffer;
    };
    expect((await o2.offer.keepMine()).data).toEqual({ text: "my edit", title: "new title" });

    // Both change the same field: the offer names it with the three values, and Keep mine puts mine there.
    deps.drafts.edit(kept, view, [{ op: "replace", path: "/data/pvi/9/1", value: 233 }]);
    const both = structuredClone(kept.data.pvi as number[][]);
    (both[9] as number[])[1] = 240;
    (both[2] as number[])[1] = 180;
    hub.write("main", "profile", "L9", { pvi: both, st: { P1: 150 } }, "other");
    const o3 = (await save(deps, key)) as { offer: import("../../src/core/save.ts").StaleOffer };
    expect(o3.offer.changes.both).toEqual([{ path: "/data/pvi/9/1", base: 232, mine: 233, theirs: 240 }]);
    const third = await o3.offer.keepMine();
    expect((third.data.pvi as number[][])[9]).toEqual([4500, 233]);
    expect((third.data.pvi as number[][])[2]).toEqual([1000, 180]);
    expect(deps.drafts.all()).toEqual([]);
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
