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
