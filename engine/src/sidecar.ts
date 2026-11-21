// The stdio sidecar: node engine/src/sidecar.ts (engine/PROTOCOL.md). The loop is serve.ts; this entry only starts
// it, so importing serve.ts (as the tests do) never starts a sidecar.

import { serve } from "./serve.ts";
import { EXIT_FAILED } from "./tol.ts";

serve().catch((e: unknown) => {
  process.stderr.write(`engine sidecar failed: ${(e as Error)?.stack ?? String(e)}\n`);
  process.exitCode = EXIT_FAILED;
});
