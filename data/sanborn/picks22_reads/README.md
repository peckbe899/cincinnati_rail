# Plates 25, 28, 39 and 40: the two reads merged

Each strip read twice, independently (`docs/sanborn/workspace_notes/sbg/INSTRUCTIONS22.md`, section of 8 November). A pick is kept only where the two reads have the same crossing (same street names) within 60 px, at their mean (`tools/sanborn/complete/merge_reads.py`). Strips overlap by about 300 px, so a crossing near a strip edge can be counted in two strips; the fit merges those.

## 22-25

| Strip | Read A crossings | Read B crossings | Picks | Not agreed |
|---|---|---|---|---|
| 1 | 6 | 6 | 6 | 0 |
| 2 | 4 | 4 | 4 | 0 |
| 3 | 1 | 1 | 1 | 0 |
| 4 | 4 | 5 | 4 | 1 |
| 5 | 14 | 14 | 14 | 1 |
| 6 | 15 | 14 | 14 | 0 |
| **All** | 44 | 44 | 43 | 2 |

Crossings the reads did not agree on:

- strip 4, West 8th Street & Robb (read B at 5928, 168): only read B has it
- strip 5, Delhi Avenue & Fairbanks Avenue (read A at 7660, 7035): only read A has it

## 22-28

| Strip | Read A crossings | Read B crossings | Picks | Not agreed |
|---|---|---|---|---|
| 1 | 29 | 29 | 29 | 0 |
| 2 | 28 | 28 | 28 | 0 |
| 3 | 20 | 23 | 13 | 17 |
| 4 | 30 | 26 | 20 | 14 |
| 5 | 40 | 40 | 36 | 8 |
| 6 | 40 | 39 | 38 | 3 |
| **All** | 187 | 185 | 164 | 42 |

Crossings the reads did not agree on:

- strip 3, Warsaw Avenue & Glenway Avenue (read A at 5470, 1782): only read A has it
- strip 3, Harris Avenue & St. Lawrence Avenue (read A at 3872, 4198): only read A has it
- strip 3, Regina Avenue & St. Lawrence Avenue (read A at 4006, 4196): only read A has it
- strip 3, Academy Avenue & St. Lawrence Avenue (read A at 4385, 4195): only read A has it
- strip 3, Academy Avenue & St. Lawrence Avenue (read A at 4485, 4175): only read A has it
- strip 3, Beech Street & St. Lawrence Avenue (read A at 4980, 3982): only read A has it
- strip 3, Seton Avenue & St. Lawrence Avenue (read A at 5390, 3846): only read A has it
- strip 3, Glenway Avenue & Beech Street (read B at 4936, 1790): only read B has it
- strip 3, Warsaw Avenue & Seton Avenue (read B at 5385, 1782): only read B has it
- strip 3, Vincent Avenue & Beech Street (read B at 4975, 2948): only read B has it
- strip 3, Vincent Avenue & Seton Avenue (read B at 5390, 2947): only read B has it
- strip 3, Glenway Avenue & Seton Avenue (read B at 5395, 3837): only read B has it
- strip 3, Glenway Avenue & Beech Street (read B at 4982, 3983): only read B has it
- strip 3, Glenway Avenue & Academy Avenue (read B at 4485, 4157): only read B has it
- strip 3, Glenway Avenue & Academy Avenue (read B at 4365, 4182): only read B has it
- strip 3, Glenway Avenue & Regina Avenue (read B at 4003, 4184): only read B has it
- strip 3, Glenway Avenue & Harris Avenue (read B at 3886, 4188): only read B has it
- strip 4, Quebec Road & Glenway Avenue (read A at 5562, 1715): only read A has it
- strip 4, Laclede & LaSalle (read A at 7200, 2650): only read A has it
- strip 4, Warsaw Avenue & St. Lawrence Avenue (read A at 6965, 3470): only read A has it
- strip 4, Seton Avenue & St. Lawrence Avenue (read A at 5392, 3832): only read A has it
- strip 4, Rapid Avenue & St. Lawrence Avenue (read A at 5785, 3690): only read A has it
- strip 4, Kirbert Avenue & St. Lawrence Avenue (read A at 5888, 3662): only read A has it
- strip 4, Oakland Avenue & St. Lawrence Avenue (read A at 6320, 3550): only read A has it
- strip 4, Olive Avenue & St. Lawrence Avenue (read A at 6720, 3510): only read A has it
- strip 4, Rapid Avenue & Glenway Avenue (read B at 5790, 3692): only read B has it
- strip 4, Kirbert Avenue & Glenway Avenue (read B at 5875, 3662): only read B has it
- strip 4, Oakland Avenue & Glenway Avenue (read B at 6318, 3540): only read B has it
- strip 4, Olive Avenue & Glenway Avenue (read B at 6725, 3512): only read B has it
- strip 5, Ross Avenue & West Liberty Street (read A at 6755, 174): only read A has it
- strip 5, Glenway Avenue & Mayfield Avenue (read A at 7333, 1640): only read A has it
- strip 5, Glenway Avenue & Fairbanks Avenue (read A at 8942, 1638): only read A has it
- strip 5, Warsaw Avenue & Olive Avenue (read A at 6717, 3492): only read A has it
- strip 5, Mayfield Avenue & Carson Avenue (read B at 7342, 672): only read B has it
- strip 5, Glenway Avenue & Kuhlman Street (read B at 6640, 1640): only read B has it
- strip 5, Lasalle Street & McPherson Avenue (read B at 7928, 2258): only read B has it
- strip 5, Price Avenue & Fairbanks Avenue (read B at 8870, 5091): only read B has it
- strip 6, Foley Street & Brevier Avenue (read A at 8716, 2481): only read A has it
- strip 4, Warsaw Avenue & Glenway Avenue (read A at 5455, 1775): the reads are 2315 px apart
- strip 4, Seton Avenue & Glenway Avenue (read A at 5390, 1778): the reads are 2060 px apart
- strip 6, Mansion Avenue & Brevier Avenue (read A at 9902, 2470): the reads are 52 px apart
- strip 6, Elberon Avenue & West 8th Street (read B at 10045, 5753): the reads are 179 px apart

