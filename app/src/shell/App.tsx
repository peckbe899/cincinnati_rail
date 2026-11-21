// The shell: a top bar (view, units, undo, save), the dock, the status bar, toasts and the 412 banner.

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import type { LayerMeta } from "../api/types.ts";
import type { AppHost } from "../core/host.ts";
import type { StatusItem, Toast } from "../core/plugin.ts";
import type { StaleOffer } from "../core/save.ts";
import type { AppState } from "../core/store.ts";
import { Dock } from "./Dock.tsx";

function useAppState<T>(host: AppHost, pick: (s: AppState) => T): T {
  return useSyncExternalStore(
    (fn) => host.store.subscribe(fn),
    () => pick(host.store.getState()),
  );
}

function useTick(subscribe: (fn: () => void) => () => void): number {
  const [n, setN] = useState(0);
  useEffect(() => subscribe(() => setN((v) => v + 1)), [subscribe]);
  return n;
}

const SLUG_RE = /^[a-z][a-z0-9_-]{0,63}$/;

function TopBar({ host }: { host: AppHost }) {
  const layer = useAppState(host, (s) => s.layer);
  const year = useAppState(host, (s) => s.year);
  const tl = useAppState(host, (s) => s.tl);
  const [layers, setLayers] = useState<LayerMeta[]>([]);
  useTick(useCallback((fn) => host.undo.subscribe(fn), [host]));
  useTick(useCallback((fn) => host.drafts.subscribe(() => fn()), [host]));
  useTick(useCallback((fn) => host.units.onChange(() => fn()), [host]));
  const [yearText, setYearText] = useState(year === null ? "" : String(year));
  useEffect(() => setYearText(year === null ? "" : String(year)), [year]);

  const loadLayers = useCallback(() => {
    host.api.layers().then(setLayers, () => setLayers([]));
  }, [host]);
  useEffect(loadLayers, [loadLayers]);

  const onLayer = async (v: string) => {
    if (v !== "+new") {
      host.store.getState().update({ layer: v });
      return;
    }
    const slug = window.prompt("Name of the new scenario (lowercase letters, digits, - and _):", "try");
    if (!slug) return;
    if (!SLUG_RE.test(slug)) {
      host.toast({ text: `${slug} is not a layer name.`, level: "warn" });
      return;
    }
    try {
      await host.api.createLayer(slug, "scenario", layer.includes(":") ? "main" : layer);
      loadLayers();
      host.store.getState().update({ layer: slug });
    } catch (e) {
      host.problem(e);
    }
  };

  const writable = layers.filter((l) => l.tier === "main" || l.tier === "scenario" || l.tier === "proposal");
  const dirty = host.drafts.all().filter((d) => host.drafts.dirty(d.key)).length;
  return (
    <header className="topbar">
      <strong className="brand">Cincinnati Rail hub</strong>
      <label>
        Layer{" "}
        <select aria-label="Layer" value={layer} onChange={(e) => void onLayer(e.target.value)} data-testid="layer">
          {writable.length === 0 || !writable.some((l) => l.slug === layer) ? (
            <option value={layer}>{layer}</option>
          ) : null}
          {writable.map((l) => (
            <option key={l.slug} value={l.slug}>
              {l.slug}
            </option>
          ))}
          <option value="+new">New scenario…</option>
        </select>
      </label>
      <label>
        Year{" "}
        <input
          aria-label="Year"
          className="year"
          placeholder="now"
          value={yearText}
          onChange={(e) => setYearText(e.target.value)}
          onBlur={() => {
            const y = yearText.trim() === "" ? null : Number(yearText);
            if (y === null || (Number.isInteger(y) && y >= -9999 && y <= 9999))
              host.store.getState().update({ year: y, month: null });
            else setYearText(year === null ? "" : String(year));
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") (e.target as HTMLInputElement).blur();
          }}
        />
      </label>
      <button
        type="button"
        onClick={() => host.store.getState().update({ tl: tl === "canon" ? "real" : "canon" })}
        title="Timeline"
      >
        {tl}
      </button>
      <button type="button" onClick={() => host.units.toggle()} title="Display units" data-testid="units">
        {host.units.length}
      </button>
      <span className="spacer" />
      <button type="button" disabled={!host.undo.canUndo} onClick={() => void host.undoLast()} title="Undo (Ctrl+Z)">
        Undo
      </button>
      <button
        type="button"
        disabled={!host.undo.canRedo}
        onClick={() => void host.redoLast()}
        title="Redo (Ctrl+Shift+Z)"
      >
        Redo
      </button>
      <button
        type="button"
        disabled={dirty === 0}
        onClick={() => void host.saveAll()}
        title="Save (Ctrl+S)"
        data-testid="save"
      >
        Save{dirty ? ` (${dirty})` : ""}
      </button>
      <button
        type="button"
        onClick={() => host.ui.emit({ type: "palette", open: true })}
        title="Commands and old keys (Ctrl+K)"
      >
        Ctrl+K
      </button>
    </header>
  );
}

