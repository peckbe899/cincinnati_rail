// A sidecar for the engine host's tests: the real serve loop (engine/src/serve.ts) and method table, plus methods
// that misbehave on purpose. Run as: node tests/enginehost/sidecar_fixture.mts
//
//   test.hang      never answers (for timeouts and kills)
//   test.exit      writes to stderr, then exits with code 3 mid-call
//   test.progress  sends progress lines, then answers {done: true}
//   test.close_stdout  closes its stdout and keeps running without answering (a process that outlives its reader)

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
      case "test.close_stdout":
        closeSync(1);
        return new Promise(() => {});
      case "test.progress":
        for (const p of [0.25, 0.5, 0.75]) emit({ id: req.id, progress: p, stage: `stage ${p}` });
        return Promise.resolve({ id: req.id ?? null, ok: true, result: { done: true } });
      default:
        return undefined;
    }
  },
});
