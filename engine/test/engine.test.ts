// The engine's exports: the method table, the version, solve()'s checks and the build hash recipe.

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";
import { buildFiles, ENGINE_DIR, engineBuild } from "../src/build.ts";
import { CONTRACTS, VerticalRail } from "../src/contract/index.ts";
import {
  ENGINE_VERSION,
  EngineFault,
  findMethod,
  hello,
  METHOD_REFS,
  METHODS,
  methodRef,
  solve,
  UNKNOWN_BUILD,
} from "../src/index.ts";
import { fixture } from "./fixtures.ts";

describe("engine", () => {
  test("ENGINE_VERSION is engine/package.json's version", () => {
    const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8")) as { version: string };
    expect(ENGINE_VERSION).toBe(pkg.version);
  });

  test("METHODS lists vertical.rail@1 with its contracts", () => {
    expect(METHOD_REFS).toContain("vertical.rail@1");
    expect(new Set(METHOD_REFS).size).toBe(METHODS.length);
    const row = findMethod("vertical.rail");
    expect(methodRef(row)).toBe("vertical.rail@1");
    expect(findMethod("vertical.rail@1")).toBe(row);
    expect(row.contracts).toEqual({ input: "section_input", output: "vertical_rail" });
    for (const m of METHODS) {
      for (const c of [m.contracts.input, m.contracts.output]) if (c) expect(CONTRACTS[c]).toBe(0);
    }
    expect(() => findMethod("vertical.rail@2")).toThrow(EngineFault);
    expect(hello(UNKNOWN_BUILD).hello.methods).toEqual([...METHOD_REFS]);
  });

  test("solve checks the input, stamps the output and checks it against VerticalRail", async () => {
    const input = fixture("CVG_Express");
    const out = (await solve("vertical.rail", input, { engineBuild: "a".repeat(64) })) as Record<string, unknown>;
    expect(VerticalRail.safeParse(out).success).toBe(true);
    expect(out.engine_build).toBe("a".repeat(64));
    expect(out.contract).toBe("vertical_rail/0");
    await expect(solve("vertical.rail", { ...input, step_m: -1 })).rejects.toMatchObject({ code: "invalid_input" });
    await expect(solve("no.method", {})).rejects.toMatchObject({ code: "unknown_method" });
  });

  test("flags: overlapping platforms, an unset level and a short curve each cite their rule", async () => {
    const input = {
      ...fixture("Line_2b"),
      stations: [
        { platform_id: "a", order: 0, c_m: 500, level_m: 150, grade_permille: 0 },
        { platform_id: "b", order: 1, c_m: 540, level_m: 152, grade_permille: 0 },
        { platform_id: "c", order: 2, c_m: 2000, level_m: null, grade_permille: null },
      ],
      pvi: [
        { c_m: 1000, z_m: 160 },
        { c_m: 1010, z_m: 150 },
      ],
    };
    const out = (await solve("vertical.rail", input)) as { flags: { kind: string; rule: string; data: unknown }[] };
    const kinds = out.flags.map((f) => f.kind);
    expect(kinds).toContain("platform_overlap");
    expect(kinds).toContain("platform_level_unset");
    expect(kinds).toContain("vertical_curve_short");
    const rules = new Set(findMethod("vertical.rail").rules as readonly string[]);
    for (const f of out.flags) expect(rules.has(f.rule), f.rule).toBe(true);
  });

  test("engine_build follows the recipe of PROTOCOL.md", () => {
    const files = buildFiles();
    expect(files[0]).toBe("package.json");
    expect(files).toContain("src/index.ts");
    expect(files).toContain("src/contract/common.ts");
    expect([...files].sort()).toEqual(files);
    const h = createHash("sha256");
    for (const rel of files) {
      h.update(`${rel}\n`);
      h.update(readFileSync(join(ENGINE_DIR, ...rel.split("/"))));
    }
    expect(engineBuild()).toBe(h.digest("hex"));
  });
});
