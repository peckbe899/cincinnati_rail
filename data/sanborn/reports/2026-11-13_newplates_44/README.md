# Plate 44 (central Northside) onto the applied 1922 layer, 13 November 2026

Two reads per strip (six strips), merged by `tools/sanborn/complete/merge_reads.py`; fit by `tools/sanborn/cufp/fit.py 44` (seeded from street names, no GeoTIFF); placed by `tools/sanborn/joint/newplates.py 22-44 --write`.

| | |
|---|---|
| Picks (both reads within 60 px) | 45 across the strips |
| Not agreed | 25 (strip 2 read B was read coarsely, about 15-20 px) |
| Matched to OSM / controls | 34 |
| Name-seeded fit, leave-one-out | 3.55 m (tps10, rms 2.41 m) |
| Rule 12 spline, held-out | 3.36 m (max 9.45 m, lambda 10) |
| Ties to applied plates | 12 (37L 1, 37R 3, 43 5, 45 3) |

Seams with the new plate (`reports/2026-11-13_seams_newplates_44`): 37L 1 at 1.61 m; 37R 3, median 1.20 m; 43 5, median 0.50 m; 45 3, median 0.83 m.

The script's own "neighbour median not worse" check came out false for 37L (1.26 -> 1.27 m) and 45 (0.56 -> 0.70 m) only because its "after" mixes in the new seams with 44; the gate in force (held-out under 5 m; existing seams compared, new seams reported) passes, and the existing seams were unchanged after the build.
