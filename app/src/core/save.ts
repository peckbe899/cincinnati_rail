// Saving a draft, and the 412 flow (section 8: "A 412 offers Keep mine or Take theirs").
//
// save() sends the draft's coalesced patch with If-Match on its base. On success the response goes into the cache,
// the changeset onto the undo stack, and the draft is done. On 412 the server's body carries the current record
// (its by and a diff); save() returns a StaleOffer instead of throwing. The offer says what each side changed from
// the draft's base, and where both changed the same field, so the banner can name them before Ben chooses:
// - keepMine() rebases my changes onto their record (a three-way rebase: only the fields I changed are sent, with
//   If-Match on theirs), so their change to a field I never touched stays. Where both changed a field, mine wins
//   there, and the offer named it first. It is never a whole-document save (plan section 18);
// - takeTheirs() drops my draft and shows their record.
//
// One save of a draft is in flight at a time. A second save() of the same draft (Enter in a cell, then Ctrl+S)
// waits for the first and then sends only what was typed since, against the revision the first one wrote; sent at
// once, it would carry the first one's If-Match and come back 412 against this tab's own save.

import { type Api, ApiError, etagOf } from "../api/client.ts";
import type { Body, JsonPatch, Rec } from "../api/types.ts";
import { bodyOf, type Draft, type Drafts } from "./drafts.ts";
import { diff, getAt, rebase3 } from "./jsonpatch.ts";
import type { RecordCache } from "./records.ts";
import type { UndoStack } from "./undo.ts";

/** One field one side changed, from the draft's base: its pointer in the body and its value before and after. */
export interface FieldChange {
  path: string;
  before: unknown;
  after: unknown;
}

/** What each side changed from the draft's base, and the fields both changed (where Keep mine puts mine). */
export interface StaleChanges {
  mine: FieldChange[];
  theirs: FieldChange[];
  both: { path: string; base: unknown; mine: unknown; theirs: unknown }[];
}

export interface StaleOffer {
  draft: Draft;
  mine: Body;
  theirs: Rec;
  by: string | null;
  diff: JsonPatch | null;
  changes: StaleChanges;
  keepMine(): Promise<Rec>;
  takeTheirs(): Rec;
}

/** The three-way picture of a stale draft: base, my working copy, their record. */
export function staleChanges(base: Body, mine: Body, theirs: Body): StaleChanges {
  const r = rebase3(base, mine, theirs);
  const change = (other: Body) => (path: string) => ({ path, before: getAt(base, path), after: getAt(other, path) });
  return {
    mine: r.mine.map(change(mine)),
    theirs: r.theirs.map(change(theirs)),
    both: r.both.map((path) => ({
      path,
      base: getAt(base, path),
      mine: getAt(mine, path),
      theirs: getAt(theirs, path),
    })),
  };
}

export type SaveOutcome = { status: "clean" } | { status: "saved"; rec: Rec } | { status: "stale"; offer: StaleOffer };

export interface SaveDeps {
  api: Api;
  drafts: Drafts;
  records: RecordCache;
  undo: UndoStack;
}

function done(deps: SaveDeps, d: Draft, rec: Rec, rev: number, label: string): Rec {
  deps.records.set(rec, d.view);
  deps.drafts.saved(d.key, rec, rev);
  if (rec.changeset) deps.undo.push({ changeset: rec.changeset, label, view: d.view });
  return rec;
}

const inflight = new WeakMap<Drafts, Map<string, Promise<unknown>>>();

function writes(drafts: Drafts): Map<string, Promise<unknown>> {
  let m = inflight.get(drafts);
  if (!m) {
    m = new Map();
    inflight.set(drafts, m);
  }
  return m;
}

/** Run one write of a draft, recorded as the draft's write in flight until it settles. */
function track<T>(drafts: Drafts, key: string, run: () => Promise<T>): Promise<T> {
  const m = writes(drafts);
  const p = run();
  m.set(key, p);
  const clear = () => {
    if (m.get(key) === p) m.delete(key);
  };
  p.then(clear, clear);
  return p;
}

export async function save(deps: SaveDeps, key: string, label = "edit"): Promise<SaveOutcome> {
  const running = writes(deps.drafts).get(key);
  if (running) {
    const prev = await running.catch(() => null);
    // A save that came back stale has raised its offer already; a second send would only meet the same 412.
    if (prev && typeof prev === "object" && (prev as SaveOutcome).status === "stale") return prev as SaveOutcome;
    return save(deps, key, label);
  }
  return track(deps.drafts, key, () => saveOnce(deps, key, label));
}

async function saveOnce(deps: SaveDeps, key: string, label: string): Promise<SaveOutcome> {
  const d = deps.drafts.byKey(key);
  if (!d) return { status: "clean" };
  const ops = deps.drafts.ops(d);
  if (ops.length === 0) {
    deps.drafts.drop(key);
    return { status: "clean" };
  }
  deps.drafts.setSaving(key, true);
  try {
    const rec = await deps.api.patch(d.kind, d.id, ops, d.view, etagOf(d.base));
    return { status: "saved", rec: done(deps, d, rec, d.rev, label) };
  } catch (e) {
    deps.drafts.setSaving(key, false);
    if (e instanceof ApiError && e.status === 412) return { status: "stale", offer: await offer(deps, key, e, label) };
    throw e;
  }
}

async function offer(deps: SaveDeps, key: string, e: ApiError, label: string): Promise<StaleOffer> {
  const d = deps.drafts.byKey(key) as Draft;
  const theirs = (e.problem.current as Rec | null | undefined) ?? (await deps.api.getRecord(d.kind, d.id, d.view));
  const takeTheirs = (): Rec => {
    deps.drafts.drop(key);
    deps.records.set(theirs, d.view);
    return theirs;
  };
  return {
    draft: d,
    mine: d.body,
    theirs,
    by: e.problem.by ?? theirs.by ?? null,
    diff: e.problem.diff ?? null,
    changes: staleChanges(bodyOf(d.base), d.body, bodyOf(theirs)),
    async keepMine() {
      const running = writes(deps.drafts).get(key);
      if (running) await running.catch(() => undefined);
      const cur = deps.drafts.byKey(key) ?? d;
      // Only what this tab changed from its base goes onto theirs: a field it never touched keeps their value.
      const merged = rebase3(bodyOf(cur.base), cur.body, bodyOf(theirs)).result;
      const ops = diff(bodyOf(theirs), merged);
      if (ops.length === 0) return takeTheirs();
      deps.drafts.rebase(key, theirs, merged);
      deps.drafts.setSaving(key, true);
      return track(deps.drafts, key, async () => {
        try {
          const rec = await deps.api.patch(d.kind, d.id, ops, d.view, etagOf(theirs));
          return done(deps, cur, rec, cur.rev, label);
        } finally {
          deps.drafts.setSaving(key, false);
        }
      });
    },
    takeTheirs,
  };
}
