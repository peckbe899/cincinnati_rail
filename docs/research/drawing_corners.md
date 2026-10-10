# Metro drawing checks: unfinished and incorrect corners

Ben's request (2026-10-10), on the drawn KMZ path of each Metro line (the Rail Profiles page flags the same, under Drawing and Platform curve). A finished curve is drawn as a run of vertices each turning a little (typically 5 to 20 degrees, about 60 m apart).

- **Single-angle corner** (WARNING, unfinished): a bend drawn as one vertex turning 5 degrees or more, with no same-way turn of 2 degrees or more on either side. Draw it as a curve.
- **Join kink** (ERROR): a turn of 10 degrees or more beside a segment under 10 m, where two drawn pieces do not meet cleanly.
- **Doubles back** (ERROR): a turn over 90 degrees: drawn pieces overlap or leave a sideways gap.
- **S-curve platform**: the path turns both ways inside the platform span (centre +/- 76.2 m, where the platform is slid to). 5 degrees or more each way is an ERROR (no station works on an S-curve, whatever the fitted radius; gap fillers do not fix it), 2 to 5 degrees a WARNING (a small wiggle in the drawing).

Totals: S-curve platforms 19 ERROR, 11 WARNING; corners 10 doubling back, 25 join kinks, 53 single-angle corners.

Coordinates are latitude, longitude of the vertex, to find it in Google Earth.

## S-curve platforms: ERROR

| Line | Station | Chainage | Turns one way | Turns the other way |
|---|---|---|---|---|
| Line 1 | University | 9+498 | 57° | 57° |
| Line 1 | Central Ave | 11+217 | 14° | 10° |
| Line 1 | 6th | 13+511 | 11° | 57° |
| Line 1 | Pennsylvania Station | 16+081 | 26° | 30° |
| Line 1 | Levee | 16+922 | 12° | 20° |
| Line 2 | Roebling | 13+916 | 167° | 167° |
| Line 2 | Wallace Woods | 17+362 | 13° | 17° |
| Line 3 | Bruckman | 9+078 | 36° | 34° |
| Line 3 | Paycor | 16+388 | 27° | 27° |
| Line 5 | Northside | 8+187 | 81° | 90° |
| Line 5 | Colerain | 8+918 | 24° | 18° |
| Line 7 | Fountain Square | 16+502 | 78° | 78° |
| Line 8 | River Rd | 11+472 | 8° | 5° |
| Line 9 | VA Medical Center | 15+824 | 19° | 10° |
| Line 11 | Clay | 0+820 | 33° | 40° |
| Line 13 | Woolper | 3+633 | 10° | 34° |
| Line 13 | AVondale | 5+561 | 31° | 9° |
| Line 13 | Linwood Square | 11+875 | 25° | 9° |
| Line 13 | Mt Lookout | 12+729 | 14° | 34° |

## S-curve platforms: WARNING

| Line | Station | Chainage | Turns one way | Turns the other way |
|---|---|---|---|---|
| Line 3 | Draper | 12+232 | 6° | 5° |
| Line 4 | City Hall | 13+830 | 3° | 12° |
| Line 4 | Garfield | 14+260 | 9° | 4° |
| Line 6 | Forest | 4+825 | 2° | 3° |
| Line 7 | Krohn | 19+189 | 3° | 18° |
| Line 7 | Edgecliff | 19+941 | 12° | 4° |
| Line 8 | Cincinnati State | 1+228 | 3° | 3° |
| Line 8 | Cincinnati State | 1+230 | 3° | 3° |
| Line 10 | Greenwell | 3+288 | 2° | 24° |
| Line 10 | Cincinnati Art Museum | 15+050 | 3° | 5° |
| Line 10 | Carlisle | 19+486 | 5° | 9° |

## Doubling back: ERROR

| Line | Chainage | Turn | Where (lat, lon) | Drawn piece |
|---|---|---|---|---|
| Line 1 | 11+366 | 170° | 39.11915, -84.52681 | Line 1 North Ext 1 |
| Line 1 | 11+369 | 170° | 39.11917, -84.52680 | Line 1 North Ext 1 |
| Line 2 | 13+909 | 167° | 39.09599, -84.51166 | Line 2 |
| Line 2 | 13+910 | 167° | 39.09599, -84.51167 | Line 2 |
| Line 4 | 9+006 | 174° | 39.11055, -84.57189 | Line 4 West Ext |
| Line 4 | 9+057 | 179° | 39.11060, -84.57247 | Line 4 |
| Line 5 | 17+672 | 180° | 39.10209, -84.49911 | Line 5 |
| Line 5 | 17+735 | 159° | 39.10242, -84.49969 | Line 5 South Ext |
| Line 6 | 10+493 | 178° | 39.09817, -84.50549 | Line 6 |
| Line 6 | 10+551 | 178° | 39.09868, -84.50563 | Line 6 South Ext 1 |

