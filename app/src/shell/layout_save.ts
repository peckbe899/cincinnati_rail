// Saving the dock's layout (Dock.tsx) without costing the page. Two traps in dockview made a save every 500 ms,
// for ever, and each one, with a pane maximised, laid the whole dock out twice (the map's WebGL canvas resized
// both times), a 50 to 90 ms long task in the middle of a drag:
//
// - updateParameters() fires the layout change the save listens to, so a save that writes a pane's state back,
//   changed or not, schedules the next save;
// - toJSON() on a maximised dock exits the maximised view, serialises, and maximises again.
//
// So a save writes a pane's state only when it changed, never calls toJSON() while a pane is maximised (it lays
// the pane states over the last layout taken docked), and writes storage only when the text changed.

export interface SavePanel {
  id: string;
  params?: Record<string, unknown>;
  api: { updateParameters(p: Record<string, unknown>): void };
}

export interface SaveApi {
  readonly panels: readonly SavePanel[];
  toJSON(): unknown;
  hasMaximizedGroup(): boolean;
}

export interface LayoutSaver {
  /** Save now: the panes' states into their params, the layout into storage. */
  save(): void;
  /** Take the docked layout now (before a maximise the session kept is put back), so a save while maximised has
   * a layout to lay the pane states over. */
  prime(): void;
}

const same = (a: unknown, b: unknown) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

export function layoutSaver(o: {
  api: () => SaveApi | null;
  /** A pane's serialize() result, undefined when it keeps none. */
  stateOf: (p: SavePanel) => unknown;
  /** The layout as stored (withoutMaximised). */
  clean: (layout: unknown) => unknown;
  write: (text: string) => void;
}): LayoutSaver {
  let docked: { panels?: Record<string, { params?: Record<string, unknown> }> } | null = null;
  let written: string | null = null;
  const take = (api: SaveApi) => {
    docked = structuredClone(o.clean(api.toJSON())) as typeof docked;
  };
  return {
    prime() {
      const api = o.api();
      if (api && !api.hasMaximizedGroup()) take(api);
    },
    save() {
      const api = o.api();
      if (!api) return;
      for (const p of api.panels) {
        const state = o.stateOf(p);
        if (state === undefined || same(state, p.params?.state)) continue;
        p.api.updateParameters({ ...(p.params ?? {}), state });
      }
      let layout: unknown;
      if (!api.hasMaximizedGroup()) {
        take(api);
        layout = docked;
      } else {
        if (!docked) return; // nothing docked to save over yet: the save after the maximise ends writes it
        const panels = { ...(docked.panels ?? {}) };
        for (const p of api.panels) {
          const was = panels[p.id];
          if (was) panels[p.id] = { ...was, params: p.params };
        }
        layout = { ...docked, panels };
      }
      const text = JSON.stringify(layout);
      if (text === written) return;
      written = text;
      o.write(text);
    },
  };
}
