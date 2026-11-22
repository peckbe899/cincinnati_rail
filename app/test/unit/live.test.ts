// @vitest-environment happy-dom
// The live hub in the app: the Sources chip's words, the pending marks, and the Sources pane updating in place (rows
// kept, only changed text rewritten) with Undo this import and Pause live.

import { describe, expect, it, vi } from "vitest";
import type { LiveStatus, SourceEvent } from "../../src/api/types.ts";
import { chipText, LiveBoard, liveBoard, stateText } from "../../src/core/live.ts";
import type { Host, PaneContext } from "../../src/core/plugin.ts";
import plugin from "../../src/plugins/sources/index.ts";

const src = (over: Partial<SourceEvent> = {}): SourceEvent => ({
  source: "import:profile_lines",
  label: "Line files",
  kind: "import",
  state: "applied",
  text: "Line 3 updated from the line files: 2 stations moved, re-solving",
  at: "2026-11-22T14:02:00Z",
  run: 7,
  changeset: "CS1",
  review: 0,
  sections: ["S3"],
  toast: true,
  undo: true,
  ...over,
});

describe("the Sources chip", () => {
  it("says live, pending, paused and off in plain words", () => {
    const b = new LiveBoard();
    expect(chipText(b)).toBe("live");
    b.summary = { paused: false, pending: 2, updated: null };
    expect(chipText(b)).toBe("live: 2 pending");
    b.summary = { paused: true, pending: 1, updated: null };
    expect(chipText(b)).toBe("live: paused, 1 waiting");
    b.summary = { paused: false, pending: 0, updated: "2026-11-22T14:02:00Z" };
    expect(chipText(b)).toMatch(/^live, updated \d\d:\d\d$/);
    b.enabled = false;
    expect(chipText(b)).toBe("live: off");
    expect(stateText("held")).toBe("held (you undid it)");
  });

  it("marks a section importing before re-solving, in its own view only", () => {
    const b = new LiveBoard();
    b.setMarks([{ type: "profiles.solve_section", scope: "S3", view: "main|-|canon", state: "re-solving" }]);
    expect(b.pendingFor("S3", "main|-|canon")).toBe("re-solving");
    expect(b.pendingFor("S3", "try|-|canon")).toBeNull();
    b.setMarks([...b.marks, { type: "import", scope: "S3", view: "main|-|canon", state: "importing" }]);
    expect(b.pendingFor("S3", "try|-|canon")).toBe("importing");
    expect(b.pendingFor("S6", "main|-|canon")).toBeNull();
  });
});

describe("the Sources pane", () => {
  it("updates rows in place and offers Undo this import and Pause live", async () => {
    const status: LiveStatus = {
      enabled: true,
      paused: false,
      pending: 0,
      updated: null,
      sources: [src({ state: "idle", text: "up to date", changeset: null, undo: false })],
    };
    const liveSource = vi.fn(async (_s: string, _a: string) => src({ state: "held", changeset: null, undo: false }));
    const livePause = vi.fn(async (on: boolean) => ({ paused: on, pending: 0, updated: null }));
    const host = {
      api: { live: async () => status, liveSource, livePause },
      toast: vi.fn(),
      problem: vi.fn(),
      status: vi.fn(),
      openPane: vi.fn(),
    } as unknown as Host;
    const el = document.createElement("div");
    const pane = plugin.panes?.[0];
    const mounted = await pane?.mount(el, { host, params: {}, state: undefined } as unknown as PaneContext);
    await new Promise((r) => setTimeout(r, 0));
    const row = () => el.querySelector('tr[data-source="import:profile_lines"]') as HTMLTableRowElement;
    expect(row()).not.toBeNull();
    const first = row();
    expect(first.textContent).toContain("up to date");
    expect((first.querySelector('button[data-action="undo"]') as HTMLButtonElement).hidden).toBe(true);
    liveBoard.source(src());
    expect(row()).toBe(first); // the same row, updated in place
    expect(first.dataset.state).toBe("applied");
    expect(first.textContent).toContain("Line 3 updated from the line files: 2 stations moved, re-solving");
    const undo = first.querySelector('button[data-action="undo"]') as HTMLButtonElement;
    expect(undo.hidden).toBe(false);
    undo.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(liveSource).toHaveBeenCalledWith("import:profile_lines", "undo");
    expect(row().dataset.state).toBe("held");
    expect((first.querySelector('button[data-action="apply"]') as HTMLButtonElement).hidden).toBe(false);
    const toggle = el.querySelector('[data-testid="live-toggle"]') as HTMLButtonElement;
    expect(toggle.textContent).toBe("Pause live");
    toggle.click();
    await new Promise((r) => setTimeout(r, 0));
    expect(livePause).toHaveBeenCalledWith(true);
    expect(toggle.textContent).toBe("Resume live");
    expect(el.querySelector('[data-testid="sources-history"]')?.textContent).toContain("Line 3 updated");
    mounted?.dispose();
  });
});
