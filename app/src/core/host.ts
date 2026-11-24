// The Host every plugin and pane gets (section 8): the transport, the URL store, the record cache patched by the
// event stream, drafts, undo, units, the engine and the registry, plus the shell's services (toasts, status items,
// opening panes, the 412 banner). The React shell renders what the host's ui bus says; the host knows no React.

import { Api, ApiError } from "../api/client.ts";
import { connectEvents, type EventFeed, type FeedMessage } from "../api/events.ts";
import type { HubEvent, Meta, Rec } from "../api/types.ts";
import { createEngine, type EngineHandle } from "../engine/client.ts";
import { patchLabel } from "./describe.ts";
import { type Draft, Drafts } from "./drafts.ts";
import { Names } from "./names.ts";
import type { Disposable, Host, Selection, StatusItem, Toast } from "./plugin.ts";
import { isRecordRef } from "./plugin.ts";
import { RecordCache } from "./records.ts";
import type { Registry } from "./registry.ts";
import { type SaveOutcome, type StaleOffer, save } from "./save.ts";
import { type AppStore, createAppStore, setSelection, stateView } from "./store.ts";
import { UndoStack } from "./undo.ts";
import { Units } from "./units.ts";
import { makeView, type View } from "./view.ts";

export type UiMessage =
  | { type: "toast"; toast: Toast }
  | { type: "status"; item: StatusItem | { id: string; remove: true } }
  | { type: "open"; pane: string; params: Record<string, unknown> }
  | { type: "stale"; offer: StaleOffer }
  | { type: "palette"; open: boolean }
  | { type: "reset-layout" };

export class Emitter<T> {
  private subs = new Set<(m: T) => void>();
  on(fn: (m: T) => void): () => void {
    this.subs.add(fn);
    return () => this.subs.delete(fn);
  }
  emit(m: T): void {
    for (const fn of [...this.subs]) fn(m);
  }
}

export interface HostOptions {
  registry: Registry;
  api?: Api;
  store?: AppStore;
  events?: EventFeed | null;
  engine?: EngineHandle;
  units?: Units;
  /** Where unsaved drafts are kept across a reload of the tab (sessionStorage by default; null keeps none). */
  draftStore?: Pick<Storage, "getItem" | "setItem" | "removeItem"> | null;
}

/** The sessionStorage key of the tab's unsaved drafts. */
export const DRAFTS_KEY = "cr.drafts";

export class AppHost implements Host {
  readonly api: Api;
  readonly store: AppStore;
  readonly records: RecordCache;
  readonly names: Names;
  readonly events: EventFeed;
  readonly drafts = new Drafts();
  readonly undo: UndoStack;
  readonly units: Units;
  readonly engine: EngineHandle;
  readonly registry: Registry;
  readonly ui = new Emitter<UiMessage>();
  /** The status bar's items, kept so a status bar that mounts late shows them. */
  readonly statusItems = new Map<string, StatusItem>();
  private metaP: Promise<Meta> | null = null;
  private oldHubUrl = "http://127.0.0.1:8765";
  private activations: Disposable[] = [];
  private unsubs: (() => void)[] = [];
  private readonly draftStore: Pick<Storage, "getItem" | "setItem" | "removeItem"> | null;
  /** Drafts kept by the tab before a reload, until Ben restores or drops them. */
  private kept: Draft[] = [];
  private keepTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(o: HostOptions) {
    this.registry = o.registry;
    this.api = o.api ?? new Api({ clientId: sessionClientId() });
    this.store = o.store ?? createAppStore();
    this.records = new RecordCache(this.api);
    this.names = new Names(this.records);
    this.units = o.units ?? new Units("m", safeStorage());
    this.engine = o.engine ?? createEngine();
    this.undo = new UndoStack(this.api, (recs, view) => this.applyWritten(recs, view));
    this.events =
      o.events ??
      connectEvents({
        url: `${this.api.base}/events`,
        pollUrl: `${this.api.base}/events/poll`,
        clientId: this.api.clientId,
      });
    this.unsubs.push(this.events.subscribe((m) => this.onFeed(m)));
    this.draftStore = o.draftStore === undefined ? safeSession() : o.draftStore;
    this.kept = this.readKept();
    this.unsubs.push(this.drafts.subscribe(() => this.keepDrafts()));
    // An old key in the URL (?route=Line_6, #Line_8, sel=legacy/...) is resolved through /legacy once it arrives.
    this.unsubs.push(
      this.store.subscribe((s, p) => {
        if (s.sel !== p.sel && s.sel && "legacy" in s.sel) void this.resolveSelection();
      }),
    );
  }

