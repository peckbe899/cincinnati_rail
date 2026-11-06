# Sanborn intersection picks (1904 Cincinnati atlas)

You read street intersections off scanned Sanborn fire-insurance sheets so the sheets can be georeferenced and the streets rebuilt as straight lines between intersections. Precision matters: every point must be the true centre of the crossing, to within about 15 page pixels.

## Tool

    cd data/sanborn/sbg
    python3 sb.py size SHEET
    python3 sb.py render SHEET OUT.jpg                     # whole sheet with a pixel grid
    python3 sb.py render SHEET x0 y0 x1 y1 OUT.jpg         # zoomed crop, grid labelled in ORIGINAL page pixels
    python3 sb.py check SHEET OUT.jpg                      # draws your saved picks on the sheet

All coordinates are ORIGINAL page pixels (x to the right, y down, from the top-left corner of the scan). Put your renders in your own scratch folder, not in sbg/picks.

Work method per sheet: render the whole sheet, list the streets and their labels, then zoom on each intersection (crop windows of about 300-600 px) and read the centre off the grid. Save the JSON, run `check`, look at it, fix anything off, save again.

## What to record

Write one file per sheet: `picks/s<SHEET>.json` (e.g. picks/s38.json):

    {
      "sheet": 38,
      "intersections": [
        {"a": "Freeman Avenue", "b": "West 8th Street", "x": 812, "y": 236, "kind": "cross"},
        {"a": "Freeman Avenue", "b": "Van Horne Street", "x": 812, "y": 735, "kind": "T"}
      ],
      "widths": [ {"street": "West 7th Street", "ft": 70} ],
      "alleys": [ {"name": "Wingate Alley", "x1": 900, "y1": 1500, "x2": 2400, "y2": 1520, "ft": 12} ],
      "bends": [ {"street": "Freeman Avenue", "x": 800, "y": 3400, "note": "turns onto iron bridge"} ],
      "ends":  [ {"street": "Kenyon Avenue", "x": 3300, "y": 2700, "note": "dead end at railroad"} ],
      "notes": "anything odd"
    }

- **intersections**: every place on the sheet where two streets meet (crossings and T-junctions), including streets that only just enter the sheet, as long as the crossing centre itself is on the sheet. The point is where the two street CENTRELINES cross: the middle of the open crossing between the four (or two) block corners, not a block corner and not the label. For a T-junction, the point is where the ending street's centreline meets the through street's centreline. Include crossings with named alleys (put the alley as a or b). kind = "cross" or "T".
- **names**: as printed on the sheet, with abbreviations expanded: St. -> Street, Av. -> Avenue, Al. -> Alley, Pl. -> Place, W. -> West, E. -> East. Numbered streets as digits: "West 8th Street", "East 5th Street" (the sheet may print "W. 8th" or "W. EIGHTH"). Keep the printed spelling of the name itself. If a cross street's name is printed only on a neighbouring sheet, use the name it carries there if you can tell from the key map below; otherwise write "?" and describe it in notes.
- **widths**: the printed street width in feet (labels like 60' or 50 ft printed in the street), one entry per street per sheet.
- **alleys**: unnamed or named alleys that do not cross a street on this sheet as a full crossing: give the alley centreline from one end to the other (where it meets the bounding streets), name if printed ("" if not), width in feet if printed (null if not).
- **bends**: where a street changes direction between two intersections (curves, angle points).
- **ends**: where a street stops without meeting another street (dead ends, the edge of a rail yard, a street stopping at the river).

Ignore railroad tracks, the canal itself and building details. Do not guess intersections that are off the sheet.

## Key maps (where sheets sit)

Volume 1 key map: data/sanborn/km1.jpg (sheets 1-83, West End and the CBD west of Main).
Volume 2 key map: data/sanborn/km2.jpg (sheets 101-200, CBD east of Main, OTR east, Mt Auburn).
Volume 3 key map: data/sanborn/km3.jpg (sheets 201-305, north of Liberty).

Volume 5 key map: data/sanborn/km5.jpg (sheets 451-555, Price Hill, Fairmount, Millvale).
Volume 6 key map: data/sanborn/km6.jpg (sheets 601-716), with a sharper crop of Northside, South Cumminsville and Camp Washington north (sheets 601-635) in data/sanborn/km6_northside.jpg.

Sheets 233, 234, 245, 246, 253 and 254 cross the Mill Creek rail yards: pick every street intersection, including streets that stop at the yards (record those stops as ends).

## Added 2026-10-18: Mt Auburn, Walnut Hills, Mt Adams

Volume 4 key map: data/sanborn/km4.jpg (sheets 311-415, north of McMillan; sheets 325-332 are the strip south of McMillan around Kemper Lane, Gilbert and Columbia Avenue). Volume 4 sheets are Library of Congress scans (about 6,500 x 7,800 px), larger than the volume 2 pages (4,125 x 4,763): crop windows of 600-1,000 px work better there.

Volume 2 sheets 161-198 are Mt Auburn and the streets toward McMillan; 199 and 200 are Mt Adams and the Eden Park edge; 107-110 and 127-130 are the east riverfront and the foot of Mt Adams (Front, Martin, Pavilion, Hill, Gregory, Celestial).

Streets that continue from neighbouring sheets: always write the street's full name as printed on THIS sheet (or on the neighbouring sheet if this sheet only shows a stub), spelled the same way each time, so the same street joins across sheets. If a street changes name at a crossing (for example a Street becoming an Avenue), record both names at that crossing and say so in notes. Hillside streets often curve: record bends generously (every 100-200 px along a curve), and record dead ends at steps, hillsides and park edges as ends. Stairways printed as streets ("steps") go in notes, not as streets.

## Added 2026-10-20: the rest of Volume 3 (Clifton Heights, Fairview, Corryville west, Burnet Woods, the hill above Camp Washington)

Sheets: 228-232, 237-244, 248-252, 256-271, 276-278, 283-286, 290-292, 296-300 (key map km3.jpg). Volume 3 sheets are Library of Congress scans (6,488 x 7,795 px): crop windows of 600-1,000 px work better than the 300-600 px used on volume 2.

These sheets join sheets that are already picked and on the map (219-227, 233-236, 245-247, 253-255, 272-275, 279-282, 287-289, 293-295, 301-305, and volume 2 sheets 161-200 east of Vine). Before you start a sheet, open the picks of its already-picked neighbours (sbg/picks/sNNN.json) and copy their spelling of every street that continues onto your sheet, so the same street joins across sheets. Streets known to end at the edge of the mapped area and continue onto your sheets include Renner Street (219), West Clifton Avenue (219, 220), Warner (236; write "Warner Street" unless the sheet prints otherwise), Gilmore Street and Gourd Street (275, 282, 289). Where a street crosses the edge into a picked neighbour, also pick its crossings that lie on YOUR sheet only; do not re-pick crossings that sit on the neighbour.

Hillside streets (Fairview, Ravine, Ziegler, McMicken hill, Clifton Heights, the streets climbing from Camp Washington) curve: record bends every 100-200 px along a curve. Record dead ends at hillsides, steps, parks (Burnet Woods) and rail yards as ends. Steps printed as streets go in notes, not as streets.
