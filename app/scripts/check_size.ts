// The first chunk stays under 400 KB gzipped (section 10, WP6). The first chunk is what index.html loads before
// anything else: its entry script and every chunk it preloads. CSS is reported beside it. Run after a build:
//
//   npm run build -w app && npm run check:size -w app

import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

export const BUDGET = 400 * 1024;

export function firstChunk(dist: string): { files: { file: string; gzip: number }[]; js: number; css: number } {
  const html = readFileSync(join(dist, "index.html"), "utf-8");
  const js = [
    ...html.matchAll(/<script[^>]+type="module"[^>]+src="([^"]+)"/g),
    ...html.matchAll(/<link[^>]+rel="modulepreload"[^>]+href="([^"]+)"/g),
  ].map((m) => m[1] as string);
  const css = [...html.matchAll(/<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"/g)].map((m) => m[1] as string);
  const size = (href: string) => gzipSync(readFileSync(join(dist, href.replace(/^\//, ""))), { level: 9 }).length;
  const files = [...new Set([...js, ...css])].map((f) => ({ file: f, gzip: size(f) }));
  const sum = (list: string[]) => files.filter((f) => list.includes(f.file)).reduce((s, f) => s + f.gzip, 0);
  return { files, js: sum(js), css: sum(css) };
}

const same = (a: string, b: string) => (process.platform === "win32" ? a.toLowerCase() === b.toLowerCase() : a === b);
const isMain = process.argv[1] !== undefined && same(resolve(process.argv[1]), fileURLToPath(import.meta.url));
if (isMain) {
  const dist = resolve(dirname(fileURLToPath(import.meta.url)), "..", "dist");
  if (!existsSync(join(dist, "index.html"))) {
    console.error("check:size: no app/dist/index.html; run npm run build -w app first.");
    process.exit(2);
  }
  const r = firstChunk(dist);
  for (const f of r.files) console.log(`${(f.gzip / 1024).toFixed(1).padStart(8)} KB gz  ${f.file}`);
  console.log(
    `first chunk: ${(r.js / 1024).toFixed(1)} KB gzipped JavaScript (budget ${BUDGET / 1024} KB), plus ${(r.css / 1024).toFixed(1)} KB CSS`,
  );
  if (r.js + r.css > BUDGET) {
    console.error("check:size: the first chunk is over budget.");
    process.exit(1);
  }
}
