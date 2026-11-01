# Realism and broken-logic audit (1 November 2026)

Ben: "look over the code for anything that needs to be taken into account for realism and for these types of
broken/incomplete logic." Three readers: the Profiles engine, the tie and record flows, the Python copy and 3D build.
Line numbers are as of commit a43e088.

## A. Ways the system still changes what Ben saved (fix first)

1. **The Profiles page keeps the old route while the tie moves the profile under it.** `profiles.html` alignments
   onSnapshot (2846): the moved profile arrives with its station point moved and `so` relative to the new point, but the
   page's station list (`S.data`, `S.cache`, `LINKS`) was loaded once and never refreshed. The platform appears back at
   the old point; if Ben drags it back and saves, the slide is stored against the old point and the next tie moves it
   again. A real ping-pong, and the most likely cause of "the tie keeps undoing my changes" that remained after today's
   fix. Fix: on the hub's `files` event for profiles, or when the incoming doc's length or station points differ from the
   page's, refetch the route file, links and context, rebuild the stations, clear the undo stack, then apply the doc;
   until refetched, refuse the doc and show a banner.
2. **The deck tie's version check reads the version after the run** (`pipeline.py` job_deck_tie 237-245), so a profile
   saved during the two-minute tie is silently replaced by the moved copy of the older one. Fix: record each profile's
   version in `prepare()` and pass that to the write; on mismatch keep Ben's and re-run.
3. **Saves carry no version** (`hub.py` do_PUT 244; the Profiles and Deck pages PUT whole documents). The Deck page can
   overwrite a platform offset the platform tie just wrote, after which the sync record calls that platform "moved on
   the Deck" and the next tie resets Ben's Profiles slide. Fix: `If-Match` on every PUT, reject on mismatch, merge or
   ask; the Deck page should PATCH only the station entries it changed.
4. **`move_doc` does not move `tf` (tube form) paints** when a route is re-pathed or lengthens (`rer_deck_routes.py`
   453-461); a shortened route collapses bend points past its end onto one chainage with no note.
5. **Slides are clamped to half a platform on load** (`alignFromDoc` 1548; the Deck allows 150 m; the sync record has
   Kenard at -135 m): a larger slide is clamped and the next save moves the centre. One shared limit, never clamp on
   load, flag instead.
6. **The platform tie decides by record age, not by what changed** (`platform_tie.py` 117-121); every run re-pushes
   every non-zero slide; shared stretches (B, C, E on the CVG trunk) carry three slides for one platform and the last
   processed wins. Keep the Profiles slide per platform in the sync record and push only what changed; on both-changed,
   a conflict row for Ben.
7. **The seed merge mixes a record edited on both sides** two levels deep (`store.py` merge_dir 173-253): station
   levels from the seed, bend points from the local copy, a profile nobody designed, reported only in a run log. Treat a
   profile or the layout as one unit: keep local, save the seed copy aside, show it on the hub page.
8. `copyStretch` (374-393) copies a station level onto the other route ignoring its canon-fixed level and copies the
   slide with a sign instead of the centre; `applyLocks` zeroes slides and un-deletes stations inside a lock on every load.
9. `station_types`, `station_platforms`, `approach_extra` and the access records are keyed by bare station name; a line
   with two stations of one name (Line 8 "Cincinnati State") keeps only the second.

## B. Results a designer would call wrong on sight

1. **The launch box swallows boreable ground** (`solveTypes` launch 1324): the end box is carried to the farthest sample
   below half a diameter of cover, through any boreable ground before it. A station box, 800 m at 11 m, then one 10 m
   spot at 7 m: an 810 m box. Stop the launch box at the first run boreable over a drive, and price "carry the box"
   against "drive plus pocket" with the same cost sums.
2. **"Deep" means four things**: the TBM method (TYPES.deep), the access threshold 18.29 m (deep_from), the old depth
   setting (deepBelow, still used by `kindAt` and `pointType`), and the canon's "deep" (drill and blast in rock), which
   comes out drawn as a hand shield. A "Deep bore (TBM)" paint on a 1905 line is accepted. Each sample should carry a
   method (box, hand shield, TBM, drill and blast, immersed), a depth class (stations only) and a tube form; a paint
   whose method the phase did not have is an error.
3. **A Phase 2 mined station sits inside the 9.0 m running bore** (1310-1312): on Lines 8 to 12 a station deeper than
   16.5 m is drawn as the double-track bore with no platforms anywhere (15 stations). A mined station must be its own
   structure (two platform tunnels at the twin spacing, or a cavern), an anchor with its own approaches; `anchorAt`
   reports it as a double-track box today.
4. **A 20 m ground dip inside a tunnel becomes a portal** (1259-1262, MIN_RUN 20): a 30 m gully over a 10 m deep tube
   ends the drive with launch and approach boxes both sides. A train cannot surface in 20 m; at 50 per mille a trough
   needs about 90 m of ramp each side. An open run is a portal only if long enough for the ramps or reaching a station.
5. **Regrade builds bends its vertical curves cannot fit** (regradeDrive 3103-3177): bends 30 m apart, but a sag between
   -48 and +48 per mille on R 1500 needs 144 m and lifts the rail 1.7 m, so the rail is short again, the loop deepens
   the whole drive and "Vertical curve" issues appear. Space bends by the curve lengths and bound the curved rail.
6. **The 3D build's "bored island"** eases Phase 1 type A tubes out to 10.90 m "as part of the station tunnels": a 16 m
   mined cavern on a 1903 hand shield. Phase 1 mined stations are side platforms in separate platform tunnels; islands
   only in boxes or TBM-era caverns.
