// The engine in a Web Worker, over Comlink (section 3: src/engine/worker.ts). It runs the same @cr/engine source as
// the Node sidecar; Vite bundles it into this worker's chunk. The engine is imported lazily, so a missing or broken
// engine build answers hello() with an error instead of killing the worker.

import { expose } from "comlink";

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

export interface EngineWorkerApi {
  hello(): Promise<WorkerHello>;
  solve(method: string, input: unknown, opts?: { engineBuild?: string; checkOutput?: boolean }): Promise<WorkerSolve>;
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
    const result = await e.solve(method, input, {
      engineBuild: opts.engineBuild,
      checkOutput: opts.checkOutput ?? false,
    });
    return { result, ms: performance.now() - t0 };
  },
};

// In a worker, serve the API; when imported on the main thread (the fallback) do nothing.
if (typeof (globalThis as { WorkerGlobalScope?: unknown }).WorkerGlobalScope !== "undefined") expose(workerApi);
