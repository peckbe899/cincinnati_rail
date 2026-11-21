// Jobs: the pane listing running and recent jobs, and the status bar's job count. Job and result events are
// ephemeral (section 5), so after every reconnect and resync the list is re-read from /jobs?active=1.

import type { Job, ResultEvent } from "../../api/types.ts";
import type { Host, Plugin } from "../../core/plugin.ts";

/** The jobs the app knows of, by id, from /jobs and job events. */
export class JobBoard {
  readonly jobs = new Map<string, Job & { at: number }>();
  readonly results: (ResultEvent & { at: number })[] = [];
  private subs = new Set<() => void>();

  reset(active: Job[]): void {
    for (const [id, j] of this.jobs) if (j.state === "queued" || j.state === "running") this.jobs.delete(id);
    for (const j of active) this.jobs.set(j.id, { ...j, at: Date.now() });
    this.emit();
  }

  job(j: Job): void {
    this.jobs.set(j.id, { ...this.jobs.get(j.id), ...j, at: Date.now() });
    const finished = [...this.jobs.values()].filter((x) => x.state !== "queued" && x.state !== "running");
    for (const old of finished.sort((a, b) => a.at - b.at).slice(0, Math.max(0, finished.length - 30)))
      this.jobs.delete(old.id);
    this.emit();
  }

  result(r: ResultEvent): void {
    this.results.unshift({ ...r, at: Date.now() });
    this.results.length = Math.min(this.results.length, 20);
    this.emit();
  }

  active(): Job[] {
    return [...this.jobs.values()].filter((j) => j.state === "queued" || j.state === "running");
  }

  subscribe(fn: () => void): () => void {
    this.subs.add(fn);
    return () => this.subs.delete(fn);
  }

  private emit(): void {
    for (const fn of [...this.subs]) fn();
  }
}

const board = new JobBoard();

async function reread(host: Host): Promise<void> {
  try {
    board.reset(await host.api.jobs(true));
  } catch {
    /* the status bar shows the connection state already */
  }
}

function statusText(): string {
  const a = board.active();
  const running = a.filter((j) => j.state === "running").length;
  if (!a.length) return "jobs: idle";
  return `jobs: ${running} running, ${a.length - running} queued`;
}

const plugin: Plugin = {
  id: "jobs",
  activate(host) {
    const unsubBoard = board.subscribe(() =>
      host.status({ id: "jobs", text: statusText(), level: "info", order: 10, title: "Open the jobs pane" }),
    );
    const unsubEvents = host.events.subscribe((m) => {
      if (m.type === "status" && m.state === "open") void reread(host);
      if (m.type !== "event") return;
      if (m.event.type === "job") board.job(m.event.data);
      else if (m.event.type === "result") board.result(m.event.data);
      else if (m.event.type === "resync") void reread(host);
    });
    void reread(host);
    return {
      dispose() {
        unsubBoard();
        unsubEvents();
      },
    };
  },
  panes: [
    {
      id: "jobs",
      title: "Jobs",
      async mount(el, ctx) {
        const host = ctx.host;
        const root = document.createElement("div");
        root.className = "pane";
        el.append(root);
        const draw = () => {
          root.replaceChildren();
          const h = document.createElement("h3");
          h.textContent = statusText();
          const table = document.createElement("table");
          table.className = "grid";
          table.innerHTML =
            "<tr><th class=name>job</th><th class=name>scope</th><th class=name>state</th><th>progress</th><th></th></tr>";
          const jobs = [...board.jobs.values()].sort((a, b) => b.at - a.at);
          for (const j of jobs) {
            const tr = document.createElement("tr");
            tr.dataset.job = j.id;
            const cells = [
              j.type,
              j.scope,
              j.error ? `${j.state}: ${j.error}` : `${j.state}${j.msg ? ` (${j.msg})` : ""}`,
            ];
            for (const text of cells) {
              const td = document.createElement("td");
              td.className = "name";
              td.textContent = text;
              tr.append(td);
            }
            const prog = document.createElement("td");
            const bar = document.createElement("span");
            bar.className = "progress";
            const fill = document.createElement("span");
            fill.style.width = `${Math.round(Math.max(0, Math.min(1, j.progress ?? 0)) * 100)}%`;
            bar.append(fill);
            prog.append(bar);
            const act = document.createElement("td");
            if (j.state === "queued" || j.state === "running") {
              const b = document.createElement("button");
              b.type = "button";
              b.textContent = "Cancel";
              b.onclick = () => host.api.cancelJob(j.id).catch((e) => host.problem(e));
              act.append(b);
            }
            tr.append(prog, act);
            table.append(tr);
          }
          root.append(h, table);
          if (board.results.length) {
            const r = document.createElement("h3");
            r.textContent = "Recent results";
            const ul = document.createElement("ul");
            ul.className = "plain";
            for (const x of board.results) {
              const li = document.createElement("li");
              li.textContent = `${x.type} ${x.scope} ${x.status}${x.changed?.length ? `, changed ${x.changed.map(([a, b]) => `${Math.round(a ?? 0)}-${Math.round(b ?? 0)} m`).join(", ")}` : ""}`;
              ul.append(li);
            }
            root.append(r, ul);
          }
        };
        draw();
        return { dispose: board.subscribe(draw) };
      },
    },
  ],
  commands: [{ id: "jobs.pane", title: "Show jobs", run: (host) => host.openPane("jobs") }],
};

export default plugin;
