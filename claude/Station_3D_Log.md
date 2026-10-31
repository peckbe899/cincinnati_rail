# Station 3D log

Decisions and state for the Station 3D tool (brief: `claude/Station_3D_Brief.md`; code: `tools/station3d/`).

## 2026-10-26: phases 1 and 2 for Fountain Square

Ben's rulings before the build:

- Platforms: Metro 400 ft, TRI 670 ft (204.216 m).
- Line 7 (no saved alignment): drawn from the Profiles editor's built-in defaults, marked unsaved.
- Levels: always the Profiles editor's values, pulled fresh at each sync. They are unfinished, so the RER-1 / Line 2 overlap under Vine is drawn as it is, without a flag.
- Layout: the model moved to `stations/fountain_square/`, the brief to `claude/`, the tool to `tools/station3d/`.

Built:

- The sync runs both editors headless and reads their own functions. The levels it reads at Fountain Square match the brief's table: Line 1 160.9 m, Line 2 153.4 m, RER-1 156.56 m, RER-2 140.59 m. Line 7 160.98 m and RER-4 155.99 m come from defaults.
- The page: https://claude.ai/artifact/MxbB1bnkqwZYxCbbEsHQZA. Free camera (orbit, pan, zoom, from below, double-click sets the centre), camera remembered per viewer, shared named views, see-through ground and structures, a cut above an elevation, a near-half cutaway, one level or all, a height scale, labels facing the camera, presets (plan, Republic iso, SE 139° at 12°, SW 229° at 32°, SSW 204° at 28°, from below), PNG and glTF downloads.
- The Republic iso preset uses `fs_3d.py`'s default view (frame 30° at 26°, so facing true 19°). Confirm it matches the Republic drawings.

Assumptions to set (shown on the page):

- Metro box 8.5 m wide; twin tubes 7.0 m apart.
- RER box 11.0 m wide; RER bored tubes twin, 8.5 m across, 11.0 m apart.
- Platform tops 1.0 m above the rail.
- The ground is one fitted plane (about 2 m rms).

Not yet done:

- Elevators as at Republic: they arrive with the station model in phase 3.
- The Fountain Square model's halls, flights and lifts: phase 3. Its depths are drawing values, not the editor's.
- Checks: phase 4.

## 2026-10-26: tracks from the Deck (platform_track)

- `platform_track/` moved to `design/platform_track/` as its brief says; the root copy of its brief removed and the brief copied to `claude/Platform_Track_Design_Brief.md`.
- The sync now runs its `extract.js` inside the headless Deck and draws the tracks the Deck draws: Metro bored tubes 8.0 m apart, boxes 3.9 m, islands pushing tracks to ±5.45 m (TRI ±7.25 m). The guessed 7.0 m tube spacing and fixed box widths are gone; boxes are the track spacing plus 2.3 m (Metro) or 3.25 m (TRI) walls, still assumptions.
- New issues the sync reports at Fountain Square:
  - Line 1: 308 m cut and cover in the Profiles editor but twin tubes in the Deck, and 42 m the other way. This is platform_track brief conflict 9: the Deck's construction snapshot predates Line 1's 17:25 save.
  - TRI B: 670 m bored, but the Deck's 4.5 m TRI spacing is too close for two tubes (brief conflict 2, decision 2).
- Still open between the Deck and the Fountain Square model: A/D on two tracks and one island (Deck) against four tracks and two islands (model); Metro 2 and 7 islands (Deck) against side platforms (model). Platform_track brief decisions 3 and 4.

## 2026-10-26: the whole region; A/D share the Fountain Square platforms

Ben's rulings:

- Extent: what the Mill Creek Deck renders lines over (its Region limits, E 699,000-736,900, N 4,320,800-4,347,000), not 400 m around Fountain Square.
- TRI A and D share the Fountain Square platforms: the Deck's one island on the A/D pair (platform_track decision 3, option A). The Fountain Square model's four-track A/D layout is superseded; to change in phase 3.
- Station information comes from both editors.

Built:

