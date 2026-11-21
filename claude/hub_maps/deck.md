# Deck, streets, plots, transit drawn, bridges: data model map (read-only survey, branch hub_region)

## 1. Files and how the page loads them

`hub/sites/deck/index.html` (2,840 lines, 360 KB, one IIFE from line 348; JSTS 2.12.1 from a CDN, line 6). In `boot()` (2784-2811), `deck.json`, `context.json`, `sheets.json`, `tiles_n/index.json` and `relief.json` are fetched in parallel. Then the others load one after another, each in try/catch: `tracks.json`, `structures.json`, `viaducts.json`, `hwy.json`, `yard.json`, `norwood.json`, `airport.json` and `basin.json`. basin.json's features are pushed into `S.deck.features`, so the basin and the deck are one feature list. `plots.json` loads asynchronously, followed by the `tiles12`, `tiles_22` and `tiles_b` indexes. `RECS` (2813) also loads the hub records `metro_structure`, `station_types`, `station_platform_default` and `tube_points` from `<k>.json` or from the db `params/<k>`. The layout is one document, `deck/layout`, saved through `window.claude.use('db')` (the old shim, 2815-2832).

| File | Raw MB | gzip MB | Items | Vertices | Last commit |
|---|---|---|---|---|---|
| plots.json | 3.35 | 0.76 | 32,464 plots | 232,180 | 2026-10-29 |
| basin.json | 2.35 | 0.36 | 5,587 | 43,143 | 2026-11-14 (lane B) |
| context.json | 1.91 | 0.56 | 1,605 rows | 77,573 | |
| tracks.json | 1.48 | 0.42 | 312 + cvx | 59,669 | |
| yard.json | 0.79 | 0.18 | 356 | 34,940 | |
| hwy.json | 0.64 | 0.16 | 322 | 15,544 | |
| deck.json | 0.50 | 0.13 | 398 | 16,901 | 2026-10-29 |
| airport.json | 0.24 | 0.06 | 311 | 4,372 | |
| norwood / structures / viaducts / sheets | 0.10 / 0.08 / 0.08 / 0.06 | | 33 / 55 / 12 / 386 | | |

- **Total vector data:** about 11.6 MB raw, about 2.8 MB gzipped.
- **CRS:** EPSG:26916 (UTM 16N), in metres, declared as `"crs":"EPSG:26916"` (a string, not a GeoJSON crs object) in deck, basin, tracks, yard and airport. Exports convert to CRS84 with `utmToLL` (378-389).
- **data/deck/:** `deck`, `norwood`, `structures` and `tracks` are byte-identical to the hub/sites copies. `context.json` differs only in `rer_marks`. `rer_routes.geojson` (2.9 MB, CRS84 lon/lat, no crs member) is the export written by the Deck tie: the Deck run headless by `tools/station3d/harness.js` from `hub/pipeline.py:218-221`.
- **Generators:** none in the repo for deck, plots, sheets, context, tracks, hwy, yard, norwood or relief (Code_Scrutiny line 103). `basin.json`, `plots.json`, `tiles_22` and the staged `deck`/`tracks`/`context` are rewritten by lane B's `data/sanborn/apply/apply.py`.

## 2. Feature kinds, fields, counts, ids

### deck.json: 398 features

- **Top-level metadata:** `params` (blvd_w 70, rb_r 80, sq 140, park_w 100, hh_w/hh_d, plat_w 152, palace_w/d/gap, t_w and ns_w 18.288). Also `axis`, `cut`, `garrard`, `anchors` (29 sheet anchors: name, side, sheet, px, pt, w_ft, basin_pt), `dive_cut`, and build logs `fill17`, `aligned17`, `clean17`, `edge17`, `plan17`, `campw18`, `cwscrap18`. `cwscrap18` lists 27 streets removed, 10 cut, 128 blocks and 2,242 lots removed.
- **block, 309:** Polygon 306, MultiPolygon 3. Fields: `id`, `type` (building 274, planting 18, square 16, park 1), `area_m2`, `side`, `name`, and the flags extended17, clean17, edge17, joined17. Ids are `B###` (184) and `FB###` (125).
- **street, 67 LineStrings:** `id`, `name`, `kind` (through 23, WV 21, T 10, NS 7, radial 4, frontage 2), `width_m`, `side`, `zone` (1, 2 or 3), `cut`, `note`. Ids are `S###` and `S###E`.
- **wv_cut 5 and wv_regrade 3 (Points):** `street`, `by`, `rail`, `street_z`, `diff`, `need`, `how`, `label`. These are street re-grade levels.
- **Singletons:** deck, axis, boulevard, roundabout, palace, forecourt, cut_square, cut_park, cut_headhouse, cut_precinct, cut_building (Union Terminal), cut_concourse, dive_cut, rail_open. They have no ids, only `name`.

