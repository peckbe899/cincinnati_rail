# Re-read of the 15 widest ties, 2026-11-06

Ben's ruling (6 November): re-read the 15 widest ties after the joint solve (`reports/2026-11-06_joint/README.md`, "Ties, widest after the solve"); apply nothing. No plate was refitted. Tiles, streets, the 1904 bend, `sbg/picks22` and every model are unchanged. The new picks sit beside the old ones in `data/sanborn/picks22_reread/`.

## How it was read

- **Strips:** for each tie, on both plates, a region round the crossing was cut from the scan the picks were read on: Ben's PNGs (`CS2/New Sanborn/PNG`, via `configs/sanborn_paths.json`), his GeoTIFF for 35N, and the Library of Congress scans for the 37L, 37R and 34R halves. Each region covers the old pick and the other plate's position mapped onto this plate. It was rendered with a grid labelled in original plate pixels, as `sbg/sb.py render` does (`method/prep.py`, `method/crop.py`).
- **Reads:** two independent reads of every crossing (30 plate-crossings, 60 reads; 8 reader agents in 4 groups). The rules are those of `docs/sanborn/workspace_notes/sbg/INSTRUCTIONS.md` and `INSTRUCTIONS22.md`: the crossing of the centrelines, about 10 px precision from 300-1,000 px crops, and names as printed. Readers did not see the old picks or each other's reads. Raw reads are in `reads/`.
- **Records:** `data/sanborn/picks22_reread/<plate>/t<NN>_<street>__<street>.json` holds the crossing, both reads, the new pick (the mean of two reads within 60 px, or the single read found), the old pick with each reader's pick behind it, the OSM crossing the plate's fit matched it to, and the OSM crossings of the same two names with their distances.
- **Verdict rules:** positions use each plate's own model.
  - (a) mis-pick: one side's new read moved more than 5 m and now agrees with the other plate within 5 m, while the other side's reads stand.
  - (b) wrong name match: the pairing joins two different crossings.
  - (c) real disagreement: both reads stand (moved 5 m or less) and still differ by more than 10 m.
  - Judgements beyond the rules are in `method/overrides.json`, with reasons; `verdicts.json` has all of it.

## Name check: other crossings of the same two names within 150 m

- **Ridgeway Avenue & Reading Road** (ties 2, 4): a jog. The east and west legs meet Reading 26.7 m apart in OSM; on the plates the legs are 100-180 px apart (22-66, 22-68, 22-69).
- **Montgomery Road & Clarion Avenue** (tie 12): a jog. OSM has two crossings 12.9 m apart; on 22-75 the west arm and the east stub meet Montgomery about 70-80 px apart.
- **Brewster Avenue & Montgomery Road** (tie 13): a jog on both plates (22-69 and 22-75). OSM has only one crossing.

No other picks of the same two names lie within 150 m on any of the 13 plates, and the readers found no further same-name crossings in their regions.

## Verdicts

