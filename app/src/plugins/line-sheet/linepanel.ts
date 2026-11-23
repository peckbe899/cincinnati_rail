// The line panel (claude/hub_maps/profiles_parity.md, section C: R52 to R61): the old page's side cards for the whole
// line, under the station panel. The line summary and the type table (updatePanels 2872-2884), Profile set (R53),
// the issues with their filters and groups and each one's fix buttons (renderIssues 2928-2950), the line's buttons
// (Ease all platforms, Solve levels with crossings, Fix unbuildable, Check all lines, 2898-2900), the paint review
// (renderPaints 2963-2983) and the canon card (2885-2913, its first part). Built from the draft's solves; every
// button calls back into the sheet, which lays the edit on the draft as one undo step. No state of its own but what
// is folded and filtered, kept for the session.

import type { SectionSolveInput, SolvedSection, StationFact } from "@cr/engine/contract";
import type { Units } from "../../core/units.ts";
import { flagText, fmtCh, fmtG, fmtGap, SEV_COLOURS, TYPES, typeColour } from "./drawing.ts";
import { issueText, type Words, wordsIn } from "./solved.ts";

/** The colour of each issue kind's tag (ISS_CAT 2136). */
export const KIND_COLOURS: Record<string, string> = {
  Grade: "#d9822b",
  "Curve grade": "#d9822b",
  Clearance: "#b0479e",
  Context: "#b0479e",
  Cover: "#8a6d3b",
  "Thin cover": "#8a6d3b",
  River: "#1f8fa0",
  "Tunnel method": "#3f6fb5",
  "Low cover": "#3f6fb5",
  Ground: "#8a6d3b",
  Regrade: "#3f6fb5",
  "Tube form": "#6a5acd",
  "Tube choice": "#6a5acd",
  "Approach box": "#7f8c8d",
  Canon: "#7a8c2e",
  Painted: "#7a8c2e",
  Unbuildable: "#c0392b",
  Drawing: "#95a5a6",
  "Platform curve": "#a04070",
  "Platform slide": "#a04070",
  "Platform grade": "#a04070",
  "Platform overlap": "#a04070",
  "Vertical curve": "#b9770e",
  Drainage: "#2e86c1",
  Road: "#b03a2e",
  Access: "#2a9d8f",
};

/** A station flag's page kind (the old issue list's kinds for station.facts@1's flags). */
export function stationPage(kind: string): string {
  if (kind === "platform_grade_over") return "Platform grade";
  if (kind === "platform_curve" || kind === "platform_s_curve") return "Platform curve";
  if (kind === "platform_slide_over") return "Platform slide";
  if (kind === "platform_overlap") return "Platform overlap";
  if (kind.startsWith("access_")) return "Access";
  if (kind === "platform_level_unset") return "Level";
  return "Tunnel method";
}

/** One row of the issues list: a finding of the whole solve or a station's flag, in the old page's terms. */
export interface IssueRow {
  key: string;
  page: string;
  sev: "error" | "warn" | "note";
  c: number;
  text: string;
  rule: string;
  /** this line, crossings with lines set, crossings with lines not set yet */
  grp: "own" | "cross" | "pending";
  fix?: { mode: "lower" | "raise"; c0: number; c1: number; fit: { t: string; why: string } | null };
  propose?: { c0: number; c1: number };
  clear?: { c0: number; c1: number; station: string | null };
  /** a station's flag: its platform id, for Show and its own fix */
  station?: string;
  stationKind?: string;
}

const SEV_OF = { error: "error", warn: "warn", info: "note" } as const;

/** The station flags the whole solve lists itself (its Tunnel method and Unbuildable findings, as the old page did):
 * from station.facts@1 they are left out of the list once the whole solve is in, so no finding is listed twice. */
const SOLVE_LISTS = new Set([
  "station_tbm_before_phase_3",
  "station_box_past_cc_max",
  "station_mined_in_box_stretch",
  "station_box_roof_out_of_ground",
]);

/** The old page's names of the access types (ACCESS 467-477). */
const ACCESS_LABEL: Record<string, string> = {
  surface: "Surface station",
  platform_level: "Platform level",
  platform_level_xu: "Platform level, crossunder",
  end_halls: "End ticket halls",
  mezzanine: "Mezzanine",
  mezzanine_full: "Full-length mezzanine",
  mined_hall: "Street hall, mined station",
  deep: "Deep station",
  elevated_mezzanine: "Elevated, mezzanine under",
};

