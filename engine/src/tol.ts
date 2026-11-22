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
