# Plate 40 refitted with Ben's first-pass GeoTIFF as a guide (9 November 2026)

Plate 40 failed the 5 m held-out gate in `reports/2026-11-09_newplates_39_40` (6.23 m). Ben supplied a first-pass
GeoTIFF (`40 first pass.tif`, EPSG:32616). It sits a median 7.2 m from OSM at the controls, so it is a seed and a check
on names, not a model.

What it showed: two 1922 street names on this plate are other streets in OSM today.

| 1922 name on the plate | OSM name | Evidence |
|---|---|---|
| Carthage Avenue | Vine Street | 9 crossings land 1 to 14 m from Vine Street crossings |
| Canal Street | Baker Place | crossings land 10 to 14 m from Baker Place crossings |

Both are per-plate aliases in `cufp/config.json` (plate 40, `alias`), read by `tools/sanborn/cufp/fit.py`. They are
for Ben to confirm. Donnell, Ammen and Ludlow looked similar but less certain and are not aliased.

| | Before | After |
|---|---|---|
| Controls | 29 | 39 |
| Name-seeded fit, leave-one-out | 6.23 m | 4.58 m (tps3, rms 2.39 m) |
| Rule 12 spline, held-out | over 5 m | 4.52 m (max 11.42 m, lambda 3) |

Dropped by the fit's tests: Spring Grove/Platt, Martin/Leo, Wuest/Kessler, Keenan/Station.

Tie to plate 39 (applied, held fixed): Mitchell Avenue & Kessler Avenue, 2.54 m before, 1.53 m after. Plate 39's seam
median with its neighbours is 3.25 m without plate 40 and 2.68 m with it. No applied plate's model changed, so the
existing seams are unchanged. Seam report: `reports/2026-11-09_seams_newplates_40`.

Gate: held-out under 5 m, yes; existing seams not worse, yes. `cufp/40/fwd_complete.pkl` is written. Plate 40 is not
built onto the page yet.

`fit.py` also now reads the GeoTIFF's own CRS (`tif_crs`) instead of assuming EPSG:3857.
