// The paints as the solver reads them (effOvr 837-850, overrideAt 833), the station selections from a saved
// profile (sttFromDoc 852-861), and the type and tube at any chainage once the line is solved (autoType 1605-1610,
// typeAt 1669-1676, tubeKeyAt 1119-1123). P1b.

import type {
  Align,
  Codes,
  LiveStation,
  Lock,
  PortDoc,
  Range3,
  SectionModel,
  SelectedType,
  TubeKey,
  Type,
  TypedModel,
} from "../types.ts";
import { TYPE_CODES } from "../types.ts";
import { cutRange, nearestIndex } from "../util.ts";
import { isRer, railOf, riverAt, stationAt } from "./at.ts";
import { metroTube } from "./phase.ts";
import { pointType, pointTypeOf } from "./point.ts";
import { keyOfTube } from "./tables.ts";

/** The station types Ben can select (STT, 269). */
export const SELECTABLE: ReadonlySet<string> = new Set<SelectedType>(["cutcover", "shield", "deep", "elevated"]);

/**
 * effOvr (837-850): the paints as the solver and the fill read them. On the Metro, inside each platform only the
 * station's selection (a paint across a station paints the running line, never the station:
 * structure.paint.station_paint_running_line_only); a station a lock holds keeps the lock's paint. Sorted by start.
 */
export function effOvr(
  stations: readonly LiveStation[],
  align: Pick<Align, "ovr" | "stt">,
  locks: readonly Lock[],
  platform: number,
  metro: boolean,
): Range3<Type>[] {
  if (!metro) return align.ovr.slice();
  const half = platform / 2;
  let list: Range3<Type>[] = align.ovr.slice();
  stations.forEach((s, i) => {
    if (locks.some((lk) => typeof lk.st[s.name] === "number")) return;
    list = cutRange(list, s.c - half, s.c + half);
    const t = align.stt[i];
    if (t && SELECTABLE.has(t)) list.push([s.c - half, s.c + half, t]);
  });
  return list.sort((a, b) => a[0] - b[0]);
}

/** overrideAt (833): the effective paint at c, the last range winning. */
export function overrideAt(m: Pick<SectionModel, "effOvr">, c: number): Type | null {
  const o = m.effOvr;
  for (let k = o.length - 1; k >= 0; k--) {
    const r = o[k] as Range3<Type>;
    if (c >= r[0] && c <= r[1]) return r[2];
  }
  return null;
}

export interface SttOptions {
  /** false on the RER: no selections (every station '') */
  readonly metro?: boolean;
  /** The page's rule: a saved selection equal to the paint over the station's centre came from the 2 November
   * migration, not from Ben, and is dropped (elevated kept). The hub's import keeps such selections (S62, intended):
   * pass false to read them as Ben's. */
  readonly dropMigrated?: boolean;
}

/**
 * sttFromDoc (852-861): a saved profile's selections by live station, by platform id. A profile with no `stt`
 * (saved before 2 November) gives none: the rules decide.
 */
export function sttFromDoc(
  doc: PortDoc | null,
  stations: readonly LiveStation[],
  ovr: readonly Range3[],
  opts: SttOptions = {},
): (SelectedType | "")[] {
  const { metro = true, dropMigrated = true } = opts;
  if (!metro) return stations.map(() => "");
  const by = doc?.stt && typeof doc.stt === "object" ? doc.stt : null;
  return stations.map((s) => {
    if (!by) return "";
    const v = by[s.platform_id];
    if (!v || !SELECTABLE.has(v)) return "";
    const sel = v as SelectedType;
    if (!dropMigrated) return sel;
    let t: string | null = null;
    for (let k = ovr.length - 1; k >= 0; k--) {
      const r = ovr[k] as Range3;
      if (s.c >= r[0] && s.c <= r[1]) {
        t = r[2];
        break;
      }
    }
    return t === sel && sel !== "elevated" ? "" : sel;
  });
}

/** The solved type of sample i. */
export const solvedType = (m: TypedModel, i: number): Type => TYPE_CODES[m.types.type[i] as number] as Type;

/**
 * autoType (1605-1610): the solve's type at round(c / step) when the rail asked about is within autoTypeRailTol of
 * the solved rail there (geometry.band.engine_is_the_drawing); off the drawn profile, the point on its own.
 */
export function autoType(m: TypedModel, c: number, z: number): Type {
  const T = m.types;
  const i = Math.round(c / T.grid.step);
  if (i >= 0 && i < T.type.length && Math.abs((T.z[i] as number) - z) < m.literals.autoTypeRailTol)
    return solvedType(m, i);
  return pointTypeOf(m, c, pointType(m, c, z));
}

/**
 * typeAt (1669-1676): the type at c for a rail level (the drawn rail by default). On the Metro the engine's answer
 * (paints at stretch level, selections at stations). On the RER the page's paint rules over the open types: a
 * station is one type by the paint at its centre; under a river the sunk box whatever the paint.
 */
export function typeAt(m: TypedModel, c: number, z: number = railOf(m, c)): Type {
  if (!isRer(m) && m.structure) return autoType(m, c, z);
  const st = stationAt(m, c);
  if (st) {
    const o = overrideAt(m, st.c);
    if (o) return o;
    if (overrideAt(m, c)) return autoType(m, st.c, railOf(m, st.c));
  }
  const o = overrideAt(m, c);
  const r = riverAt(m, c);
  if (o && o !== "elevated" && r && !r.bridge && !r.alongShore) return autoType(m, c, z);
  return o || autoType(m, c, z);
}

/** typeAt at every sample on the drawn rail: the drawn band (the golden's grid.type). */
export function typeArray(m: TypedModel): Codes {
  const out = new Uint8Array(m.grid.n);
  for (let i = 0; i < m.grid.n; i++) {
    const t = typeAt(m, m.grid.c[i] as number, m.rail.z[i] as number);
    out[i] = TYPE_CODES.indexOf(t);
  }
  return out;
}

/** tubeKeyAt (1119-1123): the solve's tube at c, else the phase's tube with the painted form; null on the RER. */
export function tubeKeyAt(m: TypedModel, c: number): TubeKey | null {
  if (!m.structure || !m.tables || isRer(m)) return null;
  const T = m.types;
  const i = nearestIndex(T.grid, c);
  const k = T.tube.table[T.tube.codes[i] as number];
  if (k) return k;
  return keyOfTube(m.tables, metroTube(m, c));
}
