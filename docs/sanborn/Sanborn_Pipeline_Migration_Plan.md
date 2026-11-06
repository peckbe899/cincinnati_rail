# Sanborn pipeline: out of the Topography workspace, into the repo and hub

Written 31 October 2026. This is the plan for moving the Sanborn (1904 and 1922) street and imagery pipeline out of the Topography conversation's cloud workspace and into the repo (`peckbe899/cincinnati_rail`, local copy `_Cincinnati Rail\3D`), so the Deck in the hub can be rebuilt from scratch and new 1922 plates can go in.

Copies: project doc `claude/Sanborn_Pipeline_Migration_Plan.md` (for chat sessions) and `_Cincinnati Rail\Maps\Sanborn\Sanborn_Pipeline_Migration_Plan.md` (for Claude Code). The method itself is `claude/Sanborn_1922_Plate_Process.md`; the history is `claude/Relief_Maps_Log.md`.

## 1. Where things stand

- The 1922 layer has 17 plates from Ben's PNGs (26A, 26B, 29, 31, 33, 35, 38, 66, 67, 68, 69, 70, 75, 76, 82A, 83A) plus the Library of Congress halves 16R, 34L, 34R, 37L, 37R. Mill Creek Deck artifact and hub have the same 197 tiles.

- 59 plates in `CS2\New Sanborn` are not on it yet (section 6).

- The hub has no full-resolution Sanborn imagery. `hub/sites/deck/tiles_22`, `tiles_n`, `tiles_b` and `tiles12` hold only their index and 2 m overview; the page asks for `tiles_*/<E>_<N>.webp` and gets nothing. The 0.25 m tiles exist only in the Mill Creek Deck artifact (and the Topography workspace).

- The scripts and data that made the Deck's Sanborn layers exist only in the Topography conversation's workspace (last seen at `/tmp/claude-0/-home-claude/9669db83-3d5c-5670-bb77-ef568f3a22e2/scratchpad`). Ben's computer has copies only as of 13 October (page version 26): `Maps\Basin_Street_Map` (1904 scripts zip, picks zip with picks22 and picks12 as of that day, transforms), `Maps\Sanborn\Georef_1904` (`lph_scripts.zip`, deck and north transforms), `Maps\Deck_Street_Map` (`deck_gen.py`, `west_valley.py`, `rera.py`). Everything from 14 to 28 October is in the workspace only.

- The project copy of `Relief_Maps_Log.md` is missing sections 10zb to 10zzy.9 (it jumps from 10za.8 to 10zzy.10). Those cover, among other things, plates 35 and 38 (versions 84-87) and 66-70 (versions 89-90).

- The Mill Creek Deck artifact holds 422 of its 512 files. It stays frozen; nothing new is published to it.

- Status 31 October: the workspace is exported to `Maps\Topography_Export` (P1), with the live `_vN` files and the page database snapshots added in `extras_01.zip` (P1b; 32 files, checksums checked). Every street set in the Deck's `basin.json` now has its inputs in the export except two 1904 sets from 19 October: te (Times/Eggleston, ids SE) and ma (Mt Auburn, Walnut Hills, Mt Adams, ids SM). Their `sbg/fit/streets_raw_te.json`, `streets_raw_ma.json`, `ext_te.json` and `ext_ma.json` are added by P1c. Log sections 10zzx to 10zzy.9 (20-22 October, plates 66-70) are lost; plates 66-70's figures survive in their `report.json` files.

- The 0.25 m tiles are saved to `Maps\MCD_Tiles_Snapshot` (P2): 404 files in six zips with a manifest, every tile in the four indexes.

- Plate 35 is drawn from Ben's GeoTIFF georeference as is (`cuf/ben_georef.json`, checked against 30 crossings, not refitted). That breaks rule 2 in section 7, so the rebuild refits it from its picks (`sbg/picks22/s22-35N_*`).

## 2. What the Topography workspace holds

Priority A cannot be recreated without re-doing agent or Ben's work. B can be rebuilt but only with these scripts. C is provenance; its outputs are already on Ben's computer.

