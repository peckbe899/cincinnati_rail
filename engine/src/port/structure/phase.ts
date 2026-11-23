// The building phase of a chainage and its rules (phaseAt 1091-1106, phaseRules 1239-1243, methodAt 1245), the
// tube form Ben painted (tubeFormAt 1124) and the phase's bored tube (twinOf 1117, metroTube 1108-1116). P1a.

import type {
  ChrSegment,
  LiveStation,
  Phase,
  PhaseRecord,
  PhaseRules,
  SectionModel,
  Structure,
  TubeForm,
} from "../types.ts";
import { halfPlatform, pieceAt, stationAt } from "./at.ts";
import { tubeOfKey } from "./tables.ts";

type PhaseModel = Pick<SectionModel, "input" | "stations" | "settings" | "chronology" | "structure">;

/**
 * phaseAt (1091-1106). A station is one phase: the earlier-opened of the Chronology segments either side of its
 * platform (1 m past each end) decides it, for the whole platform (station.phase.earlier_segment); else the segment
 * the chainage is in, when it has a phase (era.phase.by_chronology); else the piece's phase, the line's, later.
 * Off the Metro record the page gives null; here "later" (the RER has no phases).
 */
export function phaseAt(m: PhaseModel, c: number): Phase {
  return phaseAtStation(m, c, stationAt(m, c));
}

/** phaseAt with the station whose platform covers c already found (stationAt), or null for none. */
export function phaseAtStation(m: PhaseModel, c: number, st: LiveStation | null): Phase {
  const S = m.structure;
  const sgs = m.chronology;
  const half = halfPlatform(m);
  if (st) {
    const at = (q: number): ChrSegment | undefined => sgs.find((x) => q >= x.c0 && q <= x.c1);
    // [A, B] with a phase, sorted by year (none last, a tie keeps A first), the first
    const A = at(st.c - half - 1);
    const B = at(st.c + half + 1);
    const year = (x: ChrSegment): number => x.year ?? Number.POSITIVE_INFINITY;
    const pick = A?.phase && (!B?.phase || year(A) <= year(B)) ? A : B?.phase ? B : null;
    if (pick?.phase) return pick.phase;
  }
  const sg = sgs.find((s) => c >= s.c0 && c <= s.c1);
  if (sg?.phase) return sg.phase;
  if (!S) return "later";
  const pc = pieceAt(m, c);
  return S.piece_phase[pc] ?? S.line_phase ?? "later";
}

/** The record's phase, later where the record has none of that name (MS.phases[ph] || MS.phases.later). */
export function phaseRecord(m: Pick<SectionModel, "structure">, ph: Phase): PhaseRecord | null {
  const S = m.structure;
  if (!S) return null;
  return S.phases[ph] ?? S.phases.later;
}

/** phaseRules (1239-1243): the deepest cut and cover, the shortest drive, the lift-station depth, the TBM. */
export function phaseRules(m: PhaseModel, c: number, ph: Phase = phaseAt(m, c)): PhaseRules {
  const p = phaseRecord(m, ph);
  return {
    ccMax: p?.cc_max ?? m.settings.shallowMax,
    minDrive: p?.min_drive ?? m.input.literals.minDriveFallback,
    deepFrom: p?.deep_from ?? m.settings.deepBelow,
    tbm: p?.tbm ?? (ph === "3" || ph === "later"),
  };
}

/** methodAt (1245): the TBM's deep bore from Phase 3, the hand shield before (geometry.method.tbm_from_phase_3). */
export function methodAt(m: PhaseModel, c: number, ph?: Phase): "shield" | "deep" {
  return phaseRules(m, c, ph).tbm ? "deep" : "shield";
}

/** tubeFormAt (1124): the tube form painted over c, the last range winning. */
export function tubeFormAt(m: Pick<SectionModel, "align">, c: number): TubeForm | null {
  const o = m.align.tf;
  for (let k = o.length - 1; k >= 0; k--) {
    const r = o[k];
    if (r && c >= r[0] && c <= r[1]) return r[2];
  }
  return null;
}

/** twinOf (1117): the twin tubes of a phase whose tube is the bore, type A to Phase 2, type C after. */
export const twinOf = (ph: Phase): "A" | "C" => (ph === "1" || ph === "2" ? "A" : "C");

/**
 * metroTube (1108-1116): the phase's tube at c, the painted form over it (a painted bore; painted twin tubes where
 * the phase's tube is the bore). Off the record: the era's shield structure.
 */
export function metroTube(m: PhaseModel & Pick<SectionModel, "tables" | "align">, c: number): Structure {
  const T = m.tables;
  if (!T) throw new Error("metroTube: the Metro structure record is missing");
  const ph = phaseAt(m, c);
  const t = (phaseRecord(m, ph) as PhaseRecord).tube;
  const f = tubeFormAt(m, c);
  if (f === "bore") return T.bore;
  if (f === "twin" && t === "bore") return tubeOfKey(T, twinOf(ph));
  return tubeOfKey(T, t);
}
