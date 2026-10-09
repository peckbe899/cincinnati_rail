# Metro platform curvature

Ben's check (2026-10-09), from the Rail Profiles page: over each Metro platform span (centre +/- 76.2 m, wherever the platform has been slid) the drawn path is resampled every 2 m and a circle fitted by least squares; a straight span is an infinite radius. Extra platform gap for the 15.56 m car: outside face 15.56^2 / 8R, inside face (end doors about 5.4 m from the car centre) 5.4^2 / 2R. A curved two-track station has one face of each, so the outside face governs.

- ERROR: R < 600 m (outside-face extra gap over 5 cm); allowed only as a named exception with gap fillers (station card: 'Gap fillers (named exception)').
- WARNING: 600 m <= R < 3,000 m (extra gap 1 to 5 cm).
- No flag: R >= 3,000 m or straight.

428 Metro stations checked: **113 ERROR**, **64 WARNING**, 251 clear. Saved profiles (with any slid platforms) on Lines 1, 2, 4, 5 and 6; the rest at their drawn points.

The path is the drawn KMZ: straight segments with corners about 80 m apart. 'Corners in span' lists the turn at each drawn vertex inside the platform span; 40 of the ERRORs have a single corner of 20 degrees or more there, often where two drawn pieces meet (e.g. Paycor at the Line 3 / South Ext 1 join, Price Hill at the Line 4 / West Ext join, which doubles back 174 degrees). Fix by sliding the platform off the corner, redrawing the curve with more vertices, or naming an exception.

## ERROR

