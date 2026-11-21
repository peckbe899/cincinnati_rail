// The tab's end of the event stream. In a browser with SharedWorker every tab shares one connection through
// events.worker.ts; elsewhere (and in tests) the tab runs its own EventClient. Either way subscribers get the same
// FeedMessages: status changes and hub events.

import { EventClient, type EventClientOptions, type FeedMessage, type FeedStatus } from "./stream.ts";

export type { FeedMessage, FeedStatus } from "./stream.ts";

export interface EventFeed {
  readonly shared: boolean;
  subscribe(fn: (m: FeedMessage) => void): () => void;
  status(): FeedStatus;
  /** Drop and reopen the connection now. */
  reconnect(): void;
  close(): void;
}

const IDLE: FeedStatus = {
  type: "status",
  state: "idle",
  reconnected: false,
  epoch: null,
  seq: null,
  engine_build: null,
};

export interface ConnectOptions extends EventClientOptions {
  /** Use a SharedWorker when the browser has one (default true). */
  shared?: boolean;
  /** For tests: the SharedWorker constructor to use. */
  SharedWorkerImpl?: typeof SharedWorker;
}

export function connectEvents(o: ConnectOptions): EventFeed {
  const SW = o.SharedWorkerImpl ?? (globalThis as { SharedWorker?: typeof SharedWorker }).SharedWorker;
  if (o.shared !== false && SW) {
    try {
      return sharedFeed(o, SW);
    } catch (e) {
      console.warn("SharedWorker unavailable, using a connection per tab", e);
    }
  }
  return localFeed(o);
}

function localFeed(o: EventClientOptions): EventFeed {
  const client = new EventClient(o);
  client.start();
  return {
    shared: false,
    subscribe: (fn) => client.subscribe(fn),
    status: () => client.status(),
    reconnect: () => client.reconnect(),
    close: () => client.stop(),
  };
}

function sharedFeed(o: ConnectOptions, SW: typeof SharedWorker): EventFeed {
  // Written out as new SharedWorker(new URL(...)) so Vite bundles the worker; a test passes its own constructor.
  const worker =
    SW === globalThis.SharedWorker
      ? new SharedWorker(new URL("./events.worker.ts", import.meta.url), { type: "module", name: "cr-events" })
      : new SW("events.worker.js", { type: "module", name: "cr-events" });
  const port = worker.port;
  const subs = new Set<(m: FeedMessage) => void>();
  let current = IDLE;
  port.onmessage = (e: MessageEvent) => {
    const m = e.data as FeedMessage;
    if (m?.type === "status") current = m;
    for (const fn of [...subs]) fn(m);
  };
  port.start();
  const { SharedWorkerImpl: _sw, shared: _s, fetch: _f, ...options } = o;
  const start = () => port.postMessage({ type: "start", options });
  start();
  const bye = () => port.postMessage({ type: "bye" });
  // pagehide also fires when the page goes into the back/forward cache, and the relay then forgets this tab. A page
  // restored from that cache says start again, or it would get no more events.
  const back = (e: Event) => {
    if ((e as PageTransitionEvent).persisted) start();
  };
  globalThis.addEventListener?.("pagehide", bye);
  globalThis.addEventListener?.("pageshow", back);
  return {
    shared: true,
    subscribe(fn) {
      subs.add(fn);
      return () => subs.delete(fn);
    },
    status: () => current,
    reconnect: () => port.postMessage({ type: "reconnect" }),
    close() {
      globalThis.removeEventListener?.("pagehide", bye);
      globalThis.removeEventListener?.("pageshow", back);
      bye();
      port.close();
    },
  };
}