### basin.json: 5,587 features

- **Top level:** `source` (1904 Sanborn, 154 sheets in one joint fit) and `ezzard17`.
- **street, 2,941 LineStrings:** `kind` is we_street 2,282 or we_alley 659. Fields: `width_m`, `width_ft`, `width_src` (printed 2,080, default 782, …), `src` (Sanborn 1904: 1,502; Sanborn 1922: 985; OSM: 408; Millvale grid: 38; …), `sheets`, `geom_src` (50+ distinct strings), `set` (plate set: c66, c68, w1, ma, v3, mv, lph, wv, hwy …), `osm_class`, `clip_by`, `ext_by`, `structure` (deck level / underpass), `cut`, `check`, `note`, `wv`, `kept_for_edit`.
  - Ids use plate-set prefixes: SB 1,030, SZ 384, SM 261, SV 143, S 105, SP 83, SR 68 … plus SMV, LPH, SBW, HW, EZ.
  - **`SR0018` and `SR0051` are each present twice** (exact copies, from "apply 2026-11-07 … kept for Ben's edit"). The page's `streetById` keeps the last copy.
- **block, 2,573:** `type` is building 2,560 or park 13. Fields: `area_m2`, `name`, `src`, `set`. Ids are SBB 1,241, SMB 210, SPB 129, SMVB 107, SYB 95 … LPHB.
- **CUT plan pieces from the 1931 plot plan:** cut_walk 46, cut_lawn 13, cut_road 8 (with `kind`), plus cut_lincoln, cut_plaza, cut_terrace and wv_cut 3.
- **Extent:** E 699,000-736,900, N 4,320,800-4,347,000 (38 × 26 km, because of the OSM roads).

Together, deck and basin hold 3,008 streets (3,006 unique ids) and 2,882 blocks.

### plots.json: 32,464 plots, compact encoding

- **Layout:** `{o:[711500,4330100], labels:[2,842 sheet-label strings], plots:[[id, block, kind, street, u0, labelIdx[], rings]], edgelots17:{…}}`.
- **Rings:** each ring is `[x0,y0,dx1,dy1,…]` in integer decimetres from `o`, delta-encoded (`decodePlots`, 878-887). Rings per plot: 1 (32,368), 2 (91), 3 (5).
- **kind:** l = lot (31,798), i = interior (618), o = open (48). `street` is a frontage street id (null for 817). `u0` is the use read from the sheet (i 2,156, c 1,637, v 189, w 134, s 71, p 12, l 2; null 28,263).
- **Ids:** `{block}-{NNN}` (for example `SBB0843-103`), plus `B###-F##`, `FB###-E##` and one `SBB…~a`. Blocks with plots: 1,563.
- **1,319 base blocks have no plots** (892 from Sanborn 1922, 316 from 1904, 111 Millvale), because plots.json predates the 1922 work.
- **Extent:** E 711,530-716,321, N 4,330,133-4,338,161.

### context.json: Metro and RER as drawn

