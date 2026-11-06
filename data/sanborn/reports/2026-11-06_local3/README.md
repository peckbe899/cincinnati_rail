# Local fit with a page-curl option, 2026-11-06

Ben's ruling (6 November): the plates are bound-book scans, so the distortion near a spine is page curl. A page-curl correction (`tools/sanborn/joint/curl.py`) is offered beside affine and thin plate; the five plates (33, 34R, 37L, 37R, 38) are fitted together, the other 16 fixed, with the 37L/37R gutter pairs as ties at weight 3. Method: `tools/sanborn/joint/local3.py` (its docstring). Nothing is applied by this report: the new models sit beside the old ones (`fwd_local3.pkl`, `cuf38/fwd38_local3.pkl`).

48 ties, 206 gutter pairs (weight 3). Gutter gap (the same paper point on both halves): median 27.59 m, max 32.17 m before; median 0.17 m, 90% 0.52 m, max 1.46 m after.

## Part 3 check

- 33, 34R, 38 own control rms within 0.3 m of before, 37L and 37R within 0.5 m: **no** (over: 22-37R)
- Gutter gap median under 2 m: **yes** (0.17 m)
- Plate-plate seam median across the five falls: **yes** (4.54 to 3.08 m)
- Plate-plate seam 90% across the five falls: **yes** (20.93 to 10.79 m)
- So Part 3 **does not** go ahead (stop after Part 2).

"Before" is each plate's own model on the same controls (the round-3 re-read pixel positions). Seams before: `reports/2026-11-06_seams_reread3` (own models, re-read picks, wrong matches dropped); after: `reports/2026-11-06_seams_local3`.

## Gutter edges

| Plate | Gutter edge | From | Fold line (px) |
|---|---|---|---|
| 22-33 | bottom | page position not in docs/sanborn: the edge with the worst held-out rms of its controls (4.32 m, 19 controls within 2000 px) | image edge |
| 22-34R | left | page position: a right half, spine on its left edge (INSTRUCTIONS22.md) | x = 209 -0.0141 y |
| 22-37L | right | page position: a left half, spine on its right edge (INSTRUCTIONS22.md) | x = 5841 +0.0082 y |
| 22-37R | left | page position: a right half, spine on its left edge (INSTRUCTIONS22.md) | x = 166 +0.0020 y |
| 22-38 | right | page position not in docs/sanborn: the edge with the worst held-out rms of its controls (8.05 m, 12 controls within 2000 px) | image edge |

All 21 plates: `data/sanborn/joint/curl_sides.json`.

## Per plate

