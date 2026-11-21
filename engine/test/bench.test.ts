// The engine budget of section 6: Line 6 vertical.rail under 20 ms, measured in process as the median of warm runs
// (the first runs compile). The time includes validating the input and the output against the contract.

import { describe, expect, test } from "vitest";
import { solve } from "../src/index.ts";
import { fixture } from "./fixtures.ts";

const BUDGET_MS = 20;
const WARM = 5;
const RUNS = 25;

describe("bench", () => {
  test("Line 6 under 20 ms", async () => {
    const input = fixture("Line_6");
    for (let i = 0; i < WARM; i++) await solve("vertical.rail", input);
    const times: number[] = [];
    for (let i = 0; i < RUNS; i++) {
      const t0 = performance.now();
      await solve("vertical.rail", input);
      times.push(performance.now() - t0);
    }
    times.sort((a, b) => a - b);
    const median = times[Math.floor(RUNS / 2)] as number;
    console.info(`Line 6 vertical.rail: median ${median.toFixed(2)} ms over ${RUNS} runs`);
    expect(median).toBeLessThan(BUDGET_MS);
  });
});
