// The hand-written transport over /api/v1 (decision 9.21): one fetch wrapper that sends X-CR-Client on every
// request and a JSON content type on every write, sends If-Match where a write needs one, keeps ETags so a repeated
// GET sends If-None-Match and a 304 reuses the body, and turns RFC 9457 problem bodies into ApiError.
// The shapes are in ./types.ts until src/api/gen is generated from region/api/openapi.json.

import type { FeatureCollection } from "geojson";
import { type View, viewQuery } from "../core/view.ts";
import { listOf, normaliseLayers, normaliseList, normaliseMeta } from "./normalise.ts";
import type {
  ChangesetOp,
  Conflict,
  Job,
  JsonPatch,
  LayerMeta,
  Meta,
  Problem,
  Rec,
  ResultArray,
  ResultMeta,
  TierStatus,
  WriteResult,
} from "./types.ts";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly problem: Problem;
  constructor(problem: Problem) {
    super(problem.detail || problem.title || `HTTP ${problem.status}`);
    this.problem = problem;
    this.name = "ApiError";
    this.status = problem.status;
    this.code = problem.code ?? `http_${problem.status}`;
    this.requestId = problem.request_id ?? null;
  }
}

export interface ApiOptions {
  /** "/api/v1" in the browser; an absolute URL in tests. */
  base?: string;
  /** X-CR-Client: this tab's id, so SSE echoes of its own writes can be skipped. */
  clientId?: string;
  fetch?: typeof fetch;
}

export interface SendOptions {
  query?: Record<string, string | number | boolean | null | undefined>;
  json?: unknown;
  contentType?: string;
  ifMatch?: string | null;
  headers?: Record<string, string>;
  /** Keep the ETag and send If-None-Match next time (default for GET). */
  cache?: boolean;
  /** Return the Response body as an ArrayBuffer. */
  binary?: boolean;
  signal?: AbortSignal;
}

export interface Sent<T> {
  status: number;
  data: T;
  etag: string | null;
  headers: Headers;
}

export type ListFilters = Partial<Record<"bbox" | "parent" | "ref" | "ids" | "q" | "fields" | "after", string>> & {
  limit?: number;
};

/** The ETag of a record, as the server writes it: "<layer>:<version>" with the quotes. */
export const etagOf = (r: Pick<Rec, "layer" | "version">): string => `"${r.layer}:${r.version}"`;

export function newClientId(): string {
  const n = globalThis.crypto?.getRandomValues?.(new Uint16Array(1))[0] ?? Math.floor(Math.random() * 65536);
  return `tab-${n.toString(16).padStart(4, "0")}`;
}

export class Api {
  readonly base: string;
  readonly clientId: string;
  private readonly fetchFn: typeof fetch;
  private readonly etags = new Map<string, { etag: string; data: unknown }>();

  constructor(opts: ApiOptions = {}) {
    this.base = (opts.base ?? "/api/v1").replace(/\/$/, "");
    this.clientId = opts.clientId ?? newClientId();
    this.fetchFn = opts.fetch ?? ((...a) => globalThis.fetch(...a));
  }

  url(path: string, query?: SendOptions["query"]): string {
    const q = Object.entries(query ?? {})
      .filter(([, v]) => v !== undefined && v !== null && v !== "")
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      .join("&");
    return `${this.base}${path}${q ? `?${q}` : ""}`;
  }

  async send<T>(method: string, path: string, o: SendOptions = {}): Promise<Sent<T>> {
    const url = this.url(path, o.query);
    const headers: Record<string, string> = { Accept: "application/json", "X-CR-Client": this.clientId, ...o.headers };
    const write = method !== "GET" && method !== "HEAD";
    if (write) headers["Content-Type"] = o.contentType ?? "application/json";
    if (o.ifMatch) headers["If-Match"] = o.ifMatch;
    const useCache = o.cache ?? !write;
    const cached = useCache ? this.etags.get(url) : undefined;
    if (cached) headers["If-None-Match"] = cached.etag;
    let res: Response;
    try {
      res = await this.fetchFn(url, {
        method,
        headers,
        body: write ? JSON.stringify(o.json ?? {}) : undefined,
        signal: o.signal,
      });
    } catch (e) {
      if ((e as Error)?.name === "AbortError") throw e;
      throw new ApiError({ status: 0, code: "network", detail: `The hub did not answer (${String(e)}).` });
    }
    const etag = res.headers.get("ETag");
    if (res.status === 304 && cached)
      return { status: 304, data: cached.data as T, etag: cached.etag, headers: res.headers };
    if (!res.ok) throw new ApiError(await problemOf(res));
    const data = (o.binary ? await res.arrayBuffer() : await bodyOf(res)) as T;
    if (useCache && etag && !o.binary) this.etags.set(url, { etag, data });
    return { status: res.status, data, etag, headers: res.headers };
  }

