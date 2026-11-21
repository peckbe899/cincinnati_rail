// Records cached by TanStack query-core under (kind, id, view) (section 8), and patched by events.
//
// A record event (kind, id, layer, version) invalidates every cached view of that record unless the cached revision
// is already on that layer at that version or newer: the echo of the tab's own write, or a replay. Lists and
// GeoJSON of the kind are invalidated too; they come back cheaply because the transport sends If-None-Match.
// A bulk changeset (summary: true) invalidates every query of its kinds; a resync invalidates everything.

import { QueryClient, type QueryKey, QueryObserver, type QueryObserverResult } from "@tanstack/query-core";
import type { FeatureCollection } from "geojson";
import type { Api, ListFilters } from "../api/client.ts";
import type { HubEvent, Rec } from "../api/types.ts";
import { type View, viewToken } from "./view.ts";

export type RecordResult = QueryObserverResult<Rec, Error>;

export class RecordCache {
  readonly qc: QueryClient;
  private readonly api: Api;

  constructor(api: Api) {
    this.api = api;
    this.qc = new QueryClient({
      defaultOptions: {
        queries: { staleTime: Number.POSITIVE_INFINITY, gcTime: 5 * 60_000, retry: false, refetchOnWindowFocus: false },
      },
    });
  }

  static key(kind: string, id: string, view: View): QueryKey {
    return ["rec", kind, id, viewToken(view)];
  }

  get(kind: string, id: string, view: View): Promise<Rec> {
    return this.qc.fetchQuery({
      queryKey: RecordCache.key(kind, id, view),
      queryFn: () => this.api.getRecord(kind, id, view),
    });
  }

  peek(kind: string, id: string, view: View): Rec | undefined {
    return this.qc.getQueryData<Rec>(RecordCache.key(kind, id, view));
  }

  /** Put a record the server just returned (a write's response) into the cache for the view it was written in. */
  set(rec: Rec, view: View): void {
    this.qc.setQueryData(RecordCache.key(rec.kind, rec.id, view), rec);
  }

  /** Follow one record: fn runs now with what is cached and again on every change. */
  watch(kind: string, id: string, view: View, fn: (r: RecordResult) => void): () => void {
    const obs = new QueryObserver<Rec, Error>(this.qc, {
      queryKey: RecordCache.key(kind, id, view),
      queryFn: () => this.api.getRecord(kind, id, view),
    });
    const unsub = obs.subscribe(fn);
    // subscribe() reports changes only; a record already cached is reported now.
    const now = obs.getCurrentResult();
    if (now.data !== undefined || now.error) fn(now);
    return unsub;
  }

  list(kind: string, view: View, f: ListFilters = {}): Promise<{ items: Rec[]; next: string | null }> {
    return this.qc.fetchQuery({
      queryKey: ["list", kind, viewToken(view), f],
      queryFn: () => this.api.list(kind, view, f),
    });
  }

  geojson(kind: string, view: View, f: ListFilters = {}): Promise<FeatureCollection> {
    return this.qc.fetchQuery({
      queryKey: ["geojson", kind, viewToken(view), f],
      queryFn: () => this.api.geojson(kind, view, f),
    });
  }

  /** Patch the cache for one hub event. Returns how many queries it invalidated (for tests and the status bar). */
  apply(ev: HubEvent): number {
    const qc = this.qc;
    let n = 0;
    const invalidate = (pred: (key: QueryKey, data: unknown) => boolean) => {
      for (const q of qc.getQueryCache().getAll()) {
        if (pred(q.queryKey, q.state.data)) {
          n++;
          void qc.invalidateQueries({ queryKey: q.queryKey, exact: true });
        }
      }
    };
    switch (ev.type) {
      case "record": {
        const e = ev.data;
        invalidate((k, data) => {
          if (k[0] === "rec" && k[1] === e.kind && k[2] === e.id) {
            const d = data as Rec | undefined;
            return !(d && d.layer === e.layer && d.version >= e.version);
          }
          return (k[0] === "list" || k[0] === "geojson") && k[1] === e.kind;
        });
        break;
      }
      case "changeset": {
        if (!ev.data.summary) break;
        const kinds = new Set(Object.keys(ev.data.kinds ?? {}));
        invalidate((k) => typeof k[1] === "string" && kinds.has(k[1]));
        break;
      }
      case "resync":
        this.api.forget();
        invalidate(() => true);
        break;
      default:
        break;
    }
    return n;
  }
}
