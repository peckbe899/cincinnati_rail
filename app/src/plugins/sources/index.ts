// Sources: the live hub in the app (checklist I2.0). A status bar chip ("live", "live: 2 pending", "live: paused")
// that opens the Sources pane; a toast in plain words for every change the hub takes in ("Line 3 updated from the
// old hub: 2 stations moved, re-solving"), with Undo and Review; and the pane, listing each watched source, its state,
// its last change and what it did, with Pause live, Undo this import, Apply (held files) and Check now. The pane is
// updated in place from the events: rows are found by source id and only the text that changed is rewritten, so
// nothing flickers and a focused button keeps its focus.

import type { SourceEvent } from "../../api/types.ts";
import { chipText, liveBoard } from "../../core/live.ts";
import type { Host, Plugin } from "../../core/plugin.ts";
import { act, pause, reread } from "./actions.ts";

function chip(host: Host): void {
  const s = liveBoard.summary;
  host.status({
    id: "sources",
    text: chipText(liveBoard),
    level: !liveBoard.enabled || s.paused ? "warn" : "info",
    order: 5,
    title: liveBoard.enabled
      ? "The hub takes in changes to the line files, the old hub and the data tiers as they are saved. Click for the sources."
      : "The hub serves without live updates (crhub serve --no-live).",
    command: "sources.pane",
  });
}

function toast(host: Host, ev: SourceEvent): void {
  if (!ev.toast || !ev.text) return;
  const actions: { label: string; run(): void }[] = [];
  if (ev.undo) actions.push({ label: "Undo this import", run: () => void act(host, ev.source, "undo") });
  if (ev.review) actions.push({ label: "Review", run: () => host.openPane("review") });
  host.toast({ text: ev.text, level: ev.level === "error" ? "error" : ev.level === "warn" ? "warn" : "info", actions });
}

const plugin: Plugin = {
  id: "sources",
  activate(host) {
    const offBoard = liveBoard.subscribe(() => chip(host));
    chip(host);
    const offEvents = host.events.subscribe((m) => {
      if (m.type === "status") {
        if (m.state === "open") void reread(host);
        return;
      }
      const ev = m.event;
      if (ev.type === "source") {
        liveBoard.source(ev.data);
        toast(host, ev.data);
      } else if (ev.type === "live") liveBoard.setSummary(ev.data);
      else if (ev.type === "pending") liveBoard.setMarks(ev.data.items ?? []);
      else if (ev.type === "resync") void reread(host);
    });
    void reread(host);
    return {
      dispose() {
        offBoard();
        offEvents();
        host.status({ id: "sources", remove: true });
      },
    };
  },
  panes: [
    {
      id: "sources",
      title: "Sources",
      async mount(el, ctx) {
        const { mountPane } = await import("./pane.ts");
        const dispose = mountPane(el, ctx.host);
        return { dispose };
      },
    },
  ],
  commands: [
    { id: "sources.pane", title: "Show the sources (live updates)", run: (host) => host.openPane("sources") },
    {
      id: "live.pause",
      title: "Pause live",
      run: (host) => pause(host, true),
      when: () => liveBoard.enabled && !liveBoard.summary.paused,
    },
    {
      id: "live.resume",
      title: "Resume live",
      run: (host) => pause(host, false),
      when: () => liveBoard.enabled && liveBoard.summary.paused,
    },
  ],
};

export default plugin;
