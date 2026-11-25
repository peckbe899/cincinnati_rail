// Run times on the line sheet (I2.1, claude/hub_maps/i21_plan.md sections 1.4 to 1.7): the saved run of the
// section's route, kept fresh by the hub, and a draft run of Ben's unsaved edit.
//
// The saved run is a job like the rail's: POST /compute {type: railsim.run, scope: <route>} at priority 2 while the
// sheet has the focus and 3 while it is open (9 when it closes), with the same watch, so the hub runs it again after
// every save and import; its result events bring the new key. It reruns only when its inputs' content hash changes
// (the hub's early cutoff); the sheet never asks during a drag.
//
// The draft run is railsim on the sheet's own edit, before it is saved: POST /x/railsim/sections/{id}/draft with the
// SectionInput of the draft and the whole solve's structure types for that edit. It is posted only when no editing
// drag is on, once the whole solve of the current edit has landed, and 300 ms after the last edit; a newer edit
// aborts the request in flight. A draft equal to the saved records is never posted: the saved run is shown.
//
// Nothing here polls or keeps a timer when nothing is due: an idle sheet makes no requests.

import { ApiError } from "../../api/client.ts";
import type * as Gen from "../../api/gen/index.ts";
import type { HubEvent, ResultArray, ResultMeta } from "../../api/types.ts";
import type { View } from "../../core/view.ts";
import { toFloat64 } from "./model.ts";

export const RUN_JOB = "railsim.run";
export const ATTRIBUTION_JOB = "railsim.attribution";
export const ASSEMBLE_JOB = "route.assemble";
export const HORIZONTAL_JOB = "route.horizontal";
/** How long after the last edit a draft is posted (ms). */
export const DRAFT_PAUSE_MS = 300;
/** How long the hub keeps the run's goal fresh after an ask (s), as the rail's. */
export const RUN_WATCH_S = 600;
/** The priority of the saved run: after the rail (0 and 1), in focus first. */
export const runPriority = (focused: boolean): number => (focused ? 2 : 3);
export const CLOSED_PRIORITY = 9;
export const ATTRIBUTION_PRIORITY = 4;
/** How long a draft stays shown after the draft is clean again, waiting to learn whether it was saved (ms). */
const CLEAN_GRACE_MS = 400;
/** How long a saved draft is kept while the saved run of the new records is on its way (ms). */
const SAVE_HOLD_MS = 120_000;
/** How often a waiting draft looks again whether the drag is over (ms). */
const DRAG_RETRY_MS = 100;

// ------------------------------------------------------------------------------------------- the contract
// run_result/0 (region/ext/railsim/contract.py), from the generated API types, with the direction narrowed to 1 or
// -1 and the members the sheet reads that the schema leaves open.

/** ``T`` less the keys ``K``; unlike ``Omit`` it keeps the named members of a type with an index signature. */
type Without<T, K extends PropertyKey> = { [P in keyof T as P extends K ? never : P]: T[P] };

export type Leg = Gen.RunLeg;
export type StationRow = Gen.RunStation;
export type RunDirection = Without<Gen.RunDirection, "dir" | "stations"> & {
  /** 1 is rising section chainage, -1 falling. */
  dir: 1 | -1;
  stations: StationRow[];
};
export type SpeedZone = Gen.RunZone;
export type CurveLimit = Gen.RunCurveLimit;

type DraftOnly = "arrays" | "base" | "cached" | "draft" | "edit_rev" | "key" | "ms" | "types";

export type RunResult = Without<Gen.DraftOut, DraftOnly | "contract" | "directions" | "padding"> & {
  contract: string;
  directions: RunDirection[];
  padding: { percent?: number; final_leg_s?: number };
  headway_min?: number | null;
  trains_needed?: number;
};

export type DraftOut = RunResult &
  Without<Pick<Gen.DraftOut, DraftOnly>, "draft" | "edit_rev"> & {
    draft: true;
    edit_rev: number | null;
  };

/** railsim.attribution's meta: where each direction's time goes. */
export interface Attribution {
  directions: {
    dir: 1 | -1;
    zones: { c0_m: number; c1_m: number; reason: string; rule: string | null; limit_kmh: number; lost_s: number }[];
    grades_s: number;
    tunnel_drag_s: number;
    dwell_s: number;
  }[];
}

export const RUN_ARRAYS = ["limit_ms", "v_fwd_ms", "v_rev_ms", "t_fwd_s", "t_rev_s"] as const;
export type RunArray = (typeof RUN_ARRAYS)[number];

