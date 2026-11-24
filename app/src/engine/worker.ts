// The engine in a Web Worker, over Comlink (section 3: src/engine/worker.ts). It runs the same @cr/engine source as
// the Node sidecar; Vite bundles it into this worker's chunk. The engine is imported lazily, so a missing or broken
// engine build answers hello() with an error instead of killing the worker.

import { expose, transfer } from "comlink";

export interface WorkerHello {
  engine_version: string;
  methods: string[];
  contracts: Record<string, number>;
}

export interface WorkerSolve {
  result: unknown;
  /** Time spent in solve, in milliseconds. */
  ms: number;
}

export interface SolveOpts {
  engineBuild?: string;
  checkOutput?: boolean;
  /** A stashed input (stash) the call's input is laid over, member by member: a large input crosses to the worker
   * once, and each call sends only what changed. */
  base?: string;
  /** Dotted paths of number arrays in the result to hand back as Float32Array (null as NaN), moved, not copied:
   * a large result costs the page's thread no copy. */
  typed?: readonly string[];
}

export interface EngineWorkerApi {
  hello(): Promise<WorkerHello>;
  solve(method: string, input: unknown, opts?: SolveOpts): Promise<WorkerSolve>;
  /** Keep a value in the worker under a key, for solve's base (optional: a stand-in engine may have none). */
  stash?(key: string, value: unknown): Promise<void>;
}

const stashed = new Map<string, unknown>();

/** The arrays at the dotted paths as Float32Array, and their buffers to move. */
function typedArrays(result: unknown, paths: readonly string[]): ArrayBuffer[] {
  const out: ArrayBuffer[] = [];
  for (const path of paths) {
    const parts = path.split(".");
    let node = result as Record<string, unknown> | null;
    for (const k of parts.slice(0, -1)) node = (node?.[k] as Record<string, unknown> | undefined) ?? null;
    const last = parts[parts.length - 1] as string;
    const arr = node?.[last];
    if (!node || !Array.isArray(arr)) continue;
    const f = Float32Array.from(arr as (number | null)[], (v) => (v == null ? Number.NaN : v));
    node[last] = f;
    out.push(f.buffer);
  }
  return out;
}

type EngineModule = typeof import("@cr/engine");

let engine: Promise<EngineModule> | null = null;
const load = (): Promise<EngineModule> => {
  engine ??= (async () => {
    // The hub's CSP has no 'unsafe-eval'. zod (the engine's contract library) probes new Function() unless told
    // not to, and Chromium reports that probe as a CSP violation even though zod catches it. jitless skips it.
    // app/package.json declares zod at the engine's version, so npm dedupes the two to one copy and this config
    // reaches the zod the engine uses.
    const zod = await import("zod");
    zod.config({ jitless: true });
    return import("@cr/engine");
  })();
  return engine;
};

export const workerApi: EngineWorkerApi = {
  async hello() {
    const e = await load();
    const h = e.hello(e.UNKNOWN_BUILD).hello;
    return { engine_version: h.engine_version, methods: h.methods, contracts: h.contracts };
  },
  async solve(method, input, opts = {}) {
    const e = await load();
    const t0 = performance.now();
    const base = opts.base === undefined ? undefined : stashed.get(opts.base);
    if (opts.base !== undefined && base === undefined) throw new Error(`nothing stashed as ${opts.base}`);
    const full = base ? { ...(base as Record<string, unknown>), ...(input as Record<string, unknown>) } : input;
    const result = await e.solve(method, full, {
      engineBuild: opts.engineBuild,
      checkOutput: opts.checkOutput ?? false,
    });
    const out = { result, ms: performance.now() - t0 };
    if (!opts.typed?.length) return out;
    const buffers = typedArrays(result, opts.typed);
    // in a worker, move the buffers; on the main thread (the fallback) transfer only marks them, harmlessly
    return transfer(out, buffers);
  },
  async stash(key, value) {
    stashed.set(key, value);
  },
};

// In a worker, serve the API; when imported on the main thread (the fallback) do nothing.
if (typeof (globalThis as { WorkerGlobalScope?: unknown }).WorkerGlobalScope !== "undefined") expose(workerApi);