| Priority | Group | What (workspace paths) | Used for |
|---|---|---|---|
| A | 1922 crossing picks | `sbg/picks22/` (all halves and plates, including the `_a.._f` strip files and second reads) | Every 1922 fit |
| A | 1904 and 1912 picks | `sbg/picks/`, `sbg/picks12/` | 1904 fits, bends, basin and north streets |
| A | Reader instructions | `sbg/INSTRUCTIONS.md`, `INSTRUCTIONS22.md`, `INSTRUCTIONS12.md`, `sbg/sb.py`, `sbg/r12.py` | Reading new plates the same way |
| A | Per-plate settings and rules | `cufp/config.json` (best_names, merge, split, drop, keep_sets, avoid_existing, clip_to, png paths), `cufp/strips.json`, `cuf_cw/config.json`, alias and exclusion lists inside `cufp/fit.py` and `cuf_cw/fit.py`, forced matches in `cuf/tps1922.py` | Same results on rebuild |
| A | 1904 fix lists | `sbg/osmchk/corrections.json`, `pick_fix.json`, `cuts.json`, `additions.json`, `sbg/fit/osm_biased.json`, `lph/wv_1904.json`, ROT_FIX and panel boxes in `lph/solve_all.py` and `lph/mosn.py` | Same 1904 streets on rebuild |
| A | Ben's boundary lines | `wh/western_hills_area.kml`, `wh/area_utm.json`, `norwood/limits_utm.json`, `sgc/cemetery_utm.json` | Clipping and keep-outs |
| A | Seeds | `cufp/<plate>/png2tif.json` for every plate | Starting position (from the GeoTIFF, which is never used again) |
| B | Plate fits | `cufp/<plate>/` matches, report, forward model; `cuf_cw/<half>/model.npz`; `cuf38/`; `lph/tf22_aff.json`, `tf22_cw.json` | Tiles, bends, streets |
| B | 1904 fits and bends | `sbg/fit/tf.json`, `sizes.json`, `osmx.pkl`; `lph/tf_all.json`, `tf_all_v3.json`, `tps.pkl`, `tps_pre1922.pkl`, `obs_all.pkl`, `report_all.json`; `cuf/x1904*.json`, `tps1922_report*.json` | tiles_n, tiles_b, streets |
| B | Pipeline scripts | `cufp/` (prep, fit, build, plot_build, gaps, frames_under, PROCESS_1922.md), `cuf/` (plates, tiles22, tiles22_add, x1904, tps1922, build22, undo_sets, rebuild_streets.sh), `cuf38/`, `cuf_cw/` (fit, diag, far, cands, frames_under, shift_sb, frames_all.txt), `sbg/fit/` (load, solve, solve_north, build, post, tiles, osmx, osmfollow, widthnotes, run_build_safe, add_ext, names), `sbg/osmchk/`, `lph/` (solve_all, tps, mosn, fit22, osm3, tiles_n, tiles_all, add22, lph_grid, seam_combo, corners_built, w8gest), `millvale/build_mv.py`, `wh/build_osm.py`, `wh/q1914.py`, `deck/deck_gen.py`, `deck/west_valley.py` | Rebuilding the Deck's Sanborn layers |
| B | Street-set removal files | One per set (c22, c38, c66-c70, c75, c76, c82A, c83A, c26A, c26B, c29, c31, c33, v3/SV, w1, mv, lph, wv, hwy) and `wh/removed.json` | Undoing a set cleanly before a rebuild |
| B | OSM extracts | `lph/osm_north`, `osm_east`, `osm_west`, `osm_norwood` (geojson), `basin/osm_basin`, `osm_valley`, `lph/osm2.pkl`, `osm3.pkl` | Controls (rebuildable from `Historic_Topo\OSM\streets_all.geojson`) |
| B | Other page generators | `transit/build_transit.py`, `ut_box.py`; `cut/tracks_gen3.py`, `structures.py`, `trimet3d.json`, `trimet_bridges.json`; `rera/rera.py`; `rer1023/` (apply.py, metro400, norwood_pass, gaps_pass, l10_pass, KMLs); `rer1024/`; `trunk/` (frames, plan, north_pass); `nv/geom27.py`; `hwy/build_hwy.py`; `norwood/sk10.py`; `nw2/`; `nwring/ring.py`; whatever writes `plots.json`, `yard.json`, `viaducts.json`, `airport.json` | Provenance for the hub's static deck files; port only if a file has to be regenerated |
| B | Page history | `deckpage/index.html` and its `_vNN` backups, data backups | Reference only; the page is the repo's now |
| C | Relief and river | `topo/`, `bathy/`, `run_all.sh` | Outputs already in `Historic_Topo` |
| C | Notes | `lph/RESUME.md`, `cufp/PROCESS_1922.md`, the workspace's own `Relief_Maps_Log.md` (with the missing sections) | Logs and open items |

