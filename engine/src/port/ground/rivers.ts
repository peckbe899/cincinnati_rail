// P2 rivers (claude/hub_maps/engine_port_plan.md, section 5.2): the sunk box, the band its roof keeps under each river,
// the canon bridges and the made-up bed, as the old Rail Profiles page computes them (data/profile/profiles.html
// 992-1036). Every Metro and RER river crossing in tunnel is a sunk double-track box (river.crossing.bridge_or_sunk,
// structure.sunk_box.dimensions_from_record); its roof sits between riverSink below the bed and riverRise above it
// (river.sunk_box.roof_band); over a roof above the bed the bed is made up (river.sunk_box.made_up_bed); a canon
// bridge that is not fixed holds the rail at its navigation clearance (river.bridge.navigation_clearance); an RER
// river range along the covered way is the shore (river.shore_not_crossing).

import { gridChainage } from "../../grid.ts";
import type {
  BridgeRecord,
  CanonModel,
  GroundLayers,
  PortInput,
  RiverModel,
  RiverRecord,
  SectionModel,
  SunkBox,
  TypedModel,
  TypesModule,
} from "../types.ts";
import { canonAt } from "./canon.ts";
import { bedOf, riverIndex, sampleGround } from "./layers.ts";

/**
 * The sunk box (sunkBox, 1007-1012): on the Metro the structure record's box (rail to underside, roof underside,
 * inside, track spacing) with the sunk unit's roof slab (settings.riverRoof) on top; on the RER the envelope box,
 * invertDepth under the rail. The page fell back to fixed numbers without the record; the port has the record on
 * every Metro section and says so when it has not.
 */
export function sunkBox(input: Pick<PortInput, "system" | "structure" | "settings" | "section_id">): SunkBox {
  if (input.system === "rer") {
    const r = input.settings.rer;
    if (!r) throw new Error(`${input.section_id}: an RER section without settings.rer has no sunk box`);
    return { below: r.invertDepth, top: r.envelope, inside: Number.NaN, spacing: Number.NaN };
  }
  const ms = input.structure;
  if (!ms) throw new Error(`${input.section_id}: a Metro section without the structure record has no sunk box`);
  const bx = ms.box;
  return { below: bx.below, top: bx.roof_underside + input.settings.riverRoof, inside: bx.inside, spacing: bx.spacing };
}

/** The canon bridge a Metro river is crossed on (bridgeOf, 948): none on the RER, whose canon has none. */
export function bridgeOf(
  input: Pick<PortInput, "system" | "canon">,
  r: Pick<RiverRecord, "name">,
): BridgeRecord | null {
  if (input.system === "rer") return null;
  return input.canon.bridges[r.name] ?? null;
}

/** An RER river range along the embanked covered way (a canon 'covered' section at its middle) is the shore, not a
 * crossing, unless the river is crossed inside it (alongShore, 1015). */
export function alongShore(
  m: Pick<SectionModel, "canon" | "input">,
  r: Pick<RiverRecord, "c0" | "c1" | "inCoveredWay">,
): boolean {
  if (m.input.system !== "rer") return false;
  const sec = canonAt(m, (r.c0 + r.c1) / 2);
  return !!sec && sec.m === "covered" && !r.inCoveredWay;
}

/** What the river band reads: the input's rivers, the finished ground, the canon, the sunk box and the settings. */
export type RiverContext = Pick<SectionModel, "input" | "settings" | "ground" | "canon" | "sunk">;

/** The river bed at c: the canon bed of the first river there, else the finished ground (bedAt, 710). */
export function bedAt(m: Pick<SectionModel, "input" | "settings" | "ground">, c: number): number {
  const rivers = m.input.rivers;
  const k = riverIndex(rivers, c);
  const b = k >= 0 ? bedOf(rivers[k] as RiverRecord, m.settings.pool) : null;
  return b != null ? b : sampleGround(m.ground.finished, m.ground.step, c);
}

/**
 * The band the sunk box keeps under a river (riverBand, 1017-1031), from its points under water (bed below the
 * pool) every step from c0: the rail at most riverRise over (bed less the box top) at every wet point; at least
 * riverSink under it on the flat bottom (a bed within riverFlatTol of the lowest); on a navigable river, the rail
 * under the clear-water level or the roof and its cap under the lowest bed. null along the shore, or with no point
 * under water: not a crossing.
 */
