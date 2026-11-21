// The app's entry: find the plugins, build the host, bind the URL, render the shell, start the plugins.

import "dockview-react/dist/styles/dockview.css";
import "./shell/shell.css";
import { createRoot } from "react-dom/client";
import { AppHost } from "./core/host.ts";
import type { Plugin } from "./core/plugin.ts";
import { discover, eventKey } from "./core/registry.ts";
import { bindUrl } from "./core/store.ts";
import { App } from "./shell/App.tsx";
import { corePlugin, TEXT_KEYS } from "./shell/core_plugin.ts";

const registry = discover();
const host = new AppHost({ registry });
registry.add(corePlugin(host));
bindUrl(host.store, window, () => [...registry.urlParams.values()].map((e) => e.def));

// Keys go through the registry's keymap to commands.
window.addEventListener("keydown", (e) => {
  const key = eventKey(e);
  const binding = registry.keymap.get(key)?.def;
  if (!binding) return;
  const t = e.target as HTMLElement | null;
  const typing = !!t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));
  if (typing && TEXT_KEYS.has(key)) return;
  e.preventDefault();
  void host.runCommand(binding.command);
});

// Browser errors reach the hub's log through /client-log (section 9, Logging).
let logged = 0;
const report = (kind: string, message: string, stack?: string) => {
  if (logged++ > 50) return;
  void host.api.clientLog({ level: "error", kind, msg: message, stack, url: location.href, client: host.api.clientId });
};
window.addEventListener("error", (e) => report("error", e.message, (e.error as Error | undefined)?.stack));
window.addEventListener("unhandledrejection", (e) =>
  report("unhandledrejection", String((e.reason as Error)?.message ?? e.reason), (e.reason as Error)?.stack),
);

// For tests and the console: the host, and a way to add a plugin at run time (the e2e fixture plugin).
(window as unknown as { __cr: unknown }).__cr = {
  host,
  registry,
  addPlugin(p: Plugin) {
    registry.add(p);
    const d = p.activate?.(host);
    return d;
  },
};

const root = document.getElementById("root");
if (root) createRoot(root).render(<App host={host} />);
host.activate();
void host.meta().catch(() => host.status({ id: "core.meta", text: "hub: not reachable", level: "error", order: 1 }));
