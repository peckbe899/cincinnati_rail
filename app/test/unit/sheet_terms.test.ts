// @vitest-environment happy-dom
// @vitest-environment-options {"url": "http://hub.test/w/design"}
// The line sheet and the host as Ben meets them: names instead of ids, a cleared level the browser solves as the
// server does, Enter that saves and leaves the cell, a sheet that is read-only where the save would be refused,
// chainage typed as 4+233.8, a save that says what it saved, a platform that opens its line, and drafts that
// survive a reload.

import type { SectionInput } from "@cr/engine/contract";
import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { Api, type ApiError, Api as RawApi } from "../../src/api/client.ts";
import type { EventFeed, FeedMessage } from "../../src/api/events.ts";
import type { Rec } from "../../src/api/types.ts";
import { fieldLabel, layerPhrase, localTime, valueText } from "../../src/core/describe.ts";
import { AppHost, DRAFTS_KEY, type UiMessage } from "../../src/core/host.ts";
import type { MountedPane, PaneContext } from "../../src/core/plugin.ts";
import { discover } from "../../src/core/registry.ts";
import { createAppStore } from "../../src/core/store.ts";
import { Units } from "../../src/core/units.ts";
import { parseUrl } from "../../src/core/url.ts";
import { createEngine } from "../../src/engine/client.ts";
import { changedText } from "../../src/plugins/jobs/index.ts";
import { mountSheet } from "../../src/plugins/line-sheet/pane.ts";
import review from "../../src/plugins/review/index.ts";
import { corePlugin, fieldKeepsKey } from "../../src/shell/core_plugin.ts";
import { BASE, FakeHub } from "./fake_hub.ts";

const SEC = "01DXF6DT00G2RN476ZR8N14PM3";
const PROF = "01DXF6DT00DAA2QCT2RPG72AYQ";
const PA = "01DXF6DT00WSWS0QYFS47VFZ1M";
const PB = "01DXF6DT00ZFVP0VMY5AH612Y8";
const SA = "01DXF6DT001RS7Q80XN7KS2A2C";
const SB = "01DXF6DT001WGDA7QZYBDZ42P9";

const hub = new FakeHub();
/** The inputs the engine was asked to solve, newest last. */
const solved: SectionInput[] = [];

/** The server's input of the saved profile (what /x/profiles/sections/{id}/input answers). */
function inputOf(layer: string): SectionInput {
  const p = hub.resolve(layer, "profile", PROF) as Rec;
  const st = (p.data.st ?? {}) as Record<string, number | null>;
  return {
    contract: "section_input/0",
    section_id: SEC,
    length_m: 6000,
    chainage_basis: "grid:26916",
    scale: 0.99983821,
    step_m: 2,
    params: { platform_m: 121.92, vc_radius_m: 1500, vc_min_len_m: 30.5 },
    stations: [
      { platform_id: PA, order: 0, c_m: 60.5, level_m: st[PA] ?? null, grade_permille: 0 },
      { platform_id: PB, order: 1, c_m: 1084.2, level_m: st[PB] ?? null, grade_permille: 0 },
    ],
    pvi: ((p.data.pvi ?? []) as number[][]).map(([c, z]) => ({ c_m: c as number, z_m: z as number })),
  };
}

const server = setupServer(
  ...hub.handlers(),
  http.get(`${BASE}/k/:kind`, ({ request, params }) => {
    const u = new URL(request.url);
    const layer = u.searchParams.get("layer") ?? "main";
    const parent = u.searchParams.get("parent");
    const ids = u.searchParams.get("ids")?.split(",");
    const items = [...hub.recs.values()]
      .filter((r) => r.kind === params.kind && (r.layer === "main" || r.layer === layer))
      .map((r) => hub.resolve(layer, r.kind, r.id) as Rec)
      .filter((r, i, all) => all.findIndex((x) => x.id === r.id) === i)
      .filter((r) => !parent || (r.data as Record<string, unknown>).section === parent)
      .filter((r) => !ids || ids.includes(r.id));
    return HttpResponse.json({ items, next: null });
  }),
  http.get(`${BASE}/x/profiles/sections/:id/input`, ({ request }) =>
    HttpResponse.json(inputOf(new URL(request.url).searchParams.get("layer") ?? "main")),
  ),
  http.get(`${BASE}/results`, () => HttpResponse.json({ key: null })),
  http.get(`${BASE}/jobs`, () => HttpResponse.json({ items: [] })),
  http.get(`${BASE}/conflicts`, () =>
    HttpResponse.json({
      items: [{ id: "C1", layer: "try", rec_id: PROF, kind: "profile", reason: "both_changed", state: "open" }],
    }),
  ),
  http.post(`${BASE}/compute`, () => HttpResponse.json({ key: "k1", state: "queued", job: "j1" })),
);
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterAll(() => server.close());

