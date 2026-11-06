# Seam report, 2026-11-06 (plates on the joint refit)

Plate models: joint refit (fwd_joint.pkl).

Read only: every street crossing that two 1922 plates, or a 1922 plate and a 1904 frame, both show, and how far apart the two copies sit on the page. Nothing was fitted, rebuilt or changed. Method: `tools/sanborn/seams.py` (its docstring); matched by street names within 45 m. Files: `seams.csv` (every pair), `per_pair.csv` (by plate and frame), `seams.json` (all of it, with the sha256 of every file read).

Read: 21 plates on the 1922 layer (1986 crossings), 235 1904 deck and north frames (2298 crossings), 142 1904 basin frames (2446 crossings).

## Summary

| Seam | Source pairs | Shared crossings | Median m | RMS m | 90% m | Max m | > 5 m | > 10 m | > 20 m | Same names 45-150 m |
|---|---|---|---|---|---|---|---|---|---|---|
| plate-plate | 30 | 146 | 2.45 | 7.2 | 11.79 | 28.79 | 33 | 17 | 5 | 1 |
| plate-1904 | 156 | 556 | 1.25 | 6.64 | 7.62 | 34.73 | 90 | 52 | 22 | 0 |

Plate against 1904, by how the frame is drawn:

| 1904 frames | Shared crossings | Frames | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| deck/north, bent onto 1922 (lph/tps.pkl) | 458 | 88 | 1.01 | 3.87 | 28.98 |
| deck/north, not bent | 98 | 23 | 5.35 | 24.88 | 34.73 |
| basin (sbg/fit/tf.json) | 0 | 0 | - | - | - |

## Plate against plate

| Plate | Plate | Shared | Median m | Max m | Mean shift E, N m |
|---|---|---|---|---|---|
| 22-16R | 22-34R | 2 | 4.79 | 5.58 | -0.9, +0.1 |
| 22-16R | 22-35N | 3 | 3.67 | 3.71 | +1.2, -0.3 |
| 22-26A | 22-29 | 13 | 1.44 | 4.01 | -0.1, -0.3 |
| 22-29 | 22-31 | 11 | 1.8 | 4.75 | -0.1, +0.3 |
| 22-31 | 22-33 | 6 | 2.98 | 9.51 | -0.4, +1.3 |
| 22-33 | 22-34L | 7 | 3.73 | 9.36 | -0.2, -1.1 |
| 22-33 | 22-34R | 1 | 25.05 | 25.05 | +16.6, -18.8 |
| 22-34R | 22-35N | 5 | 2.08 | 4.0 | -0.3, -0.2 |
| 22-34R | 22-37R | 3 | 1.65 | 10.29 | -1.4, -2.7 |
| 22-34R | 22-38 | 2 | 17.2 | 17.91 | +0.5, +17.2 |
| 22-35N | 22-38 | 4 | 4.52 | 12.41 | -1.1, +1.4 |
| 22-37L | 22-37R | 12 | 5.02 | 23.33 | +4.1, -1.8 |
| 22-37R | 22-38 | 1 | 15.5 | 15.5 | -5.4, +14.5 |
| 22-38 | 22-66 | 1 | 1.2 | 1.2 | -0.6, +1.1 |
| 22-38 | 22-68 | 4 | 5.38 | 9.45 | +0.2, -0.9 |
| 22-66 | 22-67 | 3 | 2.77 | 3.3 | -1.3, +1.1 |
| 22-66 | 22-68 | 7 | 3.63 | 4.48 | -0.4, +1.0 |
| 22-66 | 22-69 | 8 | 3.81 | 24.66 | +0.6, +2.8 |
| 22-67 | 22-69 | 2 | 17.66 | 28.79 | +4.3, +16.9 |
| 22-67 | 22-70 | 9 | 1.41 | 5.7 | +0.2, -0.6 |
| 22-68 | 22-69 | 4 | 2.67 | 27.13 | +4.7, +5.8 |
| 22-68 | 22-75 | 2 | 2.68 | 2.89 | +0.2, -0.2 |
| 22-69 | 22-70 | 2 | 2.56 | 3.02 | +1.3, +1.9 |
| 22-69 | 22-75 | 3 | 1.56 | 13.61 | +2.6, +3.5 |
| 22-70 | 22-75 | 3 | 11.16 | 15.0 | -3.1, -0.2 |
| 22-75 | 22-76 | 4 | 1.62 | 13.22 | -2.9, -2.6 |
| 22-75 | 22-82A | 5 | 2.86 | 9.33 | +1.6, -0.3 |
| 22-76 | 22-82A | 10 | 1.8 | 4.15 | +0.5, +0.2 |
| 22-76 | 22-83A | 3 | 2.18 | 4.91 | +0.4, -0.8 |
| 22-82A | 22-83A | 6 | 1.12 | 5.73 | -0.6, +0.0 |

