# Canon interstate earthworks (map 3)

Built from Ben's New Interstates.kmz (I-75 Alignment, I-71 Reroute, I-275 Loop, Middle Ring), clipped to the LiDAR extent.

## What is carved

Only the stretches that do not already ride an existing freeway or trunk road (within 45 m). Where an alignment follows an existing freeway, the LiDAR already has it.

## Design assumptions

- Max grade 5%. Vertical curves no tighter than 6 km radius.

- Formation 40 m wide. Cut and fill side slopes 1:2.

- Bridge where the deck is more than 12 m above ground. Tunnel where the cut is deeper than 30 m. Bridges and tunnels leave the ground untouched, as in the LiDAR.

- Ohio crossings: the deck stays at least 167 m NAVD88 over the river. That is 163.0 m low steel plus 4 m of structure. The low steel figure is the Brent Spence companion bridge clearance, 81.2 ft over normal pool 453.6 ft (USCG public notice D08r PN 921-24).

- I-75 Price Hill: trench at least 7 m below ground with vertical walls (tracker 4B). The as-built depth runs 7 to 20 m, median 10 m.

- The profile is a least-absolute-deviation fit to ground under those limits. It is pinned to the existing freeway grade within 400 m of each end.

- No carving within 1.5 km of where a line leaves the extent.

- Interchanges and ramps are not modelled.

## Files

- **map3_canon_interstates_delta_dm.tif:** new ground minus LiDAR, in decimetres, EPSG:26916, on the LiDAR 2 m grid. Add it to the map 3 base.

- **canon_interstates_profiles.json:** stations every 10 m, with ground, design grade and type.

- **canon_interstates_structures.geojson:** grade, trench, bridge and tunnel runs, with deck range and maximum cut and height.

- **hw_profiles.png, hw_views.jpg:** long sections and before/after hillshades.
