// What P4's tests read besides the shared adapter (from_golden.ts), from the golden and the read-only records, as
// the old page had them:
// - the other packages' outputs as data (claude/hub_maps/engine_port_plan.md, section 7.4): the crossings, context
//   blocks and roads of P3, the station flags of station.facts@1 (Access, Platform grade, curve, slide, overlap), the
//   misfits, all from the golden;
// - the saved profile's frame (reframeDoc reads it): each saved station's point, paired with the live stop the page
//   paired it with (the same index and name, 1843-1847), by platform id;
// - the input with the crossings the page linked and the other lines' drawn ground (P2's test input), so P2's
//   rebuildGround gives the page's crossing ground;
// - AlignDeps: P2's buildCanon, rebuildGround, riverModels, sunkBox, applyLocks and P1's sttFromDoc, the real ones.

import { readFileSync } from "node:fs";
import { applyLocks, buildCanon, rebuildGround, riverModels, sunkBox } from "../../../src/port/ground/index.ts";
import { sttFromDoc } from "../../../src/port/structure/index.ts";
import type {
  AlignDeps,
  ContextClearance,
  CrossingClearance,
  PortDoc,
  PortFlag,
  PortInput,
  RoadCheck,
  Sev,
  Structure,
} from "../../../src/port/types.ts";
import type { OldPageDump } from "../../golden/old_page/load.ts";
import { fromGolden, REPO, seedDoc } from "../from_golden.ts";
import { withNeighbours } from "../ground/input.ts";

/** The page's severity as the port's (the page's note is info). */
export const sevOf = (s: string): Sev => (s === "note" ? "info" : s === "warn" ? "warn" : "error");

const readJson = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, REPO), "utf8")) as T;

interface SeedFrame {
  length_m?: number;
  stations?: { name: string; point_c?: number }[];
  del?: string[];
}

/** The saved profile's frame: its length and each saved point by platform id, paired as reframeDoc pairs them. */
export function frameOf(d: OldPageDump): PortDoc["frame"] {
  let s: SeedFrame | null = null;
  try {
    s = readJson<SeedFrame>(`hub/seed/alignments/${d.line}.json`);
  } catch {
    return null;
  }
  if (!s?.stations?.length) return null;
  const del = new Set(s.del ?? []);
  const live = d.stations_file.filter((f) => !del.has(f.key));
  const point_c: Record<string, number> = {};
  s.stations.forEach((x, i) => {
    const st = i < live.length && live[i]?.name === x.name ? live[i] : null;
    if (st && typeof x.point_c === "number") point_c[st.key] = x.point_c;
  });
  return { length_m: typeof s.length_m === "number" ? s.length_m : d.L, point_c };
}

/** The input of one line with its frame, the page's crossings and the other lines' drawn ground. */
export function levelInput(line: string): PortInput {
  const { dump, input } = fromGolden(line);
  const doc = input.doc ? { ...input.doc, frame: frameOf(dump) } : null;
  return withNeighbours({ ...input, doc }, line);
}

/** alignFromDoc's dependencies: P2's and P1's own functions. */
export const ALIGN_DEPS: AlignDeps = {
  sttFromDoc: (doc, stations, ovr) => sttFromDoc(doc, stations, ovr),
  buildCanon,
  rebuildGround,
  riverModels,
  sunkBox,
  applyLocks,
};

type PageStruct = { k: Structure["k"]; below: number; top: number; od?: number; label?: string };
const struct = (s: PageStruct | null | undefined): Structure | null =>
  s ? { k: s.k, below: s.below, top: s.top, ...(s.od != null ? { od: s.od } : {}) } : null;

/** lineReady (2141): the other line's saved profile is marked set. */
export const lineReady = (wid: string): boolean => !!(seedDoc(wid) as { ready?: boolean } | null)?.ready;

/** The golden's crossings as P3's CrossingClearance (pending where the other line is not set). */
export function goldenCrossings(d: OldPageDump): CrossingClearance[] {
  return d.crossings.map((x) => {
    const y = x as Record<string, unknown>;
    return {
      c: x.c,
      wid: x.wid,
      with: String(y.with),
      oc: x.oc,
      zo: x.zo,
      z: Number(y.z),
      clear: (y.clear as number | null) ?? null,
      need: (y.need as number | null) ?? null,
      meUp: !!y.meUp,
      t: struct(y.t as PageStruct) as Structure,
      to: struct(y.to as PageStruct),
      level: !!y.level,
      ok: !!y.ok,
      pending: !lineReady(x.wid),
      source: null,
    };
  });
}

/** The golden's context clearances as P3's ContextClearance. */
export function goldenContext(d: OldPageDump): ContextClearance[] {
  return d.context.map((x) => {
    const y = x as Record<string, unknown>;
    const to = y.to as PageStruct;
    return {
      block: x.block,
      c: x.c,
      zo: Number(y.zo),
      z: Number(y.z),
      clear: Number(y.clear),
      need: Number(y.need),
      meUp: !!y.meUp,
      t: struct(y.t as PageStruct) as Structure,
      to: { k: to.k, below: to.below, top: to.top },
      level: !!y.level,
      short: Number(y.short),
      ok: !!x.ok,
    };
  });
}

/** The kind of a road finding from the page's text (roadChecksNow 2263-2275). */
export function roadKind(text: string): RoadCheck["kind"] {
  if (text.startsWith("level crossing")) return "level_crossing";
  if (text.startsWith("an open trough under")) return "trough_under_road";
  if (/pier/i.test(text) && !/underside/.test(text)) return "pier_in_road";
  return "clearance_over_road";
}

/** The golden's road findings as P3's RoadCheck. */
export function goldenRoads(d: OldPageDump, input: PortInput): RoadCheck[] {
  const roads = input.context.roads;
  return d.roads.map((x) => {
    const r = x.road as unknown as readonly unknown[];
    const k = roads.findIndex((q) => q[0] === r[0] && q[4] === r[4]);
    return { kind: roadKind(x.text), sev: sevOf(x.sev), c: x.c, road: k };
  });
}

const STATION_KIND: Record<string, { kind: string; rule: PortFlag["rule"] }> = {
  Access: { kind: "access", rule: "access.type.shallower_than_d_hall" },
  "Platform grade": { kind: "platform_grade_over", rule: "platform.grade.limit_by_era" },
  "Platform curve": { kind: "platform_curve", rule: "platform.curvature.gapfill" },
  "Platform slide": { kind: "platform_slide_over", rule: "platform.slide.limit_never_clamped" },
  "Platform overlap": { kind: "platform_overlap", rule: "platform.length.by_system" },
};

/** The station flags of station.facts@1 as the page listed them (Access, and the platform checks of designChecks). */
export function goldenStationFlags(d: OldPageDump): PortFlag[] {
  return d.issues
    .filter((x) => x.kind in STATION_KIND)
    .map((x) => {
      const s = STATION_KIND[x.kind] as { kind: string; rule: PortFlag["rule"] };
      return {
        kind: s.kind,
        page: x.kind,
        sev: sevOf(x.sev),
        c0: x.c0,
        c1: x.c1,
        c: x.c,
        rule: s.rule,
        data: { text: x.plain, src: x.src },
      };
    });
}