  async get<T>(path: string, query?: SendOptions["query"]): Promise<T> {
    return (await this.send<T>("GET", path, { query })).data;
  }

  /** Forget the cached ETag of every URL starting with prefix (after a resync). */
  forget(prefix = ""): void {
    for (const k of this.etags.keys()) if (k.startsWith(this.base + prefix)) this.etags.delete(k);
  }

  // ----------------------------------------------------------------------------------------------- meta and records

  async meta(): Promise<Meta> {
    return normaliseMeta(await this.get<unknown>("/meta"));
  }

  health(): Promise<unknown> {
    return this.get("/health");
  }

  async list(kind: string, view: View, f: ListFilters = {}): Promise<{ items: Rec[]; next: string | null }> {
    return normaliseList(await this.get<unknown>(`/k/${kind}`, { ...viewQuery(view), ...f }));
  }

  geojson(kind: string, view: View, f: ListFilters = {}): Promise<FeatureCollection> {
    return this.get(`/k/${kind}`, { ...viewQuery(view), ...f, format: "geojson", crs: "4326" });
  }

  getRecord<D = Record<string, unknown>>(kind: string, id: string, view: View, at?: number): Promise<Rec<D>> {
    return this.get(`/k/${kind}/${encodeURIComponent(id)}`, { ...viewQuery(view), at });
  }

  async create(kind: string, body: Rec["data"] | { data: unknown; geom?: string | null }, view: View): Promise<Rec> {
    const key = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
    const json = "data" in (body as object) ? body : { data: body, geom: null };
    return (
      await this.send<Rec>("POST", `/k/${kind}`, { query: viewQuery(view), json, headers: { "Idempotency-Key": key } })
    ).data;
  }

  async put(
    kind: string,
    id: string,
    body: { data: unknown; geom: string | null },
    view: View,
    ifMatch: string,
  ): Promise<Rec> {
    return (
      await this.send<Rec>("PUT", `/k/${kind}/${encodeURIComponent(id)}`, {
        query: viewQuery(view),
        json: body,
        ifMatch,
      })
    ).data;
  }

  async patch(kind: string, id: string, ops: JsonPatch, view: View, ifMatch: string): Promise<Rec> {
    const path = `/k/${kind}/${encodeURIComponent(id)}`;
    const o = { query: viewQuery(view), json: ops, ifMatch, contentType: "application/json-patch+json" };
    return (await this.send<Rec>("PATCH", path, o)).data;
  }

  async remove(kind: string, id: string, view: View, ifMatch: string): Promise<Rec> {
    return (await this.send<Rec>("DELETE", `/k/${kind}/${encodeURIComponent(id)}`, { query: viewQuery(view), ifMatch }))
      .data;
  }

  history(kind: string, id: string, view: View): Promise<Rec[]> {
    return this.get(`/k/${kind}/${encodeURIComponent(id)}/history`, viewQuery(view));
  }

  async restore(kind: string, id: string, version: number, view: View, ifMatch: string): Promise<Rec> {
    const path = `/k/${kind}/${encodeURIComponent(id)}/restore`;
    return (await this.send<Rec>("POST", path, { query: { ...viewQuery(view), version }, ifMatch })).data;
  }