## Join kinks: ERROR

| Line | Chainage | Turn | Where (lat, lon) | Drawn piece | Short segment |
|---|---|---|---|---|---|
| Line 1 | 9+565 | 57° | 39.13356, -84.52026 | Line 1 North Ext 2 | 4.3 m |
| Line 1 | 9+569 | 57° | 39.13354, -84.52022 | Line 1 North Ext 2 | 4.3 m |
| Line 1 | 16+083 | 30° | 39.10112, -84.50049 | Line 1 | 7.6 m |
| Line 1 | 16+090 | 26° | 39.10105, -84.50047 | Line 1 South Ext 1 | 7.6 m |
| Line 2 | 8+184 | 65° | 39.14465, -84.51160 | Line 2 North Ext | 2.8 m |
| Line 2 | 8+186 | 66° | 39.14466, -84.51157 | Line 2 North Ext | 2.8 m |
| Line 2 | 17+349 | 13° | 39.06561, -84.50390 | Line 2 South Ext 1 | 4.6 m |
| Line 2 | 17+354 | 17° | 39.06557, -84.50387 | Line 2 South Ext 1 | 4.6 m |
| Line 3 | 1+223 | 20° | 39.16892, -84.46037 | Line 3 North Ext Line | 8.8 m |
| Line 3 | 4+891 | 17° | 39.16800, -84.49783 | Line 3 North Ext Line | 0.4 m |
| Line 3 | 4+892 | 11° | 39.16800, -84.49784 | Line 3 North Ext Line | 0.4 m |
| Line 3 | 9+022 | 35° | 39.15448, -84.53829 | Line 3 MCE | 0.7 m |
| Line 3 | 9+023 | 34° | 39.15447, -84.53829 | Line 3 MCE | 0.7 m |
| Line 3 | 16+388 | 27° | 39.09521, -84.51647 | Line 3 | 3.9 m |
| Line 3 | 16+392 | 27° | 39.09518, -84.51645 | Line 3 | 3.9 m |
| Line 4 | 18+634 | 11° | 39.13431, -84.48723 | Line 4 | 2.1 m |
| Line 4 | 18+636 | 25° | 39.13433, -84.48722 | Line 4 | 2.1 m |
| Line 5 | 8+191 | 81° | 39.16006, -84.53944 | Line 5 North Ext | 3.4 m |
| Line 5 | 8+195 | 79° | 39.16005, -84.53940 | Line 5 North Ext | 3.4 m |
| Line 6 | 5+359 | 50° | 39.14182, -84.50027 | Line 6 North Ext | 3.9 m |
| Line 6 | 5+363 | 55° | 39.14180, -84.50030 | Line 6 North Ext | 3.9 m |
| Line 6 | 14+306 | 27° | 39.07730, -84.51093 | Line 6 South Ext 1 | 2.1 m |
| Line 6 | 14+308 | 26° | 39.07730, -84.51096 | Line 6 South Ext 1 | 2.1 m |
| Line 7 | 16+509 | 78° | 39.10245, -84.51319 | Line 7 West | 1.6 m |
| Line 7 | 16+511 | 78° | 39.10244, -84.51318 | Line 7 West | 1.6 m |

## Single-angle corners: WARNING

