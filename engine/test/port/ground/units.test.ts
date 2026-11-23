// P2 ground, unit by unit: the named cases of the plan (claude/hub_maps/engine_port_plan.md, section 7.2: Line 1's L&N
// bridge, Line 6's Ohio and Licking crossings), the page's edge cases each function keeps, the differences from the
// page that are on purpose (each named with its reason), and agreement with station.facts@1's own copies
// (src/station/ground.ts, src/station/live.ts), so the integrator can make those thin re-exports.

import { describe, expect, test } from "vitest";
import type { PathPoint } from "../../../src/geom/path.ts";
import {
  alongShore,
  applyLocks,
  bedOf,
  buildCanon,
  chainLL,
  crossGround,
  drawnGround,
  fixedLevel,
  GROUND_RULES,
  gndLevel,
  lockAt,
  lockedStation,
  madeBedArray,
  normGnd,
  parseGnd,
  refAt,
  regradeGround,
  riverBand,
  riverBridges,
  riverIndex,
  sampleGround,
  spanAt,
  sunkBox,
  viaductSpans,
} from "../../../src/port/ground/index.ts";
import type {
  Align,
  CanonModel,
  LiveStation,
  Lock,
  PortInput,
  RiverRecord,
  SectionModel,
} from "../../../src/port/types.ts";
import { isRuleId } from "../../../src/rules.gen.ts";
import { parseGnd as stationParseGnd, sampleGround as stationSample } from "../../../src/station/ground.ts";
import { liveCanon } from "../../../src/station/live.ts";
import { ground } from "../../golden/old_page/load.ts";
import { goldenTypes, METRO_LINES, typedFromGolden } from "../from_golden.ts";
import { buildP2 } from "./compare.ts";

describe("Line 1: the L&N bridge (a deck lock on its piers)", () => {
  const run = buildP2("Line_1");
  const { canon, model: m } = run;

  test("the deck is a locked stretch from its first pier to its last, Elevated, its bend points to 0.1 m", () => {
    expect(canon.locks).toHaveLength(1);
    const lk = canon.locks[0] as Lock;
    expect(lk.name).toBe("L&N bridge truss spans");
    expect(canon.piers).toHaveLength(6);
    expect(lk.lo).toBe(canon.piers[0]);
    expect(lk.hi).toBe(canon.piers[5]);
    expect(lk.pvi).toEqual([
      [16384.5, 162.72],
      [16463, 164.19],
      [16779.4, 157.64],
    ]);
    expect(lk.ovr).toEqual([[lk.lo, lk.hi, "elevated"]]);
    expect(lockAt(m, lk.lo - 0.5)).toBe(lk);
    expect(lockAt(m, lk.lo - 0.6)).toBeNull();
  });

  test("the Ohio is on the fixed bridge: no band, no navigation-clearance band, no made-up bed", () => {
    const ohio = run.rivers.find((r) => r.name === "Ohio River");
    expect(ohio?.bridge?.fixed).toBe(true);
    expect(ohio?.band).toBeNull();
    expect(ohio?.bridgeBand).toBeNull();
    expect(riverBridges(m)).toEqual([]);
    const typed = typedFromGolden("Line_1");
    const mb = madeBedArray({ ...m, types: typed.types, spans: [] }, goldenTypes(run.dump));
    expect(Array.from(mb).every(Number.isNaN)).toBe(true);
  });

  test("the spans over the river are the bridge's own piers", () => {
    const typed = typedFromGolden("Line_1");
    const spans = viaductSpans(m, typed.types, goldenTypes(run.dump));
    const r10 = (v: number): number => Math.round(v * 10) / 10;
    const pierCs = canon.piers.map(r10);
    for (let k = 0; k + 1 < pierCs.length; k++)
      expect(spans.some((s) => s.c0 === pierCs[k] && s.c1 === pierCs[k + 1])).toBe(true);
    // over 40 m: through trusses, span / 8 deep over the rail, the deck under it
    const truss = spans.filter((s) => s.truss);
    expect(truss.length).toBeGreaterThan(0);
    for (const s of truss) {
      expect(s.above).toBeCloseTo(s.L / 8, 9);
      expect(s.below).toBe(m.settings.deckDepth);
    }
    expect(spanAt(spans, (pierCs[1] as number) + 1)?.c0).toBe(pierCs[1]);
    expect(spanAt(spans, 0)).toBeNull();
  });

  test("a path 25 m off the bridge (the old Line 1 tunnel) puts no line on it: every pier must be within DECK_ON", () => {
    const off = 25 / 110540; // 25 m north
    const path: PathPoint[] = run.input.path.map(([c, x, y]) => [c, x, y + off] as const);
    const moved = buildCanon({ ...run.input, path }, m.stations, m.grid);
    expect(moved.locks).toEqual([]);
    expect(moved.piers).toEqual([]);
    const pier = run.input.canon.decks[0]?.piers[0];
    if (!pier) throw new Error("Line 1 has the L&N deck");
    const [lon, lat] = pier;
    expect(chainLL(path, lon, lat, 5)).toBeNull();
    expect(chainLL(path, lon, lat)).not.toBeNull(); // within the default 30 m
  });

  test("applyLocks puts a moved stretch back, says so with a flag, and never changes its argument", () => {
    const lk = canon.locks[0] as Lock;
    const mid = (lk.lo + lk.hi) / 2;
    const moved: Align = {
      ...m.align,
      pvi: [...m.align.pvi.filter((p) => p.c < lk.lo || p.c > lk.hi), { c: mid, z: 140 }].sort((a, b) => a.c - b.c),
      ovr: [
        ...m.align.ovr.filter((o) => o[2] !== "elevated" || o[1] < lk.lo || o[0] > lk.hi),
        [mid - 10, mid + 10, "cutcover"],
      ],
    };
    const before = JSON.stringify(moved);
    const out = applyLocks(moved, canon, m.stations);
    expect(JSON.stringify(moved)).toBe(before);
    expect(out.changed).toBe(true);
    expect(out.align.pvi).toEqual(m.align.pvi);
    expect(out.align.ovr.filter((o) => o[1] > lk.lo && o[0] < lk.hi)).toEqual([[lk.lo, lk.hi, "elevated"]]);
    expect(out.flags).toHaveLength(1);
    expect(out.flags[0]).toMatchObject({
      kind: "lock_kept",
      rule: "network.canon.locks",
      sev: "info",
      c0: lk.lo,
      c1: lk.hi,
    });
    // the golden's align is already as canon has it: nothing to change, no flag
    expect(applyLocks(m.align, canon, m.stations)).toMatchObject({ changed: false, flags: [] });
  });
});

