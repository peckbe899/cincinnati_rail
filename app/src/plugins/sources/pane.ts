// The Sources pane (see index.ts): each watched source, its state, its last change and what it did, with Pause live,
// Undo this import, Apply and Check now, and the last ten changes. Rows are found by source id and only the text that
// changed is rewritten, so nothing flickers and a focused button keeps its focus.

import type { SourceEvent } from "../../api/types.ts";
import { clockText, liveBoard, stateText } from "../../core/live.ts";
import type { Host } from "../../core/plugin.ts";
import { act, pause, reread } from "./actions.ts";

function button(text: string, title: string, run: () => void): HTMLButtonElement {
  const b = Object.assign(document.createElement("button"), { type: "button", textContent: text, title });
  b.onclick = run;
  return b;
}

function setText(el: HTMLElement, text: string): void {
  if (el.textContent !== text) el.textContent = text;
}

export function mountPane(el: HTMLElement, host: Host): () => void {
  const root = document.createElement("div");
  root.className = "pane sources-pane";
  root.dataset.testid = "sources-pane";
  const head = document.createElement("div");
  head.className = "sources-head";
  const summary = document.createElement("strong");
  summary.dataset.testid = "sources-summary";
  const toggle = button("Pause live", "Stop taking in changes until you resume", () => {
    void pause(host, !liveBoard.summary.paused);
  });
  toggle.dataset.testid = "live-toggle";
  head.append(summary, toggle);
  const table = document.createElement("table");
  table.className = "grid sources";
  const thead = document.createElement("tr");
  for (const h of ["source", "state", "last change", "what it did", ""]) {
    const th = document.createElement("th");
    th.className = "name";
    th.textContent = h;
    thead.append(th);
  }
  table.append(thead);
  const recent = document.createElement("ul");
  recent.className = "plain sources-history";
  recent.dataset.testid = "sources-history";
  const recentTitle = Object.assign(document.createElement("h3"), { textContent: "Recent" });
  root.append(head, table, recentTitle, recent);
  el.append(root);
  type Row = {
    tr: HTMLTableRowElement;
    cells: [HTMLElement, HTMLElement, HTMLElement, HTMLElement];
    buttons: [HTMLButtonElement, HTMLButtonElement, HTMLButtonElement];
  };
  const rows = new Map<string, Row>();

  const row = (src: SourceEvent) => {
    let r = rows.get(src.source);
    if (!r) {
      const tr = document.createElement("tr");
      tr.dataset.source = src.source;
      const cell = () => {
        const td = document.createElement("td");
        td.className = "name";
        tr.append(td);
        return td;
      };
      const cells: Row["cells"] = [cell(), cell(), cell(), cell()];
      const actions = document.createElement("td");
      const undo = button(
        "Undo this import",
        "Revert this import's changes (held until its files change again)",
        () => void act(host, src.source, "undo"),
      );
      undo.dataset.action = "undo";
      const apply = button(
        "Apply",
        "Take in the files you undid, as they are now",
        () => void act(host, src.source, "apply"),
      );
      apply.dataset.action = "apply";
      const check = button("Check now", "Look at this source now", () => void act(host, src.source, "check"));
      check.dataset.action = "check";
      actions.append(undo, apply, check);
      tr.append(actions);
      table.append(tr);
      r = { tr, cells, buttons: [undo, apply, check] };
      rows.set(src.source, r);
    }
    const [name, state, when, what] = r.cells;
    setText(name, src.label);
    setText(state, stateText(src.state));
    r.tr.dataset.state = src.state;
    setText(when, clockText(src.at ?? src.changed));
    setText(what, src.text || "");
    const [undo, apply, check] = r.buttons;
    // offered while the source's last import stands: a re-save, a half-written file or a no-op does not hide it
    const canUndo = src.undo ?? (!!src.changeset && (src.state === "applied" || src.state === "review"));
    undo.hidden = src.kind !== "import" || !canUndo;
    apply.hidden = src.state !== "held";
    check.hidden = src.kind !== "import";
  };

  const draw = () => {
    const s = liveBoard.summary;
    setText(
      summary,
      liveBoard.enabled
        ? `${s.paused ? "Live is paused" : "Live"}: ${liveBoard.sources.size} sources watched${s.pending ? `, ${s.pending} waiting` : ""}${s.updated ? `, last change taken in at ${clockText(s.updated)}` : ""}`
        : "Live is off: this hub serves with --no-live.",
    );
    setText(toggle, s.paused ? "Resume live" : "Pause live");
    toggle.title = s.paused
      ? "Take in what changed while paused, and every change from now on"
      : "Stop taking in changes until you resume";
    toggle.disabled = !liveBoard.enabled;
    for (const src of liveBoard.sources.values()) row(src);
    const items = liveBoard.history.slice(0, 10);
    const texts = items.map((h) => `${clockText(h.at)} ${h.text}`);
    const now = [...recent.children].map((li) => li.textContent);
    if (texts.join("\n") !== now.join("\n")) {
      recent.replaceChildren(...texts.map((t) => Object.assign(document.createElement("li"), { textContent: t })));
    }
  };
  draw();
  void reread(host);
  const off = liveBoard.subscribe(draw);
  return () => {
    off();
    el.replaceChildren();
  };
}