function seed(): void {
  hub.seed({ kind: "section", id: SEC, data: { name: "Line 6", key: "Line_6" } });
  hub.seed({ kind: "stop", id: SA, data: { name: "Towne", section: SEC, c: 60.5, order: 0 } });
  hub.seed({ kind: "stop", id: SB, data: { name: "Bond Hill", section: SEC, c: 1084.2, order: 1 } });
  hub.seed({ kind: "platform", id: PA, data: { name: "Towne", section: SEC, stop: SA } });
  hub.seed({ kind: "platform", id: PB, data: { name: "Bond Hill", section: SEC, stop: SB } });
  hub.seed({ kind: "authority", id: "01DXF6DT00AUTHPR0F1LE00000", data: { kind: "profile", owner: "legacy" } });
  hub.seed({
    kind: "profile",
    id: PROF,
    data: {
      section: SEC,
      pvi: [
        [357, 168.5],
        [3005, 175],
        [4233.8, 204.6],
      ],
      st: { [PA]: 150, [PB]: 151.5 },
    },
  });
}

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

const memory = () => {
  const m = new Map<string, string>();
  return {
    getItem: (k: string) => m.get(k) ?? null,
    setItem: (k: string, v: string) => void m.set(k, v),
    removeItem: (k: string) => void m.delete(k),
    m,
  };
};

function makeHost(url: string, draftStore = memory()) {
  const host = new AppHost({
    registry: discover(),
    api: new Api({ base: BASE, clientId: "tab-terms" }),
    store: createAppStore(parseUrl(url)),
    events: feed(),
    draftStore,
    engine: createEngine({
      makeWorker: () => null,
      inline: async () => ({
        hello: async () => ({ engine_version: "0", methods: ["vertical.rail@1"], contracts: {} }),
        solve: async (_m: string, inp: unknown) => {
          solved.push(inp as SectionInput);
          return { result: { rail_m: [], grade_permille: [], grid: { c0: 0, step_m: 2, n: 0 } }, ms: 0 };
        },
      }),
    }),
  });
  host.registry.add(corePlugin(host));
  const ui: UiMessage[] = [];
  host.ui.on((m) => ui.push(m));
  const toasts = () => ui.flatMap((m) => (m.type === "toast" ? [m.toast.text] : []));
  return { host, ui, toasts, draftStore };
}

const titles: string[] = [];
function ctxOf(host: AppHost): PaneContext {
  return {
    host,
    params: {},
    state: undefined,
    setTitle: (t) => titles.push(t),
    onResize: () => ({ dispose: () => {} }),
  };
}

async function until(pred: () => boolean, ms = 2000): Promise<void> {
  const t0 = Date.now();
  while (!pred()) {
    if (Date.now() - t0 > ms) throw new Error("timed out waiting");
    await new Promise((r) => setTimeout(r, 5));
  }
}

let mounted: MountedPane | null = null;
afterEach(() => {
  mounted?.dispose();
  mounted = null;
  document.body.replaceChildren();
});

async function openSheet(url: string) {
  const h = makeHost(url);
  const el = document.createElement("div");
  document.body.append(el);
  mounted = await mountSheet(el, ctxOf(h.host));
  const cell = (label: string) => el.querySelector(`input[aria-label="${label}"]`) as HTMLInputElement | null;
  await until(() => cell("Station Bond Hill level") !== null && !(cell("PVI 1 level") as HTMLInputElement).disabled);
  return { ...h, el, cell };
}

