# Seam report, 2026-11-06 (models: complete)

Plate models: fwd_complete.pkl where a plate has one, else its own.

Read only: every street crossing that two 1922 plates, or a 1922 plate and a 1904 frame, both show, and how far apart the two copies sit on the page. Nothing was fitted, rebuilt or changed. Method: `tools/sanborn/seams.py` (its docstring); matched by street names within 45 m. Files: `seams.csv` (every pair), `per_pair.csv` (by plate and frame), `seams.json` (all of it, with the sha256 of every file read).

Read: 21 plates on the 1922 layer (2281 crossings), 235 1904 deck and north frames (2298 crossings), 142 1904 basin frames (2446 crossings).

## Summary

| Seam | Source pairs | Shared crossings | Median m | RMS m | 90% m | Max m | > 5 m | > 10 m | > 20 m | Same names 45-150 m |
|---|---|---|---|---|---|---|---|---|---|---|
| plate-plate | 31 | 210 | 1.5 | 4.2 | 4.35 | 34.47 | 16 | 6 | 2 | 1 |
| plate-1904 | 157 | 586 | 2.12 | 6.74 | 8.2 | 38.72 | 120 | 50 | 21 | 1 |

Plate against 1904, by how the frame is drawn:

| 1904 frames | Shared crossings | Frames | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| deck/north, bent onto 1922 (lph/tps.pkl) | 481 | 88 | 1.74 | 6.38 | 38.72 |
| deck/north, not bent | 105 | 23 | 4.27 | 25.08 | 32.13 |
| basin (sbg/fit/tf.json) | 0 | 0 | - | - | - |

## Plate against plate

| Plate | Plate | Shared | Median m | Max m | Mean shift E, N m |
|---|---|---|---|---|---|
| 22-16R | 22-34R | 2 | 2.56 | 3.56 | -1.0, -0.2 |
| 22-16R | 22-35N | 3 | 1.15 | 1.78 | +0.5, -0.0 |
| 22-26A | 22-29 | 13 | 0.62 | 3.18 | -0.1, -0.1 |
| 22-29 | 22-31 | 12 | 1.16 | 3.55 | +0.0, +0.2 |
| 22-31 | 22-33 | 13 | 1.99 | 4.69 | -0.5, -0.2 |
| 22-33 | 22-34L | 9 | 2.62 | 7.16 | -0.5, -0.6 |
| 22-33 | 22-34R | 1 | 9.65 | 9.65 | +5.0, -8.3 |
| 22-34R | 22-35N | 5 | 1.81 | 3.42 | -0.1, -0.1 |
| 22-34R | 22-37R | 3 | 0.92 | 0.97 | -0.1, -0.7 |
| 22-34R | 22-38 | 2 | 3.07 | 4.14 | +0.5, +3.0 |
| 22-35N | 22-38 | 4 | 3.27 | 5.88 | +0.3, -0.2 |
| 22-37L | 22-37R | 12 | 1.53 | 4.24 | -0.1, -0.2 |
| 22-37R | 22-38 | 1 | 4.66 | 4.66 | -3.5, +3.1 |
| 22-38 | 22-66 | 1 | 0.99 | 0.99 | -0.7, -0.7 |
| 22-38 | 22-68 | 8 | 4.19 | 34.47 | +2.4, +1.2 |
| 22-66 | 22-67 | 10 | 1.43 | 3.72 | -0.1, +0.1 |
| 22-66 | 22-68 | 10 | 1.28 | 4.65 | -0.1, -0.1 |
| 22-66 | 22-69 | 10 | 1.78 | 6.62 | -0.6, +0.2 |
| 22-67 | 22-69 | 8 | 3.63 | 26.33 | +0.7, +5.3 |
| 22-67 | 22-70 | 14 | 0.97 | 5.49 | +0.0, -0.5 |
| 22-68 | 22-69 | 11 | 1.89 | 3.54 | -0.1, -0.2 |
| 22-68 | 22-75 | 4 | 2.3 | 3.94 | -0.3, -0.3 |
| 22-69 | 22-70 | 7 | 1.13 | 4.25 | -0.3, +0.7 |
| 22-69 | 22-75 | 6 | 1.55 | 9.75 | -0.2, +1.3 |
| 22-70 | 22-75 | 3 | 1.55 | 8.13 | +0.4, +3.2 |
| 22-70 | 22-76 | 1 | 0.5 | 0.5 | -0.3, +0.4 |
| 22-75 | 22-76 | 9 | 1.31 | 10.96 | -0.8, -0.6 |
| 22-75 | 22-82A | 6 | 1.54 | 2.24 | +0.3, -0.3 |
| 22-76 | 22-82A | 11 | 0.61 | 2.51 | +0.3, +0.1 |
| 22-76 | 22-83A | 3 | 2.23 | 3.32 | +0.0, -0.4 |
| 22-82A | 22-83A | 8 | 0.67 | 3.09 | -0.5, -0.1 |

