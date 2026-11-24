// The budget of section.solve@1 (claude/hub_maps/engine_port_plan.md, section 8): Line 6 under 60 ms median in
// process and every Metro line under 120 ms, by thread CPU time (wall clock where Node has none), as the packages'
// benches measure, so other work on the machine does not count.

import { describe, expect, test } from "vitest";
import { solveSection } from "../../src/port/model.ts";
import { METRO_LINES } from "./from_golden.ts";
import { integrationInput } from "./integration_input.ts";

const cpuMs = (): number => {
  const u = (process as { threadCpuUsage?: () => { user: number; system: number } }).threadCpuUsage?.();
  return u ? (u.user + u.system) / 1000 : performance.now();
};

function median(f: () => void, batches = 7, per = 3): number {
  f();
  const t: number[] = [];
  for (let b = 0; b < batches; b++) {
    const t0 = cpuMs();
    for (let k = 0; k < per; k++) f();
    t.push((cpuMs() - t0) / per);
  }
  t.sort((a, b) => a - b);
  return t[Math.floor(t.length / 2)] as number;
}

describe("section.solve@1 budget", () => {
  const times: Record<string, number> = {};
  test.each(METRO_LINES)("%s under 120 ms", (line) => {
    const input = integrationInput(line);
    const ms = median(() => solveSection(input));
    times[line] = ms;
    expect(ms).toBeLessThan(line === "Line_6" ? 60 : 120);
  });
  test("report", () => {
    console.log(JSON.stringify(times));
  });
});
