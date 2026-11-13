# Plate 45: reads, picks and fit (13 November 2026)

Plate 45 (Northside north of Chase Avenue; Hamilton Avenue through the middle, Spring Grove Cemetery on the east).
Six strips, each read twice (`picks22_reads/22-45`, `picks22_reads/README.md`).

| | |
|---|---|
| Crossings read (A / B) | 152 / 164 with both streets named |
| Picks (both reads within 60 px) | 127 across the strips, overlaps counted twice |
| Not agreed | 61 |
| Matched to OSM | 73 |
| Controls | 70 |
| Name-seeded fit, leave-one-out | 3.27 m (tps1, rms 1.92 m) |
| Rule 12 spline, held-out | 3.27 m (max 8.23 m, lambda 1) |

Dropped by the fit's tests: Chase & Virginia (two picks, 25.9 m and 6.9 m), Glen Parker & Thompson Heights (6.9 m).

No applied 1922 plate touches plate 45, so there are no ties and no plate-plate seams. Its neighbours are 1904
frames (not bent onto it), `reports/2026-11-13_seams_newplates_45`:

| 1904 frame | Crossings | Median | Max |
|---|---|---|---|
| 619 | 3 | 5.51 m | 10.88 m |
| 620 | 5 | 5.33 m | 10.79 m |
| 621 | 6 | 5.04 m | 5.62 m |
| 622 | 3 | 4.99 m | 5.64 m |
| 623 | 3 | 5.72 m | 7.04 m |
| 625 | 2 | 0.95 m | 1.53 m |
| 626 | 1 | 0.59 m | 0.59 m |
| 627i | 1 | 1.08 m | 1.08 m |
| 627m | 2 | 3.08 m | 5.65 m |
| 628m | 1 | 0.33 m | 0.33 m |
| 629 | 6 | 4.41 m | 10.68 m |
| 630 | 5 | 5.13 m | 8.02 m |
| 631 | 2 | 5.48 m | 8.17 m |
| 632 | 8 | 4.86 m | 6.69 m |
| 633 | 7 | 4.46 m | 5.66 m |
| 634 | 6 | 3.56 m | 6.00 m |
| 635 | 5 | 4.94 m | 6.71 m |

Gate: held-out under 5 m, yes; existing seams untouched (no applied model changed). `cufp/45/fwd_complete.pkl` is
written. Plate 45 is not built: it lies over the Northside 1904 frames, whose streets Ben has edited.
