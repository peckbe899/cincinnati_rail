// The design settings (claude/hub_maps/profiles_parity.md, section C: R20; profiles.html 196-208, 543-582, 3737-3766):
// the old page's settings rows, each now a param record (settings.<key>, the registry's value on import:registry,
// Ben's on his layer). A change is a draft on that record, saved with Save like every other edit, and the line's
// whole solve previews it at once. Restore defaults puts every row back to the registry's value (drafts again);
// Reset this line is the level solver's default profile for this line (a proposal in the profile's draft).

import type { Units } from "../../core/units.ts";

/** The Metro's rows (SETTING_ROWS_METRO 581): key, label, unit ("len" follows m / ft), step. */
export const SETTING_ROWS: readonly (readonly [string, string, "len" | "ft" | "‰" | "k", number])[] = [
  ["maxGrade", "Max grade", "‰", 1],
  ["sustainedLen", "Sustained grade: averaged over (shorter is a warning)", "len", 10],
  [
    "riverRoof",
    "Sunk river box roof (Metro; over the box's 4.0 m to the roof underside; RER: the envelope)",
    "len",
    0.1,
  ],
  ["riverSink", "Sunk river box: roof at most this far below the bed", "len", 0.1],
  ["riverRise", "Sunk river box: roof at most this far above the bed", "len", 0.1],
  ["riverFlatTol", "River bottom: bed within this of the lowest bed", "len", 0.1],
  ["riverClearWater", "Navigable channel: clear water at normal pool", "len", 0.01],
  ["riverCap", "Clay, canopy and riprap over a raised roof", "len", 0.1],
  ["roadClearHighway", "Clearance over a highway (street surface to the structure underside)", "len", 0.1],
  ["roadClearMajor", "Clearance over a major road", "len", 0.1],
  ["roadClearMinor", "Clearance over a minor street", "len", 0.1],
  ["platform", "Platform length", "len", 0.1],
  ["defDepth", "Default rail depth at stations", "len", 0.1],
  ["elevAbove", "Elevated when rail is above ground by", "len", 0.1],
  ["coverBelow", "Covered when rail is below ground by", "len", 0.1],
  ["deepBelow", "Deep tunnel (outside canon) when rail is below ground by", "len", 0.5],
  ["shallowMax", "Flag canon-shallow stretches deeper than", "len", 0.5],
  ["deckDepth", "Viaduct deck below rail (over a crossing)", "len", 0.1],
  ["poolFt", "Ohio normal pool (Markland)", "ft", 0.1],
  ["vcRadius", "Vertical curve radius", "len", 100],
  ["vcMinLen", "Min vertical curve length", "len", 0.5],
  ["drainMin", "Min tunnel grade for drainage", "‰", 0.5],
  ["stationMaxGrade", "Max platform grade (RER; Metro by era)", "‰", 0.5],
  ["curveK", "Curve compensation, k in k / R per mille", "k", 50],
  ["groundMax", "Drawn ground: steepest grade (a street)", "‰", 5],
  ["groundWarn", "Drawn ground: sustained grade warning past", "‰", 5],
  ["groundSustain", "Drawn ground: sustained over", "len", 10],
  [
    "fillSlope",
    "Drawn ground: steepest side slope at a line's ends, back to the ground (an embankment; 1 in 2 is 500)",
    "‰",
    50,
  ],
];

const FT = 0.3048;

/** One row's param: its value in the stored unit (metres for lengths and the pool), whether Ben's draft changed it,
 * whether it is this line's own (a route or section scope: read only here, as the old page's line overlay). */
export interface SettingParam {
  value: number;
  changed: boolean;
  own: boolean;
  /** the registry's value, when the view could read it */
  registry: number | null;
}

export interface SettingsCtx {
  units: Units;
  params: Map<string, SettingParam>;
  canEdit: boolean;
  readOnly: string | null;
  edit(key: string, value: number): void;
  restoreDefaults(): void;
  resetLine(): void;
  resetArmed: boolean;
}

