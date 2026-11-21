// The committed golden files of vertical.rail@1, under engine/test/golden/:
//
// - inputs/<route>.json: the SectionInput of each baseline route on the production 2 m grid (test/fixtures.ts),
//   for tests outside TypeScript (tests/enginehost) and for WP5's record-built inputs to be compared with;
// - vertical_rail.json: for each route, the input_hash and the sha256 of the RFC 8785 JSON of the output without
//   engine_build (which changes with every source edit), plus the log of every accepted change, each with the rule
//   id it was accepted under.
//
// test/golden.bytes.test.ts fails when either drifts; scripts/golden_update.ts rewrites them, and refuses to run
// without a rule id.

import { readFileSync } from "node:fs";
import { canonicalJson, type SectionInput } from "../src/contract/index.ts";
import { sha256Hex, solve } from "../src/index.ts";
import { fixture, ROUTES } from "./fixtures.ts";

export const GOLDEN_DIR = new URL("./golden/", import.meta.url);
export const GOLDEN_FILE = new URL("vertical_rail.json", GOLDEN_DIR);
export const inputFile = (route: string): URL => new URL(`inputs/${route}.json`, GOLDEN_DIR);

export interface GoldenRoute {
  input_hash: string;
  output_sha256: string;
  n: number;
}

export interface GoldenChange {
  rule: string;
  note: string;
  routes: string[];
}

export interface Golden {
  about: string;
  method: string;
  routes: Record<string, GoldenRoute>;
  changes: GoldenChange[];
}

export const ABOUT =
  "vertical.rail@1 outputs for the 41 baseline routes: sha256 of the RFC 8785 JSON of each output without engine_build. " +
  "Written by engine/scripts/golden_update.ts, which needs a rule id; changes lists every accepted change.";

/** The text of an input file as written (scripts/golden_update.ts then formats the folder with Biome). */
export const inputText = (input: SectionInput): string => `${JSON.stringify(input, null, 2)}\n`;

/** The golden entry of one input: what the engine gives for it now. */
export async function goldenOf(input: SectionInput): Promise<GoldenRoute> {
  const out = (await solve("vertical.rail", input)) as {
    engine_build: string;
    input_hash: string;
    grid: { n: number };
  };
  const { engine_build: _, ...rest } = out;
  return { input_hash: out.input_hash, output_sha256: await sha256Hex(canonicalJson(rest)), n: out.grid.n };
}

/** Every route's input and golden entry as the engine gives them now. */
export async function current(): Promise<{ inputs: Map<string, SectionInput>; routes: Record<string, GoldenRoute> }> {
  const inputs = new Map<string, SectionInput>();
  const routes: Record<string, GoldenRoute> = {};
  for (const route of ROUTES) {
    const input = fixture(route);
    inputs.set(route, input);
    routes[route] = await goldenOf(input);
  }
  return { inputs, routes };
}

/** The committed golden file, or null when there is none yet. */
export function committed(): Golden | null {
  try {
    return JSON.parse(readFileSync(GOLDEN_FILE, "utf8")) as Golden;
  } catch {
    return null;
  }
}
