// The line sheet pane (section 8): canvas bands for one section, and a table that edits PVI and station levels.
//
// Flow: the selection (a profile or a section) gives the section; the server builds its SectionInput in the view
// (/x/profiles/sections/{id}/input), and the sheet reads the section's stops and platforms, the records the server
// builds the stations from. Every keystroke in the table edits the shared draft of the profile record, and the
// engine worker re-solves the draft's input at once; the stations and PVIs of that input are rebuilt from the draft
// by the server's own rule (model.ts stationsOf, region/ext/profiles/inputs.py), so the browser's rail and the
// server's agree. Save PATCHes the profile; the server's profiles.solve_section job runs and its result event
// brings the server's rail back, drawn under the local one. A new revision of the section, its stops, platforms,
// ground or params, or of the profile itself, reads the input again.
//
// Names, not ids: the sheet's title and tab name the section ("Line 6"), the station table and the canvas name the
// platforms ("Bond Hill"). Enter in a cell saves and leaves the cell, so the next Ctrl+Z is the hub's undo. A cell
// is read-only where the save would be refused: an import or legacy layer, or main while the old hub owns profiles.
// Selecting a platform, stop or station (on the map, or with Ctrl+K) opens its line here at its chainage.

import type {
  SectionInput,
  SectionProposal,
  SectionSolveInput,
  SolvedSection,
  StationFact,
  StationInput,
  VerticalRail,
} from "@cr/engine/contract";
import type { JsonPatch, Rec } from "../../api/types.ts";
import { layerPhrase } from "../../core/describe.ts";
import { bodyOf } from "../../core/drafts.ts";
import { deepEqual } from "../../core/jsonpatch.ts";
import { liveBoard } from "../../core/live.ts";
import { shortId } from "../../core/names.ts";
import type {
  BandData,
  BandDef,
  Handle,
  Host,
  MountedPane,
  PaneContext,
  RecordRef,
  Selection,
  SheetMark,
  SheetText,
  SheetView,
} from "../../core/plugin.ts";
import { isRecordRef } from "../../core/plugin.ts";
import { setChainage } from "../../core/store.ts";
import { CHAINAGE_HELP, formatChainage, parseChainage } from "../../core/units.ts";
import { type View, viewToken } from "../../core/view.ts";
import { createEngine, type EngineHandle } from "../../engine/client.ts";
import { MAXIMISE_REQUEST, MAXIMISED_EVENT } from "../../shell/maximise.ts";
import { stationLevel } from "./bands.ts";
import { bendCard, groundCard, helpCard } from "./cards.ts";
import { designNote, designOps, editOps, keepsDesign, laidIn, type SheetDesign } from "./design.ts";
import { bbox, grow, heldInside, type Rect, railSpan } from "./dirty.ts";
import {
  flagText,
  fmtCh,
  fmtZ,
  margins,
  SEV_COLOURS,
  streetShort,
  streetText,
  typeColour,
  typeLabel,
  valueAt,
  worstSeverity,
} from "./drawing.ts";
import {
  download,
  type ExportModel,
  exportGeoJson,
  exportJson,
  exportKmz,
  profileByKey,
  stationTypeAt,
} from "./exports.ts";
import { buildLinePanel, type CheckRow, type IssueRow, type PaintRowView } from "./linepanel.ts";
import {
  addPvi,
  easeGrade,
  factsInput,
  frameFor,
  hasDesign,
  localInput,
  maxDiff,
  nudgeLevel,
  type ProfileData,
  pviRows,
  removePvi,
  removeStation,
  restoreStation,
  roundSlide,
  type SelectableType,
  STATION_PROFILE_FIELDS,
  type StationFrame,
  setAccess,
  setGapfill,
  setPlatformSide,
  setPviC,
  setPviZ,
  setStationGrade,
  setStationLevel,
  setStationSlide,
  setStationType,
  solveInput,
  solveInputOf,
  stationFrame,
  toFloat64,
} from "./model.ts";
import { buildPanel, keepFocus } from "./panel.ts";
import { buildSettings, type SettingParam } from "./settings.ts";
import { issueAt, labelBoxes, levelExtent, resetLabels, type ShowMode, sampleAt, typeAtSample } from "./solved.ts";
import { StaticLayer, sameKey, staticPrefix } from "./static_layer.ts";
import {
  addGroundAt,
  BRUSH_LABELS,
  BRUSH_TIPS,
  type Brush,
  clearMisfit,
  clearPaints,
  type GroundPoint,
  groundLines,
  moveGroundPoint,
  paintRange,
  proposalOps,
  removeGroundPoint,
  setPvi,
  setReady,
  type Tool,
  TYPE_BRUSHES,
} from "./tools.ts";

export const SOLVE_JOB = "profiles.solve_section";

/** Record kinds the section's input is built from: a new revision of one reads the input again. */
const INPUT_KINDS: ReadonlySet<string> = new Set(["section", "stop", "platform", "ground_profile", "param"]);

interface Target {
  sectionId: string;
  profile: Rec | null;
}

/** Whether the sheet can show a selection: a profile or a section. */
export const sheetAccepts = (sel: Selection): sel is RecordRef =>
  isRecordRef(sel) && (sel.kind === "profile" || sel.kind === "section");

/** Whether a selection names a place on a line the sheet can go to: a platform, a stop or a station. */
export const sheetFollows = (sel: Selection): sel is RecordRef =>
  isRecordRef(sel) && (sel.kind === "platform" || sel.kind === "stop" || sel.kind === "station");

/** The section and profile a selection names. */
export async function resolveTarget(host: Host, view: View, sel: Selection): Promise<Target | null> {
  if (!isRecordRef(sel)) return null;
  if (sel.kind === "profile") {
    const profile = await host.records.get("profile", sel.id, view);
    const d = profile.data as Record<string, unknown>;
    const sectionId = [d.section, d.section_id, d.parent].find((v) => typeof v === "string") as string | undefined;
    if (!sectionId) throw new Error(`profile ${sel.id} names no section`);
    return { sectionId, profile };
  }
  if (sel.kind === "section") {
    let items: Rec[] = [];
    for (const f of [{ parent: sel.id }, { ref: sel.id }]) {
      try {
        items = (await host.records.list("profile", view, { ...f, limit: 2 })).items;
      } catch {
        items = [];
      }
      if (items.length) break;
    }
    return { sectionId: sel.id, profile: items[0] ?? null };
  }
  return null;
}

/** Every record of a list query, page by page. */
async function listAll(host: Host, kind: string, view: View, f: { parent?: string; ref?: string }): Promise<Rec[]> {
  const out: Rec[] = [];
  let after: string | undefined;
  for (;;) {
    const page = await host.records.list(kind, view, { ...f, limit: 500, ...(after ? { after } : {}) });
    out.push(...page.items);
    if (!page.next) return out;
    after = page.next;
  }
}

/** Where on which line a platform, stop or station is: its stops' sections and chainages. */
export async function placesOf(host: Host, view: View, sel: RecordRef): Promise<{ sectionId: string; c: number }[]> {
  const stopAt = (s: Rec) => {
    const d = s.data as Record<string, unknown>;
    return typeof d.section === "string" && typeof d.c === "number" ? [{ sectionId: d.section, c: d.c }] : [];
  };
  if (sel.kind === "stop") return stopAt(await host.records.get("stop", sel.id, view));
  if (sel.kind === "platform") {
    const p = (await host.records.get("platform", sel.id, view)).data as Record<string, unknown>;
    return typeof p.stop === "string" ? stopAt(await host.records.get("stop", p.stop, view)) : [];
  }
  if (sel.kind === "station") return (await listAll(host, "stop", view, { ref: sel.id })).flatMap(stopAt);
  return [];
}

