// The SSE client (section 5, Events): one connection to /events, read with fetch so the Last-Event-ID header can
// be sent on every connect (EventSource sends it only on its own reconnects and cannot be told a starting id).
//
// - Durable events (record, changeset) carry their seq as the SSE id. The client remembers the newest, reconnects
//   with Last-Event-ID, and drops a replayed event it has already passed on, so each reaches subscribers once.
// - hello is the first message of every connection. A new epoch (server restart or database restore) means the
//   client's cursor is meaningless: it raises resync {reason: "epoch"} and follows from the hello's seq. A resync
//   the server sends itself (pruned, overflow) is passed on; a second resync on one connection with nothing durable
//   between is folded into the first.
// - Every open after the first is marked reconnected, so ephemeral state (jobs, results) is re-read.
// - engine {engine_build} arrives when the server's engine pool answers after the hello (which then said null); the
//   status takes the build.
// - Reconnects back off from minDelayMs to maxDelayMs with jitter, and reset after a hello. When the response has no
//   readable body the client polls /events/poll?since= instead.

import { type SseMessage, SseParser } from "./sse.ts";
import { DURABLE_EVENTS, type EngineEvent, type HelloEvent, type HubEvent, type ResyncEvent } from "./types.ts";

export type FeedState = "idle" | "connecting" | "open" | "closed";

export interface FeedStatus {
  type: "status";
  state: FeedState;
  reconnected: boolean;
  epoch: string | null;
  seq: number | null;
  engine_build: string | null;
  error?: string;
}

export type FeedMessage = FeedStatus | { type: "event"; event: HubEvent };

export interface EventClientOptions {
  /** The SSE URL, "/api/v1/events". */
  url: string;
  /** The polling fallback, "/api/v1/events/poll". */
  pollUrl?: string;
  fetch?: typeof fetch;
  clientId?: string;
  /** Resume after this seq (a tab that knew one). */
  lastEventId?: number | null;
  epoch?: string | null;
  minDelayMs?: number;
  maxDelayMs?: number;
  /** Reconnect when nothing, not even a comment, arrived for this long. */
  idleMs?: number;
  pollMs?: number;
  random?: () => number;
}

export class EventClient {
  private lastSeq: number | null;
  private epoch: string | null;
  private running = false;
  private ctrl: AbortController | null = null;
  private subs = new Set<(m: FeedMessage) => void>();
  private connections = 0;
  private failures = 0;
  private resyncedThisConnection = false;
  private durableSinceResync = false;
  private wake: (() => void) | null = null;
  private helloSeen = false;
  private current: FeedStatus;
  private readonly fetchFn: typeof fetch;

  private readonly o: EventClientOptions;

  constructor(o: EventClientOptions) {
    this.o = o;
    this.lastSeq = o.lastEventId ?? null;
    this.epoch = o.epoch ?? null;
    this.fetchFn = o.fetch ?? ((...a) => globalThis.fetch(...a));
    this.current = {
      type: "status",
      state: "idle",
      reconnected: false,
      epoch: this.epoch,
      seq: this.lastSeq,
      engine_build: null,
    };
  }

  get seq(): number | null {
    return this.lastSeq;
  }

  status(): FeedStatus {
    return this.current;
  }

  subscribe(fn: (m: FeedMessage) => void): () => void {
    this.subs.add(fn);
    return () => this.subs.delete(fn);
  }

  start(): void {
    if (this.running) return;
    this.running = true;
    void this.loop();
  }

  stop(): void {
    this.running = false;
    this.ctrl?.abort();
    this.wake?.();
    this.setStatus({ state: "closed" });
  }

  /** Drop the current connection and reconnect now (used after the page wakes up). */
  reconnect(): void {
    this.failures = 0;
    this.ctrl?.abort();
    this.wake?.();
  }

  private emit(m: FeedMessage): void {
    for (const fn of [...this.subs]) {
      try {
        fn(m);
      } catch (e) {
        console.warn("event subscriber failed", e);
      }
    }
  }

  private setStatus(s: Partial<FeedStatus>): void {
    this.current = { ...this.current, reconnected: false, error: undefined, ...s, type: "status" };
    this.emit(this.current);
  }

  private async loop(): Promise<void> {
    while (this.running) {
      try {
        this.setStatus({ state: "connecting" });
        await this.connectOnce();
      } catch (e) {
        if (!this.running) break;
        this.setStatus({ state: "closed", error: String((e as Error)?.message ?? e) });
      }
      if (!this.running) break;
      if (!this.helloSeen) this.failures++;
      if (this.current.state !== "closed") this.setStatus({ state: "closed" });
      await this.sleep(this.delay());
    }
  }

