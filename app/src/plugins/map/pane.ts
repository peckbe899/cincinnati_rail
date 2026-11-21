// The map pane. Everything it loads is local: the style, glyphs and sprite from /map/ (committed under
// app/public/map), the records as GeoJSON from /api/v1/k/<kind>?format=geojson&crs=4326, the overviews from
// /api/v1/data/<tier>/. Era filtering runs here, on the open and close month intervals the features carry.
//
// Records are read in the view's own instant. A list at the present (year unset) leaves out every record that has
// closed (region.core.view.is_open), so a list read once at the present and filtered here could never show a line
// in 1931 that closed in 1950. The API has no "every era" list yet; until it has, a change of year or month reads
// the records again, and the client filter keeps the map right between the change and the answer.

import "maplibre-gl/dist/maplibre-gl.css";
import type { FeatureCollection } from "geojson";
import { type GeoJSONSource, Map as MlMap, type StyleSpecification, setWorkerUrl } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import type { LayerDef, MountedPane, PaneContext } from "../../core/plugin.ts";
import { isRecordRef } from "../../core/plugin.ts";
import { setLayerToggle, setMapPos } from "../../core/store.ts";
import { lonLatToUtm, utmToLonLat } from "../../core/utm.ts";
import { viewInstant } from "../../core/view.ts";
import { eraFilter, FONT } from "./layers.ts";

const DEFAULT_CENTER = { lat: 39.12, lon: -84.51, z: 11 };

setWorkerUrl(workerUrl);

/** The local style with its glyph and sprite URLs made absolute (MapLibre needs absolute URLs). */
export async function loadStyle(base = location.href): Promise<StyleSpecification> {
  const url = new URL("/map/style.json", base);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`the map style ${url.pathname} is missing (HTTP ${res.status})`);
  const style = (await res.json()) as StyleSpecification;
  if (style.glyphs) style.glyphs = decodeURI(new URL(style.glyphs, url).href);
  if (typeof style.sprite === "string") style.sprite = new URL(style.sprite, url).href;
  return style;
}

interface Corners {
  E0: number;
  N0: number;
  E1: number;
  N1: number;
}

export function imageCoordinates(c: Corners): [[number, number], [number, number], [number, number], [number, number]] {
  return [utmToLonLat(c.E0, c.N1), utmToLonLat(c.E1, c.N1), utmToLonLat(c.E1, c.N0), utmToLonLat(c.E0, c.N0)];
}

