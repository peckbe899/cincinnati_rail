// @vitest-environment happy-dom
// I2.1, the run times on the line sheet (claude/hub_maps/i21_plan.md, sections 1.5 to 1.7 and 4): the saved run of
// the section's route through POST /compute and its result events, a draft run of Ben's unsaved edit (never during a
// drag, only once the whole solve of that edit has landed and 300 ms have passed, a newer edit aborting the older
// request, nothing posted for a draft equal to the saved records), the run-time band and the run-time table.
// The fixture is a real railsim.run of Line 6 on main (31 stops: Greenlee and Lytle Park removed).

import { readFileSync } from "node:fs";
import { URL as NodeURL } from "node:url";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../src/api/client.ts";
import type { HubEvent } from "../../src/api/types.ts";
import type { BandData, SheetMark, SheetText, SheetView } from "../../src/core/plugin.ts";
import { formatChange, formatDuration, formatSpeed, Units } from "../../src/core/units.ts";
import { BANDS } from "../../src/plugins/line-sheet/bands.ts";
import { runStationsCsv } from "../../src/plugins/line-sheet/exports.ts";
import {
  DRAFT_PAUSE_MS,
  type DraftOut,
  RUN_ARRAYS,
  RUN_JOB,
  type Run,
  type RunBandData,
  type RunResult,
  Runs,
  type RunsApi,
  runFromDraft,
  runFromResult,
} from "../../src/plugins/line-sheet/runs.ts";
import { buildRunTable, type RunTableCtx } from "../../src/plugins/line-sheet/runtable.ts";
import { RUNTIME_H, runHeader, runtimeBand } from "../../src/plugins/line-sheet/runtime_band.ts";

const RAW = JSON.parse(readFileSync(new NodeURL("./fixtures/run_result_line6.json", import.meta.url), "utf-8")) as {
  key: string;
  meta: RunResult;
  /** little-endian float32, base64 */
  arrays: Record<string, string>;
};
const f32 = (b64: string): (number | null)[] => {
  const bytes = Buffer.from(b64, "base64");
  const a = new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 4);
  return Array.from(a, (x) => (Number.isFinite(x) ? x : null));
};
const FIX = {
  key: RAW.key,
  meta: RAW.meta,
  arrays: Object.fromEntries(Object.entries(RAW.arrays).map(([k, v]) => [k, f32(v)])) as Record<
    string,
    (number | null)[]
  >,
};
const META = FIX.meta;
const TOKEN = "main|-|canon";
const VIEW = { layer: "main", year: null, month: null, timeline: "canon" as const };
const SEC = "01DXF6DT00G2RN476ZR8N14PM3";
const ROUTE = "01DXF6DT00BGVCFV19RSHKD3VH";

const f8 = (xs: (number | null)[]): ArrayBuffer =>
  Float64Array.from(xs.map((x) => (x === null ? Number.NaN : x))).buffer as ArrayBuffer;

/** A draft answer: the fixture with every arrival later by `later` s (forward) and its trip time with it. */
function draftOut(later = 12, key = "d1"): DraftOut {
  const m = JSON.parse(JSON.stringify(META)) as RunResult;
  const d0 = m.directions[0];
  if (!d0) throw new Error("fixture");
  d0.trip_s += later;
  d0.running_s += later;
  for (const s of d0.stations.slice(1)) s.arrive_s += later;
  return {
    ...m,
    draft: true,
    key,
    cached: false,
    ms: 380,
    types: "draft",
    base: { assemble: "a1", run: FIX.key },
    edit_rev: 1,
    arrays: FIX.arrays,
  } as DraftOut;
}

interface Call {
  fn: string;
  args: unknown[];
}

function fakeApi(over: Partial<RunsApi> = {}) {
  const calls: Call[] = [];
  const log =
    (fn: string, out: (...a: unknown[]) => unknown) =>
    (...args: unknown[]) => {
      calls.push({ fn, args });
      return out(...args);
    };
  const api: RunsApi = {
    compute: log("compute", async () => ({ key: FIX.key, state: "hit", job: null })) as RunsApi["compute"],
    latestResult: log("latestResult", async () => FIX.key) as RunsApi["latestResult"],
    result: log("result", async (k) => ({
      key: k,
      type: RUN_JOB,
      scope: ROUTE,
      view: TOKEN,
      status: "ok",
      meta: META,
    })) as RunsApi["result"],
    resultArray: log("resultArray", async (_k, name) => ({
      dtype: "<f8",
      shape: [FIX.arrays[name as string]?.length ?? 0],
      buffer: f8(FIX.arrays[name as string] ?? []),
    })) as RunsApi["resultArray"],
    focus: log("focus", async () => undefined) as RunsApi["focus"],
    railsimDraft: log("railsimDraft", async () => draftOut()) as RunsApi["railsimDraft"],
    ...over,
  };
  return { api, calls };
}

