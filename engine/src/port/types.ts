// The shared types of the port of the rest of the Profiles page's engine (I2.2; claude/hub_maps/engine_port_plan.md).
//
// Four work packages build against these types at once:
//   P1 types       engine/src/port/types/      pointType ... applyMS: the structure solver and type lookup
//   P2 ground      engine/src/port/ground/     ground layers, rivers, viaducts, canon and locks
//   P3 crossings   engine/src/port/crossings/  other lines, context blocks, roads
//   P4 checks      engine/src/port/checks/     summary, radii, design checks, issues, fill, levels and docs
// Each package takes and gives the data below, never another package's functions, so each is built and tested
// alone on engine/test/golden/old_page (the old page's own answers for every intermediate value). Where a package
// needs a function of another at a point off the grid (typeAt at a crossing), it takes the module interface at
// the end of this file and its tests pass a golden-backed stand-in.
//
// Conventions: chainage c in metres on the section's grid, from 0; levels in metres NAVD88; grades in per mille;
// arrays on the 2 m grid have n = floor(L / step) + 1 points at c_i = min(i * step, L) (src/grid.ts). Ground
// arrays are Float32Array, as the page holds them, so every threshold falls the same way. Names on the left of the
// settings are the page's (profiles.html 277), as src/params.ts does. No UI text: kinds, numbers and rule ids.

import type { PathPoint } from "../geom/path.ts";
import type { RuleId } from "../rules.gen.ts";
import type { Design } from "../vertical/design.ts";

// ------------------------------------------------------------------------------------------------ scalars, codes

/** A structure type (TYPES, profiles.html 256). */
export type Type = "elevated" | "atgrade" | "trough" | "cutcover" | "shield" | "deep" | "sunk";
/** Every type, in the code order of a TypeCodes array. */
export const TYPE_CODES = ["elevated", "atgrade", "trough", "cutcover", "shield", "deep", "sunk"] as const;

/** A station type Ben can select (STT, 269). */
export type SelectedType = "cutcover" | "shield" | "deep" | "elevated";
/** A tube form Ben can paint (tf, 1124). */
export type TubeForm = "twin" | "bore";
/** A building phase (metro_structure.phases, chronology.phase_years). */
export type Phase = "1" | "2" | "3" | "later";
/** A bored tube (metro_structure.tubes). */
export type TubeKey = "A" | "C" | "bore";
/** A canon method section (CANON 293; rer/canon.json sections). */
export type MethodSection = "shallow" | "deep" | "canal" | "covered";
/** A sample's part of the solve: '' running line, 'a' a station approach box, 'S' a station platform (1597). */
export type Part = "" | "a" | "S";
/** A sample's role in the solve (base, 1371-1385): open track, the sunk river box, a box anchor, tunnel, mined station. */
export type Role = "open" | "river" | "box" | "tunnel" | "mined";
/** A station's role (stOf, 1388-1398). */
export type StationRole = "box" | "mined" | "open";
/** pointType's class of a Metro tunnel point outside the canon (1265): too shallow to bore, either, past cc_max. */
export type PointClass = "C" | "E" | "B";
/** An engine finding's severity (contract Flag); the page's "note" is "info". */
export type Sev = "info" | "warn" | "error";
/** A road class (context roads, 454). */
export type RoadClass = "highway" | "major" | "minor";
/** A [c0, c1, value] range as the profile stores paints and tube forms. */
export type Range3<T extends string = string> = readonly [c0: number, c1: number, v: T];

/** One value per grid sample, as codes into a table (TYPE_CODES, or a table the array carries). */
export type Codes = Uint8Array;

/** The grid of one section. */
export interface Grid {
  readonly n: number;
  readonly step: number;
  readonly length: number;
  /** c_i = min(i * step, length). */
  readonly c: Float64Array;
}

/** A categorical array with its table: value of sample i is table[codes[i]] (null where the table holds null). */
export interface CodedArray<T> {
  readonly table: readonly T[];
  readonly codes: Codes;
}

// -------------------------------------------------------------------------------------------- params and records

/**
 * The settings the engine reads, resolved by Python (settings.* or settings_rer.* by system, the line's overlay,
 * then Ben's main revisions; decision 9.25). Page names; units in the comments.
 */
export interface PortSettings {
  readonly maxGrade: number; // permille
  readonly platform: number; // m
  readonly defDepth: number; // m
  readonly elevAbove: number; // m
  readonly coverBelow: number; // m
  readonly deepBelow: number; // m
  readonly shallowMax: number; // m
  readonly deckDepth: number; // m
  /** settings.poolFt converted to metres once (pool(), 603). */
  readonly pool: number; // m
  readonly vcRadius: number; // m
  readonly vcMinLen: number; // m
  readonly drainMin: number; // permille
  readonly curveK: number; // permille * m
  /** The platform grade limit: literal.ERA.sgMax.* on the Metro (sgMaxFor, 1227), stationMaxGrade on the RER. */
  readonly stationMaxGrade: number; // permille
  readonly fillSlope: number; // permille
  readonly groundWarn: number; // permille
  readonly groundSustain: number; // m
  readonly groundMax: number; // permille
  readonly sustainedLen: number; // m
  readonly riverRoof: number; // m
  readonly riverSink: number; // m
  readonly riverRise: number; // m
  readonly riverFlatTol: number; // m
  readonly riverClearWater: number; // m
  readonly riverCap: number; // m
  readonly roadClearHighway: number; // m
  readonly roadClearMajor: number; // m
  readonly roadClearMinor: number; // m
  /** RER only (settings_rer.*); absent on the Metro, where structFor and reqCover read the structure record. */
  readonly rer?: {
    readonly envelope: number;
    readonly boreCrown: number;
    readonly invertDepth: number;
    readonly minCover: number;
    readonly surfStep: number;
  };
}

