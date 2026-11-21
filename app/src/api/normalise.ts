// Normalisers for the server's container shapes. Until region/api/openapi.json fixes them, the transport accepts a
// list as a bare array or under items, records, data or results, and /meta with kinds as an array or an object.

import type { KindMeta, LayerMeta, Meta, Rec } from "./types.ts";

export function listOf<T>(r: unknown, ...keys: string[]): T[] {
  if (Array.isArray(r)) return r as T[];
  if (r && typeof r === "object") {
    for (const k of [...keys, "items", "records", "data", "results"]) {
      const v = (r as Record<string, unknown>)[k];
      if (Array.isArray(v)) return v as T[];
    }
  }
  return [];
}

export function normaliseList(r: unknown): { items: Rec[]; next: string | null } {
  const items = listOf<Rec>(r);
  let next: string | null = null;
  if (r && typeof r === "object" && !Array.isArray(r)) {
    const o = r as Record<string, unknown>;
    const v = o.next ?? o.after ?? o.cursor ?? null;
    next = typeof v === "string" ? v : null;
  }
  return { items, next };
}

export function normaliseLayers(r: unknown): LayerMeta[] {
  return listOf<LayerMeta | string>(r, "layers").map((l) => (typeof l === "string" ? { slug: l, tier: tierOf(l) } : l));
}

function tierOf(slug: string): string {
  if (slug === "main") return "main";
  const head = slug.split(":")[0] ?? "";
  return ["import", "legacy", "proposal"].includes(head) && slug.includes(":") ? head : "scenario";
}

/** /meta in one shape, whether the server lists kinds as an array or an object, and whatever it calls members. */
export function normaliseMeta(raw: unknown): Meta {
  const r = (raw ?? {}) as Record<string, unknown>;
  const kinds: Record<string, KindMeta> = {};
  const rawKinds = r.kinds;
  const entries: [string | null, unknown][] = Array.isArray(rawKinds)
    ? rawKinds.map((k) => [null, k])
    : Object.entries((rawKinds ?? {}) as Record<string, unknown>);
  for (const [key, v] of entries) {
    const k = (v ?? {}) as Record<string, unknown>;
    const name = String(k.kind ?? k.name ?? key ?? "");
    if (!name) continue;
    const spec = (k.spec && typeof k.spec === "object" ? k.spec : k) as Record<string, unknown>;
    kinds[name] = {
      ...(spec as object),
      kind: name,
      version: Number(spec.version ?? k.version ?? 1),
      schema: (spec.schema ?? spec.data_schema ?? {}) as KindMeta["schema"],
    } as KindMeta;
  }
  const engine = (r.engine ?? r.engine_hello ?? r.hello ?? null) as Meta["engine"];
  const cfg = (r.config ?? {}) as Record<string, unknown>;
  return {
    kinds,
    layers: normaliseLayers(r.layers ?? []),
    features: listOf<unknown>(r.features).map((f) =>
      typeof f === "string" ? f : String((f as { name?: string }).name ?? ""),
    ),
    importers: listOf(r.importers),
    job_types: listOf(r.job_types ?? r.jobs),
    engine:
      engine && typeof engine === "object" && "hello" in engine
        ? ((engine as { hello: Meta["engine"] }).hello ?? null)
        : engine,
    schema_version: typeof r.schema_version === "number" ? r.schema_version : null,
    epoch: typeof (r.epoch ?? r.server_epoch) === "string" ? String(r.epoch ?? r.server_epoch) : null,
    old_hub: String(r.old_hub ?? cfg.old_hub ?? "http://127.0.0.1:8765"),
    raw,
  };
}
