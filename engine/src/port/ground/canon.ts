// P2 canon (claude/hub_maps/engine_port_plan.md, section 5.2): a route's canon record placed on its live stations, as
// the old Rail Profiles page does on every edit (data/profile/profiles.html 864-930, 1041; buildCanon is called from
// alignFromDoc and changed(), so a draft's canon is always its own live stations': bug A of the parity prove). Method
// sections by their end stations, fixed station levels (network.canon.fixed_levels), RER station modes, locked
// stretches and the Metro's fixed bridge decks (network.canon.locks), and applyLocks, which puts a locked stretch
// back as canon has it and says so with a flag, never silently.

import type { PathPoint } from "../../geom/path.ts";
import { gridChainage } from "../../grid.ts";
import {
  DEG_HALF_TURN,
  M_PER_DEG_LAT,
  M_PER_DEG_LON,
  PORT_CHAINLL_L2_MIN,
  PORT_CHAINLL_TOL_M,
  PORT_DECK_PVI_PER_M,
  PORT_LOCK_PAD_M,
} from "../../tol.ts";
import type {
  Align,
  CanonModel,
  CanonSection,
  FixedLevel,
  Grid,
  LiveStation,
  Lock,
  PortFlag,
  PortInput,
  Range3,
  SectionModel,
  Type,
} from "../types.ts";
import { cutRange } from "../util.ts";
import { riverIndex, sampleGround } from "./layers.ts";

/**
 * The chainage of a lon/lat on a path of [c, lon, lat] (its nearest point, on a flat earth about the path's first
 * point), or null more than tol m off it (chainLL, 866-875).
 */
export function chainLL(
  path: readonly PathPoint[],
  lon: number,
  lat: number,
  tol: number = PORT_CHAINLL_TOL_M,
): number | null {
  const P = path;
  if (!P || P.length < 2) return null;
  const kx = M_PER_DEG_LON * Math.cos(((P[0] as PathPoint)[2] * Math.PI) / DEG_HALF_TURN);
  const ky = M_PER_DEG_LAT;
  let best: [number, number] | null = null;
  for (let i = 1; i < P.length; i++) {
    const p = P[i - 1] as PathPoint;
    const q = P[i] as PathPoint;
    const ax = (p[1] - lon) * kx;
    const ay = (p[2] - lat) * ky;
    const bx = (q[1] - lon) * kx;
    const by = (q[2] - lat) * ky;
    const dx = bx - ax;
    const dy = by - ay;
    const L2 = dx * dx + dy * dy || PORT_CHAINLL_L2_MIN;
    const t = Math.max(0, Math.min(1, -(ax * dx + ay * dy) / L2));
    const d = Math.hypot(ax + dx * t, ay + dy * t);
    if (!best || d < best[0]) best = [d, p[0] + (q[0] - p[0]) * t];
  }
  return best && best[0] <= tol ? best[1] : null;
}

/** The canon section at c, later sections winning (canonAt, 1041). */
export function canonAt(m: Pick<SectionModel, "canon">, c: number): CanonSection | null {
  const a = m.canon.sections;
  for (let k = a.length - 1; k >= 0; k--) {
    const s = a[k] as CanonSection;
    if (c >= s.lo && c <= s.hi) return s;
  }
  return null;
}

/** The first locked stretch at c, PORT_LOCK_PAD_M past its ends (lockAt, 911). */
export function lockAt(m: Pick<SectionModel, "canon">, c: number): Lock | null {
  return m.canon.locks.find((lk) => c >= lk.lo - PORT_LOCK_PAD_M && c <= lk.hi + PORT_LOCK_PAD_M) ?? null;
}

const lockIndex = (locks: readonly Lock[], c: number): number =>
  locks.findIndex((lk) => c >= lk.lo - PORT_LOCK_PAD_M && c <= lk.hi + PORT_LOCK_PAD_M);

const sectionIndex = (secs: readonly CanonSection[], c: number): number => {
  for (let k = secs.length - 1; k >= 0; k--) {
    const s = secs[k] as CanonSection;
    if (c >= s.lo && c <= s.hi) return k;
  }
  return -1;
};

/**
 * The route's canon on its live stations (buildCanon, 876-908). A section is placed from the first live station of
 * each of its end names, half a platform past each (or short of an end left out of it), and dropped while either is
 * removed; fixed levels and modes are keyed by live station index; each locked stretch reaches from c0 to c1; on the
 * Metro, a fixed bridge deck is a locked stretch from its first pier to its last, its bend points to the 0.1 m and
 * Elevated, only where every pier is within DECK_ON of the path (896-905). The RER deck of groundFor (940-951) is not
 * in the canon record yet (slice 2).
 */
