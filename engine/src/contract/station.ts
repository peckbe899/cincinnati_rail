// StationInput v0 and StationFacts v0: the input and output of station.facts@1, what the line sheet shows and sets
// about each station (claude/hub_maps/profiles_parity.md, section A).
//
// The input carries the section's SectionInput (the rail is solved from it, as vertical.rail@1 solves it), the
// profile's station fields as the record holds them (the sheet sends its draft's), the section's platforms with what
// the records know about each (side or island, opening year and phase, complex), the section's path, its streets
// and roads, and every param the rules read. Python builds it (region/ext/profiles/inputs.py station_input); the
// engine never reads records.

import { z } from "zod";
import { Sha256, unit } from "./common.ts";
import { Flag } from "./flags.ts";
import { SectionInput } from "./section_input.ts";

export const StationType = z
  .enum(["elevated", "atgrade", "trough", "cutcover", "shield", "deep", "sunk"])
  .meta({ description: "A structure type, as the Profiles page names them (profiles.html 256)." });
export type StationType = z.infer<typeof StationType>;

export const SelectedType = z
  .enum(["cutcover", "shield", "deep", "elevated"])
  .meta({ description: "A station type Ben can select (stt, profiles.html 269)." });

export const AccessType = z
  .enum([
    "surface",
    "platform_level",
    "platform_level_xu",
    "end_halls",
    "mezzanine",
    "mezzanine_full",
    "mined_hall",
    "deep",
    "elevated_mezzanine",
  ])
  .meta({ description: "A station access type (profiles.html 467-477)." });
export type AccessType = z.infer<typeof AccessType>;

export const AccessChoice = z
  .strictObject({
    type: AccessType,
    stages: z.array(z.unknown()).optional().meta({ description: "Later stages of the access, as saved." }),
    source: z.string().optional().meta({ description: "Who chose it (the old hub wrote Ben)." }),
  })
  .meta({ description: "Ben's access choice for one platform (profile.access)." });

const Range3 = z.tuple([z.number(), z.number(), z.string()]);

export const StationProfile = z
  .strictObject({
    st: z.record(z.string(), z.number().nullable()).optional(),
    sg: z.record(z.string(), z.number()).optional(),
    so: z.record(z.string(), z.number()).optional(),
    del: z.array(z.string()).optional(),
    stt: z.record(z.string(), z.string()).optional(),
    gapfill: z.array(z.string()).optional(),
    access: z.record(z.string(), AccessChoice).optional(),
    mode: z.record(z.string(), z.string()).optional(),
    ovr: z.array(Range3).optional(),
    gnd: z.array(z.array(z.tuple([z.number(), z.number()]))).optional(),
  })
  .meta({
    description:
      "The profile record's station fields, keyed by platform id, as the record (or the sheet's draft) holds them: st, sg, so, del, stt, gapfill, access, mode, and the chainage fields the station rules read (ovr paints, gnd drawn ground).",
  });
export type StationProfile = z.infer<typeof StationProfile>;

export const ComplexMember = z
  .strictObject({
    line: z.string(),
    station: z.string(),
    sys: z.string(),
    name: z.string().meta({ description: "The member line's name for the text (Line 5)." }),
    year: z.number().nullable().meta(unit("year", "Opening year from the Chronology, null when none.")),
  })
  .meta({ description: "Another line's station this one is one station with (station_complex records)." });

export const StationPlatform = z
  .strictObject({
    platform_id: z.string().min(1),
    key: z.string().meta({ description: "The station key within its route (name, or name#index)." }),
    name: z.string(),
    order: z.int().nonnegative().meta(unit("index", "The platform's place along the section, in stop order.")),
    point_c_m: z.number().meta(unit("m", "The stop's drawn point on the section.")),
    side: z.enum(["side", "island"]).nullable().meta({ description: "platform.side: null reads as side." }),
    side_source: z.enum(["import", "ben", "default"]),
    year: z.number().nullable().meta(unit("year", "Opening year (Chronology), null when none.")),
    year_phase: z
      .string()
      .nullable()
      .meta({ description: "The phase of the opening year (chronology.phase_years), null when no year." }),
    phase: z.string().meta({ description: "The building phase at the station (Chronology segment, else line)." }),
    phase_source: z.enum(["chronology", "piece_phase", "line_phase", "default"]),
    complex: z.array(ComplexMember),
  })
  .meta({ description: "One platform of the section with what its records say, deleted ones included." });
