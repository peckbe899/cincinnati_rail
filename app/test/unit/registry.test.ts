import { describe, expect, it } from "vitest";
import type { Plugin } from "../../src/core/plugin.ts";
import { DuplicateId, discover, eventKey, normaliseKey, Registry } from "../../src/core/registry.ts";

const pane = (id: string) => ({ id, title: id, mount: async () => ({ dispose() {} }) });

describe("plugin registry", () => {
  it("duplicate ids fail", () => {
    const reg = new Registry();
    reg.add({
      id: "a",
      panes: [pane("p1")],
      commands: [{ id: "a.run", title: "Run", run: () => {} }],
      keymap: [{ key: "Ctrl+K", command: "a.run" }],
    });
    // The same plugin id.
    expect(() => reg.add({ id: "a" })).toThrow(DuplicateId);
    // A pane id another plugin has.
    expect(() => reg.add({ id: "b", panes: [pane("p1")] })).toThrow(/duplicate pane id "p1" in plugins a and b/);
    // A command id, a key (in any spelling), a band, a layer.
    expect(() => reg.add({ id: "c", commands: [{ id: "a.run", title: "x", run: () => {} }] })).toThrow(DuplicateId);
    expect(() => reg.add({ id: "d", keymap: [{ key: "ctrl+k", command: "x" }] })).toThrow(DuplicateId);
    // Two of one kind inside one plugin.
    expect(() =>
      reg.add({
        id: "e",
        bands: [
          { id: "b1", height: 0, draw() {} },
          { id: "b1", height: 0, draw() {} },
        ],
      }),
    ).toThrow(DuplicateId);
    // A URL parameter the core owns, or one of its aliases.
    expect(() => reg.add({ id: "f", urlParams: [{ name: "sel" }] })).toThrow(DuplicateId);
    expect(() => reg.add({ id: "g", urlParams: [{ name: "band", aliases: ["timeline"] }] })).toThrow(DuplicateId);
    // A failed add leaves nothing behind.
    expect([...reg.plugins.keys()]).toEqual(["a"]);
    expect(reg.panes.size).toBe(1);
    expect(reg.bands.size).toBe(0);
    // Removing a plugin frees its ids.
    reg.remove("a");
    reg.add({ id: "b", panes: [pane("p1")] });
    expect(reg.panes.get("p1")?.plugin).toBe("b");
  });

  it("discovers every plugin folder with unique ids", () => {
    const reg = discover();
    expect([...reg.plugins.keys()].sort()).toEqual([
      "inspector",
      "jobs",
      "legacy",
      "line-sheet",
      "map",
      "palette",
      "review",
      "sources",
    ]);
    for (const id of ["map", "line-sheet", "inspector", "jobs", "review", "legacy", "sources"])
      expect(reg.pane(id)).toBeDefined();
    expect(reg.layers.has("sections")).toBe(true);
    expect(reg.bandList().map((b) => b.id)).toEqual([
      "axes",
      "water",
      "ground",
      "ground-works",
      "context",
      "crossings",
      "locks",
      "over-grade",
      "outlines",
      "station-structure",
      "station-access",
      "roads",
      "rail",
      "grades",
      "curve-grade",
      "drawn-ground",
      "pvi",
      "platforms",
      "crossing-ticks",
      "station-flags",
      "issues",
      "paint-preview",
      "frame",
      "structure-strip",
      "runtime",
      "chainage",
      "chronology-strip",
      "overview",
    ]);
    expect(reg.keymap.get("ctrl+k")?.def.command).toBe("palette.open");
  });

  it("builds from glob modules in path order and refuses a module without a plugin", () => {
    // Section 8's activate returns Disposable | void: an arrow that only calls a void method is a valid plugin.
    const quiet: Plugin = { id: "quiet", activate: (h) => h.toast("started") };
    expect(quiet.activate).toBeTypeOf("function");
    const a: Plugin = { id: "a" };
    const b: Plugin = { id: "b" };
    const reg = Registry.fromModules({
      "../plugins/b/index.ts": { default: b },
      "../plugins/a/index.ts": { plugin: a },
    });
    expect([...reg.plugins.keys()]).toEqual(["a", "b"]);
    expect(() => Registry.fromModules({ "../plugins/x/index.ts": {} })).toThrow(/exports no Plugin/);
    expect(() =>
      Registry.fromModules({
        "../plugins/a/index.ts": { default: { id: "dup" } },
        "../plugins/b/index.ts": { default: { id: "dup" } },
      }),
    ).toThrow(DuplicateId);
  });

  it("normalises keys", () => {
    expect(normaliseKey("Shift+Ctrl+Z")).toBe("ctrl+shift+z");
    expect(normaliseKey("Cmd+K")).toBe("ctrl+k");
    expect(eventKey({ ctrlKey: false, metaKey: true, altKey: false, shiftKey: false, key: "K" } as KeyboardEvent)).toBe(
      "ctrl+k",
    );
  });
});
