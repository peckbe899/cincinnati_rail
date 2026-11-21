// The golden test of vertical.rail@1 against the Profiles page (section 7 of the spec).
//
// tests/baseline/profiles/<route>.json holds the page's rail every 5 m (rounded to 1 mm) on all 41 routes, and its
// normalised input (`align`). The fixtures (test/fixtures.ts) rebuild the engine input from that align, the line
// files and the registry, so a difference here is a difference of geometry. The baseline and the tolerance are
// fixed: a difference is investigated, never absorbed.

import { describe, expect, test } from "vitest";
import type { SectionInput } from "../src/contract/index.ts";
import { gradeAt, railAt, railGrid, sectionDesign, solve } from "../src/index.ts";
import { baseline, fixture, ROUTES, seedFixture } from "./fixtures.ts";

/** The golden tolerance: the rail within 1 mm of the page's at every 5 m sample. */
const RAIL_TOL_M = 0.001;
/** The baseline's sample step. */
const BASELINE_STEP_M = 5;

interface RailOut {
  grid: { c0: number; step_m: number; n: number };
  rail_m: number[];
  grade_permille: number[];
}

async function rail(input: SectionInput): Promise<RailOut> {
  return (await solve("vertical.rail", input)) as RailOut;
}

/** The samples where the rail is more than RAIL_TOL_M off the baseline: count, worst difference and its chainage. */
function compare(out: RailOut, want: number[]): { bad: number; worst: number; at: number } {
  let bad = 0;
  let worst = 0;
  let at = -1;
  for (let i = 0; i < want.length; i++) {
    const d = Math.abs((out.rail_m[i] ?? Number.NaN) - (want[i] as number));
    if (!(d <= RAIL_TOL_M)) bad++;
    if (!(d <= worst)) {
      worst = d;
      at = i * BASELINE_STEP_M;
    }
  }
  return { bad, worst, at };
}

describe("vertical.rail@1 golden", () => {
  test("41 of 41 routes rail every 5 m within 1 mm", async () => {
    expect(ROUTES.length).toBe(41);
    const failures: string[] = [];
    for (const route of ROUTES) {
      const want = baseline(route);
      expect(want.step_m).toBe(BASELINE_STEP_M);
      const out = await rail(fixture(route, { step_m: BASELINE_STEP_M }));
      expect(out.grid.n, `${route}: grid size`).toBe(want.n);
      const r = compare(out, want.rail_m);
      if (r.bad) failures.push(`${route}: ${r.bad} samples off, worst ${r.worst.toFixed(4)} m at ${r.at} m`);
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });

  test("the 2 m grid by merge sweep equals railAt and gradeAt at every point", () => {
    for (const route of ROUTES) {
      const input = fixture(route);
      expect(input.step_m).toBe(2);
      const { design: d } = sectionDesign(input);
      const g = railGrid(d, input.length_m, input.step_m);
      let off = 0;
      for (let i = 0; i < g.n; i++) {
        const c = g.c[i] as number;
        if (g.rail[i] !== railAt(d, c) || g.grade[i] !== gradeAt(d, c)) off++;
      }
      expect(off, `${route}: grid points that differ from railAt`).toBe(0);
    }
  });

  // The hub/seed docs fed straight in, without the page's normalisation (reframeDoc, applyLocks,
  // ensureJunctionPvis, defaultAlign). Where the doc gives the same input as the page's align, the rail must match
  // the baseline; where it does not, the cause is named, and the rail is left to the normalisation ports
  // (increment 2: reframeDoc and defaultAlign).
  test("seed docs straight in: the rail matches wherever the doc is the page's input", async () => {
    const byCause = new Map<string, string[]>();
    const add = (cause: string, route: string): void => {
      byCause.set(cause, [...(byCause.get(cause) ?? []), route]);
    };
    const pvis = (s: SectionInput): string =>
      JSON.stringify(s.pvi.map((p) => [p.c_m, p.z_m]).sort((a, b) => (a[0] as number) - (b[0] as number)));
    for (const route of ROUTES) {
      const seed = seedFixture(route, { step_m: BASELINE_STEP_M });
      if (!seed) {
        add("no seed doc (defaultAlign)", route);
        continue;
      }
      const page = fixture(route, { step_m: BASELINE_STEP_M });
      const pairs = seed.stations.map((s, i) => [s, page.stations[i]] as const);
      const causes: string[] = [];
      if (seed.stations.length !== page.stations.length) causes.push("stations");
      if (pairs.some(([a, b]) => a.c_m !== b?.c_m)) causes.push("slides (reframeDoc)");
      if (pairs.some(([a, b]) => a.level_m !== b?.level_m)) causes.push("levels (applyLocks)");
      if (pairs.some(([a, b]) => (a.grade_permille ?? 0) !== (b?.grade_permille ?? 0))) causes.push("grades");
      if (seed.pvi.length !== page.pvi.length) causes.push("PVI count (applyLocks, ensureJunctionPvis)");
      else if (pvis(seed) !== pvis(page)) causes.push("PVI chainages (reframeDoc)");
      const r = compare(await rail(seed), baseline(route).rail_m);
      if (!causes.length) {
        expect(r.bad, `${route}: the seed doc is the page's input, yet ${r.bad} samples differ`).toBe(0);
        add("same input, rail matches", route);
      } else add(`${causes.join(" + ")}${r.bad ? "" : ", rail still matches"}`, route);
    }
    const table = [...byCause].map(([cause, routes]) => `${routes.length} ${cause}: ${routes.join(", ")}`);
    console.info(`seed docs straight in:\n${table.join("\n")}`);
    expect(byCause.get("same input, rail matches")?.length).toBe(20);
    expect(byCause.get("no seed doc (defaultAlign)")).toEqual(["Line_10", "Line_11", "Line_13"]);
  });
});