| Line | Chainage | Turn | Where (lat, lon) | Drawn piece |
|---|---|---|---|---|
| Line 1 | 19+469 | 7° | 39.07713, -84.47836 | Line 1 South Ext 1 |
| Line 2 | 18+841 | 6° | 39.05239, -84.50313 | Line 3 South Ext 2 |
| Line 3 | 12+424 | 5° | 39.12561, -84.53342 | Line 3 |
| Line 3 | 17+910 | 7° | 39.08181, -84.51393 | Line 3 South Ext 1 |
| Line 4 | 1+254 | 11° | 39.15530, -84.62883 | Line 4 West Ext |
| Line 4 | 14+319 | 8° | 39.10445, -84.51373 | Line 4 |
| Line 4 | 15+278 | 6° | 39.10744, -84.50397 | Line 4 |
| Line 4 | 18+489 | 5° | 39.13310, -84.48782 | Line 4 |
| Line 4 | 18+942 | 8° | 39.13600, -84.48449 | Line 4 East Ext |
| Line 4 | 19+054 | 12° | 39.13666, -84.48351 | Line 4 East Ext |
| Line 5 | 6+869 | 7° | 39.17160, -84.54292 | Line 5 North Ext |
| Line 5 | 6+985 | 13° | 39.17056, -84.54277 | Line 5 North Ext |
| Line 5 | 8+536 | 10° | 39.15715, -84.54047 | Line 5 |
| Line 5 | 19+974 | 6° | 39.11731, -84.48354 | Line 5 South Ext |
| Line 5 | 20+184 | 13° | 39.11857, -84.48171 | Line 5 South Ext |
| Line 6 | 4+108 | 10° | 39.15170, -84.49438 | Line 6 North Ext |
| Line 6 | 8+510 | 8° | 39.11404, -84.50194 | Line 6 |
| Line 6 | 9+271 | 11° | 39.10878, -84.50713 | Line 6 |
| Line 6 | 16+183 | 18° | 39.06903, -84.52824 | Line 6 South Ext 2 |
| Line 6 | 16+601 | 25° | 39.06593, -84.53098 | Line 6 South Ext 2 |
| Line 6 | 16+934 | 9° | 39.06433, -84.53422 | Line 6 South Ext 2 |
| Line 6 | 17+034 | 33° | 39.06372, -84.53510 | Line 6 South Ext 2 |
| Line 6 | 22+049 | 16° | 39.02874, -84.56717 | Line 6 South Ext 2 |
| Line 7 | 19+530 | 9° | 39.11818, -84.48811 | Line 7 East |
| Line 7 | 20+115 | 7° | 39.12257, -84.48490 | Line 7 East |
| Line 7 | 22+183 | 6° | 39.13811, -84.48183 | Line 7 East |
| Line 7 | 24+275 | 11° | 39.15324, -84.47328 | Line 7 East |
| Line 7 | 27+690 | 12° | 39.18238, -84.46501 | Line 7 East |
| Line 8 | 4+237 | 9° | 39.13395, -84.50937 | Line 8? |
| Line 9 | 5+594 | 5° | 39.15583, -84.60886 | Line 9 |
| Line 9 | 8+993 | 7° | 39.14361, -84.57899 | Line 9 |
| Line 9 | 13+115 | 6° | 39.13721, -84.53668 | Line 9 |
| Line 9 | 19+604 | 15° | 39.13061, -84.46644 | Line 9 |
| Line 10 | 0+136 | 7° | 39.09655, -84.64044 | Line 10 |
| Line 10 | 1+157 | 8° | 39.09445, -84.62904 | Line 10 |
| Line 10 | 7+882 | 5° | 39.09259, -84.56150 | Line 10 |
| Line 10 | 15+727 | 6° | 39.10831, -84.49452 | Line 10 |
| Line 11 | 0+581 | 43° | 39.11499, -84.46777 | Line 11 |
| Line 11 | 0+774 | 40° | 39.11388, -84.46947 | Line 11 |
| Line 11 | 3+758 | 41° | 39.09568, -84.49330 | Line 11 |
| Line 11 | 19+076 | 13° | 39.02175, -84.61693 | Line 11 |
| Line 12 | 5+178 | 13° | 39.13632, -84.53134 | Line 12 |
| Line 12 | 15+625 | 10° | 39.15467, -84.44193 | Line 12 |
| Line 12 | 19+428 | 6° | 39.18078, -84.42735 | Line 12 |
| Line 13 | 10+494 | 11° | 39.13735, -84.44081 | Line 13 |
| Line 13 | 11+344 | 12° | 39.13270, -84.43342 | Line 13 |
| Line 13 | 15+759 | 27° | 39.10697, -84.39914 | Line 13 |
| Line 13 | 16+325 | 16° | 39.10472, -84.39327 | Line 13 |
| Line 13 | 19+934 | 16° | 39.08045, -84.37194 | Line 13 |
| Line 13 | 20+466 | 8° | 39.07752, -84.36708 | Line 13 |
| Line 14 | 15+347 | 11° | 39.17509, -84.45543 | Line 14 |
| Line 14 | 18+472 | 23° | 39.15602, -84.43852 | Line 14 |
| Line 14 | 24+155 | 16° | 39.14476, -84.37838 | Line 14 |

