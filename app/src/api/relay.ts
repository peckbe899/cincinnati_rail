// The SharedWorker's relay: one EventClient for every tab of the hub (the old hub's 29 October fix for the
// six-connection limit, kept). A tab's port sends {type: "start"} with the URLs, then {type: "bye"} on pagehide.
// A port that joins late gets the latest status at once. The stream stops when the last tab leaves.

import { EventClient, type EventClientOptions, type FeedMessage, type FeedStatus } from "./stream.ts";

export interface PortLike {
  postMessage(m: unknown): void;
  onmessage: ((e: MessageEvent) => void) | null;
  start?(): void;
}

export type TabMessage = { type: "start"; options: EventClientOptions } | { type: "bye" } | { type: "reconnect" };

export class Relay {
  readonly ports = new Set<PortLike>();
  private client: EventClient | null = null;
  private last: FeedStatus | null = null;

  private readonly make: (o: EventClientOptions) => EventClient;

  constructor(make: (o: EventClientOptions) => EventClient = (o) => new EventClient(o)) {
    this.make = make;
  }

  connect(port: PortLike): void {
    this.ports.add(port);
    port.onmessage = (e: MessageEvent) => this.receive(port, e.data as TabMessage);
    port.start?.();
    if (this.last) port.postMessage(this.last);
  }

  receive(port: PortLike, m: TabMessage): void {
    if (!m || typeof m !== "object") return;
    if (m.type === "start") {
      // A tab that said bye (pagehide) and came back from the back/forward cache starts again on the same port.
      this.ports.add(port);
      if (!this.client) {
        this.client = this.make(m.options);
        this.client.subscribe((msg) => this.broadcast(msg));
        this.client.start();
      } else if (this.last) {
        port.postMessage(this.last);
      }
    } else if (m.type === "bye") {
      this.ports.delete(port);
      if (this.ports.size === 0 && this.client) {
        this.client.stop();
        this.client = null;
        this.last = null;
      }
    } else if (m.type === "reconnect") {
      this.client?.reconnect();
    }
  }

  broadcast(msg: FeedMessage): void {
    if (msg.type === "status") this.last = msg;
    for (const p of [...this.ports]) {
      try {
        p.postMessage(msg);
      } catch {
        this.ports.delete(p);
      }
    }
  }
}