/**
 * A station flag in the old issue list's words (designChecks 2087-2101, stationAccess 519-526), or null to word it
 * as the station panel does (a flag the old page had no row for).
 */
export function stationIssueText(
  f: { kind: string; sev: string; data?: unknown },
  station: string,
  w: Words,
  name: (pid: string) => string,
  cOf: (pid: string) => number | null,
  myC: number,
): string | null {
  const d = (f.data ?? {}) as Record<string, unknown>;
  const n = (k: string) => (typeof d[k] === "number" ? (d[k] as number) : Number.NaN);
  const lit = w.input?.literals;
  const access = ACCESS_LABEL[String(d.access)] ?? String(d.access);
  const who = d.source === "ben" ? "Ben" : "rule";
  switch (f.kind) {
    case "platform_grade_over":
      return `${station} platform at ${fmtG(n("grade_permille"))} is over the ${n("limit_permille")}‰ station limit`;
    case "platform_s_curve":
      return `${station} platform is on an S-curve (turns ${n("pos_deg").toFixed(0)}° one way and ${n("neg_deg").toFixed(0)}° the other inside the span)${f.sev === "error" ? ": unfinished, a station needs a straight or a single curve" : ": small wiggle in the drawing"}`;
    case "platform_curve": {
      const R = n("R_m");
      const what = `${station} platform on a ${Number.isFinite(R) ? `${Math.round(R)} m` : "straight"} curve: extra gap ${fmtGap(n("out_m"))} outside face, ${fmtGap(n("inn_m"))} inside face`;
      if (d.level === "error" && !d.gapfill)
        return `${what} (under ${lit?.PLAT_R_ERR ?? 600} m: needs gap fillers as a named exception, or slide or move the platform)`;
      return d.level === "error" ? `${what}: named exception with gap fillers` : what;
    }
    case "platform_slide_over":
      return `${station} platform slid ${n("slide_m").toFixed(0)} m from its point (the Deck allows ${n("limit_m")} m); slide it back or move the station point on the Deck`;
    case "platform_overlap": {
      const other = String(d.other);
      const oc = cOf(other);
      const [a, b] = oc != null && oc < myC ? [name(other), station] : [station, name(other)];
      return `${a} and ${b} platforms overlap (centres ${n("apart_m").toFixed(0)} m apart); slide one or remove a station`;
    }
    case "access_crossunder":
      return `${station}: ${d.island ? "an island" : "an interchange"} shallower than D_HALL (${w.z(n("depth_m"), 1)} of ${w.z(n("d_hall_m"), 2)} ${w.u}): platform level with a crossunder; a hall needs the rail ${w.z(n("d_hall_m") - n("depth_m"), 1)} ${w.u} deeper`;
    case "access_no_year":
      return `${station}: no opening year in the Chronology: the access type falls back to the line's phase (${String(d.phase)}), drawn dashed`;
    case "access_hall_too_shallow":
      return `${station}: ${access} (${who}) needs the rail at least ${w.z(n("d_hall_m"), 2)} ${w.u} down for the hall over the box; it is ${w.z(n("depth_m"), 2)}: lower the station, or choose platform level`;
    case "access_mezzanine_clearance":
      return `${station}: ${access} (${who}) needs ${w.z(n("need_m"), 2)} ${w.u} clear under the platform deck (the rail ${w.z(n("rail_over_ground_m"), 2)} ${w.u} over the ground); ${Number.isFinite(n("under_m")) ? `there is ${w.z(n("under_m"), 2)}` : "no ground here"}: raise the station`;
    case "access_not_mezzanine_on_elevated":
      return `${station}: ${access} chosen for an elevated station: the platforms are reached from a mezzanine under them`;
    case "access_hall_over_mined":
      return `${station}: ${access} (${who}) over a mined station: there is no box roof to build the hall on; choose a street hall`;
    default:
      return null;
  }
}