export async function mountMap(el: HTMLElement, ctx: PaneContext): Promise<MountedPane> {
  const host = ctx.host;
  const wrap = document.createElement("div");
  wrap.className = "map-root";
  wrap.dataset.testid = "map";
  const toggles = document.createElement("div");
  toggles.className = "map-layers";
  el.append(wrap, toggles);

  const pos = host.store.getState().map ?? DEFAULT_CENTER;
  const map = new MlMap({
    container: wrap,
    style: await loadStyle(),
    center: [pos.lon, pos.lat],
    zoom: pos.z,
    attributionControl: false,
    fadeDuration: 0,
  });
  (wrap as HTMLElement & { __map?: MlMap }).__map = map;
  const loaded = new Promise<void>((resolve) => map.once("load", () => resolve()));

  const layers = () => host.registry.layerList();
  const added = new Map<string, string[]>();
  const avail = new Map<string, true | string>();
  const hasDates = new Map<string, boolean>();
  const timers = new Map<string, ReturnType<typeof setTimeout>>();

  const isOn = (d: LayerDef) => host.store.getState().lay[d.id] ?? d.defaultOn ?? false;
  const selectedId = () => {
    const s = host.store.getState().sel;
    return isRecordRef(s) ? s.id : null;
  };

  const recordsView = () => host.view();
  let gone = false;

  const fetchRecords = async (d: LayerDef): Promise<FeatureCollection> => {
    if (d.source.type !== "records") throw new Error("not a records layer");
    const fc = await host.records.geojson(d.source.kind, recordsView(), d.source.query ?? {});
    hasDates.set(
      d.id,
      fc.features.some((f) => f.properties && "open_lo" in f.properties),
    );
    return fc;
  };

  const applyTime = (d: LayerDef) => {
    if (d.time !== "intervals" || !hasDates.get(d.id)) return;
    const instant = viewInstant(host.view());
    for (const id of added.get(d.id) ?? []) {
      const base = d
        .style({ source: `src-${d.id}`, prefix: `${d.id}-`, font: FONT, selected: selectedId() })
        .find((l) => l.id === id);
      const own = base && "filter" in base ? base.filter : undefined;
      map.setFilter(id, own ? (["all", own, eraFilter(instant)] as never) : eraFilter(instant));
    }
  };

  const addLayer = async (d: LayerDef) => {
    if (added.has(d.id)) return;
    const src = `src-${d.id}`;
    if (d.source.type === "records") {
      map.addSource(src, { type: "geojson", data: await fetchRecords(d), promoteId: "id" });
    } else if (d.source.type === "image") {
      const base = `${host.api.base}/data/${d.source.tier}/`;
      const corners = (await (await fetch(base + d.source.corners)).json()) as Corners;
      map.addSource(src, { type: "image", url: base + d.source.image, coordinates: imageCoordinates(corners) });
    } else if (d.source.type === "geojson") {
      map.addSource(src, { type: "geojson", data: d.source.url });
    } else {
      return;
    }
    const specs = d.style({ source: src, prefix: `${d.id}-`, font: FONT, selected: selectedId() });
    const before = d.group === "base" ? layers().find((x) => x.group !== "base" && added.has(x.id)) : undefined;
    const beforeId = before ? added.get(before.id)?.[0] : undefined;
    for (const s of specs) map.addLayer(s, beforeId);
    added.set(
      d.id,
      specs.map((s) => s.id),
    );
    applyTime(d);
  };

  const removeLayer = (d: LayerDef) => {
    for (const id of added.get(d.id) ?? []) if (map.getLayer(id)) map.removeLayer(id);
    if (map.getSource(`src-${d.id}`)) map.removeSource(`src-${d.id}`);
    added.delete(d.id);
  };

  // One sync at a time: two at once would both see a layer as not added yet, the second addSource would throw, and
  // its catch would remove the layer the first had added and mark it unavailable.
  let syncing: Promise<void> | null = null;
  let syncAgain = false;
  const sync = (): Promise<void> => {
    if (syncing) {
      syncAgain = true;
      return syncing;
    }
    syncing = (async () => {
      try {
        do {
          syncAgain = false;
          await syncOnce();
        } while (syncAgain && !gone);
      } finally {
        syncing = null;
      }
    })();
    return syncing;
  };

  const syncOnce = async () => {
    await loaded;
    for (const d of layers()) {
      if (gone) return;
      if (!avail.has(d.id)) avail.set(d.id, await d.available().catch((e) => String(e)));
      const ok = avail.get(d.id) === true;
      try {
        if (ok && isOn(d)) await addLayer(d);
        else removeLayer(d);
      } catch (e) {
        avail.set(d.id, `could not load: ${String((e as Error).message ?? e)}`);
        removeLayer(d);
      }
    }
    drawToggles();
  };

  const drawToggles = () => {
    toggles.replaceChildren();
    for (const d of layers()) {
      const a = avail.get(d.id);
      const label = document.createElement("label");
      const box = document.createElement("input");
      box.type = "checkbox";
      box.checked = a === true && isOn(d);
      box.disabled = a !== true;
      box.onchange = () => setLayerToggle(host.store, d.id, box.checked);
      label.append(box, ` ${d.title ?? d.id}`);
      if (typeof a === "string") {
        const r = document.createElement("div");
        r.className = "reason";
        r.textContent = a;
        label.append(r);
      }
      toggles.append(label);
    }
  };

  const refresh = (d: LayerDef) => {
    clearTimeout(timers.get(d.id));
    timers.set(
      d.id,
      setTimeout(async () => {
        if (gone || !map.getSource(`src-${d.id}`)) return;
        try {
          const fc = await fetchRecords(d);
          const s = gone ? undefined : (map.getSource(`src-${d.id}`) as GeoJSONSource | undefined);
          if (!s) return;
          s.setData(fc);
          applyTime(d);
        } catch (e) {
          host.problem(e);
        }
      }, 150),
    );
  };

  map.on("moveend", () => {
    const c = map.getCenter();
    setMapPos(host.store, { z: map.getZoom(), lat: c.lat, lon: c.lng });
  });
  map.on("click", (e) => {
    const pickable = layers().filter((d) => d.pick && added.has(d.id));
    const ids = pickable.flatMap((d) => added.get(d.id) ?? []);
    if (!ids.length) return;
    const box: [[number, number], [number, number]] = [
      [e.point.x - 4, e.point.y - 4],
      [e.point.x + 4, e.point.y + 4],
    ];
    for (const f of map.queryRenderedFeatures(box, { layers: ids })) {
      const d = pickable.find((x) => (added.get(x.id) ?? []).includes(f.layer.id));
      const ref = d?.pick?.({
        id: f.id as string | number | undefined,
        properties: (f.properties ?? {}) as Record<string, unknown>,
        layer: f.layer.id,
      });
      if (ref) {
        host.select(ref);
        return;
      }
    }
  });
  map.on("mousemove", (e) => {
    const [x, y] = lonLatToUtm(e.lngLat.lng, e.lngLat.lat);
    wrap.title = `E ${x.toFixed(1)}  N ${y.toFixed(1)} (EPSG:26916)`;
  });
  map.on("error", (e) => console.warn("map:", (e as unknown as { error?: { message?: string } }).error?.message ?? e));

  const unsubStore = host.store.subscribe((s, p) => {
    if (s.lay !== p.lay) void sync();
    if (s.year !== p.year || s.month !== p.month) for (const d of layers()) applyTime(d);
    if (s.layer !== p.layer || s.tl !== p.tl || s.year !== p.year || s.month !== p.month)
      for (const d of layers()) if (d.source.type === "records" && added.has(d.id)) refresh(d);
    if (s.sel !== p.sel) {
      for (const d of layers()) {
        if (!added.has(d.id)) continue;
        for (const spec of d.style({ source: `src-${d.id}`, prefix: `${d.id}-`, font: FONT, selected: selectedId() })) {
          const paint = (spec as { paint?: Record<string, unknown> }).paint ?? {};
          for (const [k, v] of Object.entries(paint))
            if (map.getLayer(spec.id)) map.setPaintProperty(spec.id, k as never, v as never);
        }
      }
    }
  });
  const unsubEvents = host.events.subscribe((m) => {
    if (m.type !== "event") return;
    const ev = m.event;
    const kinds =
      ev.type === "record"
        ? [ev.data.kind]
        : ev.type === "changeset"
          ? Object.keys(ev.data.kinds ?? {})
          : ev.type === "resync"
            ? null
            : [];
    for (const d of layers()) {
      if (d.source.type !== "records" || !added.has(d.id)) continue;
      if (kinds === null || kinds.includes(d.source.kind)) refresh(d);
    }
    if (ev.type === "tier") {
      avail.clear();
      void sync();
    }
  });
  const resize = ctx.onResize(() => map.resize());
  const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => map.resize()) : null;
  ro?.observe(wrap);
  const unsubReg = host.registry.onChange(() => void sync());
  void sync();

  return {
    dispose() {
      gone = true;
      unsubStore();
      unsubEvents();
      unsubReg();
      resize.dispose();
      ro?.disconnect();
      for (const t of timers.values()) clearTimeout(t);
      map.remove();
    },
  };
}
