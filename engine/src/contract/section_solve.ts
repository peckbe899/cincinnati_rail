// SectionSolveInput v0 and SolvedSection v0: the input and output of section.solve@1, the whole solve of one section
// as the old Profiles page made it (claude/hub_maps/engine_port_plan.md, sections 3 and 4; engine/src/port/types.ts
// is the source of these shapes). Python builds the input from records (region/ext/profiles/inputs.py
// section_solve_input); the line sheet's worker swaps in its draft's profile and solves it after the rail.
//
// JSON only: NaN and infinities are null; arrays on the grid are plain number arrays (null where a value is not a
// number) or runs [value, c0, c1] by chainage.

import { z } from "zod";
import { unit } from "./common.ts";
import { RuleId, Severity } from "./flags.ts";

const num = (u: Parameters<typeof unit>[0], d?: string) => z.number().meta(unit(u, d));
const opt = z.number().nullable();
const Range3 = z.tuple([z.number(), z.number(), z.string()]);
const Phase = z.enum(["1", "2", "3", "later"]);
const TubeKey = z.enum(["A", "C", "bore"]);
const TypeName = z.enum(["elevated", "atgrade", "trough", "cutcover", "shield", "deep", "sunk"]);
const System = z.enum(["metro", "rer", "cvx"]);

export const PortSettingsJson = z
  .object({
    maxGrade: num("permille"),
    platform: num("m"),
    defDepth: num("m"),
    elevAbove: num("m"),
    coverBelow: num("m"),
    deepBelow: num("m"),
    shallowMax: num("m"),
    deckDepth: num("m"),
    pool: num("m", "settings.poolFt in metres"),
    vcRadius: num("m"),
    vcMinLen: num("m"),
    drainMin: num("permille"),
    curveK: num("permille"),
    stationMaxGrade: num("permille"),
    fillSlope: num("permille"),
    groundWarn: num("permille"),
    groundSustain: num("m"),
    groundMax: num("permille"),
    sustainedLen: num("m"),
    riverRoof: num("m"),
    riverSink: num("m"),
    riverRise: num("m"),
    riverFlatTol: num("m"),
    riverClearWater: num("m"),
    riverCap: num("m"),
    roadClearHighway: num("m"),
    roadClearMajor: num("m"),
    roadClearMinor: num("m"),
    rer: z
      .object({
        envelope: num("m"),
        boreCrown: num("m"),
        invertDepth: num("m"),
        minCover: num("m"),
        surfStep: num("m"),
      })
      .optional(),
  })
  .meta({ description: "The settings the solve reads (settings.* or settings_rer.* by system), page names." });

export const PortLiteralsJson = z
  .object({
    MIN_RUN: z.number(),
    BOX_COVER: z.number(),
    SEP_GAP: z.number(),
    BED_DEPTH: z.number(),
    VIA_SPAN: z.number(),
    VIA_CLEAR: z.number(),
    RIVER_SPAN: z.number(),
    GIRDER_MAX: z.number(),
    girder: z.object({ ratio: z.number(), add: z.number() }),
    trussRatio: z.number(),
    DECK_ON: z.number(),
    GND_W: z.number(),
    SLIDE_M: z.number(),
    CAR_LEN: z.number(),
    END_DOOR: z.number(),
    PLAT_R_ERR: z.number(),
    PLAT_R_WARN: z.number(),
    DRAW: z.object({
      single: z.number(),
      nb: z.number(),
      kink: z.number(),
      kinkSeg: z.number(),
      back: z.number(),
      sErr: z.number(),
      sWarn: z.number(),
    }),
    openClear: z.number(),
    bridgeAbovePool: z.number(),
    autoTypeRailTol: z.number(),
    drainageMinLen: z.number(),
    radii: z.object({ step: z.number(), h: z.number() }),
    approachHold: z.number(),
    coverHardFallback: z.number(),
    minDriveFallback: z.number(),
    minRadiusFallback: z.number(),
    portalMinFallback: z.number(),
    approachFallback: z.number(),
    tubeStreetNoteLen: z.number(),
    fillOver: z.number(),
    fillBand: z.object({ above: z.number(), below: z.number() }),
    platformOverlap: z.number(),
    limitTol: z.number(),
    lowCoverMinShort: z.number(),
    hall: z.object({ endHallsLen: z.number(), mezzanineFraction: z.number() }),
    regradeMargin: num("m", "literal.regrade_margin: Lower / Raise keep the rail this far past the bound.").optional(),
    regradeReserve: num(
      "permille",
      "literal.regrade_grade_reserve: Lower / Raise grade at most the limit less this.",
    ).optional(),
  })
  .meta({ description: "The page's named literals, each from its literal.* param (the plan's section 3.4)." });

