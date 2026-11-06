# Canon ground, 1912 onward (`data/ground`)

The canon topography from the Cincinnati Topography chat (relief maps, October 2026), packed for the repo. It gives the code the ground as it stood in 1912, plus each canon work after 1912 as its own layer, so ground for any year can be composed.

Packed 5 November 2026 from `_Cincinnati Rail\Historic_Topo` on Ben's computer. Every file is under 25 MiB, so the folder can be uploaded through GitHub's web page. `MANIFEST.csv` lists every file with its size, SHA-256 and the original it came from.

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

The 2026 canon ground (map 3) is already in the repo: `data/profile/dem/map3_profile_dem_dm.vrt`.

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

## Known gaps

- **Embankment dates:** the 7 October plan, citing tracker 2J, says 1925-1930. Ben ruled on 8 October for 1903-1925, with the Mill Creek mouth to Sawyer Point stretch on map 2. The ledger follows the ruling; the tracker needs updating.
- **The river is at today's level.** Both banks sit on today's Markland pool; no 1912 river level has been set.
- **Outside the survey cover,** including most of Kentucky away from the riverworks window, the 1912 ground is cleaned modern LiDAR.
- **The 2026 riverworks layer is combined.** It joins works with different dates (rest of the Embankment, deck, Lunken, airfield lift); splitting it by year needs the parts, which `topo/rw_build.py` in the scripts zip draws separately.
- **Kept real works** (`real_works_kept` in the ledger) have no build years yet.
- **Nothing here covers the outer TRI region** beyond the LiDAR extent.