## 22-39

| Strip | Read A crossings | Read B crossings | Picks | Not agreed |
|---|---|---|---|---|
| 1 | 3 | 3 | 3 | 0 |
| 2 | 0 | 2 | 0 | 2 |
| 3 | 12 | 12 | 12 | 0 |
| 4 | 15 | 12 | 10 | 7 |
| 5 | 10 | 10 | 9 | 2 |
| 6 | 13 | 12 | 9 | 6 |
| **All** | 53 | 51 | 43 | 17 |

Crossings the reads did not agree on:

- strip 2, Lafayette Avenue & Middleton Avenue (read B at 3853, 3608): only read B has it
- strip 2, Warren Avenue & Middleton Avenue (read B at 3957, 5382): only read B has it
- strip 4, Lafayette Avenue & Marjorie Avenue (read A at 6790, 3585): only read A has it
- strip 4, Clifton Avenue & Belsaw Place (read A at 5375, 4385): only read A has it
- strip 4, Belsaw Place & Belsaw Place (read A at 5080, 4553): only read A has it
- strip 4, Belsaw Place & Belsaw Place (read A at 5080, 4920): only read A has it
- strip 4, Clifton Avenue & Belsaw Place (read A at 5387, 4927): only read A has it
- strip 4, Lafayette Circle & Marjorie Avenue (read B at 6800, 3585): only read B has it
- strip 4, Clifton Avenue & McAlpin Avenue (read B at 5422, 7003): only read B has it
- strip 5, Woolper Avenue & Vine Street (read A at 8541, 6815): only read A has it
- strip 5, McAlpin Avenue & Vine Street (read B at 8544, 6820): only read B has it
- strip 6, Greendale Avenue & Vine Street (read A at 8756, 6436): only read A has it
- strip 6, Woolper Avenue & Vine Street (read A at 8528, 6822): only read A has it
- strip 6, Kessler Avenue & Ringwalt Avenue (read A at 9158, 2017): only read A has it
- strip 6, Frank Court & Vine Street (read B at 10553, 3102): only read B has it
- strip 6, McAlpin Avenue & Vine Street (read B at 8528, 6853): only read B has it
- strip 6, Ehrman Avenue & Vine Street (read A at 9290, 5626): the reads are 64 px apart

## 22-40

| Strip | Read A crossings | Read B crossings | Picks | Not agreed |
|---|---|---|---|---|
| 1 | 18 | 18 | 16 | 2 |
| 2 | 15 | 15 | 14 | 2 |
| 3 | 8 | 8 | 8 | 1 |
| 4 | 6 | 7 | 5 | 2 |
| 5 | 7 | 7 | 7 | 0 |
| 6 | 20 | 22 | 19 | 4 |
| **All** | 74 | 77 | 69 | 11 |

Crossings the reads did not agree on:

- strip 2, Mitchell Avenue & Donnell Avenue (read A at 2845, 3925): only read A has it
- strip 2, Spring Grove Avenue & Donnell Avenue (read B at 2840, 3873): only read B has it
- strip 4, Chickering Avenue & Spring Grove Avenue (read A at 4828, 1795): only read A has it
- strip 4, Spring Grove Avenue & Erie Avenue (read B at 4823, 1783): only read B has it
- strip 6, Spring Grove Avenue & Beech Avenue (read A at 7300, 190): only read A has it
- strip 6, Andrews Street & West Ross Avenue (read B at 8987, 1411): only read B has it
- strip 6, Andrews Street & Bank Avenue (read B at 8983, 2086): only read B has it
- strip 6, Bank Avenue & Carthage Avenue (read B at 9559, 2093): only read B has it
- strip 1, Winton Avenue & McMakin Avenue (read A at 65, 900): the reads are 78 px apart
- strip 1, McMakin Avenue & North Edgewood Avenue (read A at 1568, 900): the reads are 78 px apart
- strip 3, Spring Grove Avenue & Mitchell Avenue (read B at 2873, 3823): the reads are 35 px apart

