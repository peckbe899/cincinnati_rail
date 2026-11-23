// The station panel (claude/hub_maps/profiles_parity.md A.3): everything the old Profiles page's station card showed
// and set, in groups, each row with its value, where the value comes from (Ben, the old hub, the line file, a rule,
// a param) and the rule behind it. Every edit goes into the profile's draft (the side into the platform's), so the
// sheet re-solves at once, a changed row says what it was, and nothing is saved until Save (Ctrl+S, or Enter in a
// field). The panel is built from station.facts@1 of the draft and the draft itself; it holds no state of its own.

import type { StationFact, StationInput } from "@cr/engine/contract";
import type { Units } from "../../core/units.ts";
import {
  curveWord,
  flagText,
  fmtCh,
  fmtG,
  fmtGap,
  fmtR,
  fmtZ,
  hallRoomText,
  openingText,
  SEV_COLOURS,
  slideText,
  streetText,
  typeColour,
  typeLabel,
  typeReason,
} from "./drawing.ts";
import { ACCESS, nudgeLevel, type ProfileData, type SelectableType, STT_LABELS, sttSameAsPaint } from "./model.ts";

/** What a row's value comes from, in Ben's words, and the rule or param behind it. */
export interface Source {
  text: string;
  rule?: string;
  title?: string;
}

export interface PanelCtx {
  units: Units;
  pid: string;
  name: string;
  /** "Line 3" */
  line: string;
  /** The station's place among the live ones, for Prev and Next. */
  index: number;
  count: number;
  half: number;
  /** station.facts@1 of the draft, null until it has run (or when the engine is not there). */
  fact: StationFact | null;
  params: StationInput["params"] | null;
  /** "settings" on the Metro, "settings_rer" on the RER: where the platform length and depths are. */
  paramPrefix: string;
  metro: boolean;
  /** The draft's values and the saved record's, for the sources and the "was" notes. */
  draft: ProfileData;
  saved: ProfileData;
  /** The draft or record before the design was laid in (design.ts), when the sheet draws one Ben's profile does
   * not hold: a value that is the design's says so ("default design, not saved"). */
  held?: ProfileData;
  /** Who wrote the saved profile ("import:old_hub", "ben"). */
  savedBy: string;
  /** The drawn point (the stop's chainage) and the platform centre now. */
  point: number;
  centre: number;
  /** The rail at the centre now (the station's own level, or the design's when it has none). */
  rail: number | null;
  ground: number | null;
  groundDem: number | null;
  gradeIn: number | null;
  gradeOut: number | null;
  side: { now: "side" | "island"; was: "side" | "island"; source: string };
  canEdit: boolean;
  canEditSide: boolean;
  /** Why the inputs are read only, when they are. */
  readOnly: string | null;
  /** The rule texts by id, for the hover on a rule (rules/registry.yaml), when known. */
  ruleText?(id: string): string | undefined;
  act: {
    level(z: number | null, step: string): void;
    depth(d: number, step: string): void;
    grade(permille: number, step: string): void;
    slide(so: number, step: string): void;
    ease(): void;
    remove(): void;
    type(t: SelectableType | null): void;
    access(t: string | null): void;
    gapfill(on: boolean): void;
    side(s: "side" | "island"): void;
    prev(): void;
    next(): void;
    close(): void;
    save(): void;
    openParam(path: string): void;
    select(pid: string): void;
  };
}

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

/** The current visit of each field (pid:field), so a run of keystrokes is one undo step. */
const visits = new Map<string, string>();
let visitSeq = 0;
let restoring = false;

const has = (o: unknown, k: string): boolean => !!o && typeof o === "object" && Object.hasOwn(o as object, k);
const val = (o: unknown, k: string): unknown => (has(o, k) ? (o as Record<string, unknown>)[k] : undefined);

/** Who a saved value is from: the old hub's import, the line file, else Ben. */
export function byWord(by: string): string {
  if (by === "import:old_hub") return "old hub";
  if (by === "import:profile_lines") return "line file";
  if (by.startsWith("import:")) return by.slice("import:".length).replace(/_/g, " ");
  return "Ben";
}