Already on Ben's computer, not to be copied: the New Sanborn PNGs and GeoTIFFs, `Maps\Sanborn\cincinnati_*` scans, `Historic_Topo` (LiDAR 2 m, 1912 survey, OSM, USGS quads, relief outputs), the KMZs in `_Cincinnati Rail`, the reader crops `cufp/22-N.jpg` (made from the PNGs).

## 3. Target layout in the repo

- `tools/sanborn/`: the scripts, with every path read from one file, `configs/sanborn_paths.json` (New Sanborn, Maps\Sanborn, Historic_Topo on Ben's machine).

- `data/sanborn/`: everything judged by an agent or Ben, in git: picks (1904, 1922, 1912), per-plate config, aliases, exclusions, forced matches, fix lists, boundary lines, seeds, frame lists.

- `data/sanborn/manifest.json`: every input file by path, size and sha256. A changed scan stops the build.

- `data/sanborn/models/`: forward models and control lists (small, in git). Inverse grids are rebuilt.

- `data/sanborn/reports/`: per-plate fit report, seam report, comparison and checksums, one folder per run.

- `docs/sanborn/`: this plan, the process, and the rules (section 7).

- Outputs go to `hub/sites/deck/` (`basin.json`, `plots.json`, `sheets.json`, `tiles_*`). Tile images stay out of git (`.gitignore` the `.webp`; index and overview stay in).

- One entry point, for example `python -m tools.sanborn build [--plates ...] [--check]`.

Reproducible means:

1. Agents' readings are inputs, never part of a rebuild.

2. Every step is solved over the whole map: plate fits checked against every plate and 1904 frame they share crossings with; the 1904 bend solved for all frames together; each tile composited from every plate that touches it in a fixed depth order. The current `tiles22_add.py` (lays a new plate under what is already drawn) goes, because its result depends on the order plates were added.

3. Street ids come from the plate and street, not a running count. The ids in use now are frozen once in a lookup table, so Ben's edits (keyed by id) never orphan.

4. Random steps (SIFT, RANSAC) have fixed seeds; library versions are pinned.

5. A rebuild with nothing changed gives identical outputs, checked by checksum.

## 4. Steps

| # | Step | Who | Prompt | Done when |
|---|---|---|---|---|
| 1 | Export the workspace | Topography conversation | P1 | `Maps\Topography_Export` has MANIFEST.csv, README.md, TREE.txt and every group in section 2, and the full log is back in the project |
| 2 | Check the export; save the tiles | A project chat | P2 | Gaps listed; `Maps\MCD_Tiles_Snapshot` holds every tile in the four indexes |
| 3 | Into the repo; tiles into the hub | Claude Code | P3 | Hub Deck shows 0.25 m Sanborn imagery; scripts and data in the section 3 layout on a branch, nothing behaving differently |
| 4 | Rebuild test | Claude Code | P4 | A rebuild of the 17 plates, the 1904 bend and the street sets from committed data matches the hub files (or every difference is explained); every street id in Ben's layout still exists with the same name |
| 5 | Log | A project chat | P6 | Relief_Maps_Log entry for steps 1-4 |
| 6 | New plates, batch by batch | Claude Code | P5 | Section 6 order; one batch per run; decisions made before each batch |
| 7 | Log each batch | A project chat | P6 | One entry per batch |

If the Topography workspace is gone: the Oct 13 copies on Ben's computer still hold the 1904 picks, the 1904 transforms and the picks for the vol. 1 halves (3, 6, 9, 10, 13, 16, 26, 29, 31, 33, 34, 35, 37). The picks for plates 35, 38, 66-70, 75, 76, 82A, 83A, 26A, 26B, 29, 31 and 33 (Ben's PNGs) would have to be read again. The page's current tiles and streets survive in the artifact and the hub, so nothing on the page is lost; only its rebuild is.