/** The page's named literals, each from its literal.* param of rules/registry.yaml (the plan's section 3.4). */
export interface PortLiterals {
  readonly MIN_RUN: number;
  readonly BOX_COVER: number;
  readonly SEP_GAP: number;
  readonly BED_DEPTH: number;
  readonly VIA_SPAN: number;
  readonly VIA_CLEAR: number;
  readonly RIVER_SPAN: number;
  readonly GIRDER_MAX: number;
  /** literal.girder_soffit: a girder span's rail to soffit is L / ratio + add (987). */
  readonly girder: { readonly ratio: number; readonly add: number };
  /** literal.truss_depth: a truss is L / ratio deep (987). */
  readonly trussRatio: number;
  readonly DECK_ON: number;
  readonly GND_W: number;
  readonly SLIDE_M: number;
  readonly CAR_LEN: number;
  readonly END_DOOR: number;
  readonly PLAT_R_ERR: number;
  readonly PLAT_R_WARN: number;
  readonly DRAW: {
    readonly single: number;
    readonly nb: number;
    readonly kink: number;
    readonly kinkSeg: number;
    readonly back: number;
    readonly sErr: number;
    readonly sWarn: number;
  };
  /** literal.OPEN_CLEAR.metro (replaced by metro_structure.open_clear_height when the record has it) and .rer. */
  readonly openClear: number;
  /** literal.bridge_above_pool: a rail this far over the pool inside a river range is a bridge (1255, 1374, 2198). */
  readonly bridgeAbovePool: number;
  /** literal.autoType_rail_tol: typeAt reads the solve only within this of the solved rail (1607). */
  readonly autoTypeRailTol: number;
  /** literal.drainage_min_len: a flat tunnel chord shorter than this is not flagged (2107). */
  readonly drainageMinLen: number;
  /** literal.radii_window: radii every `step` m from a circle through points `h` steps apart (1952). */
  readonly radii: { readonly step: number; readonly h: number };
  /** literal.approach_K_window: the launch box holds its cover for approach_m (1474). */
  readonly approachHold: number;
  readonly coverHardFallback: number;
  readonly minDriveFallback: number;
  readonly minRadiusFallback: number;
  readonly portalMinFallback: number;
  readonly approachFallback: number;
  /** literal.tube_street_note_len: twin tubes under a narrow street are a note from this length (1550). */
  readonly tubeStreetNoteLen: number;
  /** literal.fill_over / fill_band: Propose fill's margin over the minimum and the band its points keep (1708, 1715). */
  readonly fillOver: number;
  readonly fillBand: { readonly above: number; readonly below: number };
  /** literal.platform_overlap: platforms closer than platform less this overlap (2101). */
  readonly platformOverlap: number;
  /** literal.station_limit_tol: the 0.05 m of the station and limit checks. */
  readonly limitTol: number;
  /** literal.low_cover_min_short: a tube short of cover by less than this is not flagged (1532). */
  readonly lowCoverMinShort: number;
  /** literal.hall.end_halls_len and .mezzanine_fraction (528-529). */
  readonly hall: { readonly endHallsLen: number; readonly mezzanineFraction: number };
  /** Lower / Raise: the margin past the bound (literal.regrade_margin) and the grade reserve under the limit
   * (literal.regrade_grade_reserve); the page's 0.3 m and 2 per mille when the input has none */
  readonly regradeMargin?: number;
  readonly regradeReserve?: number;
}

export interface TubeRecord {
  readonly inside: number;
  readonly outside: number;
  readonly rail_over_invert: number;
  readonly spacing: number;
  readonly label: string;
}

/** One building phase of metro_structure.phases (each member from its param; Phase later from its own or 3's). */
export interface PhaseRecord {
  readonly tube: TubeKey;
  readonly cc_max: number;
  readonly min_drive: number;
  readonly deep_from: number;
  readonly min_radius: number;
  readonly grade_max: number;
  readonly grade_straight: number;
  readonly straight_warn: boolean;
  readonly grade_curve: number | null;
  readonly curve_radius: number;
  readonly tbm: boolean;
  readonly prefer: "cutcover" | "bored";
}

/** The Metro structure record (metro_structure.*, applyMS 1065), resolved for one section. */
export interface StructureParams {
  readonly box: {
    readonly below: number;
    readonly top: number;
    readonly roof_underside: number;
    readonly inside: number;
    readonly spacing: number;
  };
  readonly island_box: { readonly spacing: number; readonly roof_underside: number };
  readonly tubes: Readonly<Record<TubeKey, TubeRecord>>;
  readonly phases: Readonly<Record<Phase, PhaseRecord>>;
  readonly approach_m: number;
  readonly portal_min_m: number;
  readonly min_radius: number;
  readonly cost: { readonly cover_hard: number };
  readonly grades: { readonly straight_radius: number; readonly straight_underground_max: number | null };
  readonly hall: { readonly clear: number; readonly roof: number; readonly cover: number };
  readonly mezzanine_clear_m: number;
  readonly open_clear_height: number;
  readonly subway_streets: readonly string[];
  /** metro_structure.line_phase for this route, null when none (phaseAt falls back to later). */
  readonly line_phase: Phase | null;
  /** metro_structure.piece_phase for this route: piece name to phase. */
  readonly piece_phase: Readonly<Record<string, Phase>>;
}

/** ERA[id] (1186): the shield of a line without the record, and its platform grade limit. */
export interface Era {
  readonly shield: "tube" | "bore";
  readonly sgMax: number;
}

/** A canon method section by its end stations (CANON sections; buildCanon 876). */
export interface CanonSectionRecord {
  readonly a: string;
  readonly b: string;
  readonly aIn: boolean;
  readonly bIn: boolean;
  readonly m: MethodSection;
  readonly src: string;
}

