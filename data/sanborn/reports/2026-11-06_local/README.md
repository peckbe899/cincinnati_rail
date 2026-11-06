# Local fit of plates 33, 34R, 37L, 37R and 38, 2026-11-06

Ben's ruling (6 November): option (c) for these five plates. Their positions are refitted together, the other 16 plates held fixed as tie partners, 37L and 37R treated as one sheet at the gutter. Nothing is applied by this report: the new models sit beside the old ones (`fwd_local.pkl`, `cuf38/fwd38_local.pkl`). Method: `tools/sanborn/joint/local.py` (its docstring).

48 ties (12 of them 37L/37R paper points), 206 gutter pairs matched between the 37L and 37R scans. The gutter gap between the halves (the same paper point on both): median 27.59 m, max 32.17 m before; median 0.14 m, max 1.31 m after.

## Part 3 check

- Every plate's own control rms within 0.3 m of before: **no** (worse: 22-37R)
- Plate-plate seam median across the five falls: **yes** (4.54 to 3.2 m)
- Plate-plate seam 90% across the five falls: **yes** (20.91 to 10.76 m)
- So Part 3 **does not** go ahead (stop after Part 2).

"Across the five": every plate-plate seam a fitted plate takes part in (with another of the five or with a fixed plate). The wrong name matches of the re-read are left out of both before and after.

## Per plate

Controls: the plate's own OSM crossings. Rms: own controls, m. Held-out: leave-one-out rms (before: the plate's fit report). Corner move: largest move of the plate image's four corners.

| Plate | Own model | Correction | Controls | Rms before | Rms after | Change | Held-out before | Held-out after | Max corner move m | Median control move m | Ties |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 22-33 | tps0.3 | affine | 62 | 1.44 | 1.54 | +0.10 | 3.67 | 3.76 | 1.26 | 0.36 | 14 |
| 22-34R | tps0.3 | affine | 49 | 1.44 | 1.57 | +0.13 | 3.91 | 4.04 | 2.89 | 0.51 | 13 |
| 22-37L | tps30 | tps10 | 20 | 2.97 | 2.67 | -0.30 | 4.67 | 5.41 | 25.03 | 1.93 | 12 |
| 22-37R | tps0.3 | affine | 15 | 1.02 | 2.18 | +1.16 **worse** | 5.9 | 7.02 | 5.41 | 1.86 | 16 |
| 22-38 | tps1 | affine | 63 | 2.29 | 2.43 | +0.14 | 4.75 | 4.95 | 2.69 | 0.59 | 12 |

## Why 37R fails, and that it is not the model choice

The per-plate choice converged (a third pass changes nothing). With the other four as chosen, every correction 37R could take misses its 0.3 m limit (own rms before 1.02 m, so at most 1.32 m):

| 37R correction | 37R own rms m | 37R held-out m | 37L own rms m |
|---|---|---|---|
| affine (chosen) | 2.18 | 7.02 | 2.67 |
| tps0.3 | 2.12 | 11.85 | 1.82 |
| tps1 | 2.42 | 10.92 | 1.85 |
| tps3 | 2.69 | 10.02 | 1.89 |
| tps10 | 2.85 | 8.91 | 1.96 |
| tps30 | 2.69 | 8.04 | 2.11 |
| tps100 | 2.44 | 7.46 | 2.32 |

Making the two halves one sheet (the gutter gap goes from 27.6 m to 0.14 m) is what moves 37R off its own controls: the two halves' OSM controls cannot both be met with the halves continuous at the gutter. So at least one half's controls near the gutter are wrong or misread, and that is where to look next (37R has 15 controls, 37L 20). Also note 37L's thin-plate correction moves its far corner 25 m; its controls barely reach that corner.

## Seams

Seam report on the new models (the five on `fwd_local`, the others on their own): `reports/2026-11-06_seams_local/`.

| Plate-plate seams | | Shared | Median m | 90% m | Max m | > 10 m | > 20 m |
|---|---|---|---|---|---|---|---|
| touching the five | before | 48 | 4.54 | 20.91 | 27.44 | 11 | 6 |
| touching the five | after | 48 | 3.2 | 10.76 | 25.17 | 6 | 1 |
| among the five | before | 19 | 7.47 | 23.74 | 27.44 | 9 | 6 |
| among the five | after | 19 | 1.36 | 18.11 | 25.17 | 4 | 1 |
| all plates | before | 143 | 2.78 | 11.12 | 30.01 | 16 | 7 |
| all plates | after | 143 | 2.6 | 8.78 | 30.01 | 11 | 2 |
| plate-1904, the five | before | 304 | 0.23 | 4.34 | 35.09 | 15 | 7 |
| plate-1904, the five | after | 304 | 1.31 | 6.01 | 35.01 | 13 | 4 |

The 1904 frames have not moved (their bend is Part 3), so the plate-1904 seams of the five open where the plates move.

## Ties, widest after the fit

| Plates | Crossing | Before m | After m | Weight |
|---|---|---|---|---|
| 22-33 / 22-34R | Marshall Avenue & Garrard Avenue | 25.58 | 25.17 | 0.238 |
| 22-37R / 22-38 | Ludlow Avenue & Lafayette Avenue | 19.81 | 18.81 | 0.319 |
| 22-34R / 22-38 | Vermont Avenue & Stock Avenue | 21.84 | 17.94 | 0.334 |
| 22-34R / 22-38 | Vermont Avenue & Bates Alley | 20.54 | 16.54 | 0.363 |
| 22-35N / 22-38 | West McMicken Avenue & Dixmyth Avenue | 14.52 | 12.33 | 0.487 |
| 22-31 / 22-33 | Queen City Avenue & Garrard Avenue | 10.0 | 10.09 | 0.595 |
| 22-33 / 22-34L | Casper Street & Baltimore Avenue | 10.02 | 9.05 | 0.663 |
| 22-38 / 22-68 | Ruther Avenue & Vine Street | 8.27 | 9.04 | 0.664 |
| 22-33 / 22-34L | Seegar Avenue & Carll Street | 8.35 | 8.8 | 0.682 |
| 22-34R / 22-37R | Spring Grove Avenue & Sassafras Street | 11.39 | 8.46 | 0.709 |
| 22-37L / 22-37R | Spaeth Street & Dreman Avenue | 11.9 | 7.72 | 25.0 (sheet) |
| 22-33 / 22-34L | Casper Street & Pulte Street | 8.44 | 7.24 | 0.829 |
| 22-38 / 22-68 | Glenmary Avenue & Vine Street | 6.82 | 6.18 | 0.972 |
| 22-33 / 22-34L | Casper Street & Carll Street | 6.8 | 5.9 | 1.0 |
| 22-16R / 22-34R | Colerain Avenue & Marshall Avenue | 5.76 | 5.62 | 1.0 |

Choice trail: [{'pass_': 1, 'plate': '22-37L', 'frm': 'affine', 'to': 'tps10', 'heldout': 5.406}]. Computed with numpy 2.4.2, scipy 1.18.1.
