# The complete set of named crossings on the 1922 plates (Part 1, 2026-11-06)

Rule 12 (`docs/sanborn/RULES.md`): every plate is fitted on every named crossing it shows. The crossings were listed from OSM: every crossing of two differently named streets that falls on the plate under its current model, the realigned streets of rule 3 left out (renamed ones kept: rule 3 aliases them). A crossing counts as picked before when an existing pick (sbg/picks22) with the same names, aliased, lies within 45 m of it. Each of the others was read twice, by two readers working independently (`tools/sanborn/complete/READERS.md`), and kept when both found it within 60 px of each other and within 45 m of its OSM crossing under the plate's current model.

| Plate | On the plate | Realigned | Picked before | Read | New picks | Picked after | Not found | Reads disagree | Over 45 m from OSM | Canal bed | Duplicate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 22-34L | 23 | 0 | 17 | 6 | 1 | 18 | 4 | 0 | 0 | 1 | 0 |
| 22-37L | 47 | 13 | 20 | 14 | 4 | 24 | 9 | 1 | 0 | 0 | 0 |
| 22-37R | 28 | 7 | 11 | 10 | 3 | 14 | 2 | 1 | 0 | 4 | 0 |
| 22-34R | 59 | 0 | 51 | 8 | 0 | 51 | 3 | 0 | 0 | 5 | 0 |
| 22-16R | 23 | 0 | 14 | 9 | 7 | 21 | 1 | 0 | 0 | 1 | 0 |
| 22-35N | 61 | 8 | 28 | 25 | 8 | 36 | 10 | 2 | 0 | 4 | 1 |
| 22-38 | 97 | 10 | 62 | 25 | 12 | 74 | 8 | 1 | 1 | 2 | 1 |
| 22-66 | 153 | 0 | 95 | 58 | 49 | 144 | 2 | 2 | 1 | 0 | 4 |
| 22-67 | 128 | 0 | 75 | 53 | 37 | 112 | 5 | 7 | 0 | 0 | 4 |
| 22-68 | 109 | 2 | 77 | 30 | 19 | 96 | 3 | 4 | 2 | 0 | 2 |
| 22-69 | 98 | 0 | 49 | 49 | 27 | 76 | 9 | 2 | 2 | 0 | 9 |
| 22-70 | 102 | 0 | 75 | 27 | 18 | 93 | 6 | 3 | 0 | 0 | 0 |
| 22-82A | 131 | 5 | 93 | 33 | 13 | 106 | 6 | 7 | 1 | 0 | 6 |
| 22-83A | 58 | 0 | 47 | 11 | 3 | 50 | 8 | 0 | 0 | 0 | 0 |
| 22-75 | 86 | 0 | 54 | 32 | 17 | 71 | 5 | 6 | 0 | 0 | 4 |
| 22-76 | 158 | 5 | 123 | 30 | 15 | 138 | 11 | 3 | 0 | 0 | 1 |
| 22-26A | 73 | 0 | 50 | 23 | 11 | 61 | 9 | 2 | 0 | 0 | 1 |
| 22-26B | 30 | 0 | 11 | 19 | 5 | 16 | 13 | 1 | 0 | 0 | 0 |
| 22-29 | 85 | 0 | 73 | 12 | 9 | 82 | 1 | 1 | 0 | 0 | 1 |
| 22-31 | 59 | 0 | 30 | 29 | 16 | 46 | 6 | 1 | 3 | 3 | 0 |
| 22-33 | 84 | 0 | 61 | 23 | 21 | 82 | 1 | 1 | 0 | 0 | 0 |
| **All** | 1692 | 50 | 1116 | 526 | 295 | 1411 | 122 | 45 | 10 | 20 | 34 |

"Not found": neither reader found the two streets meeting near the crossing (most are streets laid out or joined after 1922). The reads that disagreed, and the picks left out as far from OSM:

