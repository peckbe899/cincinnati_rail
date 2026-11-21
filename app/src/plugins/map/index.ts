// The region map: MapLibre with a fully local style (9.30), drawing every registered map layer.
// MapLibre itself loads only when the pane opens (see pane.ts), so it stays out of the first chunk.

import type { Plugin } from "../../core/plugin.ts";
import { bindHost, LAYERS } from "./layers.ts";

const plugin: Plugin = {
  id: "map",
  layers: LAYERS,
  panes: [
    {
      id: "map",
      title: "Map",
      async mount(el, ctx) {
        const { mountMap } = await import("./pane.ts");
        return mountMap(el, ctx);
      },
    },
  ],
  activate(host) {
    bindHost(host);
    return { dispose: () => bindHost(null) };
  },
  commands: [{ id: "map.pane", title: "Show the map", run: (host) => host.openPane("map") }],
};

export default plugin;
