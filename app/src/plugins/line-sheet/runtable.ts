// The run-time table (I2.1, claude/hub_maps/i21_plan.md 4.3): a card in the line panel with railsim's station table
// per direction (Station, km, Run, Dwell, Arrive, Depart, Scheduled, Vmax), the removed stations in grey with no
// times, the direction's totals, the round trip, "where the time goes" (folded: the legs' phases from the run, the
// restrictions' cost from railsim.attribution, asked only while it is open), the sources in plain words and the
// warnings. With a draft the times are the draft's, with a Change column against the saved run. Built from the runs;
// every action calls back into the sheet.

import type { Units } from "../../core/units.ts";
import { formatChange, formatDuration, formatSpeed, speedLabel } from "../../core/units.ts";
import { type Attribution, directionOf, type Run, type RunDirection, type RunDirs, type StationRow } from "./runs.ts";

export interface RunTableCtx {
  units: Units;
  /** "Line 6" */
  line: string;
  saved: Run | null;
  draft: Run | null;
  updating: boolean;
  error: string | null;
  note: string | null;
  removed: { c: number; name: string }[];
  dirs: RunDirs;
  /** Below 1000 px: one direction at a time (the band's toggle picks it). */
  narrow: boolean;
  attribution: Attribution | null;
  attributionOpen: boolean;
  act: {
    /** A row clicked: the sheet moves to the station. */
    select(platformId: string | null, c: number | null): void;
    /** A row hovered (its leg lit on the band), or left (null). */
    hover(dir: 1 | -1, k: number | null): void;
    dirs(d: RunDirs): void;
    attribution(open: boolean): void;
    exportCsv(): void;
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

/** What is folded, kept across rebuilds for the session. */
const open = new Map<string, boolean>([
  ["runs", true],
  ["where", false],
]);

const sec = (s: number | null | undefined) => (s == null || !Number.isFinite(s) ? "–" : String(Math.round(s)));
const kwh = (x: number) => `${Math.round(x)} kWh`;

/** The removed stations among a direction's rows, in the order the train would pass them. */
function rowsOf(
  d: RunDirection,
  removed: RunTableCtx["removed"],
): ({ row: StationRow; k: number } | { gone: string; c: number })[] {
  const out: ({ row: StationRow; k: number } | { gone: string; c: number })[] = d.stations.map((row, k) => ({
    row,
    k,
  }));
  for (const r of removed) {
    const at = (x: (typeof out)[number]) => ("row" in x ? (x.row.c_m ?? 0) : x.c);
    const i = out.findIndex((x) => (d.dir === 1 ? at(x) > r.c : at(x) < r.c));
    const item = { gone: r.name, c: r.c };
    if (i < 0) out.push(item);
    else out.splice(i, 0, item);
  }
  return out;
}

function directionTable(c: RunTableCtx, run: Run, dir: 1 | -1): HTMLElement | null {
  const d = directionOf(run, dir);
  if (!d) return null;
  const u = c.units;
  const base = c.draft && c.saved ? directionOf(c.saved, dir) : null;
  const baseOf = new Map((base?.stations ?? []).map((s) => [s.platform_id ?? s.name, s]));
  const box = el("section", { cls: "rt-dir" });
  box.dataset.dir = String(dir);
  const m = run.meta;
  box.append(
    el("h4", { textContent: `${d.from} to ${d.to}` }),
    el("p", {
      cls: "lp-hint",
      textContent: `${m.train.name}, load ${Math.round(m.train.load_factor * 100)}%, ${Math.round(m.train.mass_t)} t, ${m.train.rail_condition} rail; ${m.era?.name ?? "no era"}${m.year !== null ? ` (${m.year})` : ""}`,
    }),
  );
  const head = el("tr");
  const cols: [string, string][] = [
    ["station", "Station"],
    ["km", "km"],
    ["run", "Run"],
    ["dwell", "Dwell (s)"],
    ["arrive", "Arrive"],
    ["depart", "Depart"],
    ["sched", "Scheduled"],
    ["vmax", `Vmax (${speedLabel(u)})`],
  ];
  if (base) cols.push(["change", "Change"]);
  for (const [k, t] of cols) {
    const th = el("th", { textContent: t });
    th.dataset.col = k;
    head.append(th);
  }
  const body = el("tbody");
  for (const it of rowsOf(d, c.removed)) {
    const tr = el("tr");
    if ("gone" in it) {
      tr.className = "removed";
      tr.append(el("td", { textContent: it.gone }), el("td", { textContent: "removed", colSpan: cols.length - 1 }));
      body.append(tr);
      continue;
    }
    const s = it.row;
    const td = (k: string, t: string) => {
      const x = el("td", { textContent: t });
      x.dataset.col = k;
      tr.append(x);
    };
    td("station", s.name);
    td("km", s.km.toFixed(2));
    td("run", s.leg ? formatDuration(s.leg.run_s) : "");
    td("dwell", it.k === 0 || it.k === d.stations.length - 1 ? "" : sec(s.dwell_s));
    td("arrive", formatDuration(s.arrive_s));
    td("depart", it.k === d.stations.length - 1 ? "" : formatDuration(s.depart_s));
    td("sched", formatDuration(s.scheduled_arrive_s));
    td("vmax", s.leg ? formatSpeed(s.leg.vmax_kmh, u) : "");
    if (base) {
      const b = baseOf.get(s.platform_id ?? s.name);
      td("change", b ? formatChange(s.arrive_s - b.arrive_s) : "new");
    }
    tr.title = "Show this station on the sheet";
    tr.onclick = () => c.act.select(s.platform_id, s.c_m);
    tr.onmouseenter = () => c.act.hover(dir, it.k);
    tr.onmouseleave = () => c.act.hover(dir, null);
    body.append(tr);
  }
  const table = el("table", { cls: "rt-table" }, el("thead", {}, head), body);
  const tot = el("ul", { cls: "rt-totals", testid: "run-totals" });
  const ch = (now: number | null, was: number | null | undefined) =>
    base && now !== null && was != null ? ` (${formatChange(now - was)})` : "";
  const kv = (k: string, v: string) => tot.append(el("li", { textContent: `${k} ${v}` }));
  kv("Running", `${formatDuration(d.running_s)}${ch(d.running_s, base?.running_s)}`);
  kv("Dwell", `${formatDuration(d.dwell_s)}${ch(d.dwell_s, base?.dwell_s)}`);
  kv("Trip", `${formatDuration(d.trip_s)}${ch(d.trip_s, base?.trip_s)}`);
  kv("Scheduled", `${formatDuration(d.scheduled_s)}${ch(d.scheduled_s, base?.scheduled_s)}`);
  kv("Average", `${formatSpeed(d.average_kmh, u, 1)} ${speedLabel(u)}`);
  kv("Top speed", `${formatSpeed(d.max_kmh, u, 1)} ${speedLabel(u)}`);
  kv("Traction", kwh(d.energy_traction_kwh));
  kv("Regenerated", kwh(d.energy_regen_kwh));
  box.append(el("div", { cls: "rt-scroll" }, table), tot);
  return box;
}

function whereTheTimeGoes(c: RunTableCtx, run: Run): HTMLElement {
  const box = el("div", { testid: "run-where" });
  for (const dir of [1, -1] as const) {
    const d = directionOf(run, dir);
    if (!d || (c.dirs === "fwd" && dir === -1) || (c.dirs === "rev" && dir === 1)) continue;
    box.append(el("h4", { textContent: d.label }));
    const legs = el("table", { cls: "rt-table" });
    legs.append(
      el(
        "thead",
        {},
        el(
          "tr",
          {},
          ...["Leg", "Accelerating", "Cruising", "Coasting", "Braking"].map((t) => el("th", { textContent: t })),
        ),
      ),
    );
    const lb = el("tbody");
    d.stations.forEach((s, k) => {
      if (!s.leg) return;
      const prev = d.stations[k - 1]?.name ?? "";
      lb.append(
        el(
          "tr",
          {},
          el("td", { textContent: `${prev} to ${s.name}` }),
          ...[s.leg.accel_s, s.leg.cruise_s, s.leg.coast_s, s.leg.brake_s].map((x) =>
            el("td", { textContent: `${sec(x)} s` }),
          ),
        ),
      );
    });
    legs.append(lb);
    box.append(el("div", { cls: "rt-scroll" }, legs));
    const a = c.attribution?.directions.find((x) => x.dir === dir);
    const cost = el("ol", { cls: "rt-cost", testid: "run-cost" });
    if (a) {
      for (const z of [...a.zones].sort((p, q) => q.lost_s - p.lost_s))
        cost.append(
          el("li", {
            textContent: `${z.reason} (${formatSpeed(z.limit_kmh, c.units)} ${speedLabel(c.units)}): ${sec(z.lost_s)} s`,
          }),
        );
      cost.append(
        el("li", { textContent: `Grades: ${sec(a.grades_s)} s` }),
        el("li", { textContent: `Tunnel drag: ${sec(a.tunnel_drag_s)} s` }),
      );
      box.append(el("p", { cls: "lp-hint", textContent: "What each restriction costs, largest first:" }), cost);
    } else box.append(el("p", { cls: "lp-hint", textContent: "Working out what each restriction costs…" }));
  }
  return box;
}

/** Sources in plain words: "Era 2026: CBTC driverless (GoA3). Train: CMCC Type 2005. Station classes from the Line 6
 * config. Curves fitted to the drawn path. Ground from the line file." */
export function sourcesText(run: Run, line: string): string {
  const m = run.meta;
  const parts: string[] = [];
  if (m.era) parts.push(`Era ${m.year ?? ""}: ${m.era.name ?? "unnamed"}.`.replace("Era :", "Era:"));
  parts.push(`Train: ${m.train.name}.`);
  if (m.sources?.classes) parts.push(`Station classes from the ${line} config.`);
  if (m.sources?.curves) parts.push(`Curves ${m.sources.curves.replace("section path", "drawn path")}.`);
  if (m.sources?.ground) parts.push(`Ground from the ${m.sources.ground}.`);
  return parts.join(" ");
}

/** The turnback at each end in minutes, as railsim's round trip line put it: "0 min turnback at each end", or
 * "turnback 3 min at Towne, 4 min at Beechgrove". */
function turnbackWords(run: Run): string {
  const tb = run.meta.turnback_s ?? [];
  const min = (s: number | undefined) => `${Math.round(((s ?? 0) / 60) * 10) / 10} min`;
  if (min(tb[0]) === min(tb[1])) return `${min(tb[0])} turnback at each end`;
  const d = directionOf(run, 1) ?? run.meta.directions[0];
  return `turnback ${min(tb[0])} at ${d?.from ?? "the start"}, ${min(tb[1])} at ${d?.to ?? "the end"}`;
}

/** The run-time card. Returns the element; the sheet puts it in the line panel. */
export function buildRunTable(c: RunTableCtx): HTMLElement {
  const root = el("div", { cls: "lp rt", testid: "run-table" });
  const run = c.draft ?? c.saved;
  const d = el("details", { cls: "lp-group" });
  d.dataset.group = "runs";
  d.open = open.get("runs") ?? true;
  d.addEventListener("toggle", () => open.set("runs", d.open));
  const title = el("h3", { textContent: "Run times" });
  if (c.draft) title.append(el("span", { cls: "rt-tag", textContent: " draft" }));
  if (c.updating) title.append(el("span", { cls: "rt-tag", textContent: " updating" }));
  d.append(el("summary", {}, title));
  root.append(d);
  if (c.error) d.append(el("p", { cls: "lp-hint rt-error", textContent: c.error }));
  if (c.note) d.append(el("p", { cls: "lp-hint", textContent: c.note }));
  if (!run) {
    d.append(el("p", { cls: "lp-hint", textContent: c.updating ? "Working out the run times…" : "No run yet." }));
    return root;
  }
  // the direction toggle, as on the band
  const bar = el("div", { cls: "lp-buttons", testid: "run-dirs" });
  for (const [k, t] of [
    ["both", "Both"],
    ["fwd", "Forward"],
    ["rev", "Back"],
  ] as const) {
    const b = el("button", { type: "button", textContent: t });
    b.setAttribute("aria-pressed", String(c.dirs === k));
    b.onclick = () => c.act.dirs(k);
    bar.append(b);
  }
  const exp = el("button", { type: "button", textContent: "Export CSV", testid: "run-export" });
  exp.title = "Both directions as railsim's stations_<dir>.csv";
  exp.onclick = () => c.act.exportCsv();
  bar.append(exp);
  d.append(bar);
  const shown: (1 | -1)[] =
    c.dirs === "fwd" ? [1] : c.dirs === "rev" ? [-1] : c.narrow ? [run.meta.directions[0]?.dir ?? 1] : [1, -1];
  for (const dir of shown) {
    const t = directionTable(c, run, dir);
    if (t) d.append(t);
  }
  // a narrow sheet shows one direction with Both pressed: say where the other one is
  const other = c.dirs === "both" && shown.length === 1 ? directionOf(run, shown[0] === 1 ? -1 : 1) : null;
  if (other)
    d.append(
      el("p", {
        cls: "lp-hint",
        testid: "run-other-dir",
        textContent: `${other.label}: press ${other.dir === 1 ? "Forward" : "Back"} above to see its table.`,
      }),
    );
  // the round trip
  const m = run.meta;
  const rt = el("p", {
    cls: "lp-hint",
    testid: "run-round-trip",
    textContent: `Round trip ${formatDuration(m.round_trip_s)} (scheduled both ways plus ${turnbackWords(run)})${m.headway_min ? `; ${m.trains_needed ?? "?"} trains at a ${m.headway_min} min headway` : ""}`,
  });
  d.append(rt);
  // where the time goes
  const w = el("details", { cls: "lp-group" });
  w.dataset.group = "where";
  w.open = c.attributionOpen;
  w.append(el("summary", { textContent: "Where the time goes" }));
  if (w.open) w.append(whereTheTimeGoes(c, run));
  w.addEventListener("toggle", () => {
    open.set("where", w.open);
    c.act.attribution(w.open);
  });
  d.append(w);
  d.append(el("p", { cls: "lp-hint", testid: "run-sources", textContent: sourcesText(run, c.line) }));
  if (m.warnings?.length) {
    const ul = el("ul", { cls: "rt-warnings", testid: "run-warnings" });
    for (const x of m.warnings) ul.append(el("li", { textContent: x }));
    d.append(ul);
  }
  return root;
}

/** Whether "where the time goes" was left open this session. */
export const whereOpen = (): boolean => open.get("where") ?? false;