describe("the line sheet in Ben's terms", () => {
  it("names the line and its stations, and solves a cleared level as the server does", async () => {
    seed();
    const { host, el, cell } = await openSheet(`/w/design?layer=try&sel=profile:${PROF}`);
    // usability-5: the title, the tab and the station rows name the line and the platforms; no ULID shows.
    expect(el.querySelector(".sheet-bar strong")?.textContent).toBe("Line 6");
    expect((el.querySelector(".sheet-bar strong") as HTMLElement).dataset.section).toBe(SEC);
    expect(titles.at(-1)).toBe("Line 6");
    const names = [...el.querySelectorAll('[data-testid="station-table"] td.name')].map((t) => t.textContent);
    expect(names).toEqual(["Towne", "Bond Hill"]);
    expect(el.querySelector('[data-testid="station-table"]')?.textContent).not.toMatch(/01DX/);
    // usability-14: the header says which revision the sheet edits.
    expect(el.querySelector('[data-testid="profile-info"]')?.textContent).toBe("Line 6 profile, version 1 on main");
    // usability-8: chainage reads as the readout writes it.
    expect(cell("PVI 3 chainage")?.value).toBe("4+233.8");

    // compute-3: Ben clears Bond Hill's level. The draft removes the key, and the browser solves Bond Hill unset,
    // exactly as the server builds it (st.get(pid) is None); it never keeps the 151.5 the input was built with.
    const pb = cell("Station Bond Hill level") as HTMLInputElement;
    pb.focus();
    pb.value = "";
    pb.dispatchEvent(new Event("input"));
    const key = host.drafts.key("profile", PROF, host.view());
    expect(host.drafts.byKey(key)?.body.data.st).toEqual({ [PA]: 150 });
    await until(() => solved.at(-1)?.stations[1]?.level_m === null);
    expect(solved.at(-1)?.stations.map((s) => s.level_m)).toEqual([150, null]);
    // When the focus leaves, the cell shows what the draft holds: empty, not the old level.
    pb.blur();
    pb.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));
    await until(() => cell("Station Bond Hill level")?.value === "");
    host.dispose();
  });

  it("Enter saves, says so, and leaves the cell, so Ctrl+Z is the hub's undo", async () => {
    seed();
    const { host, cell, toasts, el } = await openSheet(`/w/design?layer=try&sel=profile:${PROF}`);
    const z = cell("PVI 1 level") as HTMLInputElement;
    z.focus();
    // A cell that still shows what it was drawn with hands Ctrl+Z to the hub; typed text keeps it.
    expect(fieldKeepsKey(z, "ctrl+z")).toBe(false);
    z.value = "169";
    z.dispatchEvent(new Event("input"));
    expect(fieldKeepsKey(z, "ctrl+z")).toBe(true);
    z.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(document.activeElement).not.toBe(z);
    await until(() => host.undo.canUndo);
    const saved = hub.resolve("try", "profile", PROF) as Rec;
    expect(saved.version).toBe(2);
    expect((saved.data.pvi as number[][])[0]).toEqual([357, 169]);
    // usability-14: the save names what it saved and the version it made.
    await until(() => toasts().some((t) => t.startsWith("Saved")));
    expect(toasts().find((t) => t.startsWith("Saved"))).toBe("Saved PVI 1 level on Line 6 profile: version 2 on try.");
    await until(() => el.querySelector('[data-testid="profile-info"]')?.textContent?.includes("version 2") ?? false);
    // The hub's undo, with a notice of what it undid.
    await host.undoLast();
    expect((hub.resolve("try", "profile", PROF) as Rec).version).toBe(3);
    expect(toasts().at(-1)).toBe("Undone: PVI 1 level on Line 6 profile, now version 3 on try.");
    host.dispose();
  });

  it("Ctrl+Z while the save is still on its way undoes the save, not the step being saved", async () => {
    // On a busy hub the answer to a save can come after Ben's next Ctrl+Z: that Ctrl+Z waits for it, then reverts
    // the saved changeset, rather than taking the unsaved step back out of a save already written.
    seed();
    const { host, cell } = await openSheet(`/w/design?layer=try&sel=profile:${PROF}`);
    const z = cell("PVI 1 level") as HTMLInputElement;
    z.focus();
    z.value = "169";
    z.dispatchEvent(new Event("input"));
    z.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await host.undoLast();
    const now = hub.resolve("try", "profile", PROF) as Rec;
    expect(now.version).toBe(3);
    expect((now.data.pvi as number[][])[0]).toEqual([357, 168.5]);
    expect(host.dirtyDrafts("try")).toEqual([]);
    host.dispose();
  });

  it("reads 4+233.8 as a chainage and refuses a bad one in words, without saving", async () => {
    seed();
    const { host, cell, toasts, el } = await openSheet(`/w/design?layer=try&sel=profile:${PROF}`);
    const v0 = (hub.resolve("try", "profile", PROF) as Rec).version;
    const c = cell("PVI 2 chainage") as HTMLInputElement;
    c.focus();
    c.value = "3+105.5";
    c.dispatchEvent(new Event("input"));
    const key = host.drafts.key("profile", PROF, host.view());
    expect((host.drafts.byKey(key)?.body.data.pvi as number[][] | undefined)?.[1]).toEqual([3105.5, 175]);
    c.value = "3,205";
    c.dispatchEvent(new Event("input"));
    expect((host.drafts.byKey(key)?.body.data.pvi as number[][] | undefined)?.[1]).toEqual([3205, 175]);
    c.value = "3+2x";
    c.dispatchEvent(new Event("input"));
    expect(c.classList.contains("bad")).toBe(true);
    expect(el.querySelector('[data-testid="sheet-notice"]')?.textContent).toContain(
      'PVI 2 chainage: "3+2x" is not a chainage',
    );
    c.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(toasts().at(-1)).toMatch(/^Not saved: PVI 2 chainage "3\+2x" is not a chainage/);
    expect((hub.resolve("try", "profile", PROF) as Rec).version).toBe(v0);
    host.dispose();
  });

  it("is read-only on main while the old hub owns profiles, and Save covers this layer only", async () => {
    seed();
    const h = makeHost(`/w/design?layer=main&sel=profile:${PROF}`);
    const el = document.createElement("div");
    document.body.append(el);
    mounted = await mountSheet(el, ctxOf(h.host));
    const cell = (label: string) => el.querySelector(`input[aria-label="${label}"]`) as HTMLInputElement | null;
    await until(() => (el.querySelector('[data-testid="sheet-notice"]')?.textContent ?? "").includes("old hub"));
    expect(el.querySelector('[data-testid="sheet-notice"]')?.textContent).toBe(
      "The old hub owns Line 6's profile on main: switch to a scenario (Layer, at the top) to edit it.",
    );
    expect(cell("PVI 1 level")?.disabled).toBe(true);
    expect(cell("Station Towne level")?.disabled).toBe(true);
    expect(await h.host.editable("profile", h.host.view())).toMatch(/old hub owns profile records on main/);
    // A draft typed on main (from before this rule, or by the inspector) is not sent by Save on a scenario.
    const rec = await h.host.records.get("profile", PROF, h.host.view());
    h.host.drafts.edit(rec, h.host.view(), [{ op: "replace", path: "/data/pvi/0/1", value: 180 }]);
    h.host.store.getState().update({ layer: "try" });
    const before = hub.log.filter((l) => l.method === "PATCH").length;
    expect(await h.host.saveAll()).toEqual([]);
    expect(hub.log.filter((l) => l.method === "PATCH").length).toBe(before);
    expect(h.host.dirtyDrafts("main").length).toBe(1);
    h.host.dispose();
  });

  it("Discard drops the sheet's draft", async () => {
    seed();
    const { host, cell, el } = await openSheet(`/w/design?layer=try&sel=profile:${PROF}`);
    const discard = el.querySelector('[data-testid="sheet-discard"]') as HTMLButtonElement;
    expect(discard.disabled).toBe(true);
    const z = cell("PVI 1 level") as HTMLInputElement;
    z.value = "170";
    z.dispatchEvent(new Event("input"));
    await until(() => !discard.disabled);
    discard.click();
    expect(host.drafts.all()).toEqual([]);
    await until(() => cell("PVI 1 level")?.value === "168.5");
    host.dispose();
  });

  it("a platform picked elsewhere opens its line at its stop's chainage", async () => {
    seed();
    const h = makeHost("/w/design?layer=try");
    const el = document.createElement("div");
    document.body.append(el);
    mounted = await mountSheet(el, ctxOf(h.host));
    h.host.select({ kind: "platform", id: PB });
    await until(() => el.querySelector(".sheet-bar strong")?.textContent === "Line 6");
    await until(() => h.host.store.getState().c === 1084.2);
    h.host.dispose();
  });
});

