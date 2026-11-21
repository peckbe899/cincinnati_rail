// The inspector: a form for any selected record, from its kind's JSON Schema (see form.ts).

import type { Plugin } from "../../core/plugin.ts";
import { isRecordRef } from "../../core/plugin.ts";

const plugin: Plugin = {
  id: "inspector",
  panes: [
    {
      id: "inspector",
      title: "Inspector",
      accepts: (sel) => isRecordRef(sel),
      async mount(el, ctx) {
        const { mountInspector } = await import("./pane.ts");
        return mountInspector(el, ctx);
      },
    },
  ],
  commands: [{ id: "inspector.pane", title: "Show the inspector", run: (host) => host.openPane("inspector") }],
};

export default plugin;
