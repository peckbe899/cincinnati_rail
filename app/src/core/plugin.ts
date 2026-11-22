// The contract between the shell and its features (section 8). A feature is a folder app/src/plugins/<f>/ whose
// index.ts exports a Plugin as its default export (or as `plugin`). The registry finds it by import.meta.glob.
//
// Keep a plugin's index.ts small: it declares ids and lazy-imports the pane code inside mount(), so the first chunk
// stays small however many plugins there are.

import type { LayerSpecification } from "maplibre-gl";
import type { Api } from "../api/client.ts";
import type { EventFeed } from "../api/events.ts";
import type { Meta, Rec } from "../api/types.ts";
import type { EngineHandle } from "../engine/client.ts";
import type { Drafts } from "./drafts.ts";
import type { Names } from "./names.ts";
import type { RecordCache } from "./records.ts";
import type { Registry } from "./registry.ts";
import type { AppStore } from "./store.ts";
import type { UndoStack } from "./undo.ts";
import type { Units } from "./units.ts";
import type { View } from "./view.ts";

export interface Disposable {
  dispose(): void;
}

/** A record by kind and id. */
export interface RecordRef {
  kind: string;
  id: string;
}

/** An old key not yet resolved to a record (from a legacy URL alias or Ctrl+K). */
export interface LegacyRef {
  lkind: string;
  key: string;
}

/** What is selected: a record, an old key waiting for /legacy, or nothing. */
export type Selection = RecordRef | { legacy: LegacyRef } | null;

export function isRecordRef(sel: Selection): sel is RecordRef {
  return sel !== null && "kind" in sel && "id" in sel;
}

// ------------------------------------------------------------------------------------------------------- panes

export interface PaneContext {
  host: Host;
  /** The pane's params (from openPane or the saved layout). */
  params: Record<string, unknown>;
  /** What serialize() returned before the layout was saved, if anything. */
  state: unknown;
  /** Set the tab's title. */
  setTitle(title: string): void;
  /** Called when the pane is resized (dockview layout changes). */
  onResize(fn: () => void): Disposable;
}

export interface MountedPane {
  dispose(): void;
  serialize?(): unknown;
}

export interface PaneDef {
  id: string;
  title: string;
  /** Whether this pane can show the selection (the shell offers it on select). */
  accepts?(sel: Selection): boolean;
  /** Draw into el, which the shell owns. Any framework or none. */
  mount(el: HTMLElement, ctx: PaneContext): Promise<MountedPane>;
}

// ---------------------------------------------------------------------------------------------------- map layers

/** Where a map layer's data comes from. */
export type Source =
  | { type: "records"; kind: string; query?: Record<string, string> }
  | { type: "image"; tier: string; image: string; corners: string }
  | { type: "geojson"; url: string }
  | { type: "pmtiles"; url: string };

export interface LayerStyleContext {
  /** The MapLibre source id the shell added for this layer's Source. */
  source: string;
  /** Prefix for MapLibre layer ids, so plugins never collide. */
  prefix: string;
  /** The font stack for labels in the local style. */
  font: string[];
  /** The selected record id, if any. */
  selected: string | null;
}

/** A picked map feature, as the shell hands it to pick(). */
export interface PickedFeature {
  id?: string | number;
  properties: Record<string, unknown>;
  layer: string;
}

export interface LayerDef {
  id: string;
  group: string;
  title?: string;
  /** Shown when the URL's lay list does not mention the layer. */
  defaultOn?: boolean;
  source: Source;
  style(ctx: LayerStyleContext): LayerSpecification[];
  /** "intervals": features carry open/close month intervals and the client filters them by the view's instant. */
  time?: "intervals" | "none";
  pick?(f: PickedFeature): RecordRef | null;
  /** true, or the plain reason the layer cannot show (a missing tier). */
  available(): Promise<true | string>;
}

// --------------------------------------------------------------------------------------------------- sheet bands

/** The line sheet's coordinate frame, shared by every band. */
export interface SheetView {
  c0: number;
  c1: number;
  z0: number;
  z1: number;
  width: number;
  height: number;
  /** Device pixels per CSS pixel. */
  dpr: number;
  /** Top of this band in CSS pixels. */
  top: number;
  x(c: number): number;
  c(x: number): number;
  y(z: number): number;
  z(y: number): number;
  units: Units;
  cursor: number | null;
}

