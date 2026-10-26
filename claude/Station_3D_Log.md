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
