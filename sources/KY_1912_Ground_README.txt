Kentucky 1912 ground (maps 1 and 2), riverworks window
EPSG:26916, 2 m, int16 decimetres, nodata -32768. Same grid as Canon_Riverworks.

ky1912_ground_dm.tif     Kentucky land only. I4 surface (cleaned LiDAR; Kentucky is outside the 1912 survey)
                         with every post-1912 work in Z_all rebuilt: I-71/75, I-471, I-275 and its interchange,
                         the Covington, Newport and Dayton floodwalls/levees, bridge approaches.
ky1912_delta_vs_I4_dm.tif  Change from the I4 surface (positive = cut refilled, negative = fill removed).

Method: thin-plate solve over the zones at 4 m, surrounding ground held fixed, pulled toward 1914 USGS
20 ft contours (West and East Cincinnati 1:62,500) that were labelled on unchanged ground and carried
into the zones. 23 zones, 5.50 km2; change p5 / p50 / p95 = -4.1 / +0.1 / +11.8 m.

map2_relief.jpg   Map 2 (alternate 1912) re-rendered with this ground.
ky_check.jpg      Before/after crops: Covington, Newport, Bellevue/Dayton (red = zone edge, 20 ft contours).
ky_over.jpg       Overview: green = raised, magenta = lowered, orange = modern motorways.

Not yet done: 1912 river level (bank sits on the modern pool); Kentucky terraces belong to map 3 only.
