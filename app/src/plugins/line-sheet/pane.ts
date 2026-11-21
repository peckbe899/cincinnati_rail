// The line sheet pane (section 8): canvas bands for one section, and a table that edits PVI and station levels.
//
// Flow: the selection (a profile or a section) gives the section; the server builds its SectionInput in the view
// (/x/profiles/sections/{id}/input). Every keystroke in the table edits the shared draft of the profile record,
// and the engine worker re-solves the draft's input at once. Save PATCHes the profile; the server's
// profiles.solve_section job runs and its result event brings the server's rail back, drawn under the local one.

import type { SectionInput, VerticalRail } from "@cr/engine/contract";
import type { JsonPatch, Rec } from "../../api/types.ts";
import { bodyOf } from "../../core/drafts.ts";
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
import { type View, viewToken } from "../../core/view.ts";
import {
  addPvi,
  localInput,
  maxDiff,
  type ProfileData,
  pviRows,
  removePvi,
  setPviC,
  setPviZ,
  setStationLevel,
  solveInput,
  toFloat64,
} from "./model.ts";

export const SOLVE_JOB = "profiles.solve_section";

interface Target {
  sectionId: string;
  profile: Rec | null;
}

/** Whether the sheet can show a selection: a profile or a section. */
export const sheetAccepts = (sel: Selection): sel is RecordRef =>
  isRecordRef(sel) && (sel.kind === "profile" || sel.kind === "section");

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