/** Where one of the profile's station values comes from: Ben's draft, the saved record, or the rules. */
export function fieldSource(
  draft: ProfileData,
  saved: ProfileData,
  savedBy: string,
  field: string,
  pid: string,
  rule?: string,
  held?: ProfileData,
): Source & { changed: boolean; was: unknown } {
  const read = (d: ProfileData) =>
    field === "gapfill" || field === "del" ? (d[field] as string[] | undefined)?.includes(pid) : val(d[field], pid);
  const now = read(draft);
  const was = read(saved);
  // a value of the design the sheet draws where the profile holds none (design.ts): not Ben's, and not saved
  if (held && JSON.stringify(now ?? null) !== JSON.stringify(read(held) ?? null))
    return { text: "default design, not saved", rule, changed: false, was };
  const changed = JSON.stringify(now ?? null) !== JSON.stringify(was ?? null);
  if (changed) return { text: "Ben, not saved", rule, changed, was };
  if (was !== undefined && was !== false) return { text: byWord(savedBy), rule, changed, was };
  return { text: rule ? "rule" : "not set", rule, changed, was };
}

/** Build the panel for one station. Returns the element; the pane puts it in place of the old card. */
export function buildPanel(c: PanelCtx): HTMLElement {
  const u = c.units;
  const ul = u.length;
  const f = c.fact;
  const root = el("div", { cls: "sp", testid: "station-panel" });
  const ro = !c.canEdit;

  // ---- the head: type square, name, line, Prev / Next, Remove, close
  const sq = el("span", { cls: "sp-square", title: typeLabel(f?.type) });
  sq.style.background = typeColour(f?.type);
  const prev = el("button", { type: "button", textContent: "‹", title: "The previous station ([)" });
  prev.setAttribute("aria-label", "Previous station");
  prev.disabled = c.index <= 0;
  prev.onclick = c.act.prev;
  const next = el("button", { type: "button", textContent: "›", title: "The next station (])" });
  next.setAttribute("aria-label", "Next station");
  next.disabled = c.index >= c.count - 1;
  next.onclick = c.act.next;
  const remove = el("button", {
    type: "button",
    textContent: "Remove",
    title:
      "Remove station: leave this station out of the profile; restore it from the Removed list. Delete, twice, does the same.",
    testid: "sp-remove",
  });
  remove.disabled = ro;
  remove.onclick = () => {
    if (remove.dataset.armed) {
      c.act.remove();
      return;
    }
    remove.dataset.armed = "1";
    remove.textContent = "Click again to remove";
    setTimeout(() => {
      if (remove.isConnected) {
        delete remove.dataset.armed;
        remove.textContent = "Remove";
      }
    }, 4000);
  };
  const close = el("button", { type: "button", textContent: "×", title: "Clear the selection (Esc)" });
  close.onclick = c.act.close;
  root.append(
    el(
      "div",
      { cls: "sp-head" },
      sq,
      el("strong", { textContent: c.name, testid: "station-card-name" }),
      el("span", { cls: "muted sp-line", textContent: `${c.line}, station ${c.index + 1} of ${c.count}` }),
      el("span", { cls: "spacer" }),
      prev,
      next,
      remove,
      close,
    ),
  );
  if (c.readOnly) root.append(el("div", { cls: "sp-note", textContent: c.readOnly }));
  const groups = el("div", { cls: "sp-groups" });
  root.append(groups);

  // Each group folds (its heading is a summary with a one-line digest of what is in it); Ben's choice is kept per
  // group across stations and visits. The groups Ben uses most come first and open; the rest start folded, so the
  // panel fits a 1,000 px window without scrolling.
  const bodies = new Map<string, HTMLElement>();
  const digests = new Map<string, HTMLElement>();
  const group = (title: string, id: string) => {
    const digest = el("span", { cls: "sp-digest" });
    digests.set(id, digest);
    const d = el(
      "details",
      { cls: "sp-group", testid: `sp-group-${id}` },
      el("summary", {}, el("h4", { textContent: title }), digest),
    );
    d.open = groupOpen(id, f);
    // the toggle event also follows the open set just above (it is sent later): only Ben's own clicks are kept
    let shown = d.open;
    d.addEventListener("toggle", () => {
      if (d.open === shown) return;
      shown = d.open;
      keepGroup(id, d.open);
    });
    const body = el("div", { cls: "sp-body" });
    d.append(body);
    groups.append(d);
    bodies.set(id, body);
    return body;
  };
  const digest = (id: string, text: string) => {
    const d = digests.get(id);
    if (d) d.textContent = text;
  };
  const sourceEl = (s: Source | null) => {
    if (!s) return el("span", { cls: "sp-src" });
    const span = el("span", { cls: "sp-src", textContent: s.text });
    if (s.rule) span.append(el("span", { cls: "sp-rule", textContent: s.rule }));
    span.title = s.title ?? (s.rule ? (c.ruleText?.(s.rule) ?? `rule ${s.rule}`) : s.text);
    return span;
  };
  const row = (
    g: HTMLElement,
    label: string,
    value: Node | string,
    src: Source | null,
    testid: string,
    was?: string | null,
  ) => {
    const v = el("span", { cls: "sp-val" }, value);
    if (was) v.append(el("span", { cls: "sp-was", textContent: `was ${was}` }));
    const r = el(
      "div",
      { cls: "sp-row", testid: `sp-${testid}` },
      el("span", { cls: "sp-label", textContent: label }),
      v,
      sourceEl(src),
    );
    if (was) r.classList.add("changed");
    g.append(r);
    return r;
  };
  /** A number field: edits on every keystroke as one undo step per visit, Enter saves, Up and Down step it. */
  const numberInput = (
    field: string,
    label: string,
    value: number | null,
    fmt: (v: number) => string,
    parse: (t: string) => number | null,
    apply: (v: number | null, step: string) => void,
    opts: {
      step?: number;
      coarse?: number;
      allowNull?: boolean;
      placeholder?: string;
      disabled?: boolean;
      /** A length in the display unit: Up and Down step 0.1 (Shift 1) ft or m, kept to the centimetre (S22). */
      length?: boolean;
    } = {},
  ) => {
    const i = el("input", { cls: "sp-input" });
    i.dataset.field = field;
    i.value = value === null ? "" : fmt(value);
    i.dataset.drawn = i.value;
    i.placeholder = opts.placeholder ?? "";
    i.inputMode = "decimal";
    i.setAttribute("aria-label", label);
    i.disabled = ro || !!opts.disabled;
    // One visit to the field is one undo step: a rebuild that puts the focus back keeps the visit.
    const vkey = `${c.pid}:${field}`;
    i.addEventListener("focus", () => {
      if (!restoring || !visits.has(vkey)) visits.set(vkey, `${vkey}:${++visitSeq}`);
    });
    const push = () => {
      const visit = visits.get(vkey) ?? `${vkey}:${++visitSeq}`;
      const t = i.value.trim();
      if (t === "" && opts.allowNull) {
        i.classList.remove("bad");
        apply(null, visit);
        return;
      }
      const v = parse(t);
      i.classList.toggle("bad", v === null);
      if (v !== null) apply(v, visit);
    };
    i.addEventListener("input", push);
    i.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (i.classList.contains("bad")) return;
        i.blur();
        c.act.save();
      } else if ((e.key === "ArrowUp" || e.key === "ArrowDown") && opts.step) {
        e.preventDefault();
        const cur = parse(i.value) ?? value ?? 0;
        const k = e.shiftKey ? (opts.coarse ?? opts.step * 10) : opts.step;
        const v = opts.length
          ? nudgeLevel(cur, e.key === "ArrowUp" ? 1 : -1, e.shiftKey, u.length)
          : Math.round((cur + (e.key === "ArrowUp" ? k : -k)) / opts.step) * opts.step;
        i.value = fmt(v);
        push();
      }
    });
    return i;
  };
  const zFmt = (v: number) => fmtZ(v, u, 2);
  const zParse = (t: string) => u.parse(t, "m");
  const prof = (field: string, rule?: string) => fieldSource(c.draft, c.saved, c.savedBy, field, c.pid, rule, c.held);

  // ---- Place
  const place = group("Place", "place");
  const slid = Math.abs(c.centre - c.point) > 0.01;
  row(place, "Chainage", `${fmtCh(c.centre)}${slid ? ` (point ${fmtCh(c.point)})` : ""}`, null, "chainage");
  row(place, "Platform", `${fmtCh(c.centre - c.half)} to ${fmtCh(c.centre + c.half)}`, null, "platform");
  const so = c.centre - c.point;
  const soSrc = prof("so", "platform.slide.limit_never_clamped");
  const pos = numberInput(
    "point",
    `${c.name} point from platform start`,
    c.half - so,
    (v) => (Math.abs(v) < 0.05 ? 0 : v).toFixed(1),
    (t) => {
      const v = Number(t.replace(",", "."));
      return t !== "" && Number.isFinite(v) ? v : null;
    },
    (v, step) => v !== null && c.act.slide(c.half - Math.max(0, Math.min(2 * c.half, v)), step),
    { step: 0.5, coarse: 5 },
  );
  row(
    place,
    "Point from platform start (m)",
    pos,
    soSrc,
    "point",
    soSrc.changed ? String(c.half - Number(soSrc.was ?? 0)) : null,
  );
  const posBtns = el("div", { cls: "sp-buttons" });
  for (const [label, v, title] of [
    ["Point at start", c.half, "The drawn point at the platform start (low chainage end)"],
    ["Centred", 0, "The drawn point at the platform centre"],
    ["Point at end", -c.half, "The drawn point at the platform end (high chainage end)"],
  ] as const) {
    const b = el("button", { type: "button", textContent: label, title });
    b.disabled = ro;
    b.onclick = () => c.act.slide(v, `pos:${label}:${Date.now()}`);
    posBtns.append(b);
  }
  place.append(posBtns);
  place.append(
    el("p", {
      cls: "sp-hint",
      textContent:
        "The drawn point (tick on the bar) stays put; the platform slides along it. Alt + drag the bar to slide it (Alt + Left or Right, 0.5 m; Shift 5 m).",
    }),
  );

  // ---- Level
  const lv = group("Level", "level");
  const stSrc = prof("st", f && !f.level_set ? "network.level_solver.shallow_as_grade_allows" : undefined);
  const level = numberInput(
    "level",
    `${c.name} rail level`,
    typeof val(c.draft.st, c.pid) === "number" ? (val(c.draft.st, c.pid) as number) : null,
    zFmt,
    zParse,
    (v, step) => c.act.level(v, step),
    {
      step: 0.1,
      coarse: 1,
      length: true,
      allowNull: true,
      placeholder: f?.default_level_m != null ? `not set (${fmtZ(f.default_level_m, u, 2)})` : "not set",
    },
  );
  row(
    lv,
    `Rail level (${ul})`,
    level,
    stSrc,
    "level",
    stSrc.changed ? (typeof stSrc.was === "number" ? zFmt(stSrc.was) : "not set") : null,
  );
  if (f && !f.level_set && f.default_level_m !== null) {
    const set = el("button", {
      type: "button",
      textContent: `Set to ground − ${fmtZ(c.params?.def_depth_m ?? 7.62, u, 2)} ${ul}`,
      testid: "sp-set-default",
    });
    set.disabled = ro;
    set.onclick = () => c.act.level(Math.round((f.default_level_m as number) * 100) / 100, `default:${Date.now()}`);
    lv.append(el("div", { cls: "sp-buttons" }, set));
  }
  const depth = c.rail !== null && c.ground !== null ? c.ground - c.rail : null;
  const depthIn = numberInput(
    "depth",
    `${c.name} rail below ground`,
    depth,
    zFmt,
    zParse,
    (v, step) => v !== null && c.act.depth(v, step),
    { step: 0.1, coarse: 1, length: true, disabled: c.ground === null },
  );
  row(
    lv,
    `Rail below ground (${ul})`,
    depthIn,
    { text: "the ground here", title: "Sets the rail level to the ground at the centre minus this" },
    "depth",
  );
  const fill = c.ground !== null && c.groundDem !== null && Math.abs(c.ground - c.groundDem) > 0.02;
  row(
    lv,
    "Ground at centre",
    `${fmtZ(c.ground, u, 2)} ${ul}${fill ? ` (${(c.ground as number) > (c.groundDem as number) ? "fill" : "cut"} ${fmtZ(Math.abs((c.ground as number) - (c.groundDem as number)), u)})` : ""}`,
    { text: fill ? "finished ground" : "survey" },
    "ground",
  );
  const gIn = f?.grade_in_permille ?? c.gradeIn;
  const gOut = f?.grade_out_permille ?? c.gradeOut;
  row(
    lv,
    "Grade in / out",
    `${gIn === null ? "–" : fmtG(gIn)} / ${gOut === null ? "–" : fmtG(gOut)}`,
    { text: "1 m beyond each end" },
    "grades",
  );
  const sgNow = typeof val(c.draft.sg, c.pid) === "number" ? (val(c.draft.sg, c.pid) as number) : 0;
  const sgSrc = prof("sg", "platform.grade.limit_by_era");
  const sgIn = numberInput(
    "grade",
    `${c.name} platform grade`,
    sgNow,
    (v) => v.toFixed(1),
    (t) => {
      const v = Number(t.replace(",", ".").replace("‰", ""));
      return t !== "" && Number.isFinite(v) ? v : null;
    },
    (v, step) => v !== null && c.act.grade(v, step),
    { step: 0.5, coarse: 5 },
  );
  const lim = f?.grade_limit_permille ?? c.params?.sg_max_permille ?? null;
  const limParam = f?.grade_limit_param ?? c.params?.sg_max_param ?? "";
  const sgWrap = el("span", {}, sgIn);
  if (lim !== null) {
    const a = el("a", {
      href: "#",
      cls: "sp-param",
      textContent: ` limit ${lim.toFixed(1)}‰`,
      title: `param ${limParam}: open it`,
    });
    a.onclick = (e) => {
      e.preventDefault();
      c.act.openParam(limParam);
    };
    sgWrap.append(a);
  }
  row(lv, "Platform grade (‰)", sgWrap, sgSrc, "sg", sgSrc.changed ? Number(sgSrc.was ?? 0).toFixed(1) : null);
  const ease = el("button", {
    type: "button",
    textContent: "Ease the bends",
    title: "Slope this platform toward the grades on either side, up to the station limit (E)",
    testid: "sp-ease",
  });
  ease.disabled = ro;
  ease.onclick = c.act.ease;
  lv.append(el("div", { cls: "sp-buttons" }, ease));

  // ---- Structure
  const sx = group("Structure", "structure");
  if (c.metro) {
    const sel = el("select", { cls: "sp-select" });
    sel.dataset.field = "stt";
    sel.setAttribute("aria-label", `${c.name} station type`);
    sel.disabled = ro;
    const cur = (val(c.draft.stt, c.pid) as string | undefined) ?? "";
    sel.append(el("option", { value: "", textContent: `Rules${cur ? "" : `: ${typeLabel(f?.type)}`}` }));
    for (const [k, label] of Object.entries(STT_LABELS))
      sel.append(el("option", { value: k, textContent: label, selected: cur === k }));
    sel.title =
      "The station's structure, whole platform. Rules: a box within the phase's cut-and-cover limit, mined deeper, open by level. Elevated sets the rail at the mezzanine's height over the ground if it is lower.";
    sel.onchange = () => c.act.type((sel.value || null) as SelectableType | null);
    const sttSrc = prof("stt", "station.type.selection_else_limit");
    row(
      sx,
      "Station type",
      sel,
      sttSrc,
      "stt",
      sttSrc.changed ? (sttSrc.was ? STT_LABELS[sttSrc.was as SelectableType] : "Rules") : null,
    );
    if (sttSameAsPaint(c.draft, c.pid, c.centre))
      sx.append(
        el("p", {
          cls: "sp-hint",
          testid: "sp-stt-paint",
          textContent:
            "Same as the paint here: the old page showed this as Rules (it took it for its 2 November migration). The hub keeps it as your selection; choose Rules to let the rules decide.",
        }),
      );
  }
  const ts = el(
    "span",
    {},
    el("span", { cls: "sp-chip", textContent: " " }),
    ` ${f ? typeReason(f, u) : "working it out…"}`,
  );
  (ts.firstChild as HTMLElement).style.background = typeColour(f?.type);
  row(
    sx,
    "Structure",
    ts,
    { text: f?.type_source === "ben" ? "Ben" : "rule", rule: "station.type.selection_else_limit" },
    "type",
  );
  if (f?.structure)
    row(
      sx,
      "Outline",
      `${f.structure.kind === "box" ? "box" : f.structure.kind === "deck" ? "deck" : `tube ${f.structure.kind}`}: top ${fmtZ(f.structure.top_m, u, 2)}, bottom ${fmtZ(f.structure.bottom_m, u, 2)} ${ul}`,
      {
        text: "metro_structure",
        title: "Box top 4.6 m (5.2 island) over the rail, 1.0 m under it; the phase's tube; the deck",
      },
      "outline",
    );
  if (f?.selected === "elevated" && f.elevated_rail_min_m !== null)
    row(
      sx,
      "Mezzanine",
      `rail at least ${fmtZ(f.elevated_rail_min_m, u, 2)} ${ul} for the mezzanine under it`,
      { text: "rule", rule: "station.type.elevated_mezzanine" },
      "mezz",
    );
  const side = el("select", { cls: "sp-select" });
  side.dataset.field = "side";
  side.setAttribute("aria-label", `${c.name} side or island`);
  side.disabled = !c.canEditSide;
  side.append(
    el("option", { value: "side", textContent: "Side platforms", selected: c.side.now === "side" }),
    el("option", { value: "island", textContent: "Island", selected: c.side.now === "island" }),
  );
  side.title =
    "Side platforms or one island between the tracks: it sets the box top (4.6 or 5.2 m), the hall depth and the access rule.";
  side.onchange = () => c.act.side(side.value as "side" | "island");
  row(
    sx,
    "Platforms",
    side,
    { text: c.side.now !== c.side.was ? "Ben, not saved" : c.side.source },
    "side",
    c.side.now !== c.side.was ? (c.side.was === "island" ? "Island" : "Side platforms") : null,
  );

  // ---- Access (the Metro)
  if (c.metro) {
    const ax = group("Access and street", "access");
    const a = f?.access ?? null;
    const sel = el("select", { cls: "sp-select" });
    sel.dataset.field = "access";
    sel.setAttribute("aria-label", `${c.name} access`);
    sel.disabled = ro || !a;
    const ben = val(c.draft.access, c.pid) as { type?: string } | undefined;
    sel.append(el("option", { value: "", textContent: `Rules: ${a ? (ACCESS[a.rule]?.label ?? a.rule) : "…"}` }));
    for (const [k, v] of Object.entries(ACCESS))
      sel.append(el("option", { value: k, textContent: v.label, selected: ben?.type === k }));
    sel.title = a ? (ACCESS[a.type]?.note ?? "") : "";
    sel.onchange = () => c.act.access(sel.value || null);
    const accSrc = prof("access", a?.rule_id);
    row(
      ax,
      "Access",
      sel,
      accSrc,
      "access",
      accSrc.changed
        ? (accSrc.was as { type?: string } | undefined)?.type
          ? ACCESS[(accSrc.was as { type: string }).type]?.label
          : "Rules"
        : null,
    );
    if (a) {
      row(
        ax,
        "Opening",
        openingText(a),
        {
          text: a.year !== null ? "Chronology" : "line phase",
          rule: a.year === null ? "access.year.fallback_to_line_phase" : undefined,
        },
        "opening",
      );
      row(
        ax,
        "Hall room",
        hallRoomText(a, u),
        {
          text: "rule",
          rule: "access.type.shallower_than_d_hall",
          title: "D_HALL: the box's rail-to-roof-top plus the hall's clear height, roof and cover (metro_structure)",
        },
        "hallroom",
      );
    }
  }
  if (f) {
    const g = c.metro ? (bodies.get("access") as HTMLElement) : group("Street", "street");
    row(g, "Street", streetText(f.street), { text: "section context", rule: "road.station.street_known" }, "street");
    digest(
      c.metro ? "access" : "street",
      `${f.access ? (ACCESS[f.access.type]?.label ?? f.access.type) : ""}${f.access ? " · " : ""}${streetText(f.street)}`,
    );
  }

  // ---- Platform curve (the Metro)
  if (c.metro && f?.curve) {
    const cv = group("Platform curve", "curve");
    const pc = f.curve;
    const word = curveWord(pc);
    const r = el("span", {}, fmtR(pc.R_m));
    if (word) {
      const w = el("span", { textContent: ` · ${word}` });
      w.style.color = pc.level === "error" && !pc.gapfill ? SEV_COLOURS.error : SEV_COLOURS.info;
      r.append(w);
    }
    row(cv, "Platform curve", r, { text: "rule", rule: "platform.curvature.gapfill" }, "curve");
    row(
      cv,
      "Extra gap out / in",
      `${fmtGap(pc.out_m)} / ${fmtGap(pc.inn_m)}`,
      { text: "rule", rule: "platform.curvature.gapfill" },
      "gaps",
    );
    if (pc.turns.s)
      row(
        cv,
        "Drawing",
        `S-curve (${pc.turns.pos.toFixed(0)}° / ${(-pc.turns.neg).toFixed(0)}°)`,
        { text: "rule", rule: "platform.curvature.no_s_curve" },
        "scurve",
      );
    const needed = pc.R_m !== null && pc.R_m < (c.params?.plat_r_err_m ?? 600);
    const on = (c.draft.gapfill as string[] | undefined)?.includes(c.pid) ?? false;
    const gf = el("button", {
      type: "button",
      textContent: on ? "Gap fillers: on" : "Gap fillers (named exception)",
      title: "Allow this curved platform as a named exception with gap fillers",
      testid: "sp-gapfill",
    });
    gf.setAttribute("aria-pressed", String(on));
    gf.disabled = ro || (!needed && !on);
    gf.onclick = () => c.act.gapfill(!on);
    const gsrc = prof("gapfill", "platform.curvature.gapfill");
    const wrap = el("span", {}, gf);
    if (!needed && !on)
      wrap.append(
        el("span", {
          cls: "muted",
          textContent: ` not needed: ${pc.R_m === null ? "straight" : `R ${Math.round(pc.R_m).toLocaleString("en-US")} m`}`,
        }),
      );
    row(cv, "Gap fillers", wrap, gsrc, "gapfill-row", gsrc.changed ? (gsrc.was ? "on" : "off") : null);
  }

  // ---- Flags, with their fix buttons
  const fl = group("Flags", "flags");
  if (!f) fl.append(el("p", { cls: "sp-hint", textContent: "Working out this station's flags…" }));
  else if (!f.flags.length) fl.append(el("p", { cls: "sp-hint", textContent: "None." }));
  for (const x of f?.flags ?? []) {
    const chip = el("span", {
      cls: "sp-sev",
      textContent: x.sev === "error" ? "error" : x.sev === "warn" ? "warning" : "note",
    });
    chip.style.color = SEV_COLOURS[x.sev];
    // the severity, then the flag in words over a line with its rule and its fix: a narrow panel keeps the text wide
    const foot = el("div", { cls: "sp-flag-foot" });
    const rule = el("span", { cls: "sp-src", textContent: x.rule });
    rule.title = c.ruleText?.(x.rule) ?? `rule ${x.rule}`;
    foot.append(rule);
    const fix = fixFor(x, c);
    if (fix) {
      const b = el("button", { type: "button", textContent: fix.label, testid: `sp-fix-${x.kind}` });
      b.disabled = ro;
      b.onclick = fix.run;
      foot.append(b);
    }
    const r = el(
      "div",
      { cls: "sp-flag", testid: `sp-flag-${x.kind}` },
      chip,
      el("div", {}, el("span", { textContent: flagText(x, u, (id) => id) }), foot),
    );
    fl.append(r);
  }

  // ---- Limits: the params that touch stations, read only, each opening its record
  const lm = group("Limits", "limits");
  const P = c.params;
  if (P) {
    const lim2 = (label: string, value: string, path: string, testid: string) => {
      const a = el("a", {
        href: "#",
        cls: "sp-param",
        textContent: path,
        title: `param ${path}: open it in the inspector`,
      });
      a.onclick = (e) => {
        e.preventDefault();
        c.act.openParam(path);
      };
      const r = row(lm, label, value, null, testid);
      (r.lastElementChild as HTMLElement).replaceChildren(a);
    };
    lim2("Platform length", `${fmtZ(P.platform_m, u, 1)} ${ul}`, `${c.paramPrefix}.platform`, "lim-platform");
    lim2("Default depth", `${fmtZ(P.def_depth_m, u, 2)} ${ul}`, `${c.paramPrefix}.defDepth`, "lim-depth");
    lim2("Max platform grade", `${P.sg_max_permille.toFixed(1)}‰`, P.sg_max_param, "lim-grade");
    lim2("Deck depth", `${fmtZ(P.deck_depth_m, u, 2)} ${ul}`, `${c.paramPrefix}.deckDepth`, "lim-deck");
  }
  digest("place", `${fmtCh(c.centre)}${slid ? `, ${slideText(c.centre - c.point, u)}` : ""}`);
  digest("level", `${fmtZ(c.rail, u, 2)} ${ul}, ${depth === null ? "–" : `${fmtZ(depth, u, 2)} down`}, ${fmtG(sgNow)}`);
  digest("structure", `${typeLabel(f?.type)}, ${c.side.now === "island" ? "island" : "side platforms"}`);
  if (f?.curve) digest("curve", `${fmtR(f.curve.R_m)}${curveWord(f.curve) ? ` · ${curveWord(f.curve)}` : ""}`);
  const nErr = f?.flags.filter((x) => x.sev === "error").length ?? 0;
  const nWarn = f?.flags.filter((x) => x.sev === "warn").length ?? 0;
  digest(
    "flags",
    f
      ? f.flags.length
        ? `${nErr} error${nErr === 1 ? "" : "s"}, ${nWarn} warning${nWarn === 1 ? "" : "s"}`
        : "none"
      : "",
  );
  if (P) digest("limits", `grade ${P.sg_max_permille.toFixed(1)}‰, platform ${fmtZ(P.platform_m, u, 1)} ${ul}`);
  for (const id of GROUP_ORDER) {
    const b = bodies.get(id);
    if (b?.parentElement) groups.append(b.parentElement);
  }
  return root;
}

