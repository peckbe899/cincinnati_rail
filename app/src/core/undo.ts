// Undo as a stack of server changesets (decision 9.13, section 8). Undo posts /changesets/{id}/revert, which writes
// the prior content as a new revert changeset with If-Match on what the original produced; redo reverts that
// revert. So Ctrl+Z after an edit to version 2 gives version 3 equal to version 1, and a later edit by anyone makes
// the undo a 409 that leaves the stack as it was.

import type { Api } from "../api/client.ts";
import type { Rec, WriteResult } from "../api/types.ts";
import type { View } from "./view.ts";

export interface UndoEntry {
  changeset: string;
  label: string;
  view: View;
}

type Listener = () => void;

export class UndoStack {
  private done: UndoEntry[] = [];
  private undone: UndoEntry[] = [];
  private subs = new Set<Listener>();
  private busy = false;

  private readonly api: Api;
  /** Called with the records a revert wrote, so the cache and drafts follow. */
  private readonly onRecords: (recs: Rec[], view: View) => void;
  private readonly limit: number;

  constructor(api: Api, onRecords: (recs: Rec[], view: View) => void = () => {}, limit = 200) {
    this.api = api;
    this.onRecords = onRecords;
    this.limit = limit;
  }

  push(e: UndoEntry): void {
    this.done.push(e);
    if (this.done.length > this.limit) this.done.shift();
    this.undone = [];
    this.emit();
  }

  get canUndo(): boolean {
    return this.done.length > 0 && !this.busy;
  }

  get canRedo(): boolean {
    return this.undone.length > 0 && !this.busy;
  }

  /** The label of what Ctrl+Z would undo. */
  peek(): UndoEntry | null {
    return this.done[this.done.length - 1] ?? null;
  }

  /** The label of what Ctrl+Shift+Z would redo. */
  peekRedo(): UndoEntry | null {
    return this.undone[this.undone.length - 1] ?? null;
  }

  async undo(): Promise<WriteResult | null> {
    return this.step(this.done, this.undone);
  }

  async redo(): Promise<WriteResult | null> {
    return this.step(this.undone, this.done);
  }

  clear(): void {
    this.done = [];
    this.undone = [];
    this.emit();
  }

  subscribe(fn: Listener): () => void {
    this.subs.add(fn);
    return () => this.subs.delete(fn);
  }

  private async step(from: UndoEntry[], to: UndoEntry[]): Promise<WriteResult | null> {
    if (this.busy) return null;
    const e = from.pop();
    if (!e) return null;
    this.busy = true;
    this.emit();
    try {
      const r = await this.api.revert(e.changeset);
      if (r.changeset) to.push({ ...e, changeset: r.changeset });
      this.onRecords(r.records ?? [], e.view);
      return r;
    } catch (err) {
      from.push(e);
      throw err;
    } finally {
      this.busy = false;
      this.emit();
    }
  }

  private emit(): void {
    for (const fn of [...this.subs]) fn();
  }
}
