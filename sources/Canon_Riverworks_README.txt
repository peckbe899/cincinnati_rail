Canon riverworks: Ohio Embankment, Lunken levees, Mill Creek deck, lower Mill Creek culvert
2 m grid, EPSG:26916, elevations NAVD88. All rasters share one window (Sedamsville to Belterra, river to Camp Washington).

Files (per map)
  mapN_riverworks_target_dm.tif  target elevation, decimetres (nodata -32768)
  mapN_riverworks_mode.tif       1 = force (deck, quai bas), 2 = fill only (never cuts), 0 = untouched
  mapN_riverworks_delta_dm.tif   change in decimetres against the base used here
                                 (map 3: LiDAR; map 2: the I4 1912 surface). Re-apply target+mode to a new base.
  mapN_riverworks_preview.jpg    hillshade, change tinted (orange = fill, blue = cut)
  rw_wall_arc.geojson            the wall line: your Ohio River outline from Sedamsville to Belterra
  rw_params.json                 every number below

Levels (Cincinnati gauge zero 428.05 ft NAVD88)
  Embankment wall / quai haut  70 ft = 151.8 m, never raised
  Lunken levees                83 ft = 155.8 m (raised after 1937)
  Quai bas                     142.0 m, 12 m wide along the water (assumption)
  Quai haut                    flat to 52 m from the bank or the full reclaimed strip, then 3.5% down to existing
                               ground (3.5% = the real slope from the CUT plaza down to the West End)

Map 3 (2026)
  Embankment: Sedamsville to Riverbend/Belterra along the outline, gap at the Little Miami.
  Lunken: real levee ring raised to 155.8 m with 1:3 sides; new levee along the LMR east bank to high ground;
          airfield lifted 1 m on Metro spoil (1.9 km2).
  Mill Creek deck: 151.8 m where it meets the Embankment, rising evenly to 160 m at Camp Washington north
          (4.84 km); flat over the rail corridor and creek, then 3.5% down to existing ground on both sides.
          Yards under the deck sit 8.5 m below it (cut deepest by Chinatown, none north of Hopple).
Map 2 (1912)
  Embankment: Mill Creek mouth to Sawyer Point only (built 1903-12), same section.
  Lower Mill Creek culvert (1903-08): channel filled to the surrounding floor from the mouth to about Harrison Ave.

Kentucky riverworks, map 3 only (added 2026-10-08)
  map3_ky_terraces_target_dm.tif / _mode.tif / _delta_dm.tif   same conventions (mode 1 force, 2 fill only)
  ky_terr_params.json, ky_terraces_check.jpg (segments coloured)
  Built on the river outline (no push into the river), to 70 ft = 151.8 m, only where the land behind the bank is
  below 151.8 m and open to the river; elsewhere the bank is already high.
  Covington (Ludlow line to the Licking)   3 tiers: 142.0 m quai 0-15 m from the water, 147.0 m promenade 15-30 m,
                                           151.8 m 30-45 m, then 3.5% down (raised grade, like Cincinnati)
  Newport (Licking to Bellevue line)        2 tiers: 142.0 m wharf 0-20 m, 151.8 m 20-35 m, then 1:3 down
  Bellevue-Dayton (to the Fort Thomas bluff) 2 tiers: 142.0 m walk 0-10 m, 151.8 m 10-20 m, then 1:3 down
  Bromley-Ludlow                           riprap 1:2 from the water to 151.8 m, 8 m crest, 1:3 back
  Licking, both banks to Threemile Creek   wall to 151.8 m at the bank, 8 m crest, 1:3 back
  Tiebacks to ground at 151.8 m            Threemile Creek line (both banks), Bromley west end, Dayton east end
  Real floodwalls and riverside fills within 400 m of the Kentucky bank are taken back to the 1912 ground.
  Dayton marina basin (0.076 km2) filled to the ground around it, about 144.2 m.
  map3_relief.jpg now includes all of this.
