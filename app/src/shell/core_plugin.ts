// The shell's own commands and keys, registered like any plugin so the palette and the keymap see them.
// Ctrl+Z and Ctrl+Shift+Z leave a focused text field to its own undo; Ctrl+S and Ctrl+K work everywhere.

import type { AppHost } from "../core/host.ts";
import type { Plugin } from "../core/plugin.ts";

export function corePlugin(host: AppHost): Plugin {
  return {
    id: "core",
    commands: [
      {
        id: "core.undo",
        title: "Undo the last saved change",
        run: () => host.undoLast(),
        when: () => host.undo.canUndo,
      },
      { id: "core.redo", title: "Redo", run: () => host.redoLast(), when: () => host.undo.canRedo },
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
        run: () => {
          for (const k of Object.keys(localStorage)) if (k.startsWith("cr.layout.")) localStorage.removeItem(k);
          location.reload();
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

/** Keys a focused text field keeps for itself. */
export const TEXT_KEYS: ReadonlySet<string> = new Set(["ctrl+z", "ctrl+shift+z", "ctrl+y"]);