  /** Replace an old-key selection in the URL with the record it maps to (replaceState: no extra history step). */
  async resolveSelection(): Promise<void> {
    const sel = this.store.getState().sel;
    if (!sel || !("legacy" in sel)) return;
    const ref = await this.resolveLegacy(sel.legacy.lkind, sel.legacy.key);
    if (this.store.getState().sel !== sel) return;
    if (ref) this.store.getState().update({ sel: ref }, "replace");
    else this.toast({ text: `No record for old key ${sel.legacy.lkind} ${sel.legacy.key}.`, level: "warn" });
  }

  /** Whether closing or reloading the tab must ask first: any unsaved draft, in any layer. */
  beforeUnload(e: Pick<BeforeUnloadEvent, "preventDefault"> & { returnValue?: unknown }): boolean {
    this.flushKept();
    if (this.dirtyDrafts().length === 0) return false;
    e.preventDefault();
    e.returnValue = "";
    return true;
  }

  /** Write the tab's drafts to sessionStorage soon (a burst of keystrokes writes once). */
  private keepDrafts(): void {
    if (!this.draftStore || this.keepTimer) return;
    this.keepTimer = setTimeout(() => this.flushKept(), 300);
  }

  private flushKept(): void {
    if (this.keepTimer) clearTimeout(this.keepTimer);
    this.keepTimer = null;
    if (!this.draftStore) return;
    const all = [...this.dirtyDrafts(), ...this.kept];
    try {
      if (all.length === 0) this.draftStore.removeItem(DRAFTS_KEY);
      else
        this.draftStore.setItem(
          DRAFTS_KEY,
          JSON.stringify(all.map((d) => ({ kind: d.kind, id: d.id, view: d.view, base: d.base, body: d.body }))),
        );
    } catch {
      /* storage full or denied: the unload prompt still guards them */
    }
  }

  private readKept(): Draft[] {
    try {
      const raw = this.draftStore?.getItem(DRAFTS_KEY);
      if (!raw) return [];
      const list = JSON.parse(raw) as Pick<Draft, "kind" | "id" | "view" | "base" | "body">[];
      return list.map((d) => ({ ...d, key: this.drafts.key(d.kind, d.id, d.view), rev: 0, saving: false }));
    } catch {
      return [];
    }
  }

  /** Drafts this tab held before it was reloaded, not yet restored or dropped. */
  keptDrafts(): readonly Draft[] {
    return this.kept;
  }

  /** Put the kept drafts back as drafts (a save of one whose record moved on meets the 412 banner). */
  restoreKept(): number {
    const n = this.kept.length;
    for (const d of this.kept) this.drafts.restore(d);
    this.kept = [];
    this.flushKept();
    return n;
  }

  dropKept(): void {
    this.kept = [];
    this.flushKept();
  }

  /** After a reload: say that unsaved edits were kept, and offer them back. */
  offerKeptDrafts(): void {
    if (this.kept.length === 0) return;
    const what = this.kept.map((d) => `${this.names.text(d.kind, d.id, d.view)} on ${d.view.layer}`);
    this.toast({
      text: `Unsaved edits from before the reload: ${[...new Set(what)].join("; ")}.`,
      level: "warn",
      ttl: 0,
      actions: [
        {
          label: "Restore them",
          run: () => {
            const n = this.restoreKept();
            this.toast({ text: `Restored ${n} unsaved edit${n === 1 ? "" : "s"}.`, level: "info", ttl: 3000 });
          },
        },
        { label: "Drop them", run: () => this.dropKept() },
      ],
    });
  }

  /** Run every plugin's activate(), then resolve an old-key selection from the URL. Call once, after the shell is up. */
  activate(): void {
    void this.resolveSelection();
    this.offerKeptDrafts();
    for (const p of this.registry.plugins.values()) {
      try {
        const d = p.activate?.(this);
        if (d) this.activations.push(d);
      } catch (e) {
        this.toast({ text: `Plugin ${p.id} failed to start: ${String(e)}`, level: "error" });
      }
    }
  }

  dispose(): void {
    for (const d of this.activations) d.dispose();
    for (const u of this.unsubs) u();
    this.events.close();
    this.engine.dispose();
  }

  view(): View {
    return stateView(this.store.getState());
  }

