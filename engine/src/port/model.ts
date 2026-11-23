// The integration of the port (claude/hub_maps/engine_port_plan.md, sections 7.5 and 8): one section's whole solve,
// in the build order of the page.
//
//   deriveStations, buildCanon, reframeDoc and alignFromDoc (P4 with P1's sttFromDoc and P2's ground, rivers, sunk
//   box and locks); the rail (the existing vertical design); radii and curve allowance (P4, from the path); the
//   SectionModel; then solveTypes (P1); viaduct spans (P2); the halls on the solved types; made bed (P2); the drawn
//   band and the legal band (P1); misfits (P1); crossings, context, roads, streets (P3); the curve grades, design and
//   ground checks, summary, river checks and every issue (P4); the level solver's answer (P4).
//
// Pure: reads its input and returns new values. Station facts (access, platform grade, curve, slide) stay with
// station.facts@1: allIssues gets no station flags here, so the sheet and the server list those once, from there.

import { design } from "../vertical/design.ts";
import { railGrid } from "../vertical/rail.ts";
import { vertices } from "../vertical/vertices.ts";
import { radii } from "./checks/curve.ts";
import { type Derived, derivedDoc } from "./checks/derived.ts";
import { designChecks } from "./checks/design.ts";
import { allIssues, curveAllowance, curveGradeRanges, drawingFlags, gndChecks } from "./checks/index.ts";
import { computeSummary, riverChecks } from "./checks/summary.ts";
import { contextClearances, crossingClearances, roadChecks, stationStreet } from "./crossings/index.ts";
import {
  applyLocks,
  buildCanon,
  madeBedArray,
  rebuildGround,
  riverModels,
  sunkBox,
  viaductSpans,
} from "./ground/index.ts";
import { stationHalls } from "./halls.ts";
import { alignFromDoc, type DesignSource } from "./levels/doc.ts";
import { defaultAlign } from "./levels/levels.ts";
import {
  effOvr,
  gradeLimitArrays,
  limitLines,
  openTypes,
  paintMisfits,
  solveTypes,
  structArrays,
  sttFromDoc,
  TYPES_MODULE,
} from "./structure/index.ts";
import { applyMS } from "./structure/tables.ts";
import type {
  AlignDeps,
  ChrSegment,
  CurveGradeRange,
  LevelSolution,
  Phase,
  PortInput,
  PortPlatform,
  PortSolved,
  SectionModel,
  Structure,
  Type,
  TypedModel,
  TypesModule,
} from "./types.ts";
import { gridOf } from "./util.ts";

/** alignFromDoc's dependencies: P1's and P2's own functions. */
export const ALIGN_DEPS: AlignDeps = {
  sttFromDoc: (doc, stations, ovr) => sttFromDoc(doc, stations, ovr),
  buildCanon,
  rebuildGround,
  riverModels,
  sunkBox,
  applyLocks,
};

/** What the integration gives besides PortSolved: the drawn band per sample and the curve grade ranges. */
export interface SolvedSection extends PortSolved {
  /** the drawn type per sample (typeAt at the rail, what the band and the outline draw) */
  readonly drawn: readonly Type[];
  /** the structure at the rail per sample (the outline's kind and its offsets from the rail) */
  readonly struct: readonly Structure[];
  readonly curveGrade: readonly CurveGradeRange[];
  readonly model: TypedModel;
  /** alignFromDoc's own findings (reframed, locks kept, levels unset) */
  readonly docFlags: PortSolved["flags"];
  /** the doc's derived members as the page's serialize() wrote them on save (R6) */
  readonly derived: Derived;
  /** whose design was solved, the stations at the level solver's level, and whether the profile was reframed */
  readonly design: { readonly source: DesignSource; readonly defaulted: readonly string[]; readonly reframed: boolean };
}

/** chrSegments (1077): the line's Chronology segments between its stations, from the table. The page built the list
 * once on load and cached it on the station array (S._chr, 1081) before the profile's slides and removals were laid
 * in, so its segments run between every station of the route at its drawn point: the Chronology's own segments,
 * whatever a profile removes or slides. Kept (the goldens' chr_segments). */
export function chronologyOf(input: PortInput): ChrSegment[] {
  const t = input.chronologyTable;
  if (!t) return [...input.chronology];
  const st = [...input.platforms].sort((a, b) => a.point_c - b.point_c || a.order - b.order);
  if (st.length < 2) return [];
  const ofYear = (y: number | null): Phase | null => {
    if (y == null) return null;
    for (const [a, b, p] of t.phase_years) if (y >= a && y <= b) return p as Phase;
    return null;
  };
  const out: ChrSegment[] = [];
  for (let i = 0; i + 1 < st.length; i++) {
    const [x, y] = [(st[i] as PortPlatform).name, (st[i + 1] as PortPlatform).name].sort();
    const key = t.sys === "metro" ? `metro|${input.route}|${x}|${y}` : `${t.sys}|${x}|${y}`;
    const e = t.segments[key] ?? {};
    const yr = e.year == null || e.year === "" ? null : Number(e.year);
    out.push({
      key,
      c0: i ? (st[i] as PortPlatform).point_c : 0,
      c1: i + 2 < st.length ? (st[i + 1] as PortPlatform).point_c : input.length,
      year: yr,
      phase: (e.phase as Phase | null | undefined) || ofYear(yr),
      set: !!(e.phase || yr != null),
    });
  }
  return out;
}

