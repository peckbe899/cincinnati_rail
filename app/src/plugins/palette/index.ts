// The command palette (Ctrl+K): run any command, open any pane, or jump to a record by its name ("Line 6", "Bond
// Hill") or by an old key through the legacy index (section 8: "Ctrl+K resolves legacy keys"). Hits show names, never
// ids. Enter while a search is still on its way waits for it, then runs the top item; a search that finds nothing
// says so.

import type { AppHost } from "../../core/host.ts";
import type { Host, Plugin } from "../../core/plugin.ts";
import { parseSel } from "../../core/url.ts";
import { type LegacyHit, lookup, type NameHit, searchNames } from "./lookup.ts";

interface Item {
  label: string;
  hint: string;
  run(): void;
}

function open(host: Host): void {
  if (document.querySelector(".palette-backdrop")) return;
  const back = document.createElement("div");
  back.className = "palette-backdrop";
  const box = document.createElement("div");
  box.className = "palette";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-label", "Command palette");
  const input = document.createElement("input");
  input.className = "palette-input";
  input.placeholder = "A line or station (Line 6, Bond Hill), a command, or an old key (Line_8)";
  input.setAttribute("aria-label", "Command or old key");
  const list = document.createElement("ul");
  box.append(input, list);
  back.append(box);
  document.body.append(back);
  input.focus();

  let items: Item[] = [];
  let active = 0;
  let ctrl: AbortController | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  /** The search for the text as typed now, while it is on its way. */
  let searching: Promise<void> | null = null;
  /** Fires the debounced search at once (Enter before the pause is over). */
  let fireNow: (() => void) | null = null;
  const empty = document.createElement("p");
  empty.className = "muted palette-empty";
  empty.hidden = true;
  box.append(empty);
  const close = () => {
    ctrl?.abort();
    if (timer) clearTimeout(timer);
    back.remove();
  };

  const render = () => {
    list.replaceChildren();
    items.forEach((it, i) => {
      const li = document.createElement("li");
      li.className = i === active ? "active" : "";
      li.textContent = it.label;
      const small = document.createElement("small");
      small.textContent = it.hint;
      li.append(small);
      li.onmousedown = (e) => {
        e.preventDefault();
        close();
        it.run();
      };
      list.append(li);
    });
  };

  const staticItems = (q: string): Item[] => {
    const ql = q.toLowerCase();
    const out: Item[] = [];
    for (const { def } of host.registry.commands.values()) {
      if (def.id === "palette.open") continue;
      if (!ql || def.title.toLowerCase().includes(ql) || def.id.includes(ql)) {
        out.push({ label: def.title, hint: def.id, run: () => void host.runCommand(def.id) });
      }
    }
    for (const { def } of host.registry.panes.values()) {
      if (!ql || def.title.toLowerCase().includes(ql))
        out.push({ label: `Open ${def.title}`, hint: "pane", run: () => host.openPane(def.id) });
    }
    const sel = parseSel(q);
    if (sel && "kind" in sel) out.unshift({ label: `Select ${q}`, hint: "record", run: () => host.select(sel) });
    return out.slice(0, 30);
  };

  const view = host.view();
  /** "Bond Hill (Line 6)" for a platform, a stop or a station; a line by its own name. */
  const nameLabel = (h: NameHit, sections: Map<string, string>) => {
    if (h.section && (h.kind === "platform" || h.kind === "stop"))
      return `${h.name} (${sections.get(h.section) ?? host.names.text("section", h.section, view)})`;
    const line = h.kind === "station" && h.key?.includes("|") ? h.key.split("|")[0]?.replace(/_/g, " ") : null;
    return line ? `${h.name} (${line})` : h.name;
  };
  const KIND_WORD: Record<string, string> = {
    section: "line",
    route: "route",
    station: "station",
    platform: "platform",
  };

  const update = () => {
    const q = input.value;
    items = staticItems(q);
    active = 0;
    empty.hidden = true;
    render();
    ctrl?.abort();
    if (timer) clearTimeout(timer);
    searching = null;
    fireNow = null;
    if (q.trim().length < 2) return;
    let release: () => void = () => {};
    searching = new Promise<void>((r) => {
      release = r;
    });
    const run = async () => {
      timer = null;
      fireNow = null;
      const c = new AbortController();
      ctrl = c;
      const meta = await host.meta().catch(() => null);
      const [legacyHits, nameHits] = await Promise.all([
        meta ? lookup(host.api, meta, q, c.signal).catch((): LegacyHit[] => []) : Promise.resolve([] as LegacyHit[]),
        searchNames(host.api, view, q, c.signal).catch((): NameHit[] => []),
      ]);
      if (c.signal.aborted) return release();
      for (const h of nameHits) host.names.remember(h.kind, h.id, h.name, view);
      // The lines of the platforms found, by name, before the list draws.
      const secIds = [...new Set(nameHits.flatMap((h) => (h.section ? [h.section] : [])))];
      const secNames = new Map(
        await Promise.all(secIds.map(async (id) => [id, await host.names.get("section", id, view)] as const)),
      );
      if (c.signal.aborted) return release();
      const byName: Item[] = nameHits.map((h) => ({
        label: nameLabel(h, secNames),
        hint: KIND_WORD[h.kind] ?? h.kind,
        run: () => host.select({ kind: h.kind, id: h.id }),
      }));
      const fresh = legacyHits.filter((h) => !nameHits.some((n) => n.kind === h.kind && n.id === h.id));
      // An old key's record by name, with its line for a platform or a stop: "Line_6|Bond Hill → Bond Hill (Line 6)".
      const named = await Promise.all(fresh.map((h) => host.names.full(h.kind, h.id, view)));
      if (c.signal.aborted) return release();
      const legacy: Item[] = fresh.map((h, i) => ({
        label: `${h.key} → ${named[i]}`,
        hint: `old ${h.lkind} key, ${KIND_WORD[h.kind] ?? h.kind}`,
        run: () => host.select({ kind: h.kind, id: h.id }),
      }));
      items = [...legacy, ...byName, ...staticItems(q)];
      active = 0;
      empty.textContent = `No line, station, command or old key matches "${q.trim()}".`;
      empty.hidden = items.length > 0;
      render();
      release();
    };
    fireNow = () => {
      if (timer) clearTimeout(timer);
      void run();
    };
    timer = setTimeout(() => void run(), 200);
  };

  input.addEventListener("input", update);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
    else if (e.key === "ArrowDown") active = Math.min(items.length - 1, active + 1);
    else if (e.key === "ArrowUp") active = Math.max(0, active - 1);
    else if (e.key === "Enter") {
      e.preventDefault();
      // A search still on its way (Enter right after typing): wait for it, so Enter runs what the text finds.
      const pending = searching;
      fireNow?.();
      void (async () => {
        if (pending) await pending;
        const it = items[active];
        if (!it) {
          empty.hidden = false;
          return;
        }
        close();
        it.run();
      })();
      return;
    } else return;
    e.preventDefault();
    render();
  });
  back.addEventListener("mousedown", (e) => {
    if (e.target === back) close();
  });
  update();
}

const plugin: Plugin = {
  id: "palette",
  commands: [{ id: "palette.open", title: "Command palette", run: (host) => open(host) }],
  keymap: [{ key: "Ctrl+K", command: "palette.open" }],
  activate(host) {
    const ui = (host as Partial<AppHost>).ui;
    const off = ui?.on((m) => {
      if (m.type === "palette" && m.open) open(host);
    });
    return off ? { dispose: off } : undefined;
  },
};

export default plugin;
