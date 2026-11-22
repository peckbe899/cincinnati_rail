// Names in Ben's terms (plan section 7). Wherever the app would show a record id it shows the record's name: its
// data.name (or title or key); a profile is "<its section's name> profile"; a platform or a stop can also carry its
// section's name, "Bond Hill (Line 6)". An id with no name known yet shows short, as "section …N14PM3", never as the
// whole ULID.
//
// Names are read through the record cache and kept per view. peek() answers at once with what is known; get() reads
// the record when it is not; text() answers at once and reads in the background, and onChange() tells a pane to
// redraw when a name arrives. learn() takes the names of records a pane has read already (a list, a write's answer).

import type { Rec } from "../api/types.ts";
import type { RecordCache } from "./records.ts";
import { type View, viewToken } from "./view.ts";

/** A ULID as the record ids are written (region/core/ids.py). */
export const ULID_RE = /^[0-7][0-9A-HJKMNP-TV-Z]{25}$/;

/** "…N14PM3": the end of an id, for a record whose name is not known. */
export function shortId(id: string): string {
  return id.length > 8 ? `…${id.slice(-6)}` : id;
}

/** The name a record carries itself, or null. */
export function ownName(rec: Pick<Rec, "kind" | "data">): string | null {
  const d = (rec.data ?? {}) as Record<string, unknown>;
  for (const k of ["name", "title", "label"]) {
    const v = d[k];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  if (rec.kind === "authority" && typeof d.kind === "string") return `who owns ${d.kind} records`;
  if (typeof d.path === "string" && d.path) return d.path;
  if (typeof d.key === "string" && d.key) return d.key.replace(/_/g, " ");
  return null;
}

/** The section a record belongs to, for the kinds that name one. */
function sectionOf(rec: Pick<Rec, "kind" | "data">): string | null {
  const d = (rec.data ?? {}) as Record<string, unknown>;
  const s = d.section ?? (rec.kind === "profile" ? (d.section_id ?? d.parent) : undefined);
  return typeof s === "string" && s ? s : null;
}

export class Names {
  private readonly records: RecordCache;
  private readonly known = new Map<string, string>();
  private readonly reading = new Map<string, Promise<string>>();
  private readonly subs = new Set<() => void>();
  private soon: ReturnType<typeof setTimeout> | null = null;

  constructor(records: RecordCache) {
    this.records = records;
  }

  private key(kind: string, id: string, view: View): string {
    return `${viewToken(view)}|${kind}|${id}`;
  }

  /** Keep the names of records already read. */
  learn(recs: Iterable<Rec>, view: View): void {
    let changed = false;
    for (const r of recs) {
      const n = r.kind === "profile" ? null : ownName(r);
      if (n === null) continue;
      const k = this.key(r.kind, r.id, view);
      if (this.known.get(k) !== n) {
        this.known.set(k, n);
        changed = true;
      }
    }
    if (changed) this.changed();
  }

  /** Keep one name found some other way (a name search's hit). */
  remember(kind: string, id: string, name: string, view: View): void {
    const k = this.key(kind, id, view);
    if (this.known.get(k) === name) return;
    this.known.set(k, name);
    this.changed();
  }

  /** The name known now (from this map or the record cache), or null. */
  peek(kind: string, id: string, view: View): string | null {
    const have = this.known.get(this.key(kind, id, view));
    if (have !== undefined) return have;
    const rec = this.records.peek(kind, id, view);
    if (!rec) return null;
    if (kind === "profile") {
      const sec = sectionOf(rec);
      const sn = sec ? this.peek("section", sec, view) : null;
      return sn ? `${sn} profile` : null;
    }
    return ownName(rec);
  }

  /** The record's name, reading the record (and a profile's section) when it is not known. Never throws. */
  get(kind: string, id: string, view: View): Promise<string> {
    const now = this.peek(kind, id, view);
    if (now !== null) return Promise.resolve(now);
    const k = this.key(kind, id, view);
    const running = this.reading.get(k);
    if (running) return running;
    const p = (async () => {
      try {
        const rec = await this.records.get(kind, id, view);
        let n = ownName(rec);
        if (kind === "profile") {
          const sec = sectionOf(rec);
          n = sec ? `${await this.get("section", sec, view)} profile` : "profile";
        }
        const out = n ?? `${kind} ${shortId(id)}`;
        this.known.set(k, out);
        this.changed();
        return out;
      } catch {
        return `${kind} ${shortId(id)}`;
      } finally {
        this.reading.delete(k);
      }
    })();
    this.reading.set(k, p);
    return p;
  }

  /** The name, with the section's after it for a platform or a stop: "Bond Hill (Line 6)". */
  async full(kind: string, id: string, view: View): Promise<string> {
    const n = await this.get(kind, id, view);
    if (kind !== "platform" && kind !== "stop") return n;
    try {
      const sec = sectionOf(await this.records.get(kind, id, view));
      return sec ? `${n} (${await this.get("section", sec, view)})` : n;
    } catch {
      return n;
    }
  }

  /** The name known now, or the kind and a short id while it is read; onChange() fires when it arrives. */
  text(kind: string, id: string, view: View): string {
    const now = this.peek(kind, id, view);
    if (now !== null) return now;
    void this.get(kind, id, view);
    return `${kind} ${shortId(id)}`;
  }

  /** Called (once per burst) when names arrive. */
  onChange(fn: () => void): () => void {
    this.subs.add(fn);
    return () => this.subs.delete(fn);
  }

  private changed(): void {
    if (this.soon) return;
    this.soon = setTimeout(() => {
      this.soon = null;
      for (const fn of [...this.subs]) fn();
    }, 0);
  }
}