const TubeRecord = z.object({
  inside: z.number(),
  outside: z.number(),
  rail_over_invert: z.number(),
  spacing: z.number(),
  label: z.string(),
});
const PhaseRecord = z.object({
  tube: TubeKey,
  cc_max: z.number(),
  min_drive: z.number(),
  deep_from: z.number(),
  min_radius: z.number(),
  grade_max: z.number(),
  grade_straight: z.number(),
  straight_warn: z.boolean(),
  grade_curve: z.number().nullable(),
  curve_radius: z.number(),
  tbm: z.boolean(),
  prefer: z.enum(["cutcover", "bored"]),
});

export const StructureParamsJson = z
  .object({
    box: z.object({
      below: z.number(),
      top: z.number(),
      roof_underside: z.number(),
      inside: z.number(),
      spacing: z.number(),
    }),
    island_box: z.object({ spacing: z.number(), roof_underside: z.number() }),
    tubes: z.object({ A: TubeRecord, C: TubeRecord, bore: TubeRecord }),
    phases: z.object({ "1": PhaseRecord, "2": PhaseRecord, "3": PhaseRecord, later: PhaseRecord }),
    approach_m: z.number(),
    portal_min_m: z.number(),
    min_radius: z.number(),
    cost: z.object({ cover_hard: z.number() }),
    grades: z.object({ straight_radius: z.number(), straight_underground_max: z.number().nullable() }),
    hall: z.object({ clear: z.number(), roof: z.number(), cover: z.number() }),
    mezzanine_clear_m: z.number(),
    open_clear_height: z.number(),
    subway_streets: z.array(z.string()),
    line_phase: Phase.nullable(),
    piece_phase: z.record(z.string(), Phase),
  })
  .meta({ description: "The Metro structure record (metro_structure.*) resolved for the route." });

export const CanonRecordJson = z
  .object({
    sections: z.array(
      z.object({
        a: z.string(),
        b: z.string(),
        aIn: z.boolean(),
        bIn: z.boolean(),
        m: z.enum(["shallow", "deep", "canal", "covered"]),
        src: z.string(),
      }),
    ),
    fixed: z.record(
      z.string(),
      z.object({ abs: z.number().optional(), off: z.number().optional(), ref: z.number().optional(), src: z.string() }),
    ),
    modes: z.record(z.string(), z.object({ mode: z.enum(["under", "surface"]), src: z.string().optional() })),
    locked: z.array(
      z.object({
        c0: z.number(),
        c1: z.number(),
        st: z.record(z.string(), z.number()),
        pvi: z.array(z.tuple([z.number(), z.number()])),
        ovr: z.array(Range3),
        src: z.string(),
        name: z.string().optional(),
      }),
    ),
    bridges: z.record(
      z.string(),
      z.object({ fixed: z.boolean().optional(), clear: z.number().optional(), src: z.string() }),
    ),
    decks: z.array(
      z.object({
        name: z.string(),
        pvi: z.array(z.tuple([z.number(), z.number(), z.number()])),
        piers: z.array(z.tuple([z.number(), z.number()])),
        src: z.string(),
      }),
    ),
  })
  .meta({ description: "One route's canon: method sections, fixed levels, modes, locks, bridges, decks." });

const Street = z.tuple([z.number(), z.number(), z.number(), z.string(), z.string()]);
const Road = z.tuple([z.number(), z.number(), z.number(), z.number(), z.string(), z.string()]);
const GroundRun = z.object({ i0: z.int().nonnegative(), v: z.array(z.number()) });

