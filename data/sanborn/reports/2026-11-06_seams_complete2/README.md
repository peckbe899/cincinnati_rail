# Seam report, 2026-11-06 (models: complete2)

Plate models: fwd_complete2.pkl where a plate has one, else its own.

Read only: every street crossing that two 1922 plates, or a 1922 plate and a 1904 frame, both show, and how far apart the two copies sit on the page. Nothing was fitted, rebuilt or changed. Method: `tools/sanborn/seams.py` (its docstring); matched by street names within 45 m. Files: `seams.csv` (every pair), `per_pair.csv` (by plate and frame), `seams.json` (all of it, with the sha256 of every file read).

Read: 21 plates on the 1922 layer (2281 crossings), 235 1904 deck and north frames (2298 crossings), 142 1904 basin frames (2446 crossings).

## Summary

| Seam | Source pairs | Shared crossings | Median m | RMS m | 90% m | Max m | > 5 m | > 10 m | > 20 m | Same names 45-150 m |
|---|---|---|---|---|---|---|---|---|---|---|
| plate-plate | 31 | 210 | 1.66 | 4.18 | 4.95 | 31.94 | 19 | 5 | 2 | 1 |
| plate-1904 | 157 | 586 | 2.23 | 6.31 | 11.01 | 38.63 | 140 | 70 | 5 | 1 |

Plate against 1904, by how the frame is drawn:

| 1904 frames | Shared crossings | Frames | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| deck/north, bent onto 1922 (lph/tps.pkl) | 481 | 88 | 1.72 | 8.99 | 38.63 |
| deck/north, not bent | 105 | 23 | 4.32 | 16.39 | 24.92 |
| basin (sbg/fit/tf.json) | 0 | 0 | - | - | - |

## Plate against plate

| Plate | Plate | Shared | Median m | Max m | Mean shift E, N m |
|---|---|---|---|---|---|
| 22-16R | 22-34R | 2 | 2.19 | 3.73 | -2.0, -0.4 |
| 22-16R | 22-35N | 3 | 2.02 | 2.47 | +0.7, -0.3 |
| 22-26A | 22-29 | 13 | 0.59 | 3.18 | -0.1, +0.1 |
| 22-29 | 22-31 | 12 | 1.12 | 3.31 | +0.1, +0.1 |
| 22-31 | 22-33 | 13 | 1.38 | 3.81 | -0.2, -0.2 |
| 22-33 | 22-34L | 9 | 2.34 | 5.28 | -0.8, -0.8 |
| 22-33 | 22-34R | 1 | 1.93 | 1.93 | +1.9, -0.2 |
| 22-34R | 22-35N | 5 | 2.16 | 3.42 | -0.0, -0.2 |
| 22-34R | 22-37R | 3 | 0.99 | 6.69 | +1.9, -0.5 |
| 22-34R | 22-38 | 2 | 3.02 | 3.4 | +2.8, +1.0 |
| 22-35N | 22-38 | 4 | 5.98 | 7.42 | -0.2, -0.3 |
| 22-37L | 22-37R | 12 | 1.42 | 4.41 | +0.3, -0.4 |
| 22-37R | 22-38 | 1 | 5.93 | 5.93 | -4.6, +3.8 |
| 22-38 | 22-66 | 1 | 1.94 | 1.94 | -1.3, -1.4 |
| 22-38 | 22-68 | 8 | 5.19 | 31.94 | +2.6, +0.6 |
| 22-66 | 22-67 | 10 | 1.77 | 4.16 | -0.2, -0.3 |
| 22-66 | 22-68 | 10 | 2.54 | 3.84 | +0.0, -0.2 |
| 22-66 | 22-69 | 10 | 4.07 | 6.22 | +0.3, +1.1 |
| 22-67 | 22-69 | 8 | 5.19 | 26.25 | +0.6, +5.4 |
| 22-67 | 22-70 | 14 | 0.97 | 5.49 | -0.0, -0.5 |
| 22-68 | 22-69 | 11 | 2.16 | 3.59 | -0.1, -0.2 |
| 22-68 | 22-75 | 4 | 2.51 | 3.66 | -0.2, -0.0 |
| 22-69 | 22-70 | 7 | 1.63 | 4.87 | -0.8, -0.2 |
| 22-69 | 22-75 | 6 | 2.03 | 14.11 | -0.6, +2.2 |
| 22-70 | 22-75 | 3 | 1.37 | 1.53 | +0.2, +0.4 |
| 22-70 | 22-76 | 1 | 0.5 | 0.5 | -0.3, +0.4 |
| 22-75 | 22-76 | 9 | 1.16 | 10.98 | -0.8, -0.7 |
| 22-75 | 22-82A | 6 | 1.16 | 1.76 | +0.2, -0.1 |
| 22-76 | 22-82A | 11 | 0.6 | 2.52 | +0.3, +0.1 |
| 22-76 | 22-83A | 3 | 2.27 | 3.3 | -0.0, -0.4 |
| 22-82A | 22-83A | 8 | 0.55 | 3.27 | -0.4, -0.0 |