describe("Line 6: the Ohio and the Licking in sunk boxes", () => {
  const run = buildP2("Line_6");
  const { model: m, dump: d } = run;
  const S = m.settings;

  test("each river's band as the page's, the Ohio navigable (12 ft of clear water), the Licking not", () => {
    const [ohio, licking] = run.rivers;
    expect([ohio?.name, licking?.name]).toEqual(["Ohio River", "Licking River"]);
    const top = run.sunk.top;
    expect(top).toBe(5); // the box's 4.0 m roof underside plus the 1.0 m roof (structure.sunk_box.dimensions_from_record)
    expect(ohio?.band?.nav).toBeCloseTo(S.pool - S.riverClearWater - S.riverCap - top, 9);
    expect(licking?.band?.nav).toBeNull();
    for (const [k, r] of [ohio, licking].entries()) {
      const g = d.rivers[k]?.band as { ub: number; lb: number; low: number };
      expect(r?.band?.ub).toBeCloseTo(g.ub, 6);
      expect(r?.band?.lb).toBeCloseTo(g.lb, 6);
      expect(r?.band?.low).toBeCloseTo(g.low, 6);
      // the lower limit holds on the flat bottom only: the highest bed within riverFlatTol of the lowest, less sink
      const flatBed = (r?.band?.lb as number) + top + S.riverSink;
      expect(flatBed).toBeGreaterThanOrEqual(r?.band?.low as number);
      expect(flatBed).toBeLessThanOrEqual((r?.band?.low as number) + S.riverFlatTol);
    }
  });

  test("the made-up bed over the Ohio box roof, on the page's own types and on P1's", () => {
    const g = ground(d).made_bed;
    const pageCount = g.filter((v) => !Number.isNaN(v)).length;
    expect(pageCount).toBeGreaterThan(0);
    const typed = typedFromGolden("Line_6");
    const mb = madeBedArray({ ...m, types: typed.types, spans: [] }, goldenTypes(d));
    expect(Array.from(mb).filter((v) => !Number.isNaN(v)).length).toBe(pageCount);
    // only over a river, on the sunk box
    for (let i = 0; i < mb.length; i++)
      if (!Number.isNaN(mb[i] as number)) expect(m.riverAt[i]).toBeGreaterThanOrEqual(0);
  });

  test("the surface is the pool over each river, the finished ground elsewhere", () => {
    const i = Math.round(((run.rivers[1]?.c0 as number) + 4) / 2);
    expect(run.ground.surface[i]).toBe(S.pool);
    expect(run.ground.surface[0]).toBe(run.ground.finished[0]);
  });
});

