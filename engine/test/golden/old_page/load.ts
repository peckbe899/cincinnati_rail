// Loader of the old page's golden dumps (format old_page/1): engine/test/golden/old_page/<Line>.json.gz, written by
// engine/scripts/old_page_dump.mjs from a scratch copy of the old hub (README.md beside this file).
//
// loadOldPage(line) reads one file and gives it back with NaN and the infinities restored ("__NaN__", "__Inf__",
// "__-Inf__" in the file). The helpers expand what the file keeps short: unrle() a run-length list to one value per
// 2 m sample, ground() the five ground layers from the DEM and the runs where each differs from the layer under it.
// The port's goldens (claude/hub_maps/engine_port_plan.md, section 6) compare against these, per output, within the
// tolerance the plan gives each.

import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

export const OLD_PAGE_DIR = new URL("./", import.meta.url);

export type Rle<T> = [T, number][];
/** Runs where a layer differs from the one under it: [first index, values]. */
export type Runs = [number, number[]][];

export interface OldIssue {
  kind: string;
  sev: "error" | "warn" | "note";
  c: number;
  c0: number;
  c1: number;
  /** Where c0 and c1 came from: the source list, the platform (c +/- half), the text ("from 1+145 to 1+205") or c alone. */
  range_from: "source" | "platform" | "text" | "point";
  /** The list the issue came from in the same dump, and its index there. */
  src: [string, number] | null;
  grp: string | null;
  text: string;
  plain: string;
  fix: { mode: "lower" | "raise"; c0: number; c1: number; t?: string; why?: string } | null;
  clear: { c0: number; c1: number; si?: number } | null;
  propose: { c0: number; c1: number } | null;
}

export interface OldStation {
  i: number;
  name: string;
  key: string;
  idx: number;
  point_c: number;
  c: number;
  rail: number;
  sg: number;
  so: number;
  stt: string;
  ref: number;
  ground: number;
  surface: number;
  type: string;
  role: "box" | "mined" | "open" | null;
  platDef: "side" | "island" | null;
  platKind: "side" | "island";
  phase: string;
  year: number | null;
  sgMax: number;
  access: Record<string, unknown> & {
    type: string;
    rule: string;
    source: string;
    flags: { sev: string; plain: string }[];
  };
  curve: { R: number | null; out: number; inn: number; level: string | null; gapfill: boolean; turns: unknown };
  street: { text: string; street: unknown; roads: unknown[] };
}

export interface OldAlign {
  st: number[];
  sg: number[];
  so: number[];
  del: string[];
  pvi: { c: number; z: number }[];
  ovr: [number, number, string][];
  stt: string[];
  tf?: [number, number, string][];
  shafts?: number[];
  gnd: { c: number; z: number }[][];
  gapfill?: string[];
  ready?: boolean;
  mode?: string[];
}

export interface OldPageDump {
  format: "old_page/1";
  line: string;
  system: string;
  L: number;
  step: number;
  n: number;
  settings: Record<string, number>;
  era: { shield: string; sgMax: number; era: string } | null;
  canon_record: unknown;
  had_doc: boolean;
  stations_file: { i: number; name: string; c: number; key: string }[];
  align: OldAlign;
  stations: OldStation[];
  grid: {
    rail: number[];
    grade: number[];
    type: Rle<string>;
    tube_key: Rle<string | null>;
    phase: Rle<string | null>;
    point: Rle<string>;
    ovr: Rle<string | null>;
    canon: Rle<string | null>;
    lock: Rle<string | null>;
    tf: Rle<string | null>;
    station: Rle<number | null>;
    /** "lim|warn" of gradeLimitAt (warn empty when none), per mille. */
    grade_limit: Rle<string>;
    /** "k|below|top" of structFor(type, c): the structure drawn at the rail. */
    struct: Rle<string>;
    /** The legal band (profiles.html 2525-2532): ground less a shield tube's top and diameter, NaN where not underground. */
    limit_tube: number[];
    /** Ground less the phase's cut-and-cover limit, NaN where not underground. */
    limit_box: number[];
    solved: { t: Rle<string>; z_matches_rail: boolean; tube: Rle<string | null>; part: Rle<string> } | null;
    ground: { dem_dm: (number | null)[]; regraded: Runs; finished: Runs; surface: Runs; bed: Runs; made_bed: Runs };
  };
  ten: { radii: (number | null)[]; allowance: number[] };
  solve: {
    bad: { why: "cover" | "box" | "roof"; c0: number; c1: number; worst: number }[];
    platDef: Record<string, "side" | "island">;
    stRole: Record<string, "box" | "mined" | "open">;
    shafts: number[];
    flags: {
      c0: number;
      c1: number;
      kind: string;
      text: string;
      plain: string;
      info?: true;
      warn?: true;
      error?: true;
      propose?: true;
    }[];
    approaches: {
      station: string | null;
      kind: string;
      side: number;
      shift: number;
      c: number;
      len: number;
      river?: string;
    }[];
  } | null;
  eff_ovr: [number, number, string][];
  chr_segments: { key: string; c0: number; c1: number; year: number | null; phase: string | null; set: boolean }[];
  canon: {
    secs: unknown[];
    fixed: Record<string, unknown>;
    modes: Record<string, unknown>;
    locks: unknown[];
    piers: number[];
    deck: unknown[];
  };
  rivers: {
    name: string;
    c0: number;
    c1: number;
    bed: number | null;
    navigable: boolean;
    along_shore: boolean;
    bridge: unknown;
    band: unknown;
  }[];
  sunk_box: { k: "sunk"; below: number; top: number; inside?: number; spacing?: number; label: string };
  river_bridges: { name: string; c0: number; c1: number; lb: number; ub: number; src: string }[];
  viaduct_spans: {
    c0: number;
    c1: number;
    L: number;
    truss: boolean;
    below: number;
    above: number;
    ends: [boolean, boolean];
  }[];
  misfits: { c0: number; c1: number; t: string; why: string; worst: number; si?: number; station?: string }[];
  crossings: (Record<string, unknown> & {
    c: number;
    wid: string;
    oc: number;
    zo: number | null;
    source: string | null;
  })[];
  context: (Record<string, unknown> & { c: number; block: number; ok: boolean })[];
  roads: { kind: "Road"; sev: string; c: number; road: unknown[]; text: string; pier?: unknown[] }[];
  gnd_cross: unknown[];
  gnd_checks: { sev: string; c: number; text: string }[];
  drawing: { kind: "Drawing"; c: number; text: string; warn?: true }[];
  curve_grade: unknown[];
  design: { checks: { kind: string; c: number; text: string; warn?: true }[]; sumps: number };
  summary: Record<string, unknown> & { len: Record<string, number>; maxG: number; over: unknown[] };
  issues: OldIssue[];
  issues_src_ok: boolean;
  levels: {
    default_align: OldAlign;
    reframe: ({ changed: boolean } & Record<string, unknown>) | null;
    propose_fill: { c0: number; c1: number; kind: string; msg: string; added: { c: number; z: number }[][] }[];
    reset: OldAlign;
  };
}

