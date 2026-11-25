// @vitest-environment happy-dom
// The run times as Ben reads them (I2.1 review against railsim's own report): the band's header keeps the draft and
// updating marks clear of the direction toggle, the hover readout sits under the header (the toggle never covers a
// row), the speed curves come down to a stand at each stop as railsim's profile plot did, the train line says the
// load as railsim did ("load 50%"), and the round trip names the turnback at each end in minutes.

import { readFileSync } from "node:fs";
import { URL as NodeURL } from "node:url";
import { describe, expect, it, vi } from "vitest";
import type { BandData, SheetMark, SheetText, SheetView } from "../../src/core/plugin.ts";
import { Units } from "../../src/core/units.ts";
import {
  RUN_ARRAYS,
  type Run,
  type RunBandData,
  type RunResult,
  runFromResult,
} from "../../src/plugins/line-sheet/runs.ts";
import { buildRunTable, type RunTableCtx } from "../../src/plugins/line-sheet/runtable.ts";
import { RUN_TOGGLE_W, RUNTIME_H, runtimeBand } from "../../src/plugins/line-sheet/runtime_band.ts";

const RAW = JSON.parse(readFileSync(new NodeURL("./fixtures/run_result_line6.json", import.meta.url), "utf-8")) as {
  key: string;
  meta: RunResult;
  arrays: Record<string, string>;
};
const f32 = (b64: string): number[] => {
  const bytes = Buffer.from(b64, "base64");
  return Array.from(new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 4));
};
const ARR = Object.fromEntries(Object.entries(RAW.arrays).map(([k, v]) => [k, f32(v)]));
const meta = (): RunResult => JSON.parse(JSON.stringify(RAW.meta)) as RunResult;
const runOf = (m: RunResult, draft = false): Run =>
  runFromResult(
    draft ? "d1" : RAW.key,
    m,
    Object.fromEntries(RUN_ARRAYS.map((k) => [k, Float64Array.from(ARR[k] ?? [])])),
    draft,
  );

interface Drawn {
  texts: { s: string; x: number }[];
  /** every path point, with the stroke colour it was drawn in */
  points: { x: number; y: number; colour: string }[];
}

/** A 2D context that keeps the text it is asked to draw (6 px a character) and the points of its paths. */
function fakeContext(out: Drawn): CanvasRenderingContext2D {
  let colour = "";
  return new Proxy(
    {},
    {
      get(_t, k) {
        if (k === "measureText") return (s: string) => ({ width: s.length * 6 });
        if (k === "fillText") return (s: string, x: number) => out.texts.push({ s, x });
        if (k === "moveTo" || k === "lineTo") return (x: number, y: number) => out.points.push({ x, y, colour });
        if (k === "strokeStyle") return colour;
        return () => {};
      },
      set(_t, k, v) {
        if (k === "strokeStyle") colour = String(v);
        return true;
      },
    },
  ) as unknown as CanvasRenderingContext2D;
}

function view(c0: number, c1: number, w = 700, pointer: { x: number; y: number } | null = null): SheetView {
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
    units: new Units("m"),
    cursor: null,
    ...(pointer ? { pointer } : {}),
  } as SheetView;
}

const bandRun = (over: Partial<RunBandData> = {}): RunBandData => ({
  saved: runOf(meta()),
  draft: null,
  updating: false,
  error: null,
  note: null,
  dirs: "both",
  removed: [],
  lit: null,
  ...over,
});

function draw(run: RunBandData, v: SheetView) {
  const out: Drawn = { texts: [], points: [] };
  const marks: SheetMark[] = [];
  const reports: SheetText[] = [];
  const d: BandData = {
    sectionId: "s",
    input: null,
    rail: null,
    server: null,
    profile: null,
    selected: null,
    run,
    mark: (m) => marks.push(m),
    report: (t) => reports.push(t),
  };
  runtimeBand.draw(fakeContext(out), v, d);
  return { ...out, marks, reports };
}

