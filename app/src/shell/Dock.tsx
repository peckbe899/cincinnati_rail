// The dock: dockview hosting every pane. Each dockview panel is the generic "pane" component, which looks the
// PaneDef up in the registry by params.paneId and lets it draw into a plain div (panes choose their framework).
// The layout is kept per workspace in localStorage, with each pane's serialize() result in its params.

import type { DockviewApi, DockviewReadyEvent, IDockviewPanelProps } from "dockview-react";
import { DockviewReact, themeDark } from "dockview-react";
import { useCallback, useEffect, useRef } from "react";
import type { AppHost } from "../core/host.ts";
import type { MountedPane, PaneContext } from "../core/plugin.ts";
import { layoutSaver, type SaveApi } from "./layout_save.ts";
import {
  isMaximiseKey,
  keepMaximised,
  keptMaximised,
  MAXIMISE_ACTIVE,
  MAXIMISE_REQUEST,
  MAXIMISED_EVENT,
  withoutMaximised,
} from "./maximise.ts";

interface PaneParams {
  paneId: string;
  state?: unknown;
  [k: string]: unknown;
}

// 2: the line sheet takes about half the width, so its stations can be told apart (profiles_parity.md A.1).
const LAYOUT_VERSION = 2;

function layoutKey(workspace: string): string {
  return `cr.layout.v${LAYOUT_VERSION}.${workspace}`;
}

/**
 * The default design workspace: the map on the left, the line sheet in the middle with the whole column's height
 * (its table needs the rows) and about two thirds of the width, the inspector on the right with Jobs, Review, Old hub and Sources as tabs below it.
 */
export function defaultLayout(api: DockviewApi, has: (id: string) => boolean): void {
  const add = (paneId: string, position?: Parameters<DockviewApi["addPanel"]>[0]["position"]) => {
    if (!has(paneId)) return;
    const title = paneId;
    api.addPanel({ id: paneId, component: "pane", title, params: { paneId }, position });
  };
  add("map");
  add("line-sheet", has("map") ? { referencePanel: "map", direction: "right" } : undefined);
  add("inspector", has("line-sheet") ? { referencePanel: "line-sheet", direction: "right" } : undefined);
  const below = has("inspector") ? "inspector" : "line-sheet";
  add("jobs", has(below) ? { referencePanel: below, direction: "below" } : undefined);
  add("review", has("jobs") ? { referencePanel: "jobs" } : undefined);
  add("legacy", has("jobs") ? { referencePanel: "jobs" } : undefined);
  add("sources", has("jobs") ? { referencePanel: "jobs" } : undefined);
  api.getPanel("jobs")?.api.setActive();
  api.getPanel("inspector")?.api.setActive();
  api.getPanel("line-sheet")?.api.setActive();
  // The line sheet gets about two thirds of the width, the map and the inspector a sixth each: with the station
  // panel beside it the plot keeps about 650 px on a 1600 px screen (at half the width it had 490, too few to tell
  // the downtown stations apart).
  const w = api.width;
  if (w > 900) {
    try {
      api.getPanel("map")?.api.setSize({ width: Math.round(w * 0.18) });
      api.getPanel("inspector")?.api.setSize({ width: Math.round(w * 0.18) });
    } catch {
      /* a layout without these panes keeps dockview's split */
    }
  }
}

function PaneHost(props: IDockviewPanelProps<PaneParams> & { host: AppHost }) {
  const ref = useRef<HTMLDivElement>(null);
  const { host, api, containerApi } = props;
  const paneId = props.params.paneId;
  // The pane mounts once per pane id; later parameter changes reach it through ctx.params, not a remount.
  const params = useRef(props.params);
  params.current = props.params;
  useEffect(() => {
    const el = ref.current;
    const def = host.registry.pane(paneId);
    if (!el) return;
    if (!def) {
      el.textContent = `No pane "${paneId}" is registered.`;
      return;
    }
    api.setTitle(def.title);
    let mounted: MountedPane | null = null;
    let gone = false;
    const resizers = new Set<() => void>();
    const sub = api.onDidDimensionsChange(() => {
      for (const fn of resizers) fn();
    });
    // Maximise (maximise.ts): the pane's own button asks from inside its element; the dock says whether it is.
    const toggle = (e: Event) => {
      e.stopPropagation();
      if (api.isMaximized()) api.exitMaximized();
      else api.maximize();
    };
    el?.addEventListener(MAXIMISE_REQUEST, toggle);
    const tell = () => {
      if (!el) return;
      const on = api.isMaximized();
      if ((el.dataset.maximised === "1") === on) return;
      if (on) el.dataset.maximised = "1";
      else delete el.dataset.maximised;
      el.dispatchEvent(new CustomEvent(MAXIMISED_EVENT, { detail: on }));
    };
    tell();
    const maxSub = containerApi.onDidMaximizedGroupChange(tell);
    const ctx: PaneContext = {
      host,
      // A getter, so params set later (openPane on a pane already open) are what the pane reads.
      get params() {
        return params.current;
      },
      state: params.current.state,
      setTitle: (t) => api.setTitle(t),
      onResize(fn) {
        resizers.add(fn);
        return { dispose: () => resizers.delete(fn) };
      },
      isActive: () => api.isActive,
      onActive(fn) {
        const d = api.onDidActiveChange((e) => fn(e.isActive));
        return { dispose: () => d.dispose() };
      },
    };
    def.mount(el, ctx).then(
      (m) => {
        if (gone) m.dispose();
        else mounted = m;
        (el as HTMLElement & { __serialize?: () => unknown }).__serialize = () => mounted?.serialize?.();
      },
      (e) => {
        el.textContent = `The ${def.title} pane failed to open: ${String((e as Error)?.message ?? e)}`;
        host.problem(e);
      },
    );
    return () => {
      gone = true;
      sub.dispose();
      maxSub.dispose();
      el.removeEventListener(MAXIMISE_REQUEST, toggle);
      mounted?.dispose();
      el.replaceChildren();
    };
  }, [host, api, containerApi, paneId]);
  return <div ref={ref} className="pane-root" data-pane={paneId} />;
}

