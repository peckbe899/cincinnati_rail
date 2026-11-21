// The app state that lives in the URL, in a zustand vanilla store (section 8). The store mirrors the URL:
// bindUrl() writes every change back with replaceState while a value is being typed or dragged (chainage, map
// position, layer toggles) and with pushState on navigation (selection, layer, year, timeline, workspace), and
// reads the URL again on popstate.

import { createStore, type StoreApi } from "zustand/vanilla";
import type { Selection, UrlParamDef } from "./plugin.ts";
import { DEFAULT_STATE, formatUrl, type MapPos, parseUrl, type UrlState } from "./url.ts";
import type { View } from "./view.ts";

export type Nav = "push" | "replace";

export interface AppState extends UrlState {
  /** Merge a change. nav picks pushState or replaceState; by default it follows the keys that changed. */
  update(patch: Partial<UrlState>, nav?: Nav): void;
}

export type AppStore = StoreApi<AppState> & {
  /** The nav of the latest update, read by bindUrl. */
  lastNav: Nav;
};

/** Keys whose change is navigation (pushState); the rest change while typing (replaceState). */
const NAV_KEYS: ReadonlySet<keyof UrlState> = new Set(["workspace", "layer", "year", "month", "tl", "sel"]);

export function navFor(patch: Partial<UrlState>): Nav {
  return Object.keys(patch).some((k) => NAV_KEYS.has(k as keyof UrlState)) ? "push" : "replace";
}

export function createAppStore(initial: Partial<UrlState> = {}): AppStore {
  const store = createStore<AppState>()((set) => ({
    ...DEFAULT_STATE,
    lay: {},
    extra: {},
    ...initial,
    update(patch, nav) {
      (store as AppStore).lastNav = nav ?? navFor(patch);
      set(patch);
    },
  })) as AppStore;
  store.lastNav = "replace";
  return store;
}

/** The URL part of the state (without the update action). */
export function urlState(s: AppState): UrlState {
  const { workspace, layer, year, month, tl, sel, c, lay, map, extra } = s;
  return { workspace, layer, year, month, tl, sel, c, lay, map, extra };
}

export function stateView(s: UrlState): View {
  return { layer: s.layer, year: s.year, month: s.year === null ? null : s.month, timeline: s.tl };
}

export interface UrlWindow {
  location: { href: string };
  history: {
    pushState(data: unknown, unused: string, url?: string): void;
    replaceState(data: unknown, unused: string, url?: string): void;
  };
  addEventListener(type: "popstate", fn: () => void): void;
  removeEventListener(type: "popstate", fn: () => void): void;
}

/**
 * Keep the store and the window's URL in step. The store is first set from the URL (with the plugins' parameter
 * aliases), then each change writes the canonical URL. Returns the unbind function.
 */
export function bindUrl(store: AppStore, win: UrlWindow, params: () => Iterable<UrlParamDef> = () => []): () => void {
  let writing = false;
  const read = () => {
    writing = true;
    try {
      store.getState().update(parseUrl(win.location.href, { params: params() }), "replace");
    } finally {
      writing = false;
    }
  };
  read();
  const first = formatUrl(urlState(store.getState()));
  const here = new URL(win.location.href);
  if (`${here.pathname}${here.search}` !== first) win.history.replaceState(null, "", first);
  let last = first;
  const unsub = store.subscribe((s) => {
    if (writing) return;
    const next = formatUrl(urlState(s));
    if (next === last) return;
    last = next;
    if (store.lastNav === "push") win.history.pushState(null, "", next);
    else win.history.replaceState(null, "", next);
  });
  const onPop = () => {
    read();
    last = formatUrl(urlState(store.getState()));
  };
  win.addEventListener("popstate", onPop);
  return () => {
    unsub();
    win.removeEventListener("popstate", onPop);
  };
}

// Small typed helpers the panes use.

export function setSelection(store: AppStore, sel: Selection, c?: number | null): void {
  const patch: Partial<UrlState> = { sel };
  if (c !== undefined) patch.c = c === null ? null : Math.round(c * 10) / 10;
  store.getState().update(patch, "push");
}

export function setChainage(store: AppStore, c: number | null): void {
  store.getState().update({ c: c === null ? null : Math.round(c * 10) / 10 }, "replace");
}

export function setMapPos(store: AppStore, map: MapPos): void {
  const r = (v: number, d: number) => Math.round(v * 10 ** d) / 10 ** d;
  store.getState().update({ map: { z: r(map.z, 2), lat: r(map.lat, 5), lon: r(map.lon, 5) } }, "replace");
}

export function setLayerToggle(store: AppStore, id: string, on: boolean): void {
  store.getState().update({ lay: { ...store.getState().lay, [id]: on } }, "replace");
}
