// The NDJSON serve loop of the sidecar (engine/PROTOCOL.md); node engine/src/sidecar.ts runs it on stdio.
//
// It writes its hello first, then answers one NDJSON request per line, possibly out of order. stdout carries
// protocol lines only; anything else goes to stderr. It exits when stdin reaches EOF (Windows does not kill orphans,
// so this is how a sidecar outlives no parent), once the requests it has started are answered.

import { createInterface } from "node:readline";
import { engineBuild } from "./build.ts";
import { handle, line, type Reply } from "./host.ts";
import { hello } from "./index.ts";

export interface ServeOptions {
  /** engine_build for the hello and every output; computed from the files when not given. */
  engineBuild?: string;
  input?: NodeJS.ReadableStream;
  output?: NodeJS.WritableStream;
  /** Tests only: answer a request line before the method table sees it (return undefined to pass it on). */
  intercept?: (text: string, emit: (msg: unknown) => void) => Promise<Reply> | undefined;
}

/** Serve requests until the input ends. Resolves when every started request has been answered. */
export function serve(opts: ServeOptions = {}): Promise<void> {
  const build = opts.engineBuild ?? engineBuild();
  const input = opts.input ?? process.stdin;
  const output = opts.output ?? process.stdout;
  const write = (msg: unknown): void => {
    output.write(`${line(msg)}\n`);
  };
  // a reader that went away (EPIPE) is not an error worth dying of: the requests are lost either way
  output.on("error", () => {});
  write(hello(build));
  const pending = new Set<Promise<void>>();
  const rl = createInterface({ input, crlfDelay: Number.POSITIVE_INFINITY });
  rl.on("line", (text) => {
    if (!text.trim()) return;
    const answer = opts.intercept?.(text, write) ?? handle(text, { engineBuild: build, emit: write });
    const job: Promise<void> = answer
      .then(write, (e: unknown) => {
        process.stderr.write(`engine sidecar: ${(e as Error)?.stack ?? String(e)}\n`);
      })
      .finally(() => {
        pending.delete(job);
      });
    pending.add(job);
  });
  return new Promise((resolve) => {
    rl.on("close", () => {
      Promise.allSettled([...pending]).then(() => resolve());
    });
  });
}