/** A fixed station level (CANON fixed): absolute, or an offset from the ground, and an optional reference level. */
export interface FixedLevel {
  readonly abs?: number;
  readonly off?: number;
  readonly ref?: number;
  readonly src: string;
}

/** A locked stretch (canon locked, Ben 27 October): its bend points, station levels and paints are canon. */
export interface LockRecord {
  readonly c0: number;
  readonly c1: number;
  readonly st: Readonly<Record<string, number>>;
  readonly pvi: readonly (readonly [c: number, z: number])[];
  readonly ovr: readonly Range3<Type>[];
  readonly src: string;
  readonly name?: string;
}

/** A fixed bridge deck placed by position (CANON decks), so a re-path carries it. */
export interface DeckRecord {
  readonly name: string;
  readonly pvi: readonly (readonly [lon: number, lat: number, z: number])[];
  readonly piers: readonly (readonly [lon: number, lat: number])[];
  readonly src: string;
}

/** A canon river bridge (CANON bridges): fixed (the L&N), or held at a navigation clearance over the pool. */
export interface BridgeRecord {
  readonly fixed?: boolean;
  readonly clear?: number;
  readonly src: string;
}

/** One route's canon, a record (new kind canon v1, plan section 3.2). */
export interface CanonRecord {
  readonly sections: readonly CanonSectionRecord[];
  readonly fixed: Readonly<Record<string, FixedLevel>>;
  /** RER station modes; empty on the Metro. */
  readonly modes: Readonly<Record<string, { readonly mode: "under" | "surface"; readonly src?: string }>>;
  readonly locked: readonly LockRecord[];
  readonly bridges: Readonly<Record<string, BridgeRecord>>;
  readonly decks: readonly DeckRecord[];
}

/** A river on the section with its canon properties (section.rivers plus canon.rivers.<name>.*). */
export interface RiverRecord {
  readonly name: string;
  readonly c0: number;
  readonly c1: number;
  /** canon.rivers.<name>.bed_below_pool_m: the bed this far under the pool; null reads the bed from the ground. */
  readonly bedBelowPool: number | null;
  readonly navigable: boolean;
  readonly inCoveredWay: boolean;
}

/** A street the line runs along: [c0, c1, width, name, class] (section_context.streets). */
export type Street = readonly [c0: number, c1: number, width: number, name: string, cls: string];
/** A road the line crosses: [c, c0, c1, width, name, class] (section_context.roads). */
export type Road = readonly [c: number, c0: number, c1: number, width: number, name: string, cls: string];

/** An other-system structure as a chainage block (section_context blocks, from the Deck; 2213). */
export interface ContextBlock {
  /** name */
  readonly n: string;
  /** label in text */
  readonly l: string;
  /** kind: box, tube, viaduct, fill, atgrade, trough, ... */
  readonly k: string;
  readonly st?: string;
  readonly c0: number;
  readonly c1: number;
  /** its rail by chainage on this line, [c, z] */
  readonly p: readonly (readonly [c: number, z: number])[];
  /** rail to underside */
  readonly b: number;
  /** rail to top */
  readonly t: number;
  /** open (a line in the open: its clear envelope dotted) */
  readonly o?: boolean;
  /** its platforms [c0, c1, z] */
  readonly pl?: readonly (readonly [c0: number, c1: number, z: number])[];
  readonly s?: unknown;
  readonly gaps?: unknown;
}

export interface ContextRecord {
  readonly streets: readonly Street[];
  readonly roads: readonly Road[];
  readonly blocks: readonly ContextBlock[];
  readonly add: readonly { readonly i0: number; readonly v: readonly number[] }[];
  readonly cap: readonly { readonly i0: number; readonly v: readonly number[] }[];
}

/** Where another line crosses this one (section.crossings). */
export interface CrossingRecord {
  readonly c: number;
  /** the other line's section id when it is in the hub */
  readonly other: string | null;
  /** the old key (Line_3, RER_A_trunk) */
  readonly wid: string;
  /** the other line's chainage at the crossing */
  readonly oc: number;
  readonly kind: string;
  readonly with: string;
}

/**
 * The other line at a crossing, as much as this line's solve reads of it. otherRail (2182) rebuilds its rail from
 * its saved profile's derived stations and bend points; the port sends the same, plus its solved type at the
 * crossing when the hub has one (clearance.crossing.other_line_guessed decides which the check reads).
 */
export interface Neighbour {
  readonly section: string;
  readonly wid: string;
  readonly system: "metro" | "rer" | "cvx";
  readonly length_m: number;
  readonly platform_m: number;
  readonly vc_radius_m: number;
  readonly vc_min_len_m: number;
  /** its live stations in order: platform centre, rail level, platform grade */
  readonly stations: readonly { readonly c: number; readonly rail: number; readonly sg: number }[];
  readonly pvi: readonly { readonly c: number; readonly z: number }[];
  /** its drawn ground lines (crossGround, 674) */
  readonly gnd: readonly (readonly { readonly c: number; readonly z: number }[])[];
  /** its streets (for the width of its drawn ground across this line) */
  readonly streets: readonly Street[];
  /** profile.ready: its weaving is set (network.profile_set.crossings_apart) */
  readonly ready: boolean;
  /** what the levels came from: Ben's profile, the level solver's default (no profile), or the old rail table */
  readonly source: "profile" | "default" | "metro_rails";
  /** its line_phase (kindAt reads the other line's phase from it, 1108) */
  readonly phase: Phase | null;
  /** its settings the structure guess reads (setOf, 1195): riverRoof for a Metro line's sunk box (sunkBox 1011), rer
   * for an RER line's box, bore and cover (structFor 1210, reqCover 1217). Optional (added by P3): the guess throws
   * where it needs one that is missing. */
  readonly settings: Pick<PortSettings, "elevAbove" | "coverBelow" | "deepBelow" | "deckDepth"> &
    Partial<Pick<PortSettings, "riverRoof" | "rer">>;
  /** its clear height in the open (openTop 1200): literal.OPEN_CLEAR.rer on the RER; on the Metro the record's
   * open_clear_height, as this line's tables have it when absent (added by P3) */
  readonly open_clear_m?: number;
  /** its solved type and structure at the crossing, when the hub has solved it */
  readonly solved?: { readonly type: Type; readonly structure: Structure; readonly rail: number } | null;
}