  select(sel: Selection, opts: { c?: number } = {}): void {
    if (sel && "legacy" in sel) {
      void this.resolveLegacy(sel.legacy.lkind, sel.legacy.key).then((ref) => {
        if (ref) setSelection(this.store, ref, opts.c);
        else this.toast({ text: `No record for old key ${sel.legacy.lkind} ${sel.legacy.key}.`, level: "warn" });
      });
      return;
    }
    setSelection(this.store, sel, opts.c);
    if (isRecordRef(sel)) {
      for (const e of this.registry.panes.values())
        if (e.def.accepts?.(sel)) this.ui.emit({ type: "open", pane: e.def.id, params: {} });
    }
  }

  async resolveLegacy(lkind: string, key: string): Promise<{ kind: string; id: string } | null> {
    try {
      return await this.api.legacy(lkind, key);
    } catch (e) {
      this.problem(e);
      return null;
    }
  }

  openPane(paneId: string, params: Record<string, unknown> = {}): void {
    this.ui.emit({ type: "open", pane: paneId, params });
  }

  async runCommand(id: string, arg?: unknown): Promise<void> {
    const c = this.registry.commands.get(id)?.def;
    if (!c) {
      this.toast({ text: `No command ${id}.`, level: "warn" });
      return;
    }
    if (c.when && !c.when(this)) return;
    try {
      await c.run(this, arg);
    } catch (e) {
      this.problem(e);
    }
  }

  toast(t: Toast | string): void {
    this.ui.emit({ type: "toast", toast: typeof t === "string" ? { text: t } : t });
  }

  /** Show any error as a toast, with the request id of a problem response. */
  problem(e: unknown): void {
    if (e instanceof ApiError) {
      this.toast({
        text: e.message,
        level: e.status >= 500 || e.status === 0 ? "error" : "warn",
        requestId: e.requestId,
      });
    } else {
      this.toast({ text: String((e as Error)?.message ?? e), level: "error" });
    }
  }

  status(item: StatusItem | { id: string; remove: true }): void {
    if ("remove" in item) this.statusItems.delete(item.id);
    else this.statusItems.set(item.id, item);
    this.ui.emit({ type: "status", item });
  }

  meta(): Promise<Meta> {
    this.metaP ??= this.api.meta().then(
      (m) => {
        this.oldHubUrl = m.old_hub;
        return m;
      },
      (e) => {
        this.metaP = null;
        throw e;
      },
    );
    return this.metaP;
  }

  oldHub(): string {
    return this.oldHubUrl;
  }

  /**
   * Who owns a kind's records on main (decision 9.23): "legacy" while the old hub does, "model" once flipped, null
   * when no authority record names the kind. Read from main's authority records, which the record cache keeps fresh.
   */
  async owner(kind: string): Promise<string | null> {
    try {
      const { items } = await this.records.list("authority", makeView({ layer: "main" }), { limit: 500 });
      const rec = items.find((r) => (r.data as Record<string, unknown>).kind === kind && !r.deleted);
      const o = rec ? (rec.data as Record<string, unknown>).owner : null;
      return typeof o === "string" ? o : null;
    } catch {
      return null;
    }
  }

  /**
   * Whether records of a kind can be written in a view: true, or the plain reason they cannot. Import and legacy
   * layers are read-only; main refuses a kind the old hub owns (the server answers 409 authority).
   */
  async editable(kind: string, view: View = this.view()): Promise<true | string> {
    if (view.layer.includes(":")) return `${view.layer} is read-only: switch to a scenario to edit`;
    if (view.layer === "main" && (await this.owner(kind)) === "legacy")
      return `The old hub owns ${kind} records on main: switch to a scenario to edit`;
    return true;
  }

  /** The drafts with unsaved changes, in one layer or in all. */
  dirtyDrafts(layer?: string): Draft[] {
    return this.drafts.all().filter((d) => (layer === undefined || d.view.layer === layer) && this.drafts.dirty(d.key));
  }

  /** What a draft changes, in Ben's terms: "PVI 3 level on Line 6 profile". */
  draftLabel(d: Draft): string {
    const name = (id: string) => this.names.text("platform", id, d.view);
    return `${patchLabel(d.kind, this.drafts.ops(d), name)} on ${this.names.text(d.kind, d.id, d.view)}`;
  }

  /**
   * Save the drafts of the layer on view (the current one by default): a draft typed in another layer stays a draft
   * there, so Save on a scenario never re-sends a draft main refused. A stale one raises the Keep mine / Take theirs
   * banner; each save says what it saved, and as which version.
   */
  saveAll(label?: string, layer: string = this.view().layer): Promise<SaveOutcome[]> {
    // Kept until it ends, so a Ctrl+Z pressed meanwhile undoes this save, not the step it is writing (undoLast).
    const p = this.saveAllNow(label, layer);
    this.saving.add(p);
    const done = () => void this.saving.delete(p);
    p.then(done, done);
    return p;
  }

