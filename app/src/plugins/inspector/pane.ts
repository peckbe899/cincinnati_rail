// The inspector pane: the selected record's bookkeeping and a form from its kind's schema. Edits go into the shared
// draft (the line sheet sees them at once); Save sends the coalesced patch with If-Match.
//
// In Ben's terms: the heading names the record ("Section: Line 6", "Profile: Line 6 profile"), the bookkeeping line
// says which layer and who in plain words, in local time, and a reference or a platform id inside the form shows the
// record's name. The form is read-only where a save would be refused (an import or legacy layer, or main while the
// old hub owns the kind), and says why.

import type { JsonPatch, Rec } from "../../api/types.ts";
import { actorText, layerPhrase, localTime } from "../../core/describe.ts";
import { bodyOf } from "../../core/drafts.ts";
import type { MountedPane, PaneContext } from "../../core/plugin.ts";
import { isRecordRef } from "../../core/plugin.ts";
import { FormBuilder } from "./form.ts";

export async function mountInspector(el: HTMLElement, ctx: PaneContext): Promise<MountedPane> {
  const host = ctx.host;
  const root = document.createElement("div");
  root.className = "pane";
  el.append(root);
  let rec: Rec | null = null;
  let stopWatch: (() => void) | null = null;
  let pending = false;
  let renders = 0;

  /** Whether Ben is typing in a field of the form: then a redraw waits, so his text is not replaced under him. A
   * focused button or checkbox does not hold a redraw back: after "Remove this item" the form must show the list
   * as it now is, or the next click would act on an index that has moved. */
  const typing = () => {
    const a = document.activeElement;
    if (!a || !root.contains(a)) return false;
    if (a instanceof HTMLTextAreaElement) return true;
    return a instanceof HTMLInputElement && !["checkbox", "radio", "button", "submit"].includes(a.type);
  };

  const render = async () => {
    if (typing()) {
      pending = true;
      return;
    }
    pending = false;
    // Renders can overlap (the record watch and follow() both start one, each awaiting /meta): only the latest
    // one draws, and it replaces the pane's content in one step, so the form is never drawn twice.
    const n = ++renders;
    const sel = host.store.getState().sel;
    if (!isRecordRef(sel)) {
      root.replaceChildren(
        Object.assign(document.createElement("p"), {
          className: "muted",
          textContent: "Select a record on the map or in a list.",
        }),
      );
      return;
    }
    if (!rec) {
      root.replaceChildren(
        Object.assign(document.createElement("p"), {
          className: "muted",
          textContent: `Loading ${host.names.text(sel.kind, sel.id, host.view())}…`,
        }),
      );
      return;
    }
    const view = host.view();
    const shown = rec;
    const [meta, editable, name] = await Promise.all([
      host.meta().catch(() => null),
      host.editable(shown.kind, view),
      host.names.full(shown.kind, shown.id, view),
      primeNames(shown),
    ]);
    if (n !== renders || !rec) return;
    if (typing()) {
      pending = true;
      return;
    }
    const out: HTMLElement[] = [];
    const kind = meta?.kinds[rec.kind];
    const draft = host.drafts.get(rec.kind, rec.id, view);
    const body = draft?.body ?? bodyOf(rec);
    const head = document.createElement("h3");
    head.textContent = `${kind?.title ?? rec.kind}: ${name}`;
    head.title = `${rec.kind} ${rec.id}`;
    const book = document.createElement("p");
    book.className = "muted";
    book.textContent = `version ${rec.version} ${layerPhrase(rec.layer)}, by ${actorText(rec.by)}, ${localTime(rec.updated)}${draft ? " (unsaved changes)" : ""}`;
    book.title = `layer ${rec.layer}, by ${rec.by}, ${rec.updated}`;
    const bar = document.createElement("div");
    const save = Object.assign(document.createElement("button"), {
      type: "button",
      textContent: "Save",
      disabled: !draft,
    });
    save.onclick = () => void host.runCommand("core.save");
    const discard = Object.assign(document.createElement("button"), {
      type: "button",
      textContent: "Discard",
      disabled: !draft,
    });
    discard.onclick = () => draft && host.drafts.drop(draft.key);
    bar.append(save, discard);
    out.push(head, book, bar);
    if (!kind) {
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(body.data, null, 1);
      out.push(
        Object.assign(document.createElement("p"), {
          className: "muted",
          textContent: "No schema for this kind in /meta.",
        }),
        pre,
      );
      root.replaceChildren(...out);
      return;
    }
    const current = rec;
    const readOnly = editable !== true;
    const form = new FormBuilder({
      units: host.units,
      base: current.data,
      readOnly,
      refs: kind.refs,
      name: (k, id) => (k ? host.names.text(k, id, view) : (anyName(id) ?? id)),
      choices: async (k) => {
        const { items } = await host.records.list(k, view, { limit: 500, fields: "name,key" });
        host.names.learn(items, view);
        return items.map((r) => ({ id: r.id, name: host.names.text(k, r.id, view) }));
      },
      open: (k, id) => host.select({ kind: k, id }),
      onPatch: (ops: JsonPatch) => {
        try {
          host.drafts.edit(current, view, ops);
        } catch (e) {
          host.problem(e);
        }
      },
    }).build(kind.schema, body.data);
    if (readOnly) {
      out.push(
        Object.assign(document.createElement("p"), {
          className: "muted",
          textContent: `${editable}.`,
        }),
      );
    }
    out.push(form);
    root.replaceChildren(...out);
  };

  /** Names of the records a record's form shows by id: a profile's platform keys, from its section's platforms. */
  const primed = new Set<string>();
  const primeNames = async (r: Rec) => {
    const d = r.data as Record<string, unknown>;
    const sec = typeof d.section === "string" ? d.section : null;
    if (r.kind !== "profile" || !sec || primed.has(sec)) return;
    primed.add(sec);
    try {
      const { items } = await host.records.list("platform", host.view(), { parent: sec, limit: 500 });
      host.names.learn(items, host.view());
    } catch {
      /* the ids show short instead */
    }
  };
  /** A platform's or a stop's name by id alone (the form's id keys do not say their kind). */
  const anyName = (id: string): string | null => {
    for (const k of ["platform", "stop", "station", "section", "route", "node"]) {
      const n = host.names.peek(k, id, host.view());
      if (n) return n;
    }
    return null;
  };

  const follow = () => {
    stopWatch?.();
    stopWatch = null;
    rec = null;
    const sel = host.store.getState().sel;
    if (isRecordRef(sel)) {
      stopWatch = host.records.watch(sel.kind, sel.id, host.view(), (r) => {
        if (r.data) rec = r.data;
        if (r.error) {
          renders++;
          root.replaceChildren(
            Object.assign(document.createElement("p"), {
              className: "muted",
              textContent: `${host.names.text(sel.kind, sel.id, host.view())}: ${r.error.message}`,
            }),
          );
          return;
        }
        void render();
      });
    }
    void render();
  };

  const onFocusOut = () => {
    setTimeout(() => {
      if (pending && !typing()) void render();
    }, 0);
  };
  root.addEventListener("focusout", onFocusOut);
  const unsubStore = host.store.subscribe((s, p) => {
    if (s.sel !== p.sel || s.layer !== p.layer || s.year !== p.year || s.tl !== p.tl) follow();
  });
  // A draft edited elsewhere (the line sheet's table, one keystroke at a time) redraws the form once typing pauses,
  // so the form never competes with the sheet's re-solve for the main thread.
  let soon: ReturnType<typeof setTimeout> | null = null;
  const unsubDrafts = host.drafts.subscribe(() => {
    if (soon) clearTimeout(soon);
    soon = setTimeout(() => void render(), 150);
  });
  const unsubUnits = host.units.onChange(() => void render());
  const unsubNames = host.names.onChange(() => void render());
  follow();
  return {
    dispose() {
      renders++;
      stopWatch?.();
      unsubStore();
      unsubDrafts();
      if (soon) clearTimeout(soon);
      unsubUnits();
      unsubNames();
      root.removeEventListener("focusout", onFocusOut);
    },
  };
}
