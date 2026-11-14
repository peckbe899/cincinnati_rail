# Plate 80 (St. Bernard), 13 November 2026: gate NOT passed, not built

Two reads per strip, 41 picks (27 not agreed); fit seeded from street names (no GeoTIFF). fit.py now also reads the Norwood OSM extract for 80, and Carthage Avenue is aliased to Vine Street (as on plate 40).

| | |
|---|---|
| Matched to OSM / controls | 24 / 23 (Delmar & Zetta dropped at 6.2 m) |
| Name-seeded fit, leave-one-out | affine 6.38 m (max 11.13); no spline does better (tps100 6.39) |
| Rule 12 spline, held-out | 6.33 m (max 11.23 m, lambda 100) - over 5 m |
| Ties | 2, both with 40 (median 2.81 m) |

The misfit is spread over the plate, not one bad control: nine controls are 7-11 m off on leave-one-out, among them Franklin & Kemper, Mitchell & Zetta, Bertus & Mitchell, Advance & Greenlee, and three on Sullivan. Readers named several avenues from house numbers or from the name printed elsewhere (Tower and Sullivan north of where they are printed, Greenlee and Kemper over their whole length), and several reported 30-50 px scatter between crops. Carthage crossings (Ross, Clay, Albert, Oak) found no OSM crossing within 30 m: Vine Street does not follow the 1922 Carthage line there, or the alias is wrong.

cufp/80/fwd_complete.pkl was written by newplates.py but 80 is not in cuf/plates.py and was not built: nothing on the page changed.