/** A run as the sheet shows it: its meta, its arrays on the section grid (NaN where the train never is). */
export interface Run {
  key: string;
  meta: RunResult;
  arrays: Record<RunArray, Float64Array>;
  draft: boolean;
}

/** What the run-time band reads (BandData.run). */
export interface RunBandData {
  saved: Run | null;
  draft: Run | null;
  updating: boolean;
  error: string | null;
  note: string | null;
  /** Both directions, or one. */
  dirs: RunDirs;
  /** The removed stations (no leg times): faint dashed lines. */
  removed: { c: number; name: string }[];
  /** A leg lit from the table: its direction and its arrival's index. */
  lit: { dir: 1 | -1; k: number } | null;
}
export type RunDirs = "both" | "fwd" | "rev";

export function runFromResult(
  key: string,
  meta: RunResult,
  arrays: Partial<Record<string, Float64Array>>,
  draft: boolean,
): Run {
  const n = meta.grid?.n ?? 0;
  const out = {} as Record<RunArray, Float64Array>;
  for (const k of RUN_ARRAYS) out[k] = arrays[k] ?? new Float64Array(n).fill(Number.NaN);
  return { key, meta, arrays: out, draft };
}

export function runFromDraft(d: DraftOut): Run {
  const arrays: Partial<Record<string, Float64Array>> = {};
  for (const k of RUN_ARRAYS) {
    const xs = d.arrays?.[k];
    if (xs) arrays[k] = Float64Array.from(xs, (x) => (x === null ? Number.NaN : x));
  }
  return runFromResult(d.key, d, arrays, true);
}

/** Whether two runs give the same times: every direction's running and trip time and every arrival. */
export function sameRun(a: Run | null, b: Run | null): boolean {
  if (!a || !b || a.meta.directions.length !== b.meta.directions.length) return false;
  const eq = (x: number | null | undefined, y: number | null | undefined) =>
    x === y || (typeof x === "number" && typeof y === "number" && Math.abs(x - y) < 1e-6);
  return a.meta.directions.every((d, i) => {
    const e = b.meta.directions[i];
    if (!e || d.dir !== e.dir || !eq(d.running_s, e.running_s) || !eq(d.trip_s, e.trip_s)) return false;
    if (d.stations.length !== e.stations.length) return false;
    return d.stations.every((s, k) => eq(s.arrive_s, e.stations[k]?.arrive_s));
  });
}

/** The direction of a run, by its sign. */
export const directionOf = (r: Run | null, dir: 1 | -1): RunDirection | null =>
  r?.meta.directions.find((d) => d.dir === dir) ?? null;

// ------------------------------------------------------------------------------------------- the controller

/** The parts of the Api the runs use (a fake in the tests). */
export interface RunsApi {
  compute(
    type: string,
    scope: string,
    view: string,
    priority?: number,
    watchS?: number,
  ): Promise<{ key: string; state: string; job: string | null }>;
  latestResult(type: string, scope: string, view: string): Promise<string | null>;
  result(key: string): Promise<ResultMeta>;
  resultArray(key: string, name: string): Promise<ResultArray>;
  focus(type: string, scope: string, view: string, priority: number): Promise<void>;
  railsimDraft(
    sectionId: string,
    view: View,
    body: { section_input: unknown; type_runs?: unknown[] | null; edit_rev?: number | null },
    signal?: AbortSignal,
  ): Promise<DraftOut>;
}

export interface RunsOptions {
  api: RunsApi;
  /** Something the band or the table shows changed. */
  onChange(): void;
  /** Whether Ben is dragging something that edits the draft (a draft waits for the pointer to come up). */
  dragging(): boolean;
  now?(): number;
}

export interface RunTarget {
  sectionId: string;
  routeId: string;
  view: View;
  token: string;
}

/** A whole solve of the draft that landed: what a draft run is posted with. */
export interface ReadyEdit {
  rev: number;
  /** The SectionInput of the draft (what the sheet's worker solves). */
  input: unknown;
  /** section.solve@1's type_runs of the same edit; null to run on the saved structure. */
  typeRuns: unknown[] | null;
  /** Whether the draft differs from the saved records. */
  dirty: boolean;
}

export interface RunStatus {
  updating: boolean;
  error: string | null;
  note: string | null;
  /** Why this line has no run (no route, not a railsim line); null when it has one. */
  none: string | null;
}

const OK_STATES = new Set(["hit", "ok", "done"]);

const message = (e: unknown): string => String((e as Error)?.message ?? e);

