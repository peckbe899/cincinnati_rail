# The 1912 ground, re-derived: what the local session delivers and how the cloud session uses it

Written 6 November 2026 for a Claude Code session on Ben's computer (reads the raw sheets) and the cloud session on
`hub_region` (reads only what is in git). Everything below is a contract: paths, grids, formats, fields, limits, and
the handshake. If something here cannot be met, the local session writes why in `STATUS.json` and stops; it does not
improvise a different layout.

## 0. Why this is being done, and what went wrong before

Read this before the rest. The old 3D conversation lost weeks to exactly these faults; the local session is expected
to do better by knowing them.

**Why a true 1912 surface matters.** The Metro's early phases (1905 to the 1930s) are tunnelled and cut into the
ground as it was then. The tunnel engine decides box or bore, cover and portals from the ground surface along each
line, and the earthworks model composes every later year on top of the 1912 base. If the base is today's ground,
every early-phase profile is wrong wherever the land has changed since 1912: fills, cuts, yards, quarries, the whole
Mill Creek valley floor. Measured on 6 November: outside every recorded work, map 3 and the current "1912" surface
differ by 0.94 m on average over 615 km², with 82 km² over 2 m and 20 km² over 5 m, and those are only the places
the two surfaces happen to differ, not the real 1912 changes.

**What the current file actually is.** `canon_1912_ground_dm.vrt` was made by the I4 method: the 1912 contours were
vectorised and labelled, a true 1912 surface was solved per tile (`pilot_*_S1912`), and then `tile_mosaic.py` built
the final surface from cleaned LiDAR everywhere, using the 1912 surface only inside the works zones, with the 1912
contour texture added below about 30 m. A cross-correlation test on 6 November found zero shift and a correlation of
1.00 between it and map 3: it is LiDAR at every scale that matters. The real 1912 surfaces that were solved per tile
were not kept as the product.

**The problems that caused it, each avoided by this spec.**

1. *The product was a picture, not data.* Only the final raster survived; the contours, labels, per-tile surfaces
   and registration residuals stayed in a cloud workspace and were mostly lost. Here the contours and the fit are
   the product (sections 4.2, 4.3, 4.7) and the raster is derived from them.
2. *A blend hid the gaps.* Where contours were sparse or the sheet was blank, LiDAR was filled in silently, so the
   file looks complete and is wrong. Here nodata means nodata (4.4), and the confidence raster (4.5) says how much to
   trust each cell.
3. *No interface.* The 3D conversation produced files whose grids, units, nodata, extents and names differed from
   one run to the next, and every consumer re-guessed them. Here every grid, unit, nodata, name and field is fixed
   (sections 2 and 4) and the cloud session's reader is written to them (section 6).
4. *Work that lived on one machine or in one chat.* Anything not in git was gone when the workspace was reclaimed.
   Here nothing is done until it is pushed (section 7), raw inputs are listed with checksums (section 3), and the
   rebuild runs from one command with paths in one file (section 5).
5. *Edges solved per tile.* Tiles were blended with tent weights, so seams averaged two different registrations
   instead of agreeing. Here the sheets are registered jointly with seam constraints and every seam residual is
   reported (4.2, 4.7).
6. *Targets unstated.* Nobody said what "good enough" was, so nothing failed. Here the targets are numbers (4.7)
   and a miss is reported, not absorbed.
7. *Scope creep into other layers.* The topography work edited the deck, the river beds and the works rasters along
   the way, and the ledger could not say which file was which vintage. Here the local session touches only the paths
   in section 8.

**What "better than before" looks like at the end.** A surface that, where the land has not changed, matches LiDAR
to under a metre, and where it has changed, shows the 1912 ground rather than today's; contours you can open in
QGIS with their sheet and level; a report that says how good each sheet and each seam is; and a rebuild anyone can
run again next year and get the same files.

## 1. What is being produced

The **real 1912 ground**: the surface the 1912 City Topographic Survey drew, as a raster on the LiDAR lattice, with the
contours it came from as vectors, a confidence raster, a cover mask and a fit report. Not the canon 1912 ground: the
canon works of 1903-1912 (the Embankment stretch, the Mill Creek culvert) are added by the compositor from the ledger
(`ground/works_ledger.json`, work `ohio_embankment_1912`). The old surface `ground/1912/canon_1912_ground_dm.vrt`
(LiDAR shape with 1912 texture, method I4) is moved to `ground/1912/legacy_I4/` and kept until the new one passes.

