// engine_build: the sha256 of engine/src/** and engine/package.json (engine/PROTOCOL.md). Node only: the sidecar and
// the CLI import this; index.ts never does, so the browser bundle stays free of node:fs.
//
// The recipe: every regular file under engine/src plus engine/package.json, named by its POSIX path relative to
// engine/, sorted by that path; for each, the line "<path>\n" then the file's bytes, all hashed in one stream.
// region/enginehost/build.py computes the same value from the same files.

import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

/** The engine/ folder this file belongs to. */
export const ENGINE_DIR: string = fileURLToPath(new URL("../", import.meta.url));

const local = (engineDir: string, rel: string): string => join(engineDir, ...rel.split("/"));

/** The files engine_build covers, as POSIX paths relative to engine/, sorted. */
export function buildFiles(engineDir: string = ENGINE_DIR): string[] {
  const out: string[] = ["package.json"];
  const walk = (rel: string): void => {
    for (const ent of readdirSync(local(engineDir, rel), { withFileTypes: true })) {
      const child = `${rel}/${ent.name}`;
      if (ent.isDirectory()) walk(child);
      else if (ent.isFile()) out.push(child);
    }
  };
  walk("src");
  return out.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

/** The engine_build of the engine at engineDir. */
export function engineBuild(engineDir: string = ENGINE_DIR): string {
  const h = createHash("sha256");
  for (const rel of buildFiles(engineDir)) {
    h.update(`${rel}\n`, "utf8");
    h.update(readFileSync(local(engineDir, rel)));
  }
  return h.digest("hex");
}