const flush = async () => {
  for (let i = 0; i < 8; i++) await Promise.resolve();
};
const result = (type: string, scope: string, key: string, view = TOKEN): HubEvent => ({
  type: "result",
  seq: null,
  data: { key, type, scope, view, status: "ok", changed: [] },
});

describe("units for run times", () => {
  it("durations as m:ss, changes with their sign, speeds in km/h or mph", () => {
    expect(formatDuration(3120)).toBe("52:00");
    expect(formatDuration(67.8)).toBe("1:08");
    expect(formatDuration(3725)).toBe("1:02:05");
    expect(formatChange(12.2)).toBe("+0:12");
    expect(formatChange(-65)).toBe("-1:05");
    expect(formatChange(0.2)).toBe("0:00");
    expect(formatSpeed(88.51392, new Units("m"))).toBe("89");
    expect(formatSpeed(88.51392, new Units("ft"))).toBe("55");
  });
});

describe("the saved run (POST /compute railsim.run and its result events)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("asks the route's run at priority 2 in focus, 3 open, with the watch, and reads its meta and arrays", async () => {
    const { api, calls } = fakeApi();
    const runs = new Runs({ api, onChange: () => {}, dragging: () => false, now: () => Date.now() });
    runs.open({ sectionId: SEC, routeId: ROUTE, view: VIEW, token: TOKEN }, true);
    await flush();
    const c = calls.find((x) => x.fn === "compute");
    expect(c?.args).toEqual([RUN_JOB, ROUTE, TOKEN, 2, 600]);
    expect(runs.saved?.key).toBe(FIX.key);
    expect(runs.saved?.meta.directions[0]?.trip_s).toBeCloseTo(META.directions[0]?.trip_s ?? 0);
    expect(Object.keys(runs.saved?.arrays ?? {}).sort()).toEqual([...RUN_ARRAYS].sort());
    expect(Number.isNaN(runs.saved?.arrays.v_fwd_ms[0])).toBe(true);
    runs.active(false);
    runs.close();
    await flush();
    expect(calls.filter((x) => x.fn === "focus").map((x) => x.args[3])).toEqual([3, 9]);
  });

  it("a result event of this route and view reads the new run; another route's or view's reads nothing", async () => {
    const { api, calls } = fakeApi({
      compute: async () => ({ key: "k-new", state: "queued", job: "j1" }),
      latestResult: async () => null,
    });
    const runs = new Runs({ api, onChange: () => {}, dragging: () => false, now: () => Date.now() });
    runs.open({ sectionId: SEC, routeId: ROUTE, view: VIEW, token: TOKEN }, true);
    await flush();
    expect(runs.saved).toBeNull();
    expect(runs.status().updating).toBe(true);
    runs.event(result(RUN_JOB, "OTHER", "x"));
    runs.event(result(RUN_JOB, ROUTE, "y", "s1|-|canon"));
    await flush();
    expect(calls.filter((x) => x.fn === "result")).toHaveLength(0);
    runs.event(result(RUN_JOB, ROUTE, "k-new"));
    await flush();
    expect(runs.saved?.key).toBe("k-new");
    expect(runs.status().updating).toBe(false);
  });

  it("a job event of the route's run puts the updating mark on, a failed one shows its message", async () => {
    const { api } = fakeApi();
    const runs = new Runs({ api, onChange: () => {}, dragging: () => false, now: () => Date.now() });
    runs.open({ sectionId: SEC, routeId: ROUTE, view: VIEW, token: TOKEN }, true);
    await flush();
    const job = (state: string, msg = ""): HubEvent =>
      ({
        type: "job",
        seq: null,
        data: { id: "j", type: RUN_JOB, scope: ROUTE, view: TOKEN, state, progress: 0, msg },
      }) as HubEvent;
    runs.event(job("running", "forward"));
    expect(runs.status().updating).toBe(true);
    runs.event(job("failed", "railsim: no train for 1830"));
    expect(runs.status().updating).toBe(false);
    expect(runs.status().error).toContain("no train for 1830");
  });

  it("a done job, or a result equal to the run shown (an early cutoff), takes the updating mark off", async () => {
    const { api } = fakeApi();
    const runs = new Runs({ api, onChange: () => {}, dragging: () => false, now: () => Date.now() });
    runs.open({ sectionId: SEC, routeId: ROUTE, view: VIEW, token: TOKEN }, true);
    await flush();
    const job = (state: string, msg = ""): HubEvent =>
      ({
        type: "job",
        seq: null,
        data: { id: "j", type: RUN_JOB, scope: ROUTE, view: TOKEN, state, progress: 1, msg },
      }) as HubEvent;
    runs.event(job("running", "done"));
    expect(runs.status().note).toBeNull();
    runs.event(job("done"));
    expect(runs.status().updating).toBe(false);
    runs.event(job("queued"));
    runs.event(result(RUN_JOB, ROUTE, FIX.key));
    await flush();
    expect(runs.status().updating).toBe(false);
  });

  it("a line with no run (no route, not a railsim line) says so and keeps the band folded", async () => {
    const { api } = fakeApi({
      compute: async () => {
        throw new ApiError({ status: 422, code: "invalid", title: "invalid", detail: "no config for Line 2" });
      },
    });
    const runs = new Runs({ api, onChange: () => {}, dragging: () => false, now: () => Date.now() });
    runs.open({ sectionId: SEC, routeId: ROUTE, view: VIEW, token: TOKEN }, true);
    await flush();
    expect(runs.status().none).toContain("no config for Line 2");
    expect(runtimeBand.heightFor?.({ run: runs.band("both", []) })).toBe(0);
  });
});

