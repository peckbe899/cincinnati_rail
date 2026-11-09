# Seam report, 2026-11-08

Plate models: each plate's own (fwd.pkl, Ben georeference for 35N).

Read only: every street crossing that two 1922 plates, or a 1922 plate and a 1904 frame, both show, and how far apart the two copies sit on the page. Nothing was fitted, rebuilt or changed. Method: `tools/sanborn/seams.py` (its docstring); matched by street names within 45 m. Files: `seams.csv` (every pair), `per_pair.csv` (by plate and frame), `seams.json` (all of it, with the sha256 of every file read).

Read: 23 plates on the 1922 layer (2162 crossings), 235 1904 deck and north frames (2298 crossings), 142 1904 basin frames (2446 crossings).

## Summary

| Seam | Source pairs | Shared crossings | Median m | RMS m | 90% m | Max m | > 5 m | > 10 m | > 20 m | Same names 45-150 m |
|---|---|---|---|---|---|---|---|---|---|---|
| plate-plate | 38 | 173 | 1.28 | 4.89 | 5.72 | 29.33 | 21 | 8 | 3 | 1 |
| plate-1904 | 156 | 556 | 0.46 | 6.38 | 7.41 | 32.13 | 80 | 47 | 23 | 0 |

Plate against 1904, by how the frame is drawn:

| 1904 frames | Shared crossings | Frames | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| deck/north, bent onto 1922 (lph/tps.pkl) | 458 | 88 | 0.27 | 3.41 | 27.58 |
| deck/north, not bent | 98 | 23 | 4.69 | 25.43 | 32.13 |
| basin (sbg/fit/tf.json) | 0 | 0 | - | - | - |

## Plate against plate

| Plate | Plate | Shared | Median m | Max m | Mean shift E, N m |
|---|---|---|---|---|---|
| 22-16R | 22-34R | 2 | 2.56 | 3.56 | -1.0, -0.2 |
| 22-16R | 22-35N | 3 | 1.15 | 1.78 | +0.5, -0.0 |
| 22-25 | 22-26A | 2 | 0.9 | 1.5 | +0.1, +0.6 |
| 22-25 | 22-26B | 4 | 0.34 | 0.85 | +0.1, -0.2 |
| 22-25 | 22-28 | 9 | 0.38 | 5.84 | +0.5, -0.1 |
| 22-25 | 22-29 | 1 | 0.37 | 0.37 | +0.1, +0.3 |
| 22-26A | 22-28 | 1 | 1.49 | 1.49 | +0.1, -1.5 |
| 22-26A | 22-29 | 13 | 0.62 | 3.18 | -0.1, -0.1 |
| 22-26B | 22-28 | 1 | 0.55 | 0.55 | +0.2, +0.5 |
| 22-28 | 22-29 | 8 | 0.54 | 0.86 | -0.0, +0.1 |
| 22-28 | 22-31 | 1 | 0.71 | 0.71 | +0.5, +0.5 |
| 22-29 | 22-31 | 11 | 0.94 | 3.55 | -0.1, +0.2 |
| 22-31 | 22-33 | 6 | 2.59 | 4.69 | -0.9, -0.6 |
| 22-33 | 22-34L | 7 | 2.62 | 7.16 | -0.8, -0.7 |
| 22-33 | 22-34R | 1 | 10.05 | 10.05 | +5.4, -8.5 |
| 22-34R | 22-35N | 5 | 1.81 | 3.42 | -0.1, -0.1 |
| 22-34R | 22-37R | 3 | 1.57 | 7.11 | -0.3, -1.5 |
| 22-34R | 22-38 | 2 | 4.85 | 5.79 | +0.1, +4.8 |
| 22-35N | 22-38 | 4 | 3.21 | 5.88 | +0.3, -0.2 |
| 22-37L | 22-37R | 12 | 1.29 | 5.19 | +0.1, +0.3 |
| 22-37R | 22-38 | 1 | 12.34 | 12.34 | +12.3, +0.6 |
| 22-38 | 22-66 | 1 | 0.99 | 0.99 | -0.7, -0.7 |
| 22-38 | 22-68 | 4 | 4.19 | 11.15 | -1.9, +3.1 |
| 22-66 | 22-67 | 3 | 1.25 | 3.72 | -0.4, +1.4 |
| 22-66 | 22-68 | 7 | 1.42 | 4.65 | -0.1, -0.8 |
| 22-66 | 22-69 | 8 | 2.56 | 27.75 | +1.2, +3.5 |
| 22-67 | 22-69 | 2 | 16.09 | 26.33 | +2.1, +15.8 |
| 22-67 | 22-70 | 9 | 0.8 | 5.49 | +0.3, -0.6 |
| 22-68 | 22-69 | 4 | 2.33 | 29.33 | +4.8, +6.7 |
| 22-68 | 22-75 | 2 | 2.3 | 2.97 | +1.0, +0.8 |
| 22-69 | 22-70 | 2 | 2.88 | 4.25 | +0.3, +2.9 |
| 22-69 | 22-75 | 3 | 0.77 | 9.62 | +1.1, +3.0 |
| 22-70 | 22-75 | 3 | 8.13 | 16.14 | -2.8, -1.3 |
| 22-75 | 22-76 | 4 | 0.97 | 10.96 | -1.5, -2.7 |
| 22-75 | 22-82A | 5 | 1.8 | 2.24 | +0.2, -0.3 |
| 22-76 | 22-82A | 10 | 0.64 | 2.51 | +0.3, +0.2 |
| 22-76 | 22-83A | 3 | 2.23 | 3.32 | +0.0, -0.4 |
| 22-82A | 22-83A | 6 | 0.67 | 3.09 | -0.2, -0.2 |

