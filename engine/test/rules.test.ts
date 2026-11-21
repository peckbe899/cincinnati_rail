// src/rules.gen.ts is generated from rules/registry.yaml (scripts/gen_rules.ts) and committed; it must match the
// registry, and every rule a method declares must be a live rule of it.

import { readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { generate, OUT, registryRules } from "../scripts/gen_rules.ts";
import { RuleId as ContractRuleId } from "../src/contract/index.ts";
import { isRuleId, METHODS, methodRef, RULE_IDS, RULE_STATUS } from "../src/index.ts";

describe("rules", () => {
  test("RuleId matches registry", () => {
    expect(readFileSync(OUT, "utf8"), "src/rules.gen.ts is stale: run node engine/scripts/gen_rules.ts").toBe(
      generate(),
    );
    const ids = registryRules().map((r) => r.id);
    expect([...RULE_IDS]).toEqual(ids);
    expect(new Set(RULE_IDS).size).toBe(RULE_IDS.length);
    for (const id of RULE_IDS) expect(ContractRuleId.safeParse(id).success, id).toBe(true);
    expect(isRuleId("era.vertical_curve.radius_and_min_length")).toBe(true);
    expect(isRuleId("era.vertical_curve.no_such_rule")).toBe(false);
  });

  test("every rule a method can cite is in the registry and not superseded", () => {
    for (const m of METHODS) {
      for (const rule of m.rules) {
        expect(isRuleId(rule), `${methodRef(m)} cites ${rule}`).toBe(true);
        expect(RULE_STATUS[rule], `${methodRef(m)} cites ${rule}`).not.toBe("superseded");
      }
    }
  });

  test("a malformed or repeated registry id is refused", () => {
    expect(() => registryRules("rules:\n  - {id: Not.An.Id, status: ratified}\n")).toThrow(/malformed/);
    expect(() => registryRules("rules:\n  - {id: a.b, status: x}\n  - {id: a.b, status: x}\n")).toThrow(/repeated/);
  });
});
