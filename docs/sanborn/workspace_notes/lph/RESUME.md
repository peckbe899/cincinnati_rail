# LPH seam + deck refit + north: resume notes (2026-10-13)

## Rulings (Ben, 2026-10-12)

- Sanborn spline only in the Lower Price Hill block: Western Ave, State Ave, Gest St, Ohio River; 1922 plates 3, 6, 26, 29.
- "The rest of the deck can be set in the same method as we used before": read as the basin method (picks + OSM + 1912 + ties). Told Ben; no reply yet.
- Earlier (02:48): Camp Washington (Central Parkway to Beekman) and Northside/South Cumminsville by the same method; extend Metro and RER.

## Done

- Picks: 1922 halves 3L/R, 6L/R, 26L/R (26R has main + inset parts), 29L/R (+9, 10, 13, 16, 31, 33L, 34 unused). Vol 5 sheets 460-464, 466-468, 491-496, 504, 505, 511-514, 519, 520, 522 (sbg/picks). North: 233-305, 601-635 (sbg/picks); 1912 corners sbg/picks12 (campwash, northside_e, cumminsville_w).
- lph/fit22.py: 1922 halves, affine, OSM (lph/osm2.pkl = osm_basin + osm_valley) + basin frames + ties -> lph/tf22_aff.json. Medians 1.3-3.3 m. Plates 26 and 29 are 200 ft/in (5.2 px/m), 3 and 6 100 ft/in (10.2 px/m).
- Finding: old deck sheets 33/34/35/47 were 13-20 m west, 57 8-10 m; 1922, 1912 (Garrard track, curve, W 8th viaduct) and OSM Horne remnant agree.
- lph/solve_all.py: joint fit of deck + north frames (basin tf.json fixed), CHPL affine, LOC similarity, 1922 corners as control inside the block, old deck obs (no 6th1912; in the block only L: lines) -> lph/tf_all.json (104 frames), report_all.json, obs_all.pkl. Ties 0.8 m, OSM 1.5, 1912 1.9, 1922 2.0. Basin 223/224 left out of ties (5-6 m off; north agent saw 10-17 m at Harrison). ROT_FIX 236, 295, 492 (-33.7, State Ave bearing).
- lph/tps.py: per box frame TPS of crossing residuals onto 1922 with zero anchors (>120 m from a crossing) and taper to 0 over 80 m before Gest (N 4331620) and Western (E 712880) -> lph/tps.pkl. warpfn_factory(TF) gives the warp. Checked: Evans/W 8th four-sheet corner continuous; McLean-Harriet seam (35/47 vs basin 36/37) continuous.
- Image correlation 1904 vs 1922 tried and dropped (noisy).
- lph/mosn.py: mosaic renderer (page masks, PANEL_KEEP/DROP for 460u, 468m), overlay OSM + 1922 points.

## Open / to flag

- Sheet 34 SW corner (creek mouth at W 6th): 34 and 1922 3L put the creek bend ~35 m east of the 1912 survey; no control within 150 m; left as fitted.
- 460 lower panel unplaced (no crossings); 605 unplaced; 458, 459, 465, 474 not picked (west of State).
- Basin 223/224 need a refit with 1912 corners on Harrison.

## Done 2026-10-13 (page version 20, log 10t)

- 223/224 refitted in solve_all (BASIN_REFIT). Deck layer regenerated (deck_gen.py reads tf_all + tps; precinct rule fixed). CUT tracks re-run (tiny changes).
- Basin + north streets: sbg/fit/build.py and post.py with SBG_TF_EXTRA=lph/tf_all.json SBG_SUFFIX=_n -> basin_sanborn_n.json, installed as basin_sanborn.json and deckpage/basin.json (v13 kept as basin_sanborn_v13.json / basin_v13.json).
- Transit window north (build_transit.py WIN), context.json.
- Tiles: deckpage/tiles_n (lph/tiles_n.py, panel polygons for 460, 468, 627, 628); tiles_b regenerated with 223/224 (sbg/fit/tiles.py patched). Old deck tiles removed from the artifact. sheets.json rebuilt.
- Published page version 20; log pushed to project; Deck_Street_Map, Basin_Street_Map and Georef_1904 (106 GeoTIFFs, transforms with spline, scripts) committed to Ben's computer.

## Waiting on Ben

- Confirm the reading of "the rest of the deck" (basin method).

## Done 2026-10-13, later (page versions 21-22, log 10u)

- Picks 22-35L, 22-37L, 22-37R (agents). City-wide OSM projected: lph/osm_north.geojson; corners lph/osm3.pkl.
- fit22 (HALVES=16L,16R,31L,31R,33L,34L,34R,35L,37L,37R USE_ALL=1 USE_T12=1 OSMPKL=osm3.pkl) -> lph/tf22_cw.json (v1 kept as tf22_cw_v1.json).
- post.py: Central Parkway follows osm_north (SBG_OSMP_PARKWAY), 90 ft north of N 4,333,300. Run: cd sbg/fit; SBG_SUFFIX=_n SBG_OSMP_PARKWAY=<SP>/lph/osm_north.geojson python3 post.py; then copy basin_sanborn_n.json to basin_sanborn.json and deckpage/basin.json; then python3 lph/add22.py --install (appends the 1922 streets, joins CP to Ludlow). Backups: basin_sanborn_n_v20.json, deckpage/basin_v20.json, post_pre_cp.py.
- tiles_n.py: 1922 underlay (POLY22: 34L, 34R, 37L, 37R, 16R strip), 1904 always wins. Backups tiles_n_v20/, tiles_n_v20.py, sheets_v20.json, index_v20.html.
- Exports: Basin_Street_Map (README, geojsons, sanborn1922_valley_transforms.json, picks zip), Georef_1904/lph_scripts.zip.

## Waiting on Ben (added)

- Question 4: Lower Price Hill west of the boulevard (options table sent), and whether the vol. 5 grid gets drawn for the rest of the west bank.
- Hopple viaduct level: 165.3 m or more over the APEx ramp (158.5 m), about 6.4 m above the deck.

## Done 2026-10-13, evening (page version 23, log 10v)

- Ben: RER D gradient check; option C for LPH with the north-of-8th block razed (straight Gest, basin W-E streets carried to Depot against Depot/Summer/Berlin/Evans).
- deck_gen.py: LPH_X through streets, LPH_NS (Summer, Berlin, Evans), RAZED blocks, straight Gest, W 8th from State (backup deck_gen_v12.py, deck_v12.json).
- lph/lph_grid.py -> lph/lph_streets.json (LPH 1904 grid, set "lph"). lph/add22.py now reads sbg/fit/basin_sanborn_n.json, installs 1922 streets (set "1922") + LPH grid, cuts the 1904 Hopple at Meeker, joins CP to Ludlow. Rebuild order: post.py -> deck_gen.py (copy deck.json to deckpage) -> lph_grid.py -> add22.py --install.
- Levels: lph/zprof.py samples the LiDAR 2 m DEM (Historic_Topo/LiDAR_2m, int16 decimetres).
- Open: RER D at the deck's north edge (156.8 m vs 160.1 m deck, APEx portal 151.8 m at the same spot).