export const NeighbourJson = z
  .object({
    section: z.string(),
    wid: z.string(),
    system: System,
    length_m: num("m"),
    platform_m: num("m"),
    vc_radius_m: num("m"),
    vc_min_len_m: num("m"),
    stations: z.array(z.object({ c: z.number(), rail: z.number(), sg: z.number() })),
    pvi: z.array(z.object({ c: z.number(), z: z.number() })),
    gnd: z.array(z.array(z.object({ c: z.number(), z: z.number() }))),
    streets: z.array(Street),
    ready: z.boolean(),
    source: z.enum(["profile", "default", "metro_rails"]),
    phase: Phase.nullable(),
    settings: z.object({
      elevAbove: z.number(),
      coverBelow: z.number(),
      deepBelow: z.number(),
      deckDepth: z.number(),
      riverRoof: z.number().optional(),
      rer: PortSettingsJson.shape.rer,
    }),
    open_clear_m: z.number().optional(),
  })
  .meta({ description: "Another line at a crossing, as this line's solve reads it (plan section 3.3)." });

export const SectionSolveInput = z
  .object({
    contract: z.literal("section_solve_input/0"),
    section_id: z.string().min(1),
    route: z.string(),
    system: System,
    length: num("m"),
    step: num("m"),
    path: z.array(z.tuple([z.number(), z.number(), z.number()])),
    pieces: z.array(z.object({ name: z.string(), c0: z.number(), c1: z.number() })),
    dem: z.array(opt).meta({ description: "The surveyed ground on the grid, m; null where none." }),
    platforms: z.array(
      z.object({
        platform_id: z.string(),
        key: z.string(),
        name: z.string(),
        order: z.int().nonnegative(),
        point_c: z.number(),
        side: z.enum(["side", "island"]),
        year: z.number().nullable(),
        yearPhase: Phase.nullable(),
        transferAtOpen: z.boolean(),
        trunk: z.boolean(),
        sideSet: z.boolean().optional(),
        interchangeAtOpen: z.boolean().optional(),
      }),
    ),
    doc: z
      .object({
        st: z.record(z.string(), z.number().nullable()),
        sg: z.record(z.string(), z.number()),
        so: z.record(z.string(), z.number()),
        del: z.array(z.string()),
        pvi: z.array(z.tuple([z.number(), z.number()])),
        ovr: z.array(Range3),
        stt: z.record(z.string(), z.string()),
        tf: z.array(Range3),
        shafts: z.array(z.number()),
        gnd: z.array(z.array(z.tuple([z.number(), z.number()]))),
        gapfill: z.array(z.string()),
        mode: z.record(z.string(), z.enum(["under", "surface"])),
        ready: z.boolean(),
        frame: z.object({ length_m: z.number(), point_c: z.record(z.string(), z.number()) }).nullable(),
      })
      .nullable(),
    settings: PortSettingsJson,
    literals: PortLiteralsJson,
    structure: StructureParamsJson.nullable(),
    era: z.object({ shield: z.enum(["tube", "bore"]), sgMax: z.number() }).nullable(),
    canon: CanonRecordJson,
    rivers: z.array(
      z.object({
        name: z.string(),
        c0: z.number(),
        c1: z.number(),
        bedBelowPool: z.number().nullable(),
        navigable: z.boolean(),
        inCoveredWay: z.boolean(),
      }),
    ),
    context: z.object({
      streets: z.array(Street),
      roads: z.array(Road),
      blocks: z.array(
        z.looseObject({
          // l, the block's label in text, travels as an extra member (a one-letter name the Python models refuse)
          n: z.string(),
          k: z.string(),
          c0: z.number(),
          c1: z.number(),
          p: z.array(z.tuple([z.number(), z.number()])),
          b: z.number(),
          t: z.number(),
          o: z.boolean().optional(),
          pl: z.array(z.tuple([z.number(), z.number(), z.number()])).optional(),
        }),
      ),
      add: z.array(GroundRun),
      cap: z.array(GroundRun),
    }),
    crossings: z.array(
      z.object({
        c: z.number(),
        other: z.string().nullable(),
        wid: z.string(),
        oc: z.number(),
        kind: z.string(),
        with: z.string(),
      }),
    ),
    neighbours: z.record(z.string(), NeighbourJson),
    chronology: z.array(
      z.object({
        key: z.string(),
        c0: z.number(),
        c1: z.number(),
        year: z.number().nullable(),
        phase: Phase.nullable(),
        set: z.boolean(),
      }),
    ),
    approachExtra: z.array(
      z.object({ station: z.string().nullable(), side: z.number(), c: z.number(), extra: z.number() }),
    ),
    access: z.record(z.string(), z.string()).optional(),
    chronologyTable: z
      .object({
        sys: z.string(),
        segments: z.record(
          z.string(),
          z.looseObject({
            year: z.union([z.number(), z.string()]).nullable().optional(),
            phase: z.string().nullable().optional(),
          }),
        ),
        phase_years: z.array(z.tuple([z.number(), z.number(), z.string()])),
      })
      .optional()
      .meta({ description: "The Chronology's entries the line reads, so the segments follow a draft's stations." }),
  })
  .meta({
    title: "SectionSolveInput",
    description:
      "Everything section.solve@1 reads about one section, built from records (plan section 3): the profile, platforms, settings, literals, structure record, canon, rivers, context, crossings with their neighbours, Chronology.",
  });