## 5. Prompts

### P1: Topography conversation

```
Export your workspace to my computer so the Sanborn pipeline can move into the repo. Don't change, rerun or delete anything first.

1. Check the workspace still exists. Write TREE.txt: every file with size and date (skip scan images and tile images).
2. Copy into _Cincinnati Rail\Maps\Topography_Export\, keeping workspace paths:
   - picks: sbg/picks, sbg/picks22 (all strip and second-read files), sbg/picks12, sbg/INSTRUCTIONS*.md, sbg/sb.py, sbg/r12.py
   - 1922: cufp (scripts, config.json, strips.json, PROCESS_1922.md, and per plate png2tif.json, matches, report, forward model; inverse grids only if there's room), cuf, cuf38, cuf_cw (with the half models)
   - 1904 and streets: sbg/fit (scripts, tf.json, sizes.json, osmx.pkl, every fix list), sbg/osmchk, lph (scripts, tf_all*.json, tf22_*.json, tps*.pkl, obs_all.pkl, report_all.json, wv_1904.json, osm*.pkl and geojson, RESUME.md), basin/osm_basin, millvale, wh, deck/deck_gen.py and west_valley.py, every street set's removal file
   - other page generators: transit, cut, rera, rer1023, rer1024, trunk, nv, hwy, norwood, nw2, nwring, sgc, plots, and whatever writes yard.json, viaducts.json and airport.json
   - notes: your Relief_Maps_Log.md
   - topo and bathy scripts only (no rasters)
3. Skip: my PNGs and GeoTIFFs, the 22-N.jpg reader crops, deckpage tiles, dem2m.npy and anything else already in Historic_Topo, and old _vNN backups unless they are the only copy of something.
4. Zip anything over 25 MB; split it if still too big.
5. MANIFEST.csv: path, size, sha256, group, what writes it, what reads it.
6. README.md: for each deck page file (basin, plots, deck, context, tracks, structures, hwy, norwood, yard, viaducts, airport, sheets, and the tiles_22, tiles_n, tiles_b, tiles12 indexes) the script and command that writes it, and the rebuild order; per 1922 plate its id, seed source, model, controls, leave-one-out, street set and prefix; the open items from RESUME.md.
7. The project's Relief_Maps_Log.md is missing sections 10zb to 10zzy.9 (plates 35, 38, 66-70 among them). Put the full log back in the project.
8. Tell me what's missing, what was deleted earlier to save disk, and what you couldn't copy.
```

### P1b: Topography conversation, after P1

```
Two gaps in the export, both caught by my "skip old _vNN backups" rule. Add these to Maps\Topography_Export as extras_01.zip with workspace paths, and add their rows to MANIFEST.csv:
1. Every _vN file that a current script still reads, or that a build writes as its live output. At least lph/tf_all_v3.json, sbg/fit/ext_v3.json, sbg/fit/streets_raw_v3.json, basin/streets_v3.json and lph/lph_streets_v3.json. Check every skipped _vNN file against the scripts and list what you added.
2. The page database snapshots dbread*/deck/layout*.json (dbread to dbread10), with a README note of which script read which snapshot.
Don't change anything else.
```

### P1c: Topography conversation, after P1b

```
One more gap: the te and ma street sets (log 10zzq.3 and 10zzq.5) are in the Deck's basin.json, but their add_ext inputs aren't exported. Add sbg/fit/streets_raw_te.json, streets_raw_ma.json, ext_te.json and ext_ma.json as extras_02.zip with workspace paths, add their rows to MANIFEST.csv, and add to the README the exact build.py and add_ext.py commands (suffix, set, prefix, sheet list, SBG_TF_EXTRA) that made each set, from your notes or shell history. Don't change anything else.
```

### P2: a project chat (Claude, not Claude Code)

```
Read claude/Sanborn_Pipeline_Migration_Plan.md. Check _Cincinnati Rail\Maps\Topography_Export against section 2 and the export's MANIFEST.csv, and list anything missing. Then save the Mill Creek Deck artifact's tile folders (tiles_22, tiles_n, tiles_b, tiles12) to _Cincinnati Rail\Maps\MCD_Tiles_Snapshot\ and check each folder's count against its index.json. Don't publish to the artifact or touch the repo.
```

