// The issue list in the old page's words (claude/hub_maps/profiles_parity.md, R54, R55): for all 16 Metro lines,
// every row of the sheet's issue list reads as the old Rail Profiles page's row, word for word, with its numbers.
//
// The whole solve runs here on the golden adapter's input (engine/test/port/integration_input.ts: the records as the
// old page read them), so its findings are the old page's one for one (engine/test/port/integration.test.ts). The
// station flags are station.facts@1's on the hub's records (fixtures/station_flags.json: station.facts@1 run on the
// station_input/0 of each line from a scratch hub on main, trimmed to the flags). The old rows are the goldens'
// (engine/test/golden/old_page: the page's own issues, with its texts), repeats removed as the page listed them once.
//
// Every difference left is listed below with its reason, and counted; any other fails.

import { readFileSync, writeFileSync } from "node:fs";
import type { StationFact } from "@cr/engine/contract";
import { afterAll, describe, expect, it } from "vitest";
import { solveSection } from "../../../engine/src/port/model.ts";
import { inputJson, solvedJson } from "../../../engine/src/port/wire.ts";
import { distinctIssues } from "../../../engine/test/port/checks/compare.ts";
import { fromGolden, METRO_LINES } from "../../../engine/test/port/from_golden.ts";
import { integrationInput } from "../../../engine/test/port/integration_input.ts";
import { Units } from "../../src/core/units.ts";
import { issueRows } from "../../src/plugins/line-sheet/linepanel.ts";

interface FixtureStation {
  name: string;
  c: number;
  flags: { kind: string; sev: string; rule: string; data: Record<string, unknown> }[];
}
const FACTS = JSON.parse(readFileSync(new URL("./fixtures/station_flags.json", import.meta.url), "utf8")) as Record<
  string,
  FixtureStation[]
>;

/** The station flags of a line as station.facts@1 gives them (only what the issue list reads). */
function factsOf(line: string): { facts: StationFact[]; names: Map<string, string> } {
  const names = new Map<string, string>();
  const facts = (FACTS[line] ?? []).map((s, i) => {
    const id = `P${i}`;
    names.set(id, s.name);
    return { platform_id: id, deleted: false, c_m: s.c, flags: s.flags } as unknown as StationFact;
  });
  return { facts, names };
}

/** The sheet's rows of a line and the old page's, each as "kind|severity|text". */
function rowsOf(line: string): { sheet: string[]; page: string[] } {
  const inp = integrationInput(line);
  const solved = solvedJson(inp, solveSection(inp)) as Parameters<typeof issueRows>[0];
  const { facts, names } = factsOf(line);
  const rows = issueRows(solved, facts, new Units("m"), (p) => names.get(p) ?? p, inputJson(inp));
  const sheet = rows.map((r) => `${r.page}|${r.sev}|${r.text}`);
  const { dump } = fromGolden(line);
  const page = distinctIssues(dump).map((x) => `${x.kind}|${x.sev}|${x.plain}`);
  return { sheet, page };
}

/**
 * The rows that differ, each with its reason (claude/hub_maps/profiles_parity.md). Only the sheet has them; the old
 * page has no row the sheet lacks.
 */
const DOCLESS = new Set(["Line_10", "Line_11", "Line_13"]);
function listed(line: string, row: string): boolean {
  const [page, sev, text] = row.split("|") as [string, string, string];
  // A.1 S57 (interim): a line with no saved levels (Lines 10, 11, 13) has its stations "level not set", read at
  // ground - 7.62 m; the old page solved a level for each (defaultAlign), and said nothing
  if (DOCLESS.has(line) && page === "Level" && sev === "warn" && text.includes(": Level not set: ground − 7.62"))
    return true;
  // S84: read at ground - 7.62 m, these stations are shallower than D_HALL (7.6 m down); defaultAlign put them deeper
  if (
    DOCLESS.has(line) &&
    page === "Access" &&
    sev === "note" &&
    /^[^:]+: an (island|interchange) shallower than D_HALL \(7\.6 of /.test(text)
  )
    return true;
  // S62, S88: Ben's selection of Cut & cover equal to the paint over the centre is kept in the hub (the old page
  // dropped it on load), so the station is a box shallower than D_HALL: a crossunder note the old page had not
  if (line === "Line_2" && page === "Access" && text.startsWith("McMicken: an island shallower than D_HALL"))
    return true;
  if (line === "Line_3" && page === "Access" && text.startsWith("Aloysius: an island shallower than D_HALL"))
    return true;
  // the hub says it laid the saved profile on the route as drawn now (reframeDoc 1838); the old page did it silently
  if (line === "Line_2b" && page === "Reframe" && sev === "note") return true;
  return false;
}

/** The count of listed differences per line, so a listed reason cannot hide a new row of the same kind. */
const LISTED: Record<string, number> = { Line_2: 1, Line_2b: 1, Line_3: 1, Line_10: 34, Line_11: 25, Line_13: 31 };

/** a - b as multisets */
function minus(a: readonly string[], b: readonly string[]): string[] {
  const n = new Map<string, number>();
  for (const x of b) n.set(x, (n.get(x) ?? 0) + 1);
  const out: string[] = [];
  for (const x of a) {
    const k = n.get(x) ?? 0;
    if (k > 0) n.set(x, k - 1);
    else out.push(x);
  }
  return out;
}

describe("the issue list in the old page's words, all 16 Metro lines", () => {
  const results = new Map<string, { onlySheet: string[]; onlyPage: string[]; total: number }>();
  for (const line of METRO_LINES) {
    it(`${line}: every row reads as the old page's`, () => {
      const { sheet, page } = rowsOf(line);
      const onlySheet = minus(sheet, page);
      const onlyPage = minus(page, sheet);
      results.set(line, { onlySheet, onlyPage, total: page.length });
      expect(onlyPage).toEqual([]);
      expect(onlySheet.filter((r) => !listed(line, r))).toEqual([]);
      expect(onlySheet.length).toBe(LISTED[line] ?? 0);
    });
  }
  afterAll(() => {
    const out = process.env.WORDS_REPORT;
    if (out) writeFileSync(out, JSON.stringify(Object.fromEntries(results), null, 1));
  });
});