export async function mountSheet(el: HTMLElement, ctx: PaneContext): Promise<MountedPane> {
  const host = ctx.host;
  const root = document.createElement("div");
  root.className = "sheet";
  const bar = document.createElement("div");
  bar.className = "sheet-bar";
  const title = document.createElement("strong");
  const solveInfo = Object.assign(document.createElement("span"), { className: "muted" });
  solveInfo.dataset.testid = "solve-info";
  const serverInfo = Object.assign(document.createElement("span"), { className: "muted" });
  serverInfo.dataset.testid = "server-info";
  const fit = Object.assign(document.createElement("button"), { type: "button", textContent: "Fit" });
  bar.append(title, solveInfo, serverInfo, fit);
  const canvasWrap = document.createElement("div");
  canvasWrap.className = "sheet-canvas";
  const canvas = document.createElement("canvas");
  canvas.dataset.testid = "sheet-canvas";
  canvasWrap.append(canvas);
  const tables = document.createElement("div");
  tables.className = "sheet-table";
  root.append(bar, canvasWrap, tables);
  el.append(root);

  let view = host.view();
  let target: Target | null = null;
  let input: SectionInput | null = null;
  let local: VerticalRail | null = null;
  let server: { rail_m: Float64Array; step_m: number; key: string } | null = null;
  let range: [number, number] | null = ((ctx.state as { range?: [number, number] } | undefined)?.range ?? null) as
    | [number, number]
    | null;
  let cursor: number | null = host.store.getState().c;
  let selected: Handle | null = null;
  let shownSection: string | null = (ctx.state as { section?: string } | undefined)?.section ?? null;
  let stopWatch: (() => void) | null = null;
  /** The profile or section the sheet shows. A selection the sheet cannot show (a station picked on the map)
   * leaves it on its section. */
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
  const bands = () => host.registry.bandList();

  /** The profile data to show: the draft's working copy, else the record. */
  const data = (): ProfileData | null => {
    const p = target?.profile;
    if (!p) return null;
    return (host.drafts.get(p.kind, p.id, view)?.body ?? bodyOf(p)).data as ProfileData;
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
      const inp = solveInput(input, data());
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
    const inp = solveInput(input, data());
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

  const load = async () => {
    generation++;
    const gen = generation;
    view = host.view();
    stopWatch?.();
    stopWatch = null;
    target = null;
    input = null;
    local = null;
    server = null;
    asked = null;
    builtPvis = -1;
    tables.replaceChildren();
    const sel = host.store.getState().sel;
    if (sheetAccepts(sel)) shownSel = sel;
    try {
      target = await resolveTarget(host, view, shownSel);
      if (gen !== generation) return;
      if (!target) {
        title.textContent = "Line sheet";
        solveInfo.textContent = "Select a profile or a section.";
        draw();
        return;
      }
      title.textContent = `Section ${target.sectionId}`;
      ctx.setTitle(`Sheet ${target.sectionId.slice(-6)}`);
      input = await host.api.sectionInput(target.sectionId, view);
      if (gen !== generation) return;
      if (!range || shownSection !== target.sectionId) range = [0, input.length_m];
      shownSection = target.sectionId;
      if (target.profile) {
        const p = target.profile;
        stopWatch = host.records.watch(p.kind, p.id, view, (r) => {
          if (!r.data || !target || gen !== generation) return;
          target.profile = r.data;
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

  // ------------------------------------------------------------------------------------------------- the table

  /** Edit the profile's draft. The ops are made from the data as it is now (the draft's working copy), never from a
   * copy taken when the table was drawn: the table is not redrawn while a cell has the focus, and ops made from an
   * old copy would undo earlier edits ("add /data/st {}" a second time) or miss a value typed since. */
  const edit = (make: (cur: ProfileData) => JsonPatch) => {
    const p = target?.profile;
    const cur = data();
    if (!p || !cur) return;
    try {
      host.drafts.edit(p, view, make(cur));
    } catch (e) {
      host.problem(e);
    }
  };

  const numberCell = (
    value: number | null,
    xunit: string,
    onValue: (v: number | null) => void,
    label: string,
    dirty: boolean,
    allowNull = false,
  ) => {
    const td = document.createElement("td");
    const i = document.createElement("input");
    i.value = value === null ? "" : host.units.format(value, xunit);
    i.placeholder = allowNull ? "design" : "";
    i.setAttribute("aria-label", label);
    i.inputMode = "decimal";
    if (dirty) i.classList.add("dirty");
    i.disabled = !target?.profile || view.layer.includes(":");
    i.addEventListener("input", () => {
      if (allowNull && i.value.trim() === "") {
        i.classList.remove("bad");
        onValue(null);
        return;
      }
      const v = host.units.parse(i.value, xunit);
      i.classList.toggle("bad", v === null);
      if (v !== null) onValue(v);
    });
    i.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        void host.runCommand("core.save");
      }
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
    if (!input) return;
    const d = data();
    const base = target?.profile ? (target.profile.data as ProfileData) : null;
    const lu = host.units.label("m");

    const pt = document.createElement("table");
    pt.className = "grid";
    pt.dataset.testid = "pvi-table";
    pt.innerHTML = `<caption>PVIs</caption><tr><th>#</th><th>chainage (${lu})</th><th>level (${lu})</th><th></th></tr>`;
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
          "m",
          (v) => v !== null && edit((cur) => setPviC(cur, r.index, v)),
          `PVI ${r.index + 1} chainage`,
          !!b && b.c !== r.c,
        ),
      );
      tr.append(
        numberCell(
          r.z,
          "m",
          (v) => v !== null && edit((cur) => setPviZ(cur, r.index, v)),
          `PVI ${r.index + 1} level`,
          !!b && b.z !== r.z,
        ),
      );
      const rm = Object.assign(document.createElement("button"), {
        type: "button",
        textContent: "−",
        title: "Remove this PVI",
      });
      rm.disabled = !d || view.layer.includes(":");
      rm.onclick = () => edit(() => removePvi(r.index));
      const td = document.createElement("td");
      td.append(rm);
      tr.append(td);
      pt.append(tr);
    }
    const add = Object.assign(document.createElement("button"), { type: "button", textContent: "+ PVI at the cursor" });
    add.disabled = !d || cursor === null || view.layer.includes(":");
    addButton = add;
    add.onclick = () => {
      if (cursor === null) return;
      const c = cursor;
      const z = local ? (local.rail_m[Math.round(c / local.grid.step_m)] ?? 0) : 0;
      edit((cur) => addPvi(cur, Math.round(c * 10) / 10, Math.round(z * 1000) / 1000));
    };

    const stt = document.createElement("table");
    stt.className = "grid";
    stt.dataset.testid = "station-table";
    stt.innerHTML = `<caption>Stations</caption><tr><th class=name>platform</th><th>chainage (${lu})</th><th>level (${lu})</th></tr>`;
    const li = localInput(input, d);
    li.stations.forEach((s) => {
      const tr = document.createElement("tr");
      tr.dataset.platform = s.platform_id;
      const name = Object.assign(document.createElement("td"), {
        className: "name",
        textContent: s.platform_id.split("|").pop() ?? s.platform_id,
      });
      name.title = s.platform_id;
      tr.append(name);
      tr.append(Object.assign(document.createElement("td"), { textContent: host.units.format(s.c_m, "m") }));
      const was = base?.st?.[s.platform_id] ?? null;
      tr.append(
        numberCell(
          s.level_m,
          "m",
          (v) => edit((cur) => setStationLevel(cur, s.platform_id, v)),
          `Station ${s.platform_id} level`,
          (d?.st?.[s.platform_id] ?? null) !== was,
          true,
        ),
      );
      stt.append(tr);
    });
    const left = document.createElement("div");
    left.append(pt, add);
    tables.append(left, stt);
    if (!target?.profile)
      tables.append(
        Object.assign(document.createElement("p"), {
          className: "muted",
          textContent: "No profile record for this section: read only.",
        }),
      );
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
  let frame = 0;
  const draw = () => {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
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
      input: input ? localInput(input, data()) : null,
      rail: local ? { rail_m: local.rail_m, grade_permille: local.grade_permille, step_m: local.grid.step_m } : null,
      server: server ? { rail_m: server.rail_m, step_m: server.step_m } : null,
      profile: target?.profile ?? null,
      selected,
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
    if (frame) {
      cancelAnimationFrame(frame);
      frame = 0;
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

  const resize = ctx.onResize(draw);
  const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(draw) : null;
  ro?.observe(canvasWrap);

  const unsubStore = host.store.subscribe((s, p) => {
    const newSel = s.sel !== p.sel && (sheetAccepts(s.sel) || shownSel === null);
    if (newSel || s.layer !== p.layer || s.year !== p.year || s.month !== p.month || s.tl !== p.tl) void load();
    else if (s.c !== p.c) {
      cursor = s.c;
      if (addButton) addButton.disabled = !data() || cursor === null || view.layer.includes(":");
      draw();
    }
  });
  const unsubDrafts = host.drafts.subscribe((key) => {
    const p = target?.profile;
    if (p && key === host.drafts.key(p.kind, p.id, view)) {
      refreshTable();
      void solve();
    }
  });
  const unsubUnits = host.units.onChange(() => {
    table();
    compare();
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
    }
  });
  const unsubEngine = host.engine.onChange(() => void solve());

  void load();
  return {
    dispose() {
      generation++;
      if (frame) cancelAnimationFrame(frame);
      stopWatch?.();
      resize.dispose();
      ro?.disconnect();
      unsubStore();
      unsubDrafts();
      unsubUnits();
      unsubEvents();
      unsubEngine();
    },
    serialize: () => ({ range, section: shownSection }),
  };
}
