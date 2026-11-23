// Maximise a pane to the whole dock, and back (dockview's maximised group). Any pane can ask: its own button sends
// MAXIMISE_REQUEST from inside its element; Shift+F (outside a text field), a double-click on a tab and the palette's
// command toggle the pane in focus. The dock tells each pane whether it is maximised with MAXIMISED_EVENT on its
// element and a data-maximised attribute. The state is kept for the browser tab's session (sessionStorage), not in
// the saved layout, so a new session starts with every pane in its place.

/** Sent (bubbling) from inside a pane's element: toggle this pane's maximised state. */
export const MAXIMISE_REQUEST = "cr:maximise";
/** Sent on window by the palette command: toggle the pane in focus. */
export const MAXIMISE_ACTIVE = "cr:maximise-active";
/** Sent on a pane's element by the dock, detail true or false: the pane is now maximised or not. */
export const MAXIMISED_EVENT = "cr:maximised";

export function maximisedKey(workspace: string): string {
  return `cr.maximised.${workspace}`;
}

/** The pane kept maximised in this session, if any. */
export function keptMaximised(workspace: string, store: Pick<Storage, "getItem"> = sessionStorage): string | null {
  try {
    return store.getItem(maximisedKey(workspace));
  } catch {
    return null;
  }
}

export function keepMaximised(
  workspace: string,
  paneId: string | null,
  store: Pick<Storage, "setItem" | "removeItem"> = sessionStorage,
): void {
  try {
    if (paneId) store.setItem(maximisedKey(workspace), paneId);
    else store.removeItem(maximisedKey(workspace));
  } catch {
    /* storage denied: the pane is maximised for now only */
  }
}

/** Whether a key press is the maximise key: Shift+F, outside a text field (where it types an F). */
export function isMaximiseKey(e: {
  key: string;
  shiftKey: boolean;
  ctrlKey: boolean;
  altKey: boolean;
  metaKey: boolean;
  target: EventTarget | null;
}): boolean {
  if (!e.shiftKey || e.ctrlKey || e.altKey || e.metaKey || (e.key !== "F" && e.key !== "f")) return false;
  const t = e.target as HTMLElement | null;
  return !(t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName ?? "")));
}

/** A saved layout without dockview's maximised node: maximising lasts the session, the layout outlives it. */
export function withoutMaximised<T>(layout: T): T {
  const grid = (layout as { grid?: Record<string, unknown> } | null)?.grid;
  if (grid && "maximizedNode" in grid) {
    const { maximizedNode: _, ...rest } = grid;
    return { ...(layout as object), grid: rest } as T;
  }
  return layout;
}