/** The SectionModel of an input: the profile read onto the live stations, the rail, the ground, canon and rivers. */
export function buildModel(input: PortInput): {
  model: SectionModel;
  docFlags: PortSolved["flags"];
  design: SolvedSection["design"];
} {
  const grid = gridOf(input.length, input.step);
  const read = alignFromDoc(input, ALIGN_DEPS);
  const { align, stations } = read;
  const S = input.settings;
  const verts = vertices({
    length: input.length,
    platform: S.platform,
    vcRadius: S.vcRadius,
    vcMinLen: S.vcMinLen,
    stations: stations.map((s, i) => {
      const z = align.st[i] as number;
      return { c: s.c, z: Number.isFinite(z) ? z : null, gradePermille: align.sg[i] ?? 0, order: i };
    }),
    pvi: align.pvi,
  });
  const dsg = design(verts);
  const rg = railGrid(dsg, input.length, input.step);
  const R = radii(input.path, input.length, input.literals);
  const metro = input.system !== "rer";
  const riverAt = new Int16Array(grid.n);
  for (let i = 0; i < grid.n; i++) {
    const c = grid.c[i] as number;
    riverAt[i] = read.rivers.findIndex((r) => c >= r.c0 && c <= r.c1);
  }
  const model: SectionModel = {
    input,
    grid,
    settings: S,
    literals: input.literals,
    structure: input.structure,
    stations,
    align,
    rail: { design: dsg, z: rg.rail, grade: rg.grade },
    ground: read.ground,
    rivers: read.rivers,
    riverAt,
    canon: read.canon,
    sunk: ALIGN_DEPS.sunkBox(input),
    effOvr: effOvr(stations, align, read.canon.locks, S.platform, metro),
    chronology: chronologyOf(input),
    tables: input.structure ? applyMS(input.structure, input.literals.openClear) : null,
    curve: { step: input.literals.radii.step, radii: R, allowance: curveAllowance(R, S) },
    halls: [],
  };
  return {
    model,
    docFlags: read.flags,
    design: { source: read.design, defaulted: read.defaulted, reframed: read.reframed },
  };
}

/** One section's whole solve (section.solve@1), on P1's TYPES_MODULE unless a stand-in is given. */
export function solveSection(input: PortInput, T: TypesModule = TYPES_MODULE): SolvedSection {
  const { model, docFlags, design: whose } = buildModel(input);
  const metro = input.system !== "rer";
  const types = metro ? solveTypes(model) : openTypes(model);
  let m: TypedModel = { ...model, types, spans: [] };
  m = { ...m, spans: viaductSpans(m, types, T) };
  m = { ...m, halls: stationHalls(m, T) };
  const madeBed = madeBedArray(m, T);
  const band = structArrays(m);
  const limits = limitLines(m, band.type);
  const gradeLimit = gradeLimitArrays(m);
  const misfits = paintMisfits(m);
  const crossings = crossingClearances(m, T);
  const context = contextClearances(m, T);
  const roads = roadChecks(m, T);
  const streets = m.stations.map((s) => stationStreet(m, s));
  const drawing = metro ? drawingFlags(input.path, input.pieces, input.literals) : [];
  const ground = gndChecks(m);
  const curveGrade = curveGradeRanges(m, T);
  const design = designChecks(m, T);
  const summary = computeSummary(m, T);
  const rivers = riverChecks(m, T);
  const flags = allIssues(
    {
      over: summary.over,
      crossings,
      context,
      rivers,
      roads,
      stations: [],
      deepShallow: summary.deepShallow,
      checks: [...design.flags, ...drawing],
      ground,
      types,
      misfits,
    },
    { half: m.settings.platform / 2 },
  );
  const lv: LevelSolution = defaultAlign(m, null, [], m.align.stt);
  return {
    grid: m.grid,
    align: m.align,
    stations: m.stations,
    rail: m.rail,
    ground: m.ground,
    types,
    structBelow: band.structBelow,
    structTop: band.structTop,
    limitTube: limits.limitTube,
    limitBox: limits.limitBox,
    madeBed,
    gradeLimit,
    radii: m.curve.radii,
    allowance: m.curve.allowance,
    rivers: m.rivers,
    canon: m.canon,
    spans: m.spans,
    misfits,
    crossings,
    context,
    roads,
    streets,
    summary: { ...summary, sumps: design.sumps },
    flags: [...docFlags, ...flags],
    levels: lv,
    drawn: band.type,
    struct: band.struct,
    curveGrade,
    model: m,
    docFlags,
    design: whose,
    derived: derivedDoc(m, summary, T),
  };
}
