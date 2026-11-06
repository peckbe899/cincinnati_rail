# Seam report, 2026-11-06

Read only: every street crossing that two 1922 plates, or a 1922 plate and a 1904 frame, both show, and how far apart the two copies sit on the page. Nothing was fitted, rebuilt or changed. Method: `tools/sanborn/seams.py` (its docstring); matched by street names within 45 m. Files: `seams.csv` (every pair), `per_pair.csv` (by plate and frame), `seams.json` (all of it, with the sha256 of every file read).

Read: 21 plates on the 1922 layer (1986 crossings), 235 1904 deck and north frames (2298 crossings), 142 1904 basin frames (2446 crossings).

## Summary

| Seam | Source pairs | Shared crossings | Median m | RMS m | 90% m | Max m | > 5 m | > 10 m | > 20 m | Same names 45-150 m |
|---|---|---|---|---|---|---|---|---|---|---|
| plate-plate | 30 | 146 | 2.88 | 8.16 | 12.75 | 30.01 | 43 | 19 | 9 | 1 |
| plate-1904 | 156 | 556 | 0.4 | 6.73 | 7.75 | 35.09 | 87 | 51 | 25 | 0 |

Plate against 1904, by how the frame is drawn:

| 1904 frames | Shared crossings | Frames | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| deck/north, bent onto 1922 (lph/tps.pkl) | 458 | 88 | 0.25 | 3.95 | 28.60 |
| deck/north, not bent | 98 | 23 | 5.22 | 25.17 | 35.09 |
| basin (sbg/fit/tf.json) | 0 | 0 | - | - | - |

## Plate against plate

| Plate | Plate | Shared | Median m | Max m | Mean shift E, N m |
|---|---|---|---|---|---|
| 22-16R | 22-34R | 2 | 4.82 | 5.76 | -0.8, -0.5 |
| 22-16R | 22-35N | 3 | 3.97 | 4.91 | +2.4, -0.1 |
| 22-26A | 22-29 | 13 | 1.57 | 4.16 | -0.1, -0.5 |
| 22-29 | 22-31 | 11 | 2.33 | 6.26 | -0.6, +1.2 |
| 22-31 | 22-33 | 6 | 2.81 | 10.0 | -0.6, +1.6 |
| 22-33 | 22-34L | 7 | 6.8 | 10.02 | +0.5, -3.2 |
| 22-33 | 22-34R | 1 | 25.58 | 25.58 | +17.4, -18.8 |
| 22-34R | 22-35N | 5 | 3.09 | 3.67 | +0.7, +1.0 |
| 22-34R | 22-37R | 3 | 1.28 | 11.39 | -0.5, -4.2 |
| 22-34R | 22-38 | 2 | 21.19 | 21.84 | -0.3, +21.2 |
| 22-35N | 22-38 | 4 | 3.67 | 14.52 | -1.1, +2.2 |
| 22-37L | 22-37R | 12 | 6.0 | 27.44 | +6.6, -1.1 |
| 22-37R | 22-38 | 1 | 19.81 | 19.81 | -4.2, +19.4 |
| 22-38 | 22-66 | 1 | 1.6 | 1.6 | -1.0, +1.3 |
| 22-38 | 22-68 | 4 | 6.08 | 8.27 | -0.3, +0.5 |
| 22-66 | 22-67 | 3 | 3.28 | 3.94 | -1.8, +1.4 |
| 22-66 | 22-68 | 7 | 3.65 | 5.78 | -0.8, +2.1 |
| 22-66 | 22-69 | 8 | 6.71 | 27.77 | +1.4, +6.5 |
| 22-67 | 22-69 | 2 | 19.07 | 30.01 | +4.7, +18.2 |
| 22-67 | 22-70 | 9 | 1.26 | 5.49 | +0.4, -0.6 |
| 22-68 | 22-69 | 4 | 3.71 | 29.87 | +5.5, +6.7 |
| 22-68 | 22-75 | 2 | 2.73 | 2.78 | +0.3, +0.1 |
| 22-69 | 22-70 | 2 | 2.88 | 4.81 | +2.0, +2.0 |
| 22-69 | 22-75 | 3 | 1.57 | 16.33 | +3.4, +5.1 |
| 22-70 | 22-75 | 3 | 12.12 | 14.25 | -3.0, +0.7 |
| 22-75 | 22-76 | 4 | 2.2 | 14.24 | -3.2, -3.4 |
| 22-75 | 22-82A | 5 | 2.85 | 9.83 | +2.0, -0.4 |
| 22-76 | 22-82A | 10 | 2.05 | 4.06 | +0.9, +0.2 |
| 22-76 | 22-83A | 3 | 1.9 | 5.36 | +0.6, -1.3 |
| 22-82A | 22-83A | 6 | 1.21 | 6.05 | -0.9, -0.1 |

