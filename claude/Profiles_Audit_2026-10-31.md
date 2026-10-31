# Rail Profiles: audit of the tunnel-type system (31 October 2026)

Ben, after the Benton to Henry Clay screenshot (Line 3): "audit the whole system you have, because there are obviously holes
and faults in whatever it is you're doing, and there has to be a better way of doing it."

## How the system works today

1. Ben draws the rail by hand: station levels, bend points, and paints (structure types over chainage ranges).
2. The engine (`solveTypes` in `data/profile/profiles.html`, copied in `railsim/metro_profile.py`) reads the finished rail and
   decides a structure for every 2 m: box, bored tube (shallow shield or deep), sunk box, open track. Paints override it on
   the drawing.
3. Anything the engine cannot make legal goes into the issues list (30 to 60 errors per line).
4. Station 3D and the Deck read the editor's result through a headless run (`tools/station3d/harness.js`).

## What is wrong, measured over every Metro line (repo data)

| Fault | Where | Size |
|---|---|---|
| A bored tube drawn with less than one diameter of cover | Lines 1, 3, 5, 6, 7, 9, 10, 13, 14, 2b, CVG Express | about 5.9 km |
| A box drawn deeper than its phase's cut-and-cover limit (not an approach) | mostly Lines 3, 6, 11, 2b, 2 | about 3.1 km |
| "Deep tunnel" drawn where the rail is less than 18.29 m down | every line but 13 | about 17.8 km |
| Stretches painted by hand, overriding the engine | Lines 1, 2, 3, 4, 5, 14, 2b | about 18.2 km |
| Errors in the issues list | each line | 6 to 58 |

The same check on Ben's export (pushed 31 October, `hub/seed`): tube without cover 5.0 km, box past its limit 3.6 km, "deep"
under 18.29 m 18.8 km, painted 21.7 km (Lines 1, 2 and 4 about 6 to 7 km each), 4 to 37 errors a line. Benton to Henry Clay
on his Line 3: the drive (type C tubes) climbs from Benton's approach at about 10.8 m down, close to one diameter of cover
(10.85 m), drawn as Deep tunnel; the drawing shows the tube, not the cover it needs, so it reads as running at the surface.

## Root causes

1. **The drawing lies when the profile breaks a rule.** The engine checks a hand-drawn rail after the fact. When no legal
   structure exists (Benton to Henry Clay: about 800 m with too little cover for a tube, too long and too deep for a box), it
   still draws one, a tube, and puts a line in a list of 50. The drawing must never show something that cannot be built.
2. **The rail is free; the rules are checks.** Nothing in the editor shows the band of rail levels where a structure is legal,
   so every edit can break a rule and the only feedback is a flag. The rules should shape the profile, not judge it later.
3. **"Deep tunnel" and "shallow shield" are treated as two structures.** They are the same shield and lining; the depth only
   matters for stations (lifts and escalators). Splitting running tunnels by depth created the "switching in the middle"
   class of faults, and the "one class per drive" fix made 17.8 km of shallow tube read as deep.
4. **Old paints.** About 18 km of paints were made to work round earlier rules. They now override the engine and produce
   conflicts the engine cannot see (Line 1's deep paints over the Ohio bank boxes, Line 4's 13 m shield paint).
5. **I test on stale data.** The repo's saved profiles (`hub/seed/alignments`) date from 27 and 28 October. Ben's hub has
   newer edits, so a fix that checks clean here can still fail on his screen (the Benton approach box shows here, not there).
6. **Fixes were made per screenshot, not per rule, without a check over every line before pushing.** Each patch moved a
   fault somewhere else.
7. **Two copies of every rule** (editor and Python) double the work and the chance of drift; they now agree on every sample,
   but every rule change costs two implementations.

## Proposal

A. **Never draw what cannot be built.** Each stretch gets a legal structure or is drawn as infeasible: red hatching on the
   profile and the type bar, with the reason ("too little cover for a tube, too deep and long for a box: lower the rail
   here", with Regrade). No tube without cover, no box past its limit.

B. **Show the legal band while editing.** Draw the rules as lines on the profile: the deepest a box may go (cut-and-cover
   limit) and the shallowest a tube may go (one diameter of cover), so a drag shows at once which side of them the rail is.
   Auto and Regrade solve the rail inside the band.

C. **One bored type for running tunnels.** "Bored tube" (twin tubes or the double-track bore), no deep/shallow split between
   stations; stations stay box, mined or deep (for access). Removes the depth-class rules and their flags.

D. **Paint review.** A list of every paint per line with what the engine would do there, and one button to clear the paints
   that only restate the rules or contradict them. Paints kept for station method and tube form.

E. **One system check before every push.** The measurements above as a hub page and a test: tube without cover, box past
   its limit, box inside a drive, short tube between boxes, slivers, paints in conflict; the invalid classes must be zero
   (or drawn infeasible) on every line.

F. **Work on Ben's data.** Ben runs `python hub/hub.py export` and commits `hub/seed` (or sends the export), so the check runs
   on his current profiles.

## Built (31 October, Ben: "yes"; and "deep-bore is a thing when it's TBM")

- A. Unbuildable stretches (a tube short of one diameter of cover, a box past its phase's limit; the river bank works and
  canon box sections aside) are hatched red on the profile and the type band, and listed as errors with their fix: Regrade
  lowers the rail, Raise lifts it, as straight grades within the grade limit, moving a station in the way (not a canon or
  locked one). "Fix unbuildable" runs every fix on the line.
- B. Two dashed limits on the profile where the line is underground: the shallowest a tube may run, the deepest a box may go.
- C. Running tunnels by method, not depth: the shield in Phases 1-2, the deep bore (TBM) from Phase 3 (the record's
  `phases.tbm`, Phase 3 and later by default); mined stations are built as their drive; 18.29 m only marks lift stations.
  The end boxes of a drive carry on, within the cut-and-cover limit, through every spot where the tube would lack cover
  (Benton to Henry Clay is now a box up to Henry Clay, then the TBM drive with its cover).
- D. Paints card: every paint with what the rules would do there without it; clear one, the ones that repeat the rules, or all.
- E. "Check all lines" (unbuildable km by kind, errors, paints, per line) and a test that nothing unbuildable is unmarked.
- F. The Python copy reads the hub's exported records (hub/seed: the Chronology, the structure record, platform kinds,
  approach straights) and the Chronology's own station list, as the editor does; they agree on every sample of every Metro
  line on Ben's export except 3 samples on Line 5 (an approach straight the 3D build regenerates).
- On Ben's export after this: tube without cover 1.7 km (Lines 1 and 7, and small spots), box past its limit 2.4 km; "Fix
  unbuildable" clears all of it except Line 4 at State (canon-locked) and two 10 m spots on Line 7 where no level meets both
  limits. Some raises are large (Line 14 Mariemont 9.5 m, Line 2 Fountain Square 6.8 m, Line 2b West Covington 4.7 m): the
  other fix there is to lower for a whole drive.