describe("the run-time band as Ben reads it", () => {
  it("the header never runs under the direction toggle, and a draft or an update says so in what is drawn", () => {
    const later = meta();
    const d0 = later.directions[0];
    if (d0) d0.trip_s += 12;
    for (const [over, word] of [
      [{ draft: runOf(later, true) }, "draft"],
      [{ updating: true }, "updating"],
    ] as const) {
      const v = view(0, 29540, 700);
      const { texts, reports } = draw(bandRun(over), v);
      const head = reports.find((r) => r.kind === "run")?.text ?? "";
      const drawn = texts.find((t) => t.s.includes("Towne to Beechgrove") || t.s.includes(word));
      expect(drawn, `the header is drawn (${head})`).toBeTruthy();
      const right = (drawn?.x ?? 0) + (drawn?.s.length ?? 0) * 6;
      expect(right, drawn?.s).toBeLessThanOrEqual(v.plot.x + v.plot.w - RUN_TOGGLE_W);
      expect(drawn?.s).toContain(word);
      expect(drawn?.s).toMatch(/50:\d\d/);
    }
  });

  it("with room, the header keeps the era and train", () => {
    const v = view(0, 29540, 1400);
    const { texts } = draw(bandRun(), v);
    expect(texts.some((t) => t.s.includes("2026, GoA3, Type 2005"))).toBe(true);
  });

  it("the hover readout sits under the header line, clear of the toggle", () => {
    const v0 = view(2000, 4000, 1400);
    const v = view(2000, 4000, 1400, { x: v0.x(3000), y: v0.top + 60 });
    const { marks } = draw(bandRun(), v);
    const ro = marks.find((m) => m.kind === "readout" && m.id === "run") as { y0: number } | undefined;
    expect(ro).toBeTruthy();
    expect(ro?.y0 ?? 0).toBeGreaterThanOrEqual(v.top + 16);
  });

  it("each speed curve comes down to a stand at every stop, as railsim's profile plot did", () => {
    const v = view(0, 29540, 1400);
    const { points } = draw(bandRun(), v);
    const y0 = v.top + RUNTIME_H - 14; // zero speed
    const stops = (colour: string) => points.filter((p) => p.colour === colour && Math.abs(p.y - y0) < 0.5).length;
    const n = RAW.meta.directions[0]?.stations.length ?? 0;
    expect(n).toBeGreaterThan(20);
    // both ends and every stop between: down to the stand and up again from it
    expect(stops("#5aa9e6")).toBeGreaterThanOrEqual(n);
    expect(stops("#e6b450")).toBeGreaterThanOrEqual(n);
  });
});

const ctx = (over: Partial<RunTableCtx> = {}): RunTableCtx => ({
  units: new Units("m"),
  line: "Line 6",
  saved: runOf(meta()),
  draft: null,
  updating: false,
  error: null,
  note: null,
  removed: [],
  dirs: "both",
  narrow: false,
  attribution: null,
  attributionOpen: false,
  act: { select: vi.fn(), hover: vi.fn(), dirs: vi.fn(), attribution: vi.fn(), exportCsv: vi.fn() },
  ...over,
});

describe("the run-time table as Ben reads it", () => {
  it("the train line gives the load as a percentage and the mass in tonnes, as railsim's header did", () => {
    const el = buildRunTable(ctx());
    const line = el.querySelector('[data-dir="1"] .lp-hint')?.textContent ?? "";
    expect(line).toContain("load 50%");
    expect(line).toContain("333 t");
    expect(line).toContain("dry rail");
  });

  it("a narrow sheet shows one direction at a time and says where the other is", () => {
    const el = buildRunTable(ctx({ narrow: true }));
    expect(el.querySelectorAll(".rt-dir")).toHaveLength(1);
    const hint = el.querySelector('[data-testid="run-other-dir"]')?.textContent ?? "";
    expect(hint).toContain("Beechgrove to Towne");
    expect(hint).toContain("Back");
    expect(buildRunTable(ctx({ narrow: true, dirs: "rev" })).querySelector('[data-testid="run-other-dir"]')).toBeNull();
    expect(buildRunTable(ctx()).querySelector('[data-testid="run-other-dir"]')).toBeNull();
  });

  it("the round trip names the turnback at each end in minutes", () => {
    const same = buildRunTable(ctx()).querySelector('[data-testid="run-round-trip"]')?.textContent ?? "";
    expect(same).toContain("Round trip 1:43:07");
    expect(same).toContain("0 min turnback at each end");
    const m = meta();
    m.turnback_s = [180, 240];
    const diff = buildRunTable(ctx({ saved: runOf(m) })).querySelector('[data-testid="run-round-trip"]')?.textContent;
    expect(diff).toContain("turnback 3 min at Towne, 4 min at Beechgrove");
  });
});