describe("the page's edge cases, kept", () => {
  const g = Float32Array.from([10, Number.NaN, 14, 16]);

  test("sampleGround: linear, held at the ends, a NaN sample takes its neighbour's value", () => {
    expect(sampleGround(g, 2, 5)).toBe(15);
    expect(sampleGround(g, 2, -3)).toBe(10);
    expect(sampleGround(g, 2, 99)).toBe(16);
    expect(sampleGround(g, 2, 1)).toBe(10); // b is NaN: a
    expect(sampleGround(g, 2, 2.5)).toBe(14); // a is NaN: b
  });

  test("intended: sampleGround of an empty ground is NaN (the page read undefined out of range)", () => {
    expect(sampleGround(new Float32Array(0), 2, 3)).toBeNaN();
  });

  test("regradeGround adds the re-grades, caps at the open cuts, leaves NaN alone, and is the DEM with neither", () => {
    expect(regradeGround(g, { add: [], cap: [] })).toBe(g);
    const r = regradeGround(g, { add: [{ i0: 0, v: [1, 1, 1] }], cap: [{ i0: 2, v: [12, 99, 0] }] });
    expect(Array.from(r)).toEqual([11, Number.NaN, 12, 16]);
    expect(Array.from(g)).toEqual([10, Number.NaN, 14, 16]);
  });

  test("parseGnd keeps finite points, lines of two or more over 1 m, sorted; a null reads as 0 as on the page", () => {
    const raw = [
      [
        [30, 5],
        [10, 4],
        [20, Number.NaN],
      ],
      [[5, 1]],
      [
        [0, 1],
        [0.5, 2],
      ],
      [
        [null, 3],
        [3, 3],
      ],
    ] as unknown as Parameters<typeof parseGnd>[0];
    expect(parseGnd(raw)).toEqual([
      [
        { c: 0, z: 3 },
        { c: 3, z: 3 },
      ],
      [
        { c: 10, z: 4 },
        { c: 30, z: 5 },
      ],
    ]);
    expect(parseGnd(null)).toEqual([]);
  });

  test("gndLevel and normGnd: straight grades, held past the ends; the ends on the regraded ground to the cm", () => {
    const P = [
      { c: 10, z: 4 },
      { c: 30, z: 6 },
    ];
    expect(gndLevel(P, 20)).toBe(5);
    expect(gndLevel(P, 40)).toBe(6);
    const base = Float32Array.from([
      1.234, 1.234, 1.234, 1.234, 1.234, 1.234, 1.234, 1.234, 1.234, 1.234, 1.234, 1.234, 1.234, 1.234, 1.234, 1.234,
    ]);
    const out = normGnd([P], base, 2);
    expect(out).toEqual([
      [
        { c: 10, z: 1.23 },
        { c: 30, z: 1.23 },
      ],
    ]);
    expect(P[0]?.z).toBe(4);
  });

  test("drawnGround: the crossing line's level across its street unless this line draws there; own lines win", () => {
    const base = new Float32Array(11).fill(100);
    const line = [
      { c: 0, z: 101 },
      { c: 6, z: 101 },
    ];
    const cross = [{ c0: 4, c1: 12, z: 90, wid: "X", with: "X", street: null, w: 8 }];
    const out = drawnGround(base, [line], cross, 2);
    expect(Array.from(out)).toEqual([101, 101, 101, 101, 90, 90, 90, 100, 100, 100, 100]);
    expect(drawnGround(base, [], [], 2)).toBe(base);
  });

  test("crossGround: the neighbour's drawn level at the crossing, across its street (GND_W where none); never its own", () => {
    const nb = {
      gnd: [
        [
          { c: 90, z: 150 },
          { c: 110, z: 152 },
        ],
      ],
      streets: [[95, 105, 22, "Main St", "major"] as const],
    };
    const input = {
      section_id: "L",
      route: "L",
      crossings: [
        { c: 500, wid: "N", oc: 100, kind: "metro", with: "Line N", other: "N" },
        { c: 700, wid: "N", oc: 200, kind: "metro", with: "Line N", other: "N" },
        { c: 900, wid: "L", oc: 100, kind: "metro", with: "self", other: "L" },
      ],
      neighbours: { N: nb, L: nb } as unknown as PortInput["neighbours"],
    };
    expect(crossGround(input, 15)).toEqual([
      { c0: 489, c1: 511, z: 151, wid: "N", with: "Line N", street: "Main St", w: 22 },
    ]);
    const noStreet = { ...input, neighbours: { N: { ...nb, streets: [] } } as unknown as PortInput["neighbours"] };
    expect(crossGround(noStreet, 15)[0]).toMatchObject({ c0: 492.5, c1: 507.5, w: 15, street: null });
  });

  test("riverIndex: the first river whose range holds c", () => {
    const rs = [
      { c0: 0, c1: 10 },
      { c0: 5, c1: 20 },
    ];
    expect([riverIndex(rs, 7), riverIndex(rs, 15), riverIndex(rs, 25)]).toEqual([0, 1, -1]);
  });

  test("fixedLevel: absolute, else an offset from the ground; NaN with neither, as the page", () => {
    expect(fixedLevel({ abs: 160.3, src: "" }, 150)).toBe(160.3);
    expect(fixedLevel({ off: -18.29, src: "" }, 250)).toBeCloseTo(231.71, 9);
    expect(fixedLevel({ src: "" }, 250)).toBeNaN();
  });

  test("bedOf: the canon bed below the pool where the river has one, else the ground (null)", () => {
    expect(bedOf({ bedBelowPool: 3 }, 138.684)).toBeCloseTo(135.684, 9);
    expect(bedOf({ bedBelowPool: null }, 138.684)).toBeNull();
  });
});

