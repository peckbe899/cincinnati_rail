// P3's share of the section solve's budget (claude/hub_maps/engine_port_plan.md, section 8: section.solve@1 on
// Line 6 under 60 ms median in process): the crossings, context clearances, road checks and every station's street of
// a line, on warm runs, as the structure bench does. Held on the main thread's CPU time (process.threadCpuUsage; wall
// clock where it is missing), so a machine busy with other work does not fail it. Every Metro line is timed.

import { describe, expect, test } from "vitest";
import { contextClearances, crossingClearances, roadChecks, stationStreet } from "../../../src/port/crossings/index.ts";
import { TYPES_MODULE } from "../../../src/port/structure/index.ts";
import { METRO_LINES } from "../from_golden.ts";
import { crossingModel } from "./neighbours.ts";

/** P3's share on Line 6: a tenth of the section's 60 ms. */
const BUDGET_MS = 6;
const WARM = 5;
const RUNS = 21;
/** Runs per sample: the thread's CPU clock ticks in milliseconds, coarser than one run. */
const BATCH = 10;
const US_PER_MS = 1000;

type CpuUsage = { user: number; system: number };
const threadCpu = (process as unknown as { threadCpuUsage?: (prev?: CpuUsage) => CpuUsage }).threadCpuUsage;

function all(line: string): void {
  const m = crossingModel(line);
  crossingClearances(m, TYPES_MODULE);
  contextClearances(m, TYPES_MODULE);
  roadChecks(m, TYPES_MODULE);
  for (const s of m.stations) stationStreet(m, s);
}

/** The median CPU and wall milliseconds of a run, over warm samples of BATCH runs. */
function p3Median(line: string): { cpu: number; wall: number } {
  for (let i = 0; i < WARM; i++) all(line);
  const cpu: number[] = [];
  const wall: number[] = [];
  for (let i = 0; i < RUNS; i++) {
    const t0 = performance.now();
    const c0 = threadCpu?.call(process);
    for (let k = 0; k < BATCH; k++) all(line);
    const w = (performance.now() - t0) / BATCH;
    const dc = c0 ? threadCpu?.call(process, c0) : undefined;
    wall.push(w);
    cpu.push(dc ? (dc.user + dc.system) / US_PER_MS / BATCH : w);
  }
  const mid = (a: number[]): number => a.sort((x, y) => x - y)[Math.floor(RUNS / 2)] as number;
  return { cpu: mid(cpu), wall: mid(wall) };
}

describe("bench", () => {
  test("crossings, context, roads and streets: Line 6 under 6 ms", () => {
    const { cpu, wall } = p3Median("Line_6");
    console.info(
      `Line 6 P3: median ${cpu.toFixed(2)} ms CPU, ${wall.toFixed(2)} ms wall, over ${RUNS} samples of ${BATCH} runs`,
    );
    expect(cpu).toBeLessThan(BUDGET_MS);
  }, 60_000);

  test("every Metro line, timed", () => {
    const out = METRO_LINES.map((line) => {
      const { cpu, wall } = p3Median(line);
      return `${line} ${cpu.toFixed(2)} ms CPU (${wall.toFixed(2)} wall)`;
    });
    console.info(`P3 medians: ${out.join(", ")}`);
    expect(out).toHaveLength(METRO_LINES.length);
  }, 120_000);
});