/** approach_extra (hub params/approach_extra): a straight after a platform or box end where no arc fits (1293). */
export interface ApproachExtra {
  readonly station: string | null;
  readonly side: number;
  readonly c: number;
  readonly extra: number;
}

/** One platform as the solve reads it, in station order, removed ones included (StationInput.platforms, plus). */
export interface PortPlatform {
  readonly platform_id: string;
  /** name, or name#index where a name repeats (keyOf, 718) */
  readonly key: string;
  readonly name: string;
  readonly order: number;
  readonly point_c: number;
  readonly side: "side" | "island";
  readonly year: number | null;
  readonly yearPhase: Phase | null;
  /** another Metro line already open here when this one opens (platDef, 1584) */
  readonly transferAtOpen: boolean;
  /** RER: a station on a drawn trunk defaults to under */
  readonly trunk: boolean;
  /** false where no record sets the side (the solve's platform default decides it, platKind 1584); default true
   * (added by the integration: the halls read it) */
  readonly sideSet?: boolean;
  /** any other line of the station's complex already open when this one opens (stationAccess 507: atOpen, any
   * system); added by the integration for the halls */
  readonly interchangeAtOpen?: boolean;
}

/** The profile's fields as the record holds them, keyed by platform id where the page keyed by station key. */
export interface PortDoc {
  readonly st: Readonly<Record<string, number | null>>;
  readonly sg: Readonly<Record<string, number>>;
  readonly so: Readonly<Record<string, number>>;
  readonly del: readonly string[];
  readonly pvi: readonly (readonly [c: number, z: number])[];
  readonly ovr: readonly Range3[];
  readonly stt: Readonly<Record<string, string>>;
  readonly tf: readonly Range3[];
  readonly shafts: readonly number[];
  readonly gnd: readonly (readonly (readonly [c: number, z: number])[])[];
  readonly gapfill: readonly string[];
  readonly mode: Readonly<Record<string, "under" | "surface">>;
  readonly ready: boolean;
  /** The frame the profile was saved in: its route length and each platform's point (reframeDoc, 1839). */
  readonly frame: { readonly length_m: number; readonly point_c: Readonly<Record<string, number>> } | null;
}

/**
 * The input of the port (contract section_solve_input/0 when it is a method; plan section 3). Everything the
 * page read from S, records and globals for one line, resolved by Python; the engine reads nothing else.
 */
export interface PortInput {
  readonly section_id: string;
  readonly route: string;
  readonly system: "metro" | "rer" | "cvx";
  readonly length: number;
  readonly step: number;
  readonly path: readonly PathPoint[];
  readonly pieces: readonly { readonly name: string; readonly c0: number; readonly c1: number }[];
  /** ground_profile: the surveyed ground on the grid (NaN where none), single precision */
  readonly dem: Float32Array;
  readonly platforms: readonly PortPlatform[];
  readonly doc: PortDoc | null;
  readonly settings: PortSettings;
  readonly literals: PortLiterals;
  readonly structure: StructureParams | null;
  readonly era: Era | null;
  readonly canon: CanonRecord;
  readonly rivers: readonly RiverRecord[];
  readonly context: ContextRecord;
  readonly crossings: readonly CrossingRecord[];
  readonly neighbours: Readonly<Record<string, Neighbour>>;
  /** The Chronology segments along the line (chrSegments, 1077), by live station. */
  readonly chronology: readonly ChrSegment[];
  readonly approachExtra: readonly ApproachExtra[];
  /** Ben's access choice by platform id (profile.access: its type), for the halls (stationAccess 504); added by the
   * integration */
  readonly access?: Readonly<Record<string, string>>;
  /** The Chronology's entries for this line (segments by key, the phase of each year range), so the segments follow
   * the live stations of a draft (chrSegments 1077: a station removed or slid moves them); absent, `chronology` is
   * used as given. Added by the integration. */
  readonly chronologyTable?: ChronologyTable;
}

/** The Chronology record's part a line reads (chronology.segments, phase_years). */
export interface ChronologyTable {
  /** the key's system part: metro (keys metro|route|a|b), cvx or tri (sys|a|b) */
  readonly sys: string;
  readonly segments: Readonly<
    Record<string, { readonly year?: number | string | null; readonly phase?: string | null }>
  >;
  readonly phase_years: readonly (readonly [number, number, string])[];
}

// ------------------------------------------------------------------------------------------- the normalised model

/** A Chronology segment by chainage (chrSegments, 1077). */
export interface ChrSegment {
  readonly key: string;
  readonly c0: number;
  readonly c1: number;
  readonly year: number | null;
  readonly phase: Phase | null;
  readonly set: boolean;
}

/** A live station: in order, deleted ones out, slid (deriveStations, 720). */
export interface LiveStation {
  readonly index: number;
  readonly platform_id: string;
  readonly key: string;
  readonly name: string;
  /** the drawn point (c0 on the page) */
  readonly point_c: number;
  /** the platform centre: point plus slide */
  readonly c: number;
  readonly side: "side" | "island";
  readonly year: number | null;
  readonly transferAtOpen: boolean;
  readonly trunk: boolean;
}

