// The plugin registry: every Plugin found under app/src/plugins/*/index.ts, with each contribution indexed by id.
// Ids must be unique across all plugins (a pane id, a layer id, a band id, a command id, a URL parameter, a key);
// add() throws DuplicateId on the first clash, which is what the registry unit test proves.

import type { BandDef, CommandDef, KeyBinding, KindUiDef, LayerDef, PaneDef, Plugin, UrlParamDef } from "./plugin.ts";
import { CORE_PARAMS } from "./url.ts";

export class DuplicateId extends Error {
  readonly what: string;
  readonly id: string;
  readonly plugins: [string, string];
  constructor(what: string, id: string, plugins: [string, string]) {
    super(`duplicate ${what} id "${id}" in plugins ${plugins[0]} and ${plugins[1]}`);
    this.what = what;
    this.id = id;
    this.plugins = plugins;
    this.name = "DuplicateId";
  }
}

interface Entry<T> {
  plugin: string;
  def: T;
}

type Listener = () => void;

export class Registry {
  readonly plugins = new Map<string, Plugin>();
  readonly panes = new Map<string, Entry<PaneDef>>();
  readonly layers = new Map<string, Entry<LayerDef>>();
  readonly bands = new Map<string, Entry<BandDef>>();
  readonly commands = new Map<string, Entry<CommandDef>>();
  readonly keymap = new Map<string, Entry<KeyBinding>>();
  readonly urlParams = new Map<string, Entry<UrlParamDef>>();
  readonly kinds = new Map<string, Entry<KindUiDef>>();
  private listeners = new Set<Listener>();

  /** Add one plugin. Throws DuplicateId (and adds nothing) when any of its ids is taken. */
  add(p: Plugin): void {
    if (!p || typeof p.id !== "string" || !p.id) throw new Error("a plugin needs a non-empty string id");
    const taken = this.plugins.get(p.id);
    if (taken) throw new DuplicateId("plugin", p.id, [p.id, p.id]);
    const staged: [Map<string, Entry<unknown>>, string, string, unknown][] = [];
    const seen = new Map<string, string>();
    const stage = <T>(map: Map<string, Entry<T>>, what: string, id: string, def: T) => {
      const other = map.get(id);
      if (other) throw new DuplicateId(what, id, [other.plugin, p.id]);
      const local = `${what}:${id}`;
      if (seen.has(local)) throw new DuplicateId(what, id, [p.id, p.id]);
      seen.set(local, p.id);
      staged.push([map as Map<string, Entry<unknown>>, what, id, def]);
    };
    for (const d of p.panes ?? []) stage(this.panes, "pane", d.id, d);
    for (const d of p.layers ?? []) stage(this.layers, "layer", d.id, d);
    for (const d of p.bands ?? []) stage(this.bands, "band", d.id, d);
    for (const d of p.commands ?? []) stage(this.commands, "command", d.id, d);
    for (const d of p.keymap ?? []) stage(this.keymap, "key", normaliseKey(d.key), d);
    for (const d of p.urlParams ?? []) {
      for (const name of [d.name, ...(d.aliases ?? [])]) {
        if (CORE_PARAMS.has(name)) throw new DuplicateId("url parameter", name, ["core", p.id]);
        stage(this.urlParams, "url parameter", name, d);
      }
    }
    for (const d of p.kinds ?? []) stage(this.kinds, "kind ui", d.kind, d);
    for (const [map, , id, def] of staged) map.set(id, { plugin: p.id, def });
    this.plugins.set(p.id, p);
    for (const fn of this.listeners) fn();
  }

  /** Remove a plugin and everything it contributed (used by tests and the e2e fixture plugin). */
  remove(id: string): void {
    if (!this.plugins.delete(id)) return;
    for (const map of [
      this.panes,
      this.layers,
      this.bands,
      this.commands,
      this.keymap,
      this.urlParams,
      this.kinds,
    ] as Map<string, Entry<unknown>>[]) {
      for (const [k, e] of map) if (e.plugin === id) map.delete(k);
    }
    for (const fn of this.listeners) fn();
  }

  onChange(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  pane(id: string): PaneDef | undefined {
    return this.panes.get(id)?.def;
  }

  /** Bands in plugin order then declaration order. */
  bandList(): BandDef[] {
    return [...this.bands.values()].map((e) => e.def);
  }

  layerList(): LayerDef[] {
    return [...this.layers.values()].map((e) => e.def);
  }

  /** Build a registry from the modules import.meta.glob returned, in path order so the result is stable. */
  static fromModules(mods: Record<string, unknown>): Registry {
    const reg = new Registry();
    for (const path of Object.keys(mods).sort()) {
      const mod = mods[path] as { default?: Plugin; plugin?: Plugin } | undefined;
      const p = mod?.default ?? mod?.plugin;
      if (!p) throw new Error(`${path} exports no Plugin (export default or export const plugin)`);
      reg.add(p);
    }
    return reg;
  }
}

/** "ctrl+shift+z" and "Shift+Ctrl+Z" are the same key. */
export function normaliseKey(key: string): string {
  const parts = key.split("+").map((s) => s.trim().toLowerCase());
  const main = parts.pop() ?? "";
  const mods = ["ctrl", "alt", "shift", "meta"].filter(
    (m) => parts.includes(m) || (m === "ctrl" && parts.includes("cmd")),
  );
  return [...mods, main].join("+");
}

/** The key of a keyboard event in normaliseKey form; Cmd counts as Ctrl so Mac shortcuts match. */
export function eventKey(e: KeyboardEvent): string {
  const mods: string[] = [];
  if (e.ctrlKey || e.metaKey) mods.push("ctrl");
  if (e.altKey) mods.push("alt");
  if (e.shiftKey) mods.push("shift");
  return [...mods, e.key.toLowerCase()].join("+");
}

/** Every plugin under app/src/plugins/<f>/index.ts. Eager, because the index files are small by convention. */
export function discover(): Registry {
  return Registry.fromModules(import.meta.glob("../plugins/*/index.ts", { eager: true }));
}