- **`metro` (44 pieces, 15 line names):** `id` (`M-L{n}-{E}-{N}`, for example `M-L1-714186-4339800`), `name`, `era` (twin 27, bore 17), `c` (vertices), `k` (`{segIndex:[x,y]}` quadratic control points), `curves` (`[R, x, y]`), `hs` (`[x, y, bored 0/1]` every 20 m; 42 pieces), `sub`, `outer` (28).
- **`rer` (73 pieces):** `id` (`R-{letters}-{E}-{N}`), `name`, `lines[]`, `sub`, `c`, `k`, `curves`.
- **Stations:** `stations` (339 Metro: `{name, line, p}`) and `rer_stations` (131: `{name, lines[], p}`).
- **`tracks` (238: rer 150, metro 88):** `{sys, line, pid, c, name}`.
- **`plats` (730: metro 599, rer 131):** `{sys, line, pid, st, id:'P-M-L2-E-N', c ring}`.
- **Other lists:** `marks` 10, `rer_struct` 16 (`{line, state (viaduct, ramp, deck, tunnel, embankment), s0, s1, c}`), `rer_marks` 24.
- **`meta`:** metro_platform_m 121.92, rer_platform_m 204.2, metro_twin/bore/rer half-spacings, taper_m 40, ut_box offsets, bd_approach, metro_spacing.

### tracks.json: 312 features plus `cvx` and `summary`

- **Features:** apex 116 (name, level, kind, state, num, kmh), marker 110, lower 53 (level −2, rail), label 10, apex_plat 8 (rail 160.3, length_m 488, width_m), bridge 8 (rail_m, clearance_ft), lower_plat 4, passing 1, cvg_yard 1, cvg_shop 1.
- **`cvx` (the CVG Express line):** `{id:'CVX', platform_m 200, island_m, side_m, h0, edge, v, k, stations[5] {name, p, z, ground, depth, km, o0}, plats[10], tracks[4]}`.
- **`summary`:** 37 level and design keys.

### structures.json (55) and viaducts.json (12)

- **structures.json, `rule`:** `edge_m` 4.2, `close_m` 3.0. Footprints are the outer track centre plus 4.2 m each side, and gaps under 6 m are decked over.
- **`struct` (16 footprints):** `{name, kind: viaduct | station | trough | viaduct_existing | bridge | embankment, note, area_m2, tracks (free text), w_min, w_max, length_m, rer_platforms}`. Examples: CUT approach viaduct (south) 72,097 m²; North arch viaduct 438,350 m²; C&O pair trough and viaduct; APEx bridge; CVG Express span; CS bridge (1922); C&O bridge (1929); Ludlow underbridge.
- **`struct_w`:** 39 width-label points `{width_m, of}`.
- **viaducts.json:** 12 `viaduct_part` features `{sel, name, area_m2}`. The `sel` values are north_arch, cut_arch, cut_kentucky, cut_cardinal, cut_cvgx, cw_upper, cw_lower, cno, westwood, northgate, northside and wh_sc.
  - They are written by `tools/viaduct_parts.py`, which uses structures.json, the Profiles context and the elevated runs in `hub/work/harness_out.json` (half-width 6.45 m), simplified to 0.3 m.
  - `VIA_REPLACED` (1798) hides four parent structs that these parts replace.

### Other layers

- **hwy.json (322):** hw_strip 161 (kind, piece, tunnel), hw_line 101, hw_sig 36, hw_lab 12, hw_piece 11 (`w`, route, type, km, section text), hw_area 1.
- **yard.json (356, footprint_ha 85.1):** yard_track 236, ud_line 51, ud_box 34 (rail, sys), yard_mark 12 (deck and floor levels), yard_xing 8, yard_hist 4, yard_lead 4, yard_fan 3 (tracks, floor), yard_limit, yard_today, deck_col, deck_cell.
- **norwood.json (33):** nw_track 16 (sys, track), nw_plat 6, nw_lab 6, nw_area, nw_mark, nw_bldg, nw_conc, nw_pass.
- **airport.json (311):** cvg_stand 148 (terminal, cls, airline, w, d), cvg_taxi_cl 132, cvg_building 7, cvg_apron 7, cvg_runway 5, cvg_runway_cl 5, cvg_area 5, cvg_taxi 2.
- **sheets.json:** 386 sheet outlines `{sheet, vol, poly[4], basin?}`. Volumes 1904 vol. 1-6 (381) and 1922 vol. 1 (5).
- **Ids:** none of the layers in this section have feature ids, only names.

