# Local fit again (after the round-3 re-read), 2026-11-06

Ben's ruling (6 November): the five plates (33, 34R, 37L, 37R, 38) fitted together again, the other 16 fixed, 37L and 37R one sheet at the gutter, with the re-read picks in place of the old ones and the wrong matches dropped. The 37L and 37R corrections are affine only; 33, 34R and 38 are chosen by held-out error. Method: `tools/sanborn/joint/local2.py` (its docstring). Nothing is applied: the new models sit beside the old ones (`fwd_local2.pkl`, `cuf38/fwd38_local2.pkl`).

Re-read picks used: all 11 of round 3 were confirmed (none moved more than 3.8 m, none a wrong match), so no control was dropped and no plate's own model was rebuilt; the re-read pixel positions stand in for the old ones. Round-1 re-reads of 37L/37R, 37R/38 and 35N/38 crossings stand in for their ties too.

48 ties, 206 gutter pairs. Gutter gap (the same paper point on both halves): median 27.59 m, max 32.17 m before; median 4.72 m, max 12.52 m after.

## Part 3 check

- Every plate's own control rms within 0.3 m of before: **no** (worse: 22-37L, 22-37R)
- Plate-plate seam median across the five falls: **no** (4.54 to 5.49 m)
- Plate-plate seam 90% across the five falls: **yes** (20.93 to 13.91 m)
- So Part 3 **does not** go ahead (stop after Part 2).

"Before" is each plate's own model on the same controls (the re-read pixel positions); "rms, old controls" is the first local fit's before. Seams before: the plates' own models with the re-read picks and the wrong matches dropped (`reports/2026-11-06_seams_reread3`); after: the new models (`reports/2026-11-06_seams_local2`). "Across the five": every plate-plate seam a fitted plate takes part in.

## Per plate

| Plate | Own model | Correction | Controls | Rms, old controls | Rms before | Rms after | Change | Held-out before | Held-out after | Max corner move m | Median control move m | Ties |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 22-33 | tps0.3 | affine | 62 | 1.44 | 1.44 | 1.54 | +0.10 | 3.67 | 3.76 | 1.26 | 0.36 | 14 |
| 22-34R | tps0.3 | affine | 49 | 1.44 | 1.44 | 1.62 | +0.18 | 3.91 | 4.07 | 3.41 | 0.63 | 13 |
| 22-37L | tps30 | affine | 20 | 2.97 | 2.95 | 14.14 | +11.19 **worse** | 4.67 | 15.14 | 45.22 | 11.28 | 12 |
| 22-37R | tps0.3 | affine | 15 | 1.02 | 1.03 | 18.6 | +17.57 **worse** | 5.9 | 21.06 | 79.3 | 13.76 | 16 |
| 22-38 | tps1 | affine | 63 | 2.29 | 2.29 | 2.4 | +0.11 | 4.75 | 4.93 | 2.31 | 0.5 | 12 |

## The controls of the plates that got worse

Each control's distance from its OSM crossing, before and after (all of them; `controls.csv` has all five plates).