describe("the draft run (POST /x/railsim/sections/{id}/draft)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  const setup = (over: Partial<RunsApi> = {}) => {
    const f = fakeApi(over);
    const state = { dragging: false };
    const runs = new Runs({
      api: f.api,
      onChange: () => {},
      dragging: () => state.dragging,
      now: () => Date.now(),
    });
    runs.open({ sectionId: SEC, routeId: ROUTE, view: VIEW, token: TOKEN }, true);
    const posts = () => f.calls.filter((x) => x.fn === "railsimDraft");
    return { ...f, runs, state, posts };
  };
  const SI = { contract: "section_input/0", section_id: SEC, length_m: 29539.6, step_m: 2, stations: [], pvi: [] };
  const TYPES = [["cutcover", 0, 640]];

  it("posts only once the whole solve of the edit has landed and 300 ms have passed since the last edit", async () => {
    const { runs, posts } = setup();
    await flush();
    runs.edited();
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS + 50);
    expect(posts()).toHaveLength(0);
    runs.ready({ rev: 1, input: SI, typeRuns: TYPES, dirty: true });
    await vi.advanceTimersByTimeAsync(0);
    expect(posts()).toHaveLength(1);
    const body = posts()[0]?.args[2] as { section_input: unknown; type_runs: unknown; edit_rev: number };
    expect(body).toEqual({ section_input: SI, type_runs: TYPES, edit_rev: 1 });
    await flush();
    expect(runs.draft?.draft).toBe(true);
    expect(runs.shown()?.key).toBe("d1");
  });

  it("waits out the 300 ms after the last edit", async () => {
    const { runs, posts } = setup();
    await flush();
    runs.edited();
    runs.ready({ rev: 1, input: SI, typeRuns: TYPES, dirty: true });
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS - 50);
    expect(posts()).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(60);
    expect(posts()).toHaveLength(1);
  });

  it("never posts while Ben drags; the draft goes once the pointer is up", async () => {
    const { runs, posts, state } = setup();
    await flush();
    state.dragging = true;
    runs.edited();
    runs.ready({ rev: 1, input: SI, typeRuns: TYPES, dirty: true });
    await vi.advanceTimersByTimeAsync(2000);
    expect(posts()).toHaveLength(0);
    state.dragging = false;
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS + 150);
    expect(posts()).toHaveLength(1);
  });

  it("a newer edit aborts the request in flight and drops the one waiting", async () => {
    let signal: AbortSignal | undefined;
    const { runs, posts } = setup({
      railsimDraft: (async (_s: string, _v: unknown, _b: unknown, sig?: AbortSignal) => {
        signal = sig;
        return new Promise<DraftOut>((_res, rej) =>
          sig?.addEventListener("abort", () => rej(new DOMException("aborted", "AbortError"))),
        );
      }) as RunsApi["railsimDraft"],
    });
    await flush();
    runs.edited();
    runs.ready({ rev: 1, input: SI, typeRuns: TYPES, dirty: true });
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS + 10);
    expect(signal?.aborted).toBe(false);
    runs.edited();
    expect(signal?.aborted).toBe(true);
    await flush();
    expect(runs.draft).toBeNull();
    expect(runs.status().error).toBeNull();
    expect(posts()).toHaveLength(0); // the counted fakes log only through fakeApi's own railsimDraft
  });

  it("a draft equal to the saved records posts nothing and shows the saved run", async () => {
    const { runs, posts } = setup();
    await flush();
    runs.edited();
    runs.ready({ rev: 1, input: SI, typeRuns: TYPES, dirty: true });
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS + 10);
    await flush();
    expect(runs.draft).not.toBeNull();
    // Ctrl+Z back to the record: clean, then the whole solve of the record lands with dirty false
    runs.clean();
    runs.ready({ rev: 2, input: SI, typeRuns: TYPES, dirty: false });
    await vi.advanceTimersByTimeAsync(1000);
    expect(posts()).toHaveLength(1);
    expect(runs.draft).toBeNull();
    expect(runs.shown()?.key).toBe(FIX.key);
  });

  it("after a save the draft stays until the saved run of the new records arrives over SSE", async () => {
    const { runs } = setup();
    await flush();
    runs.edited();
    runs.ready({ rev: 1, input: SI, typeRuns: TYPES, dirty: true });
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS + 10);
    await flush();
    runs.profileSaved();
    runs.clean();
    await vi.advanceTimersByTimeAsync(5000);
    expect(runs.shown()?.draft).toBe(true);
    runs.event(result(RUN_JOB, ROUTE, "k-after-save"));
    await flush();
    expect(runs.draft).toBeNull();
    expect(runs.shown()?.key).toBe("k-after-save");
  });

  it("409 pending sends the draft again on the route's next assemble result", async () => {
    let n = 0;
    const { runs, calls } = setup({
      railsimDraft: (async () => {
        n += 1;
        if (n === 1)
          throw new ApiError({ status: 409, code: "pending", title: "pending", detail: "no route.assemble yet" });
        return draftOut();
      }) as RunsApi["railsimDraft"],
    });
    await flush();
    runs.edited();
    runs.ready({ rev: 1, input: SI, typeRuns: TYPES, dirty: true });
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS + 10);
    await flush();
    expect(n).toBe(1);
    expect(runs.status().note).toContain("waiting");
    runs.event(result("route.assemble", ROUTE, "a2"));
    await vi.advanceTimersByTimeAsync(0);
    await flush();
    expect(n).toBe(2);
    expect(runs.draft?.key).toBe("d1");
    expect(calls.some((c) => c.fn === "compute")).toBe(true);
  });

  it("409 superseded is not an error", async () => {
    const { runs } = setup({
      railsimDraft: (async () => {
        throw new ApiError({ status: 409, code: "superseded", title: "superseded", detail: "newer" });
      }) as RunsApi["railsimDraft"],
    });
    await flush();
    runs.edited();
    runs.ready({ rev: 1, input: SI, typeRuns: TYPES, dirty: true });
    await vi.advanceTimersByTimeAsync(DRAFT_PAUSE_MS + 10);
    await flush();
    expect(runs.status().error).toBeNull();
  });

  it("an idle sheet sets no timers and makes no requests", async () => {
    const { runs, calls } = setup();
    await flush();
    const n = calls.length;
    await vi.advanceTimersByTimeAsync(10_000);
    expect(calls.length).toBe(n);
    expect(vi.getTimerCount()).toBe(0);
    runs.close();
  });
});

