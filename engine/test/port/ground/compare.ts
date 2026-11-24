// P2's outputs against the old page's goldens, output by output, within the tolerances of section 6 of
// claude/hub_maps/engine_port_plan.md. Each output gives its differences; report.ts classes them.
//
// The P2 model is built by P2 alone from the golden's input (the line file, the seed doc's drawn ground, the context,
// the canon record) and the golden's live stations: the ground layers, canon, sunk box and rivers are P2's own, not
// the golden's. The two outputs that need the types (viaduct spans, made-up bed) run twice: on the old page's own
// type solve (goldenTypes) and on P1's solveTypes run on P2's model, and both must match.

import {
  applyLocks,
  buildCanon,
  canonAt,
  groundModule,
  lockAt,
  madeBedArray,
  normGnd,
  parseGnd,
  rebuildGround,
  refAt,
  riverAtArray,
  riverBridges,
  riverModels,
  sunkBox,
  viaductSpans,
} from "../../../src/port/ground/index.ts";
import { solveTypes, TYPES_MODULE } from "../../../src/port/structure/index.ts";
import type {
  CanonModel,
  GroundLayers,
  PortInput,
  RiverModel,
  SectionModel,
  SunkBox,
  TypedModel,
  TypeSolve,
  TypesModule,
  ViaductSpan,
} from "../../../src/port/types.ts";
import { ground, type OldPageDump, unrle } from "../../golden/old_page/load.ts";
import { fromGolden, goldenTypes, typedFromGolden } from "../from_golden.ts";
import type { Difference, OutputResult } from "../report.ts";
import { withNeighbours } from "./input.ts";

const MAX_LISTED = 20;

/** Per-sample numbers within a tolerance (0 is exact), NaN equal to NaN; the first n samples. */
export function perSampleNum(
  output: string,
  page: ArrayLike<number>,
  port: ArrayLike<number>,
  tol: number,
  n: number = Math.max(page.length, port.length),
): OutputResult {
  const differences: Difference[] = [];
  let count = 0;
  if (page.length < n || port.length < n) differences.push({ at: "length", page: page.length, port: port.length });
  const k = Math.min(n, page.length, port.length);
  for (let i = 0; i < k; i++) {
    const a = page[i] as number;
    const b = port[i] as number;
    const same = Number.isNaN(a) ? Number.isNaN(b) : a === b || Math.abs(a - b) <= tol;
    if (!same) {
      count++;
      if (differences.length < MAX_LISTED) differences.push({ at: `i=${i}`, page: a, port: b });
    }
  }
  if (count > MAX_LISTED) differences.push({ at: `${count - MAX_LISTED} more samples`, page: null, port: null });
  return { output, compared: k, differences };
}

/** Per-sample values, exact. */
export function perSample<T>(output: string, page: readonly T[], port: (i: number) => T, n: number): OutputResult {
  const differences: Difference[] = [];
  let count = 0;
  for (let i = 0; i < n; i++) {
    const p = port(i);
    if (p !== page[i]) {
      count++;
      if (differences.length < MAX_LISTED) differences.push({ at: `i=${i}`, page: page[i], port: p });
    }
  }
  if (count > MAX_LISTED) differences.push({ at: `${count - MAX_LISTED} more samples`, page: null, port: null });
  return { output, compared: n, differences };
}

/** Two values as canonical JSON, exact. */
export function same(output: string, page: unknown, port: unknown): OutputResult {
  const a = JSON.stringify(page);
  const b = JSON.stringify(port);
  return { output, compared: 1, differences: a === b ? [] : [{ at: "value", page: a, port: b }] };
}

/** Pairwise records in the same order: exact fields and numeric fields within a tolerance. */
export function pairs<A, B>(
  output: string,
  page: readonly A[],
  port: readonly B[],
  exact: [string, (x: A) => unknown, (x: B) => unknown][],
  nums: [string, (x: A) => number | null, (x: B) => number | null, number][],
): OutputResult {
  const differences: Difference[] = [];
  if (page.length !== port.length) differences.push({ at: "length", page: page.length, port: port.length });
  const n = Math.min(page.length, port.length);
  for (let k = 0; k < n; k++) {
    for (const [name, fa, fb] of exact) {
      const a = JSON.stringify(fa(page[k] as A));
      const b = JSON.stringify(fb(port[k] as B));
      if (a !== b) differences.push({ at: `${k}.${name}`, page: a, port: b });
    }
    for (const [name, fa, fb, tol] of nums) {
      const a = fa(page[k] as A);
      const b = fb(port[k] as B);
      const ok = a == null || b == null ? a === b : Number.isNaN(a) ? Number.isNaN(b) : Math.abs(a - b) <= tol;
      if (!ok) differences.push({ at: `${k}.${name}`, page: a, port: b });
    }
  }
  return { output, compared: n, differences };
}

