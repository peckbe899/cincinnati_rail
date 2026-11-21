// The command palette (Ctrl+K): run any command, open any pane, or jump to a record by an old key through the
// legacy index (section 8: "Ctrl+K resolves legacy keys").

import type { AppHost } from "../../core/host.ts";
import type { Host, Plugin } from "../../core/plugin.ts";
import { parseSel } from "../../core/url.ts";
import { type LegacyHit, lookup } from "./lookup.ts";

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
  input.placeholder = "Command, pane, kind:id or an old key (Line_8, Line_8|Cincinnati State#2)";
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

  const update = () => {
    const q = input.value;
    items = staticItems(q);
    active = 0;
    render();
    ctrl?.abort();
    if (timer) clearTimeout(timer);
    if (q.trim().length < 2) return;
    timer = setTimeout(async () => {
      const c = new AbortController();
      ctrl = c;
      let hits: LegacyHit[] = [];
      try {
        hits = await lookup(host.api, await host.meta(), q, c.signal);
      } catch {
        hits = [];
      }
      if (c.signal.aborted) return;
      const legacy: Item[] = hits.map((h) => ({
        label: `${h.key} → ${h.kind} ${h.id}`,
        hint: `old ${h.lkind}`,
        run: () => host.select({ kind: h.kind, id: h.id }),
      }));
      items = [...legacy, ...staticItems(q)];
      render();
    }, 200);
  };

  input.addEventListener("input", update);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
    else if (e.key === "ArrowDown") active = Math.min(items.length - 1, active + 1);
    else if (e.key === "ArrowUp") active = Math.max(0, active - 1);
    else if (e.key === "Enter") {
      const it = items[active];
      close();
      it?.run();
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
