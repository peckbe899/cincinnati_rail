// section.propose@1 (engine/src/port/propose.ts) against the old page's own proposers on the seed
// (engine/test/golden/old_page/proposers, written by engine/scripts/old_page_proposers.mjs from the scratch old hub):
// Lower and Raise on every issue that offers them, Fix unbuildable, Solve levels with crossings, Reset this line and
// the paint review, on all 16 Metro lines. Each proposal's edit, laid on the line as loaded, must give the old page's
// bend points and station levels within a centimetre.
//
// One known difference: Line_2b's first Lower (1+840 to 1+908). Its profile is saved in an older frame and the page
// reads it reframed (claude/hub_maps/profiles_parity.md, A.8: "Line 2b, its doc is reframed on load, not ported"); the
// other two Line_2b fixes and every other proposal agree.

import { readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { SectionProposal, SectionProposeInput } from "../../../src/contract/index.ts";
import { findMethod, METHOD_REFS, solve } from "../../../src/index.ts";
import { type Proposal, propose } from "../../../src/port/propose.ts";
import { inputJson } from "../../../src/port/wire.ts";
import { METRO_LINES } from "../from_golden.ts";
import { integrationInput } from "../integration_input.ts";

interface Golden {
  before: { pvi: [number, number][]; st: Record<string, number | null> };
  regrade: {
    fix: { mode: "lower" | "raise"; c0: number; c1: number; t: string | null; why: string | null };
    msg: string;
    after: { pvi: [number, number][]; st: Record<string, number | null> };
  }[];
  fix_all: { msg: string; after: { pvi: [number, number][]; st: Record<string, number | null> } };
  solve_cross: { msg: string; after: { pvi: [number, number][]; st: Record<string, number | null> } };
  reset: { msg: string; after: { pvi: [number, number][]; st: Record<string, number | null> } };
  paints: string[];
}

const golden = (line: string): Golden =>
  JSON.parse(readFileSync(new URL(`../../golden/old_page/proposers/${line}.json`, import.meta.url), "utf8"));

const KNOWN = new Set(["Line_2b|lower|1840|1908"]);
const TOL = 0.02;

/** The largest difference between the page's bends and levels after a proposal and the edit laid on the line. */
function gap(g: Golden, p: Proposal, after: Golden["regrade"][number]["after"], reset = false) {
  const pvi = p.edit.pvi ?? g.before.pvi;
  const st: Record<string, number | null> = reset ? { ...(p.edit.st ?? {}) } : { ...g.before.st, ...(p.edit.st ?? {}) };
  const dp =
    pvi.length === after.pvi.length
      ? Math.max(
          0,
          ...pvi.map((q, i) => {
            const w = after.pvi[i] as [number, number];
            return Math.abs(q[0] - w[0]) + Math.abs(q[1] - w[1]);
          }),
        )
      : Number.POSITIVE_INFINITY;
  const ds = Math.max(0, ...Object.keys(after.st).map((k) => Math.abs((st[k] ?? 0) - (after.st[k] ?? 0))));
  return Math.max(dp, ds);
}

const count = (msg: string, re: RegExp): number | null => {
  const m = re.exec(msg);
  return m ? Number(m[1]) : null;
};

describe("section.propose@1 against the old page", () => {
  test.each(METRO_LINES)("%s: Lower and Raise on every issue", (line) => {
    const g = golden(line);
    const input = integrationInput(line);
    for (const r of g.regrade) {
      const p = propose(input, {
        kind: "regrade",
        mode: r.fix.mode,
        c0: r.fix.c0,
        c1: r.fix.c1,
        fit: r.fix.why ? ({ t: r.fix.t, why: r.fix.why } as never) : null,
      });
      if (KNOWN.has(`${line}|${r.fix.mode}|${r.fix.c0}|${r.fix.c1}`)) continue;
      expect(gap(g, p, r.after), `${r.fix.mode} ${r.fix.c0}-${r.fix.c1}: ${r.msg}`).toBeLessThan(TOL);
      // the page's words name the same stations moved
      const moved = (p.report.lowered as { name: string }[]).map((x) => x.name);
      for (const name of moved) expect(r.msg).toContain(name);
    }
  });

  test.each(METRO_LINES)("%s: Fix unbuildable, Solve levels with crossings, Reset this line", (line) => {
    const g = golden(line);
    const input = integrationInput(line);
    const fx = propose(input, { kind: "fix_all" });
    expect(gap(g, fx, g.fix_all.after)).toBeLessThan(TOL);
    const left = count(g.fix_all.msg, /^(\d+) unbuildable/);
    const all = count(g.fix_all.msg, /^All (\d+) fixed/);
    if (left !== null) expect(fx.report.left).toBe(left);
    if (all !== null) expect([fx.report.found, fx.report.left]).toEqual([all, 0]);
    if (/^Nothing/.test(g.fix_all.msg)) expect(fx.report.found).toBe(0);

    const sc = propose(input, { kind: "solve_cross" });
    expect(gap(g, sc, g.solve_cross.after)).toBeLessThan(TOL);
    const m = /Cleared (\d+) of (\d+)/.exec(g.solve_cross.msg);
    expect(m).not.toBeNull();
    expect([sc.report.held, sc.report.of]).toEqual([Number(m?.[1]), Number(m?.[2])]);

    const rs = propose(input, { kind: "reset" });
    expect(gap(g, rs, g.reset.after, true)).toBeLessThan(TOL);
  });

  test.each(METRO_LINES)("%s: the paint review", (line) => {
    const g = golden(line);
    const pr = propose(integrationInput(line), { kind: "paint_review" });
    const rows = pr.paints ?? [];
    expect(rows.length).toBe(g.paints.length);
    rows.forEach((r, i) => {
      const text = g.paints[i] as string;
      expect(text.includes("(the same)"), `${r.a}-${r.b} ${r.paint}: ${text}`).toBe(r.same);
      expect(/does not fit/.test(text)).toBe(r.misfit > 0);
    });
  });
});

describe("section.propose@1 as a method", () => {
  test("is served", () => {
    expect(METHOD_REFS).toContain("section.propose@1");
    expect(findMethod("section.propose@1").contracts).toEqual({
      input: "section_propose_input",
      output: "section_proposal",
    });
  });

  test("Line_6: JSON in and out, schema checked, the same edit as on PortInput, one hash", async () => {
    const input = integrationInput("Line_6");
    const json = { ...inputJson(input), contract: "section_propose_input/0", request: { kind: "solve_cross" } };
    expect(SectionProposeInput.safeParse(json).success).toBe(true);
    const out = (await solve("section.propose", JSON.parse(JSON.stringify(json)), {
      checkOutput: true,
    })) as SectionProposal;
    expect(SectionProposal.safeParse(out).success).toBe(true);
    const direct = propose(input, { kind: "solve_cross" });
    expect(out.edit.st).toEqual(direct.edit.st);
    expect(out.report.held).toBe(direct.report.held);
    const again = (await solve("section.propose", json)) as SectionProposal;
    expect(again.input_hash).toBe(out.input_hash);
  });

  test("a regrade that a canon or locked station blocks changes nothing", () => {
    // Line_4's State and Garrard are locked: Fix unbuildable leaves their stretches and says so
    const fx = propose(integrationInput("Line_4"), { kind: "fix_all" });
    const blocked = (fx.report.blocked as { name: string }[]).map((b) => b.name);
    expect(new Set(blocked)).toEqual(new Set(["State", "Garrard"]));
  });
});