export interface OldPageIndex {
  format: "old_page/1";
  sources: Record<string, string | number | boolean>;
  lines: {
    line: string;
    file: string;
    json_sha256: string;
    bytes: number;
    n: number;
    issues: number;
    issues_src_ok: boolean;
  }[];
}

const SPECIAL: Record<string, number> = {
  __NaN__: Number.NaN,
  __Inf__: Number.POSITIVE_INFINITY,
  "__-Inf__": Number.NEGATIVE_INFINITY,
};

const revive = (_k: string, v: unknown): unknown => (typeof v === "string" && v in SPECIAL ? SPECIAL[v] : v);

export function oldPageIndex(): OldPageIndex {
  return JSON.parse(readFileSync(new URL("index.json", OLD_PAGE_DIR), "utf8")) as OldPageIndex;
}

/** One line's dump (Line_6, CVG_Express, ...), NaN and the infinities restored. */
export function loadOldPage(line: string): OldPageDump {
  const entry = oldPageIndex().lines.find((l) => l.line === line);
  if (!entry) throw new Error(`no old-page golden for ${line}`);
  const raw = readFileSync(new URL(entry.file, OLD_PAGE_DIR));
  const text = entry.file.endsWith(".gz") ? gunzipSync(raw).toString("utf8") : raw.toString("utf8");
  return JSON.parse(text, revive) as OldPageDump;
}

/** A run-length list as one value per sample. */
export function unrle<T>(list: Rle<T>): T[] {
  const out: T[] = [];
  for (const [v, k] of list) for (let i = 0; i < k; i++) out.push(v);
  return out;
}

/** `under` with `runs` laid over it. */
export function overlay(under: readonly number[], runs: Runs): number[] {
  const out = under.slice();
  for (const [i0, v] of runs)
    v.forEach((x, k) => {
      out[i0 + k] = x;
    });
  return out;
}

/**
 * The ground layers on the grid, in single precision as the page holds them: dem (the line file's ground_dm / 10),
 * regraded (the Deck's add and cap runs), finished (the drawn ground and other lines' drawn ground across their
 * street), surface (pool over rivers) and bed (the river bed where the canon gives one). made_bed is NaN except over
 * a sunk box whose roof stands above the bed. surface, bed and made_bed are the page's values at c_i in double
 * precision (the pool and the canon bed are not single-precision numbers).
 */
export function ground(d: OldPageDump): {
  dem: Float32Array;
  regraded: Float32Array;
  finished: Float32Array;
  surface: number[];
  bed: number[];
  made_bed: number[];
} {
  const g = d.grid.ground;
  const dem = Float32Array.from(g.dem_dm, (v) => (v == null ? Number.NaN : v / 10));
  const regraded = overlay(Array.from(dem), g.regraded);
  const finished = overlay(regraded, g.finished);
  return {
    dem,
    regraded: Float32Array.from(regraded),
    finished: Float32Array.from(finished),
    surface: overlay(finished, g.surface),
    bed: overlay(finished, g.bed),
    made_bed: overlay(new Array<number>(d.n).fill(Number.NaN), g.made_bed),
  };
}
