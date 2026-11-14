# Plate 80 (St. Bernard) onto the applied 1922 layer, 13-14 November 2026: guided reads

The first pass, read blind in six strips, gave 23 controls and 6.33 m held-out and was not built
(`reports/2026-11-13_newplates_80_blind`). This pass uses guided reads (`tools/sanborn/guided/`,
`picks22_guided/22-80/`): each of the 116 crossings on today's map that fall on the plate, projected through the
first fit, shown to two readers as a full-size crop with both street names.

| | |
|---|---|
| Today's crossings on the plate | 116 (78 inside, 38 along the plate's edge: Mitchell Avenue, Carthage Avenue) |
| Found by both readers | 90 (same verdict on 115 of 116) |
| The two readers apart | median 3.1 px, 90% within 9.3 px |
| Picks | 80 plate points |
| Not drawn in 1922 (both readers) | 25: cemetery, estates, the canal where City Park Drive runs, Martin, Wess Park Drive, Railroad Avenue |
| Controls | 73 |
| Name-seeded fit, leave-one-out | 1.89 m (tps1); affine 2.48 m |
| Rule 12 spline, held-out | 1.87 m (max 4.77 m, lambda 1, not damped; corners move up to 5.9 m) |
| Ties with plate 40 | 7 on Carthage Avenue: 0.86 to 3.28 m, median 1.80 m |

Kept out of the fit but drawn (`cufp/config.json` "guided_not_controls"): 80-082 and 80-116 (plate corners), 80-097
(Washington at Carthage's bend), 80-112 and 80-115 (Rose Hill / Red Bud, 12-13 m from the fit of the interior
crossings). Dropped altogether ("guided_drop"): 80-096, McClelland at Carthage, 40 m off: McClelland did not reach
Carthage in 1922. Tower & Delmar is a jog; both legs are in the street set, neither is a control.

The first guided build (13 November, 53 controls) left out every crossing within 160 px of the plate's edge, so Mitchell
Avenue and the streets south of Delmar were not drawn, and Rose Hill Avenue and Rose Hill Lane were run together into
one diagonal. Both are corrected here.

The east half (cemetery) has 3 controls and is the least certain part of the plate.
