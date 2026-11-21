import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { createEngine, EngineUnavailableError, unavailableEngine } from "../../src/engine/client.ts";
import type { EngineWorkerApi } from "../../src/engine/worker.ts";

const ENGINE_INDEX = fileURLToPath(new URL("../../../engine/src/index.ts", import.meta.url));

describe("engine handle", () => {
  it("falls back to the main thread without a worker and solves", async () => {
    const calls: string[] = [];
    const inline: EngineWorkerApi = {
      hello: async () => ({ engine_version: "0.0.0", methods: ["engine.echo@1"], contracts: {} }),
      solve: async (method, input) => {
        calls.push(method);
        return { result: input, ms: 0.1 };
      },
    };
    const e = createEngine({ makeWorker: () => null, inline: async () => inline });
    expect(await e.ready()).toBe(true);
    expect(e.state()).toBe("ready");
    expect(e.hello()?.methods).toEqual(["engine.echo@1"]);
    expect((await e.solve("engine.echo", { a: 1 })).result).toEqual({ a: 1 });
    expect(calls).toEqual(["engine.echo"]);
  });

  it("is unavailable, with a reason, when the engine cannot load", async () => {
    const e = unavailableEngine("WP4 has not landed");
    expect(await e.ready()).toBe(false);
    expect(e.state()).toBe("unavailable");
    expect(e.reason()).toMatch(/WP4 has not landed/);
    await expect(e.solve("vertical.rail", {})).rejects.toBeInstanceOf(EngineUnavailableError);
  });

  it("is unavailable when the hello never comes", async () => {
    const e = createEngine({
      makeWorker: () => null,
      inline: async () => ({ hello: () => new Promise(() => {}), solve: async () => ({ result: null, ms: 0 }) }),
      timeoutMs: 20,
    });
    expect(await e.ready()).toBe(false);
    expect(e.reason()).toMatch(/did not answer within 20 ms/);
  });

  // WP4 builds the engine in parallel: this runs once engine/src/index.ts exists, as the API drift test waits for
  // openapi.json. Until then the fallbacks above are what the app uses.
  it.skipIf(!existsSync(ENGINE_INDEX))("runs the real @cr/engine through the worker API", async () => {
    const api = (await import("../../src/engine/worker.ts")).workerApi;
    const h = await api.hello();
    expect(h.methods).toContain("engine.echo@1");
    expect(h.methods).toContain("vertical.rail@1");
    const echo = await api.solve("engine.echo", { x: [1, 2] });
    expect(echo.result).toEqual({ x: [1, 2] });
  });
});