/** The groups, the most used first: the level and grade, the structure, the flags, the slide, then the rest. */
export const GROUP_ORDER = ["level", "structure", "flags", "place", "access", "street", "curve", "limits"] as const;
/** Open until Ben folds them; the rest start folded. The flags open by themselves when the station has a flag. */
const OPEN_BY_DEFAULT = new Set(["level", "structure"]);
export const GROUPS_KEY = "cr.sheet.groups";

function storedGroups(): Record<string, boolean> {
  try {
    return JSON.parse(localStorage.getItem(GROUPS_KEY) ?? "{}") as Record<string, boolean>;
  } catch {
    return {};
  }
}

/** Whether a group is open: Ben's choice, else the default (the flags open when there is an error or warning). */
export function groupOpen(id: string, f: { flags: { sev: string }[] } | null): boolean {
  const kept = storedGroups()[id];
  if (typeof kept === "boolean") return kept;
  if (id === "flags") return !!f?.flags.some((x) => x.sev === "error" || x.sev === "warn");
  return OPEN_BY_DEFAULT.has(id);
}

function keepGroup(id: string, open: boolean): void {
  try {
    localStorage.setItem(GROUPS_KEY, JSON.stringify({ ...storedGroups(), [id]: open }));
  } catch {
    /* storage denied: the group folds back on the next station */
  }
}