describe("unsaved drafts across a reload (usability-2, data-13)", () => {
  it("asks before the tab closes, keeps the drafts, and offers them back after a reload", async () => {
    seed();
    const store = memory();
    const a = makeHost(`/w/design?layer=try&sel=profile:${PROF}`, store);
    const rec = await a.host.records.get("profile", PROF, a.host.view());
    const ev = { preventDefault: () => (prevented = true), returnValue: undefined as unknown };
    let prevented = false;
    expect(a.host.beforeUnload(ev)).toBe(false);
    a.host.drafts.edit(rec, a.host.view(), [{ op: "replace", path: "/data/pvi/1/1", value: 215 }]);
    expect(a.host.beforeUnload(ev)).toBe(true);
    expect(prevented).toBe(true);
    expect(JSON.parse(store.m.get(DRAFTS_KEY) as string)).toHaveLength(1);
    a.host.dispose();

    // The reload: a new host on the same tab storage offers the edit back, and restores it on request.
    const b = makeHost(`/w/design?layer=try&sel=profile:${PROF}`, store);
    b.host.activate();
    const offer = b.ui.find((m) => m.type === "toast" && m.toast.text.startsWith("Unsaved edits from before"));
    expect(offer).toBeTruthy();
    const restore = (offer as Extract<UiMessage, { type: "toast" }>).toast.actions?.find(
      (x) => x.label === "Restore them",
    );
    restore?.run();
    const d = b.host.drafts.get("profile", PROF, b.host.view());
    expect((d?.body.data.pvi as number[][] | undefined)?.[1]).toEqual([3005, 215]);
    // Reset the pane layout no longer reloads the page: it asks the dock to lay out again.
    await b.host.runCommand("core.reset-layout");
    expect(b.ui.some((m) => m.type === "reset-layout")).toBe(true);
    expect(b.host.drafts.all()).toHaveLength(1);
    b.host.dispose();
  });
});

