# 1922 Sanborn plates onto the Mill Creek Deck page: the process

Written 21 October 2026 from the plate 35 and plate 38 work (20 October, page versions 84-87), as Ben asked, and updated after plates 66-70 went through it (page versions 89-90). Paths are relative to the session scratchpad.

## 0. Principles (Ben)

- The 1922 plate is the reference. Fit the plate first, then bend the 1904 sheets onto it, not the other way round.

- Ben's GeoTIFF is imperfect. Use it only as a starting reference (a seed), never as the answer. The image that is fitted and drawn is his raw PNG scan.

- Fit to streets that have not moved or been widened since 1922. Today's OpenStreetMap crossings of those streets are the control points.

- 1922 lives on its own page layer ("Sanborn 1922", tiles_22), drawn over the 1904 layer (tiles_n), never mixed into it.

- Only the 1904 sheets already on the page are bent; no new 1904 sheets are pulled in during this step.

## 1. Stage and prepare (cufp/prep.py)

- Copy the plate's PNG and GeoTIFF from Ben's computer (New Sanborn\PNG and New Sanborn\GeoTIFF). Disk is tight: copy the GeoTIFFs one at a time and delete each after step 1. The transfer limit is 400 MB a file; a larger GeoTIFF cannot come across, and its plate is seeded from street names instead (step 3).

- `python3 cufp/prep.py N "<GeoTIFF path>"` writes:
  - cufp/22-N.jpg, the full-size scan for the readers;
  - cufp/N/png_s8.jpg, an overview;
  - cufp/N/png_alpha_s4.npy, the plate's mapped-area mask;
  - cufp/N/png2tif.json, the seed. SIFT matches between the PNG and the GeoTIFF at quarter scale give a RANSAC homography for the inliers, then a degree-3 polynomial from PNG pixels to GeoTIFF pixels, trimmed three times at 3x the median residual.

- Plate 38's version of this step is cuf38/match.py.

## 2. Read the crossings (reader agents)

- Register the sheet id in sbg/sb.py `find()` and add a section to sbg/INSTRUCTIONS22.md: what the plate shows, its size, the names to expect, what is not a street, and the disk note.

- Split the plate into vertical strips of equal mapped area (cufp/strips.json; six strips for a plate of about 10,000 px). Give one reader agent each strip.
  - Each reader picks every crossing in its strip plus 300 px past each edge, so neighbouring strips overlap.
  - Precision is about 10 px, read from 600-1,000 px crops.
  - Names are recorded as printed, expanded; bends, real ends (not plate-edge cuts) and printed widths are added.
  - Each reader writes sbg/picks22/s22-N_<part>.json and checks it with `sb.py check`.

- Agent limits: run the readers in waves (one plate, six readers, at a time), not all at once.

## 3. Fit the plate (cufp/fit.py; plate 38: cuf38/fit38.py)

- Merge the picks. The same street pair within 60 px counts as one crossing at the mean of its reads; the spread between readers is reported.

- Seed every crossing into the world. The seed is PNG to GeoTIFF pixels (png2tif.json), then the GeoTIFF's EPSG:3857 transform, then EPSG:26916.
  - Without a GeoTIFF, the seed is a RANSAC affine on crossings whose street-name pair is unique both on the plate and in OSM.

- Match each crossing to the OSM crossing of the same two names, within 45 m of the seed. Then fit, seed again from that fit, and match again within 30 m (a GeoTIFF can be 20-40 m off at plate edges; plate 69). Streets renamed since 1922 get an alias (Victory Boulevard = Victory Parkway, Clough Avenue = Crane Avenue). The OSM sources are lph/osm_north, basin/osm_basin and lph/osm_east.

- Leave out streets realigned since 1922 by name (plate 38: Dixmyth, Glenmary, Lafayette).
  - Then drop, one at a time, any control the less-smoothed spline (tps1) misses by more than 6 m.
  - The tps1 test is used because a stiffer field wrongly drops the plate's real edge distortion (Vine on plate 38).

