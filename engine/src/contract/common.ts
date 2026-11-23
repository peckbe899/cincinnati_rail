// Shared pieces of engine contract v0: contract majors, units, hashes and canonical JSON.
//
// The engine contract is owned here, in zod, because TypeScript executes it (decision 9.12). scripts/gen_schema.ts
// exports every contract to schema/v0/*.json; Python validates against those files and generates pydantic models
// from them, never the other way round.

import { z } from "zod";

/** The contract majors this engine speaks, sent in the hello. Python refuses a major it does not know. */
export const CONTRACTS = { section_input: 0, vertical_rail: 0, station_input: 0, station_facts: 0 } as const;
export type ContractName = keyof typeof CONTRACTS;

/** Units as in region/kinds/_vocab.yaml. Every number in a contract carries one as x-unit. */
export type Unit = "m" | "mm" | "permille" | "ratio" | "index" | "count" | "s" | "deg" | "year";

/** The metadata of a number field: its unit and a plain description. */
export function unit(u: Unit, description?: string): { "x-unit": Unit; description?: string } {
  return description === undefined ? { "x-unit": u } : { "x-unit": u, description };
}

/** A lowercase sha256 hex digest. */
export const Sha256 = z
  .string()
  .regex(/^[0-9a-f]{64}$/)
  .meta({ description: "A lowercase sha256 hex digest." });

/** The chainage basis every section declares (decision 9.14): UTM 16N grid length, not ground distance. */
export const ChainageBasis = z
  .literal("grid:26916")
  .meta({ description: "Chainage is UTM 16N (EPSG:26916) grid length along the plan geometry (decision 9.14)." });

/**
 * RFC 8785 (JCS) canonical JSON: object keys sorted by UTF-16 code units, no whitespace, numbers as
 * JSON.stringify writes them. region.core.fsio.canonical_json gives the same bytes for the same value, so
 * input_hash = sha256(canonicalJson(params)) agrees between Python and the engine.
 */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value === "boolean" || typeof value === "string") {
    return JSON.stringify(value);
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new TypeError("NaN and infinity have no JSON form");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((v) => canonicalJson(v === undefined ? null : v)).join(",")}]`;
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj)
      .filter((k) => obj[k] !== undefined)
      .sort();
    return `{${keys.map((k) => `${JSON.stringify(k)}:${canonicalJson(obj[k])}`).join(",")}}`;
  }
  throw new TypeError(`${typeof value} has no canonical JSON form`);
}
