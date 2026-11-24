// P4's timing (claude/hub_maps/engine_port_plan.md, sections 7.4 and 8): the checks a solve runs after the type
// solve (radii and curve allowance, drawing, drawn ground, design checks with the curve grade, summary, river checks,
// allIssues) and the levels it runs before (alignFromDoc with the level solver, on P2's and P1's real functions),
// per Metro line, median of warm runs, on the main thread's CPU time (process.threadCpuUsage, a batch of calls per sample; wall clock
// where it is missing) with the wall-clock median beside it. Propose fill runs on a button, not on a solve: timed per proposal.
// The page took 50 to 70 ms for its summary and checks on Lines 5, 6 and 14; the budget held here is P4's share of
// section.solve@1's 60 ms on Line 6 (the lead's).

import { describe, expect, test } from "vitest";
import {
  allIssues,
  computeSummary,
  curveAllowance,
  designChecks,
  drawingFlags,
  gndChecks,
  proposeFill,
  radii,
  riverChecks,
} from "../../../src/port/checks/index.ts";
import { alignFromDoc } from "../../../src/port/levels/index.ts";
import { TYPES_MODULE } from "../../../src/port/structure/index.ts";
import type { TypedModel } from "../../../src/port/types.ts";
import { fromGolden, goldenMisfits, METRO_LINES, typedFromGolden } from "../from_golden.ts";
import { ALIGN_DEPS, goldenContext, goldenCrossings, goldenRoads, goldenStationFlags, levelInput } from "./input.ts";

const CHECKS_BUDGET_MS = 30;
const LEVELS_BUDGET_MS = 15;
const WARM = 3;
const RUNS = 11;
/** Calls per timed sample: the thread CPU clock ticks in milliseconds on some machines, so each sample times a batch. */
const BATCH = 8;
const US_PER_MS = 1000;

type CpuUsage = { user: number; system: number };
const threadCpu = (process as unknown as { threadCpuUsage?: (prev?: CpuUsage) => CpuUsage }).threadCpuUsage;

function median(run: () => void): { cpu: number; wall: number } {
  for (let i = 0; i < WARM; i++) run();
  const cpu: number[] = [];
  const wall: number[] = [];
  for (let i = 0; i < RUNS; i++) {
    const t0 = performance.now();
    const c0 = threadCpu?.call(process);
    for (let k = 0; k < BATCH; k++) run();
    const w = (performance.now() - t0) / BATCH;
    const dc = c0 ? threadCpu?.call(process, c0) : undefined;
    wall.push(w);
    cpu.push(dc ? (dc.user + dc.system) / US_PER_MS / BATCH : w);
  }
  const mid = (a: number[]): number => a.sort((x, y) => x - y)[Math.floor(RUNS / 2)] as number;
  return { cpu: mid(cpu), wall: mid(wall) };
}

/** Everything P4 checks on a solved line, as section.solve@1 will run it. */
function checks(line: string): () => void {
  const m: TypedModel = typedFromGolden(line);
  const { dump, input } = fromGolden(line);
  const T = TYPES_MODULE;
  const crossings = goldenCrossings(dump);
  const context = goldenContext(dump);
  const roads = goldenRoads(dump, input);
  const stations = goldenStationFlags(dump);
  const misfits = goldenMisfits(dump);
  return () => {
    const R = radii(input.path, input.length, input.literals);
    curveAllowance(R, input.settings);
    const drawing = drawingFlags(input.path, input.pieces, input.literals);
    const ground = gndChecks(m);
    const design = designChecks(m, T);
    const summary = computeSummary(m, T);
    const rivers = riverChecks(m, T);
    allIssues(
      {
        over: summary.over,
        crossings,
        context,
        rivers,
        roads,
        stations,
        deepShallow: summary.deepShallow,
        checks: [...design.flags, ...drawing],
        ground,
        types: m.types,
        misfits,
      },
      { half: m.settings.platform / 2 },
    );
  };
}

const levels = (line: string): (() => void) => {
  const input = levelInput(line);
  return () => {
    alignFromDoc(input, ALIGN_DEPS);
  };
};

describe("bench", () => {
  test("checks: Line 6 under 30 ms; levels: Line 6 under 15 ms", () => {
    const c = median(checks("Line_6"));
    const l = median(levels("Line_6"));
    console.info(
      `Line 6 checks: ${c.cpu.toFixed(2)} ms CPU (${c.wall.toFixed(2)} wall); levels: ${l.cpu.toFixed(2)} ms CPU (${l.wall.toFixed(2)} wall)`,
    );
    expect(c.cpu).toBeLessThan(CHECKS_BUDGET_MS);
    expect(l.cpu).toBeLessThan(LEVELS_BUDGET_MS);
  }, 60_000);

  test("every Metro line, timed (checks, levels, Propose fill per proposal)", () => {
    const out = METRO_LINES.map((line) => {
      const c = median(checks(line));
      const l = median(levels(line));
      const m = typedFromGolden(line);
      const fills = fromGolden(line).dump.levels.propose_fill;
      const f = fills.length
        ? median(() => {
            for (const p of fills) proposeFill(m, p.c0, p.c1, TYPES_MODULE);
          })
        : null;
      return `${line} checks ${c.cpu.toFixed(1)} (${c.wall.toFixed(1)}) levels ${l.cpu.toFixed(1)} (${l.wall.toFixed(1)}) fill ${
        f ? (f.cpu / fills.length).toFixed(2) : "-"
      }`;
    });
    console.info(`P4 medians, ms CPU (wall):\n${out.join("\n")}`);
    expect(out).toHaveLength(METRO_LINES.length);
  }, 180_000);
});
