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
