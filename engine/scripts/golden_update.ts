// Accept a change of vertical.rail outputs (or of the golden inputs) under a rule id:
//
//   node engine/scripts/golden_update.ts --rule <rule id> [--note "what changed and why"]
//
// It rewrites engine/test/golden/inputs/*.json and engine/test/golden/vertical_rail.json and appends one entry to
// the file's change log naming the rule and the routes whose output changed. It refuses to run without a rule id of
// rules/registry.yaml: an output change is always a rule fix or a ruling, never an unexplained drift. The page
// baseline (tests/baseline/profiles) is never touched by this script.

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { isRuleId, RULE_STATUS } from "../src/index.ts";
import { EXIT_USAGE } from "../src/tol.ts";
import {
  ABOUT,
  committed,
  current,
  GOLDEN_DIR,
  GOLDEN_FILE,
  type Golden,
  inputFile,
  inputText,
} from "../test/golden_files.ts";

function arg(name: string): string | undefined {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

function refuse(message: string): never {
  process.stderr.write(`golden:update refused: ${message}\n`);
  process.stderr.write('usage: node engine/scripts/golden_update.ts --rule <rule id> [--note "why"]\n');
  process.exit(EXIT_USAGE);
}

const rule = arg("--rule");
if (!rule) refuse("it needs the rule id the change is accepted under (--rule)");
if (!isRuleId(rule)) refuse(`${rule} is not a rule id of rules/registry.yaml`);
if (RULE_STATUS[rule] === "superseded") refuse(`${rule} is superseded`);
const note = arg("--note") ?? "";

const before = committed();
const now = await current();
const changed = Object.keys(now.routes).filter(
  (r) => JSON.stringify(before?.routes[r]) !== JSON.stringify(now.routes[r]),
);
const removed = Object.keys(before?.routes ?? {}).filter((r) => !(r in now.routes));

mkdirSync(new URL("inputs/", GOLDEN_DIR), { recursive: true });
const inputsDir = new URL("inputs/", GOLDEN_DIR);
for (const old of readdirSync(inputsDir)) {
  if (old.endsWith(".json") && !now.inputs.has(old.slice(0, -".json".length))) rmSync(new URL(old, inputsDir));
}
for (const [route, input] of now.inputs) writeFileSync(inputFile(route), inputText(input), "utf8");

/** Format the golden folder as Biome does (biome.json checks engine/**), so the files pass npm run lint. */
function format(): void {
  const biome = fileURLToPath(new URL("../../node_modules/@biomejs/biome/bin/biome", import.meta.url));
  if (!existsSync(biome)) {
    process.stderr.write("golden:update: Biome is not installed (npm ci); the files are left unformatted\n");
    return;
  }
  const r = spawnSync(process.execPath, [biome, "format", "--write", fileURLToPath(GOLDEN_DIR)], { encoding: "utf8" });
  if (r.status !== 0) process.stderr.write(`golden:update: biome format failed:\n${r.stdout}${r.stderr}`);
}

if (!changed.length && !removed.length && before) {
  format();
  console.log("golden:update: no output changed; nothing logged");
  process.exit(0);
}
const golden: Golden = {
  about: ABOUT,
  method: "vertical.rail@1",
  routes: now.routes,
  changes: [...(before?.changes ?? []), { rule, note, routes: [...changed, ...removed].sort() }],
};
writeFileSync(GOLDEN_FILE, `${JSON.stringify(golden, null, 2)}\n`, "utf8");
format();
console.log(
  `golden:update: ${changed.length + removed.length} route(s) under ${rule}; wrote ${fileURLToPath(GOLDEN_FILE)}`,
);