// ------------------------------------------------------------------------------------------------- the band

function fakeContext(texts: string[]): CanvasRenderingContext2D {
  return new Proxy(
    {},
    {
      get(_t, k) {
        if (k === "measureText") return (s: string) => ({ width: s.length * 6 });
        if (k === "fillText") return (s: string) => texts.push(s);
        return () => {};
      },
      set: () => true,
    },
  ) as unknown as CanvasRenderingContext2D;
}

function view(c0: number, c1: number, units = new Units("m"), w = 1400): SheetView {
  const plot = { x: 60, y: 40, w, h: 500 };
  const sx = plot.w / (c1 - c0);
  return {
    c0,
    c1,
    z0: 100,
    z1: 200,
    width: w + 80,
    height: 900,
    dpr: 1,
    top: 600,
    plot,
    x: (c) => plot.x + (c - c0) * sx,
    c: (x) => c0 + (x - plot.x) / sx,
    y: (z) => z,
    z: (y) => y,
    units,
    cursor: null,
  };
}

const saved = (): Run =>
  runFromResult(
    FIX.key,
    META,
    Object.fromEntries(RUN_ARRAYS.map((k) => [k, Float64Array.from(FIX.arrays[k] ?? [], (x) => x ?? Number.NaN)])),
    false,
  );

