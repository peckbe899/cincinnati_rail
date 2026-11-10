# Plates 39 and 40 on the applied 1922 layer (Part 2), 2026-11-09

Method as `reports/2026-11-08_newplates` (`tools/sanborn/joint/newplates.py`): each plate a thin-plate spline on its picks matched to OSM, smoothing by exact held-out error, solved together with ties to the applied plates (held fixed). Models `cufp/39/fwd_complete.pkl`, `cufp/40/fwd_complete.pkl`; not built.

| Plate | Controls | Name-seeded fit | Smoothing | Own rms m | Held-out m | Held-out max m | Max corner move m | Ties | Tie partners |
|---|---|---|---|---|---|---|---|---|---|
| 22-39 | 24 | quadratic | 3.0 | 2.36 | 4.85 | 9.93 | 4.99 | 5 | 22-38, 22-40 |
| 22-40 | 29 | tps100 | 100.0 | 5.3 | 6.58 | 15.25 | 1.33 | 1 | 22-39 |

Seams (`reports/2026-11-09_seams_newplates`): existing seams unchanged (the applied plates are held fixed). New: 39 with 38, 4 seams, median 3.25 m, max 5.28 m; 39 with 40, 1 seam, 3.72 m (Kessler Avenue at Mitchell Avenue). Plate 40 shares no crossing with any applied plate.

## Gate

- Held-out under 5 m: 22-39 yes (4.85 m); **22-40 no (6.58 m)**.
- Existing seams: unchanged.

Plate 40 has 69 picks but only 29 controls: 16 picks are on streets OSM no longer has under those names (Carthage Avenue, Ammen, Donnell, Canal), 8 have no OSM crossing within 30 m, 3 were dropped by rule 4, and the spline settles at the stiffest smoothing (100), close to an affine. Not built.
