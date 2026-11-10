# Plate 40 with Ben's street names (9 November 2026): gate not passed, applied model unchanged

Ben's names, now in `cufp/config.json` (plate 40): Carthage = Vine, Canal = Baker Place, Ammen = Salway Street, Este
Avenue at Spring Grove = Kings Run Drive at Spring Grove. Donnell is gone (`moved`); Beech & Spring Grove is not where
it was (`force_out`); Railroad & Beech stays.

The names add three controls (Spring Grove & Ammen, Ammen & Hope, Este & Spring Grove): 42 in all. Held-out error
with them is 5.73 m (max 16.44 m), over the 5 m gate, so `cufp/40/fwd_complete.pkl` was not rewritten. It is still
the 39-control model of `reports/2026-11-09_newplates_40` (held-out 4.52 m). `cufp/40/fwd.pkl` is the 42-control
name-seeded fit.

Where the new controls land against the 39-control model:

| Crossing | Offset east, north (m) | Distance |
|---|---|---|
| Este (Kings Run) & Spring Grove | 14.6, 8.2 | 16.8 m |
| Spring Grove & Ammen (Salway) | -7.5, -12.2 | 14.4 m |
| Ammen (Salway) & Hope | -3.6, -7.7 | 8.4 m |

Held-out error by control set (name-seeded spline, best smoothing):

| Controls | n | Held-out | Max |
|---|---|---|---|
| All of Ben's names | 42 | 5.76 m | 16.4 m |
| Without Este & Spring Grove | 41 | 5.10 m | 14.1 m |
| Without the two Ammen crossings | 40 | 5.43 m | 15.4 m |
| Without Este & Spring Grove and Spring Grove & Ammen | 40 | 4.82 m | 12.6 m |
| Without all three (the applied model's set) | 39 | 4.58 m | 11.4 m |

Largest held-out errors with all 42: Este & Spring Grove 17.1 m, Beech & Railroad 15.1 m, Spring Grove & Mitchell
14.8 m, Spring Grove & Ammen 11.0 m, Spring Grove & Durham 8.1 m, Spring Grove & Clifton 7.3 m. Five of the six are
on Spring Grove Avenue.
