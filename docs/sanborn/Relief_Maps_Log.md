# Relief Maps: Work Log

Every attempt on the topography work, in order, with its result and status. Add an entry for each new attempt, including failures, before moving on. The plan and current rules live in claude/Relief_Maps_Plan.md; this file is the history.

Status key: **Kept** (in the current pipeline), **Rejected** (don't retry), **Superseded** (worked, replaced by something better), **Open** (built, not yet decided), **Candidate** (tested, waiting on a go).

Scripts are in the session scratchpad (topo/); delivered files are under Historic_Topo on Ben's computer.

## 1. Data gathering (2026-10-07)

| # | What | Result | Status |
|---|---|---|---|
| 1.1 | 1912 City Topographic Survey, 48 sheets (CHPL scans) | All 48 in hand; 5 ft contours, bold index every 25 ft; legend datum "mean sea level" | Kept |
| 1.2 | USGS historical quads via Claude Code prompts (1914 East/West Cincinnati 1:62,500 20 ft; 1950-55 Covington/Newport and 1953 Cincinnati East/West 1:24,000 10 ft) | Already georeferenced; chamfer check (usgs_shift.py) puts them within about one pixel of LiDAR, no correction needed | Kept |
| 1.3 | Second download prompt | Duplicated files already in USGS_Historical_Quads (my miss: didn't check the folder first). USGS_Historical can be deleted | Rejected |
| 1.4 | LiDAR: USGS 3DEP 1 m DEM resampled to 2 m, 56 tiles; extended south to N4315 (remosaic.py) | dem2m.npy, 17500 x 20000, decimetres NAVD88, EPSG:26916 | Kept |
| 1.5 | OSM roads/rail/earthworks/water (motorway, trunk, primary only) | Used for zones and interstate overlap | Kept |
| 1.6 | OSM all streets + 452,789 building footprints (Claude Code, 2026-10-08) | streets_all.geojson 51 MB, buildings.geojson 139 MB; 3 self-touching polygons and closed plazas as outlines, both harmless here | Kept |
| 1.7 | Direct downloads from the workspace (USGS, proj.org, Overpass, Geofabrik, Microsoft buildings) | Blocked by the egress proxy (403); all external data has to come through Claude Code on Ben's machine | Constraint |

## 2. 1912 sheet georeference (2026-10-07)

| # | What | Result | Status |
|---|---|---|---|
| 2.1 | Fits to Ben's QGIS GCPs on sheets 29 and 30 (fit29/fit30.py) | Gave the grid origin, 39.128686 N 84.521455 W (average of the two) | Superseded |
| 2.2 | Automatic neatline corners (edges, corners, corners2, refine, refineB, comp.py), then recorded corner pixels and grid labels per sheet (write_C.py, sheet_index.json) | Grid homography per sheet | Kept as the base |
| 2.3 | Ladder check: contour crossings along lines against LiDAR 5 ft steps (ladder.py); windowed chamfer shift tests (win, wtest, diag1.py) | Datum offset 0; the sheets are on MSL matching NAVD88 within 0.5 ft | Kept |
| 2.4 | Contour skeleton and bold (index) detection by stroke width (extract, bold1-4, boldx.py) | Skeletons for all sheets | Kept |
| 2.5 | Per-sheet affine / low-order fits | Seams didn't meet between sheets | Rejected |
| 2.6 | Lens model (Brown radial + decentering, lens.py) | Degenerate with a free centre on sheets 06, 11, 19, 42 | Rejected |
| 2.7 | Neatline traces (neat.py) and Coons-patch correction | Neatlines bow inward up to 35 px; Coons alone leaves 17.9 px band residual | Kept (base) |
| 2.8 | Per-sheet polynomial ICP against LiDAR 25 ft lines (icp.py run/run2) | Unconstrained cubic diverged on sheet 36 | Rejected |
| 2.9 | Joint fit: continuous regional field on a 4,000 ft lattice + edge-constrained cubic shape per sheet (prep_joint, joint.py, joint_4000_100_1) | Band residual 17.9 to 9.7 (field) to 4.9 px (field + shape); seams about 1.4 m; ICP normal RMS 2.8 m; index contours about 2 m from LiDAR | Kept (georef_1912.json) |
| 2.10 | Warp to 0.5 m GeoTIFFs + VRT (warp_sheets, mkvrt.py) | First mask from a coarse lattice left seam slivers; fixed by interpolating grid coordinates. Committed to Georef_LiDAR | Kept |

## 3. Contour labelling (whole survey, 2026-10-07)

| # | What | Result | Status |
|---|---|---|---|
| 3.1 | LiDAR anchors + uphill-neighbour relations, robust least squares (label.py) | Circular (relations come from LiDAR) and the +1 relations drift | Rejected |
| 3.2 | Bold = nearest 25 ft to LiDAR, thin = nearest 5 ft (label2.py); C-field = LiDAR + interpolated residual (surf.py, C4m.npy) | Index labels reliable only where change is under 12.5 ft; thin labels unreliable (sheet accuracy ±3 ft is wider than half of 5 ft) | Superseded by 8.x |

## 4. Change zones

| # | What | Result | Status |
|---|---|---|---|
| 4.1 | Automatic zones: index contours off the 25 ft lattice + steep ground with no 1912 contours (zones_oh, zones_oh2.py) | Missed the flat Mill Creek interstates; kept only as a noisy "flagged for review" layer (3.3 km²) | Rejected as primary |
| 4.2 | OSM footprints of post-1912 works, widened over slopes over 15% up to 60 m (zones_osm.py) | Z_all (maps 1-2) 42 km²; Z_real (map 3) 2.2 km² with four held items. First KY test used a northing cut (wrong), fixed with the Ohio River line; unbounded hole filling swallowed land between highways, capped at 20,000 m² | Kept (Z_all) |
| 4.3 | Map 3 zones v2: real freeway kept if a canon alignment runs within 60 m along half its length, plus tracker list (zones_osm2.py) | Carriageway pairs split classes | Superseded |
| 4.4 | v2 with 100 m tolerance, Columbia Pkwy downtown end kept, real I-275 pieces under 1.5 km kept as interchange slivers | Z_real 3.5 km²; northern I-471 kept per 4D (reversed my earlier default) | Kept |

## 5. Canon interstates for map 3 (canon_hw.py)

| # | What | Result | Status |
|---|---|---|---|
| 5.1 | Overlap of Ben's 4 KMZ alignments with OSM (ni_overlap.py) | Which stretches ride existing freeways and which are new | Kept |
| 5.2 | Design profile v1: L1 fit to ground under 5% grade and 6 km vertical curves (LP); 40 m formation, 1:2 slopes, bridge over 12 m fill, tunnel over 30 m cut | River decks sagged to about 10 m over the water; edge-of-extent tunnels | Superseded |
| 5.3 | v2: fill cost relaxed once a station is a bridge; Ohio deck at least 167 m NAVD88 (Brent Spence companion clearance 81.2 ft over a 453.6 ft pool, plus 4 m); no carving within 1.5 km of the extent edge | I-75 Delhi-Villa Hills 1.36 km bridge; I-71 1.9 km low crossing | Superseded |
| 5.4 | v3: Price Hill trench forced at least 7 m under ground | Trench 7-20 m deep, median 10 m; 112 km carved, about 5.1 km² changed. Delivered to Canon_Interstates | Kept |
| 5.5 | I-71 KMZ route vs tracker 4B (Rookwood, Mt Lookout trench, bluff-to-bluff) | Conflict flagged; awaiting Ben | Open |

## 6. Street and building imprints in LiDAR

| # | What | Result | Status |
|---|---|---|---|
| 6.1 | Gaussian smoothing 6 m and 15 m (Westwood demo) | Blurs escarpments before the street grid goes | Rejected |
| 6.2 | 15 m smoothing with ridge/valley restore (Terrain Sculptor style) | No real gain over 6.1 | Rejected |
| 6.3 | Median filter 26 m and 42 m | Clears house pads and building scars, keeps slopes crisp; street grid and lot terraces survive in post-1912 suburbs | Kept as the base filter |
| 6.4 | OTR/Pendleton/Mt Auburn demo | Core imprints line up with the 1912 street pattern, so mostly 1912-era; I-71 is the big modern scar | Finding |
| 6.5 | LiDAR point classes to remove roads/buildings | Not possible: the DEM is already bare earth, and the 3DEP minimum scheme (1, 2, 7, 9, 17, 18, 20-22) has no road or building class; graded ground has no class at all | Rejected |

## 7. Mixing methods, analysis before building (2026-10-07)

| # | What | Result | Status |
|---|---|---|---|
| 7.1 | Option A (zones only) vs D (1912 contours only) | Ben noted the 1912 sheets draw contours through streets; A would leave texture seams at zone edges | Led to 7.2 |
| 7.2 | Six methods proposed (zone swap, erase-and-refill, band clip, frequency split, difference swap, 1912 only) | Scrutinised when Ben asked: imprints are 0.8 m typical, 2-2.5 m at the 90th percentile, while an honest 1912 band is about ±2 m on hillsides; only 10-16% of hillside pixels fall outside it | |
| 7.3 | Band clip as an imprint remover | Too loose to catch most imprints; leaves shelves at the band edge | Rejected (kept as QA) |
| 7.4 | Frequency split | A step split by frequency leaves a ridge-and-trough line; worse than the bench | Rejected |
| 7.5 | Final four trials: change-gated, erase-and-refill, 1912 base with LiDAR on natural ground, one weighted solve | Ben: run all four as trials | Done (section 9) |

## 8. Pilot 1912 surface (Westwood and OTR/Mt Auburn, 3.4 km windows, 2026-10-08)

| # | What | Result | Status |
|---|---|---|---|
| 8.1 | 5 ft labels by counting along gradient paths between index contours (pilot_label.py) | Both bracketing index contours found for 51% / 33% of samples; count alone fixed only 20% / 9%; S25 rounding right 54%, LiDAR rounding 51-52% | Rejected |
| 8.2 | Topological propagation: path crossings give +1 relations, index labels anchor, majority vote (pilot_label2.py) | 83% / 77% of contour length labelled; 88% / 83% of relations consistent | Kept |
| 8.3 | Surface fit with labels as fixed heights, per-pixel IRLS, λ=2 (pilot_surface.py) | Lumpy, dark ticks; surface bent to fit mislabels | Rejected |
| 8.4 | Same, λ=20 with capped cell averages | Too stiff; several contours share one 4 m cell; 23% of segments dropped | Rejected |
| 8.5 | Same, bilinear observations, λ=5 | Still lumpy (third failed attempt, so method changed) | Rejected |
| 8.6 | Free-level fit: index contours fixed, each 5 ft contour a level line with a floating level, propagated label as a soft prior, robust weights (pilot_surface2.py) | Clean in Westwood; geometry overruled 25% (Westwood) / 38% (OTR) of propagated labels. OTR hillsides soft, flat basin unreliable. Two bugs on the way: reused AMG hierarchy solved a stale matrix (diverged); 0/0 level update | Kept |
| 8.7 | Survey coverage = within 60 m of a contour | Holes in the flat basin made arc artifacts; fixed by filling enclosed holes | Kept (fixed) |

## 9. Trials (same two windows)

| Trial | Outside 1912 band (W / OTR) | Imprint left | Natural detail kept | Status |
|---|---|---|---|---|
| LiDAR as is | 29% / 38% | 1.0 | 1.0 | |
| 1. Change-gated (median LiDAR, zones = OSM + band-found changes, refilled from 1912 surface) | 18% / 22% | 0.9 | 0.85-0.89 | Superseded by combo |
| 2. Erase and refill (streets grown over shoulders, pads +4 m, zones; 1912 surface + membrane offset) | 10% / 9% | 0.6 | 0.83-0.88 | Superseded |
| 3. 1912 base, LiDAR on natural ground (30 m taper) | 2% / 0% | 0.45 | 0.87-0.92 | Superseded by 4 |
| 4. One weighted solve | 1% / 1% | 0.45 | 0.83-0.89 | Kept (outside the core) |

Notes: trial 1's band-found zones caught real fills (the creek valley off Queen City Ave) but threw false patches across the OTR basin. Trial 2 left lot terraces and a seam at the edge of 1912 coverage. Trial 4 is within 0.4 m of trial 3 and only softens joins.

## 10. Combination and fixes

| # | What | Result | Status |
|---|---|---|---|
| 10.1 | Combo: inside a 1912 built-up core, median LiDAR with only OSM works rebuilt; trial 4 outside; one solve, core feathered 100 m (pilot_combo.py) | | Kept |
| 10.2 | Core = black ink density > 0.03, 80 m smoothing (pilot_core.py) | Lettering and railroad hatching made false cores in Westwood; OTR 91% | Superseded |
| 10.3 | Core threshold 0.04 at wider smoothing | OTR 63%, patchwork of sharp and soft hills | Rejected |
| 10.4 | Core threshold 0.03 at about 100 m, close 150 m, open 60 m, drop under 0.2 km² | OTR 83%, Westwood none; escarpments crisp, I-71 rebuilt to the Gilbert ravine; a natural-mask bug (binary_dilation with iterations=0 fills everything) found and fixed | Kept |
| 10.5 | Big-pad fix: footprints over 1,000 m² grown 30 m over cut/fill; LiDAR flat-pad finder with 1912 water/park check (pilot_pads.py) | 451 footprints, 15% of OTR erased. Flat-pad finder found 0, then 0 after splitting flats at steps, then 2 after loosening the edge test | Kept |
| 10.6 | The basin "rectangle" | Was TQL Stadium's works zone refilled from the weak basin 1912 surface (I first called it an old building; wrong). Core works zones with sparse contours now refill from their edges | Kept |
| 10.7 | Refill method: membrane | Dents and blotches in big holes | Rejected |
| 10.8 | Refill method: thin plate | Smooth, but overshoots into domes across very large holes (stadium) | Kept, needs blending |
| 10.9 | Basin test A: erase every footprint and street on flat core ground | Domes; broad shape shifted 0.9 m | Rejected |
| 10.10 | Basin test B: morphological filter (close then open, 30 m) + light smoothing | Foundations and grid gone; broad shape shift 0.33 m; occasional ring around a large pit | Candidate |
| 10.11 | Basin test C: 24 m Gaussian on flat core ground | Smoothest, but wipes the 5 ft knolls the 1912 sheet shows | Rejected |
| 10.12 | 1912 information in the basin | 30 km of contours in the flat core, median 21 m to the nearest (my earlier "sparse" was wrong); only 40% of index contours there within 2.5 ft of LiDAR, so labels or real regrading can't yet be told apart | Finding |
| 10.13 | Reading printed contour elevations with tesseract on the 0.5 m warped mosaic (ocr_test.py) | 279 reads, 0 valid: digits about 6 px tall, italic, touching contour lines. I read the seven labels on the Dorsey St slope by eye without trouble | Rejected (this route) |

## 10b. Iterations toward "1912 texture, LiDAR fidelity, no building outlines" (2026-10-08, pilot_iter.py)

Target set by Ben: looks like the 1912 surface's smoother texture, keeps the LiDAR's accuracy, no building outlines, within the 1912 survey.

| # | What | Westwood / OTR scores (imprint left; outside 1912 band; fine relief vs 1912 surface 0.34 / 0.32) | Result | Status |
|---|---|---|---|---|
| 10b.1 (I1) | LiDAR-based everywhere: median, erase every building (+4 m), street (grown over shoulders), big footprint and flat pad, refill with the average of membrane and thin plate (cures both dents and domes); developed ground closed then opened with a 32 m disk and smoothed 8 m; natural ground smoothed 4 m; OSM works and band-found changes from the 1912 surface where contours are dense, refilled from edges where sparse | 0.74 / 0.63; 17% / 26%; 0.28 / 0.29 | Basin foundations gone, but the 1912-surface zones showed hard seams and sawtooth outlines | Superseded |
| 10b.2 (I2) | I1 with the zones feathered 10 m and merged before the filter, so the filter runs across the seam; band-found zones limited to over 2 m excess and 1 ha | 0.80 / 0.67; 24% / 34%; 0.25 / 0.24 | Seams gone; Westwood street lines and lot steps still faintly visible; LiDAR-flat fields and parking remain | Superseded |
| 10b.3 (I3) | Developed ground = LiDAR shape above 20 m (from the filtered, erased LiDAR) + 1912 surface texture below 20 m; outside 1912 cover, filtered LiDAR; zones as I1 but feathered | 0.54 / 0.51; 8% / 19%; 0.31 / 0.30 | Texture now matches the 1912 surface; street lines mostly gone; escarpments keep LiDAR position | Superseded |
| 10b.4 (I4) | I3 with the hand-over at 30 m | 0.48 / 0.46; 4% / 16%; 0.33 / 0.32 | Closest to the 1912 look; outlines gone in both windows; fidelity at over 40 m within about 0.8 m (Westwood) and 1.2 m (OTR) at the 95th percentile | Kept |

Remaining after I4: a large graded field in Westwood (bigger than the hand-over scale) still reads faintly; small lumps in the 1912 basin surface (unresolved basin labels, 10.12) come through as faint texture; ground outside the 1912 survey has no 1912 texture to borrow (needs the 1914 sheet).

## 10c. Full survey run of I4 (2026-10-08, finished 13:41 UTC)

67 tiles cover the 48-sheet survey (3 km cores, 3.4 km windows, 400 m blended overlaps; tiles.json). Per tile: labels (pilot_label2), free-level surface warm-started from the index-only surface with 7 rounds (pilot_surface2), street/building masks (tile_masks), pads (pilot_pads), I4 (pilot_iter). Tiles with no usable contours fall back to cleaned LiDAR (tile_fallback). Mosaic, cover mask, GeoTIFF and preview via tile_mosaic.py; overlap agreement via seam_check.py.

| # | What | Result | Status |
|---|---|---|---|
| 10c.1 | First run (05:20) | Stopped after 3 tiles: the workspace was reclaimed while idle and the nohup job died with it | Fixed by staying in session |
| 10c.2 | Scoring on fallback tiles | Crashed (empty cover); pilot_iter now skips scores when cover is under 1,000 px | Fixed |
| 10c.3 | Full run, restarted 08:09 | All 67 tiles; 12 fallback (t03 t06 t09 t12 t19 t20 t26 t27 t33 t41 t42 t56); about 5-7 min per tile, 2 CPUs, 3.5 GB peak per tile (too much to run two at once in 7 GB) | Kept |
| 10c.4 | Per-tile scores (55 scored tiles) | Imprint left median 0.41 (range 0.05-0.64); outside 1912 band median 12%. Outliers t40, t48 (73%) are edge slivers with 1% cover; t28 (riverfront, 28% cover) has the weakest labelling (67% of relations consistent) | Finding |
| 10c.5 | Overlap agreement (85 adjacent pairs) | Median mean difference 0.46 m, median p95 2.15 m. Worst: t14-t21 (p95 16.8 m) and t01-t05 (9.6 m), both confined to riverside works zones where each tile labels the 1912 contours differently; the tent blend averages them | Open (minor) |
| 10c.6 | Tent blend with weights floored at 0.01 | Faint straight lines at tile window edges (filter edge effects leaking through the small weight) | Rejected |
| 10c.7 | Blend dropping 40 m of each window edge, ramp over 360 m | Edge lines gone in the zoom check | Kept |
| 10c.8 | Mosaic cover mask as a plain OR of tile covers | Holes in the flat basin and Mill Creek where contours are over 60 m apart; specks around stray marks | Rejected |
| 10c.9 | Cover closed 20 m, holes filled, pieces under 0.1 km² dropped | 270 km² | Kept |
| 10c.10 | Visual review (8 m preview, 2 m zooms of the t14/t21 seam and downtown) | No visible tile seams; downtown buildings and street grid gone; riverfront works band (Fort Washington Way area) reads as soft lumps; a few thin crisp lines where single 1912 contours carry through the texture | Kept, notes for later |
| 10c.11 | Delivery | Historic_Topo\1912_Ground_I4: I4_1912_ground_dm.tif (int16 dm, deflate + predictor, 30 MB), I4_1912_cover.tif, I4_preview.jpg, README.txt | Done |

## 10d. Canon riverworks (2026-10-08, rw_setup.py, rw_build.py)

Context reread before building: the 1900 Cincinnati Plan (May 11 conversation) and the May 17 embankment design (bank pushed to the 1792 low-water line, continuous quai wall, Mill Creek Barrier Dam, Kentucky's defensive terraces). Ben's decisions this session: 70 ft wall never raised, except higher at Lunken (airport built later on Metro spoil, levees as at the real airport); Embankment 1903-1925 so map 2 gets the Mill Creek mouth to Sawyer Point stretch and the lower Mill Creek culvert; deck sloped from the Embankment up to Camp Washington with the yards cut deeper by Chinatown and higher by Crosley; deck sides slope down like the CUT plaza to the West End, not level; Lunken levees at 83 ft.

| # | What | Result | Status |
|---|---|---|---|
| 10d.1 | Height of a deck at wall height over freight yards at grade | 70 ft is 151.8 m against a 150-152 m valley floor: no room for trains. Ben: slope the deck and cut the yards | Resolved by 10d.4 |
| 10d.2 | Ohio outline vs today's river (8 m, one water level) | The LiDAR river surface steps by about 3 m between collection dates, so one level made false land-in-river patches | Rejected |
| 10d.3 | Same with a local water level per 400 m block | Reclaimed strip 1.1 km2, typically 20-50 m wide downtown and 50-140 m around the Lunken bend; Kentucky bank on today's line | Kept |
| 10d.4 | Deck: flat over the OSM rail corridor in the valley plus the creek, 151.8 m at the Embankment rising evenly to 160 m at Camp Washington north (4.84 km), then 3.5% down to existing ground on both sides, fill only | Corridor 2.32 km2, side slopes 1.80 km2. Yards 8.5 m below the deck: cut about 7.6 m by Chinatown, 4-5 m from CUT to Queen City Ave, 3 m at Hopple, none north of it | Kept |
| 10d.5 | Side slope | 3.5%, measured from LiDAR: the CUT plaza (about 159.8 m) falls about 7 m over about 200 m east to the West End | Kept |
| 10d.6 | Embankment section along Ben's outline, Sedamsville to Belterra, gap at the Little Miami | Quai bas 142.0 m, 12 m wide at the water; wall and quai haut at 151.8 m to 52 m from the bank or the whole reclaimed strip; 3.5% down to existing ground behind; 3.44 km2 changed | Kept |
| 10d.7 | Lunken: real levee ring from LiDAR (ridge over a 50 m opening by more than 2.5 m) raised to 155.8 m with 1:3 sides; new levee 55 m off the Little Miami's east bank up to high ground | 2.73 km2 including the airfield lift | Kept |
| 10d.8 | Airfield lift by filling the ring's interior | The ring isn't closed on the west, so nothing filled | Rejected |
| 10d.9 | Airfield lift as the low flat component around the runways | +1 m over 1.9 km2 (Metro spoil only stretches to 1-2 m) | Kept |
| 10d.10 | Map 2: same Embankment section from the Mill Creek mouth to Sawyer Point (5.28 km); culvert fills the OSM Mill Creek channel to the surrounding floor from the mouth to about Harrison Ave | 0.86 km2 and 0.06 km2 | Kept |
| 10d.11 | Memory: one 8000 x 6105 window with index-returning distance transforms | Too heavy for 7 GB; each work now runs on its own crop | Changed method |
| 10d.12 | Delivery | Historic_Topo\Canon_Riverworks: target, mode and delta GeoTIFFs for maps 2 and 3, previews, the wall line, parameters, README | Done |

Notes: map 3 here sits on raw LiDAR, so real works canon removes (I-75 ramps, stadiums) still poke through until the map 3 base is rebuilt; target plus mode re-apply to any base. Kentucky terraces (Covington 1912-28, Newport 1915-30, Bellevue/Dayton 1920s, Ludlow-Bromley riprap) are not built yet.

## 10e. Kentucky 1912 ground for maps 1-2 (2026-10-08, ky1912.py)

Kentucky is outside the 1912 survey, so its base is the I4 surface (cleaned LiDAR) with every post-1912 work in Z_all rebuilt from the 1914 USGS 1:62,500 sheets (West and East Cincinnati, 20 ft contours).

| # | What | Result | Status |
|---|---|---|---|
| 10e.1 | Extend I4 to the window's south edge: tiles k00-k05 | No 1912 cover, fallback to cleaned LiDAR; mosaic now 16701 x 13701, window gap 0.2% | Kept |
| 10e.2 | 1914 contours: brown pixels in LAB, skeleton, one id per segment, labelled by the mode of nearest-20 ft LiDAR on ground at least 20 m outside the zones (8 px, 50% agreement) | 22,203 segments, 9,529 labelled; 6,465 constraint px inside the zones | Kept |
| 10e.3 | Thin-plate rebuild per zone bounding box at 2 m | Box up to 3778 x 2102 px: far too large | Rejected |
| 10e.4 | Thin-plate over zone pixels only at 4 m, surrounding ground fixed, contour pull weight 0.3, feathered back to 2 m | 23 zones, 5.50 km2; change p5/p50/p95 -4.1/+0.1/+11.8 m. I-471 and I-71/75 cuts refilled, I-275 interchange and Combs-Hehman approach (-18.7 m) removed, Covington, Newport and Dayton levees taken down (about -5 m) | Kept |
| 10e.5 | Map 2 render: Kentucky ground replaces the I4 base wherever no 1912 riverworks sit | Clean; the refilled I-275/I-471 interchange reads as a smooth dome | Kept |
| 10e.6 | Delivery | Historic_Topo\KY_1912_Ground (ground, delta, checks, README); map2_relief.jpg updated; 1912_Ground_I4 gets a south extension file (the full mosaic is 32 MB) | Done |

Notes: the bank still sits on today's pool until the 1912 river level is set. Covington's terraces start in 1912 but belong to map 3 only.

## 10f. Kentucky terraces and levees for map 3 (2026-10-08, ky_terr.py)

Ben's calls: top at 70 ft (151.8 m); outer edge on the river outline, since Cincinnati had already narrowed the river; Licking both banks down to Threemile Creek / Fredericks Landing; tiers left to me.

| # | What | Result | Status |
|---|---|---|---|
| 10f.1 | Where works are needed: Kentucky land below 151.8 m (1912 ground) connected to the river | 6.60 km2; Covington and Newport downtowns sit mostly above it; low ground is the riverfront strips, Covington's Licking side, Dayton's flat and the Licking floodplain | Kept |
| 10f.2 | Sections: Covington 3 tiers (142.0 / 147.0 / 151.8 m, 15 m each, 3.5% back like Cincinnati); Newport 2 tiers (142.0 m wharf 20 m, 151.8 m 15 m, 1:3 back); Bellevue-Dayton 2 tiers (10 m each, 1:3 back); Bromley-Ludlow riprap 1:2, 8 m crest, 1:3 back; Licking wall plus 8 m crest, 1:3 back | Works only where flood-prone land lies within 60 m of the bank, gaps under about 200 m bridged | Kept |
| 10f.3 | First crop started too far south and cut off Bellevue-Dayton; Covington/Newport split used the Threemile column instead of the Licking mouth | Fixed | Fixed |
| 10f.4 | 3.5% back slope everywhere | Long fills over Dayton's flat; changed to 1:3 for Newport and Bellevue-Dayton (functional works), kept 3.5% for Covington | Changed |
| 10f.5 | Tiebacks to ground at 151.8 m: Threemile Creek line (both banks), Bromley west end, Dayton east end at the Fort Thomas bluff | 0.015 km2 | Kept |
| 10f.6 | Real Covington and Newport floodwalls still showing behind the new sections | Real works (Z_all) within 400 m of the bank taken back to the 1912 ground, canon interstates excepted; a binary opening had dropped the thin walls, and pixels inside the new back slopes were being dropped, both fixed | Kept |
| 10f.8 | Dayton marina basin (LiDAR water at 140.8 m behind the new wall) | Filled on a small crop by pull-push from a ring 10-30 m outside it: 0.076 km2 to about 144.2 m, the level of Dayton's flat | Kept |
| 10f.7 | Result | 1.509 km2 changed; map3_relief.jpg re-rendered; Historic_Topo\Canon_Riverworks: map3_ky_terraces target, mode, delta, params, check image, README | Done |

Notes: the raised modern pad on Dayton's riverfront (about 153 m, not in Z_all) is still in the map 3 base; it needs the 1950s sheets. Map 2 gets no Kentucky terraces (Covington starts in 1912).

## 10g. Map 3 base: real-only works rebuilt from the 1950s sheets (2026-10-08, m3_contours.py, m3_rebuild.py)

| # | What | Result | Status |
|---|---|---|---|
| 10g.1 | Contours from the 1:24,000 sheets with the 1914 colour rule | Picked up street edges in the pink urban tint and missed the contours | Rejected |
| 10g.2 | Colours measured on the sheets: contours on white L 85-160, a 2-14, b 26-45; over the tint a 25-45, b 28-50; red roads a about 46-76 masked with a 5 px buffer | Contours caught on white and over tint; few street edges | Kept |
| 10g.3 | Covington 1950 and Newport 1952 | Ohio half left blank; the 1955 editions cover both states, so those are used (both still predate every real-only work) | Changed |
| 10g.4 | Thin-plate per zone at 4 m, surrounding LiDAR fixed, contours labelled by the nearest 10 ft of LiDAR outside the zones, weight 0.3 | Bumps where single wrong labels pull the surface | Changed |
| 10g.5 | Contour kept only with 6+ px in the zone and residual spread under 2 m against the edge-only fill; none within 8 m of the zone edge; weight 0.1; 6 m smoothing inside the zone | Clean; corridors follow the ridge and valley pattern they crossed | Kept |
| 10g.6 | Applying a 4 m delta to the 2 m LiDAR | Lane and pad detail survived inside the zones; the 2 m output now replaces the LiDAR inside each zone, feathered | Fixed |
| 10g.7 | Dayton's raised riverfront (about 153 m, not in Z_all; the 1955 sheet shows a slope from 450 ft at the bank to about 490 ft at the road) | Added as an extra zone, 0.36 km2: Dayton's riverfront within 220 m of the bank | Kept |
| 10g.8 | Auto-detecting other Kentucky riverfront fills (LiDAR over 1955 contours by 3 m) | Found only scattered Licking-side hits, some on kept roads; not used | Rejected |
| 10g.9 | Result | 18 zones, 3.60 km2 changed; map 3 now uses it in place of the provisional pull-push; Kentucky terraces re-run on the new base; Historic_Topo\Map3_Base delivered | Done |

Notes: the downtown basin zones (Fort Washington Way, stadiums, 6th St) have no contours inside and are filled from their edges; most of them sit under the Embankment anyway. The strip north of 39.25 N (top of comp 1, Colerain I-275) has no 1:24,000 sheet in the set. Rebuilt corridors read smooth against the textured city around them.

## 10h. Map 3: building and street imprint removed (2026-10-08, m3_smooth.py)

Ben: erode and rebuild the rectangles in the basin so it looks more natural.

| # | What | Result | Status |
|---|---|---|---|
| 10h.1 | Area opening + closing at 1.6 and 4.8 ha | Flat-basin blocks clear (they are local highs or lows of any shape); hillside terraces stay, because a step on a slope is not a local high | Partial |
| 10h.2 | 26 m median; opening/closing by reconstruction (16 m disk) | Median clears pads and keeps big forms; reconstruction leaves most rectangles | Median kept as a stage |
| 10h.3 | Area filter + median on gentle ground, LiDAR or 18 m median on slopes over 22% | Basin smooth, faint block ghosts left on the sloping basin (a staircase of blocks) | Changed |
| 10h.4 | Detrended: 80 m trend + residual, area filter on the residual, everywhere | Block staircases and hillside terraces flatten onto the trend; bluffs, ravines and big landforms keep their shape | Kept |
| 10h.5 | The street network is one connected low, so the area filter keeps it; 24 m closing on gentle ground first, and 8 m extra smoothing on flat ground for sub-metre steps | Basin reads as terrain | Kept |
| 10h.6 | Whole riverworks window, 1,600 px tiles with 300 px overlap | Change p1/p50/p99 -8.3/0.0/+5.4 m; about 13 minutes, run in the background | Done |
| 10h.8 | Window edge (Ben asked whether it meets the real LiDAR) | First run stepped at the border: median 1.4 m, p90 7.6 m, max 38 m (edge effects of the trend and area filter). Recomputed with a 1.2 km margin of real LiDAR and feathered into it over the outer 300 m: border difference at most 0.002 m | Fixed |
| 10h.9 | Profile DEM for the travel-time repo (profile.dem, dem_scale 0.1) | map3_profile_dem_dm.tif: smoothed base + canon interstates + riverworks + Kentucky works, window only, int16 dm, 9.7 MB; 99% of border cells within 0.1 m of LiDAR + real-only rebuild + interstates, exception the raised Lunken levees at the east edge (up to 12.4 m) | Done |
| 10h.10 | Profile analyzer handoff for the travel-time session | _Cincinnati Rail\Profile_Analyzer_Handoff: the Metro Profiles page code, settings (defaults), 15 line files with ground_dm resampled from the map 3 DEM inside its window (original LiDAR kept as ground_dm_lidar; outside unchanged, original sampling matches LiDAR to 0.02 m), Ben's saved profiles for Lines 1, 2, 4, 5, network.json, the DEM, README with a short prompt. One edge step on the lines: Line 12 at 14,728 m, 5.9 m, canon I-71 crossing the north edge | Done |
| 10h.11 | Map 3 ground over the whole LiDAR extent (holds every Metro line; Ben asked to extend past the I-71 edge step) | m3_smooth_full.py: same method at 4 m (its smallest relief is 15-20 m), resampled to 2 m, two workers, about 10 minutes; matches the 2 m window version within 0.14 m (p95). m3_profile_full.py: + canon interstates + riverworks and Kentucky works pasted from the window; 4 tiles of 14-17 MB + hand-written VRT (no gdalbuildvrt here). Lines re-sampled along their whole length; Line 12 step gone; remaining sharp steps are canon walls, levees and I-75 cuts | Done |
| 10h.7 | Delivery | Historic_Topo\Map3_Base\map3_base_ground_dm.tif (window, 9 MB); map3_relief.jpg and Kentucky terraces re-run on it | Done |

Notes: the base keeps 2 m cells but its smallest relief is about 15-20 m across (detail under 20 m drops from 0.55 to 0.28 m std on a test block). Hilltop street benches (Mt Auburn, Walnut Hills) soften but still read; real large features (Eden Park reservoirs, the CUT plaza) stay. Map 2 already had its imprint removed by I4.

## 10i. Ohio and Licking bed (2026-10-09, bathy/b1-b7)

Sources: USACE Louisville District eHydro surveys, Markland pool: OH_LD_MKL_20220201_OT_PRS_436_484 and _484_532 (single-beam, cross-sections every 200 ft, 3-5 ft along each), and the Licking backwater LR_LD_MKL_20241212_OT_PRS_0_7. Depths in feet below the project pool, 455.0 ft; Kentucky North state plane, US feet. Bed = (455.0 - depth) x 0.3048 m. The NGVD 29 to NAVD 88 offset is not applied (a few tenths of a foot, unverified).

| # | What | Result | Status |
|---|---|---|---|
| 10i.1 | Real bed: 192,555 soundings inside the frame, linear triangulation at 4 m inside the canon Ohio and Licking outlines, pool-level points on the outline where no sounding is within 40 m, 12 m masked smoothing | Domain 26.7 km2, all of it within 100 m of a sounding. Bed 119.6-139.9 m, median 132.5 m (about 6 m below pool) | Kept |
| 10i.2 | Pier scour at real bridges | Residuals at the bridges are -1.2 to -1.7 m (Roebling -3.8 m) against a bed residual sd of 1.5 m; the 61 m line spacing does not resolve pier holes, so nothing to remove at Brent Spence or the Daniel Carter Beard | No change |
| 10i.3 | Canon deepening: flood-stage (146.3 m) water extent on real LiDAR and on the map 3 terrain, within 300 m of the canon outline, tributary valleys excluded; width per 1 km window along the centreline; live-bed contraction scour (Laursen, HEC-18), depth below flood stage x (W real / W canon)^0.64 | Sedamsville to Pennsylvania x1.1-1.2; East End loop and Lunken bend up to x1.3-1.4; west of Sedamsville and upstream of the Lunken bend about x1.0. Deepening median 0.05 m, p90 2.4 m, max 7.1 m | Kept, pending Ben on method |
| 10i.4 | Bed at the RER river crossings (canon) | RER-2 Roebling-Rivercenter 125.6 m (13.0 m below pool); RER-4 Pennsylvania-Mansion Hill 127.7 m (11.0 m); RER-5 Mill Creek-Ludlow 123.4 m (15.3 m) | Recorded |
| 10i.5 | Delivery | Historic_Topo\Ohio_Bed: ohio_bed_real_2022_dm.tif and ohio_bed_canon_map3_dm.tif (4 m, int16 dm, nodata -32768), bed_canon_preview.jpg | Done |
| 10i.6 | Tube rule (Ben: option A) | Metro tubes 1905-41 by shield, cover one 4.4 m tube diameter; RER tubes 1985-2005 as sunk sections, 1.5 m backfill; 1.0 m flood-scour margin on both. With the 5.5 m envelope: Metro rail <= bed - 10.9 m, RER rail <= bed - 8.0 m | Ruled 2026-10-09 |
| 10i.7 | Merged into the profile terrain (water pixels at or below 146.0 m inside the outlines; 99% of the river now bed) and the river samples of Lines 1, 2, 3, 6, 8, 10, 11 re-read; README gains the tube rule and an update prompt; copied to both Profile_Analyzer_Handoff folders | Every Metro river crossing breaks the rule by 17-40 m (rail between 133 and 149 m against needed 106-120 m) | Done; profiles need re-solving |
| 10i.8 | Crossing sites (Ben: founding-era Metro crossings were sited at the shallowest points): at each Metro Ohio crossing (Lines 1, 2, 3, 6, 8, 10) the bed is raised to the shallowest section within 500 m, full over 100 m and blended out to 250 m along the river | Gains: Line 2 +5.0 m, Line 8 +5.8 m, Lines 1, 6, 10 +0.6 to +0.9 m, Line 3 +0.3 m. Drops still needed: 16-35 m (Line 1 16.4, 2 26.1, 3 27.4, 6 24.3 and 25.4 at the Licking, 8 34.6, 10 28.0, 11 23.1) | Kept; terrain, lines and both handoff folders updated |
| 10i.9 | Pool level | Normal pool 455.0 ft is the Markland dam's held minimum for navigation, not a typical level; floodwalls don't set it, and a higher pool would not change tube depth (the rule runs off the bed) | Answered |
| 10i.10 | Metro cover cut to half a tube diameter (Ben: option B). Lines 1, 2, 3 and 6 were aimed at Kentucky from the founding era, so their riverfront levels were fixed before the 1935-41 crossings were driven with the shield technology of the day; the engineers had backed themselves into thin cover | Metro rail <= bed - 8.7 m (1.0 + 2.2 + 5.5). Drops still needed: Line 1 14.2, 2 23.9, 3 25.2, 6 22.1 (Licking 23.2), 8 32.4, 10 25.8, 11 (Licking) 20.9 m | Ruled 2026-10-09; README updated in both handoff folders |
| 10i.11 | Bed on map 3: render shows the bed under the canon water (depth-tinted blues, bed hillshade); pool-level bank points dropped within 30 m of the Embankment wall (they made false shoals in front of the wall); pipeline rerun (bathy/run_all.sh) | Crossings now: Metro beds Line 1 127.7, 2 127.1, 3 125.0, 6 127.4 (Licking 130.8), 8 123.0, 10 128.8, 11 131.1; drops needed 14.5-32.4 m; RER beds RER-2 126.6, RER-4 127.5, RER-5 123.4 (rail <= 118.6 / 119.5 / 115.4) | Done; Map3_Base gets map3_relief.jpg and map3_window_ground_with_bed_dm.tif, Ohio_Bed refreshed, both handoff folders updated |
| 10i.12 | River level for the maps (Ben): 30 ft on the Cincinnati gauge = 458.05 ft NAVD88 = 139.62 m, about 0.9 m over normal pool. Check against the USGS ADCP measurements at the Roebling Bridge (Dec 2025, Mar and Aug 2026; area / width = mean depth 27.7-32.8 ft): the surveyed bed at that section gives 31.8 ft mean depth at the 30 ft level (width 1,076 ft, canon outline) | Map 3 re-rendered with depths tinted from 139.62 m; handoff README notes the level | Done |
| 10i.13 | Datum check from a year of 15-minute Cincinnati gauge readings (Oct 2025-Oct 2026): low 25.95 ft, median 27.93, mean 29.41, 76% of the time under 30 ft, high 45.08 (Mar 2026). The low (454.0 ft NAVD88) sits under the Corps' 455.0 ft pool, so that pool is on an older datum and the bed is at least 1 ft (0.3 m) high | Ben: leave it, 1 ft doesn't matter | Not applied |

## 10j. Metro structure sections (2026-10-09, staged for the tracker, not logged there)

| # | What | Result | Status |
|---|---|---|---|
| 10j.1 | Car and tube | IRT-gauge car about 2.62-2.70 m wide, 3.61 m tall; IRT Joralemon Street tube (1908) 4.7 m inside, 5.1 m outside. Canon's 4.4 m tube clears the car by only 0.05-0.3 m | Ben: 4.4 m is canon. Works with rail 0.5 m above the invert (0.29 m over the car); 4.76 m outside |
| 10j.2 | Heights (estimates beyond the car and tube) | Box: about 1.0 m below rail, 4.6 m rail to top, 5.6 m total. Twin tube: 0.93 m below rail, 4.15 m rail to top, 5.08 m total | Recorded |
| 10j.3 | Minimum tube cover | About 2 m above the water table (about 140 m in the basin gravels), about one diameter below it in soft wet ground, half a diameter plus 1 m under the river | Recorded |
| 10j.4 | Basin shield form by era (Ben) | Founding era (Lines 1-7, 1903-18): twin single-track tubes, about 8 m track centres, island-platform station boxes. Later eras: one double-track bore once large shields were proven (Holland Tunnel 1920-27, 9.0 m outside diameter): about 3.9 m track centres, side platforms; rail about 5.8-6.7 m to top of a 9 m bore | Ruled 2026-10-09 |
| 10j.5 | Analyzer rules (Ben: both leans) | Per-type heights: box 1.0 / 4.6 m, twin tube 0.68 / 4.08 m (deep everywhere, shield on Lines 1-7, all river crossings), double-track bore 3.2 / 5.8 m (shield on Lines 8-14); crossings by the summed rule; cover 2.0 m above 140 m, one diameter below; Metro river rule bed - 7.5 m, RER bed - 8.0 m | Handoff README rewritten in both folders; implementation spec given to Ben |
| 10j.6 | Platform curvature (Ben) | Outside face governs (every curved two-track station has one inside and one outside face). Error R < 600 m (named exception with gap fillers only); warning 600-3,000 m; car 15.56 m, end doors about 5.4 m from centre | Added to both handoff READMEs; spec given to Ben |
| 10j.7 | Code session questions (Ben) | Portals: trough under 4.6 m rail depth, roof-as-street box 4.6-5.2 m (warning), box with 0.6 m cover from 5.2 m. Clear height under a structure in the open: Metro 4.2 m (track lift and bounce), RER 5.8 m. RER river crossings as sunk RER boxes, rail <= bed - 9.1 m (corrects the 5.5 m Metro placeholder). Little Miami pool - 3 m. Both solvers hold the river limits; saved profiles flagged only | README updated in both folders; answers given to Ben |

## 10k. Deck street map (2026-10-10)

| # | What | Result | Status |
|---|---|---|---|
| 10k.1 | Sanborn 1922 vol. 1 sheets 3, 6, 9, 16, 29, 31, 33 | Mill Creek valley: W Liberty, Gest and W 8th cross the creek; Garrard Ave runs straight north-south on the east bank (W 8th to Marshall Ave), West End streets end on it; W 6th runs west to the creek mouth; Queen City Ave crosses at the north end (sheet 16) | Read |
| 10k.2 | Boulevard (Ben) | Brand new, on the creek line west of Garrard over the culverted creek; straight north-south (today's straightened channel stays within about E 712,250-712,440), from the Palace roundabout at the Queen City / Harrison junction south past CUT to W 6th | Ruled |
| 10k.3 | CUT west side (Ben) | Minor rear headhouse; a mirror of the eastern front with a park, shorter to the boulevard and less ornate, on CUT's east-west axis. No grand staircase (the May 24 line is wrong) | Ruled |
| 10k.4 | Grid joins | Liberty, Gest and 8th continuous; other streets T into the boulevard | Ruled |
| 10k.5 | Under the deck | Rail yards and the culverted creek only; the boulevard is the MCE's decked stretch | Ruled |
| 10k.6 | Blocks over the freight yards (Ben) | A mixture of buildings and parks or squares with vents | Ruled |
| 10k.7 | Sources (Ben) | 1904 and 1922 Sanborn only (pre-1950s). Ben downloaded 1904 vol. 1 (Cincinnati library scans), vols 3 and 5 (LOC) and named 49 sheets for the valley | Done |
| 10k.8 | Tool (Ben) | Python generation plus an interactive page like the profile analyzer | Done |
| 10k.9 | 1904 georeference (joint.py, warp.py) | 40 of the 49 sheets: intersections matched to the georeferenced 1912 survey or surviving OSM corners, line points, sheet-to-sheet ties; one joint least-squares fit. Vol. 3/5 similarity at the bar scale 19.73 px/m; vol. 1 scans were resized to a fixed page (4125 x 4763), so separate x/y scales held near square and near 11.19 px/m. Residuals mostly 0.2-5 m; 69/77 up to 7 m; 202/212 up to 10 m on 1912 street lines; 504/505/520 10-22 m (few surviving corners at the South Fairmount junction). Not fitted: 458-461, 465, 474 (Price Hill side, creek mouth) and 513, 519, 522 (North Fairmount) | Kept |
| 10k.10 | Georef tries | Chamfer match of Sanborn ink to 1912 ink (wandered on sparse sheets); free scale on vol. 3/5 with only line points (scale ran off to 5.9-52 px/m); per-sheet rotation free on two ties (sheet 67 swung 6 deg) | Rejected |
| 10k.11 | Boulevard (deck_gen.py) | Axis fitted to the 1904 creek: E = 712,348 + 0.066 (N - 4,332,000), bearing 3.8 deg, parallel to Garrard (3.6 deg) about 175 m west. W 6th (712,275, 4,330,887) to the roundabout centre on Queen City Ave (712,457, 4,333,647): 2,765 m. Width 70 m (draft parameter; canon width open) | Draft |
| 10k.12 | Palace roundabout | Radius 80 m (draft). Queen City Ave passes through east-west; Harrison Ave (1904 crossing about 385 m south, N 4,333,25x-4,333,35x) re-aligned as two avenues to the circle; Palace 180 x 80 m north of the circle with a forecourt, grounds to Alfred St | Draft, Ben to rule placement |
| 10k.13 | CUT west side | CUT axis 93.5 deg (Ezzard Charles Dr). Terminal square 140 m on the boulevard at (712,342, 4,331,902); west headhouse 110 x 35 m west of a 152 m platform zone (APEx 1-16); park 100 m wide, 236 m long (east axis to Linn St about 790 m). Precinct Hopkins St to Kenner St per tracker; Sedgewick lies on the axis and gives way to the park | Draft |
| 10k.14 | Streets | Through: W 6th, W 8th (110 ft viaduct line), Gest, W Liberty. T streets from the West End at Garrard: W 7th, Budd, W 9th, Richmond, Court, Clark, Oehler, Hopkins, Kenner, Courtland, Wilstach, Wade, Flint, Findlay, Poplar, Sherman, York, Exeter, Dayton, Bank; from Lower Price Hill at Evans: Perin, South, Hopkins (LPH); north of Queen City: Alfred, Straight, Marshall. New streets A-E every 90 m between Bank and the roundabout (no 1904 street there). Deck streets on the Garrard and Horne lines. Saratoga and Oscar dropped (would cross Liberty) | Draft |
| 10k.15 | Blocks | Deck 2.32 km2; 88 blocks: 71 building, 11 squares with vents, 3 park, 3 planting. Boulevard frontage all building; every third interior block under 1.5 ha a square | Draft |
| 10k.16 | Page and files | Mill Creek Deck artifact (Sanborn 0.25 m tiles, map 3 relief, Metro/RER, sheet index; line editing and block types saved to the page's db doc deck/layout; GeoJSON and KMZ export). Georeferenced sheets at 0.15 m in Maps\Sanborn\Georef_1904; layer, KMZ and generator in Maps\Deck_Street_Map | Kept |

## 10l. CUT approach tracks (2026-10-10, cut/tracks_gen.py)

| # | What | Result | Status |
|---|---|---|---|
| 10l.1 | APEx field (Ben: upper tracks about 1,600 ft, as built) | 1955 image: field N 4,331,650-4,332,130, throats about N 4,331,400 and 4,332,400. Drawn at E 712,686-712,838 (deck page platform zone), N 4,331,646-4,332,134, 16 tracks in 8 islands, numbered 1 at the building to 16 west (CVG Express 15-16 on the west side) | Ruled (length) / Draft (numbering) |
| 10l.2 | Traffic check | APEx: 241 Limiteds / 18 knots; north 135/18 = 7.5 a window, south 106/18 = 5.9; 3-min headway = 3.3 a track, so north 3 in + 3 out, south 2 + 2 plus the CVG pair. Lower level north: ORR 14 (X1 2, X2 2, R1-R5 5, L56/L71/L73/L74/L75 5) + Transvalley 6 (placeholder) = 20 a hour, one full pair, so 2 pairs; south 10 (Transvalley 6 + intercity 4, placeholders), one pair a bridge; TRI B/D one pair. North 6 + 4 + 2 = 12 tracks, south 4 + 2 + 4 = 10. Lower platform use 210 + 18 + 80 = 308 track-min an hour = 5.1 of 8 | Kept |
| 10l.3 | Level order (Ben chose B) | 0: APEx rail 144 m; -1: Hartwell concourse; -2: lower platforms, rail 131.9 m; TRI A at or below 123.8 m and Metro 8/10 at or below 125.8 m pass under the lower level, so Evans goes underground. Option A (lower at 127.8 m, cross-lines between) rejected: CS climb 3.4-3.6% | Ruled |
| 10l.4 | Lower level | 8 through tracks, 4 islands, about 80 m (E 712,700-712,780) under the north and middle of the APEx field, west of Line 7. A-D 200 m (TRI 8-car standard), Transvalley, to the CS pair; E-H 305 m (1,000 ft), ORR and intercity, to the C&O pair; all eight reach the north pairs | Draft |
| 10l.5 | North splits | Trunk W to E: 2 lower, 6 APEx, 2 lower, 2 TRI B/D. Lower pairs leave the trunk flanks at portals N 4,332,630 (231 m of ramp before the APEx ladder overruns the flanks at about N 4,332,372), drop 12.1 m in 346 m at 3.5%, then a 150 m ladder at -2 to the platforms at N 4,332,134 | Draft |
| 10l.6 | CS connection (Ben: west of the APEx throat) | CS bridge: fixed, 78.9 ft vertical clearance, mile 472.3 (Waterway Guide); low chord 162.3 m on the 453.6 ft pool or 163.7 m on canon pool; rail taken as 164-166 m (truss floor assumed 1.5-2 m). North abutment about (712,585, 4,330,665) on Ben's river outline. Climb from the A-D ladder end (N 4,331,814) 1,161 m at 2.8-2.9%; clear of the field by 135.9 m at about E 712,677; rail 148.9 m at W 8th; passes deck level near 7th St (N 4,331,075) | Ruled (west) / Draft |
| 10l.7 | Stock (Ben) | Lower level all electric; push-pull allowed. At 2.9% with a 90 t locomotive: 10 coaches at grip 0.25 (the platform cap) and 8 at 0.20 | Ruled |
| 10l.8 | C&O pair | Level at -2 under the APEx south throat, clear at N 4,331,460, 2.5% to 144 m at N 4,330,979, then east along the riverfront beside the Cardinal branch | Draft |
| 10l.9 | TRI B/D east flank | Proposed: outermost east on the trunk, never under the APEx tracks or the lower ramps, joining the canon path at the field's NE corner to the Union Terminal TRI box (E 713,157); Western station shifts about 30 m east | Open, Ben to rule |
| 10l.10 | Saved profiles vs the APEx tracks | Profiler ground is the surface, not the yard level. TRI A (Union Terminal 142.0 m) crosses the field at about 146-148 m; TRI B 136.3-137.6 m under the north throat (moot if east flank); Line 4 Chinatown (146.8 m) sits inside the APEx south approach (needs at or below 137.9 m, or over at 152.1 m or more); Lines 7, 8, 10 not profiled | Open, Ben's profiler |
| 10l.11 | APEx river crossing | The KMZ line crosses the CS bridge line mid-river; APEx has to stay east of the CS bridge or share a rebuilt one | Open |
| 10l.12 | W 8th over the CS pair | Deck about 153.4 m there; the CS pair (148.9 m + 6.6 m envelope) needs W 8th about 3 m higher locally, or a viaduct like the real one | Open |
| 10l.13 | Page | CUT tracks layer (tracks.json), Approaches zoom, CUT approaches panel, platform letters and track numbers when zoomed, tracks in the GeoJSON and KMZ exports. Version 2 of the Mill Creek Deck artifact | Kept |
| 10l.14 | Ben's new sources | TRIMET_Lines.kmz (6 lines, absolute 3D): CUT rail 156.3 m; north trunk 151.2 m at Camp Washington rising to 155.6 m at the field; CS bridge north bank (712,595, 4,330,684), rail 164.0-164.7 m (Lebanon-Walton; CVG Express 161.7-163.9); C&O viaduct from the APEx approach at 158.6 m east along the riverfront (159-161.7 m) to the C&O bridge at (714,496, 4,329,961), 163.1-165.3 m. "westwood and northside cut alignment.kmz": the original Westwood and Northside RER ROWs meet at about (712,630, 4,332,880) and run straight to the field's east side (712,801, 4,332,156) | Read (cut/trimet3d.json, trimet_bridges.json) |
| 10l.15 | Straight trunk (Ben: clear the street between Alfred and D; straighten Camp Washington-CUT) | Straight from (712,750, 4,334,233) to the throat (712,762, 4,332,400), 1,833 m; clears the Garrard-line deck street (it overlapped between D and Alfred). Passes Line 7 Harrison station (712,721, 4,333,373) at the trunk's west edge. TRI B/D left on their canon path (RER layer); east-flank proposal withdrawn | Draft (tracks_gen2.py) |
| 10l.16 | Freight passing track (Ben: keep it) | Single track throat to throat on the field's west side (E 712,681), as the 1955 track ran; joins the westmost APEx main north and the first APEx main south | Draft |
| 10l.17 | South connections on TRIMET | CVG Express pair leaves the APEx approach at N 4,331,200 onto the TRIMET CS viaduct; CS pair (A-D) merges with it at (712,631, 4,330,830) onto the CS bridge: 1,120 m at 2.86% from 131.9 to 164.0 m; under Gest at 139.4 m, W 8th at 148.9 m (W 8th humps 3.8 m), over W 6th at 159.8 m (needs 158.5). C&O pair (E-H): 1.4% to pass under W 6th at 144.4 m, then 2.4% onto the TRIMET C&O viaduct at 160.1 m (713,433, 4,330,462) | Draft |
| 10l.19 | Ben's ruling: arch viaduct | Elevated at a set height above the cross streets between Garrard and McLean keeps every street (my "costs streets" came from holding the platforms at TRIMET's 156.3 m); CUT's upper platforms may rise. Applied: APEx rail = deck + 6.5 m (4.9 m street clearance + 1.6 m arch crown, fill and track, working) from Marshall to W 6th: 164.5 over Marshall, 161.2 over Liberty, 160.3 at CUT (+4.0 on TRIMET, 0.5 m above the 159.8 m rotunda floor), 159.8 Gest, 159.2 W 8th, 158.5 W 6th; 0.17% along the deck. APEx climbs 0.94% over 1,347 m in the deck's street-free north lobe; the four lower tracks and TRI B/D stay under the deck from there (the tunnel split). -1 Hartwell concourse at street level under the viaduct; -2 rail 144 m | Ruled (viaduct) / Draft (levels; tracker 2J and the CUT level table to restate) |
| 10l.20 | Lower platforms (Ben) | E-H 305 m centred under the field (N 4,331,738-4,332,042); A-D 200 m end level with E-H (N 4,331,738-4,331,938) | Ruled |
| 10l.21 | CS and C&O on the viaduct basis | Street over open track: canon RER clear height 5.8 m + 1.0 m deck = 6.8 m. CS pair (A-D) runs about 30 m east of Horne, under Gest (144.8 m) and W 8th, over W 6th (159.7 m), merging with the CVG pair at the CS bridge abutment (163.8 m). Climb after W 8th by W 8th hump: 0 m 3.41%, 1 m 3.22%, 2 m 3.03%, 3 m 2.84% (drawn), 4 m 2.65%, 5 m 2.46%. C&O pair (E-H) level at 144 m under Gest, W 8th and W 6th, then 2.09% onto the TRIMET C&O viaduct (160.4 m). CVG pair 0.9% from the viaduct (159.1 m) to the bridge | Draft |
| 10l.22 | Smooth curves (Ben) | Every alignment rebuilt with Chaikin corner cutting and tangent-matched junction curves; no vertex turns more than 6 deg; tightest curves are the -2 ladders (129-155 m) and the south throat fan (145 m); C&O connection about 162 m. Freight passing track moved inside the 152 m zone (E 712,688.5), islands 9.4 m | Kept (tracks_gen3.py; page version 4) |
| 10l.23 | Profiles on the viaduct basis | TRI A must pass under the lower level at or below 135.9 m (from Evans at grade, 2.9-3.4%); TRI B fits on its canon path; Line 4 between Garrard (153.7 m) and Chinatown meets the CS pair at about 150 m against a CS rail of 148.9 m; Lines 7, 8, 10 not profiled | Open |
| 10l.24 | Real CUT platform level (Ben) | TRIMET's 156.3 m is the real 1933 CUT platform level on the terminal's embankment, from LiDAR; the viaduct basis raises it 4.0 m to 160.3 m | Recorded |
| 10l.25 | Lower platforms (Ben) | All eight at 305 m, N 4,331,738-4,332,042, centred under the APEx field (supersedes the 200 m A-D in 10l.20) | Ruled |
| 10l.26 | TRI A and B/D (Ben) | TRI A may run at or below 135.9 m under the lower level; TRI B/D can share TRI A's level at the Union Terminal TRI box, or sit above it, if planned together | Ruled (profiles in Ben's profiler) |
| 10l.27 | APEx river crossing (Ben: see the KMZ) | My mid-river clash in 10l.11 was wrong: the APEx Routes KMZ line is a two-point segment that crosses the water from (712,678, 4,330,647) to (712,553, 4,330,366), just east of the CS bridge, and meets the CS line about 300 m into Ludlow. Drawn as a bridge parallel to the CS bridge, 58 m east of it, through the KMZ crossing. The south approach now runs straight from the throat onto it; APEx climbs 0.86% from W 8th (159.2 m) to about 164 m at the bank (162.5 m over W 6th). CVG Express pair leaves the viaduct south of W 8th and climbs 1.2% to the CS bridge | Kept (version 5) |
| 10l.28 | Lower-pair dive (Ben: ORR/intercity dive under the deck at a street break; streets may be broken; balance grade against tunnel length) | The lower pairs now climb with the APEx at the deck's north end and ride the viaduct to Bank, then dive between Bank (over, 162.1 m) and W Liberty (under, 147.8 m): 2.47% over 581 m, open between them; tunnel from Liberty to the lower platforms 338 m at 1.13%. Streets re-graded where 3 m or less does it: Dayton lowered 1.8 m, Poplar raised 2.9 m, Sherman raised 1.1 m; Exeter (3.6 m), York (4.9 m) and Findlay (4.7 m) end at the dive. First tried between Alfred and Harrison Ave (the existing gap by the roundabout): 2.44% but 1,345 m of tunnel | Superseded by 10l.30 |
| 10l.29 | RER stations on the page (Ben) | 20 stations from Cincinnati Rail.kmz (RER-1 to RER-5 lettered A to E, the code-session mapping Ben uses), merged where lines share a stop: Union Terminal A B D at E 713,157 and E at E 712,984; Straight and Western B D sit on the trunk (Straight under the viaduct) | Kept (context.json) |
| 10l.30 | Dive between Bank and Findlay (Ben: both unbroken) | With both streets left level the dive would be 3.80% over 368 m (Bank south edge to Findlay north edge). Bank lowered 2.0 m and Findlay raised 2.0 m: 2.71% from 160.1 m over Bank to 150.2 m under Findlay, open between them. The same grade carries on in the tunnel to Sherman (146.0 m), then 0.51% to the lower platforms at 144 m; tunnel from Findlay 551 m. Poplar, Sherman and W Liberty stay as they are (cover 6.8, 8.7, 8.9 m). Dayton (4.0 m), Exeter (6.0 m) and York (5.9 m) end at the dive. Re-grade options at each end: 1 m 3.25%, 1.5 m 2.98%, 2 m 2.71%, 2.5 m 2.44% (Poplar then needs +0.8 m), 3 m 2.16% | Draft (version 7) |
| 10l.18 | Viaduct vs tracker 2J (pushback, superseded by 10l.19) | Tracker 2J: yards decked, under-deck steam ventilation solved by CUT approach electrification (1929-1933), i.e. the approach runs under the deck (Grand Central model). Ben's arch viaduct (Glebe type) would put APEx at about 156.3 m at CUT (TRIMET) and 161-165 m over deck streets, -2 at about 144 m: Gest dips about 3 m under the south throat; Courtland, Flint, Wade, Wilstach end at the viaduct; the CS pair must either dip W 8th about 4.4 m or climb 3.5%; TRI A at or below 135.9 m works from Evans at grade, Line 4 and TRI B nearly fit as saved. Under the deck: streets intact except a 3.8 m W 8th hump; TRI A to 123.8 m (Evans underground), Line 4 to 137.9 m | Open, Ben to rule |

## 10m. Basin streets from the 1912 survey (2026-10-11, basin/)

Superseded by 10n: Ben rejected the traced streets (wobbly, blobbed junctions, widths changing along the block) and ruled the deck method.

| # | What | Result | Status |
|---|---|---|---|
| 10m.1 | Request (Ben) | Streets for the West End west of Plum and the rest of the basin, same method as the deck; agents allowed | Ruled |
| 10m.2 | Source | 1912 City Topographic Survey sheets 18, 19, 29, 30, 32, 33 (already georeferenced, 10c) instead of Sanborn: one consistent sheet set, every street drawn as paired property lines, so blocks and centrelines can be extracted automatically. Sanborn underlay for the basin not done (would be about 80 more sheets) | Rejected (Ben: use the deck method) |
| 10m.3 | Mosaic (mos.py) | 0.5 m; per pixel the sheet whose neatline is farthest (first-come order left neatline bands and a hard seam); 2 m band at each neatline blanked | Kept |
| 10m.4 | OSM check (osmcheck.py) | 1912 midlines against OSM centrelines of surviving streets: sheet 30 off 4.5 m E / 1.3 m N, sheet 29 off 1.2 m / 1.0 m (5-8 m mismatch at their seam). Affine per sheet (residual MAD 2.3-2.7 m) applied to 29 and 30; 18 and 19 shifted 2-4 m | Kept |
| 10m.5 | Ink and blocks | Adaptive threshold (background 70th percentile), red contours and blue pencil removed; free space labelled after 3 px dilation. First tries: fixed threshold missed sheet 29's lighter ink; 1-2 px dilation leaked blocks into the street network through outline gaps | Kept (blk2, blk3) |
| 10m.6 | Block test | Components by 75th-percentile skeleton width (street bands under 13.5 m), solidity, elongation; touch graph (a component wedged between touching neighbours is a closed-off street piece); carriageway bands between curb lines (sidewalk-width gaps along both sides); merged components re-split at 6 px dilation (split.py, split_giant.py, 92 + 50 blocks recovered); building pockets attached | Kept |
| 10m.7 | Tried and dropped | Skeleton of the street mask (wiggles, spurs at every building notch); removing thick strokes (text, ties) before labelling (opened every outline gap and merged the whole grid); thick-ink contact as a block feature (no signal) | Rejected |
| 10m.8 | Centrelines (vor.py, vgraph.py, streets.py) | Boundaries between neighbouring blocks' expansion cells, traced to a graph; spurs pruned, split crossings contracted, corners and width steps kept as nodes | Kept |
| 10m.9 | Names | 13 parallel agents read the 1912 labels chain by chain (West End 876 chains, east 752); 9 disagreements settled by hand; names carried along straight-through streets; 1912 spellings kept (Maeher, Coleraine, Cortland, Bremen, Hunt, Allison, Webster, Grandolfo, Barpes); Broadway bare; canal banks North/South Canal Street and East/West Plum Street | Kept |
| 10m.10 | Result (basin.json) | 2,512 street pieces, 398 distinct names, 168 km; 1,151 blocks, 4.39 km2; parks Lincoln, Sinton, McKinley, Washington, Lytle. One width per named street (length-weighted median, property line to property line). Canal open, Central Parkway not drawn (pre-1920s canon) | Superseded by 10n (page version 10) |
| 10m.11 | Area | West End: Plum St and the canal to the deck, river to Harrison Ave. East: Plum to Lytle Park and Eggleston, river to McMicken and the hillside foot (Liberty Hill, Reading Rd) | Kept |
| 10m.12 | CUT east strip | Kenner to Hopkins east of CUT (1912 McLean Ave yard) left open; real 1933 forecourt and Lincoln Park Drive not drawn | Open, Ben to rule |
| 10m.13 | Files | Page layers "Basin streets" and "1912 survey" (208 tiles at 0.5 m); Maps\Basin_Street_Map on Ben's computer (GeoJSON both CRS, names, scripts, README) | Kept |

## 10n. Basin streets by the deck method (2026-10-11, sbg/)

| # | What | Result | Status |
|---|---|---|---|
| 10n.1 | Ruling (Ben) | Back to the deck method: georeference the 1904 Sanborn sheets and build the streets from them; the traced 1912 layer (10m) is rejected | Ruled |
| 10n.2 | Sheets | 154 sheets from the key maps: vol. 1 sheets 1-83 (CHPL, 4125 x 4763 px; sheet 82 is a smaller 3438 x 3969 page), vol. 2 sheets 101-106, 111-126, 131-142, 145-148, 151-156 (CHPL), vol. 3 sheets 201-227 (LOC, about 6500 x 7800 px). Vol. 2 carries later paste-overs (1920s buildings, Central Parkway on the canal) | Kept |
| 10n.3 | Picks (agents, sbg/picks, INSTRUCTIONS.md, sb.py) | Every intersection read as the crossing of the two centrelines, names as printed, printed widths, alleys, bends and ends: 2,640 intersections, 1,390 widths, 211 alleys, 127 bends, 98 ends. Split sheets (13, 14, 17, 31, 32, 111, 112) carry two frames each | Kept |
| 10n.4 | Joint fit (fit/solve.py) | 161 frames: CHPL affine with soft similarity and page-size scale priors (about 11.4 px/m), LOC similarity (about 20.0 px/m); deck sheets 33-35, 47, 57-58, 67-69, 77, 201-202, 211-212, 221-222 held fixed. Observations: 1,080 ties between sheets (same named crossing), 608 OSM corners, 167 corners of demolished streets from the 1912 layer (sigma 6 m); RANSAC start, gates 25/15/10 m, Huber reweighting. Residuals: ties median 0.63 m (p90 1.8), OSM median 1.05 m (p90 3.4), frame medians median 0.74 m (max 3.9). Sheet 1 placed from two ties with its neighbour's rotation; 17 lower frame (Mill Creek mouth, west of the deck) not fitted | Kept |
| 10n.5 | Widened streets | First pass pulled the fit toward modern centrelines that moved since 1904: Linn -5.9 m (28 corners), W Liberty -3.2 m, E Liberty +3.6 m, Eggleston +3.9 m, Cutter -4.1 m, Central Parkway -6.0 m, Reading Rd +3.6 m, and 20 smaller ones. Dropped from control by rule (3+ corners with median offset over 2 m or p75 over 5 m; 1-2 corners over 4 m); fit re-run until none left | Kept (fit/osm_biased.json) |
| 10n.6 | Streets (fit/build.py) | 1,695 intersection nodes (663 read on more than one sheet), clustered within 10 m, outliers over 6 m from the cluster median dropped. Each street ordered along a spanning tree (gaps over 450 m split), cut into straight runs (total least squares, 2 m tolerance, printed bends forced), junctions at the run lines' intersection; T and L ends snapped onto the centreline they meet. Width per run: printed width on that run's sheets, else the street's printed width elsewhere, else 10 ft for alleys and 40 ft for streets (48 pieces, 3.8 km). Alley segments snapped to the bounding streets; parallel duplicates (one street read under two names, jog pieces also read under the plain name) removed | Kept |
| 10n.7 | Blocks (fit/post.py) | Faces of the street network minus the street bands; kept where the 1912 survey blocks cover at least 30% of the face (outside the 1912 cover, faces under 2.5 ha); pieces under 120 m2 or thinner than 4 m dropped. Parks from the 1912 park polygons (Lincoln, Sinton, McKinley, Washington). Everything clipped to outside the deck outline and the CUT east forecourt | Kept |
| 10n.8 | Result (basin.json) | 711 street pieces, 205 km (323 streets 151 km, 388 alleys 54 km), 499 names; 1,041 blocks, 4.87 km2. Streets drawn in deck style (ink casing, then fill) on top of the blocks | Draft (page version 10) |
| 10n.9 | Sanborn underlay (fit/tiles.py) | Each frame keeps the hull of its own picks (buffered 330 px CHPL, 560 px LOC); overlaps go to the frame the pixel is deepest inside, so seams fall near shared streets; deck sheets left to the deck tiles. 45 tiles of 512 m at 0.25 m plus a 2 m overview (21 MB), loaded on demand; rail yards with no picked streets fall outside every hull | Kept |
| 10n.10 | Checks | Streets over the warped sheets at 0.25 m (West End at Gest/Court/Richmond, CBD at Vine/3rd/Pearl, OTR at Liberty, riverfront yards): centrelines down the middle of the drawn streets, bands matching the printed widths. Light, dark and phone screenshots | Done |
| 10n.11 | Tried and dropped | Neatline detection for the masks (CHPL pages have no strong neatline; strengths 0.02-0.16); one free scale per CHPL sheet (sheet 19 ran to 12.05 px/m, 5% off); OSM corners on every surviving street (10n.5) | Rejected |

## 10o. Basin streets checked against OSM (2026-10-11, sbg/osmchk/)

| # | What | Result | Status |
|---|---|---|---|
| 10o.1 | Request (Ben) | Check the basin layer against the OSM grid; anything that should still be there can be verified | Ruled |
| 10o.2 | Method (check.py, runs.py, filt.py) | Every basin street sampled every 4 m against the OSM street of the same name (within 25 m); every named OSM road in the area sampled against the basin streets (within 8 m, parallel). 182 offset runs and 314 missing runs; modern names, stretches outside sheet cover and same-street offsets filtered out, leaving 91 offset items (40 m+, over 3 m) and 122 missing items (28 m+). Each rendered over the warped sheets with basin and OSM lines and reviewed by five agents | Kept |
| 10o.3 | Review | Offsets: 74 real changes since 1904 (Liberty, Linn, Eggleston, Gest, Freeman, Harrison, Winchell, McMicken widened or realigned; OSM drawing Garfield Place, Court and Central Parkway as two carriageways), 10 basin lines off the 1904 street, 2 a misregistered sheet, 5 no sheet. Missing: 73 modern, 32 on the 1904 sheets but missing here, 12 OSM along one building line of a 1904 street we have, 5 no sheet | Done (osmchk/results_all.json) |
| 10o.4 | Sheet 18 | The free solve had rotated it -18.5 deg (its picks lie on two parallel N-S lines and only 3 observations passed the gates); rotation pinned to its neighbours' -3.5 deg; residuals now 0.1-2.4 m. Carr, Freeman, Sloo, Sibley and Sargent back on OSM | Kept (solve.py ROT_FIX) |
| 10o.5 | Placement fixes (corrections.json, pick_fix.json) | Moved onto the OSM centreline where OSM sits on the 1904 street: W 9th (two stretches), W McMicken at Freeman, Reedy, Baum (with its east bend). W Court (Mound-John) 5 m south. W Central Parkway west of Elm and on its E-W stretch onto the middle of the OSM carriageways (it ran on the south block face). W 6th west of Harriet: sheet 17 lower-frame bends had been placed with the upper frame's transform. Lockport: north leg kept apart from the diagonal, diagonal from the sheet 140 centreline points, approximate sheet 141 corner dropped. Findlay Market: Elder drawn as its two 45 ft roadways with the market house open between, Pleasant meeting both | Kept |
| 10o.6 | Links through buildings (bldg.py) | Each centreline tested for 12 m+ runs over building fill on the warped sheets (35 flags), plus crossings no pick supports; the 1912 survey used as tie-break. Cut 9: Snyder, Hazen (twice), the N-S Betts alley, E 4th's diagonal, Sweeney's diagonal, W Court between Harriet and Freeman (no picked crossing with Carr, Louisa or Fillmore), John through the Central Union Depot train shed, Sloo west of Carr. The rest were narrow streets or buildings put up after 1904 (theatres, YMCA, the 1919 courthouse) and stay | Kept (cuts.json) |
| 10o.7 | Added | 35 pieces for the 32 missing items, drawn on the OSM line, clipped to sheet cover, ends snapped onto the network; widths printed where legible, else estimated from the sheet or defaulted. Includes Branch St (30 ft), Lang St to McMicken (40 ft), the Hopkins gap at Dalton, both Hurst Alley legs, Bogen Alley, East Clifton Ave, Cumber and Young Sts, and about 20 unnamed alleys. Crossings with an unnamed way now count as vertices (62), which brings back Gest Alley | Kept |
| 10o.8 | Result | Same-name agreement on streets that did not change: median 0.69 to 0.68 m, within 2 m 83 to 85%, within 3 m 92 to 94%, over 5 m 6.2 to 5.2% (mostly where today's street is shorter or ends at a T). 749 pieces, 205.6 km, 492 names; 1,045 blocks, 4.89 km2 | Draft (page version 11) |
| 10o.9 | Sheet editions | The vol. 1 CHPL scans are the 1904 atlas corrected to about 1930 (buildings dated 1915-1931 pasted over), so a street built over on the image may still have existed in 1904 | Finding |

## 10p. Metro and RER over the basin; 6th, Pearl, Court; streets on OSM (2026-10-11, transit/, sbg/fit/osmfollow.py)

| # | What | Result | Status |
|---|---|---|---|
| 10p.1 | Request (Ben) | Extend the Metro and RER lines to the basin; draw actual tracks and platforms, as at the CUT; 6th, Pearl and Court look wrong; follow OSM for Central Parkway, Eggleston Ave and Reading Rd | Ruled |
| 10p.2 | Metro and RER layer (transit/build_transit.py) | Alignments and stations clipped to the whole page window (E 711300-716800, N 4329650-4335800), not just the deck. Metro: 17 pieces of Lines 1-12 and the 2b branch (12 twin-tube pieces, 5 single-bore), 107 stations. RER: 17 pieces, 29 stations; shared trunks drawn once (same line drawn twice removed at under 5 m Hausdorff; a trunk drawn again under another line with the same KMZ name split where the two coincide within 60 m). Fountain Square RER stations placed on the platform lines from Ben's A-D and B platform KMZs | Kept |
| 10p.3 | Tracks and platforms | Two track lines per piece (68) and platform outlines (225: 195 Metro, 30 RER), drawn at 0.8 px/m and closer in place of the single line. Platform lengths are canon: Metro 500 ft (152.4 m), RER 670 ft (204.2 m) (Ben, 2026-10-05). Layout follows 10j.4: Lines 1-7 twin tubes with island platforms, Lines 8-14 one double-track bore with side platforms. Drawing values, not canon: Metro tube centres 8 m, island 8 m, side platforms 4 m, rail to edge 1.45 m; RER tunnel centres 4.5 m, island 11 m, rail to edge 1.75 m (as the CUT lower level); tracks spread to the island over 40 m tapers. Platforms dropped where under 60% of the length fits inside the window | Kept |
| 10p.4 | W 6th (sheet 30) | The market space was one 6th St band at the full space width. Now two 42 ft roadways with the market house between; the south roadway lines up with 6th east of Elm | Kept (pick_fix.json) |
| 10p.5 | W Pearl (sheet 12) | Same fault. Now two 40 ft roadways with the warehouse block between, and Public Play Grounds No. 1 kept as a park (its face is outside the 1912 block cover, so the park point now overrides the 30% rule) | Kept |
| 10p.6 | E Court, Vine-Walnut | Left at the printed 126 ft: the sheet edition shows the space open, with the market house pasted over. Could be split into two roadways like 6th and Pearl | Open (Ben) |
| 10p.7 | Streets on OSM (osmfollow.py, post.py FOLLOW) | Central Parkway, Eggleston Ave (with the Lockport diagonal it replaces) and Reading Rd rebuilt from the OSM ways of those names (motorway, links and service ways skipped): carriageway pairs 6-45 m apart and parallel centred to their midpoint, chained along the longest path of the spanning tree, lightly smoothed, simplified to 1.5 m. Central Parkway runs 2.31 km at 150 ft from Eggleston/Reading west and north to McMicken, replacing the sheet pieces and the W/E Plum canal-bank streets; Eggleston 0.94 km at 91 ft, Reading 0.70 km at 70 ft (widths kept from the sheets). Crossing streets' ends moved onto the new lines; pieces under 30 m left by the swap dropped | Kept |
| 10p.8 | Result | 746 pieces, 205.5 km (330 streets, 416 alleys), 489 names; 1,041 blocks and 9 parks, 4.88 km2 | Draft (page version 12) |
| 10p.9 | Checks | Screenshots at overview, Fountain Square, Union Terminal and the Central Parkway station, light, dark and phone | Done |
| 10p.10 | Fountain Square model | The detailed station model (Station_Area_Maps_Log) gives Lines 1, 2 and 7 side platforms there; the map follows the later 10j.4 island rule | Discrepancy (Ben) |

## 10q. Basin streets aligned (2026-10-11, sbg/fit/build.py, post.py, widthnotes.py)

| # | What | Result | Status |
|---|---|---|---|
| 10q.1 | Request (Ben) | Streets better aligned: some slightly off-centre and not continuous. Mid-task: Central Parkway's turn, W 8th between Central and Elm, and John St doubled between 6th and 7th may be wrong | Ruled |
| 10q.2 | Drawing | Every basin casing drawn first, then every fill, so crossings and joins read as one paved surface (each piece had drawn its own casing across the street it met) | Kept |
| 10q.3 | Straight runs | Neighbouring runs merged into one line where the merged fit stays within 3 m (RMS 1.25 m) and they differ by 8 deg or less; printed bends never merged. Near-parallel runs that do not meet within 12 m of their junction now step at that crossing (the old link tilted both runs toward a midpoint). W/E halves of one street put on one line where both fit it within 3 m (14 pairs). Small bends (0.3-6 deg) in Sanborn-built pieces 74 to 46, the rest being real bends | Kept |
| 10q.4 | Doubled streets | One street read under two names on different sheets had been drawn twice: John (sheets 23-24 call the piece south of 7th plain John; folded into one street that jogs 16 m at 7th, as sheets 42-43 print it), L'Hommedieu (the plain line ran through St Paul's Church between Central and Elm), Carlisle (Cutter to Baymiller), W 8th east of Central, Branch (OSM addition on top of the sheet piece), Deming (a dead end read on two sheets made a hairpin). Rule: a long link of one name is not drawn where two or more vertices of a section name of the same street lie within 15 m of it; a terminal dead end read twice keeps the reading that does not turn back; named alley segments within 20 m of and parallel to their built street dropped. L'Hommedieu no longer runs from the Shillito wall to Race (sheet 45) | Kept (pick_fix alias, nolink_at) |
| 10q.5 | Overlaps | Where two pieces lie on top of each other, a jog link of one street lying along another is cut from the jogging street (it had removed Gilbert Ave under E Court's jog); one street read twice keeps the longer reading | Kept |
| 10q.6 | 6th St market | South roadway now its own piece, straight from Plum to Elm; 6th east of Elm starts at Elm, 3.5 m north of it as sheet 30 prints (the diagonal across the market space at Elm is gone) | Kept |
| 10q.7 | Central Parkway turn | The OSM carriageways part at the turn, so the centreline came out as two pieces with a hook and a 32 m gap. Joined by a circular-arc fillet tangent to both; it runs midway between the OSM carriageways | Kept (osmfollow.bridge) |
| 10q.8 | W 8th, Central to Elm | Matches the sheet (between City Hall and St Peter's) and OSM within 1.1-1.9 m. The 21 m jog at Central is printed on sheet 43 (60 ft west of Central, 53 ft east of it, centre ~246 px further north); W 9th jogs there too. Modern 8th west of Central has been realigned | Checked, no change |
| 10q.9 | Widths | 37 width notes that name a side of a crossing ("40' north of West 5th", "printed 50' between Liberty and Wade") parsed; runs split at that crossing and given the width printed for their side, the nearest named crossing deciding. John 40 ft north of 5th and 60 ft south; Smith 40/50 at 5th; Hopkins 60/50/80/40 at McLean, Dalton and Freeman; W Liberty, W 14th, Dalton, Freeman, Baymiller, Butler, Oliver likewise. Streets with market-space overrides (W 6th, W Pearl, Elder) excluded | Kept |
| 10q.10 | Result | 764 pieces, 204.0 km (344 streets, 420 alleys), 489 names; 1,039 blocks and 9 parks, 4.86 km2. Visible gaps (an end stopping short of a street's edge) 2: Gamble Alley 13.5 m short of Wade and Pennock Alley 4.3 m short of Mound, both as read | Draft (page version 13) |

## 10r. Deck streets on the basin lines, dive cuts, Union Terminal TRI box (2026-10-12, deck/deck_gen.py, cut/tracks_gen3.py, transit/ut_box.py)

| # | What | Result | Status |
|---|---|---|---|
| 10r.1 | Request (Ben) | Realign the new deck streets on the 10q basin streets; Dayton, Exeter and Bank cut on both sides of the viaduct ramp; TRI B/D platforms Chatelet-Les Halles style with two tracks per platform, D's platforms on RER A's tracks | Ruled |
| 10r.2 | T streets | Each deck street that carries a West End street starts where the basin centreline meets the deck edge and runs on the basin street's own line to the boulevard (was the 1904 anchor at Garrard on one 93.6 deg bearing). Ends had been up to 10.5 m and 3.3 deg off (W 7th, Budd, W 9th, Richmond worst). Court has no basin street at the deck edge and keeps its 1904 line | Kept |
| 10r.3 | Through streets | On the basin street's line from its west end across the boulevard; the bend to the west-bank line falls at the boulevard's west edge (W 6th 10.6 deg, Gest 4.5, W 8th 1.7, Liberty 0.1). W 6th now reaches the basin piece (a 206 m gap closed); Gest and Liberty no longer overlap theirs (121 m and 218 m) | Kept |
| 10r.4 | New streets | North of Bank the deck streets now continue the basin streets that reach the deck edge: Dolph (N 4,333,099), McRoberts (4,333,149) and Western Avenue (4,333,255), west on the deck grid; Harrison's re-aligned avenue ends on the basin Harrison (712,784, 4,333,349). The old New street D (on top of Harrison) is gone; New street E stays. Dolph and McRoberts arrive 50 m apart, so the block between is about 32 m deep | Kept |
| 10r.5 | Dive cuts | The ramps run on both flanks of the APEx viaduct, so Dayton, Exeter and York now stop at the outer wall on each side (open cut E 712,733-712,787, N 4,332,595-4,332,955, track envelope 2.0 m + wall 1.5 m) and nothing crosses between; flags on both sides; the cut is a void for the blocks and drawn on the page. York, not Bank: Bank was ruled unbroken in 10l.30 (lowered 2.0 m, passes under the lower pairs at 160.1 m) | Kept |
| 10r.6 | Knock-on in the tracks | Track generator now reads the realigned streets: Bank's south edge 6 m further south, dive 2.76% over 360 m (was 2.71% over 368 m), tunnel 553 m; Dayton 3.8 m, Exeter 5.9 m, York 6.0 m (all still over 3 m, so they end); Sherman cover 8.8 m, Liberty 9.0 m; CS climb 2.81% (was 2.83), 160.0 m over W 6th (needs 158.5); C&O 2.12% (was 2.09) | Kept (page version 14) |
| 10r.7 | Union Terminal TRI box | Six tracks, three islands of two: north A westbound / D westbound, centre B westbound / B eastbound, south D eastbound / A eastbound (right-hand running, as the Fountain Square A/D proposal: A outer, D inner). B and D arrive together from Western and split in the box; east of it D joins A's tracks (A eastbound onto D eastbound, A westbound off D westbound) to City Hall and B leaves on its own pair. Platforms 204.2 m (canon); drawing values island 11 m, 14.5 m across an island, 4.5 m back to back, 52.5 m overall; heading -3.75 deg | Superseded by 10r.10 |
| 10r.8 | Crossings the box needs | B/D between A's tracks means two crossings at separate levels, as at Chatelet. West: B/D over or under A westbound 106 m from the platform end, pinned by the canon B/D curve; 6.8 m between levels is 6.4% for one line, 3.2% each if A westbound dips 3.4 m and B/D stay 3.4 m up. East: A/D westbound over or under B 248 m out (2.7% one line, 1.4% split); A/D stay north to 300 m to keep it there. Needs TRI B/D at TRI A's level in the box (allowed, 10l.26) | Superseded by 10r.11 |
| 10r.10 | Union Terminal box set by direction (Ben: like Chatelet, connected accordingly) | Chatelet order with two tracks per island, westbound north: A westbound / north island / B westbound, D westbound / centre island / D eastbound, B eastbound / south island / A eastbound. A and B change cross-platform in the same direction; D has the centre. B and D arrive as one pair from Western: B takes the line track into the station and D leaves it at a turnout (and joins it westbound). East of the station D's tracks join A's (A westbound off D westbound at 330 m, A eastbound into D eastbound at 470 m) to City Hall; B leaves on its own pair north of the A/D trunk. Direction labels on the platform tracks when zoomed in | Draft (page version 15) |
| 10r.11 | Crossings this needs | West: A westbound across the B/D bundle at 193-223 m out, nearest 91 m beyond the platform end (pinned by the canon B/D curve): 6.8 m between levels is 7.5% for one line, 3.7% each if split. East: three crossings, all B against A/D (A westbound across B westbound 293 m out, B eastbound across D eastbound 352 m, A/D westbound across B eastbound 390 m), so the B pair changes level once: 3.6% if B takes all 6.8 m from the platform end, 1.8% split. Curves: B/D into the station 130-165 m radius (the canon curve), elsewhere 165 m or more | West superseded by 10r.12 |
| 10r.12 | B/D western approach moved (Ben: extend the curve further out if it helps A; the B/D ROW came from the freight-yard ROW, not a true ROW through the deck) | From the end of the KMZ Mill Creek trunk (712,661, 4,332,809, heading -79.4 deg): right bend 17.2 deg at 250 m radius, 591 m straight SSW west of the lower pairs, left bend 250 m radius onto the station axis 330 m west of the station centre, then on the axis to the box. North of A's line throughout, so B/D cross only A westbound: now 377-398 m out, 275 m beyond the platforms (6.8 m is 2.5% for one line, 1.2% split). The crossing sits under CUT's lower level, where TRI must stay at or below 135.9 m, so B/D dip under A westbound (about 129 m) and A keeps its level. Every box track now 144 m radius or more (A eastbound's rejoin, the tightest). The new route no longer crosses RER E north of the station | Route north of the final bend superseded by 10r.13 |
| 10r.13 | B/D on a direct bored line (Ben: the route need not follow the grid, but it is bored, so no needless curves) | From the KMZ trunk just south of the B/D junction (712,245, 4,335,539, heading -92.4 deg): left 8.6 deg at 1,200 m radius, one 3,285 m straight at -84.0 deg under the deck (past the Palace and the roundabout), then the 10r.12 final bend (80.2 deg at 250 m) onto the station axis 330 m west of the centre. Old line (freight-yard trace, Straight bow, S-bend, 10r.12 approach) 4,002 m with 287 deg of turning; new 3,845 m with 89 deg. Stations moved onto it, each between cross streets: Camp Washington (712,303, 4,334,859) opposite the Line 5/9 station, 161 m (was 98 m); Straight (712,383, 4,334,099) between Straight and Alfred, 535 m from Line 5 Straight (was 162 m, the one transfer this costs); Western (712,479, 4,333,196) between Dolph and Western, platform ends at both streets, 285 m from Western Hills A (was 385 m). B/D now run 83-140 m east of A from Bank to Straight. A westbound crossing 378-398 m out, 286 m beyond the platforms. Box tracks unchanged | Superseded by 10r.14 (wrongly took the line as bored from Camp Washington) |
| 10r.14 | B/D construction (Ben: at grade to Camp Washington, then dug tunnel, then bored) | At grade under the deck's north lobe to Camp Washington and dug on the KMZ trunk to Straight, so both stations and the KMZ line through them stay (Camp Washington 712,401.5, 4,334,799.9; Straight 712,754.5, 4,334,139.1). Bored from Straight (my reading: Straight's box launches the bore; Ben to confirm where dug ends). The KMZ bend into Straight (measured 418-454 m radius) is kept as one 450 m curve of 38.8 deg from (712,677, 4,334,414); it ends 14 m past the Straight station point on a straight through that point and tangent to the box curve: 1,992 m at -94.55 deg (0.8 deg off the deck grid), then 90.8 deg at 250 m onto the station axis 330 m west of the centre. Drops the freight-yard trace past Western, its S-bend and the 10r.12 right bend: from the curve start to the box, 2,734 m with about 183 deg of turning before, 2,720 m with 130 deg now. Western (712,678, 4,333,183) on the straight between Dolph and Western, entrances at both, 53 m from the KMZ point, 194 m from Harrison (Line 7) (was 218 m); 60 m west of the CUT bundle, 87 m from the dive cut. A westbound crossing 280 m beyond the platforms. Platform tapers at Straight sit on the 450 m curve, as in the KMZ | Draft (page version 18) |
| 10r.9 | Chatelet layout (checked) | 7 tracks, 4 islands: 1A (A east) / quai 1 / 1B (B south), 3 (D south) / quai 3 / Z / quai 4 / 4 (D north), 2B (B north) / quai 2 / 2A (A west); A-B cross-platform in the same direction on the outer islands, D in the centre with a shared Z track | Source (fr.wikipedia Gare de Chatelet - Les Halles) |

## 10s. Sheets 34 and 35 re-registered (2026-10-12, deck/sheet_tf.json, sbg/fit/tf.json)

| # | What | Result | Status |
|---|---|---|---|
| 10s.1 | Request (Ben) | Major disconnect in the streets between the sheets between McLean and Harriet | Ruled |
| 10s.2 | Cause | Deck sheet 35 has no corners east of McLean and basin sheet 36 none west of Harriet, so nothing tied them. Sheet 35 hung from a W 8th tie to sheet 47 and three points on the 1912 6th Street line, both pulling it north: 34 and 35 show W 8th only in part at their top edge, and the 6th1912 line sits about 20 m north of the 1912 survey's 6th Street centre. At the seam, sheet 35's W 8th, W 7th, Deming Alley and Budd lay 11.5, 14.2, 15.7 and 18.2 m north of sheet 36's; against the 1912 survey, W 7th 12 m, Deming 10.5 m, Budd 6.4 m. Sheet 36 agrees with the 1912 survey within 2 m (4 m at W 8th). The basin streets bridged the gap with a skewed run (W 7th at -6.9 deg between McLean and Harriet) | Found |
| 10s.3 | Fix | Sheets 34 and 35 moved 15 m south (34 with 35: it hangs from the same W 8th ties and shares Horne with 35). At the seam after: W 8th +3 m, W 7th +1 m, Deming -1 m, Budd -3 m | Kept (page version 19) |
| 10s.4 | Knock-on | Basin W 7th, Deming, Budd and W 8th now run straight from McLean to Harriet (W 7th -2.9 deg); nothing else in the basin layer moved. Deck T streets W 7th and Budd follow their basin lines, so their boulevard ends move 52 m and 33 m south (the skewed run had rotated them); W 8th's bend at the boulevard moves 15.6 m south. CUT tracks: CS climb 2.84% (was 2.81), 159.9 m over W 6th (needs 158.5); APEx 162.5 m at W 6th (was 162.6). Georef_1904 sheets 34 and 35, basin_sbg layer and transforms, and Deck_Street_Map re-exported | Kept |

## 10t. Deck refit, Lower Price Hill spline onto the 1922 plates, Camp Washington and Northside (2026-10-13, lph/, sbg/fit/, deck/deck_gen.py, transit/build_transit.py)

| # | What | Result | Status |
|---|---|---|---|
| 10t.1 | Request (Ben, 2026-10-12) | Camp Washington (Central Parkway to Beekman) and Northside/South Cumminsville by the same method as before (terrain map plus Sanborn); extend the Metro and RER. Then: the Sanborn spline only for the Lower Price Hill block (Western Ave, State Ave, Gest St, Ohio River; 1922 plates 3, 6, 26, 29); "the rest of the deck can be set in the same method as we used before" | Ruled |
| 10t.2 | Reading of "the rest of the deck" | Taken as the basin method (picks + OSM + 1912 + ties), not the old deck fit; told Ben, no reply yet | My reading (Ben to confirm) |
| 10t.3 | Picks (agents, sbg/picks22, sbg/picks, sbg/picks12) | 1922 vol. 1 halves 3L/R, 6L/R, 26L/R (26R main + inset), 29L/R (also 9, 10, 13, 16, 31, 33L, 34, unused). Vol. 5 sheets 460-464, 466-468, 491-496, 504-505, 511-514, 519-520, 522 (1-17 crossings each; the yard sheets are sparse). North: vol. 3 sheets 233-305 and vol. 6 601-635. 1912 survey corners for the north: 417 (campwash 160, northside_e 96, cumminsville_w 161) | Done |
| 10t.4 | 1922 georeference (lph/fit22.py, tf22_aff.json) | Affine per half on OSM corners (osm_basin + osm_valley), fitted basin frames and ties between halves. Plates 26 and 29 are 200 ft to the inch (5.2 px/m), 3 and 6 100 ft (10.2 px/m). Medians 1.3-1.5 m (east halves), 2.0-3.3 m (west, where State at 8th, Gest and Wilder have since been realigned) | Kept |
| 10t.5 | Finding | The old deck fit put sheets 33-35 and 47 13-20 m too far west and 57 8-10 m (34 had no observations of its own). The 1922 plates, the 1912 survey (track along Garrard, its curve, the W 8th viaduct) and OSM's surviving Horne Street agree within 1-3 m; sheet 58 (tied to the basin) agreed already | Found |
| 10t.6 | Joint refit (lph/solve_all.py, tf_all.json) | 106 frames free (deck vol. 1 as affine with soft similarity priors at 11.40 px/m, vol. 3/5/6 as similarity at 20.0 px/m), basin frames fixed except 223/224. Controls: OSM corners, 1912 corners (picks12; traced basin streets at 6 m), 1922 corners inside the block, old deck line points and block-corner ties (6th1912 line and in-block old points dropped). Residuals: ties 0.8 m (388), OSM 1.7, 1912 2.1, 1922 2.0. Rotation pinned: 236 (-2.6), 295 (-3.5), 492 (-33.7, State Ave bearing; its two crossings are both at Lehman) | Kept |
| 10t.7 | Basin 223/224 | Their ties sat 5-17 m off (1912 survey, OSM, deck 234) and the solve left them out; refitted in the same adjustment: 223 moves 8-20 m, 224 3-12 m, mostly north at Harrison | Kept |
| 10t.8 | Lower Price Hill spline (lph/tps.py, tps.pkl) | Per sheet (33, 34, 35, 47, 460u, 461-464, 466-468m): thin-plate spline of crossing residuals onto the 1922 positions (smoothing 0.05 in 100 m units), zero anchors on a 60 m grid more than 120 m from any crossing, tapered to zero over the last 80 m before Gest (N 4,331,620) and Western Ave (E 712,880). Crossings held within 0.3 m (468m 0.7); bends up to 7.3 m (463). Checked: Evans/W 8th four-sheet corner and the McLean-Harriet seam continuous | Kept |
| 10t.9 | Creek mouth (sheet 34 SW corner) | 34 and 1922 plate 3 draw the creek bend at W 6th about 35 m east of the 1912 survey; no crossing within 150 m; left as fitted | Open |
| 10t.10 | Deck layer (deck_gen.py from tf_all + tps) | Garrard line 12 m east at Budd/W 8th, 10 m at Gest, 8 m at N 4,331,900, 5 m at 4,332,500, 1 m at Harrison; boulevard bearing 3.78 to 3.64 deg (south end 3.8 m east, roundabout end 2.7 m west); CUT square 1 m. Precinct now starts 9 m north of Hopkins along its whole south edge (the one-point rule let Hopkins clip it and cut Hopkins short). Deck streets follow: W 7th 15 m, Budd 11, Richmond 11, McRoberts 17 (with the 223 refit), Harrison east 17 at their east ends. 87 blocks | Kept (deck_v11.json superseded) |
| 10t.11 | CUT tracks | Re-run on the new deck: CS climb 2.83% (was 2.84), dive 2.72% over 366 m (2.76% over 360), APEx 162.6 m at W 6th | Kept |
| 10t.12 | Basin + north streets (sbg/fit/build.py, post.py with SBG_TF_EXTRA, SBG_SUFFIX) | Deck vol. 1/3 frames and north frames from tf_all (vol. 5 kept out), spline applied. 2,272 features: 280.9 km of streets, 629 names, 1,250 blocks (was 204.0 km, 489, 1,039). Basin core unchanged (715 of 725 streets within 0.5 m); Brighton streets move 4-15 m with 223/224 | Draft (page version 20) |
| 10t.13 | Metro and RER (build_transit.py) | Window to E 710,300-716,800, N 4,329,650-4,339,800: Metro 17 to 18 pieces, 107 to 135 stations (Northside, Chase, Kirby, Colerain, Spring Lawn, Winton Place and others); RER 16 to 21 pieces, 29 to 37 stations | Kept |
| 10t.14 | Tiles and page | Deck + north frames in one on-demand set (tiles_n: 66 tiles of 512 m at 0.25 m, 2 m overview; each pixel from the frame it lies deepest inside; panel lines read off 460, 468, 627, 628); basin tiles regenerated for 223/224; old deck tiles removed; sheet index rebuilt; North zoom button; sources notes rewritten | Done (page version 20) |
| 10t.15 | Tried and dropped | Correlating 1904 against 1922 line ink to bend the sheets: peaks 0.1-0.45, shifts scattered 3-5 m and biased against the named crossings | Rejected |

## 10u. 1922 fill, Camp Washington strip, Central Parkway north, Hopple and Ludlow (2026-10-13, lph/fit22.py, osm3.py, add22.py, tiles_n.py, sbg/fit/post.py)

| # | What | Result | Status |
|---|---|---|---|
| 10u.1 | Request (Ben, 2026-10-13) | 1. The other streets in Camp Washington from the 1922 map, plus Central Parkway. 2. The viaducts/roads across to the west side. 3. Fill in the area between sheets 522 and 608. 4. Discuss the space west of the boulevard in Lower Price Hill: does it have the grid too? | Ruled |
| 10u.2 | Picks (agents) | 1922 vol. 1 halves 35L (50 crossings), 37L (68), 37R (58). 35L's canal-side strip (Gilmore, Rachel, Bader) is already on the 1904 sheets; the rest of 35L is the Clifton Heights hillside, left out. 37R carries Ludlow Avenue | Done |
| 10u.3 | City-wide OSM | Historic_Topo/OSM/streets_all.geojson (Overpass, 2026-10-07) projected to UTM for E 709,500-716,500, N 4,329,000-4,341,000 (lph/osm_north.geojson, same source as osm_basin/osm_valley to the millimetre); OSM corners for the valley in lph/osm3.pkl (3,662 pairs). The north now has OSM control | Kept |
| 10u.4 | 1922 georeference (fit22.py, tf22_cw.json) | Halves 16L, 16R, 31L, 31R, 33L, 34L, 34R, 35L, 37L, 37R, affine, on OSM corners (osm3), fitted 1904 frames (tf_all), 1912 corners and ties. Medians 1.7-3.8 m at the controls. 37L had control only in its top half until the city-wide OSM gave Beekman/Fricke Road at its foot | Kept |
| 10u.5 | Central Parkway north (post.py, SBG_OSMP_PARKWAY) | Follows OSM from Brighton to Ludlow Avenue (6.2 km in all). OSM's line runs in the 1922 canal bed through the strip; drawn 90 ft north of Brighton (canal bed about 27 m on the plates), 150 ft in the basin. Gilmore gives way where the two coincide (four pieces left). North end carried 17 m onto the 1922 Ludlow line | Draft |
| 10u.6 | Camp Washington strip (add22.py) | Between the canal bed and West McMicken south of Marshall, from 16R: Halstead, Klottman (40 ft west of Halstead, 25 ft east), West McMillan, Hukill (15 ft), Eliza, Rush, West McMicken's missing 854 m, Straight and Marshall carried on to McMicken; 9 blocks. Also Gene Alley, Meeker (Spring Grove to Hopple), Burlington and Ledlie (34R). Stephens is the 1904 sheet's Heywood (east of Massachusetts), already drawn. Not drawn: Bogan and Oswaldt (only their Queen City ends are on 16R), Rush Alley (no south end), Addison (not picked), Tafel and Straight east of McMicken (hillside) | Draft |
| 10u.7 | Hopple Street viaduct | From Johnson (the 1904 piece's west end) west to Beekman on the 1922 line (34L, 34R; matches OSM's Hopple Street Viaduct), 496 m, 402 m over the deck's north lobe. It crosses the APEx trunk where the ramp is at 158.5 m against a 158.9 m deck (0.94% from the portal), so the roadway has to stand at 165.3 m or more (6.8 m over rail, 10l.21), about 6.4 m above the deck. Canon Metro L9 runs under it (North Fairmount at Beekman, Camp Washington) | Draft |
| 10u.8 | Ludlow Avenue | From Dodsworth Avenue (the 1904 name of its first block from Knowlton's Corner) south beside the B&O, which it crosses at grade on 37R, then over the old canal bed, past Central Parkway's north end, up to Lafayette Avenue, 990 m; Lafayette junction within 25 m of the 1912 survey corner. Drawn as a street, not a viaduct | Draft |
| 10u.9 | Already across | W 6th, W 8th, Gest and Liberty cross the deck; Harrison and Queen City reach the deck's west edge at the Palace roundabout; Colerain crosses the creek below Northside on the 1904 sheets | Recorded |
| 10u.10 | 1922 underlay (tiles_n.py) | Plate halves 34L, 34R, 37L, 37R and the 16R strip under the 1904 sheets (a 1904 pixel always wins), each clipped to its mapped area (key boxes, title blocks and other plates' blank areas left out). Fills the west bank between 522 and 607-608, the creek and railroads north of Hopple, the strip east of the canal bed. 77 tiles (was 66), 42 new or redrawn; 1922 outlines in the sheet index | Done (page version 21) |
| 10u.11 | Layer | 2,301 features, 289.0 km of streets, 640 names, 1,257 blocks (was 2,272, 280.9 km, 629, 1,250). Page: 1922 streets under the basin toggle, viaducts with dashed edges, notes paragraph | Done (page version 22) |
| 10u.12 | West of the boulevard in Lower Price Hill (question 4; ruled in 10v.6) | No grid. The deck there (about 100,000 m2 south of Gest, the C.H.&D. yard between Depot and Evans) has no blocks; W 6th, W 8th and Gest cross it, Perin and South run in from Evans. Lower Price Hill's own grid (State to Evans) is not drawn: the vol. 5 sheets were kept out of the street build (10t.12), so the whole west side shows Sanborn only. Options put to Ben | Open, Ben to rule |

## 10v. Crossing levels against TRIMET and APEx; Lower Price Hill option C (2026-10-13, lph/add22.py, lph/lph_grid.py, deck/deck_gen.py)

| # | What | Result | Status |
|---|---|---|---|
| 10v.1 | Request (Ben) | 1. The TRIMET KMZ has the gradient of the RER D viaduct north of Camp Washington, if it affects Hopple or the other crossings. 2. Option C for Lower Price Hill, but most buildings north of W 8th are razed for the deck and the Expo: straighten Gest and continue the basin's W-E streets against Lower Price Hill's N-S streets like Evans | Ruled |
| 10v.2 | RER D (TRIMET Greensburg-California) | Falls about 1.8% from Westwood (181 m at 711,511, 4,336,604) on a viaduct over South Cumminsville (30+ m over Borden and Llewellyn) and down the creek line to the trunk at 152.2 m about N 4,335,140, 250 m north of Hopple. At Hopple every TRIMET line is on the trunk at 151.1-151.4 m, under the deck. Sets neither Hopple nor Ludlow | Recorded |
| 10v.3 | Found: RER D vs the deck's north end | At the deck's north edge (N 4,335,582) RER D is at 156.8 m against a 160.1 m deck surface (3.3 m), at the same spot as the APEx portal (151.8 m, 5 m below it). Not a street matter; left for the CUT approach work | Open |
| 10v.4 | Hopple profile (LiDAR 2 m ground) | Beekman 160.8 m; APEx ramp 158.5 m at the crossing, so 165.3 m or more (6.8 m over rail); Spring Grove 152.1 m, so 158.9 m or more over it; Meeker 157.6 m. Drawn as a viaduct from Meeker: 1.0% up from Beekman, 4.4% down to Spring Grove, 1.6% to Meeker. The 1904 Hopple piece now ends at Meeker; Johnson's south end and Spring Grove pass under | Draft |
| 10v.5 | Ludlow profile | The TRIMET north trunk crosses 208 m from Dodsworth at 155.5 m, at grade (ground 155.5 m), so 162.3 m or more; the climb starts at Knowlton's Corner (149.4 m) along Dodsworth, about 3.5% over 370 m, then about 2% to the old canal bank (163-166 m) 400 m on. Viaduct for those 400 m, at grade beyond; Central Parkway's north end sits on the bank at 167.7 m | Draft |
| 10v.6 | Lower Price Hill north of W 8th (deck_gen.py) | W 9th, Richmond, Court, Oehler, Clark and Hopkins cross the boulevard to Depot (Hopkins to Summer), kind through; Summer and Berlin on their 1904 lines from W 8th north, Evans from W 8th to Hopkins, kind NS; W 9th and Richmond end on Dutton and South at Depot (5 and 11 m snaps); South and Hopkins (LPH) dropped; Gest straight from State to the basin Gest (1.5 m north at the APEx trunk; track levels unchanged); W 8th from State. Blocks over the deck plus the cleared block: 112 (was 87). Between Evans and the boulevard the blocks run about 290 m | Draft (page version 23) |
| 10v.7 | Lower Price Hill's own grid (lph_grid.py) | Basin layer, set "lph": south of W 8th State, Depot, Burns, Neave, Hatmaker, Staebler, Storrs, St. Michael, German, Price, Evans, W 6th to Burns; north of W 8th the strip west of Depot (Depot, Dutton, South). 14 streets, 3.9 km, 11 blocks. The covered C.H.&D. curve south of W 8th is one long deck block; Perin is the only street across to the boulevard | Draft |
| 10v.8 | Layer and page | Basin layer 2,327 features, 292.9 km, 653 names, 1,268 blocks. Page: Lower Price Hill paragraph and crossing levels in the notes; side LPH in the street card | Done (page version 23) |

## 10w. The combined grid: Garrard seam, straight Lower Price Hill streets, 1904 squaring (2026-10-13, deck/deck_gen.py, lph/lph_grid.py, lph/seam_combo.py, lph/corners_built.py)

| # | What | Result | Status |
|---|---|---|---|
| 10w.1 | Request (Ben) | Make the LPH/deck corners square; then a non-90 degree seam at Garrard or Horne so LPH lines up with the basin, Market Street style; then combine that with options A-D. Ruled: the recommended set (seam at Garrard, A, W 8th and Gest on their own lines, jogs at Depot, D-lite) | Ruled |
| 10w.2 | Seam (deck_gen.py) | East of the Garrard line every E-W deck street keeps its basin line; at Garrard it bends onto the boulevard's square (axis 3.641 degrees, so 93.641). Bends up to 1.22 degrees (Richmond). West-end moves: T streets 0.1-2.2 m (Budd 2.2), Court 0.5, Clark 2.5, Oehler 2.6, Hopkins 5.7 m; W Liberty takes the seam (6.5 m north at its west end, nothing drawn there). Garrard was left on its fitted 3.36 degrees (turning it would move its ends about 9 m), so its west corners are 0.28 degrees. The N-side T streets (Alfred, Straight, Marshall) and Perin stay on GB 93.6 degrees (0.04 degrees off) | Done |
| 10w.3 | Option A | Depot (whole length, Price to the north end), Summer, Berlin and Evans straight and parallel to the boulevard, best fit through the 1904 centres: largest moves 2.5, 1.0, 1.4, 3.4 m. Evans' W 8th corner moves 3.4 m west. Depot is the whole length so Price meets it square (the table to Ben quoted 0.7 m for Depot north of W 8th alone) | Done |
| 10w.4 | W 8th and Gest | Own lines kept (both front surviving 1904 blocks at State; bending them at Garrard would move W 8th's State end 9.8 m south and Gest's 11.1 m north). 13 crossings west of Garrard at 0.37-0.73 degrees. Block rows taper: W 8th-W 9th 76 to 69 m, Court-Gest 61 to 52 m | Done |
| 10w.5 | W 9th and Richmond at Depot | Snaps to Dutton and South removed; they meet Depot 8.4 m and 6.2 m south of Dutton and South (jogs). Smaller than the 9.7 and 9.5 m quoted in the options: the analysis used the snapped lines east of Garrard, the build uses the true basin lines | Done |
| 10w.6 | D-lite (lph_grid.py) | Hatmaker, Staebler, Storrs, St. Michael, Price, Dutton and South straight on 93.641 degrees, Burns (W 6th to Hatmaker) and Depot on 3.641, each a best fit through its 1904 crossings; crossings on State, Neave, Evans and W 6th slide along those streets. Largest vertex moves: Depot and Price 2.5 m, State, Burns and Hatmaker 2.0, Storrs 1.6, Dutton 1.0, South 0.8, Neave 0.6, St. Michael 0.6, Staebler 0.5, W 6th 0.4 m. St. Michael's mid-block bend dropped. Burns/Depot crossings 0.18-2.67 degrees before, all square now. Neave, German, Evans' dogleg, Burns' kink to W 8th and State keep their surveyed angles | Done |
| 10w.7 | Found: two missing 1904 blocks | Between Burns and Evans south of W 8th the faces had never closed (the 1904 Evans/W 8th vertex sat 0.2 m off the deck's W 8th). With Evans' corner now on W 8th they close: 13 LPH blocks (was 11), 113,600 m2 (was 73,300) | Fixed |
| 10w.8 | Corner check (corners_built.py, on the built deck.json) | West of Garrard and north of W 8th, the 84 crossings not on W 8th or Gest: median 0.01, max 0.30 degrees (was median 0.26, max 1.69, 39 over 0.3). W 8th and Gest: max 0.73 (was 7.45 at W 8th/Evans). East of Garrard unchanged (basin lines on Garrard and Horne) | Done |
| 10w.9 | Layer and page | Deck: 45 streets, 111 blocks (was 112). Basin layer 2,329 features, 292.9 km, 653 names, 1,270 blocks. Page notes: seam, straight LPH streets, jogs, 1904 squaring | Done (page version 24) |

## 10x. Gest on the grid, W 8th straightened part way (2026-10-13, deck/deck_gen.py, lph/lph_grid.py, lph/w8gest.py)

| # | What | Result | Status |
|---|---|---|---|
| 10x.1 | Request (Ben) | Gest and W 8th are still off the grid. Ruled: with the upper part of LPH razed for the fair, move Gest's State intersection into line with the grid; W 8th can be altered slightly (125 years of organic straightening), mostly in line but not perfectly | Ruled |
| 10x.2 | Options (w8gest.py) | Bending either street at Garrard onto 93.64 misses its 1904 State corner by about 10 m (W 8th's Garrard-State chord 94.25, Gest 92.91). Put at State: W 8th 9.7 m S (1,900 m2 of 1904 fronts; Line 4's State station 19 m off the centreline), Gest 11.1 m N. Jog at Depot: W 8th 6.8 m, Gest 10.1 m. Jog at Garrard: 9.7 / 11.1 m (breaks the seam) | Superseded by 10x.1 |
| 10x.3 | Gest | Bends at Garrard onto 93.641 and runs straight to State, meeting it 11.1 m north of the 1904 corner (10.2 m at Depot, 6.4 m at Evans, 2.7 m at the boulevard). State is carried north to it; the strip block South-Gest grows to 9,300 m2. The 1904 Gest west of State (not drawn) would meet it with an 11 m jog | Done |
| 10x.4 | W 8th | One straight run from Garrard to State on 93.944, halfway between its own chord (94.248) and the grid (93.641); the 30 m kink at State is gone. Moves (south): boulevard west edge 1.5, Evans 1.9, Burns 2.2, Depot 2.5, State corner 4.8 m. 733 m2 of the 1904 blocks' fronts fall under the street. Line 4 at most 5.7 m off the centreline (was 2.8), State station 14.3 m (was 9.5), inside the 16.8 m half-width; Garrard station 1.5 m | Done |
| 10x.5 | Corner check | West of Garrard and north of W 8th: the 84 other crossings median 0.01, max 0.30; W 8th and Gest crossings max 0.30 (were 0.73) | Done |
| 10x.6 | Fix | Evans' 1904 corner is carried 0.3 m past the deck's W 8th so the Burns-Evans faces node (they dropped out on the first rebuild) | Done |
| 10x.7 | Layer and page | Deck 111 blocks; basin layer 2,329 features, 292.9 km, 653 names, 1,270 blocks; LPH 13 blocks. Page notes updated | Done (page version 25) |

## 10y. RER A between CUT, Evans, Westwood and Northside; Exposition Boulevard (2026-10-13, rera/rera.py, lph/wb_propose.py; design, not yet drawn)

| # | What | Result | Status |
|---|---|---|---|
| 10y.1 | Request (Ben) | Settle RER A between Westwood (on the hill), Evans and CUT before the streets west of the boulevard; Westwood at ground on the hill if possible; the short streets between State and the boulevard may be cut by the viaduct; the Northside branch may be viaducted or troughed/decked (it was at grade and cut streets); lean viaduct south of at least Alfred so both branches descend to Evans together | Ruled |
| 10y.2 | Found | RER A leaves the deck at N 4,332,790, 430 m north of Evans; both branches then run in the open 6-35 m west of the deck edge. Westwood (KMZ) is on the spur between State and Harrison at about 169 m. The valley floor west of the boulevard is about 100 m wide north of Liberty; State Avenue runs on the hillside at 170-175 m there (the sketch's streets to State north of Liberty were wrong) | Recorded |
| 10y.3 | Profile (G 3.3%, R 200 m) | Evans at yard level 147.5 m under W Liberty (reading of "Evans at grade"; 1.8% down to 135.9 m under CUT's lower level). Under the deck to its edge (148.4 m), one 3.3% ramp along the deck's west edge, fork at about N 4,333,115 (159.2 m). Westwood branch: 63.4 deg at 200 m radius over the foot of State Avenue (8.7 m clear), 3.27% up the spur to a 204.2 m platform at 168.9 m, at ground, centred on the KMZ point (leaves the KMZ line between the fork and the station). Northside: 164.5 m from about N 4,333,290 on a viaduct; Western Hills elevated; Harrison radial, Queen City and all area 2 streets pass under (8.5-10 m). Cut: Exeter, Dayton, Bank, Dolph west of the boulevard; McRoberts passes under (7.5 m) | Proposed |
| 10y.4 | North of Alfred (Ben: N2) | Viaduct rises to 168.2 m over the Hopple viaduct (161.4 m, 6.8 m); Hopple station elevated | Ruled |
| 10y.5 | North of Hopple (Ben: only underground by Spring Grove Cemetery at Linden/Crawford) | Ruled (Ben agreed, built in 10z): hold about 167 m (7.3 m under RER D's viaduct at South Cumminsville, 174.3 m); South Cumminsville and Northside elevated; 3.3% down from the Northside platform end to 144.2 m at Linden (5.9 m under it, box roof) into the tunnel under the cemetery. Cut: Chambers, Lingo, Dane; Hamilton, Knowlton, Fergus, Mad Anthony and all Millvale streets pass under. A covered line through South Cumminsville and Northside would meet Line 12 (Llewellyn station on the path), Line 13 and Line 5 (Northside station) | Ruled |
| 10y.6 | Boulevard name (Ben) | Exposition Boulevard: Mill Creek was decked over for the 1913 Exposition; "the deck" means the Mill Creek deck. Tracker 2J groups the creek burial with the post-1933 deck program; flagged to Ben | Ruled |
| 10y.7 | Garrard (Ben) | Shift the whole Garrard line west so its north end meets Camp Washington's Garrard Avenue (it was not a set street in the Sanborn): 9 m (1904 Garrard Ave points 8.7-9.4 m west of the deck line, 1922 6.6-14.1 m) | Ruled, applied in 10z |
| 10y.8 | Area 2 north of the Palace (Ben) | Align with Camp Washington's grid using the 1922 plates (16L, 34R): its streets there run 93.0 deg E-W (Alfred, Straight, Marshall, Township, Willow Lane) with Garrard Avenue, Rawson, Meeker and Johnson N-S; new E-W lines to be anchored on Camp Washington's own streets, not the west-bank ones | Ruled, drawn in 10z |

## 10z. West side of the valley, RER A drawn, Garrard moved, Exposition Boulevard (2026-10-13, deck/west_valley.py, deck/deck_gen.py, rera/rera.py, transit/build_transit.py, lph/add22.py; page version 26)

| # | Item | Result | Status |
|---|---|---|---|
| 10z.1 | Request (Ben) | "Do all of the things requested since the last artifact update": RER A as designed (10y), Exposition Boulevard, Garrard moved west, the west side of the valley filled from W 6th to Ralston east of State and Beekman (area 1 on the deck grid ending at the hill foot north of Liberty, area 2 on a grid like area 1 and Camp Washington's own lines north of the Palace, area 3 a full grid), the accepted defaults (Exposition grounds rebuilt on the grid, boulevard crossings, full grid in Millvale, midway street Hopkins to the hill) | Done |
| 10z.2 | Garrard | The fitted line moved 9.0 m west as a whole (a reduced by 9 m x sqrt(1 + b^2)); it meets the 1904 Garrard Avenue's south end 0.4 m off, and the Garrard line now runs on into it (0.9 m). The seam bends move with it (0.19 m at most); corners west of Garrard still median 0.01 deg, max 0.32 deg (York) | Done |
| 10z.3 | Exposition Boulevard | Feature, legend, selection and notes renamed; the deck is described as laid for the 1913 Exposition (Ben). Tracker 2J conflict still flagged, tracker not edited | Done |
| 10z.4 | RER A drawn (rera.py rewritten: KMZ RER-1a [3] + [2] read raw, not from the simplified page copy) | 135.9 m under CUT, 147.5 m at Evans, deck edge 148.4 m (s 1,225); boxed 60 m, walled ramp 3.3% to the fork at 159.3 m (712,364, 4,333,117). Westwood: 62.6 deg at 200 m (63.4 on the simplified line), 3.26% up, over State's foot at 162.5 m (8.8 m clear), platform at ground 168.9 m. Northside: viaduct from the fork, 165.2 m over Harrison's avenue, 168.2 m over Hopple (6.8 m), easing to 167.0 m at the RER D crossing (TRIMET 3D, 174.27 m, s 4,962), 167.0 m through South Cumminsville and Northside, 3.3% down from the Northside platform end (s 6,556) to 144.2 m at Linden (s 7,246), tunnel beyond (not profiled). Structure states from the map 3 ground: viaduct >= +5 m, box <= -4.6 m, ramp between. Page: viaduct dashed edges, ramp walls, under deck or boxed dotted, level marks | Done |
| 10z.5 | Portal rule applied (10j.7) | Exeter (rail 5.2 m under it) rides the box roof, the warning band, instead of being cut as in the 10y sketch; Linden over the box (5.9 m). Cut by RER A: Dayton, Bank, Dolph (deck), Chambers, Lingo, Dane (basin); every other crossing passes under or over | Done |
| 10z.6 | Area 1, Hopkins to Harrison | Kenner, Courtland, Flint, Wade, Wilstach, Sherman, Poplar, Findlay, York, Exeter and McRoberts cross the boulevard on its square to State (south of Liberty) or Wallace Street (north of it); Wallace = the 1904 Wallace from State to Saratoga carried along the hill foot (the deck strip's west edge, the 157 m contour) to State at Ernst. Hopkins carried from Summer to State, W Liberty to State; Summer, Berlin, Evans carried north to Wallace; New street W midway between Evans and the boulevard, Hopkins to Wallace. Dayton and Bank keep 86 m and 64 m stubs from Wallace to the ramp; Dolph's stub (56 m) is dropped and Dolph, Western and the strip north of Bank end at the boulevard (Ben: too short to build on) | Done |
| 10z.7 | Area 2, Harrison to Hopple | Queen City and Harrison's re-aligned avenue carried to their 1904 corners on Beekman; Tremont, Waverly, Knox carried east to Johnson. North of the Palace: Alfred (92.98), Straight (93.04), Marshall (93.13) from Garrard to Beekman on their own 1904 lines, replacing the deck's north-side T streets (Alfred meets Beekman at Fairmount); Township and Willow Lane carried west from their 1922 ends (41 m apart: one-lot blocks, as east of Garrard); New street N midway between Marshall and Township; Johnson (from Harrison), Rawson and Meeker (from Alfred) carried south on Garrard's bearing at their printed widths; New streets J1-J3 parallel to Johnson every 100 m toward Beekman (J4 dropped, within 80 m of Beekman) | Done |
| 10z.8 | Area 3, Hopple to Ralston | Stock to Earl and Whiteley (added; the sketch missed it) carried west on 93.6 deg to Beekman (OSM north of Hopple); Follett, Roll, Dawson, Borden carried south on their own bearings to Hopple or Beekman (the sketch's grid) | Done |
| 10z.9 | Rail cuts (new rule set) | Streets end where a line crosses within 6.8 m (6.5 m under the APEx viaduct, as ruled for it). APEx north approach: 151.8 m at the north tip, 0.94% to 164.5 m at Marshall; it cuts Township, Willow Lane, New street N, Johnson, Rawson, Meeker and the Garrard line (5.7 m, 70 m north of Marshall), and Stock, Ethan, Bates, Alabama between Hopple and the tip; Marshall passes (6.5 m). North of the tip the TRIMET trunk (151.7-153.2 m, 3D) and the APEx Vandalia/Norwood lines (KMZ, at grade) cut Monmouth to Whiteley; RER D (TRIMET 3D, 156.7 m at the tip) cuts Monmouth. Open corridors carry no blocks; no blocks under the Hopple viaduct | Done |
| 10z.10 | Basin layer | State Avenue (Gest to Harrison), the 1904 Harrison (State to Beekman), Beekman (1904 line; OSM north of Hopple), Cummings, Vinton and Denham stubs from the picked crossings (lph/wv_1904.json, set "wv", installed by add22); Chambers, Lingo, Dane cut at RER A (add22 rer_cut, from the profile) | Done |
| 10z.11 | Build | deck_gen: 91 streets, 276 blocks (153 off the deck, 123 on it); 22 cut marks on the deck, 3 in the basin. Rebuild order: rera.py, deck_gen.py, copy deck.json, lph_grid.py, add22.py --install, rera.py (crossings), build_transit.py, copy context.json | Done |
| 10z.12 | Found | The page's RER D (KMZ) leaves the trunk at the deck tip; the TRIMET 3D line, whose levels set the RER A crossing, runs up the trunk to Arlington (161 m) before turning west. The zone 3 cuts follow the 3D line; on the KMZ line Sassafras's west piece would lose about 100 m at its east end | Open |
| 10z.13 | Found | The Garrard line is cut by the APEx ramp 70 m north of Marshall (5.7 m < 6.5 m), so it meets Garrard Avenue only on the north side of the ramp; holding the viaduct level about 70 m further north (ramp 0.99%) would keep it | Open |

## 10za. North trunk viaduct, Ludlow to the deck (2026-10-13/14, nv/; built as page version 27)

| # | Item | Result | Status |
|---|---|---|---|
| 10za.1 | Request (Ben) | The north trunk is viaducted all the way from Ludlow Ave (check the topography); count the tracks from the RER and APEx/ORR lines coming from Dayton and Norwood; set the RER with it; decide the viaduct's width and where the tracks start and end | Open |
| 10za.2 | Canon read | ORR workbook Map Segments: APX-0 CUT-Camp Washington ~10-12 tracks (APEx, TRI and Transvalley, ORR); APX-1a Camp Washington-St. Bernard/Ivorydale east flank; the Dayton line and the Norwood corridor split at St. Bernard/Ivorydale (tenth set); R5 Hamilton by the west flank via Northside. KMZs: APEx Indianapolis (Greensburg-CUT TRIMET) leaves the trunk at Arlington (s 4,135 from CUT on the APEx line); TRIMET 3D Greensburg (RER D) at Adelaide (s 4,555), 163.7 m there; the page's RER D (Cincinnati Rail.kmz RER-4) at the deck tip; APEx Dayton/Norwood split at (715,547, 4,338,555) | Recorded |
| 10za.3 | Tracks | CUT trains v2 and 10l.2: north 7.5 Limiteds per knot window, 3.3 a track at 3 min, so APEx 3 + 3; Indianapolis 2.1 (1 + 1, leaves at Arlington); Dayton 1.8 + Norwood 3.6 = 5.4 (2 + 2 to St. Bernard); ORR 14 + Transvalley 6 an hour, two pairs; TRI B/D one pair, D leaves at Adelaide. 12 tracks at the deck tip | Proposed |
| 10za.4 | Profile (map 3) | Rails at ground at Ludlow (155.5 m, TRIMET level; Ludlow keeps its 10v.5 bridge), 0.75% up to the arch-viaduct level 190 m north of the deck tip (166.6 m = deck + 6.5), held at deck + 6.5 over the north lobe to Marshall (164.5 m, unchanged). Clearances: Millvale 7.0-11.9 m (Whiteley 7.4 at 0.75%), 1904 Colerain/Ford/Streng 6.9 m (0.66% would leave them 6.6-6.7), lobe streets 6.5 m (arch-viaduct rule). The APEx portal at the tip and the 0.94% lobe ramp go | Proposed |
| 10za.5 | RER B/D | Under the deck to the tip (151.8 m), box under Monmouth (7.7 m), open ramp 2.5% to the viaduct at Arlington (164 m), D leaves west at Adelaide on the TRIMET 3D line; B down with the viaduct to Ludlow. A dive between Alabama and Monmouth does not fit (176 m, 6.6%) | Proposed |
| 10za.6 | Width | Drawn spacing 4.5 m in a group, 6.75 m between groups; 4.75 m outer track to edge (working value from a 14 m double-track HSR deck at 4.5 m centres). Deck tip-Arlington: APEx 6 + ORR 4, 45.0 m between outer tracks, 54.5 m deck, B/D ramp beside; Arlington-Ludlow: APEx 4 + ORR 4 + B/D 2, 47.25 m, 56.8 m. The Indianapolis pair crosses over ORR W and the B/D ramp to leave west | Proposed |
| 10za.7 | Consequences | No APEx ramp void in the lobe: Township, Willow Lane, New street N, Johnson, Rawson, Meeker, Stock, Ethan, Bates, Alabama and the Garrard line pass under (Garrard reaches Garrard Avenue, 10z.13); Monmouth to Whiteley pass under; Hopple no longer has to clear the APEx and can cross the lobe at deck level (6.5 m, like Marshall); RER D moves to the TRIMET 3D line (10z.12, 10v.3) | Proposed |
| 10za.8 | Found | North of St. Bernard the Norwood line's 3.6 Limiteds per window exceed one track each way (3.3); the map 3 I-75 trench runs 20-80 m west of the APEx line north of Spring Grove Ave, so the width goes east there | Open |
| 10za.9 | Ben: TRIMET group on the east side | RER is at surface from Northside/Spring Grove north, so the tracks come down at Ludlow (option A); the APEx Indianapolis pair and TRI B/D share the TRIMET ROW, so they run on the east side (looking north) and D and the Indianapolis pair climb and fly over the APEx tracks. Layout (west to east): ORR W, APEx Dayton/Norwood 4, ORR E, APEx Indianapolis 2, TRI B/D 2. The Indianapolis pair moves east of ORR E over ORR E's dive between Exeter and Findlay (ORR E 6.8 m or more below it there), so no extra flyover at CUT | Proposed (v2 sketch) |
| 10za.10 | Error in the v1 sketch | B/D's 2.5% climb ran through the RER B Arlington station (KMZ point 250 m north of the deck tip); a 204 m platform cannot sit on it | Corrected in v2 |
| 10za.11 | v2 levels | Viaduct as 10za.4. B/D under Monmouth in a box (151.8 m), 2.5% to 163.0 m by s 4,351; Arlington moved about 350 m north (platform s 4,398-4,602, over Marquis and Adelaide), elevated at 163.0 m, B and D both calling; B 0.78% down to the surface at Ludlow (155.5 m), Northside/Spring Grove at surface (s 5,725); street clearances 7.0-10.3 m. D 3% from the station's north end to 169.2 m at Earl; the Indianapolis pair 1% from the deck tip to 173.8 m; both fly over ORR E, APEx and ORR W at Earl (viaduct 161.1 m) and follow the TRIMET 3D line west over RER A (174.3 m, as ruled). Widths: lobe 57 m (10 tracks), deck tip to Arlington 68 m (12), the station 78 m (11 m island), Earl to Ludlow 57 m (10). North of Ludlow B on the east side would cross the Norwood tracks at St. Bernard | Proposed |
| 10za.12 | Arlington (Ben: decide so the geometry works) | Arlington station: move north and elevate (recommended), keep it at the KMZ point in a box (B dips to 144 m under the 1904 Spring Grove Ave crossing), or keep it at surface (Sassafras to Whiteley cut at B) | Decided in 10za.18 (elevated, B only) |
| 10za.13 | Request (Ben) | Any arrangement, as long as the APEx, ORR/intercity and RER geometry works together; ORR must not cross the APEx Indianapolis pair. ORR Segments.kmz (statewide) available | Recorded |
| 10za.14 | ORR KMZ read | APX-0 runs CUT to the Arlington point; APX-1a carries on with the APEx line to St. Bernard; SW-10 "Cumminsville Spur" leaves at Arlington beside the Indianapolis and TRIMET D lines (on their north side) to South Cumminsville, then "Northside-Northgate" runs north. Workbook: SW-10 carries R5 only. 10l.4: the west lower pair is Transvalley (A-D), the east pair ORR/intercity (E-H); v2 called the west pair "ORR W" | Recorded |
| 10za.15 | Error (v1, v2) | The KMZ "Cincinnati-Camp Washington" piece starts at N 4,335,706.8, steps to 4,335,836.9 and jumps back south, so my chainage north of the deck tip ran about 260 m long. Rebuilt (profile.py): Ludlow s 5,300 (OSM; 1922 bridge s 5,368), Sassafras 4,062, Arlington St 4,136, Marquis 4,211, Adelaide 4,298, Brashears 4,413, Earl 4,549, Whiteley 4,635, 1904 Spring Grove 4,801, Ford 4,847 and 4,943, Colerain 4,929; St. Bernard split 8,666. On true chainage v2's B/D ramp passed 1.7 m over Sassafras, and the "350 m north" station was really 130-330 m north | Corrected in v3 |
| 10za.16 | v3 arrangement | Indianapolis leaves west, R5 has to end up on its north side, and the ORR/intercity pair is east of the APEx tracks at CUT, so ORR stays on the east throughout and the Indianapolis pair is the west APEx pair. West to east: Transvalley 2, Indianapolis 2, APEx Dayton/Norwood 4, ORR 2 (the lobe as built). Indianapolis then crosses only the Transvalley pair (not 6 tracks), B ends up west of the APEx tracks (the Norwood line leaves St. Bernard without crossing it), and B/D comes up in the slot Indianapolis leaves. Departs from Ben's east-side suggestion (10za.9) | Proposed (v3 sketch) |
| 10za.17 | v3 levels | APEx Dayton/Norwood + ORR: deck + 6.5 m to the tip (166.56 m), then a straight 0.787% to 155.5 m at Ludlow (s 5,300, 1,405 m); street clearance 7.0 m (Ford) to 13.4 m. Transvalley: 2% from the tip to 159.8 m (s 4,233), level to s 4,754 (Earl and Whiteley 6.9 m), then with the band. Indianapolis: 1.3% from s 3,800; over Transvalley s 4,081-4,130 (7.5 m); 174.3 m over RER A (7.3 m) | Proposed |
| 10za.18 | v3 TRI B/D | Under the deck at 151.8 m to Monmouth (cover 7.7 m); 3.3% open ramp in the slot to 163.0 m at s 4,242; Sassafras cut (rail 157.1 m over a 154.1 m street), Arlington St 8.2 m, Marquis 10.5 m. D splits at s 4,242 (flat junction), climbs on at 3.3%, 300 m curve, over Transvalley s 4,361-4,400 (7.2 m), joins the TRIMET D line at the RER A crossing at 174.3 m (as ruled) and crosses the I-75 trench (floor 141.4 m) there. Arlington, B only as in the KMZ: elevated at 163.0 m, s 4,300-4,504, over Adelaide and Brashears, Transvalley moved 10 m west along it; B 0.94% down to 155.5 m at Ludlow (streets 7.6-11.3 m). A box at the KMZ point was checked: D underground would have to bridge the I-75 trench at about 148 m and cut South Cumminsville streets beyond it | Proposed |
| 10za.19 | v3 R5 | Leaves the ORR pair on the east at s 4,300 (163.4 m, flat junction), 0.7% up to 167.0 m on its own deck, over the band, B and Transvalley s 4,822-4,951 (7.0 m or more), 250 m curves to SW-10 north of South Cumminsville, under RER A. Its stop, descent (about 15 m to grade) and street crossings west of the trunk are not set | Proposed (indicative) |
| 10za.20 | v3 widths | Lobe: 10 tracks, 45.0 m between outer tracks, 54.5 m (as built). Arlington station: Transvalley (-34.75/-30.25), B island (-23.5/-9.0), APEx 4 (-2.25 to 11.25), ORR (18/22.5): 57.25 m, about 66.75 m; R5 deck 14 m east of it. Ford to Ludlow and north at grade: Transvalley 2, B 2, APEx 4, ORR 2 = 4.5 + 6.75 + 4.5 + 6.75 + 13.5 + 6.75 + 4.5 = 47.25 m, 56.75 m. Viaduct from the deck tip (s 3,895) to Ludlow (s 5,300) | Proposed |
| 10za.21 | v3 open | Map 3 I-75 trench edge 26-28 m west of the APEx line at s 5,150-5,250 and 12-24 m at s 5,850-7,250: the band moves 5-7 m east from Ford and 10-20 m east north of Ludlow, east edge in a 5-7 m cut. St. Bernard: APEx Norwood crosses the ORR pair's Dayton-bound trains (X2). Flat junctions for D and R5. Sassafras cut (Ben). RER A's 167 m hold stays as ruled | Open |
| 10za.22 | Track count by segment (Ben: tracks between merges from traffic, by type) | APEx from CUT trains v2 (18-hour averages; Limiteds in the 10-min knot window, 3.3 a track at the 10l.2 3-min working headway): Norwood 5.0/h, knot 3.6; Dayton 3.8, knot 1.8; Indianapolis 5.2, knot 2.1. ORR north (workbook): X1, X2 30 min (15 at peak per the ridership flags), R1, R2, R3, R5, L71 hourly, L75 hourly (no workbook figure). X rides APEx track (155 mph APEx-shared; X2 alone on APX-4a with X-only loops at Middletown). TRI B 20-30 tph (May 2026 RER export, RER-2), D 6-10 (assumed). Need: Norwood-St. Bernard APEx 1+1 (knot 108% of 3.3) or 2+2, ORR 1+1 (5 tph); Dayton-St. Bernard APEx 1+1, TRI B 1+1, no ORR pair; St. Bernard-Arlington APEx 2+2 (knot 5.4, 81%), ORR 1+1 (5), TRI B 1+1; Arlington-CUT APEx 3+3 (knot 7.5, 75%), ORR 1+1 (6), TRI B/D 1+1 (26-40). Corrections to 10l.2: its ORR 14 counted L56, L74, R4 (APX-8a) and L73 (Oasis per its station sheet; the workbook's APX-0/1a/1b rows still list it), and Transvalley 6 was a placeholder (TV1-TV3 never use the trunk), so the second north lower pair has no canon traffic | Superseded by 10za.23 |
| 10za.23 | Ben's corrections and track count by merge | X does not use APEx track: APEx has its own tracks, ORR/intercity (X, R, L) its own pair, at the CUT lower level. Four merges: Ivorydale (APEx, ORR), Winton Place (Transvalley; the TRIMET Oxford line's exit at s 7,885; my "Transvalley stays off the trunk" was wrong), R5's ROW, RER D/APEx Indianapolis (s 4,135-4,295). Pairs, trains an hour each way: APEx Norwood 5.0 (knot 3.6, 108% of one track), Dayton 3.8 (1.8), Ivorydale-Arlington 8.8 (5.4, 81% of two), into CUT 14.0 (7.5, 75% of three); ORR Norwood side 7 (9 peak), Dayton side X2 2 (4), Ivorydale-CUT 9 (13); Transvalley 6 (10l.2 placeholder, no canon figure) + R5 1 = 7 on the west pair (35% of a track), so R5 joins on the west side and v3's R5 flyover goes; TRI B 20-30, B+D 26-40. Ben: a 3-track section (MBTA Southwest Corridor) is an option. It fits where the two directions bunch at different times: APEx Norwood (Limited arrivals :50-:00 and departures :15-:25, the other direction carrying 1.4 an hour), ORR (CUT terminal pulse), TRI B/D peak direction; not APEx Ivorydale-Arlington (the opposite :30 wave puts 3.5 on one track, 106%) or into CUT. Count: Norwood side 5 (APEx 3, ORR 2); Dayton side 6 (APEx 2, ORR 2, TRI 2); Ivorydale-Winton Place 8 (APEx 4, ORR 2, TRI 2); Winton Place-Indianapolis 10 (+ Transvalley/R5 2); into CUT 12 (APEx 6, ORR 2, Transvalley/R5 2, TRI 2), 14 with third tracks on ORR and TRI. Indianapolis and D still leave across the west pair, now with R5 on it | Proposed |
| 10za.24 | Ben's ruling restated; R5 on the left | The ruling is about keeping APEx Indianapolis and RER D together as they cross west to the tunnel: the order cannot change from [ORR E][Indianapolis][RER D] to [Indianapolis][ORR E][RER B/D], since Indianapolis and ORR would have to cross at grade. A grade-separated crossing over other tracks is fine (I had read it as "never cross ORR"). With R5 on the left (west) pair it stays on the viaduct at the CUT-approach level and only has to clear RER A. Arrangement, west to east: Transvalley/R5, APEx Dayton/Norwood 4, APEx Indianapolis (the east APEx pair, as at CUT), TRI B/D (out from under the deck between them), ORR E (moved 11.25 m east). Indianapolis (1.3% from s 3,800, 174.3 m by s 4,407) and D (3.3% from the deck tip, splitting from B at s 4,242) cross west together over APEx Dayton/Norwood and Transvalley/R5 at s 4,429-4,608 on a 600 m curve (D 169.2 m over a 162.4 m band at the start), then on to RER A at 174.3 m. R5 leaves the west pair north of that at about the band level (160.2 m at s 4,700, 6.8 m under RER A's 167.0 m). North of the crossing: Transvalley, APEx 4, B, ORR E (10 tracks, 47.25 m, 56.75 m); south of it 12 tracks, 56.25 m, 65.75 m. Consequence at Ivorydale: B and ORR are east of APEx, so APEx Norwood crosses B and the Dayton-bound ORR (X2) there | Proposed |
| 10za.25 | Arlington (Ben: on the east side of the viaduct with the RER tracks, close to the KMZ point, centred on Arlington) | Centred on the KMZ point (s 4,146) it has to be a box: B comes out from under the deck at 151.8 m 243 m south of it and cannot get over Sassafras (s 4,062) or Arlington St. B and D split under the deck at about s 3,700 (flat junction, D on the west of the pair); B drops 1.7% to 145.8 m by s 4,053: box station s 4,044-4,248 under the east side of the viaduct, cover 8.3 m at Sassafras, 5.5 m at Arlington St, 5.7 m at Marquis; B stays boxed (143.9 m under the 1904 Spring Grove Ave, cover 5.3 m), then 2.3% up from Ford (s 4,943) to 155.5 m at s 5,350, in the slot east of APEx that Indianapolis leaves, to Northside/Spring Grove at surface. D holds 151.8 m to the deck tip, then 3.3% up beside Indianapolis (Sassafras cut by D's ramp: 157.0 m over a 154.1 m street; Arlington St 8.2 m) to the grouped crossing at s 4,429-4,608 | Superseded by 10za.26 |
| 10za.26 | Elevated Arlington, no street cut (Ben: it is all a viaduct, Ludlow to CUT; why can it not get over the streets) | The viaduct carries APEx, ORR and Transvalley; TRI B/D run at grade under the deck's north lobe (Ben, 10r.14), so they leave the deck tip at the old ground level, about 15 m under the viaduct, 159 m short of Sassafras. Fix: B/D rise 0.46% under the deck to the slab limit (152.7 m at the tip; Monmouth cover 6.5 m), climb 3.3% to 158.5 m at s 4,071; Sassafras lowered 2.7 m where it passes under (rail 158.2 m), within the 3 m re-grade precedent (10l.28, 10l.30); Arlington elevated on the east side at 158.5 m, s 4,071-4,275, centred 27 m north of the KMZ point (Arlington St 7.2 m, Marquis 7.0 m). B then 0.7% to 159.8 m (Adelaide 7.0 m, Brashears 7.4 m), level to s 4,754 (Earl and Whiteley 6.9 m), then down with the band to 155.5 m at Ludlow (Colerain 7.1 m, Ford 7.0 m). D splits at the station's south end, climbs 3.3% past its west side and clears the band by 6.8 m from s 4,401 (169.4 m over 162.6 m). Deck about 87 m along the station while D runs beside it | Superseded by 10za.30 |
| 10za.27 | Indianapolis grade (Ben: the Indianapolis pair can split earlier if it needs a shallower climb) | Not needed: the crossing point is set by D (3.3% out from under the deck, clear of the band from s 4,401). Indianapolis can ease from 1.3% to 0.75% from s 3,800: 170.9 m at s 4,401 (8.3 m over the band), 174.6 m at RER A (7.6 m over 167.0 m), and then sits within 1.5 m of D (169.4 m) at the start of the crossing, so the two pairs can share one deck | Superseded by 10za.30 |
| 10za.28 | B/D climb linked from Camp Washington to the crossover (Ben) | One continuous climb in two grades: from the Camp Washington platform end (s 3,168, 151.4 m) 0.40% in the box under the deck to 154.3 m under Monmouth (s 3,903; covers Hopple 7.5 m at deck level, Stock 6.7, Ethan 6.5, Bates 6.3, Alabama 6.2, Monmouth 5.2), then 3.0% from the deck edge to 158.5 m at s 4,043. A single grade from Camp Washington cannot work: under Monmouth it must be 0.42% or less, over Sassafras 1.1% or more. Arlington (B) elevated at 158.5 m, s 4,043-4,247, centred on the KMZ point (s 4,145), on the east side; Sassafras lowered 2.4 m (to 151.7 m), Arlington St 7.2 m, Marquis 7.0 m; B then 0.4% to 159.8 m, level to s 4,754, down with the band to Ludlow (streets 6.8-11.0 m). D goes on at 3.0% from the station's south end past its west side; Indianapolis 0.75% from s 3,800 clears the band by 6.8 m at s 4,302, where the pair start west on a 600 m curve; D is over APEx Dayton/Norwood from s 4,418 (169.8 m against 169.2 m needed, Indianapolis 171.0 m), the pair share one deck (171.4 and 171.3 m at s 4,470), clear Transvalley/R5 at s 4,551, D at 174.3 m from s 4,570. Sketch nv/North_Trunk_v4_long_section.png (nv/v4.py, sketch4.py) | Superseded by 10za.30 |
| 10za.29 | One viaduct for Indianapolis and D (Ben: same path, why two viaducts) | My 10za.27/28 gave them separate structures until s 4,418; corrected. Indianapolis stays in the band (deck + 6.5 m, then 0.79% down) until D, climbing 3.0% alone beside the Arlington platforms from s 4,043, reaches its level: 164.0 m at s 4,226. From there one 4-track viaduct (Indianapolis + D) climbs 2.5% (APEx preferred 2.0-2.5%, maximum 3.0%, per the April 2026 stations export) to 174.3 m by s 4,639, starts west on the 600 m curve at s 4,432 (169.1 m, 6.8 m over the band), has D's tracks over APEx Dayton/Norwood from s 4,536 and is clear of Transvalley/R5 at s 4,682, then on over RER A to the tunnel. D cannot join sooner: it is held in the box at 154.3 m under Monmouth by the deck streets, 12 m below the band at the tip. Sketch nv/North_Trunk_v4b_long_section.png | Superseded by 10za.30 (the shared deck is kept) |
| 10za.30 | Every path on one viaduct; Camp Washington elevated (Ben: why are the paths not travelling together, why is Camp Washington below ground; the RER only has to dive earlier than the others to reach Straight; APEx/ORR are viaducted from CUT to Ludlow, whose bridge goes over the tracks) | Camp Washington was low only because I held 10r.14's "at grade to Camp Washington" as the old ground under the deck slab, with the TRIMET KMZ level (151.3 m). Now (west to east): Transvalley/R5, APEx Dayton/Norwood 4, APEx Indianapolis 2, TRI B/D 2, ORR E 2, all on the viaduct from Ludlow (155.5 m, s 5,300) to Camp Washington. Camp Washington (B, D) elevated at the band level, 165.1-165.4 m, s 2,964-3,168 (canon chainage s 3,066; island centred 25 m east of the canon point), Hopple and Johnson under it at 6.5 m. B/D dive 3.3% from the platform's south end to 151.64 m at s 2,556, level 153 m into Straight (s 2,403): ramp above the deck s 2,758-2,964, open trough s 2,594-2,758, box (dug) from s 2,594, Marshall cover 6.4 m; B/D curves back onto the KMZ line under the APEx tracks (about 1,550 m radius) once 6.8 m below them (s 2,758), and ORR E swings back over it to its as-built line by Marshall. Streets at the dive: Garrard line raised 1.9 m onto the box roof (keeps the 10z.13 link to Garrard Ave); Rawson and Willow Lane lowered 1.2 and 1.4 m (they meet at the B/D line) and Township 2.8 m to pass under the ramp; Meeker and New street N end at the dive. D leaves B by a flat junction between s 3,168 and 3,644 (D on the west, beside Indianapolis). Indianapolis + D on one deck leave the band at s 3,644 (166.1 m), 2.5% to 174.3 m by s 3,971, 6.8 m over the band at the KMZ curve start (s 3,924, about 745 m radius, fitted), clear of Transvalley/R5 at s 4,202, 7.3 m over RER A (167.0 m, as ruled) about 950 m along the curve. Arlington (B) on the east side, s 4,044-4,248, centred on the KMZ point, platform level 164.6 m (band 165.4-163.8; B 1.33% in from the tip, back on the band at s 4,397), streets under it 10.5-13.3 m. B with the band to Ludlow, streets 7.0-12.2 m; lobe streets 6.5 m. Gone from v4b: the box under the lobe, the Monmouth cover limit, the Sassafras re-grade, D's solo climb, the 87 m Arlington section. Widths: Camp Washington to Arlington 66.25 m between outer tracks, deck 75.75 m (-27.25 to +48.5 m; ORR E at 39.25/43.75), up to 12 m past the deck's east edge at s 2,850-3,350 over Camp Washington blocks at deck level; north of Arlington B and ORR E move west into the slot the Indianapolis pair left: 10 tracks, 47.25 m, 56.75 m. Replaces 10r.14's construction with: elevated to Camp Washington, dug to Straight, bored from Straight. Sketch nv/North_Trunk_v5_long_section.png (nv/v5.py, sketch5.py) | Proposed |
| 10za.31 | B/D traffic (Ben: how does the traffic work; does B/D need quad tracking) | B alone north of the D junction: 20-30 tph (May 2026 RER export, every 2-3 min), 50-75% of canon's 90 s TRI minimum (40 tph, tracker 2M). Shared D junction to CUT (Camp Washington, Straight, Western): B + D 20 + 6 = 26 to 30 + 10 = 40 tph, 65-100%. The limit is v5's flat junction (northbound D across southbound B at grade). Fix in the climb D already makes: southbound D on the west of B, northbound D on the east, neither crossing B at grade; northbound D climbs 2.5% with the Indianapolis + D deck from s 3,644, 6.8 m over B by s 3,924, crosses over B in the turn west; deck 77.0 m for about 350 m (v5 75.75 m). Then plain double track: at about 85% of 40 (my working value), about 34 tph, so B every 2.5 min + D every 7.5 min (24 + 8 = 32) fits and B 2 min + D 6 min (40) does not. Quad helps only if it runs into the CUT box (Camp Washington, the dive, Straight, a second bore through Western, the box's west throat, 10r.10-14); quad on the viaduct gains nothing (B alone); a third track does not fit (B and D through-run, equal frequency both ways; the two-track bore still caps it). East of CUT D shares A's tracks to City Hall (10r.10), so D's frequency is also capped by A's 90 s trunk | Decided in 10za.32 |
| 10za.32 | B/D peak service and the D junction (Ben: peak 4 min for B, 8 min for D on the same two tracks from Camp Washington to CUT; the B-D branching is a flyover) | B 60 / 4 = 15 tph, D 60 / 8 = 7.5, shared Camp Washington-CUT 15 + 7.5 = 22.5 tph each way, 56% of canon's 90 s minimum (40); with B held to every 4 min and D between alternate B pairs, the gaps run 2, 2, 4 min (least 120 s against 90). North of the junction B alone, 15 tph (37.5%). Replaces B 20-30 and B+D 26-40 (10za.22, .23, .31; the May 2026 export's 2-3 min for RER-2); TRI stays one pair into CUT, no third track (10za.23's count of 14 with third tracks drops to 12 plus any ORR third track). Flyover: southbound D west of B, merging into B's southbound track; northbound D peels off B's northbound track on the east and climbs 2.5% with the Indianapolis + D deck from s 3,644, 6.8 m over B by s 3,924, crossing over B in the turn west; s 3,800 section: Transvalley/R5, APEx Dayton/Norwood 4, Indianapolis 6.75/11.25 + southbound D 15.75 (climbing), B 22.5/27.0, northbound D 33.75 (climbing), ORR E 40.5/45.0: 67.5 m, deck 77.0 m for about 350 m (v5 75.75 m). Still open: D's 7.5 tph east of CUT on A's tracks to City Hall (10r.10) against A's 90 s trunk; B's peak load against 15 tph not checked (ridership workbook not in this session). Sketch nv/North_Trunk_v5_long_section.png redrawn | Ruled |
| 10za.33 | Capacity check (Ben: B every 4 min, D every 8 min on one pair, Camp Washington to CUT; build if it checks out) | Ridership model v17 workbook (Lines sheet) gives each line's busiest AM peak-hour stretch only: TRI B 28,669 (Covington Union to Rivercenter), TRI D 28,476 (Mansion Hill to Pennsylvania), both off the Mill Creek section, so B there is under 28,669; D's northwest branch, scaled from its stations' entries, about 9,900-16,400 (rough). Canon gives no TRI seat count except the Dec 2025 export's generic 1,000-1,200 a train; Paris MI 09 holds about 1,300 per 112 m unit, 2,600 coupled (Wikipedia), so about 2,300 for a 200 m train (scaled). B 15 x 2,300 = 34,500/h against 28,669 at most (83%); D 7.5 x 2,300 = 17,250 against 9,900-16,400 (57-94%). Checks out on the trunk. Flags: the export's 1,000-1,200 a train would fail (B 18,000/h); D's busiest stretch east of CUT needs about 12 trains an hour (28,476 / 2,300 = 12.4), so about 5 extra D trains start at CUT eastbound on A's tracks | Recorded |
| 10za.34 | Built: page version 27 (2026-10-14) | cut/tracks_gen4.py (from v3; backup deckpage/tracks_v26.json): trunk NT = the page's CN from the deck tip south + the KMZ line north to Ludlow (s 5,420), smoothed at the KMZ corner near s 4,600; APEx Dayton/Norwood and Transvalley/R5 from Ludlow; the Indianapolis pair on the KMZ curve (offset curve, 745 m) to the plan's west edge; ORR E 18/22.5 at Marshall to 40.5/45.0 from Camp Washington to Arlington, 20.25/24.75 north of it; R5 off the west pair at s 4,150 onto the SW-10 Cumminsville Spur and Northside-Northgate (levels not set); markers for Ludlow, the tip, Hopple, the Indianapolis + D climb; the deck-tip portal marker and ramp summary removed (tracks.summary.north). Fix found: STR_G kept the last piece of a street name, so Bank's west-side stub broke the lower-pair dive lookup; it now keeps the piece across the trunk (CS at Gest 144.8 to 144.9 m from the same fix). nv/geom27.py: shared plan geometry and levels (band, bd_z, b_z, sh_z, tracks by chainage, tri_centre, bd_tracks, d_centre). transit/build_transit.py (backup _v26): B/D north of s 2,460 replaced (blend onto +20.25 by s 2,758, Camp Washington island 18/32.5, split at s 3,250), B to Ludlow (Arlington island 18/32.5, then 9/13.5), D southbound west of B and northbound east of it, then with the Indianapolis pair to the west edge (the KMZ RER-4 D piece removed); stations Camp Washington and Arlington moved onto the new line (25 m east of the KMZ points); rer_struct for B/D (box, ramp, viaduct), B and D; rer_marks. North of Ludlow the KMZ B line is kept (at-grade layout not set; B leaves the viaduct 11 m east of it). deck/west_valley.py (backup _v26): bars = the viaduct band (6.5 m), TRI B/D centre with its profile (6.5 m, box rule, re-grade up to 3 m with the worst rail level under the street's width), the Indianapolis + D viaduct, R5 (indicative 0.4% down); APEx KMZ cut only north of Ludlow; voids: RER A ramps and B/D's trough and ramp (s 2,594-2,964); the lobe and Millvale corridor and the Hopple void dropped (blocks fill under the viaduct, as under the arch viaduct south of Marshall). Result: New street N and Meeker end at the dive; Township lowered 2.8 m, Rawson 1.2 m, Garrard line raised 1.8 m (10za.30's 1.9 was a hand estimate; Willow Lane does not reach the B/D line on the page). Streets 91 to 78 and blocks 276 to 256 as cut pieces rejoin (block area 2.88 to 2.98 km2). deck_gen.py (backup _v16): wv_regrade layer. lph/add22.py (backup _v26): Hopple at deck level (structure 'deck level', note rewritten); rera.py (backup _v26) selects Hopple by set and labels 'over Hopple, rail 168.2 m' (profile unchanged). Page (backup index_v26.html): track summary (north viaduct, Indianapolis + D), north trunk note, west-side cut sentence, re-grade diamonds and legend, rail_open text. Screens lph/shots28. Published version 27 | Built |

## 10zb. Page editor: curves, Metro and RER lines, stations, more block types (2026-10-14, deckpage/index.html, transit/build_transit.py; page version 28)

| # | Item | Result | Status |
|---|---|---|---|
| 10zb.1 | Request (Ben) | Curves on street centre lines (the Harrison extension came out choppy with straight runs between points); Metro and RER centre lines and platforms editable like streets (Westwood's RER platform, Line 5 off Spring Grove Ave's centre), not fixed by Claude; more block types (towers like Carew, landmarks like Music Hall). Added mid-task: island or side platforms per station, platforms slid up or down the line while still reaching the station point, and deleting a station | Recorded |
| 10zb.2 | Curves | Every segment of a street or line can bend as a quadratic curve: a round handle at its middle, dragged to bend (control point 2m - (a+b)/2), double-click a filled handle to straighten. Double-click on a curve inserts a point and splits it exactly (de Casteljau); removing a point between curves leaves one curve through it. Smooth curve (tangents at the points bisected, each segment scaled by its own length; Line 5 grows 10 m on 11.9 km) and Straighten buttons | Built |
| 10zb.3 | Metro and RER lines | The 18 Metro and 21 RER centre lines are their own selectable, editable features, with stable ids from build_transit (prefix, line, first point). A line edited, or with a station on it changed, hides its generated tracks and draws a pair along the centre line (RER 2.25 m, twin tubes 4.0 m, bores 1.95 m each side), opened out round island platforms with 40 m tapers | Built |
| 10zb.4 | Stations | 172 station points (135 Metro, 37 RER); platforms grouped by station and line, 222 with a line, the Union Terminal RER box fixed. Per line at a station: island or side; centre slid along the line (slider or drag), at most half a platform from the station point so it always reaches it; delete and restore. Lengths canon (500 and 670 ft). Widths are drawing values: island 8.0 m Metro and 11.0 m RER and side 4.0 m Metro as generated; side 6.0 m RER new (not canon). Generated platforms are straight chords whose corners sit within 0.8 m of their lines, so they are redrawn centred, bent with the line | Built |
| 10zb.5 | Found | 8 generated platforms sit more than half a platform from their station point: Fountain Square L2 139 m, Mill Creek RER E 136, Elsinore L10 112, Burnet East L9 111, Forest L13 101, McAlpin L13 81, Wilstach L10 80, St Bernard L3 78. They keep that place until moved; moving one brings it within reach | Open (Ben) |
| 10zb.6 | Blocks | 11 types (building, tower, landmark, civic, worship, school, hospital, industrial, square, park, planting) and an optional name drawn on the plan | Built |
| 10zb.7 | Picking | A click lists everything under the pointer (station dots and platforms, lines by distance, areas, the block); clicking again steps through them; Also here buttons; Escape clears. In Edit mode a click keeps the selected line (so double-clicks land) unless it hits a station dot | Built |
| 10zb.8 | Saving | deck/layout gains transit {id: {c, k}} and stations {key: {del, s: {line id: {t, o}}}}; streets gain k; a block may be {t, n}. Ben's saved edits (9 streets, 3 blocks, doc version 54) read unchanged. The page writes the whole doc, so an older copy left open would save without the new keys. GeoJSON and KMZ exports add the lines, stations and platforms | Built |
| 10zb.9 | Checks | Playwright on the local copy (no db): Westwood platform slid 61 m, set to side, deleted; Perin bent, split, merged, straightened; a Line 5 point moved and the line smoothed; a block set to tower and named; Camp Washington (L5 island, L9 side), Union Terminal (fixed box) and Kirby (no platforms) panels; exports run; no page errors. Published as version 28 with context.json carrying the ids | Done |
| 10zb.10 | Undo and redo (Ben) | Undo and Redo buttons in the toolbar, Ctrl/Cmd+Z and Ctrl/Cmd+Shift+Z (or Ctrl+Y): one step per finished change (a drag, a click, a field, a reset, Reset all), up to 200 steps, kept for the visit (not saved); an undo is saved like any edit. Tested: drag, side, two undos, one redo; toolbar fits at 390 px. Version 29 | Built |
| 10zb.11 | Direction lock (Ben: extend New street W in line with the grid) | Holding Ctrl (Cmd on a Mac) while dragging a point keeps it on the line's own direction (the tangent of the segment ending there; at a middle point, whichever of its two segments the drag follows), so the line only lengthens or shortens; a dashed guide and a signed length readout show while held; letting go of Ctrl frees the point. The canvas no longer opens the context menu (Ctrl+click on a Mac). Tested on New street W: an off-axis drag lengthened it 82.4 m along its own line (1,029 to 1,112 m). Version 30 | Built |

## 10zc. North trunk straight between Ethan and Brashears, centred between New streets J1 and J2 (2026-10-15, nv/geom27.py; page version 31)

| # | Item | Result | Status |
|---|---|---|---|
| 10zc.1 | Request (Ben) | Centre the viaduct between New streets J1 and J2 (as he extended them on the page, deck/layout doc version 150: J1 to N 4,336,296, J2 to 4,336,455, J3 to 4,336,635); straight between Brashears and Ethan, curved to the next stages beyond | Recorded |
| 10zc.2 | Geometry | J1 and J2 run 3.36 degrees east of north, 99.9 m apart (centre lines), 18.3 m wide. The viaduct's outer tracks (Transvalley -22.5 to ORR E +45.0 east of NT) are centred on the midline, so NT runs 11.25 m west of it, straight from Ethan's south edge (N 4,335,248) to Brashears' north edge (N 4,336,099), 853 m. Structure 67.5 m between outer tracks + 4.75 m each side = 77.0 m in an 81.6 m gap: 2.3 m from each street | Built |
| 10zc.3 | Curves | Cubic curves tangent at both ends, handles chosen for the largest least radius: south from Ethan to Camp Washington's north platform end (s 3,168), least radius 435 m (was about 350 m); north from Brashears to s 4,950 on the descent to Ludlow, 740 m (was 290 m at the KMZ corner). Camp Washington's platforms and everything south of s 3,168, and north of s 4,950, are unchanged. Chainage between the joins is by length along the new line (projection onto the KMZ line jumped up to 7.8 m at its corner) | Built |
| 10zc.4 | Track changes | ORR E moves in (40.5/45.0 to 20.25/24.75) from s 4,430 to 4,780, north of Brashears, instead of 4,248 to 4,600, so the viaduct keeps its full width (and its centre) from Ethan to Brashears. The Indianapolis + D pair now eases off the trunk onto the KMZ curve (the trunk is 13.5 m east of the KMZ line at the curve start), least radius about 480 m (was 570-650 m). Arlington (B) island stays on the straight. Indianapolis/D and R5 leave west across J2 on their own decks | Built |
| 10zc.5 | Consequences | The block between J1 and J2 from Ethan to Brashears is the viaduct; J1 passes under it between Hopple and Ethan and at its north end past Brashears. Rebuilt the full chain; deck streets unchanged, six deck blocks changed by under 10 m2 (resampling), basin unchanged; one RER piece id changed (B/D from Hopple, R-BD-712316-4334957), not used by any saved edit; Ben's saved line and station edits all still match | Done |

## 10zd. Line 8 smoothed at Melindy and the old Ziegler turn (2026-10-15, l8/l8fix.py; a page edit, deck/layout version 169)

| # | Item | Result | Status |
|---|---|---|---|
| 10zd.1 | Request (Ben) | The Line 8 turn where Ziegler was (Ben deleted the station) is jagged: make it constant radius with no straight pieces in the curve; Melindy's L8 platform sits on two corners instead of a smooth curve | Recorded |
| 10zd.2 | Found | The KMZ line turns 89.3 degrees (bearing 167.5 to 256.9) through five corners within about 100 m (tightest about 20 m measured over 20 m), and bends 16.7 degrees left in two corners 37.5 m apart inside Melindy's platform | Recorded |
| 10zd.3 | Melindy | One 750 m radius curve between the Mt Auburn straight (184.3) and the straight south of Melindy (167.5); the whole platform is on it (offset of its 152 m chord 3.9 m). Largest radius that still leaves a straight before the turn | Done |
| 10zd.4 | Turn | One 180 m radius curve, 89.3 degrees, from 21 m south of the Melindy curve to East 13th Street, ending 8 m short of 13th's L8 platform (its east end limits the radius: the full 13th platform kept on the straight). It runs under the corner blocks between Woodward Street and East 13th instead of following the street corner. Drawn as quadratic pieces of 15 degrees or less (radius within 5% along it) | Done |
| 10zd.5 | Applied | As Ben's page edit of M-L8-712614-4337421 (written to deck/layout pinned to version 168; his other edits unchanged), so he can adjust it. Line 8 is now drawn from settings: tracks as a pair along the line and every L8 platform along it. Line 8 is 55 m shorter | Done |

## 10ze. Constant-radius curves on every Metro and RER line, from their own points (2026-10-15, arcs/fitarcs.py, arcs/fitarcs.js, transit/build_transit.py; page version 32)

| # | Item | Result | Status |
|---|---|---|---|
| 10ze.1 | Request (Ben) | All curved lines, not just Line 8: "the points give the radius of the circle, the lines should adapt to it"; RER B's curve between Music Hall and Fountain Square too. Not a minimum-radius rule (option B declined) | Recorded |
| 10ze.2 | Method | Doubled clicks (a piece under 12 m and under 0.3 of its neighbours) merged. Corner points turning the same way, under 150 m apart, make one curve. Three or more points: the circle fitted to them (least squares) if they sit on it within 0.6% of the radius (1 m at least), else the best split into two to four touching circles (a compound curve), else one circle within 2.5%. One or two points: the curve between the straights either side, radius fitted to the two points, or for a lone corner the largest that fits (each straight shared half and half). The straights become the common tangents of their curves; a line end on its first curve starts on it. A curve that cannot join, sweeps the wrong way, turns a straight more than 25 degrees, or strays from the drawn line (points 8 m, between points 12 m, a lone corner 20 m, straights 8 m) falls back to the curve between its straights, then shrinks, then stays a corner. Curves drawn as quadratic pieces of 15 degrees or less | Built |
| 10ze.3 | Generated lines | build_transit fits the 18 Metro lines and the KMZ RER pieces (32 lines, 692 curves); the designed B/D pieces (v27) are left as built. Tracks and platforms follow the fitted lines; ids stay on the drawn lines; RER A's structure bands follow the fitted line. The page gets each line as points plus a control point per curved piece, so editing a line keeps its curves. Largest departure from the drawn lines about 15 m (lone corners rounded); 3 corners stay sharp | Built |
| 10ze.4 | RER B, Music Hall to Fountain Square | One 335 m curve (14 points) from West 13th Street south toward Fountain Square, and a 966 m curve west of Music Hall | Built |
| 10ze.5 | Ben's edited lines | Line 3, Line 5, RER A trunk and RER A Westwood refitted from his own points; any piece he had bent more than 5 m off straight adds points along it (every 60 m or so) so the fit keeps it. Line 3: 85 curves, tightest 63 m, within 4.2 m of his line; Line 5: 39, 47 m, 4.1 m; Westwood: 13, 200 m (the designed curve kept as one circle), 1.7 m; RER A trunk: 22, 326 m, 5.6 m. Line 8 kept as 10zd. His previous edits saved in arcs/ben_transit_before_fit_v169.json. Written pinned to version 169 (now 170) | Done |
| 10ze.6 | Page | Fit curves (replaces Smooth curve) on any street or line runs the same rules in the page (JavaScript port, identical on all 39 lines); the selected line shows R labels on its curves; the panel gives the number of curves, the tightest and the radii along the line. Tested on Harrison Avenue's 13-point edit | Built |
| 10ze.7 | Found | The points give some very tight curves: 104 curve pieces under 100 m and 41 under 60 m on the page (Line 1 12, Line 10 11, Line 2 6, Line 5 3, Line 12 3, Line 3 2, RER A 2, Line 6 1, RER B 1), where the KMZ points hug street corners. Tightest: RER B 23 m at the Ludlow end of its KMZ piece (the 11 m step to the v27 B line, open since 10za), Line 10 24-25 m at its east end, Line 12 28-31 m | Open (Ben) |

## 10zf. Plots and land use on every block, following the streets live (2026-10-15, plots/; page version 33)

| # | Item | Result | Status |
|---|---|---|---|
| 10zf.1 | Request (Ben) | Subdivide every block into its plots, keep block-wide editing, add land use (residential, commercial, industrial, mixed use and so on), prefill only where the sheet says it plainly (garage, company: commercial or industrial; church: religious), no research into each plot; the deck at the basin's density; plots can be split and merged; streets and plots change together live (a street through a plot makes two plots, moved away they merge). Follow-up: the hybrid of measured and snapped; unlabelled = not set; open land can be filled by hand and blocks stretch and join | Recorded |
| 10zf.2 | Plots (plots/frontage.py, gen.py, run_all.py, build_plots.py) | Each block face classed every metre as street front (main street within half its width + 3 m), open area or alley. The longest face and those parallel or opposite to it (0.4 of its length and within 35 degrees, or 0.8 and within 60) front the lots; the block is split between them by a Voronoi of their sample points. Lot width per face measured from the sheet's lot lines (line strength 2-14 m into the block, autocorrelation 4.5-20 m, r 0.22 or more), cuts square to the street, each moved onto the nearest printed line within 2.5 m; no clear repeat: even widths. Zones deeper than 60 m are cut at 40 m and the rest left as interior plots (about 40 m grid). Slivers under 30 m2 and interior pieces under 400 m2 merged. Open blocks (park, square, planting) one plot each. 1,526 blocks, 35,611 plots (34,777 lots, 784 interior, 51 open), clipped to their blocks (47 invalid rings fixed); plots cover each block to within 0.4% | Built |
| 10zf.3 | Uses from the sheets | Tesseract read too little (rotated text lost). 534 crops of 190 m at 4 px/m with a 25 m grid (plots/crops) read by 18 vision agents against plots/labels/INSTRUCTIONS.md: every use or business label inside each crop's 150 m core, with its class (religious, civic, commercial, industrial) and position. 5,809 labels; private garages and "Auto" sheds behind dwellings dropped, "Auto Parking" as parking; 5,679 after de-duplication across crop edges; 4,796 inside a plot, 278 within 5 m, 605 on streets or yards. 4,227 plots prefilled (industrial 2,171, commercial 1,647, civic 263, religious 134, parking 12); a plot with several kinds takes the commonest, ties to religious, civic, industrial, commercial. Some sheets are later revisions (filling stations, garages, a 1928 building), read as printed | Built |
| 10zf.4 | Use order | A plot's own setting, else its parent's (X~a and X.2 fall back to X), else the block's (Set every plot), else the sheet label, else the block type (worship: religious; civic, school, hospital: civic; industrial; square, park, planting: open), else not set. Classes: residential, mixed use, commercial, industrial, religious, civic, parking, open or vacant, not set | Built |
| 10zf.5 | Live streets (page, JSTS 2.12.1 from jsdelivr) | A street whose points or width differ from the generated layer: its new corridor (flat ends, mitred bends in the basin, round on the deck) cuts the plots (pieces X, X~a, X~b; the largest keeps the id and its settings), and its old corridor less every current corridor and open area is vacated; the plots that front it take the strip out to the old centre line (frontage edges within 0.9 m of the old half width, swept square to the centre line). Strips under 0.6 m and cuts thinner than 0.5 m are ignored (a street redrawn a few cm off). Land no plot takes is open land, hatched. Blocks are the generated block less the new corridors plus the land their plots took; blocks that now touch join; a block cut through becomes B, B~a. Corridors cut into 60 m tiles fingerprinted to 1 cm, so a moved street only recomputes the tiles it changed. Overlays fall back to cleaned inputs, a 1 mm grid, then enhanced precision (JSTS threw non-noded intersections on the raw inputs). Plots rebuild when a drag is let go | Built |
| 10zf.6 | With Ben's edits (deck/layout version 298, 31 changed streets) | 35,560 plots, 113 blocks redrawn, 14 joined groups (Gulow's old line in Northside: three blocks one; Horne line and the LPH extensions across the old yards; W 8th narrowed from 33.5 to 18 m), 11 pieces of open land (largest 2,366 m2 on Ludlow's old viaduct line). First rebuild about 4.5 s in headless Chromium (the page shows the generated plots meanwhile); a dragged street 0.5 s | Built |
| 10zf.7 | Page tools | Plots drawn from 1.1 px/m, filled by use (not set faint over the sheet); blocks by leading use or by type (Colour by); Plots layer. Plot panel: use, name, sheet labels, Split with a line (Ctrl squares it to the street), Merge with neighbours (click touching plots), Divide along the street (n lots, default frontage / 7.6 m), Reset. Block panel: land use mix, Land use for every plot, Clear, Re-divide into lots (lot width, square to the longest side, two rows when deeper than 55 m; each sheet label goes to the one new lot over its old plot's middle). Open land: Add to a touching plot, Make it one plot, Divide into lots (square to the street it came from; new land with no block nearby makes its own block). Saved as edits.plots {id: {u, n}}, edits.blocks[id].u and edits.plotOps (s split, m merge, d divide, f fill, r re-divide), replayed in order and cached on their inputs; undo and redo cover them; GeoJSON and KMZ carry plots, live blocks and open land | Built |
| 10zf.8 | Tests (plots/ptest.py, pinter.py, pinter2.py, predo.py, pfull.py; JSTS routed to the npm copy) | Load with Ben's layout, use set, split, merge, divide, undo, block use, open land add, fill and lots, street drag, re-divide, exports (16.8 MB GeoJSON, 21.9 MB KMZ zip), light, dark and phone width: no page errors | Done |
| 10zf.9 | Found | Some basin blocks are missing from the block layer (around Mulberry, Schiller and Hugh at the foot of Mount Auburn), so they have no plots. Regenerating blocks from saved edits will need the plots regenerated too: plot settings and steps are keyed to the present plot ids | Open |

## 10zg. Select several and merge; the plot method rejected (2026-10-15, plots/patch_v34.py; page version 34)

| # | Item | Result | Status |
|---|---|---|---|
| 10zg.1 | Request (Ben) | Shift- or Ctrl-select several things and merge them: street pieces that have been extended into each other, and lots; a click-and-drag box as well, since a site like Crosley needs the whole thing selected | Recorded |
| 10zg.2 | Page | Shift, Ctrl or Cmd click adds or removes a thing; dragging with one held draws a box that adds every plot whose middle is inside it (plots showing, 1.1 px/m and closer). Panel for several: plots that make one connected piece merge into the first selected (one plot step; it keeps its id, use and name) and can all be given one use; two or more streets merge into the first selected: the others are joined end to end (each piece turned so its end nearest the chain goes first, attached at whichever end of the chain is nearer), leading points drawn over the chain (within half the width, 2 m at least) dropped, a gap bridged straight, curves kept. The others are stored as merged into it ({del, into}), drop out of the plan, exports and picking, and their whole old corridor counts as left land in the plot engine; the merged street keeps the state before the merge (mg.pre), and Unmerge or Reset puts every piece back. Tested: two and five plots (box), use for all, Dalton SB0630 + SB0633 and Unmerge, undo; no page errors | Built |
| 10zg.3 | Angled lots (Ben: Dalton between Sherman and Findlay) | Lots drawn at an angle where nothing on the ground is angled. Cause: a block with only two street faces keeps both as lot fronts even when one is a short end square to the other (gen.primary_runs returns two runs unchanged), and the split between fronts is a Voronoi bisector, so the corner lots meet on a 45-degree line; the "another long face at an angle" rule (0.8 of the longest, within 60 degrees) does the same. Ben: angled lots only where a street is angled (as Western Avenue); not to be fixed yet | Open (later) |
| 10zg.4 | Plot method (Ben) | "Many of the lots were drawn haphazardly and without real distinction or check against the sheets"; worst: Pleasant Court, and the block of Smith, Central, 2nd and 3rd (Central Union Station). Found: the method never traced lot lines. It measured a repeat spacing per face and snapped each cut to the strongest line within 2.5 m; faces with no repeat got even widths whatever the sheet shows; big single sites (the station and train shed, factories, warehouses) were chopped into standard lots plus a 40 m interior grid; Voronoi splits between fronts and the 40 m depth cap gave arcs (Pleasant Court) and diagonals (10zg.3); and no block was checked against its sheet after generation (only the use labels were). Ben's three merges in SBB0843 are keyed to the present plot ids | Open (method to be chosen) |

## 10zh. Union Terminal from the 1931 plot plan, the General CUT Path, RER and APEx to the region bounds; plots tabled (2026-10-15, cutplan/, cut/cut1931.py, cut/tracks_gen4.py, cut/apex_region.py, transit/build_transit.py, plots/patch_v36.py; page version 36)

| # | Item | Result | Status |
|---|---|---|---|
| 10zh.1 | Request (Ben) | Table the plots and label them unfinished; use the 1931 Union Terminal plot plan (TIF) for a better CUT and former Lincoln Park outline; use the General CUT Path KMZ for the path from CUT to the four-track APEx bridge; extend RER and APEx to Erlanger, CVG Terminal 1, Eastgate and Aviation. Mid-turn: Dalton has an underpass through the terminal, and President Place is gone (replaced by the park) | Recorded |
| 10zh.2 | Plots | Layer "Plots (unfinished)", status line prefixed "Plots, unfinished", a note in every plot panel, and the Plots paragraph in the notes says the lot lines were not checked against the sheets and are to be redrawn (10zg.4) | Tabled |
| 10zh.3 | Union Terminal (cutplan/georef.py, trace.py; cut/cut1931.py) | Plot plan of 1 June 1931 (HABS OH-705, sheet 1) fitted by an affine on five street crossings (Dalton, Denman, Freeman on Kenner and Hopkins), residuals 0.54-1.05 m; rotunda 180 ft across on the drawing. Traced: building with rotunda 8,151 m2; train concourse 2,930 m2 (ends at about E 712,724, short of the west headhouse; the APEx field runs on to it); plaza (bus and cab ramps, plaza driveway, cascade) 31,391 m2, replacing the open east forecourt; former Lincoln Park (north and south driveways, mall) 38,815 m2 | Built |
| 10zh.4 | Streets at the terminal | Dalton Avenue: an underpass under the plaza, Hopkins to Kenner (dashed walls on the plan, 58 px = 10.8 m apart; plan centre line within 0.7 m of the 1904 line, so drawn on it), basin id SB0631U, structure underpass, drawn translucent with dashed walls. President Place (SB0899) removed; its strip (18.4 m by 176 m, 3,240 m2) added to the park block SBB0453. Curran Street (SB0626) removed: not on the plan, it ran under the building's east face and the plaza driveway (done with Ben's two rulings; not ruled by Ben himself) | Built |
| 10zh.5 | South approach (cut/tracks_gen4.py; backup tracks_gen4_v35.py) | General CUT Path of APEx.kmz: straight south on the field centre line, one curve of 814 m radius between W 8th and W 6th, then straight across the Ohio at bearing 204.0 degrees on the four-track bridge, centred on the KMZ line: 97.6 m east of the CS bridge centre at the Ohio bank, 28.2 m at the Kentucky bank; 0.88% up from W 8th. Tracks end 120 m past the Kentucky bank (APB_X 712,506 / 4,330,261) | Built |
| 10zh.6 | Found: Ludlow convergence (settled in 10zi.5) | The KMZ path runs into the CS corridor: at APB_X the APEx centre line is beside the CVG pair's end (712,501 / 4,330,262), and south of there the KMZ line runs along TRIMET's CVG Express 3D through Ludlow and Bromley, crossing it repeatedly from 712,444 / 4,330,121 to 711,167 / 4,327,249. Side by side or at separate levels is not set | Open (Ben) |
| 10zh.7 | Region (cut/apex_region.py, transit/build_transit.py; backup build_transit_v35.py) | Box E 701,600-736,900, N 4,320,800-4,347,000 (CVG Terminal 1 at the west edge, Erlanger south, Eastgate east, Aviation north). RER outside the plan window: Cincinnati Rail.kmz as drawn, shared trunks once, with stations, tracks and 670 ft islands (rer 68 pieces, 128 stations, 178 tracks, 372 platforms; inner ids, stations and Metro unchanged). APEx: APEx Routes.kmz lines, shared corridors once, left out within 120 m of the designed approaches and joined to their ends by tangent curves; four tracks where two or more Tier 1 routes share a corridor (the Kentucky trunk through Erlanger, the north trunk to the Vandalia/Norwood split) unless continuing a two-track bundle, two elsewhere; 6 pieces, 77.6 km, 13.9 km four-track; stations Erlanger, Norwood, Eastgate. Track counts and spacing outside the designed approaches are drawing values. Metro stays in the plan window; no Sanborn or relief beyond it | Built |
| 10zh.8 | Page (plots/patch_v36.py after patch_page.py and patch_v34.py) | Region button (fits the box with a margin), zoom out to 0.02 px/m, off-screen tracks and track features culled by bounding box, region APEx at least 1.3 px when zoomed out, APEx station labels and the Aviation and CVG Terminal 1 RER labels at region zoom; plaza, former Lincoln Park and concourse drawn, labelled (area centroids, Union Terminal first, overlapping labels skipped) and pickable; concourse outlined dashed over the platforms; CUT approaches panel gives both bridge offsets, bearing, curve radius and the region totals. Tested in Chromium with deck/layout version 335: no page errors | Built |

## 10zi. Union Terminal from the first-floor plan, the 1931 track field, plaza roads, CUT layers, CVG flyover, Ludlow approaches (2026-10-15, cutfp/fp_trace.py, cutplan/tracktrace2.py, field1931.py, plaza_trace.py, cut/tracks_gen4.py, cut/cut1931.py, plots/patch_v37.py; page version 37)

| # | Item | Result | Status |
|---|---|---|---|
| 10zi.1 | Request (Ben) | Make the whole building visible (the left sheet of the floor-plan image shows it better) and take the outline from that image; extend the whole concourse to the west headhouse; lay out the plaza roads on top; layers for CUT; edit the track layout from the TIF (the mail platforms are the CVG Express platforms); Ludlow: the bridges are too abrupt, approaches for the CS/APEx split like the north viaduct. Answers: mail platform = the one beside the building (SE); Ludlow: the pink tracks extend to Ludlow, at least 6-8 tracks there (4 APEx from that bridge, at least 2 intercity, maybe 2 spare depending on traffic; later RER additions will change the count) | Recorded |
| 10zi.2 | Building and concourse (cutfp/fp_trace.py) | Traced on the first-floor plan (PNG, west up) and fitted to the plot plan by a similarity on six building corners (scale 2.436 plan px a PNG px, residuals 0.6-2.4 m), then by the plot plan's affine: wings, link block, rotunda, front and the bus and cab ramp arms, 11,439 m2 (the plot-plan trace without the arms was 8,151). Concourse 24.6 m wide, carried west to the west headhouse's east face: 155.7 m, 3,799 m2 | Built |
| 10zi.3 | Track field (cutplan/tracktrace2.py, field1931.py) | Track centres traced on the TIF (matched filter on the rail pair, followed row by row) are straight and parallel through the platform zone at bearing 178.84 degrees; 8 islands: pair centres 3.97 m, 11.68 m across an island (platforms 8.32 m, edges 1.68 m from track centres), 15.65 m a unit. My first reading (a ninth island north-west) was wrong: north and south traces were off by one pair across the concourse; with the slope carried through, the islands run continuously under the concourse (a bridge). Seven concourse islands = APEx 1-14 from the building westward; the island beside the building, stub-ended on its east side at the building's north and south faces = M, CVG Express 15-16; the westmost through track = freight passing track. Platform zone kept at the ruled N 4,331,646-4,332,134 (the plan is cut off north of N 4,332,094); M north N 4,331,899-4,332,134, M south 4,331,646-4,331,847 | Built |
| 10zi.4 | South approach | Six APEx tracks (Kentucky 4 + Cardinal 2) from the field, curve 872 m between W 8th and W 6th; Kentucky 4 on the bridge; Cardinal leaves east south of W 8th. CVG Express from M on the east side flies over the six APEx tracks at N 4,331,181: 1.36% up from M (159.9 m) to 166.4 m over the APEx (159.6 m, 6.8 m clear), 0.45% down onto the TRIMET CS viaduct; joins the intercity pair (A-D, pink) at the abutment at 164.1 m; tightest CVG curve 626 m. A-D renamed the intercity pair (Ben's word) | Built |
| 10zi.5 | Ludlow (Kentucky) | CS pair (intercity + CVG Express) across the 1922 bridge and at grade on the TRIMET Lebanon-Walton line (12.2 km in the region); APEx 4 east of it, 15.75 m centre to centre (group spacing 6.75 m), 2.0% up from the Kentucky bank on a viaduct, over the CS line 993 m from the bank at 183.9 m against 168.6 m (15.3 m clear, 18 degree skew), then the KMZ line toward Erlanger; tightest APEx curve in Ludlow 727 m. 6 tracks drawn: CVG Express 6 an hour at the peak (tracker) + intercity placeholder 4 (10l.2) = 10 an hour each way on the CS pair, about half a double track at 3 minutes, so no spare pair yet; room left on the west side. CVG Express leaves the CS line at Erlanger (708,854 / 4,323,107), as on TRIMET (9.7 km to CVG; tightest curve 118 m near the terminal, the TRIMET alignment) | Built |
| 10zi.6 | Plaza and park (cutplan/plaza_trace.py) | Bus and cab ramps in both arms (circles fitted to the walls), terrace and cascade, plaza lawns, the mall's north, central and south lawns, north and south driveways, the Kenner and Hopkins side drives and the Freeman end drive, walks and fountain circles; roads drawn over the plaza and over the arms (ramps see-through) | Built |
| 10zi.7 | Page (plots/patch_v37.py) | Union Terminal layers under CUT tracks: building, train concourse, roads and ramps, plaza/terrace/park, platform level (APEx, CVG), lower level and intercity; building outline heavier; track numbers from any track name; CUT approaches panel: field, CVG Express, Ludlow. Tested in Chromium (deck/layout 335): clicks on a ramp, toggles, no page errors | Built |
| 10zi.8 | Open | Ludlow streets under the APEx viaduct not checked (no Ludlow sheets); intercity south traffic is still the 10l.2 placeholder; 10l.1's "CVG Express 15-16 on the west side" is superseded (M beside the building) | Open |

## 10zj. CVG Express at grade, the Kentucky APEx in tunnel, lower platforms recentred, headhouse east, M full length (2026-10-15, cut/tracks_gen4.py, cut/apex_region.py, cut/cut1931.py, plots/patch_v38.py; page version 38)

| # | Item | Result | Status |
|---|---|---|---|
| 10zj.1 | Request (Ben) | 1. No flyover for CVG Express (a single line); 2. ORR follows the existing tracks, the APEx does not: it is tunnelled through the hills and already grade-separated from ORR/intercity; RER E leaves the APEx tunnel and passes over it; at one point three tracks are stacked, top down ORR/intercity, RER E, APEx; 3. recentre the underground platforms on the APEx platforms; 4. the west headhouse can move east; 5. track 16 and its platform run the full length | Recorded |
| 10zj.2 | CVG Express (superseded by 10zk.3) | Flyover removed (10zi.4 superseded). The pair leaves M, crosses the six APEx approach tracks at grade just south of the throat (7 crossings, N 4,331,406-4,331,358) and runs onto the TRIMET CS viaduct, 0.41% up to the bridge, joining the intercity pair at 163.9 m; tightest curve 205 m. Working reason it fits: 6 trains an hour each way = 12 crossing moves an hour, placed in the :25-:50 inter-knot period when the Kentucky approach is quiet | Built |
| 10zj.3 | Kentucky APEx (10zi.5 viaduct superseded) | 2.0% down from the Kentucky bank (164.0 m), portal 340 m from the bank (cover 7.8 m: box rule 6.8 m + 1 m fill, LiDAR ground), tunnel at 146 m under the CS line about 1 km from the bank (CS 168.6 m, 22.6 m below) and under the valley at about N 4,329,000 (ground about 154 m), then 1.0% up toward Erlanger (working values). Region APEx on the Kentucky trunk drawn as tunnel (dashed); its portals toward Erlanger are not set | Built |
| 10zj.4 | Three levels | RER E (Cincinnati Rail.kmz) crosses the APEx KMZ line three times, each within 20 m of the CS line: N 4,328,225 (CS 185.3 m, APEx 153.0 m), N 4,327,195 (199.0 / 164.3 m), N 4,325,649 (224.7 / 181.2 m, at Erlanger). RER E drawn midway (169, 182, 203 m), a working value; which of the three Ben means is not said | Built / Open (which point) |
| 10zj.5 | Lower platforms | A-H centred under the APEx platforms (platform 7 west edge to platform M east edge): 80 m block from E 712,743.6 (was 712,700); CS (A-D) and C&O (E-H) leads moved with them; intercity pair climb 2.86%, C&O 2.12% | Built |
| 10zj.6 | West headhouse | Moved 30.0 m east to 2.5 m west of the freight passing track; west park extended to it (park length 264.5 m); precinct trimmed; concourse now 125.6 m to the headhouse | Built |
| 10zj.7 | Track 16 and platform M | Full length, N 4,331,646-4,332,134 (the stubs at the building faces in 10zi.3 removed) | Built |

## 10zk. CVG Express on its own span (option A); plot locks (2026-10-16, cut/tracks_gen4.py, plots/patch_v39.py; page version 39)

| # | Item | Result | Status |
|---|---|---|---|
| 10zk.1 | Ben on 10zj.2 | 12 at-grade crossings an hour is one every 5 minutes, not good; discussed before changing. Options put: A, CVG on the APEx bridge side and over the APEx tunnel in Ludlow; B, dive under at CUT (about 5 deck streets cut); C, CVG to the west island (against the mail ruling). My timing claim in 10zj.2 was wrong: the :25-:50 period carries the Express and Local wave | Recorded |
| 10zk.2 | Ruling (Ben) | A, with a separate span next to the APEx bridge | Ruled |
| 10zk.3 | Built (Ludlow part superseded by 10zl.4) | CVG pair from platform M east of the APEx approach (throat curves 1,024 m and over), crossing only the Cardinal pair at grade (4 diamonds, N 4,330,993-4,331,028; Cardinal 25 trains each way a day, about 1.4 an hour); its own double-track span east of the APEx bridge, tracks 22.5 and 27.0 m east of the APEx centre, about 6.3 m between structures (drawing values, 4.75 m outer track to deck edge); in Ludlow parallel to the APEx for 260 m past the bank, then a 380 m reverse curve (tightest 543 m) west over the APEx, 10.3 m clear at the closest (426 m from the bank, APEx in its cut and tunnel), onto the CS line 645 m from the bank by a flat junction (southbound CVG across the northbound CS track; conflicts only with northbound intercity). The intercity pair has the CS bridge to itself: 2.88% to the TRIMET CS viaduct at 164.0 m. Eight tracks cross the river (CS 2, APEx 4, CVG 2) | Built |
| 10zk.4 | Request (Ben) | A lock or mark for blocks already edited by hand so they need no plot checks | Recorded |
| 10zk.5 | Built: plot locks | edits.blocks[id].lk = date locked (generated block id; pieces inherit). Block panel: Edited by hand (plot steps, plot uses or names, block type/name/use), Plots locked, Lock/Unlock button; locked: block use, re-divide, and every plot's use, name, split, merge, divide and reset disabled; merge tool and open-land fill refuse locked plots; multiple selection: locked plots left out of merge and use, Lock/Unlock their blocks; Layers panel: count and one button to lock every block with hand edits (11 now: B053, SBB0075, SBB0079, SBB0285, SBB0360, SBB0453, SBB0843, SBB0147, SBB0571, SBB0148, SBB0479; not locked until Ben presses it); map: accent outline and padlock; GeoJSON export plots_locked. A street moved across a locked block still cuts it. The plot redraw (10zg.4) is to keep locked blocks' plots as they stand. Tested in Chromium (deck/layout 348): lock, unlock, panel gating, bulk lock; no page errors | Built |

## 10zl. CVG airport layer; CVG Express on CVG Express New.kmz (2026-10-16, cvg/build_airport.py, cut/tracks_gen4.py, cut/apex_region.py, transit/build_transit.py, plots/patch_v40.py; page version 40)

| # | Item | Result | Status |
|---|---|---|---|
| 10zl.1 | Request (Ben) | Map CVG from CVG Layout.kmz (runways are centre lines, 150 ft wide; terminals and hubs are buildings; the areas are general areas); put the CVG Express on CVG Express New.kmz; the path to the terminals is not set (airside train; RER is landside): one stop for 2/3/4 like the RER, or a stop at each terminal | Recorded |
| 10zl.2 | Sources | Staged from Ben's computer (Documents/_Personal/_Cincinnati Rail): CVG Layout.kmz (5 terminals, 2 hubs, 5 runway centre lines, 4 areas), CVG Express New.kmz (4 lines). The CVG Express line is the APEx KMZ line from CUT through Ludlow and the hills to Erlanger (within 0-10 m), then its own line west, the last part on the TRIMET CVG line, ending at E 705,253 N 4,325,600, about 2 km east of Terminals 2-4 | Read (cvgkmz/) |
| 10zl.3 | Airport (deckpage/airport.json) | Runways 150 ft (45.72 m) on their centre lines: 18L/36R 12,000 ft, 9L/27R 12,000, 18C/36C 11,000, 9R/27L 10,010, 18R/36L 9,000; buildings Terminals 1A, 1B, 2, 3, 4, Amazon Hub, DHL Hub; areas Cargo Plane Parking, Hangar Space, Hangar/Cargo, Parking ("Hanger" spelled Hangar). Page: CVG airport layer, CVG zoom, labels, picking. Region box widened west to E 699,000 (RER and APEx rebuilt: RER 72 pieces, 130 stations; transit edit ids unchanged) | Built |
| 10zl.4 | CVG Express route (supersedes the Ludlow junction in 10zk.3) | Own span beside the APEx bridge as before; then beside the APEx (own bores, 24.75 m east of its centre) through Ludlow and the hills, level with it; 1.69% up from 3.45 km past the bank; over the APEx 15.1 m (working value, bore over bore) at E 710,269 N 4,325,230 just north of Erlanger, where it turns west; under the CS line at E 709,278 N 4,324,227 (224.7 m against 249.5 m); on the TRIMET CVG line's levels from E 707,194 (262.5 m) to the KMZ end (270.4 m); 12.0 km from the Kentucky bank; tightest curve 470 m. No crossing in Ludlow and no CS junction; the CS pair carries only the intercity trains. Old CVG branch on the CS line removed. Its last 3.8 km is the corridor the RER B/C/E line to CVG also uses (both KMZs on the TRIMET CVG line): side by side not set | Built / Open |
| 10zl.5 | Terminal end (Ben to choose) | A: two airside stops like the RER: Terminal 2/3/4 between T2 and T4 (about 90 m to each, T3 about 300 m) and Terminal 1 at T1B (T1A 775 m across runway 18C/36C); about 3.1 km past the KMZ end. B: a stop at each terminal (T4, T2, T3, T1B, T1A), about 4.9 km, three more stops | Open |

## 10zm. CVG Express to the terminals from CVG Express Final.kmz (2026-10-16, ludlow/cvg_block4.py in cut/tracks_gen4.py, cut/apex_region.py, plots/patch_v41.py; page version 41)

| # | Item | Result | Status |
|---|---|---|---|
| 10zm.1 | Request (Ben) | Option 1 or 1b; the CVG Express is deep-bored and the RER is shallow; CVG Express Final.kmz shows the evolution: extending 18L north cut the original tracks, and the new Terminals 2 and 3 caused the line to be tunneled south | Recorded |
| 10zm.2 | Sources | Final.kmz staged from Ben's computer (cvgkmz/final_raw, cvgkmz/cvg_final.json). Pieces 1-3 the same as New.kmz; piece 4 ends at the split, E 707,285 N 4,323,668 (the rest of New piece 4 is the Original). 5 - Original (6.8 km): north-west on the TRIMET/RER path to about E 705,063, then west across the north end of 18L (N about 4,326,055) to T1A. 5 - Today (8.4 km). Yard (about 100 by 690 m) and maintenance building north-west of T1A. Stop points T3, T2, T4, T1B, T1A, all within 3 m of the Today line. The RER B/E line (Erlanger-Beaverlick) follows piece 4 from E 709,258 and the Original to about E 705,030 | Read |
| 10zm.3 | Plan | Today's straights joined by circular curves: 3,810 m (9.0 degrees) after the split, 762 m (56.6) under 18L/36R onto the north-north-west straight through T3, T2 and T4, 292 m (64.0; 380 m in Ben's drawing, tightened so the T1B platform is straight), 475 m (89.1) north into the yard. Five stations at Ben's stop points (option 1, as in the KMZ): 150 m side platforms with screen doors (drawing: edge 1.6 m from the track centre, 6 m wide), 366, 266, 818 and 672 m apart. The bore joins the 1969 line at E 702,134, just east of T1B | Built |
| 10zm.4 | Profile | Unchanged to the APEx crossing north of Erlanger (1.69% from 3.45 km past the bank; 200.8 m, 15.1 m over the APEx). Then level at 209.5 m: 40 m under the CS line (249.5 m), in its own bores under the RER B/E line from the CS line to the split, and under the creek valley east of the airport (floor 221.9 m at E 706,729 N 4,323,833; 12 m rail to floor, working value). 0.76% up from 10.06 to 13.88 km past the bank to 238.5 m, the airport level under the shallow RER (working values: RER rail 12 m below the apron at T4, about 253.5 m; the CVG Express 15 m under it). Stations level at 238.5 m, 21 to 29 m below the ground. Beyond T1A 2.04% up to the yard at 255.5 m; portal about 880 m past T1A, under the tip of T1A's west pier. First try (level at 238.5 m from the CS line) put the line in the open across the creek valley, 13 m over its floor; replaced by the bore under it | Built |
| 10zm.5 | Distances | From the south end of platform M: T3 15.33 km, T2 15.70, T4 15.96, T1B 16.78, T1A 17.45; 17.6 km from the Kentucky bank to the yard. First stop to T1A about 5.4 min (rough: 0.8 m/s2, 80 km/h cap, 30 s stops; not verified figures) | Recorded |
| 10zm.6 | Former line | The 1969 line from where the RER leaves it (E 705,030) west across the north end of 18L to the junction east of T1B, drawn grey dashed, with a marker where 18L cuts it (E 703,627 N 4,326,054). The RER uses the 1969 line from the split to about E 705,000 | Built |
| 10zm.7 | Page | Station platforms and markers (labels from the CVG zoom), yard, maintenance building, former line; clicking a platform gives rail, depth and distance from platform M; yard and building pickable; CUT approaches panel and notes rewritten. Tested in Chromium: no page errors | Built |
| 10zm.8 | Supersedes | 10zl.4 (TRIMET levels to the KMZ end; side by side with the RER) and settles 10zl.5 (option 1, five stops) | Done |

## 10zn. CVG Express platforms 200 m and editable like the RER and Metro (2026-10-16, ludlow/cvg_block4.py in cut/tracks_gen4.py, plots/patch_v42.py; page version 42)

| # | Item | Result | Status |
|---|---|---|---|
| 10zn.1 | Request (Ben) | Platforms 200 m (four 50 m or three 67 m units), with the same changeable rules as the RER and Metro stations (movable, island or side, and so on) | Recorded |
| 10zn.2 | Data (tracks.json 'cvx') | The airside line from the split (E 707,285 N 4,323,668) to the yard as a station-editor line: 29 vertices with a quadratic control per curved piece (arcs cut into pieces of 10 degrees or less), five stations at Ben's stop points (rail 238.5 m, depth, km from platform M), generated side platforms (200 m, edge 1.6 m from the track, 6 m wide), generated tracks (tunnel dashed, open to the yard solid). The tracks.json CVG pieces now stop at the split | Built |
| 10zn.3 | Curves and platforms | Curves back to Ben's radii (3,810, 762, 380 and 475 m; the 292 m of 10zm.3 is undone). Generated platforms centred on the stop points except T1B (centre 80 m west, so the platform clears the 380 m curve by 15 m) and T1A (14 m east, clear of the curve to the yard). Level from 50 m before the T3 platform to 15 m past the T1A platform; the climbs follow (0.76% before T3, 2.07% to the yard; portal about 874 m past T1A) | Built |
| 10zn.4 | Page | Third system 'cvx' in the station editor: line selectable and editable (Edit points, curves, reset), stations selectable, platforms island or side (island 10 m, drawing value), moved along the line within half a platform of the station point (slider or drag in Edit mode), delete and restore, reset; tracks redrawn as a pair round island platforms once edited; shown with the CUT tracks layer; centre line and station dots when zoomed out, tracks and platforms from 0.8; station panel adds rail level, depth and km; GeoJSON export cvx_line, cvx_station, cvx_platform. The airport is now drawn under the transit layer. Tested in Chromium: island, move 60 m, delete; no page errors | Built |
| 10zn.5 | Note | Three 67 m units are 201 m, 1 m longer than the platform; if those units are used the platforms want about 205 m (one value in the generator, PLAT_CVX) | Open |

## 10zo. Filled blocks, the deck edge no longer a boundary, stretch edits (2026-10-17, fill/fill_blocks.py, plots/engine.js, plots/patch_v43.py; page version 43)

| # | Item | Result | Status |
|---|---|---|---|
| 10zo.1 | Request (Ben) | Fill the land between streets that has no block with editable blocks (not divided), many around Queen City Ave; the deck is not a boundary for blocks or lots (keep it as a layer); pick two points on a line and change the stretch between them (street widths that change along a street, e.g. Harrison Ave; one constant-radius curve on a Metro/RER line instead of fitting the whole line) | Recorded |
| 10zo.2 | Method | Faces of the street network (street ends run on half a width plus 3 m so a street that stops at another closes the face), less the street corridors and the plaza, precinct, palace, park and other area layers. Blocks with any saved hand edit or plot edit (live layout version 492) are left as they are | Built |
| 10zo.3 | Deck edge | 11 groups of blocks cut by the deck outline joined into one block each (larger id kept; plots move to it; joined17 lists the others); 12 pairs of lots cut by it joined (same frontage, both under 1,500 m2, sharing 5 m or more of the edge). B026 and SBB1037 (locked, merged by hand) left as Ben has them | Built |
| 10zo.4 | Fill | 37 pieces of land that a block stopped short of (at the deck edge or another non-street line) joined to that block as one new lot each (about 39 ha; extended17); 129 new blocks on land with no block (about 180 ha; side 'fill', type building, one lot each, ids FB001-FB129). Large ones sit on the 1904 rail yards along the Mill Creek; their type can be changed in the block panel | Built |
| 10zo.5 | Stretch tool | In Edit mode a click on a point picks it; a second point picks the stretch. Streets: width for the stretch (per-segment widths e.wv, kept through added, removed or refitted points; drawn run by run; the plot engine cuts with each run's width); 'One width again' drops them. Any line: 'One curve between them', the largest circle tangent to the line before the first point and after the second (or a smaller given radius), with straights to it; refuses an S bend. Tested in Chromium: Harrison Ave (west) 32 m on its first segment, an added point keeps it; RER E bend made one 211 m curve; no page errors | Built |
| 10zo.6 | Pipeline | fill/fill_blocks.py runs after cut1931.py and build_plots.py; it reads plots/live/deck/layout.json for hand-edited blocks and refuses to run twice (deck.json fill17) | Note |

## 10zp. Ludlow straight, CVG Express beside the APEx, bridge spans, CUT plaza on the grid (2026-10-17, cut/tracks_gen4.py, ludlow/cvg_block4.py, cut/plaza_align.py, plots/patch_v44.py; page version 44)

| # | Item | Result | Status |
|---|---|---|---|
| 10zp.1 | Request (Ben) | The CS Bridge KY Approach.kmz shows the normal approach; the APEx reverse curve in Ludlow makes no sense for HSR. The CVG Express need not be 24.75 m off the APEx except on the bridge. The CUT park and terrace are not aligned with the grid or the real CUT. Add-ons: Ezzard Charles to replace Laurel (CUT-Music Hall axis); Bridge Spans.kmz gives the real span ends | Recorded |
| 10zp.2 | Ludlow | CS pair on the KMZ CS approach (then TRIMET). APEx straight off its bridge on the KMZ bearing (204 degrees) with no curve until the hills. Exactly on the KMZ line it would pass 8.4 m from the CS line at N 4,330,200 (both about 161-165 m), so the line (bridge, Ludlow straight and the hills KMZ line) is drawn 7.5 m east of the KMZ: the least that keeps 15.75 m to the CS pair. Portal 360 m from the span end; under the CS line at E 712,148 N 4,329,438, 22.8 m under | Built (shift to confirm) |
| 10zp.3 | CVG Express | 24.58 m east of the APEx on the Ohio approach and its span (from the KMZ spans), then in to 15.75 m within 250 m of the Kentucky span end (APEx outer track 6.75 m, CVG inner 13.5 m) through Ludlow and the hills; CVG pieces now cut on the centre line, then offset | Built |
| 10zp.4 | Spans | Bridge Spans.kmz: APEx, CVG Express and CS bridges and the C&O drawn span to span (APEx and CVG moved 7.5 m with the line; the APEx descent starts at its span end); Clay Wade Bailey, Roebling, Cincinnati-Newport and L&N added as other bridges. Ohio approach curve now 735 m | Built |
| 10zp.5 | CUT plaza | East plaza group (plaza, former Lincoln Park, drives, ramps, terrace, lawns, walks: 47 features) turned 1.02 degrees about the terminal's east face onto Kenner and Hopkins (-3.03 degrees) and centred between them (3.3 m north); west park rebuilt as a rectangle on the deck's Kenner and Hopkins (-3.44 degrees, was 0), terminal square to the west headhouse, 114 m wide, centred | Built |
| 10zp.6 | Ezzard Charles | Options put to Ben: widen Laurel in place (about 1.4 ha taken, 26 lots lost, 81 cut) or one straight from the plaza axis at Freeman to Music Hall (about 2.5 ha, 95 lots lost, 98 cut; up to 54 m north of Laurel); 30.5 m (100 ft) assumed | Open |

## 10zq. Ezzard Charles Drive on Laurel; the intercity pair on the CS span (2026-10-17, cut/ezzard.py, cut/tracks_gen4.py; page version 45)

| # | Item | Result | Status |
|---|---|---|---|
| 10zq.1 | Request (Ben) | Ezzard Charles widened in place, as the modern road; the ORR (intercity) viaduct on the Cincinnati side no longer lines up with the bridge | Recorded |
| 10zq.2 | Ezzard Charles | Laurel (SB0817-SB0819) replaced by Ezzard Charles Drive on its modern OSM line (about 10 m north of Laurel's centre), Freeman to Music Hall at Central Parkway: EZ1 Freeman to Baymiller 45.7 m (150 ft, divided), EZ2 to Central Avenue 24.4 m (80 ft), EZ3 to Music Hall 18.3 m (60 ft); widths are drawing values from the modern lane counts. 14 blocks lose 1.45 ha; 6 lots gone, 116 trimmed; no hand-edited block touched | Built |
| 10zq.3 | CS span | The intercity pair now runs onto the CS bridge's own line 120 m before the span (Bridge Spans.kmz) and across it exactly; the climb reaches 164.0 m at the span's north end (before, at N 4,330,705, 75 m out on the bridge). From W 8th that is 3.37% with the 3 m street hump (2.92% with 5 m) | Built (grade settled in 10zs) |

## 10zr. The CUT on one axis (2026-10-17, cut/cutclean.py and cut/cutclean2.py; page version 46)

| # | Item | Result | Status |
|---|---|---|---|
| 10zr.1 | Request (Ben) | The CUT and Ezzard Charles area was choppy: streets overlapping, the station and park not aligned with the streets, the plaza not symmetrical | Recorded |
| 10zr.2 | Defects found | Kenner and Hopkins changed width at every piece (Kenner 15.2 / 18.3 m, Hopkins 18.3 / 15.2 / 18.3 / 24.4 m), so their plaza-side edges jogged up to 3 m; Hopkins zigzagged at Dalton (-3.1, -4.1, -2.5, -3.1 degrees); the terminal sat at -3.82 degrees and 2.8 m south of the street midline, the west park at -3.44, the square at -3.65; the traced plaza's pairs differed by up to 6 m (central lawn and fountain 5.6 m north of the axis); the 1931 "north drive", "south drive" and "Freeman end drive" sat on Kenner, Hopkins and Freeman; Ezzard Charles began 7-9 m south of the plaza axis | Recorded |
| 10zr.3 | Axis | -3.0 degrees, through E 713,377.8 N 4,331,846.7 (Freeman). Kenner (SB0799, 18.29 m) and Hopkins (SB0775, 24.38 m) straight and parallel to it from Garrard to Freeman, through their Freeman ends (Garrard ends move 1.7 m); inner edges 165.5 m apart, the axis midway. Ben's page merges (S013 into SB0799; S012, SB0776, SB0777 into SB0775) baked into the data, so those six saved street edits are cleared | Built |
| 10zr.4 | Terminal group | Building, concourse, west headhouse and the cab and bus ramps turned 0.82 degrees and moved 2.8 m onto the axis; building made exactly symmetric (north half mirrored; 165.5 m wide, filling the street gap); concourse and headhouse as rectangles on the axis; platforms polygon from street edge to street edge with its ends along the platform tracks (bearing 178.84 degrees). West park (256.6 x 114.1 m) and terminal square (140 m) re-centred on the axis against the headhouse; Garrard's two stubs end on the park edges | Built |
| 10zr.5 | Plaza | Turned 0.015 degrees onto the axis (it was 0.13 m off); 19 north/south pairs, the south one now the mirror of the north; terrace, forecourt, Lincoln approach and the central lawn and fountain centred and mirrored; the three drives that duplicated Kenner, Hopkins and Freeman removed; everything clipped to the street inner edges and Freeman's west edge | Built |
| 10zr.6 | Ezzard Charles | EZ1 (Freeman to Baymiller) now on the axis, as wide as the plaza driveways outer edge to outer edge, 57.3 m (188 ft; was 45.7 m on the OSM line), so the two driveways run straight on into it; EZ2 starts at Baymiller's centre line (its south edge within 1 m of EZ1's); EZ2 and EZ3 otherwise unchanged. Alley SB0021 (inside the new EZ1) removed; Harold Alley runs to the new centre line | Built |
| 10zr.7 | Blocks and lots | Recut only where a street or CUT shape moved (the whole CUT strip, square to Freeman, plus the old Laurel strips): 36 blocks; 13 pieces of freed land (0.63 ha) joined to the block they border most; lots clipped (302) and widened across freed land with their side lines carried straight (151); 14 lots gone (13 in SBB0451, which the new EZ1 covers, and SBB0452-012), none in saved edits; locked blocks B088 and SBB0453 only clipped by streets | Built |
| 10zr.8 | EZ1 width | EZ1 at 57.3 m keeps the 1931 plaza as traced; the alternative is EZ1 back to 45.7 m with the plaza driveways pulled in 5.8 m each (central lawn 23.6 m instead of 35 m), which gives the blocks north of EZ1 6 m more depth. Ben: keep 57.3 m | Settled |

## 10zs. W 8th raised 5 m with a wall portal; the APEx on one grade to the bridge (2026-10-17, cut/tracks_gen4.py, ludlow/cvg_block4.py; page version 47)

| # | Item | Result | Status |
|---|---|---|---|
| 10zs.1 | Request (Ben) | W 8th raised 5 m on an embankment, the intercity pair leaving through a portal in the vertical wall on its south side (like the Central Parkway subway portal); the APEx straightened to make room | Recorded |
| 10zs.2 | APEx | One straight grade from the platforms' south end (N 4,331,646, 159.9 m) to the bridge (164.0 m): 0.43% (was a dip to 159.2 m at W 8th, then 0.9% up). Now 160.3 m over Gest, 161.7 m over W 8th, 163.4 m over W 6th. The CVG Express and Cardinal pairs follow it to the bank; no other level changed | Built |
| 10zs.3 | W 8th | Street 5 m up at the intercity pair (157.7 m), allowed 2.5 m up under the APEx (161.7 - 6.5 - 152.7), so about 3.3% down to the APEx over about 75 m; Horne raised 5 m at W 8th (ramps about 100 m) | Built (markers) |
| 10zs.4 | Intercity pair | 1.71% from 144 m to W 8th (150.9 m, 145.2 m under Gest), then 2.92% to the CS bridge (162.3 m over W 6th). Portal in the south wall at 151.4 m; rails reach ground 42 m south of it | Built |
| 10zs.5 | Found | The pair crosses W 7th at about 153.0 m (0.4 m above the street) and Budd at about 154.9 m (2.4 m above), too close to pass over or under either. Already true at 3 m (151.4 and 153.6 m). Proposed: W 7th and Budd end either side of the pair | Open |

## 10zt. Viaduct and bridge footprints (2026-10-17, cut/structures.py, plots/patch_v48.py; page version 48)

| # | Item | Result | Status |
|---|---|---|---|
| 10zt.1 | Request (Ben) | A layer showing the width of the train viaducts (the CUT approach above all, for the lots either side; catenary and stations on them) and the other bridges and viaducts; Ben redraws the lots himself | Recorded |
| 10zt.2 | Rule | Footprint = track centre lines on structure, each widened 4.2 m beyond the outer track (overhead masts on the deck edge, walkway, parapet; drawing value from a 13.4 m double-track deck with 5.0 m centres), gaps under 6 m between tracks decked over, RER platforms on the structure added. Double track comes out 12.9 m, four APEx tracks 21.9 m | Working value |
| 10zt.3 | Structures | CUT approach viaduct south (21.9-44.9 m: APEx 4, Cardinal 2, CVG Express 2, freight passing track; field to the river); CUT platform deck (133.9 m); north arch viaduct (31.1-54.0 m, APEx, lower pairs, passing track, RER on the viaduct with Camp Washington); intercity pair from the W 8th wall portal (51 m trough, then 380 m on fill or viaduct to the CS span); C&O pair from south of W 6th (trough, then viaduct) and the TRIMET C&O viaduct to the bridge; APEx bridge, CVG Express span, CS and C&O bridges. Width labels where the width changes; click a footprint for its width range and tracks | Built |
| 10zt.4 | Not drawn | Road bridges (Roebling, Clay Wade Bailey, Cincinnati-Newport) and the L&N bridge: no widths set; ORR/Transvalley tracks on the north viaduct only where the RER structure list has them; the real CS and C&O truss widths are drawn by the same rule | Open |

## 10zu. The former deck edge cleaned (2026-10-17, cut/deckedge.py; page version 49)

| # | Item | Result | Status |
|---|---|---|---|
| 10zu.1 | Request (Ben) | Problems along the former deck edge: a zigzag line through blocks; B027 with a jagged east side and a sliver (FB005) beside it at McRoberts | Recorded |
| 10zu.2 | Cause | The deck outline was traced off the Sanborn zigzag edge symbol on a 2 m grid: steps of about 7 m, 2-6 m either side of the real line, on most of its length. Blocks the fill step could not join (held ones) or slivers it left kept that line | Found |
| 10zu.3 | Outline | Smoothed onto the middle of the zigzag (Gaussian along the ring, sigma 6 m; at most 4.0 m from the traced vertices); the traced outline is kept in fill/deck_outline_raw.json | Built |
| 10zu.4 | Blocks | In each street face (Ben's saved street edits included): B027 + FB005 and B035 + FB003 joined; pieces of SBB0169 and B052 reaching across the old edge given to the block holding that face; 85 slivers along the edge (0.42 ha) given to the block beside them; B026 and SBB1037 (both locked, with saved lot edits, split by Ben's Western Avenue extension) keep their own lots, the line between them now on the smoothed edge. Blocks are changed only within 10 m of the old edge | Built |
| 10zu.5 | Lots | Away from the old edge unchanged; across the 7 m zigzag band each lot is carried straight on, first on its own side of the smoothed edge, then across it where the other side had no lot; the four empty fill lots shared out the same way; one lot gone (B026-032, not in saved edits) | Built |
| 10zu.6 | Follow-up (Ben) | The issue was the lots: jagged lot lines and gaps along the old edge, still there after 10zu (only the 60 blocks it changed had their lots redone) | Recorded |
| 10zu.7 | Lots, every edge block (cut/edgelots.py, page version 50) | All 98 blocks within 7 m of the traced edge: each lot keeps its shape outside the zigzag band; inside it, and in any gap in the block, land goes to the lot beside it with its side lines carried straight (own side of the smoothed edge first). Notches the zigzag left in the block outlines next to streets filled (360 m2). Lot gaps 1,363 m2 before, 886 m2 after, all hairlines under 0.1 m wide; one lot gone (B050-039, not in saved edits). Ben's merges and uses still apply (checked at W Liberty / Horne); held blocks B026, B027, B035, B053, B088, SBB1037 had only their band lots redrawn | Built |

## 10zv. Sideways position for a narrower stretch of street (2026-10-17, plots/patch_v51.py; page version 51)

| # | Item | Result | Status |
|---|---|---|---|
| 10zv.1 | Request (Ben) | A way to line up a street whose two sides of a junction are not on one line or one width (Central Parkway north of Liberty) without an S-bend: the narrower part free to sit anywhere within the wider part's width, like a station's platforms | Recorded |
| 10zv.2 | Tool | In Edit mode pick two points (the stretch tool); after its width, a stretch narrower than the road on either side gets a sideways position: a slider and Left edge / Centre / Right edge, limited so it stays inside the wider road's width at both ends (when both neighbours are wider, inside both). Saved as edits.streets[id].ov, one offset per segment (+ to the left looking along the line), kept through point edits like the widths. The street's line stays straight; only the roadway moves. Lots follow it as for any street change. Tested on Central Parkway (30 m north of Liberty set to its east edge): no kink, lots on the west side take the freed land | Built |
| 10zv.3 | Follow-up (Ben: no option visible) | The sideways controls only appeared once a stretch was already narrower, so nothing showed on a one-width street. Now the width row has 'Sits on: the centre line / the left edge / the right edge of the road beside it / where it is now', applied with the width in one step; the slider still follows once narrower. The selection highlight follows the narrowed stretch; no disc where runs meet in a straight line. Clicked through on Central Parkway (points 113-119, 30 m, right edge): offset -7.86 m, edge in line (page version 52) | Built |
| 10zv.4 | Follow-up (Ben) | Wanted a slider at the point where a narrower street meets a wider one (e.g. Central Parkway point 106), not a stretch fixed to a side. Built (page version 53): pick that one point in Edit mode; the panel shows a slider from the wider street's right edge to its left edge. The narrower street's end moves across; its last straight turns about its far end (no kink at points along it); the wider street does not move. Saved as edits.streets[id].jo {point: offset}. The v51/v52 stretch side controls are removed from the panel. Clicked through on Ben's Central Parkway (point 106, 24.4 m into 45.7 m): slides 0 to 10.6 m either way, lots follow | Built |

## 10zw. The CUT box redrawn from Ben's GeoTIFF (2026-10-17, cut/cutplan.py, cut/cutplan2.py; page version 54)

| # | Item | Result | Status |
|---|---|---|---|
| 10zw.1 | Request (Ben) | The Kenner-Western-Hopkins-McLean box still wrong; Ben gave CUT_Layout.tif (the 1931 plot plan georeferenced to the real ground, EPSG:3857, 0.24 m pixels) and said the blocks are right | Recorded |
| 10zw.2 | Reference | Warped to EPSG:26916 at 0.25 m (cutgeo/cut_utm.png); the plan's mirror axis found by correlation: -3.35 degrees through E 713,380.0 N 4,331,839.25 (the 10zr axis was -3.0 degrees, 7.5 m north at Freeman); rectified onto that axis (cutgeo/rect.png) and traced on a 2 m grid | Done |
| 10zw.3 | Streets | Kenner on the plan's property lines, v +86.0 to +104.3 (18.3 m, its printed 60 ft; blocks start at 104.3-107.6); Hopkins the mirror line -86.0 to the blocks at -100.3 (14.3 m; the plan's own south property line is at -105.5, 5 m into the blocks, which Ben says are right); both straight and parallel to the axis Garrard to Freeman; Dalton and the Kenner/Hopkins cross streets (Denman, Hoeffer, Louisa, Harriet) end on the new lines; EZ1 on the plan axis at 47.0 m (the driveways, outer edge to outer edge) | Built |
| 10zw.4 | Terminal group | Building, concourse, headhouse, ramps, west park and square turned from -3.0 to -3.35 degrees onto the plan axis, front 5 m west to the plan's (fitted on the ramp arms and front); platforms polygon on the Kenner/Hopkins plaza lines | Built |
| 10zw.5 | Plaza | Traced from the plan and mirrored: forecourt and Plaza Driveway, the two straight driveways, terrace and cascade with the pergola pools, four forecourt lawns, the two triangle islands, the long north and south lawns with their walks, crossings and fountain circles, the central lawn (round ends) with the fountain ring, the drives along Kenner and Hopkins; 66 features. Blocks recut (35; 1.3 ha of freed land given to neighbours; no lots lost) | Built |
| 10zw.6 | Follow-up (Ben: follow the plans; park and buildings not linked) | Hopkins on the plan's property lines, -86.0 to -105.5 (19.5 m); the blocks south of it cut back. Terminal square, west park, west headhouse and the platforms polygon now one band from Kenner's south line to Hopkins' north line (172 m), with no block slivers between them and the streets (B040 gone); Garrard's stubs end at Kenner and Hopkins. The locked Lincoln Park block (SBB0453, type park) reshaped to the whole plaza east of the terminal as one park lot (its 56 1904 lots, none edited, replaced). Page version 55 | Built |
| 10zw.7 | Terminal footprint (Ben's georeferenced First Floor and Main Floor sheets, page version 56) | Both sheets rectified onto the plan axis (cutgeo/fl_*.png); their centre line lies 0.5 m south of the plot plan's (taken out). Building traced from the first floor and mirrored: front at u -434, wings to -545.5 (+-25 m), north and south blocks -512 to -493.5 out to +-57 m, rotunda wings to +-43.8 m, arms on one centre (-419, +-35.5), outer radius 49.5 m to their tips at about u -414; 11,780 m2 (was 11,439). Train concourse 24.5 m wide, from the west headhouse to the building. Bus and cab drives redrawn in the arms (radii 33-49.5 and 19.6-33, main floor). Platforms polygon ends at the building front. The APEx platform tracks agree with the main-floor platforms to about 2 m (not moved) | Built |
| 10zw.8 | Follow-up (Ben: wings off, west headhouse over the viaduct, back section wrong; page version 57) | Building outline now taken from the first-floor sheet's own cut-out edge (its alpha mask, cutgeo/mask.py), not traced or mirrored; checked by compositing the sheet onto the page render (cutgeo/pagecmp.py): arms, office blocks and back section on its lines. West of u -534 the track sheet covers the edge, so the back section's west face (u -545.5) is from the drawing. Bus and cab drives on arcs fitted to the sheet's arm edges (centre u -420.1, v +-35.9; radii 18.3 and 49.4), clipped to the building. West headhouse moved 3.2 m west to clear the station viaduct footprint (concourse lengthened to meet it). Viaduct layer now drawn under the terminal layers | Built |
| 10zw.9 | Follow-up (Ben: the back section's west side is angled, not square to the grid; page version 58) | Read off the first-floor sheet: the west wall runs parallel to the tracks, u = -545.3 - 0.08 (v - 11.8) (-546.3 at v 24.3, -541.8 at v -26.2); the back section and the concourse's east end now follow it | Built |

## 10zx. Transfer track, APEx switches, CVG taxiways (2026-10-18, cut/railx.py, cvg/taxi.py, plots/patch_v59.py; page version 59)

| # | Item | Result | Status |
|---|---|---|---|
| 10zx.1 | Request (Ben) | 1. transfer track from the freight track / platforms 13-14 to the CS bridge; 2. more streets west of the viaduct in Camp Washington, near Manhattan grid, blocks longer W-E; 3. switches on the APEx, mindful that turnouts are slow places on HSR; 4. CVG taxiways from CVG_Layout.tif (runways longer than on it) | Recorded |
| 10zx.2 | Transfer track | Single track, both ways: leaves the freight passing track at N 4,331,430, runs on the station viaduct 7 m west of Kentucky 1 across W 8th (about 6.3 m over the street where it has fallen toward the APEx), W 7th and Budd, then curves (tightest 216 m) onto the intercity east track at N 4,330,877 (161.1 m, easing down about 0.75%), north of W 6th; 579 m; 1:12 turnouts (about 60 km/h, 50 km/h on the curve); a 1:12 crossover between the intercity tracks just south so either CS bridge track is reached; platform track 14 to the passing track by a 1:9 connection (13 reaches 14 in the throat). Added to the viaduct footprint | Built |
| 10zx.3 | Switches | Throat turnouts where the platform tracks converge onto each approach track (12, 1:12, 60 km/h). Ladders just outside both throats, two staggered rows of 1:15 crossovers (80 km/h), so every platform reaches every approach track: south N 4,331,385 and 4,331,310 (Kentucky 1-4, Cardinal 1-2), north N 4,332,485 and 4,332,560. Open line: one pair of 1:46 crossovers (about 160 km/h diverging, line speed straight) per line in the map area, on straight track: north trunk between Ludlow and the Southwest Chief / Transcontinental split, Cardinal east, Cardinal / Floridian west. None on the Kentucky line between the throat and the bridge or in the tunnels. 17 crossovers, 50 switch points; turnout numbers and speeds are drawing values | Built |
| 10zx.4 | CVG taxiways | CVG_Layout.tif is the FAA airport diagram (January 2020), 4 m pixels, georeferenced (runways match the KMZ to a few metres). Grey pavement extracted (lettering closed, specks dropped), cut by the canon runways and buildings: taxiways and aprons 2.75 km2. Runways lengthened in canon: 18R/36L 2,744 m (diagram 2,438) and 18L/36R 3,658 m (3,048): their parallel taxiways carried on at the diagram's offsets (140 m, 173 m) with an entry at the new ends (dashed). 9L/27R and 18C/36C are the diagram lengths. 9R/27L (canon, not on the diagram) runs over the diagram's taxiway N; no parallel drawn for it yet | Built |
| 10zx.5 | Camp Washington grid | Not built: the N-S lines there are Ben's J1-J3 (100 m apart, 3.4 deg east of north) and the 1922 Follett, Roll, Dawson, Borden carried south (about 80 m apart, slanting the other way, so the blocks between them taper); E-W streets 74-172 m apart. Options put to Ben | Open |

## 10zy. Camp Washington grid; CVG airside designed (2026-10-18, cut/campw.py, cvg/airside.py, plots/patch_v60.py; page version 60)

| # | Item | Result | Status |
|---|---|---|---|
| 10zy.1 | Request (Ben) | Option A for Camp Washington; CVG taxiways smoother and like a real system for a very busy widebody hub (Pan Am hub; United, Delta, American; GE maintenance); gate pads at Terminal 1A; the diagram was inspiration, and the trace kept its lettering and lost HS 1 | Recorded |
| 10zy.2 | Camp Washington | West of the viaduct, Hopple to Ralston, Beekman to the trunk: Ben's J1-J3 kept (100 m apart, 3.36 deg), new avenues J5 and J7 every 200 m west (J7 runs out against Beekman); Follett, Roll, Dawson and Borden carried south removed; E-W streets kept and seven new ones (A-G, 15.2 m) where gaps were over 115 m, so they are 70-95 m apart. 62 blocks replaced by 115 street-face blocks, 1,899 lots square to the long side (10 m frontage, two rows when deeper than 55 m); no held blocks or saved lot edits in the area. The RER A Westwood viaduct crosses over the blocks. Pre copies fill/*_precampw.json | Built |
| 10zy.3 | CVG airside | Replaces the 10zx.4 trace. Designed on the canon runways (drawing values, ICAO Code E/F practice): 25 m taxiways on centre lines, full-length parallels 190 m off each runway (A east of 18R; C and D either side of 18C; T and S either side of 18L; K and M either side of 9L; N and R either side of 9R), entries at every runway end, two 30-degree rapid exits for each landing direction, crossing connectors every 800 m, links to the aprons, filleted junctions. Aprons round each concourse with 96 nose-in widebody stands (80 x 70 m: T1A 19, T1B 11, T1B/T4 bar 18, T4 12, T2 24, T3 12), taxilanes behind, run on to the nearest taxiway; stands in a runway strip (150 m) or a taxiway strip dropped (so none on T1B's west face). Cargo apron at the Amazon and DHL hubs, maintenance aprons in front of the hangar areas. 76 km of taxiway centre line, 1.8 km2 taxiway and 2.0 km2 apron | Built |
| 10zy.4 | HS 1 | On the FAA diagram HS 1 is a hot spot (a marked area where runway incursions have happened, at the 9/27 and 18C/36C crossing), not pavement | Noted |

## 10zz. CVG contact stands measured, large and smaller widebody; Terminals 1B and 4 moved north (2026-10-18, cvg/gates.py, cvg/gates_grid.py, cvg/airside2.py, plots/patch_v61.py; page version 61)

| # | Item | Result | Status |
|---|---|---|---|
| 10zz.1 | Request (Ben) | Measure how many gates fit at the terminals instead of guessing; read about CVG's terminals; split widebody stands into large (777, 747, A350) and smaller (767, 787, A330); terminals and taxiways may move | Recorded |
| 10zz.2 | Sizes (verified) | 747-8 span 68.40 m, length 76.25 m (Code F); 777-9 span 71.76 m extended, 64.84 m folded (Code E on the ground), length 76.73 m; 777-300ER 64.80 / 73.90 m; A350-1000 64.75 / 73.78 m; A330-900 64 / 63.69 m; A330-300 60.30 / 63.69 m; 787-9 about 60 / 62.8 m; 787-10 about 68 m long; 767-300ER 47.57 / 54.94 m. Clearances, ICAO Annex 14 Table 3-1 (2018 amendment) and 3.13.6: stand clearance 7.5 m (Codes D-F); stand taxilane centre line to object E 40 m, F 47.5 m; taxiway to object F 51 m (FAA 13B ADG-VI half-TOFA 167.5 ft agrees); taxiway to taxiway F 91 m. FAA 13B Tables 4-1, 5-1 and G-11/G-12 could not be read; runway to parallel taxiway 190 m stays a working value | Read |
| 10zz.3 | Stand classes | Large: 75.9 m wide (747-8 span + 7.5), 76.7 m deep (777-9), Code F taxilane (95 m object free area). Smaller: 71.5 m wide (A330-900 span + 7.5), 68.3 m deep (787-10), Code E (80 m). Nose 7.5 m off the building. The smaller class saves little because the A330-900 and 787-10 are nearly as big as the 777s; only the 767 is much smaller | Recorded |
| 10zz.4 | Method | Each terminal face, offset by the nose clearance, walked metre by metre; a stand fits where its envelope stays out of the buildings, the runway parking limit, the parallel taxiways' object free areas and other stands, with a clear taxilane object free area behind it. Mixed rows keep their taxilane behind the deepest (large) stand. Each taxilane runs on to the nearest taxiway; a corner or tip stand blocking a taxilane's way out is given up (6). Best of the terminal orders | Built |
| 10zz.5 | Terminals moved | Terminal shift trials: T1B and T4 together 90 m north opens the T1B/T4-Terminal 2 gap from 195 m to 285 m, so both faces take stands (the as-drawn gap fits one row); moving T2 or T3 south instead puts T3's south row onto taxiway K. Unshifted, the split layout fits about 127 | Built |
| 10zz.6 | Result (as built) | 141 contact stands: 57 large, 84 smaller (40% large): T1A 12 + 18, T1B 12 + 15, T4 12 + 19, T2 11 + 18, T3 10 + 14. All large: 134. All smaller: 153. 18 stands (T1A east face 7, T1B west face 8, T3 west wing 3) push back onto a runway's parallel taxiway | Built |
| 10zz.7 | Taxiways | Parallels as before (190 m); link F across the T1B and T4 tips moved north beyond the tip stands, with D and T carried north to it; hand links J, B, G, H and L replaced by taxilanes run on to the nearest taxiway | Built |
| 10zz.8 | Knock-ons | The RER CVG Terminal 1 and Terminal 2/3/4 stations (about N 4,325,540) are now 60-90 m south of the T1B/T4 bar, under the apron (a passage to the building); Ben's Terminal 4 CVG Express platform (offset 49 m) now only reaches the bar at its north end; sliding it about 100 m north would centre it | Open (Ben) |
| 10zz.9 | Canon check | Fact tracker: Terminal 1 (A-C) 48 gates (16 widebody), Terminal 2 42 (12), Terminal 3 32 (8), Terminal 4 28 (4): 150 gates, 40 widebody. Measured all-widebody contact capacity is 134-153, close to the 150 total, but the tracker's 40 widebody conflicts with "mostly widebody" (and with Pan Am mainline being 100% widebody) | Open (Ben) |
| 10zz.10 | Real CVG (OTL) | Terminal 3 (1994, Delta) with Concourses A, B (islands, people mover) and C (regional, closed 2008, demolished 2016); Terminals 1 and 2 closed 2006-2012 and demolished 2017; today one terminal, two island concourses, 51 gates | Read |

## 10zza. CVG gates against airline traffic (2026-10-18; analysis, nothing rebuilt)

| # | Item | Result | Status |
|---|---|---|---|
| 10zza.1 | Request (Ben) | Check gates per terminal against the airlines there; if the breakdown doesn't work, expand (longer like DEN, branched like ORD, or hubs like SFO Terminal 2) | Recorded |
| 10zza.2 | Demand (working values) | Canon passengers per terminal; seats: Pan Am 309 (canon fleet at range midpoints, 256 aircraft), Delta and United 280, T4 220; 82% load; design day 1.10 x average; peak-hour share 12% (hubs), 9% (T4); gate occupancy 2.5 h (hubs), 1.5 h (T4); 10% buffer. Need: Pan Am 64 (177 departures/day), Delta 44 (122), United 38 (104), T4 7 (40); total 153 against 141 built. Share of 141 by passengers: 61, 38, 32, 10 | Estimated |
| 10zza.3 | Breakdown | T1A+T1B 57 (-7), T2 29 (-15), T3 24 (-14), T4 31 (+24) | Doesn't work |
| 10zza.4 | Room to grow | T2 and T3 boxed in by taxiways D (west), T (east), K (south) and the T1B/T4 rows (north): no lengthening or branches in place. Measured options: courtyard pier off the T1B/T4 bar (ORD-style, shares the courtyard taxilanes) +19; midfield satellite on the Parking area between 18R, 18C and 9L +15 (E-W pier) to +17 (cross) | Measured |
| 10zza.5 | Options put to Ben | A: courtyard pier, Delta to T4 + pier, United T2 + T3, others T3 west wing, Pan Am takes T4's part of the bar (canon terminal assignments change); B: pier as Pan Am Concourse C + satellite split between Delta and United; C: satellite only | Open (Ben) |
| 10zza.6 | Canon flag | Fact tracker: Pan Am about 56.5 daily departures at CVG, which carries about 10.4M a year at 309 seats and 82%, against canon 32.7M | Open (Ben) |

## 10zzb. 1904 Sanborn extended: Times to Elsinore; Winton Place and Mitchell Ave to Ivorydale (2026-10-18, lph/solve_ext.py, lph/tiles_ext.py, lph/sheets_merge_ext.py; page version 62)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzb.1 | Request (Ben) | Extend the 1904 Sanborn to cover between the Elsinore and Times stations, and to Ivorydale (Mitchell Ave / Winton Place) | Recorded |
| 10zzb.2 | Sheets | Staged from Ben's computer: vol. 2 sheets 143, 144, 149, 150, 157, 158, 159, 160 (CHPL); vol. 6 sheets 647-656, 663, 664, 665 (LOC). Picks by six agents (sbg/picks/s*.json): 647 three panels (north, spring-grove-east, spring-grove-west), 649 main + inset, 650 main + north-east, 665 upper + lower | Read |
| 10zzb.3 | Fit (lph/tf_ext.json) | Existing frames fixed (sbg/fit/tf.json, lph/tf_all.json); new frames fitted to ties with them, ties between new frames, OSM corners (lph/osm_north.geojson, basin/osm_basin.geojson) and points on OSM centrelines of the picked streets; CHPL affine (shape and 2% scale holds), LOC similarity (scale held to 0.5%). Residuals mostly 1-3 m; Mitchell/Spring Grove cluster (649, 650, 656) about 8 m from today's Mitchell corner but tied to each other within 1.5 m (Mitchell jogs 43 ft at Spring Grove; legs tied leg to leg) | Built |
| 10zzb.4 | Ivorydale | 663 (one crossing), 664 (none), 665 lower (none): placed from hand-read points (June/Spring Grove just off 664, Beech/Spring Grove on 665), points on Spring Grove and June centrelines and the north arrows (lph/ext_extra.json); approximate (a few metres). Not placed: 649 inset, 650 north-east panel (one crossing each), 665 upper (Emery Candle Co.; its streets are not in OSM) | Built / Open |
| 10zzb.5 | Tiles | lph/tiles_ext.py: 26 tiles of deckpage/tiles_n re-rendered (panel polygons lph/panels_ext.json), index and overview rebuilt; 23 frames added to sheets.json (vol. 2 and vol. 6). Basin tiles stay on top where they overlap. Backups lph/tiles_n_pre_ext_bak/, deckpage/sheets_pre_ext.json. Streets not rebuilt from the new sheets | Built |
| 10zzb.6 | Gap | St. Bernard sheets 657-662 (between Mitchell Ave and Ivorydale east of Spring Grove) not included | Open |

## 10zzc. CVG: landside court cleared, terminals reshaped, stands matched to carriers (2026-10-18, cvg/gates.py, cvg/airside2.py, plots/patch_v63.py; page version 63)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzc.1 | Ben | T1B and T4 have landside portions (the arrivals and departures area inside the U had been filled with gates); T3 may change shape; T2 may be as long as T3; T1A may extend south into the parking area if Pan Am needs more | Recorded |
| 10zzc.2 | Landside | The court inside the U (between T1B's east face, T4's west face and the bar's north face, open to the north) kept clear: no stands, taxilanes or apron; drawn as area "Landside (T1B / T4)". Link F across the north removed (it closed the U's road opening); D and T carried 160 m past the north ends of 18C and 18L instead, for the T1B and T4 tip stands. The courtyard pier option (10zza.4/5) falls away | Built |
| 10zzc.3 | Reshaped | T3 a plain bar (west wing removed), E 702,000 to E 703,330; T2 the same length (west end out to E 702,000, both carried east to E 703,330, about 85 m short of taxiway T's object free area); T1A's stem carried south into the parking area to N 4,324,850 (parking area trimmed to what is left); T1B/T4 stay 90 m north (10zz.5) | Built |
| 10zzc.4 | Stands | 152 contact stands (60 large, 92 smaller): T1A 51, T1B 12, T4 18, T2 36, T3 35 (51+12+18+36+35 = 152). By carrier: Pan Am + Gateway 63 (T1A + T1B) against 64 needed; Delta + SkyTeam 44 (T2 36 + the 8 T4 bar stands facing T2) against 44; United + Star 35 (T3) against 38; American, Southwest and others 10 (T4 east leg) against 7. Stands carry an airline tag | Built |
| 10zzc.5 | Canon | Delta using the T4 bar stands that face T2 is a terminal-assignment change against the fact tracker (T2 D-F Delta, T4 I-J others) | Open (Ben) |

## 10zzd. Camp Washington streets scrapped for a new grid (2026-10-18, cut/cwscrap.py; page version 64)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzd.1 | Request (Ben) | Scrap every street between Spring Grove and Beekman, Hopple and Dreman (cut at those streets), except Geringer and J1 (they box in the viaduct), to rethink the Manhattan-style layout | Recorded |
| 10zzd.2 | Done | 27 streets deleted through the saved layout (del flag, reversible): the campw18 avenues J5, J7 and streets A-G, the carried-west Alabama, Monmouth, Sassafras, Arlington, Marquis, Adelaide, Brashears, Earl, Whiteley, and Borden, Dawson, Follett, Johnson (2), Ralston, Roll, Ledlie and two unnamed. Cut at the boundary (saved layout geometry): J3 (489 m left south of Hopple), Stock, Adelaide, Alabama, Bates, Ethan, Ford, Llewellyn, Marquis. 128 blocks and 2,242 lots removed (no held blocks or lot edits). deck/layout written at version 1033 -> 1034; pre copies fill/*_precwscrap.json | Built |
| 10zzd.3 | Next | New street grid for the cleared area | Open (Ben) |

## 10zze. CVG stands to real planning standards; T4 small widebodies; tunnel notches; grounds and landside (2026-10-18, cvg/gates.py, cvg/airside2.py, plots/patch_v65.py; page version 65)

| # | Item | Result | Status |
|---|---|---|---|
| 10zze.1 | Request (Ben) | Look up how gates are designed and laid out; the T1A and T1B notches are the tunnel between them (smaller is fine, must line up); T4 mostly small widebodies (767-200, 787-8 or smaller); CVG Grounds.kmz is the buildable area and CVG Landside.kmz where gates cannot go; T1B may go north (pull the U, the end of 18C/36C and taxiway A north) | Recorded |
| 10zze.2 | Research (agent) | PANYNJ Terminal Planning Guidelines: nose to building 37 ft (ADG V/VI), 25 ft wingtip clearance, 5 ft tail clearance, tail-of-stand road (FAA AC 150/5360-13A: 20-25 ft), stand depth 275-285 ft (777-9 / 747-8), 2-3 bridges per widebody gate, no single taxilane for more than 8 contact gates (dual taxilanes), turn times ADG V 90 min / VI 105 min plus 15-20 min buffer. FAA 13A taxilane CL to object ADG V 138 ft, VI 167 ft; ICAO stand taxilane CL to CL E 72.5 m, F 87.5 m. Facing piers: about 377-384 m face to face with dual taxilanes, about 296 m with one. HKG about 930k passengers per contact stand (35% of passenger stands remote); ATL about 540k per gate. 787-8 60.1 / 56.7 m; 767-200 47.6 / 48.5 m | Read |
| 10zze.3 | Model | Nose 11.3 m off the facade; envelope = length + 1.5 m + 7.6 m road; behind it the taxilane object distance (ADG VI 51 m, V 42 m) plus half the dual-taxilane spacing; facing rows may not share a lane; nothing outside CVG Grounds or in CVG Landside. Classes: large (747-8 / 777-9), smaller (A330-900 / 787-10), small (787-8, T4 only) | Built |
| 10zze.4 | Layout | T1B/T4 back in place (Ben's landside U); T1A and T1B tunnel notches cut to 40 by 15 m and centred on the CVG Express line (N 4,326,072); T1B carried north to N 4,326,880 inside the grounds; T2 at net +11 m and T3 at net -82 m from their drawn positions (best of a position search) | Built |
| 10zze.5 | Stands | 126: T1A 42, T1B 8, T4 18 (small), T2 22, T3 36 (42+8+18+22+36 = 126). Carriers: Pan Am 50, Delta 31 (T2 22 + 9 T4 bar stands facing T2), United 36, others 9 | Built |
| 10zze.6 | Demand | Peak-hour method (10zza.2): Pan Am 64, Delta 44, United 38, others 7 (153). Turn-based check (3.5 turns a gate a day): Pan Am 51, Delta 35, United 30, others 7 (123) | Estimated |
| 10zze.7 | Knock-ons | T3 CVG Express platform (Ben's offset -50 m) now about 35 m north of T3: slide about 60 m south; T2 platform still on T2 | Open (Ben) |
| 10zze.8 | Options | Concourse C west of T1A's stem (branch off the north arm into the parking area): measured +38 stands; T1B north beyond the grounds (Ben's offer) | Open (Ben) |

## 10zzf. CVG empty faces and the T2 hole fixed (2026-10-18; page version 66)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzf.1 | Ben | Why are there big empty spaces at T1A and T1B and a hole between T2 and T4? | Recorded |
| 10zzf.2 | Causes | (1) With the real stand depth (97 m for a 777-9 stand) the T1A east and T1B west faces sat too close to the 18C parallels (190 m off, a working value): tails reached the taxiway object free area, so most stands failed. (2) T2 had been put 11 m north of its drawn spot: 187 m to the bar, too little for a row on either side | Found |
| 10zzf.3 | Fixes | Parallels 550 ft (167.6 m) off the runways (FAA AC 150/5300-13A Table 3-5 notes: approaches below 1/2 mile; CVG elevation under 1,345 ft); small (787-8) stands allowed as a fallback where nothing larger fits; T2 14 m south of its drawn spot (T2 north row faces the bar across one taxilane), T3 92 m south (T3 south row pushes onto taxiway K) | Built |
| 10zzf.4 | Stands | 153: T1A 53, T1B 16, T2 37, T3 38, T4 9 (53+16+37+38+9 = 153). Carriers: Pan Am 69, Delta 37, United 38, others 9. Against need: peak-hour 64/44/38/7, gate-turn 51/35/30/7 | Built |
| 10zzf.5 | Knock-ons | CVG Express T3 platform about 45 m north of T3 (slide about 50 m south); T2 platform about 5 m south of T2 | Open (Ben) |

## 11. Current best pipeline

1. Georeference: joint model (2.9).
2. Labels: index from LiDAR on unchanged ground, 5 ft by propagation (8.2).
3. 1912 surface: free-level fit (8.6).
4. Erase every building, street (with shoulders), big footprint and stepped flat pad; refill with the membrane/thin-plate average (10b.1).
5. Works and big changes: 1912 surface where contours are dense, edge refill where sparse, feathered 10 m before filtering (10b.2).
6. Developed ground: LiDAR shape above 30 m plus 1912 surface texture below 30 m; natural ground: lightly smoothed LiDAR (10b.4).
7. Whole survey: 67 tiles, edge-trimmed tent blend, filled cover mask (10c).
8. Map 3: real-only zones v2 rebuilt from the 1950s sheets (10g), imprint removed (10h), canon interstates v3 (5.4), riverworks (10d), Kentucky works (10f).

Superseded by this: the combo core split (10.1-10.4) and trial 4 as the outside-core treatment (9).

## 12. Don't retry

- Re-running deck/joint.py or using deck/sheet_tf.json: the deck sheets are now fitted by lph/solve_all.py (10t); the old fit had 33-35, 47 13-20 m west.
- Correlating 1904 Sanborn ink against the 1922 plates (10t.15).

- Gaussian smoothing as the imprint fix (6.1, 6.2, 10.11).
- LiDAR point classes for roads or buildings (6.5).
- Band clip as a remover; frequency split (7.3, 7.4).
- Per-sheet affine, lens, or unconstrained per-sheet polynomial georef (2.5, 2.6, 2.8).
- 5 ft labels from LiDAR rounding, S25 rounding, or counting alone (3.2, 8.1).
- Surface fits that treat 5 ft labels as fixed heights (8.3-8.5).
- OSM-free automatic zones as the primary zone set (4.1).
- Ink-density core with under about 100 m support (10.2).
- Membrane-only refill; thin plate alone across very large holes (10.7, 10.8).
- Erasing every footprint on flat ground (10.9).
- Tesseract on the warped 0.5 m mosaic (10.13).
- Tesseract for Sanborn use labels: rotated and small lettering lost; vision agents on gridded crops read them (10zf.3).
- Tile blend weights that reach the window edge (10c.6).
- Neighbourhood filters (trend, area filter, median) run right to a window edge: compute with a margin and feather (10h.8).
- Tracing a street map from survey ink (skeletons, Voronoi centrelines) when a clean plan is wanted: build it from picked intersections instead (10m, 10n).

## 13. Tooling lessons

- Long jobs under nohup, but the workspace is reclaimed when the session goes idle and takes background jobs with it; for runs of hours, stay in session and poll in foreground waits of up to 10 minutes.
- Kill by PID, never pkill -f (it killed the shell, again on 2026-10-08).
- A pyamg hierarchy solves the matrix it was built from; when weights change, rebuild it or use it only as a CG preconditioner.
- scipy binary_dilation with iterations=0 dilates until nothing changes.
- A `cmd | tail` exit code reflects tail, not the script.
- Committing to Ben's computer: files over about 30 MB fail by staged path, and SendUserFile also caps at 30 MiB; deflate with predictor=2 halves an int16 GeoTIFF, LZMA is worse, and past that split the raster.
- Log end markers: test the last line (tail -1), since old ALL DONE lines stay in the log.
- Never pipe a long script into head: it dies on the next print after head exits, leaving stale outputs.
- Build big area works on per-work crops; index-returning distance transforms over a whole 50 Mpx window exhaust 7 GB.

- One I4 tile peaks at 3.5 GB; the workspace has 7 GB and 2 CPUs, so tiles run one at a time.

- Shell calls stop at 2 minutes: run fits and warps under nohup and poll.
- Publishing to an artifact this session has not read is refused once and counts as the read; republish the same file.
- Eighteen agents saving zoom tiles filled the session's disk allowance (157 MB left); tell agents to keep zooms small and delete them, and clear their folders after.
- JSTS overlays throw on near-coincident edges: wrap every union, difference and intersection with fallbacks (10zf.5). In node, run JSTS inside its own vm context (arrays from another context fail its instanceof checks).

## 14. Open

- 10za (built, page version 27): north of Ludlow at grade not laid out (B on its KMZ line, 11 m west of where it leaves the viaduct; Northside's position against the APEx and ORR tracks); R5's levels west of the trunk; D's extra trains east of CUT on A's tracks (10za.33); TRI seat count (export 1,000-1,200 too low); the corridor past the deck's east edge at Camp Washington; I-75 trench offsets north of Ford; St. Bernard X2 crossing (10za.21).
- 10z: RER D's two lines north of the deck tip (10z.12); Garrard cut by the APEx ramp north of Marshall (10z.13); tracker 2J vs the 1913 deck (10y.6).
- 10v: RER D at the deck's north end (10v.3); Hopple and Ludlow levels are drawn from draft deck and APEx levels (10v.4, 10v.5); the west bank west of State and Beekman (South Fairmount, Price Hill side) still has no street lines.
- 10u: Hopple viaduct level over the APEx ramp (10u.7).
- 10t: Ben to confirm the reading of "the rest of the deck" (10t.2); creek mouth at W 6th (10t.9); 460 lower panel and 605 unplaced; 458, 459, 465, 474 not picked (west of State); relief and the 1912 survey tiles stop at N 4,335,700 / 4,333,750, so the north shows Sanborn, streets and transit only.

- Sanborn sheets: the workspace shell can't reach loc.gov, but the built-in browser can (tested). Maps\Sanborn\sanborn_download.py pulls, from Ben's own computer: Covington 1909 (115), Newport 1910 (90), Cincinnati 1904 vols 3-7 (108, 108, 108, 118, 121; vol 2 is index only, vol 1 not online) and 1922 vols 1-2 (107, 97 images; double plates as L/R halves), about 3.7 GB. 1934-1950 editions are also online. Run --index first to pick sheets.

- 1912 river level for maps 1-2 (both banks sit on today's pool).

- Ohio bed (10i): Metro river crossings must drop 14.5-32.4 m to meet the tube rule (cover 2.2 m) (re-solve Lines 1, 2, 3, 6, 8, 10, 11); canon bridge set to reconcile (June 15 road-bridge list, plus the Cincinnati Southern, C&O and L&N rail bridges; Brent Spence and Daniel Carter Beard out).

- Lunken: the raised levees stop at the riverworks window's east edge (-84.398); rebuild them on a wider crop before rendering a map that extends east of it. No Metro line crosses there.

- Riverside works zones where adjacent tiles disagree (10c.5): one shared 1912 label pass across tile overlaps would remove the disagreement.
- Basin: apply B (10.10) with blended refill, or anchor the basin with printed elevations (read by eye for the pilots, digit templates on the original scans for all 48 sheets) and use the 1912 surface there.
- Seam where the 1912 survey ends: needs the 1914 USGS surface.
- Flat-pad finder still untested on a parking-heavy area.
- I-71 crossing vs tracker 4B; I-75 wording vs 4B.
- Earlier staged tracker items (2B, 2D, 2C, 2K, 2I, KY schedule), 20 ft separation rule, platform length.
- Basin streets (10n-10q): widths printed without a side ("narrows to 10' above York") still apply to the whole run; E Court Vine-Walnut as one 126 ft band or two roadways (10p.6); Fountain Square Metro platforms, side (station model) or island (10j.4) (10p.10); sheet 17 lower frame (Mill Creek mouth) not fitted; E 6th SW of Eggleston, John north of George and W 7th east of Melvin to recheck; unnamed alley pieces. (CUT east forecourt strip: replaced by the 1931 plaza, 10zh.3.)
- Deck street map: roundabout placement against the Harrison crossing (10k.12); boulevard and roundabout widths; regenerate blocks from Ben's saved page edits (since 10zb also transit lines with curves, station platform settings and deletions, block names and the new types); fit the 9 remaining sheets if the Price Hill edge or North Fairmount matter.

- CUT approaches (10l): TRI B/D east flank (10l.9); Lines 7, 8, 10 profiles against the -2 box (10l.10); Line 4 between Garrard and Chinatown against the CS pair (about 150 m vs 148.9 m); TRI A drop to 135.9 m; W 8th hump (10l.12); Transvalley and intercity frequencies (placeholders in 10l.2).

- Staged for the tracker from 10l: CUT levels (APEx platforms on the arch viaduct at about 160.3 m, level with the rotunda; -1 Hartwell concourse at street level; -2 lower platforms at 144 m, centred; Metro at CUT below the lower level); 2J restated (approach on a Glebe-type arch viaduct over the deck streets, widened over time; lower-level and TRI tracks under the deck, which is what the approach electrification ventilates); APEx islands 1-2 2,400 ft to about 1,600 ft; lower platforms all 305 m, centred under the APEx field; lower pairs dive between Bank and Findlay (10l.30).

- Kentucky: APEx portals toward Erlanger and RER E levels at the three-level points (10zj.3, 10zj.4); intercity south traffic placeholder; spare pair if traffic grows (10zi.5).

- Plots: method to be chosen and the lots redrawn (10zg.4), keeping locked blocks as they stand (10zk.5); angled lots (10zg.3).

- CVG Express: yard tracks not drawn; the RER depth at CVG and the 12 m under the creek valley are working values; Ben said 1 or 1b and the KMZ has five stop points, so it is built as 1 (1b would merge T2 and T4 into one stop between them) (10zm).

- CVG Express platforms: 200 m against three 67 m units (201 m) (10zn.5).

- W 7th and Budd across the intercity pair (10zs.5).

- Structures layer: road bridge and L&N widths; ORR/Transvalley on the north viaduct (10zt.4).

- CVG: Delta on the T4 bar stands (10zzc.5); United 3 short (10zzc.4); Pan Am daily departures vs passengers (10zza.6); canon gate counts against the measured 134-153 widebody contact stands (10zz.9); RER and T4 CVG Express stations against the moved T1B/T4 bar (10zz.8).


## 10zzg. CVG: Pan Am held to 60 stands, Delta 2:1, 797 stands (2026-10-18, cvg/gates.py, cvg/stem.py, cvg/airside2.py; page version 67)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzg.1 | Request (Ben) | Shorten T1A's south stem to give Pan Am 60 stands (slightly under the peak-hour need, not enough to force new construction); Delta 2:1 smaller (A330/767/787) to large (747/777/A350); add the 797 to the rotations | Recorded |
| 10zzg.2 | 797 stand | Canon (fact tracker) gives the 797-6 (200 seats, 5,500 nm) and 797-7 (235 seats, 5,200 nm), twin-aisle 2-3-2, but no dimensions. Stand sized on the 767-300ER (47.57 m span, 54.94 m long, Code D) as a stand-in; the 767 now uses this stand too | Placeholder (Ben) |
| 10zzg.3 | Mixes | Pan Am from the canon fleet (midpoints): large 777-8 70 + 747-10 15 + A350-1000 7 = 92; smaller 787-9 75 + 787-10 18 = 93; 797 20 + 51 = 71; shares 36 / 36 / 28%. Delta: large, smaller and 797/767 a third each (smaller plus 797/767 = 2:1). T3 unchanged (large 40%); T4 787-8 class | Built |
| 10zzg.4 | Stem | T1A stem south end moved from N 4,324,850 to N 4,325,320 (470 m shorter); the parking area takes the land back | Built |
| 10zzg.5 | Stands | 148: T1A 42 (16 large, 14 smaller, 12 797), T1B 18 (7, 6, 5), T2 41 (14, 13, 14), T3 38 (15 large, 22 smaller, 1 small), T4 9 (787-8). 42+18+41+38+9 = 148. Carriers: Pan Am 60, Delta 41, United 38, others 9 | Built |
| 10zzg.6 | Against need | Peak-hour 64 / 44 / 38 / 7; gate turns 51 / 35 / 30 / 7. Pan Am 4 and Delta 3 under peak, both over the gate-turn figure | Recorded |


## 10zzh. CVG: 797 sized as a 767-200; parking rules (2026-10-18; page version 68)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzh.1 | Ruling (Ben) | The 797 is 767-200 size: the middle ground of widebody capacity and efficiency on a narrow-body footprint, a larger A321XLR (APEx takes most short-haul; in this timeline the A310 also sold much better). A 797 can park at any CVG stand; smaller widebodies can park at large stands; 747s only at large stands | Recorded |
| 10zzh.2 | Stand | 797 stand now 767-200 span and length (47.57 / 48.51 m, Code D; was the 767-300ER stand-in, 54.94 m long). The 767-300 moves to the smaller widebody stand | Built |
| 10zzh.3 | Stem | Shorter stands let the stem shrink again: south end N 4,325,400 (was 4,325,320; 550 m shorter than version 66) | Built |
| 10zzh.4 | Stands | 148: T1A 41 (15 large, 13 smaller, 13 797), T1B 19 (7, 6, 6), T2 41 (14, 13, 14), T3 38 (15, 22, 1 small), T4 9 (small). 41+19+41+38+9 = 148; by class 51 + 54 + 33 + 10 = 148. Carriers: Pan Am 60, Delta 41, United 38, others 9 | Built |
| 10zzh.5 | Check | Under the parking rules the 797 stands are the only ones a 787 or larger cannot use. Pan Am at fleet shares: large 36% of 60 = 21.6 against 22 large stands; large plus smaller 72% = 43.2 against 41 large-or-smaller stands (2 short) | Open (Ben) |


## 10zzi. CVG: four stand sizes and five A380 stands (2026-10-18; page version 69)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzi.1 | Ruling (Ben) | Three stand sizes plus A380: small widebody (797-size), widebody (787-size), large widebody (747-size), A380-compatible (also the 777X with wingtips extended). Ben supplied a wingspan and length table for every widebody since 1969 | Recorded |
| 10zzi.2 | Sizes (Ben's answers) | Small: 767-300ER with blended winglets, 50.9 x 54.9 m (797, every 767-200/300, A300, A310). Widebody: 64.8 m span (A350-900 / 777-200LR) x 68.3 m (787-10): every 787, A330, A340-200/300/500, A350-900, 777-200 family. Large: 747-8 span 68.4 x 777-9 length 76.7 m: every 747, 777-300/ER, A340-600, A350-1000, 777X folded. A380: 79.8 x 76.7 m. The separate 787-8 class is gone; T4 is two-thirds small, one-third widebody | Built |
| 10zzi.3 | A380 stands | 5 at Terminal 1: 3 for Pan Am's A380s (T1A), 2 for Gateway partners (T1B). Never given up for a taxilane run-out | Built |
| 10zzi.4 | Canon flag | The fact tracker's 2025 Pan Am mainline fleet lists no A380 (A350-1000 is its only Airbus) | Open (Ben) |
| 10zzi.5 | Stem | T1A stem south end N 4,325,270 | Built |
| 10zzi.6 | Stands | 149: T1A 43 (3 A380, 14 large, 14 widebody, 12 small), T1B 17 (2, 6, 5, 4), T2 41 (14 large, 13 widebody, 14 small), T3 38 (14, 23, 1), T4 10 (3 widebody, 7 small). 43+17+41+38+10 = 149; by size 5 + 48 + 58 + 38 = 149. Carriers: Pan Am 60, Delta 41, United 38, others 10 | Built |
| 10zzi.7 | Nesting check | Pan Am at fleet shares: large 21.6 against 25 A380-or-large stands; large plus widebody 43.2 against 44 stands that take them. The 2-stand shortfall in 10zzh.5 is gone | Recorded |


## 10zzj. CVG: A380 stands together at T1B north; T1A north side large; United 30:50:20; 18C moved north (2026-10-18; page version 70)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzj.1 | Request (Ben) | All A380 stands together at the north end of T1B (prestige spot, seen from the interstate); T1A's north side almost all large widebody for the same reason; United 30:50:20 large:widebody:small; pull 18C north per new 18C.kmz | Recorded |
| 10zzj.2 | 18C/36C | New centre line N end (701,695.7, 4,326,982.8), S end (701,771.8, 4,323,629.8): moved 434 m north, length unchanged (3,353.9 m, 11,000 ft); its south end now clears 9R/27L. Base file deckpage/airport_v58b.json; taxiway D's 160 m north run-on dropped (no longer needed) | Built |
| 10zzj.3 | Zones | cvg/gates.py zones: T1B north leg (N of 4,326,330) takes the 5 A380 stands first (west face, N 4,326,439 to 4,326,788); T1A north arm's north face takes large stands first: 7 large plus 1 widebody at the elbow | Built |
| 10zzj.4 | Stem | T1A stem south end N 4,325,340 | Built |
| 10zzj.5 | Stands | 150: T1A 43 (15 large, 15 widebody, 13 small), T1B 17 (5 A380, 4, 4, 4), T2 41 (14, 13, 14), T3 39 (12, 19, 8), T4 10 (3 widebody, 7 small). 43+17+41+39+10 = 150; by size 5 + 45 + 54 + 46 = 150. Carriers: Pan Am 60, Delta 41, United 39, others 10. United 12/19/8 = 31/49/21% | Built |
| 10zzj.6 | Nesting check | Pan Am: 24 A380-or-large stands against 21.6 large aircraft; 43 stands that take widebodies against 43.2 | Recorded |


## 10zzk. CVG: T1A stem tip stand moved to the west end (2026-10-18; page version 71)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzk.1 | Request (Ben) | Remove the angled stand off T1A's stem tip and put it somewhere else, such as a slightly longer T1A west end | Recorded |
| 10zzk.2 | Done | No stand may start south of the stem's end (blocked zone, cvg/gates.py); T1A's west end carried 40 m west (to E 700,790); the west tip now takes a small (797-size) stand facing west. Stem end unchanged at N 4,325,340; the north face keeps its 7 large stands | Built |
| 10zzk.3 | Stands | Unchanged totals: 150; T1A 43 (15 large, 15 widebody, 13 small); Pan Am 60 | Built |


## 10zzl. CVG: stands squared to the facades; atria and T1B tip cleared (2026-10-18; page version 72)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzl.1 | Request (Ben) | Remove T1B stand 42 (north tip); stand 147 cannot go in front of T1A's atrium (the tunnel notch); stands must not sit at strange angles, and where the terminal's shape causes it, smooth the shape | Recorded |
| 10zzl.2 | Placement | cvg/gates.py: each stand now faces the chord of the nose line it covers, and is refused where the nose line strays more than 3 m off that chord (a frontage across a corner); on a gentle curve the stand steps out by the bulge to keep the 11.3 m nose clearance. Keep-out areas in front of both tunnel atria (T1A notch; the T1B notch at the other end of the same tunnel) and T1B's north tip | Built |
| 10zzl.3 | Shapes smoothed | T1B's outer curve a true arc (R 234 m) and its inner curve (R 189 m); T1A's inner elbow corner a concave arc (R 82 m) in place of the 45-degree chamfer; T4's south-east corner a true arc (R 116 m). Only the T1B outer arc still takes stands (two, fanned with the curve) | Built |
| 10zzl.4 | Stem | T1A stem south end N 4,325,240 (100 m longer than version 71) to hold Pan Am at 60; west end stays 40 m out | Built |
| 10zzl.5 | Stands | 148: T1A 43 (16 large, 15 widebody, 12 small), T1B 17 (5 A380, 4, 4, 4), T2 39 (13, 13, 13), T3 39 (11, 19, 9), T4 10 (3 widebody, 7 small). 43+17+39+39+10 = 148; by size 5 + 44 + 54 + 45 = 148. Carriers: Pan Am 60, Delta 39 (lost its two angled end stands), United 39 (28/49/23%), others 10 | Built |


## 10zzm. CVG taxiways replanned from gate-to-runway route trials (2026-10-18, cvg/taxi_trial.py, cvg/airside2.py; page version 73)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzm.1 | Request (Ben) | Fix taxiways that don't make sense; trial paths for planes to and from the gates and runways. 18R mostly Pan Am; 18C and 18L the other airlines (harder to reach from T1, but still reachable) | Recorded |
| 10zzm.2 | Trial method | cvg/taxi_trial.py builds the taxiway graph (runway centre lines node it; a path may cross a runway but not run along one), joins every stand to its taxilane, and routes each stand to every runway's departure threshold and from every exit angled for the landing direction (1,500 m roll or more) to the stand; reports mean distance, runway crossings and unreachable stands per terminal and runway direction | Built |
| 10zzm.3 | Faults found (version 72) | 11 T1A stands unreachable (T1A's east taxilane ran 16 m beside taxiway C without joining it); 41 dead ends (parallels overrunning the thresholds by 60 m, maintenance and cargo links stopping 7-20 m short of their taxiways, a crossing stub to nothing west of 18R); rapid exits of opposite directions meeting or crossing (X shapes on 18C and 9L) and an 18R exit cutting through a connector; S east of 18L serving nothing; M running the whole south side of 9L with nothing west of C; only two incidental ways across 18C | Found |
| 10zzm.4 | Plan | A (east of 18R) only, carried south to K; C and D both sides of 18C; T (west of 18L) only, S removed; K north of 9L the full length and on east to T; M from C east to T (maintenance aprons); N and R for 9R (maintenance, cargo). Parallels run threshold to threshold. Rapid exits only into A, C, D, T, K and R, placed by a solver: first exit about 1,750 m into the roll, second about 2,350 m where room allows; none within 250 m of another runway, none across another parallel, opposite-direction exits on one side at least 620 m apart when they point at each other, none across a crossing. Crossings of 18C: B (T1A's north taxilane to D: Pan Am T1B to and from 18R) and E (just south of T1A's stem); K-M and N-R crossings and single-side connectors about every 750 m clear of the exits and 200 m off runway intersections. A taxilane duplicating a parallel is dropped (its stands push back onto the parallel); taxilanes still ending in the open are turned square onto the nearest taxiway; any loose piece is joined by the shortest clear link | Built |
| 10zzm.5 | Results | One connected network; no unreachable stand. Mean taxi distance (departure / arrival, km): T1A 18R 2.33 / 1.93, 36L 2.34 / 1.80, no crossings; T1B 18R 2.88 / 2.89, 36L 3.03 / 2.35, one crossing (18C at B); T2 18C 2.60 / 1.62, 18L 1.87 / 2.58; T3 18C 3.06 / 1.27, 18L 2.29 / 2.18; T4 18L 0.61 / 2.56, 18C 3.53 / 2.95. Departures from 36C and 36R cross 9L or 9R (those thresholds lie south of the crosswind runways) | Built |
| 10zzm.6 | Flag | 9R/27L's west 750 m (west of about E 701,457) lies outside CVG Grounds.kmz, so N and R stop at the boundary and the 9R threshold cannot be reached | Open (Ben) |


## 10zzn. CVG runway roles, holding bays, exits and crossings from ORD, LAX, JFK and BOS practice (2026-10-18; page version 74)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzn.1 | Request (Ben) | Provide for lining up and traffic near the runways; use it to plan the exits; limit runway crossings; study ORD, LAX, JFK, BOS. Ben supplied takeoff and landing field lengths by type | Recorded |
| 10zzn.2 | Research (agent) | ORD: six parallels, crossings cut from six to two; the runways nearest the terminals depart (9R/27L, 10L/28R), the outer ones arrive; central deicing facility off the terminals. LAX: outboard runways arrive (24R/25L), inboard depart (24L/25R); 25L moved 55 ft south and a 10,000 ft centre taxiway (2008) so 25L arrivals hold there before crossing 25R. JFK: Bay Runway hold pads at the departure end let aircraft bypass those held; high-speed exits added on 13L-31R and 4L-22R; surface metering (aircraft wait at the gate). BOS: 9,300 ft centerfield taxiway (2009) between 4R-22L and 4L-22R to cut crossings of 4L-22R and add queuing room. FAA AC 150/5300-13B: bypass taxiways (4.8.3), holding bays at runway ends (4.9), end-around taxiways (4.12); EB 75: limit crossings of active runways, no straight access from an apron onto a runway. ICAO Doc 9157 Part 2: touchdown ~450 m in for categories C/D, exits ~450 m apart to within 600 m of the far end; 95% of category D aircraft can exit within 2,950 m. AC 13B exit-distance figure not read (FAA site blocked) | Read |
| 10zzn.3 | Runway lengths | 18R/36L 2,744 m (9,000 ft); 18C/36C 3,354 m (11,000 ft); 18L/36R 3,658 m (12,000 ft); 9L/27R 3,657 m; 9R/27L 3,050 m. Ben's takeoff lengths (sea level, 30 C, MTOW): 777-300ER 3,215 m, 747-8 3,260 m, 787-9/-10 2,800 m, A350-900 2,600 m; landing lengths 1,370-2,195 m. 18R is too short for long-haul heavies at full weight but ample for landings | Found |
| 10zzn.4 | Runway roles (ORD/LAX pattern) | 18R/36L arrivals (Pan Am, T1A); 18L/36R arrivals (T2, T3, T4; T1B in north flow); 18C/36C departures for everyone (T1A by C, the rest by D: no crossing); 18L also takes heavy departures needing 12,000 ft. T1B arrivals in south flow land 18R and cross 18C at B, behind departures that have started their roll (2.8 km) or land 18L with no crossing (4.2 km) | Proposed |
| 10zzn.5 | Exits | Arrival runways: exits aimed at 1,600, 2,050, 2,500 and 2,950 m (within 600 m of the far end), staggered by the solver. 18C: one each way each side (~1,900 m). Crosswinds unchanged | Built |
| 10zzn.6 | Crossings | 18C crossed only near its departure ends: B ~430 m from the 18C threshold, F ~420 m from the 36C threshold, plus the threshold and second entries; the mid-field crossing E removed | Built |
| 10zzn.7 | Departure ends | Second entry 150 m in from every threshold of the three north-south runways. Holding bays (a bypass taxiway 91 m outboard, joined at both ends, 85 m clear of other taxiways, 51 m clear of buildings and stands): 18R and 36L (A), 36C (C and D), 36R (T). Holding aprons (stubs): 18C (C 260 m, D 150 m, squeezed by T1A and T1B's A380 stands). None fits at the 18L end (T4 and the boundary) | Built |
| 10zzn.8 | Trial (plan flows) | Arrivals: T1A 18R 1.8 km / 36L 1.65 km, no crossing; T2 18L 2.7 / 36R 1.3; T3 2.3 / 1.3; T4 2.7 / 0.6; T1B 36R 2.6. Departures 18C: T1A 2.3, T1B 1.1, T2 2.6, T3 3.1, T4 3.5 km, no crossing. North-flow departures from 36C and 36R cross 9L or 9R (crosswinds, inactive in normal flow) | Built |
| 10zzn.9 | Open | South-flow departures from T2-T4 to 18C taxi north on D past T1B's A380 stands, whose pushback lane is D; small holding apron only. Options: meter at the gate, or send T2-T4 departures to 18L in south flow | Open (Ben) |


## 10zzo. CVG: 9R taxiways to its west end; gate hold (2026-10-18; page version 75)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzo.1 | Ben | 9R still needs taxiways; gate hold is fine for south-flow departures from T2-T4 (10zzn.9) | Recorded |
| 10zzo.2 | 9R | 9R/27L's own taxiway corridor (runway to 60 m beyond each parallel, 80 m past each end) is allowed past CVG Grounds.kmz, so N and R now run to the 9R threshold with its entries and the west N-R crossing; C and D carried south past 36C's threshold to N | Built |
| 10zzo.3 | Gate hold | South-flow departures from T2-T4 to 18C are metered at the gate (JFK practice); no queue on D past T1B's A380 stands | Decided |


## 10zzp. KMZ export: CVG folders (2026-10-18; page version 76)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzp.1 | Request (Ben) | Add CVG to the KMZ export as selectable folders, like CUT | Recorded |
| 10zzp.2 | Done | The KMZ (and GeoJSON) export now carries the airport: one "CVG airport" folder with a subfolder per layer, each switchable in Google Earth: terminals and buildings; stands in four folders by size (A380, large 747-size, widebody 787-size, small 797-size); aprons; runways; runway centre lines; taxiway pavement; taxiway centre lines; areas; CVG Express yard (moved here from the CUT tracks folders). 313 placemarks (148 stands + 132 taxiway centre lines + 7 buildings + 7 aprons + 5 runways + 5 runway centre lines + 5 areas + 2 taxiway pavement + yard + shop). CVG Express line, stations and platforms stay with the transit layers | Built |


## 10zzq. 1904 Sanborn streets: Times/Eggleston; Mt Auburn, Walnut Hills and Mt Adams (2026-10-19; page versions 77 and 78)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzq.1 | Request (Ben) | Streets for Times/Eggleston, then Mt Auburn, Walnut Hills and Mt Adams (the rest of Volume 2 and Volume 4 sheets 325-332), with streets that continue from earlier sheets joined to them | Recorded |
| 10zzq.2 | Method | Street-corner picks per sheet (sbg/picks, sbg/INSTRUCTIONS.md addendum for the Volume 4 key map); joint fit with existing frames fixed (lph/solve_ext.py -> lph/tf_ext2.json); Volume 2 affine with similarity priors, Volume 4 similarity; build.py streets, then sbg/fit/add_ext.py appends new pieces to basin.json under their own set tag without renumbering anything | Built |
| 10zzq.3 | Times/Eggleston (set te, ids SE) | 49 street pieces (20 joined end-to-end to the same street on earlier sheets, 11 ends snapped onto a crossing street) and 25 blocks | Built (v77) |
| 10zzq.4 | Fit (59 frames) | Sheets 107-110, 127-130, 161-200 (part sheets 161, 172, 199, 200 as inset/main panels) and 325-332. Corner control rms median 1.5 m (worst single corner 10.1 m, sheet 184); tie rms median 1.2 m, max 4.4 m. No OSM control on 110, 167, 200 and 328 (placed by ties only). OSM corners skipped where streets were realigned after 1904 (Dorchester, Florence, Auburn/Sycamore, Gilbert pairs). OSM extent widened east (lph/osm_east.geojson) for Volume 4 | Built |
| 10zzq.5 | Mt Auburn / Walnut Hills / Mt Adams (set ma, ids SM) | 262 street pieces: 29 ends joined to the same street on earlier sheets (Lang, Peete, Sycamore into Auburn, and others), 10 snapped onto an existing crossing street, 22 more loose ends within 15 m closed onto the nearest street (new pass in add_ext.py). 210 blocks. 36 new or re-rendered tiles | Built (v78) |
| 10zzq.6 | Open (names) | 189: unnamed street off Vine. 199: opening off Kemper, unnamed. 332: "Moorman Avenue" is a guess. 162: "Shaar Alley" as read. 163: Edinburgh Place strip. 174/183: two Earnshaws, the avenue kept as "Earnshaw Avenue (Superior)". Section Street is a paper street | Open (Ben) |
| 10zzq.7 | Open (coverage) | 199 park panels not placed; 328, 329 and 332 insets skipped; lots not generated for the new blocks | Open |
| 10zzq.8 | Fix (Ben: Deer Creek Rd wrong) | Deer Creek Road stopped 119 m south of Florence at its angle point: the next point, the Elsinore crossing on sheet 168, was 478 m away, past build.py's 450 m gap limit. Added a line point where the road leaves the bottom of sheet 167 (picks s167 bends; backup picks_bak_1019/s167_pre_deer.json); the road now runs Florence, angle point, sheet edge, Elsinore, on the printed road. Only SM0115 changed. Sheets print it open with addresses down to the angle point; south of there "NOT OPEN", the stretch north of Elsinore vacated for City Park; the dashed "NOT OPENED" line south of Elsinore through the C.L.&N. yard (sheet 160) is not drawn | Built (v79) |
| 10zzq.9 | Fix (Ben: Deer Creek and Reading don't line up between sheets) | Sheet 168 had control only along Elsinore (three crossings in one line), so its top swung: at the 167/168 match line A-B it sat 35 m west of 167, and Gilbert at its top 37 m off OSM. Refit 168 (lph/refit168.py, affine, others fixed) on the Reading/Elsinore crossing (fixed 159/160), the Gilbert/Elsinore corner and Gilbert's centre near the top (OSM; Gilbert unchanged along Eden Park) and the four crossings of the A-B line read on both sheets; residuals 0.3-3.6 m, then a thin-plate spline on those residuals so it lands exactly (lph/tps168.py; tps.pkl frame '168', new 'notaper' flag in tps.py). A similarity fit could not satisfy both ends (16-21 m), hence the spline. Sheet 159's Reading at its far corner then sat 8 m off 168's; bent locally onto it with a spline held by 159's picked crossings and a 60 m grid of zero anchors (lph/tps159.py). Tiles re-rendered (lph/tiles_168.py, REDO=frames), TE and MA streets rebuilt and reinstalled; Reading Road now runs smooth from Dorchester to Elsinore, Deer Creek Road continuous across A-B. Backups: tf_ext2_pre168, tf_all_ma_pre168, tps_pre168.pkl/py, basin_v79, sheets_v79, tiles *.pre168/*.pre159. MA street ids from SM0227 on shift by one (one Reading piece fewer) | Built (v80) |
| 10zzq.10 | Fix (Ben: merging plots no longer works) | Plot rebuild was failing every time ("Maximum call stack size exceeded"): an overlay left a line in a result and the polygon walk in partsJ() recursed on it forever, so no plot step (merge, split, fill) showed. The walk now skips lines and points. With Ben's saved steps replayed, Music Hall (SBB0360) comes out as one 12,954 m2 plot; the later merges he tried there name plots already merged and do nothing | Built (v81) |
| 10zzq.11 | Change (Ben: "between 2 points" should work with a single width) | The joint slider at a picked point now also works where both sides have the same width: the side before the point slides sideways up to its full width, so the street jogs there. Merging streets now carries widths, shifts and joints set between points onto the merged line (they had kept the old point numbers: Central Parkway's 24.4 m stretch spread over nearly the whole merged street and its joint at point 21 sits at a different point now; left as saved) | Built (v81) |
| 10zzq.12 | Land-use colours (Ben) | Residential #00ff00, Mixed use #00a88f, Commercial #0064b0, Industrial #ffce00, Religious #60269e, Civic #da291c, School #ffb7b7 (new), Landmark/museum #ed8b00 (new), Park #00843d (new), Parking grey and Not set unchanged, Open/vacant #ff007f; same opacity, same colours in dark mode. Block types now default to the new uses (school to School, landmark to Landmark, park/square/planting to Park). Sanborn-labelled plots: 71 schools, academies and colleges moved from Civic to School, 2 museums to Landmark (plots.json; backup plots_v81.json) | Built (v82) |


## 10zzr. 1904 Sanborn Volume 3 finished: Clifton Heights, Fairview, Corryville west, the hill above Camp Washington (2026-10-20; page version 83)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzr.1 | Request (Ben) | Finish Volume 3; streets already on the map that continue north must join the new ones without overlapping stubs (e.g. Renner St) | Recorded |
| 10zzr.2 | Sheets | The 49 not yet done: 228-232, 237-244, 248-252, 256-271, 276-278, 283-286, 290-292, 296-300 (scans staged from Ben's folder). Picked by seven parallel readers (sbg/INSTRUCTIONS.md addendum): 472 crossings. Names matched across sheets; jogged pieces carry qualifiers ("Emming Street (east of Ravine)", "Conroy Street (east of Ravine)", "Ravine Street (upper section)", "Guy Street (north of McMillan)", "Falke Street (north of University)" and others); ELYISIAN written Elysian; private ways not built; "No Name Street (not open)" left unnamed | Done |
| 10zzr.3 | Fit | lph/solve_ext.py (vol 3 similarity, existing frames fixed) -> lph/tf_ext3.json, 49 frames: corner rms median about 2 m, worst corner 11 m (250, 258). 277, 278, 286 and 292 (one or two crossings each) started from the sheet's north direction plus their crossing, then held by their street lines (lph/ext_extra.json init_north_deg). 260's out-of-place west panel is its own frame 260i; 259's University of Cincinnati panel (drawn out of place, no crossings) left off the tiles; 300 (a short piece of Dixmyth, no crossings) not placed | Built |
| 10zzr.4 | Streets | 187 street pieces and 89 blocks (set v3, ids SV). add_ext.py: an old stub ending at the old edge is now extended in place (old id kept) instead of getting a second piece beside it: Warner (236) and Bush Alley; short doglegs where two sheets read a crossing a few metres apart are straightened. Renner: continues straight from North Elm through Hamburg to Vernon; its 27 m east of North Elm is Renner's real end at the Bellevue Incline (sheet 219), so it stays. build.py now reads panel frames for sheet 260 (its inset streets had been placed with the main frame) | Built (v83) |
| 10zzr.5 | Open | Sheet 300 unplaced; UC panel on 259 unplaced; Traction Co. incline road (231, "private way") not drawn; lots not generated for the new blocks | Open |


## 10zzs. 1922 Sanborn plate 35 (north) replaces the 1904 sheets west of Hopson and north of Straight (2026-10-20; page version 84)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzs.1 | Request (Ben) | Check his georeferenced 1922 plate 35 north (35_northern_CUF.tif) against streets that are unchanged today; use it instead of the 1904 sheets west of Hopson and north of Straight, with the streets built from it | Recorded |
| 10zzs.2 | Georeference check | Plate read in three overlapping crops (cuf/22-35N.jpg; picks sbg/picks22/s22-35N_w/_m/_e.json, sbg/INSTRUCTIONS22.md): 72 crossings, 36 matched to OSM crossings. On 30 crossings of unchanged streets: rms 3.1 m, worst 5.3 m. A spline correction on them gave leave-one-out rms 3.3 m, no better than reading noise, so Ben's georeference is used as it is (cuf/fit_corr.py). Larger offsets, all on streets that moved or were rebuilt: Dixmyth/Whitfield 35 m, Clifton/Dixmyth 12.7 m, McMicken/Riddle 9.6 m, Duke 6.7-8.2 m, Taylor/Foulke 6.3 m | Done |
| 10zzs.3 | Area | Plate footprint (3 m inside its edge), east of McMicken (Ben's edited line), north of Straight, west of Hopson/Woodside Place; east of Clifton it reaches down to Calhoun. 166.2 ha (cuf/area_c22.json) | Built |
| 10zzs.4 | Streets (set c22, ids SC) | 29 street pieces and 15 blocks from the plate (cuf/build22.py). The edge streets (McMicken, Straight, Hopson/Woodside, Calhoun and the streets west of McMicken) stay as they were; only Straight's stretch from Fairview to Clifton, missing before, is added from the plate. 16 earlier streets removed (SV0004, SV0005, Mountain Alley, Clifton SV0080, Deckebach, Dixmyth SV0088, Enslin, Foulke, Marshall x2, Probasco, Ravine, Riddle, Tafel, Wagner, the v3 McMicken beside Ben's line), 6 cut at the edge (Clifton SV0079, Fairview, Guy, Hartshorn, Morrison, West University), 1 block removed. Dixmyth: the 1904 piece from Whitfield to Clifton was dropped, as it only doubled the plate's line (the plate draws Dixmyth bowing up to 40 m south of today's straight line there). Whitfield and Morrison carried onto the plate's Dixmyth, Guy joined to the plate's Stratford, Riddle onto McMicken | Built (v84) |
| 10zzs.5 | Tiles | The 12 tiles touching the area (713216-714752 by 4334080-4335104) show the plate inside the area over the earlier render (cuf/overlay_tiles.py, originals *.pre_c22); overview rebuilt (cuf/overview.py) | Built (v84) |
| 10zzs.6 | Upkeep | Rerun cuf/overlay_tiles.py after any tile render touching the area, and cuf/build22.py --install after any v3 reinstall (it puts back what it took out first, cuf/c22_removed.json) | Note |
| 10zzs.7 | Open | Fortune Avenue's west end stops 48 m short of Ravine, as drawn. Claassen and Hopson north ends at the area edge were already loose. Lots not generated for the new blocks | Open |


## 10zzt. 1922 plates on their own layer; Millvale grid and boulevard (2026-10-20; page version 85)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzt.1 | 1922 layer (Ben: 1922 on its own layer, not in 1904) | New page layer "Sanborn 1922" (toggle and opacity, default 85%, drawn over the 1904 sheets): deckpage/tiles_22 from cuf/tiles22.py and cuf/plates.py (vol. 1 halves 16R, 34L, 34R, 37L, 37R as fitted in lph/tf22_cw.json; plate 35 north with Ben's georeference; plate 38 once fitted). tiles_n is 1904 only: the plate 35 overlay undone (*.pre_c22 restored, cuf/overlay_tiles.py retired) and the 39 tiles the halves touched re-rendered without them (lph/tiles_all.py REDO=22, *.pre_no22; 11 tiles held only 1922 and were dropped). 50 tiles on the 1922 layer | Built (v85) |
| 10zzt.2 | Millvale grid (Ben: option 1, Manhattan as built) | Area Dreman, Geringer, the trunk, Hopple, Beekman (102.8 ha). Avenues on the Borden and Follett lines at 3 deg, 100 ft; cross streets at 93 deg, 60 ft: Dreman-Ralston 2 blocks (90.6 m), Ralston-Hopple 20 blocks (77.7 m), New streets M1-M20, Ralston carried west and east; New street MT, 60 ft trunk frontage 18 m west of the westmost trunk track. Set mv, ids SMV (millvale/build_mv.py --install): 28 street pieces, 108 blocks (56.3 ha); blocks keep off the rail bundles (APEx Indianapolis + RER D deck, R5, RER A, trunk) | Built (v85) |
| 10zzt.3 | Millvale Boulevard (Ben's straightened KML) | 150 ft (Central Parkway's basin width) over the culverted Mill Creek on its real straightened line; passes under the trunk viaduct at the creek bottom (7-14 m clear); crosses Follett at the square under the Indianapolis + RER D deck, where the West Fork (culverted under that deck) joins; through lanes dip under Follett. Through route leaves at the split for the English Woods tunnel portal (the KML end, about 75 m east of Beekman), as US 101 leaves Lombard on Richardson; the boulevard carries on over the culvert to Hopple ("Old Boulevard" KML), meeting Follett's line at Hopple between North Fairmount (L9) and Hopple (RER A). Working name | Built (v85) |
| 10zzt.4 | Scrapped streets | The 18 scrapped 18 October Millvale/Camp Washington deck streets inside the area (S065-S073, S0901, S0902, S09100-S09106, all deleted in Ben's layout) removed from deck.json so their corridors no longer show as open land (backup deck_v84.json). Stock, Ethan and Bates (merged into SB0473, SB0710, SB0551) still leave open-land strips across M15-M17 until the new blocks get lots | Done |
| 10zzt.5 | Not from the "I-75 Cincinnati redesign" chat | Ben: nothing from that chat applies yet (incomplete). The boulevard here follows only Ben's KMLs and his rulings in this session | Recorded |
| 10zzt.6 | Open | Plate 38 fit and the 1904 refit onto the 1922 plates (in progress); names for the boulevard and the M streets; boulevard width north of the trunk crossing (off the creek, 150 ft for now); lots for the new blocks | Open |


## 10zzu. Plate 38 placed; 1904 sheets bent onto the 1922 plates; Millvale diamond park (2026-10-20; page version 86)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzu.1 | Plate 38 (Ben: fit the scan to unchanged streets; his GeoTIFF only a reference) | Picked by six readers (sbg/picks22/s22-38_a..f, INSTRUCTIONS22 addendum): 169 picks, 109 crossings, 74 matched to OSM. Seed: png to GeoTIFF by SIFT (cuf38/match.py; the GeoTIFF itself is 12.3 m rms off OSM, 20-30 m at the plate edges). Fit (cuf38/fit38.py): affine + thin-plate spline (smoothing 0.3) on 56 controls, leave-one-out rms 4.0 m. Left out: Dixmyth (named), Glenmary (all five crossings off: realigned), and controls the smooth field cannot reach (Lafayette/Ludlow, Ruther/Vine, Woolper/Vine, Ludlow/Jefferson, Ludlow/Gano, Ludlow/Brookline, Shields/Glendora, Glenmary). Layer cuf/plates.py; tiles_22 now 58 tiles | Built (v86) |
| 10zzu.2 | Plates 35 and 38 against each other | Shared crossings: Clifton/Dixmyth 2.3 m, Morrison/Dixmyth 3.6 m, Dixmyth/Whitfield 4.8 m (McMicken/Dixmyth 13.4 m, at plate 38's edge). Both put Dixmyth/Whitfield 35-41 m from today's: Dixmyth was realigned after 1922 | Recorded |
| 10zzu.3 | 1904 sheets onto 1922 (Ben: 1922 first, then 1904 to it; only sheets already on the page) | cuf/x1904.py matches each 1904 crossing to the plates; cuf/tps1922.py bends 30 frames (256-299 under plates 35 and 38) with the Lower Price Hill spline (own matches 0.05, neighbours' 0.3, zero anchors 120 m out); trust rule: frames with 3+ matches by a similarity check (6 m), others by distance (10 m), plus Dixmyth/Whitfield forced on 292. Moves: most 1-5 m; 289-291, 295, 296 8-13 m (they had been hung on today's Dixmyth); 292 35 m. 260, 261, 263 have no shared crossing (unchanged). Tiles re-rendered (lph/tiles_all.py REDO, *.pre_1922); v3 streets rebuilt (run_build_safe.py + add_ext.py), then c22 and mv reinstalled | Built (v86) |
| 10zzu.4 | Not bent in the streets | Frames 274, 275, 282, 289, 295 belong to the older north build (base set): their tiles are bent, their street lines are not (moves 4 m; 289 and 295 about 12 m) | Open |
| 10zzu.5 | Millvale, Follett crossing (Ben: B, Panhandle-like, diamond, arms as wide as the traffic needs, square ends, Follett one way to the boulevard) | The boulevard forks between M2 and M3 and rejoins between M6 and M7: two one-way arms, each half the boulevard (75 ft), round a diamond park (1.08 ha plus three wedges, 1.32 ha in all) over the Mill Creek / West Fork confluence; the 150 ft band stays park or road; M3-M6 end at the arms in square T junctions; Follett meets them at the M3 (west) and M6 (east) corners, one way toward the boulevard and 60 ft on its last block; drivers leaving the boulevard for Follett use M2 or M7 (millvale/build_mv.py). The earlier dip under Follett is dropped: it would cut into the culverts | Built (v86) |


## 10zzv. Plate 38 streets on the map (2026-10-20; page version 87)

| # | Item | Result | Status |
|---|---|---|---|
| 10zzv.1 | Fit revised before drawing | Vine's edge crossings had been dropped and Vine sat about 20 m off the 1904 Vine: the drop test now uses the less smoothed spline (tps1), so the edge distortion is followed; Lafayette left out by name (its two crossings disagree with each other and with the plate-37/1912 corner). 63 controls; leave-one-out rms 4.75 m (edge-heavy), fit rms 2.3 m. tiles_22 and the 1904 refit redone (tps1922, tiles_all REDO 265-299, *.pre_1922b) | Done |
| 10zzv.2 | Streets (set c38, ids SK; cuf38/build38.py from build22) | Area: plate 38 footprint (3 m in), east of Ben's McMicken, less plate 35's area: 213 ha. 58 street pieces, 41 blocks; earlier streets inside removed, those crossing the edge cut; McMicken and Dixmyth kept. Same-name streets in separate places kept apart (two Terrace Avenues), pieces of one street a long block apart rejoined when the gap runs along it (McAlpin, Woolper). Loose ends closed: Lafayette and Ludlow to the plate-37 Ludlow corner (S22016), Gazley to the 1904 Herbert, Vine and Woolper at the north-east corner, East Nixon and Shields to Vine, Whitfield to Dixmyth, the 1904 McMicken pieces to each other | Built (v87) |
| 10zzv.3 | Rebuild order | cuf/rebuild_streets.sh: undo c38 and c22 removals (cuf/undo_sets.py), v3 build + add_ext, build22, build38, build_mv | Note |


### 10zzw. KMZ streets at drawn width (v88, 20 October)

Ben: streets in the KML/KMZ should be as wide as on the page. Each street placemark is now a MultiGeometry: the page's own corridor polygon (corridorRuns where widths change along the street, else corridor at the street's width, mitred in the basin, round on the deck) plus the centre line. Fill is the page's street colour, thin outline. Checked on 13 random streets plus Millvale Boulevard: corridor area / centre-line length matches width_m to within 0.06 m (1707 of 1707 streets carry a polygon).

Fixed on the way: SK0010 East Nixon (plate 38) had collapsed to a point when its east end was snapped to Vine; it already started at Vine, so it keeps its 22 m stub to the plate edge (build38.py now skips a snap that would leave a piece under 5 m). The Millvale Boulevard note no longer says the through lanes dip under Follett.

### 10zzx to 10zzy.9 (20-22 October, page versions 89-92): text not recovered

These sections (among them 1922 plates 66-70, versions 89-90) were lost from every copy of this log; they are not in the workspace, the project, the session records or Ben's Drive. Restored on 31 October from Relief_Maps_Log_push.md (20 October, through 10zzw) and the current log (10zzy.10 on). Until they are rewritten, the workspace's own working notes for those versions (lph/RESUME.md) stand in for them, quoted as written:

> **2026-10-21 page versions 89-90 (1922 plates 66-70)**
>
> - cufp/: prep.py (stage + SIFT seed), fit.py (2 passes; name seed without GeoTIFF; ALIAS), fwdlib.py, build.py N (sets c66..c70, PLATE_ORDER 66,68,67,69,70, second loose-end pass), check_osm.py, plot_build.py, overlaps.py, frames_under.py, gaps.py, strips.json, PROCESS_1922.md. Picks sbg/picks22/s22-66..70_a..f.
> - cuf/x1904.py base-name matching; tps1922 over 47 frames (backup lph/tps_v87.pkl); tiles_all REDO (*.pre_66); tiles22 106 tiles.
> - tiles12 merged to 1000 m tiles (manifest 512-file limit); backup scratchpad/tiles12_v88.
> - rebuild: cuf/rebuild_streets.sh (now includes cufp builds).
>
> **2026-10-22 page version 91**
>
> - rer1023/: kml.py (Ben KMZ -> ben_1021.json), apply.py (reads deckpage/context_v90.json, tracks_v90.json, dbread2 layout; writes context.json, tracks.json, geom.json), plot*.py. Then millvale/build_mv.py --install. Page test plots/p91.py (db_data_v91.json = layout without the trunk edit). DB layout v1580: trunk transit edit removed.

Per-plate figures for 66-70 (seed, model, controls, leave-one-out) are in each plate's cufp/<plate>/report.json and in the export README (Maps\Topography_Export\README.md). Version 92 has no surviving note.

### 10zzy.10 Cross-grid deck narrowed: R5 stacked under it (22 October, v93)

Ben: the viaduct that crosses the Millvale grid was unnecessarily wide. The KMZ Cumminsville Spur ran beside the Indianapolis + D deck, 4-9 m outside the outer APEx track, so the crossing came out about 40 m wide (39.9 m measured at D s 1650).

Fix (rer1023/apply.py): between the two places the KMZ spur crosses the D line (spur s 348 and 884), the spur centreline is blended onto the deck centre, (2 x D centre + APEx 5 + APEx 6) / 4, with smoothstep ramps from 80 m before the first crossing and to 30 m past the second, then smoothed. R5 now sits 2.2-6.7 m on the APEx side of the D centre, between the D pair (+/-2.25) and the Indianapolis pair (about -6.4 and -10.8), on a lower level 7.6-8.9 m rail to rail under the 174.3 m deck. The crossing is the four-track deck only: -10.8 - 4.2 = -15.0 to +2.25 + 4.2 = +6.45, about 21.5 m.

The page's structures layer (cut/structures.py) carries the APEx pair, not RER D, on this arm; D's structure comes from rer_struct. Its arm width now reads 12.9 m (APEx alone) and 21.8 m where the R5 footprint merges with it; 34.6 m at D s 1450 is where the deck crosses RER A at the South Cumminsville station, which is a real crossing.

millvale/build_mv.py keep-out changed from a 6 m buffer with 20 m gaps closed to the structure rule (4.2 m, gaps under 6 m closed). Blocks 108, 56.8 ha.

Not done: stacking D over the Indianapolis pair to bring the crossing to about 13 m (a three-level structure over the grid).

### 10zzy.11 R5 across the grid redone at both ends (22 October, v94)

Ben: v93 made the crossing angular and slow, and both ends of the cross-grid viaduct are in question, not only the west.

What v93 did wrong: it kept the KMZ spur and pulled it onto the deck centre with smoothstep blends. That left about a 100 m curve at the RER A end (Ben's KMZ curve there was about 200 m) and S-bends at both ends.

New alignment (rer1023/apply.py, built before the station block so the junction point comes from it):

- East end: R5 leaves the lower west pair at (712247.9, 4335690.7), right under where the Indianapolis + D deck crosses over that pair. It curves left at 500 m (tangent arc, numerically solved) onto the deck centre line at D s 2339. Before, it ran north beside the main band to about 4335845. The whole curve is inside the existing deck and band footprint (rer1024/east.py: 31 m2 outside at 500 m; at 700 m and over it starts to stick out).

- Middle: on the deck centre line, (2 x D centre + APEx 5 + APEx 6) / 4, from D s 2339 to 1579, following the deck's own curves.

- West end: it leaves the deck at D s 1579 on a 200 m curve, single track, and joins the trunk centre track at trunk s 5185 (Ben's KMZ point was 5191; the platforms start at 5238). The 3-track spread now starts at s_sp − 60, so the northbound track is 4.5 m out before R5 crosses it, about 42 m short of the join.

- Trade-off at the west end (rer1024/west.py, structure outside the deck and RER A): 100 m, 125 m2, 3 m out; 150 m, 345 m2, 8 m out; 200 m, 557 m2, 13 m out; 250 m, 772 m2, 18 m out (joins at s 5204); 300 m runs into the platforms (s 5235).

- Spur 1,118 m. It rises 164.6 to 167.0 m, about 0.21%.

Structure layer:

- cut/structures.py now takes the R5 spur into the North arch viaduct.

- The rer_struct lines for 'D (with the Indianapolis pair)' and 'B' were an older alignment drawn diagonally through the Millvale grid. D now follows R-D-710306-4337028 from s 0 to 2450. B now follows R-B-712689-4336858 south of N 4336600 (its Ludlow descent is not drawn). B/D south of the main band (712000-712280, 4334180-4334800) is still the old alignment; not touched.

- Measured across the arm: 21.8 m from D s 1550 to 2250 (four tracks plus 4.2 m each side); the RER A crossing (D s 1450-1500) and the junction with the main band (D s 2300 on) are wider.

The "R5 leaves the west pair" level marker is moved to the new divergence. Blocks rebuilt (build_mv). Backups: index_v93.html, rer1023/apply_v93.py.

Ben confirmed the 200 m west curve (22 October).

### 10zzy.12 Street names, deletions and duplicates on the page (22 October, v95)

Ben: wants to rename streets (the "New street M#" names are placeholders he'll replace) and delete streets, especially the copies drawn twice along the same course with the same name.

Page (index.html, page only, no data change):

- Street panel: a Name box with "Rename this piece" and, when other pieces of the same name join it end to end (an end within 3 m), "Rename the street (N pieces)". Enter renames the piece; Shift+Enter renames the street. An empty box or the generated name puts the generated name back. There is also a "Delete this street" button, and a "Same course as" list of other streets with 90% of one within 3 m of the other.

- Multi-select: "Delete these N streets".

- Edits panel: deleted streets (not merged ones) listed with Restore and Restore all. "Find duplicate streets" scans all streets, whichever layers are showing, for same-name pairs on the same course. "Next" steps through them with the copy to drop selected: the piece lying on the other, otherwise the shorter or the unedited one. "Delete all N copies" deletes them in one go. On the v91 test layout it found 23, mostly plate overlaps (SP/SR/ST/SU) and Millvale pieces.

- Stored in the layout as streets[id].n (name) and streets[id].del (no 'into'). They are seeded like any first edit, so the generated curves stay. A deleted street's land goes to the plots beside it through the existing vacated-corridor logic, unless another street covers it.

- Exports (GeoJSON/KMZ) carry the set name, with name_generated kept.

For regeneration: these edits are keyed by street id. Any rebuild has to keep street ids stable, or carry n/del across, or Ben's names and deletions are orphaned.

### 10zzy.13 Platforms at Metro line ends (22 October, v96)

Ben: Wayne only had one platform.

Cause: Wayne is on Line 12 (through) and Line 13 (its terminus). Line 13 had no platform at Wayne. The transit build (transit/build_transit_v25.py, offset_curves) clipped each platform to its line and dropped it if less than 60% was left. A station at a line end keeps only half its platform, so it got none.

The same bug hit Kirby (Line 12 terminus), Northside (Line 8 terminus) and Pennsylvania (Line 5, where the line ends and two pieces start).

Fix (rer1023/apply.py, end pass): for a Metro station within 60 m of a line that has no platform for that line, if the 152.4 m platform would run off the end, it is slid to lie wholly on the line, ending at the line end.

- Bore lines get two side platforms (1.95 + 1.45 m out, 4.0 m wide). Twin lines get an 8.0 m island.

- Added: Wayne L13 and Kirby L12 (side x2, chain 0-152), Northside L8 (side x2, 0-152), Pennsylvania L5 (island, on the long piece, ending at the station).

- Wayne's Line 13 platforms run east along Elmore from under the Line 12 platforms.

- Checked on the page with the live layout (version 1597): no page errors, platforms drawn at all four.

### 10zzy.14 Street headings: read, set, match (22 October, v97)

Ben: Dirr's end has to move to its right place, which loses its angle. He wants to read a street's heading (Follett) and set another street (Dirr) to it, so they stay parallel. Ctrl-drag only keeps an angle the street already has.

Page (index.html only):

- The street panel has a Heading box. It shows the end-to-end heading, both ways (degrees clockwise from grid north, UTM 16N), plus each stretch's heading when there are more than two points.

- Set heading: a number box, a choice of which end to keep (named by compass, e.g. "keep the north-west end"), and a button. It turns the whole street rigidly about that end, keeping its length; curve controls turn with it. Of target and target + 180 it picks whichever is nearer the current heading, so the street never flips.

- Copy heading on one street, then "Match <name> (x°)" on another, turns the second about its kept end to the copied heading.

- While a point is dragged in Edit mode, the readout also shows the heading of the stretches either side.

Test (plots/hdg_test.py, live layout): Follett Alley SB0314 at 156.24° copied to Dirr Alley SB0297 (156.09°) gave 156.24°, kept end unmoved. Coordinates round to 0.1 m, about 0.03° on a 100 m street.

### 10zzy.15 Headings for a stretch between two points (22 October, v98)

Ben: wants the heading tools to work on a section, to fix Beekman between Dreman and Elmore.

Page (index.html only): the Between two points box (Edit mode, pick two points) now has:

- the stretch's heading (point i to j, both ways);

- Set heading, with a choice of which of the two points to keep;

- a "rest of the line moves with it" checkbox;

- Copy this heading, and Match <copied> (works with a street-level copy too).

turnRange(f, i, j, pivot, target, carry) turns the stretch's points and curve controls about the kept point, keeping its length. By default the stretch beyond the turned point bends to meet it; with carry, everything beyond turns too. The street-level Set/Match now calls turnRange over the whole line.

Test (plots/hdg_test3.py, live layout): Follett Avenue SB0720 (156.6°) matched onto Beekman SBW002 points 4-5. The stretch came out at 156.60°, point 4 stayed put, point 5 moved, and point 6 was unchanged.

### 10zzy.16 Northside / Camp Washington: 1922 and 1904 refitted to unchanged crossings (22 October, v99)

Ben: the 1922 and 1904 sheets disagree in Northside / Camp Washington, Colerain especially. He asked for both to be checked against real, unchanged crossings (Adelaide, Brashears and Arlington still exist at the north end of Camp Washington).

Before (cuf_cw/diag.py, every pick against the OSM crossing of the same two streets):

- 1922 halves (affine, 10u.4): 22-37R median 8.4 m (p90 24), 22-35L 10.5, 22-34R 5.3, 22-37L 3.8.

- 1904 frames 606-619 (Northside): 5-10 m. 611/612 to 37 m at Elmore.

- Shared 1904/1922 crossings: median 5.0 m apart, p90 13.7.

- Elmore crossings are about 40 m off on both atlases: Elmore has been realigned since.

- Today's Colerain north of the Elmore interchange sits 6-12 m off both atlases at Powers, Burgoyne, Hoffner and Blue Rock, while the side streets fit within 1-2 m. Colerain has moved or been widened there, so it is left out of the control.

- The old Colerain line in north Camp Washington is gone. Spring Grove at Adelaide, Brashears and Arlington, Arlington at Sassafras and Colerain, and Sassafras at Colerain and Comfort survive.

Second read: 22-37R and 22-37L in three strips each (six reader agents, two waves). 37R added 82 picks, among them Spring Grove at Powers, Burgoyne, Brashears, Adelaide and Arlington. 37L added 80, mostly agreeing with the first read. Readers' notes: the heavy solid lines inside streets are water pipes; Stodder Alley / Allen Street is the same band; Knowlton is a tract name here, not a street.

Refit (cuf_cw/fit.py, spline as cufp/fit.py, seeded from the affine; Elmore and northern Colerain out):

- 37R: 15 controls, tps0.3, fit 1.0 m, leave-one-out 5.9 m. Sparse: most of its streets are gone.

- 37L: 20 controls, tps30, fit 3.0 m, leave-one-out 4.7 m.

- 34R: 49 controls, fit 1.4 m. 34L: 16 controls, fit 2.7 m. 16R: 15 controls, fit 2.2 m. 35L: 24 controls, fit 1.3 m. 16L: 9 controls, fit 0.4 m. 35L and 16L are not on the layer.

- cuf/plates.py uses the models; tiles_22 re-rendered.

1904 bend: cuf_cw/frames_under.py lists 49 frames under the halves. x1904 and tps1922 were run on these plus the 47 already bent (86 in all). tiles_n re-rendered for the 49 (REDO, BAK pre_cw).

After:

- 1922 against OSM: median 1.6 m (4.6 before), north 2.1 m (5.2).

- 1904 against OSM: median 2.7 m (3.4).

- Shared 1904/1922 crossings: median 0.3 m apart (5.0), p90 3.4 m (13.7). Every Colerain crossing is within 3.4 m.

Streets:

- cuf/rebuild_streets.sh was run (the background run was cut off at 30 minutes after plate 69; plate 70 and Millvale were finished by hand). It rebuilds the v3/SV and plate sets but not the north SB layer.

- Rerunning sbg/fit/post.py would renumber every SB street, so cuf_cw/shift_sb.py moved 143 SB streets, 96 SBB blocks and 2,373 plots by exactly their frames' change in placement (largest 11.4 m), ids unchanged.

- Ben's live layout (version 1772: 24 names, 34 deletions): all 204 of his edits on basin streets still point at the same id and name. Merged-away pieces are unchanged geometrically. 20 SV ids changed name in the rebuild; none of them carry edits.

Files: cuf_cw/ (fit.py, config.json, diag.py, far.py, cands.py, frames_under.py, shift_sb.py, frames_all.txt, the per-half models). Backups: lph/tps_v98.pkl, cuf/tps1922_report_v98.json, cuf/x1904_v98.json, tiles_22_v98, tiles_n_v98, deckpage/basin_v98.json, plots_v98.json, index_v98.html. PROCESS_1922.md section 9 added.

Open: 35L and 16L are refitted but not on the layer. 1904 Northside north of Powers (Hoffner, Blue Rock; frames 614-622) has no 1922 plate to bend to, and sits 5-10 m off OSM at Colerain, which itself has moved.

### 10zzy.17 Highway update on the deck page (22 October, v100)

Ben: push the highway work (the Cincinnati Interstate Types map and the "I-75 Cincinnati redesign" conversation) onto the page, building Millvale Boulevard from the page's streets because the map's lanes did not follow them.

Highways layer (deckpage/hwy.json, from hwy/build_hwy.py):

- OH-75 parkway (km 14.54 to 19.4, 40.2 m: 4.0 m planted median, BRT 3.5 + 0.5, two 3.5 m lanes, 0.6 and 1.5 m shoulders, 2.5 m verge, 2.5 m walk each way), from the highway map's centre line.

- Millvale Boulevard (km 19.4 to 21.4) on the page streets SMV0033-0035 and the one-way arms SMV0037/0038 (150 ft: 1.0 planted centre, BRT 3.5, platform or planted strip 3.0, two 3.3 m lanes, 2.5 m loading lane, 6.26 m walk each way).

- English Woods tunnel (from the portal), OH-74's last 397 m to its Colerain signal, the inner ring corner, signals from the map, labels.

- Spring Grove Cemetery outline from Ben's GeoTIFF (alpha mask, sgc/cemetery_utm.json, 226.7 ha). Only RER A (887 m) and Metro Line 1 (266 m) pass under it, both in tunnel.

Central Parkway / OH-75 (Ben, 22 October):

- Continuous T on Albone Street's axis, km 18.96, 438 m north-east of the Ludlow signal. Central Parkway is square with Albone (its last 40 m on Albone's axis) and meets OH-75 at about 65 degrees, so the two banned movements would each have been turns of about 114 degrees.

- The leg is tangent at both ends (Ben, 22 October, after a first straight version that bent 9 degrees at Ludlow and started at Ben's doubled-back point 0): straight on from Central Parkway's own line (bearing 24.0 degrees, from his point 1, 18 m past Ludlow) for 62 m, a 21.9 degree curve of 1,000 m radius (382 m), then 48 m on Albone's axis into the T; 492 m, 27.2 m wide (2.0 m median, two 3.3 m lanes and a 3.5 m kerbside bus lane each way, 2.5 m walks; bus lanes added at Ben's request, not necessarily BRT). Nearly level, 168.3 m to 164.9 m, so the hill between Millvale, Ludlow and Central Parkway is regraded by up to 31.9 m (LiDAR), more than 5 m over 420 m; the roadway alone is about 245,000 m³ at 27.2 m, side slopes not counted. The Central Parkway / Ludlow signal sits where Central Parkway's line crosses Ludlow.

- Kerbside bus lanes the whole way from Millvale to Reading Road (Ben, 22 October; not necessarily BRT), drawn in the Highways layer on Ben's line and widths (SB0595 edit: 24.4 m on 333 pieces, 45.72 m on the last three; East Central Parkway SB0675 45.72 m). At 24.4 m: bus lane 3.5 + two 3.3 m lanes + 2.1 m walk each way, no median. At 45.72 m: walk 4.0, loading 2.5, bus 3.5, two lanes, 12.5 m planted median. Widths not changed.

- Southbound OH-75 never stops. Two protected left lanes run in the median, widened to 7.5 m for 100 m before the T, and left-turners cross the southbound bus lane before the junction. Northbound traffic and its BRT stop for that phase. Central Parkway turns right from both lanes, and the outer lane becomes a third northbound lane in the shoulder and verge; where it drops is not set.

- Banned: Central Parkway to Millvale Boulevard south-west, the northbound right into Central Parkway, and lefts from Central Parkway onto Ludlow. The median is 4.6 m for the left to Ludlow. The Albone tail is dropped.

Ludlow and the trunk:

- Ludlow (S22015) is at ground on its 1914 line, no longer a viaduct.

- nv/geom27.py: Z_LUD is 162.5 m at s 5,369 (it was 155.5 m at s 5,300), so G_BAND falls from 0.787% to 0.276%. A new north_z holds 162.5 m to s 5,570 (the end of the RER B Northside / Spring Grove platforms), then falls 1.5% to ground at s 6,270, 901 m north of Ludlow; the ground falls northward.

- Knock-ons: Arlington (B) is now 165.9 m (was 164.6). R5 leaves the west pair at 166.2 m (was 164.6), so it is still 7.3 m or more under the Indianapolis + D deck. Indianapolis + D over the trunk is 7.9 to 8.3 m rail to rail (was 8.3 to 9.3), and the s 3,924 marker is now 6.6 m. B over Millvale Boulevard is about 163.3 m on 155.3 m ground. Elmore now passes under the viaduct at 162.6 m.

- rer1023/apply.py's new end pass carries the notes and marks; the B viaduct runs to Ludlow, with B fill (rer_struct state 'embankment') to B s 970. It also adds the RER-1b over OH-74 mark (rail 160 m or more, road 153.5 m).

- cut/structures.py section 7: North trunk fill (Ludlow to ground, 19,417 m²) and the Ludlow underbridge (26 degree skew).

Northside streets:

- Colerain gets base widths between points ('wv'; the page's streetWv now falls back to f.properties.wv): 33.2 m from OH-74 (Kirby) to Blue Rock (BRT plus two lanes and a loading lane each way), and 26.2 m on to Millvale Boulevard (path A for OH-74 through traffic).

- Blue Rock (SB0567) and Spring Grove from Blue Rock to Millvale (SB0935) are 21.6 m: centre BRT and one lane each way.

- Not straightened. Hamilton is unchanged.

- 24 blocks and 314 plots trimmed back from the widened corridors; 3 plots too small to keep were dropped, none of them with edits.

- New streets, set hwy: HW0001 OH-75 parkway north-east of SMV0033, HW0002 OH-74, HW0003 Central Parkway (to OH-75).

Correction: RER D west was already 9.05 m from the APEx centre. The earlier 6.8 m was measured from one APEx track, so nothing moved.

Pipeline: rer1023/apply.py, then cut/structures.py, then hwy/build_hwy.py --install. Run build_hwy after any street rebuild; it is idempotent. build_mv.py was not rerun: its rerun would move the Millvale carried streets onto the v99 SB shift, which is a separate change. Backups: *_v99 for context, tracks, structures, basin, plots, index; nv/geom27_v99.py, rer1023/apply_v99.py, cut/structures_v99.py.

### 10zzy.18 Metro Line 3 realigned; Central Parkway leg at 80 ft (23 October, v104)

Line 3:

- Ben's Line_3.kmz (copied to rer1023/line3_1023.kml) comes from topographic maps of the real Cincinnati subway right-of-way through Camp Washington, St Bernard, Bond Hill and Norwood.

- The pieces South Ext 1, Line 3, MCE and North Ext are joined, clipped to the Metro window and fitted (fitarcs: 82 curves, 13,124 m in the window). The tracks and island platforms are rebuilt as the transit build does, in a new pass in rer1023/apply.py. The line keeps id M-L3-716800-4339056.

- Inside the window, the line moves up to about 29 m between Bruckman and St Bernard and east of St Bernard. Most of the change, through Bond Hill and Norwood, is outside the window.

- Stations: Marshall (Line 3 only) moves 121 m to Ben's point. Kenard (Lines 1 and 3) moves 95 m to Ben's point, which is the crossing of the two lines (0.2 m off Line 1, 0.4 m off Line 3). The old Line 1 point was 88 m off the new Line 3, so Line 3 would have lost its platform there. Line 1's Kenard platform is rebuilt at the new point.

- Other shared stations keep the lower line's point, as the build's merge rule does; all are within 60 m of the new line. Line 3 has 19 platforms, as before.

- Ben's page edit of Line 3 (a change of up to 11 m at Central Ave, which the KMZ includes) was deleted from the layout (DB version 1831 to 1832) so the KMZ line shows. His station settings on the line (Central Ave side platforms, Bruckman offset 53 m) are kept.

Central Parkway:

- Ben edited Central Parkway's line: the doubled-back first point is gone and the curve near Bruckman is redrawn. He also set the leg (HW0003) to 24.4 m.

- hwy/build_hwy.py now reads dbread7. The leg starts from his new end on Ludlow: 83 m straight, a 21.8 degree curve of 1,000 m radius (380 m), then 47 m on Albone's axis; 510 m in all.

- At 24.4 m the leg has the 80 ft section (3.5 m bus lane, two 3.3 m lanes, 2.1 m walk each way, no median). The regrade is up to 32.3 m, more than 5 m over 420 m, and about 222,000 m³ for the roadway.

- Open: the 150 ft part of Central Parkway (1,714 m), options A, B and C sent to Ben.

### 10zzy.19 Metro out to the RER limits (23 October, v105)

Ben: the Metro lines and stations should be drawn within the RER limits (E 699,000-736,900, N 4,320,800-4,347,000), not only the plan window.

- New pass in rer1023/apply.py: each whole line (handoff/page/lines; Line 3 from Ben's 23 October KMZ) is fitted, and tracks and platforms are built along the whole part as the transit build does. The parts outside the window are added as 28 new pieces (ids M-L<n>-x-y, outer=True), with their tracks and platforms.

- The pieces inside the window, and Ben's transit edits on them, are unchanged.

- 204 stations added outside the window. A station of the same name within 150 m of a listed one joins it, as the build's merge rule does.

- 46 Metro pieces and 568 Metro platforms in all. The terminus pass adds platforms at the outer line ends.

- context.json is now about 1.7 MB (was 1.25 MB).

### 10zzy.20 Central Parkway's 150 ft end (23 October, v106)

Ben: the 150 ft part should have wide sidewalks, trees lining the sidewalk, parking, lanes, a median and centre bus lanes.

This covers Central Parkway from the turn south near Liberty to East Central Parkway at Reading Road: 15 + 762 + 427 + 510 = 1,714 m, at 45.72 m.

- Section, from the centre out: a 3.0 m median (room for stop platforms), a 3.5 m bus lane, two 3.3 m lanes, 2.5 m parking, a 2.0 m tree strip and a 6.76 m sidewalk each way.

- Check: 3.0 + 2 × (3.5 + 6.6 + 2.5 + 2.0 + 6.76) = 3.0 + 2 × 21.36 = 45.72 m.

- On the 80 ft parkway the bus lanes stay at the kerb, with no median, as the real Central Parkway has none. Buses cross between the kerb and the centre where the width changes; signal priority there is not drawn.

- hwy/build_hwy.py cpw_side(); page strip kinds 'parking' and 'trees'.

### 10zzy.21 Metro platforms 400 ft (23 October, v107)

Ben: Metro platforms are 400 ft (121.92 m) at every station. All 600 platforms redrawn; platforms split at piece joins rejoined on the station (rer1023/metro400.py). Rail Profiles v30 and the older Metro Profiles v3 defaults and saved profiles set to 121.92 m.

### 10zzy.22 1922 plates 82A and 83A, Norwood (24 October, v108)

Ben's scans of plates 82A (central Norwood) and 83A (east Norwood), fitted by the plate process (PROCESS_1922.md). His GeoTIFFs only seeded the match.

- Seed: SIFT, PNG to GeoTIFF, 4,111 points for 82A (8.6 px rms) and 2,124 for 83A (5.8 px).

- OSM: the existing extracts stop at E 721,364 and N 4,337,658, so a Norwood extract was cut from the same source (lph/osm_norwood.geojson, Historic_Topo/OSM/streets_all.geojson, E 716,500-723,500, N 4,335,500-4,340,500).

- Readers: 82A in six strips, 83A in four; 193 and 108 picks.

- Aliases for renamed or respelled streets: Montgomery Pike and Montgomery Avenue = Montgomery Road; McNeill = McNeil Avenue; Robertson Road = Robertson Avenue. Dudley, Wilbert, Malcolm and Victor Boulevard are not in today's OSM under those names.

- 82A: tps1, 94 controls of 100 matched (125 crossings), leave-one-out 3.78 m, fit 2.16 m. Dropped by the 6 m test: Washington/Lafayette (twice), Norwood/Montgomery, Park/Smith (twice), Smith/Lafayette, all around the Lafayette and Smith Road junction east of Montgomery. Harris west of Forest has no OSM crossing near the seed.

- 83A: tps1, 40 controls (46 crossings), leave-one-out 3.97 m.

- Overlap: five crossings used by both fits (Marion at Highland, Harper, Buxton and Norwood; Floral at Smith Road) agree within 0.7-2.0 m.

- No 1904 frames lie under either plate, so nothing was bent.

- Streets: sets c82A (SN, 57 streets, 58 blocks) and c83A (SO, 20 streets, 21 blocks), in an area that had none. Per-plate settings in cufp/config.json: best printed name per street (bare "Elm" vs "Elm Avenue"), Montgomery merged and split at the railroads (Montgomery Pike north, Montgomery Avenue south, as printed), Robertson merged into Robertson Road.

- tiles_22: 24 new tiles (130 in all).

### 10zzy.23 Inner Ring (OH-562) and Norwood Central on the page (24 October, v109)

Ben: put in the 562 inner ring and the station; not the Line 3 station yet (it is to move to a better location).

- Inner Ring North, the whole 8.09 km from Duck Creek (I-71, J8) to Broerman (OH-75, J7), as the 45.72 m boulevard (hwy/build_hwy.py; street HW0004). Before, only the page corner was drawn.

- The highway map's line lay on the rail corridor west of Norwood Central (frame s 3,400-4,350) and clipped the station's Transvalley tracks. Between s 3,330 and 4,660 it is pushed north, by up to 46 m where the map line dipped onto the tracks, so its south edge stays 3 m outside the six-track corridor and Ben's station track area (nwring/ring.py). Minimum radius in the moved stretch 446 m.

- Grade separations the ring needs: the Waynesville pair on the CL&N prong just north-east of the station; the APEx Transcontinental at Ridge (km 2.13 from Duck Creek) and near Broerman (km 8.08).

- Norwood Central: a new page layer (norwood.json, deckpage/index.html drawNorwood) holds the sketch v10 surface (12 tracks plus the Waynesville pair, six platforms), the building, and the level -1 concourse and main tunnel.

- Below ground (rer1023/norwood_pass.py, hooked into apply.py after the 400 ft pass):
  - Metro 4's terminus moved to end at frame o -3 under Montgomery Road, and its 80.5 m tail cut (it crossed Line 3 at one level).
  - Metro 14's platforms moved about 100 m south along its line, centred at o -65.
  - TRI E's platform moved to s 4,777-4,981, between the main tunnel and TRI A.
  - Tracks re-spread.
  - Metro 3 and TRI A unchanged.

- Streets: Harris Avenue and the side-street ends inside the station's track area cut back. Montgomery, Smith Road and Forest cross the station (bridges). The ring replaces the stretches of Norwood Avenue and Sycamore Street it runs along. Blocks trimmed by the ring, the track area and the building.

### 10zzy.24 1922 plates 75 and 76, between Norwood and Avondale (24 October, v110)

Ben's scans of plates 75 (east North Avondale and west Norwood) and 76 (south-east Norwood), fitted by the plate process. His GeoTIFFs only seeded the match.

- Disk: the first upload ran out of space. Old crops and backups from before v84 were deleted, and so were Ben's processed 82A/83A GeoTIFFs, with his approval. He re-sent the missing files (76_1.png, *_1.tif).

- Seed: 5,774 points for 75 (7.4 px rms) and 7,903 for 76 (11.2 px).

- 75: tps10, 47 controls of 52 matched (79 crossings), leave-one-out 4.18 m. Not in today's OSM: Mougey, Herald, Herbert, Eugenia, Armstrong Boulevard, North Side Avenue and Tibbles (mostly the Xavier campus now). Victory is printed "Boulevard" (alias Victory Parkway).

- 76: tps1, 117 controls of 127 matched (158 crossings), leave-one-out 3.15 m. Not in OSM: Cavagna, Catharine, Edmonson, Carland.

- Overlaps: 75 with 68, 69, 70 and 82A at 1.5-3 m, except for crossings on 75's cut edges (Brewster, Clarion and Woodburn at Montgomery and Hopkins, 10-16 m), which the earlier plates own. 76 with 75, 82A and 83A at 0.5-5 m.

- No 1904 frames under either plate.

- Streets: sets c75 (SX, 50 pieces, 30 blocks) and c76 (SY, 55 pieces, 97 blocks), with best printed names; Edmonson merged into Edmonson Road. Each plate's area excludes the earlier plates. No loose ends left. hwy/build_hwy.py reinstalled (no change).

- tiles_22: 147 tiles (35 new or changed).

### 10zzy.25 Norwood Central throats relaxed, building on Floral, Metro 3 terminus (24 October, v111)

Ben edited the streets around the station to show where they end: Floral west to Montgomery at 120 ft, Smith Road ending on Floral, Foraker to Station Avenue, and the north streets ending at the ring. He also said the station's tracks are in a cut, with Montgomery on a viaduct over the platforms and Foraker on a retained embankment.

- Sketch v11 (norwood/sk10.py): the platforms are unchanged and the throats are relaxed to his street ends instead of the Station Area KML. The checker uses norwood/limits_utm.json (Foraker, Station, Floral, Smith Road and the ring band; 2.5 m from a track centre).
  - Radii: APEx platform tracks 772 m (was 527); Transvalley 661-1,057 (213); ORR 337-928 (207-417); bays 284-334 (212-232).
  - Tightest point: ORR T2 at 2.6 m from Foraker's edge (s 4,050), on the retained embankment.

- Building: 122 x 46 m with its front on Floral's north edge (o -113.0 to -113.6), about 5 m north of before. The KML area is kept in norwood.json but hidden (build_hwy reads it).

- Metro 3: Ben's line (nw2/l3kml.py) from St Bernard to Norwood Central. It matches the page line within 1 m to about 900 m short of Norwood; piece M-L3-720291-4337966 takes his geometry (rer1023/norwood_pass.py apply_l3, hooked in apply.py). The terminus platform is at frame s 4,585-4,707, o +38. Ross, Aloysius and Bond Hill are unchanged.

- Metro 3's level at Norwood is open: at grade or -1 (Ben leans -1).
  - Its line runs under the Inner Ring for about 2 km, including s 3,932-4,428 just west of the station, and crosses Montgomery at s 4,510.
  - At -1, the terminus's east end (s 4,707) meets the main tunnel (s 4,700-4,718, which reaches o +70).

### 10zzy.26 Norwood Central: elevated concourse, Transvalley junction, building centred (24 October, v112)

Ben: "at grade" means at the station's own (platform) grade, not the street. The platforms are partly sunken, with their roofs at street level and the concourse above them, Baltimore Penn rather than New Haven. The concourse reaches the boulevard on the north side, and the entrance from the station building climbs slightly to it, as at Union Terminal. Metro 3 terminates at platform level, which also leaves more room for Metro 4 and 14 below.

- Elevated concourse: centred on the heritage platforms at s 4,697.5, 30 m wide (a drawing value). It runs from the building over every track to the Inner Ring's south edge. The level -1 main tunnel is gone. The level -1 passage from Metro 4 to TRI A along the axis stays, below the platforms, for the transfers.

- Building: front on Floral, centred on the concourse (s 4,636.5-4,758.5).

- Transvalley east end (norwood/sk10.py, v12): a double junction east of the island.
  - W1 leaves T9 at s 4,850; W2 is T10's line to s 4,950.
  - T9 and T10 go on as the Hamilton pair beside APEx's north side (+7.25 / +11.75), with one diamond where W1 crosses T10 (s 5,022).
  - The prong curve has a straight lead-in at o +28.66 and its minimum radius is now 130 m (was 119); the Waynesville pair used to start in mid-air between the two tracks.
  - East of the station: 8 tracks besides Waynesville (ORR 4, APEx 2, Hamilton 2).

### 10zzy.27 Norwood Central: Waynesville underground to the TRI/TV meet (24 October, v113)

Ben: the Transvalley north (Waynesville) is underground under the streets, so it can be straightened. TRI A and the Transvalley meet at his "TRI/TV Meet" point (frame s 5,233, o +391, on TRI A). It works like SF's Embarcadero / N Judah split in reverse: looking south, TRI goes deeper and the Transvalley climbs towards Norwood. The Transvalley swings south-east to avoid TRI A's box, and is drawn wide (one track each side of TRI A) as the two separate.

- norwood/sk10.py (v13): the centre curve runs from the station lead (o +28.66), swings south-east and joins TRI A at s 5,186 / o +251, then follows TRI A to the meet point.
  - Swing points were searched for radius (nw2/swing_opt.py), keeping the deep part at least 9 m from the box. The centre curve's minimum radius is 121 m; the tracks' are W1 124 m and W2 108 m.
  - The pair widens from 2.25 to 6.75 m half-spacing between s 5,168 and 5,186, on the straighter stretch, and stays 4.0-5.0 m from the TRI A tracks to the meet point.
  - W2 crosses over TRI A once, at the box's north-east corner (s 5,101), where the Transvalley is near the surface. The diamond with Hamilton T10 moved to s 5,051.

- Page: the Waynesville tracks are dashed where underground (o > +60), with a TRI/TV meet marker.

### 10zzy.28 TRI A through Norwood Central (24 October, v114)

Ben asked what happened to RER A's Norwood point. Its station marker had not moved (frame s 5,061), but the line had a 130 m gap right through the station: piece R-A-718498 ended at s 5,009 and R-A-720547 started at s 5,093, with the station between them. There was also a 60 m gap at s 5,158-5,178 to R-A-720769, and no platform was ever drawn. Both gaps date from at least v90.

- rer1023/norwood_pass.py apply_tria (hooked in apply.py):
  - R-A-718498 now runs on across the gap and through R-A-720547's first curve (as polyline points).
  - R-A-720547 now runs to R-A-720769's end.
  - Island platform 204.2 m x 11 m centred on the station (s 4,995-5,122), with tracks re-spread. The marker is on the platform centre (s 5,060, o +4).

### 10zzy.29 Every line unbroken; Line 5 through Pennsylvania (24 October, v115)

Ben asked for every RER and Metro line to be checked for breaks (he had seen RER E broken at Norwood), and for Line 5 at Pennsylvania: the loop stub off the station taken out, the two arms joined, the platform curved east.

The check (nw2/gapcheck2.py) reads each piece as the page draws it, with its curves and Ben's live edits. It found 47 breaks: 13 Metro joins at the plan window edges (0.6-14 m), 11 small RER joins (1-11 m), and 23 real gaps of 43-215 m, nearly all on the KMZ pieces outside the plan window, where a line stopped about 60 or 120 m short of the next piece or of the trunk it branches from. RER E at Norwood was 188.7 m (frame s 4,981-5,170).

The fix (rer1023/gaps_pass.py, hooked into apply.py after the Norwood passes):

- Gaps under 20 m: the loose end point moves onto the other piece.

- End to end: two quadratic curves, tangent to both pieces.

- A branch drawn short of its trunk: one quadratic, landing on the trunk where the two tangent lengths are equal.

- Only an end that is loose for every line it carries may move, and Ben's edited pieces never move (the other piece comes to them).

- Xavier: RER-1y (Milford) and RER-1x (Norwood) both start from the trunk's end.

- Wesselman: RER A runs straight from its north piece to its south piece across D, so A is taken off D's 150 m piece there (R-AD-700206 now carries D only).

- Earlier passes had written 'RER A' / 'RER E' as track line names; now 'A' / 'E' like the rest.

Left open on purpose: the Union Terminal box gaps (B 286 m, D 166 m, A 2.6 m; drawn by ut_box) and lines that end at the plan's outer edge. Two branch junctions land about 60 m inside a shared piece (C at the CVG BCE piece, E at the Crescent Springs BE piece), so the check still lists that shared piece's end for that letter; the line itself is continuous.

Line 5 (apply_l5): stub M-L5-716208-4331118 and the east arm M-L5-716208-4331118-868 are gone; the west arm M-L5-712097 now runs through. The corner is one quadratic from 51 m before the station to 120 m along the old east arm, taking in that arm's own bend; it stays within 3.3 m of the line as drawn and is about 100 m radius at its tightest. The platform is one 121.92 m island on the curve, centred on the station. The same change was written to Ben's live edit of M-L5-712097 (layout version 2080).

Counts: metro pieces 46 to 44, tracks 242 to 238, platforms 730 to 729. Backup deckpage/context_v114.json.

### 10zzy.30 Line 10 on its new right of way (24 October, v116)

Ben sent the new Line 10 alignment (rer1023/line10_1024.kml: "Metro Line 10" and "Line 10", 10.4 km together) and said everything west of it stays as it was. He also sent the Line 10 Baines platform position (KML point "Bains", 716,983 / 4,332,077).

rer1023/l10_pass.py, hooked into apply.py between apply_l5 and the line-joining pass:

- The KML starts on the old line 4,252.5 m along M-L10-710747, just west of Wilstach. The inner piece keeps the old line (with its curves) to there, then follows the KML to the plan window edge (716,800 / 4,331,856.6). The outer piece M-L10-716800-4331840 is the KML from the edge to Ft Thomas.

- The 18 stations from Wilstach east got their platforms rebuilt on the new line: two 121.92 m bore side platforms each (3.4-7.4 m off the centre line), centred where the old ones were. The new line passes within 3 m of the old platform centres, except Bonnie Leslie (7.3 m).

- Baines: the Line 10 platforms are centred on Ben's point, 61 m west of the shared Line 5/10 station mark, which stays where it was. Before this there was only one side platform there; now there are two.

- Bore tracks re-spread at 1.95 m. Line 10 has no breaks. Backup deckpage/context_v115.json.

Addendum (v117): Ben said he could not see the new alignment. The published context matched the KMZ (within 0.05 m), but the KMZ itself is within 26 m of the old line everywhere: 17 m at the corner west of Paradrome, 26 m near Bonnie Leslie, 21 m near Carlisle. Ben's live edit of M-L10-710747 (made after layout v2080) overrides the inner piece on the page; it matches the KMZ's west part within 2.8 m but ends at 716,800 / 4,331,840, so the outer piece's start was pulled 16.6 m onto it. Asked Ben whether the KMZ was the version he meant.

Addendum (v118): Ben showed the page still drawing his older live edit south of Paradrome (the tight loop to Whittaker, radii 24-57 m), not the KMZ. Fixed at the source: l10_pass.edit_fix rewrote his live edit of M-L10-710747 as his edit up to the KMZ start, then the KMZ to the window edge (layout version 2209; within 0.05 m of the KMZ). The v117 snap of the outer piece's start was undone (back to 716,800 / 4,331,856.6, where the edit now ends).

### 10zzy.31 Platform slide to 150 m (24 October, v119)

Ben: the station platform slider stopped at 60 m (half a 400 ft platform), not enough to move the Line 10 Baines platform back from the river turn. index.html: SLIDE_M = 150; slideMax(stop) = max(150, half the platform) now limits the slider, the drag and stopOff. Backup deckpage/index_v118.html.

### 10zzy.32 Western Hills streets from OSM; main roads outside (24 October, v120)

Plan agreed with Ben: modern streets first (as Central Parkway was), the 1922 plates fitted to them after, starting with the southern plates 25, 26, 28 and 29. Inside his boundary (wh/western_hills_area.kml, 44 km2, roughly following roads from Sedamsville to North Fairmount and west to Cheviot) every public street; outside it, out to the plan edges, only the main roads. Pre-war layout: few cul-de-sacs, as in the close Chicago suburbs; where the ground forces otherwise, the plates and the terrain map say where streets go. Widths and lots later.

wh/build_osm.py (set w1, removal file wh/removed.json, in cuf/rebuild_streets.sh after Millvale):

- Source: Historic_Topo/OSM/streets_all.geojson. Inside: residential, unclassified, living street, tertiary, secondary, primary, trunk (no motorways, links, service ways, footways); the boundary buffered 30 m so its own roads come in, and local streets that run past it are cut back to their last junction inside. Outside: tertiary, secondary, primary, trunk.

- Divided roads (a share of 10 m samples with a same-name carriageway 6-45 m off, parallel, over 0.3) are centred with sbg/fit/osmfollow.centreline. Short same-name pieces lying along a longer one (carriageway scraps) are dropped (145).

- Nothing is drawn over what the page has (its streets buffered half-width plus 6 m, its blocks and the deck); ends stopping at that edge are carried onto the page street within 30 m.

- Outside the boundary a road is kept only where it was already there in 1914: black ink of the USGS 1:62,500 West and East Cincinnati quads (1914) within 25 m (wh/q1914.py), scored in 100 m stretches at 0.55, one doubtful stretch between good ones forgiven, runs under 300 m dropped; roads named Expressway, Highway, Bypass, Columbia Parkway, Airport, Aero Parkway, Terminal Drive dropped outright. Tested first: old pikes scored 0.8-1.0 (Harrison, Glenway, Montana, Queen City, Montgomery, Cleves Warsaw, Madison Pike), later roads 0.0-0.4 (Aero Parkway, Eastgate, Ivy Pointe, Ronald Reagan). 523 km dropped.

- Result: inside 898 streets, 388.5 km (SW####); outside 614, 702.1 km (SZ####); 471 inside streets have a dead end (field dead_ends, the post-war pocket candidates for the plate stage). All 50 ft placeholder width (width_src default). basin.json 1.71 to 2.76 MB; page frame times 150-300 m s at deck, area and region scale.

Known: the KY cities (Covington, Newport) and the east side neighbourhoods not yet on the page get only their main roads for now; they are urban, not suburban, and will need the full treatment later. Backup deckpage/basin_v119.json.

Correction (25 October, v121): Ben wanted only the major streets taken from OSM in the area, everything else from the plates. v120's set was undone (basin.json back to basin_v119.json) and rebuilt with primary, secondary and tertiary only, inside his line and out to the plan edges, without the 1914 dating or the name exclusions. Inside 57 streets, 101.5 km; outside 800, 1,195.6 km. The first version is kept as wh/build_osm_v120.py.

Correction (25 October, v122): Ben: primary and secondary only. Rebuilt: inside 23 streets, 47.5 km; outside 394, 555.8 km.

### 10zzy.33 Price Hill plates 26a, 26b, 29 around the OSM streets (25 October, v123)

Ben: plates next, southern ones first (25, 26, 28, 29). His New Sanborn folder has 26a (southern Price Hill, Sedamsville, Lower Price Hill), 26b (west Price Hill, St. Joseph Cemetery; the second "26" on the index) and 29 (East Price Hill and the valley); 25 and 28 are not there (no PNG or GeoTIFF), so Ben was asked for them.

Process as cufp/PROCESS_1922.md, with these plate ids 26A, 26B, 29:

- Prep from the GeoTIFF seed (26A 4,436 points, rms 1.9 px; 29 4,067, 2.0 px); 26B has no GeoTIFF and was seeded from street names. GeoTIFFs deleted after prep.

- Readers: 6 strips each for 26A and 29, 3 for 26B (sbg/picks22/s22-26A_a..f, s22-29_a..f, s22-26B_a..c).

- Fit (cufp/fit.py; new OSM extract lph/osm_west.geojson, E 703,500-713,500, N 4,327,500-4,334,500; aliases Mt. Hope Road = Mount Hope Avenue, Filson Terrace = Filson Place, Alpine Way = Alpine Place): 26A tps3, 49 controls, leave-one-out about 3.0 m; 29 tps0.3, 72 controls, 2.8 m; 26B tps0.3, 11 controls, 3.5 m (mostly cemetery and estates). 26A and 29 agree on 12 shared crossings within 1.5 m median, 4.2 m max. Streets gone since 1922 (Kansas, Littleton, English, Doll, Amelia, Denver, Seminary, Wallace, Dutten, Claypool) have no OSM control.

- 1922 layer: cuf/tiles22.py ran out of memory with every plate held at once; cuf/tiles22_add.py adds plates tile by tile under what existing tiles show and rebuilds the index and overview (32 tiles added, 179 in all).

- Streets (cufp/build.py, config keep_sets ["w1"], avoid_existing, clip_to wh/area_utm.json): the OSM primary and secondary streets stay as they are and plate pieces lying along them are cut back (18 m) and snapped onto them; the plate takes only ground the page has not drawn (existing streets buffered half-width plus 6 m and closed over 180 m gaps, existing blocks), so Lower Price Hill, the deck and the valley stay; and only inside Ben's line. Set c29 32 streets, 29 blocks (94.5 ha); c26A 34 streets, 29 blocks (113.7 ha); c26B 8 streets, 5 blocks (69.5 ha). Widths printed where read, else 50 ft.

- Rebuild order (cuf/rebuild_streets.sh): wh/build_osm.py, then 29, 26A, 26B; build_osm ignores these plate sets so it never loses ground to them.

Backups: deckpage/basin_v122.json, deckpage/tiles_22_v122/, cufp/build_v122.py.

### 10zzy.34 Fairmount plates 31 and 33 (25 October, v124)

Same process as 10zzy.33. Plate ids 31 (South Fairmount) and 33 (North Fairmount); GeoTIFF seeds (31: 5,545 points, 1.75 px rms; 33: 4,748, 1.82 px), GeoTIFFs deleted after prep. Six readers each (a weekly rate limit cut seven of them off part-way; they were resumed and finished).

- cufp/fit.py now also matches a street whose suffix changed since 1922 on its stem when that stem is one OSM street (Quebec Avenue = Quebec Road); a wrong pairing is caught by the 6 m residual test. Refits: 26A 49 controls, 29 72 (unchanged).
- 31: tps1, 31 controls, fit 1.8 m (many 1922 streets in Lick Run and South Fairmount are gone, so few controls). 33: tps0.3, 62 controls, fit 1.4 m, leave-one-out about 3.7 m. Shared crossings: 29/31 2.3 m median (6.3 max), 31/33 2.8 m median (10.0 max, Garrard / Queen City at the plate edge).
- Tiles: cuf/tiles22_add.py 22-31 22-33 (29 tiles, 197 in all).
- Streets: c31 22 streets, 12 blocks (86.1 ha; Ben's line leaves out most of South Fairmount's middle and east); c33 64 streets, 65 blocks (165.3 ha). Brestel Road (an estate loop road on 33) left out with a new build.py config option "drop".
- Rebuild order: wh/build_osm.py, then 29, 26A, 26B, 31, 33. Backup deckpage/basin_v123.json.

### 10zzy.35 North trunk, option 3: RER B east, ORR beside APEx, on to the split and Norwood (25 October, v125)

Ben: option 3 (RER B on the east edge), with the B/D split widened like the other splits, the viaduct widened at the stations, and the geometry consistent with the upper (Indianapolis + D) and lower (R5) decks across the Millvale grid.

Code: trunk/frames.py (trunk, Dayton and Norwood frames), trunk/plan.py (offsets, levels), trunk/north_pass.py (installs into context.json and tracks.json; hooked at the end of rer1023/apply.py). cut/structures.py: fill section uses the ten north tracks; new Transvalley and B/X2 flyover structures. apply.py itself no longer runs (handoff/page/lines/index.json is gone), so the pass was applied to the v124 data directly.

- B/D passes under ORR while still 6.8 m or more below the viaduct and comes up east of it; ORR runs straight at 18/22.5 m from Marshall (no 22 m jog). Camp Washington island at 29.25/43.75 m.
- Flying junction at s 3,200: southbound D keeps the west track, southbound B turns out east, northbound D turns out between the two B tracks. D climbs 2.5%; northbound D crosses over southbound B at s 3,500-3,590 (7.0 m), then the D pair at 174.3 m drifts over ORR onto the Indianapolis deck (unchanged from s 3,864).
- Arlington island 29.25/43.75 m on the east edge. After it ORR moves in to 9/13.5 m and B to 20.25/24.75 m (s 4,430-4,780).
- North of Ludlow: ten tracks, west to east Transvalley, APEx Dayton, APEx Norwood, ORR, B. The corridor bends up to 18 m west (s 5,050-5,400, eased back by s 7,300) so B's Northside / Spring Grove island (20.25/34.75 m) clears the OH-75 parkway by about 3 m; nothing stands on the west side there.
- Transvalley holds 162.5 m off the fill and crosses over APEx Dayton (s 6,000-6,300, 8.7 m or more), ground by about s 6,720; Dayton moves 13.5 m west under it. Transvalley then sits between the APEx pairs, its order at Norwood.
- Mitchell Ave island at ground, east edge. ORR X2 turns out east after it (s 7,949-8,149; southbound X2 crosses ORR northbound on the level). B and X2 climb 2.5% from s 8,208, are 7.3 m over the Norwood tracks s 8,500-8,875, ground by s 9,167.
- Dayton leaves the KMZ line at s 8,568 on a 1,000 m curve onto the Southwest Chief straight; Norwood tracks carry straight on (first curve about 650 m) along the Transcontinental, easing to Norwood Central's 8.25 m group gaps and meeting T10/T9, T7/T6, T4/T2 exactly.
- Ivorydale island east of X2. B outside the window redrawn 22.5 m east of the Southwest Chief line. X2 drawn to the RER window edge. Crossovers: one set each in the Dayton and Norwood pairs.
- Ben's live edit of the B/D piece got the same change north of s 2,460 (DB version 2287 to 2288).

Open: Transvalley placement (my choice, flyover over Dayton); the X2 flat crossing; the Inner Ring west end (J7) sits on the Norwood branch near E 716,700-717,200 and needs a bridge; street cuts at the moved B/D ramp at Camp Washington not re-run. Backups *_v124 (context, tracks, structures, apply.py, structures.py).