### P3: Claude Code

```
Read ..\Maps\Sanborn\Sanborn_Pipeline_Migration_Plan.md (sections 3 and 7) and ..\Maps\Topography_Export\README.md.
1. Copy the tile images from ..\Maps\MCD_Tiles_Snapshot\ into hub/sites/deck/tiles_22, tiles_n, tiles_b and tiles12. Keep the .webp files out of git, the index and overview files in. Check the Deck shows them at full zoom.
2. Bring the export into the repo in the section 3 layout: scripts under tools/sanborn, everything judged by an agent or me under data/sanborn, the plan, process and rules under docs/sanborn, an input manifest with checksums, local paths in configs/sanborn_paths.json. Don't change behaviour yet.
Commit on a branch and push.
```

### P4: Claude Code

```
Rebuild test, docs/sanborn plan step 4. Export the hub first. From committed data only, rebuild the 17 1922 plates, the 1904 bend and the street sets, and compare with hub/sites/deck: tiles, basin.json, plots.json, sheets.json, street ids, and every edit in my layout. Replace tiles22_add with a full per-tile composite and freeze the street ids (plan section 3). Write the fit, seam and comparison reports to data/sanborn/reports. Don't replace hub files until they match; report any difference you can't explain.
```

### P3 to P6 in one Claude Code run

```
Read ..\Maps\Sanborn\Sanborn_Pipeline_Migration_Plan.md (sections 1, 3, 6 and 7), ..\Maps\Topography_Export\README.md and ..\Maps\MCD_Tiles_Snapshot\README.md. Do the parts below in order on one branch, committing after each. If a part fails its check, stop and report; don't start the next.

Part 1, tiles: unzip ..\Maps\MCD_Tiles_Snapshot\*.zip into hub/sites/deck (tiles_22, tiles_n, tiles_b, tiles12) and check every file against its MANIFEST.csv. Keep the .webp files out of git; index and overview files stay in. Check the Deck shows the tiles at full zoom.

Part 2, import: unzip ..\Maps\Topography_Export\*.zip (the extras zips too) and bring it into the repo in the section 3 layout: scripts in tools/sanborn; everything judged by an agent or me in data/sanborn; the plan, process, rules and the export README in docs/sanborn; an input manifest with checksums; my local paths in configs/sanborn_paths.json. Repoint the workspace and /mnt paths. No change in behaviour.

Part 3, rebuild test: export the hub first. From committed data only, rebuild the 1922 plates, the 1904 bend and the street sets, and compare with hub/sites/deck: tiles, basin.json, plots.json, sheets.json, street ids, and every edit in my layout. Replace tiles22_add with a full per-tile composite and freeze the street ids. Page files that bake in my edits are rebuilt on their current copies, as the export README says. Plate 35 is the one expected difference: it is drawn from my GeoTIFF as is, which breaks rule 2, so refit it from its picks (22-35N) like the other plates and report how far it moves. Write the fit, seam and comparison reports to data/sanborn/reports. Replace hub files only when everything else matches or each difference is explained.

Part 4, batch 1: add plates 25 and 28 (section 6, batch 1), built like 26A and 29 inside the Western Hills line. They have no GeoTIFF, so seed from street names; fit and draw my PNGs. Read the crossings with reader agents in strips per the instructions, commit the picks, then do a full rebuild. Report the fits, the seams, loose ends and every street of mine that moved.

Part 5, log: write a log entry for parts 1 to 4 to data/sanborn/reports/<run>/LOG_ENTRY.md, in the Relief_Maps_Log style (numbered rows: what, result, status), for a chat session to put in the project log.

Push the branch and stop. Later batches need my rulings first.
```

After it, in a project chat: `Read the newest LOG_ENTRY.md in data/sanborn/reports (repo _Cincinnati Rail\3D) and add it to claude/Relief_Maps_Log.md.`

### P3 to P6 in one cloud Claude Code run (linked to Ben's computer)

Before it: Ben runs `python hub/hub.py export` on his computer, commits and pushes `hub/seed`.