export type StationPlatform = z.infer<typeof StationPlatform>;

export const PhaseRules = z.strictObject({
  cc_max_m: z.number().meta(unit("m", "Deepest cut and cover (metro_structure.phases.<p>.cc_max).")),
  deep_from_m: z.number().meta(unit("m", "Rail depth from which a mined station has lifts.")),
  tbm: z.boolean().meta({ description: "Bored by tunnel boring machine (deep), else hand shield." }),
  tube: z.enum(["A", "C", "bore"]).meta({ description: "The phase's running tube." }),
});

export const Tube = z.strictObject({
  inside: z.number().meta(unit("m")),
  outside: z.number().meta(unit("m")),
  rail_over_invert: z.number().meta(unit("m")),
});

export const StationStructure = z
  .strictObject({
    box_below_m: z.number().meta(unit("m", "metro_structure.box.below")),
    box_top_m: z.number().meta(unit("m", "metro_structure.box.top")),
    box_roof_underside_m: z.number().meta(unit("m", "metro_structure.box.roof_underside")),
    island_roof_underside_m: z.number().meta(unit("m", "metro_structure.island_box.roof_underside")),
    hall_clear_m: z.number().meta(unit("m", "metro_structure.hall.clear")),
    hall_roof_m: z.number().meta(unit("m", "metro_structure.hall.roof")),
    hall_cover_m: z.number().meta(unit("m", "metro_structure.hall.cover")),
    mezzanine_clear_m: z.number().meta(unit("m", "metro_structure.elevated_station.mezzanine_clear_m")),
    tubes: z.record(z.string(), Tube),
    phases: z.record(z.string(), PhaseRules),
    subway_streets: z.array(z.string()),
  })
  .meta({ description: "The Metro structure record's values the station rules read." });
export type StationStructure = z.infer<typeof StationStructure>;

export const StationParams = z
  .strictObject({
    platform_m: z.number().positive().meta(unit("m", "settings.platform")),
    def_depth_m: z.number().meta(unit("m", "settings.defDepth")),
    elev_above_m: z.number().meta(unit("m", "settings.elevAbove")),
    cover_below_m: z.number().meta(unit("m", "settings.coverBelow")),
    deck_depth_m: z.number().meta(unit("m", "settings.deckDepth")),
    pool_m: z.number().meta(unit("m", "settings.poolFt in metres")),
    sg_max_permille: z.number().meta(unit("permille", "Platform grade limit (literal.ERA.sgMax.* by line).")),
    sg_max_param: z.string().meta({ description: "The param path the limit came from." }),
    slide_max_m: z.number().meta(unit("m", "literal.SLIDE_M")),
    car_len_m: z.number().meta(unit("m", "literal.CAR_LEN")),
    end_door_m: z.number().meta(unit("m", "literal.END_DOOR")),
    plat_r_err_m: z.number().meta(unit("m", "literal.PLAT_R_ERR")),
    plat_r_warn_m: z.number().meta(unit("m", "literal.PLAT_R_WARN")),
    s_err_deg: z.number().meta(unit("deg", "literal.DRAW.sErr")),
    s_warn_deg: z.number().meta(unit("deg", "literal.DRAW.sWarn")),
    tol_m: z.number().meta(unit("m", "literal.station_limit_tol")),
    box_cover_m: z.number().meta(unit("m", "literal.BOX_COVER")),
    hall_end_len_m: z.number().meta(unit("m", "literal.hall.end_halls_len")),
    mezzanine_fraction: z.number().meta(unit("ratio", "literal.hall.mezzanine_fraction")),
  })
  .meta({ description: "Resolved params of the station rules." });
export type StationParams = z.infer<typeof StationParams>;

export const GroundRun = z.strictObject({
  i0: z.int().nonnegative().meta(unit("index", "First 2 m ground index of the run.")),
  v: z.array(z.number().meta(unit("m"))),
});

export const CrossGround = z
  .strictObject({
    c0: z.number().meta(unit("m")),
    c1: z.number().meta(unit("m")),
    z: z.number().meta(unit("m", "Another line's drawn ground level across its street.")),
  })
  .meta({ description: "Another line's drawn ground across this line (crossGround, profiles.html 674)." });