7. **The CVG Express Ohio bridge** gets 108 m trusses on piers to the bed; the navigable Ohio needs a 250 to 300 m
   channel span. A navigation span rule per canon river.
8. **Terminals have no tail tracks or crossovers**, junctions no structure, no vent shafts on long deep drives, no
   crossover boxes: the engine ends at the last platform.

## C. Silent interactions between rules

1. **Fill makes anything buildable** (`applyFill` 1437): a Shield or Deep paint raises the finished ground to one
   diameter over the tube without limit, and every rule then reads that ground (depths, unbuildable, access, roads,
   Regrade). Cap the fill at a plausible street regrade (a setting, unlimited only on `subway_streets`), flag the
   excess, and keep the surveyed ground for the cover check under a tube.
2. **The cost compares unequal things** (1318-1326): the bored option pays no `switch` at its two ends and nothing for
   the approach boxes it forces; only pockets pay. Charge switch at each drive end that meets a box plus the approach
   metres, and show both totals in the note.
3. **Pockets get station approaches** (approachAt 1282): a working shaft in twin tubes is anchored as a 3.90 m box, so
   the tracks ease in and out over 40 m on the running line. Pockets and launch boxes should keep the tube spacing.
4. **The crossing rule guesses the other line's structure from depth and phase** (`kindAt` 1858), not from its solved
   boxes, approaches or tube form: under a Phase 2 box station at 16 m it demands the twin-tube gap. Read the other
   line's solved type and tube samples (the 3D build already publishes `tube_points`).
5. **One shortfall, three issues**: a treated low-cover stretch gets a note, a "Cover" error and below half a diameter an
   "Unbuildable" error; a hall too shallow gets "Access" and "Box roof above ground"; a Phase 1 station past 12.19 m gets
   "Canon" and "Unbuildable". One owner per condition.
6. **A short leftover converts the whole stretch to cut and cover** (1360), including pockets and the other piece's
   approaches, which stay listed.
7. **The approach straight round-trips through a record** (`approach_extra`): a longer approach can shorten a drive under
   min_drive, which deletes the approach, which deletes the extra, which brings the drive back: a two-state flip whenever
   a drive is within the extra's length of min_drive. Compute the straight in the engine from the plan curvature.
8. **The 3D job's one re-run** only aligns the Deck's island defaults; the platforms and approach extras it writes reach
   the snapshot one run later. Unmatched Deck rings are written as `side` with no provenance, so the editor's own
   fallback never runs.

## D. Hard thresholds with no hysteresis

A 1 cm move flips whole stretches: a station at 12.19 against 12.20 m turns box into mined and changes anchors,
approaches, tube form and access; the bore/twin decision flips the whole drive at 50/50; `allBoxOk` flips a kilometre
when one sample passes cc_max; at-grade / trough / box at 3.0 and 4.6 m and elevated at 3.0 m create portals and piers
(an embankment 3.1 m high is drawn as a viaduct with its girder underground). Round depths to 0.1 m, keep a dead band
(about 0.25 m) inside which the previous solve's decision stands, decide elevated by soffit clearance.

## E. Inputs the rules ignore

Soils and the water table (the basin alluvium is near pool level: boxes need dewatering, shields compressed air; all
methods cost the same per metre); floods (anything over pool + 1 m is a "bridge"; the 1937 crest was about 16 m over
pool; portals and troughs in the floodplain are never checked); horizontal radius on the running line (a 60 m curve
inside a drive is unflagged; `min_radius` only sizes approaches); sags (sumps are a count, Regrade lowers stations into
the sag it makes; drainage ignores troughs); platform grade by line, not by phase; station box width for island against
side as a lookup; stacked tubes (the 28 October ruling) with no representation; the shaft position of a deep station
(drawn at the centre, real ones at an end or beside).

## F. The Python copy against the page, and railsim

Roads over a viaduct: the page uses the span's girder, the copy the deck depth (the copy passes what the page fails by
1.8 m). Hall tops at crossings: page only. Grade limits: the copy's summary counts over a flat 50 per mille. Platform
grade: no check in the copy. Settings: the copy reads the repo's `settings.json` through a key map that has no entries
for rivers, roads, deck depth, fill taper, sustained length or cost, so a hub setting change never reaches railsim. No
viaduct spans in the copy. railsim: the S-ease reverse curves (165 m, no spiral, no cant) and the Deck's plan never reach
the simulator (trains leave every platform at line speed), dwell ignores island against side, interchange and lift
access, a box and a 9 m bore are the same for tunnel drag.

## G. Dead or stale

`pointType` is a second, older engine still reachable through `autoType` and the API; `deepBelow`, `shallowMax`,
`coverBelow` rows look live but feed fallbacks and a duplicate warning; ERA strings describe the pre-record tube;
settings notes say "the deep-tube threshold decides"; `cost.switch` is never charged at a drive's ends.

## Proposed order

1. A1 to A3 (the page refetches the route on a tie; versions on every save; the deck tie's version check), then A4 to A9.
2. B1, B3, B4, C1, C2, C3, C6 and the threshold dead band (D): the engine's remaining wrong-on-sight results.
3. B2 (method, depth class and form as separate fields; the canon's drill and blast), B5 (Regrade's curves), C4 (the
   other line's solved structure at crossings), C5 (one issue per condition), C7 (the approach straight in the engine).
4. B6 to B8 and E: new modelling (mined stations as structures, terminals and crossovers, navigation spans, floods,
   soils, running-line radius, sags), each a ruling from Ben first.
5. F and G.