| Plate | Crossing | Pixel | Before m | After m | Moved m |
|---|---|---|---|---|---|
| 22-37L | Beekman Avenue & Fricke Road | (2594, 6378) | 3.14 | 30.83 | 33.07 |
| 22-37L | Dawson Avenue & Ralston Avenue | (4080, 3558) | 4.89 | 22.45 | 19.63 |
| 22-37L | Roll Avenue & Ralston Avenue | (4490, 3558) | 2.68 | 22.25 | 20.11 |
| 22-37L | Borden Street & Dreman Avenue | (3572, 2612) | 1.52 | 15.47 | 14.09 |
| 22-37L | Follett Avenue (south of Dreman) & Dreman Avenue | (4889, 2626) | 0.55 | 15.46 | 15.65 |
| 22-37L | Roll Avenue & Dreman Avenue | (4490, 2622) | 0.41 | 14.98 | 15.17 |
| 22-37L | Dawson Avenue & Dreman Avenue | (4080, 2620) | 0.5 | 14.38 | 14.7 |
| 22-37L | Beekman Avenue & Dreman Avenue | (2699, 2576) | 5.74 | 14.29 | 12.95 |
| 22-37L | Llewellyn Avenue & Dreman Avenue | (3136, 2586) | 0.67 | 13.68 | 13.47 |
| 22-37L | Dirr Street & Dreman Avenue | (5418, 2630) | 4.13 | 12.17 | 16.3 |
| 22-37L | Borden Street & Weber Street | (3578, 1722) | 2.53 | 11.85 | 9.61 |
| 22-37L | Cass Avenue & Faraday Road | (942, 2254) | 3.67 | 10.35 | 9.57 |
| 22-37L | Cherry Street & Burgoyne Street | (5910, 646) | 2.31 | 9.1 | 6.84 |
| 22-37L | Borden Street & Townsend Street | (3580, 761) | 3.35 | 8.84 | 5.51 |
| 22-37L | Tappan Avenue & Powers Street | (526, 350) | 3.08 | 6.83 | 5.75 |
| 22-37L | Cass Avenue & Powers Street | (948, 356) | 0.89 | 6.31 | 5.42 |
| 22-37L | Cherry Street & Powers Street | (5902, 340) | 0.92 | 5.81 | 5.53 |
| 22-37L | Herron Avenue & Powers Street | (1372, 365) | 0.38 | 5.37 | 5.13 |
| 22-37L | Turrill Street & Powers Street | (6259, 318) | 5.52 | 5.22 | 5.72 |
| 22-37L | Sylvan Avenue & Powers Street | (2248, 380) | 1.2 | 3.62 | 4.7 |
| 22-37R | Ludlow Avenue & Bowdle Place | (4189, 3070) | 0.4 | 46.36 | 46.73 |
| 22-37R | Bless Avenue & Streng Street | (2776, 2968) | 0.62 | 29.97 | 29.47 |
| 22-37R | Comfort Street & Sassafras Street | (3288, 7169) | 0.65 | 22.49 | 22.84 |
| 22-37R | Colerain Avenue & Arlington Street | (2824, 6764) | 0.89 | 18.86 | 18.41 |
| 22-37R | Spring Grove Avenue & Powers Street | (1317, 313) | 0.59 | 17.69 | 17.3 |
| 22-37R | Colerain Avenue & Sassafras Street | (2835, 7164) | 1.28 | 17.58 | 17.56 |
| 22-37R | Apple Street & Powers Street | (1047, 313) | 0.64 | 14.37 | 13.76 |
| 22-37R | Spring Grove Avenue & Burgoyne Street | (1231, 665) | 1.51 | 13.48 | 14.99 |
| 22-37R | Turrill Street & Powers Street | (667, 316) | 2.08 | 10.56 | 8.72 |
| 22-37R | Spring Grove Avenue & Arlington Street | (1420, 6731) | 0.22 | 7.28 | 7.07 |
| 22-37R | Spring Grove Avenue & Brashears Street | (1274, 5336) | 0.34 | 5.74 | 5.45 |
| 22-37R | Spring Grove Avenue & Adelaide Street | (1404, 5923) | 0.7 | 5.61 | 6.06 |
| 22-37R | Cherry Street & Powers Street | (319, 336) | 0.94 | 4.49 | 4.09 |
| 22-37R | Spring Grove Avenue & Ralston Avenue | (787, 3314) | 0.69 | 4.03 | 3.38 |
| 22-37R | Cherry Street & Burgoyne Street | (321, 642) | 1.76 | 1.71 | 3.07 |

## Why 37L and 37R fail