function bandData(run: RunBandData): BandData {
  return {
    sectionId: SEC,
    input: null,
    rail: null,
    server: null,
    profile: null,
    selected: null,
    run,
  };
}

function drawBand(run: RunBandData, v = view(0, 29540)) {
  const marks: SheetMark[] = [];
  const reports: SheetText[] = [];
  const texts: string[] = [];
  runtimeBand.draw(fakeContext(texts), v, {
    ...bandData(run),
    mark: (m) => marks.push(m),
    report: (t) => reports.push(t),
  });
  return { marks, reports, texts };
}

const bandRun = (over: Partial<RunBandData> = {}): RunBandData => ({
  saved: saved(),
  draft: null,
  updating: false,
  error: null,
  note: null,
  dirs: "both",
  removed: [
    { c: 3116.2, name: "Greenlee" },
    { c: 16000, name: "Lytle Park" },
  ],
  lit: null,
  ...over,
});

describe("the run-time band", () => {
  it("is a strip band under the structure strip, about 110 px, folded when the line has no run", () => {
    const ids = BANDS.map((b) => b.id);
    expect(ids.indexOf("runtime")).toBe(ids.indexOf("structure-strip") + 1);
    expect(runtimeBand.axis).toBe("strip");
    expect(RUNTIME_H).toBeGreaterThanOrEqual(100);
    expect(runtimeBand.heightFor?.({ run: bandRun() })).toBe(RUNTIME_H);
    expect(runtimeBand.heightFor?.({ run: null })).toBe(0);
  });

  it("draws both directions with their trip times, a leg label per leg and the header", () => {
    const { marks, reports } = drawBand(bandRun());
    const runs = marks.filter((m) => m.kind === "run");
    expect(runs.map((m) => m.dir)).toEqual([1, -1]);
    expect(runs[0]?.trip_s).toBeCloseTo(META.directions[0]?.trip_s ?? 0);
    expect(runs[1]?.running_s).toBeCloseTo(META.directions[1]?.running_s ?? 0);
    expect(runs.every((m) => m.draft === false)).toBe(true);
    const legs = marks.filter((m) => m.kind === "leg");
    // 30 legs each way, some thinned at the whole line, every one reported
    const fwd = reports.filter((r) => r.kind === "leg" && r.text.startsWith("Towne"));
    expect(reports.filter((r) => r.kind === "leg")).toHaveLength(60);
    expect(fwd[0]?.text).toMatch(/^Towne to Bond Hill 1:11$/);
    expect(legs.length).toBeGreaterThan(10);
    expect(legs.length).toBeLessThanOrEqual(60);
    const head = reports.find((r) => r.kind === "run");
    expect(head?.text).toContain("Towne to Beechgrove 50:35 (running 36:41, dwell 13:54); back 50:20");
    expect(head?.text).toContain("2026, GoA3, Type 2005");
    expect(marks.filter((m) => m.kind === "station-line").length).toBe(31);
    expect(marks.filter((m) => m.kind === "removed-line").map((m) => m.id)).toEqual(["Greenlee", "Lytle Park"]);
  });

  it("zoomed in, every leg in view gets its label", () => {
    const { marks } = drawBand(bandRun(), view(0, 5000));
    const legs = marks.filter((m) => m.kind === "leg" && m.dir === 1);
    expect(legs.map((m) => m.to)).toEqual(expect.arrayContaining(["Bond Hill", "Chalet"]));
  });

  it("Forward alone leaves the back curve and its legs out", () => {
    const { marks } = drawBand(bandRun({ dirs: "fwd" }));
    expect(marks.filter((m) => m.kind === "run").map((m) => m.dir)).toEqual([1]);
    expect(marks.filter((m) => m.kind === "leg").every((m) => m.dir === 1)).toBe(true);
  });

  it("a draft draws over the saved run, says draft and shows the change after each trip time", () => {
    const d = runFromDraft(draftOut(12));
    const { marks, reports } = drawBand(bandRun({ draft: d }));
    const runs = marks.filter((m) => m.kind === "run");
    expect(runs.every((m) => m.draft === true)).toBe(true);
    const head = reports.find((r) => r.kind === "run")?.text ?? "";
    expect(head).toContain("draft");
    expect(head).toContain("+0:12");
    expect(head).toContain("back 50:20 (0:00)");
  });

  it("pending: updating in the header, never blank", () => {
    const { marks, reports } = drawBand(bandRun({ updating: true }));
    expect(reports.find((r) => r.kind === "run")?.text).toContain("updating");
    expect(marks.filter((m) => m.kind === "run")).toHaveLength(2);
    const none = drawBand(bandRun({ saved: null, updating: true }));
    expect(none.reports.find((r) => r.kind === "run")?.text).toContain("Run times: updating");
  });

  it("in feet the axis is in mph", () => {
    const { texts, reports } = drawBand(bandRun(), view(0, 29540, new Units("ft")));
    expect(texts).toContain("mph");
    expect(texts).toContain("50");
    expect(reports.find((r) => r.kind === "run")?.text).not.toContain("km/h");
  });

  it("the hover readout gives both speeds, the limit with its reason and the times the front passes", () => {
    const v = view(2000, 4000);
    const zone = META.speed_zones.find((z) => z.reason.startsWith("curve")) as RunResult["speed_zones"][number];
    const c = (zone.c0_m + zone.c1_m) / 2;
    const vv = { ...v, pointer: { x: v.x(c), y: v.top + 60 } };
    const { reports } = drawBand(bandRun(), vv);
    const rows = reports.filter((r) => r.kind === "run-readout").map((r) => r.text);
    expect(rows.some((t) => /^Forward \d+ km\/h/.test(t))).toBe(true);
    expect(rows.some((t) => /^Back \d+ km\/h/.test(t))).toBe(true);
    expect(rows.some((t) => t.includes(zone.reason))).toBe(true);
    expect(rows.some((t) => /passes at \d+:\d\d/.test(t))).toBe(true);
  });

  it("the header line follows the plan's words", () => {
    const s = saved();
    expect(runHeader(s, null, new Units("m"), "both", false)).toMatch(
      /^Towne to Beechgrove 50:35 \(running 36:41, dwell 13:54\); back 50:20/,
    );
  });
});

