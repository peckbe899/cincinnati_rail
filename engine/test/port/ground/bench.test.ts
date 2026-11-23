// P2's time per line (claude/hub_maps/engine_port_plan.md, section 8): the part before the type solve (the ground
// layers, the canon, the sunk box, the rivers and their bands, riverAt) and the part after it (the viaduct spans and
// the made-up bed on P1's solve). Warm runs; each sample is a batch of runs timed on the main thread's CPU
// (process.threadCpuUsage, whose clock ticks in milliseconds here; wall clock where it is missing), so a machine busy
// with other sessions or the rest of the suite does not fail it; the median batch per run is held. The section's own
// budget (section.solve@1 under 60 ms on Line 6) is the lead's; P2's share is held well under it, at 10 ms a line.

import { describe, expect, test } from "vitest";
import {
  buildCanon,
  madeBedArray,
  rebuildGround,
  riverAtArray,
  riverModels,
  sunkBox,
  viaductSpans,
} from "../../../src/port/ground/index.ts";
import { solveTypes, TYPES_MODULE } from "../../../src/port/structure/index.ts";
import { METRO_LINES } from "../from_golden.ts";
import { buildP2 } from "./compare.ts";

const BUDGET_MS = 10;
const WARM = 3;
const RUNS = 11;
const BATCH = 8;
const US_PER_MS = 1000;

type CpuUsage = { user: number; system: number };
const threadCpu = (process as unknown as { threadCpuUsage?: (prev?: CpuUsage) => CpuUsage }).threadCpuUsage;
const clock = (): number => {
  const u = threadCpu?.call(process);
  return u ? (u.user + u.system) / US_PER_MS : performance.now();
};

function median(line: string): { pre: number; post: number } {
  const { model: m, input } = buildP2(line);
  const solve = solveTypes(m);
  const typed = { ...m, types: solve, spans: [] };
  const pre: number[] = [];
  const post: number[] = [];
  for (let k = 0; k < WARM + RUNS; k++) {
    const t0 = clock();
    for (let b = 0; b < BATCH; b++) {
      const g = rebuildGround(input, m.align.gnd, input.rivers);
      const canon = buildCanon(input, m.stations, m.grid);
      const rivers = riverModels(input, g, canon, sunkBox(input));
      riverAtArray(rivers, input.length, input.step);
    }
    const t1 = clock();
    for (let b = 0; b < BATCH; b++) {
      viaductSpans(m, solve, TYPES_MODULE);
      madeBedArray(typed, TYPES_MODULE);
    }
    const t2 = clock();
    if (k >= WARM) {
      pre.push((t1 - t0) / BATCH);
      post.push((t2 - t1) / BATCH);
    }
  }
  const mid = (a: number[]): number => a.sort((x, y) => x - y)[Math.floor(RUNS / 2)] as number;
  return { pre: mid(pre), post: mid(post) };
}

describe("bench", () => {
  test("P2 on every Metro line: under 10 ms a line, before and after the type solve together", () => {
    const out = METRO_LINES.map((line) => ({ line, ...median(line) }));
    console.info(
      `P2 medians (CPU ms, before + after the type solve): ${out.map((o) => `${o.line} ${o.pre.toFixed(2)} + ${o.post.toFixed(2)}`).join(", ")}`,
    );
    for (const o of out) expect(o.pre + o.post, o.line).toBeLessThan(BUDGET_MS);
  }, 120_000);
});
