// P3's extension of the golden adapter (claude/hub_maps/engine_port_plan.md, sections 3.3 and 7.3): the crossings and
// the neighbours of one line as the old page read them, from read-only repository files.
//
// - The crossings: the line file's, plus the crossings each RER line file names with this line (linkRerCrossings
//   3395-3402: the page took the exact points from the RER files), sorted by chainage. The hub's section records hold
//   the line file's list only (region/ext/network/importers.py), so the lead's input builder must link them too.
// - The neighbours: each crossed line's saved profile as the page read it (S.saved: hub/seed/alignments, the old
//   hub's seed), else the stale rer/metro_rails.json (Lines 10, 11 and 13, which have no saved profile; production
//   never reads it, plan section 3.3). Its settings are its system's (setOf 1195: the registry's settings_rer.* and
//   settings.*, else the page's defaults, named below), its phase its line_phase, its open clear height its system's.

import { readFileSync } from "node:fs";
import { solveTypes } from "../../../src/port/structure/index.ts";
import type { CrossingRecord, Neighbour, Phase, PortInput, Street, TypedModel } from "../../../src/port/types.ts";
import type { OldPageDump } from "../../golden/old_page/load.ts";
import { fromGolden, REPO, registryParams, seedDoc, structureOf, typedFromGolden } from "../from_golden.ts";

const readJson = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, REPO), "utf8")) as T;

const cache = new Map<string, unknown>();
function once<T>(key: string, make: () => T): T {
  if (!cache.has(key)) cache.set(key, make());
  return cache.get(key) as T;
}

interface RailDoc {
  length_m?: number;
  platform_m?: number;
  stations?: { name: string; c: number; rail: number | null }[];
  pvi?: [number, number][];
  sg?: Record<string, number>;
  gnd?: [number, number][][];
  ready?: boolean;
}

interface RerLine {
  id: string;
  line: string;
  short?: string;
  crossings?: { c: number; wid: string; oc: number; kind: string; with: string }[];
}

interface LineFileCrossings {
  crossings?: { c: number; wid?: string; oc?: number; kind: string; with: string }[];
}

/** The RER line files in the page's load order (rer/lines/index.json). */
const rerLines = (): RerLine[] =>
  once("rer", () =>
    readJson<{ id: string }[]>("data/profile/rer/lines/index.json").map((e) =>
      readJson<RerLine>(`data/profile/rer/lines/${e.id}.json`),
    ),
  );

/**
 * linkRerCrossings (3395-3402): the line file's crossings, an RER crossing named without a line taking the RER
 * file's exact point (within 120 m, by name), every other crossing an RER file names with this line added, sorted by
 * chainage (a stable sort: ties keep the order found). Only those with a line and an other chainage are checked.
 */
export function linkedCrossings(line: string): CrossingRecord[] {
  return once(`x:${line}`, () => {
    const lf = readJson<LineFileCrossings>(`data/profile/lines/${line}.json`);
    const list = (lf.crossings ?? []).map((x) => ({ ...x }));
    const NAME_MATCH_M = 120; // the page's own match window (3399)
    for (const r of rerLines())
      for (const x of r.crossings ?? []) {
        if (x.wid !== line) continue;
        const m = list.find(
          (y) => y.kind === "rer" && !y.wid && y.with === r.line && Math.abs(y.c - x.oc) < NAME_MATCH_M,
        );
        if (m) {
          m.wid = r.id;
          m.oc = x.c;
        } else list.push({ c: x.oc, wid: r.id, oc: x.c, kind: "rer", with: r.short || r.line });
      }
    list.sort((a, b) => a.c - b.c);
    return list
      .filter((x): x is typeof x & { wid: string; oc: number } => !!x.wid && x.oc != null)
      .map((x) => ({ c: x.c, other: x.wid, wid: x.wid, oc: x.oc, kind: x.kind, with: x.with }));
  });
}

/** A system's settings for the structure guess, the registry's value else the page's default (METRO_DEFAULTS 277,
 * RER_DEFAULTS 286). The RER falls back to settings.* where settings_rer.* has no param (elevAbove, coverBelow). */
