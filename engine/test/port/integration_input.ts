// The input the integration test and bench read for one line: the golden adapter's (the line file, the seed doc with
// its frame, the linked crossings and the neighbours as the page held them), with the facts the halls read (each
// station's complex open at its opening, the phase of its opening year, Ben's access choices).

import type { Phase, PortInput } from "../../src/port/types.ts";
import { levelInput } from "./checks/input.ts";
import { crossingInput } from "./crossings/neighbours.ts";
import { fromGolden } from "./from_golden.ts";

/** The input the integration reads for one line: the golden adapter's, with the facts the halls read. */
export function integrationInput(line: string): PortInput {
  const { dump } = fromGolden(line);
  const base = levelInput(line);
  const nb = crossingInput(line);
  const atOpen = new Map(dump.stations.map((s) => [s.key, ((s.access.atOpen ?? []) as unknown[]).length > 0]));
  // the phase of the opening year (chrPhaseOfYear): the golden's access phase where the station has a year
  const yearPhase = new Map(dump.stations.map((s) => [s.key, s.year != null ? (s.access.phase as Phase) : null]));
  return {
    ...base,
    neighbours: nb.neighbours,
    crossings: nb.crossings,
    platforms: base.platforms.map((p) => ({
      ...p,
      interchangeAtOpen: atOpen.get(p.key) ?? false,
      yearPhase: yearPhase.get(p.key) ?? null,
    })),
    access: Object.fromEntries(
      dump.stations.filter((s) => s.access.source === "Ben").map((s) => [s.key, String(s.access.type)]),
    ),
  };
}
