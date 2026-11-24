// The design the sheet draws when it is not the profile as saved (claude/hub_maps/profiles_parity.md S57, S66, S84):
// a line with no saved level and no bend point (Lines 10, 11 and 13) is drawn on its default design, the level
// solver's levels and river bend points (the old page's defaultAlign, 1756); a station with no level on a line that
// has some takes the level solver's; and a profile saved against other stops (Line 2b) is drawn mapped onto the
// current ones (reframeDoc, 1839). section.solve@1 of the draft gives that design (its output's `design`); the
// sheet lays it into the profile it draws, solves and hit-tests, and never into Ben's record: the draft takes it
// only with his first edit, in the same undo step, as the old page's save wrote S.align whole (serialize 3213).

import type { SolvedSection } from "@cr/engine/contract";
import type { JsonPatch } from "../../api/types.ts";
import { applyPatch, deepEqual } from "../../core/jsonpatch.ts";
import type { ProfileData } from "./model.ts";
import { proposalOps } from "./tools.ts";

/** What section.solve@1 says of the design it solved (its output's `design`). */
export type SheetDesign = SolvedSection["design"];

const sameFrame = (a: unknown, b: { length_m: number; point_c: Record<string, number> }): boolean => {
  if (!a || typeof a !== "object") return false;
  const f = a as { length_m?: unknown; point_c?: unknown };
  if (f.length_m !== b.length_m || !f.point_c || typeof f.point_c !== "object") return false;
  const pc = f.point_c as Record<string, unknown>;
  const keys = Object.keys(b.point_c);
  return Object.keys(pc).length === keys.length && keys.every((k) => pc[k] === b.point_c[k]);
};

/** Whether the profile has a bend point of its own. */
const hasPvis = (data: ProfileData): boolean => Array.isArray(data.pvi) && data.pvi.length > 0;

/**
 * The ops that lay the design into the profile, or none when it holds it already (a saved design in its own frame,
 * or a draft that took it): a station with no level of its own (one the solve defaulted) at the design's level; on
 * a profile with no bend point, the default design's bend points; on one saved in an older frame, the bend points,
 * slides, paints, tube forms, shafts and drawn ground in the current frame, and that frame. Ben's own values stay.
 */
export function designOps(data: ProfileData, design: SheetDesign | null | undefined): JsonPatch {
  if (!design) return [];
  const st = (data.st ?? {}) as Record<string, unknown>;
  const levels: Record<string, number> = {};
  for (const pid of design.defaulted) {
    const z = design.st[pid];
    if (typeof z === "number" && Number.isFinite(z) && typeof st[pid] !== "number") levels[pid] = z;
  }
  const edit: NonNullable<Parameters<typeof proposalOps>[1]["edit"]> = {};
  if (Object.keys(levels).length) edit.st = levels;
  const rf = design.reframed && design.reframe && !sameFrame(data.frame, design.reframe.frame) ? design.reframe : null;
  if (rf) {
    edit.pvi = design.pvi.map((p) => [p.c, p.z]);
    edit.so = { ...design.so };
    edit.ovr = rf.ovr;
    edit.tf = rf.tf;
    edit.shafts = rf.shafts;
    edit.gnd = rf.gnd;
    edit.frame = rf.frame;
  } else if (design.source === "default" && !hasPvis(data) && design.pvi.length) {
    edit.pvi = design.pvi.map((p) => [p.c, p.z]);
  }
  if (!Object.keys(edit).length) return [];
  return proposalOps(data, { edit } as Parameters<typeof proposalOps>[1]);
}

/** The profile as the sheet draws it: with the design laid in (designOps), else the profile itself. */
export function laidIn(data: ProfileData, design: SheetDesign | null | undefined): ProfileData {
  const ops = designOps(data, design);
  if (!ops.length) return data;
  return applyPatch({ data }, ops).data;
}

/**
 * What the sheet's bar says of the design it draws when it is not Ben's as saved: the solve's own words for a default
 * design ("default design (not saved)") or a default level, and for a profile saved in an older frame that it is
 * drawn on the current stops. Null when nothing is laid in.
 */
export function designNote(data: ProfileData, design: SheetDesign | null | undefined): string | null {
  if (!design || !designOps(data, design).length) return null;
  const rf = design.reframed && design.reframe && !sameFrame(data.frame, design.reframe.frame);
  if (design.source === "default" || design.source === "partial") return design.note;
  return rf ? "drawn on the current stops (not saved)" : null;
}

/**
 * A design worth keeping for the profile: one that lays something in. A solve of a profile that holds its design
 * (a saved one, or a draft that took it) says "saved"; the sheet keeps the last other one, so a Ctrl+Z back to the
 * untouched profile draws the design again at once, without waiting for a solve.
 */
export const keepsDesign = (design: SheetDesign | null | undefined): boolean =>
  !!design && (design.source !== "saved" || (design.reframed && !!design.reframe));

/**
 * The ops one edit writes into Ben's draft: the edit's own (made on the profile as drawn, laidIn) after the design's
 * (designOps of the profile as held), so the first edit takes the design with it in the same undo step. Null when the
 * edit changes nothing: then nothing is written, the design included.
 */
export function editOps(held: ProfileData, design: SheetDesign | null | undefined, ops: JsonPatch): JsonPatch | null {
  const lay = designOps(held, design);
  if (!lay.length) return ops;
  if (!ops.length) return null;
  const drawn = laidIn(held, design);
  if (deepEqual(applyPatch({ data: drawn }, ops) as never, { data: drawn } as never)) return null;
  return [...lay, ...ops];
}
