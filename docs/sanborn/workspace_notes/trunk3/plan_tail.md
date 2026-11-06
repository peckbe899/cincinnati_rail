## North of Mitchell to the borders (Version 128, 26 October 2026)

Code: `trunk3/north.py` (frames), `trunk3/build.py` (lines), `trunk3/install_north.py` (installer, base `deckpage/*_v127.json`), `trunk3/check.py`, `trunk3/tv_profile.py`.

- Split at s 8,080 (end of the Mitchell step-outs), no crossings. West group (ORR X2, RER B, APEx Dayton) on one curve left onto the Southwest Chief straight: Dayton 3,532 m, B 3,523 m, X2 3,514 m. East group (APEx Norwood, ORR/TV shared pair) straight on to s 8,821, then one 2,352 m curve onto the Norwood Central axis; the curve touches the Transcontinental KMZ line's middle straight (within 42 m of the KMZ).

- APEx Dayton follows the ORR APEx alignment (APX-4a, St Bernard-Middletown) beyond Ivorydale, including its own line through Lockland, to the border (N 4,347,000). The APEx Routes Southwest Chief lines were dropped (Ben, 26 October).

- RER B west of Dayton through Ivorydale (island; X2 steps out round it as at Mitchell), Elmwood Place and Paddock. It crosses over APEx between Paddock and Fairgrounds, keeps its own line by Fairgrounds, Arlington Heights and Lockland/Reading, and runs east of APEx from about N 4,345,900 to the border (Aviation). Platforms re-placed on the new line.

- ORR X2 drawn to the plan window edge (N 4,339,800).

- Spring Grove Avenue moved up to 12.5 m west through Ivorydale, clearing X2's deck edge by 3 m (Ben: shift it west, keep APEx straight). Kept on rebuilds through `wh/street_shifts.json`, read by `wh/build_osm.py`.

- Norwood branch (Ben: option B). Four tracks at 4.5 m to the TV junction just east of Reading Road (Aloysius). TV peels off south; the TV inbound track crosses ORR outbound on the level. TV then crosses over ORR and APEx at ground on one pair of 2,550 m curves (diagonal 6.25 deg), clearing them by 7.3 m or more between Norwood frame s 3,491 and 3,694, and lands north onto T10/T9 by s 3,899. ORR then takes one S into the station's 8.25 m gap (T4/T2).

- Levels (approximate, from the ground data). ORR and APEx drop 2% from s 3,250 to about 170.3 m, then climb about 1.7% to the platforms (about 178 m, roughly 7 m under the street). TV stays on the railway formation; Section Avenue has to rise about 4 m over it.

- Ben's "middle-aligned S" alternative (TV kept in the middle, ORR swinging out) was not used. ORR would need to swing a full pair width out and back, so it is no narrower than option B.

## Still open

- Inner Ring west end (J7) and OH-75 cross the Norwood branch near Broerman; bridge needed (unchanged).

- Millvale blocks under the new west viaduct.
