// The members the old page derived and wrote into each doc on save (serialize, 3213-3229; R6): per live station its
// name, centre, drawn point, rail, ground and depth (to the centimetre) and type; and the summary of the line (km of
// each type, the steepest grade, the count of grades over the limit). Pure: from the typed model and its summary.

import { CM_PER_M, M_PER_KM, PORT_PERMILLE_TENTHS } from "../../tol.ts";
import { sampleGround } from "../ground/index.ts";
import type { Summary, Type, TypedModel, TypesModule } from "../types.ts";
import { TYPE_CODES } from "../types.ts";

/** One station as serialize() wrote it (3226). */
export interface DerivedStation {
  readonly name: string;
  readonly c: number;
  readonly point_c: number;
  readonly rail: number;
  readonly ground: number;
  readonly depth: number;
  readonly type: Type;
}

/** The doc's derived members (serialize 3226-3227). */
export interface Derived {
  readonly stations: readonly DerivedStation[];
  readonly summary: {
    readonly km_by_type: Readonly<Record<Type, number>>;
    readonly max_grade_permille: number;
    readonly grades_over_limit: number;
  };
}

const cm = (v: number): number => Math.round(v * CM_PER_M) / CM_PER_M;

/** serialize()'s stations and summary of a typed model (see the module doc). */
export function derivedDoc(m: TypedModel, summary: Summary, T: Pick<TypesModule, "typeAt">): Derived {
  const step = m.grid.step;
  const groundAt = (c: number): number => sampleGround(m.ground.finished, step, c);
  const surfaceAt = (c: number): number =>
    m.rivers.some((r) => c >= r.c0 && c <= r.c1) ? m.settings.pool : groundAt(c);
  return {
    stations: m.stations.map((s, i) => {
      const z = m.align.st[i] as number;
      return {
        name: s.name,
        c: s.c,
        point_c: s.point_c,
        rail: z,
        ground: cm(groundAt(s.c)),
        depth: cm(surfaceAt(s.c) - z),
        type: T.typeAt(m, s.c, z),
      };
    }),
    summary: {
      km_by_type: Object.fromEntries(TYPE_CODES.map((t) => [t, Math.round(summary.len[t]) / M_PER_KM])) as Record<
        Type,
        number
      >,
      max_grade_permille: Math.round(summary.maxG * PORT_PERMILLE_TENTHS) / PORT_PERMILLE_TENTHS,
      grades_over_limit: summary.over.filter((o) => o.sev === "error").length,
    },
  };
}
