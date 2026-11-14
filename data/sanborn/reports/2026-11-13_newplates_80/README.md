# Plate 80 (St. Bernard) onto the applied 1922 layer, 13 November 2026: guided reads

The first pass, read blind in six strips, gave 23 controls and 6.33 m held-out and was not built
(`reports/2026-11-13_newplates_80_blind`). This pass uses guided reads (`tools/sanborn/guided/`,
`picks22_guided/22-80/`): each of the 78 crossings on today's map that fall on the plate, projected through the
first fit, shown to two readers as a full-size crop with both street names.

| | |
|---|---|
| Today's crossings on the plate | 78 |
| Found by both readers | 56 (same verdict on 77 of 78) |
| The two readers apart | median 3.0 px, 90% within 8.2 px |
| Picks (both within 30 px, one per plate point) | 54 |
| Not drawn in 1922 (both readers) | 21: cemetery, estates, the canal where City Park Drive runs |
| Left out | Tower & Delmar: a jog, each reader took a different leg |
| Controls | 53 |
| Name-seeded fit, leave-one-out | 1.92 m (quadratic); affine 2.34 m |
| Rule 12 spline, held-out | 2.10 m (max 5.50 m, lambda 10, damped) |

- Ties: 2, both with plate 40 on Carthage Avenue (Ross 4.19 m, Mitchell 3.28 m). The points on 80 for these are
  blind picks from the first pass, not guided ones.
- The image corners move 11-25 m between the name-seeded quadratic and the spline, so the solve was damped. The
  corners are blank paper; the east half (cemetery) has 3 controls and is the least certain part of the plate.
- The earlier blind picks with no guided pick (22) stay in `sbg/picks22` for the street set, marked "fit": false.
