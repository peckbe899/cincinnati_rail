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

import type { SectionInput, VerticalRail } from "@cr/engine/contract";
import type { JsonPatch, Rec } from "../../api/types.ts";
import { layerPhrase } from "../../core/describe.ts";
import { bodyOf } from "../../core/drafts.ts";
import { shortId } from "../../core/names.ts";
import type {
  BandData,
  Handle,
  Host,
  MountedPane,
  PaneContext,
  RecordRef,
  Selection,
  SheetView,
} from "../../core/plugin.ts";
import { isRecordRef } from "../../core/plugin.ts";
import { setChainage } from "../../core/store.ts";
import { CHAINAGE_HELP, formatChainage, parseChainage } from "../../core/units.ts";
import { type View, viewToken } from "../../core/view.ts";
import {
  addPvi,
  frameFor,
  localInput,
  maxDiff,
  type ProfileData,
  pviRows,
  removePvi,
  type StationFrame,
  setPviC,
  setPviZ,
  setStationLevel,
  solveInput,
  stationFrame,
  toFloat64,
} from "./model.ts";

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
  const discard = Object.assign(document.createElement("button"), {
    type: "button",
    textContent: "Discard",
    title: "Drop the unsaved changes to this profile",
    disabled: true,
  });
  discard.dataset.testid = "sheet-discard";
  const fit = Object.assign(document.createElement("button"), { type: "button", textContent: "Fit" });
  bar.append(title, profileInfo, solveInfo, serverInfo, discard, fit);
  const notice = Object.assign(document.createElement("div"), { className: "sheet-notice" });
  notice.dataset.testid = "sheet-notice";
  notice.setAttribute("role", "status");
  const canvasWrap = document.createElement("div");
  canvasWrap.className = "sheet-canvas";
  const canvas = document.createElement("canvas");
  canvas.dataset.testid = "sheet-canvas";
  canvasWrap.append(canvas);
  const tables = document.createElement("div");
  tables.className = "sheet-table";
  root.append(bar, notice, canvasWrap, tables);
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
    } catch (e) {
      local = null;
      solveInfo.textContent =
        host.engine.state() === "unavailable"
          ? (host.engine.reason() ?? "no local engine")
          : `local solve failed: ${String((e as Error).message ?? e)}`;
    } finally {
      solving = false;
      draw();
      if (again) {
        again = false;
        void solve();
      } else {
        solveInfo.dataset.busy = "0";
      }
    }
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
      const r = await host.api.compute(SOLVE_JOB, target.sectionId, viewToken(view), 1);
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
      const [inp, fr] = await Promise.all([host.api.sectionInput(target.sectionId, view), loadFrame(target.sectionId)]);
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
    server = null;
    asked = null;
    builtPvis = -1;
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
      const [inp, fr, ed, name] = await Promise.all([
        host.api.sectionInput(sectionId, view),
        loadFrame(sectionId),
        target.profile
          ? host.editable("profile", view)
          : Promise.resolve("This section has no profile record, so the sheet is read-only."),
        host.names.get("section", sectionId, view),
      ]);
      if (gen !== generation) return;
      input = inp;
      frame = frameFor(fr, inp);
      sectionName = name;
      title.textContent = name;
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
  const edit = (make: (cur: ProfileData) => JsonPatch) => {
    const p = target?.profile;
    const cur = data();
    if (!p || !cur || !canEdit()) return;
    try {
      host.drafts.edit(p, view, make(cur));
    } catch (e) {
      host.problem(e);
    }
  };

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
          (v) => v !== null && edit((cur) => setPviC(cur, r.index, v)),
          `PVI ${r.index + 1} chainage`,
          !!b && b.c !== r.c,
          { chainage: true },
        ),
      );
      tr.append(
        numberCell(
          r.z,
          (v) => v !== null && edit((cur) => setPviZ(cur, r.index, v)),
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

    // Stations: the name first, then the level Ben edits, then the chainage (read only).
    const stt = document.createElement("table");
    stt.className = "grid";
    stt.dataset.testid = "station-table";
    stt.innerHTML = `<caption>Stations</caption><tr><th class=name>station</th><th>level (${lu})</th><th>chainage (${cu})</th></tr>`;
    const li = localInput(input, d, frame);
    const seen = new Map<string, number>();
    li.stations.forEach((s) => {
      const tr = document.createElement("tr");
      tr.dataset.platform = s.platform_id;
      const nm = platformName(s.platform_id);
      const n = (seen.get(nm) ?? 0) + 1;
      seen.set(nm, n);
      const label = n === 1 ? nm : `${nm} ${n}`;
      const name = Object.assign(document.createElement("td"), { className: "name", textContent: label });
      name.title = `${label} (platform ${s.platform_id})`;
      tr.append(name);
      const was = base?.st?.[s.platform_id] ?? null;
      tr.append(
        numberCell(
          s.level_m,
          (v) => edit((cur) => setStationLevel(cur, s.platform_id, v)),
          `Station ${label} level`,
          (d?.st?.[s.platform_id] ?? null) !== was,
          { allowNull: true },
        ),
      );
      tr.append(Object.assign(document.createElement("td"), { textContent: formatChainage(s.c_m, host.units) }));
      stt.append(tr);
    });
    const left = document.createElement("div");
    left.append(pt, add);
    tables.append(left, stt);
    if (focusLabel) {
      const again = [...tables.querySelectorAll("input")].find((x) => x.getAttribute("aria-label") === focusLabel);
      if (again) {
        again.focus();
        const n = again.value.length;
        again.setSelectionRange(n, n);
      }
    }
  };

  // ------------------------------------------------------------------------------------------------ the canvas

  const sheetView = (w: number, h: number): SheetView => {
    const [c0, c1] = range ?? [0, input?.length_m ?? 1000];
    const profileH =
      h -
      bands()
        .filter((b) => b.axis === "strip")
        .reduce((s, b) => s + b.height, 0);
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
    const pad = Math.max(2, (z1 - z0) * 0.08);
    z0 -= pad;
    z1 += pad;
    const sx = w / Math.max(1e-6, c1 - c0);
    const sy = Math.max(1, profileH - 8) / Math.max(1e-6, z1 - z0);
    return {
      c0,
      c1,
      z0,
      z1,
      width: w,
      height: h,
      dpr: globalThis.devicePixelRatio ?? 1,
      top: profileH,
      x: (c) => (c - c0) * sx,
      c: (x) => c0 + x / sx,
      y: (z) => 4 + (z1 - z) * sy,
      z: (y) => z1 - (y - 4) / sy,
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
  const paint = () => {
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
    const bd: BandData = {
      sectionId: target?.sectionId ?? "",
      input: input ? localInput(input, data(), frame) : null,
      rail: local ? { rail_m: local.rail_m, grade_permille: local.grade_permille, step_m: local.grid.step_m } : null,
      server: server ? { rail_m: server.rail_m, step_m: server.step_m } : null,
      profile: target?.profile ?? null,
      selected,
      platformName,
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
  };

  // ------------------------------------------------------------------------------------------- interaction

  canvas.addEventListener("mousemove", (e) => {
    if (!lastView) return;
    const r = canvas.getBoundingClientRect();
    cursor = lastView.c(e.clientX - r.left);
    draw();
  });
  canvas.addEventListener("mouseleave", () => {
    cursor = host.store.getState().c;
    draw();
  });
  canvas.addEventListener("click", (e) => {
    if (!lastView) return;
    const r = canvas.getBoundingClientRect();
    const x = e.clientX - r.left;
    const y = e.clientY - r.top;
    // A band's hit() answers from its last draw, and bands are shared by every sheet pane: draw this sheet now, so
    // the click is tested against this sheet's marks and not another section's.
    if (frameReq) {
      cancelAnimationFrame(frameReq);
      frameReq = 0;
    }
    paint();
    selected = null;
    for (const b of bands()) {
      const hit = b.hit?.(x, y);
      if (hit) {
        selected = hit;
        break;
      }
    }
    const c = selected?.c ?? lastView.c(x);
    setChainage(host.store, c);
    if (selected?.kind === "pvi") {
      // The band draws the PVIs sorted by chainage; the table lists them in the record's order. Find the row.
      const hit = selected;
      const d = data();
      const row = d ? pviRows(d).find((p) => p.c === hit.c && p.z === hit.z) : undefined;
      const n = row ? row.index : hit.index;
      const cell = tables.querySelector(`input[aria-label="PVI ${n + 1} level"]`) as HTMLInputElement | null;
      cell?.focus();
    }
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
        const shift = ((e.deltaX || e.deltaY) / lastView.width) * (c1 - c0);
        range = [c0 + shift, c1 + shift];
      } else {
        const k = Math.exp(e.deltaY * 0.0015);
        const span = Math.min(input.length_m * 1.2, Math.max(50, (c1 - c0) * k));
        const f = (at - c0) / (c1 - c0);
        range = [at - f * span, at - f * span + span];
      }
      draw();
    },
    { passive: false },
  );
  fit.onclick = () => {
    range = input ? [0, input.length_m] : null;
    draw();
  };
  discard.onclick = () => {
    const k = draftKey();
    if (k) host.drafts.drop(k);
  };

  const resize = ctx.onResize(draw);
  const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(draw) : null;
  ro?.observe(canvasWrap);

  /** Keep the cursor's chainage in view when it moves off the shown range (a station picked elsewhere). */
  const reveal = (c: number | null) => {
    if (c === null || !range || !input) return;
    if (c >= range[0] && c <= range[1]) return;
    const span = range[1] - range[0];
    range = [c - span / 2, c + span / 2];
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
    if (key !== draftKey()) return;
    // Saved or discarded: the cells show the record again, and what they show is what Ctrl+Z starts from.
    if (d === null) for (const i of tables.querySelectorAll("input")) i.dataset.drawn = i.value;
    showProfile();
    refreshTable();
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

  void load().then(() => {
    const sel = host.store.getState().sel;
    if (sheetFollows(sel)) void follow(sel);
  });
  return {
    dispose() {
      generation++;
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
    },
    serialize: () => ({ range, section: shownSection }),
  };
}
