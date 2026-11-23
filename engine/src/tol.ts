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

// ------------------------------------------------------------------ the port, P1 types (src/port/structure/)
// The page's tolerances and sampling steps of the structure solver and type lookup (profiles.html 1063-1676). The
// values Ben rules on come in PortInput.literals and .structure; the ones marked "No param" are design values the
// registry does not have yet, reported to the lead (claude/hub_maps/engine_port_plan.md, section 3.4).

/** A point this far or more from its platform centre takes the centre's type (pointType, 1248). */
export const PORT_STATION_POINT_M = 1e-6;

/** Chainage slack of the solver's comparisons: within the cut-and-cover limit (1366), the approach run (1443-1444),
 * a sliver a box can take (1530), a paint run's next sample (1653). */
export const PORT_CHAINAGE_EPS_M = 1e-6;

/** A tube has its cover within this (holds 1474, the bore's cover 1424, a drive's hard cover 1486, 1552). */
export const PORT_COVER_TOL_M = 0.005;

/** Two track spacings, a box and its street, differ by more than this (1440, 1543, 1549). */
export const PORT_SPACING_TOL_M = 0.01;

/** Unbuildable runs of one kind this close are one stretch (bad, 1567). */
export const PORT_BAD_JOIN_M = 10;

/** The approach box street check samples every this many metres (1542). */
export const PORT_APPROACH_CHECK_STEP_M = 10;

/** No param: an approach box is checked against the streets only with a Deck street within this (1540). */
export const PORT_APPROACH_STREET_SEARCH_M = 300;

/** A drawn piece reaches this far past its ends (pieceAt, 2059). */
export const PORT_PIECE_PAD_M = 5;

/** No param: a tube wider inside than this is the double-track bore (tubeOf, 1063). */
export const TUBE_IS_BORE_INSIDE_M = 7;

/** gradeLimitOver samples every this many metres, from this far in (1159). */
export const PORT_GRADE_LIMIT_STEP_M = 10;
export const PORT_GRADE_LIMIT_FIRST_M = 5;

/** sustainedGrade's window step and its inner step with the curve allowance (1168, 1175). */
export const PORT_SUSTAINED_STEP_M = 5;
export const PORT_SUSTAINED_INNER_M = 10;

/** A sustained grade within this of a limit is not over it (gradeSeverity, 1181), per mille. */
export const PORT_GRADE_SEV_TOL = 0.05;

/** The approach box street check runs to this past the approach's far end (1542). */
export const PORT_APPROACH_END_SLACK_M = 0.01;

/** No param: an approach_extra entry without a station matches an approach starting within this (approachExtra,
 * 1293). */
export const PORT_APPROACH_EXTRA_MATCH_M = 20;

/** A reverse curve of radius R shifting the track by s needs sqrt(4 R s) (approachLen, 1294). Geometry, not a rule. */
export const PORT_REVERSE_CURVE_FACTOR = 4;

/** A locked stretch reaches this past its ends (lockAt, 911). */
export const PORT_LOCK_PAD_M = 0.5;

/** absorbShort's passes (1302). */
export const PORT_ABSORB_PASSES = 4;

// ------------------------------------------------------- the port, P2 ground, rivers, viaducts, canon (src/port/ground/)
// The page's tolerances and sampling steps of the ground layers, rivers, viaducts and canon (profiles.html 636-1041). The
// values Ben rules on come in PortInput.literals, .settings and .structure; the ones marked "No param" are design values
// the registry does not have yet, reported to the lead (claude/hub_maps/engine_port_plan.md, section 3.4).

/** A drawn ground line this short or shorter is dropped (parseGnd, 670). */
export const PORT_GND_MIN_LEN_M = 1;

/** chainLL's default reach: a lon/lat further than this from the path has no chainage (866). */
export const PORT_CHAINLL_TOL_M = 30;

/** chainLL's floor on a zero-length segment's squared length, m squared (870). */
export const PORT_CHAINLL_L2_MIN = 1e-9;