export class Runs {
  saved: Run | null = null;
  draft: Run | null = null;
  attribution: Attribution | null = null;
  /** How many drafts were posted, and how many whole solves were handed in (a test reads them). */
  posts = 0;
  readies = 0;
  private target: RunTarget | null = null;
  private focused = false;
  private gen = 0;
  private jobOn = false;
  private draftOn = false;
  private error: string | null = null;
  private note: string | null = null;
  private none: string | null = null;
  private lastEditAt = Number.NEGATIVE_INFINITY;
  private next: ReadyEdit | null = null;
  private waiting: ReadyEdit | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private dropTimer: ReturnType<typeof setTimeout> | null = null;
  private holdTimer: ReturnType<typeof setTimeout> | null = null;
  private ac: AbortController | null = null;
  private hold: string | null = null;
  private attrWanted = false;
  private loading: string | null = null;
  /** Each read of a saved run is numbered; one that ends after a later one has been shown is dropped. */
  private loadSeq = 0;
  private shownSeq = 0;
  private readonly now: () => number;
  private readonly o: RunsOptions;

  constructor(o: RunsOptions) {
    this.o = o;
    this.now = o.now ?? (() => performance.now());
  }

  status(): RunStatus {
    return {
      updating: this.jobOn || this.draftOn,
      error: this.error,
      note: this.note,
      none: this.none,
    };
  }

  /** The run shown: the draft's while there is one, else the saved one. */
  shown(): Run | null {
    return this.draft ?? this.saved;
  }

  /** What the band draws. Null when the line has no run (the band folds away). */
  band(dirs: RunDirs, removed: RunBandData["removed"], lit: RunBandData["lit"] = null): RunBandData | null {
    if (!this.target || this.none) return null;
    const s = this.status();
    return {
      saved: this.saved,
      draft: this.draft,
      updating: s.updating,
      error: s.error,
      note: s.note,
      dirs,
      removed,
      lit,
    };
  }

  private changed(): void {
    this.o.onChange();
  }

  private clearTimers(): void {
    for (const t of [this.timer, this.dropTimer, this.holdTimer]) if (t) clearTimeout(t);
    this.timer = this.dropTimer = this.holdTimer = null;
  }

  /** Show the run of a section's route in a view (the sheet opened a line, or its view changed). */
  open(t: RunTarget, focused: boolean): void {
    this.close(false);
    this.gen++;
    this.target = t;
    this.focused = focused;
    this.saved = this.draft = this.attribution = null;
    this.error = this.note = this.none = null;
    this.jobOn = this.draftOn = false;
    void this.ask();
  }

  /** Ask the hub for the saved run again (the watch is renewed while the sheet is open). */
  renew(): void {
    if (this.target && !this.none) void this.ask(false);
  }

  /** Read the latest saved run again (the event stream came back: result events sent meanwhile are gone). */
  reload(): void {
    const t = this.target;
    if (!t || this.none) return;
    const gen = this.gen;
    void this.o.api
      .latestResult(RUN_JOB, t.routeId, t.token)
      .then((k) => {
        if (k && gen === this.gen) void this.load(k);
      })
      .catch(() => undefined);
  }

  private async ask(first = true): Promise<void> {
    const t = this.target;
    if (!t) return;
    const gen = this.gen;
    try {
      const r = await this.o.api.compute(RUN_JOB, t.routeId, t.token, runPriority(this.focused), RUN_WATCH_S);
      if (gen !== this.gen) return;
      if (r.key && OK_STATES.has(r.state)) {
        await this.load(r.key);
        return;
      }
      this.jobOn = true;
      this.changed();
      // the previous run shows, dimmed, while the new one is worked out: never blank
      if (first && !this.saved) {
        const k = await this.o.api.latestResult(RUN_JOB, t.routeId, t.token).catch(() => null);
        if (k && gen === this.gen && !this.saved) await this.load(k, true);
      }
    } catch (e) {
      if (gen !== this.gen) return;
      if (e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 409) this.none = message(e);
      else this.error = `run times unavailable: ${message(e)}`;
      this.changed();
    }
  }

