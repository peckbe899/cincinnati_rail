// The live hub's actions, shared by the Sources plugin and its pane: read /live, Undo this import, Apply, Check now,
// Pause and Resume live. Each updates the shared board, so the chip and the pane follow at once.

import { liveBoard } from "../../core/live.ts";
import type { Host } from "../../core/plugin.ts";

export async function reread(host: Host): Promise<void> {
  try {
    liveBoard.reset(await host.api.live());
  } catch {
    /* an older hub without /live, or a hub that is down: the events status says which */
  }
}

export async function act(host: Host, source: string, action: "undo" | "apply" | "check"): Promise<void> {
  try {
    const st = await host.api.liveSource(source, action);
    liveBoard.source(st);
  } catch (e) {
    host.problem(e);
  }
}

export async function pause(host: Host, on: boolean): Promise<void> {
  try {
    liveBoard.setSummary(await host.api.livePause(on));
    host.toast({
      text: on
        ? "Live is paused: changes to the sources wait until you resume."
        : "Live resumed: what changed meanwhile is taken in now.",
      level: "info",
      ttl: 4000,
    });
  } catch (e) {
    host.problem(e);
  }
}
