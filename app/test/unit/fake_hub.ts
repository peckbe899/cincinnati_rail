// A fake hub for the unit tests: MSW handlers for the section 5 routes the app uses, over an in-memory store that
// keeps the server's rules (If-Match with 428 and 412, ETags and 304, JSON Patch, changesets and revert with 409,
// SSE with ids, Last-Event-ID replay, hello and resync). It stands in for WP2 until the real server lands.

import { HttpResponse, http } from "msw";
import type { ChangesetEvent, JsonPatch, Rec, RecordEvent } from "../../src/api/types.ts";
import { applyPatch } from "../../src/core/jsonpatch.ts";

export const BASE = "http://hub.test/api/v1";

interface Logged {
  method: string;
  url: string;
  headers: Record<string, string>;
  status: number;
}

interface CsOp {
  kind: string;
  id: string;
  layer: string;
  before: Rec | null;
  after: Rec;
}

type Event = { seq: number; type: "record" | "changeset"; data: RecordEvent | ChangesetEvent };

const problem = (status: number, code: string, detail: string, extra: Record<string, unknown> = {}) =>
  HttpResponse.json(
    {
      type: `https://cincinnati-rail.invalid/problems/${code}`,
      title: code,
      status,
      detail,
      code,
      request_id: `req-${status}`,
      ...extra,
    },
    { status, headers: { "Content-Type": "application/problem+json" } },
  );

export class FakeHub {
  /** Latest revision by `${layer}|${kind}|${id}`. */
  readonly recs = new Map<string, Rec>();
  readonly changesets = new Map<string, CsOp[]>();
  readonly events: Event[] = [];
  readonly log: Logged[] = [];
  readonly kinds: Record<string, unknown> = {};
  epoch = "epoch-1";
  /** Events at or below this seq are pruned: a Last-Event-ID below it gets a resync. */
  pruned = 0;
  private seq = 0;
  private cs = 0;
  private streams = new Set<ReadableStreamDefaultController<Uint8Array>>();
  private enc = new TextEncoder();

  seed(r: Partial<Rec> & { kind: string; id: string; data: Rec["data"] }, layer = "main"): Rec {
    const rec: Rec = {
      kv: 1,
      version: 1,
      hash: "h",
      deleted: false,
      origin: "seed",
      source: null,
      by: "seed",
      changeset: "cs-seed",
      created: "2026-11-21T00:00:00Z",
      updated: "2026-11-21T00:00:00Z",
      geom: null,
      ...r,
      layer,
    };
    this.recs.set(`${layer}|${rec.kind}|${rec.id}`, rec);
    return rec;
  }

  /** The revision a view of layer resolves to: the layer's own, else main's. */
  resolve(layer: string, kind: string, id: string): Rec | undefined {
    return this.recs.get(`${layer}|${kind}|${id}`) ?? this.recs.get(`main|${kind}|${id}`);
  }

  /** Write a new revision as `by` (another client's edit, or the server's own). */
  write(
    layer: string,
    kind: string,
    id: string,
    data: Rec["data"],
    by = "other",
    client: string | null = "tab-other",
    csId?: string,
  ): Rec {
    const cur = this.resolve(layer, kind, id);
    const next: Rec = {
      ...(cur as Rec),
      kind,
      id,
      layer,
      data,
      version: (cur?.version ?? 0) + 1,
      by,
      changeset: csId ?? `cs-${++this.cs}`,
      updated: new Date(0).toISOString(),
    };
    this.recs.set(`${layer}|${kind}|${id}`, next);
    const ops = this.changesets.get(next.changeset) ?? [];
    ops.push({ kind, id, layer, before: cur ?? null, after: next });
    this.changesets.set(next.changeset, ops);
    this.emit("record", {
      op: "patch",
      kind,
      id,
      layer,
      version: next.version,
      hash: "h",
      by,
      client,
      changeset: next.changeset,
      fields: ["data"],
      bbox: null,
    });
    return next;
  }

  emit(type: "record" | "changeset", payload: Omit<RecordEvent, "seq"> | Omit<ChangesetEvent, "seq">): number {
    const seq = ++this.seq;
    const ev = { seq, type, data: { ...payload, seq } } as Event;
    this.events.push(ev);
    for (const c of this.streams) this.send(c, `id: ${seq}\nevent: ${type}\ndata: ${JSON.stringify(ev.data)}\n\n`);
    return seq;
  }

  /** Send any SSE text to every open stream (ephemeral job and result events, comments). */
  broadcast(text: string): void {
    for (const c of this.streams) this.send(c, text);
  }

  /** Drop every open stream (a network blip). */
  closeStreams(): void {
    for (const c of this.streams) {
      try {
        c.close();
      } catch {
        /* already closed */
      }
    }
    this.streams.clear();
  }

  /** A server restart: a new epoch, and every stream dropped. */
  restart(): void {
    this.epoch = `epoch-${Number(this.epoch.split("-")[1]) + 1}`;
    this.closeStreams();
  }

  get openStreams(): number {
    return this.streams.size;
  }

  private send(c: ReadableStreamDefaultController<Uint8Array>, text: string): void {
    try {
      c.enqueue(this.enc.encode(text));
    } catch {
      this.streams.delete(c);
    }
  }