  private delay(): number {
    const min = this.o.minDelayMs ?? 250;
    const max = this.o.maxDelayMs ?? 10_000;
    const base = Math.min(max, min * 2 ** Math.min(this.failures, 16));
    const jitter = 0.8 + 0.4 * (this.o.random ?? Math.random)();
    return Math.round(base * jitter);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => {
      const t = setTimeout(done, ms);
      function done() {
        clearTimeout(t);
        resolve();
      }
      this.wake = () => {
        this.wake = null;
        done();
      };
    });
  }

  private async connectOnce(): Promise<void> {
    const ctrl = new AbortController();
    this.ctrl = ctrl;
    this.helloSeen = false;
    const headers: Record<string, string> = { Accept: "text/event-stream", "Cache-Control": "no-cache" };
    if (this.o.clientId) headers["X-CR-Client"] = this.o.clientId;
    if (this.lastSeq !== null) headers["Last-Event-ID"] = String(this.lastSeq);
    const res = await this.fetchFn(this.o.url, { headers, signal: ctrl.signal, cache: "no-store" });
    if (!res.ok) throw new Error(`events: HTTP ${res.status}`);
    if (!res.body) {
      await this.pollLoop(ctrl.signal);
      return;
    }
    const parser = new SseParser();
    const decoder = new TextDecoder();
    const reader = res.body.getReader();
    let idle: ReturnType<typeof setTimeout> | null = null;
    const arm = () => {
      if (idle) clearTimeout(idle);
      idle = setTimeout(() => ctrl.abort(), this.o.idleMs ?? 60_000);
    };
    arm();
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        arm();
        for (const msg of parser.push(decoder.decode(value, { stream: true }))) this.handle(msg);
      }
    } catch (e) {
      if (!ctrl.signal.aborted) throw e;
    } finally {
      if (idle) clearTimeout(idle);
      parser.end();
      try {
        reader.releaseLock();
      } catch {
        /* already released */
      }
    }
  }

  private async pollLoop(signal: AbortSignal): Promise<void> {
    const url = this.o.pollUrl ?? this.o.url.replace(/\/events$/, "/events/poll");
    while (this.running && !signal.aborted) {
      const since = this.lastSeq ?? 0;
      const res = await this.fetchFn(`${url}?since=${since}`, { signal, headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error(`events/poll: HTTP ${res.status}`);
      const body = (await res.json()) as unknown;
      const o = (Array.isArray(body) ? { events: body } : body) as { events?: unknown[]; epoch?: string; seq?: number };
      // The first answer opens the feed; a new epoch later (the server restarted while polling) is a hello too, so
      // it raises the epoch resync as the stream does.
      if (o.epoch !== undefined && (this.current.state !== "open" || o.epoch !== this.epoch)) {
        this.handle({
          id: null,
          event: "hello",
          data: JSON.stringify({ epoch: o.epoch, seq: o.seq ?? since, engine_build: null }),
        });
      }
      for (const ev of o.events ?? []) {
        const e = ev as { seq?: number; type?: string; data?: unknown };
        this.handle({
          id: e.seq === undefined ? null : String(e.seq),
          event: e.type ?? "message",
          data: JSON.stringify(e.data ?? {}),
        });
      }
      await this.sleep(this.o.pollMs ?? 2000);
    }
  }

  /** One SSE message (public for the relay tests and the poll path). */
  handle(msg: SseMessage): void {
    let data: unknown;
    try {
      data = JSON.parse(msg.data);
    } catch {
      return;
    }
    const type = msg.event;
    const idSeq = msg.id !== null && /^\d+$/.test(msg.id) ? Number(msg.id) : null;
    if (type === "hello") {
      const h = data as HelloEvent;
      const before = this.epoch;
      const reconnected = this.connections > 0;
      this.connections++;
      this.failures = 0;
      this.helloSeen = true;
      this.resyncedThisConnection = false;
      this.durableSinceResync = false;
      this.epoch = h.epoch;
      this.setStatus({ state: "open", reconnected, epoch: h.epoch, seq: h.seq, engine_build: h.engine_build ?? null });
      this.emit({ type: "event", event: { type: "hello", seq: h.seq, data: h } });
      if (before !== null && before !== h.epoch) this.resync({ reason: "epoch", seq: h.seq });
      else if (this.lastSeq === null) this.lastSeq = h.seq;
      return;
    }
    if (type === "resync") {
      const r = data as ResyncEvent;
      if (this.resyncedThisConnection && !this.durableSinceResync) {
        this.lastSeq = r.seq;
        return;
      }
      this.resync(r);
      return;
    }
    if (DURABLE_EVENTS.has(type)) {
      const seq = idSeq ?? (data as { seq?: number }).seq ?? null;
      if (seq !== null && this.lastSeq !== null && seq <= this.lastSeq) return;
      if (seq !== null) this.lastSeq = seq;
      this.durableSinceResync = true;
      this.emit({ type: "event", event: { type, seq, data } as HubEvent });
      return;
    }
    if (type === "engine") {
      // The pool answered after this connection's hello said engine_build null: the status takes the build, so the
      // next local solve names the build the server's sidecars run.
      const e = data as EngineEvent;
      this.setStatus({ engine_build: e.engine_build ?? null });
      this.emit({ type: "event", event: { type: "engine", seq: null, data: e } });
      return;
    }
    if (type === "job" || type === "result" || type === "tier") {
      this.emit({ type: "event", event: { type, seq: null, data } as HubEvent });
    }
  }

  private resync(r: ResyncEvent): void {
    this.resyncedThisConnection = true;
    this.durableSinceResync = false;
    this.lastSeq = r.seq;
    this.emit({ type: "event", event: { type: "resync", seq: r.seq, data: r } });
  }
}
