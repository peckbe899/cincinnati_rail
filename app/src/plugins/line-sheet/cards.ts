// The selection cards besides the station's (claude/hub_maps/profiles_parity.md, section C: R49, R50, R51): the bend
// point card (chainage, rail level, rail below ground, structure, grades meeting, vertical curve, rail at the bend,
// Remove; updateSelCard 3110-3133), the ground point card (chainage, ground level, over the ground below, grades
// meeting, rail under it, the line, Remove point and Remove ground line; 3092-3108), and the editing help card the
// old page showed with nothing selected (3022-3024), behind the "?" too. Each field's change is one draft edit.

import type { Units } from "../../core/units.ts";
import { fmtCh, fmtG, typeLabel } from "./drawing.ts";

const el = <K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Partial<HTMLElementTagNameMap[K]> & { cls?: string; testid?: string } = {},
  ...kids: (Node | string | null)[]
): HTMLElementTagNameMap[K] => {
  const { cls, testid, ...rest } = props;
  const e = Object.assign(document.createElement(tag), rest);
  if (cls) e.className = cls;
  if (testid) e.dataset.testid = testid;
  for (const k of kids) if (k !== null) e.append(k);
  return e;
};

/** A row with a number field: its value in the display unit, a change applies it (Enter too). */
function numRow(
  kv: HTMLElement,
  label: string,
  value: number,
  digits: number,
  step: number,
  disabled: boolean,
  apply: (v: number) => void,
  testid: string,
): void {
  const i = el("input", { type: "number", step: String(step), value: value.toFixed(digits), disabled, testid });
  i.setAttribute("aria-label", label);
  i.addEventListener("change", () => {
    const v = Number.parseFloat(i.value);
    if (Number.isFinite(v)) apply(v);
  });
  kv.append(el("dt", {}, el("label", { textContent: label })), el("dd", {}, i));
}

const textRow = (kv: HTMLElement, label: string, text: string, testid?: string) =>
  kv.append(el("dt", { textContent: label }), el("dd", { textContent: text, ...(testid ? { testid } : {}) }));

export interface BendCtx {
  units: Units;
  index: number;
  c: number;
  z: number;
  /** the ground (the pool over a river) at the bend, null where none */
  surface: number | null;
  /** the structure type at the bend, null before the whole solve */
  type: string | null;
  gIn: number | null;
  gOut: number | null;
  /** the vertical curve: its length, whether the design shortened it */
  curve: { L: number; short: boolean } | null;
  railAt: number | null;
  canEdit: boolean;
  readOnly: string | null;
  set(c: number, z: number): void;
  remove(): void;
}

/** The bend point card (3110-3133). */
export function bendCard(b: BendCtx): HTMLElement {
  const u = b.units;
  const lu = u.label("m");
  const toU = (m: number) => u.toDisplay(m, "m");
  const fromU = (v: number) => u.fromDisplay(v, "m");
  const root = el("div", { cls: "sp sel-card", testid: "bend-card" });
  root.append(el("h4", { textContent: "Bend point" }), el("div", { cls: "sel-title", textContent: fmtCh(b.c) }));
  const kv = el("dl", { cls: "lp-kv" });
  const ro = !b.canEdit;
  numRow(kv, "Chainage (m)", b.c, 0, 1, ro, (v) => b.set(v, b.z), "bend-c");
  numRow(kv, `Rail level (${lu})`, toU(b.z), 2, 0.1, ro, (v) => b.set(b.c, Math.round(fromU(v) * 100) / 100), "bend-z");
  if (b.surface !== null)
    numRow(
      kv,
      `Rail below ground (${lu})`,
      toU(b.surface - b.z),
      2,
      0.1,
      ro,
      (v) => b.set(b.c, Math.round(((b.surface as number) - fromU(v)) * 100) / 100),
      "bend-depth",
    );
  textRow(kv, "Structure", b.type ? typeLabel(b.type) : "–");
  textRow(
    kv,
    "Grades meeting",
    b.gIn === null || b.gOut === null ? "—" : `${fmtG(b.gIn)} / ${fmtG(b.gOut)}`,
    "bend-grades",
  );
  textRow(
    kv,
    "Vertical curve",
    !b.curve
      ? "—"
      : b.curve.L > 1e-6
        ? `${b.curve.L.toFixed(0)} m, ${fmtCh(b.c - b.curve.L / 2)} to ${fmtCh(b.c + b.curve.L / 2)}${b.curve.short ? " (shortened)" : ""}`
        : "none (no change of grade)",
    "bend-curve",
  );
  textRow(kv, "Rail at the bend", b.railAt === null ? "–" : `${u.format(b.railAt, "m", 2)} ${lu}`);
  root.append(kv);
  if (b.readOnly) root.append(el("p", { cls: "sp-hint", textContent: b.readOnly }));
  const rm = el("button", { type: "button", textContent: "Remove bend point", disabled: ro, testid: "bend-remove" });
  rm.onclick = b.remove;
  root.append(el("div", { cls: "lp-buttons" }, rm));
  return root;
}