  private async load(key: string, older = false): Promise<void> {
    const t = this.target;
    if (!t || this.loading === key) return;
    if (this.saved?.key === key) {
      // the same run again (an early cutoff, a re-save): nothing to read, and nothing is on its way
      if (!older && this.jobOn) {
        this.jobOn = false;
        this.note = null;
        this.changed();
      }
      return;
    }
    const gen = this.gen;
    const seq = ++this.loadSeq;
    this.loading = key;
    try {
      const meta = await this.o.api.result(key);
      if (gen !== this.gen) return;
      if (meta.status === "error") {
        this.jobOn = false;
        this.error = `the run failed: ${String((meta as { error?: unknown }).error ?? "see the job log")}`;
        this.changed();
        return;
      }
      const run = meta.meta as unknown as RunResult;
      const arrays: Partial<Record<string, Float64Array>> = {};
      await Promise.all(
        RUN_ARRAYS.map(async (k) => {
          const a = await this.o.api.resultArray(key, k);
          arrays[k] = toFloat64(a.dtype, a.buffer);
        }),
      );
      // a read that started before the run shown is older than it (the run shown at an open, read late)
      if (gen !== this.gen || seq < this.shownSeq) return;
      this.shownSeq = seq;
      this.saved = runFromResult(key, run, arrays, false);
      if (!older) {
        this.jobOn = false;
        this.error = null;
      }
      // a saved draft gives way to the saved run of the new records
      if (this.hold !== null && key !== this.hold) this.dropDraft();
      this.changed();
    } catch (e) {
      if (gen !== this.gen) return;
      this.error = `run result unavailable: ${message(e)}`;
      this.changed();
    } finally {
      if (this.loading === key) this.loading = null;
    }
  }

  /** The pane has the focus (2) or is open behind another (3). */
  active(on: boolean): void {
    this.focused = on;
    const t = this.target;
    if (t && !this.none) void this.o.api.focus(RUN_JOB, t.routeId, t.token, runPriority(on));
  }

  /** The sheet leaves the line: its goals go to the back (9), a draft in flight is aborted. */
  close(release = true): void {
    const t = this.target;
    if (t && release && !this.none) {
      void this.o.api.focus(RUN_JOB, t.routeId, t.token, CLOSED_PRIORITY);
      if (this.attrWanted) void this.o.api.focus(ATTRIBUTION_JOB, t.routeId, t.token, CLOSED_PRIORITY);
    }
    this.ac?.abort();
    this.ac = null;
    this.next = this.waiting = null;
    this.hold = null;
    this.clearTimers();
    if (release) {
      this.gen++;
      this.target = null;
    }
  }

  /** A hub event: the route's runs, their jobs, and the route's assemble and fit a waiting draft needs. */
  event(ev: HubEvent): void {
    const t = this.target;
    if (!t) return;
    if (ev.type === "result") {
      const d = ev.data;
      if (d.view !== t.token) return;
      if (d.type === RUN_JOB && d.scope === t.routeId) {
        // ok or error: the result's status says which (load reads it)
        void this.load(d.key);
      } else if (d.type === ATTRIBUTION_JOB && d.scope === t.routeId && d.status === "ok") {
        if (this.attrWanted) void this.loadAttribution(d.key);
      } else if (
        d.status === "ok" &&
        ((d.type === ASSEMBLE_JOB && d.scope === t.routeId) || (d.type === HORIZONTAL_JOB && d.scope === t.sectionId))
      ) {
        const w = this.waiting;
        if (w) {
          // through the same gate as every draft: never while Ben drags
          this.waiting = null;
          this.note = null;
          this.next = w;
          this.schedule();
        }
      }
    } else if (ev.type === "job") {
      const d = ev.data;
      if (d.type !== RUN_JOB || d.scope !== t.routeId || (d.view !== undefined && d.view !== t.token)) return;
      if (d.state === "queued" || d.state === "running") {
        this.jobOn = true;
        this.note = d.state === "running" && d.msg && d.msg !== "done" ? `running ${d.msg}` : null;
      } else if (d.state === "failed") {
        this.jobOn = false;
        this.note = null;
        this.error = `the run failed: ${d.msg || "see the job log"}`;
      } else if (d.state === "cancelled" || d.state === "done") {
        // done: the result event follows with the key (read by load); the mark goes either way
        this.jobOn = false;
        this.note = null;
      } else return;
      this.changed();
    }
  }

  // ------------------------------------------------------------------------------------------------ drafts

  /** The draft changed (any step of an edit, a drag's included): a draft in flight is aborted, the one waiting
   * dropped; the next whole solve of the draft brings the next. */
  edited(): void {
    this.lastEditAt = this.now();
    if (this.ac) {
      this.ac.abort();
      this.ac = null;
      this.draftOn = false;
    }
    this.next = this.waiting = null;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    if (this.dropTimer) clearTimeout(this.dropTimer);
    this.dropTimer = null;
  }

  /** The draft is the saved records again (undone to them, discarded or saved): nothing is posted, and the saved
   * run shows once it is clear the draft was not saved (a save keeps the draft until its run arrives). */
  clean(): void {
    this.edited();
    if (!this.draft || this.hold !== null) return;
    this.dropTimer = setTimeout(() => {
      this.dropTimer = null;
      if (this.hold === null) this.dropDraft();
    }, CLEAN_GRACE_MS);
  }

