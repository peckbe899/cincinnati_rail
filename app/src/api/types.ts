// Hand-written shapes of the section 5 API, used until region/api/openapi.json lands and src/api/gen is generated
// from it (npm run gen:api -w app). They follow region/core: protocols.Record, errors.to_problem and events.py.

/** A record in the get() shape (region.core.protocols.Record). */
export interface Rec<D = Record<string, unknown>> {
  id: string;
  kind: string;
  kv: number;
  layer: string;
  version: number;
  hash: string;
  deleted: boolean;
  origin: string;
  source: string | null;
  by: string;
  changeset: string;
  created: string;
  updated: string;
  geom: string | null;
  data: D;
}

/** The writable part of a record. JSON Patch paths are relative to it (/data/pvi/3/z_m). */
export interface Body<D = Record<string, unknown>> {
  data: D;
  geom: string | null;
}

export interface JsonPatchOp {
  op: "add" | "remove" | "replace" | "move" | "copy" | "test";
  path: string;
  value?: unknown;
  from?: string;
}
export type JsonPatch = JsonPatchOp[];

/** One op of POST /changesets (region.core.protocols.Op). */
export interface ChangesetOp {
  op: "create" | "put" | "patch" | "delete";
  kind: string;
  id: string | null;
  if_match: string | null;
  body?: Body | null;
  patch?: JsonPatch | null;
}

/** What a committed changeset did (region.core.protocols.WriteResult). */
export interface WriteResult {
  changeset: string | null;
  records: Rec[];
  seq: number | null;
}

/** An RFC 9457 problem body as region.core.errors.HubError.to_problem() writes it. */
export interface Problem {
  type?: string;
  title?: string;
  status: number;
  detail?: string;
  code?: string;
  request_id?: string | null;
  instance?: string;
  current?: Rec | null;
  by?: string | null;
  diff?: JsonPatch | null;
  stale?: { index: number; kind: string; id: string; if_match: string | null; etag: string | null }[];
  reason?: string;
  conflicts?: Record<string, unknown>[];
  errors?: { path: string; message: string; rule?: string }[];
  [key: string]: unknown;
}

/** A kind as /meta lists it: the kind file (region/kinds/_meta.schema.json) with its JSON Schema. */
export interface KindMeta {
  kind: string;
  version: number;
  title?: string;
  description?: string;
  geometry?: string;
  columns?: Record<string, string>;
  legacy?: string[];
  feature?: string | null;
  /** The record's references: a pointer in data (with * for any list index) and the kind it names. */
  refs?: { path: string; kind: string | string[]; role?: string; on_delete?: string; required?: boolean }[];
  merge?: { unit?: string; rebase?: string; guard?: string[] };
  schema: JsonSchema;
}

export interface LayerMeta {
  slug: string;
  tier: string;
  parent?: string | null;
  state?: string;
  title?: string | null;
  namespace?: string | null;
}

/** GET /meta, normalised by Api.meta() whatever container shapes the server uses. */
export interface Meta {
  kinds: Record<string, KindMeta>;
  layers: LayerMeta[];
  features: string[];
  importers: unknown[];
  job_types: unknown[];
  engine: { engine_version?: string; engine_build?: string; contracts?: Record<string, number> } | null;
  schema_version: number | null;
  epoch: string | null;
  old_hub: string;
  raw: unknown;
}

/** A JSON Schema 2020-12 node as the kind files write them, with the hub's annotations. */
export interface JsonSchema {
  type?: string | string[];
  title?: string;
  description?: string;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  additionalProperties?: boolean | JsonSchema;
  items?: JsonSchema;
  prefixItems?: JsonSchema[];
  enum?: unknown[];
  const?: unknown;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
  exclusiveMaximum?: number;
  minItems?: number;
  maxItems?: number;
  pattern?: string;
  default?: unknown;
  examples?: unknown[];
  oneOf?: JsonSchema[];
  anyOf?: JsonSchema[];
  "x-unit"?: string;
  "x-vocab"?: string;
  $ref?: string;
  $defs?: Record<string, JsonSchema>;
  [key: string]: unknown;
}

export interface Job {
  id: string;
  type: string;
  scope: string;
  state: "queued" | "running" | "done" | "failed" | "cancelled";
  progress: number;
  msg: string;
  view?: string;
  key?: string;
  error?: string;
}

export interface Conflict {
  id: string;
  layer: string;
  rec_id: string;
  kind: string;
  reason: string;
  state: string;
  fields?: unknown;
  proposed?: unknown;
  created?: string;
  [key: string]: unknown;
}

export interface TierStatus {
  name: string;
  status: "missing" | "partial" | "present";
  detail?: string;
  mount?: boolean;
  [key: string]: unknown;
}

export interface ResultMeta {
  key: string;
  type: string;
  scope: string;
  view: string;
  status: "ok" | "error" | "stale";
  meta?: Record<string, unknown>;
  arrays?: string[] | Record<string, unknown>;
  [key: string]: unknown;
}

/** An array of a result (GET /results/{key}/a/{name}), read with its X-Dtype and X-Shape. */
export interface ResultArray {
  dtype: string;
  shape: number[];
  buffer: ArrayBuffer;
}

// Event payloads (region/core/events.py).

export interface RecordEvent {
  seq: number;
  op: "create" | "put" | "patch" | "delete" | "restore";
  kind: string;
  id: string;
  layer: string;
  version: number;
  hash: string;
  by: string;
  client: string | null;
  changeset: string;
  fields: string[];
  bbox: number[] | null;
}
export interface ChangesetEvent {
  seq: number;
  id: string;
  layer: string;
  by: string;
  count: number;
  kinds: Record<string, number>;
  bbox: number[] | null;
  summary: boolean;
  kind?: string;
  message?: string;
  client?: string | null;
}
export interface JobEvent extends Job {}
export interface ResultEvent {
  key: string;
  type: string;
  scope: string;
  view: string;
  status: "ok" | "error" | "stale";
  changed: number[][];
}
export interface TierEvent {
  tier: string;
  status: "missing" | "partial" | "present";
  detail: string;
}
/** The engine pool answered after the stream's hello, which then said engine_build null (a cold start). */
export interface EngineEvent {
  engine_build: string | null;
  error: string | null;
}
export interface ResyncEvent {
  reason: "pruned" | "epoch" | "overflow";
  seq: number;
}
export interface HelloEvent {
  epoch: string;
  seq: number;
  engine_build: string | null;
}

export type HubEvent =
  | { type: "record"; seq: number; data: RecordEvent }
  | { type: "changeset"; seq: number; data: ChangesetEvent }
  | { type: "job"; seq: number | null; data: JobEvent }
  | { type: "result"; seq: number | null; data: ResultEvent }
  | { type: "tier"; seq: number | null; data: TierEvent }
  | { type: "engine"; seq: number | null; data: EngineEvent }
  | { type: "resync"; seq: number | null; data: ResyncEvent }
  | { type: "hello"; seq: number | null; data: HelloEvent };

export const DURABLE_EVENTS: ReadonlySet<string> = new Set(["record", "changeset"]);
