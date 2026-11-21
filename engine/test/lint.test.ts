// Source rules for engine/src (engine/PROTOCOL.md, Results): methods are pure, so the source never reads a clock or
// a random source, and every numeric constant is named in src/tol.ts, where its tolerance is written down once.
//
// Read from the TypeScript syntax tree, so strings and comments never count. The literals 0, 1 and 2 are allowed
// anywhere (indices, increments, halves). src/contract/ is exempt (WP0's contract holds majors, c0: 0 and progress
// bounds), and so is src/tol.ts itself.

import { readdirSync, readFileSync } from "node:fs";
import ts from "typescript";
import { describe, expect, test } from "vitest";

const SRC = new URL("../src/", import.meta.url);
const EXEMPT = (rel: string): boolean => rel.startsWith("contract/") || rel === "tol.ts";
const ALLOWED_NUMBERS = new Set([0, 1, 2]);
const BANNED_GLOBALS = new Set(["Date", "performance"]);

function sources(dir: URL = SRC, prefix = ""): string[] {
  const out: string[] = [];
  for (const ent of readdirSync(dir, { withFileTypes: true })) {
    const rel = `${prefix}${ent.name}`;
    if (ent.isDirectory()) out.push(...sources(new URL(`${ent.name}/`, dir), `${rel}/`));
    else if (rel.endsWith(".ts")) out.push(rel);
  }
  return out.sort();
}

interface Finding {
  file: string;
  line: number;
  what: string;
}

function scan(rel: string, text: string = readFileSync(new URL(rel, SRC), "utf8")): Finding[] {
  const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const out: Finding[] = [];
  const at = (node: ts.Node): number => sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
  const visit = (node: ts.Node): void => {
    if (ts.isIdentifier(node) && BANNED_GLOBALS.has(node.text)) {
      const parent = node.parent;
      // a property name (x.Date, { Date: 1 }) is not the global
      const isMember =
        (ts.isPropertyAccessExpression(parent) && parent.name === node) ||
        (ts.isPropertyAssignment(parent) && parent.name === node);
      if (!isMember) out.push({ file: rel, line: at(node), what: node.text });
    }
    if (
      ts.isPropertyAccessExpression(node) &&
      node.name.text === "random" &&
      ts.isIdentifier(node.expression) &&
      node.expression.text === "Math"
    ) {
      out.push({ file: rel, line: at(node), what: "Math.random" });
    }
    if (!EXEMPT(rel) && (ts.isNumericLiteral(node) || ts.isBigIntLiteral(node))) {
      const value = ts.isNumericLiteral(node) ? Number(node.text) : Number.NaN;
      if (!ALLOWED_NUMBERS.has(value))
        out.push({ file: rel, line: at(node), what: `numeric literal ${node.getText(sf)}` });
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return out;
}

describe("engine source", () => {
  test("no Date, Math.random or performance in src; no numeric literal outside tol.ts", () => {
    const files = sources();
    expect(files).toContain("tol.ts");
    const findings = files.flatMap((f) => scan(f)).map((f) => `${f.file}:${f.line} ${f.what}`);
    expect(findings, findings.join("\n")).toEqual([]);
  });

  test("the scanner finds what it bans, and not in strings or comments", () => {
    const text = [
      "const a = Date.now(); const b = Math.random(); const c = 0.5; const d = performance.now();",
      'const e = "Date 7 performance"; // Math.random() 9',
      "const f = { Date: 2 }.Date + x.performance + 1e3 + 2;",
    ].join("\n");
    const what = scan("probe.ts", text).map((f) => f.what);
    expect(what).toEqual(["Date", "Math.random", "numeric literal 0.5", "performance", "numeric literal 1e3"]);
  });
});
