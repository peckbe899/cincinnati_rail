# Plate 43: reads, picks and fit (13 November 2026)

Plate 43 (Northside west: Colerain Avenue, Wesleyan Cemetery, Hoffner Avenue; drawn at 100 ft to an inch). Six strips,
each read twice (`picks22_reads/22-43`).

| | |
|---|---|
| Crossings read (A / B) | 78 / 78 with both streets named |
| Picks (both reads within 60 px) | 75 across the strips, overlaps counted twice (71 before the avenue below was named) |
| Not agreed | 6 (14 before) |
| Matched to OSM | 33 |
| Controls | 33 |
| Name-seeded fit, leave-one-out | 2.90 m (tps3, rms 1.54 m) |
| Rule 12 spline, held-out | 2.85 m (max 11.18 m, lambda 10) |

Names:
- The plate prints HANIFIELD; some readers wrote Hanifield, some Hanfield. All were set to Hanfield Street, today's
  name (`picks22_reads/22-43/names_resolved.json`).
- In strip 1 the avenue at x about 1,820 was Kirby Avenue in read A and Runnymeade Avenue in read B (RUNNYMEADE is
  printed on it south of Hoffner; north of Wolcott only AVENUE). Ben, 13 November 2026: Runnymeade. Read A's name
  was set to it (`names_resolved.json`), so its four crossings (at Colerain, Wolcott, Kearsarge, Hoffner) are picks
  now. None became a control: Runnymeade, Wolcott and Kearsarge are not on today's map (Beekman Street and the
  expressway run there now), so the fit, the model and every number below are the same as before.

Controls are thin in the west: 6 in the west third of the plate, 9 in the middle, 18 in the east.

Ties to applied plates (held fixed), `reports/2026-11-13_seams_newplates_43`:

| Neighbour | Crossings | Median | Max |
|---|---|---|---|
| 37L | 9 | 1.25 m | 3.69 m |
| 37R | 3 | 1.26 m | 4.77 m |
| 45 | 1 | 0.56 m | 0.56 m |

Largest: Colerain & Powers (4.77 m with 37R, 3.52 m with 37L) and Borden & Powers (3.68 m). 37L's seam median goes
from 1.29 m to 1.26 m with plate 43 counted, 37R's from 1.45 m to 1.32 m.

Against the unbent 1904 frames (613, 614, 615, 617, 618, 620, 621, 622, 623, 632): 55 crossings, medians 3.1 to
5.4 m, max 9.76 m.

Gate: held-out under 5 m, yes; no neighbour's seam median worse, yes. `cufp/43/fwd_complete.pkl` written.
