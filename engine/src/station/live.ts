// What station.facts@1 works out again from the live stations of the profile it is given (a draft's, while Ben
// edits): the canon's method sections and each station's phase. The old page rebuilt both on every edit
// (changed() → deriveStations → buildCanon, profiles.html 3141; phaseAt 1091 reads the live stations), so removing,
// restoring or sliding a station gave its type at once. Before this the sheet read the saved profile's placing of
// both, and a draft's type disagreed with the old page until the save (bug A of the parity prove).

import type { StationInput } from "../contract/index.ts";

/** A live station: its name (the canon names stations) and its platform centre now. */
export interface LiveStation {
  name: string;
  c: number;
}

export type CanonSection = StationInput["canon"][number];

/**
 * buildCanon (876-885) from the live stations: a section naming its end stations is placed from the first live
 * station of each name (an end with a_in or b_in false left out of it), and dropped while an end is removed; a
 * section without names keeps its chainages.
 */
export function liveCanon(canon: readonly CanonSection[], live: readonly LiveStation[], half: number): CanonSection[] {
  const out: CanonSection[] = [];
  for (const sec of canon) {
    if (sec.a === undefined || sec.b === undefined) {
      out.push(sec);
      continue;
    }
    const A = live.find((x) => x.name === sec.a);
    const B = live.find((x) => x.name === sec.b);
    if (!A || !B) continue;
    const dir = Math.sign(B.c - A.c) || 1;
    const ca = A.c + (sec.a_in === false ? dir * half : -dir * half);
    const cb = B.c + (sec.b_in === false ? -dir * half : dir * half);
    out.push({ ...sec, c0: Math.min(ca, cb), c1: Math.max(ca, cb) });
  }
  return out;
}

type Segment = NonNullable<StationInput["chron_segments"]>[number];

/**
 * phaseAt (1091-1098) at a live station: the earlier-opened of the Chronology segments either side of its
 * platform (1 m beyond each end), else the segment at its centre; null when the segments say nothing, and the
 * platform keeps the phase it was given (its piece's or its line's).
 */
export function livePhase(segments: readonly Segment[] | undefined, c: number, half: number): string | null {
  if (!segments?.length) return null;
  const at = (q: number) => segments.find((x) => q >= x.c0 && q <= x.c1);
  const pick = [at(c - half - 1), at(c + half + 1)]
    .filter((x): x is Segment => !!x?.phase)
    .sort((u, v) => (u.year ?? Number.POSITIVE_INFINITY) - (v.year ?? Number.POSITIVE_INFINITY))[0];
  if (pick?.phase) return pick.phase;
  const sg = at(c);
  return sg?.phase ?? null;
}