export function riverBand(m: RiverContext, r: RiverRecord): RiverModel["band"] {
  if (alongShore(m, r)) return null;
  const S = m.settings;
  const pool = S.pool;
  const top = m.sunk.top;
  const step = m.input.step;
  const wet = (b: number): boolean => Number.isFinite(b) && b < pool;
  let low = Number.POSITIVE_INFINITY;
  let ub = Number.POSITIVE_INFINITY;
  let lb = Number.NEGATIVE_INFINITY;
  for (let c = r.c0; c <= r.c1; c += step) {
    const b = bedAt(m, c);
    if (wet(b)) low = Math.min(low, b);
  }
  if (!Number.isFinite(low)) return null;
  for (let c = r.c0; c <= r.c1; c += step) {
    const b = bedAt(m, c);
    if (!wet(b)) continue;
    ub = Math.min(ub, b - top + S.riverRise);
    if (b <= low + S.riverFlatTol) lb = Math.max(lb, b - top - S.riverSink);
  }
  const nav = r.navigable ? pool - S.riverClearWater - S.riverCap - top : null;
  return { ub: nav != null ? Math.min(ub, Math.max(nav, low - top - S.riverCap)) : ub, lb, low, nav };
}

/** A canon bridge that is not fixed: the rail held at its navigation clearance over the pool plus the deck, ub = lb,
 * no higher than it needs (riverBridges, 993-997). */
export function riverBridges(
  m: Pick<SectionModel, "input" | "settings">,
): { name: string; c0: number; c1: number; lb: number; ub: number }[] {
  const out: { name: string; c0: number; c1: number; lb: number; ub: number }[] = [];
  for (const r of m.input.rivers) {
    const b = bridgeOf(m.input, r);
    if (!b || b.fixed) continue;
    const lb = m.settings.pool + Number(b.clear) + m.settings.deckDepth;
    out.push({ name: r.name, c0: r.c0, c1: r.c1, lb, ub: lb });
  }
  return out;
}

/** Each river of the section with its bed, bridge, band and bridge band (the dump's rivers, river_bridges). */
export function riverModels(input: PortInput, ground: GroundLayers, canon: CanonModel, sunk: SunkBox): RiverModel[] {
  const m: RiverContext = { input, settings: input.settings, ground, canon, sunk };
  const bridges = riverBridges(m);
  return input.rivers.map((r) => {
    const bridge = bridgeOf(input, r);
    const bb = bridges.find((b) => b.name === r.name);
    return {
      name: r.name,
      c0: r.c0,
      c1: r.c1,
      bed: bedOf(r, input.settings.pool),
      navigable: r.navigable,
      alongShore: alongShore(m, r),
      bridge,
      band: bridge ? null : riverBand(m, r),
      bridgeBand: bb ? { lb: bb.lb, ub: bb.ub } : null,
    };
  });
}

/**
 * The made-up bed over a sunk box whose roof and cap stand above the bed (madeBedAt, 1032-1036): the rail plus the
 * box top plus riverCap, where the type at c is the sunk box under a river that is not bridged and not the shore;
 * NaN elsewhere. The type is P1's typeAt through T.
 */
export function madeBedAt(m: TypedModel, c: number, z: number, T: Pick<TypesModule, "typeAt">): number {
  const k = riverIndex(m.rivers, c);
  const r = k >= 0 ? (m.rivers[k] as RiverModel) : null;
  if (!r || r.bridge || r.alongShore || T.typeAt(m, c, z) !== "sunk") return Number.NaN;
  const b = r.bed != null ? r.bed : sampleGround(m.ground.finished, m.ground.step, c);
  const t = z + m.sunk.top + m.settings.riverCap;
  return Number.isFinite(b) && t > b ? t : Number.NaN;
}

/** madeBedAt at every grid sample on the drawn rail (PortSolved.madeBed). */
export function madeBedArray(m: TypedModel, T: Pick<TypesModule, "typeAt">): Float64Array {
  const g = m.grid;
  const out = new Float64Array(g.n).fill(Number.NaN);
  for (let i = 0; i < g.n; i++) {
    if (m.riverAt[i] === -1) continue;
    out[i] = madeBedAt(m, gridChainage(i, g.step, g.length), m.rail.z[i] as number, T);
  }
  return out;
}