## Plate against 1904 frames, by plate

| Plate | Frames | Shared | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| 22-16R | 11 | 34 | 1.04 | 14.76 | 18.45 |
| 22-26A | 7 | 29 | 1.72 | 3.17 | 3.60 |
| 22-29 | 16 | 53 | 2.95 | 10.13 | 38.63 |
| 22-31 | 14 | 51 | 6.45 | 16.80 | 24.92 |
| 22-33 | 12 | 37 | 4.19 | 11.25 | 24.16 |
| 22-34L | 2 | 8 | 2.25 | 8.40 | 15.81 |
| 22-34R | 23 | 139 | 1.43 | 5.39 | 17.40 |
| 22-35N | 20 | 52 | 1.75 | 5.06 | 27.52 |
| 22-37L | 9 | 52 | 1.85 | 7.65 | 13.12 |
| 22-37R | 10 | 36 | 4.79 | 9.41 | 12.48 |
| 22-38 | 14 | 47 | 3.20 | 14.35 | 15.57 |
| 22-66 | 13 | 38 | 1.43 | 4.01 | 6.15 |
| 22-67 | 4 | 7 | 0.74 | 3.57 | 4.75 |
| 22-68 | 2 | 3 | 1.68 | 11.34 | 13.76 |

## Widest 20, plate against plate

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 31.9 | 22-38 | 22-68 | Beldare Avenue & Vine Street | +31.9, -2.4 |
| 26.2 | 22-67 | 22-69 | Gilbert Avenue & Woodburn Avenue | +5.2, +25.7 |
| 14.1 | 22-69 | 22-75 | Lexington Avenue & Magill Avenue | -7.8, +11.8 |
| 12.9 | 22-67 | 22-69 | Harvard Avenue & Gilbert Avenue | +0.5, +12.9 |
| 11.0 | 22-75 | 22-76 | Ivanhoe Avenue & Montgomery Road | -5.0, -9.8 |
| 7.4 | 22-35N | 22-38 | Dixmyth Avenue & Morrison Avenue | +1.8, -7.2 |
| 6.9 | 22-38 | 22-68 | Woolper Street & Vine Street | -4.8, +4.9 |
| 6.7 | 22-34R | 22-37R | Spring Grove Avenue & Sassafras Street | +6.6, -0.9 |
| 6.6 | 22-38 | 22-68 | Glenmary Avenue & Vine Street | -4.4, +5.0 |
| 6.6 | 22-35N | 22-38 | Dixmyth Avenue & Whitfield Avenue | -5.5, -3.6 |
| 6.2 | 22-66 | 22-69 | Whittier Street & Wehrman Street | +4.2, +4.6 |
| 6.1 | 22-67 | 22-69 | Gilbert Avenue & Dixmont Avenue | -1.1, +6.0 |
| 5.9 | 22-37R | 22-38 | Ludlow Avenue & Lafayette Avenue | -4.6, +3.8 |
| 5.7 | 22-67 | 22-69 | Gilbert Avenue & Walter Avenue | -5.6, -0.8 |
| 5.5 | 22-67 | 22-70 | Montgomery Road & Hewitt Avenue | -4.8, -2.7 |
| 5.5 | 22-67 | 22-70 | Woodburn Avenue & Hewitt Avenue | +4.3, -3.3 |
| 5.4 | 22-35N | 22-38 | West McMicken Avenue & Dixmyth Avenue | +2.0, +5.0 |
| 5.4 | 22-38 | 22-68 | Erkenbrecher Avenue & Vine Street | -4.1, +3.5 |
| 5.3 | 22-33 | 22-34L | Seegar Avenue & Carll Street | -5.1, +1.2 |
| 5.0 | 22-33 | 22-34L | Carll Street & Cummings Street | -4.7, -1.7 |