## 3. The edit model (layout document)

`S.edits = {streets, blocks, transit, stations, plots, plotOps}`. It is saved whole (325 KB) with `updated` and `layout:'deck.json'` (`flush`, 2486-2501, with `ifVersion`). The seed copy is `hub/seed/deck/layout.json` (2026-11-05): 324 street, 56 block, 14 transit, 100 station and 163 plot entries, and 266 plotOps (s 129, m 120, f 13, d 4).

### streets[id]

Edits are keyed by the base street id and merged over the generated feature (`setEdit` 2336-2346, `patchStreet` 774-780). There is no way to create a new street; only base ids can be edited.

- `c`: full vertex list. `k`: `{segIndex:[x,y]}` quadratic control points.
- `w`: width. `wv[]`: per-segment widths, length n−1, null meaning the default. `ov[]`: per-segment sideways offsets. `jo`: `{vertexIndex: offset}`, a shifted joint.
- `n`: name. `del`. `into`: merged into this id. `mg`: `{ids, pre: {id: previous edit}}`, which allows unmerge (`mergeStreets` 1338-1351). `note`.

Seed counts: c 207, del 120, into 74, mg 58, note 48, n 26, w 21, wv 8, jo 4, k 4. `wv`, `ov` and `jo` are keyed by vertex index and remapped when `c` changes (`remapWv`). **22 street edits reference ids that no longer exist in the base** (S0901, S066, …, all scrapped Camp Washington streets).

### blocks[id]

Fields: `t` (type), `n` (name), `u` (use for every plot), `lk` (date locked, ISO), `arc` (arcade: blind, shops or open). A legacy form stores the type as a bare string. Seed: lk 56, t 8, u 3, n 1. One orphan edit: B028.

### plots[id]

Fields: `u` (use code from `USES`: r, m, c, i, w, v, s, l, k, p, o) and `n` (name). The lookup falls back along `chainIds` (889): `X.1.2` → `X.1` → `X`, and `X~a` → `X`. Use precedence is the plot's own, then its parent's, then the block's `u`, then the sheet's `u0`, then the block type (`plotUse`/`baseUse`, 1215-1226). 126 of the 163 plot edits are on derived ids that exist only after the ops replay. Every one resolves to a base root.

### plotOps (ordered list, replayed by `applyOps`, 1030-1075)

| op | fields | result |
|---|---|---|
| `m` merge | `{t:'m', ids:[target, …]}` | the union keeps `ids[0]` |
| `s` split | `{t:'s', id, l:[p0, p1]}` | `id.1`, `id.2` |
| `d` divide | `{t:'d', id, n (2-60), a (rad)}` | `id.1`…`id.n` strips |
| `r` regrid | `{t:'r', id:'R'+base36 time, ids, w (3-60, default 7.6), a}` | lots square to the long side, two rows if deeper than 55 m |
| `f` fill | `{t:'f', q:[x,y], to}`, or `{q, n, a}` | adds open land to plot `to`, or makes new plots `F{E}_{N}[.k]` |

- **Piece ids:** results that come out as several pieces become `id`, `id~a`, `id~b` … (largest piece keeps the id).
- **Skipped ops:** an op whose inputs are missing is skipped silently.
- **Open land:** pieces get ids `open:{E}:{N}`.
- **Blocks:** live blocks get `gen` and `joined[]`, with ids `gen` or `gen~a`.

### rebuildPlots (1082-1197)

1. Changed streets get new and old corridors (JSTS buffer: flat caps, mitred joins in the basin, round on the deck), cut into 60 m tiles.
2. Base plots are cut by the new corridors and swept out to the old centreline.
3. Land no plot takes becomes open land.
4. `applyOps` runs.
5. Blocks are rebuilt and joined where they touch within 6 cm (O(n²)).

Results are memoised on geometry signatures to 1 cm.

### transit[id] and stations

- **transit[id]:** `{c, k}`, on Metro and RER piece ids (14 in the seed).
- **stations[key]:** the key is `stKey` (669), `sys:name:round(E):round(N)`. Fields: `{del, complex (shared label), s: {pieceId: {t: 'island' | 'side', o: metres from the station point}}}`. Seed: s 96 (o 98, t 35), del 7, complex 1.