Rms: own controls, m. Held-out: leave-one-out rms (before: the plate's fit report). Curl s(0): the curl's shift at the gutter, px and m.

| Plate | Own model | Correction | Curl s(0) | Curl k | Controls | Rms before | Rms after | Change | Limit | Held-out before | Held-out after | Max corner move m | Median control move m | Ties |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 22-33 | tps0.3 | affine |  |  | 62 | 1.44 | 1.54 | +0.10 | 0.3 | 3.67 | 3.77 | 1.26 | 0.36 | 14 |
| 22-34R | tps0.3 | affine |  |  | 49 | 1.44 | 1.57 | +0.13 | 0.3 | 3.91 | 4.04 | 2.97 | 0.51 | 13 |
| 22-37L | tps30 | tps3 |  |  | 20 | 2.95 | 1.46 | -1.49 | 0.5 | 4.67 | 4.36 | 29.12 | 1.76 | 12 |
| 22-37R | tps0.3 | curl | -229.4 px (-43.71 m) | -0.016 | 15 | 1.03 | 1.62 | +0.59 **over** | 0.5 | 5.9 | 5.44 | 20.81 | 1.11 | 16 |
| 22-38 | tps1 | affine |  |  | 63 | 2.29 | 2.43 | +0.14 | 0.3 | 4.75 | 4.95 | 2.66 | 0.58 | 12 |

Curl shape of the plates that took it (s at the knots, px; m per px across the gutter):

- 22-37R: s = {0: -229.4, 200: -205.6, 500: -176.6, 1000: -155.9, 2000: -110.5}, 0.1906 m/px, k = -0.016

The plates that did not take curl, with curl forced (the others as chosen):

| Plate | Held-out with curl | Own rms with curl | Gutter gap median | s(0) px |
|---|---|---|---|---|
| 22-33 | 3.83 | 1.6 | 0.17 | 32.8 |
| 22-34R | 4.06 | 1.58 | 0.17 | -4.7 |
| 22-37L | 5.98 | 5.01 | 0.68 | 154.5 |
| 22-38 | 5.05 | 2.4 | 0.17 | -130.7 |

## The controls of the plates over their limit

| Plate | Crossing | Pixel | Before m | After m | Moved m |
|---|---|---|---|---|---|
| 22-37R | Comfort Street & Sassafras Street | (3288, 7169) | 0.65 | 3.37 | 2.78 |
| 22-37R | Colerain Avenue & Arlington Street | (2824, 6764) | 0.89 | 2.97 | 2.09 |
| 22-37R | Spring Grove Avenue & Burgoyne Street | (1231, 665) | 1.51 | 2.24 | 0.78 |
| 22-37R | Spring Grove Avenue & Arlington Street | (1420, 6731) | 0.22 | 1.72 | 1.54 |
| 22-37R | Ludlow Avenue & Bowdle Place | (4189, 3070) | 0.4 | 1.6 | 1.98 |
| 22-37R | Cherry Street & Powers Street | (319, 336) | 0.94 | 1.58 | 1.14 |
| 22-37R | Turrill Street & Powers Street | (667, 316) | 2.08 | 1.38 | 0.97 |
| 22-37R | Colerain Avenue & Sassafras Street | (2835, 7164) | 1.28 | 1.15 | 2.21 |
| 22-37R | Spring Grove Avenue & Brashears Street | (1274, 5336) | 0.34 | 1.04 | 0.71 |
| 22-37R | Cherry Street & Burgoyne Street | (321, 642) | 1.76 | 0.99 | 0.85 |
| 22-37R | Apple Street & Powers Street | (1047, 313) | 0.64 | 0.87 | 1.51 |
| 22-37R | Spring Grove Avenue & Adelaide Street | (1404, 5923) | 0.7 | 0.51 | 1.11 |
| 22-37R | Bless Avenue & Streng Street | (2776, 2968) | 0.62 | 0.19 | 0.47 |
| 22-37R | Spring Grove Avenue & Powers Street | (1317, 313) | 0.59 | 0.15 | 0.71 |
| 22-37R | Spring Grove Avenue & Ralston Avenue | (787, 3314) | 0.69 | 0.14 | 0.73 |

## Seams

| Plate-plate seams | | Shared | Median m | 90% m | Max m | > 10 m | > 20 m |
|---|---|---|---|---|---|---|---|
| touching the five | before | 48 | 4.54 | 20.93 | 25.69 | 11 | 6 |
| touching the five | after | 48 | 3.08 | 10.79 | 24.65 | 6 | 1 |
| among the five | before | 19 | 7.47 | 25.21 | 25.69 | 9 | 6 |
| among the five | after | 19 | 1.27 | 15.69 | 24.65 | 4 | 1 |
| all plates | before | 142 | 2.75 | 10.02 | 30.01 | 15 | 7 |
| all plates | after | 142 | 2.6 | 8.79 | 30.01 | 10 | 2 |
| plate-1904, the five | before | 304 | 0.24 | 4.34 | 35.09 | 15 | 6 |
| plate-1904, the five | after | 304 | 1.29 | 5.68 | 35.01 | 14 | 4 |

## Ties, widest after the fit

| Plates | Crossing | Before m | After m | Weight |
|---|---|---|---|---|
| 22-33 / 22-34R | Marshall Avenue & Garrard Avenue | 25.15 | 24.65 | 0.243 |
| 22-34R / 22-38 | Vermont Avenue & Bates Alley | 20.77 | 16.78 | 0.358 |
| 22-37R / 22-38 | Ludlow Avenue & Lafayette Avenue | 21.29 | 15.42 | 0.389 |
| 22-34R / 22-38 | Vermont Avenue & Stock Avenue | 17.82 | 13.92 | 0.431 |
| 22-35N / 22-38 | West McMicken Avenue & Dixmyth Avenue | 14.62 | 12.43 | 0.483 |
| 22-31 / 22-33 | Queen City Avenue & Garrard Avenue | 10.0 | 10.09 | 0.595 |
| 22-34R / 22-37R | Spring Grove Avenue & Sassafras Street | 11.4 | 9.87 | 0.608 |
| 22-33 / 22-34L | Casper Street & Baltimore Avenue | 10.02 | 9.05 | 0.663 |
| 22-38 / 22-68 | Ruther Avenue & Vine Street | 8.27 | 9.02 | 0.665 |
| 22-33 / 22-34L | Seegar Avenue & Carll Street | 8.35 | 8.8 | 0.682 |
| 22-37L / 22-37R | Spaeth Street & Dreman Avenue | 11.9 | 8.12 | 3.0 (gutter) |
| 22-33 / 22-34L | Casper Street & Pulte Street | 8.44 | 7.24 | 0.829 |
| 22-38 / 22-68 | Glenmary Avenue & Vine Street | 6.82 | 6.17 | 0.972 |
| 22-33 / 22-34L | Casper Street & Carll Street | 6.8 | 5.9 | 1.0 |
| 22-16R / 22-34R | Colerain Avenue & Marshall Avenue | 5.76 | 5.69 | 1.0 |

## Curl as an option for every plate alone (read-only)

Each of the 21 plates on its own controls only (its fit picks, no ties), the correction chosen among affine, affine + curl and thin plate by held-out error. Gain: held-out of the best choice without curl minus held-out with curl (positive: curl is better). Nothing written but this table (`curl21.csv`).

| Plate | Own model | Own held-out | Controls | Within 500 px of the gutter | Gutter edge | From | Best without curl | Held-out | With curl | Gain m | Would pick | s(0) px | k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 22-34L | tps3 | 4.49 | 16 | 0 | right | page position | affine | 5.27 | 5.51 | -0.24 | affine | 754.1 | -0.9 |
| 22-37L | tps30 | 4.67 | 20 | 4 | right | page position | affine | 5.51 | 5.59 | -0.08 | affine | 72.5 | 0.51 |
| 22-37R | tps0.3 | 5.9 | 15 | 3 | left | page position | affine | 6.11 | 5.19 | +0.92 | **curl** | -1641.8 | -0.127 |
| 22-34R | tps0.3 | 3.91 | 49 | 0 | left | page position | affine | 4.0 | 4.02 | -0.03 | affine | -3.7 | 0.9 |
| 22-16R | tps3 | 6.09 | 15 | 4 | left | page position | affine | 6.71 | 6.56 | +0.15 | **curl** | -125.2 | 0.308 |
| 22-35N | Ben georeference (nothing fitted) | - | 30 | 2 | bottom | worst held-out edge | affine | 3.21 | 3.18 | +0.03 | **curl** | 50.2 | 0.596 |
| 22-38 | tps1 | 4.75 | 63 | 3 | right | worst held-out edge | affine | 4.92 | 4.96 | -0.04 | affine | -56.0 | -0.9 |
| 22-66 | tps3 | 2.98 | 96 | 0 | top | worst held-out edge | affine | 3.05 | 3.1 | -0.05 | affine | 2.5 | -0.9 |
| 22-67 | tps3 | 3.56 | 70 | 7 | top | worst held-out edge | affine | 3.68 | 3.65 | +0.04 | **curl** | 3378.6 | 0.585 |
| 22-68 | tps3 | 3.34 | 68 | 2 | right | worst held-out edge | affine | 3.45 | 3.46 | -0.02 | affine | -85.3 | 0.9 |
| 22-69 | tps0.3 | 4.41 | 43 | 0 | top | worst held-out edge | affine | 4.49 | 4.91 | -0.42 | affine | 29.9 | 0.9 |
| 22-70 | tps3 | 3.76 | 74 | 3 | bottom | worst held-out edge | affine | 3.87 | 3.9 | -0.03 | affine | 6.6 | 0.9 |
| 22-82A | tps1 | 3.78 | 94 | 5 | right | worst held-out edge | affine | 3.85 | 3.85 | -0.01 | affine | -14.7 | 0.9 |
| 22-83A | tps1 | 3.97 | 40 | 6 | bottom | worst held-out edge | affine | 4.14 | 4.21 | -0.06 | affine | 10.8 | 0.176 |
| 22-75 | tps10 | 4.18 | 47 | 5 | right | worst held-out edge | affine | 4.37 | 4.36 | +0.01 | **curl** | 10.2 | 0.9 |
| 22-76 | tps1 | 3.15 | 117 | 3 | right | worst held-out edge | affine | 3.2 | 3.18 | +0.01 | **curl** | -4.2 | -0.9 |
| 22-26A | tps3 | 2.95 | 49 | 4 | left | worst held-out edge | affine | 3.08 | 3.1 | -0.02 | affine | 48.3 | 0.9 |
| 22-26B | tps0.3 | 3.5 | 11 | 4 | right | worst held-out edge | affine | 3.62 | 3.65 | -0.03 | affine | -13.4 | 0.079 |
| 22-29 | tps0.3 | 2.78 | 72 | 13 | bottom | worst held-out edge | affine | 2.82 | 2.85 | -0.02 | affine | 2031.4 | 0.9 |
| 22-31 | tps1 | 4.0 | 31 | 1 | bottom | worst held-out edge | affine | 4.18 | 4.2 | -0.03 | affine | -34.5 | 0.9 |
| 22-33 | tps0.3 | 3.67 | 62 | 4 | bottom | worst held-out edge | affine | 3.74 | 3.79 | -0.04 | affine | 1.8 | 0.9 |

Read the s(0) column with the "within 500 px" one: the value of the spline at the gutter is set only by the controls close to it, so where few or none lie there it can take sizes no page curls by (22-34L 754.1 px, 22-37R -1641.8 px, 22-67 3378.6 px, 22-29 2031.4 px). A held-out gain from such a curl rests on a handful of controls near the edge.

Would pick curl: 22-37R, 22-16R, 22-35N, 22-67, 22-75, 22-76 (held-out gain 0.92, 0.15, 0.03, 0.04, 0.01, 0.01 m).

Choice trail (the five): [{'pass_': 1, 'plate': '22-37L', 'frm': 'affine', 'to': 'tps3', 'heldout': 4.785}, {'pass_': 1, 'plate': '22-37R', 'frm': 'affine', 'to': 'curl', 'heldout': 5.44}]. Computed with numpy 2.4.2, scipy 1.18.1.
