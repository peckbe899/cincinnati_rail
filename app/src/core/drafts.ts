// Drafts: unsaved edits to a record, shared by every pane before a save (section 8). The line sheet's table and
// the inspector edit the same draft, so a PVI typed in one shows in the other at once.
//
// A draft holds the revision it started from (its base, whose ETag is the save's If-Match) and a working copy of
// the body. Edits are JSON Patch ops applied to the working copy; the save sends one coalesced patch, the diff from
// the base to the working copy, so a drag or a run of keystrokes is one changeset (9.13: no amending).
// A draft whose working copy equals its base again is dropped.
//
// Steps (claude/hub_maps/profiles_parity.md 0.4): before a save, every edit is one step Ctrl+Z takes back, as the old
// Profiles page undid each edit. A run of edits that share a step id (one drag, one run of keystrokes in a cell) is
// one step. The steps of a draft go when it is saved or discarded; after a save, Ctrl+Z is the hub's undo of the
// changeset (core/undo.ts).

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

/** One step of unsaved editing: the body the draft had before it (null: no draft yet), and what it was. */
export interface DraftStep {
  key: string;
  /** The draft's working copy before the step; null when the step started the draft. */
  before: Body | null;
  /** The draft's working copy after the step (null when it dropped the draft), for redo. */
  after: Body | null;
  /** The record the draft started from, so a step back past the start can start it again on redo. */
  rec: Rec;
  view: View;
  /** Edits with the same step id run together into this one step. */
  group: string | null;
  label: string;
}

export interface EditOptions {
  /** Edits with the same id, one after another on the same draft, are one undo step (a drag, a cell's typing). */
  step?: string;
  /** What the step did, in Ben's words ("Bond Hill rail level"). */
  label?: string;
}

export const bodyOf = (r: Rec): Body => ({ data: clone(r.data), geom: r.geom });

export class Drafts {
  private map = new Map<string, Draft>();
  private subs = new Set<DraftListener>();
  private done: DraftStep[] = [];
  private undone: DraftStep[] = [];
  /** How many steps a tab keeps, as the old page kept 200 snapshots. */
  readonly limit = 200;

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

  /** Apply ops to the record's draft, starting one from rec when there is none. Throws PatchError. Each call is one
   * undo step, or part of the last one when it carries the same step id. */
  edit(rec: Rec, view: View, ops: JsonPatch, opts: EditOptions = {}): Draft | null {
    const key = this.key(rec.kind, rec.id, view);
    const had = this.map.get(key) ?? null;
    const d =
      had ??
      ({ key, kind: rec.kind, id: rec.id, view, base: rec, body: bodyOf(rec), rev: 0, saving: false } satisfies Draft);
    const body = applyPatch(d.body, ops);
    if (deepEqual(body, d.body) && had) return had;
    const last = this.done[this.done.length - 1];
    const joins = !!opts.step && !!last && last.key === key && last.group === opts.step;
    const next: Draft = { ...d, body, rev: d.rev + 1 };
    const gone = !next.saving && deepEqual(body, bodyOf(next.base));
    if (joins && last) last.after = gone ? null : body;
    else if (!(gone && !had)) {
      this.done.push({
        key,
        before: had ? had.body : null,
        after: gone ? null : body,
        rec: had ? had.base : rec,
        view,
        group: opts.step ?? null,
        label: opts.label ?? "edit",
      });
      if (this.done.length > this.limit) this.done.shift();
    }
    this.undone = [];
    if (gone) {
      this.remove(key);
      return null;
    }
    this.map.set(key, next);
    this.emit(key, next);
    return next;
  }

  /** The unsaved step Ctrl+Z would take back in a layer, if any. */
  peekStep(layer?: string): DraftStep | null {
    for (let i = this.done.length - 1; i >= 0; i--) {
      const s = this.done[i] as DraftStep;
      if (layer === undefined || s.view.layer === layer) return s;
    }
    return null;
  }

  peekRedoStep(layer?: string): DraftStep | null {
    for (let i = this.undone.length - 1; i >= 0; i--) {
      const s = this.undone[i] as DraftStep;
      if (layer === undefined || s.view.layer === layer) return s;
    }
    return null;
  }

  /** Take back the last unsaved step in a layer: the draft goes back to its body before it. */
  stepBack(layer?: string): DraftStep | null {
    const s = this.peekStep(layer);
    if (!s) return null;
    this.done.splice(this.done.lastIndexOf(s), 1);
    this.undone.push(s);
    this.put(s, s.before);
    return s;
  }

  /** Do again the last step taken back. */
  stepForward(layer?: string): DraftStep | null {
    const s = this.peekRedoStep(layer);
    if (!s) return null;
    this.undone.splice(this.undone.lastIndexOf(s), 1);
    this.done.push(s);
    this.put(s, s.after);
    return s;
  }

  /** Set a draft's working copy to body (null or the base's body: no draft). */
  private put(s: DraftStep, body: Body | null): void {
    const cur = this.map.get(s.key);
    const base = cur?.base ?? s.rec;
    if (body === null || deepEqual(body, bodyOf(base))) {
      this.remove(s.key);
      return;
    }
    const next: Draft = cur
      ? { ...cur, body, rev: cur.rev + 1 }
      : { key: s.key, kind: base.kind, id: base.id, view: s.view, base, body, rev: 1, saving: false };
    this.map.set(s.key, next);
    this.emit(s.key, next);
  }

  /** Forget a draft's steps (saved, discarded, rebased). */
  private forget(key: string): void {
    this.done = this.done.filter((s) => s.key !== key);
    this.undone = this.undone.filter((s) => s.key !== key);
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
    this.forget(key);
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
    this.forget(key);
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

  /** Discard a draft (Discard, Take theirs, a save): its unsaved steps go with it. */
  drop(key: string): void {
    this.forget(key);
    this.remove(key);
  }

  /** The draft gone, its steps kept (an edit that put the record back as it was is still a step). */
  private remove(key: string): void {
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
