Map 3 base: real-only works rebuilt (2026-10-08, m3_rebuild.py)

map3_realonly_delta_dm.tif   Full LiDAR grid (EPSG:26916, 2 m, int16 decimetres, 0 = unchanged). Add to the 2 m LiDAR.
                             Inside each zone the rebuilt surface replaces the LiDAR outright (lanes and pads go too),
                             feathered over about 8 m at the edges.
realonly_report.json          Per zone: area, labelled 1950s contours, constraint pixels, change p5/p50/p95 (m).
map3_realonly_check.jpg       Six largest zones: LiDAR (zone outlined) | rebuilt.

What is rebuilt: zones v2 (map 3 real-only works: I-75 south of the I-74 junction, I-71 south of Rookwood,
Fort Washington Way and the Ohio Brent Spence approach, 6th St Expressway, riverfront stadiums, the real I-275
stretches canon doesn't use), 3.45 km2, plus Dayton's raised modern riverfront (0.36 km2).

Method: per zone, a thin-plate surface over the zone at 4 m with the surrounding LiDAR held fixed, pulled toward the
USGS 1:24,000 sheets' 10 ft contours (Cincinnati East/West 1953, Covington and Newport 1955 (the 1950/1952 editions
leave Ohio blank), Addyston 1954, Madeira and Withamsville 1953). Contours are labelled by the nearest 10 ft of
LiDAR on unchanged ground; a contour is used only with 6+ pixels in the zone and a self-consistent fit. Flat basin
zones downtown have no contours inside, so they are filled from their edges. The strip north of 39.25 N has no
1:24,000 sheet in the set and is filled from its edges too.

map3_base_ground_dm.tif (updated 2026-10-08)   Map 3 base over the riverworks window (same grid as Canon_Riverworks):
  16.0 x 12.2 km, 8000 x 6105 cells of 2 m, heights in decimetres (0.1 m steps), EPSG:26916.
  LiDAR + the real-only rebuild, with the building and street imprint taken out so developed ground reads as terrain
  (m3_smooth.py): 80 m trend + residual; on gentle ground a 24 m closing fills the street network; area opening and
  closing at 4.8 ha flatten pads, blocks and hillside terraces onto the trend while landforms and long ravines stay;
  18 m median, 3 m Gaussian, 8 m more on flat ground. The cells are 2 m but the smallest relief left is about 15-20 m
  across. Computed with a 1.2 km margin of real LiDAR and feathered into it over the outer 300 m, so the edge equals
  the LiDAR (largest difference on the border 0.002 m). Canon interstates, riverworks and Kentucky works go on top.
map3_edge_check.jpg   Real LiDAR above the line, this base below, at the north edge.