```
This runs in the cloud, linked to my computer. My files aren't in the repo; reach them through the computer link: _Cincinnati Rail\Maps\Sanborn\Sanborn_Pipeline_Migration_Plan.md (read sections 1, 3, 6 and 7), Maps\Topography_Export, Maps\MCD_Tiles_Snapshot, CS2\New Sanborn (my PNGs and GeoTIFFs), Maps\Sanborn (the 1904 and 1922 scans) and Historic_Topo\OSM. Stage only what each part needs and delete staged scans when done with them. I've exported my hub and pushed hub/seed; that is the source for my edits. Do the parts in order on one branch, committing and pushing after each. If a part fails its check, stop and report.

Part 1, tiles: unzip Maps\MCD_Tiles_Snapshot\*.zip into 3D\hub\sites\deck on my computer (tiles_22, tiles_n, tiles_b, tiles12) and check every file against its MANIFEST.csv. Keep the .webp files out of git; index and overview files stay in. Keep a staged copy for Part 3.

Part 2, import: stage and unzip Maps\Topography_Export\*.zip and bring it into the repo in the section 3 layout: scripts in tools/sanborn; everything judged by an agent or me in data/sanborn; the plan, process, rules and the export README in docs/sanborn; an input manifest with checksums; configs/sanborn_paths.json with two profiles, my computer (Windows paths) and a cloud run (staged copies). Repoint the workspace and /mnt paths. No change in behaviour.

Part 3, rebuild test: from committed data and hub/seed only, rebuild the 1922 plates, the 1904 bend and the street sets, and compare with hub/sites/deck and the snapshot tiles: tiles, basin.json, plots.json, sheets.json, street ids, and every edit in my layout. Replace tiles22_add with a full per-tile composite that renders one tile at a time (the old full render ran out of memory at about 6 GB), and freeze the street ids. Page files that bake in my edits are rebuilt on their current copies, as the export README says. Plate 35 is the one expected difference: it is drawn from my GeoTIFF as is, which breaks rule 2, so refit it from its picks (22-35N) like the other plates and report how far it moves. Write the fit, seam and comparison reports to data/sanborn/reports. Write rebuilt tiles to my computer and replace hub files only when everything else matches or each difference is explained.

Part 4, batch 1: add plates 25 and 28 (section 6, batch 1), built like 26A and 29 inside the Western Hills line. They have no GeoTIFF, so seed from street names; fit and draw my PNGs (stage 25.png and 28.png). Read the crossings with reader agents in strips per the instructions, commit the picks, then do a full rebuild and write the new tiles to my computer. Report the fits, the seams, loose ends and every street of mine that moved.

Part 5, log: write a log entry for parts 1 to 4 to data/sanborn/reports/<run>/LOG_ENTRY.md, in the Relief_Maps_Log style (numbered rows: what, result, status), for a chat session to put in the project log.

Push the branch and stop. Later batches need my rulings first.
```

After it: Ben pulls the branch and starts the hub, then the P6 chat prompt.

### P5: Claude Code, one per batch

```
Add 1922 plates <ids> (docs/sanborn plan section 6, batch <n>). Rulings for this batch: <...>.
Seed from the GeoTIFF only; fit and draw my PNG. Read the crossings with reader agents in strips per the instructions, commit the picks, then do a full rebuild. Export the hub first.
Report the fits, the seam report, loose ends, and every street of mine that moved.
```

### P6: a project chat

```
Read the newest run in data/sanborn/reports (repo _Cincinnati Rail\3D) and add the entry to claude/Relief_Maps_Log.md.
```

## 6. Plate batches

Coverage by 1904 is the share of the plate's control-point outline under 1904 imagery already on the page (31 October check). "PNG only" plates have no GeoTIFF and are seeded from street names, as 26B was. "Top folder" means the GeoTIFF is only in `New Sanborn\`, not `New Sanborn\GeoTIFF\`.

