// Paints must make sense (structure.paint.must_fit): where a paint or a station's selection names a structure that
// cannot be built at the drawn rail on the finished ground (fitLim 1624, fitOf 1627-1636, paintMisfits 1637-1665).
// P1b.

import { PORT_CHAINAGE_EPS_M, PORT_LOCK_PAD_M } from "../../tol.ts";
import type { Misfit, SectionModel, Type } from "../types.ts";
import { canonAt, groundAt, halfPlatform, isRer, lockedStation, railOf, riverAt, stationAt } from "./at.ts";
import { overrideAt } from "./lookup.ts";
import { phaseRules } from "./phase.ts";
import { drivenStruct } from "./structure.ts";

/** Which way the fix moves the rail for each reason (FIT_WHY, 1617). */
export const FIT_WHY: Readonly<Record<Misfit["why"], "lower" | "raise">> = {
  roof: "lower",
  above: "lower",
  high: "lower",
  cover: "lower",
  dig: "raise",
  buried: "raise",
};

const fitBoxTop = (m: SectionModel): number => (isRer(m) ? (m.settings.rer?.envelope ?? 0) : (m.tables?.box.top ?? 0)); // 1618
const fitDig = (m: SectionModel, c: number): number => (isRer(m) ? m.settings.shallowMax : phaseRules(m, c).ccMax); // 1619
function fitTube(m: SectionModel, c: number, t: Type): number {
  // 1620
  if (isRer(m)) return (m.settings.rer?.boreCrown ?? 0) + (m.settings.rer?.minCover ?? 0);
  const tb = drivenStruct(m, t, c);
  const h = m.structure?.cost.cover_hard ?? m.literals.coverHardFallback;
  return tb.top + (tb.od ?? 0) * h;
}

/** fitLim (1624): the rail level the fix moves to (Lower: the rail at most this; Raise: at least). */
export function fitLim(m: SectionModel, t: Type, why: Misfit["why"]): (c: number) => number {
  const S = m.settings;
  return (c) => {
    const g = groundAt(m, c);
    if (why === "roof") return g - fitBoxTop(m);
    if (why === "above") return g;
    if (why === "high") return g + S.elevAbove + S.deckDepth;
    if (why === "cover") return g - fitTube(m, c, t);
    if (why === "buried") return g + S.deckDepth;
    return g - (t === "trough" ? fitDig(m, c) : fitBoxTop(m));
  };
}

/** fitOf (1627-1636): how far the rail is from fitting, with its reason; null where it fits. A Metro tube, running
 * or a mined station, is the cover check of the solve (its unbuildable stretches), not a misfit. */
export function fitOf(
  m: SectionModel,
  t: Type,
  c: number,
  z: number,
  _stn: boolean,
): { why: Misfit["why"]; by: number } | null {
  const g = groundAt(m, c);
  if (!Number.isFinite(g)) return null;
  const S = m.settings;
  const tol = m.literals.limitTol;
  const d = g - z;
  const box = fitBoxTop(m);
  let why: Misfit["why"] | null = null;
  if (t === "cutcover") why = d < box - tol ? "roof" : null;
  else if (t === "trough") why = d < -tol ? "above" : d > fitDig(m, c) + tol ? "dig" : null;
  else if (t === "atgrade") why = d > box + tol ? "dig" : -d > S.elevAbove + S.deckDepth + tol ? "high" : null;
  else if (t === "elevated") why = z - S.deckDepth < g - tol ? "buried" : null;
  else if ((t === "shield" || t === "deep") && isRer(m)) why = d < fitTube(m, c, t) - tol ? "cover" : null;
  if (!why) return null;
  const lim = fitLim(m, t, why)(c);
  return { why, by: Math.abs(z - lim) };
}

/** A canon box (canal, covered way), a river crossing or a lock is the canon's: never a misfit (1645). */
function canonHolds(m: SectionModel, c: number): boolean {
  const r = riverAt(m, c);
  const sec = canonAt(m, c);
  return (
    (!!r && !r.alongShore) ||
    (!!sec && (sec.m === "canal" || sec.m === "covered")) ||
    m.canon.locks.some((lk) => c >= lk.lo - PORT_LOCK_PAD_M && c <= lk.hi + PORT_LOCK_PAD_M)
  );
}

/**
 * paintMisfits (1637-1665): running paints sample by sample (a run of one paint and one reason, MIN_RUN or
 * longer), then each station's selection (the RER: the paint at its centre) by its platform centre, the whole
 * platform. Sorted by start.
 */
export function paintMisfits(m: SectionModel): Misfit[] {
  const { n, step, length: L } = m.grid;
  const half = halfPlatform(m);
  const minRun = m.literals.MIN_RUN;
  const list: Misfit[] = [];
  type Run = { c0: number; c1: number; t: Type; why: Misfit["why"]; worst: number };
  let run: Run | null = null;
  const flush = (): void => {
    if (run && run.c1 - run.c0 + step >= minRun) list.push(run);
    run = null;
  };
  for (let i = 0; i < n; i++) {
    const c = Math.min(i * step, L);
    const o = stationAt(m, c) || canonHolds(m, c) ? null : overrideAt(m, c);
    const f = o ? fitOf(m, o, c, m.rail.z[i] as number, false) : null;
    if (!f || !o) {
      flush();
      continue;
    }
    const r = run as Run | null;
    if (r && r.t === o && r.why === f.why && c - r.c1 <= step + PORT_CHAINAGE_EPS_M) {
      r.c1 = c;
      r.worst = Math.max(r.worst, f.by);
      continue;
    }
    flush();
    run = { c0: c, c1: c, t: o, why: f.why, worst: f.by };
  }
  flush();
  m.stations.forEach((s, i) => {
    if (lockedStation(m, i) || canonHolds(m, s.c)) return;
    const t = isRer(m) ? overrideAt(m, s.c) : m.align.stt[i];
    if (!t) return;
    const f = fitOf(m, t, s.c, railOf(m, s.c), true);
    if (f) list.push({ c0: s.c - half, c1: s.c + half, t, why: f.why, worst: f.by, si: i });
  });
  return list.sort((a, b) => a.c0 - b.c0);
}