| Line | Station | Chainage | Radius | Extra gap, outside face | Extra gap, inside face | Flag | Corners in span |
|---|---|---|---|---|---|---|---|
| Line 3 | Paycor | 16+388 | 59 m | 51.3 cm | 24.7 cm | ERROR | 27°, 27° |
| Line 4 | Price Hill | 9+062 | 70 m | 43.1 cm | 20.8 cm | ERROR | 174°, 179° |
| Line 1 | 6th | 13+511 | 91 m | 33.3 cm | 16.1 cm | ERROR | 3°, 26°, 19°, 12°, 8° |
| Line 7 | Hoffman | 21+651 | 99 m | 30.5 cm | 14.7 cm | ERROR | 22°, 18°, 21° |
| Line 7 | Fountain Square | 16+502 | 100 m | 30.2 cm | 14.5 cm | ERROR | 78°, 78° |
| Line 3 | St Bernard | 4+809 | 111 m | 27.4 cm | 13.2 cm | ERROR | 8°, 17°, 10°, 11°, 21° |
| Line 10 | Baines | 16+346 | 119 m | 25.5 cm | 12.3 cm | ERROR | 21°, 19°, 19°, 11°, 7° |
| Line 11 | Clay | 0+820 | 123 m | 24.7 cm | 11.9 cm | ERROR | 40°, 33° |
| Line 8 | Ziegler | 6+870 | 126 m | 24.0 cm | 11.5 cm | ERROR | 3°, 29°, 31° |
| Line 4 | Hoyes | 19+256 | 131 m | 23.0 cm | 11.1 cm | ERROR | 23°, 15°, 20° |
| Line 9 | East Westwood | 9+686 | 136 m | 22.3 cm | 10.7 cm | ERROR | 11°, 32°, 3° |
| Line 12 | Woodburn | 10+750 | 147 m | 20.5 cm | 9.9 cm | ERROR | 30° |
| Line 10 | Bonnie Leslie | 18+442 | 150 m | 20.2 cm | 9.7 cm | ERROR | 22°, 21° |
| Line 7 | Chinatown | 14+126 | 171 m | 17.7 cm | 8.5 cm | ERROR | 22°, 22° |
| Line 14 | Appleton | 19+419 | 171 m | 17.7 cm | 8.5 cm | ERROR | 26° |
| Line 10 | Carlisle | 19+486 | 173 m | 17.5 cm | 8.4 cm | ERROR | 9°, 5° |
| Line 3 | Covington Union | 17+807 | 173 m | 17.5 cm | 8.4 cm | ERROR | 26° |
| Line 11 | Arsenal | 4+846 | 180 m | 16.8 cm | 8.1 cm | ERROR | 32° |
| Line 5 | Chinatown-Gest | 14+526 | 184 m | 16.4 cm | 7.9 cm | ERROR | 7°, 3°, 24°, 25° |
| Line 9 | UC Medical/Corryville | 16+382 | 185 m | 16.3 cm | 7.9 cm | ERROR | 19°, 17° |
| Line 9 | Lafeuille | 7+970 | 189 m | 16.0 cm | 7.7 cm | ERROR | 34°, 23° |
| Line 10 | Union Terminal | 11+134 | 197 m | 15.4 cm | 7.4 cm | ERROR | 12°, 23° |
| Line 11 | Taylor | 4+456 | 198 m | 15.3 cm | 7.4 cm | ERROR | 23° |
| Line 4 | Western Hills | 4+894 | 198 m | 15.3 cm | 7.4 cm | ERROR | 8°, 19°, 9° |
| Line 1 | Lafeyette | 6+995 | 204 m | 14.8 cm | 7.1 cm | ERROR | 4°, 10°, 5°, 5°, 8° |
| Line 13 | Woolper | 3+633 | 207 m | 14.6 cm | 7.0 cm | ERROR | 4°, 8°, 22°, 10° |
| Line 1 | Levee | 16+922 | 209 m | 14.5 cm | 7.0 cm | ERROR | 20°, 7°, 6° |
| Line 13 | Linwood Square | 11+875 | 210 m | 14.4 cm | 7.0 cm | ERROR | 9°, 7°, 17° |
| Line 13 | AVondale | 5+561 | 210 m | 14.4 cm | 6.9 cm | ERROR | 9°, 22°, 9° |
| Line 3 | Ft Wright | 22+582 | 213 m | 14.2 cm | 6.9 cm | ERROR | 21° |
| Line 9 | Ebenezer | 1+954 | 214 m | 14.1 cm | 6.8 cm | ERROR | 10°, 12°, 14° |
| Line 14 | La Crosse | 21+701 | 219 m | 13.8 cm | 6.7 cm | ERROR | 27° |
| Line 7 | Chapel | 21+179 | 220 m | 13.8 cm | 6.6 cm | ERROR | 15°, 18° |
| Line 9 | North Fairmount | 12+094 | 223 m | 13.6 cm | 6.5 cm | ERROR | 12°, 19°, 8° |
| Line 5 | Camp Washington | 10+804 | 228 m | 13.3 cm | 6.4 cm | ERROR | 6°, 26° |
| Line 14 | Floral | 17+575 | 229 m | 13.2 cm | 6.4 cm | ERROR | 34° |
| Line 4 | Garfield | 14+260 | 230 m | 13.2 cm | 6.3 cm | ERROR | 4°, 1°, 8° |
| Line 7 | Bank | 12+356 | 239 m | 12.7 cm | 6.1 cm | ERROR | 20° |
| Line 14 | Lafayette Park | 17+095 | 240 m | 12.6 cm | 6.1 cm | ERROR | 39° |
| Line 10 | Greenwell | 3+288 | 240 m | 12.6 cm | 6.1 cm | ERROR | 24°, 2° |
| Line 14 | North Bend/Carthage | 11+445 | 245 m | 12.3 cm | 5.9 cm | ERROR | 23°, 17° |
| Line 4 | Rapid Run | 7+108 | 253 m | 12.0 cm | 5.8 cm | ERROR | 18° |
| Line 1 | Bluegrass | 19+698 | 255 m | 11.9 cm | 5.7 cm | ERROR | 19° |
| Line 4 | Beecher | 18+574 | 257 m | 11.8 cm | 5.7 cm | ERROR | 2°, 10°, 11°, 25° |
| Line 2 | Latonia | 19+394 | 258 m | 11.7 cm | 5.7 cm | ERROR | 6°, 13°, 3° |
| Line 13 | Withrow | 9+313 | 258 m | 11.7 cm | 5.7 cm | ERROR | 15°, 13°, 24° |
| Line 5 | Colerain | 8+918 | 259 m | 11.7 cm | 5.6 cm | ERROR | 9°, 9°, 0°, 24° |
| Line 5 | Bank | 12+970 | 269 m | 11.2 cm | 5.4 cm | ERROR | 2°, 8°, 13°, 10° |
| Line 4 | State | 10+874 | 271 m | 11.2 cm | 5.4 cm | ERROR | 19°, 13° |
| Line 11 | Goebel | 6+830 | 276 m | 10.9 cm | 5.3 cm | ERROR | 16° |
| Line 9 | Mack | 0+000 | 284 m | 10.6 cm | 5.1 cm | ERROR | 8° |
| Line 4 | Bridgetown | 1+056 | 285 m | 10.6 cm | 5.1 cm | ERROR | 11°, 10° |
| Line 12 | Sassafras | 3+658 | 286 m | 10.6 cm | 5.1 cm | ERROR | 4°, 15° |
| Line 3 | Central Ave | 13+350 | 289 m | 10.5 cm | 5.0 cm | ERROR | 16° |
| Line 8 | Burnet North | 2+830 | 294 m | 10.3 cm | 5.0 cm | ERROR | 8°, 11° |
| Line 4 | Glenway | 1+948 | 298 m | 10.2 cm | 4.9 cm | ERROR | 9°, 14° |
| Line 9 | VA Medical Center | 15+824 | 298 m | 10.1 cm | 4.9 cm | ERROR | 10°, 7°, 11° |
| Line 7 | Krohn | 19+189 | 298 m | 10.1 cm | 4.9 cm | ERROR | 12°, 6°, 3° |
| Line 6 | Tibbatts | 12+427 | 301 m | 10.0 cm | 4.8 cm | ERROR | 5°, 14°, 12° |
| Line 10 | Sedamsville | 7+166 | 302 m | 10.0 cm | 4.8 cm | ERROR | 20°, 9°, 5°, 11° |
| Line 5 | Sawyer Point | 18+209 | 303 m | 10.0 cm | 4.8 cm | ERROR | 16°, 9°, 8° |
| Line 8 | Melindy | 6+628 | 304 m | 10.0 cm | 4.8 cm | ERROR | 5°, 11° |
| Line 14 | Robertson | 18+265 | 305 m | 9.9 cm | 4.8 cm | ERROR | 15° |
| Line 2 | St Bernard | 5+058 | 308 m | 9.8 cm | 4.7 cm | ERROR | 17° |
| Line 10 | Highlands | 21+522 | 326 m | 9.3 cm | 4.5 cm | ERROR | 10°, 10°, 7°, 20° |
| Line 5 | Northside | 8+187 | 326 m | 9.3 cm | 4.5 cm | ERROR | 11°, 81°, 79° |
| Line 13 | Mt Lookout | 12+729 | 332 m | 9.1 cm | 4.4 cm | ERROR | 14°, 34° |
| Line 5 | Delta | 24+079 | 332 m | 9.1 cm | 4.4 cm | ERROR | 11°, 9°, 19° |
| Line 8 | Jefferson | 5+002 | 334 m | 9.1 cm | 4.4 cm | ERROR | 13° |
| Line 13 | Paxton | 11+231 | 336 m | 9.0 cm | 4.3 cm | ERROR | 3°, 20° |
| Line 12 | Pleasant Ridge | 18+660 | 337 m | 9.0 cm | 4.3 cm | ERROR | 7°, 11° |
| Line 2b | Bullock | 4+107 | 337 m | 9.0 cm | 4.3 cm | ERROR | 17° |
| Line 12 | Plainfield | 22+210 | 353 m | 8.6 cm | 4.1 cm | ERROR | 13° |
| Line 4 | Hewitt | 19+832 | 376 m | 8.0 cm | 3.9 cm | ERROR | 10°, 6° |
| Line 6 | Greenlee | 3+113 | 382 m | 7.9 cm | 3.8 cm | ERROR | 18°, 19° |
| Line 9 | Burnet East | 15+358 | 384 m | 7.9 cm | 3.8 cm | ERROR | 10°, 10° |
| Line 3 | Brighton | 12+660 | 397 m | 7.6 cm | 3.7 cm | ERROR | 10°, 11° |
| Line 4 | Sherman | 13+466 | 398 m | 7.6 cm | 3.7 cm | ERROR | 6°, 8°, 3° |
| Line 2b | West Covington | 1+317 | 400 m | 7.6 cm | 3.6 cm | ERROR | 6°, 11° |
| Line 7 | Woodward | 22+831 | 413 m | 7.3 cm | 3.5 cm | ERROR | 10°, 5°, 11° |
| Line 7 | Edgecliff | 19+941 | 417 m | 7.3 cm | 3.5 cm | ERROR | 12°, 2°, 2° |
| Line 3 | Findlay | 14+024 | 421 m | 7.2 cm | 3.5 cm | ERROR | 10°, 5° |
| Line 6 | Public Landing | 10+737 | 423 m | 7.2 cm | 3.4 cm | ERROR | 4°, 12° |
| Line 11 | Bullock | 7+828 | 424 m | 7.1 cm | 3.4 cm | ERROR | 11° |
| Line 8 | Bruckman | 0+630 | 431 m | 7.0 cm | 3.4 cm | ERROR | 25°, 5° |
| Line 1 | Center Hill | 1+671 | 436 m | 6.9 cm | 3.3 cm | ERROR | 10° |
| Line 1 | Central Ave | 11+217 | 439 m | 6.9 cm | 3.3 cm | ERROR | 10°, 4°, 6°, 3° |
| Line 9 | Grandin | 20+120 | 441 m | 6.9 cm | 3.3 cm | ERROR | 10°, 4°, 7° |
| Line 5 | Mound | 15+346 | 450 m | 6.7 cm | 3.2 cm | ERROR | 1°, 8°, 9° |
| Line 1 | Stratford | 9+986 | 458 m | 6.6 cm | 3.2 cm | ERROR | 8°, 5°, 5° |
| Line 2 | Zoo | 8+437 | 461 m | 6.6 cm | 3.2 cm | ERROR | 17° |
| Line 2 | VA Medical Center | 9+007 | 467 m | 6.5 cm | 3.1 cm | ERROR | 8°, 6° |
| Line 10 | Mayhew | 4+736 | 480 m | 6.3 cm | 3.0 cm | ERROR | 10°, 6°, 4° |
| Line 6 | Kyles Lane | 17+571 | 480 m | 6.3 cm | 3.0 cm | ERROR | 11° |
| Line 8 | Ludlow | 12+358 | 491 m | 6.2 cm | 3.0 cm | ERROR | 12°, 17° |
| Line 6 | Bullock | 15+091 | 498 m | 6.1 cm | 2.9 cm | ERROR | 11° |
| Line 12 | Chase | 0+696 | 500 m | 6.1 cm | 2.9 cm | ERROR | 9°, 6° |
| Line 9 | Bridgetown | 3+694 | 502 m | 6.0 cm | 2.9 cm | ERROR | 5°, 9° |
| Line 13 | Colerain | 0+725 | 507 m | 6.0 cm | 2.9 cm | ERROR | 9° |
| Line 12 | Edmonson | 15+002 | 508 m | 6.0 cm | 2.9 cm | ERROR | 11°, 12° |
| Line 5 | Wilstach | 13+710 | 522 m | 5.8 cm | 2.8 cm | ERROR | 0°, 10°, 16° |
| Line 6 | North Avondale | 3+617 | 526 m | 5.8 cm | 2.8 cm | ERROR | 11° |
| Line 1 | Pennsylvania Station | 16+081 | 530 m | 5.7 cm | 2.7 cm | ERROR | 30°, 26° |
| Line 7 | Harrison | 11+900 | 536 m | 5.6 cm | 2.7 cm | ERROR | 8° |
| Line 9 | Robb | 4+684 | 537 m | 5.6 cm | 2.7 cm | ERROR | 9° |
| Line 5 | Kemper | 19+527 | 541 m | 5.6 cm | 2.7 cm | ERROR | 4°, 9° |
| Line 9 | Scarborough | 19+392 | 545 m | 5.5 cm | 2.7 cm | ERROR | 9° |
| Line 10 | Delhi Hills | 2+182 | 547 m | 5.5 cm | 2.7 cm | ERROR | 8° |
| Line 11 | Ft Wright | 10+768 | 561 m | 5.4 cm | 2.6 cm | ERROR | 8° |
| Line 14 | Dogwood | 24+099 | 561 m | 5.4 cm | 2.6 cm | ERROR | 16° |
| Line 4 | City Hall | 13+830 | 561 m | 5.4 cm | 2.6 cm | ERROR | 3°, 9°, 3° |
| Line 3 | Draper | 12+232 | 579 m | 5.2 cm | 2.5 cm | ERROR | 6°, 5° |
| Line 12 | Wesleyan | 1+486 | 592 m | 5.1 cm | 2.5 cm | ERROR | 8° |

