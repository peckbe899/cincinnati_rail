# Seam report, 2026-11-06

Plate models: each plate's own (fwd.pkl, Ben georeference for 35N).

Read only: every street crossing that two 1922 plates, or a 1922 plate and a 1904 frame, both show, and how far apart the two copies sit on the page. Nothing was fitted, rebuilt or changed. Method: `tools/sanborn/seams.py` (its docstring); matched by street names within 45 m. Files: `seams.csv` (every pair), `per_pair.csv` (by plate and frame), `seams.json` (all of it, with the sha256 of every file read).

Read: 21 plates on the 1922 layer (2281 crossings), 235 1904 deck and north frames (2298 crossings), 142 1904 basin frames (2446 crossings).

## Summary

| Seam | Source pairs | Shared crossings | Median m | RMS m | 90% m | Max m | > 5 m | > 10 m | > 20 m | Same names 45-150 m |
|---|---|---|---|---|---|---|---|---|---|---|
| plate-plate | 31 | 210 | 3.17 | 7.72 | 11.44 | 43.74 | 68 | 24 | 8 | 1 |
| plate-1904 | 157 | 586 | 0.55 | 6.82 | 8.0 | 38.03 | 98 | 53 | 25 | 1 |

Plate against 1904, by how the frame is drawn:

| 1904 frames | Shared crossings | Frames | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| deck/north, bent onto 1922 (lph/tps.pkl) | 481 | 88 | 0.28 | 4.37 | 38.03 |
| deck/north, not bent | 105 | 23 | 5.24 | 24.95 | 35.09 |
| basin (sbg/fit/tf.json) | 0 | 0 | - | - | - |

## Plate against plate

| Plate | Plate | Shared | Median m | Max m | Mean shift E, N m |
|---|---|---|---|---|---|
| 22-16R | 22-34R | 2 | 4.82 | 5.76 | -0.8, -0.5 |
| 22-16R | 22-35N | 3 | 3.97 | 4.91 | +2.4, -0.1 |
| 22-26A | 22-29 | 13 | 1.57 | 4.16 | -0.1, -0.5 |
| 22-29 | 22-31 | 12 | 2.1 | 6.26 | -0.5, +1.3 |
| 22-31 | 22-33 | 13 | 2.72 | 10.0 | +0.2, +0.5 |
| 22-33 | 22-34L | 9 | 5.42 | 10.02 | +0.6, -2.5 |
| 22-33 | 22-34R | 1 | 25.15 | 25.15 | +17.0, -18.6 |
| 22-34R | 22-35N | 5 | 3.09 | 3.67 | +0.7, +1.0 |
| 22-34R | 22-37R | 3 | 1.28 | 11.39 | -0.5, -4.2 |
| 22-34R | 22-38 | 2 | 19.3 | 20.77 | +0.0, +19.3 |
| 22-35N | 22-38 | 4 | 3.67 | 14.62 | -1.1, +2.2 |
| 22-37L | 22-37R | 12 | 6.0 | 25.69 | +6.5, -1.7 |
| 22-37R | 22-38 | 1 | 21.29 | 21.29 | -8.2, +19.6 |
| 22-38 | 22-66 | 1 | 1.6 | 1.6 | -1.0, +1.3 |
| 22-38 | 22-68 | 8 | 9.3 | 43.74 | +6.3, -0.7 |
| 22-66 | 22-67 | 10 | 2.06 | 8.1 | -0.4, -0.0 |
| 22-66 | 22-68 | 10 | 4.06 | 9.55 | -1.0, +3.0 |
| 22-66 | 22-69 | 10 | 6.22 | 13.39 | -0.6, +3.1 |
| 22-67 | 22-69 | 8 | 8.82 | 30.01 | +1.6, +6.2 |
| 22-67 | 22-70 | 14 | 1.62 | 7.85 | -0.3, -0.3 |
| 22-68 | 22-69 | 11 | 3.46 | 5.42 | +0.8, -1.0 |
| 22-68 | 22-75 | 4 | 3.19 | 5.6 | -1.4, -0.8 |
| 22-69 | 22-70 | 7 | 4.14 | 8.56 | +1.7, -0.8 |
| 22-69 | 22-75 | 6 | 5.5 | 16.13 | +2.9, +4.7 |
| 22-70 | 22-75 | 3 | 2.69 | 12.12 | -0.2, +4.6 |
| 22-70 | 22-76 | 1 | 18.17 | 18.17 | +1.6, +18.1 |
| 22-75 | 22-76 | 9 | 2.29 | 14.24 | -2.2, -0.3 |
| 22-75 | 22-82A | 6 | 3.11 | 9.83 | +3.1, -0.2 |
| 22-76 | 22-82A | 11 | 1.82 | 4.06 | +0.9, +0.3 |
| 22-76 | 22-83A | 3 | 1.9 | 5.36 | +0.6, -1.3 |
| 22-82A | 22-83A | 8 | 1.58 | 7.31 | -0.5, +1.3 |

## Plate against 1904 frames, by plate