/** The page's S.align: the profile as arrays by live station index, after alignFromDoc, locks and junction PVIs. */
export interface Align {
  readonly st: readonly number[];
  readonly sg: readonly number[];
  readonly so: readonly number[];
  readonly del: readonly string[];
  readonly pvi: readonly { readonly c: number; readonly z: number }[];
  readonly ovr: readonly Range3<Type>[];
  readonly stt: readonly (SelectedType | "")[];
  readonly tf: readonly Range3<TubeForm>[];
  readonly shafts: readonly number[];
  readonly gnd: readonly (readonly { readonly c: number; readonly z: number }[])[];
  readonly gapfill: readonly string[];
  readonly mode?: readonly ("under" | "surface")[];
  readonly ready: boolean;
}

/** The rail: the existing vertical design (src/vertical) and its arrays on the grid. */
export interface RailModel {
  readonly design: Design;
  /** rail level at c_i */
  readonly z: Float64Array;
  /** grade at c_i, per mille */
  readonly grade: Float64Array;
}

// ------------------------------------------------------------------------------------------------- P2 outputs

/** The ground layers on the grid (636-712): each layer the one under it changed. Float32, as the page. */
export interface GroundLayers {
  readonly step: number;
  /** the surveyed ground (ground_dm / 10) */
  readonly dem: Float32Array;
  /** dem with the Deck's add runs added and cap runs held (regradeGround, 649) */
  readonly regraded: Float32Array;
  /** regraded with other lines' drawn ground across their street, then this line's drawn lines (drawnGround, 686) */
  readonly finished: Float32Array;
  /** the pool over rivers, else finished (surfaceAt, 706), on the grid; Float64 as the page's pool is (P2) */
  readonly surface: Float64Array;
  /** the canon bed under a river with one, else finished (bedAt, 710), on the grid; Float64 as the page's bed is */
  readonly bed: Float64Array;
  /** the drawn lines, normalised (ends on the regraded ground, normGnd 672) */
  readonly lines: readonly (readonly { readonly c: number; readonly z: number }[])[];
  /** other lines' drawn ground across this line (crossGround, 674) */
  readonly cross: readonly CrossGround[];
}

export interface CrossGround {
  readonly c0: number;
  readonly c1: number;
  readonly z: number;
  readonly wid: string;
  readonly with: string;
  readonly street: string | null;
  readonly w: number;
}

/** The sunk box (sunkBox, 1007): rail to underside and to roof top. */
export interface SunkBox {
  readonly below: number;
  readonly top: number;
  readonly inside: number;
  readonly spacing: number;
}

/** A river with its band (riverBand, 1017) or its bridge (riverBridges, 993). */
export interface RiverModel {
  readonly name: string;
  readonly c0: number;
  readonly c1: number;
  /** the canon bed level, or null where the bed is the ground (bedOf, 709) */
  readonly bed: number | null;
  readonly navigable: boolean;
  /** an RER river range along the covered way: the shore, not a crossing (alongShore, 1015) */
  readonly alongShore: boolean;
  readonly bridge: BridgeRecord | null;
  /** the sunk box band; null where bridged, along the shore, or no point is under water */
  readonly band: {
    readonly ub: number;
    readonly lb: number;
    readonly low: number;
    readonly nav: number | null;
  } | null;
  /** a canon bridge that is not fixed: the rail held at lb = ub = pool + clear + deck */
  readonly bridgeBand: { readonly lb: number; readonly ub: number } | null;
}

/** A canon section by chainage (buildCanon, 883-888). */
export interface CanonSection {
  readonly m: MethodSection;
  readonly lo: number;
  readonly hi: number;
  readonly a: string;
  readonly b: string;
  readonly src: string;
}

/** A locked stretch by chainage, decks included (buildCanon 896-907). */
export interface Lock extends LockRecord {
  readonly lo: number;
  readonly hi: number;
}

/** The canon resolved on the live stations (buildCanon, 876): what canonAt, lockAt, refAt and the levels read. */
export interface CanonModel {
  /** later entries win where sections overlap (canonAt searches from the end) */
  readonly sections: readonly CanonSection[];
  /** by live station index */
  readonly fixed: Readonly<Record<number, FixedLevel>>;
  readonly modes: Readonly<Record<number, "under" | "surface">>;
  readonly locks: readonly Lock[];
  /** the bridge piers by chainage (canonPiers), for the viaduct spans */
  readonly piers: readonly number[];
  /** per sample: the canon section index, -1 for none */
  readonly sectionAt: Int16Array;
  /** per sample: the lock index (lo - 0.5 to hi + 0.5), -1 for none */
  readonly lockAt: Int16Array;
}

/** A viaduct span (viaductSpansNow, 954). */
export interface ViaductSpan {
  readonly c0: number;
  readonly c1: number;
  readonly L: number;
  readonly truss: boolean;
  /** rail to soffit */
  readonly below: number;
  /** rail to truss top (0 for a girder) */
  readonly above: number;
  readonly ends: readonly [boolean, boolean];
}

// ------------------------------------------------------------------------------------------------- P1 outputs

/** A structure at the rail (structFor, 1202): rail to underside and to top, and the cover a tube needs. */
export interface Structure {
  readonly k: "elevated" | "atgrade" | "trough" | "box" | "tube" | "bore" | "sunk";
  readonly below: number;
  readonly top: number;
  /** outside diameter of a bored tube (its cover, reqCover 1215) */
  readonly od?: number;
  readonly tube?: TubeKey;
}

/** The structure record as the four structures the page keeps (METRO_ST after applyMS, 1052-1071). */
export interface StructureTables {
  readonly box: Structure;
  /** type A, the twin tube to Phase 2 */
  readonly tube: Structure;
  /** type C */
  readonly tubeC: Structure;
  readonly bore: Structure;
  /** rail to the underside of a structure over a line in the open (OPEN_CLEAR, the record's open_clear_height) */
  readonly openClear: number;
}

