// Ctrl+K's lookup: resolve what Ben types to records. Accepted forms:
// - "<kind>:<id>" for a record he knows;
// - "<lkind>:<key>" or "<lkind> <key>" for an old key of a known legacy kind (the kinds' legacy lists in /meta);
// - a bare old key ("Line_8", "Line_8|Cincinnati State#2", "metro:Syacmore:715445:4331182", "S0089"), tried against
//   every legacy kind at once; the likely kinds for its shape go first.

import type { Api } from "../../api/client.ts";
import type { Meta } from "../../api/types.ts";

export interface LegacyHit {
  lkind: string;
  key: string;
  kind: string;
  id: string;
}

/** Legacy kinds tried when /meta's kinds declare none (the old hub's key schemes, claude/hub_maps/oldhub.md). */
export const FALLBACK_LKINDS = [
  "route",
  "section",
  "alignment_station",
  "deck_station",
  "street",
  "block",
  "roadmap_item",
];

/** Every legacy kind the kinds declare, and which kind each maps to ("" when only the fallback list is known). */
export function legacyKinds(meta: Meta): Map<string, string> {
  const out = new Map<string, string>();
  for (const k of Object.values(meta.kinds)) for (const l of k.legacy ?? []) out.set(l, k.kind);
  if (out.size === 0) for (const l of FALLBACK_LKINDS) out.set(l, "");
  return out;
}

/** Legacy kinds whose keys look like this text, most likely first; the rest follow. */
export function guessOrder(text: string, lkinds: string[]): string[] {
  const likely: string[] = [];
  const has = (re: RegExp) => lkinds.filter((l) => re.test(l));
  if (/^(Line_\d+[a-z]?|RER_[A-Z0-9_]+|CVG_Express)$/i.test(text)) likely.push(...has(/route|alignment$|line/));
  if (text.includes("|")) likely.push(...has(/^alignment|profile/), ...has(/station|stop|platform/));
  if (/^(metro|rer|cvx):/i.test(text)) likely.push(...has(/deck/), ...has(/station/));
  if (/^S[A-Z]*\d+$/.test(text)) likely.push(...has(/street/));
  if (/^(B|SBB|FB)\d+/.test(text)) likely.push(...has(/block|plot/));
  if (/^r\d\d$/.test(text)) likely.push(...has(/roadmap/));
  return [...new Set([...likely, ...lkinds])];
}

export async function lookup(api: Api, meta: Meta, raw: string, signal?: AbortSignal): Promise<LegacyHit[]> {
  const text = raw.trim();
  if (!text) return [];
  const lk = legacyKinds(meta);
  const named = /^([a-z][a-z0-9_]*)(?::|\s+)(.+)$/.exec(text);
  if (named?.[1] && named[2] && lk.has(named[1])) {
    const hit = await api.legacy(named[1], named[2].trim());
    return hit ? [{ lkind: named[1], key: named[2].trim(), ...hit }] : [];
  }
  const order = guessOrder(text, [...lk.keys()]);
  const found = await Promise.all(
    order.map(async (l) => {
      if (signal?.aborted) return null;
      try {
        const hit = await api.legacy(l, text);
        return hit ? { lkind: l, key: text, ...hit } : null;
      } catch {
        return null;
      }
    }),
  );
  return found.filter((h): h is LegacyHit => h !== null);
}

/** A record found by its name. */
export interface NameHit {
  kind: string;
  id: string;
  name: string;
  /** The section a platform or a stop is on, when the record says it. */
  section: string | null;
  /** A station's old key ("Line_3|Bond Hill"), which says its line. */
  key: string | null;
}

/** The kinds Ctrl+K searches by name, the likeliest first. */
export const NAME_KINDS = ["section", "route", "station", "platform"];

/** The ways a name may be typed: "Line6", "line_6" and "Line 6" all look for "Line 6". */
export function nameQueries(text: string): string[] {
  const t = text.trim();
  const spaced = t
    .replace(/_/g, " ")
    .replace(/([A-Za-z])(\d)/g, "$1 $2")
    .replace(/\s+/g, " ");
  return [...new Set([t, spaced])].filter((q) => q.length >= 2);
}

/** Records whose name matches the text (the server's name search, /k/<kind>?q=), a few per kind. */
export async function searchNames(
  api: Api,
  view: import("../../core/view.ts").View,
  text: string,
  signal?: AbortSignal,
  kinds: string[] = NAME_KINDS,
  perKind = 8,
): Promise<NameHit[]> {
  const qs = nameQueries(text);
  const found = await Promise.all(
    kinds.flatMap((kind) =>
      qs.map(async (q) => {
        if (signal?.aborted) return [];
        try {
          const { items } = await api.list(kind, view, { q, limit: perKind, fields: "name,key,section" });
          return items.map((r) => {
            const d = r.data as Record<string, unknown>;
            return {
              kind,
              id: r.id,
              name: typeof d.name === "string" ? d.name : r.id,
              section: typeof d.section === "string" ? d.section : null,
              key: typeof d.key === "string" ? d.key : null,
            };
          });
        } catch {
          return [];
        }
      }),
    ),
  );
  const seen = new Set<string>();
  return found.flat().filter((h) => {
    const k = `${h.kind}:${h.id}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}
