// Links to the old hub's pages on port 8765 (decision 9.23: two processes, no change to the old hub). The pages
// keep working until the new panes replace them; this pane only links, and never writes to the old hub.

import type { Host, Plugin } from "../../core/plugin.ts";
import { isRecordRef } from "../../core/plugin.ts";

export const OLD_PAGES: { id: string; title: string; path: string; about: string }[] = [
  { id: "home", title: "Home", path: "/", about: "Roadmap, runs, metro structure" },
  { id: "deck", title: "Deck", path: "/deck/", about: "Streets, blocks, stations and plots" },
  { id: "profiles", title: "Profiles", path: "/profiles/profiles.html", about: "Line profiles (Metro and RER)" },
  { id: "3d", title: "Station 3D", path: "/3d/", about: "Stations and structures in 3D" },
  { id: "chronology", title: "Chronology", path: "/chronology/", about: "Segment and station dates" },
  { id: "access", title: "Access", path: "/access/", about: "Station access choices" },
];

const ROUTE_RE = /^(Line_[0-9]+[a-z]?|RER_[A-Z0-9_]+|CVG_Express)$/i;

/** The old page URL for a page id, with the route as the Profiles page's hash when one is known. */
export function oldPageUrl(base: string, page: string, route?: string | null): string {
  const p = OLD_PAGES.find((x) => x.id === page) ?? OLD_PAGES[0];
  const url = `${base.replace(/\/$/, "")}${p?.path ?? "/"}`;
  return page === "profiles" && route && ROUTE_RE.test(route) ? `${url}#${route}` : url;
}

/** The old route id of the selection, if the URL or the record says one. */
async function routeOf(host: Host): Promise<string | null> {
  const s = host.store.getState();
  if (s.sel && "legacy" in s.sel && s.sel.legacy.lkind === "route") return s.sel.legacy.key;
  if (!isRecordRef(s.sel)) return null;
  try {
    const rec = await host.records.get(s.sel.kind, s.sel.id, host.view());
    const d = rec.data as Record<string, unknown>;
    for (const v of [d.route, d.route_id, d.line, d.name, d.legacy_key])
      if (typeof v === "string" && ROUTE_RE.test(v)) return v;
  } catch {
    /* no record, no route */
  }
  return null;
}

const plugin: Plugin = {
  id: "legacy",
  panes: [
    {
      id: "legacy",
      title: "Old hub",
      async mount(el, ctx) {
        const host = ctx.host;
        const root = document.createElement("div");
        root.className = "pane";
        el.append(root);
        const draw = async () => {
          const base = host.oldHub();
          const route = await routeOf(host);
          root.replaceChildren();
          const h = document.createElement("h3");
          h.textContent = `The old hub (${base})`;
          const ul = document.createElement("ul");
          ul.className = "plain";
          for (const p of OLD_PAGES) {
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = oldPageUrl(base, p.id, route);
            a.target = "_blank";
            a.rel = "noopener";
            a.textContent = p.id === "profiles" && route ? `${p.title}: ${route}` : p.title;
            const small = document.createElement("span");
            small.className = "muted";
            small.textContent = ` ${p.about}`;
            li.append(a, small);
            ul.append(li);
          }
          const note = document.createElement("p");
          note.className = "muted";
          note.textContent =
            "The old hub runs separately (python hub\\hub.py). These links open it; nothing here writes to it.";
          root.append(h, ul, note);
        };
        await host.meta().catch(() => null);
        await draw();
        const unsub = host.store.subscribe((s, prev) => {
          if (s.sel !== prev.sel) void draw();
        });
        return { dispose: unsub };
      },
    },
  ],
  commands: [
    {
      id: "legacy.open-profiles",
      title: "Open this route in the old Profiles page",
      async run(host) {
        window.open(oldPageUrl(host.oldHub(), "profiles", await routeOf(host)), "_blank", "noopener");
      },
    },
    { id: "legacy.pane", title: "Show the old hub's pages", run: (host) => host.openPane("legacy") },
  ],
};

export default plugin;