/** The phase's rules at a chainage (phaseRules, 1239). */
export interface PhaseRules {
  readonly ccMax: number;
  readonly minDrive: number;
  readonly deepFrom: number;
  readonly tbm: boolean;
}

/** pointType (1246): one chainage on its own, the type or a Metro tunnel class. */
export type PointType =
  | { readonly t: Type; readonly stn?: boolean }
  | {
      readonly cls: PointClass;
      readonly d: number;
      readonly deep: boolean;
      readonly ph: Phase;
      readonly R: PhaseRules;
      readonly shieldFrom: number;
    };

/** gradeLimitAt (1142): the limit, a warning limit above it, and why, as data. */
export interface GradeLimit {
  readonly lim: number;
  readonly warn: number | null;
  /** straight_underground | straight_open | straight | curve_long | curve, for the sheet to word */
  readonly why: "straight_underground" | "straight_open" | "straight" | "curve_long" | "curve" | "rer";
  readonly phase: Phase | null;
  /** the train-averaged radius, Infinity on a straight */
  readonly R: number;
}

/** A station approach box (approachAt, 1431-1447). */
export interface Approach {
  readonly station: string | null;
  readonly kind: "side" | "island" | "box" | "river";
  readonly river?: string;
  /** -1 or 1: the side of the anchor the approach runs to */
  readonly side: number;
  /** per track, m (tube spacing less the anchor's, halved) */
  readonly shift: number;
  /** where it starts: the platform end, river edge or box end */
  readonly c: number;
  /** rounded to the cm, as the page */
  readonly len: number;
}

/** An unbuildable stretch as drawn (bad, 1558-1572). */
export interface Unbuildable {
  readonly why: "cover" | "box" | "roof";
  readonly c0: number;
  readonly c1: number;
  /** the most it is short, m */
  readonly worst: number;
}

/** A paint or selection that cannot be built (paintMisfits, 1637). */
export interface Misfit {
  readonly c0: number;
  readonly c1: number;
  readonly t: Type;
  readonly why: "roof" | "above" | "high" | "cover" | "dig" | "buried";
  readonly worst: number;
  /** the live station index for a station selection */
  readonly si?: number;
}

/** A stretch's decision (one Tunnel method note per stretch, 1520), as data. */
export interface Stretch {
  readonly c0: number;
  readonly c1: number;
  readonly a: number;
  readonly b: number;
  readonly phase: Phase;
  readonly method: "box" | "bored";
  /** why, as a reason slug the sheet words, with its rule id */
  readonly why: string;
  readonly rule: RuleId;
  readonly cls: Type | null;
  readonly form: TubeForm;
  /** how far the launch boxes carry on at each end, m */
  readonly boxes: readonly [number, number];
  readonly from: AnchorRef;
  readonly to: AnchorRef;
}

/** What a stretch runs from or to, for the note (name, 1462). */
export type AnchorRef =
  | { readonly kind: "end" }
  | { readonly kind: "station"; readonly station: string }
  | { readonly kind: "river"; readonly river: string }
  | { readonly kind: "shaft" | "portal" | "box" };

/** The structure solve of one line (stretchTypes/solveTypes, 1335-1604), arrays on the grid. */
export interface TypeSolve {
  readonly grid: Grid;
  /** the solved type of each sample (TYPE_CODES) */
  readonly type: Codes;
  /** the solved rail the types are for (typeAt reads type only within autoTypeRailTol of it) */
  readonly z: Float64Array;
  /** the bored tube of each sample (shield or deep, not a station), else null */
  readonly tube: CodedArray<TubeKey | null>;
  readonly part: CodedArray<Part>;
  readonly phase: CodedArray<Phase>;
  readonly role: CodedArray<Role>;
  readonly bad: readonly Unbuildable[];
  readonly approaches: readonly Approach[];
  /** by station key: the computed default platform type (platDef, 1574-1600) */
  readonly platDef: Readonly<Record<string, "side" | "island">>;
  /** by station key */
  readonly stRole: Readonly<Record<string, StationRole>>;
  readonly shafts: readonly number[];
  readonly stretches: readonly Stretch[];
  /** every finding of the solve (Tunnel method, Painted, Tube form, Approach box, Low cover), deduplicated */
  readonly flags: readonly PortFlag[];
}

// ------------------------------------------------------------------------------------------------- P3 outputs

/** A crossing with the other line (crossingClearancesNow, 2235). */
export interface CrossingClearance {
  readonly c: number;
  readonly wid: string;
  readonly with: string;
  readonly oc: number;
  /** the other line's rail at oc, null when it has no levels */
  readonly zo: number | null;
  readonly z: number;
  readonly clear: number | null;
  readonly need: number | null;
  readonly meUp: boolean;
  /** this line's structure at c (with the hall over a box, hallAt 536) */
  readonly t: Structure;
  /** the other line's structure (kindAt 2197, or its solved structure) */
  readonly to: Structure | null;
  readonly level: boolean;
  readonly ok: boolean;
  /** the other line is not marked set: listed apart (network.profile_set.crossings_apart) */
  readonly pending: boolean;
  readonly source: Neighbour["source"] | null;
  /** the live station whose hall over the box the check ran over, when it did (hallAt 536; added by P3) */
  readonly hall?: number;
  /** the rule that decided the check (added by P3; CROSSINGS_RULES) */
  readonly rule?: RuleId;
}