/** A deck's bend points are rounded to this many per metre, a tenth (buildCanon, 898). */
export const PORT_DECK_PVI_PER_M = 10;

/** Viaduct piers are rounded to this many per metre, a tenth (viaductSpansNow, 983). */
export const PORT_VIA_PIER_PER_M = 10;

/** An elevated run shorter than this has no spans (960). */
export const PORT_VIA_RUN_MIN_M = 1;

/** No param: a canon bridge's own piers count within this of the river range (972). */
export const PORT_VIA_PIER_SEARCH_M = 400;

/** A canon bridge's pier counts only this far past the last pier placed (972); a pier this far on is a new one, and a
 * span this short is none (981, 985). */
export const PORT_VIA_SPAN_MIN_M = 0.5;

/** A bank pier is placed only this far past the last pier (975). */
export const PORT_VIA_BANK_GAP_M = 1;

/** No param: a pier goes before a crossing or road (else after it) when the gap is over this many VIA_SPANs and the
 * crossing starts this far on (979). */
export const PORT_VIA_BEFORE_SPANS = 1.6;
export const PORT_VIA_BEFORE_MIN_M = 3;

// ------------------------------------------------------------------ the port, P3 crossings (src/port/crossings/)
// The page's tolerances of the crossing, context and road checks (profiles.html 2182-2275). The design values come in
// PortInput.literals, .settings, .structure and the neighbours; the one marked "No param" is a design value the
// registry does not have yet, reported to the lead (claude/hub_maps/engine_port_plan.md, section 3.4).

/** A crossing is clear within this of its need (crossingClearancesNow 2244), a context block too (2232). */
export const PORT_CLEARANCE_TOL_M = 0.05;

/** No param: a line in the open within this of a context track at grade or in a trough is a level clash (2229). */
export const PORT_CONTEXT_LEVEL_M = 1;

/** A road check passes within this of its need: the trough's bridge (2269), the clearance over a road (2270). */
export const PORT_ROAD_TOL_M = 0.02;

/** A viaduct pier stands in a road when it is this far inside the road's edges (2272). */
export const PORT_PIER_ROAD_INSET_M = 0.5;

// ------------------------------------------------- the port, P4 checks and levels (src/port/checks/, src/port/levels/)
// The page's tolerances, sampling steps and roundings of the summary, the design checks, the issues, Propose fill and
// the level solver (profiles.html 1684-2178). The values Ben rules on come in PortInput.settings and .literals; the
// ones marked "No param" are design values the registry does not have yet, reported to the lead
// (claude/hub_maps/engine_port_plan.md, section 3.4).

/** The 10 m check grid: the summary's bins (1903), the curve grade (1989) and cover samples (2118), from 5 m. */
export const PORT_CHECK_STEP_M = 10;
export const PORT_CHECK_FIRST_M = 5;

/** Two flagged samples of the 10 m grid join into one range within this (1995, 2116). */
export const PORT_CHECK_JOIN_M = 20;

/** A curve allowance under this (per mille) is no curve for the curve grade check (1992). */
export const PORT_CURVE_ADD_MIN = 0.5;

/** curveAllowance's half window in samples is the platform over this (1977: a train length on the 10 m grid). */
export const PORT_ALLOWANCE_WINDOW_DIV_M = 20;

/** Three points of the radii circle closer to a line than this (twice the area, m^2) are straight (1966). */
export const PORT_RADII_AREA_MIN = 1e-6;

/** A drawn ground's end slope passes within this of fillSlope, per mille (1737). */
export const PORT_GND_SLOPE_TOL = 0.5;

/** A drawn ground line shorter than this many points has no sustained stretch between its end slopes (1741). */
export const PORT_GND_SUSTAIN_MIN_POINTS = 4;

/** Two design vertices this close in level make a platform transition chord (designChecks 2083). */
export const PORT_LEVEL_EQ_M = 1e-9;

