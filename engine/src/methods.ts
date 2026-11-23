// The method table: one row per method the engine serves, shared by the sidecar, the CLI and the browser worker.
//
// A row declares the method's name and version (name@version, the version rises whenever outputs change meaning),
// its input and output contracts with their majors, the rule ids its flags can cite, and the function. Adding a
// method is adding a row here with its zod in and out, a golden or property test, and a regenerated schema.

import { z } from "zod";
import {
  CONTRACTS,
  type ContractName,
  SectionInput,
  StationFacts,
  StationInput,
  VerticalRail,
} from "./contract/index.ts";
import type { RuleId } from "./rules.gen.ts";
import { STATION_FACTS_RULES, stationFacts } from "./station/facts.ts";
import { VERTICAL_RAIL_RULES, verticalRail } from "./vertical/method.ts";

/** What a method may use besides its input. Methods are pure: they read nothing else. */
export interface MethodCtx {
  /** Report progress 0 to 1 with a stage name; the host may drop calls. */
  progress(f: number, stage: string): void;
}

export interface MethodDef {
  /** "vertical.rail" */
  readonly name: string;
  /** 1 */
  readonly version: number;
  /** The input contract and the output contract, by name; their majors are in CONTRACTS. */
  readonly contracts: { readonly input: ContractName | null; readonly output: ContractName | null };
  readonly input: z.ZodType;
  readonly output: z.ZodType;
  /** Members of the output the host fills in: engine_build and input_hash, for contract outputs. */
  readonly stamped: boolean;
  /** The rule ids this method's flags can cite. */
  readonly rules: readonly RuleId[];
  run(input: unknown, ctx: MethodCtx): unknown;
}

export const METHODS: readonly MethodDef[] = [
  {
    name: "vertical.rail",
    version: 1,
    contracts: { input: "section_input", output: "vertical_rail" },
    input: SectionInput,
    output: VerticalRail,
    stamped: true,
    rules: VERTICAL_RAIL_RULES,
    run: (input) => verticalRail(input as SectionInput),
  },
  {
    // What the line sheet shows and sets about each station (claude/hub_maps/profiles_parity.md 0.2); the rail is
    // the section's design, as vertical.rail@1 solves it, so vertical.rail@1 and its goldens do not change.
    name: "station.facts",
    version: 1,
    contracts: { input: "station_input", output: "station_facts" },
    input: StationInput,
    output: StationFacts,
    stamped: true,
    rules: STATION_FACTS_RULES,
    run: (input) => stationFacts(input as StationInput),
  },
  {
    // Returns its params unchanged: a health check and the probe of the round-trip budget.
    name: "engine.echo",
    version: 1,
    contracts: { input: null, output: null },
    input: z.unknown(),
    output: z.unknown(),
    stamped: false,
    rules: [],
    run: (input) => input,
  },
];

/** "vertical.rail@1" for a row. */
export const methodRef = (m: MethodDef): string => `${m.name}@${m.version}`;

/** The contract majors the methods use (CONTRACTS, for the hello). */
export const CONTRACT_MAJORS: Readonly<Record<string, number>> = CONTRACTS;
