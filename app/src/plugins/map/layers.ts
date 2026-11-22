// The map's first layers (section 8): the Metro sections and stations as full GeoJSON from the API (9.30: editable
// data is never vector tiles), and the relief and Sanborn overviews as image sources from mounted data tiers.
// A layer whose tier is missing says why in available() and shows as a greyed toggle, never as an error.

import type { ExpressionSpecification, FilterSpecification, LayerSpecification } from "maplibre-gl";
import type { Host, LayerDef, PickedFeature, RecordRef } from "../../core/plugin.ts";

/** The label font stack; its glyphs are committed under app/public/map/glyphs/dejavu-sans. */
export const FONT = ["dejavu-sans"];

let hostRef: Host | null = null;

/** The map plugin's activate() gives the layers the host they read tiers through. */
export function bindHost(h: Host | null): void {
  hostRef = h;
}

const SYSTEM_COLORS: ExpressionSpecification = [
  "match",
  ["coalesce", ["get", "system"], "other"],
  "metro",
  "#5aa9e6",
  "tri",
  "#e6b450",
  "apex",
  "#c792ea",
  "orr",
  "#7fd962",
  "tv",
  "#f78c6c",
  "#9aa3b2",
];

/** A record reference from a feature: properties kind and id, or the feature id with the layer's kind. */
export function pickRecord(kind: string) {
  return (f: PickedFeature): RecordRef | null => {
    const p = f.properties ?? {};
    const id = (typeof p.id === "string" && p.id) || (typeof f.id === "string" ? f.id : null);
    if (!id) return null;
    return { kind: typeof p.kind === "string" ? p.kind : kind, id };
  };
}

async function tierAvailable(name: string): Promise<true | string> {
  if (!hostRef) return "the map is not started";
  try {
    const t = (await hostRef.api.tiers()).find((x) => x.name === name);
    if (!t) return `data tier ${name} is not configured`;
    if (t.status === "missing") return `data tier ${name} is missing${t.detail ? ` (${t.detail})` : ""}`;
    if (t.mount === false) return `data tier ${name} is not served`;
    return true;
  } catch (e) {
    return `tiers could not be read: ${String((e as Error).message ?? e)}`;
  }
}

const selectedWidth = (selected: string | null): ExpressionSpecification | number =>
  selected ? ["case", ["==", ["get", "id"], selected], 6, 3] : 3;

export const sectionsLayer: LayerDef = {
  id: "sections",
  group: "network",
  title: "Sections",
  defaultOn: true,
  source: { type: "records", kind: "section" },
  time: "intervals",
  pick: pickRecord("section"),
  available: async () => true,
  style: (ctx): LayerSpecification[] => [
    {
      id: `${ctx.prefix}line`,
      type: "line",
      source: ctx.source,
      filter: ["in", ["geometry-type"], ["literal", ["LineString", "MultiLineString"]]] as FilterSpecification,
      layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": SYSTEM_COLORS, "line-width": selectedWidth(ctx.selected) },
    },
    {
      id: `${ctx.prefix}label`,
      type: "symbol",
      source: ctx.source,
      minzoom: 11,
      layout: {
        "symbol-placement": "line",
        "text-field": ["coalesce", ["get", "name"], ["get", "route"], ""],
        "text-font": ctx.font,
        "text-size": 11,
      },
      paint: { "text-color": "#d8dbe2", "text-halo-color": "#16181d", "text-halo-width": 1.5 },
    },
  ],
};

export const stationsLayer: LayerDef = {
  id: "stations",
  group: "network",
  title: "Stations",
  defaultOn: true,
  source: { type: "records", kind: "station" },
  time: "intervals",
  pick: pickRecord("station"),
  available: async () => true,
  style: (ctx): LayerSpecification[] => [
    {
      id: `${ctx.prefix}icon`,
      type: "symbol",
      source: ctx.source,
      filter: ["==", ["geometry-type"], "Point"] as FilterSpecification,
      layout: {
        "icon-image": "station",
        "icon-allow-overlap": true,
        "text-field": ["step", ["zoom"], "", 12, ["coalesce", ["get", "name"], ""]],
        "text-font": ctx.font,
        "text-size": 11,
        "text-offset": [0, 1.1],
        "text-anchor": "top",
        "text-optional": true,
      },
      paint: { "text-color": "#d8dbe2", "text-halo-color": "#16181d", "text-halo-width": 1.5 },
    },
  ],
};

function imageLayer(
  id: string,
  title: string,
  tier: string,
  image: string,
  corners: string,
  opacity: number,
): LayerDef {
  return {
    id,
    group: "base",
    title,
    defaultOn: false,
    source: { type: "image", tier, image, corners },
    time: "none",
    available: () => tierAvailable(tier),
    style: (ctx): LayerSpecification[] => [
      {
        id: `${ctx.prefix}raster`,
        type: "raster",
        source: ctx.source,
        paint: { "raster-opacity": opacity, "raster-fade-duration": 0 },
      },
    ],
  };
}

export const reliefLayer = imageLayer("relief", "Relief (Deck overview)", "deck", "relief.webp", "relief.json", 0.6);
export const sanbornLayer = imageLayer(
  "sanborn",
  "Sanborn 1922 (overview)",
  "sanborn_tiles_22",
  "overview.webp",
  "overview.json",
  0.85,
);

/** Base layers first, so the network draws over them. */
export const LAYERS: LayerDef[] = [reliefLayer, sanbornLayer, sectionsLayer, stationsLayer];

/**
 * Whether a layer's features are filtered by the view's instant: only when some feature carries a date. A kind
 * with no dates (sections and stations today) has open_lo and close_lo null on every feature, and the server shows
 * all of them at any year, so the map must too; filtering them would empty the map at any year without a word.
 * A dated kind's undated records still show only at the present (9.16), as the server lists them.
 */
export function timeFiltered(fc: { features: { properties?: Record<string, unknown> | null }[] }): boolean {
  return fc.features.some((f) => f.properties?.open_lo != null || f.properties?.close_lo != null);
}

/** The MapLibre filter that keeps features open at a month instant (region.core.view.is_open). */
export function eraFilter(instant: number | null): FilterSpecification {
  const far = 1e9;
  const close: ExpressionSpecification = ["to-number", ["coalesce", ["get", "close_lo"], far]];
  if (instant === null) return ["==", close, far];
  const open: ExpressionSpecification = ["to-number", ["coalesce", ["get", "open_lo"], far]];
  return ["all", ["<=", open, instant], [">", close, instant]];
}