## Plate against 1904 frames, by plate

| Plate | Frames | Shared | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| 22-16R | 11 | 34 | 0.23 | 5.78 | 12.50 |
| 22-26A | 7 | 29 | 1.45 | 4.24 | 6.10 |
| 22-29 | 16 | 46 | 2.67 | 11.82 | 24.41 |
| 22-31 | 14 | 49 | 6.45 | 26.67 | 34.05 |
| 22-33 | 11 | 33 | 4.19 | 22.65 | 35.09 |
| 22-34L | 2 | 8 | 0.13 | 5.47 | 11.34 |
| 22-34R | 23 | 139 | 0.25 | 1.37 | 13.65 |
| 22-35N | 20 | 52 | 0.31 | 3.97 | 28.60 |
| 22-37L | 9 | 50 | 0.10 | 0.64 | 6.16 |
| 22-37R | 10 | 36 | 0.17 | 2.82 | 11.43 |
| 22-38 | 14 | 46 | 0.35 | 4.53 | 21.81 |
| 22-66 | 13 | 25 | 0.13 | 1.32 | 6.89 |
| 22-67 | 4 | 7 | 0.36 | 1.32 | 1.67 |
| 22-68 | 2 | 2 | 1.62 | 2.68 | 2.95 |

## Widest 20, plate against plate

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 30.0 | 22-67 | 22-69 | Gilbert Avenue & Woodburn Avenue | +5.1, +29.6 |
| 29.9 | 22-68 | 22-69 | Ridgeway Avenue & Reading Road | +17.8, +24.0 |
| 27.8 | 22-66 | 22-69 | Ridgeway Avenue & Reading Road | +17.7, +21.4 |
| 27.4 | 22-37L | 22-37R | Groub Street & Ralston Avenue | +24.3, -12.7 |
| 25.6 | 22-33 | 22-34R | Marshall Avenue & Garrard Avenue | +17.4, -18.8 |
| 23.3 | 22-37L | 22-37R | Geringer Street & Ralston Avenue | +20.3, -11.5 |
| 21.8 | 22-34R | 22-38 | Vermont Avenue & Stock Avenue | +0.1, +21.8 |
| 21.8 | 22-37L | 22-37R | Geringer Street & Groub Street | +20.2, -8.1 |
| 20.5 | 22-34R | 22-38 | Vermont Avenue & Bates Alley | -0.7, +20.5 |
| 19.8 | 22-37R | 22-38 | Ludlow Avenue & Lafayette Avenue | -4.2, +19.4 |
| 16.3 | 22-69 | 22-75 | Brewster Avenue & Montgomery Road | +7.1, +14.7 |
| 14.5 | 22-35N | 22-38 | West McMicken Avenue & Dixmyth Avenue | -3.0, +14.2 |
| 14.2 | 22-70 | 22-75 | Montgomery Road & Clarion Avenue | -10.3, -9.8 |
| 14.2 | 22-75 | 22-76 | Ivanhoe Avenue & Montgomery Road | -9.0, -11.1 |
| 13.4 | 22-66 | 22-69 | Wehrman Street & Gilbert Avenue | -13.2, -1.9 |
| 12.1 | 22-70 | 22-75 | Montgomery Road & Brewster Avenue | +3.4, +11.6 |
| 11.9 | 22-37L | 22-37R | Spaeth Street & Dreman Avenue | +11.8, +1.2 |
| 11.4 | 22-34R | 22-37R | Spring Grove Avenue & Sassafras Street | -1.1, -11.3 |
| 10.0 | 22-33 | 22-34L | Casper Street & Baltimore Avenue | +4.3, -9.1 |
| 10.0 | 22-31 | 22-33 | Queen City Avenue & Garrard Avenue | +0.4, +10.0 |

