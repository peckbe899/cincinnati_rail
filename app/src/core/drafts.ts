// Drafts: unsaved edits to a record, shared by every pane before a save (section 8). The line sheet's table and
// the inspector edit the same draft, so a PVI typed in one shows in the other at once.
//
// A draft holds the revision it started from (its base, whose ETag is the save's If-Match) and a working copy of
// the body. Edits are JSON Patch ops applied to the working copy; the save sends one coalesced patch, the diff from
// the base to the working copy, so a drag or a run of keystrokes is one changeset (9.13: no amending).
// A draft whose working copy equals its base again is dropped.

import type { Body, JsonPatch, Rec } from "../api/types.ts";
import { applyPatch, clone, deepEqual, diff } from "./jsonpatch.ts";
import type { View } from "./view.ts";

export interface Draft {
  key: string;
  kind: string;
  id: string;
  view: View;
  base: Rec;
  body: Body;
  /** Rises on every edit, so a save can tell whether edits came in while it was in flight. */
  rev: number;
  saving: boolean;
}

export type DraftListener = (key: string, d: Draft | null) => void;

export const bodyOf = (r: Rec): Body => ({ data: clone(r.data), geom: r.geom });

export class Drafts {
  private map = new Map<string, Draft>();
  private subs = new Set<DraftListener>();

  /** Drafts are per record and per layer: a scenario's draft never shows in main. */
  key(kind: string, id: string, view: View): string {
    return `${kind}/${id}@${view.layer}`;
  }

  get(kind: string, id: string, view: View): Draft | null {
    return this.map.get(this.key(kind, id, view)) ?? null;
  }

  byKey(key: string): Draft | null {
    return this.map.get(key) ?? null;
  }

  all(): Draft[] {
    return [...this.map.values()];
  }

  /** What a pane shows for a record: the draft's working copy if there is one. */
  view(rec: Rec, view: View): Body {
    return this.get(rec.kind, rec.id, view)?.body ?? bodyOf(rec);
  }

  /** Apply ops to the record's draft, starting one from rec when there is none. Throws PatchError. */
  edit(rec: Rec, view: View, ops: JsonPatch): Draft | null {
    const key = this.key(rec.kind, rec.id, view);
    const d =
      this.map.get(key) ??
      ({ key, kind: rec.kind, id: rec.id, view, base: rec, body: bodyOf(rec), rev: 0, saving: false } satisfies Draft);
    const body = applyPatch(d.body, ops);
    const next: Draft = { ...d, body, rev: d.rev + 1 };
    if (!next.saving && deepEqual(body, bodyOf(next.base))) {
      this.drop(key);
      return null;
    }
    this.map.set(key, next);
    this.emit(key, next);
    return next;
  }

  /** The one patch a save sends: from the base to the working copy. */
  ops(d: Draft): JsonPatch {
    return diff(bodyOf(d.base), d.body);
  }

  dirty(key: string): boolean {
    const d = this.map.get(key);
    return d !== undefined && this.ops(d).length > 0;
  }

  setSaving(key: string, saving: boolean): void {
    const d = this.map.get(key);
    if (!d) return;
    const next = { ...d, saving };
    this.map.set(key, next);
    this.emit(key, next);
  }

  /**
   * A save of the draft at revision rev came back as rec. If nothing was typed meanwhile the draft is done;
   * otherwise it carries on from rec with the newer edits still in it.
   */
  saved(key: string, rec: Rec, rev: number): void {
    const d = this.map.get(key);
    if (!d) return;
    if (d.rev === rev || deepEqual(d.body, bodyOf(rec))) {
      this.drop(key);
      return;
    }
    const next = { ...d, base: rec, saving: false };
    this.map.set(key, next);
    this.emit(key, next);
  }

  /** Start the draft from another base (Keep mine after a 412), with my changes rebased onto it as body. */
  rebase(key: string, base: Rec, body?: Body): void {
    const d = this.map.get(key);
    if (!d) return;
    const next = { ...d, base, body: body ?? d.body, saving: false };
    this.map.set(key, next);
    this.emit(key, next);
  }

  /** Put back a draft kept across a reload (host.restoreKept), unless one for the record is open already. */
  restore(d: Pick<Draft, "kind" | "id" | "view" | "base" | "body">): Draft | null {
    const key = this.key(d.kind, d.id, d.view);
    if (this.map.has(key) || deepEqual(d.body, bodyOf(d.base))) return null;
    const next: Draft = {
      key,
      kind: d.kind,
      id: d.id,
      view: d.view,
      base: d.base,
      body: d.body,
      rev: 1,
      saving: false,
    };
    this.map.set(key, next);
    this.emit(key, next);
    return next;
  }

  drop(key: string): void {
    if (this.map.delete(key)) this.emit(key, null);
  }

  subscribe(fn: DraftListener): () => void {
    this.subs.add(fn);
    return () => this.subs.delete(fn);
  }

  private emit(key: string, d: Draft | null): void {
    for (const fn of [...this.subs]) fn(key, d);
  }
}