  private record(req: Request, status: number) {
    const headers: Record<string, string> = {};
    req.headers.forEach((v, k) => {
      headers[k] = v;
    });
    this.log.push({ method: req.method, url: req.url, headers, status });
  }

  handlers() {
    const url = (p: string) => `${BASE}${p}`;
    const etag = (r: Rec) => `"${r.layer}:${r.version}"`;
    return [
      http.get(url("/meta"), ({ request }) => {
        this.record(request, 200);
        return HttpResponse.json({
          kinds: this.kinds,
          layers: [{ slug: "main", tier: "main" }],
          epoch: this.epoch,
          old_hub: "http://127.0.0.1:8765",
        });
      }),
      http.get(url("/k/:kind/:id"), ({ request, params }) => {
        const layer = new URL(request.url).searchParams.get("layer") ?? "main";
        const r = this.resolve(layer, String(params.kind), String(params.id));
        if (!r || r.deleted) {
          this.record(request, 404);
          return problem(404, "not_found", "no such record");
        }
        if (request.headers.get("if-none-match") === etag(r)) {
          this.record(request, 304);
          return new HttpResponse(null, { status: 304, headers: { ETag: etag(r) } });
        }
        this.record(request, 200);
        return HttpResponse.json(r, { headers: { ETag: etag(r) } });
      }),
      http.patch(url("/k/:kind/:id"), async ({ request, params }) => {
        const layer = new URL(request.url).searchParams.get("layer") ?? "main";
        const kind = String(params.kind);
        const id = String(params.id);
        const ifMatch = request.headers.get("if-match");
        if (!request.headers.get("x-cr-client")) {
          this.record(request, 403);
          return problem(403, "forbidden", "X-CR-Client is required");
        }
        if (!(request.headers.get("content-type") ?? "").includes("application/json-patch+json")) {
          this.record(request, 415);
          return problem(415, "unsupported_media_type", "JSON Patch only");
        }
        const cur = this.resolve(layer, kind, id);
        if (!cur) {
          this.record(request, 404);
          return problem(404, "not_found", "no such record");
        }
        if (!ifMatch) {
          this.record(request, 428);
          return problem(428, "precondition_required", "If-Match required");
        }
        if (ifMatch !== etag(cur)) {
          this.record(request, 412);
          return problem(412, "precondition_failed", "Stale If-Match", {
            current: cur,
            by: cur.by,
            diff: [],
            stale: [],
          });
        }
        const ops = (await request.json()) as JsonPatch;
        const body = applyPatch({ data: cur.data, geom: cur.geom }, ops);
        const next = this.write(layer, kind, id, body.data, "ben", request.headers.get("x-cr-client"));
        this.record(request, 200);
        return HttpResponse.json(next, { headers: { ETag: etag(next) } });
      }),
      http.post(url("/changesets/:id/revert"), ({ request, params }) => {
        const ops = this.changesets.get(String(params.id));
        if (!ops) {
          this.record(request, 404);
          return problem(404, "not_found", "no such changeset");
        }
        for (const o of ops) {
          const cur = this.recs.get(`${o.layer}|${o.kind}|${o.id}`);
          if (!cur || cur.version !== o.after.version) {
            this.record(request, 409);
            return problem(409, "conflict_revert", "A later edit stands in the way.", {
              reason: "revert",
              conflicts: [{ kind: o.kind, id: o.id }],
            });
          }
        }
        const csId = `cs-${++this.cs}`;
        const records = ops.map((o) =>
          this.write(
            o.layer,
            o.kind,
            o.id,
            (o.before ?? o.after).data,
            "ben",
            request.headers.get("x-cr-client"),
            csId,
          ),
        );
        this.record(request, 200);
        return HttpResponse.json({ changeset: csId, records, seq: this.seq });
      }),
      http.get(url("/legacy/:lkind/:key"), ({ request, params }) => {
        this.record(request, 200);
        if (params.lkind === "route" && params.key === "Line_6")
          return HttpResponse.json({ kind: "section", id: "SEC6" });
        return problem(404, "not_found", "no legacy key");
      }),
      http.get(url("/events"), ({ request }) => {
        this.record(request, 200);
        const last = request.headers.get("last-event-id");
        let ctrl!: ReadableStreamDefaultController<Uint8Array>;
        const stream = new ReadableStream<Uint8Array>({
          start: (c) => {
            ctrl = c;
          },
          cancel: () => {
            this.streams.delete(ctrl);
          },
        });
        this.streams.add(ctrl);
        this.send(
          ctrl,
          `: hello\nevent: hello\ndata: ${JSON.stringify({ epoch: this.epoch, seq: this.seq, engine_build: null })}\n\n`,
        );
        if (last !== null) {
          const from = Number(last);
          if (from < this.pruned) {
            this.send(ctrl, `event: resync\ndata: ${JSON.stringify({ reason: "pruned", seq: this.seq })}\n\n`);
          } else {
            // Replays from the event the client already has, so the client's de-duplication is exercised too.
            for (const e of this.events.filter((x) => x.seq >= from)) {
              this.send(ctrl, `id: ${e.seq}\nevent: ${e.type}\ndata: ${JSON.stringify(e.data)}\n\n`);
            }
          }
        }
        return new HttpResponse(stream, {
          headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
        });
      }),
    ];
  }
}
