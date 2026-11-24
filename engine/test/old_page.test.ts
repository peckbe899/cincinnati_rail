// The old page's golden dumps (engine/test/golden/old_page, format old_page/1) load whole and hang together: every
// file is the one its index names, every per-2 m list covers the grid, every issue is tied to its source list. The
// port's own comparisons against these files come with each work package (claude/hub_maps/engine_port_plan.md).

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { describe, expect, test } from "vitest";
import { ground, loadOldPage, OLD_PAGE_DIR, oldPageIndex, unrle } from "./golden/old_page/load.ts";

const METRO = [
  "Line_1",
  "Line_2",
  "Line_2b",
  "Line_3",
  "Line_4",
  "Line_5",
  "Line_6",
  "Line_7",
  "Line_8",
  "Line_9",
  "Line_10",
  "Line_11",
  "Line_12",
  "Line_13",
  "Line_14",
  "CVG_Express",
];

describe("old page goldens", () => {
  const index = oldPageIndex();

  test("all 16 Metro lines, made from the repository's page", () => {
    expect(index.lines.map((l) => l.line).sort()).toEqual([...METRO].sort());
    const page = readFileSync(new URL("../../data/profile/profiles.html", import.meta.url));
    expect(index.sources.page_sha256).toBe(createHash("sha256").update(page).digest("hex"));
  });

  test.each(METRO)("%s: file, grid and issues", (line) => {
    const entry = index.lines.find((l) => l.line === line);
    if (!entry) throw new Error(line);
    const text = gunzipSync(readFileSync(new URL(entry.file, OLD_PAGE_DIR))).toString("utf8");
    expect(createHash("sha256").update(text).digest("hex")).toBe(entry.json_sha256);
    const d = loadOldPage(line);
    expect(d.n).toBe(Math.floor(d.L / d.step) + 1);
    expect(d.grid.rail).toHaveLength(d.n);
    expect(d.grid.grade).toHaveLength(d.n);
    expect(d.grid.limit_tube).toHaveLength(d.n);
    expect(d.grid.limit_box).toHaveLength(d.n);
    for (const k of [
      "type",
      "tube_key",
      "phase",
      "point",
      "ovr",
      "canon",
      "lock",
      "tf",
      "station",
      "grade_limit",
      "struct",
    ] as const)
      expect(unrle<unknown>(d.grid[k]), k).toHaveLength(d.n);
    if (d.grid.solved) {
      expect(d.grid.solved.z_matches_rail).toBe(true);
      expect(unrle(d.grid.solved.t)).toHaveLength(d.n);
    }
    const g = ground(d);
    // the layers rebuild in single precision exactly: every run value is a float32
    for (const [, v] of [...d.grid.ground.regraded, ...d.grid.ground.finished])
      for (const x of v) expect(Math.fround(x)).toBe(x);
    expect(g.finished.length).toBeGreaterThanOrEqual(d.n);
    expect(g.surface.length).toBeGreaterThanOrEqual(d.n);
    expect(d.issues_src_ok).toBe(true);
    expect(d.issues.every((x) => Number.isFinite(x.c0) && Number.isFinite(x.c1))).toBe(true);
    expect(d.stations).toHaveLength(d.align.st.length);
    expect(d.levels.default_align.st).toHaveLength(d.stations.length);
    if (!d.had_doc) expect(d.align.st).toEqual(d.levels.default_align.st);
  });
});