- **What an affine correction can do:** the two halves' own models agree at the top of the gutter (Cherry & Powers, Cherry & Burgoyne, within about 1-2 m of OSM on both) and disagree by about 25 m in the middle of it (Groub, Geringer, Ralston). An affine correction moves a whole half by a straight-line rule, so it cannot open a gap at the top and close one of 25 m in the middle.
- **What the sheet constraint does:** it outweighs the controls (206 gutter pairs at weight 25, against 20 and 15 controls), so to bring the gutter closer (median gap 27.6 m to 4.7 m) it drags both halves off their own controls. 37L reaches 14.1 m rms, 37R 18.6 m, and 37R's far corner moves 79 m.
- **Which controls move furthest:** those far from the gutter. On 37R: Ludlow & Bowdle 46 m, Bless & Streng 30 m, Comfort & Sassafras 22 m. On 37L: Beekman & Fricke 31 m, Dawson & Ralston and Roll & Ralston 22 m. The full list is above.
- **The first local fit:** it let 37L take a thin-plate correction, closed the gap to 0.14 m, and still left 37R 1.16 m worse. So closing the gutter needs a correction that bends along the gutter, but no control lies along the gutter below y about 700 to check one against. Whatever shape a fit gives the halves there is not tested by any control.

## Seams

| Plate-plate seams | | Shared | Median m | 90% m | Max m | > 10 m | > 20 m |
|---|---|---|---|---|---|---|---|
| touching the five | before | 48 | 4.54 | 20.93 | 25.69 | 11 | 6 |
| touching the five | after | 47 | 5.49 | 13.91 | 25.44 | 11 | 2 |
| among the five | before | 19 | 7.47 | 25.21 | 25.69 | 9 | 6 |
| among the five | after | 18 | 10.2 | 18.23 | 25.44 | 9 | 2 |
| all plates | before | 142 | 2.75 | 10.02 | 30.01 | 15 | 7 |
| all plates | after | 141 | 3.06 | 10.1 | 30.01 | 15 | 3 |
| plate-1904, the five | before | 304 | 0.24 | 4.34 | 35.09 | 15 | 6 |
| plate-1904, the five | after | 302 | 1.7 | 14.71 | 35.0 | 48 | 12 |

## Ties, widest after the fit

| Plates | Crossing | Before m | After m | Weight |
|---|---|---|---|---|
| 22-37R / 22-38 | Ludlow Avenue & Lafayette Avenue | 21.29 | 46.42 | 0.129 |
| 22-33 / 22-34R | Marshall Avenue & Garrard Avenue | 25.15 | 25.44 | 0.236 |
| 22-34R / 22-37R | Comfort Street & Sassafras Street | 0.19 | 21.79 | 0.275 |
| 22-34R / 22-38 | Vermont Avenue & Bates Alley | 20.77 | 16.71 | 0.359 |
| 22-34R / 22-37R | Colerain Avenue & Sassafras Street | 1.28 | 16.14 | 0.372 |
| 22-34R / 22-38 | Vermont Avenue & Stock Avenue | 17.82 | 13.96 | 0.43 |
| 22-37L / 22-37R | Turrill Street & Powers Street | 3.85 | 13.87 | 25.0 (sheet) |
| 22-35N / 22-38 | West McMicken Avenue & Dixmyth Avenue | 14.62 | 12.73 | 0.472 |
| 22-37L / 22-37R | Colerain Avenue & Elmore Street | 0.43 | 12.69 | 25.0 (sheet) |
| 22-37L / 22-37R | Cherry Street & Burgoyne Street | 1.49 | 10.8 | 25.0 (sheet) |
| 22-37L / 22-37R | Colerain Avenue & Dhonau Street | 1.08 | 10.61 | 25.0 (sheet) |
| 22-31 / 22-33 | Queen City Avenue & Garrard Avenue | 10.0 | 10.1 | 0.594 |
| 22-37L / 22-37R | Cherry Street & Powers Street | 0.27 | 9.79 | 25.0 (sheet) |
| 22-37L / 22-37R | Spaeth Street & Dreman Avenue | 11.9 | 9.36 | 25.0 (sheet) |
| 22-37L / 22-37R | Colerain Avenue & Burgoyne Street | 5.67 | 9.28 | 25.0 (sheet) |

Choice trail (33, 34R, 38): affine kept. Computed with numpy 2.4.2, scipy 1.18.1.
