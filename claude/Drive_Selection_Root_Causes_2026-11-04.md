# Drive selection: why it keeps going wrong (4 November 2026)

Ben: "I painted this as cut-and-cover, and it refuses to acknowledge that. ... It's in cut-and-cover territory, but it's
decided to do 3 different construction methods ... I want you to pore over the history and logic you have been using to
make the drive selection and come back with the root causes."

Nothing in the engine was changed for this note.

## The screenshot (Line 1, Newport Central to Carothers Center, 18+150 to 18+900, Phase 3)

Ben's current Line 1 is only in his hub, so this is read from the engine's code and the screenshot, not reproduced.

1. **The station ignores the paint.** Since 2 November a paint across a station paints only the running line; the
   station keeps its own type (the card's selection). When selections came in, each saved paint at a station's centre
   was converted into a selection (`sttFromDoc`). An old shield paint at Carothers Center would now be a "Shield"
   selection that a new cut-and-cover paint cannot reach. The page shows no sign that the paint was set aside. The
   station is drawn mined at about 5 m depth, and its platform is hatched for lack of cover.
2. **Unpainted cut-and-cover territory is "either method".** From 18+165 to 18+590 the rail is between the shield
   minimum and the Phase 3 cut-and-cover limit, so both methods are allowed. The rule there came from the 28 October
   handoff (written in a chat session): "between the two: cut and cover unless the stretch meets the minimum drive".
   On 1 November I turned that into a cost choice. With the record's costs a box at 12 m costs 2.16 units a metre, a
   bored tube 1.0, and a change of method 180 at each end, so any stretch longer than about 310 m comes out bored. In
   Phase 3 bored means TBM.
3. **The 60 m box before the station** is either Ben's paint or the box where the tube is short of cover. With the
   mined station after it, the stretch shows three methods in 600 m.

## Root causes

1. **No decision rule that Ben ratified.** The rules come from three sources: Ben's rulings, handoff documents written
   in chat sessions, and changes I made during the audits. Where they conflict, my code chose, and I did not always
   say so. Examples:
   - "between the limits, bored if a whole drive" (handoff, 28 October);
   - the cost logic and the half-diameter "treatment" (mine, 1 November), which broke the 29 October rule that the box
     carries on until the tube has its cover;
   - the fill cap (mine, 1 November);
   - the Lines 1-7 island default (generator, 9 October).
2. **Ben's inputs are not constraints.** A paint, a station selection and the canon are inputs to a chain of passes.
   Later passes can override them: the station cut-outs, approach boxes, launch boxes, pockets, short-piece
   conversion and sliver absorption. The drawn band (`typeAt`, paint first) and the engine's result (`solveTypes`)
   are two separate answers. The band shows one, the checks and the 3D partly use the other.
3. **The engine is a stack of about fifteen passes built by patching.** Since 25 October there have been 45 commits to
   the Profiles page, about 30 of them to the tunnel logic. Each fixed one picture by adding a pass or a threshold.
   Conflicts are settled by the order of the passes, not by a priority Ben set, so a fix in one pass moves results
   elsewhere.
4. **Decisions are made per 2 m sample on raw lidar with hard thresholds**: shield cover, cut-and-cover limit, box
   roof, at grade, elevated. Cliffs and cuts (Aloysius, Rapid Run) flip the method. The smoothing (MIN_RUN, the dead
   band, portal_min) was added afterwards as patches instead of deciding per stretch.
5. **Stations are decided apart from their line**: one type by the platform centre, or a selection. A station can be
   mined in the middle of a cut-and-cover run, and the line round it bends to suit it.
6. **Verification checked the wrong things**: page against Python parity, and narrow unit tests. Ben's rules were never
   checked as invariants over every line. Ben's current profiles live only in his hub, so tests ran on the repo copy or
   on defaults, not on what he sees.
7. **Every change is made twice by hand** (page and Python port), which pushes towards small local edits.
8. **Process.** Each screenshot was treated as a local defect. I guessed instead of asking, and changed what rules meant
   without saying so.

## What would fix it (not started; Ben to decide)

1. Write the decision rule down as a short ranked list that Ben ratifies, for example:
   1. A paint or a station selection is final. If it cannot be built, it is flagged, never overridden, and a paint
      that crosses a selected station says so.
   2. Unpainted, within the cut-and-cover limit: cut and cover, with no cost choice.
   3. Unpainted, deeper: bored by the phase's method, a tube only with its full cover.
   4. Methods change only at stations, portals or shafts.
   5. A station takes the method of its stretch unless selected.
2. Replace the pass stack with one function that applies the list in order, used by the drawing, the checks and
   Station 3D alike.
3. Turn each rule into a test run over every saved line, and over Ben's own hub profiles (a hub export pushed to
   `hub/seed`).

## Done the same day

Ben: "go back and rethink how the logic needs to work", then "make the changes". The rewrite is in `data/profile/profiles.html` (`solveTypes`) and `railsim/metro_profile.py` (`_stretch_types`), described in `data/profile/README.md` ("Tunnel engine rewritten") and the Station 3D log for 4 November. Ben's choices: phase preference (Phase 1 cut and cover, later bored), paints snapped to the anchors with a Shaft brush for a change partway, the migrated selections cleared.