- 22-26A `26A_010` Kulla Viken Lane & Mount Hope Avenue: read 1 found it, read 2 did not
- 22-26A `26A_021` Grand Avenue & Nonaly Avenue: read 2 found it, read 1 did not
- 22-26B `26B_000` Greenwich Avenue & West 8th Street: read 2 found it, read 1 did not
- 22-29 `29_001` Neff Avenue & Wilder Avenue: the reads are 76 px apart
- 22-31 `31_003` Grand Avenue & Mickey Avenue: read 2 found it, read 1 did not
- 22-31 `31_024` Harrison Avenue & State Avenue: 59 m from its OSM crossing under the current model
- 22-31 `31_025` Harrison Avenue & State Avenue: 48 m from its OSM crossing under the current model
- 22-31 `31_026` Harrison Avenue & Westwood Avenue: 77 m from its OSM crossing under the current model
- 22-33 `33_013` Queen City Avenue & Sperber Avenue: the reads are 392 px apart
- 22-35N `35N_012` Hull Street & Maisel Drive: read 2 found it, read 1 did not
- 22-35N `35N_015` Clifton Avenue & Clifton Court: read 1 found it, read 2 did not
- 22-37L `37L_012` Prang Street & Townsend Place: the reads are 239 px apart
- 22-37R `37R_001` Spring Grove Avenue & William P. Dooley Bypass: read 1 found it, read 2 did not
- 22-38 `38_002` Evanswood Place & Morrison Place: 86 m from its OSM crossing under the current model
- 22-38 `38_018` Ludlow Avenue & Manor Hill Drive: read 2 found it, read 1 did not
- 22-66 `66_039` Reading Road & William Howard Taft Road: read 2 found it, read 1 did not
- 22-66 `66_040` Burnet Avenue & William Howard Taft Road: read 1 found it, read 2 did not
- 22-66 `66_056` Lincoln Avenue & May Street: 49 m from its OSM crossing under the current model
- 22-67 `67_002` Ashland Avenue & Chapel Street: the reads are 318 px apart
- 22-67 `67_003` Chapel Street & Victory Parkway: read 1 found it, read 2 did not
- 22-67 `67_006` Dixmont Avenue & Gilbert Avenue: the reads are 370 px apart
- 22-67 `67_023` Taft Road Lane & William Howard Taft Road: read 2 found it, read 1 did not
- 22-67 `67_027` Myrtle Avenue & Victory Parkway: read 1 found it, read 2 did not
- 22-67 `67_038` East Martin Luther King Junior Drive & Mentor Avenue: read 2 found it, read 1 did not
- 22-67 `67_045` East Martin Luther King Junior Drive & Gilbert Avenue: the reads are 160 px apart
- 22-68 `68_007` Baxter Avenue & Norwich Lane: read 2 found it, read 1 did not
- 22-68 `68_008` Baxter Avenue & Bonfield Drive: read 2 found it, read 1 did not
- 22-68 `68_009` Baxter Avenue & Wilson Avenue: 52 m from its OSM crossing under the current model
- 22-68 `68_011` Alaska Avenue & Forest Park Drive: read 1 found it, read 2 did not
- 22-68 `68_018` Burnet Avenue & Erkenbrecher Avenue: 110 m from its OSM crossing under the current model
- 22-68 `68_028` Estes Place & Van Antwerp Court: read 2 found it, read 1 did not
- 22-69 `69_003` Fredonia Avenue & Stanton Avenue & Whittier Street: 64 m from its OSM crossing under the current model
- 22-69 `69_017` Jonathan Avenue & Sulsar Street: 212 m from its OSM crossing under the current model
- 22-69 `69_019` Dixmont Avenue & Gilbert Avenue: the reads are 70 px apart
- 22-69 `69_034` Jonathan Avenue & Roselawn Place: read 1 found it, read 2 did not
- 22-70 `70_003` Madison Road & O’Bryon Street: the reads are 75 px apart
- 22-70 `70_009` Floral Avenue & Lexington Avenue: read 2 found it, read 1 did not
- 22-70 `70_017` Duck Creek Road & Potomac Avenue: the reads are 71 px apart
- 22-75 `75_001` Byrnes Lane & Glenwood Avenue: read 1 found it, read 2 did not
- 22-75 `75_003` Glenwood Avenue & Lexington Avenue: read 1 found it, read 2 did not
- 22-75 `75_004` Hudson Avenue & Montgomery Road: read 2 found it, read 1 did not
- 22-75 `75_021` Lexington Avenue & Victory Parkway: the reads are 186 px apart
- 22-75 `75_022` Musketeer Drive & Saint Francis Xavier Way: read 2 found it, read 1 did not
- 22-75 `75_029` Ledgewood Drive & Victory Parkway: the reads are 145 px apart
- 22-76 `76_009` Duck Creek Road & Williams Avenue: the reads are 67 px apart
- 22-76 `76_028` Arbor Place & Edwards Road: read 2 found it, read 1 did not
- 22-76 `76_029` Edmondson Road & Garland Avenue: read 2 found it, read 1 did not
- 22-82A `82A_001` Cleveland Avenue & Lincoln Avenue: read 1 found it, read 2 did not
- 22-82A `82A_005` Rolston Avenue & Ross Avenue: read 1 found it, read 2 did not
- 22-82A `82A_009` Sherman Avenue & Victory Parkway: read 1 found it, read 2 did not
- 22-82A `82A_026` Sherman Avenue & Smith Road: 80 m from its OSM crossing under the current model
- 22-82A `82A_027` Smith Road & Wall Street: read 1 found it, read 2 did not
- 22-82A `82A_028` Maple Avenue & Smith Road: read 2 found it, read 1 did not
- 22-82A `82A_030` Reading Road & Victory Parkway: read 1 found it, read 2 did not
- 22-82A `82A_031` Asmann Avenue & Hopkins Avenue: read 2 found it, read 1 did not