describe("words for fields, layers, times and a stopped hub (usability-5, -14, -18)", () => {
  it("labels a profile's fields as Ben names them", () => {
    const name = (id: string) => (id === PB ? "Bond Hill" : id);
    expect(fieldLabel("profile", "/data/pvi/9/1", name)).toBe("PVI 10 level");
    expect(fieldLabel("profile", "/data/pvi/9/0", name)).toBe("PVI 10 chainage");
    expect(fieldLabel("profile", "/data/pvi", name)).toBe("the PVI list");
    expect(fieldLabel("profile", `/data/st/${PB}`, name)).toBe("Bond Hill level");
    expect(fieldLabel("profile", `/data/sg/${PB}`, name)).toBe("Bond Hill grade");
    expect(fieldLabel("section", "/data/scale", name)).toBe("scale");
    expect(valueText("profile", "/data/pvi/9/1", 232, new Units())).toBe("232 m");
    expect(valueText("profile", `/data/st/${PB}`, null, new Units())).toBe("design");
    expect(valueText("profile", `/data/st/${PB}`, undefined, new Units())).toBe("not set");
    expect(layerPhrase("legacy:old_hub")).toBe("from the old hub's data");
    expect(layerPhrase("try")).toBe("on try");
    expect(localTime("2026-11-21T23:21:27.423Z")).not.toContain("T23:21");
  });

  it("says the hub is not running, and how to start it", async () => {
    const dead = new RawApi({ base: BASE, fetch: () => Promise.reject(new TypeError("Failed to fetch")) });
    const e = (await dead.health().catch((x: unknown) => x)) as ApiError;
    expect(e.message).toMatch(
      /^The hub is not answering\. Is it running\? Start it from the repo folder with \.\\crhub/,
    );
    expect(e.message).not.toContain("TypeError");
    const { host } = makeHost("/w/design");
    (host as unknown as { onFeed(m: FeedMessage): void }).onFeed({
      type: "status",
      state: "closed",
      reconnected: false,
      epoch: null,
      seq: null,
      engine_build: null,
    });
    expect(host.statusItems.get("core.events")?.text).toBe("events: the hub is not answering");
    expect(host.statusItems.get("core.events")?.title).toMatch(/crhub/);
    host.dispose();
  });

  it("the jobs pane writes chainage as the readout does, and the review queue names its records", async () => {
    seed();
    const { host } = makeHost("/w/design?layer=try");
    expect(
      changedText(
        [
          [3514, 4566],
          [0, 29538],
        ],
        host,
      ),
    ).toBe("3+514.0 to 4+566.0, 0+000.0 to 29+538.0");
    const el = document.createElement("div");
    document.body.append(el);
    const pane = review.panes?.[0];
    mounted = (await pane?.mount(el, ctxOf(host))) ?? null;
    await until(() => el.querySelector("a")?.textContent === "Line 6 profile");
    expect(el.textContent).not.toContain(PROF);
    host.dispose();
  });
});
