// What P2's input reads besides the shared adapter's (from_golden.ts), built from the repository's read-only records
// as the old page had them:
// - the crossings as the page held them after linkRerCrossings (3395): the line file's, with each RER line's own
//   crossing points laid in (an RER crossing the line file names without a key takes the RER file's points; one it
//   does not name is added). Python's section.crossings carries these; the adapter reads the line file alone.
// - the neighbours crossGround (674) reads: each crossing line's saved profile's drawn ground (S.saved, the hub's seed
//   alignments) and that line's Deck streets (context/lines.json). Only gnd and streets are filled from the records;
//   the other members are what P3's own extension of the adapter builds (claude/hub_maps/engine_port_plan.md,
//   section 3.3) and are left neutral here, because P2 reads nothing else of a neighbour.

import { readFileSync } from "node:fs";
import type { CrossingRecord, Neighbour, PortInput, Street } from "../../../src/port/types.ts";
import { lineFile, REPO } from "../from_golden.ts";

const readJson = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, REPO), "utf8")) as T;

interface RerLine {
  id: string;
  line?: string;
  short?: string;
  crossings?: { c: number; wid: string; oc: number; kind: string; with: string }[];
}

let rer: RerLine[] | null = null;
/** The RER line files in the order of their index, as the page loaded them into S.rerData (3313-3319). */
function rerLines(): RerLine[] {
  if (!rer) {
    const idx = readJson<{ id: string }[]>("data/profile/rer/lines/index.json");
    rer = idx.flatMap((l) => {
      try {
        return [readJson<RerLine>(`data/profile/rer/lines/${l.id}.json`)];
      } catch {
        return [];
      }
    });
  }
  return rer;
}

/** The line's crossings after linkRerCrossings (3395-3403). */
export function linkedCrossings(line: string): CrossingRecord[] {
  const own = (lineFile(line).crossings ?? []).map(
    (x) => ({ ...x }) as { c: number; wid?: string; oc: number; kind: string; with: string },
  );
  const list = rerLines();
  if (list.length)
    for (const r of list)
      for (const x of (r.crossings ?? []).filter((y) => y.wid === line)) {
        const m = own.find((y) => y.kind === "rer" && !y.wid && y.with === r.line && Math.abs(y.c - x.oc) < 120);
        if (m) {
          m.wid = r.id;
          m.oc = x.c;
        } else own.push({ c: x.oc, wid: r.id, oc: x.c, kind: "rer", with: r.short || r.line || r.id });
      }
  own.sort((a, b) => a.c - b.c);
  return own.map((x) => ({ c: x.c, wid: x.wid ?? "", oc: x.oc, kind: x.kind, with: x.with, other: x.wid ?? null }));
}

interface SavedDoc {
  gnd?: [number, number][][];
  ready?: boolean;
  pvi?: [number, number][];
}

const docs = new Map<string, SavedDoc | null>();
function savedDoc(wid: string): SavedDoc | null {
  if (!docs.has(wid)) {
    let d: SavedDoc | null = null;
    try {
      d = JSON.parse(readFileSync(new URL(`hub/seed/alignments/${wid}.json`, REPO), "utf8")) as SavedDoc;
    } catch {
      d = null;
    }
    docs.set(wid, d);
  }
  return docs.get(wid) ?? null;
}

let ctx: Record<string, { streets?: Street[] }> | null = null;
function streetsOf(wid: string): Street[] {
  if (!ctx)
    ctx = (
      JSON.parse(readFileSync(new URL("data/profile/context/lines.json", REPO), "utf8")) as {
        lines: Record<string, { streets?: Street[] }>;
      }
    ).lines;
  return ctx[wid]?.streets ?? [];
}

/** A ground-only neighbour for each crossing line that has a saved profile (a seed alignment). */
export function groundNeighbours(line: string): Record<string, Neighbour> {
  const out: Record<string, Neighbour> = {};
  for (const x of linkedCrossings(line)) {
    if (out[x.wid] || x.wid === line) continue;
    const doc = savedDoc(x.wid);
    if (!doc) continue;
    out[x.wid] = {
      section: x.wid,
      wid: x.wid,
      system: x.wid.startsWith("RER_") ? "rer" : x.wid === "CVG_Express" ? "cvx" : "metro",
      length_m: Number.NaN,
      platform_m: Number.NaN,
      vc_radius_m: Number.NaN,
      vc_min_len_m: Number.NaN,
      stations: [],
      pvi: (doc.pvi ?? []).map(([c, z]) => ({ c, z })),
      // the raw [c, z] points; crossGround keeps them as parseGnd does
      gnd: (doc.gnd ?? []).map((L) => L.map(([c, z]) => ({ c: +c, z: +z }))),
      streets: streetsOf(x.wid),
      ready: !!doc.ready,
      source: "profile",
      phase: null,
      settings: { elevAbove: Number.NaN, coverBelow: Number.NaN, deepBelow: Number.NaN, deckDepth: Number.NaN },
    };
  }
  return out;
}

/** The golden input with the page's crossings and the ground-only neighbours laid in. */
export const withNeighbours = (input: PortInput, line: string): PortInput => ({
  ...input,
  crossings: linkedCrossings(line),
  neighbours: groundNeighbours(line),
});
