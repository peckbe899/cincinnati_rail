// The URL codec (section 8): every view links to any other.
//
//   /w/design?layer=main&year=1985&tl=canon&sel=profile:01K…&c=12400.0&lay=+relief,-plots&map=14/39.10/-84.51
//
// parseUrl reads a URL (and the old pages' aliases) into a UrlState; formatUrl writes the canonical form back.
// formatUrl(parseUrl(u)) is canonical and parseUrl(formatUrl(s)) equals s for a state at URL precision (c to 0.1 m,
// zoom to 0.01, latitude and longitude to 1e-5 degrees).
//
// Legacy aliases accepted on read, never written:
// - query names: scenario and l for layer; timeline and t for tl; y for year; m for month; chainage and ch for c;
//   layers for lay; select and rec for sel; route and line (an old route id such as Line_6) for a legacy selection.
// - year=1931-09 for year=1931&month=9.
// - sel=<collection>/<key>, the old hub's record path (alignments/Line_8), for a legacy selection.
// - the old Profiles page's hash #Line_8 (a route id) and the Deck's hash #<E>,<N>,<scale> (EPSG:26916 centre and
//   pixels per metre); MapLibre's own hash #<z>/<lat>/<lon> too.
// - a + in lay that a form encoder turned into a space.

import type { LegacyRef, RecordRef, Selection, UrlParamDef } from "./plugin.ts";
import { utmToLonLat } from "./utm.ts";
import type { Timeline } from "./view.ts";
import { LAYER_RE } from "./view.ts";

export interface MapPos {
  z: number;
  lat: number;
  lon: number;
}

export interface UrlState {
  workspace: string;
  layer: string;
  year: number | null;
  month: number | null;
  tl: Timeline;
  sel: Selection;
  c: number | null;
  /** Map layer toggles in URL order: true for +name, false for -name. */
  lay: Record<string, boolean>;
  map: MapPos | null;
  /** Plugin-owned and unknown parameters, by canonical name. */
  extra: Record<string, string>;
}

export const DEFAULT_WORKSPACE = "design";

export const DEFAULT_STATE: UrlState = Object.freeze({
  workspace: DEFAULT_WORKSPACE,
  layer: "main",
  year: null,
  month: null,
  tl: "canon",
  sel: null,
  c: null,
  lay: {},
  map: null,
  extra: {},
}) as UrlState;

const ALIASES: Record<string, string> = {
  layer: "layer",
  scenario: "layer",
  l: "layer",
  year: "year",
  y: "year",
  month: "month",
  m: "month",
  tl: "tl",
  timeline: "tl",
  t: "tl",
  sel: "sel",
  select: "sel",
  rec: "sel",
  c: "c",
  chainage: "c",
  ch: "c",
  lay: "lay",
  layers: "lay",
  map: "map",
  route: "route",
  line: "route",
};

/** Names a plugin's UrlParamDef may not take: the core parameters and their aliases. */
export const CORE_PARAMS: ReadonlySet<string> = new Set(Object.keys(ALIASES));

/** The old hub's record collections and the lkind of their keys (the legacy index of WP5). */
export const OLD_COLLECTIONS: Record<string, string> = {
  alignments: "route",
  roadmap: "roadmap_item",
};

const KIND_RE = /^[a-z][a-z0-9_]{0,47}$/;
const ROUTE_RE = /^(Line_[0-9]+[a-z]?|RER_[A-Z0-9_]+|CVG_Express)$/i;

function decode(s: string): string {
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
}

/** encodeURIComponent, keeping : / , + readable (the parser never turns + into a space). */
function encode(s: string): string {
  return encodeURIComponent(s).replace(/%3A/gi, ":").replace(/%2F/gi, "/").replace(/%2C/gi, ",").replace(/%2B/gi, "+");
}

