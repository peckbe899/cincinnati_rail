# Intersection picks on the 1922 Sanborn plates (Mill Creek valley)

Same job as INSTRUCTIONS.md (read it first: what to record, names, precision), on the 1922 atlas, volume 1. Each plate is a double page photographed as two images, a left half (L) and a right half (R). The two halves overlap at the gutter: the same strip of streets appears near the right edge of L and the left edge of R. Treat each half as its own sheet.

## Tool

    cd data/sanborn/sbg
    python3 sb.py size 22-16L
    python3 sb.py render 22-16L OUT.jpg                     # whole half with a pixel grid
    python3 sb.py render 22-16L x0 y0 x1 y1 OUT.jpg         # zoomed crop, grid in ORIGINAL pixels of that half
    python3 sb.py check 22-16L OUT.jpg                      # draws picks22/s22-16L.json

Write one file per half: picks22/s22-16L.json, picks22/s22-16R.json, with "sheet": "22-16L" and the same fields as INSTRUCTIONS.md (intersections, widths, alleys, bends, ends, notes). Widths and alleys are optional here; intersections matter most.

## What to pick

- Every intersection of two named streets on the half, including the ones in the gutter overlap (pick them on BOTH halves: they tie the halves together) and the ones at the plate's outer edges. Precision about 10 pixels.
- Ignore the margin, the scale bar, the title block, the key and anything outside the plate's neat line.
- The plates are at 100 ft to an inch, so streets are narrow: zoom to crops of 300-500 px to read the centre of each crossing.
- Names as printed, expanded as in INSTRUCTIONS.md. Some streets were renamed between 1904 and 1922; record the 1922 name and, if a street is printed with an old name in brackets, put the bracketed name in notes.
- The old canal bed ("OLD BED MIAMI & ERIE CANAL") is not a street; railroads are not streets.

## Added 2026-10-20: plate 35 north (Clifton Heights, University, Fairview), sheet id 22-35N

Ben's georeferenced copy of 1922 plate 35 (north half): one image, 8,830 x 7,674 px, already turned north-up (no L/R halves). Tool commands as above with the sheet id 22-35N (render, size). It is at about 0.21 m a pixel, so crossings of 40-60 ft streets are 60-90 px wide: read the centre within about 10 px, using crops of 600-1,000 px.

Each reader gets a strip of the plate and writes its OWN file, picks22/s22-35N_<part>.json (with "sheet": "22-35N"), and checks it with

    python3 sb.py check 22-35N OUT.jpg picks22/s22-35N_<part>.json x0 y0 x1 y1