## Done 2026-10-13, night (page version 24, log 10w)

- Ben ruled the combined grid (recommended set): Garrard seam, option A, W 8th and Gest on own lines, jogs at Depot, D-lite.
- deck_gen.py (backup deck_gen_v13.py, deck_v13.json): ax_line/proj helpers; TH_AX/TH_W, G_INF, seam() applied to side-E T streets in the anchor loop; W Liberty via _seam_thru; DEPOT straight (best fit of the 5 1904 vertices); LPH_NSL straight (ax_line) built before the LPH_X loop; LPH_X extend along the west segment to Depot/Summer, ends 0.3 m past; LPH_SNAP removed; RAZED from straight Depot (hard-coded vertices dropped). 45 streets, 111 blocks.
- lph_grid.py (backup lph_grid_v1.py, lph_streets_v1.json): S04 = 1904 picks; SQ streets + Burns main run + Depot squared (best fit, fixed bearings from the deck boulevard); NEW maps crossings (State/Neave slide); Evans' top vertex = deck Evans start. 13 blocks (two Burns-Evans blocks now close).
- Checks: lph/corners_built.py <deck.json> (west of Garrard north of W 8th: median 0.01, max 0.30; W 8th/Gest max 0.73). lph/seam_combo.py = the options analysis. Screens lph/shots23.
- Page backups: deckpage/index_v23.html, deck_v23.json, basin_v23.json. Exports refreshed (Deck_Street_Map, basin_sbg -> Basin_Street_Map, lph_scripts.zip) and committed.

## Done 2026-10-13, late (page version 25, log 10x)

- Ben: Gest's State intersection moves onto the grid (fair razing); W 8th straightened slightly, mostly on the grid.
- deck_gen.py (backup deck_gen_v14.py, deck_v14.json): STATE_1904 (+80 m north), _to_state(); Gest = State end on 93.641 ray from its Garrard point; W 8th on TH_W8 = (own chord 94.248 + 93.641)/2 = 93.944.
- lph_grid.py (backup lph_grid_v2.py): NEW maps State's W 8th and Gest vertices to the deck ends; Evans' corner carried 0.3 m past W 8th (noding).
- Analysis lph/w8gest.py. Page backups index_v24.html, deck_v24.json, basin_v24.json. Exports refreshed and committed.

## Done 2026-10-13, night (page version 26, log 10y-10z)

- Ben agreed the RER A design (10y) and asked for everything since v25: RER A drawn, Exposition Boulevard, Garrard moved west 9 m as a whole, the west side filled W 6th to Ralston (zones 1-3).
- rera/rera.py rewritten (backup rera_v1.py): reads KMZ RER-1a [3]+[2] and RER-1c raw from kmz/rer_lines.json (not context.json); profile north of Hopple (167.0 m from the RER D crossing to the Northside platform end, 3.3% to Linden 144.2 m); structure states (deck, tunnel/box <= -4.6 m, ramp, viaduct >= +5 m), level marks, crossings with the portal rule (10j.7). Westwood curve now 62.6 deg (63.4 on the simplified line).
- deck/west_valley.py (new, called from deck_gen.py after RAZED): zone 1-3 streets, rail barriers (RER A profile, APEx north approach 151.8 m + 0.94% to Marshall, TRIMET 3D trunk and Greensburg, APEx Vandalia/Norwood KMZ north of the tip), cuts (60 m stub rule; zone 1 streets fall back to their T when the west piece goes), WV_AREA (zones minus basin blocks/streets), VOIDS (open rail + Hopple viaduct), 1904 boundary streets -> lph/wv_1904.json.
- deck_gen.py (backup deck_gen_v15.py, deck_v15.json): G_SHIFT 9 m (AG_FIT keeps the fit), Exposition Boulevard, WV integration, block side WV, layers wv_cut and rail_open, cut-mark de-dup. 91 streets, 276 blocks (153 off the deck).
- add22.py (backup add22_v25.py): installs lph/wv_1904.json; rer_cut() cuts basin streets at RER A from the profile (Chambers, Lingo, Dane) and adds wv_cut points.
- transit/build_transit.py (backup build_transit_v25.py): RER A pieces from rera.json; rer_struct and rer_marks in context.json.
- Page (backup index_v25.html, deck_v25.json, basin_v25.json, context_v25.json): West side zoom, legend, RER structure drawing, cut marks, rail_open, notes. Published version 26.
- Rebuild order: rera.py -> deck_gen.py -> cp deck.json deckpage -> lph_grid.py -> add22.py --install -> rera.py (crossings) -> build_transit.py -> cp transit/context.json deckpage.
- Plots: wv/plot_wv.py x0 y0 x1 y1 out; wv/diag.py; screens lph/shots27.
- Exports refreshed and committed (Deck_Street_Map incl. west_valley.py, rera.py, rera_A_long_section.json; Basin_Street_Map; lph_scripts.zip).

## Open after v26

- RER D: KMZ (page) turns west at the deck tip; TRIMET 3D runs up the trunk to Arlington first (10z.12).
- Garrard line cut by the APEx ramp 70 m north of Marshall (5.7 m) (10z.13).
- Tracker 2J vs the 1913 deck (10y.6), not edited.

## North trunk viaduct v3 (2026-10-13, nv/, not built; log 10za.13-10za.21)

- Chainage fixed: nv/profile.py rebuilds the APEx path in true vertex order (old profile in profile_v2.*); v1/v2 numbers north of the deck tip were ~260 m long.
- nv/v3.py: levels and checks (band 0.787% tip to Ludlow s 5,300; Transvalley dip 2% to 159.8; Indianapolis 1.3% from s 3,800; B/D 3.3% ramp in the vacated Indianapolis slot, D split s 4,242, Arlington (B) elevated s 4,300-4,504; R5 0.7% to 167.0, over the band s 4,822-4,951). nv/v3_box.py is the rejected box-station variant.
- nv/sketch3.py -> nv/North_Trunk_Viaduct_sketch_v3.png (sent to Ben).
- Waiting on Ben: v3 arrangement (Indianapolis west, ORR east, departs from his east-side idea), Sassafras cut. Build list once agreed: tracks.json north approach (drop the 0.94% portal ramp, Indianapolis climb, Transvalley dip), B/D ramp and Arlington on the page, D on the new path, R5, deck/basin voids and cuts, Hopple at deck level, context.json, publish v27.
- v4 (10za.24-10za.28): order Transvalley/R5, APEx D/N 4, Indianapolis 2, TRI B/D 2, ORR E 2; B/D 0.40% under the deck from Camp Washington to Monmouth, 3.0% to Arlington (B) at 158.5 m centred on the KMZ point, Sassafras lowered 2.4 m; Indianapolis 0.75%, Indianapolis+D west together from s 4,302 (600 m curve); R5 leaves the west pair north of that. nv/v4.py, nv/sketch4.py -> North_Trunk_v4_long_section.png.

