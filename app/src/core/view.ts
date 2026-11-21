// The view every read runs in: (layer, year, month, timeline), the TypeScript twin of region/core/view.py.
// token() and query() give the same strings as the Python View, so cache keys and API queries agree.

export type Timeline = "canon" | "real";

export interface View {
  layer: string;
  year: number | null;
  month: number | null;
  timeline: Timeline;
}

/** A layer slug, as region.core.view.LAYER_RE. */
export const LAYER_RE = /^[a-z][a-z0-9_-]{0,63}(:[a-z0-9][a-z0-9_.-]{0,63})?$/;

export const DEFAULT_VIEW: View = Object.freeze({ layer: "main", year: null, month: null, timeline: "canon" });

/** A view with defaults filled in. Throws on a value the server would refuse. */
export function makeView(v: Partial<View> = {}): View {
  const view: View = {
    layer: v.layer ?? "main",
    year: v.year ?? null,
    month: v.year == null ? null : (v.month ?? null),
    timeline: v.timeline ?? "canon",
  };
  if (!LAYER_RE.test(view.layer)) throw new Error(`${view.layer} is not a layer slug`);
  if (view.year !== null && (!Number.isInteger(view.year) || view.year < -9999 || view.year > 9999)) {
    throw new Error(`${view.year} is not a year from -9999 to 9999`);
  }
  if (view.month !== null && (!Number.isInteger(view.month) || view.month < 1 || view.month > 12)) {
    throw new Error(`${view.month} is not a month from 1 to 12`);
  }
  if (view.timeline !== "canon" && view.timeline !== "real") throw new Error(`${view.timeline} is not a timeline`);
  return view;
}

/** "main|-|canon", "try|1931|real", "main|1931-09|canon": the same text as View.token() in Python. */
export function viewToken(v: View): string {
  let when = "-";
  if (v.year !== null) when = v.month === null ? String(v.year) : `${v.year}-${String(v.month).padStart(2, "0")}`;
  return `${v.layer}|${when}|${v.timeline}`;
}

/** The HTTP query of a view (defaults left out), as View.query() in Python. */
export function viewQuery(v: View): Record<string, string> {
  const q: Record<string, string> = { layer: v.layer };
  if (v.year !== null) q.year = String(v.year);
  if (v.month !== null) q.month = String(v.month);
  if (v.timeline !== "canon") q.tl = v.timeline;
  return q;
}

/** The month index of the view's instant (end of its year or month), or null at the present. */
export function viewInstant(v: View): number | null {
  if (v.year === null) return null;
  return v.month === null ? v.year * 12 + 11 : v.year * 12 + v.month - 1;
}

/** Whether a thing with these month intervals is open at the instant (the rule of region.core.view.is_open). */
export function isOpen(
  instant: number | null,
  opened: [number, number] | null,
  closed: [number, number] | null,
): boolean {
  if (instant === null) return closed === null;
  if (opened === null) return false;
  if (opened[0] > instant) return false;
  return closed === null || closed[0] > instant;
}