### mergeEdits (2502-2521)

The merge is three-way per entry (base, mine, theirs). Streets, blocks, transit and plots merge at depth 0. Stations merge to depth 2, so a platform-tie offset on one platform and an edit to another platform of the same station both survive. `plotOps` is replaced whole if mine changed. Undo keeps up to 200 whole-JSON snapshots.

## 4. Stations and platforms drawn from settings (592-766)

- **Inputs:** `buildTransitFeats` turns context rows and `cvx` into `transit` features and `plat` polygons. `buildStations` creates one point per (sys, name, p) and groups platforms by `sys|pid|st` into *stops*.
- **Stop record:** `{key, pid, sys, era, plats, type0 (side if ≥2 platforms, else island), L (canon length: Metro 121.92, RER 204.2, CVX 200), o0, lat0, w0}`. These are measured on the generated line.
- **Drawn from settings:** a line is drawn this way once it, or one of its stations, is edited. **Every Metro line is always drawn this way** (`liveLines`, 724).
  - Platforms come from `stopBands`: island width from `MSR.island_box` (8.0, edges 1.45) or `PW` (RER 11.0, side 6.0).
  - The slide is clamped to ±max(150 m, L/2).
  - The default type follows `params/station_platform_default`, then `station_types` (`name#idx` keys), then the bored flag from `hs`.
- **Tracks:** `trackPair` draws each line's two tracks from half-spacing. The source is `tube_points` if present, else `hs` with `MSR` (tubes A 8.74, C 9.14, bore and box 3.9), opened out round islands with 40 m tapers.
- **Export:** `transitFeatures` (2716) writes metro/rer/cvx `_line`, `_station` and `_platform` features. Platform fields are `station_id`, `pid`, `type`, `offset_m`, `slide_max_m` and `drawn_from_settings`. The current rer_routes.geojson holds 44 metro_line, 73 rer_line, 339 metro_station, 131 rer_station, 681 metro_platform and 132 rer_platform (no cvx).
- **Downstream consumers:**
  - `tools/rer_deck_routes.py` ties each RER route's `segs` (`{piece, lines, pa, pb, fwd, c0, c1, u, v}`) to Deck piece ids, falling back to the nearest piece of the same letter. Tolerances: TOL 0.5 m, STATION_TOL 1.0 m.
  - `tools/platform_tie.py` writes Profiles slides back as `stations[station_id].s[pid].o`. Where both sides moved, the newer one wins, using `params/platform_sync`.

## 5. Sanborn tiles and relief

- **Index and naming:** each index is `{size (m), res (m/px), tiles:[[E, N], …]}`. A tile URL is `{dir}/{E}_{N}.webp`, where (E, N) is the tile's south-west corner in UTM, drawn from (E, N+size) (1412-1478).
- **Overviews:** `overview.json` is `{E0, N0, E1, N1, res: 2}`. The page uses the overview below 1.2 px/m and the tiles above it.
- **Tile format (from `tools/sanborn/cuf/tiles22.py`):** RGBA WebP at quality 72, transparent outside the plates.

| Set | Tiles | Tile size | Resolution | px per tile | Area | Overview |
|---|---|---|---|---|---|---|
| tiles_22 (1922 plates) | 267 | 512 m | 0.25 m | 2048 | about 70 km² | 7680×4864, 2.68 MB |
| tiles_n (1904) | 137 | 512 m | 0.25 m | 2048 | | 3840×4608, 0.76 MB |
| tiles_b (basin, 1904) | 45 | 512 m | 0.25 m | 2048 | | 2304×2048, 0.39 MB |
| tiles12 (1912 survey) | 15 | 1000 m | 0.5 m | 2000 | | none |

