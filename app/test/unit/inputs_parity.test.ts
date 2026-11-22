// The browser and the server must solve the same rail for the same profile (the "drawn band and engine giving two
// answers" defect). The server builds a SectionInput in region/ext/profiles/inputs.py; the line sheet rebuilds its
// stations and PVIs from the draft in src/plugins/line-sheet/model.ts. This test runs both on the same records and
// drafts, including a cleared level (a removed key), a slide, a deleted platform and an absent st, and compares.
//
// It needs a Python 3.12 or later with the repo's region package importable (only the standard library is used).
// CRHUB_PYTHON names the interpreter; otherwise python3, python and py are tried in that order.

import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import type { SectionInput } from "@cr/engine/contract";
import { describe, expect, it } from "vitest";
import { applyPatch } from "../../src/core/jsonpatch.ts";
import { localInput, type ProfileData, setStationLevel, stationFrame } from "../../src/plugins/line-sheet/model.ts";

const REPO = fileURLToPath(new URL("../../../", import.meta.url));

const SCRIPT = `
import json, sys
sys.path.insert(0, sys.argv[1])
from region.ext.profiles.inputs import Section, build
case = json.load(sys.stdin)
out = []
for prof in case["profiles"]:
    g = Section(case["section"], {"id": "PR", "data": prof} if prof is not None else None, case["stops"])
    for p in sorted(case["platforms"], key=lambda r: r["id"]):
        g.platforms.setdefault(p["data"].get("stop"), []).append(p)
    out.append(build(g, case["params"]))
json.dump(out, sys.stdout)
`;

function python(): string[] {
  const env = process.env.CRHUB_PYTHON;
  const tries = env ? [[env]] : [["python3"], ["python"], ["py", "-3"]];
  for (const t of tries) {
    const [cmd, ...pre] = t as [string, ...string[]];
    const r = spawnSync(cmd, [...pre, "-c", "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"]);
    if (r.status === 0) return t;
  }
  throw new Error("no Python 3.12 found for the parity test: set CRHUB_PYTHON to the interpreter");
}

/** What region/ext/profiles/inputs.py build() gives for each profile draft. */
function serverInputs(c: Case): SectionInput[] {
  const [cmd, ...pre] = python() as [string, ...string[]];
  // The section is sorted the way gather() sorts it before build() reads it.
  const num = (v: unknown) => (typeof v === "number" ? v : 0);
  const stops = [...c.stops].sort(
    (a, b) =>
      num(a.data.order) - num(b.data.order) ||
      num(a.data.c) - num(b.data.c) ||
      (a.id < b.id ? -1 : a.id > b.id ? 1 : 0),
  );
  const r = spawnSync(cmd, [...pre, "-I", "-c", SCRIPT, REPO], {
    input: JSON.stringify({ ...c, stops }),
    encoding: "utf8",
  });
  if (r.status !== 0) throw new Error(`inputs.build failed: ${r.stderr}`);
  return JSON.parse(r.stdout) as SectionInput[];
}

interface Case {
  section: { id: string; data: Record<string, unknown> };
  stops: { id: string; data: Record<string, unknown> }[];
  platforms: { id: string; data: Record<string, unknown> }[];
  params: SectionInput["params"];
  profiles: (ProfileData | null)[];
}

const saved: ProfileData = {
  section: "SEC",
  pvi: [
    [357, 168.5],
    [3005, 175],
  ],
  st: { PA: 150, PB: 151.5, PD: 170 },
  sg: { PA: 5, PB: -5 },
  so: { PA: -235.4, PC: 0.4 },
  del: ["PE"],
};

const draft = (ops: ReturnType<typeof setStationLevel>): ProfileData =>
  applyPatch({ data: saved, geom: null }, ops).data as ProfileData;

const CASE: Case = {
  section: {
    id: "SEC",
    data: { length_m: 6000, chainage_basis: "grid:26916", scale: 0.99983821, step_m: 2 },
  },
  stops: [
    { id: "S3", data: { order: 2, c: 4888.2 } },
    { id: "S1", data: { order: 0, c: 60.5 } },
    { id: "S2", data: { order: 1, c: 1084.2 } },
    // Two stops with the same order: c decides, then the id.
    { id: "S5", data: { order: 3, c: 5940 } },
    { id: "S4", data: { order: 3, c: 5940 } },
  ],
  platforms: [
    { id: "PB", data: { stop: "S2", name: "Bond Hill" } },
    { id: "PA", data: { stop: "S1", name: "Towne" } },
    { id: "PC", data: { stop: "S3", name: "Forest" } },
    { id: "PC2", data: { stop: "S3", name: "Forest north" } },
    { id: "PE", data: { stop: "S4", name: "Lytle Park" } },
    { id: "PD", data: { stop: "S5", name: "Greenlee" } },
  ],
  params: { platform_m: 121.92, vc_radius_m: 1500, vc_min_len_m: 30.5 },
  profiles: [
    saved,
    // Ben clears Bond Hill's level: the key goes.
    draft(setStationLevel(saved, "PB", null)),
    // He sets a level on a platform that had none.
    draft(setStationLevel(saved, "PC2", 201.25)),
    // The inspector removes st, sg or so whole, or un-deletes a platform, or slides one.
    { ...saved, st: undefined },
    { ...saved, sg: undefined, so: undefined },
    { ...saved, del: [], so: { ...saved.so, PB: 12.5 } },
    { ...saved, st: { ...saved.st, PA: null }, sg: { PA: null } },
    // PVIs in either shape, unsorted, or none at all.
    { ...saved, pvi: [{ c_m: 3005, z_m: 175 }, [357, 168.5]] },
    { section: "SEC" },
    null,
  ],
};

describe("browser and server build the same input", () => {
  it("localInput gives inputs.build's stations and PVIs for every draft", () => {
    const server = serverInputs(CASE);
    const frame = stationFrame(CASE.stops, CASE.platforms);
    // The input the sheet loaded: the server's for the saved profile.
    const loaded = server[0] as SectionInput;
    expect(loaded.stations.map((s) => s.platform_id)).toEqual(["PA", "PB", "PC", "PC2", "PD"]);
    CASE.profiles.forEach((p, i) => {
      const want = server[i] as SectionInput;
      const got = localInput(loaded, p ?? {}, frame);
      const byC = (x: SectionInput["pvi"]) => [...x].sort((a, b) => a.c_m - b.c_m);
      expect({ i, stations: got.stations, pvi: byC(got.pvi) }).toEqual({
        i,
        stations: want.stations,
        pvi: byC(want.pvi),
      });
    });
  });

  it("without the frame, a cleared level and an absent st still match the server", () => {
    const server = serverInputs(CASE);
    const loaded = server[0] as SectionInput;
    // The drafts that keep the same platforms (no del or so change): levels and grades follow the draft alone.
    for (const i of [1, 2, 3, 4, 6]) {
      const want = server[i] as SectionInput;
      const got = localInput(loaded, CASE.profiles[i] as ProfileData);
      expect({ i, stations: got.stations.map((s) => [s.platform_id, s.level_m, s.grade_permille]) }).toEqual({
        i,
        stations: want.stations.map((s) => [s.platform_id, s.level_m, s.grade_permille]),
      });
    }
  });
});