function systemSettings(rer: boolean): {
  s: Neighbour["settings"];
  platform: number;
  vcRadius: number;
  openClear: number;
} {
  const reg = registryParams();
  const num = (path: string, page: number): number => {
    const v = reg.get(path);
    return typeof v === "number" ? v : page;
  };
  const sys = (k: string, metro: number, rerPage: number): number =>
    rer ? num(`settings_rer.${k}`, num(`settings.${k}`, rerPage)) : num(`settings.${k}`, metro);
  const base = {
    elevAbove: sys("elevAbove", 3, 3),
    coverBelow: sys("coverBelow", 3, 3),
    deepBelow: sys("deepBelow", 18.29, 25),
    deckDepth: sys("deckDepth", 1.5, 2.0),
  };
  if (!rer)
    return {
      s: { ...base, riverRoof: num("settings.riverRoof", 1.0) },
      platform: num("settings.platform", 121.92),
      vcRadius: num("settings.vcRadius", 1500),
      openClear: structureOf("Line_1").open_clear_height,
    };
  return {
    s: {
      ...base,
      rer: {
        envelope: num("settings_rer.envelope", 6.6),
        boreCrown: num("settings_rer.boreCrown", 7.5),
        invertDepth: num("settings_rer.invertDepth", 1.0),
        minCover: num("settings_rer.minCover", 8.5),
        surfStep: num("settings_rer.surfStep", 250),
      },
    },
    platform: num("settings_rer.platform", 204.2),
    vcRadius: num("settings_rer.vcRadius", 3000),
    openClear: num("literal.OPEN_CLEAR.rer", 5.8),
  };
}

interface ContextLines {
  lines: Record<string, { streets?: Street[] }>;
}

interface StationsFile {
  length_m: number;
  stations: { name: string; c: number }[];
}

/**
 * What the page did to a saved profile in S.saved once it had loaded it (refreshDefaultDocs 3385 for every RER line,
 * the line's own load for a Metro line): alignFromDoc (1875) called reframeDoc (1839-1868) on the saved object
 * itself, so its bend points were mapped from the frame it was saved in to the route's current one and its length
 * became the route's, while its derived stations (what otherRail reads, 2185) stayed in the saved frame. otherRail
 * then read that mixed doc. Ported here, the parts otherRail reads (pvi, length_m), as the page ran it, once.
 */
export function reframedAsThePageHeldIt(doc: RailDoc, wid: string): RailDoc {
  const file = readJson<StationsFile>(
    wid.startsWith("RER_") ? `data/profile/rer/lines/${wid}.json` : `data/profile/lines/${wid}.json`,
  );
  const stations = doc.stations ?? [];
  if (!stations.length) return doc;
  const base = file.stations.map((st, idx) => ({ name: st.name, idx, c0: st.c }));
  const keyOf = (st: { name: string; idx: number }): string =>
    base.filter((x) => x.name === st.name).length > 1 ? `${st.name}#${st.idx}` : st.name;
  const del = Array.isArray((doc as { del?: unknown }).del) ? ((doc as { del: string[] }).del ?? []) : [];
  const live = base.filter((st) => !del.includes(keyOf(st)));
  const pairs: [number, number][] = [];
  stations.forEach((x, i) => {
    const st = i < live.length && live[i]?.name === x.name ? live[i] : null;
    const pc = (x as { point_c?: unknown }).point_c;
    if (st && typeof pc === "number") pairs.push([pc, st.c0]);
  });
  const MOVED_M = 0.05; // the page's own threshold (1849)
  if (!pairs.length || !pairs.some(([a, b]) => Math.abs(a - b) > MOVED_M)) return doc;
  pairs.sort((a, b) => a[0] - b[0]);
  const L0 = typeof doc.length_m === "number" ? doc.length_m : file.length_m;
  const xs = [0, ...pairs.map((p) => p[0]), L0];
  const ys = [0, ...pairs.map((p) => p[1]), file.length_m];
  const map = (c: number): number => {
    let i = 1;
    while (i < xs.length - 1 && (xs[i] as number) < c) i++;
    const x0 = xs[i - 1] as number;
    const x1 = xs[i] as number;
    const t = x1 === x0 ? 0 : (c - x0) / (x1 - x0);
    return (ys[i - 1] as number) + t * ((ys[i] as number) - (ys[i - 1] as number));
  };
  const TENTHS = 10; // the page rounds the mapped chainage to 0.1 m (1855)
  const r1 = (v: number): number => Math.round(v * TENTHS) / TENTHS;
  return {
    ...doc,
    pvi: (doc.pvi ?? []).map(([c, z]) => [r1(map(Number(c))), z] as [number, number]),
    length_m: file.length_m,
  };
}