  /** The record an old key maps to, or null when the legacy index has none. */
  async legacy(lkind: string, key: string): Promise<{ kind: string; id: string } | null> {
    try {
      return await this.get(`/legacy/${encodeURIComponent(lkind)}/${encodeURIComponent(key)}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  }

  // ------------------------------------------------------------------------------------------ changesets and layers

  async changeset(layer: string, message: string, ops: ChangesetOp[]): Promise<WriteResult> {
    return (await this.send<WriteResult>("POST", "/changesets", { json: { layer, message, ops } })).data;
  }

  async revert(changeset: string): Promise<WriteResult> {
    return (await this.send<WriteResult>("POST", `/changesets/${encodeURIComponent(changeset)}/revert`)).data;
  }

  async layers(): Promise<LayerMeta[]> {
    return normaliseLayers(await this.get<unknown>("/layers"));
  }

  async createLayer(slug: string, tier: "scenario" | "proposal", parent = "main", title?: string): Promise<LayerMeta> {
    return (await this.send<LayerMeta>("POST", "/layers", { json: { slug, tier, parent, title: title ?? slug } })).data;
  }

  async conflicts(query: SendOptions["query"] = { state: "open" }): Promise<Conflict[]> {
    return listOf<Conflict>(await this.get<unknown>("/conflicts", query));
  }

  // ------------------------------------------------------------------------------------------------ jobs, results

  async compute(
    type: string,
    scope: string,
    view: string,
    priority = 0,
  ): Promise<{ key: string; state: string; job: string | null }> {
    return (
      await this.send<{ key: string; state: string; job: string | null }>("POST", "/compute", {
        json: { type, scope, view, priority },
      })
    ).data;
  }

  /** The latest result key for a goal, or null. */
  async latestResult(type: string, scope: string, view: string): Promise<string | null> {
    try {
      const r = await this.get<{ key?: string | null } | string | null>("/results", { type, scope, view });
      return typeof r === "string" ? r : (r?.key ?? null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  }

  result(key: string): Promise<ResultMeta> {
    return this.get(`/results/${encodeURIComponent(key)}`);
  }

  async resultArray(key: string, name: string): Promise<ResultArray> {
    const r = await this.send<ArrayBuffer>("GET", `/results/${encodeURIComponent(key)}/a/${encodeURIComponent(name)}`, {
      binary: true,
      cache: false,
    });
    const shape = (r.headers.get("X-Shape") ?? "")
      .split(/[,x ]+/)
      .filter(Boolean)
      .map(Number);
    return { dtype: r.headers.get("X-Dtype") ?? "f8", shape, buffer: r.data };
  }

  async jobs(active = true): Promise<Job[]> {
    return listOf<Job>(await this.get<unknown>("/jobs", active ? { active: 1 } : {}));
  }

  async cancelJob(id: string): Promise<void> {
    await this.send("POST", `/jobs/${encodeURIComponent(id)}/cancel`);
  }

  async tiers(): Promise<TierStatus[]> {
    const r = await this.get<unknown>("/tiers");
    if (r && typeof r === "object" && !Array.isArray(r) && !("items" in r) && !("tiers" in r)) {
      return Object.entries(r as Record<string, unknown>).map(([name, v]) =>
        typeof v === "string"
          ? { name, status: v as TierStatus["status"] }
          : ({ name, ...(v as object) } as TierStatus),
      );
    }
    return listOf<TierStatus>(r, "tiers");
  }

  sectionInput(sectionId: string, view: View): Promise<import("@cr/engine/contract").SectionInput> {
    return this.get(`/x/profiles/sections/${encodeURIComponent(sectionId)}/input`, viewQuery(view));
  }

  /** Best effort: a browser error into the hub's log (never throws). */
  async clientLog(entry: Record<string, unknown>): Promise<void> {
    try {
      await this.send("POST", "/client-log", { json: entry, cache: false });
    } catch {
      /* the log is best effort */
    }
  }
}

// ------------------------------------------------------------------------------------------------------- helpers

async function bodyOf(res: Response): Promise<unknown> {
  if (res.status === 204) return null;
  const text = await res.text();
  if (!text) return null;
  const type = res.headers.get("Content-Type") ?? "";
  if (type.includes("json")) return JSON.parse(text);
  return text;
}

async function problemOf(res: Response): Promise<Problem> {
  let body: unknown = null;
  try {
    body = await bodyOf(res);
  } catch {
    body = null;
  }
  if (body && typeof body === "object" && !Array.isArray(body)) {
    const p = body as Problem;
    return { ...p, status: typeof p.status === "number" ? p.status : res.status };
  }
  return {
    status: res.status,
    code: `http_${res.status}`,
    detail: typeof body === "string" && body ? body.slice(0, 300) : res.statusText,
  };
}
