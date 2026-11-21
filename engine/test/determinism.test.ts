// vertical.rail is pure: the same input gives the same bytes on every run, and the order the PVIs (and the
// stations, which carry their own order) arrive in changes nothing but input_hash, which hashes the input as sent.

import fc from "fast-check";
import { describe, expect, test } from "vitest";
import type { SectionInput } from "../src/contract/index.ts";
import { solve } from "../src/index.ts";
import { fixture } from "./fixtures.ts";

const SAMPLE_ROUTES = ["Line_6", "CVG_Express", "Line_8", "RER_E_trunk", "RER_A_cumminsville"];

/** The output bytes, without input_hash (the only member that hashes the input as sent). */
async function bytes(input: SectionInput): Promise<string> {
  const { input_hash: _, ...rest } = (await solve("vertical.rail", input)) as Record<string, unknown>;
  return JSON.stringify(rest);
}

function permute<T>(items: readonly T[], keys: readonly number[]): T[] {
  return items
    .map((v, i) => [v, keys[i % keys.length] as number, i] as const)
    .sort((a, b) => a[1] - b[1] || a[2] - b[2])
    .map(([v]) => v);
}

describe("determinism", () => {
  test("same bytes across runs and PVI permutations", async () => {
    for (const route of SAMPLE_ROUTES) {
      const input = fixture(route);
      const first = JSON.stringify(await solve("vertical.rail", input));
      expect(JSON.stringify(await solve("vertical.rail", structuredClone(input))), `${route}: second run`).toBe(first);
      const want = await bytes(input);
      await fc.assert(
        fc.asyncProperty(fc.array(fc.integer(), { minLength: 1, maxLength: 64 }), async (keys) => {
          const pvi = permute(input.pvi, keys);
          const stations = permute(input.stations, [...keys].reverse());
          expect(await bytes({ ...input, pvi })).toBe(want);
          expect(await bytes({ ...input, pvi, stations })).toBe(want);
        }),
        { numRuns: 15 },
      );
    }
  });

  test("input_hash is the sha256 of the canonical input", async () => {
    const input = fixture("Line_6");
    const out = (await solve("vertical.rail", input)) as { input_hash: string };
    const shuffled = { ...input, pvi: [...input.pvi].reverse() };
    const other = (await solve("vertical.rail", shuffled)) as { input_hash: string };
    expect(out.input_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(other.input_hash).not.toBe(out.input_hash);
    // key order does not matter: the hash is over RFC 8785 JSON
    const reordered = Object.fromEntries(Object.entries(input).reverse()) as SectionInput;
    expect(((await solve("vertical.rail", reordered)) as { input_hash: string }).input_hash).toBe(out.input_hash);
  });
});