/** What the sheet hands each band: the section input, the local solve, the server result and the draft. */
export interface BandData {
  sectionId: string;
  input: import("@cr/engine/contract").SectionInput | null;
  rail: { rail_m: ArrayLike<number>; grade_permille: ArrayLike<number>; step_m: number } | null;
  server: { rail_m: ArrayLike<number>; step_m: number } | null;
  profile: Rec | null;
  selected: Handle | null;
  /** A platform's name for labels ("Bond Hill"); the id when none is known. */
  platformName?(id: string): string;
}

/** A grabbable thing on a band (a PVI, a platform). */
export interface Handle {
  band: string;
  kind: string;
  index: number;
  c: number;
  z?: number;
}

export interface BandDef {
  id: string;
  height: number;
  /** "profile" bands share the z axis; "strip" bands have their own height and no z axis. */
  axis?: "profile" | "strip";
  draw(g: CanvasRenderingContext2D, view: SheetView, data: BandData): void;
  hit?(x: number, y: number): Handle | null;
}

// --------------------------------------------------------------------------------------------- commands and keys

export interface CommandDef {
  id: string;
  title: string;
  run(host: Host, arg?: unknown): void | Promise<void>;
  when?(host: Host): boolean;
}

export interface KeyBinding {
  /** "Ctrl+K", "Ctrl+Shift+Z"; Ctrl also matches Cmd on a Mac. */
  key: string;
  command: string;
}

/** A URL parameter a plugin owns, beyond the core ones (layer, year, month, tl, sel, c, lay, map). */
export interface UrlParamDef {
  name: string;
  aliases?: string[];
}

/** How a kind shows in the app: a label for its records and per-field widget hints for the inspector. */
export interface KindUiDef {
  kind: string;
  label?(rec: Rec): string;
  hidden?: string[];
}

export interface Plugin {
  id: string;
  panes?: PaneDef[];
  layers?: LayerDef[];
  bands?: BandDef[];
  commands?: CommandDef[];
  keymap?: KeyBinding[];
  urlParams?: UrlParamDef[];
  kinds?: KindUiDef[];
  // biome-ignore lint/suspicious/noConfusingVoidType: section 8 fixes this signature; with void, an activate that only calls a void method (h.status(...)) type-checks.
  activate?(h: Host): Disposable | void;
}

// --------------------------------------------------------------------------------------------------------- host

export interface Toast {
  text: string;
  level?: "info" | "warn" | "error";
  requestId?: string | null;
  actions?: { label: string; run(): void }[];
  /** Milliseconds; 0 keeps it until dismissed. */
  ttl?: number;
}

/** A status bar item; plugins own theirs by id. */
export interface StatusItem {
  id: string;
  text: string;
  level?: "info" | "warn" | "error";
  title?: string;
  order?: number;
}

/** What a plugin and a pane may use. */
export interface Host {
  api: Api;
  store: AppStore;
  records: RecordCache;
  /** Record names in Ben's terms, for every place the app would show an id. */
  names: Names;
  events: EventFeed;
  drafts: Drafts;
  undo: UndoStack;
  units: Units;
  engine: EngineHandle;
  registry: Registry;
  /** The current view (layer, year, month, timeline) from the URL. */
  view(): View;
  select(sel: Selection, opts?: { c?: number }): void;
  openPane(paneId: string, params?: Record<string, unknown>): void;
  runCommand(id: string, arg?: unknown): Promise<void>;
  toast(t: Toast | string): void;
  /** Show an error as a toast; a problem response's request id goes with it. */
  problem(e: unknown): void;
  status(item: StatusItem | { id: string; remove: true }): void;
  meta(): Promise<Meta>;
  /** true when records of the kind can be written in the view, else the plain reason they cannot (9.23). */
  editable(kind: string, view?: View): Promise<true | string>;
  /** The old hub's base URL (configs/hub.json old_hub). */
  oldHub(): string;
}
