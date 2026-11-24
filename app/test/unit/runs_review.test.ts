// I2.1 review of the sheet's runs controller (runs.ts): each case here failed on the code as the lanes left it.
// - A saved run read later than a newer one must not replace it: the run shown while the first job of an open is
//   computed (the newest result before it) can come back after the new run's result event has been read.
// - A draft held back by 409 pending is not posted while Ben drags, even when the route's assemble lands mid-drag.

import { readFileSync } from "node:fs";
import { URL as NodeURL } from "node:url";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../src/api/client.ts";
import type { HubEvent, ResultMeta } from "../../src/api/types.ts";
import { DRAFT_PAUSE_MS, RUN_JOB, type RunResult, Runs, type RunsApi } from "../../src/plugins/line-sheet/runs.ts";

const RAW = JSON.parse(readFileSync(new NodeURL("./fixtures/run_result_line6.json", import.meta.url), "utf-8")) as {
  key: string;
  meta: RunResult;
};
const TOKEN = "main|-|canon";
const VIEW = { layer: "main", year: null, month: null, timeline: "canon" as const };
const SEC = "S1";
const ROUTE = "R1";

const flush = async () => {
  for (let i = 0; i < 12; i++) await Promise.resolve();
};
const result = (type: string, scope: string, key: string): HubEvent => ({
  type: "result",
  seq: null,
  data: { key, type, scope, view: TOKEN, status: "ok", changed: [] },
});
const meta = (key: string): ResultMeta =>
  ({ key, type: RUN_JOB, scope: ROUTE, view: TOKEN, status: "ok", meta: RAW.meta }) as unknown as ResultMeta;

function api(over: Partial<RunsApi> = {}): { api: RunsApi; calls: string[] } {
  const calls: string[] = [];
  const a: RunsApi = {
    compute: async () => ({ key: "", state: "queued", job: "j1" }),
    latestResult: async () => null,
    result: async (k) => meta(k),
    resultArray: async () => ({ dtype: "<f8", shape: [0], buffer: new ArrayBuffer(0) }),
    focus: async () => undefined,
    railsimDraft: (async () => {
      calls.push("draft");
      return { ...RAW.meta, draft: true, key: "d1", cached: false, ms: 1, types: "draft", base: {}, edit_rev: 1 };
    }) as unknown as RunsApi["railsimDraft"],
    ...over,
  };
  return { api: a, calls };
}

describe("runs.ts review", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("an older saved run that comes back late never replaces the newer one", async () => {
    let release: (() => void) | null = null;
    const { api: a } = api({
      latestResult: async () => "k-old",
      result: async (k) => {
        if (k === "k-old") await new Promise<void>((res) => (release = res));
        return meta(k);
      },
    });
    const runs = new Runs({ api: a, onChange: () => {}, dragging: () => false, now: () => Date.now() });
    runs.open({ sectionId: SEC, routeId: ROUTE, view: VIEW, token: TOKEN }, true);
    await flush();
    expect(release).not.toBeNull();
    runs.event(result(RUN_JOB, ROUTE, "k-new"));
    await flush();
    expect(runs.saved?.key).toBe("k-new");
    (release as unknown as () => void)();
    await flush();
    expect(runs.saved?.key).toBe("k-new");
  });

  it("a draft waiting on 409 pending is not posted during a drag; it goes when the pointer is up", async () => {
    let n = 0;
    const state = { dragging: false };
    const { api: a } = api({
      compute: async () => ({ key: "k1", state: "hit", job: null }),
      railsimDraft: (async () => {
        n += 1;
        if (n === 1) throw new ApiError({ status: 409, code: "pending", title: "pending", detail: "no assemble" });
        return { ...RAW.meta, draft: true, key: "d1", cached: false, ms: 1, types: "draft", base: {}, edit_rev: 1 };
      }) as unknown as RunsApi["railsimDraft"],
    });
    const runs = new Runs({ api: a, onChange: () => {}, dragging: () => state.dragging, now: () => Date.now() });
    runs.open({ sectionId: SEC, routeId: ROUTE, view: VIEW, token: TOKEN }, true);
    await flush();
    runs.edited();
    runs.ready({ rev: 1, input: {}, typeRuns: null, dirty: true });
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS + 10);
    await flush();
    expect(n).toBe(1);
    state.dragging = true; // pointer down, nothing moved yet
    runs.event(result("route.assemble", ROUTE, "a2"));
    await vi.advanceTimersByTimeAsync(1000);
    await flush();
    expect(n).toBe(1);
    state.dragging = false;
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS + 150);
    await flush();
    expect(n).toBe(2);
    expect(runs.draft?.key).toBe("d1");
  });

  it("a saved draft whose run equals the saved run goes at once: no result event follows an unchanged run", async () => {
    const { api: a } = api({
      compute: async () => ({ key: "k1", state: "hit", job: null }),
      resultArray: async () => ({ dtype: "<f8", shape: [0], buffer: new ArrayBuffer(0) }),
    });
    const runs = new Runs({ api: a, onChange: () => {}, dragging: () => false, now: () => Date.now() });
    runs.open({ sectionId: SEC, routeId: ROUTE, view: VIEW, token: TOKEN }, true);
    await flush();
    expect(runs.saved?.key).toBe("k1");
    runs.edited(); // a note or a ground point: the profile is dirty, its run is the saved one
    runs.ready({ rev: 1, input: {}, typeRuns: null, dirty: true });
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS + 10);
    await flush();
    expect(runs.draft?.key).toBe("d1");
    runs.profileSaved();
    runs.clean();
    await vi.advanceTimersByTimeAsync(1000);
    expect(runs.draft).toBeNull();
    expect(runs.shown()?.key).toBe("k1");
  });
});
