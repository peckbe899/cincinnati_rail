// The Host every plugin and pane gets (section 8): the transport, the URL store, the record cache patched by the
// event stream, drafts, undo, units, the engine and the registry, plus the shell's services (toasts, status items,
// opening panes, the 412 banner). The React shell renders what the host's ui bus says; the host knows no React.

import { Api, ApiError } from "../api/client.ts";
import { connectEvents, type EventFeed, type FeedMessage } from "../api/events.ts";
import type { HubEvent, Meta, Rec } from "../api/types.ts";
import { createEngine, type EngineHandle } from "../engine/client.ts";
import { Drafts } from "./drafts.ts";
import type { Disposable, Host, Selection, StatusItem, Toast } from "./plugin.ts";
import { isRecordRef } from "./plugin.ts";
import { RecordCache } from "./records.ts";
import type { Registry } from "./registry.ts";
import { type SaveOutcome, type StaleOffer, save } from "./save.ts";
import { type AppStore, createAppStore, setSelection, stateView } from "./store.ts";
import { UndoStack } from "./undo.ts";
import { Units } from "./units.ts";
import type { View } from "./view.ts";

export type UiMessage =
  | { type: "toast"; toast: Toast }
  | { type: "status"; item: StatusItem | { id: string; remove: true } }
  | { type: "open"; pane: string; params: Record<string, unknown> }
  | { type: "stale"; offer: StaleOffer }
  | { type: "palette"; open: boolean };

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
}

export class AppHost implements Host {
  readonly api: Api;
  readonly store: AppStore;
  readonly records: RecordCache;
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

  constructor(o: HostOptions) {
    this.registry = o.registry;
    this.api = o.api ?? new Api({ clientId: sessionClientId() });
    this.store = o.store ?? createAppStore();
    this.records = new RecordCache(this.api);
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

  /** Run every plugin's activate(), then resolve an old-key selection from the URL. Call once, after the shell is up. */
  activate(): void {
    void this.resolveSelection();
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

  /** Save every draft; a stale one raises the Keep mine / Take theirs banner. */
  async saveAll(label = "edit"): Promise<SaveOutcome[]> {
    const out: SaveOutcome[] = [];
    for (const d of this.drafts.all()) {
      try {
        const r = await save(this, d.key, label);
        if (r.status === "stale") this.ui.emit({ type: "stale", offer: r.offer });
        out.push(r);
      } catch (e) {
        this.problem(e);
      }
    }
    return out;
  }

  async undoLast(): Promise<void> {
    try {
      await this.undo.undo();
    } catch (e) {
      this.problem(e);
    }
  }

  async redoLast(): Promise<void> {
    try {
      await this.undo.redo();
    } catch (e) {
      this.problem(e);
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
      const label = m.state === "open" ? "live" : m.state === "connecting" ? "connecting" : m.state;
      this.status({
        id: "core.events",
        text: `events: ${label}`,
        level: m.state === "open" ? "info" : "warn",
        order: 0,
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