## WARNING

| Line | Station | Chainage | Radius | Extra gap, outside face | Extra gap, inside face | Flag | Corners in span |
|---|---|---|---|---|---|---|---|
| Line 4 | Times | 14+964 | 603 m | 5.0 cm | 2.4 cm | WARNING | 1°, 18° |
| Line 1 | University | 9+498 | 616 m | 4.9 cm | 2.4 cm | WARNING | 57°, 57° |
| Line 3 | Monmouth | 10+480 | 629 m | 4.8 cm | 2.3 cm | WARNING | 4°, 11° |
| Line 8 | Morrison | 1+966 | 637 m | 4.7 cm | 2.3 cm | WARNING | 9° |
| Line 3 | Bond Hill | 2+877 | 644 m | 4.7 cm | 2.3 cm | WARNING | 5°, 5° |
| Line 10 | River Rd | 9+030 | 646 m | 4.7 cm | 2.3 cm | WARNING | 5°, 7° |
| Line 5 | Corbin | 23+055 | 657 m | 4.6 cm | 2.2 cm | WARNING | 7°, 6° |
| Line 5 | Torrance | 22+037 | 662 m | 4.6 cm | 2.2 cm | WARNING | 6°, 5° |
| Line 12 | Hopple | 4+966 | 676 m | 4.5 cm | 2.2 cm | WARNING | 6°, 4° |
| Line 6 | McGregor | 7+497 | 709 m | 4.3 cm | 2.1 cm | WARNING | 4°, 14° |
| Line 5 | Courthouse | 16+598 | 709 m | 4.3 cm | 2.1 cm | WARNING | 8° |
| Line 13 | Burwood | 8+491 | 746 m | 4.1 cm | 2.0 cm | WARNING | 9° |
| Line 7 | Ledgewood | 24+219 | 754 m | 4.0 cm | 1.9 cm | WARNING | 1°, 11° |
| Line 3 | Kenard | 6+834 | 754 m | 4.0 cm | 1.9 cm | WARNING | 7° |
| Line 5 | Genesee | 15+744 | 756 m | 4.0 cm | 1.9 cm | WARNING | 6°, 5° |
| Line 2 | Jefferson | 10+241 | 775 m | 3.9 cm | 1.9 cm | WARNING | 3°, 5° |
| Line 12 | Woodford | 19+434 | 787 m | 3.8 cm | 1.9 cm | WARNING | 6° |
| Line 3 | Marshall | 11+748 | 791 m | 3.8 cm | 1.8 cm | WARNING | 5°, 2°, 7° |
| Line 7 | Hoyes | 22+191 | 791 m | 3.8 cm | 1.8 cm | WARNING | 6°, 2° |
| Line 10 | Fairbanks | 6+356 | 797 m | 3.8 cm | 1.8 cm | WARNING | 3°, 5°, 7° |
| Line 3 | Peaselburg | 19+440 | 801 m | 3.8 cm | 1.8 cm | WARNING | 7° |
| Line 13 | Bruckman | 1+121 | 819 m | 3.7 cm | 1.8 cm | WARNING | 6° |
| Line 5 | Sassafras | 9+954 | 823 m | 3.7 cm | 1.8 cm | WARNING | 2°, 4° |
| Line 9 | Hopple | 13+460 | 830 m | 3.6 cm | 1.8 cm | WARNING | 6° |
| Line 14 | Hunter Park | 15+167 | 857 m | 3.5 cm | 1.7 cm | WARNING | 3°, 4° |
| Line 8 | Villa Hills | 17+488 | 892 m | 3.4 cm | 1.6 cm | WARNING | 9° |
| Line 14 | Seymour Plaza | 13+451 | 909 m | 3.3 cm | 1.6 cm | WARNING | 4°, 5° |
| Line 4 | Guerley | 6+218 | 951 m | 3.2 cm | 1.5 cm | WARNING | 5° |
| Line 2 | Broerman | 4+162 | 975 m | 3.1 cm | 1.5 cm | WARNING | 5° |
| Line 4 | Werk | 3+172 | 978 m | 3.1 cm | 1.5 cm | WARNING | 5° |
| Line 6 | Pendleton | 9+211 | 987 m | 3.1 cm | 1.5 cm | WARNING | 11° |
| Line 1 | Kenard | 6+183 | 1005 m | 3.0 cm | 1.5 cm | WARNING | 7°, 9° |
| Line 2 | Woolper | 7+488 | 1010 m | 3.0 cm | 1.4 cm | WARNING | 2°, 10° |
| Line 9 | Woodburn | 18+730 | 1027 m | 2.9 cm | 1.4 cm | WARNING | 7° |
| Line 2 | Wallace Woods | 17+362 | 1041 m | 2.9 cm | 1.4 cm | WARNING | 13°, 17° |
| Line 6 | Arlington | 16+251 | 1051 m | 2.9 cm | 1.4 cm | WARNING | 18° |
| Line 13 | Athenaeum | 19+559 | 1112 m | 2.7 cm | 1.3 cm | WARNING | 4° |
| Line 9 | Dixmyth | 14+672 | 1128 m | 2.7 cm | 1.3 cm | WARNING | 6° |
| Line 1 | Carothers Center | 18+814 | 1153 m | 2.6 cm | 1.3 cm | WARNING | 4° |
| Line 3 | Aloysius | 1+985 | 1156 m | 2.6 cm | 1.3 cm | WARNING | 4° |
| Line 3 | Henry Clay | 21+202 | 1226 m | 2.5 cm | 1.2 cm | WARNING | 4° |
| Line 7 | Hathaway | 14+734 | 1235 m | 2.4 cm | 1.2 cm | WARNING | 4° |
| Line 9 | Bathgate | 16+996 | 1238 m | 2.4 cm | 1.2 cm | WARNING | 4° |
| Line 4 | Norwood-Sherman | 22+878 | 1250 m | 2.4 cm | 1.2 cm | WARNING | 4° |
| Line 14 | Worth | 15+513 | 1285 m | 2.4 cm | 1.1 cm | WARNING | 0°, 4° |
| Line 10 | Cincinnati Art Museum | 15+050 | 1291 m | 2.3 cm | 1.1 cm | WARNING | 3°, 5° |
| Line 2b | Covington Union | 4+963 | 1328 m | 2.3 cm | 1.1 cm | WARNING | 17°, 4° |
| Line 8 | River Rd | 11+472 | 1400 m | 2.2 cm | 1.0 cm | WARNING | 8°, 1°, 4° |
| Line 2 | Glenwood | 6+658 | 1436 m | 2.1 cm | 1.0 cm | WARNING | 3° |
| Line 5 | Queen City | 12+298 | 1495 m | 2.0 cm | 1.0 cm | WARNING | 4° |
| Line 7 | 6th | 15+190 | 1528 m | 2.0 cm | 1.0 cm | WARNING | 13° |
| Line 2 | Township | 2+798 | 1575 m | 1.9 cm | 0.9 cm | WARNING | 3° |
| Line 8 | Cincinnati State | 1+228 | 1601 m | 1.9 cm | 0.9 cm | WARNING | 3°, 3° |
| Line 8 | Cincinnati State | 1+230 | 1605 m | 1.9 cm | 0.9 cm | WARNING | 3°, 3° |
| Line 6 | Forest | 4+825 | 1798 m | 1.7 cm | 0.8 cm | WARNING | 2°, 1°, 3° |
| Line 7 | Millcrest | 24+755 | 1820 m | 1.7 cm | 0.8 cm | WARNING | 3° |
| Line 2 | Inwood | 10+749 | 1871 m | 1.6 cm | 0.8 cm | WARNING | 5° |
| Line 11 | Ft Mitchell | 12+322 | 1943 m | 1.6 cm | 0.8 cm | WARNING | 16° |
| Line 12 | Ridge | 17+686 | 2340 m | 1.3 cm | 0.6 cm | WARNING | 5° |
| Line 7 | Aloysius | 26+217 | 2408 m | 1.3 cm | 0.6 cm | WARNING | 2° |
| Line 12 | Maverick | 16+242 | 2529 m | 1.2 cm | 0.6 cm | WARNING | 2° |
| Line 11 | Mutter Gottes | 5+962 | 2772 m | 1.1 cm | 0.5 cm | WARNING | 10° |
| Line 13 | McAlpin | 2+873 | 2845 m | 1.1 cm | 0.5 cm | WARNING | 2° |
| Line 12 | Llewellyn | 2+778 | 2878 m | 1.1 cm | 0.5 cm | WARNING | 3° |

