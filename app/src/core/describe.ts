// Fields and values in Ben's terms: "PVI 10 level", "Bond Hill level", "scale". Used by the 412 banner (what each
// side changed), the save and undo notices, and the labels of undo entries.

import type { JsonPatch } from "../api/types.ts";
import { parsePointer } from "./jsonpatch.ts";
import { ULID_RE } from "./names.ts";
import type { Units } from "./units.ts";

/** The profile fields keyed by platform id, and what each holds. */
const BY_PLATFORM: Record<string, string> = {
  st: "level",
  sg: "grade",
  so: "slide",
  stt: "structure",
  mode: "mode",
};

const words = (t: string) => t.replace(/_/g, " ");

/**
 * A pointer of a record body as Ben would name it. name() turns an id inside the pointer (a platform id key) into a
 * name.
 */
export function fieldLabel(kind: string, path: string, name: (id: string) => string = (id) => id): string {
  const t = parsePointer(path);
  if (t[0] === "geom") return "geometry";
  const d = t[0] === "data" ? t.slice(1) : t;
  if (d.length === 0) return "every field";
  const idx = (s: string | undefined) => (s !== undefined && /^\d+$/.test(s) ? String(Number(s) + 1) : s);
  if (kind === "profile") {
    const [f, a, b] = d as [string, string | undefined, string | undefined];
    if (f === "pvi") {
      if (a === undefined) return "the PVI list";
      if (b === undefined) return `PVI ${idx(a)}`;
      return `PVI ${idx(a)} ${b === "0" || b === "c_m" || b === "c" ? "chainage" : "level"}`;
    }
    const what = BY_PLATFORM[f];
    if (what) return a === undefined ? `every station ${what}` : `${name(a)} ${what}`;
    if (f === "del") return a === undefined ? "the platforms left out" : `platform left out ${idx(a)}`;
    if (f === "frame" && a === "point_c" && b !== undefined) return `${name(b)} frame chainage`;
  }
  return d.map((s) => (ULID_RE.test(s) ? name(s) : /^\d+$/.test(s) ? idx(s) : words(s))).join(" ");
}

/** Whether a field holds a length in metres (to show it in the display unit). */
function isLength(kind: string, path: string): boolean {
  const t = parsePointer(path);
  if (kind === "profile") {
    if (t[1] === "pvi" && t.length === 4) return true;
    if ((t[1] === "st" || t[1] === "so") && t.length === 3) return true;
  }
  return /(^|_)(c|m|c_m|z_m|length_m|step_m|level)$/.test(t[t.length - 1] ?? "");
}

/** A value for a sentence: a number in the display unit, a list or object by its size, "not set" when absent. */
export function valueText(kind: string, path: string, v: unknown, units: Units): string {
  if (v === undefined) return "not set";
  if (v === null) return kind === "profile" && parsePointer(path)[1] === "st" ? "design" : "none";
  if (typeof v === "number") {
    if (isLength(kind, path)) return `${units.format(v, "m")} ${units.label("m")}`;
    return String(Number(v.toPrecision(12)));
  }
  if (typeof v === "string") return `"${v.length > 40 ? `${v.slice(0, 39)}…` : v}"`;
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (Array.isArray(v)) return `${v.length} item${v.length === 1 ? "" : "s"}`;
  const n = Object.keys(v as object).length;
  return `${n} entr${n === 1 ? "y" : "ies"}`;
}

/** A short label for a patch: its first fields, as an undo entry and a save notice name it. */
export function patchLabel(kind: string, ops: JsonPatch, name?: (id: string) => string): string {
  const labels = [...new Set(ops.map((o) => fieldLabel(kind, o.path, name)))];
  if (labels.length === 0) return "no change";
  if (labels.length <= 2) return labels.join(" and ");
  return `${labels.slice(0, 2).join(", ")} and ${labels.length - 2} more`;
}

/** A layer in plain words: "main", "try", "the old hub's data", "the line files import". */
export function layerText(slug: string): string {
  if (slug === "legacy:old_hub" || slug.startsWith("legacy:")) return "the old hub's data";
  if (slug === "import:profiles") return "the Metro line files";
  if (slug === "import:registry") return "the rules registry";
  if (slug.startsWith("import:")) return `the ${words(slug.slice("import:".length))} import`;
  return slug;
}

/** Where a revision lives, as a phrase: "on main", "on try", "from the old hub's data". */
export function layerPhrase(slug: string): string {
  return slug.includes(":") ? `from ${layerText(slug)}` : `on ${slug}`;
}

/** Who wrote a revision in plain words: "ben", "the line files import". */
export function actorText(by: string): string {
  if (by === "import:profile_lines") return "the Metro line files import";
  if (by === "import:old_hub") return "the old hub import";
  if (by.startsWith("import:")) return `the ${words(by.slice("import:".length))} import`;
  return by;
}

/** A stored UTC time as Ben's local date and time. */
export function localTime(iso: string): string {
  const t = new Date(iso);
  return Number.isNaN(t.getTime()) ? iso : t.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