/** The value a row shows: lengths in the display unit, the pool in feet as the old page showed it. */
export function shown(unit: string, value: number, units: Units): number {
  if (unit === "len") return units.toDisplay(value, "m");
  if (unit === "ft") return value / FT;
  return value;
}

/** What a typed value stores. */
export function stored(unit: string, typed: number, units: Units): number {
  if (unit === "len") return units.fromDisplay(typed, "m");
  if (unit === "ft") return typed * FT;
  return typed;
}

export function buildSettings(c: SettingsCtx): HTMLElement {
  const root = document.createElement("div");
  root.className = "sheet-pop";
  root.dataset.testid = "settings-panel";
  root.setAttribute("role", "dialog");
  root.setAttribute("aria-label", "Design settings");
  const h = document.createElement("h3");
  h.textContent = "Design settings";
  root.append(h);
  const kv = document.createElement("dl");
  kv.className = "lp-kv";
  for (const [k, label, unit, step] of SETTING_ROWS) {
    const p = c.params.get(k);
    const u = unit === "len" ? c.units.label("m") : unit;
    const dt = document.createElement("dt");
    const lab = document.createElement("label");
    lab.textContent = `${label} (${u})${p?.own ? " · this line" : ""}`;
    lab.htmlFor = `set_${k}`;
    dt.append(lab);
    const dd = document.createElement("dd");
    const i = document.createElement("input");
    i.type = "number";
    i.id = `set_${k}`;
    i.step = String(step);
    i.dataset.key = k;
    i.dataset.testid = `setting-${k}`;
    i.value = p ? shown(unit, p.value, c.units).toFixed(unit === "len" || unit === "ft" ? 1 : 0) : "";
    i.disabled = !p || !c.canEdit || p.own;
    i.title = p
      ? `param settings.${k}${p.registry !== null ? `, registry ${shown(unit, p.registry, c.units).toFixed(2)}` : ""}${p.changed ? " (changed, not saved)" : ""}`
      : `no param settings.${k} in this view`;
    if (p?.changed) dt.classList.add("changed");
    i.addEventListener("change", () => {
      const v = Number.parseFloat(i.value);
      if (!Number.isFinite(v) || v <= 0) return;
      c.edit(k, stored(unit, v, c.units));
    });
    dd.append(i);
    kv.append(dt, dd);
  }
  root.append(kv);
  const note = document.createElement("p");
  note.className = "lp-hint";
  note.textContent =
    "The founding sections of Lines 1 to 6 take their structure from canon (tracker 2D and your rulings). Elsewhere the deep-tube threshold decides. Painted stretches override both; painted cut and cover fills the ground over the box. Settings apply to every Metro line: each is a param record, changed in your draft and saved with Save.";
  if (c.readOnly) {
    const ro = document.createElement("p");
    ro.className = "lp-hint";
    ro.textContent = c.readOnly;
    root.append(ro);
  }
  root.append(note);
  const g = document.createElement("div");
  g.className = "lp-buttons";
  const d = document.createElement("button");
  d.type = "button";
  d.textContent = "Restore defaults";
  d.title = "Every setting back to the registry's value (in your draft: Save keeps it)";
  d.dataset.testid = "settings-defaults";
  d.disabled = !c.canEdit;
  d.onclick = c.restoreDefaults;
  const r = document.createElement("button");
  r.type = "button";
  r.textContent = c.resetArmed ? "Click again to reset" : "Reset this line";
  r.title =
    "This line back to the level solver's default profile: every station back, default levels, no paints, slides or drawn ground (a preview in your draft)";
  r.dataset.testid = "settings-reset-line";
  r.disabled = !c.canEdit;
  r.onclick = c.resetLine;
  g.append(d, r);
  // the buttons under the heading, where no toast covers them
  h.after(g);
  return root;
}