export async function mountSheet(el: HTMLElement, ctx: PaneContext): Promise<MountedPane> {
  const host = ctx.host;
  const root = document.createElement("div");
  root.className = "sheet";
  const bar = document.createElement("div");
  bar.className = "sheet-bar";
  const title = document.createElement("strong");
  const profileInfo = Object.assign(document.createElement("span"), { className: "muted" });
  profileInfo.dataset.testid = "profile-info";
  const solveInfo = Object.assign(document.createElement("span"), { className: "muted" });
  solveInfo.dataset.testid = "solve-info";
  const serverInfo = Object.assign(document.createElement("span"), { className: "muted" });
  serverInfo.dataset.testid = "server-info";
  // The live hub's mark while this section is being imported or re-solved (region/live)
  const pendingMark = Object.assign(document.createElement("span"), { className: "pending-mark" });
  pendingMark.dataset.testid = "pending";
  pendingMark.hidden = true;
  // "default design (not saved)": the sheet draws a design that is not Ben's record (S57, S66, design.ts)
  const designMark = Object.assign(document.createElement("span"), { className: "design-mark" });
  designMark.dataset.testid = "design-note";
  designMark.hidden = true;
  const discard = Object.assign(document.createElement("button"), {
    type: "button",
    textContent: "Discard",
    title: "Drop the unsaved changes to this profile",
    disabled: true,
  });
  discard.dataset.testid = "sheet-discard";
  const fit = Object.assign(document.createElement("button"), { type: "button", textContent: "Fit" });
  // "32 stations, 1 removed, 3 errors" (the old page's line summary, S82)
  const summary = Object.assign(document.createElement("span"), { className: "muted" });
  summary.dataset.testid = "station-summary";
  const saveBtn = Object.assign(document.createElement("button"), {
    type: "button",
    textContent: "Save",
    title: "Save the unsaved changes to this line (Ctrl+S, or Enter in a field)",
    disabled: true,
  });
  saveBtn.dataset.testid = "sheet-save";
  saveBtn.onclick = () => void host.runCommand("core.save");
  // Maximise (the dock's, shell/maximise.ts): the sheet fills the window, the plot its whole height (the old page's
  // 1,230 px wide plot at 1,600 px); Shift+F or a double-click on the tab does the same. The tables fold away under
  // the Tables button (folded by default while maximised), so the plot keeps the height.
  const maxBtn = Object.assign(document.createElement("button"), {
    type: "button",
    textContent: "Maximise",
    title: "Fill the window with the sheet (Shift+F, or double-click its tab); again to put it back",
  });
  maxBtn.dataset.testid = "sheet-maximise";
  maxBtn.setAttribute("aria-pressed", "false");
  maxBtn.onclick = () => maxBtn.dispatchEvent(new Event(MAXIMISE_REQUEST, { bubbles: true }));
  const tablesBtn = Object.assign(document.createElement("button"), {
    type: "button",
    textContent: "Tables",
    title: "Show or fold away the stations and PVI tables under the plot",
  });
  tablesBtn.dataset.testid = "sheet-tables";
  // Show: Rail, Rail + box or Box, as on the old page (S.show): the structure outlines over the rail, or the rail alone.
  const showGroup = document.createElement("span");
  showGroup.className = "sheet-show";
  showGroup.dataset.testid = "sheet-show";
  showGroup.setAttribute("role", "group");
  showGroup.setAttribute("aria-label", "Show");
  const SHOW_KEY = "cr.sheet.show";
  let show: ShowMode = (() => {
    try {
      const v = sessionStorage.getItem(SHOW_KEY);
      return v === "rail" || v === "box" ? v : "railbox";
    } catch {
      return "railbox";
    }
  })();
  const showBtns = (
    [
      ["rail", "Rail", "The rail alone, coloured by structure"],
      ["railbox", "Rail + box", "The rail with the tunnel, box and viaduct outlines"],
      ["box", "Box", "The structures, the tunnels' rail left to the outline"],
    ] as const
  ).map(([mode, label, tip]) => {
    const b = Object.assign(document.createElement("button"), { type: "button", textContent: label, title: tip });
    b.dataset.show = mode;
    b.onclick = () => {
      show = mode;
      try {
        sessionStorage.setItem(SHOW_KEY, mode);
      } catch {
        /* the choice lasts for this pane */
      }
      for (const q of showBtns) q.setAttribute("aria-pressed", String(q.dataset.show === show));
      draw();
    };
    return b;
  });
  for (const q of showBtns) q.setAttribute("aria-pressed", String(q.dataset.show === show));
  showGroup.append(...showBtns);
  bar.append(
    title,
    designMark,
    summary,
    profileInfo,
    solveInfo,
    serverInfo,
    pendingMark,
    saveBtn,
    discard,
    fit,
    showGroup,
    tablesBtn,
    maxBtn,
  );
  // The tools row: the old page's toolbar (claude/hub_maps/profiles_parity.md, C: R1, R7 to R13, R16 to R20, R49).
  const toolsRow = Object.assign(document.createElement("div"), { className: "sheet-tools" });
  toolsRow.dataset.testid = "sheet-tools";
  const mk = (text: string, title: string, testid: string, run: () => void): HTMLButtonElement => {
    const b = Object.assign(document.createElement("button"), { type: "button", textContent: text, title });
    b.dataset.testid = testid;
    b.onclick = run;
    return b;
  };
  const group = (label: string, ...kids: HTMLElement[]): HTMLSpanElement => {
    const g = Object.assign(document.createElement("span"), { className: "sheet-group" });
    g.setAttribute("role", "group");
    g.setAttribute("aria-label", label);
    g.append(...kids);
    return g;
  };
  // the line picker: every line with its length (buildLineSel 3341), Metro first
  const lineSel = document.createElement("select");
  lineSel.dataset.testid = "line-picker";
  lineSel.setAttribute("aria-label", "Line");
  lineSel.title = "Every line with its length: pick one to show it here";
  lineSel.onchange = () => {
    if (lineSel.value && lineSel.value !== target?.sectionId) host.select({ kind: "section", id: lineSel.value });
  };
  let tool: Tool = "move";
  let brush: Brush = "auto";
  const toolBtns = (
    [
      ["move", "Move", "Drag stations and bend points (M)"],
      ["paint", "Paint", "Paint structure type along the line (P)"],
      [
        "ground",
        "Ground",
        "Draw the ground: double-click to start a line or add a point to one, drag the points, Del removes one (G)",
      ],
    ] as const
  ).map(([t, label, tip]) => {
    const b = mk(label, tip, `tool-${t}`, () => setTool(t));
    b.dataset.tool = t;
    return b;
  });
  const brushBar = group("Structure brush");
  brushBar.classList.add("sheet-brushes");
  brushBar.dataset.testid = "sheet-brushes";
  const BRUSHES: Brush[] = ["auto", ...TYPE_BRUSHES, "shaft", "tf:twin", "tf:bore", "tf:auto"];
  const brushBtns = BRUSHES.map((k) => {
    const b = mk(BRUSH_LABELS[k], BRUSH_TIPS[k] ?? `Paint ${BRUSH_LABELS[k]}`, `brush-${k.replace(":", "-")}`, () => {
      brush = k;
      for (const q of brushBtns) q.setAttribute("aria-pressed", String(q.dataset.brush === brush));
      setTool("paint");
    });
    b.dataset.brush = k;
    if ((TYPE_BRUSHES as readonly string[]).includes(k)) {
      const sw = Object.assign(document.createElement("span"), { className: "swatch" });
      sw.style.background = typeColour(k);
      b.prepend(sw);
    }
    b.setAttribute("aria-pressed", String(k === brush));
    return b;
  });
  brushBar.append(...brushBtns);
  const setTool = (t: Tool) => {
    tool = t;
    for (const b of toolBtns) b.setAttribute("aria-pressed", String(b.dataset.tool === t));
    brushBar.style.opacity = t === "paint" ? "1" : "0.55";
    canvas.dataset.tool = t;
    if (t !== "ground" && selected?.kind === "gp") {
      selected = null;
      renderCard();
    }
    draw();
  };
  const settingsBtn = mk("Settings", "The design settings (params) for every Metro line", "settings-open", () =>
    toggleSettings(),
  );
  settingsBtn.setAttribute("aria-expanded", "false");
  const helpBtn = mk("?", "How to edit: the tools, the keys and the mouse", "help-open", () => toggleHelp());
  helpBtn.setAttribute("aria-expanded", "false");
  toolsRow.append(
    group("Line", lineSel),
    group("Tool", ...toolBtns),
    brushBar,
    group(
      "Undo",
      mk("Undo", "Undo (Ctrl+Z)", "sheet-undo", () => void host.runCommand("core.undo")),
      mk("Redo", "Redo (Ctrl+Shift+Z)", "sheet-redo", () => void host.runCommand("core.redo")),
    ),
    group(
      "Zoom",
      mk("−", "Zoom out (-)", "zoom-out", () => zoomBy(1 / 0.6)),
      mk("+", "Zoom in (+)", "zoom-in", () => zoomBy(0.6)),
    ),
    group(
      "Export",
      mk("Export PNG", "The whole line's long section as a picture", "export-png", () => void exportAs("png")),
      mk(
        "Export JSON",
        "The profile, its stations and summary, and a sample every 10 m",
        "export-json",
        () => void exportAs("json"),
      ),
      mk(
        "Export GeoJSON",
        "The designed rail (3D, rail level) by structure, and the stations, as GeoJSON",
        "export-geojson",
        () => void exportAs("geojson"),
      ),
      mk(
        "Export KMZ",
        "The designed rail (3D, rail level) and the stations, for Google Earth",
        "export-kmz",
        () => void exportAs("kmz"),
      ),
    ),
    group("Settings", settingsBtn, helpBtn),
  );
  const pop = Object.assign(document.createElement("div"), { className: "sheet-popover" });
  pop.hidden = true;
  pop.dataset.testid = "sheet-popover";
  const notice = Object.assign(document.createElement("div"), { className: "sheet-notice" });
  notice.dataset.testid = "sheet-notice";
  notice.setAttribute("role", "status");
  const canvasWrap = document.createElement("div");
  canvasWrap.className = "sheet-canvas";
  const canvas = document.createElement("canvas");
  canvas.dataset.testid = "sheet-canvas";
  // the tool the sheet opens with: Move, the brushes dimmed until Paint (setTool 3728)
  canvas.dataset.tool = tool;
  for (const b of toolBtns) b.setAttribute("aria-pressed", String(b.dataset.tool === tool));
  brushBar.style.opacity = "0.55";
  canvas.tabIndex = 0;
  canvas.setAttribute("role", "img");
  canvas.setAttribute(
    "aria-label",
    "Long section. Click a station or a PVI to select it; drag it up or down to set its level, Alt + drag a station to slide it; drag elsewhere to pan; wheel to zoom; double-click the rail to add a PVI. Arrows nudge the selection (Alt + Left or Right slides a station, Page Up or Down tilts it), [ and ] step through the stations, E eases the bends, Delete twice removes a station, F shows the whole line, Shift+F maximises the sheet, Esc clears.",
  );
  // What the canvas drew, in words: station names and levels, grades. Hidden from sight, read by screen readers.
  const textLayer = document.createElement("ul");
  textLayer.className = "sheet-text";
  textLayer.dataset.testid = "sheet-labels";
  textLayer.setAttribute("aria-label", "On the sheet");
  canvasWrap.append(canvas, textLayer);
  const card = document.createElement("div");
  card.className = "sheet-card";
  card.dataset.testid = "station-card";
  const tables = document.createElement("div");
  tables.className = "sheet-table";
  // the side column: the selection's card over the line panel (the old page's side cards)
  const linePanel = document.createElement("div");
  linePanel.className = "sheet-line";
  const side = Object.assign(document.createElement("div"), { className: "sheet-side" });
  side.dataset.testid = "sheet-side";
  side.append(card, linePanel);
  root.append(bar, toolsRow, notice, canvasWrap, side, tables, pop);
  el.append(root);

  let maximised = el.dataset.maximised === "1";
  /** Whether the tables show, kept for the session apart for the maximised sheet and the docked one. */
  const tablesKey = () => `cr.sheet.tables.${maximised ? "max" : "docked"}`;
  const tablesShown = (): boolean => {
    try {
      const v = sessionStorage.getItem(tablesKey());
      return v === null ? !maximised : v === "1";
    } catch {
      return !maximised;
    }
  };
  const showMode = () => {
    root.classList.toggle("maximised", maximised);
    maxBtn.textContent = maximised ? "Restore" : "Maximise";
    maxBtn.setAttribute("aria-pressed", String(maximised));
    const shown = tablesShown();
    root.classList.toggle("tables-hidden", !shown);
    // folded away, so the plot takes the sheet's whole height
    tables.style.display = shown ? "" : "none";
    tablesBtn.setAttribute("aria-pressed", String(shown));
  };
  showMode();
  const onMaximised = (e: Event) => {
    maximised = !!(e as CustomEvent<boolean>).detail;
    showMode();
  };
  el.addEventListener(MAXIMISED_EVENT, onMaximised);
  tablesBtn.onclick = () => {
    try {
      sessionStorage.setItem(tablesKey(), tablesShown() ? "0" : "1");
    } catch {
      /* the choice lasts until the next change of mode */
    }
    showMode();
  };

  let view = host.view();
  let target: Target | null = null;
  let input: SectionInput | null = null;
  /** The section's stops and platforms; null when they could not be read (the stations then follow the input). */
  let frame: StationFrame | null = null;
  let sectionName = "";
  /** true when the profile can be edited in this view, else why not. */
  let editable: true | string = "Loading…";
  /** Why the view hides the section, when it does (a dated view and an undated section). */
  let timeNote: string | null = null;
  /** Cells whose text is not a number, by label, with the reason. */
  const bad = new Map<string, string>();
  let local: VerticalRail | null = null;
  /** The section's StationInput (the input of station.facts@1), null when the hub could not give it. */
  let si: StationInput | null = null;
  /** station.facts@1 of the draft, one per platform; null until it has run. */
  let facts: StationFact[] | null = null;
  /** The section's SectionSolveInput (the input of section.solve@1), null when the hub could not give it. */
  let ssi: SectionSolveInput | null = null;
  /** section.solve@1 of the draft, the last one that landed (the bands keep it during a drag); null until then. */
  let solved: SolvedSection | null = null;
  /** The design the sheet draws where the profile holds none (design.ts): the last one section.solve@1 gave that
   * lays something in, kept while the profile does not hold it (so a Ctrl+Z back to the record draws it at once). */
  let design: SheetDesign | null = null;
  /** How many designs have been laid in (a test waits for it). */
  let designRev = 0;
  let fullBusy = false;
  let fullAgain = false;
  /** Counts the drafts the sheet has solved the rail for: a full solve that started on an older one runs again. */
  let editRev = 0;
  let factsBusy = false;
  let factsAgain = false;
  /** The section's platform records, by id (the side edit drafts them). */
  let platformRecs = new Map<string, Rec>();
  /** Whether platform records can be written in this view (the side), else why not. */
  let sideEditable: true | string = "Loading…";
  /** What the bands drew last, as numbers (the marks() hook on the canvas, for the tests). */
  let lastMarks: SheetMark[] = [];
  /** A Delete pressed once on a station: a second within 4 s removes it (S46). */
  let removeArmed: { id: string; until: number } | null = null;
  let server: { rail_m: Float64Array; step_m: number; key: string } | null = null;
  let range: [number, number] | null = ((ctx.state as { range?: [number, number] } | undefined)?.range ?? null) as
    | [number, number]
    | null;
  let cursor: number | null = host.store.getState().c;
  let selected: Handle | null = null;
  let shownSection: string | null = (ctx.state as { section?: string } | undefined)?.section ?? null;
  let stopWatch: (() => void) | null = null;
  /** The profile or section the sheet shows. A selection the sheet cannot show leaves it on its section. */
  let shownSel: RecordRef | null = null;
  /** The profile revision the hub was last asked to solve ("layer:version"). */
  let asked: string | null = null;
  /** How many PVI rows the table was built with: a change in the count rebuilds it even while a cell is focused. */
  let builtPvis = -1;
  /** The "+ PVI at the cursor" button, enabled once a chainage is picked. */
  let addButton: HTMLButtonElement | null = null;
  let solving = false;
  let again = false;
  /** A rail solve is asked for and starts after the next frame (solve()). */
  let solveDue = false;
  /** Starts the due solve when no frame comes (a hidden page): DUE_MS after it was asked for. */
  let dueTimer: ReturnType<typeof setTimeout> | null = null;
  const DUE_MS = 100;
  const WARM_SOLVES = 16;
  /** A task right after the frame: the solve due starts there, after the frame's paint and raster. */
  const afterFrame = new MessageChannel();
  afterFrame.port1.onmessage = () => startDue();
  let dueSince = 0;
  /** The last key down or up in the sheet, and how long a burst of keys may hold a solve back. */
  let lastKeyAt = -1e9;
  const KEY_QUIET_MS = 8;
  const DUE_MAX_MS = 120;
  const keyAt = () => {
    lastKeyAt = performance.now();
  };
  el.addEventListener("keydown", keyAt, true);
  el.addEventListener("keyup", keyAt, true);
  /** Work that waits for the rail solve out to land (landed() runs it before the paint). */
  const railWaiters: (() => void)[] = [];
  /** Run fn now, or as the rail solve out lands; resolves once it ran. */
  const afterRail = (fn: () => void): Promise<void> => {
    if (!solving) {
      fn();
      return Promise.resolve();
    }
    return new Promise((resolve) =>
      railWaiters.push(() => {
        try {
          fn();
        } finally {
          resolve();
        }
      }),
    );
  };
  let generation = 0;
  let refreshTimer: ReturnType<typeof setTimeout> | null = null;
  // The hub keeps this pane's goal fresh (watch_s) at priority 0 while the pane has the focus and 1 while it is open;
  // a section the sheet leaves goes back to the background (5). The watch is renewed while the pane is open.
  const WATCH_S = 600;
  let focused: { sectionId: string; token: string } | null = null;
  let renewTimer: ReturnType<typeof setInterval> | null = null;
  const priority = () => ((ctx.isActive?.() ?? true) ? 0 : 1);
  const release = () => {
    if (focused) void host.api.focus(SOLVE_JOB, focused.sectionId, focused.token, 5);
    focused = null;
  };
  const showPending = () => {
    const what = target ? liveBoard.pendingFor(target.sectionId, viewToken(view)) : null;
    pendingMark.hidden = !what;
    const text = what ? `${what}…` : "";
    if (pendingMark.textContent !== text) pendingMark.textContent = text;
    pendingMark.title =
      what === "importing" ? "A change to this line's sources is being taken in" : "The hub is solving this line again";
  };
  const bands = () => host.registry.bandList();
  const canEdit = () => editable === true && !!target?.profile;
  /** The read-only reason in Ben's terms: main refuses a kind the old hub owns, named by the line. */
  const editMessage = (ed: true | string): true | string =>
    ed === true || !target?.profile || view.layer !== "main"
      ? ed
      : `The old hub owns ${sectionName}'s profile on main: switch to a scenario (Layer, at the top) to edit it.`;

  /** The profile as Ben's draft or record holds it: the draft's working copy, else the record. */
  const raw = (): ProfileData | null => {
    const p = target?.profile;
    if (!p) return null;
    return (host.drafts.get(p.kind, p.id, view)?.body ?? bodyOf(p)).data as ProfileData;
  };
  let shownMemo: { from: unknown; design: SheetDesign | null; out: ProfileData } | null = null;
  /**
   * The profile data to show, solve and hit-test: the draft's working copy, else the record, with the design laid in
   * where the profile holds none (design.ts: the default design of Lines 10, 11 and 13, Line 2b on the current stops).
   * Never written as such: edit() lays the design into the draft with Ben's first edit, in the same undo step.
   */
  const data = (): ProfileData | null => {
    const p = target?.profile;
    if (!p) return null;
    const d = host.drafts.get(p.kind, p.id, view);
    const from = d ? d.body : p;
    if (shownMemo && shownMemo.from === from && shownMemo.design === design) return shownMemo.out;
    const r = (d?.body ?? bodyOf(p)).data as ProfileData;
    const out = laidIn(r, design);
    shownMemo = { from, design, out };
    return out;
  };
  /** The bar's mark of a design drawn that is not Ben's record ("default design (not saved)"). */
  const showDesign = () => {
    const r = raw();
    const note = r ? designNote(r, design) : null;
    designMark.hidden = !note;
    if (designMark.textContent !== (note ?? "")) designMark.textContent = note ?? "";
    designMark.title = note
      ? "Drawn as the old page drew it, and not saved: it becomes this line's profile with your first edit (Ctrl+Z takes that back)"
      : "";
  };

  const draftKey = () => (target?.profile ? host.drafts.key(target.profile.kind, target.profile.id, view) : null);

  /** A platform's name: from the section's platforms, else through the name cache (the end of its id until then). */
  const platformName = (id: string): string => {
    for (const list of frame?.platforms.values() ?? []) for (const p of list) if (p.id === id) return p.name;
    const n = host.names.peek("platform", id, view);
    if (n) return n;
    void host.names.get("platform", id, view);
    return shortId(id);
  };

  /** The chainage of a platform's stop (the point a slid platform hangs on); null when the frame does not know it. */
  const stopOf = (id: string): number | null => {
    if (!frame) return null;
    for (const stop of frame.stops) if (frame.platforms.get(stop.id)?.some((p) => p.id === id)) return stop.c;
    return null;
  };

  const showNotice = () => {
    const lines: string[] = [];
    if (editable !== true && target) lines.push(editable);
    if (timeNote) lines.push(timeNote);
    for (const [label, why] of bad) lines.push(`${label}: ${why}`);
    // Never hidden: the sheet is a grid of four rows, and an empty notice is a row of no height (shell.css).
    notice.textContent = lines.join(" ");
  };

  /** The chainage in the URL, in the status bar, so it shows whichever pane Ben looks at. */
  const showChainage = () => {
    const c = host.store.getState().c;
    if (c === null || !target) host.status({ id: "sheet.chainage", remove: true });
    else
      host.status({
        id: "sheet.chainage",
        text: `c ${formatChainage(c, host.units)} on ${sectionName}`,
        level: "info",
        order: 5,
        title: "The chainage picked on the line sheet",
      });
  };

  const showProfile = () => {
    const p = target?.profile;
    const d = draftKey();
    const dirty = d !== null && host.drafts.dirty(d);
    discard.disabled = !dirty;
    showDesign();
    if (!target) {
      profileInfo.textContent = "";
      return;
    }
    profileInfo.textContent = p
      ? `${sectionName} profile, version ${p.version} ${layerPhrase(p.layer)}${dirty ? ", unsaved changes" : ""}`
      : "no profile record";
    profileInfo.dataset.version = p ? String(p.version) : "";
    profileInfo.dataset.layer = p ? p.layer : "";
  };

  /**
   * Ask for a rail solve of the draft as it is now. It starts in a task of its own right after the next frame (or
   * at once on a page with no frames), never inside a frame's paint and raster: one rail solve and one paint per
   * frame, never at once, so its answer never waits on a paint (speed; see draw()).
   */
  const solve = async () => {
    if (!input) return;
    if (solving) {
      again = true;
      return;
    }
    solveInfo.dataset.busy = "1";
    if (solveDue) return;
    solveDue = true;
    dueSince = performance.now();
    draw();
    dueTimer ??= setTimeout(startDue, DUE_MS);
  };
  /** Start the solve that is due, unless one is out (it lands first). A burst of keys (a level typed into a cell)
   * is let finish first, up to DUE_MAX_MS: Chrome holds a worker's answer back until the frame after a key, so a
   * solve started between two keys of a burst waits a frame for nothing, and its answer is stale at once. */
  const startDue = () => {
    if (dueTimer) clearTimeout(dueTimer);
    dueTimer = null;
    if (!solveDue || solving) return;
    const now = performance.now();
    if (now - lastKeyAt < KEY_QUIET_MS && now - dueSince < DUE_MAX_MS) {
      requestAnimationFrame(() => afterFrame.port2.postMessage(0));
      dueTimer = setTimeout(startDue, DUE_MS);
      return;
    }
    void runSolve();
  };
  const runSolve = async () => {
    if (!input) {
      solveDue = false;
      solveInfo.dataset.busy = "0";
      return;
    }
    solveDue = false;
    solving = true;
    solveInfo.dataset.busy = "1";
    const gen = generation;
    try {
      const inp = solveInput(input, data(), frame);
      editRev++;
      const t0 = performance.now();
      const out = await host.engine.solve("vertical.rail", inp, {
        engineBuild: host.events.status().engine_build ?? undefined,
      });
      const total = performance.now() - t0;
      if (gen !== generation) return;
      local = out.result as VerticalRail;
      solveInfo.textContent = `local solve ${total.toFixed(1)} ms (engine ${out.ms.toFixed(1)} ms)`;
      solveInfo.dataset.ms = String(total);
      solveInfo.dataset.rev = String(Number(solveInfo.dataset.rev ?? 0) + 1);
      compare();
      if (!si) {
        showSummary();
        fullSoon();
      }
      // The panel and tables follow the facts solve that comes next; without one they follow the rail.
      if (!si && tableDue) {
        tableDue = false;
        refreshTable();
      } else if (selected?.kind === "station" && !si) renderCard();
      factsSoon();
    } catch (e) {
      local = null;
      if (tableDue) {
        tableDue = false;
        refreshTable();
      }
      solveInfo.textContent =
        host.engine.state() === "unavailable"
          ? (host.engine.reason() ?? "no local engine")
          : `local solve failed: ${String((e as Error).message ?? e)}`;
    } finally {
      solving = false;
      if (profileDue) {
        profileDue = false;
        showProfile();
      }
      // Edits made while this solve ran are solved after the paint of this one (the frame's callback starts it), so
      // a solve never waits on a paint and a paint never shows a rail older than its marks (speed).
      if (again) {
        again = false;
        solveDue = true;
        dueSince = performance.now();
        dueTimer ??= setTimeout(startDue, DUE_MS);
      } else if (!solveDue) solveInfo.dataset.busy = "0";
      landed();
    }
  };

  /** A platform's side as its draft has it, when Ben changed it there (not yet saved). */
  const sideDraft = (pid: string): { side: "side" | "island"; source: "ben" } | null => {
    const rec = platformRecs.get(pid);
    if (!rec) return null;
    const d = host.drafts.get("platform", pid, view);
    const side = (d?.body.data as Record<string, unknown> | undefined)?.side;
    return d && (side === "side" || side === "island") ? { side, source: "ben" } : null;
  };

  /**
   * station.facts@1 of the draft, right after each rail solve (claude/hub_maps/profiles_parity.md 0.2): the bands and
   * the panel read it. A burst of edits runs it once more at the end, as the rail solve does.
   */
  /** The facts follow a burst of edits once it pauses (30 ms), so a run of keystrokes or a drag re-solves the rail
   * at each step and works the stations out once; they run in a worker of their own, never ahead of a rail solve. */
  let factsTimer: ReturnType<typeof setTimeout> | null = null;
  const factsSoon = () => {
    if (factsTimer) clearTimeout(factsTimer);
    factsTimer = setTimeout(() => {
      factsTimer = null;
      if (solving || solveDue) factsSoon();
      else void solveFacts();
    }, 30);
  };
  let factsEngine: EngineHandle | null = null;
  const solveFacts = async () => {
    if (!si) return;
    if (factsBusy) {
      factsAgain = true;
      return;
    }
    factsBusy = true;
    const gen = generation;
    try {
      const inp = factsInput(si, data(), frame, sideDraft);
      const t0 = performance.now();
      factsEngine ??= createEngine();
      const out = await factsEngine.solve("station.facts", inp, {
        engineBuild: host.events.status().engine_build ?? undefined,
      });
      if (gen !== generation) return;
      const apply = () => {
        if (gen !== generation) return;
        facts = (out.result as { stations: StationFact[] }).stations;
        fullSoon();
        solveInfo.dataset.factsMs = String(performance.now() - t0);
        solveInfo.dataset.factsRev = String(Number(solveInfo.dataset.factsRev ?? 0) + 1);
        showSummary();
        renderLineSoon();
        // the tables follow at the end of a drag (endDrag): rebuilding them each step held the frame
        if (!factsAgain && editingDrag()) tableDue = true;
        else if (!factsAgain) {
          tableDue = false;
          refreshTable();
          renderCard();
        }
        draw();
      };
      // never while a rail solve is out: its answer would wait behind the tables (speed)
      await afterRail(apply);
    } catch (e) {
      solveInfo.title = `station facts failed: ${String((e as Error).message ?? e)}`;
      tableDue = false;
      refreshTable();
      renderCard();
    } finally {
      factsBusy = false;
      if (factsAgain) {
        factsAgain = false;
        void solveFacts();
      }
    }
  };

  /**
   * section.solve@1 of the draft, the whole solve (claude/hub_maps/engine_port_plan.md, section 8), in a worker of
   * its own after the rail and the station facts: never during a drag (it waits for the pointer to come up), and
   * only once a burst of edits has paused for 150 ms. The bands draw the last one that landed, with the live rail.
   */
  let fullTimer: ReturnType<typeof setTimeout> | null = null;
  const FULL_PAUSE_MS = 150;
  const fullSoon = () => {
    if (!ssi) return;
    if (fullTimer) clearTimeout(fullTimer);
    fullTimer = setTimeout(() => {
      fullTimer = null;
      if (solving || solveDue || factsBusy || (drag && drag.kind !== "pan" && drag.kind !== "overview")) fullSoon();
      else void solveFull();
    }, FULL_PAUSE_MS);
  };
  /** A design from a whole solve: kept when it lays something in (design.ts keepsDesign), and when it changes what
   * the sheet draws, the rail, the facts and the tables follow it. */
  const takeDesign = (next: SheetDesign | undefined) => {
    if (!next || !keepsDesign(next) || deepEqual(next as never, design as never)) {
      showDesign();
      return;
    }
    const r = raw();
    const before = r ? designOps(r, design) : [];
    design = next;
    designRev++;
    solveInfo.dataset.designRev = String(designRev);
    showDesign();
    if (r && deepEqual(before as never, designOps(r, design) as never)) return;
    tableDue = true;
    void solve();
  };
  let fullEngine: EngineHandle | null = null;
  /** The input the full solve's worker holds (stash), so a new one from the hub is sent again. */
  let stashedSsi: SectionSolveInput | null = null;
  const SSI_STASH = "section_solve_input";
  const SOLVED_TYPED = ["limit_tube", "limit_box", "ground.finished", "ground.surface", "ground.bed"] as const;
  const solveFull = async () => {
    if (!ssi) return;
    if (fullBusy) {
      fullAgain = true;
      return;
    }
    fullBusy = true;
    const gen = generation;
    const rev = editRev;
    try {
      // the server's input crosses to the worker once (stash); each solve sends only the draft's own members, and
      // the long arrays come back moved, not copied, so the page's thread is never held by the whole solve
      // the profile as Ben's draft or record holds it, never with the design laid in: its answer says which design
      // the profile is drawn with (design), and is the same solve either way (engine/test/port/default_design.test.ts)
      const inp = solveInputOf(ssi, raw(), sideDraft);
      const t0 = performance.now();
      fullEngine ??= createEngine();
      if (stashedSsi !== ssi) {
        await fullEngine.stash(SSI_STASH, ssi);
        stashedSsi = ssi;
      }
      const ov = settingsOverride();
      const out = await fullEngine.solve(
        "section.solve",
        {
          doc: inp.doc,
          platforms: inp.platforms,
          access: inp.access,
          ...(ov ? { settings: { ...ssi.settings, ...ov } } : {}),
        },
        { engineBuild: host.events.status().engine_build ?? undefined, base: SSI_STASH, typed: SOLVED_TYPED },
      );
      if (gen !== generation) return;
      await afterRail(() => {
        if (gen !== generation) return;
        solved = out.result as SolvedSection;
        takeDesign(solved.design);
        solveInfo.dataset.fullMs = String(performance.now() - t0);
        solveInfo.dataset.fullEngineMs = String(out.ms);
        solveInfo.dataset.fullRev = String(Number(solveInfo.dataset.fullRev ?? 0) + 1);
        if (rev !== editRev) fullAgain = true;
        draw();
        renderLineSoon();
        if (selected?.kind === "pvi" || selected?.kind === "gp") renderCard();
      });
    } catch (e) {
      solveInfo.dataset.fullError = String((e as Error).message ?? e);
    } finally {
      fullBusy = false;
      if (fullAgain) {
        fullAgain = false;
        fullSoon();
      }
    }
  };

  /** The line's station summary in the bar, and the Save button's count of unsaved station edits. */
  const showSummary = () => {
    const fs = facts ?? [];
    const liveN = fs.filter((f) => !f.deleted).length;
    const removed = fs.length - liveN;
    const errors = fs.reduce((n, f) => n + f.flags.filter((x) => x.sev === "error").length, 0);
    const warns = fs.reduce((n, f) => n + f.flags.filter((x) => x.sev === "warn").length, 0);
    summary.textContent = fs.length
      ? `${liveN} stations${removed ? `, ${removed} removed` : ""}${errors ? `, ${errors} error${errors > 1 ? "s" : ""}` : ""}${warns ? `, ${warns} warning${warns > 1 ? "s" : ""}` : ""}`
      : "";
    const n = changedStations().size;
    const dirty = !!draftKey() && host.drafts.dirty(draftKey() as string);
    saveBtn.disabled = !dirty && n === 0;
    saveBtn.textContent = n ? `Save (${n} station${n > 1 ? "s" : ""})` : "Save";
  };

  /** The platforms whose station values the drafts change (the profile's station fields, or the side). */
  const changedStations = (): Set<string> => {
    const out = new Set<string>();
    const p = target?.profile;
    const cur = raw();
    if (p && cur) {
      const was = p.data as ProfileData;
      for (const f of STATION_PROFILE_FIELDS) {
        const a = cur[f];
        const b = was[f];
        if (JSON.stringify(a) === JSON.stringify(b)) continue;
        if (Array.isArray(a) || Array.isArray(b)) {
          if (f === "del" || f === "gapfill") {
            const A = new Set((a as string[] | undefined) ?? []);
            const B = new Set((b as string[] | undefined) ?? []);
            for (const k of A) if (!B.has(k)) out.add(k);
            for (const k of B) if (!A.has(k)) out.add(k);
          }
          continue;
        }
        const A = (a ?? {}) as Record<string, unknown>;
        const B = (b ?? {}) as Record<string, unknown>;
        for (const k of new Set([...Object.keys(A), ...Object.keys(B)]))
          if (JSON.stringify(A[k]) !== JSON.stringify(B[k])) out.add(k);
      }
    }
    for (const id of platformRecs.keys()) if (sideDraft(id)) out.add(id);
    return out;
  };

  /** A few silent solves of the loaded input before the first drawn one, so the engine's code is compiled (and an
   * edit re-solves within a frame) by the time Ben types. */
  const warm = async (gen: number) => {
    if (!input) return;
    const inp = solveInput(input, data(), frame);
    // The solves an edit makes, a level and a platform grade moved each way, until the worker's compiler has them:
    // the first edit then solves as fast as the hundredth (speed).
    for (let i = 0; i < WARM_SOLVES && gen === generation; i++) {
      const d = i % 2 ? 0.5 : -0.5;
      const k = i % Math.max(1, inp.pvi.length);
      const j = i % Math.max(1, inp.stations.length);
      const step = {
        ...inp,
        pvi: inp.pvi.map((p, n) => (n === k ? { ...p, z_m: p.z_m + d } : p)),
        stations: inp.stations.map((s, n) => (n === j ? { ...s, grade_permille: (s.grade_permille ?? 0) + d } : s)),
      };
      try {
        await host.engine.solve("vertical.rail", step);
      } catch {
        return;
      }
    }
  };

  const compare = () => {
    if (!server) {
      serverInfo.textContent = "";
      return;
    }
    // the hub solves the profile as saved (profiles.solve_section): with a design laid in (design.ts) the sheet's rail
    // is another design's, and a difference would say nothing
    const r = raw();
    const laid = !!r && designOps(r, design).length > 0;
    const d = local && !laid ? maxDiff(local.rail_m, server.rail_m) : null;
    serverInfo.textContent = `server ${server.key.slice(0, 8)}${laid ? ", the profile as saved" : d === null ? "" : `, max diff ${host.units.format(d, "m", 3)} ${host.units.label("m")}`}`;
    serverInfo.dataset.key = server.key;
  };

  /** Ask the hub to solve the section in this view (POST /compute). A hit answers with its key at once; otherwise
   * the job runs and its result event brings the key. The sheet asks when it opens a section and after every new
   * revision of its profile (a save here, in another tab, an undo), so the server's rail follows each save whether
   * or not the hub keeps a goal for this view. */
  const requestSolve = async () => {
    if (!target) return;
    const gen = generation;
    const p = target.profile;
    asked = p ? `${p.layer}:${p.version}` : "";
    try {
      const token = viewToken(view);
      if (focused && (focused.sectionId !== target.sectionId || focused.token !== token)) release();
      focused = { sectionId: target.sectionId, token };
      const r = await host.api.compute(SOLVE_JOB, target.sectionId, token, priority(), WATCH_S);
      if (gen === generation && r.key && (r.state === "hit" || r.state === "ok" || r.state === "done"))
        void loadServer(r.key);
    } catch {
      /* the server's rail is a comparison only; the status bar shows a hub that is down */
    }
  };

  const loadServer = async (key?: string | null) => {
    if (!target) return;
    const gen = generation;
    const k = key ?? (await host.api.latestResult(SOLVE_JOB, target.sectionId, viewToken(view)).catch(() => null));
    if (!k || gen !== generation) return;
    try {
      const meta = await host.api.result(k);
      const arr = await host.api.resultArray(k, "rail_m");
      if (gen !== generation) return;
      const step = Number((meta.meta as Record<string, unknown> | undefined)?.step_m ?? input?.step_m ?? 2);
      server = { rail_m: toFloat64(arr.dtype, arr.buffer), step_m: step, key: k };
      compare();
      draw();
    } catch (e) {
      serverInfo.textContent = `server result unavailable: ${String((e as Error).message ?? e)}`;
    }
  };

  /** The section's stops and platforms in the view, sorted as the server sorts them. */
  const loadFrame = async (sectionId: string): Promise<StationFrame | null> => {
    try {
      const [stops, platforms] = await Promise.all([
        listAll(host, "stop", view, { parent: sectionId }),
        listAll(host, "platform", view, { parent: sectionId }),
      ]);
      host.names.learn(platforms, view);
      host.names.learn(stops, view);
      platformRecs = new Map(platforms.map((p) => [p.id, p]));
      return stationFrame(stops, platforms);
    } catch {
      return null;
    }
  };

  /** Whether the view shows the section at its instant; a note when it does not (9.16). */
  const loadTimeNote = async (sectionId: string): Promise<string | null> => {
    if (view.year === null) return null;
    try {
      const { items } = await host.records.list("section", view, { ids: sectionId, limit: 1 });
      if (items.length) return null;
    } catch {
      return null;
    }
    const when = view.month === null ? String(view.year) : `${view.year}-${String(view.month).padStart(2, "0")}`;
    return `${sectionName} is not open at ${when} (it has no dates there, and undated records count only at the present), so the map leaves it out; the sheet shows its design as it stands.`;
  };

  /** Read the input and the frame again (a new revision of a record they are built from), keeping the view. */
  const refreshInput = async () => {
    if (!target) return;
    const gen = generation;
    try {
      // The station input is the heavier read: it follows on its own, so the rail never waits for it.
      const sectionId = target.sectionId;
      void host.api
        .stationInput(sectionId, view)
        .then((sti) => {
          if (gen !== generation) return;
          si = sti;
          void solveFacts();
        })
        .catch(() => undefined);
      const [inp, fr] = await Promise.all([host.api.sectionInput(sectionId, view), loadFrame(sectionId)]);
      if (gen !== generation) return;
      input = inp;
      frame = frameFor(fr, inp) ?? frameFor(frame, inp);
      refreshTable();
      void solve();
      // the whole solve's input last: the heaviest read never holds up the rail's
      void host.api
        .solveInput(sectionId, view)
        .then((x) => {
          if (gen !== generation) return;
          ssi = x;
          fullSoon();
        })
        .catch(() => undefined);
    } catch {
      /* the input stays as it was; the next revision tries again */
    }
  };
  const scheduleRefresh = () => {
    if (refreshTimer) clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => void refreshInput(), 250);
  };

  const load = async () => {
    generation++;
    const gen = generation;
    view = host.view();
    stopWatch?.();
    stopWatch = null;
    target = null;
    input = null;
    frame = null;
    local = null;
    si = null;
    facts = null;
    ssi = null;
    solved = null;
    design = null;
    shownMemo = null;
    designMark.hidden = true;
    server = null;
    asked = null;
    builtPvis = -1;
    selected = null;
    paintRows = null;
    checkRows = null;
    checkNote = null;
    linePanel.replaceChildren();
    card.hidden = true;
    editable = "Loading…";
    timeNote = null;
    bad.clear();
    tables.replaceChildren();
    const sel = host.store.getState().sel;
    if (sheetAccepts(sel)) shownSel = sel;
    try {
      target = await resolveTarget(host, view, shownSel);
      if (gen !== generation) return;
      if (!target) {
        title.textContent = "Line sheet";
        delete title.dataset.section;
        solveInfo.textContent = "Select a line, a profile or a station.";
        showProfile();
        showNotice();
        draw();
        return;
      }
      const sectionId = target.sectionId;
      void fillPicker();
      title.dataset.section = sectionId;
      title.title = `section ${sectionId}`;
      sectionName = host.names.text("section", sectionId, view);
      title.textContent = sectionName;
      const [inp, fr, ed, name, sti, sed] = await Promise.all([
        host.api.sectionInput(sectionId, view),
        loadFrame(sectionId),
        target.profile
          ? host.editable("profile", view)
          : Promise.resolve("This section has no profile record, so the sheet is read-only."),
        host.names.get("section", sectionId, view),
        host.api.stationInput(sectionId, view).catch(() => null),
        host.editable("platform", view),
      ]);
      if (gen !== generation) return;
      input = inp;
      si = sti;
      sideEditable = sed;
      frame = frameFor(fr, inp);
      sectionName = name;
      title.textContent = name;
      showPending();
      ctx.setTitle(name);
      editable = editMessage(ed);
      timeNote = await loadTimeNote(sectionId);
      if (gen !== generation) return;
      showNotice();
      showProfile();
      showChainage();
      if (!range || shownSection !== sectionId) range = [0, input.length_m];
      // the whole solve's input is the heaviest read: it follows on its own, so the rail and facts never wait
      void host.api
        .solveInput(sectionId, view)
        .then((x) => {
          if (gen !== generation) return;
          ssi = x;
          fullSoon();
        })
        .catch(() => undefined);
      shownSection = sectionId;
      if (popKind === "settings") void loadSettings().then(renderPop);
      if (target.profile) {
        const p = target.profile;
        stopWatch = host.records.watch(p.kind, p.id, view, (r) => {
          if (!r.data || !target || gen !== generation) return;
          const was = target.profile;
          target.profile = r.data;
          if (was && was.version !== r.data.version) scheduleRefresh();
          showProfile();
          refreshTable();
          void solve();
          if (asked !== null && asked !== `${r.data.layer}:${r.data.version}`) void requestSolve();
        });
      }
      table();
      solveInfo.dataset.busy = "1";
      await warm(gen);
      if (gen !== generation) return;
      void solve();
      void loadServer();
      void requestSolve();
    } catch (e) {
      solveInfo.textContent = `Could not load the section: ${String((e as Error).message ?? e)}`;
      draw();
    }
  };

  /** Go to where a platform, stop or station is: its line at its chainage. Several lines: Ben picks one. */
  const follow = async (sel: RecordRef) => {
    let places: { sectionId: string; c: number }[] = [];
    try {
      places = await placesOf(host, view, sel);
    } catch {
      return;
    }
    if (host.store.getState().sel !== sel || places.length === 0) return;
    const go = async (p: { sectionId: string; c: number }) => {
      if (p.sectionId !== shownSection || !target) {
        shownSel = { kind: "section", id: p.sectionId };
        await load();
      }
      setChainage(host.store, p.c);
    };
    const here = places.find((p) => p.sectionId === shownSection);
    if (here || places.length === 1) {
      await go(here ?? (places[0] as { sectionId: string; c: number }));
      return;
    }
    const names = await Promise.all(places.map((p) => host.names.get("section", p.sectionId, view)));
    const what = await host.names.get(sel.kind, sel.id, view);
    host.toast({
      text: `${what} is on ${names.join(", ")}. Which line should the sheet show?`,
      level: "info",
      ttl: 0,
      actions: places.map((p, i) => ({ label: names[i] ?? p.sectionId, run: () => void go(p) })),
    });
  };

  // ------------------------------------------------------------------------------------------------- the table

  /** Edit the profile's draft. The ops are made from the data as it is now (the draft's working copy), never from a
   * copy taken when the table was drawn: the table is not redrawn while a cell has the focus, and ops made from an
   * old copy would undo earlier edits ("add /data/st {}" a second time) or miss a value typed since. */
  const edit = (make: (cur: ProfileData) => JsonPatch, opts: { step?: string; label?: string } = {}) => {
    const p = target?.profile;
    const cur = data();
    const r = raw();
    if (!p || !cur || !r || !canEdit()) return;
    try {
      // The design drawn where the profile holds none goes into the draft with Ben's first edit, in the same step
      // (the old page saved S.align whole, serialize 3213): one Ctrl+Z puts the untouched profile back. An edit that
      // changes nothing writes nothing, the design included.
      const ops = editOps(r, design, make(cur));
      if (ops) host.drafts.edit(p, view, ops, { label: `${sectionName} profile`, ...opts });
    } catch (e) {
      host.problem(e);
    }
  };

  /** A station edit: one undo step per call, or per step id (a drag, a visit to a field). */
  const editStation = (pid: string, what: string, make: (cur: ProfileData) => JsonPatch, step?: string) =>
    edit(make, { label: `${platformName(pid)} ${what}`, ...(step ? { step } : {}) });

  /** Side platforms or an island: a draft on the platform record, saved with the profile by Save. */
  const editSide = (pid: string, side: "side" | "island") => {
    const rec = platformRecs.get(pid);
    if (!rec || sideEditable !== true) return;
    const cur = (host.drafts.get("platform", pid, view)?.body ?? bodyOf(rec)).data as Record<string, unknown>;
    try {
      host.drafts.edit(rec, view, setPlatformSide(cur, side), { label: `${platformName(pid)} side or island` });
    } catch (e) {
      host.problem(e);
    }
  };

  /** Each visit to a cell is one undo step, however many keystrokes it takes. */
  const cellVisits = new Map<string, number>();
  let cellSeq = 0;
  const cellStep = (label: string) => `cell:${label}:${cellVisits.get(label) ?? 0}`;

  const numberCell = (
    value: number | null,
    onValue: (v: number | null) => void,
    label: string,
    dirty: boolean,
    opts: { allowNull?: boolean; chainage?: boolean } = {},
  ) => {
    const td = document.createElement("td");
    const i = document.createElement("input");
    const fmt = (v: number) => (opts.chainage ? formatChainage(v, host.units) : host.units.format(v, "m"));
    const parse = (t: string) => (opts.chainage ? parseChainage(t, host.units) : host.units.parse(t, "m"));
    const help = opts.chainage
      ? CHAINAGE_HELP
      : `Type a level in ${host.units.label("m")}${opts.allowNull ? ", or leave it empty for the design to set it" : ""}.`;
    i.value = value === null ? "" : fmt(value);
    i.placeholder = opts.allowNull ? "design" : "";
    i.title = help;
    i.setAttribute("aria-label", label);
    i.inputMode = "decimal";
    // What the cell showed when drawn: Ctrl+Z in a cell still showing it is the hub's undo (main.tsx).
    i.dataset.drawn = i.value;
    if (dirty) i.classList.add("dirty");
    i.disabled = !canEdit();
    i.addEventListener("focus", () => cellVisits.set(label, ++cellSeq));
    i.addEventListener("input", () => {
      if (opts.allowNull && i.value.trim() === "") {
        i.classList.remove("bad");
        if (bad.delete(label)) showNotice();
        onValue(null);
        return;
      }
      const v = parse(i.value);
      i.classList.toggle("bad", v === null);
      if (v === null) {
        bad.set(label, `"${i.value}" is not ${opts.chainage ? "a chainage" : "a number"}. ${help}`);
        i.setAttribute("aria-invalid", "true");
      } else {
        bad.delete(label);
        i.removeAttribute("aria-invalid");
        onValue(v);
      }
      showNotice();
    });
    i.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      if (bad.has(label)) {
        host.toast({
          text: `Not saved: ${label} "${i.value}" is not ${opts.chainage ? "a chainage" : "a number"}. ${help}`,
          level: "warn",
        });
        return;
      }
      // Leave the cell: the browser's text undo of what was typed must not be the next Ctrl+Z (usability-3).
      i.blur();
      void host.runCommand("core.save");
    });
    td.append(i);
    return td;
  };

  // While Ben types in a cell the table is not rebuilt under him (that would reformat "170." to "170"); it catches
  // up when the focus leaves the table. A focused button (after "+ PVI" or "−") does not hold it back, nor does a
  // change in the number of PVIs: rows are addressed by index, so a table with a row too many or too few would send
  // the next edit to the wrong PVI.
  let tableStale = false;
  /** A draft change the tables have not shown yet (they catch up after the solves). */
  let tableDue = false;
  /** A draft change the bar has not shown yet. */
  let profileDue = false;
  const refreshTable = () => {
    const a = document.activeElement;
    const typing = a instanceof HTMLInputElement && tables.contains(a);
    const d = data();
    const count = d ? (d.pvi?.length ?? 0) : (input?.pvi.length ?? 0);
    if (typing && count === builtPvis) tableStale = true;
    else table();
  };
  tables.addEventListener("focusout", (e) => {
    if (tableStale && !tables.contains(e.relatedTarget as Node | null)) {
      tableStale = false;
      table();
    }
  });

  const table = () => {
    const focused = document.activeElement as HTMLInputElement | null;
    const focusLabel = tables.contains(focused) ? focused?.getAttribute("aria-label") : null;
    tables.replaceChildren();
    bad.clear();
    showNotice();
    if (!input) return;
    const d = data();
    const base = target?.profile ? (target.profile.data as ProfileData) : null;
    const lu = host.units.label("m");
    const cu = host.units.length === "m" ? "km+m" : "ft";

    const pt = document.createElement("table");
    pt.className = "grid";
    pt.dataset.testid = "pvi-table";
    pt.innerHTML = `<caption>PVIs</caption><tr><th>#</th><th>chainage (${cu})</th><th>level (${lu})</th><th></th></tr>`;
    const rows = d ? pviRows(d) : input.pvi.map((p, index) => ({ index, c: p.c_m, z: p.z_m }));
    builtPvis = rows.length;
    tableStale = false;
    const baseRows = base ? pviRows(base) : [];
    for (const r of rows) {
      const tr = document.createElement("tr");
      tr.dataset.index = String(r.index);
      const b = baseRows[r.index];
      tr.append(Object.assign(document.createElement("td"), { textContent: String(r.index + 1) }));
      tr.append(
        numberCell(
          r.c,
          (v) =>
            v !== null &&
            edit((cur) => setPviC(cur, r.index, v), {
              step: cellStep(`PVI ${r.index + 1} chainage`),
              label: `PVI ${r.index + 1} chainage`,
            }),
          `PVI ${r.index + 1} chainage`,
          !!b && b.c !== r.c,
          { chainage: true },
        ),
      );
      tr.append(
        numberCell(
          r.z,
          (v) =>
            v !== null &&
            edit((cur) => setPviZ(cur, r.index, v), {
              step: cellStep(`PVI ${r.index + 1} level`),
              label: `PVI ${r.index + 1} level`,
            }),
          `PVI ${r.index + 1} level`,
          !!b && b.z !== r.z,
        ),
      );
      const rm = Object.assign(document.createElement("button"), {
        type: "button",
        textContent: "−",
        title: `Remove PVI ${r.index + 1}`,
      });
      rm.disabled = !d || !canEdit();
      rm.onclick = () => edit(() => removePvi(r.index));
      const td = document.createElement("td");
      td.append(rm);
      tr.append(td);
      pt.append(tr);
    }
    const add = Object.assign(document.createElement("button"), { type: "button", textContent: "+ PVI at the cursor" });
    add.disabled = !d || cursor === null || !canEdit();
    addButton = add;
    add.onclick = () => {
      if (cursor === null) return;
      const c = cursor;
      const z = local ? (local.rail_m[Math.round(c / local.grid.step_m)] ?? 0) : 0;
      edit((cur) => addPvi(cur, Math.round(c * 10) / 10, Math.round(z * 1000) / 1000));
    };

    // Stations: the type chip and name, the street, the level Ben edits, the depth, the chainage and a flag dot
    // (the old table's columns, S51, with the level editable as before).
    const stt = document.createElement("table");
    stt.className = "grid";
    stt.dataset.testid = "station-table";
    stt.innerHTML = `<caption>Stations</caption><tr><th class=name>station</th><th class=street>street</th><th>level (${lu})</th><th>depth</th><th>chainage (${cu})</th><th title="flags">!</th></tr>`;
    const li = localInput(input, d, frame);
    const factOf = new Map((facts ?? []).map((f) => [f.platform_id, f]));
    const seen = new Map<string, number>();
    li.stations.forEach((s) => {
      const tr = document.createElement("tr");
      tr.dataset.platform = s.platform_id;
      const nm = platformName(s.platform_id);
      const n = (seen.get(nm) ?? 0) + 1;
      seen.set(nm, n);
      const label = n === 1 ? nm : `${nm} ${n}`;
      const f = factOf.get(s.platform_id);
      const name = Object.assign(document.createElement("td"), { className: "name" });
      const chip = Object.assign(document.createElement("span"), { className: "type-chip", title: typeLabel(f?.type) });
      chip.style.background = typeColour(f?.type);
      chip.dataset.type = f?.type ?? "";
      name.append(chip, label);
      name.title = `${label} (platform ${s.platform_id}): click to select it on the sheet`;
      name.onclick = () => selectStation(s.platform_id, true);
      if (selected?.kind === "station" && selected.id === s.platform_id) tr.classList.add("selected");
      tr.append(name);
      const street = Object.assign(document.createElement("td"), {
        className: "street",
        textContent: f ? streetShort(f.street) : "",
        title: f ? streetText(f.street) : "",
      });
      tr.append(street);
      const was = base?.st?.[s.platform_id] ?? null;
      tr.append(
        numberCell(
          s.level_m,
          (v) =>
            editStation(
              s.platform_id,
              "rail level",
              (cur) => setStationLevel(cur, s.platform_id, v),
              cellStep(`Station ${label} level`),
            ),
          `Station ${label} level`,
          (raw()?.st?.[s.platform_id] ?? null) !== was,
          { allowNull: true },
        ),
      );
      const dep = f?.depth_m ?? null;
      tr.append(
        Object.assign(document.createElement("td"), {
          className: "num",
          textContent: dep === null ? "–" : dep >= 0 ? fmtZ(dep, host.units) : `+${fmtZ(-dep, host.units)}`,
        }),
      );
      tr.append(Object.assign(document.createElement("td"), { textContent: formatChainage(s.c_m, host.units) }));
      const sev = f ? worstSeverity(f.flags) : null;
      const dot = document.createElement("td");
      if (sev) {
        const sp = Object.assign(document.createElement("span"), { className: "flag-dot", textContent: "●" });
        sp.style.color = SEV_COLOURS[sev];
        sp.title = (f?.flags ?? []).map((x) => flagText(x, host.units, platformName)).join("\n");
        dot.append(sp);
      }
      tr.append(dot);
      stt.append(tr);
    });
    // Removed stations, each with Restore (S52): Ben's own level, grade and slide come back with it.
    const removedList = document.createElement("table");
    removedList.className = "grid";
    removedList.dataset.testid = "removed-list";
    const gone = (facts ?? []).filter((f) => f.deleted);
    if (gone.length) {
      removedList.innerHTML = "<caption>Removed</caption>";
      for (const f of gone) {
        const tr = document.createElement("tr");
        tr.dataset.platform = f.platform_id;
        tr.append(
          Object.assign(document.createElement("td"), { className: "name", textContent: platformName(f.platform_id) }),
        );
        tr.append(
          Object.assign(document.createElement("td"), { textContent: formatChainage(f.point_c_m, host.units) }),
        );
        const b = Object.assign(document.createElement("button"), {
          type: "button",
          textContent: "Restore",
          title: `Put ${platformName(f.platform_id)} back at its drawn point, with its own level if it has one`,
        });
        b.disabled = !canEdit();
        b.onclick = () => {
          editStation(f.platform_id, "restored", (cur) => restoreStation(cur, f.platform_id));
          selected = { band: "platforms", kind: "station", index: 0, id: f.platform_id, c: f.c_m };
        };
        const td = document.createElement("td");
        td.append(b);
        tr.append(td);
        removedList.append(tr);
      }
    }
    const easeAll = Object.assign(document.createElement("button"), {
      type: "button",
      textContent: "Ease all platforms",
      title: "Slope every platform toward the grades either side, up to the limit: one undo step",
    });
    easeAll.dataset.testid = "ease-all";
    easeAll.disabled = !canEdit();
    easeAll.onclick = () => void easeStations(li.stations.map((x) => x.platform_id));
    const stations = document.createElement("div");
    stations.append(easeAll, stt, removedList);
    const left = document.createElement("div");
    left.append(pt, add);
    // The stations first: Ben looks for a station's level more often than for a PVI's.
    tables.append(stations, left);
    renderCard();
    if (focusLabel) {
      const again = [...tables.querySelectorAll("input")].find((x) => x.getAttribute("aria-label") === focusLabel);
      if (again) {
        again.focus();
        const n = again.value.length;
        again.setSelectionRange(n, n);
      }
    }
  };

  // ------------------------------------------------------------------------------------------- the station card

  /** The selected station as the sheet's input has it now, with its index; null when none is selected. */
  const selectedStation = () => {
    if (selected?.kind !== "station" || !input) return null;
    const id = selected.id;
    const stations = localInput(input, data(), frame).stations;
    const index = stations.findIndex((s) => s.platform_id === id);
    return index < 0 ? null : { s: stations[index] as SectionInput["stations"][number], index, stations };
  };

  /** Select a station (from the canvas or the table); centre the view on it when asked. */
  const selectStation = (id: string, centre: boolean, maxSpan = 2500) => {
    if (!input) return;
    const stations = localInput(input, data(), frame).stations;
    const index = stations.findIndex((s) => s.platform_id === id);
    const s = stations[index];
    if (!s) return;
    const rail = local
      ? { rail_m: local.rail_m, grade_permille: local.grade_permille, step_m: local.grid.step_m }
      : null;
    selected = { band: "platforms", kind: "station", index, id, c: s.c_m, z: stationLevel(s, rail) ?? undefined };
    if (centre && range) {
      // As the old table did: centred, at most 2,500 m across (1,500 from a flag).
      const span = Math.min(range[1] - range[0], maxSpan);
      range = clampRange([s.c_m - span / 2, s.c_m + span / 2]);
    }
    setChainage(host.store, s.c_m);
    markRows();
    renderCard();
    draw();
  };

  const markRows = () => {
    const id = selected?.kind === "station" ? selected.id : null;
    for (const tr of tables.querySelectorAll<HTMLTableRowElement>("[data-testid=station-table] tr[data-platform]"))
      tr.classList.toggle("selected", tr.dataset.platform === id);
  };

  /** The selected station's panel (A.3): every setting with its value, source and rule, rebuilt after each solve.
   * A field Ben is typing in keeps its text and caret across the rebuild. */
  const renderCard = () => {
    renderLineSoon();
    if (input && selected?.kind === "pvi") {
      card.hidden = false;
      root.classList.add("with-panel");
      keepFocus(card, () => {
        const c = bendCardOf();
        card.replaceChildren(c ?? document.createElement("div"));
        return c;
      });
      return;
    }
    if (input && selected?.kind === "gp") {
      card.hidden = false;
      root.classList.add("with-panel");
      keepFocus(card, () => {
        const c = groundCardOf();
        card.replaceChildren(c ?? document.createElement("div"));
        return c;
      });
      return;
    }
    const sel = selectedStation();
    if (!sel || !input) {
      // No station selected: the panel stays in its place with what Ben can do (the old card's hint), so the
      // plot does not jump when a click on empty canvas clears the selection.
      card.hidden = !input;
      root.classList.toggle("with-panel", !!input);
      const hint = document.createElement("div");
      hint.className = "sp sp-empty";
      hint.dataset.testid = "station-panel-hint";
      hint.innerHTML =
        "<p><b>Stations.</b> Click a station's bar, its name or its row to see and set everything about it.</p>" +
        "<p class=sp-hint>Drag a bar up or down for its level (Shift: 1 m steps); Alt + drag slides it along its drawn point. " +
        "Arrows nudge the level 0.1 (Shift 1); Alt + Left or Right slides 0.5 m; Page Up or Down tilts it 0.5‰; " +
        "[ and ] step through the stations; E eases the bends; Delete twice removes one. Ctrl+Z takes back each step; " +
        "Ctrl+S or Enter in a field saves.</p>" +
        "<p class=sp-hint><b>Tools:</b> Move (M), Paint (P) with a structure brush, Ground (G) for the drawn ground. " +
        "Press <b>?</b> for every tool and key.</p>";
      card.replaceChildren(hint);
      return;
    }
    card.hidden = false;
    root.classList.add("with-panel");
    const { s, index, stations } = sel;
    const half = input.params.platform_m / 2;
    const rail = local
      ? { rail_m: local.rail_m, grade_permille: local.grade_permille, step_m: local.grid.step_m }
      : null;
    const f = facts?.find((x) => x.platform_id === s.platform_id) ?? null;
    // A station with no level is read where it is drawn (ground - the default depth, station.facts@1), not on the
    // design's rail, which is 0 m on a line with no design.
    const z = s.level_m === null && f?.rail_m != null ? f.rail_m : stationLevel(s, rail);
    const groundDem = input.ground ? valueAt(input.ground.z_m, input.ground.step_m, s.c_m) : null;
    const point = stopOf(s.platform_id) ?? f?.point_c_m ?? s.c_m;
    const pd = (target?.profile?.data ?? {}) as ProfileData;
    const prec = platformRecs.get(s.platform_id);
    const sideWas = (prec?.data as Record<string, unknown> | undefined)?.side === "island" ? "island" : "side";
    const sd = sideDraft(s.platform_id);
    const sideSrc = f?.side_source ?? (prec ? "import" : "default");
    const prefix = si?.system === "tri" ? "settings_rer" : "settings";
    const id = s.platform_id;
    const lineName = sectionName;
    keepFocus(card, () => {
      const panel = buildPanel({
        units: host.units,
        pid: id,
        name: platformName(id),
        line: lineName,
        index,
        count: stations.length,
        half,
        fact: f,
        params: si?.params ?? null,
        paramPrefix: prefix,
        metro: si ? si.structure !== null : true,
        draft: data() ?? {},
        saved: pd,
        held: raw() ?? undefined,
        savedBy: target?.profile?.by ?? "",
        point,
        centre: s.c_m,
        rail: z,
        ground: f?.ground_m ?? groundDem,
        groundDem: f?.ground_dem_m ?? groundDem,
        gradeIn: local ? valueAt(local.grade_permille, local.grid.step_m, s.c_m - half - 1) : null,
        gradeOut: local ? valueAt(local.grade_permille, local.grid.step_m, s.c_m + half + 1) : null,
        side: {
          now: sd?.side ?? sideWas,
          was: sideWas,
          source: sideSrc === "ben" ? "Ben" : sideSrc === "import" ? "old hub" : "default (side)",
        },
        canEdit: canEdit(),
        canEditSide: canEdit() && sideEditable === true && !!prec,
        readOnly: canEdit() ? null : editable === true ? "This line has no profile record to edit." : editable,
        act: {
          level: (v, step) => editStation(id, "rail level", (cur) => setStationLevel(cur, id, v), step),
          depth: (dd, step) => {
            const g = f?.ground_m ?? groundDem;
            if (g !== null)
              editStation(
                id,
                "rail below ground",
                (cur) => setStationLevel(cur, id, Math.round((g - dd) * 100) / 100),
                step,
              );
          },
          grade: (v, step) => editStation(id, "platform grade", (cur) => setStationGrade(cur, id, v), step),
          slide: (v, step) => editStation(id, "slide", (cur) => setStationSlide(cur, id, v, slideMax()), step),
          ease: () => void easeStations([id]),
          remove: () => removeSelected(id),
          type: (t: SelectableType | null) =>
            editStation(id, "station type", (cur) => setStationType(cur, id, t, f?.elevated_rail_min_m ?? null, z)),
          access: (t) => editStation(id, "access", (cur) => setAccess(cur, id, t)),
          gapfill: (on) => editStation(id, on ? "gap fillers on" : "gap fillers off", (cur) => setGapfill(cur, id, on)),
          side: (v) => editSide(id, v),
          prev: () => stepStation(-1),
          next: () => stepStation(1),
          close: () => {
            selected = null;
            markRows();
            renderCard();
            draw();
          },
          save: () => void host.runCommand("core.save"),
          openParam: (path) => void openParam(path),
          select: (pid) => selectStation(pid, true),
        },
      });
      card.replaceChildren(panel);
      return panel;
    });
  };

  // ------------------------------------------------------------------------- tools, cards and the line panel

  /** A brush's colour for the paint preview (2722): the type's, the shield's for a tube form, grey to clear. */
  const brushColour = (b: Brush): string =>
    b === "auto" || b === "tf:auto" || b === "shaft"
      ? "#8b919e"
      : b.startsWith("tf:")
        ? typeColour("shield")
        : typeColour(b);

  /** The ground below the drawn lines at c (baseAt 666): the whole solve's finished ground, else the survey. */
  const groundBelow = (c: number): number | null => {
    const f = solved ? sampleAt(solved.ground.finished as ArrayLike<number | null>, solved.step_m, c) : null;
    if (f !== null && Number.isFinite(f)) return Math.round(f * 100) / 100;
    const g = input?.ground ? valueAt(input.ground.z_m, input.ground.step_m, c) : null;
    return g === null || !Number.isFinite(g) ? null : Math.round(g * 100) / 100;
  };
  const surfaceAt = (c: number): number | null => {
    const f = solved ? sampleAt(solved.ground.surface as ArrayLike<number | null>, solved.step_m, c) : null;
    if (f !== null && Number.isFinite(f)) return f;
    return input?.ground ? valueAt(input.ground.z_m, input.ground.step_m, c) : null;
  };
  // read between the 2 m samples, as the old railAt: at a bend point off the grid ("Rail at the bend", 4+485.3 on
  // Line 6) the nearest sample was 7 cm off on a 145 per mille change of grade
  const railNow = (c: number): number | null => (local ? sampleAt(local.rail_m, local.grid.step_m, c) : null);
  const typeNow = (c: number): string | null => typeAtSample(solved, c);

  /** The bend point card of the selected PVI (3110-3133). */
  const bendCardOf = (): HTMLElement | null => {
    const sel = selected;
    if (sel?.kind !== "pvi" || !input) return null;
    const d = data();
    const row = d ? pviRowOf(sel.c, sel.z) : null;
    const rows = d ? pviRows(d) : [];
    const p = row !== null ? rows.find((r) => r.index === row) : undefined;
    const c = p?.c ?? sel.c;
    const z = p?.z ?? sel.z ?? 0;
    const curve = local?.curves.find((q) => Math.abs(q.c_m - c) < 0.5) ?? null;
    const short = (local?.flags ?? []).some(
      (f) => f.kind.includes("curve") && Math.abs(((f.c0 ?? 0) + (f.c1 ?? 0)) / 2 - c) < 0.5,
    );
    return bendCard({
      units: host.units,
      index: row ?? sel.index,
      c,
      z,
      surface: surfaceAt(c),
      type: typeNow(c),
      gIn: curve ? curve.g_in : null,
      gOut: curve ? curve.g_out : null,
      curve: curve ? { L: curve.L_m, short } : null,
      railAt: railNow(c),
      canEdit: canEdit() && row !== null,
      readOnly: canEdit() ? null : editable === true ? null : editable,
      set: (cn, zn) => {
        if (row === null) return;
        const len = input?.length_m ?? cn + 1;
        const cc = Math.round(outOfPlatforms(Math.max(1, Math.min(len - 1, cn))));
        edit((cur) => setPvi(cur, row, cc, zn), { label: `PVI ${row + 1}` });
        selected = { band: "pvi", kind: "pvi", index: row, c: cc, z: zn };
        setChainage(host.store, cc);
        renderCard();
        draw();
      },
      remove: () => {
        if (row === null) return;
        edit(() => removePvi(row), { label: `PVI ${row + 1} removed` });
        selected = null;
        renderCard();
        draw();
      },
    });
  };

  /** The ground point card of the selected drawn ground point (3092-3108). */
  const groundCardOf = (): HTMLElement | null => {
    const sel = selected;
    if (sel?.kind !== "gp" || !input) return null;
    const lines = groundLines(data());
    const l = Number(sel.id);
    const P = lines[l]?.pts;
    const p = P?.[sel.index];
    if (!P || !p) return null;
    const k = sel.index;
    const gr = (a: { c: number; z: number }, b: { c: number; z: number }) =>
      b.c - a.c > 1e-6 ? ((b.z - a.z) / (b.c - a.c)) * 1000 : null;
    const prev = P[k - 1];
    const next = P[k + 1];
    const gsel: GroundPoint = { l, k };
    return groundCard({
      units: host.units,
      c: p.c,
      z: p.z,
      end: k === 0 || k === P.length - 1,
      below: groundBelowLine(p.c, l),
      gIn: prev ? gr(prev, p) : null,
      gOut: next ? gr(p, next) : null,
      rail: railNow(p.c),
      from: (P[0] as { c: number }).c,
      to: (P[P.length - 1] as { c: number }).c,
      points: P.length,
      canEdit: canEdit(),
      set: (c, z) => {
        edit((cur) => moveGroundPoint(cur, gsel, c, z, input?.length_m ?? c), { label: "ground point" });
        const now = groundLines(data())[l]?.pts[k];
        if (now) selected = { band: "drawn-ground", kind: "gp", index: k, id: String(l), c: now.c, z: now.z };
        renderCard();
        draw();
      },
      remove: (all) => {
        edit((cur) => removeGroundPoint(cur, gsel, all), {
          label: all ? "ground line removed" : "ground point removed",
        });
        selected = null;
        renderCard();
        draw();
      },
    });
  };
  /** The ground under a drawn line at c: the survey with the Deck's re-grades, the line itself left out. */
  const groundBelowLine = (c: number, l: number): number | null => {
    const g = input?.ground ? valueAt(input.ground.z_m, input.ground.step_m, c) : null;
    const lines = groundLines(data());
    const own = lines[l]?.pts;
    const f = groundBelow(c);
    // the finished ground holds the line itself over its span: the survey is the ground below there
    if (own && c >= (own[0] as { c: number }).c && c <= (own[own.length - 1] as { c: number }).c) return g;
    return f ?? g;
  };

  // ---- the line panel (R52 to R61)
  let lineTimer: ReturnType<typeof setTimeout> | null = null;
  let busy: string | null = null;
  let paintRows: PaintRowView[] | null = null;
  let checkRows: CheckRow[] | null = null;
  let checkNote: string | null = null;
  const renderLineSoon = () => {
    if (lineTimer) return;
    lineTimer = setTimeout(() => {
      lineTimer = null;
      // not while the rail solves or Ben drags (the drag's end asks again): it lays the side panel out (speed)
      if (solving || solveDue || editingDrag()) renderLineSoon();
      else renderLine();
    }, 60);
  };
  const renderLine = () => {
    if (!input || !target) {
      linePanel.replaceChildren();
      return;
    }
    const d = data();
    const fs = facts ?? [];
    const live = fs.length ? fs.filter((f) => !f.deleted).length : localInput(input, d, frame).stations.length;
    const scroll = side.scrollTop;
    const panel = buildLinePanel({
      units: host.units,
      line: sectionName,
      length: input.length_m,
      liveStations: live,
      removed: fs.length - fs.filter((f) => !f.deleted).length,
      solved,
      ssi,
      facts,
      name: platformName,
      ready: !!(d as { ready?: unknown } | null)?.ready,
      canEdit: canEdit(),
      busy,
      paints: paintRows,
      check: checkRows,
      checkNote,
      act: {
        ready: (on) => edit((cur) => setReady(cur, on), { label: on ? "profile set" : "profile not set" }),
        show: (c) => {
          if (!range) return;
          const span = Math.min(range[1] - range[0], 1500);
          range = clampRange([c - span / 2, c + span / 2]);
          setChainage(host.store, c);
          draw();
        },
        select: (pid) => selectStation(pid, true, 1500),
        regrade: (f) =>
          void propose(
            {
              kind: "regrade",
              mode: f.mode,
              c0: f.c0,
              c1: f.c1,
              fit: f.fit ? ({ t: f.fit.t, why: f.fit.why } as never) : null,
            },
            f.mode === "lower" ? "Lower" : "Raise",
          ),
        fill: (c0, c1) => void propose({ kind: "fill", c0, c1 }, "Propose fill"),
        clear: (x) => clearOne(x),
        stationFix: (pid, kind) => stationFix(pid, kind),
        easeAll: () => {
          if (!input) return;
          void easeStations(localInput(input, data(), frame).stations.map((x) => x.platform_id));
        },
        solveCross: () => void propose({ kind: "solve_cross" }, "Solve levels with crossings"),
        fixAll: () => void propose({ kind: "fix_all" }, "Fix unbuildable"),
        checkAll: () => void checkAll(),
        openLine: (id) => host.select({ kind: "section", id }),
        reviewPaints: () => void reviewPaints(),
        clearPaint: (r) => {
          edit((cur) => clearPaints(cur, [r]), { label: "paint cleared" });
          paintRows = null;
          void reviewPaints();
        },
        clearSamePaints: () => {
          const same = (paintRows ?? []).filter((r) => r.same);
          edit((cur) => clearPaints(cur, same), { label: "paints that repeat the rules cleared" });
          paintRows = null;
          void reviewPaints();
        },
        clearAllPaints: () => {
          edit((cur) => clearPaints(cur, "all"), { label: "all paints cleared" });
          paintRows = null;
          void reviewPaints();
        },
        redraw: () => renderLine(),
      },
    });
    linePanel.replaceChildren(panel);
    side.scrollTop = scroll;
  };

  /** Clear (clearMisfit 3595): a selection back to the rules, or the paint cut out over the misfit. */
  const clearOne = (x: NonNullable<IssueRow["clear"]>) => {
    const d = data();
    if (!d) return;
    const ops = clearMisfit(d, x);
    if (!ops.length) {
      host.toast({ text: "Nothing to clear here: a lock or the canon holds it", level: "info", ttl: 2500 });
      return;
    }
    edit(() => ops, { label: x.station ? `${platformName(x.station)} back to the rules` : "paint cleared" });
    host.toast({
      text: x.station
        ? `${platformName(x.station)}: back to the rules`
        : `Paint cleared from ${fmtCh(x.c0)} to ${fmtCh(x.c1)}`,
      level: "info",
      ttl: 2500,
    });
  };

  /** A station flag's own fix from the issues list: the same as its button in the station panel. */
  const stationFix = (pid: string, kind: string) => {
    if (kind === "platform_grade_over") {
      void easeStations([pid]);
      return;
    }
    if (kind === "platform_curve") {
      editStation(pid, "gap fillers on", (cur) => setGapfill(cur, pid, true));
      return;
    }
    selectStation(pid, true, 1500);
  };

  /** A proposal of section.propose@1 on the draft, laid on it as one undo step, with the old page's words. */
  const propose = async (request: Record<string, unknown>, what: string): Promise<SectionProposal | null> => {
    if (!ssi || !canEdit() || busy) return null;
    busy = `${what}…`;
    renderLine();
    try {
      fullEngine ??= createEngine();
      if (stashedSsi !== ssi) {
        await fullEngine.stash(SSI_STASH, ssi);
        stashedSsi = ssi;
      }
      const inp = solveInputOf(ssi, data(), sideDraft);
      const out = await fullEngine.solve(
        "section.propose",
        {
          contract: "section_propose_input/0",
          doc: inp.doc,
          platforms: inp.platforms,
          access: inp.access,
          request,
          ...(settingsOverride() ? { settings: { ...ssi.settings, ...settingsOverride() } } : {}),
        },
        { engineBuild: host.events.status().engine_build ?? undefined, base: SSI_STASH },
      );
      const p = out.result as SectionProposal;
      if (p.changed) {
        const d = data();
        if (d) edit(() => proposalOps(d, p), { label: what });
      }
      if (p.kind !== "paint_review") host.toast({ text: proposalWords(p), level: "info", ttl: 5000 });
      if (p.kind === "fill" && p.changed) {
        setTool("ground");
        const l = Number(p.report.line ?? 0);
        const pts = groundLines(data())[l]?.pts;
        const k = Math.min(1, (pts?.length ?? 1) - 1);
        const pt = pts?.[k];
        if (pt) selected = { band: "drawn-ground", kind: "gp", index: k, id: String(l), c: pt.c, z: pt.z };
      } else if (p.changed && p.kind !== "paint_review") selected = null;
      renderCard();
      return p;
    } catch (e) {
      host.problem(e);
      return null;
    } finally {
      busy = null;
      renderLine();
    }
  };

  /** The old page's words for a proposal (regradeDrive 3654, fixAll 2994, proposeFill 1728, solveCross 3719). */
  const proposalWords = (p: SectionProposal): string => {
    const r = p.report as Record<string, unknown>;
    const ch = (c: unknown) => fmtCh(Number(c));
    const z = (m: unknown) => host.units.format(Number(m), "m", 1);
    const lu = host.units.label("m");
    if (p.kind === "regrade") {
      const mode = r.mode === "raise" ? "raise" : "lower";
      if (r.blocked) {
        const b = r.blocked as { name: string };
        return `This would move ${b.name}, which is held by the canon or locked: not changed`;
      }
      if (r.nothing) return `Nothing to ${mode}`;
      const lowered = (r.lowered as { name: string; by: number }[]) ?? [];
      const under = (r.under as string[]) ?? [];
      const short = r.short as { by: number; c: number } | null;
      return `${mode === "raise" ? "Raised" : "Lowered"} the rail by up to ${z(r.worst)} ${lu} from ${ch(r.c0)} to ${ch(r.c1)}${
        lowered.length
          ? `, with ${lowered.map((x) => `${x.name} ${z(x.by)}`).join(", ")} ${lu} ${mode === "raise" ? "higher" : "lower"}`
          : ""
      }${under.length ? `; under ${under.slice(0, 6).join(", ")}${under.length > 6 ? ` and ${under.length - 6} more` : ""}` : ""}${
        short ? ` (still ${host.units.format(short.by, "m", 2)} ${lu} short at ${ch(short.c)})` : ""
      }. A preview in your draft: Save keeps it, Ctrl+Z takes it back.`;
    }
    if (p.kind === "fix_all") {
      const found = Number(r.found);
      const left = Number(r.left);
      if (!found) return "Nothing unbuildable on this line";
      return left
        ? `${left} unbuildable stretch${left > 1 ? "es" : ""} left (see the issues: a canon or locked station, or a fix that would undo another)`
        : `All ${found} fixed. A preview in your draft: Save keeps it, Ctrl+Z takes it back.`;
    }
    if (p.kind === "fill")
      return p.changed
        ? `Fill drawn from ${ch(r.c0)} to ${ch(r.c1)}, up to ${z(r.top)} ${lu} high, ${r.points} points: edit it in Ground (Ctrl Z undoes it)`
        : "The structure has its cover here: no fill needed";
    if (p.kind === "solve_cross")
      return Number(r.of)
        ? `Cleared ${r.held} of ${r.of} crossings within ${r.maxGrade}‰. A preview in your draft: Save keeps it, Ctrl+Z takes it back.`
        : "No crossings with a known rail";
    if (p.kind === "reset")
      return "This line reset to the level solver's default profile (not saved: Ctrl+Z takes it back)";
    return "";
  };

  /** The paint review (2953-2983): each paint with what the rules give without it. */
  const reviewPaints = async () => {
    if (!ssi || busy) return;
    busy = "Comparing the paints with the rules…";
    renderLine();
    try {
      fullEngine ??= createEngine();
      if (stashedSsi !== ssi) {
        await fullEngine.stash(SSI_STASH, ssi);
        stashedSsi = ssi;
      }
      const inp = solveInputOf(ssi, data(), sideDraft);
      const out = await fullEngine.solve(
        "section.propose",
        {
          contract: "section_propose_input/0",
          doc: inp.doc,
          platforms: inp.platforms,
          access: inp.access,
          request: { kind: "paint_review" },
        },
        { base: SSI_STASH },
      );
      paintRows = ((out.result as SectionProposal).paints ?? []) as PaintRowView[];
    } catch (e) {
      host.problem(e);
    } finally {
      busy = null;
      renderLine();
    }
  };

  /** Check all lines (2996-3010): every Metro line's whole solve, its unbuildable km, misfits, errors and paints. */
  const checkAll = async () => {
    if (busy) return;
    const secs = await loadSections();
    const metro = secs.filter((x) => x.system !== "rer" && x.system !== "tri");
    const rows: CheckRow[] = [];
    fullEngine ??= createEngine();
    try {
      for (const [i, x] of metro.entries()) {
        busy = `Checking ${x.name} (${i + 1} of ${metro.length})…`;
        renderLine();
        let sol: SolvedSection;
        let doc: SectionSolveInput["doc"];
        if (x.id === target?.sectionId && solved && ssi) {
          sol = solved;
          doc = solveInputOf(ssi, data(), sideDraft).doc;
        } else {
          const inp = await host.api.solveInput(x.id, view);
          sol = (await fullEngine.solve("section.solve", inp, {})).result as SolvedSection;
          doc = inp.doc;
        }
        const step = sol.step_m;
        const km = (w: string) => sol.bad.filter((b) => b.why === w).reduce((t, b) => t + b.c1 - b.c0 + step, 0) / 1000;
        rows.push({
          id: x.id,
          name: x.name,
          cover: km("cover"),
          box: km("box"),
          fit: sol.misfits.reduce((t, m) => t + m.c1 - m.c0 + step, 0) / 1000,
          err: sol.flags.filter((f) => f.sev === "error" && !f.pending).length,
          paint: (doc?.ovr ?? []).reduce((t, o) => t + (o[1] - o[0]), 0) / 1000,
        });
        checkRows = rows.slice();
      }
      checkNote = `${rows.length} Metro lines checked (each as saved in this view; this line as drawn now).`;
    } catch (e) {
      checkNote = `The check stopped: ${String((e as Error).message ?? e)}`;
    } finally {
      busy = null;
      checkRows = rows;
      renderLine();
    }
  };

  /** The sections of the view, with their names, systems and lengths (the line picker, Check all lines). */
  let sectionsCache: { id: string; name: string; system: string; length: number }[] | null = null;
  const loadSections = async () => {
    if (sectionsCache) return sectionsCache;
    try {
      const recs = await listAll(host, "section", view, {});
      const out = recs.map((r) => {
        const d = r.data as Record<string, unknown>;
        return {
          id: r.id,
          name: typeof d.name === "string" ? d.name : shortId(r.id),
          system: typeof d.system === "string" ? d.system : "",
          length: typeof d.length_m === "number" ? d.length_m : 0,
        };
      });
      const num = (n: string) => Number(/(\d+)/.exec(n)?.[1] ?? 999);
      out.sort((a, b) => a.system.localeCompare(b.system) || num(a.name) - num(b.name) || a.name.localeCompare(b.name));
      sectionsCache = out;
      return out;
    } catch {
      return [];
    }
  };
  /** The line picker: every line with its km, by system (buildLineSel 3341). */
  const fillPicker = async () => {
    const secs = await loadSections();
    const groups = new Map<string, HTMLOptGroupElement>();
    lineSel.replaceChildren();
    if (!target)
      lineSel.append(Object.assign(document.createElement("option"), { value: "", textContent: "Pick a line" }));
    for (const x of secs) {
      const label = x.system === "metro" ? "Metro" : x.system === "cvx" ? "Express" : x.system.toUpperCase() || "Other";
      let g = groups.get(label);
      if (!g) {
        g = Object.assign(document.createElement("optgroup"), { label });
        groups.set(label, g);
        lineSel.append(g);
      }
      g.append(
        Object.assign(document.createElement("option"), {
          value: x.id,
          textContent: `${x.name} · ${(x.length / 1000).toFixed(1)} km`,
        }),
      );
    }
    lineSel.value = target?.sectionId ?? "";
  };

  // ---- the settings (R20): the settings.* params, each a draft on its record
  /** The settings' param records by key (settings.<key>, the system's own or this line's). */
  let settingRecs = new Map<string, { rec: Rec; own: boolean }>();
  const registryVals = new Map<string, number>();
  let resetArmed: ReturnType<typeof setTimeout> | null = null;
  let popKind: "settings" | "help" | null = null;
  const loadSettings = async () => {
    try {
      const recs = (await listAll(host, "param", view, {})).filter((r) =>
        String((r.data as Record<string, unknown>).path ?? "").startsWith("settings."),
      );
      const route = ssi?.route ?? null;
      const out = new Map<string, { rec: Rec; own: boolean }>();
      for (const r of recs) {
        const d = r.data as { path: string; scope?: { kind: string; id: string } | null };
        const key = d.path.slice("settings.".length);
        const scope = d.scope ?? null;
        const mine = !!scope && (scope.id === target?.sectionId || (route !== null && scope.id === route));
        if (scope && !mine) continue;
        const had = out.get(key);
        if (!had || mine) out.set(key, { rec: r, own: mine });
      }
      settingRecs = out;
    } catch {
      settingRecs = new Map();
    }
  };
  const paramValue = (rec: Rec): number => {
    const d = (host.drafts.get("param", rec.id, view)?.body ?? bodyOf(rec)).data as { value?: unknown };
    return Number(d.value);
  };
  /** The settings Ben changed in his drafts, as the whole solve's settings (pool in metres, as the param holds it). */
  const settingsOverride = (): Record<string, number> | null => {
    const out: Record<string, number> = {};
    for (const [k, { rec }] of settingRecs) {
      if (!host.drafts.get("param", rec.id, view)) continue;
      const v = paramValue(rec);
      if (Number.isFinite(v)) out[k === "poolFt" ? "pool" : k] = v;
    }
    return Object.keys(out).length ? out : null;
  };
  const renderPop = () => {
    if (popKind === null) {
      pop.hidden = true;
      pop.replaceChildren();
      settingsBtn.setAttribute("aria-expanded", "false");
      helpBtn.setAttribute("aria-expanded", "false");
      return;
    }
    pop.hidden = false;
    // under the tools row, so its buttons stay free
    pop.style.top = `${toolsRow.offsetTop + toolsRow.offsetHeight + 4}px`;
    settingsBtn.setAttribute("aria-expanded", String(popKind === "settings"));
    helpBtn.setAttribute("aria-expanded", String(popKind === "help"));
    if (popKind === "help") {
      pop.replaceChildren(helpCard());
      return;
    }
    const params = new Map<string, SettingParam>();
    for (const [k, { rec, own }] of settingRecs)
      params.set(k, {
        value: paramValue(rec),
        changed: !!host.drafts.get("param", rec.id, view),
        own,
        registry: registryVals.get(k) ?? null,
      });
    const prev = document.activeElement as HTMLElement | null;
    const focusKey = pop.contains(prev) ? (prev as HTMLInputElement).dataset.key : undefined;
    pop.replaceChildren(
      buildSettings({
        units: host.units,
        params,
        canEdit: paramEditable === true,
        readOnly: paramEditable === true ? null : paramEditable,
        resetArmed: resetArmed !== null,
        edit: (key, value) => {
          const r = settingRecs.get(key);
          if (!r) return;
          try {
            host.drafts.edit(r.rec, view, [{ op: "replace", path: "/data/value", value }], {
              label: `setting ${key}`,
            });
          } catch (e) {
            host.problem(e);
          }
        },
        restoreDefaults: () => void restoreDefaults(),
        resetLine: () => {
          if (!canEdit()) return;
          if (!resetArmed) {
            // armed for 4 s, as the station's Remove (the old page's 3 s was short once the sheet is busy)
            resetArmed = setTimeout(() => {
              resetArmed = null;
              renderPop();
            }, 4000);
            renderPop();
            return;
          }
          clearTimeout(resetArmed);
          resetArmed = null;
          renderPop();
          void propose({ kind: "reset" }, "Reset this line");
        },
      }),
    );
    if (focusKey) (pop.querySelector(`input[data-key="${focusKey}"]`) as HTMLInputElement | null)?.focus();
  };
  let paramEditable: true | string = "Loading…";
  const toggleSettings = async () => {
    if (popKind === "settings") {
      popKind = null;
      renderPop();
      return;
    }
    popKind = "settings";
    paramEditable = await host.editable("param", view);
    await loadSettings();
    renderPop();
  };
  // a press outside the settings or the help closes it, as the old page's pop (3765)
  const onDocDown = (e: PointerEvent) => {
    const t = e.target as Node | null;
    if (popKind && t && !pop.contains(t) && t !== settingsBtn && t !== helpBtn) {
      popKind = null;
      renderPop();
    }
  };
  document.addEventListener("pointerdown", onDocDown);
  const toggleHelp = () => {
    popKind = popKind === "help" ? null : "help";
    renderPop();
  };
  /** Restore defaults (3766): every setting back to the registry's value, as drafts Ben saves or discards. */
  const restoreDefaults = async () => {
    for (const [k, { rec, own }] of settingRecs) {
      if (own) continue;
      let reg = registryVals.get(k);
      if (reg === undefined) {
        try {
          const r = await host.records.get("param", rec.id, { ...view, layer: "import:registry" });
          reg = Number((r.data as { value?: unknown }).value);
          if (Number.isFinite(reg)) registryVals.set(k, reg);
        } catch {
          reg = undefined;
        }
      }
      if (reg === undefined || !Number.isFinite(reg)) continue;
      if (paramValue(rec) === reg) {
        const key = host.drafts.key("param", rec.id, view);
        if (host.drafts.byKey(key)) host.drafts.drop(key);
        continue;
      }
      try {
        host.drafts.edit(rec, view, [{ op: "replace", path: "/data/value", value: reg }], {
          label: `setting ${k} to default`,
        });
      } catch (e) {
        host.problem(e);
      }
    }
    renderPop();
  };

  // ---- the exports (R16 to R19)
  const exportModel = (): ExportModel | null => {
    if (!input || !target) return null;
    const d = data() ?? {};
    const fs = facts ?? [];
    const st = localInput(input, d, frame).stations;
    const half = input.params.platform_m / 2;
    const profile: Record<string, unknown> = {};
    for (const f of ["st", "pvi", "ovr", "gnd", "shafts", "tf", "ready", "sg", "gapfill", "stt", "so", "del", "access"])
      if (Object.hasOwn(d, f)) profile[f] = (d as Record<string, unknown>)[f];
    const sm = solved?.summary as { len?: Record<string, number>; maxG?: number } | undefined;
    return {
      id: sectionName.replace(/\s+/g, "_"),
      line: sectionName,
      system: ssi?.system ?? si?.system ?? "metro",
      length: input.length_m,
      platform: input.params.platform_m,
      path: (ssi?.path ?? []) as ExportModel["path"],
      railAt: railNow,
      groundAt: (c) => groundBelow(c),
      surveyedAt: (c) => (input?.ground ? valueAt(input.ground.z_m, input.ground.step_m, c) : null),
      typeAt: typeNow,
      stations: st.map((s) => {
        const f = fs.find((x) => x.platform_id === s.platform_id);
        const rail = s.level_m ?? f?.rail_m ?? railNow(s.c_m);
        return {
          name: platformName(s.platform_id),
          c: s.c_m,
          point_c: stopOf(s.platform_id) ?? s.c_m,
          rail,
          ground: f?.ground_m ?? groundBelow(s.c_m),
          depth: f?.depth_m ?? null,
          type: stationTypeAt(rail ?? null, railNow(s.c_m), typeNow(s.c_m), f?.type ?? null),
          sg: s.grade_permille ?? 0,
        };
      }),
      // keyed by station as the old doc was, not by the hub's platform ids
      profile: profileByKey(profile, (pid) => fs.find((x) => x.platform_id === pid)?.key ?? null),
      summary: sm?.len
        ? {
            km_by_type: Object.fromEntries(Object.entries(sm.len).map(([k, v]) => [k, Math.round(v) / 1000])),
            max_grade_permille: Math.round((sm.maxG ?? 0) * 10) / 10,
            grades_over_limit: (solved?.over ?? []).filter((o) => o.sev === "error").length,
          }
        : null,
      ...(half ? {} : {}),
    };
  };
  const exportAs = async (kind: "png" | "json" | "geojson" | "kmz") => {
    const m = exportModel();
    if (!m || !input) return;
    if ((kind === "geojson" || kind === "kmz") && m.path.length < 2) {
      host.toast({ text: "No plan path for this line yet: the GeoJSON and KMZ need it", level: "warn", ttl: 3000 });
      return;
    }
    const now = new Date().toISOString();
    if (kind === "json")
      download(`${m.id}_alignment.json`, new Blob([exportJson(m, now)], { type: "application/json" }));
    else if (kind === "geojson")
      download(`${m.id}_profile.geojson`, new Blob([exportGeoJson(m, now)], { type: "application/geo+json" }));
    else if (kind === "kmz")
      download(
        `${m.id}_profile.kmz`,
        new Blob([exportKmz(m, now) as BlobPart], { type: "application/vnd.google-earth.kmz" }),
      );
    else {
      // the whole line at 1 px per 6 m (2,400 to 7,000 px) by 1,000 px, nothing selected (exportPng 3792)
      const W = Math.max(2400, Math.min(7000, Math.round(input.length_m / 6)));
      const H = 1000;
      const c = document.createElement("canvas");
      c.width = W;
      c.height = H;
      const g = c.getContext("2d");
      if (!g) return;
      const keep = { range, selected, pointer, cursor };
      range = [0, input.length_m];
      selected = null;
      pointer = null;
      cursor = null;
      try {
        g.fillStyle = "#16181d";
        g.fillRect(0, 0, W, H);
        renderBands(g, W, H, 1);
        g.fillStyle = "#d8dbe2";
        g.font = "600 16px system-ui, sans-serif";
        g.fillText(`${m.system} · ${m.line}`, 12, 22);
        g.font = "12px system-ui, sans-serif";
        const first = m.stations[0]?.name ?? "";
        const last = m.stations[m.stations.length - 1]?.name ?? "";
        g.fillText(
          `Long section, ${first} to ${last} · ${(m.length / 1000).toFixed(2)} km · ${now.slice(0, 10)}`,
          12,
          40,
        );
      } finally {
        ({ range, selected, pointer, cursor } = keep);
        draw();
      }
      const blob = await new Promise<Blob | null>((res) => c.toBlob(res, "image/png"));
      if (blob) download(`${m.id}_profile.png`, blob);
    }
    host.toast({ text: `${m.id} exported (${kind.toUpperCase()}), as drawn now`, level: "info", ttl: 2500 });
  };

  /** The slide limit (literal.SLIDE_M), 150 m when the hub has not said. */
  const slideMax = () => si?.params.slide_max_m ?? 150;

  /** Open a param record in the inspector by its path (the Limits rows). */
  const openParam = async (path: string) => {
    try {
      const { items } = await host.records.list("param", view, { q: path, limit: 20 });
      const hit = items.find((r) => (r.data as Record<string, unknown>).path === path) ?? items[0];
      if (!hit) {
        host.toast({ text: `No param record ${path} in this view.`, level: "warn" });
        return;
      }
      host.openPane("inspector");
      host.select({ kind: "param", id: hit.id });
    } catch (e) {
      host.problem(e);
    }
  };

  /** Remove a station (its key into del); the selection goes, as on the old page. */
  const removeSelected = (id: string) => {
    editStation(id, "removed", (cur) => removeStation(cur, id));
    removeArmed = null;
    selected = null;
    markRows();
    renderCard();
    draw();
  };

  /** A station's rail level in the draft now: its own, else the solved rail at its centre. */
  const levelNow = (id: string): number | null => {
    if (!input) return null;
    const s = localInput(input, data(), frame).stations.find((x) => x.platform_id === id);
    const rail = local
      ? { rail_m: local.rail_m, grade_permille: local.grade_permille, step_m: local.grid.step_m }
      : null;
    return s ? stationLevel(s, rail) : null;
  };

  /** Select the previous or next live station and centre on it ([ and ]). */
  const stepStation = (by: number) => {
    if (!input) return;
    const stations = localInput(input, data(), frame).stations;
    if (!stations.length) return;
    const cur = selected?.kind === "station" ? stations.findIndex((s) => s.platform_id === selected?.id) : -1;
    const k = cur < 0 ? (by > 0 ? 0 : stations.length - 1) : Math.max(0, Math.min(stations.length - 1, cur + by));
    const s = stations[k];
    if (s) selectStation(s.platform_id, true);
  };

  /**
   * Ease the bends of some platforms (easePlatform, 3579-3592, and Ease all, 3676): each platform's grade the mean of
   * the grades either side, within the limit, three passes with the rail solved again between them, as one undo step.
   */
  const easeStations = async (ids: string[]) => {
    if (!input || !canEdit()) return;
    const half = input.params.platform_m / 2;
    const limit = si?.params.sg_max_permille ?? 7.5;
    const step = `ease:${Date.now()}`;
    const label = ids.length === 1 ? `${platformName(ids[0] as string)} eased` : "all platforms eased";
    canvas.dataset.easing = "1";
    try {
      await easePasses(ids, half, limit, step, label);
    } finally {
      canvas.dataset.easing = "0";
    }
    if (ids.length > 1) host.toast({ text: "Platforms sloped toward their grades.", level: "info", ttl: 2500 });
  };
  const easePasses = async (ids: string[], half: number, limit: number, step: string, label: string) => {
    if (!input) return;
    // As the old page (easePlatform, 3579; Ease all 3676): each platform three times, then the next, so a platform
    // eases against its neighbours as already eased.
    for (const id of ids) {
      for (let pass = 0; pass < 3; pass++) {
        const out = await host.engine.solve("vertical.rail", solveInput(input, data(), frame));
        const dv = (out.result as VerticalRail).dv;
        const s = localInput(input, data(), frame).stations.find((x) => x.platform_id === id);
        if (!s) continue;
        const g = easeGrade(dv, s.c_m, half, limit);
        if (g !== null) edit((cur) => setStationGrade(cur, id, g), { step, label });
      }
    }
  };

  // ------------------------------------------------------------------------------------------------ the canvas

  /** The level range held while a drag is on, so the axis does not jump under the pointer (the old yFrozen). */
  let frozen: { z0: number; z1: number } | null = null;
  /** The pointer over the canvas, for the readout box. */
  let pointer: { x: number; y: number } | null = null;

  /** Keep a range within the line: at least 120 m, at most the whole line with a little air. */
  const clampRange = (r: [number, number]): [number, number] => {
    const len = input?.length_m ?? 1000;
    const air = len * 0.03;
    const span = Math.min(len + 2 * air, Math.max(120, r[1] - r[0]));
    let c0 = r[0];
    if (c0 < -air) c0 = -air;
    if (c0 + span > len + air) c0 = len + air - span;
    return [c0, c0 + span];
  };

  const sheetView = (w: number, h: number): SheetView => {
    const [c0, c1] = range ?? [0, input?.length_m ?? 1000];
    const profileH =
      h -
      bands()
        .filter((b) => b.axis === "strip")
        .reduce((s, b) => s + b.height, 0);
    const M = margins(w, profileH);
    const plot = { x: M.l, y: M.t, w: Math.max(10, w - M.l - M.r), h: Math.max(10, profileH - M.t - M.b) };
    let z0 = Number.POSITIVE_INFINITY;
    let z1 = Number.NEGATIVE_INFINITY;
    const scan = (arr: ArrayLike<number> | undefined, step: number) => {
      if (!arr) return;
      const i0 = Math.max(0, Math.floor(c0 / step));
      const i1 = Math.min(arr.length - 1, Math.ceil(c1 / step));
      for (let i = i0; i <= i1; i++) {
        const z = arr[i];
        if (z !== undefined && Number.isFinite(z)) {
          if (z < z0) z0 = z;
          if (z > z1) z1 = z;
        }
      }
    };
    if (input?.ground) scan(input.ground.z_m, input.ground.step_m);
    // a rail only where there is a design: an empty profile's rail is 0 m (hasDesign); the bend points drawn (the
    // default design's on a line with none saved, Line 2b's on the current stops)
    const li = input ? localInput(input, data(), frame) : null;
    const designed = !!local && hasDesign(li);
    if (local && designed) scan(local.rail_m, local.grid.step_m);
    for (const p of li?.pvi ?? []) if (p.c_m >= c0 && p.c_m <= c1) scan([p.z_m], 1);
    // the structure under each bend point, the river and the crossing lines' boxes, as the old yRangeFor
    const ext = levelExtent({ dv: designed ? local?.dv : undefined, solved, solveInput: ssi }, c0, c1);
    if (ext) [z0, z1] = [Math.min(z0, ext.lo), Math.max(z1, ext.hi)];
    if (!Number.isFinite(z0)) [z0, z1] = [150, 250];
    const pad = Math.max(3, (z1 - z0) * 0.08);
    z0 -= pad;
    z1 += pad;
    if (frozen) {
      z0 = Math.min(frozen.z0, z0);
      z1 = Math.max(frozen.z1, z1);
      frozen = { z0, z1 };
    }
    const sx = plot.w / Math.max(1e-6, c1 - c0);
    const sy = plot.h / Math.max(1e-6, z1 - z0);
    return {
      c0,
      c1,
      z0,
      z1,
      width: w,
      height: h,
      dpr: globalThis.devicePixelRatio ?? 1,
      top: profileH,
      plot,
      pointer,
      x: (c) => plot.x + (c - c0) * sx,
      c: (x) => c0 + (x - plot.x) / sx,
      y: (z) => plot.y + (z1 - z) * sy,
      z: (y) => z1 - (y - plot.y) / sy,
      units: host.units,
      cursor,
    };
  };

  let lastView: SheetView | null = null;
  // Drawing waits for the next frame, so a burst of keystrokes and solves draws once per frame. One rail solve and
  // one paint per frame, never at once (speed): the frame paints, then the solve asked for meanwhile starts in a
  // task right after the frame (its paint and raster done), lands a few ms later and is painted by the next frame.
  // A frame that comes while a rail solve is out holds its paint until it lands (HOLD_MS at most): the paint would
  // hold the answer up, and show the old rail under the marks that moved it.
  let frameReq = 0;
  const HOLD_MS = 50;
  let heldAt = 0;
  const draw = () => {
    if (frameReq) return;
    frameReq = requestAnimationFrame(onFrame);
  };
  const onFrame = () => {
    frameReq = 0;
    if (solving) {
      const now = performance.now();
      if (!heldAt) heldAt = now;
      if (now - heldAt < HOLD_MS) return;
    }
    heldAt = 0;
    paint();
    if (solveDue) afterFrame.port2.postMessage(0);
  };
  /** Paint now (a hit test reads what the bands drew). */
  const paintNow = () => {
    if (frameReq) {
      cancelAnimationFrame(frameReq);
      frameReq = 0;
    }
    paint();
    if (solveDue) afterFrame.port2.postMessage(0);
  };
  /** A rail solve landed: the work that waited for it, then the paint on the next frame. */
  const landed = () => {
    for (const fn of railWaiters.splice(0)) fn();
    draw();
  };
  /** Whether Ben is dragging something that edits the draft (not a pan). */
  const editingDrag = () => !!drag && moved && drag.kind !== "pan" && drag.kind !== "overview";
  let shownText = "";
  const paint = () => {
    const p0 = performance.now();
    paintOnce();
    canvas.dataset.paintMs = (performance.now() - p0).toFixed(1);
  };
  const paintOnce = () => {
    const w = canvasWrap.clientWidth;
    const h = canvasWrap.clientHeight;
    if (!w || !h) return;
    const dpr = globalThis.devicePixelRatio ?? 1;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }
    const g = canvas.getContext("2d");
    if (!g) return;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    // A drag step draws again only where it changed things (dirty.ts); any other frame, the whole canvas.
    const part: { rects: { main: Rect; strips: Rect } | null; key: unknown[] } = { rects: null, key: [] };
    const prepare = (v: SheetView) => {
      part.key = frameKey(v, w, h, dpr);
      part.rects = dragRects(v, w, h, part.key);
      if (!part.rects) {
        g.clearRect(0, 0, w, h);
        return;
      }
      const r = part.rects.main;
      g.save();
      g.beginPath();
      g.rect(r.x, r.y, r.w, r.h);
      g.clip();
      g.clearRect(r.x, r.y, r.w, r.h);
    };
    let out = renderBands(g, w, h, dpr, staticLayer, prepare);
    if (part.rects) {
      g.restore();
      // the strips under the plot (the readout line, the overview) on their own: only the strip bands draw there
      const r = part.rects.strips;
      g.save();
      g.beginPath();
      g.rect(r.x, r.y, r.w, r.h);
      g.clip();
      g.clearRect(r.x, r.y, r.w, r.h);
      renderBands(g, w, h, dpr, staticLayer, null, (b) => b.axis === "strip");
      g.restore();
      const was = painted as NonNullable<typeof painted>;
      const rects = [part.rects.main, part.rects.strips];
      if (
        heldInside(was.marks, out.marks, rects, out.v.x, false) &&
        heldInside(was.texts, out.texts, rects, out.v.x, true)
      )
        dirtyFrames.part++;
      else {
        // something changed outside what was drawn (a label thinned away far off): the whole frame, now
        dirtyFrames.whole++;
        g.clearRect(0, 0, w, h);
        out = renderBands(g, w, h, dpr, staticLayer);
        part.key = frameKey(out.v, w, h, dpr);
      }
    }
    const { texts, marks, v } = out;
    const ro = marks.find((m) => m.kind === "readout") as
      | { x0: number; y0: number; x1: number; y1: number }
      | undefined;
    painted = {
      key: part.key,
      rail: local?.rail_m ?? null,
      texts,
      marks,
      readout: ro ? { x: ro.x0, y: ro.y0, w: ro.x1 - ro.x0, h: ro.y1 - ro.y0 } : null,
      cursorX: v.cursor === null ? null : v.x(v.cursor),
      dragAt: dragAt(),
    };
    canvas.dataset.staticDraws = String(staticLayer.draws);
    canvas.dataset.partFrames = String(dirtyFrames.part);
    canvas.dataset.wholeAfterPart = String(dirtyFrames.whole);
    lastView = v;
    showText(texts);
    lastMarks = marks;
  };
  /** What the last frame on the canvas was drawn from, for the next drag step's regions. */
  let painted: {
    key: unknown[];
    rail: ArrayLike<number> | null;
    texts: SheetText[];
    marks: SheetMark[];
    readout: Rect | null;
    cursorX: number | null;
    dragAt: [number, number] | null;
  } | null = null;
  /** Drag steps drawn in part, and those that had to be drawn whole after all. */
  const dirtyFrames = { part: 0, whole: 0 };
  /** Everything but the rail a frame is drawn from: when one of these changed, the frame is drawn whole. */
  const frameKey = (v: SheetView, w: number, h: number, dpr: number): unknown[] => [
    w,
    h,
    dpr,
    v.c0,
    v.c1,
    v.z0,
    v.z1,
    v.plot.x,
    v.plot.y,
    v.plot.w,
    v.plot.h,
    v.top,
    host.units.length,
    show,
    tool,
    solved,
    ssi,
    input,
    facts,
    server,
    selected?.kind ?? null,
    staticLayer.draws,
  ];
  /** The chainage range of what is dragged: the bend point, or the station's platform. */
  const dragAt = (): [number, number] | null => {
    if (drag?.kind === "pvi" && selected?.kind === "pvi") return [selected.c, selected.c];
    if (drag?.kind === "station" && input) {
      const id = drag.id;
      const s = localInput(input, data(), frame).stations.find((x) => x.platform_id === id);
      const half = input.params.platform_m / 2;
      return s ? [s.c_m - half, s.c_m + half] : null;
    }
    return null;
  };
  /** The margin either side of the rail's changed stretch: its grade labels, level tags and joins. */
  const DIRTY_MARGIN = 100;
  /**
   * The regions a drag step changes, or null to draw the whole frame: only while a bend point or a station level is
   * dragged, on the frame the last one was drawn on. The rail's changed stretch (full height), the strips under the
   * plot (the readout line, the overview), the cursor line, and the readout box at the pointer, then and now.
   */
  const dragRects = (v: SheetView, w: number, h: number, key: unknown[]): { main: Rect; strips: Rect } | null => {
    const was = painted;
    if (!was || !local || !was.rail || !editingDrag() || (drag?.kind !== "pvi" && drag?.kind !== "station"))
      return null;
    if (!sameKey(was.key, key)) return null;
    const out: Rect[] = [];
    const add = (r: Rect | null) => {
      if (r) out.push(r);
    };
    // the dragged bend point or station, where it was and where it is (its marks move before the rail is solved)
    const at = dragAt();
    for (const c of [was.dragAt, at])
      if (c !== null)
        add(grow({ x: v.x(c[0]) - DIRTY_MARGIN, y: 0, w: v.x(c[1]) - v.x(c[0]) + 2 * DIRTY_MARGIN, h }, 0, w, h));
    const span = railSpan(was.rail, local.rail_m);
    if (span) {
      const step = local.grid.step_m;
      const xa = v.x(span[0] * step) - DIRTY_MARGIN;
      const xb = v.x(span[1] * step) + DIRTY_MARGIN;
      add(grow({ x: xa, y: 0, w: xb - xa, h }, 0, w, h));
    }
    const strips = grow({ x: 0, y: v.top, w, h: h - v.top }, 2, w, h);
    const P = v.plot;
    for (const x of [was.cursorX, v.cursor === null ? null : v.x(v.cursor)])
      if (x !== null) add(grow({ x, y: P.y, w: 0, h: h - P.y }, 3, w, h));
    // the readout box: where it was, and where it goes at the pointer, as the chainage band places it
    const pt = v.pointer;
    if (pt && pt.y >= P.y && pt.y <= P.y + P.h) {
      if (!was.readout) return null;
      add(grow(was.readout, 2, w, h));
      const bw = was.readout.w + 40;
      const bh = was.readout.h + 30;
      let bx = pt.x + 14;
      if (bx + bw > P.x + P.w) bx = pt.x - 14 - bw;
      let by = pt.y + 14;
      if (by + bh > P.y + P.h) by = Math.max(P.y, pt.y - 14 - bh);
      add(grow({ x: bx, y: by, w: bw, h: bh }, 2, w, h));
    } else if (was.readout) add(grow(was.readout, 2, w, h));
    const main = bbox(out);
    return main && strips ? { main, strips } : null;
  };
  /** What the static bands reported and the label boxes they took, kept with their bitmap. */
  type StaticKept = {
    texts: SheetText[];
    marks: SheetMark[];
    labels: { x0: number; y0: number; x1: number; y1: number }[];
  };
  /** The static bands as a bitmap, copied under the others on each frame (static_layer.ts). */
  const staticLayer = new StaticLayer<StaticKept>(() => document.createElement("canvas"));
  /** Every band into a 2D context of w by h CSS pixels, on the sheet's range (the canvas, or an export). With a
   * static layer, the leading static bands come from its bitmap, drawn again only when what they read changes. */
  const renderBands = (
    g: CanvasRenderingContext2D,
    w: number,
    h: number,
    dpr: number,
    layer: StaticLayer<StaticKept> | null = null,
    prepare: ((v: SheetView) => void) | null = null,
    only: ((b: BandDef) => boolean) | null = null,
  ) => {
    const v = sheetView(w, h);
    prepare?.(v);
    const texts: SheetText[] = [];
    const marks: SheetMark[] = [];
    const li = input ? localInput(input, data(), frame) : null;
    const bd: BandData = {
      sectionId: target?.sectionId ?? "",
      input: li,
      // no rail on a line with no design yet (hasDesign): the stations stand at ground - the default depth instead
      rail:
        local && hasDesign(li)
          ? { rail_m: local.rail_m, grade_permille: local.grade_permille, step_m: local.grid.step_m }
          : null,
      server: server ? { rail_m: server.rail_m, step_m: server.step_m } : null,
      profile: target?.profile ?? null,
      selected,
      platformName,
      dv: local?.dv,
      curves: local?.curves,
      stopC: stopOf,
      report: (t) => texts.push(t),
      facts,
      mark: (m) => marks.push(m),
      solved,
      solveInput: ssi,
      show,
      draft: data(),
      tool,
      paintPreview: drag?.kind === "paint" ? { c0: drag.c0, c1: drag.c1, colour: brushColour(brush) } : null,
    };
    let top = v.top;
    const bandMs: Record<string, number> = {};
    const list = bands();
    const head = layer ? staticPrefix(list) : 0;
    if (head) {
      const t0 = performance.now();
      const key = [w, h, dpr, v.c0, v.c1, v.z0, v.z1, v.plot.x, v.plot.y, v.plot.w, v.plot.h];
      const kept = (layer as NonNullable<typeof layer>).paint(
        g,
        [...key, host.units.length, show, solved, ssi, input, li?.ground ?? null],
        Math.round(w * dpr),
        Math.round(h * dpr),
        (bg) => {
          bg.setTransform(dpr, 0, 0, dpr, 0, 0);
          const own: StaticKept = { texts: [], marks: [], labels: [] };
          const sd: BandData = { ...bd, report: (t) => own.texts.push(t), mark: (m) => own.marks.push(m) };
          resetLabels();
          for (const b of list.slice(0, head)) b.draw(bg, v, sd);
          own.labels = labelBoxes();
          return own;
        },
      );
      texts.push(...kept.texts);
      marks.push(...kept.marks);
      // the later bands' labels keep clear of the static bands' ones, as when every band is drawn in order
      resetLabels(kept.labels);
      bandMs.static = Math.round((performance.now() - t0) * 10) / 10;
    }
    for (const b of list.slice(head)) {
      const t0 = performance.now();
      if (b.axis === "strip") {
        if (!only || only(b)) b.draw(g, { ...v, top }, bd);
        top += b.height;
      } else if (!only || only(b)) {
        b.draw(g, v, bd);
      }
      bandMs[b.id] = Math.round((performance.now() - t0) * 10) / 10;
    }
    (canvas as HTMLCanvasElement & { bandMs?: Record<string, number> }).bandMs = bandMs;
    return { texts, marks, v };
  };
  // The marks() hook: what the bands drew last, as numbers (claude/hub_maps/profiles_parity.md, check 1).
  (canvas as HTMLCanvasElement & { marks?: () => SheetMark[] }).marks = () => lastMarks;
  // and the view's chainage range, set from a test or a script ([c0, c1], kept within the line)
  (canvas as HTMLCanvasElement & { setRange?: (r: [number, number]) => void }).setRange = (r) => {
    range = clampRange(r);
    draw();
  };
  // and the rail drawn now, every sample (a test or a script compares it with the old page's railAt); null with none
  (canvas as HTMLCanvasElement & { rail?: () => unknown }).rail = () =>
    local && input && hasDesign(localInput(input, data(), frame))
      ? { step_m: local.grid.step_m, rail_m: Array.from(local.rail_m) }
      : null;
  // and a whole frame drawn now, from nothing kept (a test compares it with a drag step drawn in part)
  (canvas as HTMLCanvasElement & { repaint?: () => void }).repaint = () => {
    painted = null;
    staticLayer.reset();
    paintNow();
  };
  // and the frame they were drawn in, so a test can turn metres into pixels
  (canvas as HTMLCanvasElement & { frame?: () => unknown }).frame = () =>
    lastView && {
      c0: lastView.c0,
      c1: lastView.c1,
      z0: lastView.z0,
      z1: lastView.z1,
      plot: lastView.plot,
    };

  /** The text layer: one item per thing drawn, rebuilt only when what was drawn changes. */
  const showText = (texts: SheetText[]) => {
    const key = texts
      .map((t) => `${t.kind}|${t.id ?? ""}|${t.text}|${t.drawn}|${!!t.selected}|${t.x?.toFixed(1)}|${t.y?.toFixed(1)}`)
      .join("\n");
    if (key === shownText) return;
    shownText = key;
    textLayer.replaceChildren(
      ...texts.map((t) => {
        const li = Object.assign(document.createElement("li"), { textContent: t.text });
        li.dataset.kind = t.kind;
        if (t.id) li.dataset.id = t.id;
        li.dataset.drawn = t.drawn ? "1" : "0";
        if (t.selected) li.dataset.selected = "1";
        if (t.z !== undefined) li.dataset.z = String(t.z);
        li.dataset.c = String(t.c);
        if (t.x !== undefined) li.dataset.x = t.x.toFixed(1);
        if (t.y !== undefined) li.dataset.y = t.y.toFixed(1);
        return li;
      }),
    );
  };

  // ------------------------------------------------------------------------------------------- interaction

  const roundLevel = (v: number, coarse: boolean) => (coarse ? Math.round(v) : Math.round(v * 10) / 10);

  /** Hit-test the bands at a point, against this sheet's marks (bands are shared by every sheet pane). */
  const hitAt = (x: number, y: number): Handle | null => {
    paintNow();
    // A bend point wins over a station bar under it, as on the old page (3407-3413).
    const list = bands();
    for (const b of [...list.filter((b) => b.id === "pvi"), ...list.filter((b) => b.id !== "pvi")]) {
      const hit = b.hit?.(x, y);
      if (hit) return hit;
    }
    return null;
  };

  /** The record's row index of the PVI drawn at (c, z): the band draws them sorted, the record keeps its order. */
  const pviRowOf = (c: number, z: number | undefined): number | null => {
    const d = data();
    const row = d ? pviRows(d).find((p) => p.c === c && p.z === z) : undefined;
    return row ? row.index : null;
  };

  /** A PVI chainage moved out of any platform, to half + 3 m, as the old sheet pushed it (3143-3147). */
  const outOfPlatforms = (c: number): number => {
    if (!input) return c;
    const half = input.params.platform_m / 2 + 3;
    for (const s of localInput(input, data(), frame).stations)
      if (Math.abs(c - s.c_m) < half) return c < s.c_m ? s.c_m - half : s.c_m + half;
    return Math.min(input.length_m, Math.max(0, c));
  };

  const selectHit = (hit: Handle | null, x: number) => {
    if (!lastView) return;
    if (hit?.kind === "station" && hit.id) {
      selectStation(hit.id, false);
      return;
    }
    if (hit?.kind === "flag" && hit.id) {
      selectStation(hit.id, true, 1500);
      return;
    }
    selected = hit;
    markRows();
    renderCard();
    setChainage(host.store, hit?.c ?? lastView.c(x));
    if (hit?.kind === "pvi") {
      const n = pviRowOf(hit.c, hit.z) ?? hit.index;
      const cell = tables.querySelector(`input[aria-label="PVI ${n + 1} level"]`) as HTMLInputElement | null;
      cell?.scrollIntoView({ block: "nearest" });
    }
    draw();
  };

  type Drag =
    | { kind: "station"; id: string; y0: number; z0: number; step: string }
    | { kind: "slide"; id: string; x0: number; so0: number; step: string }
    | { kind: "pvi"; row: number; x0: number; y0: number; c0: number; z0: number; step: string }
    | { kind: "pan"; x0: number; range: [number, number] }
    | { kind: "paint"; c0: number; c1: number }
    | { kind: "gp"; l: number; k: number; x0: number; y0: number; c0: number; z0: number; step: string }
    | { kind: "overview"; y: number };
  let drag: Drag | null = null;
  /** A press on the overview strip: the view keeps its span, centred on the chainage under the pointer. */
  const centreOn = (c: number) => {
    const [a, b] = range ?? [0, input?.length_m ?? 1000];
    const span = b - a;
    range = clampRange([c - span / 2, c + span / 2]);
  };
  let downAt: { x: number; y: number; hit: Handle | null } | null = null;
  let moved = false;

  const pointOf = (e: { clientX: number; clientY: number }) => {
    const r = canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  canvas.addEventListener("pointerdown", (e) => {
    if (e.button !== 0 || !lastView) return;
    const { x, y } = pointOf(e);
    const hit = hitAt(x, y);
    downAt = { x, y, hit };
    moved = false;
    const v = lastView;
    const step = `drag:${Date.now()}`;
    const plotHit = x >= v.plot.x && x <= v.plot.x + v.plot.w && y >= v.plot.y - 4 && y <= v.plot.y + v.plot.h + 26;
    if (hit?.kind === "overview") {
      centreOn(hit.c);
      drag = { kind: "overview", y };
    } else if (tool === "ground" && hit?.kind === "gp" && canEdit() && hit.z !== undefined) {
      // Ground: drag a point of the drawn ground (3432); it is selected at once
      const l = Number(hit.id);
      selected = hit;
      renderCard();
      drag = { kind: "gp", l, k: hit.index, x0: x, y0: y, c0: hit.c, z0: hit.z, step };
    } else if (tool === "paint" && plotHit && canEdit() && hit?.kind !== "flag" && hit?.kind !== "issue") {
      // Paint: drag along the line with the brush (3441); released, the stretch is painted
      const c = Math.max(0, Math.min(input?.length_m ?? 0, v.c(x)));
      drag = { kind: "paint", c0: c, c1: c };
    } else if (tool !== "move" && hit && (hit.kind === "station" || hit.kind === "pvi")) {
      // Paint and Ground never move a station or a bend point: a press there pans, as on the old page
      drag = range ? { kind: "pan", x0: x, range: [...range] as [number, number] } : null;
    } else if (tool === "move" && hit?.kind === "station" && hit.id && canEdit() && e.altKey) {
      // Alt + drag slides the platform along its drawn point (S45).
      const so = (data()?.so?.[hit.id] as number | undefined) ?? 0;
      drag = { kind: "slide", id: hit.id, x0: x, so0: so, step };
    } else if (tool === "move" && hit?.kind === "station" && hit.id && canEdit() && hit.z !== undefined)
      drag = { kind: "station", id: hit.id, y0: y, z0: hit.z, step };
    else if (tool === "move" && hit?.kind === "pvi" && canEdit() && hit.z !== undefined) {
      const row = pviRowOf(hit.c, hit.z);
      drag = row === null ? null : { kind: "pvi", row, x0: x, y0: y, c0: hit.c, z0: hit.z, step };
    } else if (range) drag = { kind: "pan", x0: x, range: [...range] as [number, number] };
    if (drag && drag.kind !== "pan" && drag.kind !== "overview" && drag.kind !== "paint")
      frozen = { z0: v.z0, z1: v.z1 };
    canvas.setPointerCapture?.(e.pointerId);
    canvas.focus({ preventScroll: true });
  });

  canvas.addEventListener("pointermove", (e) => {
    if (!lastView) return;
    const { x, y } = pointOf(e);
    pointer = { x, y };
    const v = lastView;
    if (downAt && Math.abs(x - downAt.x) + Math.abs(y - downAt.y) > 3) moved = true;
    if (drag && moved) {
      if (drag.kind === "paint") {
        drag.c1 = Math.max(0, Math.min(input?.length_m ?? 0, v.c(x)));
      } else if (drag.kind === "gp") {
        const z = roundLevel(drag.z0 + v.z(y) - v.z(drag.y0), e.shiftKey);
        const gsel = { l: drag.l, k: drag.k };
        const c = drag.c0 + v.c(x) - v.c(drag.x0);
        edit((cur) => moveGroundPoint(cur, gsel, c, z, input?.length_m ?? 0), {
          step: drag.step,
          label: "ground point",
        });
        const now = groundLines(data())[drag.l]?.pts[drag.k];
        if (now) selected = { band: "drawn-ground", kind: "gp", index: drag.k, id: String(drag.l), c: now.c, z: now.z };
      } else if (drag.kind === "overview") {
        const h = bands()
          .find((b) => b.id === "overview")
          ?.hit?.(x, drag.y);
        if (h) centreOn(h.c);
      } else if (drag.kind === "pan") {
        const span = drag.range[1] - drag.range[0];
        const shift = ((x - drag.x0) / v.plot.w) * span;
        range = clampRange([drag.range[0] - shift, drag.range[1] - shift]);
      } else if (drag.kind === "station") {
        const z = roundLevel(drag.z0 + v.z(y) - v.z(drag.y0), e.shiftKey);
        const id = drag.id;
        editStation(id, "rail level", (cur) => setStationLevel(cur, id, z), drag.step);
        if (selected?.kind === "station") selected = { ...selected, z };
      } else if (drag.kind === "slide") {
        // 0.5 m steps, Shift snaps to 5 m; never past the limit (the old setSo clamp).
        const raw = drag.so0 + v.c(x) - v.c(drag.x0);
        const so = e.shiftKey ? roundSlide(Math.round(raw / 5) * 5, slideMax()) : roundSlide(raw, slideMax());
        const id = drag.id;
        editStation(id, "slide", (cur) => setStationSlide(cur, id, so, slideMax()), drag.step);
      } else {
        const c = Math.round(outOfPlatforms(drag.c0 + v.c(x) - v.c(drag.x0)));
        const z = roundLevel(drag.z0 + v.z(y) - v.z(drag.y0), e.shiftKey);
        const row = drag.row;
        edit((cur) => [...setPviC(cur, row, c), ...setPviZ(cur, row, z)], { step: drag.step, label: `PVI ${row + 1}` });
        selected = { band: "pvi", kind: "pvi", index: row, c, z };
      }
    }
    cursor = v.c(x);
    if (!drag) {
      // The cursor shape tells what a press would do, as on the old sheet.
      let shape = tool === "paint" ? "cell" : tool === "ground" ? "copy" : "crosshair";
      let tip = "";
      for (const b of bands()) {
        const h = b.hit?.(x, y);
        if (h) {
          shape =
            !canEdit() || h.kind === "flag"
              ? "pointer"
              : tool !== "move" && (h.kind === "station" || h.kind === "pvi")
                ? tool === "paint"
                  ? "cell"
                  : "copy"
                : h.kind === "station"
                  ? e.altKey
                    ? "ew-resize"
                    : "ns-resize"
                  : "move";
          if (h.kind === "issue") tip = issueAt(x, y) ?? "";
          if (h.kind === "flag" && h.id) {
            const f = facts?.find((q) => q.platform_id === h.id);
            tip = (f?.flags ?? [])
              .map((q) => `${platformName(h.id as string)}: ${flagText(q, host.units, platformName)} (${q.rule})`)
              .join("\n");
          }
          break;
        }
      }
      canvas.style.cursor = shape;
      canvas.title = tip;
    } else if (drag.kind === "pan" && moved) canvas.style.cursor = "grabbing";
    draw();
  });

  const endDrag = (e: PointerEvent) => {
    const was = drag;
    const at = downAt;
    drag = null;
    downAt = null;
    frozen = null;
    canvas.releasePointerCapture?.(e.pointerId);
    if (was?.kind === "paint") {
      // the stretch painted with the brush (paintRange 3181); a click with the shaft brush puts a shaft there
      const d = data();
      const r = d ? paintRange(d, was.c0, was.c1, brush, si ? si.structure !== null : true) : null;
      if (r) {
        edit(() => r.ops, { label: r.what === "shaft" ? "shaft" : `paint ${BRUSH_LABELS[brush]}` });
        if (r.what === "shaft" && r.c !== undefined)
          host.toast({
            text: `Shaft at ${fmtCh(r.c)}: a method may change here`,
            level: "info",
            ttl: 2500,
          });
      }
    } else if (at && !moved && at.hit?.kind !== "overview" && !(tool === "paint" && at.hit?.kind !== "flag"))
      selectHit(tool === "ground" && at.hit && at.hit.kind !== "gp" && at.hit.kind !== "flag" ? null : at.hit, at.x);
    else if (was && (was.kind === "station" || was.kind === "slide" || was.kind === "gp")) renderCard();
    if (was && was.kind !== "pan" && was.kind !== "overview") {
      fullSoon();
      // the tables the drag held back (speed)
      if (tableDue && !solving && !factsBusy) {
        tableDue = false;
        refreshTable();
        renderCard();
      }
    }
    draw();
  };
  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);
  canvas.addEventListener("mouseleave", () => {
    pointer = null;
    if (!drag) cursor = host.store.getState().c;
    draw();
  });
  canvas.addEventListener("dblclick", (e) => {
    if (!lastView || !canEdit() || !local || !input) return;
    if (tool === "paint") return;
    if (tool === "ground") {
      // Ground: a point on a drawn line, else a new line of three points (addGroundAt 3156)
      const { x, y } = pointOf(e);
      const P = lastView.plot;
      if (x < P.x || x > P.x + P.w || y < P.y - 4 || y > P.y + P.h + 26) return;
      if (
        bands()
          .find((b) => b.id === "drawn-ground")
          ?.hit?.(x, y)
      )
        return;
      const d = data();
      if (!d) return;
      const len = input.length_m;
      const r = addGroundAt(d, Math.max(0, Math.min(len, lastView.c(x))), lastView.z(y), groundBelow, len);
      if ("refused" in r) {
        host.toast({ text: r.refused, level: "info", ttl: 2500 });
        return;
      }
      edit(() => r.ops, { label: r.started ? "ground line started" : "ground point added" });
      const pt = groundLines(data())[r.sel.l]?.pts[r.sel.k];
      if (pt) selected = { band: "drawn-ground", kind: "gp", index: r.sel.k, id: String(r.sel.l), c: pt.c, z: pt.z };
      if (r.started)
        host.toast({
          text: "Ground line started: drag its points, double-click on it to add more, Del removes one",
          level: "info",
          ttl: 3000,
        });
      renderCard();
      draw();
      return;
    }
    const { x } = pointOf(e);
    // Inside a platform there is no bend point to add (S8): the old page refused with these words.
    const at = lastView.c(x);
    const half = input.params.platform_m / 2;
    if (localInput(input, data(), frame).stations.some((s) => Math.abs(at - s.c_m) <= half)) {
      host.toast({ text: "Bend points go between platforms.", level: "info", ttl: 3000 });
      notice.dataset.flash = "Bend points go between platforms";
      return;
    }
    const c = Math.round(outOfPlatforms(at) * 10) / 10;
    const z = local.rail_m[Math.round(c / local.grid.step_m)] ?? 0;
    edit((cur) => addPvi(cur, c, Math.round(z * 1000) / 1000));
    selected = { band: "pvi", kind: "pvi", index: -1, c, z: Math.round(z * 1000) / 1000 };
    draw();
  });
  canvas.addEventListener(
    "wheel",
    (e) => {
      if (!lastView || !input) return;
      e.preventDefault();
      const r = canvas.getBoundingClientRect();
      const at = lastView.c(e.clientX - r.left);
      const [c0, c1] = range ?? [0, input.length_m];
      if (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
        const shift = ((e.deltaX || e.deltaY) / lastView.plot.w) * (c1 - c0);
        range = clampRange([c0 + shift, c1 + shift]);
      } else {
        const k = Math.exp(e.deltaY * 0.0015);
        const span = (c1 - c0) * k;
        const f = (at - c0) / (c1 - c0);
        range = clampRange([at - f * span, at - f * span + span]);
      }
      draw();
    },
    { passive: false },
  );
  const zoomBy = (k: number) => {
    if (!range || !input) return;
    const mid = cursor !== null && cursor >= range[0] && cursor <= range[1] ? cursor : (range[0] + range[1]) / 2;
    const f = (mid - range[0]) / (range[1] - range[0]);
    const span = (range[1] - range[0]) * k;
    range = clampRange([mid - f * span, mid - f * span + span]);
    draw();
  };
  /** The profile draft's revision, to tell whether a key edited it (the solve that follows then draws). */
  const draftRev = () => {
    const k = draftKey();
    return k ? (host.drafts.byKey(k)?.rev ?? null) : null;
  };
  canvas.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey) return;
    const rev0 = draftRev();
    const sel = selected;
    const station = sel?.kind === "station" && sel.id ? sel.id : null;
    if (e.altKey) {
      // Alt + Left or Right slides the selected platform 0.5 m (Shift 5 m), the drawn point staying put. They are
      // the browser's Back and Forward on Windows: the sheet keeps them even with nothing to slide (read only, no
      // station), so a press never leaves the hub.
      if (!(e.key === "ArrowLeft" || e.key === "ArrowRight")) return;
      e.preventDefault();
      if (!station || !canEdit()) return;
      const so =
        ((data()?.so?.[station] as number | undefined) ?? 0) +
        (e.key === "ArrowRight" ? 1 : -1) * (e.shiftKey ? 5 : 0.5);
      editStation(station, "slide", (cur) => setStationSlide(cur, station, so, slideMax()));
    } else if (
      !e.shiftKey &&
      (e.key === "m" || e.key === "M" || e.key === "p" || e.key === "P" || e.key === "g" || e.key === "G")
    ) {
      setTool(e.key.toLowerCase() === "m" ? "move" : e.key.toLowerCase() === "p" ? "paint" : "ground");
    } else if (sel?.kind === "gp" && canEdit() && (e.key === "Delete" || e.key === "Backspace")) {
      const gsel = { l: Number(sel.id), k: sel.index };
      edit((cur) => removeGroundPoint(cur, gsel), { label: "ground point removed" });
      selected = null;
      renderCard();
    } else if (
      sel?.kind === "gp" &&
      canEdit() &&
      (e.key === "ArrowUp" || e.key === "ArrowDown" || e.key === "ArrowLeft" || e.key === "ArrowRight")
    ) {
      // a ground point: up and down 0.1 (Shift 1) in the display unit, left and right 2 m (Shift 10), 3539
      const gsel = { l: Number(sel.id), k: sel.index };
      const P = groundLines(data())[gsel.l]?.pts;
      const p = P?.[gsel.k];
      if (!P || !p) return;
      const dz = e.key === "ArrowUp" ? 1 : e.key === "ArrowDown" ? -1 : 0;
      const dc = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      const z = dz ? nudgeLevel(p.z, dz as 1 | -1, e.shiftKey, host.units.length) : p.z;
      const c = p.c + dc * (e.shiftKey ? 10 : 2);
      edit((cur) => moveGroundPoint(cur, gsel, c, z, input?.length_m ?? 0), { label: "ground point" });
      const now = groundLines(data())[gsel.l]?.pts[gsel.k];
      if (now) selected = { ...sel, c: now.c, z: now.z };
      renderCard();
    } else if (e.key === "[" || e.key === "]") {
      stepStation(e.key === "]" ? 1 : -1);
    } else if ((e.key === "e" || e.key === "E") && station && canEdit()) {
      void easeStations([station]);
    } else if ((e.key === "PageUp" || e.key === "PageDown") && station && canEdit()) {
      // The platform grade by 0.5 per mille, rising with chainage.
      const sg = ((data()?.sg?.[station] as number | null | undefined) ?? 0) + (e.key === "PageUp" ? 0.5 : -0.5);
      editStation(station, "platform grade", (cur) => setStationGrade(cur, station, sg));
    } else if ((e.key === "Delete" || e.key === "Backspace") && station && canEdit()) {
      // Delete arms Remove; a second Delete within 4 s removes the station (the old card's two clicks).
      if (removeArmed && removeArmed.id === station && Date.now() < removeArmed.until) removeSelected(station);
      else {
        removeArmed = { id: station, until: Date.now() + 4000 };
        host.toast({ text: `Press Delete again to remove ${platformName(station)}.`, level: "info", ttl: 4000 });
      }
    } else if (e.key === "Escape") {
      selected = null;
      markRows();
      renderCard();
    } else if ((e.key === "f" || e.key === "F") && !e.shiftKey) {
      // F shows the whole line; Shift+F is the dock's maximise and goes on to it
      range = input ? clampRange([0, input.length_m]) : null;
    } else if (e.key === "+" || e.key === "=") zoomBy(1 / 1.4);
    else if (e.key === "-" || e.key === "_") zoomBy(1.4);
    else if ((e.key === "ArrowUp" || e.key === "ArrowDown") && sel && sel.z !== undefined && canEdit()) {
      // A station's level now, from the draft (an undo may have moved it since it was selected).
      const z0 = station ? (levelNow(station) ?? sel.z) : sel.z;
      // 0.1 (Shift 1) in the display unit, kept to the centimetre (3537): 152.02 steps to 152.12.
      const z = nudgeLevel(z0, e.key === "ArrowUp" ? 1 : -1, e.shiftKey, host.units.length);
      if (sel.kind === "station" && sel.id) {
        const id = sel.id;
        editStation(id, "rail level", (cur) => setStationLevel(cur, id, z));
        selected = { ...sel, z };
      } else if (sel.kind === "pvi") {
        const row = pviRowOf(sel.c, sel.z);
        if (row === null) return;
        edit((cur) => setPviZ(cur, row, z));
        selected = { ...sel, z };
      }
    } else if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && sel?.kind === "pvi" && canEdit()) {
      const row = pviRowOf(sel.c, sel.z);
      if (row === null) return;
      const c = Math.round(outOfPlatforms(sel.c + (e.key === "ArrowRight" ? 1 : -1) * (e.shiftKey ? 10 : 2)));
      edit((cur) => setPviC(cur, row, c));
      selected = { ...sel, c };
      setChainage(host.store, c);
    } else if ((e.key === "Delete" || e.key === "Backspace") && sel?.kind === "pvi" && canEdit()) {
      const row = pviRowOf(sel.c, sel.z);
      if (row === null) return;
      edit(() => removePvi(row));
      selected = null;
    } else return;
    e.preventDefault();
    // An edit is drawn when its solve is in; drawing now would put a whole frame between the edit and its solve.
    if (draftRev() === rev0) draw();
  });
  fit.onclick = () => {
    range = input ? clampRange([0, input.length_m]) : null;
    draw();
  };
  discard.onclick = () => {
    const k = draftKey();
    if (k) host.drafts.drop(k);
  };

  const resize = ctx.onResize(draw);
  // A sheet over 760 px wide puts the station panel in a column on the right, so the plot keeps its height.
  const layout = () => {
    root.classList.toggle("wide", root.clientWidth >= 760);
    draw();
  };
  const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(layout) : null;
  ro?.observe(canvasWrap);
  ro?.observe(root);

  /** Keep the cursor's chainage in view when it moves off the shown range (a station picked elsewhere). */
  const reveal = (c: number | null) => {
    if (c === null || !range || !input) return;
    if (c >= range[0] && c <= range[1]) return;
    const span = range[1] - range[0];
    range = clampRange([c - span / 2, c + span / 2]);
  };

  const unsubStore = host.store.subscribe((s, p) => {
    const newSel = s.sel !== p.sel && (sheetAccepts(s.sel) || shownSel === null);
    if (s.layer !== p.layer || s.year !== p.year || s.month !== p.month || s.tl !== p.tl) void load();
    else if (newSel && sheetAccepts(s.sel)) void load();
    else if (s.sel !== p.sel && sheetFollows(s.sel)) void follow(s.sel);
    else if (newSel) void load();
    if (s.c !== p.c) {
      cursor = s.c;
      reveal(cursor);
      showChainage();
      if (addButton) addButton.disabled = !data() || cursor === null || !canEdit();
      draw();
    }
  });
  const unsubDrafts = host.drafts.subscribe((key, d) => {
    // a setting Ben changed (a param draft): the whole solve previews it, the settings panel shows it
    if (key.startsWith("param/")) {
      if (popKind === "settings") renderPop();
      fullSoon();
      return;
    }
    // A side edit is a draft on a platform record of this line: the facts and the panel follow it.
    const pid = key.startsWith("platform/") ? key.slice("platform/".length).split("@")[0] : null;
    if (pid && platformRecs.has(pid) && key === host.drafts.key("platform", pid, view)) {
      showSummary();
      void solveFacts();
      return;
    }
    if (key !== draftKey()) return;
    if (paintRows !== null) {
      paintRows = null;
      setTimeout(() => void reviewPaints(), 200);
    }
    renderLineSoon();
    // Saved or discarded: the cells show the record again, and what they show is what Ctrl+Z starts from.
    if (d === null) for (const i of tables.querySelectorAll("input")) i.dataset.drawn = i.value;
    // The bar's text follows the solve too: a change in its width would lay the whole sheet out again first.
    profileDue = true;
    // The tables and the panel follow the solves (after the rail and the facts are in), so the rail's re-solve is
    // not held up by laying out their rows; a change in the number of PVIs rebuilds at once (rows go by index).
    const cur = data();
    if ((cur?.pvi?.length ?? 0) !== builtPvis) refreshTable();
    else tableDue = true;
    void solve();
  });
  const unsubUnits = host.units.onChange(() => {
    renderLineSoon();
    if (popKind) renderPop();
    showChainage();
    table();
    compare();
    draw();
  });
  const unsubNames = host.names.onChange(() => {
    if (!target) return;
    const n = host.names.peek("section", target.sectionId, view);
    if (n && n !== sectionName) {
      sectionName = n;
      title.textContent = n;
      ctx.setTitle(n);
      showProfile();
    }
    draw();
  });
  const unsubEvents = host.events.subscribe((m) => {
    if (m.type === "status") {
      // Result events sent while the stream was down are gone (section 5): read the latest result again.
      if (m.state === "open" && m.reconnected && target) void loadServer();
      return;
    }
    const ev = m.event;
    if (
      ev.type === "result" &&
      target &&
      ev.data.type === SOLVE_JOB &&
      ev.data.scope === target.sectionId &&
      ev.data.view === viewToken(view)
    ) {
      if (ev.data.status === "ok") void loadServer(ev.data.key);
    } else if (ev.type === "resync") {
      void load();
    } else if (target && ev.type === "source" && (ev.data.sections ?? []).includes(target.sectionId)) {
      // a change the live hub took in touched this line: read it now rather than after the record events' pause
      if (refreshTimer) clearTimeout(refreshTimer);
      refreshTimer = null;
      void refreshInput();
    } else if (target && ev.type === "record" && INPUT_KINDS.has(ev.data.kind)) {
      scheduleRefresh();
    } else if (target && ev.type === "changeset" && Object.keys(ev.data.kinds ?? {}).some((k) => INPUT_KINDS.has(k))) {
      scheduleRefresh();
    } else if (target && ev.type === "record" && ev.data.kind === "authority") {
      void host.editable("profile", view).then((ed) => {
        const now = target?.profile ? editMessage(ed) : editable;
        if (now !== editable) {
          editable = now;
          showNotice();
          table();
        }
      });
    }
  });
  const unsubEngine = host.engine.onChange(() => void solve());
  const unsubLive = liveBoard.subscribe(showPending);
  const active = ctx.onActive?.((on) => {
    if (focused) void host.api.focus(SOLVE_JOB, focused.sectionId, focused.token, on ? 0 : 1);
  });
  renewTimer = setInterval(
    () => {
      if (focused && target) void requestSolve();
    },
    (WATCH_S / 2) * 1000,
  );

  void load().then(() => {
    const sel = host.store.getState().sel;
    if (sheetFollows(sel)) void follow(sel);
  });
  return {
    dispose() {
      generation++;
      el.removeEventListener(MAXIMISED_EVENT, onMaximised);
      document.removeEventListener("pointerdown", onDocDown);
      if (lineTimer) clearTimeout(lineTimer);
      if (resetArmed) clearTimeout(resetArmed);
      if (factsTimer) clearTimeout(factsTimer);
      factsEngine?.dispose();
      if (frameReq) cancelAnimationFrame(frameReq);
      if (dueTimer) clearTimeout(dueTimer);
      afterFrame.port1.close();
      el.removeEventListener("keydown", keyAt, true);
      el.removeEventListener("keyup", keyAt, true);
      if (refreshTimer) clearTimeout(refreshTimer);
      host.status({ id: "sheet.chainage", remove: true });
      stopWatch?.();
      resize.dispose();
      ro?.disconnect();
      unsubStore();
      unsubDrafts();
      unsubUnits();
      unsubNames();
      unsubEvents();
      unsubEngine();
      unsubLive();
      active?.dispose();
      if (renewTimer) clearInterval(renewTimer);
      release();
    },
    serialize: () => ({ range, section: shownSection }),
  };
}