## Plate against 1904 frames, by plate

| Plate | Frames | Shared | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| 22-16R | 11 | 34 | 0.54 | 5.62 | 12.12 |
| 22-26A | 7 | 29 | 1.54 | 4.14 | 6.15 |
| 22-29 | 16 | 46 | 2.79 | 11.56 | 24.84 |
| 22-31 | 14 | 49 | 6.80 | 25.87 | 33.57 |
| 22-33 | 11 | 33 | 3.96 | 21.99 | 34.73 |
| 22-34L | 2 | 8 | 0.52 | 6.49 | 11.47 |
| 22-34R | 23 | 139 | 0.85 | 1.67 | 13.91 |
| 22-35N | 20 | 52 | 0.85 | 4.63 | 28.98 |
| 22-37L | 9 | 50 | 1.10 | 2.18 | 5.88 |
| 22-37R | 10 | 36 | 1.56 | 3.79 | 10.61 |
| 22-38 | 14 | 46 | 1.77 | 6.23 | 19.45 |
| 22-66 | 13 | 25 | 0.43 | 1.40 | 6.55 |
| 22-67 | 4 | 7 | 0.31 | 1.54 | 1.89 |
| 22-68 | 2 | 2 | 1.64 | 2.34 | 2.52 |

## Widest 20, plate against plate

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 28.8 | 22-67 | 22-69 | Gilbert Avenue & Woodburn Avenue | +4.9, +28.4 |
| 27.1 | 22-68 | 22-69 | Ridgeway Avenue & Reading Road | +16.3, +21.7 |
| 25.1 | 22-33 | 22-34R | Marshall Avenue & Garrard Avenue | +16.6, -18.8 |
| 24.7 | 22-66 | 22-69 | Ridgeway Avenue & Reading Road | +16.8, +18.1 |
| 23.3 | 22-37L | 22-37R | Groub Street & Ralston Avenue | +20.0, -11.9 |
| 19.2 | 22-37L | 22-37R | Geringer Street & Ralston Avenue | +15.9, -10.8 |
| 17.9 | 22-34R | 22-38 | Vermont Avenue & Stock Avenue | +0.9, +17.9 |
| 17.8 | 22-37L | 22-37R | Geringer Street & Groub Street | +16.1, -7.6 |
| 16.5 | 22-34R | 22-38 | Vermont Avenue & Bates Alley | +0.1, +16.5 |
| 15.5 | 22-37R | 22-38 | Ludlow Avenue & Lafayette Avenue | -5.4, +14.5 |
| 15.1 | 22-66 | 22-69 | Wehrman Street & Gilbert Avenue | -13.9, -5.8 |
| 15.0 | 22-70 | 22-75 | Montgomery Road & Clarion Avenue | -10.5, -10.8 |
| 13.6 | 22-69 | 22-75 | Brewster Avenue & Montgomery Road | +5.8, +12.3 |
| 13.2 | 22-75 | 22-76 | Ivanhoe Avenue & Montgomery Road | -8.6, -10.1 |
| 12.4 | 22-35N | 22-38 | West McMicken Avenue & Dixmyth Avenue | -1.7, +12.3 |
| 11.2 | 22-70 | 22-75 | Montgomery Road & Brewster Avenue | +3.2, +10.7 |
| 10.3 | 22-34R | 22-37R | Spring Grove Avenue & Sassafras Street | -2.7, -9.9 |
| 9.5 | 22-31 | 22-33 | Queen City Avenue & Garrard Avenue | +0.2, +9.5 |
| 9.4 | 22-38 | 22-68 | Ruther Avenue & Vine Street | +6.6, -6.8 |
| 9.4 | 22-33 | 22-34L | Seegar Avenue & Carll Street | -8.9, +3.0 |

