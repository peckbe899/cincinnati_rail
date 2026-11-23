// The streets and roads of a line (profiles.html 446-462, 2263-2275), from its context (the Deck's live streets, the
// highways and OSM roads; only inside the Deck region): what each station sits under (stationStreet 458) and the
// line against every road it crosses (roadChecksNow 2263). P3 of claude/hub_maps/engine_port_plan.md.

import { PORT_PIER_ROAD_INSET_M, PORT_ROAD_TOL_M, STREET_PAD_M } from "../../tol.ts";
import { openTop } from "../structure/structure.ts";
import type {
  LiveStation,
  RoadCheck,
  SectionModel,
  StationStreet,
  Street,
  TypedModel,
  TypesModule,
  ViaductSpan,
} from "../types.ts";
import { groundOn, railOn } from "./other.ts";

/** A street's name (its fourth member). */
const nameOf = ([, , , name]: Street): string => name;

/** subwayStreet (456): a street built over the subway, its name holding one of the record's subway_streets
 * (road.subway_streets). */
export function subwayStreet(m: Pick<SectionModel, "structure">, name: string): boolean {
  const s = m.structure;
  if (!s) return false;
  const low = String(name).toLowerCase();
  return s.subway_streets.some((k) => low.includes(String(k).toLowerCase()));
}

/** streetAtC (452): the index of the first context street the line runs along at c, 5 m past its ends; -1 for none. */
export function streetAtC(m: Pick<SectionModel, "input">, c: number): number {
  return m.input.context.streets.findIndex((r) => c >= r[0] - STREET_PAD_M && c <= r[1] + STREET_PAD_M);
}

/** roadsIn (453): the indexes of the context roads that cross between c0 and c1 (any part of the road's width). */
export function roadsIn(m: Pick<SectionModel, "input">, c0: number, c1: number): number[] {
  const out: number[] = [];
  m.input.context.roads.forEach((r, i) => {
    if (r[2] >= c0 && r[1] <= c1) out.push(i);
  });
  return out;
}

/** roadClear (454): the clearance over a road of its class (road.clearance.by_class). */
export function roadClear(m: Pick<SectionModel, "settings">, cls: string): number {
  const s = m.settings;
  return cls === "highway" ? s.roadClearHighway : cls === "major" ? s.roadClearMajor : s.roadClearMinor;
}

/**
 * stationStreet (458-462): what a station sits under: its street (marked where built over the subway), else the
 * roads crossing its platform, else nothing; known is false where the context has no streets or roads at all (no
 * streets known here; road.station.street_known).
 */
export function stationStreet(
  m: Pick<SectionModel, "input" | "settings" | "structure">,
  s: LiveStation,
): StationStreet {
  const ctx = m.input.context;
  const street = streetAtC(m, s.c);
  const half = m.settings.platform / 2;
  const st = street >= 0 ? ctx.streets[street] : undefined;
  return {
    street,
    subway: st ? subwayStreet(m, nameOf(st)) : false,
    roads: roadsIn(m, s.c - half, s.c + half),
    known: ctx.streets.length > 0 || ctx.roads.length > 0,
  };
}

/** The viaduct span over c, the first that holds it (spanAt, 992). */
function spanOn(spans: readonly ViaductSpan[], c: number): ViaductSpan | null {
  return spans.find((s) => c >= s.c0 && c <= s.c1) ?? null;
}

/**
 * roadChecksNow (2263-2275): the line against each road it crosses, where the ground is known. At grade: a level
 * crossing, an error on the Metro and on the RER's major roads, a warning on an RER minor street
 * (road.level_crossing). In a trough: the road's bridge needs the open clear height plus its deck from the rail to
 * the street (road.trough_under_road_bridge; the deck is literal.BED_DEPTH, as the registry has it). On a viaduct:
 * the span's soffit (the deck without a span) keeps the class's clearance over the street (road.clearance.by_class).
 * Then each viaduct pier standing in a road, once per road (road.piers_out_of_roads). In chainage order, ties in the
 * order found.
 */
export function roadChecks(m: TypedModel, T: TypesModule, spans: readonly ViaductSpan[] = m.spans): RoadCheck[] {
  const roads = m.input.context.roads;
  const rer = m.input.system === "rer";
  const out: RoadCheck[] = [];
  roads.forEach(([c, , , , , cls], road) => {
    const t = T.typeAt(m, c);
    const z = railOn(m, c);
    const g = groundOn(m, c);
    if (!Number.isFinite(g)) return;
    if (t === "atgrade") {
      out.push({
        kind: "level_crossing",
        sev: rer && cls === "minor" ? "warn" : "error",
        c,
        road,
        rule: "road.level_crossing",
      });
    } else if (t === "trough") {
      const clear = g - z;
      const need = openTop(m) + m.literals.BED_DEPTH;
      if (clear < need - PORT_ROAD_TOL_M)
        out.push({
          kind: "trough_under_road",
          sev: "error",
          c,
          road,
          clear,
          need,
          rule: "road.trough_under_road_bridge",
        });
    } else if (t === "elevated") {
      const sp = spanOn(spans, c);
      const below = sp ? sp.below : m.settings.deckDepth;
      const clear = z - below - g;
      const need = roadClear(m, cls);
      if (clear < need - PORT_ROAD_TOL_M)
        out.push({
          kind: "clearance_over_road",
          sev: "error",
          c,
          road,
          clear,
          need,
          truss: !!sp?.truss,
          rule: "road.clearance.by_class",
        });
    }
  });
  for (const sp of spans)
    for (const pc of [sp.c0, sp.c1]) {
      const road = roads.findIndex((q) => pc > q[1] + PORT_PIER_ROAD_INSET_M && pc < q[2] - PORT_PIER_ROAD_INSET_M);
      if (road >= 0 && !out.some((x) => x.kind === "pier_in_road" && x.road === road))
        out.push({ kind: "pier_in_road", sev: "warn", c: pc, road, rule: "road.piers_out_of_roads" });
    }
  return out.sort((a, b) => a.c - b.c);
}