// ------------------------------------------------------------------------------------------------ the table

const tableCtx = (over: Partial<RunTableCtx> = {}): RunTableCtx => ({
  units: new Units("m"),
  line: "Line 6",
  saved: saved(),
  draft: null,
  updating: false,
  error: null,
  note: null,
  removed: [{ c: 3116.2, name: "Greenlee" }],
  dirs: "both",
  narrow: false,
  attribution: null,
  attributionOpen: false,
  act: {
    select: vi.fn(),
    hover: vi.fn(),
    dirs: vi.fn(),
    attribution: vi.fn(),
    exportCsv: vi.fn(),
  },
  ...over,
});

describe("the run-time table", () => {
  it("one row per stop each way, removed stations in grey with no times, and the totals", () => {
    const el = buildRunTable(tableCtx());
    const fwd = el.querySelector('[data-dir="1"]') as HTMLElement;
    const rows = fwd.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(32);
    const removed = fwd.querySelector("tr.removed") as HTMLElement;
    expect(removed.textContent).toContain("Greenlee");
    expect(removed.textContent).toContain("removed");
    const bond = [...rows].find((r) => r.textContent?.includes("Bond Hill")) as HTMLElement;
    expect(bond.querySelector('[data-col="run"]')?.textContent).toBe("1:11");
    expect(bond.querySelector('[data-col="dwell"]')?.textContent).toBe("45");
    expect(bond.querySelector('[data-col="arrive"]')?.textContent).toBe("1:11");
    const totals = fwd.querySelector('[data-testid="run-totals"]') as HTMLElement;
    expect(totals.textContent).toContain("Trip 50:35");
    expect(totals.textContent).toContain("Running 36:41");
    expect(totals.textContent).toContain("Scheduled 51:41");
    expect(totals.textContent).toContain("1123 kWh");
    const round = el.querySelector('[data-testid="run-round-trip"]') as HTMLElement;
    expect(round.textContent).toContain("1:43:07");
    expect(el.querySelector('[data-testid="run-sources"]')?.textContent).toContain("Era 2026");
  });

  it("the sources line names the ground the structure types were made on", () => {
    const withGround = (ground: string | undefined) => {
      const run = saved();
      const sources = { ...run.meta.sources };
      if (ground === undefined) delete sources.ground;
      else sources.ground = ground;
      return { ...run, meta: { ...run.meta, sources } };
    };
    const text = (ground: string | undefined) =>
      buildRunTable(tableCtx({ saved: withGround(ground) })).querySelector('[data-testid="run-sources"]')
        ?.textContent ?? "";
    expect(text("line file")).toContain("Ground from the line file.");
    expect(text("ground model 2026 (canon)")).toContain("Ground from the ground model 2026 (canon).");
    expect(text(undefined)).not.toContain("Ground");
  });

  it("a draft shows its arrivals and a Change column against the saved run", () => {
    const el = buildRunTable(tableCtx({ draft: runFromDraft(draftOut(12)) }));
    const fwd = el.querySelector('[data-dir="1"]') as HTMLElement;
    expect(fwd.querySelector("th[data-col=change]")).not.toBeNull();
    const last = [...fwd.querySelectorAll("tbody tr")].at(-1) as HTMLElement;
    expect(last.querySelector('[data-col="change"]')?.textContent).toBe("+0:12");
    expect(fwd.querySelector('[data-testid="run-totals"]')?.textContent).toContain("Trip 50:47 (+0:12)");
  });

  it("feet shows vmax in mph; a row click moves the sheet to the station; Export CSV asks for the file", () => {
    const ctx = tableCtx({ units: new Units("ft") });
    const el = buildRunTable(ctx);
    expect(el.querySelector('[data-dir="1"] th[data-col="vmax"]')?.textContent).toContain("mph");
    const bond = [...el.querySelectorAll('[data-dir="1"] tbody tr')].find((r) =>
      r.textContent?.includes("Bond Hill"),
    ) as HTMLElement;
    bond.click();
    expect(ctx.act.select).toHaveBeenCalledWith("01DXF6DT00ZFVP0VMY5AH612Y8", 1084.2);
    (el.querySelector('[data-testid="run-export"]') as HTMLButtonElement).click();
    expect(ctx.act.exportCsv).toHaveBeenCalled();
  });

  it("where the time goes: the legs' phases from the run, the restrictions from the attribution", () => {
    const el = buildRunTable(
      tableCtx({
        attributionOpen: true,
        attribution: {
          directions: [
            {
              dir: 1,
              zones: [
                { c0_m: 2881, c1_m: 3252, reason: "curve R=327 m", rule: null, limit_kmh: 72.4, lost_s: 6.2 },
                { c0_m: 4000, c1_m: 4100, reason: "curve R=80 m", rule: null, limit_kmh: 30, lost_s: 21.5 },
              ],
              grades_s: 14,
              tunnel_drag_s: 9.5,
              dwell_s: 834,
            },
          ],
        },
      }),
    );
    const w = el.querySelector('[data-testid="run-where"]') as HTMLElement;
    expect(w.textContent).toContain("Bond Hill");
    const items = [...w.querySelectorAll('[data-testid="run-cost"] li')].map((x) => x.textContent ?? "");
    expect(items[0]).toContain("curve R=80 m");
    expect(items[0]).toContain("22 s");
    expect(items.some((t) => t.includes("Grades") && t.includes("14 s"))).toBe(true);
    expect(items.some((t) => t.includes("Tunnel drag"))).toBe(true);
  });

  it("the CSV of a direction is stations_<dir>.csv as railsim wrote it", () => {
    const csv = runStationsCsv(saved(), 1);
    const lines = csv.trim().split("\n");
    expect(lines[0]).toBe("station,km,arrive_s,depart_s,dwell_s,scheduled_arrive_s");
    expect(lines).toHaveLength(32);
    expect(lines[2]).toMatch(/^Bond Hill,1\.02[34],71\.3,116\.3,45\.0,73\.4$/);
  });
});
