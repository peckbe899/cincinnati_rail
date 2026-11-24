// P1's budget (claude/hub_maps/engine_port_plan.md, section 7.1): solveTypes on Line 6 under 30 ms median in process
// (the old page took 35 ms), on warm runs as test/bench.test.ts does. The budget is held on the main thread's CPU
// time (process.threadCpuUsage, Node 22.19 on; wall clock where it is missing), so a machine busy with other work
// (other sessions, the rest of the suite in parallel) does not fail it; the wall-clock median is printed beside it. The other lines are timed and printed for the report; the
// section's own budget (section.solve@1 under 60 ms on Line 6) is the lead's.

import { describe, expect, test } from "vitest";
import { solveTypes } from "../../../src/port/structure/index.ts";
import { fromGolden, METRO_LINES } from "../from_golden.ts";

const BUDGET_MS = 30;
const WARM = 5;
const RUNS = 21;
const US_PER_MS = 1000;

type CpuUsage = { user: number; system: number };
const threadCpu = (process as unknown as { threadCpuUsage?: (prev?: CpuUsage) => CpuUsage }).threadCpuUsage;

/** The median CPU and wall milliseconds of warm runs. */
function median(line: string): { cpu: number; wall: number } {
  const { model } = fromGolden(line);
  for (let i = 0; i < WARM; i++) solveTypes(model);
  const cpu: number[] = [];
  const wall: number[] = [];
  for (let i = 0; i < RUNS; i++) {
    const t0 = performance.now();
    const c0 = threadCpu?.call(process);
    solveTypes(model);
    const w = performance.now() - t0;
    const dc = c0 ? threadCpu?.call(process, c0) : undefined;
    wall.push(w);
    cpu.push(dc ? (dc.user + dc.system) / US_PER_MS : w);
  }
  const mid = (a: number[]): number => a.sort((x, y) => x - y)[Math.floor(RUNS / 2)] as number;
  return { cpu: mid(cpu), wall: mid(wall) };
}

describe("bench", () => {
  test("solveTypes: Line 6 under 30 ms", () => {
    const { cpu, wall } = median("Line_6");
    console.info(`Line 6 solveTypes: median ${cpu.toFixed(2)} ms CPU, ${wall.toFixed(2)} ms wall, over ${RUNS} runs`);
    expect(cpu).toBeLessThan(BUDGET_MS);
  }, 60_000);

  test("solveTypes: every Metro line, timed", () => {
    const out = METRO_LINES.map((line) => {
      const { cpu, wall } = median(line);
      return `${line} ${cpu.toFixed(1)} ms CPU (${wall.toFixed(1)} wall)`;
    });
    console.info(`solveTypes medians: ${out.join(", ")}`);
    expect(out).toHaveLength(METRO_LINES.length);
  }, 120_000);
});
