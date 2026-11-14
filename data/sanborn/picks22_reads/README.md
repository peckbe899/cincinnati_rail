# Plates 25 and 28: the two reads merged (2026-11-13)

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

## 22-45

| Strip | Read A crossings | Read B crossings | Picks | Not agreed |
|---|---|---|---|---|
| 1 | 38 | 39 | 34 | 9 |
| 2 | 31 | 35 | 25 | 16 |
| 3 | 33 | 29 | 27 | 8 |
| 4 | 24 | 24 | 20 | 7 |
| 5 | 15 | 24 | 15 | 9 |
| 6 | 11 | 13 | 6 | 12 |
| **All** | 152 | 164 | 127 | 61 |

Crossings the reads did not agree on:

- strip 1, Martha Street & Carlin Street (read A at 1395, 1580): only read A has it
- strip 1, Hemlock Alley & Sagateo Alley (read A at 2117, 5033): only read A has it
- strip 1, Cypress Alley & Sagateo Alley (read A at 2085, 5266): only read A has it
- strip 1, Martha Street & Tarrant Street (read B at 1190, 1742): only read B has it
- strip 1, Leher Street & Chase Avenue (read B at 775, 4243): only read B has it
- strip 1, Hemlock Alley & Agate Alley (read B at 2118, 5035): only read B has it
- strip 1, Cypress Alley & Agate Alley (read B at 2087, 5277): only read B has it
- strip 2, Innes Avenue & Otte Street (read A at 3518, 291): only read A has it
- strip 2, Innes Avenue & Philomena Avenue (read A at 3522, 690): only read A has it
- strip 2, Innes Avenue & Frederick Avenue (read A at 3528, 1085): only read A has it
- strip 2, Innes Avenue & Bruce Avenue (read A at 3626, 3413): only read A has it
- strip 2, Hamilton Avenue & Otte Street (read A at 4352, 282): only read A has it
- strip 2, Hamilton Avenue & Glen Armand Avenue (read A at 4354, 293): only read A has it
- strip 2, Kirby Avenue & Virginia Avenue (read B at 2697, 1502): only read B has it
- strip 2, Tarrant Street & Virginia Avenue (read B at 2447, 2171): only read B has it
- strip 2, Bruce Avenue & Virginia Avenue (read B at 2080, 3222): only read B has it
- strip 2, Cypress Alley & Florida Avenue (read B at 2258, 5303): only read B has it
- strip 2, Florida Avenue & Hanfield Street (read B at 2216, 5522): only read B has it
- strip 2, Kirby Avenue & Hanfield Street (read B at 2664, 5620): only read B has it
- strip 2, Gordon Street & Hanfield Street (read B at 3028, 5690): only read B has it
- strip 2, Pitts Avenue & Hanfield Street (read B at 3586, 5806): only read B has it
- strip 2, Witler Street & Hanfield Street (read B at 3947, 5873): only read B has it
- strip 3, Haight Avenue & Addingham Place (read A at 5788, 3289): only read A has it
- strip 3, Haight Avenue & Pullan Avenue (read A at 6068, 4039): only read A has it
- strip 3, Chase Avenue & Pitts (read A at 3698, 5152): only read A has it
- strip 3, Addingham & Haight Avenue (read B at 5788, 3289): only read B has it
- strip 4, East View Avenue & Thompson Heights Avenue (read A at 5843, 856): only read A has it
- strip 4, Fergus Street & Thompson Heights Avenue (read A at 7456, 803): only read A has it
- strip 4, Langland Avenue & Glen Parker Avenue (read A at 6430, 1365): only read A has it
- strip 4, Langland Avenue & Donaldson Place (read B at 6742, 3466): only read B has it
- strip 4, Fergus Street & Apjones Street (read B at 7512, 4310): only read B has it
- strip 4, Mad Anthony Street & Apjones Street (read B at 7775, 4288): only read B has it
- strip 5, Frederick Avenue & Fergus Street (read B at 7452, 797): only read B has it
- strip 5, Pullan Avenue & Beech Hill Avenue (read B at 7284, 3818): only read B has it
- strip 5, Pullan Avenue & Fergus Street (read B at 7511, 3779): only read B has it
- strip 5, Pullan Avenue & Chambers Street (read B at 8286, 3690): only read B has it
- strip 5, Pullan Avenue & Dane Street (read B at 8895, 3637): only read B has it
- strip 5, Chase Avenue & Fergus Street (read B at 7514, 5273): only read B has it
- strip 5, Chase Avenue & Mad Anthony Street (read B at 7869, 5260): only read B has it
- strip 5, Chase Avenue & Chambers Street (read B at 8463, 5178): only read B has it
- strip 5, Chase Avenue & Dane Street (read B at 9065, 5125): only read B has it
- strip 6, Crawford Road & Dane Street (read A at 9283, 2249): only read A has it
- strip 6, Crawford Road & Apjones Street (read A at 9882, 4026): only read A has it
- strip 6, Crawford Road & Ellis Street (read A at 10118, 4490): only read A has it
- strip 6, Crawford Road & Lingo Street (read A at 10472, 5437): only read A has it
- strip 6, Crawford Road & Knowlton Street (read A at 10650, 5903): only read A has it
- strip 6, Dane Street & Crawford Avenue (read B at 9280, 2250): only read B has it
- strip 6, Dane Street & Rodney Street (read B at 8822, 3148): only read B has it
- strip 6, Apjones Street & Crawford Avenue (read B at 9883, 4018): only read B has it
- strip 6, Ellis Street & Crawford Avenue (read B at 10100, 4503): only read B has it
- strip 6, Dane Street & Chase Avenue (read B at 9066, 5138): only read B has it
- strip 6, Lingo Street & Crawford Avenue (read B at 10466, 5440): only read B has it
- strip 6, Knowlton Street & Crawford Avenue (read B at 10653, 5911): only read B has it
- strip 1, Virginia Avenue & Kirby Avenue (read A at 2738, 1345): the reads are 199 px apart
- strip 1, Kirby Avenue & Virginia Avenue (read B at 2697, 1540): the reads are 199 px apart
- strip 2, Glen Parker Avenue & Hamilton Avenue (read B at 4170, 1946): the reads are 135 px apart
- strip 3, East View Avenue & Thompson Heights Avenue (read A at 5864, 858): the reads are 795 px apart
- strip 3, Hamilton Avenue & Glen Parker Avenue (read A at 4055, 1875): the reads are 72 px apart
- strip 3, Hamilton Avenue & Glen Parker Avenue (read A at 4186, 1954): the reads are 81 px apart
- strip 3, Glen Parker Avenue & Hamilton Avenue (read B at 4120, 1907): the reads are 72 px apart
- strip 4, Langland Avenue & Thompson Heights Avenue (read A at 6455, 788): the reads are 576 px apart

