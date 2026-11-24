// The line sheet's speed round (profiles_parity.md): a whole-line drag at the old page's frame rate. What the page's
// thread must not do while Ben drags or looks: save the dock's layout for ever, lay a maximised dock out twice per
// save.

import { describe, expect, it } from "vitest";
import { BANDS } from "../../src/plugins/line-sheet/bands.ts";
import { grow, heldInside, railSpan } from "../../src/plugins/line-sheet/dirty.ts";
import {
  type LayerCanvas,
  STATIC_BANDS,
  StaticLayer,
  sameKey,
  staticPrefix,
} from "../../src/plugins/line-sheet/static_layer.ts";
import { layoutSaver, type SaveApi, type SavePanel } from "../../src/shell/layout_save.ts";
import { withoutMaximised } from "../../src/shell/maximise.ts";

/** A dock like dockview's: updateParameters fires a layout change; toJSON on a maximised dock lays it out twice. */
function fakeDock(maximised = false) {
  const log = { layoutChanges: 0, relayouts: 0, toJSON: 0, writes: [] as string[] };
  const panels: SavePanel[] = ["map", "line-sheet"].map((id) => {
    const p: SavePanel = {
      id,
      params: { paneId: id },
      api: {
        updateParameters(next) {
          p.params = next;
          log.layoutChanges++;
        },
      },
    };
    return p;
  });
  const api: SaveApi & { max: boolean } = {
    max: maximised,
    panels,
    hasMaximizedGroup: () => api.max,
    toJSON() {
      log.toJSON++;
      if (api.max) {
        log.relayouts += 2;
        log.layoutChanges += 2;
      }
      return {
        grid: { root: 1, ...(api.max ? { maximizedNode: { location: [1] } } : {}) },
        panels: Object.fromEntries(panels.map((p) => [p.id, { id: p.id, params: p.params }])),
      };
    },
  };
  return { api, panels, log };
}

describe("saving the dock's layout (speed)", () => {
  const states: Record<string, unknown> = { "line-sheet": { range: [0, 100] } };
  const saverOf = (api: SaveApi, log: { writes: string[] }) =>
    layoutSaver({
      api: () => api,
      stateOf: (p) => states[p.id],
      clean: withoutMaximised,
      write: (t) => log.writes.push(t),
    });

  it("a save that changed nothing fires no layout change and writes nothing, so saves do not run for ever", () => {
    const { api, log } = fakeDock();
    const s = saverOf(api, log);
    s.save();
    expect(log.layoutChanges).toBe(1); // the sheet's state went into its params once
    expect(log.writes).toHaveLength(1);
    s.save();
    s.save();
    expect(log.layoutChanges).toBe(1);
    expect(log.writes).toHaveLength(1);
  });

  it("maximised, a save never lays the dock out: it lays the pane states over the docked layout", () => {
    const { api, log } = fakeDock();
    const s = saverOf(api, log);
    s.save();
    api.max = true;
    states["line-sheet"] = { range: [10, 20] };
    s.save();
    expect(log.relayouts).toBe(0);
    expect(log.toJSON).toBe(1);
    const saved = JSON.parse(log.writes.at(-1) as string);
    expect(saved.grid).toEqual({ root: 1 });
    expect(saved.panels["line-sheet"].params.state).toEqual({ range: [10, 20] });
    // docked again: the dock's own layout
    api.max = false;
    s.save();
    expect(log.toJSON).toBe(2);
  });

  it("a session that opens maximised takes the docked layout first (prime), and saves nothing before it", () => {
    const { api, log } = fakeDock();
    const s = saverOf(api, log);
    s.prime();
    api.max = true;
    s.save();
    expect(log.relayouts).toBe(0);
    expect(log.writes).toHaveLength(1);
    const late = fakeDock(true);
    const s2 = saverOf(late.api, late.log);
    s2.save();
    expect(late.log.relayouts).toBe(0);
    expect(late.log.writes).toHaveLength(0);
  });
});

/** A 2D context that records what is done to it. */
function recorder(log: string[]): CanvasRenderingContext2D {
  return new Proxy(
    {},
    {
      get(_t, k) {
        if (k === "globalCompositeOperation") return "source-over";
        return (...a: unknown[]) =>
          log.push(`${String(k)}${a.length ? ` ${a.filter((x) => typeof x === "number").join(",")}` : ""}`);
      },
      set(_t, k, v) {
        log.push(`${String(k)}=${String(v)}`);
        return true;
      },
    },
  ) as unknown as CanvasRenderingContext2D;
}

