# Station 3D tool: brief

Written 2026-10-26 at the end of the Fountain Square session, for a new session to build from. Ben's project rules apply throughout (fact tracker first, push back when something is unrealistic, plain language).

## Goal

An interactive 3D station modeller: a new artifact page (option B as agreed). The page takes its context (lines, levels, platforms, streets) from Ben's two editors and lets stations be designed inside it. The approach borrows from Metro Station Designer and STATIONflow:

- multi-level building;
- stairs and escalators that size themselves from the rise;
- checks on the design.

The viewer must be movable to look from any angle. Animation is not wanted. Start with Fountain Square.

## Sources

### Rail Profiles editor

The long-section editor sets gradients, depths and platform positions: https://claude.ai/artifact/A5XH4264dpWHdPdDKZgDsG

- Published files:
  - `lines/index.json` and `lines/<Line_id>.json` (Lines 1-14, 2b, CVG Express);
  - `rer/lines/RER_1..5.json`, `rer/canon.json`;
  - `network.json`, `rer/network.json`, `rer/metro_rails.json`.
- Database `alignments/<Line_id>`, one document per line, holding Ben's saved edits:
  - `platform_m`;
  - `stations` (name, c chainage, ground, rail, depth, type);
  - `st` (station rail levels), `sg` (platform grades);
  - `pvi`, `ovr` (painted structure, [c0, c1, type]), `so` (platform offsets), `del`;
  - `summary`, `updated`.
- `config/settings` and `config/settings_rer` are empty today, so the page's built-in defaults apply.
- Rail levels between control points come from the page's own code (vertical curves). The page exposes `window.railProfile`: `railAt(c)`, `typeAt(c)`, `platforms()`, `align()`, `exportGeo()`, `kml()`.
- Metro structure sizes, measured from the rail:
  - box: 1.0 m below, 4.6 m to the top, 0.6 m cover;
  - twin tube: 0.68 m below, 4.08 m to the top, 4.76 m outside diameter;
  - double-track bore: 3.2 m below, 5.8 m to the top, 9.0 m outside diameter.
- RER structure sizes: box 6.6 m above the rail, 1.0 m invert; bored tube crown 7.5 m.

### Mill Creek Deck

The plan editor holds streets, blocks, lines and station platforms: https://claude.ai/artifact/L81dVQSV8THSWai2LhZhcv

- Published files: `basin.json`, `structures.json`, `tracks.json`, `hwy.json`, `norwood.json`, `airport.json`, `plots.json`, plus map tiles.
- Database `deck/layout`, one document:
  - `streets`, `blocks`;
  - `transit`: line polylines;
  - `stations`: platform moves, island or side, deletions; keys like `metro:<name>:<E>:<N>`;
  - `plots`, `plotOps`, `updated`.

### Coordinates and existing station work

- Both editors use the same metre grid: UTM zone 16N by their numbers (EPSG:32616, still to confirm).
- Fountain Square's halls, passages, flights, elevators, gates and entrances are in the Fountain Square model:
  - repo `peckbe899/cincinnati_rail`, `stations/fountain_square/`, once pushed;
  - until then, `fountain_square_model.zip` in the Fountain Square session.
- That model uses its own frame turned 11° with the street grid; `fs_kmz_layout.py` converts to it.

## The constraint

A page can read only its own database. None of the runtime capabilities (artifact, assets, comments, db, downloads, files, mcp, room, sample, user) reads another artifact. So the 3D page gets the editors' state through a sync, run by a Claude session with ArtifactData and Artifact read, either on request or on a schedule. Whether scheduled runs can reach artifacts is untested.

The sync method:

1. Run each editor's own page headless (Playwright; Chromium is preinstalled) from its published files.
2. Give it a stand-in for `claude.use('db')` that serves the saved records.
3. Read the geometry from the editor's own functions (`railProfile.railAt`, `typeAt`, `exportGeo`; the Deck's computed lines and platforms), so the 3D view matches what the editors show.
4. Write one snapshot per station area into the 3D page's database, with its time.

Steps 1 to 3 now work for both editors (2026-10-26). The scripts are in `design/platform_track/extract/`: `deck_headless.py`, `profiles_headless.py` and `combine3d.py`. Section 10 of `claude/Platform_Track_Design_Brief.md` explains them.

