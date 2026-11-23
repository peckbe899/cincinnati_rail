// The sidecar and the CLI as processes, speaking engine/PROTOCOL.md.

import { type ChildProcessWithoutNullStreams, spawn, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, test } from "vitest";
import { engineBuild } from "../src/build.ts";
import { Hello, Response } from "../src/contract/index.ts";
import { ENGINE_VERSION, METHOD_REFS, solve } from "../src/index.ts";
import { fixture } from "./fixtures.ts";

const ENGINE = fileURLToPath(new URL("../", import.meta.url));
const SIDECAR = join(ENGINE, "src", "sidecar.ts");
const CLI = join(ENGINE, "src", "cli.ts");

interface Sidecar {
  proc: ChildProcessWithoutNullStreams;
  next(): Promise<Record<string, unknown>>;
  send(msg: unknown): void;
}

const running: ChildProcessWithoutNullStreams[] = [];

function start(): Sidecar {
  const proc = spawn(process.execPath, [SIDECAR], { cwd: ENGINE, stdio: ["pipe", "pipe", "pipe"] });
  running.push(proc);
  const lines: string[] = [];
  const waiters: ((s: string) => void)[] = [];
  createInterface({ input: proc.stdout }).on("line", (s) => {
    const w = waiters.shift();
    if (w) w(s);
    else lines.push(s);
  });
  return {
    proc,
    next: () =>
      new Promise((resolve) => {
        const s = lines.shift();
        if (s !== undefined) resolve(JSON.parse(s));
        else waiters.push((t) => resolve(JSON.parse(t)));
      }),
    send: (msg) => {
      proc.stdin.write(`${typeof msg === "string" ? msg : JSON.stringify(msg)}\n`);
    },
  };
}

afterEach(() => {
  for (const p of running.splice(0)) p.kill();
});

describe("sidecar", () => {
  test("hello then echo over NDJSON", async () => {
    const sc = start();
    const hello = await sc.next();
    expect(Hello.safeParse(hello).success).toBe(true);
    expect(hello).toEqual({
      hello: {
        engine_version: ENGINE_VERSION,
        engine_build: engineBuild(),
        contracts: {
          section_input: 0,
          vertical_rail: 0,
          station_input: 0,
          station_facts: 0,
          section_solve_input: 0,
          solved_section: 0,
          section_propose_input: 0,
          section_proposal: 0,
        },
        methods: [...METHOD_REFS],
      },
    });
    sc.send({ id: 7, method: "engine.echo", params: { a: [1, 2.5, "x"], b: null } });
    const reply = await sc.next();
    expect(reply).toEqual({ id: 7, ok: true, result: { a: [1, 2.5, "x"], b: null } });
    expect(Response.safeParse(reply).success).toBe(true);
  });

  test("errors carry the protocol codes; a bad line gets id null", async () => {
    const sc = start();
    await sc.next();
    sc.send("this is not json");
    expect(await sc.next()).toMatchObject({ id: null, ok: false, error: { code: "bad_request" } });
    sc.send({ id: 3, method: "no.such", params: {} });
    expect(await sc.next()).toMatchObject({ id: 3, ok: false, error: { code: "unknown_method" } });
    sc.send({ id: 4, method: "vertical.rail@9", params: {} });
    expect(await sc.next()).toMatchObject({ id: 4, ok: false, error: { code: "unknown_method" } });
    sc.send({ id: 5, method: "vertical.rail", params: { contract: "section_input/0" } });
    const bad = await sc.next();
    expect(bad).toMatchObject({ id: 5, ok: false, error: { code: "invalid_input" } });
    expect(Array.isArray((bad.error as { issues: unknown[] }).issues)).toBe(true);
    sc.send({ id: 6, method: "engine.echo" });
    expect(await sc.next()).toMatchObject({ id: 6, ok: false, error: { code: "bad_request" } });
  });

  test("vertical.rail over the sidecar equals solve() in process", async () => {
    const sc = start();
    const hello = (await sc.next()) as { hello: { engine_build: string } };
    const input = fixture("Line_6");
    sc.send({ id: 11, method: "vertical.rail@1", params: input });
    const reply = (await sc.next()) as { id: number; ok: boolean; result: unknown };
    expect(reply.ok).toBe(true);
    expect(JSON.stringify(reply.result)).toBe(
      JSON.stringify(await solve("vertical.rail", input, { engineBuild: hello.hello.engine_build })),
    );
  });

  test("exits on stdin EOF after answering", async () => {
    const sc = start();
    await sc.next();
    sc.send({ id: 1, method: "engine.echo", params: 1 });
    sc.proc.stdin.end();
    const code = await new Promise<number | null>((resolve) => sc.proc.on("exit", (c) => resolve(c)));
    expect(code).toBe(0);
  });
});

describe("cli", () => {
  test("one call, one reply line with id 0; exit 0 when ok, 1 when not", () => {
    const dir = mkdtempSync(join(tmpdir(), "cr-engine-cli-"));
    try {
      const file = join(dir, "input.json");
      writeFileSync(file, JSON.stringify(fixture("Line_2b")), "utf8");
      const ok = spawnSync(process.execPath, [CLI, "vertical.rail", file], { cwd: ENGINE, encoding: "utf8" });
      expect(ok.status).toBe(0);
      const lines = ok.stdout.trim().split("\n");
      expect(lines).toHaveLength(1);
      const reply = JSON.parse(lines[0] as string);
      expect(reply).toMatchObject({ id: 0, ok: true });
      expect(reply.result.engine_build).toBe(engineBuild());

      const piped = spawnSync(process.execPath, [CLI, "engine.echo", "-"], {
        cwd: ENGINE,
        encoding: "utf8",
        input: readFileSync(file, "utf8"),
      });
      expect(piped.status).toBe(0);
      expect(JSON.parse(piped.stdout).result).toEqual(fixture("Line_2b"));

      writeFileSync(file, "{}", "utf8");
      const bad = spawnSync(process.execPath, [CLI, "vertical.rail", file], { cwd: ENGINE, encoding: "utf8" });
      expect(bad.status).toBe(1);
      expect(JSON.parse(bad.stdout)).toMatchObject({ id: 0, ok: false, error: { code: "invalid_input" } });

      const usage = spawnSync(process.execPath, [CLI], { cwd: ENGINE, encoding: "utf8" });
      expect(usage.status).toBe(2);
      expect(JSON.parse(usage.stdout)).toMatchObject({ id: 0, ok: false, error: { code: "bad_request" } });
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