describe("the static layer (speed)", () => {
  it("is the leading run of the band order that no draft edit changes", () => {
    const n = staticPrefix(BANDS);
    expect(n).toBeGreaterThanOrEqual(5);
    expect(BANDS.slice(0, n).every((b) => STATIC_BANDS.has(b.id))).toBe(true);
    // the rail and everything over it are drawn on each frame
    expect(BANDS.slice(0, n).map((b) => b.id)).not.toContain("rail");
    expect(BANDS.slice(0, n).map((b) => b.id)).not.toContain("outlines");
    expect(staticPrefix([{ id: "rail" }, { id: "axes" }])).toBe(0);
  });

  it("draws its bitmap once per key and copies it on every frame", () => {
    const bgLog: string[] = [];
    const made: LayerCanvas[] = [];
    const layer = new StaticLayer<string>(() => {
      const c = { width: 0, height: 0, getContext: () => recorder(bgLog) };
      made.push(c);
      return c;
    });
    const frame: string[] = [];
    const g = recorder(frame);
    const solved = {};
    let drawn = 0;
    const draw = () => {
      drawn++;
      return "texts";
    };
    for (let i = 0; i < 30; i++)
      expect(layer.paint(g, [1200, 800, 2, 0, 29540, solved], 2400, 1600, draw)).toBe("texts");
    expect(drawn).toBe(1);
    expect(layer.draws).toBe(1);
    expect(made).toHaveLength(1);
    expect(frame.filter((x) => x.startsWith("drawImage"))).toHaveLength(30);
    expect(frame).toContain("globalCompositeOperation=copy");
    // a new solve, a new view or a new size draws it again
    layer.paint(g, [1200, 800, 2, 0, 29540, {}], 2400, 1600, draw);
    layer.paint(g, [1200, 800, 2, 100, 29540, {}], 2400, 1600, draw);
    layer.paint(g, [1200, 800, 2, 100, 29540, {}], 1200, 800, draw);
    expect(drawn).toBe(4);
    expect(sameKey([1, solved], [1, solved])).toBe(true);
    expect(sameKey([1, solved], [1, {}])).toBe(false);
  });
});

describe("a drag step drawn only where it changed (speed)", () => {
  it("finds the stretch of rail a step changed", () => {
    const a = Float64Array.from({ length: 100 }, (_, i) => i);
    const b = a.slice();
    expect(railSpan(a, b)).toBeNull();
    b[40] = 0;
    b[47] = 0;
    expect(railSpan(a, b)).toEqual([40, 47]);
    b[3] = Number.NaN;
    expect(railSpan(a, b)).toEqual([3, 47]);
    expect(railSpan(a, b.slice(0, 50))).toEqual([0, 99]);
  });

  it("grows a region to whole pixels inside the canvas", () => {
    expect(grow({ x: 10.4, y: 5.6, w: 3, h: 2 }, 2, 100, 100)).toEqual({ x: 8, y: 3, w: 8, h: 7 });
    expect(grow({ x: 98, y: -20, w: 10, h: 10 }, 0, 100, 100)).toBeNull();
  });

  it("holds when every changed mark lies inside the regions drawn, and not when one lies outside", () => {
    const rects = [{ x: 100, y: 0, w: 200, h: 800 }];
    const xOf = (c: number) => c / 10;
    const pvi = { kind: "pvi", id: "", c: 2000, z: 150, x: 200, y: 300 };
    const grade = { kind: "grade", id: "", x0: 900, x1: 950, y0: 10, y1: 24 };
    const before = [pvi, grade];
    const moved = [{ ...pvi, z: 149, y: 305 }, grade];
    expect(heldInside(before, moved, rects, xOf, false)).toBe(true);
    // a label far off thinned away (a cascade): drawn whole
    const far = [pvi, { ...grade, x0: 960, x1: 1010 }];
    expect(heldInside(before, far, rects, xOf, false)).toBe(false);
    // one more or one fewer: drawn whole
    expect(heldInside(before, [pvi], rects, xOf, false)).toBe(false);
    // a mark with only a chainage: inside the region when its chainage is
    expect(heldInside([{ kind: "r", id: "", c: 2000 }], [{ kind: "r", id: "", c: 2010 }], rects, xOf, false)).toBe(
      true,
    );
  });

  it("takes a text whose words or showing changed as reaching its rotated label, one whose level moved as a point", () => {
    const rects = [{ x: 100, y: 0, w: 200, h: 800 }];
    const name = {
      kind: "station",
      id: "p",
      text: "Oak, rail 233.4 m",
      c: 2000,
      z: 233.4,
      x: 200,
      y: 290,
      drawn: true,
    };
    const lower = { ...name, text: "Oak, rail 232.1 m", z: 232.1, y: 294 };
    expect(heldInside([name], [lower], rects, (c) => c / 10, true)).toBe(true);
    const hidden = { ...name, drawn: false };
    expect(heldInside([name], [hidden], rects, (c) => c / 10, true)).toBe(false);
  });
});