/**
 * The neighbour wid as the page read it at a crossing (otherRail 2184: S.saved, S.defaultDocs, S.metroRails): a saved
 * profile as the page held it (reframedAsThePageHeldIt), or as saved with asSaved. vc_min_len_m is this line's (the
 * page's vertices read the global settings.vcMinLen, 725).
 */
export function neighbourOf(d: OldPageDump, wid: string, asSaved = false): Neighbour | null {
  const rer = wid.startsWith("RER_");
  const seed = seedDoc(wid) as RailDoc | null;
  const saved = seed && !asSaved ? reframedAsThePageHeldIt(seed, wid) : seed;
  const rails = once("metro_rails", () => readJson<Record<string, RailDoc>>("data/profile/rer/metro_rails.json"));
  const doc = saved ?? rails[wid] ?? null;
  if (!doc || !Array.isArray(doc.stations)) return null;
  const sys = systemSettings(rer);
  const osg = doc.sg ?? {};
  const ms = once("ms_line_phase", () =>
    readJson<{ line_phase: Record<string, Phase> }>("hub/seed/params/metro_structure.json"),
  );
  const ctx = once("ctx", () => readJson<ContextLines>("data/profile/context/lines.json"));
  const FAR = 1e9; // the page's length where a doc has none (+doc.length_m || 1e9, 2187)
  return {
    section: wid,
    wid,
    system: rer ? "rer" : wid === "CVG_Express" ? "cvx" : "metro",
    length_m: Number(doc.length_m) || FAR,
    platform_m: Number(doc.platform_m) || sys.platform,
    vc_radius_m: sys.vcRadius,
    vc_min_len_m: d.settings.vcMinLen as number,
    stations: doc.stations.map((s, i) => ({
      c: Number(s.c),
      rail: Number(s.rail),
      sg: Number(osg[s.name] ?? osg[`${s.name}#${i}`] ?? 0),
    })),
    pvi: (doc.pvi ?? []).map(([c, z]) => ({ c: Number(c), z: Number(z) })),
    gnd: (doc.gnd ?? []).map((P) => P.map(([c, z]) => ({ c: Number(c), z: Number(z) }))),
    streets: ctx.lines[wid]?.streets ?? [],
    ready: !!saved?.ready,
    source: saved ? "profile" : "metro_rails",
    phase: rer ? null : (ms.line_phase[wid] ?? null),
    settings: sys.s,
    open_clear_m: sys.openClear,
  };
}

/** The input of one line with its linked crossings and their neighbours. */
export function crossingInput(line: string): PortInput {
  return once(`in:${line}`, () => {
    const { dump, input } = fromGolden(line);
    const crossings = linkedCrossings(line);
    const neighbours: Record<string, Neighbour> = {};
    for (const x of crossings) {
      if (neighbours[x.wid] || x.wid === line) continue;
      const n = neighbourOf(dump, x.wid);
      if (n) neighbours[x.wid] = n;
    }
    return { ...input, crossings, neighbours };
  });
}

/**
 * The typed model P3 reads: the golden's model and viaduct spans with the linked crossings and the neighbours, and
 * the type solve either the old page's own (golden) or P1's solveTypes on the same model (p1).
 */
export function crossingModel(line: string, solve: "golden" | "p1" = "golden"): TypedModel {
  return once(`m:${line}:${solve}`, () => {
    const typed = typedFromGolden(line);
    const input = crossingInput(line);
    const base = { ...typed, input };
    if (solve === "golden") return base;
    const { model } = fromGolden(line);
    return { ...base, types: solveTypes({ ...model, input }) };
  });
}