## Plate against 1904 frames, by plate

| Plate | Frames | Shared | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| 22-16R | 11 | 34 | 1.02 | 3.81 | 11.84 |
| 22-26A | 7 | 29 | 1.71 | 3.13 | 3.88 |
| 22-29 | 16 | 53 | 3.26 | 10.07 | 38.72 |
| 22-31 | 14 | 51 | 6.30 | 26.52 | 32.13 |
| 22-33 | 12 | 37 | 3.88 | 12.83 | 30.41 |
| 22-34L | 2 | 8 | 0.31 | 5.46 | 10.16 |
| 22-34R | 23 | 139 | 1.40 | 5.30 | 15.19 |
| 22-35N | 20 | 52 | 1.52 | 3.90 | 27.47 |
| 22-37L | 9 | 52 | 2.17 | 6.34 | 9.76 |
| 22-37R | 10 | 36 | 3.67 | 6.27 | 7.64 |
| 22-38 | 14 | 47 | 2.55 | 8.07 | 11.04 |
| 22-66 | 13 | 38 | 1.21 | 3.61 | 6.40 |
| 22-67 | 4 | 7 | 0.78 | 3.56 | 4.74 |
| 22-68 | 2 | 3 | 1.92 | 10.69 | 12.88 |

## Widest 20, plate against plate

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 34.5 | 22-38 | 22-68 | Beldare Avenue & Vine Street | +34.3, -3.0 |
| 26.3 | 22-67 | 22-69 | Gilbert Avenue & Woodburn Avenue | +5.1, +25.8 |
| 11.7 | 22-67 | 22-69 | Harvard Avenue & Gilbert Avenue | +0.1, +11.7 |
| 11.3 | 22-38 | 22-68 | Erkenbrecher Avenue & Vine Street | -11.2, +0.9 |
| 11.2 | 22-38 | 22-68 | Glenmary Avenue & Vine Street | -7.0, +8.7 |
| 11.0 | 22-75 | 22-76 | Ivanhoe Avenue & Montgomery Road | -5.3, -9.6 |
| 9.8 | 22-69 | 22-75 | Lexington Avenue & Magill Avenue | -5.0, +8.3 |
| 9.7 | 22-33 | 22-34R | Marshall Avenue & Garrard Avenue | +5.0, -8.3 |
| 8.1 | 22-70 | 22-75 | Montgomery Road & Brewster Avenue | +2.9, +7.6 |
| 7.2 | 22-33 | 22-34L | Seegar Avenue & Carll Street | -7.1, +0.8 |
| 6.6 | 22-66 | 22-69 | Wehrman Street & Gilbert Avenue | -5.9, -3.0 |
| 5.9 | 22-35N | 22-38 | Dixmyth Avenue & Morrison Avenue | -0.1, -5.9 |
| 5.9 | 22-67 | 22-69 | Gilbert Avenue & Dixmont Avenue | -1.0, +5.8 |
| 5.8 | 22-38 | 22-68 | Woolper Street & Vine Street | +0.5, +5.8 |
| 5.5 | 22-67 | 22-70 | Montgomery Road & Hewitt Avenue | -4.8, -2.7 |
| 5.5 | 22-67 | 22-70 | Woodburn Avenue & Hewitt Avenue | +4.3, -3.3 |
| 4.7 | 22-31 | 22-33 | Engel Alley & Queen City Avenue | -4.1, -2.3 |
| 4.7 | 22-37R | 22-38 | Ludlow Avenue & Lafayette Avenue | -3.5, +3.1 |
| 4.7 | 22-66 | 22-68 | French Street & Eden Avenue | +3.0, -3.5 |
| 4.5 | 22-75 | 22-76 | Lexington Avenue & Montgomery Road | +2.9, +3.5 |

