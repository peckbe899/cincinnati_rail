# Complete-control fit of the 1922 plates, 2026-11-06

Every plate a thin-plate spline on its complete control set (hand picks plus the crossings read for the complete set), all 21 solved together; method in `tools/sanborn/joint/complete.py`. Models beside the old ones (`fwd_complete.pkl`); **guard failed: not applied**.

| Plate | Controls | Hand | New | Dropped (rule 4) | Smoothing | Own rms m | Held-out before m | Held-out after m | Change | Max corner move m | Ties |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 22-34L | 17 | 16 | 1 | 0 | 3.0 | 2.96 | 4.57 | 4.21 | -0.36 | 7.68 | 9 |
| 22-37L | 24 | 20 | 4 | 0 | 10.0 | 4.84 | 5.34 | 6.75 | +1.41 | 18.93 | 12 |
| 22-37R | 18 | 15 | 3 | 0 | 3.0 | 5.83 | 6.28 | 7.75 | +1.47 | 15.01 | 16 |
| 22-34R | 49 | 49 | 0 | 0 | 1.0 | 2.27 | 3.91 | 3.77 | -0.15 | 12.08 | 13 |
| 22-16R | 22 | 15 | 7 | 0 | 3.0 | 2.12 | 5.52 | 4.56 | -0.96 | 9.24 | 5 |
| 22-35N | 37 | 30 | 7 | 1 | 1.0 | 1.91 | 3.33 | 3.24 | -0.10 | 7.56 | 12 |
| 22-38 | 69 | 59 | 10 | 4 | 3.0 | 2.9 | 4.55 | 4.17 | -0.38 | 18.87 | 16 |
| 22-66 | 138 | 96 | 42 | 7 | 1.0 | 1.86 | 3.48 | 3.04 | -0.44 | 7.37 | 31 |
| 22-67 | 105 | 69 | 36 | 2 | 3.0 | 2.62 | 3.96 | 3.83 | -0.13 | 11.08 | 32 |
| 22-68 | 86 | 68 | 18 | 1 | 3.0 | 2.3 | 3.49 | 3.25 | -0.25 | 4.22 | 33 |
| 22-69 | 65 | 41 | 24 | 3 | 1.0 | 2.42 | 4.62 | 3.83 | -0.80 | 12.28 | 42 |
| 22-70 | 89 | 73 | 16 | 3 | 3.0 | 2.38 | 4.21 | 3.31 | -0.91 | 18.01 | 25 |
| 22-82A | 106 | 94 | 12 | 1 | 0.3 | 1.58 | 4.11 | 3.75 | -0.36 | 17.39 | 25 |
| 22-83A | 42 | 40 | 2 | 1 | 0.1 | 1.1 | 4.56 | 4.53 | -0.03 | 24.12 | 11 |
| 22-75 | 64 | 47 | 17 | 0 | 10.0 | 3.44 | 4.65 | 4.42 | -0.23 | 4.18 | 28 |
| 22-76 | 129 | 117 | 12 | 3 | 3.0 | 2.42 | 3.4 | 3.39 | -0.02 | 6.83 | 24 |
| 22-26A | 58 | 49 | 9 | 2 | 1.0 | 1.68 | 3.58 | 3.19 | -0.39 | 13.15 | 13 |
| 22-26B | 16 | 11 | 5 | 0 | 3.0 | 1.7 | 3.49 | 3.25 | -0.24 | 2.89 | 0 |
| 22-29 | 78 | 71 | 7 | 2 | 1.0 | 1.58 | 2.84 | 2.63 | -0.21 | 3.62 | 25 |
| 22-31 | 46 | 31 | 15 | 1 | 3.0 | 3.02 | 4.64 | 4.33 | -0.32 | 6.16 | 25 |
| 22-33 | 83 | 62 | 21 | 0 | 3.0 | 2.99 | 4.08 | 3.99 | -0.09 | 12.11 | 23 |

Gutter gap (37L/37R, 206 pairs at weight 3.0): median 27.59 -> 0.45 m, 90% 28.97 -> 1.22 m, max 32.17 -> 2.14 m.

Seams, all plate-plate pairs (hand picks plus complete picks; `reports/2026-11-06_seams_complete_before` -> `reports/2026-11-06_seams_complete`): n 210 -> 210, median 3.17 -> 1.5 m, 90% 11.44 -> 4.35 m, max 43.74 -> 34.47 m, over 10 m 24 -> 6, over 20 m 8 -> 2.

## Guard

- 22-37L: held-out 6.75 m against 5.34 m before
- 22-37L: corner(s) [2, 3] move 18.9, 11.2 m with no control within 500 px
- 22-37R: held-out 7.75 m against 6.28 m before
- 22-37R: corner(s) [3] move 15.0 m with no control within 500 px
- 22-34R: corner(s) [3] move 12.1 m with no control within 500 px
- 22-38: corner(s) [0, 3] move 18.9, 12.1 m with no control within 500 px
- 22-67: corner(s) [2] move 11.1 m with no control within 500 px
- 22-69: corner(s) [2] move 12.3 m with no control within 500 px
- 22-70: corner(s) [1, 2] move 12.7, 18.0 m with no control within 500 px
- 22-82A: corner(s) [0] move 17.4 m with no control within 500 px
- 22-83A: corner(s) [1] move 24.1 m with no control within 500 px
- 22-26A: corner(s) [2] move 13.2 m with no control within 500 px
- 22-33: corner(s) [1] move 12.1 m with no control within 500 px

Ties: 210 (68 involve a complete pick); `ties.csv` before and after each.

