// The hover readout against the old page's (claude/hub_maps/profiles_parity.md, R47), at 112 points: seven places
// along each of the 16 Metro lines (a tenth to 95 % of the way), each row as the old readout wrote it.
//
// The old rows are the old page's own readout at those chainages (fixtures/old_readout.json: its #readout text,
// from a scratch copy of the old hub on the seed, the parity prove of 23 November). The sheet's rows come from the
// whole solve on the golden adapter's input (as sheet_words.test.ts) with the old page's rail and grade.

import { readFileSync } from "node:fs";
import type { SolvedSection } from "@cr/engine/contract";
import { describe, expect, it } from "vitest";
import { solveSection } from "../../../engine/src/port/model.ts";
import { inputJson, solvedJson } from "../../../engine/src/port/wire.ts";
import { fromGolden } from "../../../engine/test/port/from_golden.ts";
import { integrationInput } from "../../../engine/test/port/integration_input.ts";
import type { BandData } from "../../src/core/plugin.ts";
import { Units } from "../../src/core/units.ts";
import { readoutLines } from "../../src/plugins/line-sheet/bands.ts";

interface OldReadout {
  line: string;
  f: number;
  c: number;
  rows: string[];
}
const OLD = JSON.parse(readFileSync(new URL("./fixtures/old_readout.json", import.meta.url), "utf8")) as OldReadout[];

const cache = new Map<string, BandData>();
/** The sheet's band data for a line: the whole solve and its input, the old page's rail and grade on the grid. */
function dataOf(line: string): BandData {
  const hit = cache.get(line);
  if (hit) return hit;
  const inp = integrationInput(line);
  const solved = solvedJson(inp, solveSection(inp)) as unknown as SolvedSection;
  // the worker hands these back as Float32Array (pane.ts SOLVED_TYPED), as the old page held its ground
  const g = solved.ground as unknown as Record<string, unknown>;
  for (const k of ["finished", "surface", "bed"])
    g[k] = Float32Array.from(g[k] as (number | null)[], (v) => (v == null ? Number.NaN : v));
  const ssi = inputJson(inp);
  const { dump } = fromGolden(line);
  const names = new Map(solved.stations.map((s) => [s.platform_id, s.name]));
  const d = {
    sectionId: line,
    input: {
      ground: { z_m: ssi.dem.map((v) => v ?? Number.NaN), step_m: ssi.step },
      params: { platform_m: ssi.settings.platform },
      stations: solved.stations.map((s) => ({ platform_id: s.platform_id, c_m: s.c })),
    },
    rail: {
      rail_m: dump.grid.rail as number[],
      grade_permille: dump.grid.grade as number[],
      step_m: dump.step,
    },
    server: null,
    profile: null,
    selected: null,
    solved,
    solveInput: ssi,
    platformName: (id: string) => names.get(id) ?? id,
  } as unknown as BandData;
  cache.set(line, d);
  return d;
}

const norm = (s: string): string => s.replace(/\s+/g, " ").trim();

/**
 * The rows that differ, each with its reason: [old row, the sheet's row] (null: the sheet has a row the old lacks).
 * - Line 4 at 11+651.1: the rail read between the 2 m samples is 142.6450 (the old page's railAt, 142.6449...): the
 *   half-way case of the last digit, a tenth of a millimetre.
 * - Line 12 at 23+463.29 and Line 13 at 2+654.23: the prove's old hub rebuilt its context/lines.json from the Deck
 *   when it started (built 2026-11-23T10:05Z); the repository's file (2026-11-05T15:29Z), which the hub imports and
 *   the goldens read, has Montgomery Road minor from 22+900 and Middleton Avenue crossing to 2+654.3.
 */
const LISTED: Record<string, [string, string | null][]> = {
  "Line_4@11651.1": [
    ["Rail 142.64 m", "Rail 142.65 m"],
    ["Top 147.24 m · cover 5.7", "Top 147.25 m · cover 5.7"],
    ["Bottom 141.64 m · box", "Bottom 141.65 m · box"],
  ],
  "Line_12@23463.29": [["under Montgomery Road (major, 15 m)", "under Montgomery Road (minor, 15 m)"]],
  "Line_13@2654.23": [["crosses Middleton Avenue (minor, 15 m)", null]],
};

/** The old rows with the listed differences laid in. */
function expected(o: OldReadout): string[] {
  const rows = o.rows.slice();
  for (const [a, b] of LISTED[`${o.line}@${o.c}`] ?? []) {
    if (b === null) rows.push(a);
    else rows[rows.indexOf(a)] = b;
  }
  return rows;
}

describe("the hover readout reads as the old page's at 112 points", () => {
  it("has the 112 points of the prove", () => expect(OLD.length).toBe(112));
  for (const o of OLD) {
    it(`${o.line} at ${o.c}`, () => {
      const rows = readoutLines(dataOf(o.line), o.c, new Units("m")).map(norm);
      // better than the old page: inside a platform the readout names the station (listed difference)
      const own = rows.filter((r) => !r.startsWith("Station "));
      expect(own).toEqual(expected(o));
    });
  }
});
