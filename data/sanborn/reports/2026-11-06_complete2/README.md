# Complete-control fit, second pass, 2026-11-06

As `reports/2026-11-06_complete` with three changes (`tools/sanborn/joint/complete2.py`): the thin-plate part of each plate's spline damped to its affine part over 300 px outside the convex hull of its controls; 37L and 37R with the page-curl pre-correction under their splines, judged as one sheet; everything else as before. Models beside the old ones (`fwd_complete2.pkl`); **guard failed: not applied**.

| Plate | Controls | Hand | New | Dropped (rule 4) | Smoothing | Own rms m | Held-out before m | Held-out after m | Change | Max corner move m | Ties |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 22-34L | 17 | 16 | 1 | 0 | 10.0 | 3.97 | 4.57 | 5.05 | +0.48 | 9.13 | 9 |
| 22-37L | 24 | 20 | 4 | 0 | 1.0 | 3.75 | 5.34 | 6.71 | +1.37 | 39.5 | 12 |
| 22-37R | 18 | 15 | 3 | 0 | 0.3 | 5.73 | 6.28 | 8.26 | +1.98 | 15.03 | 16 |
| 22-34R | 49 | 49 | 0 | 0 | 1.0 | 2.28 | 3.91 | 3.63 | -0.29 | 17.06 | 13 |
| 22-16R | 22 | 15 | 7 | 0 | 3.0 | 2.16 | 5.52 | 4.58 | -0.94 | 20.22 | 5 |
| 22-35N | 37 | 30 | 7 | 1 | 3.0 | 2.34 | 3.33 | 3.37 | +0.03 | 8.96 | 12 |
| 22-38 | 69 | 59 | 10 | 4 | 3.0 | 3.08 | 4.55 | 4.53 | -0.02 | 23.58 | 16 |
| 22-66 | 138 | 96 | 42 | 7 | 3.0 | 2.35 | 3.48 | 3.21 | -0.27 | 17.51 | 31 |
| 22-67 | 105 | 69 | 36 | 2 | 3.0 | 2.65 | 3.96 | 3.85 | -0.11 | 23.99 | 32 |
| 22-68 | 86 | 68 | 18 | 1 | 3.0 | 2.34 | 3.49 | 3.31 | -0.19 | 13.71 | 33 |
| 22-69 | 65 | 41 | 24 | 3 | 3.0 | 3.16 | 4.62 | 4.22 | -0.41 | 45.39 | 42 |
| 22-70 | 89 | 73 | 16 | 3 | 3.0 | 2.38 | 4.21 | 3.32 | -0.90 | 17.18 | 25 |
| 22-82A | 106 | 94 | 12 | 1 | 0.3 | 1.55 | 4.11 | 3.71 | -0.41 | 24.58 | 25 |
| 22-83A | 42 | 40 | 2 | 1 | 0.1 | 1.06 | 4.56 | 3.65 | -0.91 | 36.08 | 11 |
| 22-75 | 64 | 47 | 17 | 0 | 3.0 | 2.88 | 4.65 | 4.35 | -0.30 | 18.28 | 28 |
| 22-76 | 129 | 117 | 12 | 3 | 3.0 | 2.41 | 3.4 | 3.37 | -0.03 | 57.2 | 24 |
| 22-26A | 58 | 49 | 9 | 2 | 1.0 | 1.69 | 3.58 | 3.21 | -0.37 | 26.56 | 13 |
| 22-26B | 16 | 11 | 5 | 0 | 3.0 | 1.7 | 3.49 | 3.25 | -0.24 | 12.52 | 0 |
| 22-29 | 78 | 71 | 7 | 2 | 1.0 | 1.62 | 2.84 | 2.68 | -0.17 | 8.36 | 25 |
| 22-31 | 46 | 31 | 15 | 1 | 1.0 | 2.46 | 4.64 | 4.26 | -0.38 | 12.65 | 25 |
| 22-33 | 83 | 62 | 21 | 0 | 1.0 | 2.39 | 4.08 | 3.79 | -0.30 | 15.89 | 23 |

37L + 37R as one sheet (every control of both): held-out 5.76 -> 7.42 m.

- 22-37L curl (right edge): s(u) px at u = 0, 200, 500, 1000, 2000, 4000: -6.5, -6.5, -6.5, -6.5, -5.7, 0.0; k -0.9
- 22-37R curl (left edge): s(u) px at u = 0, 200, 500, 1000, 2000, 4000: -22.1, -6.0, -2.0, -0.0, -0.0, 0.0; k -0.9

Gutter gap (37L/37R, 206 pairs at weight 3.0): median 27.59 -> 0.43 m, 90% 28.97 -> 1.22 m, max 32.17 -> 2.53 m.

Seams, all plate-plate pairs (hand picks plus complete picks; `reports/2026-11-06_seams_complete2_before` -> `reports/2026-11-06_seams_complete2`): n 210 -> 210, median 3.17 -> 1.66 m, 90% 11.44 -> 4.95 m, max 43.74 -> 31.94 m, over 10 m 24 -> 5, over 20 m 8 -> 2.

## Guard

- 22-37L + 22-37R: sheet held-out 7.42 m against 5.76 m before
- 22-34L: held-out 5.05 m against 4.57 m before
- 22-37L: corner(s) [0, 2, 3] move 20.4, 26.5, 39.5 m
- 22-37R: corner(s) [0, 3] move 10.4, 15.0 m
- 22-34R: corner(s) [0, 1, 2] move 12.2, 13.5, 17.1 m
- 22-16R: corner(s) [1, 2, 3] move 16.8, 20.2, 15.8 m
- 22-35N: held-out 3.37 m against 3.33 m before
- 22-38: corner(s) [0, 1, 2, 3] move 23.6, 12.3, 18.0, 18.1 m
- 22-66: corner(s) [0, 1, 2, 3] move 11.3, 17.5, 15.8, 13.2 m
- 22-67: corner(s) [0, 1, 2, 3] move 24.0, 10.8, 13.9, 11.8 m
- 22-68: corner(s) [2] move 13.7 m
- 22-69: corner(s) [0, 1, 2, 3] move 35.2, 44.2, 45.4, 28.6 m
- 22-70: corner(s) [1, 2, 3] move 17.2, 15.6, 13.6 m
- 22-82A: corner(s) [0, 1, 3] move 22.2, 18.1, 24.6 m
- 22-83A: corner(s) [0, 1, 2, 3] move 22.1, 21.2, 30.4, 36.1 m
- 22-75: corner(s) [0, 1, 2, 3] move 13.3, 17.2, 18.3, 11.4 m
- 22-76: corner(s) [0, 1, 2, 3] move 48.0, 49.3, 19.7, 57.2 m
- 22-26A: corner(s) [0, 1, 2, 3] move 24.6, 17.9, 15.6, 26.6 m
- 22-26B: corner(s) [0, 2] move 12.5, 11.3 m
- 22-31: corner(s) [1, 2] move 10.4, 12.7 m
- 22-33: corner(s) [0, 1, 2, 3] move 13.2, 14.7, 15.5, 15.9 m

Ties: 210 (68 involve a complete pick); `ties.csv` before and after each.