## 2. Where everything goes (all in git, on branch `hub_region`)

```
ground/1912/
  SPEC.md                          this file
  STATUS.json                      the handshake (section 7)
  MANIFEST.csv                     every raw input on Ben's machine: path, bytes, sha256, what it is (section 3)
  sheets_index.json                every sheet (section 4.1)
  georef/<sheet_id>.json           control points and the fitted transform per sheet (4.2)
  contours/<sheet_id>.geojson      the vectorised contours, spot heights and breaklines per sheet (4.3)
  surface/real_1912_ground_dm.vrt  the surface, joining the tiles below (4.4)
  surface/real_1912_ground_dm_r<R>c<C>.tif
  surface/real_1912_confidence.tif (4.5)
  surface/real_1912_cover.tif      (4.6)
  report/fit_report.json           (4.7)
  report/*.png                     previews: hillshade, residual maps, seams
  rebuild/rebuild.py               one command from the raw inputs to everything above (section 5)
  rebuild/*.py                     its helpers (the I4 label propagation and solver, reused and cleaned)
  legacy_I4/                       the old canon_1912_* files and survey_cover_1912.tif, moved here unchanged
configs/ground_paths.json          local paths (section 5); the only file with a machine-specific path in it
```

File-size limit: no file in git over 25 MiB (GitHub web upload limit; keeps clones small). Split rasters into tiles
and contours per sheet. Nothing the cloud session needs may live only on Ben's machine.

## 3. Raw inputs (stay on Ben's machine, listed in MANIFEST.csv)