## Widest 20, plate against 1904

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 38.7 | 22-29 | 1904 466 (deck/north, bent) | Warsaw Avenue & Wilder Avenue | -4.1, -38.5 |
| 32.1 | 22-31 | 1904 245 (deck/north) | Queen City Avenue & Garrard Avenue | +32.0, -2.2 |
| 30.4 | 22-33 | 1904 245 (deck/north) | Garrard Avenue & Queen City Avenue | +30.1, -4.2 |
| 30.2 | 22-31 | 1904 211 (deck/north) | York Street & Garrard Avenue | +30.2, +0.7 |
| 29.6 | 22-31 | 1904 201 (deck/north) | Poplar Street & Garrard Avenue | +29.4, +3.2 |
| 28.1 | 22-31 | 1904 233 (deck/north) | Queen City Avenue & Garrard Avenue | +27.9, -3.8 |
| 27.5 | 22-35N | 1904 284 (deck/north, bent) | Marshall Avenue & Foulke Street | -27.5, -0.7 |
| 27.0 | 22-31 | 1904 201 (deck/north) | Sherman Avenue & Garrard Avenue | +26.6, +4.4 |
| 26.8 | 22-29 | 1904 201 (deck/north) | Garrard Avenue & West Liberty Street | +26.3, +5.4 |
| 26.6 | 22-33 | 1904 233 (deck/north) | Garrard Avenue & Queen City Avenue | +25.9, -5.8 |
| 26.5 | 22-31 | 1904 211 (deck/north) | Exeter Street & Garrard Avenue | +26.5, -0.6 |
| 26.0 | 22-29 | 1904 67 (deck/north) | Garrard Avenue & West Liberty Street | +25.5, +5.1 |
| 25.2 | 22-31 | 1904 201 (deck/north) | West Liberty Street & Garrard Avenue | +24.7, +5.1 |
| 24.9 | 22-31 | 1904 233 (deck/north) | Harrison Avenue & Garrard Avenue | +23.9, +7.0 |
| 24.4 | 22-31 | 1904 221 (deck/north) | Duck Street & Garrard Avenue | +21.4, +11.8 |
| 24.4 | 22-31 | 1904 67 (deck/north) | West Liberty Street & Garrard Avenue | +23.9, +4.8 |
| 24.0 | 22-31 | 1904 222 (deck/north) | Harrison Avenue & Garrard Avenue | +23.3, +5.5 |
| 23.8 | 22-31 | 1904 221 (deck/north) | Harrison Avenue & Garrard Avenue | +22.9, +6.2 |
| 22.6 | 22-29 | 1904 57 (deck/north) | Garrard Avenue & Hopkins Street | +15.8, +16.2 |
| 22.5 | 22-29 | 1904 68 (deck/north) | Garrard Avenue & Hopkins Street | +16.0, +15.8 |

## Same street names, 45-150 m apart

Either a seam that wide or two different crossings of the same two streets; not counted above.

- 22-66 / 1904 262: Calhoun Street & Jefferson Avenue, 54.2 m
- 22-69 / 22-75: Herbert Avenue & Montgomery Road, 95.4 m

## Notes

- Plate positions come from the stored forward models (`fwd.pkl`); the page draws the plates through the inverse grids made from them on a 2 m grid, so the drawn position can differ by a fraction of a metre. Plate 35N is Ben's georeference as drawn.
- The 1904 frames bent onto the 1922 plates were bent at these same crossings, so their small distances are by construction.
- Placement checked against the workspace's own `cuf/x1904.json` (same frames, its pre-bend model): identical to 0.0 m on 830 frame crossings and 360 plate crossings.
- Computed with Python 3.12.10, numpy 2.4.2, scipy 1.18.1, pyproj 3.7.2 (the workspace's versions are not recorded).
