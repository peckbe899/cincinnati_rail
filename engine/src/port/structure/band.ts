// What the sheet draws from the solve per 2 m sample (profiles.html 2462-2484, 2525-2532): the structure at the rail
// (structFor of the type, the outline's roof and floor) and the legal band (geometry.band.engine_is_the_drawing):
// the shallowest a shield tube may run (one diameter of cover) and the deepest a box may go (the phase's
// cut-and-cover limit), where the line is underground and not under a river. P1b.

import type { Structure, Type, TypedModel } from "../types.ts";
import { groundAt, riverAt } from "./at.ts";
import { typeAt } from "./lookup.ts";
import { phaseRules } from "./phase.ts";
import { drivenStruct } from "./structure.ts";

const UND = new Set<Type>(["shield", "deep", "cutcover"]);

/** The drawn type and its structure at every sample (the golden's grid.type and grid.struct). */
export function structArrays(m: TypedModel): {
  type: Type[];
  struct: Structure[];
  structBelow: Float32Array;
  structTop: Float32Array;
} {
  const { n } = m.grid;
  const type: Type[] = new Array<Type>(n);
  const struct: Structure[] = new Array<Structure>(n);
  const structBelow = new Float32Array(n);
  const structTop = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const c = m.grid.c[i] as number;
    const z = m.rail.z[i] as number;
    const t = typeAt(m, c, z);
    const sc = drivenStruct(m, t, c);
    type[i] = t;
    struct[i] = sc;
    structBelow[i] = z - sc.below;
    structTop[i] = z + sc.top;
  }
  return { type, struct, structBelow, structTop };
}

/** The legal band's two dashed lines (2525-2532), NaN where the line is open or under a river. */
export function limitLines(
  m: TypedModel,
  types: readonly Type[] = structArrays(m).type,
): { limitTube: Float32Array; limitBox: Float32Array } {
  const { n } = m.grid;
  const limitTube = new Float32Array(n);
  const limitBox = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const c = m.grid.c[i] as number;
    const under = UND.has(types[i] as Type) && !riverAt(m, c);
    if (!under) {
      limitTube[i] = Number.NaN;
      limitBox[i] = Number.NaN;
      continue;
    }
    const g = groundAt(m, c);
    const sh = drivenStruct(m, "shield", c);
    limitTube[i] = g - sh.top - (sh.od ?? 0);
    limitBox[i] = g - phaseRules(m, c).ccMax;
  }
  return { limitTube, limitBox };
}