| Input | Where (Ben's machine) | Used for |
|---|---|---|
| The 1912 City Topographic Survey sheets | `..\Historic_Topo\1912_City_Topographic_Survey\` | the contours |
| `picks12` control points and the existing 1912 transforms | `..\Maps\Topography_Export\` or `..\Maps\Basin_Street_Map\` | the starting registration |
| Today's LiDAR, 2 m | `..\Historic_Topo\` (the `dem2m` files) | registration, datum fit, checks only |
| The 1914 USGS 1:62,500 sheets (West and East Cincinnati) | `..\Historic_Topo\` | the Kentucky check and fill where the city survey stops |
| The per-tile I4 files, if they exist | `..\Maps\Topography_Export\topo_1912\` | a shortcut for the contour vectorisation |

`MANIFEST.csv` columns: `path,bytes,sha256,kind,note`. `kind` is one of `sheet`, `picks`, `transform`, `lidar`,
`usgs1914`, `i4_tile`. The cloud session uses it to know exactly what the surface was built from.

## 4. Formats

### 4.1 `sheets_index.json`

```json
{"crs": "EPSG:26916", "contour_interval_ft": 5, "datum_note": "1912 city datum; fitted offset to NAVD88 in report/fit_report.json",
 "sheets": [{"id": "s001", "file": "<file name in the raw folder>", "sha256": "...", "px_w": 0, "px_h": 0,
             "bounds_26916": [x0, y0, x1, y1], "georef": "fitted|failed", "contours": "done|none|partial", "note": ""}]}
```

`id` is `s` plus three digits in the raw folder's sorted order, and is the key everywhere else.

### 4.2 `georef/<sheet_id>.json`

```json
{"sheet": "s001", "model": "affine|tps", "controls": [{"px": [x, y], "xy": [E, N], "name": "street A / street B", "source": "picks12|new", "residual_m": 0.0}],
 "forward": {...the model's parameters, enough to recompute px -> EPSG:26916...}, "rms_m": 0.0, "seam_rms_m": {"s002": 0.0}}
```

Control points are unchanged street intersections (as the Sanborn plates were fitted); every control carries its
residual after the joint solve, and `seam_rms_m` is the disagreement with each neighbouring sheet along the shared edge.

### 4.3 `contours/<sheet_id>.geojson`

A FeatureCollection in EPSG:26916 (state `"crs": "EPSG:26916"` at the top level; coordinates in metres, 2 decimals).
Every feature is a `LineString` (contours, streams, walls) or a `Point` (spot heights) with properties:

| property | type | meaning |
|---|---|---|
| `sheet` | string | the sheet id |
| `kind` | string | `contour`, `index`, `spot`, `stream`, `wall`, `edge` |
| `level_ft` | number or null | the printed level in the sheet's datum (feet); null for streams, walls, edges |
| `level_m` | number or null | NAVD88 metres after the datum fit |
| `confidence` | number 0 to 1 | label certainty times line quality |
| `label_source` | string | `printed`, `propagated`, `index_lidar`, `manual` |
| `length_m` | number | for lines |

No feature without `kind`; no contour without `level_ft`. Contours are not simplified below 1 m.

### 4.4 The surface

- Grid: EPSG:26916, 2 m cells, on the LiDAR lattice (cell edges on even metres). Extent: the union of the sheet
  footprints, snapped outward to 2 m. Tiles of at most 8,000 x 8,000 cells, named `_r<R>c<C>` from the north-west,
  joined by `real_1912_ground_dm.vrt` with relative `SourceFilename`s.
- Values: int16 decimetres NAVD88, nodata -32768, GeoTIFF, deflate, predictor 2, tiled 512 x 512. Nodata wherever
  the sheets are blank or illegible, or outside the survey. Never LiDAR filled in.
- The surface passes through the contours and breaklines (thin plate or TIN); between them it is smooth; it is not
  blended with LiDAR anywhere.

### 4.5 `real_1912_confidence.tif`

Same grid, uint8 0 to 100, nodata 255: contour density, label certainty and distance to a seam combined; the report
says the formula.

### 4.6 `real_1912_cover.tif`

Same grid, uint8: 1 where a sheet covers the ground and contours were read, 0 elsewhere.

### 4.7 `report/fit_report.json`

```json
{"built": "ISO time", "commit": "git sha", "datum_offset_m": {"value": 0.0, "fitted_on": "N hilltop points", "rms_m": 0.0},
 "sheets": {"s001": {"controls": 0, "rms_m": 0.0, "contours": 0, "labelled_share": 0.0}},
 "seams": [{"a": "s001", "b": "s002", "rms_m": 0.0, "max_m": 0.0}],
 "lidar_check": {"unchanged_points": 0, "rms_m": 0.0, "p95_abs_m": 0.0, "how_chosen": "..."},
 "usgs1914_check": {"rms_m": 0.0, "points": 0},
 "coverage_km2": 0.0, "nodata_km2": 0.0}
```

Targets: `lidar_check.rms_m` under 1.0; every seam `rms_m` under 0.5; `labelled_share` over 0.9 per sheet. A target
missed is reported, not hidden.

## 5. The rebuild

`python ground/1912/rebuild/rebuild.py --paths configs/ground_paths.json --out ground/1912` makes everything in
section 2 from the raw inputs, deterministically (fixed random seeds, pinned versions in `rebuild/requirements.txt`).
`configs/ground_paths.json`:

```json
{"sheets": "C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/Historic_Topo/1912_City_Topographic_Survey",
 "picks12": "...", "lidar_2m": "...", "usgs1914": "...", "i4_tiles": "... or null"}
```

A second profile may be added for another machine; the script takes the file, never a hard-coded path.

## 6. How the cloud session uses it

- `region/ground/layers.py` `CANON_1912` becomes `REAL_1912 = GROUND / "1912/surface/real_1912_ground_dm.vrt"` and
  `SURVEY_COVER` the new cover; the compositor's base is the real 1912 surface for both timelines, and the canon
  timeline applies `ohio_embankment_1912` from the ledger (it already does). The `real_1912` delta step is removed.
- `tests/test_ground.py` is updated by the cloud session to the new base; `python -m region.ground check` and the
  change catalogue are rerun and committed under `ground/reports/`.
- Contours become `earthwork`-adjacent records later (the model's `ground_layer` table) with the sheet ids as sources.

## 7. The handshake: `STATUS.json`

```json
{"stage": "registration|contours|surface|checks|done|blocked", "commit": "git sha of the last push", "updated": "ISO time",
 "done": false, "blocked_on": null, "notes": "one line per step with its numbers"}
```

The local session updates it and pushes after every stage. The cloud session acts only when `"done": true` and the
report's targets are met or explained. Nothing is "done" that is only on Ben's machine.

## 8. Rules for the local session

- Branch `hub_region`; commit after each stage; push after each commit.
- Touch only `ground/1912/`, `configs/ground_paths.json`, `ground/README.md` (a paragraph pointing here) and
  `tests/test_ground.py` if a test needs the new file names. Nothing else.
- Don't change canon, the ledger, the zones, or any other layer.
- Reuse the I4 pipeline's label propagation and per-tile solver (`ground/scripts/topo_bathy_scripts_01.zip`,
  `topo/pilot_label2.py`, `pilot_surface2.py`) where they work; replace `tile_mosaic.py`'s LiDAR blend.
- Report in plain language with the numbers from `fit_report.json`; list every target missed.
