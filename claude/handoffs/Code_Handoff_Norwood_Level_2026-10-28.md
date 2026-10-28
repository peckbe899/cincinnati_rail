# Handoff to the code session: Norwood Central track level

Chat session, 28 October 2026. For the hub repo github.com/peckbe899/cincinnati_rail, branch claude/stoic-cray-fqf881. The chat session has not touched the repo.

## 1. What's wrong

The Norwood Central tracks and platforms are set at 178.0 m. The ground around the station is about 191 m (map 3 raster: median 191.0 m within 50 m of the platforms, 190.8 m at 100 m, 191.4 m at 200 m). That puts the cut about 13 m (about 45 ft) below the street.

Ben never gave 178 m. It came from an earlier chat session's North Viaduct Plan ("about 178 m, roughly 7 m under the street", marked "approximate, from the ground data"). It contradicts his ruling in the Norwood log (v112): platforms partly sunken, roofs at street level, concourse above them (Baltimore Penn, not New Haven), with the entrance from the building climbing slightly to it.

## 2. The new level

- **Rail and platforms at Norwood Central: 185.5 m.** This is a drawing value derived from Ben's ruling: ground about 191 m, minus about 1.2 m of platform and about 4.3 m of canopy and roof, which puts the platform roofs at street level.
- **Approach from the west (Ben chose option A, 28 October):**
  - keep the existing descent: from the ground at s 3,220, 2% down to 170.0 m (about s 3,460), which lets the Transvalley cross over ORR and APEx at s 3,431-3,590;
  - then climb at one steady grade from 170.0 m to 185.5 m at the west end of the Norwood platforms;
  - level through the station.
- The west end of the platforms is about s 4,438 by the chat's reading, which gives about 1.58%. Compute it from the `nw_plat` features in the Norwood frame instead of using that number.
- **Grade:** Ben has ruled this approach acceptable ("2% gradient for a distributed power EMU is nothing"). Don't flag the 2% descent or the climb against the 1.5% APEx maximum here.

## 3. Files that hold 178 m for Norwood

| File | Where | Change |
|---|---|---|
| `tools/make_profile_context.py` | lines 144-166 | `S_TOP` becomes the platforms' west end in frame s; climb grade = (185.5 - 170.0) / (S_TOP - S_LOW); level value 185.5 in `nw_z`; `plats` at 185.5; update the comment, the print line and the block note (drop "levels approximate, from the ground data"; cite Ben's v112 ruling and his 28 October choice) |
| `tools/station3d/context3d.py` | line 299 | Norwood platforms 178.0 to 185.5 |
| `design/platform_track/extract/combine3d.py` | lines 99 and 238 | the Norwood marker and fill value 178.0 to 185.5, and their notes |
| `design/platform_track/extract/render3d.py` | line 181 | the 178.0 platform level to 185.5 (line 101's axis limit of 178 may also need raising so the platforms stay in view) |
| `tests/test_core.py` | lines 516-521 | expected level 185.5; cut floor 185.5 - 0.8 = 184.7 |

Then regenerate the Profiles context and Station 3D context, and rerun the tests.

## 4. Report back to Ben

Raising the cut floor about 7.5 m changes the clearances for the lines under and beside it. Report each, with the clear distance and what's needed:

- **Line 14:** passes under the tracks. The test notes its station is already 4.7 m over the tracks' level against the 7.8 m needed.
- **Line 3:** Norwood Central, cut and cover, rail 183.18 m (ground 189.97 m). It is now 2.3 m below the APEx rail level.
- **Line 4:** Norwood Central, rail 171.6 m.
- **RER 5 and RER E:** Norwood Central, cut and cover, rail 168.6 m. RER 5's station ground reads 177.2 m, the old cut floor, and should follow the new one.
- **RER A (Blue Ash):** Norwood Central at grade, rail 189 m.
- **The Transvalley crossing** at s 3,431-3,590: confirm it still clears ORR and APEx by at least 7.3 m (it should, since the descent is unchanged).
- **The concourse and Montgomery viaduct:** with APEx wires at 20-22 ft (6.1-6.7 m, fact tracker 1), they land about 193-194 m, 2-3 m above the street. Report if anything in the repo conflicts.

Log the change in `claude/Station_3D_Log.md`.