| # | Plates | Crossing | Seam before m | After re-read m | Verdict |
|---|---|---|---|---|---|
| 1 | 22-67 / 22-69 | Gilbert Avenue & Woodburn Avenue | 30.0 | 25.6 | unresolved: probably the junction is mis-identified on 22-67 (see below) |
| 2 | 22-68 / 22-69 | Ridgeway Avenue & Reading Road | 29.9 | (reads took different legs) | **(b)** jog: 69's east leg paired with 68's west leg; like legs 4.9 / 5.4 m |
| 3 | 22-33 / 22-34R | Marshall Avenue & Garrard Avenue | 25.6 | 25.9 | **(c)** |
| 4 | 22-66 / 22-69 | Ridgeway Avenue & Reading Road | 27.8 | (reads took different legs) | **(b)** jog: 69's east leg paired with 66's west leg; like legs 8.0 / 8.7 m |
| 5 | 22-37L / 22-37R | Groub Street & Ralston Avenue | 27.4 | 25.7 | **(c)** one paper point (gutter overlap) |
| 6 | 22-37L / 22-37R | Geringer Street & Ralston Avenue | 23.3 | 25.5 | **(c)** one paper point (gutter overlap) |
| 7 | 22-34R / 22-38 | Vermont Avenue & Stock Avenue | 21.8 | 17.5 | **(c)** |
| 8 | 22-37L / 22-37R | Geringer Street & Groub Street | 21.8 | 24.1 | **(c)** one paper point; the name pairing is doubtful (one reader finds no such crossing) |
| 9 | 22-34R / 22-38 | Vermont Avenue & Bates Alley | 20.5 | 20.6 | **(c)** |
| 10 | 22-37R / 22-38 | Ludlow Avenue & Lafayette Avenue | 19.8 | 21.3 | **(c)** |
| 11 | 22-66 / 22-69 | Wehrman Street & Gilbert Avenue | 13.4 | - | unresolved: neither name printed in either region; on 22-69 one reader finds no Wehrman |
| 12 | 22-70 / 22-75 | Montgomery Road & Clarion Avenue | 14.3 | 2.9 (jog midpoint) | **(b)** jog: 70's leg paired with 75's other leg; the rules' (a) is set aside |
| 13 | 22-69 / 22-75 | Brewster Avenue & Montgomery Road | 16.3 | 16.8 | unresolved: probably the jog again (8 m with the other leg), but that leg is estimated, not read |
| 14 | 22-75 / 22-76 | Ivanhoe Avenue & Montgomery Road | 14.3 | 13.1 | **(c)** (one reader's narrower reading of Ivanhoe on 22-75 would give 4.1 m) |
| 15 | 22-35N / 22-38 | West McMicken Avenue & Dixmyth Avenue | 14.5 | 12.7 | **(c)** |

Counts: (a) 0, (b) 3, (c) 9, unresolved 3. No old pick was a mis-pick in the sense of (a). The new reads moved the old picks by 0.1-4.8 m, except 22-75 at Clarion (11.1 m, to the middle of the jog) and 22-37R at Geringer & Groub (6.6 m, low-confidence read).

What the re-read shows:
- **The 37L/37R ties (5, 6, 8) are one paper point each.** The two halves overlap at the gutter (37L x = 37R x + 5633, the same y), and both halves' picks are the same spot on the paper. Their 24-26 m is the two halves' models disagreeing, not the reads.
- **The 34R/38 ties (7, 9) and 33/34R (3)** stand on both plates (moves under 4 m) and stay 17-26 m apart.
- **Tie 1:** both re-reads on 22-67 repeat the old reading: where the diagonal avenue merges into the north-south avenue, 29.6 m from OSM's Gilbert/Woodburn crossing. Further north on the same avenue, where Hewitt and the "MONT." branch leave (y about 135-180), it sits 4.3-13 m from 22-69's five-way point and 5-11 m from OSM. A targeted read of that junction on 22-67 would settle it.

## Round 2: two targeted reads (Ben, 6 November)

Two independent reads each (`reads/P1r1.json`, `P1r2.json`; regions by `method/prep2.py`). The records are `data/sanborn/picks22_reread/22-67/t01b_gilbert_avenue__woodburn_avenue.json` and `22-75/t13b_brewster_avenue__montgomery_road.json`. The verdicts are appended to `verdicts.json` with `"round": 2`; the last verdict for a tie counts.

- **Tie 1, Gilbert & Woodburn (22-67 / 22-69): (a) mis-pick on 22-67.**
  - Both reads put the junction where Hewitt and the "MONT." branch leave the north-south avenue at (5833, 174), 5.8 px apart.
  - That point is 3.7 m from 22-69's pick and 3.3 m from OSM's Gilbert/Woodburn crossing.
  - The old pick, where the diagonal printed GILBERT merges into the avenue at (5826, 330), is 30.0 m from 22-69 and 34.1 m from OSM. It is replaced in the rerun.
  - WOODBURN is not printed in 22-67's region; the avenue's name comes from 22-69 and OSM.
- **Tie 13, Brewster & Montgomery (22-69 / 22-75): (b) wrong name match.**
  - Brewster's other leg on 22-75, east of Montgomery, is at (8567, 7166). It lies on the plate's bottom edge with about 50 px of its width on the plate, so its centre is estimated. The two reads are 7.1 px apart.
  - That leg is 7.4 m from 22-69's pick and 8.2 m from OSM's one crossing. The old 22-75 pick, the west leg, is 17.1 m and 17.8 m away.
  - The old tie paired unlike legs of the jog, as at Ridgeway and Clarion, so it is dropped. The jog's size is uncertain: one reader gives 45 px along Montgomery, or about 10 px if a curb line is the leg's north line.

Counts after round 2: (a) 1, (b) 4, (c) 9, unresolved 1 (tie 11, Wehrman & Gilbert).

## Seam report with the wrong matches dropped

The rerun uses `tools/sanborn/seams.py` through `rerun.py`. After round 2: tie 1's pick on 22-67 is replaced by the targeted read, and ties 2, 4, 12 and 13 are dropped. Plates are on their own models. The full report is in `seams_detail.md`, `seams.csv`, `per_pair.csv` and `seams.json`. "Before" is `reports/2026-11-06_seams/`.

| Seam | | Shared | Median m | 90% m | Max m | > 10 m | > 20 m |
|---|---|---|---|---|---|---|---|
| plate-plate | before | 146 | 2.88 | 12.75 | 30.01 | 19 | 9 |
| plate-plate | after round 1 (2, 4, 12 dropped) | 143 | 2.78 | 11.12 | 30.01 | 16 | 7 |
| plate-plate | after round 2 (13 dropped too, tie 1 re-picked on 22-67) | 142 | 2.75 | 9.98 | 27.44 | 14 | 6 |
| plate-1904 | before and after | 556 | 0.40 | 7.75 | 35.09 | 51 | 25 |

After round 2 the widest plate-plate seam is 22-37L / 22-37R at Groub & Ralston (27.4 m, a real disagreement between the two halves; see `reports/2026-11-06_local/`).

## Files

- `verdicts.json`: the 15 verdicts with reasons and moves.
- `ties15.json`: each tie's old picks, reader picks, OSM matches and the other plate's position mapped onto this plate.
- `reads/`: the 8 readers' raw output (G1-G4, read 1 and read 2).
- `rerun.py`: the seam rerun.
- `method/`: the scripts that cut the regions, rendered the reader crops and collated the reads, plus the overrides. They ran from a scratch folder, so their paths are absolute.