/** P2's model of one line: P2's own ground, canon, sunk box and rivers on the golden's input and live stations. */
export interface P2Run {
  dump: OldPageDump;
  input: PortInput;
  /** the golden-fed model (fromGolden) with P2's parts laid in */
  model: SectionModel;
  ground: GroundLayers;
  canon: CanonModel;
  sunk: SunkBox;
  rivers: RiverModel[];
}

/** P2's parts for one line, built in the page's order (alignFromDoc 1875, buildCanon 876, sunkBox, riverBand). */
export function buildP2(line: string): P2Run {
  const g = fromGolden(line);
  const input = withNeighbours(g.input, line);
  const m0 = g.model;
  const ground = rebuildGround(input, m0.align.gnd, input.rivers);
  const canon = buildCanon(input, m0.stations, m0.grid);
  const sunk = sunkBox(input);
  const rivers = riverModels(input, ground, canon, sunk);
  const model: SectionModel = {
    ...m0,
    input,
    ground,
    canon,
    sunk,
    rivers,
    riverAt: riverAtArray(rivers, input.length, input.step),
  };
  return { dump: g.dump, input, model, ground, canon, sunk, rivers };
}

const spanFields: [string, (x: ViaductSpan) => number, (x: ViaductSpan) => number, number][] = [
  ["c0", (s) => s.c0, (s) => s.c0, 0],
  ["c1", (s) => s.c1, (s) => s.c1, 0],
  ["L", (s) => s.L, (s) => s.L, 1e-6],
  ["below", (s) => s.below, (s) => s.below, 1e-6],
  ["above", (s) => s.above, (s) => s.above, 1e-6],
];

function spansResult(output: string, page: readonly ViaductSpan[], port: readonly ViaductSpan[]): OutputResult {
  return pairs(
    output,
    page,
    port,
    [
      ["truss", (s) => s.truss, (s) => s.truss],
      ["ends", (s) => s.ends, (s) => s.ends],
    ],
    spanFields,
  );
}

export interface GroundLineRun {
  results: OutputResult[];
  run: P2Run;
  /** P1's solve on P2's model */
  solve: TypeSolve;
}

