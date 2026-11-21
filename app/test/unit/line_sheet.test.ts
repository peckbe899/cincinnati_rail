import type { SectionInput } from "@cr/engine/contract";
import { describe, expect, it } from "vitest";
import { applyPatch } from "../../src/core/jsonpatch.ts";
import {
  addPvi,
  localInput,
  maxDiff,
  pviRows,
  pviShape,
  removePvi,
  setPviC,
  setPviZ,
  setStationLevel,
  solveInput,
  toFloat64,
} from "../../src/plugins/line-sheet/model.ts";

const input: SectionInput = {
  contract: "section_input/0",
  section_id: "S6",
  length_m: 1000,
  chainage_basis: "grid:26916",
  scale: 1.0002,
  step_m: 2,
  params: { platform_m: 121.92, vc_radius_m: 1500, vc_min_len_m: 30.5 },
  stations: [
    { platform_id: "PA", order: 0, c_m: 100, level_m: 200, grade_permille: null },
    { platform_id: "PB", order: 1, c_m: 900, level_m: null, grade_permille: null },
  ],
  pvi: [{ c_m: 500, z_m: 205 }],
};

describe("line sheet model", () => {
  it("edits PVIs in the record's own shape and station levels by platform id", () => {
    const tuple = { pvi: [[500, 205]], st: { PA: 200 } };
    const objs = { pvi: [{ c_m: 500, z_m: 205 }] };
    const short = { pvi: [{ c: 500, z: 205 }] };
    expect(pviShape(tuple)).toEqual({ kind: "tuple" });
    expect(pviShape(objs)).toEqual({ kind: "object", c: "c_m", z: "z_m" });
    expect(pviShape(short)).toEqual({ kind: "object", c: "c", z: "z" });
    expect(setPviZ(tuple, 0, 206)).toEqual([{ op: "replace", path: "/data/pvi/0/1", value: 206 }]);
    expect(setPviZ(objs, 0, 206)).toEqual([{ op: "replace", path: "/data/pvi/0/z_m", value: 206 }]);
    expect(setPviC(short, 0, 510)).toEqual([{ op: "replace", path: "/data/pvi/0/c", value: 510 }]);

    const body = { data: tuple, geom: null };
    let b = applyPatch(body, addPvi(tuple, 300, 203));
    expect(pviRows(b.data)).toEqual([
      { index: 0, c: 300, z: 203 },
      { index: 1, c: 500, z: 205 },
    ]);
    b = applyPatch(b, removePvi(0));
    expect(b.data.pvi).toEqual([[500, 205]]);
    b = applyPatch(b, setStationLevel(b.data, "PB", 201.5));
    expect(b.data.st).toEqual({ PA: 200, PB: 201.5 });
    b = applyPatch(b, setStationLevel(b.data, "PA", null));
    expect(b.data.st).toEqual({ PB: 201.5 });
    // A record without st or pvi gets them added.
    const empty = applyPatch({ data: {}, geom: null }, [...setStationLevel({}, "PA", 1), ...addPvi({}, 10, 2)]);
    expect(empty.data).toEqual({ st: { PA: 1 }, pvi: [{ c_m: 10, z_m: 2 }] });
  });

  it("builds the local input from the draft", () => {
    const li = localInput(input, {
      pvi: [
        [700, 210],
        [400, 204],
      ],
      st: { PB: 202, PA: null },
    });
    expect(li.pvi).toEqual([
      { c_m: 400, z_m: 204 },
      { c_m: 700, z_m: 210 },
    ]);
    expect(li.stations.map((s) => s.level_m)).toEqual([null, 202]);
    expect(localInput(input, null)).toBe(input);
    // The worker's input leaves the ground out (vertical.rail does not read it) and keeps everything else.
    const withGround = { ...input, ground: { step_m: 2, z_m: [1, 2, 3] } };
    expect("ground" in solveInput(withGround, null)).toBe(false);
    expect(solveInput(withGround, null).pvi).toEqual(input.pvi);
    expect(input.pvi).toEqual([{ c_m: 500, z_m: 205 }]);
  });

  it("reads result arrays of any float dtype and compares rails", () => {
    const f8 = new Float64Array([1, 2, 3]);
    expect(Array.from(toFloat64("<f8", f8.buffer))).toEqual([1, 2, 3]);
    expect(Array.from(toFloat64("f4", new Float32Array([1.5, 2.5]).buffer))).toEqual([1.5, 2.5]);
    expect(maxDiff([1, 2, 3], [1, 2.5, 2])).toBe(1);
  });
});
