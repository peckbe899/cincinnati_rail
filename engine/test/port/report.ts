// The port's parity report (claude/hub_maps/engine_port_plan.md, section 2): per package, per line and output,
// equal or each difference with where it is and its class. A known difference is classed in classes.yaml beside
// this file (line, output, class, rule or parity item, note), reviewed like a golden update: no rule id, no class.
// A difference with no class is unexplained, and the package's test fails on it.

import { readFileSync, writeFileSync } from "node:fs";
import { parse } from "yaml";
import { RULE_IDS } from "../../src/rules.gen.ts";

export const PORT_TEST_DIR = new URL("./", import.meta.url);

export type DiffClass = "same" | "rule_fix" | "intended" | "unexplained";

export interface ClassEntry {
  package: string;
  /** a line id, or "*" for every line */
  line: string;
  output: string;
  class: Exclude<DiffClass, "unexplained">;
  /** the rule id of a rule fix */
  rule?: string;
  /** the parity matrix item of an intended difference */
  item?: string;
  note: string;
}

export interface Difference {
  /** where: a sample index, a chainage range or a key */
  at: string;
  page: unknown;
  port: unknown;
}

export interface OutputResult {
  output: string;
  /** how many values were compared */
  compared: number;
  differences: Difference[];
  class?: DiffClass;
  rule?: string;
  note?: string;
}

/** The classes of known differences (classes.yaml), checked: a rule fix names a registry rule. */
export function classes(): ClassEntry[] {
  const raw = parse(readFileSync(new URL("classes.yaml", PORT_TEST_DIR), "utf8")) as { classes?: ClassEntry[] } | null;
  const list = raw?.classes ?? [];
  const ids = new Set<string>(RULE_IDS);
  for (const e of list) {
    if (e.class === "rule_fix" && !(e.rule && ids.has(e.rule)))
      throw new Error(`classes.yaml: ${e.package} ${e.line} ${e.output} is a rule fix without a registry rule id`);
    if (e.class === "intended" && !e.item)
      throw new Error(`classes.yaml: ${e.output} is intended without a matrix item`);
  }
  return list;
}

/** The class of an output's differences: equal outputs need none; others take their classes.yaml entry. */
export function classify(pkg: string, line: string, r: OutputResult, list: ClassEntry[] = classes()): OutputResult {
  if (!r.differences.length) return r;
  const e = list.find((x) => x.package === pkg && (x.line === line || x.line === "*") && x.output === r.output);
  if (!e) return { ...r, class: "unexplained" };
  return { ...r, class: e.class, ...(e.rule ? { rule: e.rule } : {}), note: e.note };
}

/** One package's report: per line, each output equal or its differences with their class. */
export interface Report {
  package: string;
  lines: Record<string, Record<string, "equal" | Omit<OutputResult, "output">>>;
}

export function reportOf(pkg: string, byLine: Record<string, OutputResult[]>): Report {
  const lines: Report["lines"] = {};
  for (const [line, results] of Object.entries(byLine)) {
    const o: Record<string, "equal" | Omit<OutputResult, "output">> = {};
    for (const r of results) {
      const { output, ...rest } = r;
      o[output] = r.differences.length ? rest : "equal";
    }
    lines[line] = o;
  }
  return { package: pkg, lines };
}

export function writeReport(r: Report): void {
  writeFileSync(new URL(`report/${r.package}.json`, PORT_TEST_DIR), `${JSON.stringify(r, null, 2)}\n`);
}
