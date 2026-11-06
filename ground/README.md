# Canon ground, 1912 onward (`ground/`)

The canon topography from the Cincinnati Topography chat (relief maps, October 2026), packed for the repo. It gives the code the ground as it stood in 1912, plus each canon work after 1912 as its own layer, so ground for any year can be composed.

Packed 5 November 2026 from `_Cincinnati Rail\Historic_Topo` on Ben's computer, uploaded to the branch `claude/happy-planck-62a8x0` and consolidated here on 6 November (`ground/` is the home of every ground layer; the 2026 canon ground, map 3, moved here to `2026/` on 6 November with every reader repointed). Three files (`1912/canon_1912_ground_dm_n.tif`, `_s.tif`, `previews/canon_1912_preview.jpg`) were re-saved between packing and upload and differ from the packed copies by about 6 KB each; they open and read correctly (grid, cover 73.9 %, levels 134.3-296.2 m) and `MANIFEST.csv` carries the in-repo checksums with the packed ones noted. Every file is under 25 MiB, so the folder can be uploaded through GitHub's web page. `MANIFEST.csv` lists every file with its size, SHA-256 and the original it came from.

## What is here

| Path | What it is |
|---|---|
| `1912/canon_1912_ground_dm.vrt` (+ `_n.tif`, `_s.tif`) | **Canon 1912 ground (map 2).** The real 1912 ground with the canon works finished by 1912: the Ohio Embankment from the Mill Creek mouth to Sawyer Point and the lower Mill Creek culvert. Open the `.vrt`; it joins the two tiles |
| `1912/survey_cover_1912.tif` | 1 where the 1912 City Topographic Survey covers the ground (270 sq km). Outside it the "1912" ground is today's LiDAR with buildings and streets cleaned out, not 1912 |
| `works/riverworks_1912_*` | The 1912 riverworks as target, mode and delta. Subtract the delta from the canon 1912 ground to get the real 1912 ground (map 1) |
| `works/riverworks_2026_*` | The rest of the Ohio Embankment, the Mill Creek deck, the Lunken levees and the airfield lift, as one combined layer |
| `works/ky_terraces_*` | Kentucky terraces and walls (Covington, Newport, Bellevue-Dayton, Ludlow-Bromley, Licking) |
| `works/canon_interstates_*` | Canon interstate earthworks (delta against today's LiDAR), their 10 m profiles and their structures |
| `works/ohio_bed_*` | The canon Ohio and Licking bed, and the real 2022 bed |
| `works/real_works_removed_*` | Real works canon does not have, taken out of today's LiDAR |
| `works/*params.json`, `works/embankment_wall_line.geojson` | Every number the riverworks used, and the wall line |
| `zones/` | Change zones: every post-1912 work (`zones_post1912_works`), the real works canon removes, and the per-OSM-way classes |
| `works_ledger.json` | Each work with its years, layer and source. Missing years are `null` |
| `make_ground_1912.py` | Rebuilds the canon (and real) 1912 ground from the `Historic_Topo` originals |
| `previews/` | An 8 m preview of the canon 1912 ground with the survey edge, and the map 2 relief render |
| `scripts/topo_bathy_scripts_01.zip` | The relief-map scripts from the Topography workspace, for provenance (they use that workspace's absolute paths) |
| `sources/` | The original READMEs from each `Historic_Topo` folder |

The 2026 canon ground (map 3): `ground/2026/map3_profile_dem_dm.vrt` with its four tiles and the water surface `map3_profile_dem_dm_water.tif`.

## Grid and units

- **Rasters:**
  - EPSG:26916 (NAD83 / UTM 16N), on the LiDAR 2 m lattice.
  - int16 decimetres NAVD88 (divide by 10 for metres), nodata -32768. Mode rasters are uint8.
  - The two bed rasters are 4 m.
- **1912 ground extent:** E 697,252-730,654, N 4,321,822-4,349,224, which is 33.4 x 27.4 km, 16,701 x 13,701 cells. 676.5 of its 915.3 sq km hold values.
- **Riverworks, Kentucky terrace and 1912 riverworks layers:** E 708,836-724,836, N 4,324,190-4,336,400.
- **Interstate, real-works and bed layers:** the full LiDAR extent, E 695,000-735,000, N 4,315,000-4,350,000.
- **Mode values:** 1 forces the target; 2 fills only and never cuts; 0 leaves the ground untouched.
- **Vectors:**
  - `zones/*.geojson` and `works/canon_interstates_structures.geojson` are lon/lat (EPSG:4326).
  - `works/embankment_wall_line.geojson` is a bare LineString in EPSG:26916 metres.

## How the canon 1912 ground was made (checked 5 November 2026)

1. The I4 1912 ground (67 tiles over the 1912 survey; Relief_Maps_Log 10c), with its south extension laid over it (10e.1).
2. The Kentucky 1912 ground wherever it has values: post-1912 works rebuilt from the 1914 USGS sheets (10e).
3. The 1912 riverworks: mode 1 sets the target; mode 2 raises the ground to the target and never cuts (10d.10).

Checks on the result:

- Canon minus real equals the stored 1912 riverworks delta on all 225,133 riverworks cells (0.90 sq km), with no difference anywhere else.
- No Kentucky cell overlaps a riverworks cell.
- The `.vrt` reads back identical to the composed array.

## Composing ground for a year (for the hub)

- **Rule:** ground(Y) is the canon 1912 ground, except inside the footprint of each work built by Y. There it takes the 2026 canon ground (`data/profile/dem/map3_profile_dem_dm.vrt`), feathered over about 10-30 m at the footprint edge.
- **Footprints:**
  - mode greater than 0 for the target/mode layers;
  - non-zero cells for the delta layers;
  - the polygons for the zones.
- **Years:** from `works_ledger.json`.
- **Line works:** each line's own cuts, fills and portals come from the hub model by phase, not from these rasters.

## Code: `region/ground` (6 November 2026)

The compositor that turns these layers into the ground for any year, and the parametric works that will replace
hand-made rasters from here on.

```
python -m region.ground works --year 1930                       # which works count in 1930, which are skipped and why
python -m region.ground compose --year 1930 --bbox 711000 4330000 714000 4332500 --out out/ground_1930.tif
python -m region.ground check --out ground/reports/check_2026_vs_map3.json   # compose 2026 and compare with map 3
python -m pytest tests/test_ground.py
```

```python
from region.ground import compose, sample, Pad, Corridor
g = compose(1930, bbox=(x0, y0, x1, y1))          # g.z metres NAVD88, g.src the layer per cell, g.applied, g.skipped
z = sample(1930, [(x, y), ...])                    # bilinear, metres
pad = Pad("quay", polygon, level=151.8, fill_slope=1/3, cut_slope=0.5)        # an areal work with slopes to daylight
cut = Corridor("line_6_cutting", [(x, y, z), ...], half_width=6.45, cut_slope=1/1.5)   # a linear work
g2 = compose(1930, bbox, extra_works=[pad, cut]); pad.stats["fill_m3"]
```

Rule (`region/ground/compose.py`): the canon 1912 ground is the base (the 2026 canon ground where the 1912 raster does
not reach, labelled `map3_outside_1912`); timeline `real` subtracts the 1912 riverworks delta. Then every work in
`works_ledger.json` whose year (`built_by`, else `built_from`) is at or before the year is applied in ledger order by
the kind set in `region/ground/layers.py`: target and mode rasters as the riverworks were made (mode 1 forces the
target, 2 only raises); the 2026 canon ground inside a delta's footprint (the interstates: the delta was made against
today's LiDAR, which the repo does not hold); the 2026 canon ground inside the kept-works zones, feathered 16 m; a bed
surface where it has values. An undated work counts only at 2026 and is listed as skipped before. New works are
`Pad` and `Corridor` objects: per cell, with Z the design level at the nearest point of the work's edge and d the
distance to it, `proposed = clip(existing, Z - fill_slope * d, Z + cut_slope * d)`, so the daylight line is found,
not drawn, and cut and fill volumes come out of the same pass. Every cell carries the code of the layer that set it.

## Known gaps

- **Embankment dates:** the 7 October plan, citing tracker 2J, says 1925-1930. Ben ruled on 8 October for 1903-1925, with the Mill Creek mouth to Sawyer Point stretch on map 2. The ledger follows the ruling; the tracker needs updating.
- **The river is at today's level.** Both banks sit on today's Markland pool; no 1912 river level has been set.
- **Outside the survey cover,** including most of Kentucky away from the riverworks window, the 1912 ground is cleaned modern LiDAR.
- **The 2026 riverworks layer is combined.** It joins works with different dates (rest of the Embankment, deck, Lunken, airfield lift); splitting it by year needs the parts, which `topo/rw_build.py` in the scripts zip draws separately.
- **Kept real works** (`real_works_kept` in the ledger) have no build years yet.
- **Nothing here covers the outer TRI region** beyond the LiDAR extent.
