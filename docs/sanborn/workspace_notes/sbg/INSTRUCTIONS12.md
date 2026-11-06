# Intersection picks on the 1912 City Topographic Survey (georeferenced)

The 1912 survey is already in map coordinates (UTM 16N metres). You read named street intersections straight off it, in metres, to use as control points for the 1904 Sanborn sheets.

## Tool

    cd data/sanborn/sbg
    python3 r12.py render E0 N0 E1 N1 OUT.jpg            # window with a grid labelled in metres (E to the right, N up)
    python3 r12.py check AREA E0 N0 E1 N1 OUT.jpg        # draws picks12/AREA.json on a window

Work in windows of 150-400 m. The survey is 0.5 m per pixel, streets are drawn as double lines, names are printed along them.

## What to record

One file for your area: picks12/AREA.json

    {"area": "AREA",
     "intersections": [ {"a": "Hopple Street", "b": "Colerain Avenue", "E": 712951.5, "N": 4334902.0, "kind": "cross"} ],
     "notes": "..."}

- Every place where two named streets meet inside your box (crossings and T-junctions). The point is where the two centrelines cross: the middle of the open crossing, not a block corner. Read it to about 1 m (2 pixels) from the grid.
- Names as printed, expanded: St. -> Street, Ave./Av. -> Avenue, Pl. -> Place, W. -> West. Keep the printed spelling. If a name is only printed further along the street, follow the street to find it.
- Skip railroads, the canal, the creek and unnamed lanes.
- Cover the whole box systematically (strip by strip), then run check on each part and fix what is off.
