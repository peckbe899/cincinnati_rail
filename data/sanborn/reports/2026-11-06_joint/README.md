# Joint refit of the 1922 plates, 2026-11-06

Ben's ruling (6 November): one joint refit of the 1922 plates' positions; imagery tiles and plate footprints may move, streets, blocks, plots and the 1904 bend do not. This is the solve and its numbers. Nothing is applied: the new models sit beside the old ones (`fwd_joint.pkl`, `cuf38/fwd38_joint.pkl`, `cuf/joint35N.pkl`); the page, its tiles and every other file are as they were. Method: `tools/sanborn/joint/solve.py` (its docstring).

21 plates, 1082 own controls, 146 ties (crossings two plates share, from the seam report). Corrections chosen: affine for every plate (the quadratic lowered no plate's held-out error).

## Part 3 check

- Every plate's own control rms no worse by more than 0.3 m: **no** (worse: 22-34L, 22-37L, 22-37R, 22-69)
- Plate-plate seam median falls: **yes** (2.88 to 2.45 m)
- Plate-plate seam 90% falls: **yes** (12.75 to 11.79 m)
- So the 1922 imagery is **not** redrawn (stop after Part 2).

## Per plate

Controls: the plate's own OSM crossings (unchanged in number). Rms: own controls, metres. Held-out: leave-one-out rms (before: the plate's own fit report; 35N, nothing fitted, its rms). Corner move: largest move of the plate image's four corners.

| Plate | Own model | Correction | Controls | Rms before | Rms after | Change | Held-out before | Held-out after | Max corner move m | Median control move m | Ties |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 22-34L | tps3 | affine | 16 | 2.65 | 3.11 | +0.46 **worse** | 4.49 | 5.3 | 6.02 | 1.22 | 7 |
| 22-37L | tps30 | affine | 20 | 2.97 | 3.42 | +0.45 **worse** | 4.67 | 5.24 | 6.93 | 1.41 | 12 |
| 22-37R | tps0.3 | affine | 15 | 1.02 | 1.96 | +0.94 **worse** | 5.9 | 6.5 | 4.68 | 1.43 | 16 |
| 22-34R | tps0.3 | affine | 49 | 1.44 | 1.56 | +0.12 | 3.91 | 4.04 | 2.7 | 0.49 | 13 |
| 22-16R | tps3 | affine | 15 | 2.23 | 2.26 | +0.03 | 6.09 | 6.53 | 1.11 | 0.25 | 5 |
| 22-35N | Ben georeference (nothing fitted) | affine | 30 | 3.07 | 2.92 | -0.15 | 3.07 | 3.12 | 3.29 | 0.87 | 12 |
| 22-38 | tps1 | affine | 63 | 2.29 | 2.44 | +0.15 | 4.75 | 4.96 | 2.8 | 0.57 | 12 |
| 22-66 | tps3 | affine | 96 | 1.79 | 1.85 | +0.06 | 2.98 | 3.09 | 1.42 | 0.32 | 19 |
| 22-67 | tps3 | affine | 70 | 2.35 | 2.36 | +0.01 | 3.56 | 3.67 | 0.45 | 0.2 | 14 |
| 22-68 | tps3 | affine | 68 | 2.14 | 2.17 | +0.03 | 3.34 | 3.43 | 0.87 | 0.33 | 17 |
| 22-69 | tps0.3 | affine | 43 | 1.13 | 1.74 | +0.61 **worse** | 4.41 | 4.73 | 3.91 | 0.98 | 19 |
| 22-70 | tps3 | affine | 74 | 2.03 | 2.04 | +0.01 | 3.76 | 3.86 | 0.39 | 0.17 | 14 |
| 22-82A | tps1 | affine | 94 | 2.16 | 2.17 | +0.01 | 3.78 | 3.83 | 0.36 | 0.13 | 21 |
| 22-83A | tps1 | affine | 40 | 1.95 | 1.96 | +0.01 | 3.97 | 4.1 | 0.52 | 0.22 | 9 |
| 22-75 | tps10 | affine | 47 | 3.07 | 3.11 | +0.04 | 4.18 | 4.36 | 1.27 | 0.44 | 17 |
| 22-76 | tps1 | affine | 117 | 1.81 | 1.82 | +0.01 | 3.15 | 3.19 | 0.3 | 0.15 | 17 |
| 22-26A | tps3 | affine | 49 | 1.84 | 1.85 | +0.01 | 2.95 | 3.06 | 0.37 | 0.12 | 13 |
| 22-26B | tps0.3 | affine | 11 | 0.34 | 0.34 | +0.00 | 3.5 | 3.62 | 0.01 | 0.0 | 0 |
| 22-29 | tps0.3 | affine | 72 | 1.02 | 1.06 | +0.04 | 2.78 | 2.84 | 1.09 | 0.19 | 24 |
| 22-31 | tps1 | affine | 31 | 1.78 | 1.85 | +0.07 | 4.0 | 4.16 | 1.33 | 0.48 | 17 |
| 22-33 | tps0.3 | affine | 62 | 1.44 | 1.51 | +0.07 | 3.67 | 3.75 | 1.26 | 0.31 | 14 |

