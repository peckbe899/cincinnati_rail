# Topography workspace export

Exported 31 October 2026 from the Topography conversation's workspace (`/tmp/claude-0/-home-claude/9669db83-3d5c-5670-bb77-ef568f3a22e2/scratchpad`). Nothing in the workspace was changed, rerun or deleted for this export.

## What is here

- `TREE.txt`: every workspace file with size and date (UTC), scan-size images and tile images left out.

- `MANIFEST.csv`: every exported file with path, size, sha256, group, the zip it is in, the exported scripts that write it and those that read it (found by the file's name in the scripts; a script's own row lists the scripts that import or call it).

- `Relief_Maps_Log.md`: the full log (also put back in the project as `claude/Relief_Maps_Log.md`).

- Zips, one series per group, each 25 MB or less, with workspace paths inside. Unzip them all into one folder to get the workspace layout back.

| Zip | Group |
|---|---|
| `picks_01` | sbg/picks, sbg/picks22, sbg/picks12, sbg/INSTRUCTIONS*.md, sbg/sb.py, sbg/r12.py |
| `1922_01` | cufp scripts, config.json, strips.json, PROCESS_1922.md, per plate png2tif.json, matches.json, report.json, fwd.pkl (forward model), removed.json, area.json, ext.json; cuf, cuf38, cuf_cw (half models' fwd.pkl, matches, reports) |
| `1922_inverse_01` to `_05` | the inverse grids (model.npz, world to PNG pixel on a 2 m grid) for every plate and half |
| `1904_streets_01` | sbg/fit (scripts, tf.json, sizes.json, osmx.pkl, osm_biased.json), sbg/osmchk (with corrections.json, pick_fix.json, cuts.json, additions.json), lph (scripts, tf_all*.json, tf22*.json, tps*.pkl, obs_all.pkl, report_all.json, wv_1904.json, osm*.pkl and geojson, RESUME.md), basin/osm_basin.geojson, millvale, wh, deck/deck_gen.py, deck/west_valley.py |
| `removal_01` | removal files not already in the groups above: sbg/basin_1912_rejected.json, cufp/66-70/removed_prev.json |
| `generators_01`, `_02` | transit, cut, rera, rer1023, rer1024, trunk, nv, hwy, norwood, nw2, nwring, sgc, plots, yard (writes yard.json), cvg (writes airport.json) |
| `page_writers_01` | scripts outside the list that write a deck page file: trunk2, trunk3, cons, rerD, fill, and basin/basin_build.py, clean.py, clean2.py, tiles12.py, aoi.json |
| `inputs_01` | 58 small data files the exported scripts read that were not in the list (KMZ extracts, deck/obs.json, deck/sheet_tf.json, lph/sheets_*.json, lph/tf_ext*.json, sbg/fit/obs.pkl and others; MANIFEST group "inputs") |
| `topo_bathy_scripts_01` | topo and bathy scripts only |

Every removal file: cuf/c22_removed.json, cuf38/c38_removed.json, cufp/<plate>/removed.json, wh/removed.json (in their groups), plus the files in `removal_01`.

Left out, as asked: images (PNG, JPG, WebP, GeoTIFF; the 22-N.jpg reader crops), deckpage and its tiles, raster arrays (dem2m.npy, basin B.npy, ink*.npy, m12*.npy, lab3.npy, green1m.npy, cut/c55.npy, deck/m1912_1m.npy, lph/pop_masks.npy, the per-plate png_alpha_s4.npy masks), everything in topo and bathy except scripts, and old `_vNN` backups that have a current file. The png_alpha masks, png_s8.jpg and tif_s8.jpg are remade by `cufp/prep.py N <GeoTIFF>` from Ben's scans.

Paths: the scripts use the absolute workspace path `/tmp/claude-0/-home-claude/9669db83-3d5c-5670-bb77-ef568f3a22e2/scratchpad/` (as `SP` or `S`), Ben's scans as `/mnt/user-data/uploads/...` (cufp/config.json), and Historic_Topo files by their workspace copies. These have to be repointed in the repo.

## Deck page files

The page files are not rebuilt from nothing by one command. Each was made by a first build and then patched in place by later scripts (many keep a backup `*_vNN.json` first), and several of those patches bake in Ben's live page edits read from the page's database snapshots (`dbread*/deck/layout.json`, not exported; the layout lives in the page's database). So the order below rebuilds each file only on top of the copy it started from. Commands run from the workspace root unless the line says otherwise.

| File | Current copy (UTC) | Last writer | Command | Other scripts that patch it (oldest first) |
|---|---|---|---|---|
| basin.json | 27 Oct 02:30 | cut/split_cut_platforms.py | `python3 cut/split_cut_platforms.py <layout_in> <layout_out>` | basin/basin_build.py, clean.py, clean2.py (first 1912 build, superseded); sbg/fit/post.py (basin streets, set S/SB); cut/cut1931_a.py, cut1931.py, fill/fill_blocks.py, cut/plaza_align.py, ezzard.py, cutclean.py, cutclean2.py, deckedge.py, edgelots.py, cutplan2.py, campw.py; sbg/fit/add_ext.py; cuf/build22.py, cuf38/build38.py, cuf/undo_sets.py, millvale/build_mv.py, cuf_cw/shift_sb.py, hwy/build_hwy.py, cufp/build.py, wh/build_osm.py, trunk3/install_north.py |
| plots.json | 24 Oct 08:58 | hwy/build_hwy.py | `python3 hwy/build_hwy.py --install` | plots/build_plots.py (first build), fill/fill_blocks.py, cut/ezzard.py, cutclean2.py, deckedge.py, edgelots.py, cutplan2.py, campw.py, cuf_cw/shift_sb.py |
| deck.json | 27 Oct 02:30 | cut/split_cut_platforms.py | as basin.json | deck/deck_gen.py (first build: `python3 deck/deck_gen.py`, then copy deck/deck.json to deckpage), cut/cut1931_a.py, cut1931.py, fill/fill_blocks.py, cut/plaza_align.py, cutclean.py, cutclean2.py, deckedge.py, edgelots.py, cutplan2.py, campw.py |
| context.json | 27 Oct 18:25 | rerD/miamitown.py is the last traced writer (14:13); the 18:25 change, made with the backup context_v138.json, is not traced to a script | `python3 rerD/miamitown.py` | transit/build_transit.py (first build), rer1023/apply.py (`python3 rer1023/apply.py`; no longer runs, its inputs are gone, log 10zzy.35), trunk/north_pass.py (hooked in apply.py), trunk2/install.py, trunk3/install_north.py, cons/apply.py |
| tracks.json | 26 Oct 14:50 | trunk3/install_north.py | `python3 trunk3/install_north.py` | cut/tracks_gen4.py and cut/apex_region.py (first build), cut/railx.py, rer1023/apply.py, trunk2/install.py |
| structures.json | 26 Oct 14:50 | cut/structures.py | `python3 cut/structures.py` (after tracks and context) | none |
| hwy.json | 24 Oct 08:58 | hwy/build_hwy.py | `python3 hwy/build_hwy.py --install` | none |
| norwood.json | 24 Oct 15:27 | norwood/to_page.py | `python3 norwood/to_page.py` (reads norwood/sk10.py) | none |
| yard.json | 27 Oct 22:15 | yard/exportA.py | `python3 yard/exportA.py` (reads yard/A.json and deckpage/yard_v140.json) | yard/build2.py to build13.py (successive trials, each a full write) |
| viaducts.json | not in the workspace | none | none | It is a repo file (`hub/sites/deck/viaducts.json`); the workspace only reads a copy (wv3d/repo). Nothing here writes it. |
| airport.json | 18 Oct 18:21 | cvg/airside2.py | `python3 cvg/airside2.py` (output path from env AOUT, default deckpage/airport.json) | cvg/build_airport.py (first build from CVG Layout.kmz), cvg/taxi.py, cvg/airside.py |
| sheets.json | 20 Oct 05:20 | sbg/fit/add_ext.py (run as the version now kept as add_ext_pre_stub.py) | `python3 sbg/fit/add_ext.py SUFFIX SET PREFIX SHEETS --install` | sbg/fit/tiles.py (first index), lph/tiles_n.py (lph/sheets_n.json), lph/sheets_merge_ext.py |
| tiles_22/index.json | 25 Oct 09:51 | cuf/tiles22_add.py | `python3 cuf/tiles22_add.py 22-31 22-33` (adds plates, rebuilds index and overview); full render `python3 cuf/tiles22.py` (runs out of memory with every plate) | plates registered in cuf/plates.py |
| tiles_n/index.json | 22 Oct 14:56 | lph/tiles_all.py | `REDO=<frames> BAK=<tag> python3 lph/tiles_all.py` | lph/tiles_n.py (first build, `python3 lph/tiles_n.py`), lph/tiles_ext.py, tiles_ext2.py, tiles_ext3.py, tiles_168.py |
| tiles_b/index.json | 13 Oct 00:27 | sbg/fit/tiles.py | `cd sbg/fit && python3 tiles.py` (lph/run_tiles.sh) | none |
| tiles12/index.json | 21 Oct 09:10 | the merge to 1000 m tiles (log v89-90 note); no script for it survives | none | basin/tiles12.py made the original 250 m tiles from basin/m12.npy (not exported, raster) |

Rebuild order, as the workspace last ran it:

1. Imagery: `sbg/fit/tiles.py` (tiles_b), `lph/tiles_n.py` then `lph/tiles_all.py` (tiles_n), `cuf/tiles22.py` or `cuf/tiles22_add.py` (tiles_22). The 1904 bend onto 1922 comes first for tiles_n: `cuf/x1904.py <frames>` and `cuf/tps1922.py <frames>` over every bent frame (PROCESS_1922.md section 5).

2. Deck: `deck/deck_gen.py` (calls deck/west_valley.py), copy deck.json, then the CUT edits in cut/ as listed above.

3. Streets, the whole set, by `cuf/rebuild_streets.sh`: undo_sets, the 1904 v3 build and add_ext, build22 (35), build38, cufp/build.py 66 68 67 69 70 82A 83A 75 76, millvale/build_mv.py, wh/build_osm.py, cufp/build.py 29 26A 26B 31 33. The north SB layer is not rebuilt (rebuilding renumbers it and orphans Ben's edits); it is moved by cuf_cw/shift_sb.py.

4. Transit and tracks: transit/build_transit.py, then rer1023/apply.py (historical), trunk2/install.py, trunk3/install_north.py, cons/apply.py, rerD/miamitown.py.

5. Structures: `cut/structures.py`.

6. Highways and their street changes: `hwy/build_hwy.py --install` (after any street rebuild).

7. Norwood: `norwood/to_page.py`. Yard: `yard/exportA.py`. Airport: `cvg/airside2.py`. Then `cut/split_cut_platforms.py` last.

## 1922 plates

Leave-one-out is the rms of the leave-one-out errors of the chosen model (report.json "loo"); the drop test is 6 m against tps1. Prefixes: streets `<prefix>####`, blocks `<prefix>B####`. Plates are built in cufp/build.py PLATE_ORDER (each takes only ground the earlier ones left).

| Plate | Seed source | Model | Controls (matched / crossings) | Leave-one-out (m) | Street set | Prefix | Files |
|---|---|---|---|---|---|---|---|
| 35 (22-35N) | Ben's GeoTIFF, used as is (checked, not refitted) | Ben's georeference (EPSG:3857) | 30 checked crossings | 3.33 (rms; raw 3.07) | c22 | SC | cuf/ (corr_report.json, build22.py, c22_removed.json) |
| 38 | Ben's GeoTIFF (SIFT, cuf38/match.py) | tps1 | 63 (74 / 109) | 4.75 | c38 | SK | cuf38/ |
| 66 | Ben's GeoTIFF (SIFT) | tps3 | 96 (99 / 207) | 2.98 | c66 | SP | cufp/66/ |
| 68 | Ben's GeoTIFF (SIFT) | tps3 | 68 (72 / 123) | 3.34 | c68 | SR | cufp/68/ |
| 67 | Ben's GeoTIFF (SIFT) | tps3 | 70 (79 / 123) | 3.56 | c67 | SQ | cufp/67/ |
| 69 | Ben's GeoTIFF (SIFT) | tps0.3 | 43 (47 / 81) | 4.41 | c69 | ST | cufp/69/ |
| 70 | street names (no GeoTIFF) | tps3 | 74 (77 / 104) | 3.76 | c70 | SU | cufp/70/ |
| 82A | Ben's GeoTIFF (SIFT) | tps1 | 94 (100 / 125) | 3.78 | c82A | SN | cufp/82A/ |
| 83A | Ben's GeoTIFF (SIFT) | tps1 | 40 (40 / 46) | 3.97 | c83A | SO | cufp/83A/ |
| 75 | Ben's GeoTIFF (SIFT) | tps10 | 47 (52 / 79) | 4.18 | c75 | SX | cufp/75/ |
| 76 | Ben's GeoTIFF (SIFT) | tps1 | 117 (127 / 158) | 3.15 | c76 | SY | cufp/76/ |
| 29 | Ben's GeoTIFF (SIFT) | tps0.3 | 72 (73 / 105) | 2.78 | c29 | SG | cufp/29/ |
| 26A | Ben's GeoTIFF (SIFT) | tps3 | 49 (51 / 98) | 2.95 | c26A | SD | cufp/26A/ |
| 26B | street names (no GeoTIFF) | tps0.3 | 11 (11 / 17) | 3.50 | c26B | SF | cufp/26B/ |
| 31 | Ben's GeoTIFF (SIFT) | tps1 | 31 (32 / 113) | 4.00 | c31 | SH | cufp/31/ |
| 33 | Ben's GeoTIFF (SIFT) | tps0.3 | 62 (70 / 144) | 3.67 | c33 | SL | cufp/33/ |
| 16L (vol. 1 half) (not on the layer) | affine of log 10u.4 | tps0.3 | 9 (9 / 21) | 4.57 | none (imagery only; streets are the 1904 SB set, shifted by cuf_cw/shift_sb.py) | SB (1904) | cuf_cw/16L/ |
| 16R (vol. 1 half) | affine of log 10u.4 | tps3 | 15 (15 / 34) | 6.09 | none (imagery only; streets are the 1904 SB set, shifted by cuf_cw/shift_sb.py) | SB (1904) | cuf_cw/16R/ |
| 34L (vol. 1 half) | affine of log 10u.4 | tps3 | 16 (16 / 45) | 4.49 | none (imagery only; streets are the 1904 SB set, shifted by cuf_cw/shift_sb.py) | SB (1904) | cuf_cw/34L/ |
| 34R (vol. 1 half) | affine of log 10u.4 | tps0.3 | 49 (50 / 80) | 3.91 | none (imagery only; streets are the 1904 SB set, shifted by cuf_cw/shift_sb.py) | SB (1904) | cuf_cw/34R/ |
| 35L (vol. 1 half) (not on the layer) | affine of log 10u.4 | tps0.3 | 24 (25 / 50) | 9.89 | none (imagery only; streets are the 1904 SB set, shifted by cuf_cw/shift_sb.py) | SB (1904) | cuf_cw/35L/ |
| 37L (vol. 1 half) | affine of log 10u.4 | tps30 | 20 (31 / 63) | 4.67 | none (imagery only; streets are the 1904 SB set, shifted by cuf_cw/shift_sb.py) | SB (1904) | cuf_cw/37L/ |
| 37R (vol. 1 half) | affine of log 10u.4 | tps0.3 | 15 (18 / 59) | 5.90 | none (imagery only; streets are the 1904 SB set, shifted by cuf_cw/shift_sb.py) | SB (1904) | cuf_cw/37R/ |

Plates 66-70 are the ones whose log sections were lost; their figures above come from their report.json files.

## Open items from lph/RESUME.md

Quoted as written. RESUME.md was kept to 25 October; some of these have since been settled in the log.

**Open / to flag**

- Sheet 34 SW corner (creek mouth at W 6th): 34 and 1922 3L put the creek bend ~35 m east of the 1912 survey; no control within 150 m; left as fitted.
- 460 lower panel unplaced (no crossings); 605 unplaced; 458, 459, 465, 474 not picked (west of State).
- Basin 223/224 need a refit with 1912 corners on Harrison.

**Waiting on Ben**

- Confirm the reading of "the rest of the deck" (basin method).

**Waiting on Ben (added)**

- Question 4: Lower Price Hill west of the boulevard (options table sent), and whether the vol. 5 grid gets drawn for the rest of the west bank.
- Hopple viaduct level: 165.3 m or more over the APEx ramp (158.5 m), about 6.4 m above the deck.

**Open after v26**

- RER D: KMZ (page) turns west at the deck tip; TRIMET 3D runs up the trunk to Arlington first (10z.12).
- Garrard line cut by the APEx ramp 70 m north of Marshall (5.7 m) (10z.13).
- Tracker 2J vs the 1913 deck (10y.6), not edited.

**Other open notes in RESUME.md**

- Log 10zh. Open: Ludlow convergence of APEx and the CS line (10zh.6).

- Open: what runs on the NE prong (canon registers the Norwood-Blue Ash lower approach; ground rises NE so TRI A cannot portal there). L73 listed on APX-0/1a/1b but rerouted via the Oasis by the Blue Ash amendment.

- v3 (Ben: keep APEx through tracks straight): sketch3.py/.png. Through pair dead straight at +4/+8.5 (6.25 m north of page line, parallel) for the whole area; set by the east exit (Oakley -14/-9.5, X1/L75 -5/-0.5 above the SE corner at -15). Platform tracks T5 -1, T8 +13.5; APEx side platforms 6 m. ORR T4 -10.68, T3 -22.36, T2 -26.86, T1 -38.54. Transvalley one island T9 +23.18, T10 +34.86 (edge +37.4 vs +38). South strip -41 to -69 free -> headhouse. Open: Transvalley 2 vs more tracks (needs service levels).

- v8 (Ben: building ~400 x 150 ft; consider Metro/RER): sketch8.py/.png. Building 122 x 46 m at s4636-4758, -72 to -118 (south, outside area), main tunnel s4700-4718 from the building to an inner ring exit (+70). Levels (order only): 0 tracks; -1 passages (main tunnel, west hall at Montgomery Rd, east passage); -2 L3 terminus (s4678-4830 at +15, above TRI E) and L4 terminus (moved south of the tracks, centre offset -99, page tail cut back: page L4 tail to +77 crossed L3 at the same level); -3 TRI E (on the axis, straight, station s4700-4904, 37 m east of page point); -4 L14 (station moved ~100 m south along its line beside L4) and TRI A (at the A/E crossing s5057, as page). Page conflict found: L3 runs 5 m beside TRI E along the corridor from s4056, so they must stack. Open: TRI E position vs A (E under the main tunnel with a 150 m passage to A, or E ending over A).

## Extras (extras_01.zip, added 31 October)

Two gaps left by the "skip old _vNN backups" rule. MANIFEST groups `extras_v` and `extras_db`.

### _vNN files still in use

Every _vNN file in the workspace (363, outside topo and tiles) was checked against every exported current script, by literal name and by names built from a suffix (SBG_SUFFIX, SET, OUTSFX). Added:

| File | Why |
|---|---|
| lph/tf_all_v3.json | read by cuf/rebuild_streets.sh (SBG_TF_EXTRA) |
| sbg/fit/streets_raw_v3.json | live output of sbg/fit/build.py with SBG_SUFFIX=_v3; read by add_ext.py _v3 |
| sbg/fit/ext_v3.json | live output of sbg/fit/add_ext.py for set v3 |
| lph/tps_v98.pkl | read by cuf_cw/shift_sb.py (old placement for the SB shift) |
| deckpage/context_v90.json, tracks_v90.json | read by rer1023/apply.py, trunk/plan.py, trunk/frames.py, rer1024/geo.py |
| deckpage/context_v124.json | read by trunk2/draw.py, trunk2/geo3.py |
| deckpage/basin_v127.json, context_v127.json, tracks_v127.json | read by trunk3/install_north.py, trunk3/north.py (its base data) |
| deckpage/yard_v140.json | read by yard/exportA.py |
| deckpage/airport_v58b.json | read by cvg/airside2.py, cvg/gates.py |
| cvg/gates_params_v66.json | copied to gates_params.json by cvg/stem_air.sh |
| deckpage/index_v32.html | read by plots/patch_page.py |
| plots/db_data_v46, v53, v64, v91.json | page database copies read by the plots test scripts (p46, p48click, pdbg, pui; p53b, pui53; p64; p91, stedit_panel, stedit_test) |
| basin/streets_v3.json | named by Ben; no current script uses it. It is written by basin/basin_v3.py and read by basin/basin_v4.py (the superseded 1912 trace, log 10m), neither exported |
| lph/lph_streets_v3.json | named by Ben; no current script uses it. It is lph/lph_grid.py's output of 13 October; the live output is lph/lph_streets.json (already in inputs_01) |

Checked and not added: deckpage/context_v133.json (rerD/miamitown.py writes it as a backup, nothing reads it); wh/build_osm_v120.py (named only in a comment). trunk2/push/context_v126.json, tracks_v126.json and norwood/Norwood_Central_v10.kml were already exported. All other _vNN files are named by no current script.

### Page database snapshots

Copies of the page's database document deck/layout (Ben's live edits), saved into the workspace at the times shown. Nothing in the workspace writes them.

| Snapshot | Saved (UTC) | Read by |
|---|---|---|
| dbread/deck/layout.json | 24 Oct 20:07 (overwritten over time) | cuf/build22.py, cuf/build22_pre_ord.py, cuf38/build38.py, cufp/build.py, rer1023/apply.py, sbg/fit/add_ext.py |
| dbread/deck/layout_1020.json | 22 Oct 14:58 | no script names it |
| dbread2/deck/layout.json | 21 Oct 23:51 | rer1023/apply.py, rer1023/plot.py, rer1023/plot2.py |
| dbread3/deck/layout.json | 22 Oct 12:53 | no script names it |
| dbread4/deck/layout.json | 22 Oct 14:57 | no script names it |
| dbread5/deck/layout.json | 22 Oct 19:14 | hwy/ov2.py, hwy/prev.py, hwy/q1.py, hwy/q2.py |
| dbread6/deck/layout.json | 22 Oct 22:17 | only hwy/build_hwy_v101.py (old backup, not exported) |
| dbread7/deck/layout.json | 23 Oct 15:15 | hwy/build_hwy.py |
| dbread7/deck/layout_test.json | 23 Oct 15:17 | hwy/ptest.py |
| dbread8/deck/layout.json | 24 Oct 14:02 | no script names it |
| dbread9/deck/layout.json | 24 Oct 14:13 | no script names it |
| dbread10/deck/layout.json | 24 Oct 15:30 | no script names it |

The unnamed ones were most likely passed on the command line (cut/split_cut_platforms.py takes its layout in and out by argument) or read by one-off checks.

## Extras 2 (extras_02.zip, added 31 October): the te and ma street sets

sbg/fit/streets_raw_te.json, streets_raw_ma.json (build.py outputs) and ext_te.json, ext_ma.json (add_ext.py outputs) for the sets te (Times/Eggleston, ids SE, log 10zzq.3) and ma (Mt Auburn, Walnut Hills, Mt Adams, ids SM, log 10zzq.5), both in deckpage/basin.json (te 74 features, ma 471). MANIFEST group `extras_te_ma`.

No shell history for these runs survives (the session record before 31 October was compacted, and no script or log in the workspace holds the command lines). The commands below are reconstructed from lph/RESUME.md's note for versions 77-78 ("sbg/fit/run_build_safe.py -> streets_raw_te/_ma; sbg/fit/add_ext.py SUFFIX SET PREFIX SHEETS --install"), the log (set names and id prefixes), the code (build.py reads SBG_SUFFIX and SBG_TF_EXTRA; add_ext.py takes SUFFIX SET PREFIX SHEETS) and the transform files themselves:

- lph/tf_all_te.json = lph/tf_all.json (106 frames) plus exactly the 8 vol. 2 frames of log 10zzb.2: 114 frames.
- lph/tf_all_ma.json = lph/tf_all_te.json plus exactly the 59 frames of lph/tf_ext2.json (log 10zzq.4): 173 frames.
- The sheet lists are those frames, under the ids deckpage/sheets.json uses (add_ext.py matches SHEETS against sheets.json).

te (Times/Eggleston), run first:

```
cd sbg/fit
SBG_SUFFIX=_te SBG_TF_EXTRA=../../lph/tf_all_te.json python3 run_build_safe.py
python3 add_ext.py _te te SE 143,144,149,150,157,158,159,160 --install
```

ma (Mt Auburn, Walnut Hills, Mt Adams), run after te so its streets join te's:

```
cd sbg/fit
SBG_SUFFIX=_ma SBG_TF_EXTRA=../../lph/tf_all_ma.json python3 run_build_safe.py
python3 add_ext.py _ma ma SM 107,108,109,110,127,128,129,130,161i,161m,162,163,164,165,166,167,168,169,170,171,172i,172m,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189,190,191,192,193,194,195,196,197,198,199m,200i,200m,325,326,327,328,329,330,331,332 --install
```

The last runs were on 19 October 02:42-02:43 UTC, after the sheet 168 and 159 fixes (log 10zzq.8, 10zzq.9; the previous outputs are kept as streets_raw_*_pre159.json, _pre168.json, _pre_deer.json, not exported). A reinstall of a set first puts back what that set's last install changed. build.py also applies lph/tps.pkl, which later 1922 bends changed, so a rerun today may not reproduce these files exactly.