export type SectionSolveInput = z.infer<typeof SectionSolveInput>;

// ------------------------------------------------------------------------------------------------------ output

const Struct = z.object({
  k: z.string(),
  below: z.number(),
  top: z.number(),
  od: z.number().optional(),
  tube: TubeKey.optional(),
});

export const SolvedFlag = z
  .object({
    kind: z.string(),
    page: z.string().meta({ description: "The old page's issue kind it answers (Grade, Cover, Clearance, ...)." }),
    sev: Severity,
    c0: z.number(),
    c1: z.number(),
    c: z.number().meta(unit("m", "Where the marker goes.")),
    rule: RuleId,
    data: z.record(z.string(), z.unknown()),
    fix: z.object({ mode: z.enum(["lower", "raise"]), c0: z.number(), c1: z.number() }).optional(),
    propose: z.object({ c0: z.number(), c1: z.number() }).optional(),
    clear: z.object({ c0: z.number(), c1: z.number(), si: z.number().optional() }).optional(),
    pending: z.boolean().optional(),
  })
  .meta({ description: "A finding of the solve with its rule id; the sheet words it." });

/** A run of one value over a chainage range: [value, c0, c1]. */
const runOf = <T extends z.ZodType>(v: T) => z.tuple([v, z.number(), z.number()]);

