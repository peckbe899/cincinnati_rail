// vertical.rail@1 gives the committed bytes (engine/test/golden/vertical_rail.json) for the committed inputs
// (engine/test/golden/inputs/). A change of either is accepted only through scripts/golden_update.ts with a rule id.

import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";
import type { SectionInput } from "../src/contract/index.ts";
import { isRuleId } from "../src/index.ts";
import { ROUTES } from "./fixtures.ts";
import { committed, current, goldenOf, inputFile } from "./golden_files.ts";

const STALE = "accept it with npm run golden:update -w engine -- --rule <rule id> --note <why>";
const ENGINE_DIR = fileURLToPath(new URL("..", import.meta.url));

/** npm's own script, run by this Node: npm_execpath when npm started the tests, else the npm installed beside this
 * Node (bin/../lib/node_modules on POSIX, the same folder on Windows). Running it with process.execPath avoids
 * spawning npm.cmd, which Node refuses without a shell on Windows. */
function npmCli(): string | null {
  const fromNpm = process.env.npm_execpath;
  if (fromNpm && /\.c?js$/.test(fromNpm) && existsSync(fromNpm)) return fromNpm;
  const bin = dirname(process.execPath);
  for (const root of [join(bin, "node_modules"), join(dirname(bin), "lib", "node_modules")]) {
    const cli = join(root, "npm", "bin", "npm-cli.js");
    if (existsSync(cli)) return cli;
  }
  return null;
}

/** `npm run --silent <args>` in engine/, as Ben would type it. */
function npmRun(args: string[]) {
  const opts = { cwd: ENGINE_DIR, encoding: "utf8" as const };
  const cli = npmCli();
  if (cli) return spawnSync(process.execPath, [cli, "run", "--silent", ...args], opts);
  return spawnSync(["npm", "run", "--silent", ...args].join(" "), { ...opts, shell: true });
}

describe("golden bytes", () => {
  test("the committed inputs are the fixtures, and the outputs hash as committed", async () => {
    const golden = committed();
    expect(golden, "engine/test/golden/vertical_rail.json is missing").not.toBeNull();
    const now = await current();
    for (const route of ROUTES) {
      const input = JSON.parse(readFileSync(inputFile(route), "utf8")) as SectionInput;
      expect(input, `${route}: the golden input is stale: ${STALE}`).toEqual(now.inputs.get(route));
      expect(await goldenOf(input), `${route}: the output changed: ${STALE}`).toEqual(golden?.routes[route]);
    }
    expect(Object.keys(golden?.routes ?? {}).sort()).toEqual([...ROUTES]);
    for (const change of golden?.changes ?? []) expect(isRuleId(change.rule), change.rule).toBe(true);
  });

  test("npm run golden:update refuses to run without a rule id", () => {
    const none = npmRun(["golden:update"]);
    expect(none.status, none.stderr).toBe(2);
    expect(none.stderr).toMatch(/refused/);
    const bogus = npmRun(["golden:update", "--", "--rule", "no.such.rule"]);
    expect(bogus.status, bogus.stderr).toBe(2);
    expect(bogus.stderr).toMatch(/not a rule id/);
  });
});