## 22-43

| Strip | Read A crossings | Read B crossings | Picks | Not agreed |
|---|---|---|---|---|
| 1 | 13 | 13 | 12 | 2 |
| 2 | 10 | 10 | 10 | 0 |
| 3 | 13 | 13 | 13 | 0 |
| 4 | 8 | 8 | 8 | 0 |
| 5 | 14 | 14 | 13 | 2 |
| 6 | 20 | 20 | 19 | 2 |
| **All** | 78 | 78 | 75 | 6 |

Crossings the reads did not agree on:

- strip 1, Colerain Avenue & Westfork Road (read A at 958, 12): only read A has it
- strip 1, Hanfield Street & Jerome Street (read B at 2546, 110): only read B has it
- strip 5, Delaney Street & Walker Alley (read A at 8785, 2812): only read A has it
- strip 5, Joe Williams Street & McMakin Street (read B at 7716, 3358): only read B has it
- strip 6, Delaney Street & McMakin Alley (read B at 8795, 3742): only read B has it
- strip 6, Colerain Avenue & Powers Street (read A at 9005, 7005): the reads are 48 px apart

## 22-44

| Strip | Read A crossings | Read B crossings | Picks | Not agreed |
|---|---|---|---|---|
| 1 | 18 | 18 | 18 | 0 |
| 2 | 20 | 15 | 11 | 11 |
| 3 | 9 | 7 | 5 | 5 |
| 4 | 6 | 8 | 6 | 2 |
| 5 | 8 | 8 | 4 | 5 |
| 6 | 2 | 2 | 1 | 2 |
| **All** | 63 | 58 | 45 | 25 |

Crossings the reads did not agree on:

- strip 2, Hamilton Avenue & Palm Avenue (read A at 2118, 2645): only read A has it
- strip 2, Gulow Street & Hoffner Street (read A at 1406, 5351): only read A has it
- strip 2, Hamilton Avenue & Hoffner Street (read A at 2248, 5352): only read A has it
- strip 2, Hamilton Avenue & Ludlow Avenue (read A at 2252, 5348): only read A has it
- strip 2, Hamilton Avenue & Spring Grove Avenue (read A at 2218, 5388): only read A has it
- strip 2, Spring Grove Avenue & Cooper Street (read A at 1761, 6203): only read A has it
- strip 2, Spring Grove Avenue & Powers Street (read A at 1335, 7135): only read A has it
- strip 2, Kendall Street & Ingot Street (read B at 2430, 1590): only read B has it
- strip 2, Knowlton Street & Ingot Street (read B at 2473, 2069): only read B has it
- strip 3, Chase Avenue & Langland Street (read A at 2992, 62): only read A has it
- strip 3, Chase Avenue & Fergus Street (read A at 4495, 62): only read A has it
- strip 4, Fergus Street & Knowlton Street (read B at 4515, 2060): only read B has it
- strip 4, Alibone Street & Spring Grove Avenue (read B at 6240, 3575): only read B has it
- strip 5, Alibone Street & Spring Grove Avenue (read A at 6245, 3670): only read A has it
- strip 5, Chambers Street & Cornwall Place (read B at 6530, 812): only read B has it
- strip 6, Dane Avenue & Knowlton Street (read A at 7870, 1695): only read A has it
- strip 2, Hamilton Avenue & Pope Street (read A at 1540, 640): the reads are 170 px apart
- strip 2, Hamilton Avenue & Lingo Street (read A at 1746, 1139): the reads are 146 px apart
- strip 3, Blue Rock Street & Spring Grove Avenue (read A at 4020, 3600): the reads are 130 px apart
- strip 3, Fergus Street & Spring Grove Avenue (read A at 4505, 3565): the reads are 65 px apart
- strip 3, Spring Grove Avenue & Fergus Street (read B at 4445, 3590): the reads are 65 px apart
- strip 5, Dane Avenue & Bond Street (read A at 7868, 2695): the reads are 97 px apart
- strip 5, Chambers Street & Spring Grove Avenue (read A at 6755, 3665): the reads are 100 px apart
- strip 5, Dane Avenue & Spring Grove Avenue (read A at 8035, 3690): the reads are 71 px apart
- strip 6, Dane Avenue & Spring Grove Avenue (read B at 8220, 3660): the reads are 180 px apart