## Plate against 1904 frames, by plate

| Plate | Frames | Shared | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| 22-16R | 11 | 34 | 0.23 | 3.16 | 11.84 |
| 22-26A | 7 | 29 | 1.71 | 3.13 | 3.88 |
| 22-29 | 16 | 46 | 2.96 | 9.93 | 26.83 |
| 22-31 | 14 | 49 | 6.63 | 26.61 | 32.13 |
| 22-33 | 11 | 33 | 3.91 | 10.09 | 30.41 |
| 22-34L | 2 | 8 | 0.14 | 5.46 | 10.16 |
| 22-34R | 23 | 139 | 0.24 | 1.64 | 15.20 |
| 22-35N | 20 | 52 | 0.29 | 3.92 | 27.58 |
| 22-37L | 9 | 50 | 0.11 | 0.32 | 9.00 |
| 22-37R | 10 | 36 | 0.16 | 7.14 | 11.20 |
| 22-38 | 14 | 46 | 0.32 | 5.21 | 23.31 |
| 22-66 | 13 | 25 | 0.14 | 1.09 | 2.60 |
| 22-67 | 4 | 7 | 0.35 | 3.57 | 4.73 |
| 22-68 | 2 | 2 | 0.70 | 1.04 | 1.12 |

## Widest 20, plate against plate

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 29.3 | 22-68 | 22-69 | Ridgeway Avenue & Reading Road | +16.7, +24.1 |
| 27.8 | 22-66 | 22-69 | Ridgeway Avenue & Reading Road | +15.9, +22.8 |
| 26.3 | 22-67 | 22-69 | Gilbert Avenue & Woodburn Avenue | +5.1, +25.8 |
| 16.1 | 22-70 | 22-75 | Montgomery Road & Clarion Avenue | -10.4, -12.3 |
| 12.3 | 22-37R | 22-38 | Ludlow Avenue & Lafayette Avenue | +12.3, +0.6 |
| 11.2 | 22-38 | 22-68 | Glenmary Avenue & Vine Street | -7.0, +8.7 |
| 11.0 | 22-75 | 22-76 | Ivanhoe Avenue & Montgomery Road | -5.3, -9.6 |
| 10.1 | 22-33 | 22-34R | Marshall Avenue & Garrard Avenue | +5.4, -8.5 |
| 9.6 | 22-69 | 22-75 | Brewster Avenue & Montgomery Road | +3.2, +9.1 |
| 8.1 | 22-70 | 22-75 | Montgomery Road & Brewster Avenue | +2.9, +7.6 |
| 7.2 | 22-33 | 22-34L | Seegar Avenue & Carll Street | -7.1, +0.8 |
| 7.1 | 22-34R | 22-37R | Spring Grove Avenue & Sassafras Street | -1.0, -7.0 |
| 6.6 | 22-66 | 22-69 | Wehrman Street & Gilbert Avenue | -5.9, -3.0 |
| 5.9 | 22-35N | 22-38 | Dixmyth Avenue & Morrison Avenue | -0.1, -5.9 |
| 5.9 | 22-67 | 22-69 | Gilbert Avenue & Dixmont Avenue | -1.0, +5.8 |
| 5.8 | 22-25 | 22-28 | West 8th Street & Wells Street | +5.8, -0.2 |
| 5.8 | 22-34R | 22-38 | Vermont Avenue & Stock Avenue | +0.3, +5.8 |
| 5.8 | 22-38 | 22-68 | Woolper Street & Vine Street | +0.5, +5.8 |
| 5.5 | 22-67 | 22-70 | Montgomery Road & Hewitt Avenue | -4.8, -2.7 |
| 5.5 | 22-67 | 22-70 | Woodburn Avenue & Hewitt Avenue | +4.3, -3.3 |