export interface GroundCtx {
  units: Units;
  c: number;
  z: number;
  end: boolean;
  /** the ground below (the surveyed ground with the Deck's re-grades) at the point */
  below: number | null;
  gIn: number | null;
  gOut: number | null;
  rail: number | null;
  from: number;
  to: number;
  points: number;
  canEdit: boolean;
  set(c: number, z: number | null): void;
  remove(all: boolean): void;
}

/** The ground point card (3092-3108). */
export function groundCard(g: GroundCtx): HTMLElement {
  const u = g.units;
  const lu = u.label("m");
  const toU = (m: number) => u.toDisplay(m, "m");
  const fromU = (v: number) => u.fromDisplay(v, "m");
  const root = el("div", { cls: "sp sel-card", testid: "ground-card" });
  root.append(el("h4", { textContent: "Ground point" }), el("div", { cls: "sel-title", textContent: fmtCh(g.c) }));
  const kv = el("dl", { cls: "lp-kv" });
  const ro = !g.canEdit;
  numRow(kv, "Chainage (m)", g.c, 0, 1, ro, (v) => g.set(v, null), "ground-c");
  numRow(kv, `Ground level (${lu})`, toU(g.z), 2, 0.1, ro || g.end, (v) => g.set(g.c, fromU(v)), "ground-z");
  const over = g.below === null ? null : g.z - g.below;
  textRow(
    kv,
    "Over the ground below",
    over === null
      ? "–"
      : `${u.format(over, "m", 2)} ${lu}${Math.abs(over) > 0.005 ? (over > 0 ? " (fill)" : " (cut)") : ""}`,
    "ground-over",
  );
  textRow(kv, "Grades meeting", `${g.gIn === null ? "—" : fmtG(g.gIn)} / ${g.gOut === null ? "—" : fmtG(g.gOut)}`);
  textRow(kv, "Rail under it", g.rail === null ? "–" : `${u.format(g.z - g.rail, "m", 2)} ${lu} down`);
  textRow(kv, "The line", `${fmtCh(g.from)} to ${fmtCh(g.to)}, ${g.points} points`);
  root.append(kv);
  if (g.end)
    root.append(
      el("p", {
        cls: "sp-hint",
        textContent:
          "An end point stays on the ground below (the surveyed ground with the Deck's re-grades); move it along the line.",
      }),
    );
  const a = el("button", { type: "button", textContent: "Remove point", disabled: ro, testid: "ground-remove" });
  a.onclick = () => g.remove(false);
  const b = el("button", {
    type: "button",
    textContent: "Remove ground line",
    disabled: ro,
    testid: "ground-remove-line",
  });
  b.onclick = () => g.remove(true);
  root.append(el("div", { cls: "lp-buttons" }, a, b));
  return root;
}

/** The editing help (the old card with nothing selected, 3022-3024), in plain words with the keys. */
export function helpCard(): HTMLElement {
  const root = el("div", { cls: "sp sp-empty", testid: "editing-help" });
  root.innerHTML =
    "<h4>Editing</h4>" +
    "<p class=sp-hint><b>Move</b> (M): drag a station bar up or down to set its rail level (Shift: 1 m steps); Alt + drag slides it along its drawn point. Double-click the track to add a bend point, then drag it. Click a station's bar, name or row to see and set everything about it.</p>" +
    "<p class=sp-hint><b>Paint</b> (P): choose a structure and drag along the line to mark a stretch by hand; <b>Auto</b> clears it. Painted <b>Cut &amp; cover</b>, <b>Shield tunnel</b> or <b>Deep bore (TBM)</b> keeps the structure where it is (short of cover is a warning, with Propose fill); a paint must make sense there, else it is hatched as unbuildable with Lower, Raise and Clear in the issues. <b>Shaft</b>: click where a method may change. <b>Twin tubes</b> and <b>Double-track bore</b> set the tube form of a bored stretch; <b>Auto tubes</b> clears it.</p>" +
    "<p class=sp-hint><b>Ground</b> (G): draws the regraded ground like the rail. Double-click to start a line (its ends on the ground) or add a point to one, drag the points, <kbd>Del</kbd> removes one. <b>Propose fill</b> (on a cover issue, or a painted box or tube in the paint review) draws the fill a structure needs as a line to edit.</p>" +
    "<p class=sp-hint>Every fix (Lower, Raise, Propose fill, Clear, Ease, Solve levels with crossings, Fix unbuildable, Reset this line) is a preview in your draft: <kbd>Ctrl Z</kbd> takes back each step, <b>Discard</b> drops them all, <kbd>Ctrl S</kbd> saves.</p>" +
    "<p class=sp-hint><kbd>scroll</kbd> zoom · <kbd>drag</kbd> pan · <kbd>+</kbd> <kbd>−</kbd> zoom · <kbd>F</kbd> whole line · <kbd>↑</kbd><kbd>↓</kbd> nudge 0.1 (<kbd>Shift</kbd> 1) · <kbd>←</kbd><kbd>→</kbd> move a bend or ground point 2 m (<kbd>Shift</kbd> 10) · <kbd>Del</kbd> remove a bend or ground point · <kbd>[</kbd> <kbd>]</kbd> step through the stations · <kbd>E</kbd> ease · <kbd>Esc</kbd> clear · <kbd>Ctrl Z</kbd> undo · <kbd>Ctrl Shift Z</kbd> redo</p>";
  return root;
}