export function buildCanon(
  input: Pick<PortInput, "canon" | "settings" | "path" | "system" | "literals">,
  stations: readonly LiveStation[],
  grid: Grid,
): CanonModel {
  const cn = input.canon;
  const half = input.settings.platform / 2;
  const idx = (name: string): number => stations.findIndex((s) => s.name === name);
  const sections: CanonSection[] = [];
  for (const sec of cn.sections) {
    const ia = idx(sec.a);
    const ib = idx(sec.b);
    if (ia < 0 || ib < 0) continue;
    const A = stations[ia] as LiveStation;
    const B = stations[ib] as LiveStation;
    const dir = Math.sign(B.c - A.c) || 1;
    const ca = A.c + (sec.aIn === false ? dir * half : -dir * half);
    const cb = B.c + (sec.bIn === false ? -dir * half : dir * half);
    sections.push({ m: sec.m, lo: Math.min(ca, cb), hi: Math.max(ca, cb), a: sec.a, b: sec.b, src: sec.src });
  }
  const fixed: Record<number, FixedLevel> = {};
  for (const [name, f] of Object.entries(cn.fixed)) {
    const i = idx(name);
    if (i >= 0) fixed[i] = f;
  }
  const modes: Record<number, "under" | "surface"> = {};
  for (const [name, f] of Object.entries(cn.modes)) {
    const i = idx(name);
    if (i >= 0) modes[i] = f.mode;
  }
  const locks: Lock[] = cn.locked.map((lk) => ({ ...lk, lo: +lk.c0, hi: +lk.c1 }));
  const piers: number[] = [];
  if (input.system !== "rer")
    for (const dk of cn.decks) {
      const on = dk.piers.map(([lo, la]) => chainLL(input.path, lo, la, input.literals.DECK_ON));
      if (on.length < 2 || on.some((c) => c == null)) continue;
      const ps = (on as number[]).sort((a, b) => a - b);
      const pvi: [number, number][] = [];
      for (const [lo, la, z] of dk.pvi) {
        const c = chainLL(input.path, lo, la, input.literals.DECK_ON);
        if (c != null) pvi.push([Math.round(c * PORT_DECK_PVI_PER_M) / PORT_DECK_PVI_PER_M, z]);
      }
      const lo = ps[0] as number;
      const hi = ps[ps.length - 1] as number;
      locks.push({ c0: lo, c1: hi, lo, hi, pvi, ovr: [[lo, hi, "elevated"]], st: {}, src: dk.src, name: dk.name });
      piers.push(...ps);
    }
  const sectionAt = new Int16Array(grid.n);
  const lockAtArr = new Int16Array(grid.n);
  for (let i = 0; i < grid.n; i++) {
    const c = gridChainage(i, grid.step, grid.length);
    sectionAt[i] = sectionIndex(sections, c);
    lockAtArr[i] = lockIndex(locks, c);
  }
  return { sections, fixed, modes, locks, piers, sectionAt, lockAt: lockAtArr };
}

/** A fixed level: absolute, or an offset from the ground; NaN with neither, as the page (fixedLevel, 909). */
export const fixedLevel = (f: FixedLevel, ground: number): number => (f.abs != null ? f.abs : ground + Number(f.off));

/** A locked stretch that holds a level for live station i (lockedStation, 912). */
export function lockedStation(m: Pick<SectionModel, "canon" | "stations">, i: number): Lock | null {
  const s = m.stations[i];
  if (!s) return null;
  return m.canon.locks.find((lk) => typeof lk.st[s.name] === "number") ?? null;
}

const snapshot = (a: Pick<Align, "pvi" | "st" | "sg" | "ovr" | "so" | "del">): string =>
  JSON.stringify([a.pvi, a.st, a.sg, a.ovr, a.so, a.del]);

/**
 * Every locked stretch put back as canon has it (applyLocks, 915-929): its bend points replace those inside it, its
 * paints replace those over it, and its station levels are set level (grade 0); a slide and a removal stay Ben's.
 * New align; changed when anything had to change, with one flag per lock that changed it (network.canon.locks: the
 * difference is said, never applied silently; the page flashed "Locked stretch: kept as canon").
 */
export function applyLocks(
  align: Align,
  canon: Pick<CanonModel, "locks">,
  stations: readonly LiveStation[],
): { align: Align; changed: boolean; flags: PortFlag[] } {
  const locks = canon.locks;
  if (!locks.length) return { align, changed: false, flags: [] };
  let pvi = align.pvi.slice();
  let ovr: Range3<Type>[] = align.ovr.slice();
  const st = align.st.slice();
  const sg = align.sg.slice();
  const flags: PortFlag[] = [];
  let prev = snapshot(align);
  for (const lk of locks) {
    pvi = pvi
      .filter((p) => p.c < lk.lo || p.c > lk.hi)
      .concat(lk.pvi.map(([c, z]) => ({ c: +c, z: +z })))
      .sort((a, b) => a.c - b.c);
    ovr = cutRange(ovr, lk.lo, lk.hi)
      .concat(lk.ovr.map(([a, b, t]) => [+a, +b, t] as const))
      .sort((a, b) => a[0] - b[0]);
    for (const [name, z] of Object.entries(lk.st)) {
      const i = stations.findIndex((s) => s.name === name);
      if (i < 0) continue;
      st[i] = z;
      sg[i] = 0;
    }
    const now = snapshot({ ...align, pvi, st, sg, ovr });
    if (now !== prev)
      flags.push({
        kind: "lock_kept",
        page: "Locked stretch",
        sev: "info",
        c0: lk.lo,
        c1: lk.hi,
        c: (lk.lo + lk.hi) / 2,
        rule: "network.canon.locks",
        data: { name: lk.name ?? null, src: lk.src },
      });
    prev = now;
  }
  const out: Align = { ...align, pvi, ovr, st, sg };
  const changed = snapshot(out) !== snapshot(align);
  return { align: changed ? out : align, changed, flags };
}

/**
 * The level a station's depth is measured from: its canon reference level (track level at Union Terminal) or the
 * surface at its centre, the pool over a river (refAt, 930; surfaceAt 706).
 */
export function refAt(
  m: Pick<SectionModel, "canon" | "stations" | "rivers" | "settings" | "ground">,
  i: number,
): number {
  const f = m.canon.fixed[i];
  if (f && f.ref != null) return f.ref;
  const s = m.stations[i];
  if (!s) return Number.NaN;
  return riverIndex(m.rivers, s.c) >= 0 ? m.settings.pool : sampleGround(m.ground.finished, m.ground.step, s.c);
}