## v5 north trunk (10za.30, proposal)
- nv/v5.py -> nv/v5.json; nv/sketch5.py -> nv/North_Trunk_v5_long_section.png (sent). v4b kept as nv/v4.py / v4b_final.py.
- All paths on one viaduct Ludlow-Camp Washington. CW elevated at band (s 2,964-3,168, 165.1-165.4). B/D dive 3.3% to 151.64 at s 2,556, level to Straight 2,403; ramp 2,758-2,964, trough 2,594-2,758, box from 2,594.
- Dive streets: Garrard +1.9 (box), Rawson -1.2, Willow -1.4, Township -2.8, Meeker and New street N end.
- Indy+D leave band s 3,644, 2.5% to 174.3 by 3,971, KMZ curve s 3,924 R~745, clear of TV/R5 4,202. D flat junction 3,168-3,644.
- Arlington level 164.6 at s 4,044-4,248; B back on band 4,397. Widths 75.75 m deck CW-Arlington; 56.75 north.
- Build list for v27 after Ben agrees: tracks.json north approach, context.json, deck/basin voids (trough void only at the dive; rail_open goes), street restorations and re-grades, Hopple at deck level, R5, D/Indianapolis, Arlington, CW elevated.
- 10za.32 (ruled): B every 4 min (15 tph), D every 8 min (7.5), 22.5 tph shared CW-CUT on one pair; D junction is a flyover (northbound D east of B, climbs with Indy+D, over B by s 3,924); s 3,800 deck 77.0 m. sketch5.py panel D redrawn.