describe("the canon on the live stations (bug A: a draft's canon is its own)", () => {
  const run = buildP2("Line_6");
  const { model: m, input } = run;

  test("a removed end station drops its section; a slid one moves it", () => {
    const sec = input.canon.sections[0];
    if (!sec) throw new Error("Line 6 has a canon section");
    const without = m.stations.filter((s) => s.name !== sec.a);
    expect(buildCanon(input, without, m.grid).sections).toEqual([]);
    const slid = m.stations.map((s) => (s.name === sec.b ? { ...s, c: s.c + 30 } : s));
    const a = buildCanon(input, m.stations, m.grid).sections[0];
    const b = buildCanon(input, slid, m.grid).sections[0];
    expect((b?.hi as number) - (a?.hi as number)).toBeCloseTo(30, 9);
  });

  test("station/live.ts liveCanon agrees with buildCanon on every Metro line, with stations removed and slid", () => {
    for (const line of METRO_LINES) {
      const r = buildP2(line);
      const half = r.input.settings.platform / 2;
      const recs = r.input.canon.sections.map((s) => ({
        m: s.m,
        c0: 0,
        c1: 0,
        a: s.a,
        b: s.b,
        a_in: s.aIn,
        b_in: s.bIn,
      }));
      const variants: LiveStation[][] = [
        r.model.stations.slice(),
        r.model.stations.filter((_, i) => i % 3 !== 1),
        r.model.stations.map((s, i) => ({ ...s, c: s.c + (i % 2 ? 40 : -25) })),
      ];
      for (const st of variants) {
        const port = buildCanon(r.input, st, r.model.grid).sections.map((s) => [s.m, s.lo, s.hi]);
        const live = liveCanon(recs, st, half).map((s) => [s.m, s.c0, s.c1]);
        expect(port).toEqual(live);
      }
    }
  });

  test("fixed levels by live station index; lockedStation finds a lock holding a station's level", () => {
    const r4 = buildP2("Line_4");
    expect(Object.keys(r4.canon.fixed).map(Number)).toEqual([7, 8, 9]);
    const st = r4.model.stations;
    const lk: Lock = {
      c0: 0,
      c1: 1,
      lo: 0,
      hi: 1,
      st: { [st[3]?.name as string]: 200 },
      pvi: [],
      ovr: [],
      src: "test",
    };
    const mm = { canon: { ...r4.canon, locks: [lk] } as CanonModel, stations: st };
    expect(lockedStation(mm, 3)).toBe(lk);
    expect(lockedStation(mm, 4)).toBeNull();
    const out = applyLocks(r4.model.align, mm.canon, st);
    expect(out.align.st[3]).toBe(200);
    expect(out.align.sg[3]).toBe(0);
  });

  test("refAt: a canon reference level, else the surface at the centre (CVG Express: Union Terminal is absolute, no ref)", () => {
    const r = buildP2("CVG_Express");
    const fixed = { ...r.canon.fixed, 0: { ...(r.canon.fixed[0] as { abs: number; src: string }), ref: 155 } };
    expect(refAt({ ...r.model, canon: { ...r.canon, fixed } }, 0)).toBe(155);
    expect(refAt(r.model, 0)).toBe(r.dump.stations[0]?.ref);
    expect(refAt(r.model, 99)).toBeNaN();
  });
});

