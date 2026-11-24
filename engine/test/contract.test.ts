// Contract v0: the committed JSON schemas match the zod source, and the contract behaves as documented.

import { readdirSync, readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { generate, SCHEMA_DIR } from "../scripts/gen_schema.ts";
import { CONTRACTS, canonicalJson, SectionInput, VerticalRail } from "../src/contract/index.ts";

describe("contract v0", () => {
  test("schemas regenerate with no diff", () => {
    const want = generate();
    const have = readdirSync(SCHEMA_DIR)
      .filter((f) => f.endsWith(".json"))
      .sort();
    expect(have).toEqual([...want.keys()].sort());
    for (const [name, content] of want) {
      expect(
        readFileSync(new URL(name, SCHEMA_DIR), "utf8"),
        `schema/v0/${name} is stale: run npm run gen:schema`,
      ).toBe(content);
    }
  });

  test("contract majors are v0", () => {
    expect(CONTRACTS).toEqual({
      section_input: 0,
      vertical_rail: 0,
      station_input: 0,
      station_facts: 0,
      section_solve_input: 0,
      solved_section: 0,
      section_propose_input: 0,
      section_proposal: 0,
    });
  });

  // engine/test/contract.jcs.json holds [value, canonical text] pairs, ASCII-escaped; tests/core/test_core.py checks
  // region.core.fsio.canonical_json against the same file, so Python and the engine hash the same bytes.
  test("canonicalJson follows RFC 8785 and agrees with Python", () => {
    const vectors = JSON.parse(readFileSync(new URL("./contract.jcs.json", import.meta.url), "utf8")) as [
      unknown,
      string,
    ][];
    expect(vectors.length).toBeGreaterThan(0);
    for (const [value, want] of vectors) expect(canonicalJson(value)).toBe(want);
  });

  const input = {
    contract: "section_input/0",
    section_id: "01DXF6DT00G2RN476ZR8N14PM3",
    length_m: 29539.6,
    chainage_basis: "grid:26916",
    scale: 0.99983,
    step_m: 2,
    params: { platform_m: 120, vc_radius_m: 2000, vc_min_len_m: 20 },
    stations: [{ platform_id: "01DXF6DT01AAAAAAAAAAAAAAAA", order: 0, c_m: 60, level_m: null, grade_permille: 0 }],
    pvi: [{ c_m: 1000, z_m: 150.25 }],
  };

  test("a SectionInput parses and an unknown key is refused", () => {
    expect(SectionInput.parse(input)).toEqual(input);
    expect(SectionInput.safeParse({ ...input, extra: 1 }).success).toBe(false);
    expect(SectionInput.safeParse({ ...input, chainage_basis: "ground" }).success).toBe(false);
  });

  test("VerticalRail arrays must have grid.n values", () => {
    const out = {
      contract: "vertical_rail/0",
      engine_build: "0".repeat(64),
      input_hash: "f".repeat(64),
      grid: { c0: 0, step_m: 2, n: 3 },
      rail_m: [150, 150.1, 150.2],
      grade_permille: [5, 5, 5],
      dv: [{ c_m: 0, z_m: 150, kind: "end" }],
      curves: [],
      flags: [{ kind: "grade_over_limit", sev: "warn", c0: 0, c1: 4, rule: "geometry.method.per_stretch", data: {} }],
    };
    expect(VerticalRail.safeParse(out).success).toBe(true);
    expect(VerticalRail.safeParse({ ...out, rail_m: [150] }).success).toBe(false);
  });
});