## Widest 20, plate against 1904

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 32.1 | 22-31 | 1904 245 (deck/north) | Queen City Avenue & Garrard Avenue | +32.0, -2.2 |
| 30.4 | 22-33 | 1904 245 (deck/north) | Garrard Avenue & Queen City Avenue | +30.1, -4.2 |
| 30.2 | 22-31 | 1904 211 (deck/north) | York Street & Garrard Avenue | +30.2, +0.7 |
| 29.6 | 22-31 | 1904 201 (deck/north) | Poplar Street & Garrard Avenue | +29.4, +3.2 |
| 28.1 | 22-31 | 1904 233 (deck/north) | Queen City Avenue & Garrard Avenue | +27.9, -3.8 |
| 27.6 | 22-35N | 1904 284 (deck/north, bent) | Marshall Avenue & Foulke Street | -27.6, -1.1 |
| 27.0 | 22-31 | 1904 201 (deck/north) | Sherman Avenue & Garrard Avenue | +26.6, +4.4 |
| 26.8 | 22-29 | 1904 201 (deck/north) | Garrard Avenue & West Liberty Street | +26.3, +5.4 |
| 26.6 | 22-33 | 1904 233 (deck/north) | Garrard Avenue & Queen City Avenue | +25.9, -5.8 |
| 26.5 | 22-31 | 1904 211 (deck/north) | Exeter Street & Garrard Avenue | +26.5, -0.6 |
| 26.0 | 22-29 | 1904 67 (deck/north) | Garrard Avenue & West Liberty Street | +25.5, +5.1 |
| 25.2 | 22-31 | 1904 201 (deck/north) | West Liberty Street & Garrard Avenue | +24.7, +5.1 |
| 24.9 | 22-31 | 1904 233 (deck/north) | Harrison Avenue & Garrard Avenue | +23.9, +7.0 |
| 24.4 | 22-31 | 1904 221 (deck/north) | Duck Street & Garrard Avenue | +21.4, +11.8 |
| 24.4 | 22-31 | 1904 67 (deck/north) | West Liberty Street & Garrard Avenue | +23.9, +4.8 |
| 24.2 | 22-35N | 1904 289 (deck/north, bent) | West McMicken Avenue & Dixmyth Avenue | +2.7, +24.1 |
| 24.0 | 22-31 | 1904 222 (deck/north) | Harrison Avenue & Garrard Avenue | +23.3, +5.5 |
| 23.8 | 22-31 | 1904 221 (deck/north) | Harrison Avenue & Garrard Avenue | +22.9, +6.2 |
| 23.3 | 22-38 | 1904 289 (deck/north, bent) | Julia Ann Street & West McMicken Avenue | +9.5, +21.3 |
| 22.6 | 22-29 | 1904 57 (deck/north) | Garrard Avenue & Hopkins Street | +15.8, +16.2 |

## Same street names, 45-150 m apart

Either a seam that wide or two different crossings of the same two streets; not counted above.

- 22-69 / 22-75: Herbert Avenue & Montgomery Road, 95.4 m

## Notes

- Plate positions come from the stored forward models (`fwd.pkl`); the page draws the plates through the inverse grids made from them on a 2 m grid, so the drawn position can differ by a fraction of a metre. Plate 35N is Ben's georeference as drawn.
- The 1904 frames bent onto the 1922 plates were bent at these same crossings, so their small distances are by construction.
- Placement checked against the workspace's own `cuf/x1904.json` (same frames, its pre-bend model): identical to 0.0 m on 830 frame crossings and 360 plate crossings.
- Computed with Python 3.12.10, numpy 2.4.2, scipy 1.18.1, pyproj 3.7.2 (the workspace's versions are not recorded).