  /** The profile has a new saved revision: the draft shown is now the saved records, and stays until their run
   * arrives over SSE. */
  profileSaved(): void {
    if (!this.draft) return;
    if (sameRun(this.draft, this.saved)) {
      // an edit that leaves the run as it was (a note, a ground point): its saved run is the one shown, and the
      // hub sends no result event for a run that did not change
      this.dropDraft();
      return;
    }
    this.hold = this.saved?.key ?? "";
    if (this.dropTimer) clearTimeout(this.dropTimer);
    this.dropTimer = null;
    if (this.holdTimer) clearTimeout(this.holdTimer);
    this.holdTimer = setTimeout(() => {
      this.holdTimer = null;
      this.dropDraft();
    }, SAVE_HOLD_MS);
  }

  private dropDraft(): void {
    this.hold = null;
    if (this.holdTimer) clearTimeout(this.holdTimer);
    this.holdTimer = null;
    if (!this.draft) return;
    this.draft = null;
    this.changed();
  }

  /** The whole solve of an edit landed. A clean draft posts nothing; a dirty one is posted 300 ms after the last
   * edit, when no drag is on. */
  ready(x: ReadyEdit): void {
    this.readies++;
    if (!this.target || this.none) return;
    if (!x.dirty) {
      this.next = null;
      if (this.timer) clearTimeout(this.timer);
      this.timer = null;
      if (this.draft && this.hold === null && !this.dropTimer) this.clean();
      return;
    }
    this.hold = null;
    this.next = x;
    this.schedule();
  }

  private schedule(): void {
    if (this.timer) clearTimeout(this.timer);
    const wait = Math.max(0, this.lastEditAt + DRAFT_PAUSE_MS - this.now());
    this.timer = setTimeout(() => this.fire(), wait);
  }

  private fire(): void {
    this.timer = null;
    const x = this.next;
    if (!x) return;
    if (this.o.dragging()) {
      // a press held after an edit: look again shortly (the drag's next step drops this one)
      this.timer = setTimeout(() => this.fire(), DRAG_RETRY_MS);
      return;
    }
    if (this.now() < this.lastEditAt + DRAFT_PAUSE_MS) {
      this.schedule();
      return;
    }
    this.next = null;
    void this.post(x);
  }

  private async post(x: ReadyEdit): Promise<void> {
    const t = this.target;
    if (!t) return;
    this.ac?.abort();
    const ac = new AbortController();
    this.ac = ac;
    const gen = this.gen;
    this.posts++;
    this.draftOn = true;
    this.changed();
    try {
      const out = await this.o.api.railsimDraft(
        t.sectionId,
        t.view,
        { section_input: x.input, type_runs: x.typeRuns, edit_rev: x.rev },
        ac.signal,
      );
      if (ac !== this.ac || gen !== this.gen) return;
      this.draft = runFromDraft(out);
      this.error = null;
      this.note = null;
    } catch (e) {
      if (ac !== this.ac || gen !== this.gen || (e as Error)?.name === "AbortError") return;
      if (e instanceof ApiError && e.code === "pending") {
        this.waiting = x;
        this.note = "draft waiting for the route's alignment";
      } else if (!(e instanceof ApiError && e.code === "superseded")) {
        this.error = `the draft run failed: ${message(e)}`;
      }
    } finally {
      if (ac === this.ac) {
        this.ac = null;
        this.draftOn = false;
        this.changed();
      }
    }
  }

  // ------------------------------------------------------------------------------------------- attribution

  /** "Where the time goes" opened or closed: railsim.attribution is asked only while it is open. */
  wantAttribution(on: boolean): void {
    const t = this.target;
    if (!t || this.none || on === this.attrWanted) return;
    this.attrWanted = on;
    if (!on) {
      void this.o.api.focus(ATTRIBUTION_JOB, t.routeId, t.token, CLOSED_PRIORITY);
      return;
    }
    const gen = this.gen;
    void this.o.api
      .compute(ATTRIBUTION_JOB, t.routeId, t.token, ATTRIBUTION_PRIORITY, RUN_WATCH_S)
      .then((r) => {
        if (gen === this.gen && r.key && OK_STATES.has(r.state)) void this.loadAttribution(r.key);
      })
      .catch(() => undefined);
  }

  private async loadAttribution(key: string): Promise<void> {
    const gen = this.gen;
    try {
      const m = await this.o.api.result(key);
      if (gen !== this.gen || m.status !== "ok") return;
      this.attribution = (m.meta ?? null) as unknown as Attribution | null;
      this.changed();
    } catch {
      /* the phase split from the run still shows */
    }
  }
}