/** Every P2 output of one line against its golden. */
export function compareLine(line: string): GroundLineRun {
  const run = buildP2(line);
  const { dump: d, input, model: m, ground: G, canon, rivers } = run;
  const n = m.grid.n;
  const c = (i: number): number => m.grid.c[i] as number;
  const gg = ground(d);
  const results: OutputResult[] = [];

  // the ground layers: dem, regraded, finished exact (Float32); surface, bed 1e-6 m on the grid
  results.push(perSampleNum("ground.dem", gg.dem, G.dem, 0));
  results.push(perSampleNum("ground.regraded", gg.regraded, G.regraded, 0));
  results.push(perSampleNum("ground.finished", gg.finished, G.finished, 0));
  results.push(perSampleNum("ground.surface", gg.surface, G.surface, 1e-6, n));
  results.push(perSampleNum("ground.bed", gg.bed, G.bed, 1e-6, n));
  // the drawn lines: the seed doc's gnd parsed and put on the regraded ground is the golden's align.gnd
  const fromDoc = normGnd(parseGnd(input.doc?.gnd ?? null), G.regraded, input.step);
  results.push(same("ground.lines", d.align.gnd, fromDoc));
  results.push(same("ground.lines.renormalised", d.align.gnd, G.lines));
  // other lines' drawn ground at the crossings
  const gx = d.gnd_cross as {
    c0: number;
    c1: number;
    z: number;
    wid: string;
    with: string;
    street: string | null;
    w: number;
  }[];
  results.push(
    pairs(
      "gnd_cross",
      gx,
      G.cross,
      [
        ["wid", (x) => x.wid, (x) => x.wid],
        ["with", (x) => x.with, (x) => x.with],
        ["street", (x) => x.street, (x) => x.street],
      ],
      [
        ["c0", (x) => x.c0, (x) => x.c0, 1e-3],
        ["c1", (x) => x.c1, (x) => x.c1, 1e-3],
        ["z", (x) => x.z, (x) => x.z, 1e-3],
        ["w", (x) => x.w, (x) => x.w, 0],
      ],
    ),
  );

  // the canon: sections lo, hi 1e-6 m, the rest exact; per sample the section and the lock
  const secs = d.canon.secs as { a: string; b: string; m: string; src: string; lo: number; hi: number }[];
  results.push(
    pairs(
      "canon.secs",
      secs,
      canon.sections,
      [
        ["m", (s) => s.m, (s) => s.m],
        ["a", (s) => s.a, (s) => s.a],
        ["b", (s) => s.b, (s) => s.b],
        ["src", (s) => s.src, (s) => s.src],
      ],
      [
        ["lo", (s) => s.lo, (s) => s.lo, 1e-6],
        ["hi", (s) => s.hi, (s) => s.hi, 1e-6],
      ],
    ),
  );
  results.push(same("canon.fixed", d.canon.fixed, canon.fixed));
  const modes = Object.fromEntries(Object.entries(d.canon.modes).map(([k, v]) => [k, (v as { mode: string }).mode]));
  results.push(same("canon.modes", modes, canon.modes));
  results.push(same("canon.locks", d.canon.locks, canon.locks));
  results.push(same("canon.piers", d.canon.piers, canon.piers));
  results.push(perSample("canon.at", unrle(d.grid.canon), (i) => canonAt(m, c(i))?.m ?? null, n));
  results.push(
    perSample(
      "lock.at",
      unrle(d.grid.lock),
      (i) => {
        const lk = lockAt(m, c(i));
        return lk ? lk.name || `${lk.lo}..${lk.hi}` : null;
      },
      n,
    ),
  );
  results.push(
    perSample(
      "canon.sectionAt",
      unrle(d.grid.canon),
      (i) => {
        const k = canon.sectionAt[i] as number;
        return k >= 0 ? (canon.sections[k]?.m ?? null) : null;
      },
      n,
    ),
  );
  // the golden's align is after applyLocks (changed() 3141): a fixed point
  const al = applyLocks(m.align, canon, m.stations);
  results.push({
    output: "applyLocks.fixed_point",
    compared: 1,
    differences: al.changed ? [{ at: "changed", page: false, port: true }] : [],
  });

  // rivers, the sunk box, the canon bridges
  results.push(
    same(
      "sunk_box",
      { below: d.sunk_box.below, top: d.sunk_box.top, inside: d.sunk_box.inside, spacing: d.sunk_box.spacing },
      run.sunk,
    ),
  );
  type GB = { ub: number; lb: number; low: number; nav: number | null } | null;
  results.push(
    pairs(
      "rivers",
      d.rivers,
      rivers,
      [
        ["name", (r) => r.name, (r) => r.name],
        ["range", (r) => [r.c0, r.c1], (r) => [r.c0, r.c1]],
        ["navigable", (r) => r.navigable, (r) => r.navigable],
        ["along_shore", (r) => r.along_shore, (r) => r.alongShore],
        ["bridge", (r) => r.bridge, (r) => r.bridge],
        ["band", (r) => r.band == null, (r) => r.band == null],
      ],
      [
        ["bed", (r) => r.bed, (r) => r.bed, 1e-3],
        ["band.ub", (r) => (r.band as GB)?.ub ?? null, (r) => r.band?.ub ?? null, 1e-3],
        ["band.lb", (r) => (r.band as GB)?.lb ?? null, (r) => r.band?.lb ?? null, 1e-3],
        ["band.low", (r) => (r.band as GB)?.low ?? null, (r) => r.band?.low ?? null, 1e-3],
        ["band.nav", (r) => (r.band as GB)?.nav ?? null, (r) => r.band?.nav ?? null, 1e-3],
      ],
    ),
  );
  results.push(
    pairs(
      "river_bridges",
      d.river_bridges,
      riverBridges(m),
      [
        ["name", (b) => b.name, (b) => b.name],
        ["range", (b) => [b.c0, b.c1], (b) => [b.c0, b.c1]],
      ],
      [
        ["lb", (b) => b.lb, (b) => b.lb, 1e-3],
        ["ub", (b) => b.ub, (b) => b.ub, 1e-3],
      ],
    ),
  );
  // refAt per station
  results.push(
    pairs(
      "stations.ref",
      d.stations,
      m.stations.map((_, i) => refAt(m, i)),
      [],
      [["ref", (s) => s.ref, (r) => r, 1e-9]],
    ),
  );

  // the two that need the types: on the old page's own solve, and on P1's solve of P2's model
  const gt: TypesModule = goldenTypes(d);
  const goldenSolve = typedFromGolden(line).types;
  const P2g = groundModule(gt);
  const tg: TypedModel = { ...m, types: goldenSolve, spans: [] };
  results.push(spansResult("viaduct_spans", d.viaduct_spans as ViaductSpan[], P2g.viaductSpans(m, goldenSolve)));
  results.push(perSampleNum("made_bed", gg.made_bed, madeBedArray(tg, gt), 1e-6, n));
  const solve = solveTypes(m);
  const tp: TypedModel = { ...m, types: solve, spans: [] };
  results.push(spansResult("viaduct_spans.p1", d.viaduct_spans as ViaductSpan[], viaductSpans(m, solve, TYPES_MODULE)));
  results.push(perSampleNum("made_bed.p1", gg.made_bed, madeBedArray(tp, TYPES_MODULE), 1e-6, n));
  return { results, run, solve };
}