export const SolvedSection = z
  .object({
    contract: z.literal("solved_section/0"),
    engine_build: z.string(),
    input_hash: z.string(),
    section_id: z.string(),
    length_m: num("m"),
    step_m: num("m"),
    n: z.int().nonnegative(),
    stations: z.array(
      z.object({
        index: z.int(),
        platform_id: z.string(),
        key: z.string(),
        name: z.string(),
        point_c: z.number(),
        c: z.number(),
        level: opt,
        sg: z.number(),
        type: TypeName,
        role: z.string().nullable(),
        plat_def: z.string().nullable(),
        street: z.object({ street: z.int(), subway: z.boolean(), roads: z.array(z.int()), known: z.boolean() }),
      }),
    ),
    type_runs: z.array(runOf(TypeName)).meta({ description: "The drawn type (typeAt at the rail) as runs." }),
    struct_runs: z
      .array(z.tuple([Struct, z.number(), z.number()]))
      .meta({ description: "The structure at the rail as runs: below and top are offsets from the rail." }),
    tube_runs: z.array(runOf(TubeKey.nullable())),
    part_runs: z.array(runOf(z.enum(["", "a", "S"]))),
    phase_runs: z.array(runOf(Phase)),
    grade_limit_runs: z.array(z.tuple([z.number(), z.number().nullable(), z.number(), z.number()])),
    limit_tube: z.array(opt).meta({ description: "The shallowest a tube may run, per sample; null where open." }),
    limit_box: z.array(opt).meta({ description: "The deepest a box may go, per sample; null where open." }),
    ground: z.object({
      finished: z.array(opt),
      surface: z.array(opt),
      bed: z.array(opt),
      lines: z.array(z.array(z.object({ c: z.number(), z: z.number() }))),
      cross: z.array(z.looseObject({ c0: z.number(), c1: z.number(), z: z.number() })),
    }),
    made_bed: z.array(z.object({ i0: z.int(), z: z.array(z.number()) })),
    rivers: z.array(z.looseObject({ name: z.string(), c0: z.number(), c1: z.number() })),
    canon: z.object({
      sections: z.array(z.looseObject({ m: z.string(), lo: z.number(), hi: z.number() })),
      locks: z.array(z.object({ lo: z.number(), hi: z.number(), name: z.string().nullable(), src: z.string() })),
      piers: z.array(z.number()),
    }),
    spans: z.array(
      z.object({
        c0: z.number(),
        c1: z.number(),
        L: z.number(),
        truss: z.boolean(),
        below: z.number(),
        above: z.number(),
        ends: z.tuple([z.boolean(), z.boolean()]),
      }),
    ),
    bad: z.array(z.object({ why: z.string(), c0: z.number(), c1: z.number(), worst: z.number() })),
    misfits: z.array(z.looseObject({ c0: z.number(), c1: z.number(), t: z.string(), why: z.string() })),
    approaches: z.array(z.looseObject({ kind: z.string(), c: z.number(), len: z.number(), side: z.number() })),
    shafts: z.array(z.number()),
    stretches: z.array(z.looseObject({ c0: z.number(), c1: z.number(), method: z.string(), why: z.string() })),
    crossings: z.array(
      z.looseObject({
        c: z.number(),
        wid: z.string(),
        with: z.string(),
        zo: opt,
        z: z.number(),
        clear: opt,
        need: opt,
        t: Struct,
        to: Struct.nullable(),
        ok: z.boolean(),
        pending: z.boolean(),
      }),
    ),
    context: z.array(z.looseObject({ block: z.int(), c: z.number(), ok: z.boolean() })),
    roads: z.array(z.looseObject({ kind: z.string(), sev: Severity, c: z.number(), road: z.int() })),
    over: z.array(
      z.object({ c0: z.number(), c1: z.number(), g: z.number(), sev: z.enum(["local", "straight", "error"]) }),
    ),
    curve_grade: z.array(z.object({ c0: z.number(), c1: z.number(), worst: z.number(), sustained: z.boolean() })),
    summary: z.looseObject({
      len: z.record(z.string(), z.number()),
      maxG: z.number(),
      sumps: z.number(),
    }),
    flags: z.array(SolvedFlag),
    levels: z.object({ st: z.array(opt), unset: z.array(z.int()) }),
    design: z
      .object({
        source: z.enum(["saved", "default", "partial"]),
        note: z.string(),
        pvi: z.array(z.object({ c: z.number(), z: z.number() })),
        st: z.record(z.string(), opt).meta({ description: "The rail level solved at each live platform." }),
        so: z.record(z.string(), z.number()).meta({ description: "The slides solved (a reframed profile's)." }),
        defaulted: z.array(z.string()),
        reframed: z.boolean(),
        reframe: z
          .object({
            ovr: z.array(z.tuple([z.number(), z.number(), z.string()])),
            tf: z.array(z.tuple([z.number(), z.number(), z.string()])),
            shafts: z.array(z.number()),
            gnd: z.array(z.array(z.tuple([z.number(), z.number()]))),
            frame: z.object({ length_m: z.number(), point_c: z.record(z.string(), z.number()) }),
          })
          .nullable()
          .optional()
          .meta({
            description:
              "A profile saved in an older frame: its paints, tube forms, shafts and drawn ground in the current one, and the frame it is then in (reframeDoc). The sheet lays them into the draft, with the design's bend points, slides and levels, on the first edit.",
          }),
      })
      .meta({
        description:
          "Whose design was solved: Ben's (saved), the level solver's for a profile with no saved level and no bend point (default: never written as his record), or his with the level solver's level at each station he has not set (partial); the levels, slides and bend points solved (the default's river bend points, a reframed profile's mapped ones), the stations at a default level, and whether the profile was reframed.",
      }),
    derived: z
      .object({
        stations: z.array(
          z.object({
            name: z.string(),
            c: z.number(),
            point_c: z.number(),
            rail: opt,
            ground: opt,
            depth: opt,
            type: TypeName,
          }),
        ),
        summary: z.object({
          km_by_type: z.record(z.string(), z.number()),
          max_grade_permille: z.number(),
          grades_over_limit: z.int(),
        }),
      })
      .meta({
        description:
          "The doc's derived members as the old page's serialize() wrote them on save (R6): per live station its name, centre, drawn point, rail, ground and depth to the centimetre and type; the km of each type, the steepest grade and the grades over the limit. Derived, never Ben's edit.",
      }),
  })
  .meta({
    title: "SolvedSection",
    description:
      "The whole solve of one section (section.solve@1): the drawn type and structure, the legal band, ground, rivers, viaducts, canon, crossings, context, roads, summary and every finding with its rule id.",
  });
export type SolvedSection = z.infer<typeof SolvedSection>;