| Plate | Frames | Shared | Median m | 90% m | Max m |
|---|---|---|---|---|---|
| 22-16R | 11 | 34 | 0.23 | 5.78 | 12.50 |
| 22-26A | 7 | 29 | 1.45 | 4.24 | 6.10 |
| 22-29 | 16 | 53 | 2.68 | 11.99 | 38.03 |
| 22-31 | 14 | 51 | 6.45 | 26.65 | 34.05 |
| 22-33 | 12 | 37 | 4.19 | 16.77 | 35.09 |
| 22-34L | 2 | 8 | 0.13 | 5.47 | 11.34 |
| 22-34R | 23 | 139 | 0.25 | 1.37 | 13.65 |
| 22-35N | 20 | 52 | 0.31 | 3.97 | 28.60 |
| 22-37L | 9 | 52 | 0.10 | 1.36 | 6.16 |
| 22-37R | 10 | 36 | 0.17 | 3.50 | 11.43 |
| 22-38 | 14 | 47 | 0.40 | 4.50 | 21.27 |
| 22-66 | 13 | 38 | 0.29 | 5.54 | 9.14 |
| 22-67 | 4 | 7 | 0.36 | 1.32 | 1.67 |
| 22-68 | 2 | 3 | 2.95 | 11.88 | 14.11 |

## Widest 20, plate against plate

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 43.7 | 22-38 | 22-68 | Beldare Avenue & Vine Street | +43.0, -8.0 |
| 30.0 | 22-67 | 22-69 | Gilbert Avenue & Woodburn Avenue | +5.1, +29.6 |
| 25.7 | 22-37L | 22-37R | Groub Street & Ralston Avenue | +22.1, -13.2 |
| 25.5 | 22-37L | 22-37R | Geringer Street & Ralston Avenue | +21.6, -13.5 |
| 25.1 | 22-33 | 22-34R | Marshall Avenue & Garrard Avenue | +17.0, -18.6 |
| 24.1 | 22-37L | 22-37R | Geringer Street & Groub Street | +20.7, -12.3 |
| 21.3 | 22-37R | 22-38 | Ludlow Avenue & Lafayette Avenue | -8.2, +19.6 |
| 20.8 | 22-34R | 22-38 | Vermont Avenue & Bates Alley | -0.7, +20.8 |
| 18.2 | 22-70 | 22-76 | Elsmere Avenue & Lexington Avenue | +1.6, +18.1 |
| 17.8 | 22-34R | 22-38 | Vermont Avenue & Stock Avenue | +0.7, +17.8 |
| 16.2 | 22-67 | 22-69 | Harvard Avenue & Gilbert Avenue | +0.8, +16.1 |
| 16.1 | 22-69 | 22-75 | Lexington Avenue & Magill Avenue | -5.0, +15.3 |
| 14.6 | 22-35N | 22-38 | West McMicken Avenue & Dixmyth Avenue | -3.0, +14.3 |
| 14.3 | 22-67 | 22-69 | Gilbert Avenue & Walter Avenue | -14.3, -0.4 |
| 14.2 | 22-75 | 22-76 | Ivanhoe Avenue & Montgomery Road | -9.0, -11.1 |
| 13.5 | 22-38 | 22-68 | Erkenbrecher Avenue & Vine Street | -13.4, -1.0 |
| 13.4 | 22-66 | 22-69 | Wehrman Street & Gilbert Avenue | -13.2, -1.9 |
| 13.4 | 22-69 | 22-75 | Brewster Avenue & Newton Avenue | +10.0, +8.9 |
| 12.1 | 22-70 | 22-75 | Montgomery Road & Brewster Avenue | +3.4, +11.6 |
| 11.9 | 22-37L | 22-37R | Spaeth Street & Dreman Avenue | +11.8, +1.2 |

## Widest 20, plate against 1904

| m | Plate | Other | Crossing | dE, dN m |
|---|---|---|---|---|
| 38.0 | 22-29 | 1904 466 (deck/north, bent) | Warsaw Avenue & Wilder Avenue | -3.6, -37.9 |
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
| 25.5 | 22-31 | 1904 221 (deck/north) | Duck Street & Garrard Avenue | +22.2, +12.6 |
| 25.2 | 22-33 | 1904 272 (deck/north, bent) | Marshall Avenue & Garrard Avenue | +17.2, -18.4 |
| 25.1 | 22-33 | 1904 273 (deck/north, bent) | Marshall Avenue & Garrard Avenue | +16.9, -18.6 |
| 25.0 | 22-31 | 1904 222 (deck/north) | Harrison Avenue & Garrard Avenue | +24.2, +6.3 |
| 24.8 | 22-31 | 1904 201 (deck/north) | West Liberty Street & Garrard Avenue | +24.5, +3.9 |
| 24.8 | 22-31 | 1904 221 (deck/north) | Harrison Avenue & Garrard Avenue | +23.8, +7.0 |
| 24.4 | 22-29 | 1904 201 (deck/north) | Garrard Avenue & West Liberty Street | +23.3, +7.3 |
| 24.4 | 22-29 | 1904 57 (deck/north) | Garrard Avenue & Hopkins Street | +16.8, +17.6 |
| 24.2 | 22-29 | 1904 68 (deck/north) | Garrard Avenue & Hopkins Street | +17.0, +17.2 |

## Same street names, 45-150 m apart

Either a seam that wide or two different crossings of the same two streets; not counted above.

- 22-66 / 1904 262: Calhoun Street & Jefferson Avenue, 54.1 m
- 22-69 / 22-75: Herbert Avenue & Montgomery Road, 101.3 m

## Notes

- Plate positions come from the stored forward models (`fwd.pkl`); the page draws the plates through the inverse grids made from them on a 2 m grid, so the drawn position can differ by a fraction of a metre. Plate 35N is Ben's georeference as drawn.
- The 1904 frames bent onto the 1922 plates were bent at these same crossings, so their small distances are by construction.
- Placement checked against the workspace's own `cuf/x1904.json` (same frames, its pre-bend model): identical to 0.0 m on 830 frame crossings and 360 plate crossings.
- Computed with Python 3.12.10, numpy 2.4.2, scipy 1.18.1, pyproj 3.7.2 (the workspace's versions are not recorded).