export function Dock({ host, workspace }: { host: AppHost; workspace: string }) {
  const apiRef = useRef<DockviewApi | null>(null);
  const saveTimer = useRef<number | undefined>(undefined);

  // A save writes only what changed and never lays a maximised dock out (layout_save.ts): before, each save fired
  // the next one, every 500 ms, and each laid the whole dock out twice while a pane was maximised.
  const ws = useRef(workspace);
  ws.current = workspace;
  const saver = useRef(
    layoutSaver({
      api: () => apiRef.current as SaveApi | null,
      stateOf: (p) => {
        const el = document.querySelector(`[data-pane="${CSS.escape(String(p.params?.paneId ?? ""))}"]`) as
          | (HTMLElement & { __serialize?: () => unknown })
          | null;
        return el?.__serialize?.();
      },
      clean: withoutMaximised,
      write: (text) => {
        try {
          localStorage.setItem(layoutKey(ws.current), text);
        } catch {
          /* storage full or denied: the default layout comes back next time */
        }
      },
    }),
  );
  const saveLayout = useCallback(() => saver.current.save(), []);

  const onReady = useCallback(
    (event: DockviewReadyEvent) => {
      apiRef.current = event.api;
      const has = (id: string) => host.registry.panes.has(id);
      let restored = false;
      try {
        const saved = localStorage.getItem(layoutKey(workspace));
        if (saved) {
          event.api.fromJSON(JSON.parse(saved));
          for (const p of [...event.api.panels]) if (!has(String(p.params?.paneId))) p.api.close();
          restored = event.api.panels.length > 0;
        }
      } catch {
        event.api.clear();
      }
      if (!restored) defaultLayout(event.api, has);
      // A pane maximised earlier in this session is maximised again (a reload keeps it; a new session does not).
      const kept = keptMaximised(workspace);
      const keptPanel = kept ? event.api.getPanel(kept) : undefined;
      saver.current.prime();
      if (keptPanel && !keptPanel.api.isMaximized()) keptPanel.api.maximize();
      event.api.onDidMaximizedGroupChange(() => {
        const on = event.api.panels.find((p) => p.api.isMaximized());
        keepMaximised(workspace, on ? on.id : null);
      });
      event.api.onDidLayoutChange(() => {
        window.clearTimeout(saveTimer.current);
        saveTimer.current = window.setTimeout(saveLayout, 500);
      });
    },
    [host, workspace, saveLayout],
  );

  useEffect(
    () =>
      host.ui.on((m) => {
        if (m.type === "reset-layout") {
          // Lay the panes out afresh in place: the host, its drafts and its undo stack stay as they are.
          const api = apiRef.current;
          if (!api) return;
          api.clear();
          keepMaximised(workspace, null);
          defaultLayout(api, (id) => host.registry.panes.has(id));
          host.toast({ text: "The pane layout is back to the default.", level: "info", ttl: 3000 });
          return;
        }
        if (m.type !== "open") return;
        const api = apiRef.current;
        if (!api || !host.registry.panes.has(m.pane)) return;
        const existing = api.getPanel(m.pane);
        if (existing) {
          existing.api.setActive();
          if (Object.keys(m.params).length) existing.api.updateParameters({ ...(existing.params ?? {}), ...m.params });
          return;
        }
        const def = host.registry.pane(m.pane);
        api.addPanel({
          id: m.pane,
          component: "pane",
          title: def?.title ?? m.pane,
          params: { paneId: m.pane, ...m.params },
        });
      }),
    [host, workspace],
  );

  // Shift+F (outside a text field), a double-click on a tab, and the palette's command toggle the pane in focus.
  useEffect(() => {
    const toggleActive = () => {
      const p = apiRef.current?.activePanel;
      if (!p) return;
      if (p.api.isMaximized()) p.api.exitMaximized();
      else p.api.maximize();
    };
    const onKey = (e: KeyboardEvent) => {
      if (!isMaximiseKey(e)) return;
      e.preventDefault();
      toggleActive();
    };
    const onDbl = (e: MouseEvent) => {
      const t = e.target as HTMLElement | null;
      if (t?.closest?.(".dock .dv-tab")) toggleActive();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("dblclick", onDbl);
    window.addEventListener(MAXIMISE_ACTIVE, toggleActive);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("dblclick", onDbl);
      window.removeEventListener(MAXIMISE_ACTIVE, toggleActive);
    };
  }, []);

  useEffect(() => {
    window.addEventListener("pagehide", saveLayout);
    return () => window.removeEventListener("pagehide", saveLayout);
  }, [saveLayout]);

  const components = useRef({
    pane: (p: IDockviewPanelProps<PaneParams>) => <PaneHost {...p} host={host} />,
  }).current;

  return <DockviewReact className="dock" components={components} onReady={onReady} theme={themeDark} />;
}