- Compare by leave-one-out error: affine, quadratic, and affine plus a thin-plate spline at smoothing 0.3, 1, 3, 10, 30 and 100. Keep the best.
  - Plate 38 got tps1: 63 controls, leave-one-out 4.75 m, fit 2.3 m.
  - Plate 35 was checked instead of refitted: Ben's GeoTIFF was 3.1 m rms on 30 unchanged crossings and a spline did no better, so it was used as is.

- Outputs:
  - matches (every crossing, its OSM match, residual and whether it was used);
  - report;
  - forward model (pickle: model name, controls);
  - inverse grid (world to PNG pixel on a 2 m grid, npz) for rendering.

- Check where plates overlap: shared crossings should agree within a few metres. Plates 35 and 38 agreed within 2-5 m, and both put Dixmyth/Whitfield 35-41 m from today's, which showed Dixmyth was realigned after 1922.

## 4. 1922 layer (cuf/plates.py, cuf/tiles22.py)

- Register the plate in cuf/plates.py: its image loader (the PNG), its world-to-pixel map (the inverse grid) and an ok() test.

- `python3 cuf/tiles22.py` renders deckpage/tiles_22 (512 px tiles at 0.25 m) plus the index and overview. Where plates overlap, they composite by depth inside their footprints.

## 5. Bend the 1904 sheets onto 1922 (cuf/x1904.py, cuf/tps1922.py)

- `python3 cuf/x1904.py <frames>` places every 1904 crossing (sbg/picks/sNNN.json) with its frame's transform as it stood before the 1922 bend (lph/tps_pre1922.pkl). It then matches each crossing by street names to the same crossing on a 1922 plate within 45 m.

- `python3 cuf/tps1922.py <frames>` adds per-frame displacement splines to lph/tps.pkl.
  - Each frame starts from tps_pre1922.pkl.
  - Trust rule: a frame with 3 or more matches is checked by similarity (6 m); a frame with fewer accepts matches under 10 m. Individual forced matches are possible (Dixmyth/Whitfield on 292).
  - Neighbouring frames' controls are shared at smoothing 0.3 (own crossings 0.05), so seams share one field. They are excluded when forced, or when they differ from the frame's own median by more than 8 m.
  - Zero anchors are placed more than 120 m from any control.

- Crossings are matched on base names, so East and West halves of a street divided at Vine match each other.

- Find the frames under a new plate with cufp/frames_under.py, and run x1904 and tps1922 on ALL bent frames together (old and new): tps1922 rebuilds lph/tps.pkl from tps_pre1922.pkl, so a frame left out loses its bend.

- Re-render the 1904 tiles of those frames: `REDO=<frames> python3 lph/tiles_all.py`. Back up first; tiles_n stays 1904 only.

## 6. Streets from the plate (cuf/build22.py, cuf38/build38.py; a per-plate build script)

- Area: the plate footprint 3 m inside its edge, less areas already taken by earlier plates or kept lines (plate 38: east of Ben's McMicken, less plate 35's area).

- Street pieces come from the merged crossings, bends and ends, placed with the fit.
  - Points of one name are clustered, with an axis check of 25 degrees, so same-name streets in different places stay apart.
  - Each cluster is chained by a minimum spanning tree.
  - Pieces of one street a long block apart are rejoined when the gap runs along the street.

- Earlier streets and blocks inside the area are taken out; streets crossing the edge are cut there. Ben's edited streets (dbread/deck/layout.json) and named keep-lines stay.
  - Everything taken out is saved in the set's removal file, so a reinstall puts it back first.

- Loose ends: each is snapped to its real partner by name, or carried onto the plate street it meets. A second pass carries any end left 1-30 m short of a street (new or kept) onto it when it heads there or is within 15 m, cuts back overshoots past the street it ends at, and joins same-street gaps under 30 m. List what is left with cufp/gaps.py.
  - A snap is skipped if it would leave a piece under 5 m.
  - Each fix is listed in the log.

- Blocks are the faces of the new network inside the area. Widths come from printed widths, else 50 ft for streets and alley defaults for alleys.

- Each plate is its own set with its own id prefix (c22/SC, c38/SK). Install with `--install`.

## 7. Rebuild order (cuf/rebuild_streets.sh)

After any change to the 1904 frames or a plate:

