// The review queue (decision 9.11), read-only in this increment: orphans, proposals and conflicts from /conflicts,
// each a link to its record. It re-reads after a changeset that could raise conflicts (an import, a rebase, a
// promote) and after a resync.

import type { Conflict } from "../../api/types.ts";
import type { Plugin } from "../../core/plugin.ts";

export const GROUPS: { id: string; title: string; reasons: string[] }[] = [
  { id: "proposals", title: "Proposals", reasons: ["geometry_under_edit"] },
  { id: "conflicts", title: "Conflicts", reasons: ["both_changed", "authority_divergence", "namespace", "invalid"] },
  { id: "orphans", title: "Orphans", reasons: ["orphan", "dangling_ref"] },
];

export function groupConflicts(rows: Conflict[]): Record<string, Conflict[]> {
  const out: Record<string, Conflict[]> = Object.fromEntries(GROUPS.map((g) => [g.id, [] as Conflict[]]));
  for (const r of rows) {
    const g = GROUPS.find((x) => x.reasons.includes(r.reason)) ?? GROUPS[1];
    out[g?.id ?? "conflicts"]?.push(r);
  }
  return out;
}

const plugin: Plugin = {
  id: "review",
  panes: [
    {
      id: "review",
      title: "Review",
      async mount(el, ctx) {
        const host = ctx.host;
        const root = document.createElement("div");
        root.className = "pane";
        el.append(root);
        let timer: ReturnType<typeof setTimeout> | null = null;
        let rows: Conflict[] = [];
        const load = async () => {
          try {
            rows = await host.api.conflicts({ state: "open", layer: host.view().layer });
          } catch (e) {
            root.textContent = `The review queue could not be read: ${String((e as Error).message ?? e)}`;
            return;
          }
          draw();
        };
        const draw = () => {
          const groups = groupConflicts(rows);
          root.replaceChildren();
          const h = document.createElement("h3");
          h.textContent = rows.length ? `Review: ${rows.length} open` : "Review: nothing open";
          root.append(h);
          for (const g of GROUPS) {
            const list = groups[g.id] ?? [];
            if (!list.length) continue;
            const sec = document.createElement("section");
            const t = document.createElement("h3");
            t.textContent = `${g.title} (${list.length})`;
            const ul = document.createElement("ul");
            ul.className = "plain";
            for (const c of list) {
              const li = document.createElement("li");
              const a = document.createElement("a");
              a.href = "#";
              a.textContent = host.names.text(c.kind, c.rec_id, host.view());
              a.title = `${c.kind} ${c.rec_id}`;
              a.onclick = (e) => {
                e.preventDefault();
                host.select({ kind: c.kind, id: c.rec_id });
              };
              const why = document.createElement("span");
              why.className = "muted";
              why.textContent = ` (${c.kind}): ${c.reason.replace(/_/g, " ")} on ${c.layer}`;
              li.append(a, why);
              ul.append(li);
            }
            sec.append(t, ul);
            root.append(sec);
          }
        };
        const soon = () => {
          if (timer) clearTimeout(timer);
          timer = setTimeout(() => void load(), 300);
        };
        await load();
        // Names arrive after the first draw: draw again with them (a short wait folds a burst into one read).
        const unsubNames = host.names.onChange(draw);
        const unsubEvents = host.events.subscribe((m) => {
          if (m.type !== "event") return;
          const ev = m.event;
          if (ev.type === "resync") soon();
          if (ev.type === "changeset" && ["import", "rebase", "promote", "legacy"].includes(ev.data.kind ?? "")) soon();
        });
        const unsubStore = host.store.subscribe((s, p) => {
          if (s.layer !== p.layer) soon();
        });
        return {
          dispose() {
            if (timer) clearTimeout(timer);
            unsubEvents();
            unsubStore();
            unsubNames();
          },
        };
      },
    },
  ],
};

export default plugin;
