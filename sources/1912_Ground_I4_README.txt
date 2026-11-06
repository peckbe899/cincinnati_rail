1912 ground surface, I4 method (full 1912 City Topographic Survey extent)

I4_1912_ground_dm.tif
  Ground elevation in decimetres NAVD88 (int16, nodata -32768), 2 m grid, EPSG:26916 (UTM 16N).
  Inside the survey: LiDAR large-scale shape with buildings, streets and big pads erased,
  plus the 1912 contour surface's fine texture (below ~30 m). Works zones use the 1912 surface.
  Outside the survey: smoothed LiDAR with buildings erased. Not 1912 ground; use the cover mask.

I4_1912_cover.tif
  1 = inside the 1912 survey cover (holes filled, specks under 0.1 km2 dropped). 270 km2.

I4_preview.jpg
  8 m hillshade: I4 inside the survey, raw LiDAR outside, survey edge in red.

Built from 67 tiles (3 km cores, 400 m overlaps, tent blend).
12 tiles had no usable 1912 contours (outside the survey):
  t03 t06 t09 t12 t19 t20 t26 t27 t33 t41 t42 t56
Median surface difference between overlapping tiles: 0.46 m. Larger differences
(up to ~17 m at p95) are confined to works zones near the river, where each tile's
1912 labelling differs; the blend averages them.

Update 2026-10-08: tiles k00-k05 added (no 1912 cover; cleaned LiDAR) so the surface reaches the south edge of
the riverworks window in Kentucky. I4_1912_ground_south_ext_dm.tif covers 4321822-4325522 N (same grid);
lay it over I4_1912_ground_dm.tif. The full rebuilt mosaic is 32 MB, over the transfer limit.
