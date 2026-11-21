// A sidecar for the engine host's tests: the real serve loop (engine/src/serve.ts) and method table, plus methods
// that misbehave on purpose. Run as: node tests/enginehost/sidecar_fixture.mts
//
//   test.hang      never answers (for timeouts and kills)
//   test.exit      writes to stderr, then exits with code 3 mid-call
//   test.progress  sends progress lines, then answers {done: true}
//   test.close_stdout  closes its stdout pipe (every handle on it) and keeps running without answering (a process
//                      that outlives its reader)

import { closeSync } from "node:fs";
import { serve } from "../../engine/src/serve.ts";

serve({
  intercept: (text, emit) => {
    let req: { id?: number; method?: string } = {};
    try {
      req = JSON.parse(text);
    } catch {
      return undefined;
    }
    switch (req.method) {
      case "test.hang":
        return new Promise(() => {});
      case "test.exit":
        process.stderr.write("fixture: about to exit\nfixture: line two\n");
        process.exit(3);
        return undefined;
      case "test.close_stdout": {
        // Close every handle this process holds on its stdout pipe, so the reader sees EOF while the process runs on.
        // fd 1 alone is enough on POSIX but not on Windows: there libuv gave process.stdout its own duplicate of the
        // pipe handle (uv_pipe_open duplicates the stdio handles), so the pipe stayed open and the call timed out.
        // On POSIX closing the stream's handle leaves fd 1 open (libuv never closes fds 0 to 2), so both are needed.
        (process.stdout as unknown as { _handle?: { close(): void } | null })._handle?.close();
        closeSync(1);
        return new Promise(() => {});
      }
      case "test.progress":
        for (const p of [0.25, 0.5, 0.75]) emit({ id: req.id, progress: p, stage: `stage ${p}` });
        return Promise.resolve({ id: req.id ?? null, ok: true, result: { done: true } });
      default:
        return undefined;
    }
  },
});
