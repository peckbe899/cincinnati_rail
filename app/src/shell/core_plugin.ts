// The shell's own commands and keys, registered like any plugin so the palette and the keymap see them.
// Ctrl+Z and Ctrl+Shift+Z leave a focused text field to its own undo while it holds text typed since it was drawn
// (or last saved); in a field that still shows what it was drawn with, they are the hub's undo and redo, so Ctrl+Z
// right after a save never undoes one keystroke of the saved text. Ctrl+S and Ctrl+K work everywhere.

import type { AppHost } from "../core/host.ts";
import type { Plugin } from "../core/plugin.ts";

export function corePlugin(host: AppHost): Plugin {
  return {
    id: "core",
    commands: [
      {
        id: "core.undo",
        title: "Undo the last change (an unsaved step first, then the last save)",
        run: () => host.undoLast(),
        when: () => host.canUndo(),
      },
      { id: "core.redo", title: "Redo", run: () => host.redoLast(), when: () => host.canRedo() },
      { id: "core.save", title: "Save every draft", run: () => void host.saveAll() },
      { id: "core.units", title: "Switch units (m, ft)", run: () => host.units.toggle() },
      {
        id: "core.timeline",
        title: "Switch timeline (canon, real)",
        run: () => {
          const s = host.store.getState();
          s.update({ tl: s.tl === "canon" ? "real" : "canon" });
        },
      },
      {
        id: "core.reset-layout",
        title: "Reset the pane layout",
        // The dock lays the panes out again in place: no reload, so no unsaved edit is lost.
        run: () => {
          for (const k of Object.keys(localStorage)) if (k.startsWith("cr.layout.")) localStorage.removeItem(k);
          host.ui.emit({ type: "reset-layout" });
        },
      },
    ],
    keymap: [
      { key: "Ctrl+Z", command: "core.undo" },
      { key: "Ctrl+Shift+Z", command: "core.redo" },
      { key: "Ctrl+Y", command: "core.redo" },
      { key: "Ctrl+S", command: "core.save" },
    ],
  };
}

/** Keys a focused text field keeps for itself, while it holds text of its own. */
export const TEXT_KEYS: ReadonlySet<string> = new Set(["ctrl+z", "ctrl+shift+z", "ctrl+y"]);

/**
 * Whether a key belongs to the focused element rather than the hub's keymap: Ctrl+Z and its kin in a text field
 * that holds text typed since it was drawn. A field that marks what it was drawn with (data-drawn, as the line
 * sheet's cells do) and still shows it hands them to the hub.
 */
export function fieldKeepsKey(t: EventTarget | null, key: string): boolean {
  if (!TEXT_KEYS.has(key)) return false;
  const el = t as HTMLElement | null;
  if (!el || !(el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName ?? ""))) return false;
  const drawn = (el as HTMLInputElement).dataset?.drawn;
  return drawn === undefined || (el as HTMLInputElement).value !== drawn;
}
