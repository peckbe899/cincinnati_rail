// section.solve@1 as a method: the contract's JSON in and out (schema checked both ways), the same answers as the
// solve on PortInput, the input hash stable, and the RER refused nowhere it is not built (slice 2: no RER test).

import { describe, expect, test } from "vitest";
import { SectionSolveInput, SolvedSection } from "../../src/contract/index.ts";
import { findMethod, METHOD_REFS, solve } from "../../src/index.ts";
import { solveSection } from "../../src/port/model.ts";
import { inputJson } from "../../src/port/wire.ts";
import { integrationInput } from "./integration_input.ts";

describe("section.solve@1", () => {
  test("is served", () => {
    expect(METHOD_REFS).toContain("section.solve@1");
    expect(findMethod("section.solve@1").contracts).toEqual({ input: "section_solve_input", output: "solved_section" });
  });

  test.each(["Line_6", "Line_1", "Line_2b"])("%s: JSON in and out, the same answers as on PortInput", async (line) => {
    const input = integrationInput(line);
    const json = inputJson(input);
    expect(SectionSolveInput.safeParse(json).success).toBe(true);
    const out = (await solve("section.solve", JSON.parse(JSON.stringify(json)), {
      checkOutput: true,
    })) as SolvedSection;
    expect(SolvedSection.safeParse(out).success).toBe(true);
    const direct = solveSection(input);
    expect(out.flags.length).toBe(direct.flags.length);
    expect(out.crossings.length).toBe(direct.crossings.length);
    expect(out.n).toBe(direct.grid.n);
    // the runs tile the line
    for (const runs of [out.type_runs, out.struct_runs, out.phase_runs]) {
      expect(runs[0]?.[1]).toBe(0);
      expect(runs[runs.length - 1]?.[2]).toBe(out.length_m);
      for (let k = 1; k < runs.length; k++) expect(runs[k]?.[1]).toBe(runs[k - 1]?.[2]);
    }
    const len = out.type_runs.reduce((n, r) => n + (r[2] - r[1]), 0);
    expect(len).toBeCloseTo(out.length_m, 6);
    // the drawn types agree sample by sample with the solve
    const at = (c: number) => out.type_runs.find((r) => c >= r[1] && c < r[2])?.[0] ?? out.type_runs.at(-1)?.[0];
    for (let i = 0; i < direct.grid.n; i += 97) expect(at(direct.grid.c[i] as number)).toBe(direct.drawn[i]);
    // two calls, one hash
    const again = (await solve("section.solve", json)) as SolvedSection;
    expect(again.input_hash).toBe(out.input_hash);
    expect(JSON.stringify(again)).toBe(JSON.stringify(out));
  });
});
