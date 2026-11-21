// The vertices of the design line: platform starts and ends, Ben's PVIs and the two section ends
// (the port of vertices, profiles.html 725-746).
//
// Two details differ from the page, as the spec rules (section 7):
// - The page's comparator (line 739) is not antisymmetric. Here vertices sort by (chainage, kind rank, order), with
//   the ranks pe, ps, pvi: a platform end before anything at the same chainage, as the page meant, and the page's
//   insertion order (platforms in station order, then the PVIs in input order) for every other tie.
// - The page keeps the first of two overlapping platforms, so station order is meaning. It travels as `order`;
//   stations are read in that order, ties by their place in the input.

import { OVERLAP_M, PERMILLE } from "../tol.ts";

export type VertexKind = "ps" | "pe" | "pvi" | "end";

/** A vertex of the design line. */
export interface Vertex {
  readonly c: number;
  readonly z: number;
  readonly kind: VertexKind;
  /** The station (its place in station order) for ps and pe, the PVI's input index for pvi, -1 for an end. */
  readonly i: number;
  /** The platform grade as a ratio (rising with chainage) for ps and pe; 0 otherwise. */
  readonly gp: number;
}

/** A platform as the design line reads it. */
export interface PlatformIn {
  /** Platform centre chainage (the stop's point plus its slide). */
  readonly c: number;
  /** Rail level at the centre; null leaves the platform out (it has no level yet). */
  readonly z: number | null;
  /** Platform grade in per mille; null is level. */
  readonly gradePermille: number | null;
  /** Station order along the section; of two overlapping platforms the first in order wins. */
  readonly order: number;
}

export interface PviIn {
  readonly c: number;
  readonly z: number;
}

export interface VerticesIn {
  readonly length: number;
  readonly platform: number;
  readonly vcRadius: number;
  readonly vcMinLen: number;
  readonly stations: readonly PlatformIn[];
  readonly pvi: readonly PviIn[];
}

/** The vertices with the curve settings design() reads, and what was left out. */
export interface Vertices {
  readonly v: readonly Vertex[];
  /** Vertical curve radius; 0 builds no curves. */
  readonly rv: number;
  /** Shortest vertical curve; 0 when rv is 0, as on the page. */
  readonly lmin: number;
  /** Stations (input index) left out because their platform overlaps an earlier one in order. */
  readonly overlapped: readonly number[];
  /** Stations (input index) left out because they have no level. */
  readonly unset: readonly number[];
}

const RANK: Record<VertexKind, number> = { pe: 0, ps: 1, pvi: 2, end: 2 };

const clamp = (v: number, a: number, b: number): number => Math.max(a, Math.min(b, v));

/** The input index of each station in station order (ties keep input order). */
export function stationOrder(stations: readonly PlatformIn[]): number[] {
  return stations
    .map((s, k) => [s.order, k] as const)
    .sort((a, b) => a[0] - b[0] || a[1] - b[1])
    .map(([, k]) => k);
}

export function vertices(input: VerticesIn): Vertices {
  const { length: L, platform, vcRadius: rv } = input;
  const half = platform / 2;
  const tagged: { v: Vertex; seq: number }[] = [];
  const placed: [number, number][] = [];
  const overlapped: number[] = [];
  const unset: number[] = [];
  const push = (v: Vertex): void => {
    tagged.push({ v, seq: tagged.length });
  };
  for (const k of stationOrder(input.stations)) {
    const s = input.stations[k] as PlatformIn;
    if (s.z === null) {
      unset.push(k);
      continue;
    }
    // platform grade (per mille, rising with chainage) about the level at the platform centre
    const z = s.z;
    const gp = (s.gradePermille || 0) / PERMILLE;
    const ca = clamp(s.c - half, 0, L);
    const cb = clamp(s.c + half, 0, L);
    // the same platform listed twice (overlapping): one platform, the first entry's level
    if (placed.some(([a, b]) => ca < b - OVERLAP_M && cb > a + OVERLAP_M)) {
      overlapped.push(k);
      continue;
    }
    placed.push([ca, cb]);
    push({ c: ca, z: z + gp * (ca - s.c), kind: "ps", i: k, gp });
    push({ c: cb, z: z + gp * (cb - s.c), kind: "pe", i: k, gp });
  }
  input.pvi.forEach((p, j) => {
    push({ c: p.c, z: p.z, kind: "pvi", i: j, gp: 0 });
  });
  tagged.sort((a, b) => a.v.c - b.v.c || RANK[a.v.kind] - RANK[b.v.kind] || a.seq - b.seq);
  const v = tagged.map((t) => t.v);
  const lmin = rv ? input.vcMinLen : 0;
  if (!v.length) {
    const ends: Vertex[] = [
      { c: 0, z: 0, kind: "end", i: -1, gp: 0 },
      { c: L, z: 0, kind: "end", i: -1, gp: 0 },
    ];
    return { v: ends, rv: 0, lmin, overlapped, unset };
  }
  const first = v[0] as Vertex;
  if (first.c > 0) v.unshift({ c: 0, z: first.z, kind: "end", i: -1, gp: 0 });
  const last = v[v.length - 1] as Vertex;
  if (last.c < L) v.push({ c: L, z: last.z, kind: "end", i: -1, gp: 0 });
  return { v, rv: rv || 0, lmin, overlapped, unset };
}