- One snapshot, `snapshots/region` in 26 parts (4.4 MB): 21 Profiles lines, 210 levelled Deck tracks, 490 station records, 757 platforms, 2,686 streets, 2,711 blocks, a 200 m ground grid.
- A platform on a shared pair serves every line on it, at the saved line's level (first in letter order). At Fountain Square the A/D island is at RER-1's 156.56 m for A and D (RER-4's defaults give 155.99 m).
- The Union Terminal TRI box's islands are tied to A and B, D, and B and A.
- The page: a station picker (default Fountain Square) with each line's Profiles levels and Deck platform, tracks, settings and slide; levels, presets and labels follow the chosen station; a whole-region view; spread now measured from the local ground.
- Fountain Square levels unchanged: Line 1 160.9 m, Line 2 153.4 m, Line 7 160.98 m (defaults), A/D 156.56 m, B 140.59 m.

New issues the sync reports (45 in all):

- Union Terminal box: A and B change cross-platform, but the Profiles editor has A at 142.0 m and B at 135.7 m; drawn at A's.
- About 430 km of Deck track (mostly TRI out to the region's edge, plus pieces of Metro 1 and 3) and 78 Deck platforms have no Profiles line within 30 m. Drawn on the ground.
- 19 Profiles stations have no Deck station nearby (Line 3's Kentucky stations, among others).
- Deck spacing against the Profiles structure on most Metro lines (Line 1: 2.5 km cut and cover in Profiles, twin tubes in the Deck) and TRI bored stretches too narrow for two tubes on all five lines.

## 2026-10-26/27: CUT structure types, the upper deck, B/D on the Deck route, interlined pairs

From the handoff (`handoff/2026-10-26_station3d_cut_norwood`, now removed): `context3d.py`, the finished-ground tiles, the CUT and Norwood structures, platforms and tracks, built from the same definitions as the Rail Profiles context. Kept; its drawing of every structure as a deck on 20 m piers replaced with Ben's structure types:

- The fan from W 9th to W Liberty: an embankment with a bridge over each street.
- Arch viaducts only on the wide multi-track stretches, an arch over each street: the south approach to the Cardinal crossing and the north arch viaduct (arches tall enough for buses, one storey).
- Everything else a normal viaduct on piers; the intercity and C&O descents embankments with blind arches.
- The Profiles context the same way: a line in the open under an embankment or arch viaduct clears it only through a street opening. New clashes: Lines 8, 12, 13 and RER-1 under the north arch viaduct outside the street arches.

Upper deck (Ben, 2026-10-27): the lower deck (R5, B, the APEx Dayton and Norwood pairs) passes over the roads; the Indianapolis pair and D run on an upper deck at the minimum height over it, 174.5 m (the crossing rule, 7.9 m), west of the RER A viaduct to the hillside, then climb in the Floridian hillside tunnel at a constant grade to the portal at 39°9'25.61"N 84°34'0.60"W, about 186 m. D's profile north of Camp Washington follows it (`tools/make_rer4_upper.py`; repo profile, not saved in the editor).

B/D from the trunk to Union Terminal (Ben, 2026-10-27: the Profiles paths were the old KMZ line, up to 237 m west of the Deck's tracks): RER-2 and RER-4 re-pathed onto the Deck's B/D route (`tools/repath_rer_bd_trunk.py`). The editor still has the old paths until it is republished, so the sync serves the repo's files in their place. RER-2 / RER-4 run times change by -0.02 to +0.23 min; B and D now pass 7.8 m / 6.7 m under the CUT lower-level box (9.0 m needed), and the old RER-2 clash with the upper deck is gone (18 context clashes, was 19).

Interlined pairs (Ben, 2026-10-27): A/D and B/D are one pair each, drawn once and striped in both colours; D draws nothing along them. D has no saved profile, so its defaults differ from A by up to 6.7 m and from B by up to 6.0 m (Western: B 138.4 m, D 144.4 m); drawn at A's and B's levels and listed as issues.

Published: page version 6 and the snapshot (35 parts), read back at view level.

## 2026-10-27: Rail Profiles editor updated and locked; lines on the Deck tracks

- Rail Profiles editor version 34: the B/D re-path, the context, and locked stretches (B on the viaduct, Northside to Straight; D from Straight to the Floridian portal). D now takes B's levels from Union Terminal to Camp Washington, so the B/D pair is one level (Western 138.4 m for both; was D 144.4 m). The editor's saved RER-2 was moved onto the new path and RER-4 saved for the first time. Station 3D's repo stand-ins switched off by themselves.
- Tangles (Ben: RER B north of Mitchell, Line 3 at Mitchell): the lines' structures followed the Profiles paths while their rails followed the Deck tracks, up to 60 m apart, and tracks broke into pieces past 30 m. Now each line follows its Deck tracks in plan (Profiles levels by chainage), tracks match their line within 120 m with chainage kept one way, and no drawn line or track turns back on itself (checked over the whole snapshot; the fold-backs in the Line 4, 5 and 6 Profiles paths are all under Deck track).
- RER lines to the region edge (Ben: RER A past Westwood had no line): Deck track with no Profiles level is drawn on the ground in its line's colour (it was dashed grey).
- Page version 7 and the snapshot published.
- Other systems past the Deck's structures (Ben: extend the rails past the bridges into Ludlow; no dashed rails anywhere): the APEx, intercity, C&O and Transvalley tracks now run on from each structure end at their system's grade to the ground (tunnel tracks 15 m under it, 20 m over the Ohio pool over water), 42 tracks extended, none left dashed. RER-4 runs after D took B's levels: +0.00 to +0.06 min; RER-2 unchanged.

## 2026-10-27: RER trunks and branches; the routes tied to the Deck

- The Rail Profiles page now has each lettered RER line as a trunk and branches. The sync maps Deck labels to them by letter (from the page's index) and the Union Terminal box to the A, B and D trunks.
- Every sync checks each RER route against the live Deck (the harness export) with `tools/rer_deck_routes.py` and lists drift as an issue; none after the rebuild (page version 37).
- RER A's rights of way from the Deck are locked in the page (fork, Evans, Westwood, Hopple, South Cumminsville, Northside to Linden).
- New issues: shared stretches whose two routes' saved levels differ (C CVG on B CVG 6.9 m, C Withamsville on C Eastgate 6.0 m), and the far-west A/D track, which the page's links do not list as shared (D trunk 23.4 m off the A Westwood branch). Fountain Square A/D now 155.85 m (the trunks' saved profiles; RER-1 had 156.56 m).
- Snapshot published (39 parts).


## 2026-10-27: Metro lines and platforms tied to the Deck

- Ben: the Profiles ROW must match the Deck's and station positions matter, for Metro "arguably moreso". Every Metro line except CVG Express is now built from the Deck's Metro pieces (`segs`), checked and applied by `tools/rer_deck_routes.py` with the RER routes.
- Decision: a platform's position is the Deck platform's centre; the Profiles station point goes there and its saved slide is reset (the Profiles and Deck slides disagreed, e.g. Xavier -60 m vs -37 m). Ben's slides on Lines 1, 2, 4, 5 and on A Xavier / B Rivercenter were reset.
- The sync now also lists platforms off their Deck platform. None after the apply.
- Line 14's default profile clashes with the Norwood tracks after its platform moved to the Deck's (reported, not fixed: Line 14 has no saved profile).
- North arch viaduct context trimmed to the APEx tracks: RER A's false clash under it is gone.
- Rail Profiles page version 39; snapshot published (38 parts, gtiles-2 removed).

## 2026-10-27: the local hub

- Ben: connect the three so a change in one updates the others, with parameters from one central database; local only, just him.
- `hub/hub.py`: one SQLite database for the Deck, Profiles and 3D pages, served locally with a stand-in for the artifact runtime (pages unchanged; their database calls go to the hub, live over server-sent events). A Deck save runs the Deck tie and then the 3D rebuild; a Profiles save runs the 3D rebuild. Hub page: runs, shared parameters per view, roadmap, export to `hub/seed` for git.
- Fixed in the headless runner (`tools/station3d/harness.js`): it could export the Deck before the saved edits had loaded (seen as routes 200 m off). It now waits for the edits themselves.
- Found by the parameter registry: 64 of the Deck's RER island platforms are drawn about 202 m long, 44 at 204 m; the Profiles and 3D use 204.2 m.
- The artifacts are no longer updated: the hub is where the design lives.

## 2026-10-27: rails centred and unbroken

- Ben: rails unbroken between tube and cut and cover; Rivercenter West looked wrong; rails always centred on every line, no tracks off to one side.
- Cause: the 3D drew each line's rails where the Deck draws its tracks. The Deck switches spacing in steps (tube 8.0 m, box 3.9 m) in separate pieces and leans some pairs to one side (Line 2 at Rivercenter West +0.7 / -10.2 m; at Fountain Square +2.6 / -8.4 m), and the boxes were sized from those tracks.
- Now: the sync draws each line's two tracks itself, centred, at the spacing its Profiles structure needs (Deck rules), widened at island platforms, tapering over 40 m; platforms redrawn on them. No breaks in any line's rails; short close passes (under 100 m) no longer count as running on another line's track.
- Decision: TRI bored stretches at 9.5 m (two 8.5 m tubes, 1 m apart); the Deck's 4.5 m cannot hold two tubes.
- Follow-up (Ben: Rivercenter West still off to one side in plan): the centred rails sat on a centre still moved to the middle of the Deck's track pair, which leans 5 m to one side there. A line tied to the Deck's pieces now keeps its own path (the Deck's line); the island at Rivercenter West is 0.02 m off the line, rails at 5.45 m either side. This exposes fold-backs in the Deck's edited RER A Westwood piece (c 724 to 1561, 3 to 48 m spikes), listed as an issue for Ben.
- Each view served by the hub has a Home button in its bar.

## 2026-10-28: curve grade check

- Ben: RER A Blue Ash "Grade plus curve allowance reaches 36.2 per mille (tightest radius 378 m)", but the diagram showed nothing over 35.
- Cause: the allowance (800 / R) took R from a three-point circle over +/- 40 m of the drawn line, which jumps between 313 and 5,490 m on a hand-drawn curve; one kink set the figure. The diagram shows only the grade.
- Now (Rail Profiles editor): the allowance is the curvature averaged over a train length (the platform length) times k; the stretch is marked on the diagram (dashed, with "x per mille with curve"), the hover readout gives grade with curve, and the issue gives grade, allowance and the equivalent radius. On a 34.5 per mille test grade there the allowance is 0.6 to 1.5 per mille (was up to 2.6): still over 35, as the curve is real (about 530 m averaged).
- Ben (RER A Blue Ash, 3+550 to 3+700, a tunnel entry): Auto made the RER cut and cover from 3 m down, so a ramp into a tunnel had a box whose roof stood out of the ground ("Box roof 3.4 m above ground"). The Metro already had the rule; now the RER too: rail less than a box height down (the 6.6 m envelope) is an open trough, the box starts where its roof is under the ground (editor and railsim port).
- Ben: drainage is a warning at most (a flat tunnel is handled by engineering: a falling track drain, sumps, pumps). The editor's drainage check is now a warning, worded as what it needs.

## 2026-10-28: yards draft 6; Metro structure gauge (handoffs of 27-28 October)

- Handoffs in `claude/Code_Handoff_Yards_and_Metro_2026-10-28.md` and `claude/Metro_Structure_Gauge_Handoff.md`.
- Ben's answers (28 October): Phase 2 (Lines 8-12) is the 9.0 m double-track bore; each drawn piece gets a "built" phase field, all starting at their line's phase (Ben marks extensions); "straight" for the 6% rule is a radius of 1,000 m or more averaged over the train; Metro clear height under structures in the open 4.42 + 0.15 = 4.57 m; the structure values in one shared hub record read by the Deck, Profiles and 3D; the Deck page changes too; tunnel equipment drawn near the camera only.
- Step 1: Deck yards draft 6 (published Deck version 141, 1793139343-a4fe): `hub/sites/deck/yard.json` and the "Draft 6." label. Its context.json is the repo's (same file). The Deck runs headless with it.
- Disagreement noted: the yards handoff says the Profiles editor has RER A at 154.8 m at Evans; the repo has 147.5 m (locked 27 October). Both move to 139.0 m (step 2).
- Step 2: RER A trunk lowered under the yards (locks, `tools/rer_deck_locks.py`): Evans 139.0 m, level platform; the deck edge stays 148.4 m (c 330), the CUT lower-level point 135.9 m, Union Terminal 135.7 m. The Deck's "2.2% up from Evans to the deck edge" puts the 204 m platform on a grade; with a level platform the descent from the deck edge is about 34 to 35 per mille (at the RER limit) with the 3,000 m vertical curves. The yard floor over A is 145.3 to 146.1 m (yard.json): rail 7.1 m under it at Evans, but the box roof (6.6 m envelope) only about 0.4 m under the floor.
- Step 3: the shared Metro structure record `params/metro_structure` (default `data/profile/metro_structure.json`, seeded into the hub on start, edited on the hub page under "Metro structure"; a save rebuilds the 3D map and open Profiles pages update live). It holds the car and envelopes, the tubes (type A 5.10/5.50 m at 8.74 m centres, type C 5.40/5.90 m at 9.14 m, the 9.0 m double-track bore), the box (3.90 m centres, 7.90 m inside, 1.0 below and 4.6 above the rail, columns 0.25 m every 1.524 m), the island box (10.90 m centres), the 40 m approach, the 4.57 m clear height, the grade rule, the tube of each phase (1: A, 2: bore, 3 and later: C), and the phase of each line and of each drawn piece (all at their line's phase; Ben marks extensions).
  - Rail Profiles: bored stretches (shallow, deep, under rivers) take the tube of their piece's phase; the river margin is 1.0 m scour + half the tube + rail to its top (type A 8.35 m, was 7.5); clear height 4.57 m; grade rule: over 50 per mille is an error, but a warning up to 60 on a straight (train-averaged radius 1,000 m or more) bored or box stretch, where the curve-grade check is skipped.
  - Station 3D: tubes and boxes from the record by phase (snapshot types 'shield~A' and so on); rails at the tube's running centres (A 8.74, C 9.14), 3.90 m in the bore and boxes, 10.90 m at islands; boxes 9.1 m outside.
  - railsim port: reads the record (legacy_structures keeps the old sizes for the saved-page fixture test). Test expectations updated: Line 8 under CUT's lower level needs 8.0 m (bore top 6.5 m), street-opening clear height 6.67 m.
  - Lines 1-7 now go deep in type A tubes and Lines 8-12 in the 9.0 m bore (was a twin tube for every deep stretch).
- Steps 4-5: the Deck reads the record live (hub) and draws every Metro line from settings: tubes at their phase's centres (measured on the Deck: 3.9 m boxes and bore, 8.7-8.8 m type A, 9.1-9.2 m type C, 10.9 m islands); a change of spacing between a bored stretch and a box eases inside the box (never closer than the tube spacing in a tube), as do the 3D rails. Island by default where the station is shallow shield in the Profiles (hub `params/station_types`, written by each 3D build from the Profiles levels; default `data/profile/station_types.json`); Ben's per-station type wins (Taft Theater and Pennsylvania Station stay side by his setting). The Deck's own bored flag can't tell shallow from deep, so the type comes from the Profiles: a first try made 15 deep Phase 2 stations islands, undone.
- Approach report (snapshot `approach`, in the issues): 7 shallow-shield stations, all islands but Taft Theater (Ben's side); 20 side-platform stations on bored stretches, 19 of them deep (Lines 8, 10, 11, 12 in the bore, Line 1 Pennsylvania Station) plus Taft Theater; no island needs a box on the bore today and no approach misfits (terminals excluded).
- Step 7: Station 3D draws Metro tunnel equipment within about 500 m of the view's centre when zoomed in (rebuilt as it moves), on five switches under Show: box columns (0.25 m every 1.524 m between the tracks), legacy signals (signal, red aspect, trip stop, insulated joints at 250 m block ends and platform ends), CBTC and radio (transponders every 100 m and at stopping points, access points every 300 m, leaky feeder), safety (standpipe, hose valves every 61 m, blue lights every 250 m and at platform ends, cross passages every 200 m between twin tubes at bench or walkway level, distance markers every 100 m, intrusion detection on the last 100 m into each platform and along the platform edge), and power, lights, drains, shafts (third rail, cable racks, lights every 18 m, drains, sumps at low points, vent shafts at station ends, draught relief on deep tubes, type C walkway and handrail, type A and bore bench walls). Positions per tunnel type from Ben's Metro Box Cutaway and Metro Tube Cutaway pages (third rail inner in twin tubes, outer in the box and bore; type A signals on the right of travel, type C on the left).
- Step 8: docs (hub README records, Station 3D README), roadmap items added to `hub/seed/roadmap` (deep Phase 2 stations, extension phases, the RER A box roof under the yard, the yard flags, the fact tracker 2C canon update). A fresh hub seeds the records, builds the 3D map once (143 s) and passes `hub/test_hub.js`. An existing hub database keeps its roadmap records and gains the new ones; the structure record and station types are seeded when missing.
- Ben (28 October): side platforms on bored stretches are not necessarily wrong but should be noted. Now a "to check" note, not an error: in the 3D issues ("To check (not necessarily wrong)"), on the hub page under Shared parameters, and on the station's card in the Deck (with shallow shield or deep tube). Roadmap item reworded.

## 2026-10-28: Norwood Central level; north viaduct heights (handoffs of 28 October)

- Handoffs: `Code_Handoff_Norwood_Level_2026-10-28.md`, `Code_Handoff_Viaduct_Heights_and_Arcade_2026-10-28.md` (v2), with the Viaduct Arcade 3D model.
- Norwood Central (Ben: v112 ruling, roofs at street level; approach option A): rail and platforms 185.5 m (was 178.0 m, from the North Viaduct Plan, never Ben's). The descent is unchanged (ground 174.8 m at s 3,220, 2% to 170.0 m at s 3,460); then one grade, 1.58%, to the platforms' west end at s 4,438 (from the `nw_plat` features in frame s), level on. Grades accepted, not flagged. `make_profile_context.py`, `context3d.py`, `combine3d.py`, `render3d.py` (its outputs not regenerated: they need the extract inputs), tests.
  - Clearances: Line 14 (default profile) 2.2 m under the cut, needs 5.9 m (was 4.7 of 7.8); Line 4 at Norwood Central 14.0 m (needs 5.9); RER 5 and RER E cut and cover at 168.6 m: 8.8 and 10.9 m (need 7.9); RER A Blue Ash at grade 189.0 m now 3.5 m over the cut, needs 8.3 m (was 11.0): a new clash; Line 3 (183.2 m) does not cross the cut. RER 5's default profile follows the new cut floor (184.7 m).
  - The Transvalley crossing (s 3,456-3,576): the trench there is up to 0.25 m higher (1.58% instead of 1.39% from s 3,460). On the raw ground the Transvalley would clear only 2.2 to 7.0 m; its own formation must stand 0.3 to 5.1 m over the ground to keep 7.3 m (as before, nearly).
  - Concourse: APEx wires at 6.1-6.7 m put it about 193-194 m, 2-3 m over the street; nothing in the repo conflicts. The Deck's APEx Norwood track notes still say "about 178 m" (Deck text, for Ben).
- North arch viaduct (Ben: rail at street + 7.4 m): rail through each street's minimum (highest finished level across the structure + 7.4 m) from CUT (160.3 m) to the Arlington platform (165.9 m, locked), then one dip: 1.5% down to 159.8 m, 0.37% up to Ludlow (162.5 m, locked). Streets are the Deck's live layout (base streets with the layout's edits); the Millvale cross streets (M1-M20) are left out as they end at MT (section 5), MT and J1 run along, Elmore only clips the edge. True arch up to 11.9 m wide (Meeker 9.1 m; Streng and Ford 9.1 m in the Spring Grove knot), all others hidden girder bridges. The street table is in `context/lines.json` meta `north_viaduct`. The north arch openings now come from the same live streets.
- W 8th: the hump is 5.0 m to x 712,671, 2.4 m at the south approach's west face (x 712,764), to zero at 712,941 (161.7 - 153.0 - 4.3 - 2.0).
- Upper deck: 7.9 m over the highest rail it crosses, now including RER A and R5 at South Cumminsville (167.0 m): 174.9 m (was 174.5).
- Clearance changes: RER A Cumminsville under the upper deck 7.89 m (ok, was 7.49 short); RER A Cumminsville over the lower deck 6.4 m (needs 8.3; was 3.2); Lines 8 and 12 still cross the north viaduct outside a street opening, as before.

## 2026-10-28: one diameter of cover over bored Metro tubes (handoff of 28 October)

- Ben: every shield-driven tube (shallow shield, deep tube, the double-track bore) needs at least one outside diameter of ground over its crown. Replaces 2.0 m above the 140 m water table. `reqCover` (Rail Profiles) and `req_cover` (railsim port) return the tube's outside diameter; `TUBE_COVER_HIGH` and `WATER_TABLE` are gone. River rule, box roof cover (0.6 m) and the stacked-tube separation (upper floor + 0.5 m + lower top) unchanged.
- Minimum rail depth for a bored tube: type A 10.10 m, type C 10.85 m, the bore 15.50 m; shallower is cut and cover.
- Effect (current profiles, saved where there is one, default otherwise; Profiles port): no station changes type (the 7 shallow-shield stations are 11.8 to 20.7 m deep). Running tunnel from shield to cut and cover: Line 1 2.0 km, Line 2 2.5 km (0.2 of it deep tube), Line 2b 1.0, Line 3 3.3, Line 4 1.6, Line 5 9.2, Line 6 7.1, Line 7 8.8 (default), Line 8 5.6, Line 9 7.4 (default), Line 10 6.4 (default), Line 11 6.1 (default), Line 12 6.0 (default), Line 13 9.5 (default), Line 14 9.3 (default), CVG Express 1.1 km: about 87 km in all.
- Line 8 under CUT's lower level is now cut and cover there (need 6.1 m; test updated).

## 2026-10-28: the arcade remodel (viaduct handoff v2, section 4)

- Deck: a block beside an arch viaduct (within 45 m of the north arch viaduct, or of the south approach north of the Cardinal crossing) has an "Arcade facing this block" switch on its card: blind arches (default), shops in the arches, open arches. Saved in the layout (`edits.blocks[id].arc`), exported with the block (`arcade`).
- Station 3D: the arch viaducts' long faces (only along the lower deck's APEx tracks; the Indianapolis and D branch on columns is left plain) are sent as `arcade` items with each street opening (true arch up to 11.9 m wide: Meeker, Streng, Ford; all others hidden girder bridges) and each block's stretch with its state. The page draws the arcade near the camera in the mockup's style; open blocks carve a girder bridge (2.0 m deep, drawing value) through the structure. Street spans over the arch viaducts are now girder bridges at 2.0 m under the rail (true arches at 2.21 m).
- About 10 km of face in all. The Millvale-side west face from Hopple to Arlington is one blind run: the Millvale cross streets end at MT (still to be moved, section 5).
- Catenary: masonry pylons on every fourth pier with a lattice girder to mid-deck; the middle masts need the 6.0 m APEx-side gaps (section 7.2, not yet done).
- Checks: `test_context.js` views arcade_dolph, arcade_harrison, arcade_hopple, arcade_shops (every block switched to shops in the page); an open block tested in context3d.

## 2026-10-28: tunnel methods by era (handoff "Chronology and tunnel methods", section 2)

- Ben's answers (28 October): the minimum shield drive applies only to pockets inside a longer stretch; a tunnel from box to box (or a portal, or a deep station) is a drive at any length. Years between phases as proposed (1919-33 Phase 1, 1942-49 Phase 2, 1980 on later). "Deep tube (Greathead shield)" becomes "Deep tunnel" (drill-and-blast in the hills' rock). The twin-tube/bore exceptions are flagged only.
- Record (`params/metro_structure`, `phases`): cc_max (deepest cut and cover: Phase 1 12.19 m, Phase 2 16.5 m, Phase 3 and later 15 m), min_drive (400 m, 300 m, 300 m) and deep_from (18.29 m), editable on the hub page beside each phase's tube (shield-from shown: A 10.10 m, bore 15.50 m, C 10.85 m). The hub fills fields new to the default into an existing record on start.
- Rail Profiles (and the railsim port): each point is classed (must be cut and cover, either, must be bored); then over each stretch between station boxes, portals, canon sections, rivers and phase changes: a bored run is a drive if it spans the stretch or makes the minimum, else cut and cover (flagged where deeper than cc_max: the profile has to rise); a short cut-and-cover pocket inside a drive is bored where the cover allows, else flagged (the profile has to dive); deep only on a run of the minimum drive or next to a deep station, else shallow shield. Station boxes, canon sections and painted stretches as before. Results are cached with the profile.
- Effect (saved profiles where there are any, defaults otherwise): no station changes type; 12.5 km shield to cut and cover, 1.4 km deep to cut and cover, 3.5 km deep to shallow shield. 36 pockets flagged ("Tunnel method" warnings): CVG Express 1, Line 1 4, Line 10 4, Line 11 2, Line 13 1, Line 2 2, Line 3 3, Line 4 2, Line 5 4, Line 6 3, Line 7 6, Line 8 2, Line 9 2.
- Tube choice (flag only, "Tube choice" warnings): twin tubes under a street narrower than their footprint, 4 stretches, 0.8 km (Line 1 Butler St, Line 13 Forest Ave, Line 7 Monastery St); Phase 2 cut and cover deep enough for type A twin tubes but not the bore, 78 stretches, 20.2 km (mostly Lines 10 and 11). Street widths along each Metro line now in `context/lines.json` (`streets`, from the Deck's live layout; where the Deck has streets).

## 2026-10-28: the Chronology view (handoff "Chronology and tunnel methods", section 1)

- A fourth hub view, `/chronology/`: the Metro lines and the TRI's lettered routes (41 routes, 541 segments, 461 stations; the numbered RER-1 to RER-5 services are not routes) on a plain base; colour by phase or opening year; "network as of" slider; unset segments dashed; selection by two stations on a line (shift-click, Alt-drag box); a panel to set year, phase (Metro; TRI years only) and note; rule breaks in red and listed with orphans, unset segments by line and infill stations.
- Keys: Metro segments per line (`metro|Line_11|Clay|Manhattan`): no Metro lines share track (the 3D build finds interlining only on the TRI), so two Metro lines between the same two transfer stations (7 such pairs, e.g. Lines 2 and 8, Daniels-Jefferson) are separate tunnels. TRI segments by the station pair, so track shared by several routes is one segment. Stations by system and name.
- Order rules (`hub/static/chronology_rules.js`): core = the record's opening segment, else the earliest year; outward never older (a branch from its parent's segment at the junction); stations no earlier than the earliest segment touching them, later = infill; an edit that breaks a rule is refused with the reason; setting a segment later than those beyond offers to push them (and their stations) to that year.
- Phases by year (Ben): to 1933 Phase 1, 1934-49 Phase 2, 1950-79 Phase 3, 1980 on later; a phase set by hand stands.
- Starting record (`data/profile/chronology.json`): the Phase 2 opening segments with their years (Line 8 Northside-Union Terminal 1934, Line 9 Camp Washington-Oakley 1936, Line 10 Mill Creek-Paradrome 1937, Line 12 Hopple-Pleasant Ridge 1941; these are the lines' cores); the CVG Express 1969, later (Ben); each TRI route's segments its route's opening year (from the route data; 1985-1996). Everything else not set: it takes the line's phase from the structure record. Notes: Line 1 opened November 1905 (no stations named); Lines 1-7's original termini are not in the repo.
- Readers: the Rail Profiles take each stretch's phase from it (live; a band under the profile, click to open the segment here); the railsim port and the 3D sync read it (the sync's tube per chainage); the 3D build writes `params/tube_points` (tube every 50 m) and the Deck spaces each Metro line's tracks by it. A Chronology save rebuilds the 3D map; each Deck tie rebuilds the routes file.
- Starting report: rule breaks 3: RER E CVG branch (1996, from the E trunk) runs on the CVG track RER B opened in 1988 (Crescent Springs-Mineola, Mineola-CVG Terminal 2/3/4, CVG Terminal 2/3/4-CVG Terminal 1). Orphan 1: Line 11 Manhattan-Ludlow 1939 (Line 11 has no Ludlow station). Not set: 356 of 541 segments (all of Lines 1-7, 13, 14, 2b and the rest of 8-12).
- Checks: `tests/test_hub.py` (the trigger), `hub/test_hub.js` (a phase set in the Chronology reaches an open Profiles page live).

## 2026-10-28: each viaduct a selection of its own on the Deck

- Ben: break up the Deck's "Viaducts and bridges" filter, one selection per viaduct, and make Union Terminal's parts selectable as a whole too.
- Deck layers: "Union Terminal (all its parts)" now switches its six parts together (and shows when only some are on); "Viaducts and bridges (each viaduct)" switches 14 selections together: the north arch viaduct (APEx lower deck); the CUT south approach as the arch viaduct (W 9th to the Cardinal crossing) and its three branches south of it (APEx Kentucky, the Cardinal branch, the CVG Express); the Cincinnati Western viaduct upper deck (RER D and the APEx Indianapolis pair; named for the Roll Hill tunnel) and lower deck (R5); the C&O viaduct; RER A Westwood; RER A Northgate (the Colerain branch, west of the Northside branch: Ben); the Northside viaduct (RER A, the Oxford line: Ben said the trunk at Northside; in the route data the Northside viaduct is the first 1.7 km of the Northside to Wyoming route, so that is drawn); RER A Western Hills to South Cumminsville; river bridges and the Ludlow underbridge; other structures.
- Footprints: `tools/viaduct_parts.py` writes `hub/sites/deck/viaducts.json` from the Deck's structures (the north arch polygon split at 12 m from the APEx tracks: the rest is RER A's Western Hills - South Cumminsville viaduct), the Profiles context (the CUT south arch part; the south part split by the nearest branch track; the upper deck), the Deck's R5 tracks (3.0 m either side, drawing value) and the elevated stretches of the RER A routes in the Rail Profiles (6.45 m either side). The hub's 3D build reruns it, so the RER A viaducts follow the profiles. A part's card names it.

## 2026-10-28: track geometry in tunnels and station approaches (handoff "Tunnel track geometry")

- Ben: the approach where the tracks change spacing beside a station is part of the station and built as it is. Rail Profiles and the railsim port: a cut-and-cover station meeting bored tubes keeps its box through the approach until the tracks reach the tubes' spacing (side platforms 3.90 m, islands 10.90 m, to type A 8.74 m or type C 9.14 m; the bore is 3.90 m, so no approach); a box meeting tubes away from a station likewise; the approach is a switch point (not part of a drive). Length max(approach_m 40 m, sqrt(4 x min radius x shift per track)). Island or side from the Deck's platforms via the 3D build (hub `params/station_platforms`, default `data/profile/station_platforms.json`).
- Minimum radius: the editor had none. `min_radius` added to the structure record at 150 m, a drawing value (the handoff's example), editable on the hub page; with it every approach is 40 m (side to type A needs 38.1 m, to type C 39.6 m).
- Station 3D: tubes always at their spacing; each change one S-ease over the approach (inside the box, or the bored approach of a bored island); other changes hold the wider side and ease into the narrower. On curves the drawn ease is not yet the single arc per track (Ben's rule): the arcs are computed for the checks (the handoff's formulas); the drawn ease differs from them by centimetres.
- Effect: 3.9 km shallow shield to cut and cover (the approach boxes), 0.1 km deep to cut and cover; no station changes type; 27 station boxes longer (122 m to about 163 m, two approaches 204 m: Government Center and Covington Union, Line 3).
- Report (snapshot `track_geometry`, in the issues):
  - under the minimum radius (150 m), 21: e.g. Levee (Line 1) on a 149 m curve; Carothers Center (Line 1), California (Line 5) and box ends on Line 4 and the CVG Express run into a curve within the approach where no single arc fits; the rest are S-eases on curves of 160-500 m.
  - side-platform stations meeting tubes, 13: Covington Union (Line 3, both ends), Eggleston (Line 7), Xavier, Burwood, Mt Lookout (Line 13), St Xavier, Dogwood, Mariemont (Line 14), CVG Express Terminals 3, 2, 1B, 1A; 40-42 m approach boxes.
  - approach boxes not inside the street, 29 (leaving the street over blocks or round a corner, and one 13.1 m box under Forest Avenue, 12.2 m); 29 more are where the Deck has no streets (CVG airport, Line 14's east end and others), not checked.

## 2026-10-28: answers on the track geometry (Ben)

- Minimum radius by phase (Ben): Phase 1 40 m, Phase 2 55 m, Phase 3 and later 70 m, in the record's `phases` (`min_radius`, on the hub page), replacing the 150 m stand-in. Every approach stays 40 m (the largest needs 27.1 m).
- Where no single arc fits (Ben: option A): the approach box starts with a straight after the platform (or box) end, so the tightening track's arc starts no more than sqrt(2 x shift x (r_mid - Rmin)) before the curve (no single arc can join two concentric curves, so the arc always starts on the straight); the box grows by the straight. The 3D build computes it from the plan's curvature (hub `params/approach_extra`, default `data/profile/approach_extra.json`); the Profiles and the port add it to the approach. Carothers Center (Line 1) 19.3 m, the Line 4 box end at c 18,590 11.4 m, California (Line 5) 11.4 m.
- Rerun at the phase minimums: one approach still under it: the Line 3 box end at c 23,078, an S-ease on a 53 m curve (about 38 m against 40 m). Levee and the S-eases on 160-500 m curves pass.
- Approach boxes outside the street (Ben: option C): accepted everywhere, each a warning in the Profiles ("Approach box": where it leaves the street, or how much wider it is) and in the 3D issues; 29 found; the 29 where the Deck has no streets stay unchecked.
- The Deck draws its Metro tracks as the 3D build has them (Ben: switch the Deck): the build publishes each line's track offset every 10 m along the whole line with the tube (`params/tube_points`: E, N, tube, offset), and the Deck takes the offset at each point (a 50 m grid lookup), islands and approaches included; lines without published points keep the Deck's own spacing.

## 2026-10-28: answers on the Chronology, stations and the CVG Express (Ben)

- The CVG Express is not a Metro line: a separate entity, the dedicated airport line arriving airside at CVG. Its line file's system is "CVG Express" (and its generator's); the Chronology has it as its own system (`cvx|A|B` keys, its own switch on the map); it is out of the Metro "side platforms on a bored stretch" note; its own platforms (670 ft, 204.2 m, Ben 16 October) are used for its boxes and the 3D offsets (the earlier report took 122 m).
- Line 11's opening segment: Manhattan to Bullock, 1939 (Ben chose Bullock for the tracker's "Ludlow", which is on Lines 8 and 2b); the orphan is gone; Line 11's core.
- Goebel station is now Scholl (station data: Line 11, the Deck's context, the station records). Name history in the station's Chronology note: Goebel to early 1942, Commonwealth early 1942-1946, Scholl from 1946 (Hans and Sophie Scholl; Cincinnati and Covington Munich's sister city). Goebel Park keeps its name.
- Baltimore (Line 3) and Freedom Center (Line 2) restored where they were (the editor's Restore, on the hub's saved profiles); Line 3's original termini (St Bernard to Baltimore) set as Phase 1 (tracker 2B), years not set.
- Pearl Street Trunk: Line 1's first segment stays not set.
- Track year and service year apart: shared track keeps its year (RER B's CVG track 1988) with each route's service year in `services` (RER E 1996); a line running onto older track is exempt from the order rule there, its own new segments still checked. No rule breaks now (3 exempt).
- TRI defaults: the route data's opening year, marked "route data", editable.
- Record now: 0 rule breaks, 0 orphans, 326 segments not set. The hub's records exported to `hub/seed`.
- Girders (Ben): rail to soffit = span / 10 + 0.8 m, at most 3.1 m (7.4 - 4.3 bus clearance: 23 m of span); the span is the opening measured on the face. Wider openings: Harrison (24.2 m on the face) and Garrard line (32.1 m) get a pier in the street built into the arcade (two spans, girders 2.01 and 2.40 m); W 8th a median pier (two spans of about 16.75 m, 2.48 m), so its hump is at most 1.9 m (was 2.4 m). The fascia's crown sits at each opening's soffit; the 3D street spans take each street's girder.
- Flagged (in `context/lines.json` meta `north_viaduct`): no pier on the culvert: Millvale Boulevard (72.0 m, would need 8.0 m), Spring Grove Avenue (50.1 m, 5.8 m), Ford Street (27.1 m, 3.5 m), Colerain Avenue (23.4 m, 3.14 m); and two the handoff did not name, needing a pier in the street or a decision: Western Avenue (the 1904 diagonal, 34.8 m on the face, 4.28 m) and Hopple Street (29.6 m, 3.76 m). Ludlow is the existing underbridge (not on the girder rule).
- Stacked tubes (Ben): prefer one double-track bore where tubes would be stacked (the narrow-street note now says so); where stacked, the tubes' centres are one running spacing apart vertically, the same 3.24 m of ground as side by side (type A lower rail at least 18.84 m down, so deep). The Profiles' crossing rule: the upper floor + 0.5 m above the lower top only where a box is involved; 3.24 m of ground between two bored tunnels (the larger of type A's and type C's).
- Ben will fix RER A Blue Ash at Norwood himself; the Northside viaduct confirmed as drawn.

## 2026-10-28: Deck geometry (Ben: go)

- Widening for the catenary middle masts (`tools/deck_widen.py`, run once): both APEx-side gaps 4.5 to 6.0 m, by side. Along APEx north approach 3 from the CUT north throat: west side to about 1,250 m, switching over the curve (1,250-1,650 m) to the east side to Queen Street, switching back over 3,250-3,900 m to the west side; tapered over the first 150 m and the last 200 m (toward Ludlow). The widened side's pair moves 3.0 m out, APEx 1.5 m; the opposite face stays. R5 follows the west pair where it runs with it; the Indianapolis pair fades out of the shift as it leaves for the upper deck. 15 tracks moved; the north arch viaduct polygon grows by the moved tracks' 4.2 m deck edge. Checked: 6.0 m on both sides where the pairs run alongside.
- MT (SMV0032) and J1 (S056), Hopple to their north ends: near edge 2.3 m off the widened faces (layout edits, undoable on the Deck); MT moves up to 21.8 m, J1 up to 6.6 m. The Millvale cross streets (18 of SMV0001-0024, not 0005/0006) now end at the moved MT.
- J1 against Mill Creek / I-75: the Deck has the Mill Creek culvert only south of Millvale (500 m or more from J1) and no creek channel or I-75 north of Hopple, so J1's room against them is not checked. The bend at J1 / Queen is handled by the 2.3 m offset only (the curve itself not pushed north).
- Frontage streets for the arcade shops, Bank to Hopple, both sides (deck.json S080 west, S081 east): 15 m (4.5 sidewalk + 2.4 parking + 3.4 one-way lane + 2.4 parking + 2.4 sidewalk), pedestrian today with a 6.1 m fire lane; direction not set. Blocks and plots crossed by the widened deck or the frontage streets are not re-cut (the Deck draws them under).
- Station 3D: steel lattice middle masts in both gaps every 85 m (about every fourth pier) where the gap is 5.9-12 m, carrying the lattice girder (7.7-8.6 m over the rail) between the masonry pylons; 66 masts.
- Pipeline rerun (deck_tie, 3D): station positions and Line 11's levels moved with the rebuilt alignments (Line 2b and Line 4 stations up to 15 m along, Line 11 rails down 4.5 m from Taylor to Park Place, likely the 3.24 m gap between bored tunnels at its crossing near Arsenal, not yet traced; the Line 5 approach straight 16.6 m, was 14.5). Records exported to `hub/seed`.

## 2026-10-28: Ben's artifact edits brought into the hub

- Before publishing, the Profiles artifact's saved profiles were compared with the hub's: Ben saved Line 1 (21:43 UTC) and Line 2 (21:51 UTC) on the artifact on 27 October after the hub's seed was read, and the hub never had them (grade points, structure overrides, station grades and shifts). Merged into the hub: Line 1 as saved on the artifact; Line 2 as saved there with Freedom Center restored. The Deck layout on the artifact is the hub's starting version (2463), unchanged. Pipeline rerun; Line 1 now has 2 grades over the limit, max 68.9 per mille (Ben's profile). Approach straights: Carothers Center 19.4 m, the Line 4 box end 14.4 m, California 16.6 m.

## 2026-10-28: published to the artifacts (in error)

- The claude.ai artifacts are retired (Ben); this publish should not have happened. No further publishing to them.

- Rail Profiles version 40 (with the Chronology as `chronology.html` beside it, sharing the Profiles database), Mill Creek Deck version 142 (layout record 2464), Station 3D version 8 (38 parts and the summary). Records from the hub (`hub/seed`); procedure in `hub/README.md`.
- Station slides dropped by the pipeline: Ben's 27 October slides on Line 1 (Burnet North 15.5 m, Central Ave 61.0, Levee -61.0, McAlpin 13, Pennsylvania Station 61.0, Stratford -54, University -61.0) and Line 2 (Eastside -21, Garfield -16, Glenwood -61.0, Rivercenter West -12.5, St Bernard -27.5, Zoo -2) are on platforms placed on the Deck, where the Deck's position wins (no slide). To keep one, move that platform on the Deck.
- Fixes found while publishing: the 3D build had lost its streets (the approach-box street check reused the name), now 2,697 again; the page's summary record no longer carries the Deck's tube points (it was 1.3 MB, over the 256 KiB document limit); the Chronology and Deck pages work outside the hub (relative files, read-only Chronology without a database).

## 2026-10-29: Chronology fixes (Ben: "something is wrong with the RER")

- TRI branches did not reach their trunks: each route only started at its own first station, so the stretch from the junction was missing (Blue Ash began 1.5 km past Xavier; RER C's branches and its trunk did not meet at either end). The routes' paths meet exactly at their ends, so `tools/chronology.py` now joins them there: a station within 200 m of the meeting point is the junction (Xavier, Covington Union, Latonia, Edgewood, South Cumminsville), else a junction point named after the nearest station (Western Hills, Anderson Ferry, Beechmont, Mansion Hill and Crescent Springs junctions; the Kenton stem's own), drawn as part of the line, not as a station. Every TRI route now reaches its neighbour. The 24 new segments take their route's opening year ("route data"). RER E Williamstown is a 1.2 km stub with one station in the route data: nothing to draw past it.
- Two different TRI stations shared a name, and so one opening year: Western Hills (the Cumminsville stem's, and the Westwood branch's 5.4 km out) and Dent (RER A Westwood, RER D 1.6 km away). The outlying ones are now "Western Hills (RER A Westwood branch)" and "Dent (RER D trunk)"; their segments' years carried over. (Metro stations of one name far apart, e.g. Bank, Ft Wright, Langdon Farm, are left: interchanges.)
- The Profiles' Chronology band uses the Chronology's route list, so the two agree.
- Year colours: Plasma, 1905 to the end of the "Network as of" scale (2030).
- Record: 0 rule breaks, 0 orphans, 326 segments not set (all Metro).

## 2026-10-29: tunnel drives between stations (Ben: "between-station drives not working"; the Fort Mitchell screenshot)

- A tunnel between two stations is usually too shallow for a shield near each station and boreable in the middle. "Box to box at any length" only counted when the whole stretch was boreable, so a short middle (under 300-400 m) went cut and cover, even below the cut-and-cover limit. Now the only drive between two anchors is bored at any length (the station boxes carry on through the shallow ends until the tube has its cover). Drives join across spots with too little cover up to 50 m long (bored through, flagged: the profile should dive); a longer spot stays cut and cover (flagged) and splits the drives, each then at least the minimum drive.
- A station is one type, from its depth at the platform centre (Fort Mitchell, Line 6, alternated between deep and cut and cover point by point).
- A drive is one type: deep if it reaches a deep station or runs a whole drive below 18.29 m, else shallow shield (no switch partway; Kyles Lane to the valley is deep tunnel throughout).
- Result: 139 station-to-station tunnels bored (was 90). Still cut and cover below the limit, flagged: Line 1 at 2+984, Line 3 at 21+158, Line 5 at 28+916, Line 7 at 2+442, Line 10 at 17+838 (separate short drives; the profile has to rise or the drive be longer). The other mixed stations and shield/deep switches left are Ben's painted stretches.
- Same rules in the editor (`data/profile/profiles.html`) and the port (`railsim/metro_profile.py`); the test follows the new rule.
- Follow-up (Ben: "it's still doing it", Line 1 Finneytown to Center Hill): a low-cover dip longer than 50 m still split the drive. Now every boreable stretch between two anchors is one drive, joined through low-cover dips of any length (bored through, flagged: the profile should dive there); a shallow end next to a canon or river tunnel runs on as tunnel. The only cut and cover left inside a station-to-station tunnel is the station boxes carrying on until the tube has its cover, and the boxes where the track spacing changes. 168 station gaps bored (was 90 before these fixes); what still alternates is next to Ben's painted stretches (Line 4) or at real portals (the line comes out into a trough or at grade between stations: Lines 5, 6, 7, 13).
- Follow-up (Ben: Gray, Line 1, "still having trouble with one type per drive"): east of Gray only 34 m was deep enough to bore, then 780 m about 10.0 m down (a few cm short of shield cover); the 34 m became a drive with an approach box, then cut and cover, plus a 2 m shield sliver because the approach started one sample past the platform. Now a gap between two anchors is a drive only where the drive is most of it (longer than its too-shallow ends together), else the whole gap is cut and cover; the approach box starts at the platform end. West of Gray the drive from Winton Hills (a deep station) is deep tunnel throughout, bored through about 1.3 km just short of cover (flagged: the profile should dive).

## 2026-10-29: elevated structure in the Rail Profiles (Ben)

- Elevated stretches now draw the structure they need (Rail + box and Box views): piers every 25 m (drawing value, as the 3D view's normal viaducts), kept 7 m clear of the lines crossing under them; over a river, equal spans of at most 120 m with piers to the surveyed bed. A span up to 40 m is a girder under the deck, rail to soffit span/10 + 0.8 m (Ben's girder rule: 3.3 m for 25 m); a longer one is a through truss over the rail (span/8 deep) with the deck (deckDepth, 1.5 m Metro, 2.0 m RER) under it: the Ohio on Line 6 is three trusses of about 108 m. The tooltip gives the span, the soffit and the girder or truss. Clearance checks still use the deck depth setting.

## 2026-10-29: platforms both ways (Ben: "it should run in both directions; the more recent one wins")

- `tools/platform_tie.py` and the hub's `platform_tie` job (on every profile save, before the Deck tie): a Profiles slide on a station drawn on the Deck becomes the Deck platform's offset along its line piece (`stations[id].s[pid].o`); the slide is cleared and the Deck tie puts the station at the moved platform. Per platform, the side that moved it wins; both moved: the more recent record. The sync record `params/platform_sync` (each platform's Deck offset after each Deck tie) tells which side moved it. The Deck's export now carries each platform's station id, line piece, offset and slide limit.
- Tested on the hub: Line 5 Sassafras slid +20 m in the Profiles -> Deck offset 96 -> 116 m, station 10+050.2 -> 10+070.1, slide cleared; slid -40 m and then moved on the Deck before the hub ran -> the Deck won (130 m, 10+084.1); put back.
- The hub page names each job (it showed every job but the 3D build as "Deck tie").

## 2026-10-29: Metro grade limits by building phase (Ben)

- 5% everywhere; Phases 1-2: a straight stretch underground up to 6% as a warning (as before); after Phase 2 (Phase 3 on): up to 6% on a straight, allowed; after Phase 3 (later): also up to 6% on curves over 500 m (train-averaged radius); above 6% always an error. In the structure record's phases (`grade_max`, `grade_straight`, `straight_warn`, `grade_curve`, `curve_radius`), editable on the hub page; each stretch takes the phase it was built in (Chronology). The grade check, the grade-with-curve check and the grade labels use the strictest limit over each stretch; the flags say which rule applied. The Python port's summary still counts grades over 50 per mille.

## 2026-10-30: review of the Profiles rules (Ben: drives, depths, stations, gradients; full code, not per station)

- Drives: between two anchors (station boxes and approaches, portals, canon, rivers) every boreable stretch is one drive at any length; the station boxes carry on through the shallow ends; where those ends together are longer than the drive the gap is cut and cover; the approach box starts at the platform end.
- Depths: nothing is bored with less than one diameter of cover (a stretch inside a drive that shallow is cut and cover, flagged: the profile should dive; the drive carries on either side); deep tunnel only where the rail is below deep_from for a whole drive, or next to a deep station; the rest of a drive is shallow shield. A painted Deep tunnel shallower than deep_from is a warning.
- Stations: one type (the depth at the platform centre, or the paint there, for the whole platform) and one phase and tube (the earlier-opened of the segments either side, from the Chronology).
- Gradients: the grade between vertical curves is the steepest grade on the drawn rail (a vertical curve only blends two grades), so the checks use those. Limits by building phase (29 October). Sustained against localized (Ben, 30 October): a stretch over the limit is an error only where the grade averaged over the sustained length (a setting, default two platform lengths: 243.8 m Metro, 408.4 m RER) is over it too; shorter is a warning (amber on the profile, red only where sustained). The same for grade with curve (averaged with its curve allowance). The flags quote the rule of the binding point. Across Metro Lines 1-14 now 10 errors and 20 warnings.
- The Python port (railsim/metro_profile.py) follows the same rules (station type and phase, paints, minimum cover, deep, sustained grades in its summary); its types agree with the editor's to 1 sample in about 2,500 on Lines 3 and 6, exactly on Lines 10 and 13.

## 2026-10-30: one type per drive (Ben: "where is it switching for no reason in the middle of a drive?")

- Ben's rules: one type per drive, unless it comes out to at grade (a portal); otherwise a change of depth class is flagged ("the drive changes depth class"). A drive too shallow somewhere to bore: if it is shallow enough for cut and cover throughout, the whole drive is cut and cover; otherwise it stays bored as a whole and the shallow stretch is flagged (the profile has to dive there). A box coming up from a bore to a portal is a tunnel transition, not flagged. At a portal the old depth rule holds (deep only where a whole drive's length is deep).
- Painted Shallow shield and Deep tunnel now re-grade the ground over them like painted cut and cover (tube top plus one outside diameter of cover). Two fill bugs fixed on the way: in the editor the fill did nothing (a loop variable hid the fill array), and the fill's 50 per mille taper started from paints where the ground was already high enough (a Deep paint under 20 m of ground raised the ground up to 15 m, 300 m away, on Line 1 at Kenard).
- The port keeps the ground at the editor's precision (32-bit), so depth ties (Brightleaf sits exactly at the 4.6 m trough line) come out the same.
- Checks over every line: shield/deep switches inside a drive 53 -> 10, all at Ben's paints; too-shallow switches 35 -> 5, all CVG Express portal transitions; every low-cover bored stretch flagged. Editor and port types agree on every sample of Lines 1-14 except two 8 m approach-box ends, where the port read an older approach_extra file than the hub's latest 3D build.

## 2026-10-30: river crossings are sunk boxes (Ben: Metro_River_Crossings, and his answers)

- Every Metro and RER river crossing in tunnel is a sunk double-track box, a type of its own ("Sunk box", not a paint; river beats a tunnel paint), whatever the land tunnel. Only the CVG Express bridges the Ohio. Band (Ben's answer 8): the roof from 5 m below the bed to 3 m above it, Metro rail bed - 10.0 to bed - 2.0 m (roof 4.0 + 1.0 m over the rail), RER bed - 11.6 to bed - 3.6 m (6.6 m); the upper limit at every point under water, the lower on the flat bottom only (bed within 1.0 m of the lowest). Where the roof stands above the bed the bed is made up over it (clay, canopy, riprap: `riverCap` 1.0 m, a drawing value, drawn earth-coloured); on the Ohio (canon `navigable`) the made-up bed keeps 12 ft (3.66 m) of water at normal pool. Settings riverBoxTop, riverSink, riverRise, riverFlatTol, riverClearWater, riverCap replace the old margins (bed - 7.5 / 9.1 m).
- The box anchors like a station: a short cut-and-cover transition at each bank where a bored tunnel meets it, the length of a station approach (the tubes' spacing to the box's 3.90 m; at least 40 m where the spacing is the same, as the bore lines). The land tunnel type follows the Chronology phase.
- Flags: a crossing above the water (one flag per river), the box above or below its band, the made-up bed too high for the channel. The solver holds the box inside the band (at its top, or under the clear-water level). Only points under water (bed below pool) count; the RER-3 and RER-C river ranges beside the embanked covered way are the shore, not crossings (as before).
- Saved profiles, the river level only (Ben handles the approaches): Line 6 Ohio 141.3 -> 125.85 m (west bend point 60 m onto the bank so the curve stays under the band) and Licking 145.0 -> 128.75 m; RER-5 and RER-E trunk Ohio 141.3 -> 119.75 m; RER-C CVG Ohio 175.1 -> 122.75 m; RER-3 and RER-C trunk Little Miami 123.70 -> 124.13 m (0.4 m too deep). Lines 1, 2, 3, 8, 10, 11 and RER-2, 4, B, D were already in the band. The canon and handoff documents wait for Ben's sign-off.
- Station 3D: the sunk box is drawn as a box (roof 5.0 m Metro, 6.6 m RER over the rail).
- Follow-up (Ben: "make sure the sunk box has the right dimensions"; "line 6 is messed up, the water and riverbank are not matched"):
  - The sunk box now takes its section from the structure record (Metro: the canon box, 3.90 m track centres, 7.90 m inside, rail 1.0 m above its underside, 4.0 m to the roof underside) plus the sunk unit's 1.0 m roof (setting riverRoof, assumed): 5.0 m rail to roof top; RER the 6.6 m box (the envelope). The band, checks, made-up bed, Station 3D and the legend all use that one box (the separate riverBoxTop setting is gone).
  - The channel is marked over each sunk box: a dimension from normal pool to the bed over the box (the made-up bed, else the flat bottom), labelled, red when the made-up bed leaves less than the navigation depth; on the Ohio the 12 ft navigation depth is dashed across the water.
  - River ranges: the Deck rebuild (tools/rer_deck_routes.py) carried them over by the chainage map, which drifted when a path moved: Line 6's Ohio was 78 m (north bank) and 52 m (south bank) east of the riverbed in the terrain. Every rebuild now recomputes them from the river outlines (`river_ranges`; centreline rivers such as the Little Miami keep theirs); `--rivers` recomputed every route now (Line 6 Ohio 10,762-11,108 m; the others moved 1 to 20 m). Line 6 Ohio and RER-5 Ohio bend points reset to the true water edges.

## 2026-10-30: station approaches everywhere a tube meets a box (Ben: Line 2 McMicken, "still failing the tunnel-station approach")

- Four gaps, fixed in the rules, not per station: (1) canon tunnels (Line 2's deep tube up Mt Auburn into McMicken) carry no depth class, so the approach rule did not see them as bored: a canon tunnel now counts; (2) a station in a canon section had no station mark at its centre, so it was skipped (Line 3 Government Center and Convention Center, Line 5 Pennsylvania): every platform sample is now the station's; (3) a tube station meeting a box had no rule (Line 7 Krohn): the spacing now changes inside the box from the platform end; (4) approaches were placed once, before the second resolve, which can turn a cut-and-cover gap beside a station into a drive (Lines 11, 12, 14): they are placed in passes until none is missing.
- Check over Metro Lines 1-14, 2b and CVG Express: every tube-box contact is inside an approach except where the Phase 2 bore meets a box (both 3.90 m, no spacing change). Editor and port agree on every sample of Lines 1-14; test added.
- Follow-up (Ben: VA Medical Center, "something is now wrong with the spacing"): with every platform sample now the station's, a station painted Shallow shield was taken by its unpainted type (cut and cover) and got approach boxes into its own tubes. The station's type for the approaches is now its paint, else the rules'; a painted tube station meeting tubes gets none, meeting a box gets the change inside the box. The test checks the types as drawn (paints included).

## 2026-10-31: tube form, low cover, and the issues list (Ben: "there should never be double-track to double-tube boring for no reason"; Henry Clay to Ft Wright "cannot be like this"; "all of your warnings look exactly the same")

- Tube form (Ben chose "ends + paint"): a drive whose two ends are both double track (a side-platform or plain box, the sunk box, a portal, the line's end) is the double-track bore where it has the bore's cover (15.5 m to the rail) all along; shallow only at its ends, the boxes carry on to where it has it. Twin tubes where an end is an island station or a tube station of a twin-tube phase (Phase 1 deep stations), or where the bore lacks cover inside. Applies in every phase: Phase 2 bore lines go twin into an island or Phase 1 tube station. New paints Twin tubes / Double-track bore / Auto tubes (saved as `tf` in the profile) decide where painted; a painted bore without its cover, and a spacing change inside the tunnel (bore meeting twin tubes or a twin-tube station), are flagged. The approaches follow the form (no approach box where the bore meets a double-track box). Line 2 Holmes to Meinken is now the bore with no approach boxes; on Line 3 every drive still touches a Phase 1 deep station, an island or lacks 15.5 m, so it stays twin unless painted. Station 3D and the Deck take the form from the editor's samples (harness `tubeAt`).
- Low cover (Ben: "switch to cut and cover if it passes limits, or it is forced to be regraded"): a drive too shallow to bore partway (less than one diameter of cover) and too deep elsewhere for cut and cover: the shallow pockets are cut and cover when every bored piece left is still a whole drive (the phase's min_drive), else the drive stays bored and gets a Regrade error. Regrade (button on the issue) lowers the rail over the drive to the tube's cover plus a margin as straight grades (the lower hull of the cover line, at most the grade limit less 2 per mille) between the platform ends, lowering a station in the way (not a canon or locked one); one undo. Across Metro: 16 drives on 12 lines need it, each cleared by Regrade (Line 3 Henry Clay to Ft Wright: up to 5.3 m lower, Ft Wright 1.4 m; Line 9 East Westwood 7.1 m; Line 14 St Xavier 6.6 m). Not applied to saved profiles: Ben presses it.
- Issues list: errors, warnings and notes have a coloured bar (red, amber, grey); each kind has its own coloured tag and a filter chip (kept in the browser); sorted errors first, then by chainage. "Profile set" on each line (saved as `ready`): crossings with a line not marked set are listed apart, closed ("Crossings with lines not set yet"), and get no markers; context structures (CUT, Norwood) stay with the line. Canon depth notes are warnings now.
- Port: the same tube form and low-cover rules (flag kinds "spacing change in the tunnel", "painted bore lacks cover", "regrade", "low cover, cut and cover"); tests added.

## 2026-10-31: the tunnel engine rebuilt on engineering rules (Ben: "the drives need to be consistent ... approach it from a real engineering perspective")

- The cause of the repeated switching: rules layered over passes (point classes, drives, approaches placed in passes, tube forms, slivers absorbed), each fix interacting with the others; and a station rule using the deep-station depth (18.29 m, which only decides lifts and escalators) instead of the cut-and-cover limit, so Phase 1 stations between 12.19 and 18.29 m (Paycor 16.95 m) were drawn as impossible boxes.
- One pass, the same on every line (editor `solveTypes`, port `_stretch_types`; they agree on every 2 m sample of Metro Lines 1-14, 2b and the CVG Express):
  1. Stations by the phase's cut-and-cover limit (cc_max): at or above it a box station, deeper a mined station (deep or shallow shield by deep_from, for access only). Paint and open/canon box sections still decide.
  2. Boxes are the only break points: box stations, the sunk box, portals (open track), canon box sections, painted cut and cover. Short open slivers inside a tunnel (the ground dipping) are tunnel.
  3. Each stretch between two of them (in one phase) is decided once: cut and cover end to end when within cc_max throughout with no mined station and nothing forced (canon tunnel, tube paint); otherwise one bored drive through any mined stations: one tube form (the bore between double-track ends with its cover, else twin), one depth class (deep through a deep station or mostly below deep_from; canon or paint where they say), the boxes at its ends carrying on until the tube has one diameter of cover, the approach boxes (spacing change) there.
  4. Low cover inside a drive: a box (a working shaft) only where the drives either side stay whole (min_drive); else a Regrade error.
  5. A leftover drive shorter than min_drive with no mined station: beside the sunk box it is the bank works (the immersed tunnel's land end is cut and cover in a cofferdam; a note); shorter than the boxes round it, an error where that cut and cover is past its limit (raise the profile, or lower it for a whole drive); else one short bored piece (a note). Never box > tube > box inside a stretch.
  6. A tube paint over a box the rules need is a warning (the paint still wins on the drawing).
- Line 3: Paycor is a mined station; one deep drive from the Fort Washington Way portal through Paycor to the Ohio bank box, and from the far bank through Mutter Gottes and Covington Union. Line 2 Holmes to Meinken: twin tubes (both islands). Check over all Metro lines: no box inside a drive, no short tube between boxes, no slivers except at Ben's paints (Line 1 deep paints over the Ohio bank boxes, Line 4's 13 m shield paint at 20+200), all flagged.

## 2026-10-31: the audit and its fixes (Ben: "audit the whole system"; "deep-bore is a thing when it's TBM")

- Audit in `claude/Profiles_Audit_2026-10-31.md` (measured on Ben's export). Built A to E and F there: unbuildable stretches
  hatched with Regrade/Raise and "Fix unbuildable"; the two limits drawn; running tunnels by method (shield Phases 1-2, deep
  bore by TBM from Phase 3, `phases.tbm` in the structure record); end boxes carried through every low-cover spot within the
  box limit; the Paints card; "Check all lines" and a test; the Python copy on the hub's records and the Chronology's station
  list. Tests: 64 pass.

## 2026-10-31: code audit, group 1 (Ben: "yes let's start on them")

- Audit in `claude/Code_Audit_2026-10-31.md`. Done from its first group:
  - Hub: `Store.update` reads and writes under one lock (two saves at once no longer lose one); the pipeline checks every
    versioned write and says when a record was saved during a tie; `Store.emit` reports a failed listener instead of hiding
    it; run logs are kept whole (the page shows the tail); `harness.js` fails the build on any page error and on an unhandled
    exception, instead of handing over samples from a half-loaded page.
  - Derived files out of git: the pipeline writes the Deck's live export to `hub/work/rer_routes.geojson` and the viaduct
    parts to `hub/work/derived/deck/viaducts.json` (the hub serves derived files over a site's folder), and no longer writes
    `station_platforms.json` and `approach_extra.json` into `data/profile`. `python hub/hub.py export` (and the Export button)
    refreshes the four repo copies. `rer_deck_routes.py` reads the hub's export when there is one, else the repo's.
  - Profiles page: shared `stationAt`, `rangesOf`, `cutRange`, `pathAt`, `tubeOfKey`, `absorbShort(free, edgeOk)` replace
    the copies; `phaseRules(c, ph)` and `gradeLimitAt` look the phase up once; `fmtCh(1999.6)` is 2+000; dead code out
    (identical branches, unused parameters, `S.hoverXY`); the editing hint names the new tunnel labels.
  - Python copy: `rail_at` for one chainage is pure Python with a bisect (no numpy per call); `rail_grid()` evaluates the rail
    over the whole line once per design and the engine, the RER types and the fill read it; the solve went from 9 s to
    0.7 s per line and the test suite from 280 s to 62 s. The types cache is keyed by value (`_solve_key`: levels, platform
    grades, bend points, paints, tube forms, a ground version, settings, stations), not by `id()`.
  - Editor and port still agree on every sample of every Metro line (Ben's export); 64 tests pass.
