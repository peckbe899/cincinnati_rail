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

import type { SectionInput, StationFact, StationInput, VerticalRail } from "@cr/engine/contract";
import type { JsonPatch, Rec } from "../../api/types.ts";
import { layerPhrase } from "../../core/describe.ts";
import { bodyOf } from "../../core/drafts.ts";
import { liveBoard } from "../../core/live.ts";
import { shortId } from "../../core/names.ts";
import type {
  BandData,
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
import { stationLevel } from "./bands.ts";
import {
  flagText,
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
  addPvi,
  easeGrade,
  factsInput,
  frameFor,
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
  stationFrame,
  toFloat64,
} from "./model.ts";
import { buildPanel, keepFocus } from "./panel.ts";

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
  bar.append(title, summary, profileInfo, solveInfo, serverInfo, pendingMark, saveBtn, discard, fit);
  const notice = Object.assign(document.createElement("div"), { className: "sheet-notice" });
  notice.dataset.testid = "sheet-notice";
  notice.setAttribute("role", "status");
  const canvasWrap = document.createElement("div");
  canvasWrap.className = "sheet-canvas";
  const canvas = document.createElement("canvas");
  canvas.dataset.testid = "sheet-canvas";
  canvas.tabIndex = 0;
  canvas.setAttribute("role", "img");
  canvas.setAttribute(
    "aria-label",
    "Long section. Click a station or a PVI to select it; drag it up or down to set its level, Alt + drag a station to slide it; drag elsewhere to pan; wheel to zoom; double-click the rail to add a PVI. Arrows nudge the selection (Alt + Left or Right slides a station, Page Up or Down tilts it), [ and ] step through the stations, E eases the bends, Delete twice removes a station, F shows the whole line, Esc clears.",
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
  root.append(bar, notice, canvasWrap, card, tables);
  el.append(root);

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

  /** The profile data to show: the draft's working copy, else the record. */
  const data = (): ProfileData | null => {
    const p = target?.profile;
    if (!p) return null;
    return (host.drafts.get(p.kind, p.id, view)?.body ?? bodyOf(p)).data as ProfileData;
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

  const solve = async () => {
    if (!input) return;
    if (solving) {
      again = true;
      return;
    }
    solving = true;
    solveInfo.dataset.busy = "1";
    const gen = generation;
    try {
      const inp = solveInput(input, data(), frame);
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
      if (!si) showSummary();
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
      draw();
      if (again) {
        again = false;
        void solve();
      } else {
        solveInfo.dataset.busy = "0";
      }
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
      if (solving) factsSoon();
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
      facts = (out.result as { stations: StationFact[] }).stations;
      solveInfo.dataset.factsMs = String(performance.now() - t0);
      solveInfo.dataset.factsRev = String(Number(solveInfo.dataset.factsRev ?? 0) + 1);
      showSummary();
      if (!factsAgain) {
        tableDue = false;
        refreshTable();
        renderCard();
      }
      draw();
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
    const cur = data();
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
    for (let i = 0; i < 4 && gen === generation; i++) {
      try {
        await host.engine.solve("vertical.rail", inp);
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
    const d = local ? maxDiff(local.rail_m, server.rail_m) : null;
    serverInfo.textContent = `server ${server.key.slice(0, 8)}${d === null ? "" : `, max diff ${host.units.format(d, "m", 3)} ${host.units.label("m")}`}`;
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
    server = null;
    asked = null;
    builtPvis = -1;
    selected = null;
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
      shownSection = sectionId;
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
    if (!p || !cur || !canEdit()) return;
    try {
      host.drafts.edit(p, view, make(cur), { label: `${sectionName} profile`, ...opts });
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
          (d?.st?.[s.platform_id] ?? null) !== was,
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
        "Ctrl+S or Enter in a field saves.</p>";
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
    if (local) scan(local.rail_m, local.grid.step_m);
    for (const p of input?.pvi ?? []) if (p.c_m >= c0 && p.c_m <= c1) scan([p.z_m], 1);
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
  // Drawing waits for the next frame, so a burst of keystrokes and solves draws once per frame.
  let frameReq = 0;
  const draw = () => {
    if (frameReq) return;
    frameReq = requestAnimationFrame(() => {
      frameReq = 0;
      paint();
    });
  };
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
    g.clearRect(0, 0, w, h);
    const v = sheetView(w, h);
    lastView = v;
    const texts: SheetText[] = [];
    const marks: SheetMark[] = [];
    const bd: BandData = {
      sectionId: target?.sectionId ?? "",
      input: input ? localInput(input, data(), frame) : null,
      rail: local ? { rail_m: local.rail_m, grade_permille: local.grade_permille, step_m: local.grid.step_m } : null,
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
    };
    let top = v.top;
    for (const b of bands()) {
      if (b.axis === "strip") {
        b.draw(g, { ...v, top }, bd);
        top += b.height;
      } else {
        b.draw(g, v, bd);
      }
    }
    showText(texts);
    lastMarks = marks;
  };
  // The marks() hook: what the bands drew last, as numbers (claude/hub_maps/profiles_parity.md, check 1).
  (canvas as HTMLCanvasElement & { marks?: () => SheetMark[] }).marks = () => lastMarks;
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
    if (frameReq) {
      cancelAnimationFrame(frameReq);
      frameReq = 0;
    }
    paint();
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
    | { kind: "pan"; x0: number; range: [number, number] };
  let drag: Drag | null = null;
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
    if (hit?.kind === "station" && hit.id && canEdit() && e.altKey) {
      // Alt + drag slides the platform along its drawn point (S45).
      const so = (data()?.so?.[hit.id] as number | undefined) ?? 0;
      drag = { kind: "slide", id: hit.id, x0: x, so0: so, step };
    } else if (hit?.kind === "station" && hit.id && canEdit() && hit.z !== undefined)
      drag = { kind: "station", id: hit.id, y0: y, z0: hit.z, step };
    else if (hit?.kind === "pvi" && canEdit() && hit.z !== undefined) {
      const row = pviRowOf(hit.c, hit.z);
      drag = row === null ? null : { kind: "pvi", row, x0: x, y0: y, c0: hit.c, z0: hit.z, step };
    } else if (range) drag = { kind: "pan", x0: x, range: [...range] as [number, number] };
    if (drag && drag.kind !== "pan") frozen = { z0: v.z0, z1: v.z1 };
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
      if (drag.kind === "pan") {
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
      let shape = "crosshair";
      let tip = "";
      for (const b of bands()) {
        const h = b.hit?.(x, y);
        if (h) {
          shape =
            !canEdit() || h.kind === "flag"
              ? "pointer"
              : h.kind === "station"
                ? e.altKey
                  ? "ew-resize"
                  : "ns-resize"
                : "move";
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
    if (at && !moved) selectHit(at.hit, at.x);
    else if (was && (was.kind === "station" || was.kind === "slide")) renderCard();
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
    } else if (e.key === "f" || e.key === "F") {
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
    // A side edit is a draft on a platform record of this line: the facts and the panel follow it.
    const pid = key.startsWith("platform/") ? key.slice("platform/".length).split("@")[0] : null;
    if (pid && platformRecs.has(pid) && key === host.drafts.key("platform", pid, view)) {
      showSummary();
      void solveFacts();
      return;
    }
    if (key !== draftKey()) return;
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
      if (factsTimer) clearTimeout(factsTimer);
      factsEngine?.dispose();
      if (frameReq) cancelAnimationFrame(frameReq);
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