  /** Saves on their way (saveAll): Ctrl+Z and Ctrl+Shift+Z wait for them. */
  private readonly saving = new Set<Promise<unknown>>();

  private async settleSaves(): Promise<void> {
    while (this.saving.size) await Promise.allSettled([...this.saving]);
  }

  private async saveAllNow(label: string | undefined, layer: string): Promise<SaveOutcome[]> {
    const out: SaveOutcome[] = [];
    for (const d of this.dirtyDrafts(layer)) {
      const what = label ?? this.draftLabel(d);
      try {
        const r = await save(this, d.key, what);
        if (r.status === "stale") this.ui.emit({ type: "stale", offer: r.offer });
        if (r.status === "saved")
          this.toast({ text: `Saved ${what}: version ${r.rec.version} on ${r.rec.layer}.`, level: "info", ttl: 3000 });
        out.push(r);
      } catch (e) {
        this.problem(e);
      }
    }
    return out;
  }

  /** Whether Ctrl+Z has something to take back here: an unsaved step in this layer, else a saved changeset. */
  canUndo(): boolean {
    return !!this.drafts.peekStep(this.view().layer) || this.undo.canUndo;
  }

  canRedo(): boolean {
    return !!this.drafts.peekRedoStep(this.view().layer) || this.undo.canRedo;
  }

  /** Ctrl+Z: the last unsaved step of this layer first (profiles_parity.md 0.4), else the last saved changeset. */
  async undoLast(): Promise<void> {
    await this.settleSaves();
    const step = this.drafts.stepBack(this.view().layer);
    if (step) {
      this.toast({ text: `Undone: ${step.label} (not saved yet).`, level: "info", ttl: 2500 });
      return;
    }
    const e = this.undo.peek();
    try {
      const r = await this.undo.undo();
      if (r && e) this.toast({ text: `Undone: ${e.label}${versionNote(r.records)}.`, level: "info", ttl: 3000 });
    } catch (err) {
      this.problem(err);
    }
  }

  async redoLast(): Promise<void> {
    await this.settleSaves();
    const step = this.drafts.stepForward(this.view().layer);
    if (step) {
      this.toast({ text: `Redone: ${step.label} (not saved yet).`, level: "info", ttl: 2500 });
      return;
    }
    const e = this.undo.peekRedo();
    try {
      const r = await this.undo.redo();
      if (r && e) this.toast({ text: `Redone: ${e.label}${versionNote(r.records)}.`, level: "info", ttl: 3000 });
    } catch (err) {
      this.problem(err);
    }
  }

  private applyWritten(recs: Rec[], view: View): void {
    for (const r of recs) {
      this.records.set(r, view);
      const key = this.drafts.key(r.kind, r.id, view);
      if (this.drafts.byKey(key) && !this.drafts.dirty(key)) this.drafts.drop(key);
    }
  }

  private onFeed(m: FeedMessage): void {
    if (m.type === "status") {
      const label =
        m.state === "open"
          ? "live"
          : m.state === "connecting"
            ? "connecting"
            : m.state === "closed"
              ? "the hub is not answering"
              : m.state;
      this.status({
        id: "core.events",
        text: `events: ${label}`,
        level: m.state === "open" ? "info" : "warn",
        order: 0,
        title:
          m.state === "closed"
            ? "Is the hub running? Start it from the repo folder with .\\crhub (or crhub serve). The app reconnects by itself."
            : undefined,
      });
      return;
    }
    const ev: HubEvent = m.event;
    this.records.apply(ev);
    if (ev.type === "resync") {
      this.metaP = null;
      this.toast({
        text: `The hub asked for a resync (${ev.data.reason}); views were re-read.`,
        level: "info",
        ttl: 4000,
      });
    }
  }
}

/** ", now version 4 on try" for the one record an undo wrote. */
function versionNote(recs: Rec[] | undefined): string {
  const r = recs?.length === 1 ? recs[0] : undefined;
  return r ? `, now version ${r.version} on ${r.layer}` : "";
}

function safeSession(): Storage | null {
  try {
    return globalThis.sessionStorage ?? null;
  } catch {
    return null;
  }
}

function safeStorage(): Storage | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

/** One X-CR-Client per tab, kept across reloads of that tab. */
function sessionClientId(): string | undefined {
  try {
    const s = globalThis.sessionStorage;
    const have = s?.getItem("cr.client");
    if (have) return have;
    const id = new Api().clientId;
    s?.setItem("cr.client", id);
    return id;
  } catch {
    return undefined;
  }
}