| Batch | Plates | 1904 under it | Notes | Decide first |
|---|---|---|---|---|
| 1. Price Hill | 25, 28 | Not measured (no control points) | PNG only; inside the Western Hills line, built like 26A and 29 (OSM primary and secondary kept, plate fills the rest) | Nothing new |
| 2. Northside and Spring Grove | 43, 44, 45, 39, 40 | 43 72%, 44 93%, 45 50%; 39, 40 not measured | 44, 45 GeoTIFFs in the top folder; 39, 40 PNG only. Gives the 1904 Northside frames north of Powers (614-622) a plate to bend to (open since 10zzy.16) | Whether Northside streets Ben edited may move with the bend |
| 3. Camp Washington, Brighton, Clifton Heights | 13, 14, 15A, 15B, 16, 17, 18A, 18B | All 99-100% except 18A 83% | Bends 1904 frames whose streets Ben has edited | Whether Ben's own 16 replaces the Library of Congress 16R strip |
| 4. East and Norwood, no 1904 | 60B, 61, 62, 63, 64A, 64B, 65, 71, 80, 82B, 83B, 84, 85A, 85B, 87, 93A, 93B | None (60B, 65, 80, 83B, 85A, 85B, 93A not measured; they lie outside the 1904 layer) | New ground, streets straight from the plates, as Norwood. 65, 83B GeoTIFFs in the top folder; 80, 85A, 85B PNG only | OSM main roads first with a boundary line (as the Western Hills), or plates only |
| 5. Basin and Walnut Hills | 1A, 1B, 2, 3, 4, 5, 6, 7, 8A, 8B, 9, 10, 11, 12, 51, 52, 53, 54A, 54B, 55A, 55B, 56, 57, 58, 59A, 59B, 60A | 1A-12, 51-58 99-100%; 3 91%, 1B 80%, 59A 90%, 60A 56%, 59B 47% | Under the 1904 basin layer, where most of Ben's street edits are | Imagery and bend only, or rebuild the basin streets too |

Total 2 + 5 + 8 + 17 + 27 = 59.

Not plates: `74 rail cs2.tif`, `lunken cs2.tif`, the 1955 and 1956 aerials. Where a plate has several GeoTIFFs (8A, 9, 10, 13, 16, 54A, 59B) use the newest without "OLD"; it only seeds.

## 7. Rules that travel with the pipeline

From Ben and `claude/Sanborn_1922_Plate_Process.md`; Claude Code can't read the project, so these go into `docs/sanborn/`.

1. The 1922 plate is the reference. Fit the plate first, then bend the 1904 sheets onto it.

2. Ben's GeoTIFF is a starting position only. The image that is fitted and drawn is his raw PNG.

3. Controls are today's OSM crossings of streets that have not moved or been widened since 1922. Realigned streets are left out by name (Dixmyth, Glenmary, Lafayette on plate 38; Elmore; Colerain north of N 4,336,600). Renamed streets get aliases (Victory Boulevard = Victory Parkway, Clough Avenue = Crane Avenue, Montgomery Pike / Avenue = Montgomery Road, McNeill = McNeil Avenue, Robertson Road = Robertson Avenue, Mt. Hope Road = Mount Hope Avenue, Filson Terrace = Filson Place, Alpine Way = Alpine Place, Quebec Avenue = Quebec Road).

4. Match within 45 m of the seed, refit, match again within 30 m. Drop, one at a time, any control the tps1 spline misses by more than 6 m. Pick the model by leave-one-out: affine, quadratic, affine plus thin-plate spline at smoothing 0.3, 1, 3, 10, 30, 100.

5. 1922 is its own layer, drawn over 1904, never mixed into it. Only 1904 sheets already on the page are bent. The bend is solved for every bent frame together.

6. A plate's streets take its footprint 3 m inside the edge, less earlier plates and kept lines. Ben's edited streets and named keep-lines stay. Widths are printed widths, else 50 ft for streets and alley defaults for alleys. Each plate is its own street set with its own id prefix and removal file.

7. Western Hills and similar areas: OSM primary and secondary streets first (set w1), the plates fill in only ground not drawn, clipped to Ben's line.

8. Pre-war suburban layout ("Park Ridge, not Park Forest"): few cul-de-sacs; where the ground forces otherwise, the plates and the terrain map decide.

9. Street ids stay stable; Ben's names (`n`) and deletions (`del`) are keyed by id. After any rebuild, every id in his live layout must still exist with the same name.

10. Export the hub (`python hub/hub.py export`) before a build, so the build sees Ben's latest edits.

11. The claude.ai artifacts are retired. Repo and hub changes go through Claude Code; chat sessions write prompts and logs.
