# Plates 25 and 28 on the applied 1922 layer (Part 2), 2026-11-08

Each plate a thin-plate spline from pixel to world on its complete picks matched to OSM, smoothing by exact held-out error (rule 12); both solved together with ties to every plate they share crossings with, those plates held fixed at their applied models; `tools/sanborn/joint/newplates.py`. Models `cufp/25/fwd_complete.pkl`, `cufp/28/fwd_complete.pkl`.

| Plate | Controls | Name-seeded fit | Smoothing | Damped | Own rms m | Held-out m | Held-out max m | Max corner move m | Ties | Tie partners |
|---|---|---|---|---|---|---|---|---|---|---|
| 22-25 | 23 | tps0.3 | 0.3 | no | 1.1 | 3.29 | 8.6 | 2.6 | 16 | 22-26A, 22-26B, 22-28, 22-29 |
| 22-28 | 95 | tps1 | 0.3 | no | 1.49 | 3.13 | 7.81 | 2.36 | 20 | 22-25, 22-26A, 22-26B, 22-29, 22-31 |

No corner moved more than 10 m from the plate's name-seeded fit, so no damping.

## Seams (`reports/2026-11-08_seams_newplates`, against `reports/2026-11-07_seams_applied`)

| Neighbour | Seams before (n, median m) | Seams after (n, median m) | With 25 (n, median, max m) | With 28 (n, median, max m) |
|---|---|---|---|---|
| 22-26A | 13, 0.62 | 16, 0.64 | 2, 0.9, 1.5 | 1, 1.49, 1.49 |
| 22-26B | 0, None | 5, 0.48 | 4, 0.34, 0.85 | 1, 0.55, 0.55 |
| 22-29 | 24, 0.68 | 33, 0.65 | 1, 0.37, 0.37 | 8, 0.54, 0.86 |
| 22-31 | 17, 1.63 | 18, 1.62 | 0 | 1, 0.71, 0.71 |

25 with 28: 9 seams, median 0.38 m, max 5.84 m (West 8th Street at Wells Street, 5.83 m).

## Gate for Part 3

- Held-out under 5 m on both plates: yes.
- No neighbour's seam median worse: 22-26A WORSE, 22-26B ok, 22-29 ok, 22-31 ok.

**Gate fails on 22-26A: its seam median goes from 0.62 to 0.64 m.** 26A is held fixed, so its 13 existing seams are unchanged; the median rises because its three new seams with 25 (0.90 and 1.50 m) and 28 (1.49 m) lie above it. Part 3 not run.

Ties, before (each plate's name-seeded fit) and after: `ties.csv`.
