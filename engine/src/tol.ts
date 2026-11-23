// Every numeric constant of the engine source, named. Nothing else in src/ may write a number other than 0, 1 or 2
// (test/lint.test.ts holds this, with src/contract/ exempt). A tolerance says what it guards and where the Profiles
// page (data/profile/profiles.html) used the same value, so a port can be checked against the page line by line.

// ------------------------------------------------------------------------------------------------ tolerances (m)

/** Two platforms overlap when one starts more than this before the other ends (vertices, profiles.html 732). */
export const OVERLAP_M = 1e-6;

/** A platform end with a neighbour closer than this has no outward stretch (design outward, profiles.html 758-759). */
export const OUTWARD_MIN_M = 1e-6;

/** A stretch shorter than this carries no transition (design, profiles.html 771). */
export const RUN_MIN_M = 1e-6;

/** A transition shorter than this adds no vertex (design, profiles.html 785-786). */
export const EXT_MIN_M = 1e-6;

/** Two design vertices closer than this have a zero grade between them (design, profiles.html 789). */
export const CHORD_MIN_M = 1e-9;

/** A vertical curve shorter than this is no curve (railAt and gradeAt, profiles.html 810, 822). */
export const CURVE_MIN_M = 1e-6;

/** A curve shortened by more than this is flagged (design short, profiles.html 799). A design rule, not a
 * tolerance: the default of SectionInput.params.short_curve_flag_m, which Python sends once the registry has it. */
export const SHORT_FLAG_M = 0.5;

/** Grid size slack: a length within this of a whole number of steps gets that last point (floating division). */
export const GRID_SLACK = 1e-9;

// --------------------------------------------------------------------------------------------- tolerances (ratio)

/** A change of grade smaller than this (a ratio, 0.01 per mille) gets no vertical curve (design, profiles.html 754). */
export const GRADE_CHANGE_MIN = 1e-5;

// ------------------------------------------------------------------------------------------- counts and factors

/** Passes of the transition solver: each pass re-reads the neighbours' transitions (design, profiles.html 765).
 * The default of SectionInput.params.design_passes. */
export const DESIGN_PASSES = 5;

/** The two transitions on one stretch take at most this share of it (design, profiles.html 778). A design rule:
 * the default of SectionInput.params.transition_share. */
export const TRANSITION_SHARE = 0.5;

/** Per mille in one (grades are ratios inside the engine and per mille in contracts). */
export const PERMILLE = 1000;

// ------------------------------------------------------------------------------------------------ encodings

/** Hex digits: the radix of a sha256 hex digest, and the digits one byte takes. */
export const HEX_RADIX = 16;
export const HEX_DIGITS_PER_BYTE = 2;

// --------------------------------------------------------------------------------------------- processes

/** The exit code of a CLI call whose reply is not ok, and of a sidecar that cannot start. */
export const EXIT_FAILED = 1;

/** The exit code of a CLI called with the wrong arguments. */
export const EXIT_USAGE = 2;

/** How many leading CLI arguments are Node and the script (process.argv). */
export const ARGV_SKIP = 2;

/** A progress line closer than this to the last one sent for its request is dropped (the protocol asks for
 * few progress lines; the engine keeps no clock, so the host thins them by amount). */
export const PROGRESS_STEP = 0.05;

/** Lines of stack kept in an error reply. */
export const STACK_LINES = 12;

// station.facts@1 (src/station/). The values Ben rules on come in the input's params (literal.* and settings.*);
// these are the page's own tolerances and drawing sizes, written once.

/** A limit is broken only past this margin, as the page compares (|sg| > limit + 0.05, slide > 150.05; 2088, 2100). */
export const LIMIT_TOL = 0.05;

/** The access checks' margin (a hall within 0.02 m of D_HALL fits; profiles.html 521-523). */
export const ACCESS_TOL_M = 0.02;

/** Two platforms overlap when their centres are closer than the platform length less this (profiles.html 2101). */
export const OVERLAP_MARGIN_M = 0.5;

/** A street runs this far past its ends when a station is matched to it (streetAtC, profiles.html 452). */
export const STREET_PAD_M = 5;

/** A slide shorter than this is no slide (the card's "(point x)" shows over 0.01 m; profiles.html 3036). */
export const SLIDE_SHOWN_M = 0.01;

/** The crossunder passage at the platform start (profiles.html 531). */
export const PASSAGE_M = 3;

/** Half the shaft of a mined or deep station (profiles.html 531). */
export const SHAFT_HALF_M = 3;

/** A river is bridged when the rail stands this far over normal pool (pool() + 1, profiles.html 1255). */
export const BRIDGE_ABOVE_POOL_M = 1;

/** The page's local plan metres per degree (pathXY and radii, profiles.html 1955, 2009): latitude. */
export const M_PER_DEG_LAT = 110540;

/** The same, longitude at the equator (times cos of the path's first latitude). */
export const M_PER_DEG_LON = 111320;

/** Degrees in half a turn. */
export const DEG_HALF_TURN = 180;

/** A platform span within this of its chord is straight (fitRadius, profiles.html 2016). */
export const STRAIGHT_TOL_M = 0.001;

/** A determinant this small leaves the circle fit undefined (straight). */
export const DET_MIN = 1e-12;

/** Chainage slack of the platform resampling (profiles.html 2033). */
export const SPAN_EPS_M = 1e-9;

/** Chainage slack for a span shorter than a sample (profiles.html 2034). */
export const SPAN_MIN_M = 1e-6;

/** Centimetres in a metre: the page rounds drawn-ground ends and default levels to the centimetre. */
export const CM_PER_M = 100;

/** The fewest points a circle is fitted through (fitRadius, profiles.html 2012). */
export const FIT_MIN_POINTS = 3;

/** r^2 = (D^2 + E^2) / 4 - F for the circle x^2 + y^2 + Dx + Ey + F = 0. */
export const KASA_QUARTER = 4;

/** The outside face's extra gap is car length squared over 8R (the car's middle bulges out; 2036). */
export const OUTSIDE_GAP_DIV = 8;