/** A context block against this line at its worst point (contextClearancesNow, 2219). */
export interface ContextClearance {
  readonly block: number;
  readonly c: number;
  readonly zo: number;
  readonly z: number;
  readonly clear: number;
  readonly need: number;
  readonly meUp: boolean;
  readonly t: Structure;
  readonly to: { readonly k: string; readonly below: number; readonly top: number };
  readonly level: boolean;
  readonly short: number;
  readonly ok: boolean;
  /** the rule that decided the check (added by P3; CROSSINGS_RULES) */
  readonly rule?: RuleId;
}

/** A road check (roadChecksNow, 2263). */
export interface RoadCheck {
  readonly kind: "level_crossing" | "trough_under_road" | "clearance_over_road" | "pier_in_road";
  readonly sev: Sev;
  readonly c: number;
  /** index into the context's roads */
  readonly road: number;
  readonly clear?: number;
  readonly need?: number;
  readonly truss?: boolean;
  /** the rule of the check (added by P3; CROSSINGS_RULES) */
  readonly rule?: RuleId;
}

/** What a station is under (stationStreet, 458). */
export interface StationStreet {
  /** index into the context's streets, or -1 */
  readonly street: number;
  readonly subway: boolean;
  /** indexes into the context's roads crossing the platform */
  readonly roads: readonly number[];
  readonly known: boolean;
}

// ------------------------------------------------------------------------------------------------- P4 outputs

/** An engine finding, as data with its rule id (flags as data, 2.1.17). The sheet words it. */
export interface PortFlag {
  /** a stable slug: grade_over_limit, cover_short, sunk_box_high, mined_in_box_stretch, ... (plan section 5) */
  readonly kind: string;
  /** the page's issue kind it answers (Grade, Cover, Tunnel method, ...), for the parity report */
  readonly page: string;
  readonly sev: Sev;
  readonly c0: number;
  readonly c1: number;
  /** where the marker goes (the page's c) */
  readonly c: number;
  readonly rule: RuleId;
  readonly data: Readonly<Record<string, unknown>>;
  /** Lower or Raise the rail over c0..c1 (regradeDrive) */
  readonly fix?: { readonly mode: "lower" | "raise"; readonly c0: number; readonly c1: number };
  /** Propose fill over c0..c1 */
  readonly propose?: { readonly c0: number; readonly c1: number };
  /** Clear the paint or selection */
  readonly clear?: { readonly c0: number; readonly c1: number; readonly si?: number };
  /** listed apart: a crossing with a line not set */
  readonly pending?: boolean;
}

/** A grade over the limit between two bends (computeSummary 1914-1919). */
export interface GradeOver {
  readonly c0: number;
  readonly c1: number;
  readonly g: number;
  readonly limit: GradeLimit;
  readonly sustained: { readonly avg: number; readonly at: number; readonly W: number };
  readonly sev: "local" | "straight" | "error";
}

/** computeSummary (1900), the numbers only. */
export interface Summary {
  /** metres of each type, on 10 m bins */
  readonly len: Readonly<Record<Type, number>>;
  readonly deepest: { readonly d: number; readonly c: number };
  readonly highest: { readonly h: number; readonly c: number };
  readonly maxG: number;
  readonly maxGc: number;
  readonly over: readonly GradeOver[];
  readonly sumps: number;
  readonly deepShallow: readonly { readonly station: number; readonly c: number; readonly d: number }[];
}

/** The level solver's answer for a line (defaultAlign, 1756): station levels and the river bend points. */
export interface LevelSolution {
  readonly st: readonly number[];
  readonly pvi: readonly { readonly c: number; readonly z: number }[];
  /** stations the solver had no bound for (the page wrote 0 m; here flagged, never 0) */
  readonly unset: readonly number[];
  readonly flags: readonly PortFlag[];
}

/** reframeDoc (1839): a saved profile mapped from the frame it was saved in. */
export interface Reframe {
  readonly changed: boolean;
  readonly doc: PortDoc;
}

/** Propose fill (proposeFill 1684, the pure part): the drawn line to add and the lines it replaces. */
export interface FillProposal {
  readonly c0: number;
  readonly c1: number;
  /** null when there is nothing to fill (the structure has its cover) */
  readonly line: readonly { readonly c: number; readonly z: number }[] | null;
  /** indexes of this line's drawn lines it replaces */
  readonly replaces: readonly number[];
  readonly top: number;
}

/**
 * What the port adds to a solved section (contract solved_section/0 when it is a method; plan section 4): the
 * arrays the sheet draws and the findings it lists.
 */
export interface PortSolved {
  readonly grid: Grid;
  readonly align: Align;
  readonly stations: readonly LiveStation[];
  readonly rail: RailModel;
  readonly ground: GroundLayers;
  readonly types: TypeSolve;
  /** structure at the rail per sample (structFor of the type): underside and top levels, for the outline */
  readonly structBelow: Float32Array;
  readonly structTop: Float32Array;
  /** the legal band (2525-2532): the shallowest a tube may run and the deepest a box may go, NaN where open */
  readonly limitTube: Float32Array;
  readonly limitBox: Float32Array;
  /** the made-up bed over a sunk box roof (madeBedAt, 1032), NaN elsewhere; Float64, as the page's (P2) */
  readonly madeBed: Float64Array;
  readonly gradeLimit: { readonly lim: Float32Array; readonly warn: Float32Array };
  readonly radii: Float32Array;
  readonly allowance: Float32Array;
  readonly rivers: readonly RiverModel[];
  readonly canon: CanonModel;
  readonly spans: readonly ViaductSpan[];
  readonly misfits: readonly Misfit[];
  readonly crossings: readonly CrossingClearance[];
  readonly context: readonly ContextClearance[];
  readonly roads: readonly RoadCheck[];
  readonly streets: readonly StationStreet[];
  readonly summary: Summary;
  readonly flags: readonly PortFlag[];
  readonly levels: LevelSolution;
}

