// @cr/engine: the hub's rules engine. Pure TypeScript with no Node or DOM imports, so the sidecar, the CLI and the
// browser worker run the same source (decision 9.20).
//
//   import { solve, METHODS, ENGINE_VERSION } from "@cr/engine";
//   const out = await solve("vertical.rail", sectionInput, { engineBuild });
//
// engine_build is the sha256 of engine/src/** and engine/package.json (engine/PROTOCOL.md). Node computes it from the
// files (src/build.ts); the browser takes it from the server's hello, since a bundle cannot hash its own source.

import { CONTRACTS, canonicalJson } from "./contract/index.ts";
import { METHODS, type MethodCtx, type MethodDef, methodRef } from "./methods.ts";
import { HEX_DIGITS_PER_BYTE, HEX_RADIX } from "./tol.ts";

export { cumulativeLength, lowerBound, type PathPoint, pathAt, segmentAt } from "./geom/path.ts";
export { gridChainage, gridIndex, gridSize } from "./grid.ts";
export { METHODS, type MethodCtx, type MethodDef, methodRef } from "./methods.ts";
export { isRuleId, RULE_IDS, RULE_STATUS, type RuleId } from "./rules.gen.ts";
export type { Design, DesignVertex, ShortCurve } from "./vertical/design.ts";
export { design } from "./vertical/design.ts";
export { sectionDesign, verticalRail } from "./vertical/method.ts";
export { gradeAt, type RailGrid, railAt, railGrid } from "./vertical/rail.ts";
export { type Vertex, type Vertices, vertices } from "./vertical/vertices.ts";

/** The version of engine/package.json (test/engine.test.ts keeps the two equal). */
export const ENGINE_VERSION = "0.0.0";

/** The engine_build used when the caller gives none: no real build hashes to it. */
export const UNKNOWN_BUILD = "0000000000000000000000000000000000000000000000000000000000000000";

/** Every method as name@version, as the hello lists them. */
export const METHOD_REFS: readonly string[] = METHODS.map(methodRef);

/** An error a method call answers with: the protocol's error codes. */
export class EngineFault extends Error {
  readonly code: "bad_request" | "unknown_method" | "invalid_input" | "internal";
  readonly issues: unknown[] | undefined;
  constructor(code: EngineFault["code"], message: string, issues?: unknown[]) {
    super(message);
    this.name = "EngineFault";
    this.code = code;
    this.issues = issues;
  }
}

/** The row for "vertical.rail" or "vertical.rail@1"; a version the engine does not serve is unknown_method. */
export function findMethod(method: string): MethodDef {
  const at = method.indexOf("@");
  const name = at < 0 ? method : method.slice(0, at);
  const version = at < 0 ? null : method.slice(at + 1);
  const row = METHODS.find((m) => m.name === name && (version === null || String(m.version) === version));
  if (!row)
    throw new EngineFault("unknown_method", `no method ${method}; this engine serves ${METHOD_REFS.join(", ")}`);
  return row;
}

/** The lowercase hex sha256 of a UTF-8 string, by WebCrypto (in Node and in browsers). */
export async function sha256Hex(text: string): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (b) => b.toString(HEX_RADIX).padStart(HEX_DIGITS_PER_BYTE, "0")).join("");
}

/** sha256 of the RFC 8785 canonical JSON of a value: a contract output's input_hash. */
export function inputHash(params: unknown): Promise<string> {
  return sha256Hex(canonicalJson(params));
}

export interface SolveOptions {
  /** The engine_build stamped on contract outputs; UNKNOWN_BUILD when not given. */
  engineBuild?: string;
  /** Progress 0 to 1 with a stage name. */
  progress?: MethodCtx["progress"];
  /** Check the output against its contract too (the input is always checked). Default true. */
  checkOutput?: boolean;
}

/**
 * Call a method: validate the input against its contract (invalid_input with zod's issues), run it, stamp
 * engine_build and input_hash on a contract output, and check the output. Throws EngineFault.
 */
export async function solve(method: string, input: unknown, opts: SolveOptions = {}): Promise<unknown> {
  const row = findMethod(method);
  const parsed = row.input.safeParse(input);
  if (!parsed.success) {
    throw new EngineFault(
      "invalid_input",
      `params do not match ${row.contracts.input ?? row.name}: ${parsed.error.issues.length} issue(s)`,
      parsed.error.issues,
    );
  }
  const ctx: MethodCtx = { progress: opts.progress ?? (() => {}) };
  let body: unknown;
  try {
    body = row.run(parsed.data, ctx);
  } catch (e) {
    if (e instanceof EngineFault) throw e;
    throw e instanceof Error ? e : new Error(String(e));
  }
  if (!row.stamped) return body;
  const { contract, ...rest } = body as { contract: string };
  const out = {
    contract,
    engine_build: opts.engineBuild ?? UNKNOWN_BUILD,
    input_hash: await inputHash(parsed.data),
    ...rest,
  };
  if (opts.checkOutput !== false) {
    const checked = row.output.safeParse(out);
    if (!checked.success) {
      throw new Error(`output of ${methodRef(row)} does not match ${row.contracts.output}: ${checked.error.message}`);
    }
  }
  return out;
}

/** The hello a host sends: engine version, build, contract majors and methods. */
export function hello(engineBuild: string): {
  hello: { engine_version: string; engine_build: string; contracts: Record<string, number>; methods: string[] };
} {
  return {
    hello: {
      engine_version: ENGINE_VERSION,
      engine_build: engineBuild,
      contracts: { ...CONTRACTS },
      methods: [...METHOD_REFS],
    },
  };
}