## Done 2026-10-14 (page version 27, log 10za.33-10za.34)
- Capacity check (10za.33) from Cincinnati_Rail_Ridership_Model_v17.xlsx (uploads): B 15 x ~2,300 = 34,500/h vs <= 28,669; D 7.5 x 2,300 = 17,250 vs ~9,900-16,400.
- Rebuild order now: cut/tracks_gen4.py -> rera.py -> deck_gen.py -> cp deck/deck.json deckpage -> lph_grid.py -> add22.py --install -> rera.py -> build_transit.py -> cp transit/context.json deckpage.
- nv/geom27.py is shared by tracks_gen4, build_transit and west_valley (trunk NT, offsets by C chainage, profiles, tri_centre, bd_tracks, d_centre).
- Backups: deckpage/*_v26.*, deck/deck_gen_v16.py, deck/west_valley_v26.py, lph/add22_v26.py, rera/rera_v26.py, transit/build_transit_v26.py.
- Screens lph/shots28 (shots28.py; local server python3 -m http.server 8765 in deckpage). Exports: outputs/Deck_Street_Map refreshed (+ geom27.py, tracks_gen4.py, build_transit.py).
- Published version 27.


## 2026-10-14 page version 28 (editor)

- deckpage/index.html = v28 (backup index_v27.html, copy index_v28.html; WIP copy index_wip_part3.html). context.json now carries ids (metro/rer id, plats id/pid/st).
- Editor: quadratic curves per segment (edits[kind][id].k), transit edits (edits.transit), stations (edits.stations[key] = {del, s: {pid: {t, o}}}, key = sys:name:round(E):round(N)), block {t, n}.
- Tests: lph/test29.py, test29b.py, test29c.py, test29d.py (local server: python3 -m http.server 8765 in deckpage). Shots lph/shots29.
- Log 10zb. Next: regenerate layers from saved edits must read transit, stations, k and block names.


## 2026-10-15 page version 31 (trunk centred between J1 and J2)

- nv/geom27.py (backup geom27_v27.py): NT replaced between s 3,168 and 4,950 (straight Ethan-Brashears on the J1/J2 midline less 11.25 m, cubic joins); _S by length between the joins; ORR E slew S_OE0/S_OE1 = 4,430/4,780; group_track eases from the NT offset onto the IKW offset.
- Pre-change outputs in bk30/ (tracks, deck, context, basin, rera, basin_sanborn). Page copy index_v31.html. Log 10zc.
- Local server dies between turns: start with setsid nohup python3 -m http.server 8765 in deckpage.


## 2026-10-15 page version 32 (constant-radius curves)

- arcs/fitarcs.py (Python) and arcs/fitarcs.js (same rules, embedded in the page); arcs/evalfit.py, arcs/plotcheck.py, arcs/parity.js.
- build_transit.py (backup build_transit_v31.py) fits Metro and KMZ RER lines; context lines carry c (points) + k (controls) + curves; ids from g0 (the drawn line).
- Page: base k on transit features (ctrlOf falls back to it, seedEdit copies it into a new edit); Fit curves button; curveGroups radius labels. Copy index_v32.html.
- Ben's transit edits refitted (db version 170); before: arcs/ben_transit_before_fit_v169.json. Log 10ze.


## 2026-10-15 page version 33 (plots and land use)

- plots/: common.py (layers, tiles), frontage.py (faces, scan2, face_width, cuts_for), gen.py (block_plots), run_all.py -> plots_all.json; build_plots.py -> deckpage/plots.json ({o, labels, plots: [id, block, kind, street, u0, [label idx], rings as delta dm]}).
- Labels: plots/crops (534 crops, manifest.json), plots/labels/INSTRUCTIONS.md and agent_00..17.json (5,809 labels).
- Page engine: plots/engine.js spliced in by plots/patch_page.py (reads index_v32.html; rerun it after editing engine.js). Copy index_v33.html. JSTS 2.12.1 from jsdelivr; npm copy in jslib/package/dist for tests.
- Tests: plots/ptest.py (load), pinter.py, pinter2.py, predo.py, pfull.py, pdraw.py; data plots/db_data.json (deck/layout version 298). Page ?debug exposes window.__S.
- Log 10zf.


## 2026-10-15 page version 35 (select several, merge)

- plots/patch_v34.py runs after patch_page.py (python3 plots/patch_page.py && python3 plots/patch_v34.py). Copy index_v35.html. Test plots/pmulti.py.
- Streets merged away: edits.streets[id] = {del, into}; merged street carries mg {ids, pre}. Engine treats del as a changed street with no new corridor.
- Log 10zg: angled lots (open, later) and Ben's rejection of the plot method (open; options put to Ben: trace by eye with a check pass, line detection, plain regular lots, or regular lots plus marked big sites).


## 2026-10-15 page version 36 (CUT 1931, General CUT Path, region; plots unfinished)

- Rebuild order: cut/tracks_gen4.py -> cut/apex_region.py (region APEx; reads and rewrites deckpage/tracks.json) -> ... deck_gen.py -> add22.py --install -> cut/cut1931.py (building, concourse, plaza, former Lincoln Park; Dalton underpass SB0631U, removes SB0899 and SB0626, widens SBB0453) -> transit/build_transit.py (copy context.json to deckpage).
- cutplan/: plan_full.png (from Ben's TIF), georef.py -> georef.json (affine), trace.py -> cut1931_utm.json.
- Page: python3 plots/patch_page.py && python3 plots/patch_v34.py && python3 plots/patch_v36.py. Copy index_v36.html; data copies *_v36.json. Tests plots/pshots.py (views as JSON), plots/pregbtn.py (clicks, Region button); plots/db_data.json now deck/layout version 335 (old copy db_data_v298.json).
- Log 10zh. Open: Ludlow convergence of APEx and the CS line (10zh.6).


## 2026-10-15 page version 37 (CUT from the drawings, CVG flyover, Ludlow)

- Rebuild order: cut/tracks_gen4.py (reads cut/field1931.json and ludlow/kmz_south.json) -> cut/apex_region.py -> ... deck_gen.py -> add22.py --install -> cut/cut1931.py (reads cutfp/fp_utm.json, cutplan/cut1931_utm.json, cutplan/plaza_utm.json) -> build_transit.py.
- Sources: cutfp/fp.png (Ben's floor-plan image) and fp_trace.py; cutplan/tracktrace2.py -> trN.json, trS.json -> tracks_by_number.json -> field1931.py -> cut/field1931.json; cutplan/plaza_trace.py -> plaza_utm.json; ludlow/kmzscan.py -> kmz_south.json.
- Page: patch chain through plots/patch_v37.py. Copies index_v37.html and *_v37.json; backups tracks_gen4_v36.py, cut1931_v36.py, tracks_v36.json. Tests plots/p37.py.
- Log 10zi.


## 2026-10-15 page version 38

- tracks_gen4.py: CVG at grade (ludlow/cvg_block.py), Kentucky tunnel profile (ludlow/lud_profile.py, reads topo/dem2m), lower platforms centred (LX0), M full length. apex_region.py marks the Kentucky trunk as tunnel. cut1931.py moves the west headhouse east once (moved_m guard), extends the west park, trims the precinct.
- Page chain through plots/patch_v38.py. Copies index_v38.html, *_v38.json; backups *_v37.py. Log 10zj.


## 2026-10-16 page version 39

- tracks_gen4.py: CVG Express block (ludlow/cvg_block2.py): own span east of the APEx bridge (CVG_OFF 24.75 from the APEx centre), L_RUN 260 / L_REV 380 in Ludlow; intercity pair to the TRIMET CS viaduct alone (z_merge from TB cs z). Backup tracks_gen4_v38.py.
- Page chain through plots/patch_v39.py (plot locks: edits.blocks[id].lk). Copies index_v39.html, tracks_v39.json. Test plots/p39.py. Log 10zk.
- Plot redraw must skip blocks with lk (keep their current plots: replay the engine with the saved edits before replacing plots.json).


## 2026-10-16 page version 40

- cvgkmz/: CVG_Layout.kml, CVG_Express_New.kml, cvg_kmz.json (staged from Ben's computer). cvg/build_airport.py -> deckpage/airport.json.
- tracks_gen4.py: CVG block ludlow/cvg_block3.py (with the APEx to Erlanger, then the KMZ line); CORR = KC + APEx KMZ line. apex_region.py skips kind cvg in its cover. REG west edge 699,000 in tracks_gen4, apex_region, build_transit (backups *_v39.py; context_v39.json).
- Page chain through plots/patch_v40.py (airport layer, --cvg colour, CVG zoom). Copies index_v40.html, tracks/context/airport _v40.json. Test plots/p40.py. Log 10zl.



## 2026-10-16 page version 41

- cvgkmz/final_raw (CVG Express Final.kmz) -> cvgkmz/cvg_final.json (UTM). tracks_gen4.py CVG block is ludlow/cvg_block4.py (spliced in; keep the two the same): Today route with fillets, five stations (cvg_plat polygons, cvg_station markers), yard (cvg_yard), maintenance building (cvg_shop), 1969 line (apex kind cvg_former, state former). Backup tracks_gen4_v40.py; ludlow/cvg_block3.py now holds the real v40 block (with the APEx KMZ corridor _AK).
- Rebuild: cut/tracks_gen4.py -> cut/apex_region.py (no transit or deck rebuild needed for this change).
- Page chain through plots/patch_v41.py. Copies index_v41.html, tracks_v41.json. Test plots/p41.py. Published as Version 41 (index.html and tracks.json). Log 10zm.


## 2026-10-16 page version 42

- tracks.json gains top-level 'cvx' (airside line from the split: v, k, stations, plats, tracks; platform_m 200). The generator writes it (json.dump with cvx=CVX_DATA); apex_region keeps it. CVG pieces in features stop at the split.
- Page chain through plots/patch_v42.py: sys 'cvx' in buildTransitFeats/buildStations (tracks.json now loads before them), PW/H0/EDGE, visT (CUT tracks layer), drawing, panels, export; airport drawn before transit. Copies index_v42.html, tracks_v42.json, tracks_gen4_v42.py, ludlow/cvg_block4_v41.py (v41 block). Test plots/p42.py. Log 10zn.


## 2026-10-17 page version 43

- fill/fill_blocks.py (after cut1931.py and build_plots.py; reads plots/live/deck/layout.json, a fresh copy of the live db, for hand-edited blocks; marks deck.json fill17 and will not run twice). Pre-fill copies fill/*_pre.json; outputs deckpage/deck.json, basin.json, plots.json (copies *_v43.json). Log fill/fill_log.json.
- plots/engine.js: streetWv/streetRuns/corridorRuns (widths per segment). Backup engine_v42.js.
- Page chain through plots/patch_v43.py (stretch picks S.rng, setWidthRange, filletRange, remapWv in setEdit, strokeStreet). Tests plots/p43.py, p43b.py. Log 10zo.


## 2026-10-17 page version 44

- cskmz/cs_ky.json (CS Bridge KY Approach.kmz), spankmz/spans.json (Bridge Spans.kmz). tracks_gen4.py: APEX_SHIFT (7.5 m east), APB from the spans, CSB from the CS span, LWS from the KMZ CS approach then TRIMET, Ludlow straight; offs() falls back point by point when shapely splits an offset. cvg_block4.py: CVG_OFF from the CVX span, CVG_TUN 15.75 past the Kentucky span end (var_offs, cvg_d); pieces cut on the centre line. Backups *_v43.py.
- cut/plaza_align.py (after cut1931.py; marks deck.json aligned17); the west park rebuilt as a grid rectangle (inline step, see log 10zp.5). Pre copies fill/*_prealign.json.
- Page chain through plots/patch_v44.py. Copies *_v44. Log 10zp.


## 2026-10-17 page version 45

- cut/ezzard.py (after fill_blocks/plaza_align; marks basin.json ezzard17): EZ1-EZ3 replace SB0817-SB0819, blocks and plots cut. Pre copies fill/*_preez.json.
- tracks_gen4.py: MERGE and BANK_N at the CS span's north end; cs_full onto the span line (120 m lead) and across it exactly.
- Data copies *_v45.json (index.html unchanged from v44). Log 10zq.


## 2026-10-17 page version 46

- cut/cutclean.py (composition: axis -3.0 deg, Kenner SB0799 and Hopkins SB0775 straight and parallel Garrard to Freeman with Ben's merges baked in; S013, S012, SB0776, SB0777, SB0021 removed; terminal group turned onto the axis; plaza mirrored; EZ1 on the axis at 57.33 m) imported by cut/cutclean2.py (block and lot recut, writes the data; marks deck.json clean17). Run after ezzard.py. Reads plots/live2/deck/layout.json. Pre copies fill/*_preclean.json.
- db: streets S012, S013, SB0776, SB0777, SB0799, SB0775 edits cleared (now in the base data).
- Diagnostics cut/diag2.py (blocks, lots, streets, CUT shapes); test plots/p46.py (plots/db_data_v46.json). Copies *_v46.json. Log 10zr.


## 2026-10-17 page version 47

- tracks_gen4.py and ludlow/cvg_block4.py (kept identical in apex_zN): APEx straight 0.43% from FN0 to the bridge; H = 5.0 (W 8th raised 5 m), intercity portal marker in the W 8th south wall, Horne marker; summary cs_portal. Backups *_v46.py; copy tracks_v47.json. Rebuild tracks_gen4 -> apex_region. Log 10zs.


## 2026-10-17 page version 48

- cut/structures.py (after tracks_gen4 + apex_region) -> deckpage/structures.json (layer struct polygons, struct_w width labels); tracks_gen4 summary gains prof (intercity and C&O pair rail profiles). Page chain through plots/patch_v48.py (layer lVia / S.layers.via, drawStruct, click info). Copies index_v48.html, tracks_v48.json, structures_v48.json. Test plots/p48click.py. Log 10zt.


## 2026-10-17 page version 49

- cut/deckedge.py (after cutclean2; marks deck.json edge17): deck outline smoothed (raw in fill/deck_outline_raw.json); blocks joined or given slivers along the old edge per street face; lots carried across the band. Pre copies fill/*_predeckedge.json; copies *_v49.json. Diagnostic cut/diag3.py (x0 y0 x1 y1 out.png [prefix]). Log 10zu.


## 2026-10-17 page version 50

- cut/edgelots.py (after deckedge; marks plots.json edgelots17): lots in every block within 7 m of the traced edge carried straight across the band, gaps filled, small block notches filled. Pre copies fill/*_preedgelots.json; copies *_v50.json. Screenshot tests need a 20 s wait (plots/p46.py) for Ben's merges to replay. Log 10zu.6-7.


## 2026-10-17 page version 51

- plots/patch_v51.py (index.html and plots/engine.js): streetOv / offLine / runJoint, runs carry o and oc, shiftLimits / setShiftRange, sideways controls in the stretch box. Chain: ... patch_v48.py && patch_v51.py. Copy index_v51.html, backup engine_v50.js. Test data plots/db_data_t51.json (plots/p51.py). Log 10zv.


## 2026-10-17 page version 52

- plots/patch_v52.py: setWidthAlign (width + Sits on choice), selection highlight by runs, no joint disc on straight joins. Chain: ... patch_v51.py && patch_v52.py. Copy index_v52.html. Click test plots/pui.py (Edit, pick points 113 and 119 of Central Parkway). Log 10zv.3.

## 2026-10-17 page version 53
- plots/patch_v53.py (index.html and engine.js): streetJo / joInfo, runs with shifted joints (jo), joBox slider when one point is picked; stretch side controls removed. Test plots/pui53.py (selects SB0595 directly, clicks point 106). Log 10zv.4.

## 2026-10-17 page version 54
- cutgeo/: cut_layout.tif (Ben), warp.py -> cut_utm.png/json, sym.py (axis), rect.py -> rect.png/npy/json (plan frame u,v), rv.py / prof.py (tracing aids), ov.py (overlay check). cut/cutplan.py (layout) imported by cut/cutplan2.py (recut; marks deck.json plan17). Pre copies fill/*_preplan.json; copies *_v54.json. Log 10zw.
- v55: cutplan.py HO1 -105.5, band rectangles for headhouse/park/square, SBB0453 = plaza box one lot (rerun from fill/*_preplan.json). Copies *_v55.json. Log 10zw.6.
- v56: cutplan.py traces the building/concourse from the floor-plan GeoTIFFs (cutgeo/warpfl.py, flv.py, flov.py), ramps redrawn in the arms, precinct to u -434. Copies *_v56.json. Log 10zw.7.
- v57: cutplan.py building from cutgeo/ff_mask.json, drives refitted, headhouse clear of structures.json; patch_v57.py (structures drawn after blocks). Copies *_v57. Composite check cutgeo/pagecmp.py X Y scale tif out. Log 10zw.8.


## 2026-10-18 page version 59
- cut/railx.py (after tracks_gen4 + apex_region; adds transfer track, crossovers, switch markers; marks summary railx), then cut/structures.py (includes kind transfer). cvg/taxi.py (cvgkmz/cvg_layout.tif -> airport.json layer cvg_taxi). plots/patch_v59.py (switch markers, cvg_taxi drawing). Copies *_v59. Rebuild order now: tracks_gen4 -> apex_region -> railx -> structures. Log 10zx.


## 2026-10-18 page version 60
- cut/campw.py (marks deck.json campw18; pre copies fill/*_precampw.json). cvg/airside.py (from airport_v58.json; layers cvg_taxi, cvg_taxi_cl, cvg_apron, cvg_stand; replaces cvg/taxi.py). plots/patch_v60.py (draws them). Copies *_v60. Log 10zy.
- v61 (18 Oct): measured CVG stands (cvg/gates.py -> cvg/gates.json, quota 0.4; params cvg/gates_params.json incl. T1B/T4 shift +90 m N), cvg/airside2.py -> deckpage/airport.json, plots/patch_v61.py. Log 10zz.
- v62 (18 Oct): Sanborn extension (lph/solve_ext.py -> tf_ext.json, tiles_ext.py, sheets_merge_ext.py). CVG gate check pending Ben's option (log 10zza/10zzb).
- v63 (18 Oct): CVG landside court, T2/T3 reshaped, T1A south; params cvg/gates_params.json (v61 copy gates_params_v61.json), airside2 (v61 copy airside2_v61.py). Log 10zzc.
- v64 CW scrap (cut/cwscrap.py, db 1034); v65 CVG realistic (gates_params.json = gates_params5, airside2). Log 10zzd/10zze.

## 2026-10-19 page versions 77-78
- Sanborn TE (v77) and MA (v78): picks sbg/picks/s107-110, s127-130, s161-200, s325-332; lph/solve_ext.py -> tf_ext2.json (osm_east.geojson, OSM_SKIP); lph/tiles_ext2.py; sbg/fit/run_build_safe.py -> streets_raw_te/_ma; sbg/fit/add_ext.py SUFFIX SET PREFIX SHEETS --install (reinstall replaces its own set; second loose-end pass 15 m). basin backups basin_v76.json (pre-TE), basin_ma1.json (MA before loose-end pass). Log 10zzq.

## 2026-10-20 page version 83
- Volume 3 rest: picks sbg/picks/s228-300 (backups sbg/picks_bak_1020); solve: NEW=<49 sheets> FIXED_EXTRA=lph/tf_ext.json,lph/tf_ext2.json OUTSFX=3 python3 lph/solve_ext.py -> tf_ext3.json (ext_extra.json init_north_deg for 277/278/286/292); lph/tf_all_v3.json = tf_all_ma + tf_ext3; lph/tiles_ext3.py (panels_ext3.json); build SBG_SUFFIX=_v3 SBG_TF_EXTRA=../../lph/tf_all_v3.json; add_ext.py _v3 v3 SV <frames> --install (stub extension, dogleg pass). Backups basin_v82.json, sheets_pre_v3.json, tiles *.pre_v3. Log 10zzr.

## 2026-10-20 (v84): 1922 plate 35 north
- cuf/: common.py (px2ben/ben2px, Ben's EPSG:3857 transform), check_osm.py, fit_corr.py (georef good, 3.1 m rms; not corrected), build22.py (--install; set c22, SC ids; restores cuf/c22_removed.json first), overlay_tiles.py (tiles *.pre_c22), overview.py. Log 10zzs.
- Rerun overlay_tiles.py after any tiles render in the area; rerun build22.py --install after any v3 reinstall.
- Published version 84 (basin.json, 12 tiles_n tiles, tiles_n index/overview).

## 2026-10-20 (v85): 1922 layer, Millvale grid
- 1922 layer: cuf/plates.py (plate registry), cuf/tiles22.py -> deckpage/tiles_22 (index, overview); page layer l22/op22 (index_v84.html backup). tiles_n is 1904-only: lph/tiles_all.py (full renderer, POLY22 excluded; REDO=22 for the halves' tiles).
- Plate 38: picks sbg/picks22/s22-38_a..f (e pending), cuf38/match.py (png->tif SIFT seed), cuf38/fit38.py -> fwd38.pkl, model38.npz; cuf38/fwd38lib.py. Then rerun cuf/tiles22.py.
- 1904 refit onto 1922: cuf/x1904.py <frames> (matches, uses tps_pre1922.pkl), cuf/tps1922.py <frames> (adds frames to lph/tps.pkl from tps_pre1922.pkl). Then tiles_all.py REDO=<frames>, v3 rebuild (build.py + add_ext.py), build22.py --install, millvale/build_mv.py --install.
- Millvale: millvale/build_mv.py (set mv), grid_area.json, blvd2.json (Ben's KMLs). deck.json scrapped streets removed (deck_v84.json).
- v86: plate 38 placed (cuf38/fit38.py), 1904 frames 256-299 bent onto 1922 (cuf/tps1922.py; lph/tps.pkl, backup tps_pre1922.pkl), tiles re-rendered, v3 rebuilt (sbg/fit run_build_safe.py SBG_SUFFIX=_v3 SBG_TF_EXTRA=../../lph/tf_all_v3.json; add_ext.py _v3 v3 SV <49 sheets> --install), then build22 (c22_removed restored first by hand; old copy c22_removed_pre_refit.json) and build_mv reinstalled. Millvale diamond park in build_mv.py. Local page server: python3 -m http.server 8765 in deckpage.
- v87: plate 38 streets (cuf38/build38.py, set c38, ids SK); full street rebuild cuf/rebuild_streets.sh (undo_sets, v3, build22, build38, build_mv).

- v88 (20 Oct): KMZ streets exported as corridor polygons at drawn width plus centre line; SK0010 East Nixon fixed.

## 2026-10-21 page versions 89-90 (1922 plates 66-70)
- cufp/: prep.py (stage + SIFT seed), fit.py (2 passes; name seed without GeoTIFF; ALIAS), fwdlib.py, build.py N (sets c66..c70, PLATE_ORDER 66,68,67,69,70, second loose-end pass), check_osm.py, plot_build.py, overlaps.py, frames_under.py, gaps.py, strips.json, PROCESS_1922.md. Picks sbg/picks22/s22-66..70_a..f.
- cuf/x1904.py base-name matching; tps1922 over 47 frames (backup lph/tps_v87.pkl); tiles_all REDO (*.pre_66); tiles22 106 tiles.
- tiles12 merged to 1000 m tiles (manifest 512-file limit); backup scratchpad/tiles12_v88.
- rebuild: cuf/rebuild_streets.sh (now includes cufp builds).

## 2026-10-22 page version 91
- rer1023/: kml.py (Ben KMZ -> ben_1021.json), apply.py (reads deckpage/context_v90.json, tracks_v90.json, dbread2 layout; writes context.json, tracks.json, geom.json), plot*.py. Then millvale/build_mv.py --install. Page test plots/p91.py (db_data_v91.json = layout without the trunk edit). DB layout v1580: trunk transit edit removed.
- v93 (22 Oct): R5 spur blended under the Indianapolis + D deck in rer1023/apply.py (spur s 348-884); cross-grid deck ~21.5 m (was ~40). build_mv keep-out = 4.2 m buffer, gaps <6 m. Backups *_v92. Log 10zzy.10.
- v94 (22 Oct): R5 spur rebuilt in rer1023/apply.py as tangent arcs: 500 m off the W pair at N 4335691 onto the deck centre (D s 2339), deck centre to D s 1579, 200 m single track onto trunk s 5185. rer1024/east.py and west.py give the radius vs extra-structure tables. structures.py includes R5; D and B rer_struct redrawn on the current lines (B/D south still stale). Log 10zzy.11.
- v95 (22 Oct): page street rename (edits.streets[id].n), delete (del, no into), restore list and duplicate finder in the Edits panel. Rebuilds must keep street ids stable (or carry n/del). Test: plots/stedit_test.py. Log 10zzy.12.
- v96 (22 Oct): terminus Metro platforms added in rer1023/apply.py end pass (Wayne L13, Kirby L12, Northside L8, Pennsylvania L5). Log 10zzy.13.
- v97 (22 Oct): street Heading box (read, set about a kept end, copy/match), drag readout heading. Log 10zzy.14.
- v98 (22 Oct): stretch headings in the Between two points box (turnRange). Log 10zzy.15.
- v99 (22 Oct): Northside/Camp Washington 1922 halves refitted (cuf_cw/), 37L/37R second read, 1904 frames bent (86), SB layer shifted by cuf_cw/shift_sb.py (ids kept). Log 10zzy.16, PROCESS_1922.md section 9.
- v100 (22 Oct): highway update. hwy/build_hwy.py --install (deckpage/hwy.json; basin HW streets, Colerain wv, Blue Rock/Spring Grove 21.6 m, Ludlow at ground, blocks/plots trimmed; reads dbread6 layout for Central Parkway's end). geom27 Z_LUD 162.5 at s 5369 + north_z fill; apply.py end pass (marks, B fill); structures.py section 7. CPW continuous T on Albone's axis, leg tangent at both ends (R 1000 m) through regraded hill. Spring Grove Cemetery outline sgc/. Order: apply.py -> structures.py -> build_hwy.py --install (after any street rebuild too). build_mv not rerun (would shift Millvale carried streets onto the v99 SB shift). Log 10zzy.17.
- v104 (23 Oct): Line 3 realigned from Ben's KMZ (rer1023/line3_1023.kml, pass in apply.py; Kenard to the L1/L3 crossing, Marshall moved; Ben's L3 transit edit deleted, DB 1832). build_hwy reads dbread7; leg 24.4 m from Ben's new CPW end. Log 10zzy.18.
- v105 (23 Oct): Metro drawn to the RER limits (apply.py pass after Line 3; outer pieces, 204 stations). Log 10zzy.19.
- v106 (23 Oct): CPW 150 ft end: centre bus lanes, 3.0 m median, parking, tree strip, 6.76 m walks (build_hwy cpw_side). Log 10zzy.20.

## Norwood Central (23 Oct, discussion only, nothing on the page)
- Ben's "Station Area" KML -> norwood/area_utm.json (8.75 ha, 916 x 193 m min rect). Along the page APEx line (straight, bearing 108.7 deg, s 4283-5209): width 47 m at the west tip, 106-110 m from s 4533 to 4933, south side narrows at the east end, NE prong at s 5083-5200.
- Sketch norwood/sketch.png (norwood/sketch.py): 8 tracks one level. N to S: APEx side platform 488 m, T8, T7/T6 through, T5, APEx side platform; T4 + island (X1, L75) + T3; T2 + island (R1-R3, L71) + T1; headhouse 27 m deep on the south; track field 68 m. APEx platforms s 4490-4978, ORR s 4545-4850. TRI E + L3 boxes below on the axis; L4/L14 under Montgomery Rd (s 4459); TRI A crosses under at s 5061.
- Open: what runs on the NE prong (canon registers the Norwood-Blue Ash lower approach; ground rises NE so TRI A cannot portal there). L73 listed on APX-0/1a/1b but rerouted via the Oasis by the Blue Ash amendment.
- v2 (Ben): headhouse not bound by the area (area = tracks/platforms only). Transvalley lines (unmapped city layer): Norwood-Hamilton (KML starts mid-station s 4697, east along the axis, NE with the APEx diagonal, north to Reading at 721687,4338218, then Hamilton) and Cincinnati-Waynesville via Lebanon (through from CUT along the axis, out the NE prong from s ~5016). Files norwood/tv/*.kml, tv_utm.json.
- sketch2 (norwood/sketch2.py/.png): 12 tracks. Offsets from page APEx line: ORR T1 -66, T2 -54.3, T3 -49.8, T4 -38.1; APEx T5 -25.6, T6 -20.6, T7 -16.1, T8 -11.1 (side platforms -27.3/-35.6 and -1.1/-9.4); Transvalley T9 +1.4, T10 +13.1 (Hamilton island), T11 +17.6, T12 +29.3 (Waynesville island). Track span 95.2 m. East exit order S-N: Oakley, X1/L75, APEx, Hamilton; Waynesville on the prong.
- v3 (Ben: keep APEx through tracks straight): sketch3.py/.png. Through pair dead straight at +4/+8.5 (6.25 m north of page line, parallel) for the whole area; set by the east exit (Oakley -14/-9.5, X1/L75 -5/-0.5 above the SE corner at -15). Platform tracks T5 -1, T8 +13.5; APEx side platforms 6 m. ORR T4 -10.68, T3 -22.36, T2 -26.86, T1 -38.54. Transvalley one island T9 +23.18, T10 +34.86 (edge +37.4 vs +38). South strip -41 to -69 free -> headhouse. Open: Transvalley 2 vs more tracks (needs service levels).
- v4 (Ben: APEx straight, everything around it): sketch4.py/.png. APEx through pair on the page line itself (-2.25/+2.25), untouched, straight; T5 -7.25, T8 +7.25; side platforms 8.3 m. ORR south: T4 -19.23, T3 -30.91 (X1/L75 island), T2 -35.41, T1 -47.09 (Oakley island). Transvalley north: T9 +19.23, T10 +30.91, edge +33.4 (4.6 m spare to +38). Headhouse -50 to -68. Field -49.6 to +33.4 = 83 m. East exit: ORR at -7.25..-20.75, about 6 m past the SE corner (-15). West tip: ORR -7.25/-11.75, TV +7.25/+11.75.
- v5 (Ben: fine; ORR+TV platforms align; APEx extensions need not be symmetric; Hamilton platform-agnostic from the east): sketch5.py/.png. ORR, TV and new south bay island all 4545-4850 (305 m). APEx 488 m at 4455-4943 (west end at Montgomery Rd s4459; east end capped ~4980 by ORR fan-in before the south pinch). South heritage bay island, west-facing, buffers at s4870: T0 -51.59, T00 -63.27. Headhouse outside the area (-76 to -98). Field -65.8 to +33.4 = 99.2 m; 12 tracks, 10 platform faces. Area vertices in s/o: west tip s4283 -18.2/+18.1; south -68.3 at 4501, -72 at 4964, -30.3 at 5017, -17.4 at 5074, -13.9 at 5209; north +17.6 at 4337, +32.2 at 4442, +37.8 at 4513, +38.5 at 5020.
- Flag given: Hamilton reaching south (ORR/bay) faces needs a grade-separated crossing of APEx east of the station; default = TV island faces.
- v6 (Ben: APEx tunnels shortly after the Y going north, with 2-way TV N-S tracks on one side and a 2-way pair merging with SW-1 on the other, so Hamilton is platform-agnostic; APEx extensions fully one-sided, 600 ft = 183 m): sketch6.py/.png. South APEx platform 4362-4850 (all 183 m west; T5 turnout from s4262, ~20 m west of the area tip), north APEx platform 4545-5033 (all 183 m east). Forced by the area: south can't go east (edge -17.4 at s5074), north can't go west (edge +17.6 to +22 at s4337-4362). ORR west tip pair -11/-15.5; inner ORR to -19.23 by s4362. Bays are west-facing, so the only faces Hamilton can't reach.
- v7 (Ben, corrected: both APEx platforms are the same heritage 1,000 ft islands, rebuilt as side platforms with through tracks between, extended together to 1,600 ft; the 600 ft split W/E is free, extend naturally like Amsterdam/Gare du Nord): sketch7.py/.png. Both APEx platforms 4408-4896 = 450 ft W + 150 ft E of the heritage span 4545-4850. Workable range 175 ft W/425 ft E to 475 ft W/125 ft E (west limit: north edge narrows for the TV pair; east limit: ORR fan-in before the south pinch). v6 (split sides) superseded.
- v8 (Ben: building ~400 x 150 ft; consider Metro/RER): sketch8.py/.png. Building 122 x 46 m at s4636-4758, -72 to -118 (south, outside area), main tunnel s4700-4718 from the building to an inner ring exit (+70). Levels (order only): 0 tracks; -1 passages (main tunnel, west hall at Montgomery Rd, east passage); -2 L3 terminus (s4678-4830 at +15, above TRI E) and L4 terminus (moved south of the tracks, centre offset -99, page tail cut back: page L4 tail to +77 crossed L3 at the same level); -3 TRI E (on the axis, straight, station s4700-4904, 37 m east of page point); -4 L14 (station moved ~100 m south along its line beside L4) and TRI A (at the A/E crossing s5057, as page). Page conflict found: L3 runs 5 m beside TRI E along the corridor from s4056, so they must stack. Open: TRI E position vs A (E under the main tunnel with a 150 m passage to A, or E ending over A).
- v9 (Ben: 6 tracks west, 7-8 east excl. Waynesville; levels: L3+L4 same level under the station, L14+TRI A slightly deeper, TRI E deepest (deep bore, last); TRI E platform between main tunnel and TRI A; concourse Metro 4 -> TRI A through the main tunnel, parallel to L3, above TRI E; smoother merges): norwood/sk9.py (cosine-eased offsets, spline prong, checker `python3 norwood/sk9.py check`), sketch9.png with long section. APEx platforms 4438-4926 (350 W/250 E). Levels: -1 concourse s4452-5045 on the axis + main tunnel s4700-4718; -2 L3 (4678-4830, +15) and L4 (north end at -3 offset, under Montgomery Rd); -3 L14 (beside L4) and TRI A (5057); -4 TRI E 4778-4982. Radii (drawing): APEx through straight, APEx platform tracks 527 m, ORR 207-417, bays 212-232, TV 213, Waynesville 119 (Ben's prong). East ORR still ~6 m past the SE corner.
- v10 (Ben: KML of v9; platforms 400 ft): norwood/sk9.py draws sketch10.png; norwood/to_kml.py -> Norwood_Central_v10.kml (29 placemarks). Metro platforms 121.92 m.

## Metro platforms 400 ft everywhere (23 Oct)
- Page v107: rer1023/metro400.py hooked into rer1023/apply.py before the context dump (joins split platforms centred on the station, drops loop-stub platforms, re-spreads twin tracks, meta.metro_platform_m). transit/build_transit.py MPL 121.92. deckpage/index.html notes + fallback 121.92. Backups *_v106.
- Rail Profiles (A5XH4264dpWHdPdDKZgDsG) v30: profpub/index.html platform 121.92, profpub/rer/metro_rails.json; DB alignments patched (profdb/patch).
- Older Metro Profiles (EEcN5dtH7jPXMksQ4SHqAk) v3: profpub_old/index.html platform 121.92 (backup index_v1.html); DB alignments Line_1/2/4/5 platform_m 121.92 (no offsets in that schema).
- Still 500 ft elsewhere: Station_Area_Maps_Log Republic/Fountain Square models, Metro diagram profile scripts.

## 2026-10-24 page version 108 (1922 plates 82A, 83A Norwood)
- Uploads at /mnt/user-data/uploads/82A.png, 83A.png (+ GeoTIFFs, used only by prep). cufp/prep.py takes PNG=<path>; cufp/config.json "png"; cuf/plates.py PNGPATH; sb.py find 22-82A/22-83A.
- lph/osm_norwood.py -> lph/osm_norwood.geojson (fit.py loads it for plates ending in A). fit.py ALIAS: Montgomery Pike/Avenue, McNeill, Robertson Road.
- Picks sbg/picks22/s22-82A_a..f, s22-83A_a..d. cufp/82A, 83A: matches, report, fwd.pkl, model.npz.
- build.py: PLATE_ORDER + 82A, 83A (prefixes SN, SO); config merge / best_names / split. rebuild_streets.sh includes them. Backups: build_v107.py, fit_v107.py, plates_v107.py, sb_v107.py, tiles_22_v107 (md5 + index). basin was identical to basin_v106.json before install.
- cufp/frames_under2.py <plates>: none under 82A/83A.

## 2026-10-24 page version 109 (Inner Ring OH-562, Norwood Central)
- nwring/ring.py -> nwring/ring_utm.json (ring pushed north s 3,330-4,660). hwy/build_hwy.py: full ring (HW0004), Norwood street cut-backs (THROUGH set), cut adds ring + NW_AREA + NW_BLDG. Backup build_hwy_v108.py.
- norwood/to_page.py -> deckpage/norwood.json; index.html layer lNw / S.nw / drawNorwood (backup index_v108.html).
- rer1023/norwood_pass.py (idempotent) hooked in rer1023/apply.py after metro400 (backup apply_v108.py); applied directly to context.json this time. Backups deckpage/*_v108.json (hwy_v108 already had the ring from the dry run).
- Line 3's Norwood station left in place for Ben to relocate.

## 2026-10-24 page version 110 (1922 plates 75, 76)
- Uploads 75.png, 76_1.png, 75_..._1.tif, 76_..._1.tif. PNGPATH / config png for both; sb.py find includes 22-75, 22-76; strips in cufp/strips.json.
- Picks s22-75_a..f, s22-76_a..f. fit.py loads osm_norwood for 75/76. build.py PLATE_ORDER ... 82A, 83A, 75, 76 (prefixes SX, SY); config 76 merge edmonson. rebuild_streets.sh includes 75 76.
- Backups: basin_v109.json, tiles_22_v109 (md5 + index). Disk ~450 MB free.

## 2026-10-24 page version 111 (Norwood v11, Metro 3)
- norwood/sk10.py (v11 throats, LIM checker), norwood/limits_utm.json, floral_edge.json; to_page.py now execs sk10 (backup to_page_v10.py); index.html skips hidden nw_area.
- rer1023/norwood_pass.py apply_l3 (backup norwood_pass_v110.py), nw2/l3kml.py (Ben's KML); apply.py calls apply_l3 after apply. Live layout read: dbread9/deck/layout.json (v2064).

## 2026-10-24 page versions 112-114 (Norwood v12/v13, TRI A)
- norwood/sk10.py: v12 TV double junction, v13 Waynesville to the TRI/TV meet (nw2/swing_opt.py); backups sk10_v111.py, sk10_v112.py. to_page.py: elevated concourse (nw_conc), building centred (CC 4697.5), tunnel-dashed Waynesville, nw_mark; index.html draws nw_conc, nw_mark, dashed tunnel tracks.
- rer1023/norwood_pass.py apply_tria (backup norwood_pass_v113.py); context_v113.json backup. apply.py order: metro400, apply, apply_l3, apply_tria.

## 2026-10-24 page version 115 (lines unbroken, Line 5 Pennsylvania)

- rer1023/gaps_pass.py (apply_l5, then apply with the live transit edits from dbread/deck/layout.json), hooked into rer1023/apply.py after norwood_pass. Check: LAYOUT=<layout.json> python3 nw2/gapcheck2.py [context].
- Ben's live edit of M-L5-712097 was rewritten to match (layout v2080). Log 10zzy.29.

## 2026-10-24 page version 116 (Line 10 new right of way)

- rer1023/l10_pass.py (KML rer1023/line10_1024.kml, UTM rer1023/l10_new_utm.json; Baines platform at Ben's point). Log 10zzy.30.

## 2026-10-24 page version 120 (Western Hills OSM streets)

- wh/build_osm.py --install (set w1); dating helper wh/q1914.py; boundary wh/area_utm.json. Next: plates 25, 26, 28, 29 from Ben's New Sanborn folder (check which file is the second "26"), fitted to these streets. Log 10zzy.32.

## 2026-10-25 page version 123 (Price Hill plates 26A, 26B, 29)

- Plates fitted (cufp/26A, 26B, 29), tiles added with cuf/tiles22_add.py, streets installed as c29, c26A, c26B around set w1. 25 and 28 not in Ben's folder yet. Log 10zzy.33; PROCESS_1922 section 11.
- 31, 33 (v124): see log 10zzy.34; config option drop.