## Seams

Seam report rerun on the new models: `reports/2026-11-06_seams_joint/` (same matching as `reports/2026-11-06_seams/`).

| Seam | | Shared | Median m | 90% m | Max m | > 10 m | > 20 m |
|---|---|---|---|---|---|---|---|
| plate-plate | before | 146 | 2.88 | 12.75 | 30.01 | 19 | 9 |
| plate-plate | after | 146 | 2.45 | 11.79 | 28.79 | 17 | 5 |
| plate-1904 | before | 556 | 0.4 | 7.75 | 35.09 | 51 | 25 |
| plate-1904 | after | 556 | 1.25 | 7.62 | 34.73 | 52 | 22 |

The 1904 frames did not move, so plate-1904 seams change only by the plates' moves; the bent frames were bent onto the old plate positions.

## Ties, widest after the solve

| Plates | Crossing | Before m | After m | Huber weight |
|---|---|---|---|---|
| 22-67 / 22-69 | Gilbert Avenue & Woodburn Avenue | 30.01 | 28.79 | 0.208 |
| 22-68 / 22-69 | Ridgeway Avenue & Reading Road | 29.87 | 27.13 | 0.221 |
| 22-33 / 22-34R | Marshall Avenue & Garrard Avenue | 25.58 | 25.05 | 0.24 |
| 22-66 / 22-69 | Ridgeway Avenue & Reading Road | 27.77 | 24.66 | 0.243 |
| 22-37L / 22-37R | Groub Street & Ralston Avenue | 27.44 | 23.33 | 0.257 |
| 22-37L / 22-37R | Geringer Street & Ralston Avenue | 23.28 | 19.21 | 0.312 |
| 22-34R / 22-38 | Vermont Avenue & Stock Avenue | 21.84 | 17.91 | 0.335 |
| 22-37L / 22-37R | Geringer Street & Groub Street | 21.78 | 17.79 | 0.337 |
| 22-34R / 22-38 | Vermont Avenue & Bates Alley | 20.54 | 16.5 | 0.364 |
| 22-37R / 22-38 | Ludlow Avenue & Lafayette Avenue | 19.81 | 15.5 | 0.387 |
| 22-66 / 22-69 | Wehrman Street & Gilbert Avenue | 13.39 | 15.09 | 0.398 |
| 22-70 / 22-75 | Montgomery Road & Clarion Avenue | 14.25 | 15.0 | 0.4 |
| 22-69 / 22-75 | Brewster Avenue & Montgomery Road | 16.33 | 13.61 | 0.441 |
| 22-75 / 22-76 | Ivanhoe Avenue & Montgomery Road | 14.24 | 13.22 | 0.454 |
| 22-35N / 22-38 | West McMicken Avenue & Dixmyth Avenue | 14.52 | 12.41 | 0.484 |

Choice trail (affine to quadratic tried per plate, kept if held-out fell): no change.
Computed with numpy 2.4.2, scipy 1.18.1.
