// The design checks of a line (designChecks 2081-2135): vertical curves too short for their bend, flat tunnel grades
// and the sumps at low points, the curve grade, and the cover over every tunnel structure every 10 m. The platform
// grade, curve, slide and overlap checks of the same function are station.facts@1's (not again here), and the
// drawing checks are drawing.ts (the page ran them from here on the Metro).

import type { RuleId } from "../../rules.gen.ts";
import { PORT_CHECK_FIRST_M, PORT_CHECK_JOIN_M, PORT_CHECK_STEP_M, PORT_COVER_TOL_M } from "../../tol.ts";
import type { HallSpan, PortFlag, SectionModel, Structure, TypedModel, TypesModule } from "../types.ts";
import { canonAt, groundAt, isRer, railOf, riverAt, stationAt } from "./at.ts";
import { chordsOf, sumpsOf, TUNNEL } from "./chords.ts";
import { curveGradeFlag, curveGradeRanges } from "./curve.ts";

/** The hall over a box at c, of the station whose platform covers c (hallAt 536; Metro only). */
export function hallAt(
  m: Pick<SectionModel, "input" | "structure" | "stations" | "settings" | "halls">,
  c: number,
): HallSpan | null {
  if (isRer(m) || !m.structure) return null;
  const s = stationAt(m, c);
  if (!s) return null;
  return m.halls.find((h) => h.station === s.index && c >= h.c0 && c <= h.c1) ?? null;
}

/** The rules the design checks cite. */
export const DESIGN_RULES = [
  "era.vertical_curve.radius_and_min_length",
  "era.drainage.warning_only",
  "river.covered_way.flat_ok",
  "structure.cover.one_diameter_over_tubes",
  "structure.box.thin_cover_warning",
  "clearance.hall.checks_over_hall_roof",
  "road.subway_streets",
] as const satisfies readonly RuleId[];

interface CoverRun {
  c0: number;
  c1: number;
  worst: number;
  need: number;
  cv: number;
  k: Structure["k"];
  tube: Structure["tube"] | null;
  hall: boolean;
}

/**
 * designChecks (2081-2135) less the station checks: the findings in the page's order (vertical curve, drainage,
 * curve grade, cover, box roof above ground, thin cover) and the count of sumps (a falling grade then a rising one
 * in tunnel).
 */
export function designChecks(m: TypedModel, T: TypesModule): { flags: PortFlag[]; sumps: number } {
  const flags: PortFlag[] = [];
  const S = m.settings;
  const seg = chordsOf(m);
  // vertical curves the straight grades are too short for (shortened curves)
  for (const x of m.rail.design.short)
    flags.push({
      kind: "vertical_curve_short",
      page: "Vertical curve",
      sev: "error",
      c0: x.c,
      c1: x.c,
      c: x.c,
      rule: "era.vertical_curve.radius_and_min_length",
      data: { dg: x.dgPermille, need: x.need, got: x.got, radius: S.vcRadius },
    });
  // drainage: tunnel grades flatter than drainMin outside platforms (a warning only); low points need sumps
  for (const sg of seg) {
    const mid = (sg.a.c + sg.b.c) / 2;
    const t = T.typeAt(m, mid);
    const len = sg.b.c - sg.a.c;
    const cw = canonAt(m, mid); // the C trunk covered way drains beneath into the sewers
    if (
      !sg.plat &&
      TUNNEL.has(t) &&
      !(cw && cw.m === "covered") &&
      Math.abs(sg.g) < S.drainMin &&
      len > m.literals.drainageMinLen
    )
      flags.push({
        kind: "drainage_flat",
        page: "Drainage",
        sev: "warn",
        c0: sg.a.c,
        c1: sg.b.c,
        c: mid,
        rule: "era.drainage.warning_only",
        data: { g: sg.g, len, min: S.drainMin },
      });
  }
  const sumps = sumpsOf(m, T);
  // cover, sampled every 10 m: a tube one diameter, a box its roof under the ground (thin cover a warning)
  const runs = { cover: [] as CoverRun[], roof: [] as CoverRun[], thin: [] as CoverRun[] };
  const on: Record<keyof typeof runs, CoverRun | null> = { cover: null, roof: null, thin: null };
  for (let c = PORT_CHECK_FIRST_M; c < m.grid.length; c += PORT_CHECK_STEP_M) {
    if (riverAt(m, c)) continue;
    const z = railOf(m, c);
    const t = T.typeAt(m, c, z);
    const gr = groundAt(m, c);
    if (!Number.isFinite(gr) || !TUNNEL.has(t)) continue;
    const sc0 = T.structFor(m, t, c);
    const ha = sc0.k === "box" ? hallAt(m, c) : null;
    const sc: Structure = ha ? { ...sc0, top: ha.top - z } : sc0;
    const top = z + sc.top;
    const cv = gr - top;
    const need = T.reqCover(m, sc);
    const which: keyof typeof runs | null =
      sc.k === "box"
        ? cv < -PORT_COVER_TOL_M
          ? "roof"
          : !isRer(m) && cv < need - PORT_COVER_TOL_M
            ? "thin"
            : null
        : cv < need - PORT_COVER_TOL_M
          ? "cover"
          : null;
    if (!which) continue;
    const val = cv - need;
    let r = on[which];
    if (r && c - r.c1 <= PORT_CHECK_JOIN_M) {
      r.c1 = c;
      if (val < r.worst) r.worst = val;
    } else {
      r = { c0: c, c1: c, worst: val, need: 0, cv: Number.POSITIVE_INFINITY, k: sc.k, tube: null, hall: false };
      on[which] = r;
      runs[which].push(r);
    }
    r.k = sc.k;
    r.tube = sc.tube ?? null;
    r.hall = !!ha;
    r.need = Math.max(r.need, need);
    r.cv = Math.min(r.cv, cv);
  }
  for (const r of curveGradeRanges(m, T)) flags.push(curveGradeFlag(r));
  const coverFlag = (r: CoverRun, kind: string, sev: PortFlag["sev"], page: string, rule: RuleId): PortFlag => ({
    kind,
    page,
    sev,
    c0: r.c0,
    c1: r.c1,
    c: (r.c0 + r.c1) / 2,
    rule: r.hall ? "clearance.hall.checks_over_hall_roof" : rule,
    data: { k: r.k, tube: r.tube, hall: r.hall, cv: r.cv, need: r.need, worst: r.worst },
  });
  for (const r of runs.cover)
    flags.push(coverFlag(r, "tube_cover_short", "error", "Cover", "structure.cover.one_diameter_over_tubes"));
  for (const r of runs.roof)
    flags.push(coverFlag(r, "box_roof_above_ground", "error", "Cover", "structure.box.thin_cover_warning"));
  for (const r of runs.thin)
    flags.push(coverFlag(r, "box_roof_forms_street", "warn", "Thin cover", "structure.box.thin_cover_warning"));
  return { flags, sumps };
}