1. cuf/undo_sets.py puts back every plate set's removals, newest first.
2. v3 build: run_build_safe.py with SBG_SUFFIX=_v3 and SBG_TF_EXTRA=lph/tf_all_v3.json, then add_ext.py _v3 v3 SV <49 sheets> --install.
3. Each plate build --install in plate order (build22, build38, then the newer plates).
4. millvale/build_mv.py --install.

## 8. Check and publish

- Screenshots of the plate area on the page, at 1922 and 1904 opacity; shared crossings with neighbouring plates; loose-end list.

- Publish deckpage/index.html plus the changed files (basin.json, tiles_22, tiles_n) as a new version. The artifact holds at most 512 files and one publish sends at most 255; split large publishes, and list the artifact's files first if a publish is refused for files not seen in this session.

- Log the step in Relief_Maps_Log.md and update lph/RESUME.md.

## 9. Addendum (22 October 2026, Northside / Camp Washington)

- Some vol. 1 halves (22-16R, 34L, 34R, 37L, 37R) were on the layer with only an affine (lph/tf22_cw.json). cuf_cw/fit.py refits a half from its picks (old file plus any s22-<half>_<part>.json second-read strips), seeded from that affine. cuf/plates.py uses cuf_cw/<half>/model.npz when it exists, and cuf/x1904.py adds those halves to the 1922 crossings.

- A half read sparsely the first time should be read again in strips (INSTRUCTIONS22.md, 2026-10-22 section). On 22-37 the heavy solid lines inside streets are water pipes, not street faces.

- Leave out of the control any street that has moved where every atlas agrees with itself but not with OSM. Colerain north of the Elmore interchange was such a case: cuf_cw/fit.py drops Colerain crossings north of N 4336600.

- cuf/rebuild_streets.sh does NOT rebuild the 13 October north 1904 layer (set None, ids SB####, sbg/fit/post.py), and rerunning post.py renumbers every SB street (Ben's edits are keyed by id). After bending north frames, move the SB streets, SBB blocks and their plots by the change in placement instead: cuf_cw/shift_sb.py (old lph/tps_vNN.pkl vs new lph/tps.pkl, sampled over each frame's page).

- After any rebuild, check every street id in Ben's live layout still exists with the same name (cuf_cw notes, 10zzy.16). Copy the live layout to dbread/deck/layout.json first so the builds keep his latest edited streets.

- The rebuild takes more than 30 minutes. Run it in steps, or with run_in_background and a long timeout.

## 10. Addendum (24 October 2026, Norwood plates 82A and 83A)

- Plates uploaded outside New Sanborn\PNG are found through cufp/config.json ("png"), cuf/plates.py PNGPATH, and PNG=<path> for prep.py.

- Outside the existing OSM extracts, cut a new extract from the same source (Historic_Topo/OSM/streets_all.geojson) and add it to fit.py's list (lph/osm_norwood.geojson).

- Readers write the same street with and without its suffix, and sometimes print one street under two names along its length. cufp/config.json per plate: "best_names" (most common full printed name), "merge" (key to key), "split" ([key, plate px, name north, name south]). Use them only on new plates: they rename streets, and renaming changes the ids of an already-built set.

## 11. Addendum (25 October 2026, Price Hill plates 26A, 26B, 29: plates around streets already placed)

- Ben's order for the Western Hills: the OSM primary and secondary streets go in first (wh/build_osm.py, set w1), then the plates fill in. cufp/config.json per plate: "keep_sets" (sets whose streets stay; plate pieces within 18 m of them are cut, the join step snaps the ends back), "avoid_existing" (the plate takes only ground the page has not drawn: existing streets buffered half-width plus 6 m, closed by +90/-60 m, and existing blocks), "clip_to" (a polygon file the area is clipped to; Ben's Western Hills line).

- A plate's area can now be several parts (MultiPolygon); build.py and plot_build.py use its boundary.

- cuf/tiles22.py holds every plate's tiles in memory and was killed at about 6 GB. Add new plates with cuf/tiles22_add.py <ids>: one tile at a time, new plates among themselves by depth, laid under existing tile pixels.

- Plate ids with a letter that is not a half (26A, 26B) need explicit entries in sbg/sb.py find(), cuf/plates.py PNGPATH (lower-case file names), and cufp/fit.py's OSM list (the old endswith('A') rule meant Norwood).