function rawParams(search: string): [string, string][] {
  const out: [string, string][] = [];
  for (const part of search.replace(/^\?/, "").split("&")) {
    if (!part) continue;
    const eq = part.indexOf("=");
    const k = decode(eq < 0 ? part : part.slice(0, eq));
    const v = decode(eq < 0 ? "" : part.slice(eq + 1));
    out.push([k, v]);
  }
  return out;
}

function int(v: string): number | null {
  if (!/^-?\d+$/.test(v.trim())) return null;
  return Number.parseInt(v, 10);
}

function num(v: string): number | null {
  if (v.trim() === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

const round = (v: number, digits: number) => {
  const f = 10 ** digits;
  return Math.round(v * f) / f;
};

/** A selection from its URL form: kind:id, legacy/<lkind>/<key>, or an old hub record path. */
export function parseSel(v: string): Selection {
  if (!v) return null;
  if (v.startsWith("legacy/")) {
    const rest = v.slice("legacy/".length);
    const slash = rest.indexOf("/");
    if (slash > 0 && slash < rest.length - 1)
      return { legacy: { lkind: rest.slice(0, slash), key: rest.slice(slash + 1) } };
    return null;
  }
  const slash = v.indexOf("/");
  if (slash > 0) {
    const coll = v.slice(0, slash);
    const lkind = OLD_COLLECTIONS[coll];
    if (lkind) return { legacy: { lkind, key: v.slice(slash + 1) } };
  }
  const colon = v.indexOf(":");
  if (colon > 0) {
    const kind = v.slice(0, colon);
    const id = v.slice(colon + 1);
    if (KIND_RE.test(kind) && id) return { kind, id };
  }
  return null;
}

export function formatSel(sel: Selection): string | null {
  if (!sel) return null;
  if ("legacy" in sel) return `legacy/${sel.legacy.lkind}/${sel.legacy.key}`;
  return `${(sel as RecordRef).kind}:${(sel as RecordRef).id}`;
}

export function parseLay(v: string): Record<string, boolean> {
  const out: Record<string, boolean> = {};
  for (let item of v.split(",")) {
    item = item.trim() === item ? item : item.replace(/^ /, "+").trim();
    if (!item) continue;
    let on = true;
    if (item[0] === "+" || item[0] === "-") {
      on = item[0] === "+";
      item = item.slice(1);
    }
    if (item) out[item] = on;
  }
  return out;
}

export function formatLay(lay: Record<string, boolean>): string | null {
  const parts = Object.entries(lay).map(([k, on]) => `${on ? "+" : "-"}${k}`);
  return parts.length ? parts.join(",") : null;
}

export function parseMap(v: string): MapPos | null {
  const m = /^(-?[\d.]+)\/(-?[\d.]+)\/(-?[\d.]+)$/.exec(v.trim());
  if (!m) return null;
  const z = num(m[1] ?? "");
  const lat = num(m[2] ?? "");
  const lon = num(m[3] ?? "");
  if (z === null || lat === null || lon === null || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return { z: round(z, 2), lat: round(lat, 5), lon: round(lon, 5) };
}

function fixed(v: number, min: number, max: number): string {
  let s = v.toFixed(max);
  while (s.includes(".") && s.endsWith("0") && s.length - s.indexOf(".") - 1 > min) s = s.slice(0, -1);
  if (s.endsWith(".")) s = s.slice(0, -1);
  return s;
}

export function formatMap(m: MapPos | null): string | null {
  if (!m) return null;
  return `${fixed(m.z, 0, 2)}/${fixed(m.lat, 2, 5)}/${fixed(m.lon, 2, 5)}`;
}

/** The MapLibre zoom for a Deck scale in pixels per metre at a latitude (MapLibre's world is 512 px wide at zoom 0). */
export function zoomForScale(pxPerM: number, lat: number): number {
  const metresPerPxAtZ0 = (40075016.686 * Math.cos((lat * Math.PI) / 180)) / 512;
  return Math.log2(metresPerPxAtZ0 * pxPerM);
}

export interface ParseOptions {
  /** Plugin parameters, so their aliases map to their names. */
  params?: Iterable<UrlParamDef>;
}

/** Read a URL (absolute, or a path with its query and hash) into a UrlState. Never throws. */
export function parseUrl(href: string | URL, opts: ParseOptions = {}): UrlState {
  const url = typeof href === "string" ? new URL(href, "http://hub.invalid") : href;
  const st: UrlState = { ...DEFAULT_STATE, lay: {}, extra: {} };
  const ws = /^\/w\/([A-Za-z0-9_-]+)\/?$/.exec(url.pathname);
  if (ws?.[1]) st.workspace = ws[1];

  const pluginAlias = new Map<string, string>();
  for (const p of opts.params ?? []) for (const n of [p.name, ...(p.aliases ?? [])]) pluginAlias.set(n, p.name);

  let route: string | null = null;
  for (const [k, v] of rawParams(url.search)) {
    const name = ALIASES[k];
    switch (name) {
      case "layer":
        if (LAYER_RE.test(v)) st.layer = v;
        break;
      case "year": {
        const ym = /^(-?\d{1,4})-(\d{2})$/.exec(v.trim());
        if (ym) {
          st.year = Number(ym[1]);
          const mo = Number(ym[2]);
          if (mo >= 1 && mo <= 12) st.month = mo;
        } else {
          const y = int(v);
          if (y !== null && y >= -9999 && y <= 9999) st.year = y;
        }
        break;
      }
      case "month": {
        const mo = int(v);
        if (mo !== null && mo >= 1 && mo <= 12) st.month = mo;
        break;
      }
      case "tl":
        if (v === "canon" || v === "real") st.tl = v;
        break;
      case "sel":
        st.sel = parseSel(v);
        break;
      case "c": {
        const c = num(v);
        st.c = c === null ? null : round(c, 1);
        break;
      }
      case "lay":
        st.lay = parseLay(v);
        break;
      case "map":
        st.map = parseMap(v);
        break;
      case "route":
        route = v;
        break;
      default:
        st.extra[pluginAlias.get(k) ?? k] = v;
    }
  }
  if (st.year === null) st.month = null;
  if (!st.sel && route) st.sel = { legacy: { lkind: "route", key: route } };

  const hash = decode(url.hash.replace(/^#/, ""));
  if (hash) {
    const deck = /^(\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)$/.exec(hash);
    const mlHash = parseMap(hash);
    if (deck && !st.map) {
      const [lon, lat] = utmToLonLat(Number(deck[1]), Number(deck[2]));
      st.map = { z: round(zoomForScale(Number(deck[3]), lat), 2), lat: round(lat, 5), lon: round(lon, 5) };
    } else if (mlHash && !st.map) {
      st.map = mlHash;
    } else if (ROUTE_RE.test(hash) && !st.sel) {
      st.sel = { legacy: { lkind: "route", key: hash } } satisfies { legacy: LegacyRef };
    }
  }
  return st;
}

/** The canonical URL of a state: a path and query, without a hash. */
export function formatUrl(st: UrlState): string {
  const q: [string, string | null][] = [
    ["layer", st.layer],
    ["year", st.year === null ? null : String(st.year)],
    ["month", st.year === null || st.month === null ? null : String(st.month)],
    ["tl", st.tl],
    ["sel", formatSel(st.sel)],
    ["c", st.c === null ? null : round(st.c, 1).toFixed(1)],
    ["lay", formatLay(st.lay)],
    ["map", formatMap(st.map)],
  ];
  for (const k of Object.keys(st.extra).sort()) q.push([k, st.extra[k] ?? null]);
  const query = q
    .filter((e): e is [string, string] => e[1] !== null)
    .map(([k, v]) => `${encode(k)}=${encode(v)}`)
    .join("&");
  return `/w/${st.workspace}?${query}`;
}

/** Whether two states are the same view (for skipping no-op history writes). */
export function sameState(a: UrlState, b: UrlState): boolean {
  return formatUrl(a) === formatUrl(b);
}
