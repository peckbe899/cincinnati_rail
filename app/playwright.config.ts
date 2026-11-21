// End-to-end tests of the app against a running hub (section 10, WP6). They run at integration, not in the unit
// suite. Point them at a hub serving a fixture database:
//
//   CRHUB_E2E_URL=http://127.0.0.1:8766 npm run e2e -w app
//
// or let Playwright start one from a fixture database (the server restart test always starts its own):
//
//   CRHUB_E2E_DB=/path/to/fixture/region.db npm run e2e -w app
//
// CRHUB_E2E_SERVE overrides the start command as a JSON array, with {db} and {port} placeholders; the default is
// ["python", "-m", "region", "serve", "--db", "{db}", "--port", "{port}", "--no-browser"], run from the repo root.

import { defineConfig, devices } from "@playwright/test";
import { E2E_PORT, serveCommand } from "./e2e/env.ts";

/** One argument for the shell Playwright runs the command in (cmd.exe on Windows, sh elsewhere). JSON quoting would
 * double every backslash of a Windows path and leave $ and backticks live for sh. */
function shellQuote(a: string): string {
  if (/^[A-Za-z0-9_@%+=:,./\\-]+$/.test(a)) return a;
  return process.platform === "win32" ? `"${a}"` : `'${a.replace(/'/g, "'\\''")}'`;
}

const url = process.env.CRHUB_E2E_URL;
const db = process.env.CRHUB_E2E_DB;

export default defineConfig({
  testDir: "e2e",
  testMatch: "**/*.spec.ts",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: url ?? `http://127.0.0.1:${E2E_PORT}`,
    trace: "retain-on-failure",
    viewport: { width: 1600, height: 1000 },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1600, height: 1000 } } }],
  webServer:
    !url && db
      ? {
          command: serveCommand(db, E2E_PORT).map(shellQuote).join(" "),
          cwd: "..",
          url: `http://127.0.0.1:${E2E_PORT}/api/v1/health`,
          timeout: 120_000,
          reuseExistingServer: false,
        }
      : undefined,
});