## Widest 20, plate against 1904

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 38.6 | 22-29 | 1904 466 (deck/north, bent) | Warsaw Avenue & Wilder Avenue | -4.0, -38.4 |
| 27.5 | 22-35N | 1904 284 (deck/north, bent) | Marshall Avenue & Foulke Street | -27.4, -3.0 |
| 24.9 | 22-31 | 1904 245 (deck/north) | Queen City Avenue & Garrard Avenue | +24.7, +3.6 |
| 24.2 | 22-33 | 1904 245 (deck/north) | Garrard Avenue & Queen City Avenue | +23.7, +4.7 |
| 20.6 | 22-31 | 1904 233 (deck/north) | Queen City Avenue & Garrard Avenue | +20.5, +1.9 |
| 19.7 | 22-33 | 1904 233 (deck/north) | Garrard Avenue & Queen City Avenue | +19.5, +3.0 |
| 19.7 | 22-35N | 1904 289 (deck/north, bent) | West McMicken Avenue & Dixmyth Avenue | -4.6, +19.1 |
| 19.6 | 22-31 | 1904 211 (deck/north) | York Street & Garrard Avenue | +19.6, -0.0 |
| 18.6 | 22-31 | 1904 201 (deck/north) | Poplar Street & Garrard Avenue | +18.1, +4.0 |
| 18.5 | 22-35N | 1904 290 (deck/north, bent) | West McMicken Avenue & Dixmyth Avenue | -4.9, +17.8 |
| 18.4 | 22-16R | 1904 234 (deck/north, bent) | Spring Grove Avenue & Queen City Avenue | -18.2, -3.0 |
| 18.0 | 22-16R | 1904 235 (deck/north, bent) | Spring Grove Avenue & Queen City Avenue | -17.8, -2.8 |
| 17.9 | 22-29 | 1904 57 (deck/north) | Garrard Avenue & Hopkins Street | +4.8, +17.2 |
| 17.7 | 22-16R | 1904 246 (deck/north, bent) | Spring Grove Avenue & Queen City Avenue | -17.6, -2.6 |
| 17.5 | 22-29 | 1904 68 (deck/north) | Garrard Avenue & Hopkins Street | +5.1, +16.8 |
| 17.4 | 22-34R | 1904 302 (deck/north, bent) | Rawson Street & Township Street | +15.7, -7.4 |
| 17.1 | 22-31 | 1904 233 (deck/north) | Harrison Avenue & Garrard Avenue | +15.3, +7.5 |
| 17.0 | 22-34R | 1904 303 (deck/north, bent) | Johnson Street & Alabama Avenue | +0.8, -17.0 |
| 16.9 | 22-34R | 1904 302 (deck/north, bent) | Rawson Street & Spring Grove Avenue | +13.1, -10.7 |
| 16.8 | 22-31 | 1904 221 (deck/north) | Duck Street & Garrard Avenue | +12.4, +11.3 |

## Same street names, 45-150 m apart

Either a seam that wide or two different crossings of the same two streets; not counted above.

- 22-66 / 1904 262: Calhoun Street & Jefferson Avenue, 53.5 m
- 22-69 / 22-75: Herbert Avenue & Montgomery Road, 85.0 m

## Notes

- Plate positions come from the stored forward models (`fwd.pkl`); the page draws the plates through the inverse grids made from them on a 2 m grid, so the drawn position can differ by a fraction of a metre. Plate 35N is Ben's georeference as drawn.
- The 1904 frames bent onto the 1922 plates were bent at these same crossings, so their small distances are by construction.
- Placement checked against the workspace's own `cuf/x1904.json` (same frames, its pre-bend model): identical to 0.0 m on 830 frame crossings and 360 plate crossings.
- Computed with Python 3.12.10, numpy 2.4.2, scipy 1.18.1, pyproj 3.7.2 (the workspace's versions are not recorded).