- **What they give:** every Deck track with its plan and rail level, and each level's source.
- **Where the levels come from:**
  - Metro and the TRI core take the Profiles page's levels.
  - APEx, the lower level and the north trunk take the Deck's level marks. The Deck publishes no level per point, so those tracks are interpolated between the marks.
- **Conflicts:** where the two editors disagree, both levels are listed.

## Phases

1. **Sync** for Fountain Square, about 400 m around it: lines (plan, rail level, structure type), platforms (extent, island or side, level), ground and streets.
2. **The 3D page** (three.js from cdnjs or jsdelivr):
   - ground, streets, every line at its real structure size, and the platforms;
   - a free camera (Ben, 2026-10-26: "the 3D viewer should, ideally, be moveable, to view from any angle"):
     - orbit, pan and zoom from any direction, including below the street and looking up from underneath;
     - the orbit centre can be set on any point clicked;
     - the camera position is remembered per viewer;
     - named views can be saved and shared in the page's database;
   - drawn as true 3D with a depth buffer, not the painter's order the Python renderer uses, so it stays correct from every angle;
   - keeping it readable from any angle:
     - see-through floors and a cutaway plane;
     - showing one level alone, or all levels;
     - labels that always face the camera;
   - presets as starting points and for exported images: plan view, an isometric preset matching the Republic drawings, and the three views from the angle analysis (SE 139° at 12°, SW 229° at 32°, SSW 204° at 28°). With the camera free, the angle analysis now only picks these presets;
   - PNG and glTF download;
   - floors shaded a step darker each level down (Metro grey, TRI pink) and elevators drawn as at Republic, as agreed for the Fountain Square view.
3. **Station design in the page:**
   - halls, passages, stairs (rise/run 0.67) and escalators (30°) sized from their rise, elevators, gates and entrances, saved in the page's database;
   - the Fountain Square model moves in as the first station.
4. **Checks in the page:**
   - every flight lands, everything is reachable, step-free routes exist;
   - structures clear each other by the Profiles editor's rules;
   - later: the rush-hour Level of Service test and a digging index.

## Data issues found 2026-10-26

- **Metro platforms:** the editors use 400 ft (121.92 m; an editor note says Ben changed it on 23 October, from 500 ft). The Fountain Square model is still at 500 ft, as locked on 5 October. Confirm which stands.
- **TRI platforms:** the editors use 200 m, against the 670 ft (204.2 m) locked on 5 October. The CVG Express in the editor uses 204.216 m.
- **Levels at Fountain Square in the editor:**

| Line | Rail level | Depth | Structure |
|---|---|---|---|
| Line 1 | 160.9 m | 7.2 m | cut and cover |
| Line 2 | 153.4 m | 14.27 m | cut and cover |
| RER-1 | 156.56 m | 12 m | cut and cover |
| RER-2 | 140.59 m | 27.51 m | deep |

- **A clash:** where A/D crosses under Vine, RER-1's box (155.56 to 163.16 m) overlaps Line 2's (152.4 to 158.0 m) by 2.44 m, unless that crossing hasn't been solved yet. The Fountain Square model's depths are drawing values (A/D at 28 m, B at 42 m) and don't match the editor.
- **Line 7** has no saved alignment in the editor.

## Open decisions for Ben

- **Stacking:** stacked, spread or half-stacked platforms for the 1903-1913 lines (paused 7 October). At 400 ft, Line 2's platform (121.92 m) fits the 122.85 m clear between the Line 1 and Line 7 boxes with 0.93 m to spare.
- **Platforms at opening:** full length from day one, or shorter and lengthened later?
- **Pan Am Tower:** its shaft was moved north off the A/D caverns. This is a proposal.
- **TRI platform edges:** widen the islands 0.5 m each side (to 11 m and 13 m) so the edge sits about 1.75 m from the track centre.
- **3D view:** SE 139° at 12°, SW 229° at 32°, or SSW 204° at 28°.

## Working rules

- Read both editors' databases freely.
- Change the editors only when Ben asks; they hold his saved work.
- Keep the 3D page's data in its own database.
- Log decisions in `claude/Station_Area_Maps_Log.md`, or a new log for the tool.
