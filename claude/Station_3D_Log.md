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
