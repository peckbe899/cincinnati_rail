// The SharedWorker that holds the one SSE connection for every tab (section 8, Events). The work is in relay.ts
// and stream.ts, so it can be tested without a worker.

import { Relay } from "./relay.ts";

const relay = new Relay();
const scope = globalThis as unknown as { onconnect: ((e: MessageEvent) => void) | null };

scope.onconnect = (e: MessageEvent) => {
  const port = e.ports[0];
  if (port) relay.connect(port);
};