/** Every issue of the line, the whole solve's findings and the stations' flags, as the old list held them. */
export function issueRows(
  solved: SolvedSection | null,
  facts: readonly StationFact[] | null,
  units: Units,
  name: (pid: string) => string,
  input: SectionSolveInput | null = null,
): IssueRow[] {
  const w = wordsIn(units, input, solved);
  const out: IssueRow[] = [];
  (solved?.flags ?? []).forEach((f, i) => {
    // the stretch notes too: the old list carried them (Tunnel method), though no marker is drawn for them
    const cross = f.kind.startsWith("crossing_");
    const d = f.data as Record<string, unknown>;
    const si = typeof d.si === "number" ? d.si : null;
    const station = si !== null ? (solved?.stations[si]?.platform_id ?? null) : null;
    out.push({
      key: `s${i}`,
      page: f.page,
      sev: SEV_OF[f.sev],
      c: f.c,
      text: issueText(f, w),
      rule: f.rule,
      grp: f.pending ? "pending" : cross ? "cross" : "own",
      ...(f.fix
        ? {
            fix: {
              ...f.fix,
              fit: f.kind === "paint_misfit" ? { t: String(d.t), why: String(d.why) } : null,
            },
          }
        : {}),
      ...(f.propose ? { propose: f.propose } : {}),
      ...(f.clear ? { clear: { c0: f.clear.c0, c1: f.clear.c1, station } } : {}),
    });
  });
  const cOf = new Map((facts ?? []).map((s) => [s.platform_id, s.c_m]));
  for (const s of facts ?? []) {
    if (s.deleted) continue;
    s.flags.forEach((f, j) => {
      if (solved && SOLVE_LISTS.has(f.kind)) return;
      const text =
        stationIssueText(f, name(s.platform_id), w, name, (p) => cOf.get(p) ?? null, s.c_m) ??
        `${name(s.platform_id)}: ${flagText(f, units, name)}`;
      out.push({
        key: `f${s.platform_id}:${j}`,
        page: stationPage(f.kind),
        sev: SEV_OF[f.sev as keyof typeof SEV_OF] ?? "note",
        c: s.c_m,
        text,
        rule: f.rule,
        grp: "own",
        station: s.platform_id,
        stationKind: f.kind,
      });
    });
  }
  return out;
}

/** The filters Ben turned off ("s:error", "k:Grade"), kept for the session as the old page kept them. */
const HIDE_KEY = "cr.sheet.issHide";
export function hiddenFilters(): Set<string> {
  try {
    return new Set(JSON.parse(sessionStorage.getItem(HIDE_KEY) ?? "[]") as string[]);
  } catch {
    return new Set();
  }
}
function keepHidden(h: Set<string>): void {
  try {
    sessionStorage.setItem(HIDE_KEY, JSON.stringify([...h]));
  } catch {
    /* the filters last for this panel */
  }
}

export interface CheckRow {
  id: string;
  name: string;
  cover: number;
  box: number;
  fit: number;
  err: number;
  paint: number;
}

export interface PaintRowView {
  list: "ovr" | "tf" | "shafts";
  a: number;
  b: number;
  paint: string;
  rules: string | null;
  same: boolean;
  misfit: number;
  fill: boolean;
}