## Widest 20, plate against 1904

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 34.7 | 22-33 | 1904 245 (deck/north) | Garrard Avenue & Queen City Avenue | +33.4, -9.7 |
| 33.6 | 22-31 | 1904 245 (deck/north) | Queen City Avenue & Garrard Avenue | +33.6, -0.1 |
| 31.3 | 22-33 | 1904 233 (deck/north) | Garrard Avenue & Queen City Avenue | +29.2, -11.3 |
| 29.6 | 22-31 | 1904 211 (deck/north) | York Street & Garrard Avenue | +29.5, +1.9 |
| 29.4 | 22-31 | 1904 233 (deck/north) | Queen City Avenue & Garrard Avenue | +29.4, -1.8 |
| 29.0 | 22-35N | 1904 284 (deck/north, bent) | Marshall Avenue & Foulke Street | -28.8, -3.2 |
| 28.5 | 22-31 | 1904 201 (deck/north) | Poplar Street & Garrard Avenue | +28.3, +3.5 |
| 26.0 | 22-31 | 1904 211 (deck/north) | Exeter Street & Garrard Avenue | +26.0, +0.8 |
| 25.8 | 22-31 | 1904 201 (deck/north) | Sherman Avenue & Garrard Avenue | +25.5, +4.4 |
| 25.4 | 22-31 | 1904 233 (deck/north) | Harrison Avenue & Garrard Avenue | +24.2, +7.8 |
| 25.0 | 22-31 | 1904 221 (deck/north) | Duck Street & Garrard Avenue | +21.5, +12.7 |
| 24.8 | 22-29 | 1904 201 (deck/north) | Garrard Avenue & West Liberty Street | +24.0, +6.5 |
| 24.7 | 22-33 | 1904 272 (deck/north, bent) | Marshall Avenue & Garrard Avenue | +17.1, -17.8 |
| 24.6 | 22-33 | 1904 273 (deck/north, bent) | Marshall Avenue & Garrard Avenue | +16.8, -17.9 |
| 24.4 | 22-31 | 1904 222 (deck/north) | Harrison Avenue & Garrard Avenue | +23.6, +6.3 |
| 24.3 | 22-31 | 1904 221 (deck/north) | Harrison Avenue & Garrard Avenue | +23.2, +7.0 |
| 24.2 | 22-29 | 1904 57 (deck/north) | Garrard Avenue & Hopkins Street | +17.4, +16.9 |
| 24.1 | 22-29 | 1904 68 (deck/north) | Garrard Avenue & Hopkins Street | +17.6, +16.5 |
| 24.0 | 22-31 | 1904 201 (deck/north) | West Liberty Street & Garrard Avenue | +23.6, +4.7 |
| 24.0 | 22-29 | 1904 67 (deck/north) | Garrard Avenue & West Liberty Street | +23.2, +6.2 |

## Same street names, 45-150 m apart

Either a seam that wide or two different crossings of the same two streets; not counted above.

- 22-69 / 22-75: Herbert Avenue & Montgomery Road, 98.8 m

## Notes

- Plate positions come from the stored forward models (`fwd.pkl`); the page draws the plates through the inverse grids made from them on a 2 m grid, so the drawn position can differ by a fraction of a metre. Plate 35N is Ben's georeference as drawn.
- The 1904 frames bent onto the 1922 plates were bent at these same crossings, so their small distances are by construction.
- Placement checked against the workspace's own `cuf/x1904.json` (same frames, its pre-bend model): identical to 0.0 m on 830 frame crossings and 360 plate crossings.
- Computed with Python 3.12.10, numpy 2.4.2, scipy 1.18.1, pyproj 3.7.2 (the workspace's versions are not recorded).
