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
  /** Whether the pane is the one in focus (the dock's active panel). */
  isActive?(): boolean;
  /** Called when the pane gains or loses the focus: a pane in focus asks for its results first (priority 0). */
  onActive?(fn: (active: boolean) => void): Disposable;
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
  /** The profile plot inside its margins (CSS pixels): the axes and station names are drawn around it. */
  plot: { x: number; y: number; w: number; h: number };
  /** Where the pointer is over the canvas, for a readout at the pointer; null when it is not over it. */
  pointer?: { x: number; y: number } | null;
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
  /** The design line's vertices and vertical curves from the local solve (grade labels, curve ticks). */
  dv?: readonly import("@cr/engine/contract").DesignVertex[];
  curves?: readonly import("@cr/engine/contract").VerticalCurve[];
  /** The chainage of a platform's stop, the drawn point a slid platform hangs on. */
  stopC?(platformId: string): number | null;
  /** Bands report what they drew in words here (the sheet's text layer). */
  report?(item: SheetText): void;
  /** station.facts@1 of the shown draft, one per platform, removed ones included; null until it has run. */
  facts?: readonly import("@cr/engine/contract").StationFact[] | null;
  /** Bands record what they drew as numbers here (a station's bar, outline, access, flag), for the tests. */
  mark?(m: SheetMark): void;
  /** section.solve@1 of the shown draft, the last that landed (the whole line's structure, crossings, issues). */
  solved?: import("@cr/engine/contract").SolvedSection | null;
  /** Its input: the context blocks, streets, roads, crossings and Chronology the bands draw from. */
  solveInput?: import("@cr/engine/contract").SectionSolveInput | null;
  /** Show: the rail alone, the rail with the structure outlines, or the structures (the old page's S.show). */
  show?: "rail" | "railbox" | "box";
  /** The profile's draft data as it is now (the drawn ground is drawn from it, live, while Ben edits it). */
  draft?: Record<string, unknown> | null;
  /** The sheet's tool: Move, Paint or Ground (the old page's S.tool). */
  tool?: "move" | "paint" | "ground";
  /** A paint being dragged: the stretch and the brush's colour (the old page's paint preview, 2720). */
  paintPreview?: { c0: number; c1: number; colour: string } | null;
}

/** A thing a band drew, as numbers in metres and CSS pixels (claude/hub_maps/profiles_parity.md, check 1). */
export interface SheetMark {
  /** "bar", "point", "structure", "access", "dhall", "flag", "strip", "removed", "name". */
  kind: string;
  /** The platform id it belongs to. */
  id: string;
  [k: string]: unknown;
}

/** A thing a band drew, in words: the sheet lists them in a text layer for screen readers and tests. */
export interface SheetText {
  /** "station", "grade", "pvi", "axis". */
  kind: string;
  /** The record key it belongs to (a platform id), when it has one. */
  id?: string;
  text: string;
  c: number;
  z?: number;
  /** Where on the canvas it was drawn (CSS pixels), when it was in view. */
  x?: number;
  y?: number;
  /** false when the band had it but left its label out for room (thinned). */
  drawn: boolean;
  selected?: boolean;
}

/** A grabbable thing on a band (a PVI, a platform). */
export interface Handle {
  band: string;
  kind: string;
  index: number;
  c: number;
  z?: number;
  /** The record key of the thing (a platform id), when it has one. */
  id?: string;
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
  /** A command the item runs when clicked (the Sources chip opens the sources pane). */
  command?: string;
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