/** The fix button of a flag, as the old issue list offered them. */
function fixFor(x: { kind: string; data?: unknown }, c: PanelCtx): { label: string; run: () => void } | null {
  const d = (x.data ?? {}) as Record<string, number>;
  switch (x.kind) {
    case "platform_grade_over":
      return { label: "Ease", run: c.act.ease };
    case "platform_slide_over": {
      const lim = d.limit_m ?? 150;
      const so = c.centre - c.point;
      return {
        label: `Slide back to ${Math.round(lim)} m`,
        run: () => c.act.slide(Math.sign(so) * lim, `fix:${Date.now()}`),
      };
    }
    case "platform_curve":
      return (c.draft.gapfill as string[] | undefined)?.includes(c.pid)
        ? null
        : { label: "Gap fillers", run: () => c.act.gapfill(true) };
    case "access_hall_too_shallow":
      return c.ground === null
        ? null
        : {
            label: "Lower to D_HALL",
            run: () =>
              c.act.level(Math.floor(((c.ground as number) - (d.d_hall_m ?? 0)) * 100) / 100, `fix:${Date.now()}`),
          };
    case "platform_level_unset": {
      const z = d.default_level_m;
      return typeof z === "number"
        ? { label: "Set to ground − 7.62 m", run: () => c.act.level(Math.round(z * 100) / 100, `fix:${Date.now()}`) }
        : null;
    }
    case "access_hall_over_mined":
      return { label: "Choose a street hall", run: () => c.act.access("mined_hall") };
    case "access_not_mezzanine_on_elevated":
      return { label: "Mezzanine under", run: () => c.act.access("elevated_mezzanine") };
    case "station_tbm_before_phase_3":
      return { label: "Back to the rules", run: () => c.act.type(null) };
    default:
      return null;
  }
}

/** Keep a focused field across a rebuild: its raw text, its caret and its drawn value. */
export function keepFocus(from: HTMLElement, rebuild: () => HTMLElement | null): void {
  const a = document.activeElement as HTMLInputElement | HTMLSelectElement | null;
  const field = a && from.contains(a) ? a.dataset.field : undefined;
  const raw =
    a instanceof HTMLInputElement
      ? { value: a.value, s: a.selectionStart, e: a.selectionEnd, drawn: a.dataset.drawn }
      : null;
  const fresh = rebuild();
  if (!field || !fresh) return;
  const b = fresh.querySelector<HTMLInputElement | HTMLSelectElement>(`[data-field="${field}"]`);
  if (!b) return;
  if (raw && b instanceof HTMLInputElement) {
    b.value = raw.value;
    if (raw.drawn !== undefined) b.dataset.drawn = raw.drawn;
    b.classList.toggle("bad", (a as HTMLInputElement).classList.contains("bad"));
  }
  restoring = true;
  try {
    b.focus({ preventScroll: true });
  } finally {
    restoring = false;
  }
  if (raw && b instanceof HTMLInputElement && raw.s !== null) b.setSelectionRange(raw.s, raw.e);
}
