// The app's handle on the engine: a small interface so the line sheet never depends on how the engine runs.
//
// createEngine() starts the Comlink worker (engine/worker.ts). If the browser cannot start it, the engine runs on
// the main thread instead; if the engine itself cannot load (WP4's @cr/engine missing or broken), the handle is
// "unavailable" with a plain reason, solve() rejects with EngineUnavailableError, and the line sheet carries on
// without local solves: saves still work and the server's result arrives over SSE.

import { type Remote, wrap } from "comlink";
import type { EngineWorkerApi, SolveOpts, WorkerHello, WorkerSolve } from "./worker.ts";

export type EngineState = "loading" | "ready" | "unavailable";

export class EngineUnavailableError extends Error {
  constructor(reason: string) {
    super(reason);
    this.name = "EngineUnavailableError";
  }
}

export interface EngineHandle {
  state(): EngineState;
  reason(): string | null;
  hello(): WorkerHello | null;
  /** Resolves true once the engine answered its hello, false when it is unavailable. */
  ready(): Promise<boolean>;
  solve(method: string, input: unknown, opts?: SolveOpts): Promise<WorkerSolve>;
  /** Keep a value in the worker under a key (solve's base). */
  stash(key: string, value: unknown): Promise<void>;
  onChange(fn: (s: EngineState) => void): () => void;
  dispose(): void;
}

export interface EngineOptions {
  /** Make the worker; by default the bundled engine/worker.ts. Return null to skip the worker. */
  makeWorker?: () => Worker | null;
  /** Load the API on the main thread when there is no worker. */
  inline?: () => Promise<EngineWorkerApi>;
  /** How long the hello may take. */
  timeoutMs?: number;
}

function withTimeout<T>(p: Promise<T>, ms: number, what: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const t = setTimeout(() => reject(new Error(`${what} did not answer within ${ms} ms`)), ms);
    p.then(
      (v) => {
        clearTimeout(t);
        resolve(v);
      },
      (e) => {
        clearTimeout(t);
        reject(e);
      },
    );
  });
}

const defaultWorker = (): Worker | null =>
  typeof Worker === "undefined"
    ? null
    : new Worker(new URL("./worker.ts", import.meta.url), { type: "module", name: "cr-engine" });

const defaultInline = async (): Promise<EngineWorkerApi> => (await import("./worker.ts")).workerApi;

export function createEngine(o: EngineOptions = {}): EngineHandle {
  let state: EngineState = "loading";
  let reason: string | null = null;
  let hello: WorkerHello | null = null;
  let worker: Worker | null = null;
  const subs = new Set<(s: EngineState) => void>();
  const set = (s: EngineState, why: string | null = null) => {
    state = s;
    reason = why;
    for (const fn of [...subs]) fn(s);
  };

  const api: Promise<EngineWorkerApi | Remote<EngineWorkerApi>> = (async () => {
    try {
      worker = (o.makeWorker ?? defaultWorker)();
    } catch (e) {
      console.warn("engine worker could not start; solving on the main thread", e);
      worker = null;
    }
    if (worker) {
      const failed = new Promise<never>((_, reject) => {
        worker?.addEventListener("error", (ev) =>
          reject(new Error(`engine worker failed: ${(ev as ErrorEvent).message ?? "error"}`)),
        );
      });
      const remote = wrap<EngineWorkerApi>(worker);
      hello = await withTimeout(Promise.race([remote.hello(), failed]), o.timeoutMs ?? 15_000, "the engine worker");
      return remote;
    }
    const inline = await (o.inline ?? defaultInline)();
    hello = await withTimeout(inline.hello(), o.timeoutMs ?? 15_000, "the engine");
    return inline;
  })();

  const ready = api.then(
    () => {
      set("ready");
      return true;
    },
    (e: unknown) => {
      set("unavailable", `The local engine is unavailable: ${(e as Error)?.message ?? String(e)}`);
      worker?.terminate();
      return false;
    },
  );

  return {
    state: () => state,
    reason: () => reason,
    hello: () => hello,
    ready: () => ready,
    async solve(method, input, opts) {
      if (!(await ready)) throw new EngineUnavailableError(reason ?? "The local engine is unavailable.");
      return (await api).solve(method, input, opts);
    },
    async stash(key, value) {
      if (!(await ready)) throw new EngineUnavailableError(reason ?? "The local engine is unavailable.");
      const a = (await api) as EngineWorkerApi;
      if (typeof a.stash !== "function") throw new EngineUnavailableError("This engine keeps no stash.");
      await a.stash(key, value);
    },
    onChange(fn) {
      subs.add(fn);
      return () => subs.delete(fn);
    },
    dispose() {
      worker?.terminate();
      worker = null;
    },
  };
}

/** A handle that is unavailable from the start (tests, and pages that never solve). */
export function unavailableEngine(why = "No local engine in this page."): EngineHandle {
  return createEngine({
    makeWorker: () => null,
    inline: () => Promise.reject(new Error(why)),
  });
}
