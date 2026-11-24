// The halls on the box roofs (stationAccess 503-535, the halls only): what the cover check (designChecks) and the
// crossing check (crossingClearances) read through hallAt (536). The plan has them from station.facts on the solved
// types (claude/hub_maps/engine_port_plan.md, section 8); station.facts@1 reads its own provisional types, so the
// integration works the access type out here on the full solve's types, as the page did (typeAt at the centre).

import { groundAt } from "./structure/at.ts";
import type { HallSpan, PortPlatform, StructureParams, TypedModel, TypesModule } from "./types.ts";

const OPEN = new Set(["atgrade", "trough", "elevated"]);
const HALL_TYPES = new Set(["end_halls", "mezzanine", "mezzanine_full"]);
const ACCESS = new Set([
  "surface",
  "platform_level",
  "platform_level_xu",
  "end_halls",
  "mezzanine",
  "mezzanine_full",
  "mined_hall",
  "deep",
  "elevated_mezzanine",
]);

/** boxTopOf (1199): rail to the box roof top, an island's wider box by its own roof. */
export function boxTopOf(ms: StructureParams, island: boolean): number {
  return island ? ms.island_box.roof_underside + (ms.box.top - ms.box.roof_underside) : ms.box.top;
}

/** The access type of one station on the solved types (stationAccess 504-518): Ben's choice, else the rule's. */
export function accessType(
  m: TypedModel,
  T: Pick<TypesModule, "typeAt" | "phaseAt" | "phaseRules">,
  i: number,
): { type: string; island: boolean; z: number; dHall: number } | null {
  const ms = m.structure;
  const s = m.stations[i];
  if (!ms || !s || m.input.system === "rer") return null;
  const z = m.align.st[i] as number;
  const g = groundAt(m, s.c);
  const d = Number.isFinite(g) ? g - z : Number.NaN;
  const t = T.typeAt(m, s.c, z);
  const plat: PortPlatform | undefined = m.input.platforms.find((p) => p.platform_id === s.platform_id);
  const year = plat?.year ?? s.year;
  const ph = year != null ? (plat?.yearPhase ?? T.phaseAt(m, s.c)) : T.phaseAt(m, s.c);
  const island =
    plat && plat.sideSet === false ? m.types.platDef[s.key] === "island" : (plat?.side ?? s.side) === "island";
  const dHall = boxTopOf(ms, island) + ms.hall.clear + ms.hall.roof + ms.hall.cover;
  const atOpen = !!plat?.interchangeAtOpen;
  let rule: string;
  if (t === "elevated") rule = "elevated_mezzanine";
  else if (OPEN.has(t)) rule = "surface";
  else if (t === "shield" || t === "deep" || t === "sunk")
    rule = d >= T.phaseRules(m, s.c).deepFrom ? "deep" : "mined_hall";
  else if (!Number.isFinite(d)) rule = "platform_level";
  else if (d < dHall) rule = !island && !atOpen ? "platform_level" : "platform_level_xu";
  else if (ph === "1") rule = "end_halls";
  else if (ph === "2") rule = atOpen ? "mezzanine_full" : "mezzanine";
  else rule = "mezzanine_full";
  const ov = m.input.access?.[s.platform_id];
  return { type: ov && ACCESS.has(ov) ? ov : rule, island, z, dHall };
}

/** The halls of every live station (stationAccess 528-531): end halls, a mezzanine, or one the platform's length. */
export function stationHalls(m: TypedModel, T: Pick<TypesModule, "typeAt" | "phaseAt" | "phaseRules">): HallSpan[] {
  const ms = m.structure;
  if (!ms) return [];
  const half = m.settings.platform / 2;
  const plat = m.settings.platform;
  const mf = m.literals.hall.mezzanineFraction / 2;
  const out: HallSpan[] = [];
  m.stations.forEach((s, i) => {
    const a = accessType(m, T, i);
    if (!a || !HALL_TYPES.has(a.type)) return;
    const top = a.z + boxTopOf(ms, a.island) + ms.hall.clear + ms.hall.roof;
    const spans: [number, number][] =
      a.type === "end_halls"
        ? [
            [s.c - half, s.c - half + m.literals.hall.endHallsLen],
            [s.c + half - m.literals.hall.endHallsLen, s.c + half],
          ]
        : a.type === "mezzanine"
          ? [[s.c - mf * plat, s.c + mf * plat]]
          : [[s.c - half, s.c + half]];
    for (const [c0, c1] of spans) out.push({ station: i, c0, c1, top });
  });
  return out;
}