(the crop box is optional; give your strip's box so the check image is readable). Pick every crossing whose centre lies inside your strip, plus those within about 300 px past its edges (the overlap ties the strips together). Record bends generously on curved streets (Dixmyth, Riddle Road, Marshall, McMicken, the canal-side streets, the University drives are NOT streets). Railroads, the old canal bed and park drives are not streets. Names as printed, expanded as in INSTRUCTIONS.md (e.g. "Riddle Road", "Clifton Avenue", "West McMicken Avenue", "Straight Street", "Probasco Street", "Dixmyth Avenue", "West University Avenue").

## Added 2026-10-20 (later): plate 38 (Clifton: Ludlow Avenue, Clifton Avenue, Jefferson, Vine, Dixmyth to Woolper/McAlpin), sheet id 22-38

Ben's scan of 1922 plate 38: one image, 10,748 x 6,719 px, roughly north-up (compass rose in Burnet Woods points up), about 1.5 px a foot. NOT georeferenced: pixel coordinates are all we need. Black outside the plate is the background (rendered white). Tool commands as above with the sheet id 22-38.

Each reader gets a vertical strip and writes its OWN file, picks22/s22-38_<part>.json (with "sheet": "22-38"), checked with

    python3 sb.py check 22-38 OUT.jpg picks22/s22-38_<part>.json x0 y0 x1 y1

Pick every crossing of two streets whose centre lies inside your strip, plus those within about 300 px past its left and right edges. Precision about 10 px: use crops of 600-1,000 px. Record bends generously on curved streets (Ludlow, Dixmyth along the bottom edge, Jefferson, Clifton Avenue's bends, Lafayette, Brookline/Middleton style curving private drives only if named as streets), and ends where a street really ends (not where the plate's edge cuts it; say "plate edge" in the note for those). Names as printed, expanded ("Ludlow Avenue", "Clifton Avenue", "Jefferson Avenue", "Vine Street", "McAlpin Avenue", "Woolper Avenue", "Dixmyth Avenue", "Whitfield Avenue", "Morrison Avenue", "West McMicken Avenue", "Howell Avenue", "Terrace Avenue", "Lowell Avenue", "Bates Avenue", "Christiana Street", "Julia Ann Street", "Shields Street", "Nixon Street"...). Streets with no printed name get "?" and a note. Railroads, the canal, park drives and the lake are not streets. Add a "widths" entry (street, ft, x, y) where a width is printed.

## Added 2026-10-21: plates 66, 67, 68, 69, 70 (Corryville, Avondale, the Zoo, Woodburn, Evanston), sheet ids 22-66 ... 22-70

Ben's scans of 1922 plates 66 (Corryville / south Avondale), 67 (Woodburn), 68 (Corryville / the Zoo), 69 (eastern Avondale) and 70 (south-east Evanston): one image each, about 10,000-10,750 x 7,100-7,200 px, about 1.5 px a foot, NOT georeferenced (pixel coordinates are all we need). White outside the plate is the background. Plates are not all north-up (67, 69 and 70 are turned); that does not matter for picking. Tool commands as for 22-38 with the sheet ids 22-66 ... 22-70.

Each reader gets a vertical strip of one plate and writes its OWN file, picks22/s22-<N>_<part>.json (with "sheet": "22-<N>"), checked with

    python3 sb.py check 22-<N> OUT.jpg picks22/s22-<N>_<part>.json x0 y0 x1 y1

Pick every crossing of two streets whose centre lies inside your strip, plus those within about 300 px past its left and right edges. Precision about 10 px: use crops of 600-1,000 px. Record bends generously on curved or angled streets, and ends where a street really ends (not where the plate's edge cuts it; say "plate edge" in the note for those). Names as printed, expanded ("Vine Street", "Burnet Avenue", "Reading Road", "Auburn Avenue", "McMillan Street", "Highland Avenue", "Eden Avenue", "Euclid Avenue", "Bellevue Avenue", "Corry Street", "Daniels Street", "Charlton Street", "Calhoun Street", "Erkenbrecher Avenue", "Forest Avenue", "Rockdale Avenue", "Gilbert Avenue", "Woodburn Avenue", "Montgomery Road", "Dana Avenue", "Victory Parkway" ...; whatever the plate prints, not these guesses). Streets with no printed name get "?" and a note. Railroads, the canal, park and cemetery drives, the Zoo's paths and private lanes inside estates are not streets. Add a "widths" entry (street, ft, x, y) where a width is printed.

Disk is tight in this workspace: render your crops into your own folder under scratchpad (e.g. scratchpad/ag66a/), reuse a handful of file names instead of keeping every crop, and delete the folder's images when you finish.

## Added 2026-10-22: second read of 22-37L and 22-37R (Northside, South Cumminsville, north Camp Washington)

These two halves were read once (picks22/s22-37L.json, s22-37R.json) but sparsely: many crossings are missing, for example Spring Grove Avenue at Adelaide, Brashears and Arlington Streets, and most of the Northside grid around Hamilton Avenue, Hoffner, Knowlton, Blue Rock, Chase, Cherry, Powers, Burgoyne, Fergus, Lingo, Pullan and the side streets. Tool commands as at the top (sheet ids 22-37L, 22-37R; size about 6,000-6,300 x 7,800 px, about 0.19 m a pixel, so crossings are 50-90 px wide).

Each reader gets a vertical strip of one half and writes its OWN file, picks22/s22-37L_<part>.json or s22-37R_<part>.json (with "sheet": "22-37L" / "22-37R"; do not touch the old s22-37L.json / s22-37R.json), checked with

    python3 sb.py check 22-37R OUT.jpg picks22/s22-37R_<part>.json x0 y0 x1 y1

Pick EVERY crossing of two named streets whose centre lies inside your strip, plus those within about 300 px past its left and right edges, including crossings the old file already has (they are compared, not merged blindly). Precision about 10 px: use crops of 600-1,000 px. Record bends on curved or angled streets (Colerain Avenue, Spring Grove Avenue, Hamilton Avenue, Ludlow Avenue, Mad Anthony, Elmore, Chase, the hillside streets), and ends where a street really ends (not where the plate edge cuts it; say "plate edge" in the note). Names as printed, expanded ("Colerain Avenue", "Spring Grove Avenue", "Hamilton Avenue", "Hoffner Street", "Blue Rock Street", "Knowlton Street", "Chase Avenue", "Arlington Street", "Brashears Street", "Adelaide Street", "Sassafras Street"...; whatever the plate prints). Streets with no printed name get "?" and a note. Railroads, the canal bed, cemetery drives and private lanes are not streets.

Disk is very tight: render crops into your own folder under scratchpad (e.g. scratchpad/ag37ra/), reuse two or three file names, and delete the folder when you finish.

## Added 2026-10-23: plates 82A (central Norwood) and 83A (east Norwood), sheet ids 22-82A, 22-83A

Ben's scans of 1922 plates 82A (central Norwood: Montgomery Road, the B&O and Norwood railroad yards, Section Road area) and 83A (east Norwood: the Norwood car and machine works, Duck Creek along the east edge): one image each, 22-82A about 10,713 x 7,097 px, 22-83A about 6,769 x 6,134 px, about 1.5 px a foot (crossings of 50 ft streets are about 75 px wide), roughly north-up, NOT georeferenced (pixel coordinates are all we need). White outside the plate is the background. Tool commands as for 22-38 with the sheet ids 22-82A and 22-83A.

Each reader gets a vertical strip of one plate and writes its OWN file, picks22/s22-82A_<part>.json or s22-83A_<part>.json (with "sheet": "22-82A" / "22-83A"), checked with

    python3 sb.py check 22-82A OUT.jpg picks22/s22-82A_<part>.json x0 y0 x1 y1

Pick every crossing of two streets whose centre lies inside your strip, plus those within about 300 px past its left and right edges. Precision about 10 px: use crops of 600-1,000 px. Record bends generously on curved or angled streets (Montgomery Road, Smith Road, Section Road, the diagonal streets near the railroads, the hillside streets in the south-west), and ends where a street really ends (not where the plate's edge cuts it; say "plate edge" in the note for those). Names as printed, expanded ("Montgomery Road", "Avenue" / "Street" spelled out; whatever the plate prints, read from the plate, not guessed). Streets with no printed name get "?" and a note. Railroads and sidings, Duck Creek, factory yard lanes, and private lanes are not streets. The big numbers in circles are plate and sheet numbers, not addresses. Add a "widths" entry (street, ft, x, y) where a width is printed.

Disk is very tight: render crops into your own folder under scratchpad (e.g. scratchpad/ag82a/), reuse two or three file names, and delete the folder's images when you finish.

## Added 2026-10-24: plates 75 (east North Avondale, west Norwood) and 76 (south-east Norwood), sheet ids 22-75, 22-76

Ben's scans of 1922 plates 75 and 76: one image each, about 10,600 x 7,170 px for 22-75, about 1.5 px a foot (50 ft streets about 75 px wide), roughly north-up, NOT georeferenced (pixel coordinates are all we need). White outside the plate is the background. Tool commands as for 22-38 with the sheet ids 22-75 and 22-76. Plate 75 runs from North Avondale (Mitchell, Clinton Springs and Reading Road side in the west) across Victory Parkway and Dana Avenue to the railroads and streets of west Norwood in the east.

Each reader gets a vertical strip of one plate and writes its OWN file, picks22/s22-75_<part>.json or s22-76_<part>.json (with "sheet": "22-75" / "22-76"), checked with

    python3 sb.py check 22-75 OUT.jpg picks22/s22-75_<part>.json x0 y0 x1 y1

Pick every crossing of two streets whose centre lies inside your strip, plus those within about 300 px past its left and right edges. Precision about 10 px: use crops of 600-1,000 px. Record bends generously on curved or angled streets (Victory Parkway, the curving drives of North Avondale, Dana Avenue, the diagonal streets by the railroads), and ends where a street really ends (not where the plate's edge cuts it; say "plate edge" in the note for those). Names as printed, expanded, with the suffix the plate prints ("Avenue" / "Street" spelled out); read from the plate, not guessed. Streets with no printed name get "?" and a note. Railroads and sidings, creeks, park and estate drives, factory lanes, private lanes, and the grey/pink city-limit and subdivision boundary bands are not streets. Large spaced lettering is subdivision or estate names. Add a "widths" entry (street, ft, x, y) where a width is printed.

Disk is very tight: render crops into your own folder under scratchpad (e.g. scratchpad/ag75a/), reuse two or three file names, and delete the folder when you finish.

## Added 2026-10-25: plates 26a (southern Price Hill, Sedamsville), 26b (west Price Hill) and 29 (East Price Hill), sheet ids 22-26A, 22-26B, 22-29

Ben's scans of 1922 plates 26a, 26b and 29: one image each (22-26A about 10,520 x 7,090 px, 22-26B about 7,180 x 3,040 px, 22-29 about 10,230 x 6,030 px), about 1.5 px a foot (50 ft streets about 75 px wide), roughly north-up, NOT georeferenced (pixel coordinates are all we need). White outside the plate is the background. Tool commands as for 22-38 with these sheet ids.

- 22-26A: southern Price Hill from W 8th Street south (Phillips, Bassett Road, Elberon, Dooley, Summit, Del Monte), down the hillside to River Road and Sedamsville along the Ohio, and in the east Lower Price Hill (State Avenue, Perin Avenue, the viaducts) to the Mill Creek.
- 22-26B: west Price Hill west of 26a: W 8th Street along the top, Carnation, Amelia, Rydell and the streets around them, St. Joseph Cemetery in the south-west, Foley Road along the bottom.
- 22-29: East Price Hill and the valley: W Liberty and Glenway (Lehman, Claypool, Seminary, Warsaw, Price) south to W 8th Street, the incline and hillside streets, and in the east State Avenue, Hopkins, the Mill Creek and the railroads to Garrard.

Each reader gets a vertical strip of one plate and writes its OWN file, picks22/s22-26A_<part>.json, s22-26B_<part>.json or s22-29_<part>.json (with "sheet": "22-26A" / "22-26B" / "22-29"), checked with

    python3 sb.py check 22-26A OUT.jpg picks22/s22-26A_<part>.json x0 y0 x1 y1

Pick every crossing of two streets whose centre lies inside your strip, plus those within about 300 px past its left and right edges. Precision about 10 px: use crops of 600-1,000 px. Record bends generously on curved or angled streets (the hillside streets, River Road, the roads down the hill to Sedamsville and the valley), and ends where a street really ends (not where the plate's edge cuts it; say "plate edge" in the note for those). Names as printed, expanded, with the suffix the plate prints ("Avenue" / "Street" spelled out); read from the plate, not guessed. Streets with no printed name get "?" and a note. Railroads and sidings, inclines, creeks, cemetery and park drives, factory lanes, private lanes, and the grey/pink city-limit and subdivision boundary bands are not streets. Large spaced lettering is subdivision or estate names. Add a "widths" entry (street, ft, x, y) where a width is printed.

Disk is very tight: render crops into your own folder under scratchpad (e.g. scratchpad/ag26a1/), reuse two or three file names, and delete the folder when you finish.

## Added 2026-10-25 (later): plates 31 (South Fairmount) and 33 (North Fairmount), sheet ids 22-31, 22-33

Ben's scans of 1922 plates 31 and 33: one image each (22-31 about 10,220 x 6,870 px, 22-33 about 10,650 x 6,180 px), about 1.5 px a foot, roughly north-up, NOT georeferenced. White outside the plate is the background. Tool commands as for 22-38 with these sheet ids.

- 22-31: South Fairmount: from Queen City Avenue and the Westwood side in the north-west, the Fairmount hillside streets (Baltimore and the streets round it), large estate tracts in the middle and west, down to W Liberty Street and Lehman Road along the bottom; in the east the railroads, State Avenue and the Mill Creek to Garrard.
- 22-33: North Fairmount: Carll Street along the top, Baltimore, Waverly and the streets of North and South Fairmount in the middle, the Westwood Avenue / Queen City Avenue side along the bottom, the hillside subdivisions in the north-west, and the railroads and Mill Creek in the east (a key box in the top right is not part of the map).

Each reader gets a vertical strip and writes its OWN file, picks22/s22-31_<part>.json or s22-33_<part>.json (with "sheet": "22-31" / "22-33"), checked with

    python3 sb.py check 22-31 OUT.jpg picks22/s22-31_<part>.json x0 y0 x1 y1

Same rules as the 26a/26b/29 section above: every crossing in the strip plus about 300 px past its edges, about 10 px precision from 600-1,000 px crops, bends on curved streets, real ends (say "plate edge" for plate-edge cuts), names as printed and expanded, "?" for unnamed, widths where printed; railroads, inclines, creeks, cemetery and park drives, private lanes and boundary bands are not streets; large spaced lettering is subdivision or estate names. Crops in your own folder, deleted when you finish.

## Added 2026-11-08: plates 25 (south-west Price Hill) and 28 (West Price Hill), sheet ids 22-25, 22-28

Ben's scans of 1922 plates 25 and 28: one image each (22-25 about 10,790 x 7,120 px, 22-28 about 10,330 x 6,040 px), about 1.5 px a foot (50 ft streets about 75 px wide), roughly north-up, NOT georeferenced. White outside the plate is the background. Tool commands as for 22-38 with these sheet ids.

- 22-25: south-west Price Hill below West Eighth Street (along the top): Academy Avenue, the streets around Seegar and Bassett in the east, large estate tracts in the middle and west, and Mount Echo Park in the south-east corner.
- 22-28: West Price Hill: Glenway Avenue running diagonally across the middle, Warsaw, Vincent, Midland, St. William and the dense grid round them; West Eighth Street along the bottom.

Rule 12 (docs/sanborn/RULES.md): these picks are the plate's controls, so each strip is read twice, by two readers working independently. Each reader writes its OWN file, data/sanborn/picks22_reads/22-25/<read>_<part>.json (read A or B, part 1-6; "sheet": "22-25"), and must not open any other reader's file or anything under sbg/picks22. Only crossings both reads agree on within 60 px become picks (sbg/picks22/s22-25_<part>.json, written by tools/sanborn/complete/merge_reads.py).

Same rules as the 26a/26b/29 section: every crossing of two streets whose centre lies inside the strip plus about 300 px past its left and right edges, about 10 px precision from 600-1,000 px crops, bends on curved streets, real ends (say "plate edge" for plate-edge cuts), names as printed and expanded, "?" for unnamed, widths where printed; railroads, inclines, creeks, cemetery and park drives, private lanes and boundary bands are not streets; large spaced lettering is subdivision or estate names. Crops in your own folder, deleted when you finish.

## Added 2026-11-09: plates 39 (north Clifton) and 40 (Winton Place, the Mill Creek valley), sheet ids 22-39, 22-40

Ben's scans of 1922 plates 39 and 40: one image each (22-39 about 10,800 x 7,100 px, 22-40 about 9,790 x 7,070 px), about 1.5 px a foot (50 ft streets about 75 px wide), roughly north-up, NOT georeferenced. White outside the plate is the background. Tool commands as for 22-38 with these sheet ids.

- 22-39: Clifton north of McAlpin Avenue (along the bottom): Middleton Avenue, Clifton Avenue, Lafayette Avenue and the curving streets round them, large estates and farms in the west, cemetery ground in the east (its drives are NOT streets), Spring Grove Avenue and the railroads and canal across the top-left corner.
- 22-40: Winton Place and the Mill Creek valley: Spring Grove Avenue, the dense grid in the west, factories, rail yards and many sidings in the middle (NOT streets), the Mill Creek, a race track, and street grids at the east and south-east edges.

Rule 12, as for 25 and 28: each strip is read twice, by two readers working independently. Each reader writes its OWN file, data/sanborn/picks22_reads/22-39/<read>_<part>.json (read A or B, part 1-6; "sheet": "22-39"), and must not open any other reader's file or anything under sbg/picks22. Only crossings both reads agree on within 60 px become picks (tools/sanborn/complete/merge_reads.py).

Same rules as the 26a/26b/29 section: every crossing of two streets whose centre lies inside the strip plus about 300 px past its left and right edges, about 10 px precision from 600-1,000 px crops, bends on curved streets, real ends (say "plate edge" for plate-edge cuts), names as printed and expanded, "?" for unnamed, widths where printed; railroads and sidings, the canal, creeks, cemetery, park and estate drives, the race track, factory lanes and boundary bands are not streets; large spaced lettering is subdivision or estate names. Crops in your own folder, deleted when you finish.

## Added 2026-11-13: plate 45 (Northside north of Chase Avenue, College Hill slope), sheet id 22-45

Ben's scan of 1922 plate 45: one image, about 10,680 x 6,190 px, about 1.5 px a foot (50 ft streets about 75 px wide), roughly north-up, NOT georeferenced. White outside the plate is the background. Tool commands as for 22-38 with this sheet id.

- 22-45: Northside north of Hanfield Street and Knowlton Street (along the bottom): Hamilton Avenue running north-west to south-east through the middle, Chase Avenue, Bruce Avenue, Westmoreland, Pullan and Haight Avenues, the curving North Argyle streets, Colerain Avenue down the left edge, the street grids of the north-west (Martha, Tarrant, Carlin, Frederick, Schneider), large estates and City of Cincinnati park property in the north-east, Spring Grove Cemetery down the right edge (its drives are NOT streets) with a railroad beside it.

Rule 12, as for 39 and 40: each strip is read twice, by two readers working independently. Each reader writes its OWN file, data/sanborn/picks22_reads/22-45/<read>_<part>.json (read A or B, part 1-6; "sheet": "22-45"), and must not open any other reader's file or anything under sbg/picks22. Only crossings both reads agree on within 60 px become picks (tools/sanborn/complete/merge_reads.py).

Same rules as the 26a/26b/29 section: every crossing of two streets whose centre lies inside the strip plus about 300 px past its left and right edges, about 10 px precision from 600-1,000 px crops, bends on curved streets, real ends (say "plate edge" for plate-edge cuts), names as printed and expanded, "?" for unnamed, widths where printed; railroads and sidings, creeks, cemetery, park and estate drives, property lines and boundary bands are not streets; large spaced lettering is subdivision or estate names.  Crops in your own folder, deleted when you finish.

## Added 2026-11-13: plate 43 (Northside west: Colerain Avenue, Wesleyan Cemetery, Hoffner Avenue), sheet id 22-43

Ben's scan of 1922 plate 43: one image, about 10,540 x 7,240 px, drawn at 100 ft to an inch, so about 3 px a foot (50 ft streets about 150 px wide: twice the other plates), roughly north-up, NOT georeferenced. White outside the plate is the background. Tool commands as for 22-38 with this sheet id.

- 22-43: Colerain Avenue running east along the top and then south-east down to the bottom right, Hanfield Street and Chase Avenue at the top, Blue Rock Street, Hoffner Avenue right across the plate two thirds of the way down, Powers Street along the bottom, the north-south avenues of the west and south (Cass, Herron, Runnymeade, Sylvan, Edgewood, Llewellyn, Borden, Kirby, Jerome, Florida), the grid at the east (Lakeman, Witler, Delaney, Cherry, Turrill, Cooper). Wesleyan Cemetery fills the middle (its drives are NOT streets); the West Branch of Mill Creek winds through the west; railroads cross the bottom right.

Rule 12, as for 45: each strip is read twice, by two readers working independently. Each reader writes its OWN file, data/sanborn/picks22_reads/22-43/<read>_<part>.json (read A or B, part 1-6; "sheet": "22-43"), and must not open any other reader's file or anything under sbg/picks22. Only crossings both reads agree on within 60 px become picks (tools/sanborn/complete/merge_reads.py); at this plate's scale that is tighter than usual, so read each centre carefully: the centre is where the two streets' centre lines meet.

Same rules as the 26a/26b/29 section: every crossing of two streets whose centre lies inside the strip plus about 300 px past its left and right edges, about 10 px precision from 600-1,000 px crops, bends on curved streets, real ends (say "plate edge" for plate-edge cuts), names as printed and expanded, "?" for unnamed, widths where printed; alleys count as streets when named; railroads and sidings, creeks, cemetery drives, property lines and boundary bands are not streets; large spaced lettering is subdivision or estate names. Crops in your own folder, deleted when you finish.

## Added 2026-11-13: plate 44 (Northside: Hamilton Avenue, Spring Grove Avenue, the canal), sheet id 22-44

Ben's scan of 1922 plate 44: one image, about 10,770 x 7,220 px, about 1.5 px a foot (50 ft streets about 75 px wide), roughly north-up, NOT georeferenced. White outside the plate is the background. Tool commands as for 22-38 with this sheet id.

- 22-44: central Northside. Chase Avenue along the top left, Hamilton Avenue running down from the top left past Knowlton and Blue Rock to Hoffner and Cooper, Lingo, Knowlton and Bethel streets, the Vandalia railroad crossing the plate diagonally (south-west to north-east) beside a diagonal avenue, Fergus, Bonn and other streets in the middle, Spring Grove Avenue running east across the middle-right, Mad Anthony / Apple / Cooper in the lower left, and in the lower right the Mill Creek, the Miami and Erie Canal bed, railroad yards and sidings.

Rule 12, as for 43 and 45: each strip is read twice, by two readers working independently. Each reader writes its OWN file, data/sanborn/picks22_reads/22-44/<read>_<part>.json (read A or B, part 1-6; "sheet": "22-44"), and must not open any other reader's file or anything under sbg/picks22. Only crossings both reads agree on within 60 px become picks (tools/sanborn/complete/merge_reads.py).

Same rules as the 26a/26b/29 section: every crossing of two streets whose centre lies inside the strip plus about 300 px past its left and right edges, about 10 px precision from 600-1,000 px crops, bends on curved streets, real ends (say "plate edge" for plate-edge cuts), names as printed and expanded, "?" for unnamed, widths where printed; railroads and sidings, the canal and canal bed, creeks, cemetery and park drives, factory lanes, property lines and boundary bands are not streets; large spaced lettering is subdivision or estate names. Crops in your own folder, deleted when you finish.

## Added 2026-11-13: plate 80 (St. Bernard: St. Mary's Cemetery), sheet id 22-80

Ben's scan of 1922 plate 80: one image, about 9,300 x 7,150 px, about 1.5 px a foot (50 ft streets about 75 px wide), roughly north-up, NOT georeferenced. White outside the plate is the background. Tool commands as for 22-38 with this sheet id.

- 22-80: St. Bernard. A long avenue across the top third (printed AVENUE at the right), a railroad along the top edge, a street grid in the middle and lower left, a diagonal avenue down the left edge to an avenue along the bottom, St. Mary's German Catholic Cemetery filling the right half (its drives and paths are NOT streets), David Brown's estate and Schroeder's estate, and a creek in the top right.

Rule 12, as for 43, 44 and 45: each strip is read twice, by two readers working independently. Each reader writes its OWN file, data/sanborn/picks22_reads/22-80/<read>_<part>.json (read A or B, part 1-6; "sheet": "22-80"), and must not open any other reader's file or anything under sbg/picks22. Only crossings both reads agree on within 60 px become picks (tools/sanborn/complete/merge_reads.py).

Same rules as the 26a/26b/29 section: every crossing of two streets whose centre lies inside the strip plus about 300 px past its left and right edges, about 10 px precision from 600-1,000 px crops, bends on curved streets, real ends (say "plate edge" for plate-edge cuts), names as printed and expanded, "?" for unnamed, widths where printed; railroads and sidings, creeks, cemetery and estate drives, property lines and boundary bands are not streets; large spaced lettering is subdivision or estate names. Write the JSON file as plain UTF-8 without a byte-order mark. Crops in your own folder, deleted when you finish.
