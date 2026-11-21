// The line sheet: one section's profile as canvas bands, with a table for PVI and station levels (see pane.ts).

import type { Plugin } from "../../core/plugin.ts";
import { isRecordRef } from "../../core/plugin.ts";
import { BANDS } from "./bands.ts";

const plugin: Plugin = {
  id: "line-sheet",
  panes: [
    {
      id: "line-sheet",
      title: "Line sheet",
      accepts: (sel) => isRecordRef(sel) && (sel.kind === "profile" || sel.kind === "section"),
      async mount(el, ctx) {
        const { mountSheet } = await import("./pane.ts");
        return mountSheet(el, ctx);
      },
    },
  ],
  bands: BANDS,
  commands: [{ id: "line-sheet.pane", title: "Show the line sheet", run: (host) => host.openPane("line-sheet") }],
};

export default plugin;