export const StationInput = z
  .strictObject({
    contract: z.literal("station_input/0"),
    section: SectionInput,
    route: z.string().meta({ description: "The route key (Line_3)." }),
    system: z.string().meta({ description: "metro, tri, ..." }),
    path: z
      .array(z.tuple([z.number(), z.number(), z.number()]))
      .meta({ description: "The section's path as [c, lon, lat], as the line file has it (the radius fit reads it)." }),
    profile: StationProfile,
    platforms: z.array(StationPlatform),
    rivers: z.array(z.strictObject({ name: z.string(), c0: z.number(), c1: z.number() })),
    params: StationParams,
    structure: StationStructure.nullable(),
    streets: z.array(z.tuple([z.number(), z.number(), z.number(), z.string(), z.string()])),
    roads: z.array(z.tuple([z.number(), z.number(), z.number(), z.number(), z.string(), z.string()])),
    ground_add: z.array(GroundRun).meta({ description: "The Deck's street re-grades, added to the ground." }),
    ground_cap: z.array(GroundRun).meta({ description: "The Deck's open cuts, the ground held at most at these." }),
    cross_ground: z.array(CrossGround),
    canon: z
      .array(
        z.strictObject({
          m: z.enum(["shallow", "deep", "canal", "covered"]),
          c0: z.number().meta(unit("m", "The section's start as the saved profile's stations put it.")),
          c1: z.number().meta(unit("m", "The section's end as the saved profile's stations put it.")),
          a: z.string().optional().meta({ description: "The station (platform name) the section starts at." }),
          b: z.string().optional().meta({ description: "The station (platform name) the section ends at." }),
          a_in: z
            .boolean()
            .optional()
            .meta({ description: "Whether a's platform is in the section (aIn, absent: true)." }),
          b_in: z
            .boolean()
            .optional()
            .meta({ description: "Whether b's platform is in the section (bIn, absent: true)." }),
        }),
      )
      .meta({
        description:
          "The canon's method sections on this section by chainage (buildCanon, profiles.html 876). A section that names its end stations is placed again from the live stations of the profile solved (a draft's: a station removed, restored or slid moves it, and a removed end drops it, as the old page rebuilt it on every edit); c0 and c1 are then only the saved profile's placing.",
      }),
    chron_segments: z
      .array(
        z.strictObject({
          c0: z.number().meta(unit("m")),
          c1: z.number().meta(unit("m")),
          year: z.number().nullable().meta(unit("year", "Opening year, null when none.")),
          phase: z.string().nullable().meta({ description: "The segment's phase, null when not set." }),
        }),
      )
      .optional()
      .meta({
        description:
          "The Chronology's segments along the section (chrSegments, profiles.html 1077). With them a station's phase is worked out again at its live centre (phaseAt 1091: the earlier-opened segment either side of the platform), so a slide in a draft gives the old page's phase at once; absent, each platform's phase is as given.",
      }),
    phases_along: z
      .array(z.strictObject({ c0: z.number().meta(unit("m")), c1: z.number().meta(unit("m")), phase: z.string() }))
      .meta({
        description:
          "The building phase along the running line (Chronology segment, else piece, else line), as runs; a stretch of tunnel splits where it changes.",
      }),
  })
  .meta({ title: "StationInput", description: "Contract station_input/0: the input of station.facts@1." });
export type StationInput = z.infer<typeof StationInput>;

const Span = z.tuple([z.number(), z.number()]);

export const StationAccess = z
  .strictObject({
    type: AccessType,
    rule: AccessType.meta({ description: "What the rules give (the select's 'Rules: X')." }),
    source: z.enum(["ben", "rule"]),
    rule_id: z.string(),
    d_hall_m: z.number().nullable().meta(unit("m", "Least rail depth for a hall over the box (D_HALL).")),
    depth_m: z.number().nullable().meta(unit("m")),
    island: z.boolean(),
    year: z.number().nullable(),
    phase: z.string(),
    dashed: z.boolean().meta({ description: "No opening year: drawn dashed (access.year.fallback_to_line_phase)." }),
    at_open: z.array(ComplexMember),
    later: z.array(ComplexMember),
    halls: z.array(Span),
    passage: Span.nullable(),
    shaft: Span.nullable(),
    hall_bottom_m: z.number().meta(unit("m")),
    hall_top_m: z.number().meta(unit("m")),
    mezz: z
      .strictObject({ halls: z.array(Span), bottom_m: z.number(), top_m: z.number() })
      .nullable()
      .meta({ description: "The street-level mezzanine under an elevated station." }),
    stages: z.array(z.unknown()),
  })
  .meta({ description: "The station's access (stationAccess, profiles.html 503-535)." });

