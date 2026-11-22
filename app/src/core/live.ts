// The live hub as the app sees it (region/live): the summary the Sources chip shows, every watched source's last
// state, and the pending marks of the sections being imported or re-solved. The sources plugin feeds it from GET
// /live and the source, live and pending events; panes read it (the line sheet's "re-solving" mark).

import type { LiveStatus, LiveSummary, PendingMark, SourceEvent } from "../api/types.ts";

export class LiveBoard {
  enabled = true;
  summary: LiveSummary = { paused: false, pending: 0, updated: null };
  readonly sources = new Map<string, SourceEvent>();
  marks: PendingMark[] = [];
  history: { at: string; source: string; label: string; text: string }[] = [];
  private subs = new Set<() => void>();

  reset(s: LiveStatus): void {
    this.enabled = s.enabled !== false;
    this.summary = { paused: !!s.paused, pending: s.pending ?? 0, updated: s.updated ?? null };
    this.sources.clear();
    for (const src of s.sources ?? []) this.sources.set(src.source, src);
    this.marks = s.marks ?? [];
    this.history = s.history ?? [];
    this.emit();
  }

  source(ev: SourceEvent): void {
    this.sources.set(ev.source, { ...this.sources.get(ev.source), ...ev });
    if (ev.live) this.summary = ev.live;
    if (ev.toast && ev.text) {
      this.history.unshift({
        at: ev.at ?? new Date().toISOString(),
        source: ev.source,
        label: ev.label,
        text: ev.text,
      });
      this.history.length = Math.min(this.history.length, 50);
    }
    this.emit();
  }

  setSummary(s: LiveSummary): void {
    this.summary = s;
    this.emit();
  }

  setMarks(items: PendingMark[]): void {
    this.marks = items;
    this.emit();
  }

  /** The pending mark of a section in a view: "importing", "re-solving", "queued", or null. */
  pendingFor(scope: string, view: string): string | null {
    let found: string | null = null;
    for (const m of this.marks) {
      if (m.scope !== scope) continue;
      if (m.type === "import") return "importing";
      if (m.view === view) found = m.state === "queued" ? (found ?? "queued") : "re-solving";
    }
    return found;
  }

  subscribe(fn: () => void): () => void {
    this.subs.add(fn);
    return () => this.subs.delete(fn);
  }

  private emit(): void {
    for (const fn of [...this.subs]) fn();
  }
}

export const liveBoard = new LiveBoard();

/** A clock time in Ben's local zone ("14:02"), or "" for none. */
export function clockText(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** The Sources chip's text: "live", "live: 2 pending", "live: paused, 1 waiting", "live: off". */
export function chipText(b: Pick<LiveBoard, "enabled" | "summary">): string {
  if (!b.enabled) return "live: off";
  const s = b.summary;
  let text = s.paused ? "live: paused" : "live";
  if (s.pending) text += s.paused ? `, ${s.pending} waiting` : `: ${s.pending} pending`;
  const at = clockText(s.updated);
  return at ? `${text}, updated ${at}` : text;
}

/** A state in Ben's words for the sources pane. */
export function stateText(state: string): string {
  return (
    (
      {
        idle: "up to date",
        changing: "changing",
        waiting: "waiting for another program",
        importing: "importing",
        applied: "taken in",
        review: "taken in, some in Review",
        held: "held (you undid it)",
        error: "could not be read",
      } as Record<string, string>
    )[state] ?? state
  );
}