- **Tiles in this checkout:** none. `.webp` files are gitignored, except the overviews. `du -sh`: tiles_22 2.6 MB, tiles_n 756 KB, tiles_b 400 KB, tiles12 12 KB, all overview and index only.
- **Tile sizes:** per-tile sizes are not found in the repo. The source is `Maps\MCD_Tiles_Snapshot` on Ben's machine: 404 files at snapshot time (`docs/sanborn/Sanborn_Pipeline_Migration_Plan.md:23`), against 464 index entries now.
- **Relief:** `relief.webp` is 1200×2600 RGB at 2 m (80 KB), bounds from `relief.json`.

## 6. River bridges (design/river_bridges/)

### The page

`Cincinnati_River_Bridges.html` is 2.8 MB, three.js r128. Coordinates are in a local C&O frame: x along the bridge (Ohio side negative), z downstream, elevations absolute, DATUM 130. **No transform to UTM was found.** Checklist 2.0.12 leans toward deriving it from the Bridge Spans KMZ line.

**Main bridge (two Ludendorff-type bridges side by side, sharing the middle rib):**
- `L` 473.46 m of steel. `MAIN` = [129.77, 338.71] are the pier chainages. Spans are 129.77 + 208.94 + 134.75.
- `RAIL` 165.3. `RIVER` 139.62. `FL` (underside of the floor) 162.3.
- Arch rise 38.12 m (28.5 × span/156.21). DS 13 and DC 7 are the side-truss and crown truss depths. Parker side trusses: DS1 12.5, SMAX 19. Hinge at 158.3. Camber 0.25 m.
- Ribs at z = 7.6, −7.6 and −22.8. The new pair sits at z = 0 and the old pair at −15.2. PH 6, AB 10.

**Approaches:**
- `RT`: trough 0-170, climb 170-740 (2.12 % up to 160.3), quad-track viaduct 740-1570.9.
  - The S/W pair runs 9 m south of the N/E pair, with piers about 25 m apart. The viaduct rises from 160.3 to 165.3.
  - Curves onto the bridge: N/E R 721.8 m over 335.8 m; S/W R 771.7 m over 320.2 m.
  - Each pair is stored as `pts` [s, x, z, rail] (383 and 234 points) plus a `streets` list.
- `KY` (Kentucky approach):
  - Quad-track alignment 1,199 m long, on curves R1 1550 and R2 697.
  - Covington Union station 696.7-1034.7 m from the abutment, with two islands of 304.8 × 7.0 m.
  - Arcade from 460 m. Street clearances: Pike-Russell 4.3 m, W 8th 3.5 m.
  - `sec` holds 480 cross-section rows.

**Embedded grids and lines:**
- `TER`: terrain grid, 725×666 at 5 m, Int16 in base64.
- `RIV`: river grid, 1566×1845 at 10 m.
- `RC3`: 2,108 points with 11 stations, platform 204.2.
- `EMB`: river embankment.

The `facts` table (about 26 rows of value plus source) records Ben's rulings with dates.

### KMZ/KML files

- `Bridge_Spans.kmz`: 8 two-point LineStrings, one per bridge span: CS, C&O, Roebling, Cincy-Newport, L&N (4 points), APEx 4Track, CVX, CWB.
- `covington_approach.kmz`: the station area outline, 7 street polygons and 10 spot heights in feet (492-522 ft).
- `Cincinnati-Covington.kml`: one 98-point LineString with absolute rail levels (NAVD88), 165.3 down to 162.74 m.

## 7. What a merge-on-read street and plot model must preserve

- **Base ids are the join key** for every edit. Street ids follow plate-set prefixes. Lane B's `apply.py` keeps them stable:
  - `carry_set` matches a rebuilt street to an old one by name and mean distance under 40 m, and a rebuilt block by IoU over 0.3.
  - Ids that appear in Ben's layout get first claim. New features get numbers above the prefix's highest.
  - `finish` keeps an old feature whose id Ben's layout uses, marked `kept_for_edit`. This is where the duplicates come from.