/** No param: a chord flatter than this (per mille) has no sign for the sumps (2112). */
export const PORT_SUMP_FLAT = 0.5;

/** River check samples join within this many grid steps (computeSummary 1925). */
export const PORT_RIVER_JOIN_STEPS = 1.5;

/** Metres to the decimetre, centimetre and millimetre: the roundings of bend points and fill points (1797, 1724). */
export const PORT_DM_PER_M = 10;
export const PORT_MM_PER_M = 1000;

/** serialize()'s derived summary (3227): km of each type, the steepest grade to 0.1 per mille. */
export const M_PER_KM = 1000;
export const PORT_PERMILLE_TENTHS = 10;

/** Propose fill: its side slopes reach the ground within this, per mille over the slope (1716). */
export const PORT_FILL_SLOPE_TOL = 1e-6;

/** Propose fill: the point search gives up this many samples past the last fitting end (1724). */
export const PORT_FILL_SEARCH = 60;

/** Propose fill: the stretch decided by the rules is widened by its slope plus this many samples (1700). */
export const PORT_FILL_MARGIN_SAMPLES = 2;

/** reframeDoc: a station point moved by more than this is a new frame (1849), a slide is kept past it (1864). */
export const PORT_REFRAME_TOL_M = 0.05;

/** surfacePvis (RER): the ground smoothed at this many points per surface step (1813), held to the grade limit in
 * this many passes both ways (1825), and no bend points on a stretch shorter than this many steps (1820). */
export const PORT_SURF_SMOOTH_DIV = 4;
export const PORT_SURF_PASSES = 4;
export const PORT_SURF_MIN_STEPS = 1.5;

/** A saved paint or tube form is [c0, c1, kind]: shorter entries are dropped (alignFromDoc 1890, 1893). */
export const PORT_RANGE3_LEN = 3;

// ------------------------------------------------------------------------------------------------- proposers
// Lower, Raise, Fix unbuildable and Solve levels with crossings (regradeDrive 3601-3660, fixAll 2985-2995,
// solveCross 3693-3720). The page's literals, each named once.

/** Lower / Raise: the margin the rail keeps past its bound (literal.regrade_margin, 3607) when the input carries
 * none, and the grade reserve under the limit (literal.regrade_grade_reserve, 3606) and the least grade it ramps at
 * (3606). */
export const PORT_REGRADE_MARGIN_M = 0.3;
export const PORT_REGRADE_RESERVE_PERMILLE = 2;
export const PORT_REGRADE_MIN_GRADE_PERMILLE = 10;
/** Lower / Raise: at most this many passes, the margin growing by the shortfall plus this each time (3608, 3655). */
export const PORT_REGRADE_PASSES = 4;
export const PORT_REGRADE_MARGIN_STEP_M = 0.1;
/** Lower / Raise: a rail this close to its bound counts as there (3623, 3653), and a station past it by this moves
 * (3632). */
export const PORT_REGRADE_TOL_M = 0.01;
/** Lower / Raise: the bend points run from the platform end this far out (3641), at most this far past the lowered
 * part (3642), no two bends closer than this (3648), a chord kept under the line within this (3651). */
export const PORT_REGRADE_END_PAD_M = 4;
export const PORT_REGRADE_REACH_M = 400;
export const PORT_REGRADE_MIN_BEND_M = 30;
export const PORT_REGRADE_CHORD_TOL_M = 0.05;
/** inPlatform (3142): a platform and this much past each end. */
export const PORT_IN_PLATFORM_PAD_M = 2;
/** Fix unbuildable: at most this many rounds of fixes (2989). */
export const PORT_FIX_ALL_ROUNDS = 3;
/** Solve levels with crossings: a grade past the limit by this, or a held level missed by this, fails (3700, 3701). */
export const PORT_CROSS_TOL = 0.05;
/** The paint review: a paint repeats the rules where they give its type over more than this share (2956). */
export const PORT_PAINT_SAME_SHARE = 0.95;