## Widest 20, plate against 1904

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 35.1 | 22-33 | 1904 245 (deck/north) | Garrard Avenue & Queen City Avenue | +33.7, -9.9 |
| 34.0 | 22-31 | 1904 245 (deck/north) | Queen City Avenue & Garrard Avenue | +34.0, +0.1 |
| 31.6 | 22-33 | 1904 233 (deck/north) | Garrard Avenue & Queen City Avenue | +29.5, -11.5 |
| 30.3 | 22-31 | 1904 211 (deck/north) | York Street & Garrard Avenue | +30.3, +1.5 |
| 29.9 | 22-31 | 1904 233 (deck/north) | Queen City Avenue & Garrard Avenue | +29.9, -1.5 |
| 29.3 | 22-31 | 1904 201 (deck/north) | Poplar Street & Garrard Avenue | +29.2, +2.8 |
| 28.6 | 22-35N | 1904 284 (deck/north, bent) | Marshall Avenue & Foulke Street | -28.4, -3.7 |
| 26.8 | 22-31 | 1904 211 (deck/north) | Exeter Street & Garrard Avenue | +26.7, +0.3 |
| 26.6 | 22-31 | 1904 201 (deck/north) | Sherman Avenue & Garrard Avenue | +26.4, +3.6 |
| 26.0 | 22-31 | 1904 233 (deck/north) | Harrison Avenue & Garrard Avenue | +24.8, +7.8 |
| 25.6 | 22-33 | 1904 272 (deck/north, bent) | Marshall Avenue & Garrard Avenue | +17.6, -18.6 |
| 25.5 | 22-33 | 1904 273 (deck/north, bent) | Marshall Avenue & Garrard Avenue | +17.3, -18.8 |
| 25.5 | 22-31 | 1904 221 (deck/north) | Duck Street & Garrard Avenue | +22.2, +12.6 |
| 25.0 | 22-31 | 1904 222 (deck/north) | Harrison Avenue & Garrard Avenue | +24.2, +6.3 |
| 24.8 | 22-31 | 1904 201 (deck/north) | West Liberty Street & Garrard Avenue | +24.5, +3.9 |
| 24.8 | 22-31 | 1904 221 (deck/north) | Harrison Avenue & Garrard Avenue | +23.8, +7.0 |
| 24.4 | 22-29 | 1904 201 (deck/north) | Garrard Avenue & West Liberty Street | +23.3, +7.3 |
| 24.4 | 22-29 | 1904 57 (deck/north) | Garrard Avenue & Hopkins Street | +16.8, +17.6 |
| 24.2 | 22-29 | 1904 68 (deck/north) | Garrard Avenue & Hopkins Street | +17.0, +17.2 |
| 24.0 | 22-31 | 1904 67 (deck/north) | West Liberty Street & Garrard Avenue | +23.7, +3.6 |

## Same street names, 45-150 m apart

Either a seam that wide or two different crossings of the same two streets; not counted above.

- 22-69 / 22-75: Herbert Avenue & Montgomery Road, 101.3 m

## Notes

- Plate positions come from the stored forward models (`fwd.pkl`); the page draws the plates through the inverse grids made from them on a 2 m grid, so the drawn position can differ by a fraction of a metre. Plate 35N is Ben's georeference as drawn.
- The 1904 frames bent onto the 1922 plates were bent at these same crossings, so their small distances are by construction.
- Placement checked against the workspace's own `cuf/x1904.json` (same frames, its pre-bend model): identical to 0.0 m on 830 frame crossings and 360 plate crossings.
- Computed with Python 3.12.10, numpy 2.4.2, scipy 1.18.1, pyproj 3.7.2 (the workspace's versions are not recorded).