- **Derived plot ids** (`X.1.2`, `X~a`, `F{E}_{N}`, `R…`) exist only after the ordered replay. Ops refer to them, so the op order and the deterministic ids are part of the data.
- **Orphans exist:** 22 street edits and 1 block edit point at ids that are gone. They need to be listed, not silently dropped.
- **Use and name inheritance** runs along the id chain and block → sheet → type.
- **Locks:** `lk` marks blocks whose plots Ben checked by hand. An import must not touch locked blocks.
- **Per-segment arrays** (`wv`, `ov`, `jo`) are keyed by vertex index and break when vertices change.
- **Station keys depend on coordinates**, so moving a station point orphans its edits.

## What the new hub must support from this part

- **Ingest all base layers as frozen base v1** in UTM 16N. Kinds and counts as in section 2:
  - 3,008 streets, 2,882 blocks, 32,464 plots and 2,842 sheet labels.
  - 44 Metro and 73 RER pieces, 470 stations and 730 platforms, 238 tracks, plus CVX.
  - 16 structs, 39 width labels and 12 viaduct parts; hwy 322, yard 356, Norwood 33, CVG 311, sheets 386 and 312 track-file features.
  - Keep every property as an open attribute bag: `src`, `set`, `geom_src`, `width_src` and the build flags are provenance.
- **An alias table** from old keys to stable ids:
  - street, block and plot ids, plus derived plot ids;
  - `M-L…`/`R-…` piece ids and `P-…` platform ids;
  - `sys:name:E:N` station keys and the Profiles `name#i` keys.
- **Enforce id uniqueness on import:** SR0018 and SR0051 are duplicated today.
- **An edit store separate from the base:**
  - street patches (`c`, `k`, `w`, `wv`, `ov`, `jo`, `n`, `del`, `into`, `mg`, `note`) and block patches (`t`, `n`, `u`, `lk`, `arc`);
  - plot patches (`u`, `n`) and station patches (`del`, `complex`, `s[pid].{t, o}`);
  - transit patches (`c`, `k`);
  - plotOps in order (m, s, d, r, f) with a deterministic replay and a golden test against `hub/seed/deck/layout.json`.
- **Ways to create features:** new streets (impossible in the old Deck), authored blocks and lots. Each needs an `origin` and a per-feature version.
- **An import merge** that carries ids by name and geometry the way `apply.py` does, never moves an authored feature or a locked block, and reports orphaned and conflicting edits.
- **A street model with segment attributes** (width, offset, joint) keyed by chainage or a stable vertex id rather than an index, so sidewalks and kerbs can be derived later.
- **Plots** that keep `kind`, `street` (frontage), `u0` and labels. 1,319 blocks (mostly from the 1922 plates) still need plots generated.
- **Platforms as records** with their own id: line piece, station, type, length, offset and slide limit. Settings needed: `MSR`, the `PW`/`EDGE`/`H0` half-spacings, a 40 m taper, a 150 m slide, and the canon lengths (121.92, 204.2, 200).
- **Structure records:**
  - kind, tracks, width (min and max), edge rule (4.2 m and 3 m), levels, and a parent/part relation (the `sel` parts replace their parent structs);
  - for bridges: spans, pier chainages, rail and river levels, truss parameters, the quad-track approach with its stretches (trough, climb, quad) and curves, the Kentucky station, and street clearances;
  - a C&O frame to UTM transform, derived from `Bridge_Spans.kmz`;
  - KMZ ingest with absolute Z.
- **Rasters:**
  - the four Sanborn tile sets (512 m/0.25 m WebP RGBA and 1000 m/0.5 m), whose files live on Ben's disk and are addressed by the south-west corner, plus the 2 m overviews and the relief image;
  - convert to PMTiles or COG pyramids; tiles_22 alone covers about 70 km² at 0.25 m (about 1.1 Gpx);
  - consume new tiles_22 plates and tiles12 when lane B lands them, without blocking on them.
- **Vector delivery:** about 11.6 MB raw (2.8 MB gzipped). plots.json (232k vertices) and basin.json are the candidates for vector tiles or FlatGeobuf. The other layers are small enough to stay as GeoJSON records.
- **A Deck export compatible with today's consumers:** `rer_routes.geojson` layers and fields for `rer_deck_routes.py`, `platform_tie.py` and `viaduct_parts.py`, until those tools are replaced. The two copies of `data/deck` and `hub/sites/deck` should become one.