export const PlatformCurve = z
  .strictObject({
    R_m: z.number().nullable().meta(unit("m", "Fitted radius; null is straight.")),
    out_m: z.number().meta(unit("m", "Extra gap, outside face.")),
    inn_m: z.number().meta(unit("m", "Extra gap, inside face.")),
    level: z.enum(["error", "warning"]).nullable(),
    gapfill: z.boolean(),
    turns: z.strictObject({
      pos: z.number(),
      neg: z.number(),
      s: z.enum(["error", "warning"]).nullable(),
    }),
  })
  .meta({ description: "The platform curve (platformCurve, profiles.html 2030)." });

export const StationFact = z
  .strictObject({
    platform_id: z.string(),
    key: z.string(),
    name: z.string(),
    order: z.int().nonnegative(),
    deleted: z.boolean(),
    index: z.int().nullable().meta({ description: "Index among the live stations; null when deleted." }),
    point_c_m: z.number().meta(unit("m")),
    slide_m: z.number().meta(unit("m", "so, as saved (never clamped).")),
    c_m: z.number().meta(unit("m", "Platform centre.")),
    half_m: z.number().meta(unit("m")),
    level_set: z.boolean(),
    level_m: z.number().nullable().meta(unit("m", "st as saved.")),
    rail_m: z.number().nullable().meta(unit("m", "Rail at the centre (the design line).")),
    rail_ends_m: Span.nullable().meta({ description: "Rail at c - half and c + half." }),
    default_level_m: z.number().nullable().meta(unit("m", "Ground minus settings.defDepth.")),
    ground_m: z.number().nullable().meta(unit("m", "Finished ground at the centre.")),
    ground_dem_m: z.number().nullable().meta(unit("m", "Surveyed ground at the centre.")),
    depth_m: z.number().nullable().meta(unit("m", "Ground minus rail (negative above ground).")),
    grade_in_permille: z.number().nullable(),
    grade_out_permille: z.number().nullable(),
    platform_grade_permille: z.number(),
    grade_limit_permille: z.number(),
    grade_limit_param: z.string(),
    type: StationType.nullable(),
    type_source: z.enum(["ben", "rule"]),
    type_why: z.string().meta({
      description:
        "selected (Ben), open (by level), river, canon_box (the canon's canal bed), box_within_limit, mined_past_limit, drive_paint (a mined station takes its drive's painted method), or no_rail (deleted).",
    }),
    selected: z.string().nullable().meta({ description: "stt as saved, null when none." }),
    role: z.enum(["box", "mined", "open"]).nullable(),
    phase: z.string(),
    phase_source: z.string(),
    cc_max_m: z.number().nullable().meta(unit("m")),
    side: z.enum(["side", "island"]),
    side_source: z.enum(["import", "ben", "default"]),
    structure: z
      .strictObject({ kind: z.string(), top_m: z.number(), bottom_m: z.number() })
      .nullable()
      .meta({ description: "The outline to draw: box, tube A/C/bore or deck, from the rail." }),
    elevated_rail_min_m: z.number().nullable().meta(unit("m", "Ground plus deck and mezzanine clear height.")),
    access: StationAccess.nullable(),
    curve: PlatformCurve.nullable(),
    street: z.strictObject({
      text: z.string(),
      street: z.string().nullable(),
      subway: z.boolean(),
      roads: z.array(z.string()),
    }),
    gapfill: z.boolean(),
    interchanges: z.array(z.string()).meta({
      description:
        "The other lines this station is one station with (its complex), by their names (Line 3, A trunk), once each in the complex's order: the sheet tags the station with them as the old page tagged its crossings.",
    }),
    flags: z.array(Flag),
  })
  .meta({ description: "Everything the sheet shows about one platform." });
export type StationFact = z.infer<typeof StationFact>;

export const StationFacts = z
  .strictObject({
    contract: z.literal("station_facts/0"),
    engine_build: Sha256.meta({ description: "sha256 of engine/src/** and engine/package.json." }),
    input_hash: Sha256.meta({ description: "sha256 of the canonical JSON (RFC 8785) of the StationInput." }),
    stations: z.array(StationFact),
    flags: z.array(Flag),
    summary: z.strictObject({ live: z.int(), removed: z.int(), errors: z.int(), warnings: z.int() }),
  })
  .meta({ title: "StationFacts", description: "Contract station_facts/0: the output of station.facts@1." });
export type StationFacts = z.infer<typeof StationFacts>;