function StatusBar({ host }: { host: AppHost }) {
  const [items, setItems] = useState<Map<string, StatusItem>>(() => new Map(host.statusItems));
  useEffect(
    () =>
      host.ui.on((m) => {
        if (m.type !== "status") return;
        setItems((prev) => {
          const next = new Map(prev);
          if ("remove" in m.item) next.delete(m.item.id);
          else next.set(m.item.id, m.item);
          return next;
        });
      }),
    [host],
  );
  useTick(useCallback((fn) => host.engine.onChange(() => fn()), [host]));
  const engine = host.engine.state();
  const sorted = [...items.values()].sort((a, b) => (a.order ?? 50) - (b.order ?? 50));
  return (
    <footer className="statusbar" data-testid="statusbar">
      {sorted.map((i) => (
        <span key={i.id} className={`status-item ${i.level ?? "info"}`} title={i.title} data-status={i.id}>
          {i.text}
        </span>
      ))}
      <span
        className={`status-item ${engine === "unavailable" ? "warn" : "info"}`}
        title={host.engine.reason() ?? ""}
        data-status="core.engine"
      >
        engine: {engine}
      </span>
    </footer>
  );
}

function Toasts({ host }: { host: AppHost }) {
  const [toasts, setToasts] = useState<(Toast & { n: number })[]>([]);
  useEffect(() => {
    let n = 0;
    return host.ui.on((m) => {
      if (m.type !== "toast") return;
      const t = { ...m.toast, n: ++n };
      setToasts((prev) => [...prev.slice(-4), t]);
      const ttl = t.ttl ?? (t.level === "error" ? 0 : 6000);
      if (ttl > 0) setTimeout(() => setToasts((prev) => prev.filter((x) => x.n !== t.n)), ttl);
    });
  }, [host]);
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.n} className={`toast ${t.level ?? "info"}`} role={t.level === "error" ? "alert" : "status"}>
          <span>{t.text}</span>
          {t.requestId ? <small> request {t.requestId}</small> : null}
          {t.actions?.map((a) => (
            <button type="button" key={a.label} onClick={a.run}>
              {a.label}
            </button>
          ))}
          <button type="button" aria-label="Dismiss" onClick={() => setToasts((p) => p.filter((x) => x.n !== t.n))}>
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

function StaleBanner({ host }: { host: AppHost }) {
  const [offer, setOffer] = useState<StaleOffer | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => host.ui.on((m) => m.type === "stale" && setOffer(m.offer)), [host]);
  if (!offer) return null;
  const who = offer.by ?? offer.theirs.by;
  const run = async (f: () => unknown) => {
    setBusy(true);
    try {
      await f();
      setOffer(null);
    } catch (e) {
      host.problem(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="stale-banner" role="alert" data-testid="stale-banner">
      <span>
        {offer.theirs.kind} {offer.theirs.id} was saved by {who} (version {offer.theirs.version}) while you were editing
        it.
      </span>
      <button type="button" disabled={busy} onClick={() => void run(() => offer.keepMine())}>
        Keep mine
      </button>
      <button type="button" disabled={busy} onClick={() => void run(() => offer.takeTheirs())}>
        Take theirs
      </button>
    </div>
  );
}

export function App({ host }: { host: AppHost }) {
  const workspace = useAppState(host, (s) => s.workspace);
  return (
    <div className="shell">
      <TopBar host={host} />
      <StaleBanner host={host} />
      <main className="dock-area">
        <Dock key={workspace} host={host} workspace={workspace} />
      </main>
      <StatusBar host={host} />
      <Toasts host={host} />
    </div>
  );
}