describe("the RER branches (slice 2), so nothing blocks them", () => {
  const run = buildP2("Line_6");
  const rer = {
    ...run.input,
    system: "rer" as const,
    settings: {
      ...run.input.settings,
      rer: { envelope: 6.6, boreCrown: 7.5, invertDepth: 1, minCover: 8.5, surfStep: 250 },
    },
  };

  test("the RER sunk box is the envelope box; a Metro section without the record has none (the page fell back to numbers)", () => {
    expect(sunkBox(rer)).toMatchObject({ below: 1, top: 6.6 });
    expect(() => sunkBox({ ...run.input, structure: null })).toThrow(/structure record/);
    expect(() => sunkBox({ ...rer, settings: run.input.settings })).toThrow(/settings.rer/);
  });

  test("a river along the covered way is the shore, not a crossing; one crossed inside it is a crossing", () => {
    const r: RiverRecord = {
      name: "Little Miami River",
      c0: 100,
      c1: 160,
      bedBelowPool: 3,
      navigable: false,
      inCoveredWay: false,
    };
    const canon: CanonModel = {
      ...run.canon,
      sections: [{ m: "covered", lo: 0, hi: 1000, a: "A", b: "B", src: "test" }],
    };
    const m = { input: rer, canon } as Pick<SectionModel, "input" | "canon">;
    expect(alongShore(m, r)).toBe(true);
    expect(alongShore(m, { ...r, inCoveredWay: true })).toBe(false);
    expect(alongShore({ ...m, input: run.input }, r)).toBe(false);
    const band = riverBand(
      { input: { ...rer, rivers: [r] }, settings: rer.settings, ground: run.ground, canon, sunk: run.sunk },
      r,
    );
    expect(band).toBeNull();
  });

  test("the RER canon has no Metro bridges or decks", () => {
    const withDeck = buildP2("Line_1");
    const c = buildCanon({ ...withDeck.input, system: "rer" }, withDeck.model.stations, withDeck.model.grid);
    expect(c.locks).toEqual([]);
    expect(c.piers).toEqual([]);
    expect(riverBridges({ input: { ...buildP2("CVG_Express").input, system: "rer" }, settings: rer.settings })).toEqual(
      [],
    );
  });
});

describe("station.facts@1's own copies agree (src/station/ground.ts), so they can become re-exports", () => {
  test("sampleGround and parseGnd agree on every Metro line's ground and drawn lines", () => {
    for (const line of METRO_LINES) {
      const r = buildP2(line);
      const G = r.ground.finished;
      for (let c = -3; c < r.input.length + 5; c += 7.3) expect(sampleGround(G, 2, c)).toBe(stationSample(G, 2, c));
      const raw = r.input.doc?.gnd ?? [];
      expect(parseGnd(raw)).toEqual(stationParseGnd(raw as [number, number][][]));
    }
  });
});

test("GROUND_RULES are registry rules", () => {
  for (const r of GROUND_RULES) expect(isRuleId(r)).toBe(true);
});

describe("what the input must carry (for the lead's section_solve_input)", () => {
  test("the crossings after linkRerCrossings (3395): with the line file's alone, Line 11's piers miss the B CVG crossing", () => {
    const run = buildP2("Line_11");
    const typed = typedFromGolden("Line_11");
    const T = goldenTypes(run.dump);
    const page = run.dump.viaduct_spans;
    expect(viaductSpans(run.model, typed.types, T)).toEqual(page);
    const fileOnly = { ...run.model, input: { ...run.input, crossings: typed.input.crossings } };
    expect(fileOnly.input.crossings.some((x) => x.wid === "RER_B_cvg" && Math.abs(x.c - 13869.3) < 0.01)).toBe(false);
    expect(viaductSpans(fileOnly, typed.types, T)).not.toEqual(page);
  });
});
