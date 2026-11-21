// Golden fixtures: a SectionInput v0 for each of the 41 baseline routes, built as section 7 of the spec says.
//
// - stations: the line file's stations, minus the `del` keys, in order, each at its point plus its slide `so`;
//   levels and platform grades from the baseline's `align` (arrays by kept station index);
// - pvi: the baseline's `align.pvi`;
// - params: rules/registry.yaml, settings.* for the Metro and settings_rer.* for the RER (a route is RER when its
//   id starts with RER_, as the page decides), with the line file's own `settings` over them (the CVG Express's
//   204.216 m platforms). The registry has no settings_rer.vcMinLen; the RER takes settings.vcMinLen, which equals
//   the page's RER_DEFAULTS value (30.5 m).
//
// The baseline's `align` is the page's input after its normalisation (reframeDoc, defaultAlign, locks, junction
// PVIs), so these fixtures test the geometry alone. seedFixture() builds the same input from the hub/seed doc
// instead, which tests normalisation too (the separate test of section 7).

import { readdirSync, readFileSync } from "node:fs";
import { parse } from "yaml";
import type { SectionInput, SectionStation } from "../src/contract/index.ts";

export const REPO = new URL("../../", import.meta.url);
const at = (rel: string): URL => new URL(rel, REPO);
const readJson = (rel: string): unknown => JSON.parse(readFileSync(at(rel), "utf8"));

export interface Baseline {
  route: string;
  saved: boolean;
  c0: number;
  step_m: number;
  n: number;
  rail_m: number[];
  align: {
    del?: string[];
    so?: (number | null)[];
    st?: (number | null)[];
    sg?: (number | null)[];
    pvi?: { c: number; z: number }[];
  };
}

export interface LineFile {
  id: string;
  length_m: number;
  step_m: number;
  stations: { name: string; c: number }[];
  settings?: Record<string, number>;
}

export interface SeedDoc {
  length_m?: number;
  st?: Record<string, number>;
  sg?: Record<string, number>;
  so?: Record<string, number>;
  del?: string[];
  pvi?: [number, number][];
}

/** The 41 baseline routes, sorted. */
export const ROUTES: readonly string[] = readdirSync(at("tests/baseline/profiles/"))
  .filter((f) => f.endsWith(".json"))
  .map((f) => f.slice(0, -".json".length))
  .sort();

export const isRer = (route: string): boolean => route.startsWith("RER_");

export function baseline(route: string): Baseline {
  return readJson(`tests/baseline/profiles/${route}.json`) as Baseline;
}

export function lineFile(route: string): LineFile {
  return readJson(
    isRer(route) ? `data/profile/rer/lines/${route}.json` : `data/profile/lines/${route}.json`,
  ) as LineFile;
}

export function seedDoc(route: string): SeedDoc | null {
  try {
    return readJson(`hub/seed/alignments/${route}.json`) as SeedDoc;
  } catch {
    return null;
  }
}

let registryCache: Map<string, unknown> | null = null;

/** The registry's params, by path. */
export function registryParams(): Map<string, unknown> {
  if (!registryCache) {
    const doc = parse(readFileSync(at("rules/registry.yaml"), "utf8")) as {
      params: { path: string; value: unknown }[];
    };
    registryCache = new Map(doc.params.map((p) => [p.path, p.value]));
  }
  return registryCache;
}

/** A setting for the route's system, the line file's overlay over the registry. */
export function setting(route: string, key: string): number {
  const reg = registryParams();
  const over = lineFile(route).settings?.[key];
  if (typeof over === "number") return over;
  const own = reg.get(`${isRer(route) ? "settings_rer" : "settings"}.${key}`);
  const value = own ?? reg.get(`settings.${key}`);
  if (typeof value !== "number") throw new Error(`no registry param for ${key} on ${route}`);
  return value;
}

export function params(route: string): SectionInput["params"] {
  return {
    platform_m: setting(route, "platform"),
    vc_radius_m: setting(route, "vcRadius"),
    vc_min_len_m: setting(route, "vcMinLen"),
  };
}

/** The page's station key: the name, or name#index where the line file repeats the name (profiles.html 718). */
export function stationKeys(line: LineFile): string[] {
  const count = new Map<string, number>();
  for (const s of line.stations) count.set(s.name, (count.get(s.name) ?? 0) + 1);
  return line.stations.map((s, i) => ((count.get(s.name) ?? 0) > 1 ? `${s.name}#${i}` : s.name));
}

const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

export interface FixtureOptions {
  /** Grid step of the output; the line file's step_m when not given. */
  step_m?: number;
}

function base(route: string, line: LineFile, opts: FixtureOptions): Omit<SectionInput, "stations" | "pvi"> {
  return {
    contract: "section_input/0",
    section_id: route,
    length_m: line.length_m,
    chainage_basis: "grid:26916",
    scale: 1,
    step_m: opts.step_m ?? line.step_m,
    params: params(route),
  };
}

/** The golden input of a route, from its baseline `align`. */
export function fixture(route: string, opts: FixtureOptions = {}): SectionInput {
  const line = lineFile(route);
  const al = baseline(route).align;
  const keys = stationKeys(line);
  const del = new Set(al.del ?? []);
  const kept = line.stations.map((s, i) => ({ s, key: keys[i] as string })).filter((x) => !del.has(x.key));
  const stations: SectionStation[] = kept.map(({ s, key }, i) => ({
    platform_id: `${route}|${key}`,
    order: i,
    c_m: s.c + (num(al.so?.[i]) || 0),
    level_m: num(al.st?.[i]),
    grade_permille: num(al.sg?.[i]),
  }));
  const pvi = (al.pvi ?? []).map((p) => ({ c_m: p.c, z_m: p.z }));
  return { ...base(route, line, opts), stations, pvi };
}

/** The input of a route built from its hub/seed doc as saved (no reframe, locks or level solver), or null. */
export function seedFixture(route: string, opts: FixtureOptions = {}): SectionInput | null {
  const doc = seedDoc(route);
  if (!doc) return null;
  const line = lineFile(route);
  const keys = stationKeys(line);
  const del = new Set(doc.del ?? []);
  const kept = line.stations.map((s, i) => ({ s, key: keys[i] as string })).filter((x) => !del.has(x.key));
  const stations: SectionStation[] = kept.map(({ s, key }, i) => ({
    platform_id: `${route}|${key}`,
    order: i,
    c_m: s.c + (num(doc.so?.[key]) || 0),
    level_m: num(doc.st?.[key]),
    grade_permille: num(doc.sg?.[key]),
  }));
  const pvi = (doc.pvi ?? []).filter((p) => Array.isArray(p) && p.length >= 2).map(([c, z]) => ({ c_m: +c, z_m: +z }));
  return { ...base(route, line, opts), stations, pvi };
}