export interface LineCtx {
  units: Units;
  /** "Line 6" */
  line: string;
  length: number;
  liveStations: number;
  removed: number;
  solved: SolvedSection | null;
  ssi: SectionSolveInput | null;
  facts: readonly StationFact[] | null;
  name(pid: string): string;
  ready: boolean;
  canEdit: boolean;
  /** a proposal or check in flight: its buttons wait */
  busy: string | null;
  paints: PaintRowView[] | null;
  check: CheckRow[] | null;
  checkNote: string | null;
  act: {
    ready(on: boolean): void;
    show(c: number): void;
    select(pid: string): void;
    regrade(fix: NonNullable<IssueRow["fix"]>): void;
    fill(c0: number, c1: number): void;
    clear(x: NonNullable<IssueRow["clear"]>): void;
    stationFix(pid: string, kind: string): void;
    easeAll(): void;
    solveCross(): void;
    fixAll(): void;
    checkAll(): void;
    openLine(id: string): void;
    reviewPaints(): void;
    clearPaint(r: PaintRowView): void;
    clearSamePaints(): void;
    clearAllPaints(): void;
    redraw(): void;
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

const btn = (text: string, title: string, run: () => void, disabled = false, testid?: string): HTMLButtonElement => {
  const b = el("button", { type: "button", textContent: text, title, disabled, ...(testid ? { testid } : {}) });
  b.onclick = run;
  return b;
};

/** What is folded, kept across rebuilds. */
const open = new Map<string, boolean>([
  ["summary", true],
  ["issues", true],
  ["grp:own", true],
  ["grp:cross", true],
  ["grp:pending", false],
  ["paints", false],
  ["canon", false],
]);
const fold = (id: string, summary: Node, ...body: Node[]): HTMLDetailsElement => {
  const d = el("details", { cls: "lp-group" });
  d.dataset.group = id;
  d.open = open.get(id) ?? false;
  d.append(el("summary", {}, summary), ...body);
  d.addEventListener("toggle", () => open.set(id, d.open));
  return d;
};

const STATION_FIX: Record<string, string> = {
  platform_grade_over: "Ease",
  platform_curve: "Gap fillers",
  platform_slide_over: "Slide back",
  access_hall_too_shallow: "Lower to D_HALL",
  platform_level_unset: "Set level",
};

/** The line panel. Returns the element; the sheet puts it under the station panel. */
export function buildLinePanel(c: LineCtx): HTMLElement {
  const root = el("div", { cls: "lp", testid: "line-panel" });
  const u = c.units;
  const fz = (m: number | null | undefined, d = 1) => (m == null || !Number.isFinite(m) ? "–" : u.format(m, "m", d));
  const lu = u.label("m");
  const s = c.solved;
  const sm = s?.summary as
    | {
        len: Record<string, number>;
        maxG: number;
        maxGc?: number;
        deepest?: { d: number; c: number };
        highest?: { h: number; c: number };
        sumps: number;
      }
    | undefined;

  // ---- the line summary and the type table (2875-2884)
  const kv = el("dl", { cls: "lp-kv", testid: "line-summary" });
  const row = (k: string, v: string | Node, colour?: string) => {
    const dd = el("dd", {}, v);
    if (colour) dd.style.color = colour;
    kv.append(el("dt", { textContent: k }), dd);
  };
  row("Length", `${(c.length / 1000).toFixed(2)} km`);
  row("Stations", `${c.liveStations}${c.removed ? `, ${c.removed} removed` : ""}`);
  if (sm) {
    const over = s?.over ?? [];
    row(
      "Steepest grade",
      `${fmtG(sm.maxG)}${sm.maxGc != null ? ` at ${fmtCh(sm.maxGc)}` : ""}`,
      over.some((o) => o.sev === "error") ? SEV_COLOURS.error : over.length ? SEV_COLOURS.warn : undefined,
    );
    if (sm.deepest) row("Deepest rail", `${fz(sm.deepest.d)} ${lu} below, ${fmtCh(sm.deepest.c)}`);
    if (sm.highest)
      row(
        "Highest rail",
        sm.highest.h > 0 ? `${fz(sm.highest.h)} ${lu} above, ${fmtCh(sm.highest.c)}` : "none above ground",
      );
    row("Tunnel low points (sumps)", String(sm.sumps));
  } else row("Structure", "solving…");
  const types = el("div", { cls: "lp-types", testid: "type-table" });
  if (sm)
    for (const [t, info] of Object.entries(TYPES)) {
      const L = sm.len[t] ?? 0;
      const chip = el("span", { cls: "type-chip" });
      chip.style.background = typeColour(t);
      const r = el("span", {}, chip, info.label);
      r.dataset.type = t;
      types.append(
        r,
        el("span", { cls: "n", textContent: `${(L / 1000).toFixed(2)} km` }),
        el("span", { cls: "n", textContent: `${((100 * L) / Math.max(1, c.length)).toFixed(0)}%` }),
      );
    }
  // ---- Profile set (R53)
  const ready = el("input", { type: "checkbox", checked: c.ready, disabled: !c.canEdit, testid: "line-ready" });
  ready.onchange = () => c.act.ready(ready.checked);
  const readyRow = el(
    "label",
    {
      cls: "lp-ready",
      title:
        "Mark this line's weaving as set: other lines then show their crossings with it as real clearance issues. Crossings with lines not set yet are listed apart.",
    },
    ready,
    " Profile set (crossings with it count)",
  );
  root.append(fold("summary", el("h3", { textContent: `${c.line} summary` }), kv, types, readyRow));

  // ---- the issues (renderIssues 2928-2950)
  const all = issueRows(s, c.facts, u, c.name, c.ssi);
  const hide = hiddenFilters();
  const mine = all.filter((x) => x.grp !== "pending");
  const pend = all.filter((x) => x.grp === "pending");
  const ns = { error: 0, warn: 0, note: 0 };
  for (const x of mine) ns[x.sev]++;
  const counts = el("p", {
    cls: "lp-hint",
    testid: "issue-counts",
    textContent: all.length
      ? `${ns.error} errors · ${ns.warn} warnings · ${ns.note} notes${pend.length ? ` · ${pend.length} crossings with lines not set yet` : ""}`
      : s
        ? "No design flags"
        : "The issues follow the whole solve.",
  });
  const chip = (f: string, label: string, n: number, colour: string) => {
    const b = el("button", { type: "button", cls: "iss-chip", title: "Show or hide" });
    b.dataset.f = f;
    b.setAttribute("aria-pressed", String(!hide.has(f)));
    const dot = el("span", { cls: "iss-dot" });
    dot.style.background = colour;
    b.append(dot, label, " ", el("span", { cls: "n", textContent: String(n) }));
    b.onclick = () => {
      if (hide.has(f)) hide.delete(f);
      else hide.add(f);
      keepHidden(hide);
      c.act.redraw();
    };
    return b;
  };
  const sevBar = el("div", { cls: "iss-bar", testid: "issue-severity-filters" });
  for (const [k, label, col] of [
    ["error", "Errors", SEV_COLOURS.error],
    ["warn", "Warnings", SEV_COLOURS.warn],
    ["note", "Notes", SEV_COLOURS.info],
  ] as const)
    if (ns[k]) sevBar.append(chip(`s:${k}`, label, ns[k], col));
  const kinds = new Map<string, number>();
  for (const x of mine) kinds.set(x.page, (kinds.get(x.page) ?? 0) + 1);
  const kindBar = el("div", { cls: "iss-bar", testid: "issue-kind-filters" });
  for (const [k, n] of [...kinds].sort((a, b) => b[1] - a[1]))
    kindBar.append(chip(`k:${k}`, k, n, KIND_COLOURS[k] ?? SEV_COLOURS.info));
  const shownOf = (x: IssueRow) => !hide.has(`k:${x.page}`) && !hide.has(`s:${x.sev}`);
  const order = { error: 0, warn: 1, note: 2 };
  const item = (x: IssueRow): HTMLLIElement => {
    const li = el("li", { cls: `iss sev-${x.sev}` });
    li.dataset.key = x.key;
    li.dataset.page = x.page;
    li.dataset.sev = x.sev;
    li.style.setProperty(
      "--sev",
      x.sev === "error" ? SEV_COLOURS.error : x.sev === "warn" ? SEV_COLOURS.warn : SEV_COLOURS.info,
    );
    const ch = el("button", { type: "button", cls: "ch", textContent: fmtCh(x.c), title: "Show on the profile" });
    ch.onclick = () => (x.station ? c.act.select(x.station) : c.act.show(x.c));
    const tag = el("span", { cls: "tag", textContent: x.page });
    tag.style.color = KIND_COLOURS[x.page] ?? SEV_COLOURS.info;
    const tx = el("span", { cls: "tx", title: x.rule }, tag, x.text);
    li.append(ch, tx);
    const acts = el("span", { cls: "act" });
    if (c.canEdit) {
      const wait = c.busy !== null;
      if (x.fix) {
        const f = x.fix;
        acts.append(
          btn(
            f.mode === "lower" ? "Lower" : "Raise",
            f.fit
              ? `${f.mode === "lower" ? "Lower" : "Raise"} the rail here until the ${f.fit.t} fits, as straight grades (a preview in your draft: Save keeps it, Discard or Ctrl+Z takes it back)`
              : f.mode === "lower"
                ? "Lower the rail here to one tube diameter of cover, as straight grades (a preview in your draft)"
                : "Raise the rail here to within the cut-and-cover limit, as straight grades (a preview in your draft)",
            () => c.act.regrade(f),
            wait,
            "fix-regrade",
          ),
        );
      }
      if (x.propose) {
        const p = x.propose;
        acts.append(
          btn(
            "Propose fill",
            "Draw the fill this structure needs as a ground line to edit (a preview in your draft)",
            () => c.act.fill(p.c0, p.c1),
            wait,
            "fix-fill",
          ),
        );
      }
      if (x.clear) {
        const cl = x.clear;
        acts.append(
          btn(
            "Clear",
            cl.station ? "Put this station's type back to the rules" : "Clear the paint over this stretch",
            () => c.act.clear(cl),
            false,
            "fix-clear",
          ),
        );
      }
      if (x.station && x.stationKind && STATION_FIX[x.stationKind]) {
        const pid = x.station;
        const k = x.stationKind;
        acts.append(
          btn(
            STATION_FIX[k] as string,
            "Fix this station's flag",
            () => c.act.stationFix(pid, k),
            false,
            "fix-station",
          ),
        );
      }
    }
    if (acts.childElementCount) li.append(acts);
    return li;
  };
  const list = (xs: IssueRow[]) => {
    const ul = el("ul", { cls: "iss-list" });
    for (const x of xs.slice().sort((a, b) => order[a.sev] - order[b.sev] || a.c - b.c)) ul.append(item(x));
    return ul;
  };
  const shown = mine.filter(shownOf);
  const own = shown.filter((x) => x.grp === "own");
  const cross = shown.filter((x) => x.grp === "cross");
  const issues = el("div", { testid: "issues" }, counts);
  if (all.length) issues.append(sevBar, kindBar);
  if (own.length) issues.append(fold("grp:own", el("span", { textContent: `This line (${own.length})` }), list(own)));
  if (cross.length)
    issues.append(
      fold("grp:cross", el("span", { textContent: `Crossings with lines set (${cross.length})` }), list(cross)),
    );
  if (pend.length)
    issues.append(
      fold("grp:pending", el("span", { textContent: `Crossings with lines not set yet (${pend.length})` }), list(pend)),
    );
  if (mine.length - shown.length)
    issues.append(
      el("p", { cls: "lp-hint", textContent: `${mine.length - shown.length} hidden by the filters above.` }),
    );
  // the line's buttons (2898-2900)
  const wait = c.busy !== null || !c.canEdit;
  const buttons = el(
    "div",
    { cls: "lp-buttons" },
    btn(
      "Ease all platforms",
      "Slope every platform toward the grades on either side, up to the station limit",
      c.act.easeAll,
      wait,
      "line-ease-all",
    ),
    btn(
      "Solve levels with crossings",
      "Re-solve this line's station levels so every crossing keeps the minimum clearance (a preview in your draft)",
      c.act.solveCross,
      wait,
      "line-solve-cross",
    ),
    btn(
      "Fix unbuildable",
      "Lower or Raise the rail at every unbuildable stretch of this line (paints that do not fit included), one after the other (a preview in your draft: Ctrl+Z takes it back)",
      c.act.fixAll,
      wait,
      "line-fix-all",
    ),
    btn(
      "Check all lines",
      "Run the system check over every Metro line: unbuildable stretches, errors, paints",
      c.act.checkAll,
      c.busy !== null,
      "line-check-all",
    ),
  );
  issues.append(buttons);
  if (c.busy) issues.append(el("p", { cls: "lp-hint", testid: "line-busy", textContent: c.busy }));
  if (c.check || c.checkNote) {
    const out = el("div", { testid: "check-out" });
    if (c.checkNote) out.append(el("p", { cls: "lp-hint", textContent: c.checkNote }));
    if (c.check) {
      const f = (v: number) => (v ? v.toFixed(2) : "–");
      const t = el("table", { cls: "chk" });
      t.innerHTML =
        '<thead><tr><th>Line</th><th title="Tube with less than one diameter of cover, km">No cover</th><th title="Box past its cut-and-cover limit, km">Box too deep</th><th title="Paints and station types that cannot be built where they are, km">Paint misfit</th><th>Errors</th><th title="Painted, km">Paints</th></tr></thead>';
      const body = el("tbody");
      for (const r of c.check) {
        const a = el("a", { href: "#", textContent: r.name });
        a.onclick = (e) => {
          e.preventDefault();
          c.act.openLine(r.id);
        };
        const tr = el("tr", {}, el("td", {}, a));
        for (const [v, bad] of [
          [f(r.cover), r.cover > 0],
          [f(r.box), r.box > 0],
          [f(r.fit), r.fit > 0],
          [String(r.err), false],
          [f(r.paint), false],
        ] as const)
          tr.append(el("td", { textContent: v, cls: bad ? "bad" : "" }));
        body.append(tr);
      }
      t.append(body);
      out.append(t);
    }
    issues.append(out);
  }
  root.append(fold("issues", el("h3", { textContent: "Issues" }), issues));

  // ---- the paint review (renderPaints 2963-2983)
  const doc = c.ssi?.doc;
  const nPaints = (doc?.ovr.length ?? 0) + (doc?.tf.length ?? 0);
  const paintBody = el("div", { testid: "paint-review" });
  if (c.paints === null)
    paintBody.append(
      el("p", { cls: "lp-hint", textContent: "Open to compare each paint with what the rules would do." }),
    );
  else if (!c.paints.length)
    paintBody.append(el("p", { cls: "lp-hint", textContent: "No paints: the rules decide everywhere." }));
  else {
    const same = c.paints.filter((r) => r.same).length;
    paintBody.append(
      el("p", {
        cls: "lp-hint",
        textContent: 'Each paint overrides the rules on its stretch. "Rules" is what the line would be without it.',
      }),
      el(
        "div",
        { cls: "lp-buttons" },
        btn(
          `Clear the ${same} that repeat the rules`,
          "",
          c.act.clearSamePaints,
          !c.canEdit || !same,
          "paints-clear-same",
        ),
        btn("Clear all paints", "", c.act.clearAllPaints, !c.canEdit, "paints-clear-all"),
      ),
    );
    const label = (k: string | null) =>
      k === null
        ? "–"
        : (TYPES[k]?.label ??
          (k === "bore" ? "Double-track bore" : k === "twin" ? "Twin tubes" : k === "shaft" ? "Shaft" : k));
    for (const r of c.paints) {
      const where = r.list === "shafts" ? fmtCh(r.a) : `${fmtCh(r.a)} to ${fmtCh(r.b)}`;
      const left = el(
        "div",
        {},
        el("b", { textContent: where }),
        ` ${label(r.paint)}`,
        el("br"),
        el("span", {
          cls: "muted",
          textContent: `rules: ${r.list === "shafts" ? "a stretch ends here" : r.list === "tf" && r.rules === null ? "not bored" : label(r.rules)}${r.same ? " (the same)" : ""}`,
        }),
      );
      if (r.misfit)
        left.append(
          el("br"),
          el("span", { cls: "bad", textContent: `does not fit over ${Math.round(r.misfit)} m (see the issues)` }),
        );
      const right = el(
        "div",
        {},
        btn("Show", "", () => c.act.show(r.a)),
      );
      if (r.fill) right.append(btn("Propose fill", "", () => c.act.fill(r.a, r.b), !c.canEdit || c.busy !== null));
      right.append(btn("Clear", "", () => c.act.clearPaint(r), !c.canEdit));
      const pr = el("div", { cls: "paint-row" }, left, right);
      pr.dataset.paint = r.paint;
      paintBody.append(pr);
    }
  }
  const pd = fold(
    "paints",
    el(
      "span",
      {},
      el("h3", { textContent: "Paints" }),
      " ",
      el("span", { cls: "lp-hint", textContent: nPaints ? `${nPaints} on this line` : "none on this line" }),
    ),
    paintBody,
  );
  pd.addEventListener("toggle", () => {
    if (pd.open && c.paints === null) c.act.reviewPaints();
  });
  root.append(pd);

  // ---- the canon card (2885-2889, its sections and locks)
  const canon = el("ul", { cls: "lp-canon", testid: "canon-card" });
  const METHOD: Record<string, string> = {
    shallow: "Basin method",
    deep: "Deep tunnel",
    canal: "Canal-bed cut & cover",
    covered: "Covered way (cut & cover)",
  };
  for (const x of s?.canon?.sections ?? []) {
    const r = x as { m: string; lo: number; hi: number; a?: string; b?: string; src?: string };
    canon.append(
      el(
        "li",
        {},
        el("b", { textContent: METHOD[r.m] ?? r.m }),
        `, ${r.a ?? fmtCh(r.lo)} to ${r.b ?? fmtCh(r.hi)}${r.src ? `: ${r.src}` : ""}`,
      ),
    );
  }
  for (const lk of s?.canon?.locks ?? [])
    canon.append(el("li", {}, el("b", { textContent: "Locked" }), ` ${fmtCh(lk.lo)} to ${fmtCh(lk.hi)}: ${lk.src}`));
  if (!canon.childElementCount)
    canon.append(el("li", { textContent: "No canon structure set for this line; the rules decide." }));
  root.append(fold("canon", el("h3", { textContent: "Canon structure" }), canon));
  return root;
}