// ---------------------------------------------------------------------------------- the model each package reads

/** What every package reads: the input normalised, before the type solve (built by P2 and P4's alignFromDoc). */
export interface SectionModel {
  readonly input: PortInput;
  readonly grid: Grid;
  readonly settings: PortSettings;
  readonly literals: PortLiterals;
  readonly structure: StructureParams | null;
  readonly stations: readonly LiveStation[];
  readonly align: Align;
  readonly rail: RailModel;
  readonly ground: GroundLayers;
  readonly rivers: readonly RiverModel[];
  /** per sample: the river index, -1 for none (riverAt, 705) */
  readonly riverAt: Int16Array;
  readonly canon: CanonModel;
  readonly sunk: SunkBox;
  /** the paints as the solver reads them (effOvr, 837): inside each platform only the station's selection */
  readonly effOvr: readonly Range3<Type>[];
  readonly chronology: readonly ChrSegment[];
  /** applyMS of the structure record; null off the Metro */
  readonly tables: StructureTables | null;
  /** plan radius and curve allowance on their 10 m grid (radii 1952, curveAllowance 1975), from the path alone */
  readonly curve: { readonly step: number; readonly radii: Float32Array; readonly allowance: Float32Array };
  /** the halls on the box roofs (stationAccess halls, hallAt 536), from station.facts: cover and crossings read them */
  readonly halls: readonly HallSpan[];
}

/** A hall over a box station (stationAccess 528-531): its chainage range and its roof top level. */
export interface HallSpan {
  readonly station: number;
  readonly c0: number;
  readonly c1: number;
  readonly top: number;
}

/** What the level solver reads (defaultAlign runs before the rail exists): the model less the rail and the align. */
export type LevelModel = Pick<
  SectionModel,
  | "input"
  | "grid"
  | "settings"
  | "literals"
  | "structure"
  | "tables"
  | "stations"
  | "ground"
  | "rivers"
  | "riverAt"
  | "canon"
  | "sunk"
>;

/** A node of the level solver besides the stations: a river bank or an extra bound (defaultAlign 1781-1789). */
export interface LevelNode {
  readonly c: number;
  readonly ub: number;
  readonly lb: number;
}

/** A stretch where grade plus curve allowance passes the limit (curveGradeRangesNow, 1987). */
export interface CurveGradeRange {
  readonly c0: number;
  readonly c1: number;
  readonly worst: number;
  readonly g: number;
  readonly add: number;
  readonly limit: GradeLimit;
  readonly sustained: { readonly avg: number; readonly at: number; readonly W: number };
  readonly isSustained: boolean;
}

/** Everything allIssues (2143) gathers, each from the package that computes it. */
export interface IssueParts {
  readonly over: readonly GradeOver[];
  readonly crossings: readonly CrossingClearance[];
  readonly context: readonly ContextClearance[];
  readonly rivers: readonly PortFlag[];
  readonly roads: readonly RoadCheck[];
  /** the station flags of station.facts (access, platform grade, curve, slide, overlap) */
  readonly stations: readonly PortFlag[];
  readonly deepShallow: Summary["deepShallow"];
  readonly checks: readonly PortFlag[];
  readonly ground: readonly PortFlag[];
  readonly types: TypeSolve;
  readonly misfits: readonly Misfit[];
}

/** The functions alignFromDoc (1869) calls in other packages, passed in so P4 builds alone. */
export interface AlignDeps {
  sttFromDoc(doc: PortDoc | null, stations: readonly LiveStation[], ovr: readonly Range3[]): (SelectedType | "")[];
  buildCanon(input: PortInput, stations: readonly LiveStation[], grid: Grid): CanonModel;
  rebuildGround(input: PortInput, gnd: Align["gnd"], rivers: readonly RiverRecord[]): GroundLayers;
  riverModels(input: PortInput, ground: GroundLayers, canon: CanonModel, sunk: SunkBox): RiverModel[];
  sunkBox(input: PortInput): SunkBox;
  applyLocks(align: Align, canon: CanonModel, stations: readonly LiveStation[]): { align: Align; changed: boolean };
}

/** The model after the type solve: what P3 and P4 read. */
export interface TypedModel extends SectionModel {
  readonly types: TypeSolve;
  readonly spans: readonly ViaductSpan[];
}

// ------------------------------------------------------------------------- module interfaces (for stand-ins)

/** P1's functions other packages call at a chainage off the grid. */
export interface TypesModule {
  typeAt(m: TypedModel, c: number, z?: number): Type;
  structFor(m: SectionModel, t: Type, c: number, tube?: TubeKey | null): Structure;
  reqCover(m: SectionModel, s: Structure): number;
  phaseAt(m: SectionModel, c: number): Phase;
  phaseRules(m: SectionModel, c: number, ph?: Phase): PhaseRules;
  gradeLimitAt(m: TypedModel, c: number): GradeLimit;
  tubeKeyAt(m: TypedModel, c: number): TubeKey | null;
}

/** P2's functions other packages call. */
export interface GroundModule {
  sampleGround(g: Float32Array, step: number, c: number): number;
  riverIndex(m: SectionModel, c: number): number;
  canonAt(m: SectionModel, c: number): CanonSection | null;
  lockAt(m: SectionModel, c: number): Lock | null;
  madeBedAt(m: TypedModel, c: number, z: number): number;
  viaductSpans(m: SectionModel, types: TypeSolve): ViaductSpan[];
}

/** P3's functions P4 calls. */
export interface CrossingsModule {
  crossings(m: TypedModel): CrossingClearance[];
  context(m: TypedModel): ContextClearance[];
  roadChecks(m: TypedModel): RoadCheck[];
  stationStreet(m: SectionModel, s: LiveStation): StationStreet;
}
