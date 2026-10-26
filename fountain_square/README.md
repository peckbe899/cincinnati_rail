# Fountain Square station model

The Fountain Square complex (Metro Lines 1, 2 and 7; TRI A/D and B) as one Python model, with the checks, drawings and viewing-angle analysis built on it. State as of 2026-10-26. The decisions and their history are in the project doc `claude/Station_Area_Maps_Log.md`, section 4.11.

## Frame

All geometry is in metres in a frame turned with the downtown grid. The origin is the KMZ reference point (-84.5125, 39.1018). u runs east along the cross streets and v runs north up Vine, which is true bearing 349°. So true north is 11° clockwise of frame north, and a true facing = frame bearing − 11°.

`fs_kmz_layout.py` turns lon/lat into the frame (spherical Mercator, R 6,378,137 m, scaled by cos lat0, then turned 11°). Depths in the model are drawing values in metres below the street.

## Files

- `fs_model.py`: the model. It holds every floor (PARTS), stair and escalator (FLIGHTS), elevator (LIFTS), TRI fare line (GATES), track (TRACKS), entrance (ENT) and cavern.
  - `flight()` sizes a flight from its rise.
  - `well()` is the opening a flight needs in the floor above.
- `fs_geom.py`: shared helpers. Street lines (NS, EW), line badges (`badges/`), and the Pan Am Tower footprint (TOWER, a proposal).
- `fs_check.py`: checks that every flight's top and foot land on a floor, every elevator stands on each level it serves, nothing overlaps, and every well sits inside its floor. It must print `problems: 0`.
- `fs_reach.py`: checks that every part can be reached from the street, and that all nine platforms connect without leaving the station.
- `fs_levels4.py`: level plans (-1 to -4), giving `fs_levels4.png`.
- `fs_stages5.py`: the build history in nine stages (1905-07 to today), giving `fs_stages.png`.
- `fs_3d.py`: the 3D cutaway.
  - Usage: `python3 fs_3d.py OUT FRAME_BEARING ELEV K EXPL EXPL2 GHOST TRI_GLASS`.
  - Current views: frame 150 at 12 (SE 139°), frame 240 at 32 (SW 229°), frame 215 at 28 (SSW 204°), each run with `1.4 0 0 1.0 0.5`.
- Viewing-angle analysis:
  - `fs_views.py` scores 216 views and writes `views.csv`.
  - `fs_views_score.py` weights the views in Ben's order (platforms, stairs, heights, TRI, uncrowded, court, sheet) and writes `views_scored.csv`.
  - `fs_views_fine.py FACING ELEVS OUT` runs a 5° and 2° check around one view.
  - `fs_views_plot.py` draws the `fs_view_analysis.png` sheet; it needs the `cand_*.png` thumbnails.
  - `fs_vis_detail.py` gives per-view diagnostics.
- `fs_kmz_layout.py` and `fs_layout_overlay.py`: Ben's platform KMZs (`kmz_fs`, `kmz_ad`, `kmz_b`) in the frame, and the overlay against the model.
- `outputs/`: the latest renders.

## Run

```
pip install -r requirements.txt
python3 fs_check.py && python3 fs_reach.py
python3 fs_levels4.py && python3 fs_stages5.py
python3 fs_3d.py fs_3d.png 240 32 1.4 0 0 1.0 0.5
python3 fs_views.py && python3 fs_views_score.py && python3 fs_views_fine.py 229 24,26,28,30,32,34,36 views_fine.csv && python3 fs_views_plot.py
```

## Known gaps (2026-10-26)

- **Platform lengths.**
  - The model is built at 500 ft for the Metro and 670 ft for TRI (locked 2026-10-05).
  - The Profiles editor has used 400 ft for the Metro since 2026-10-23, and 200 m for TRI.
- **Depths.** The model's depths are drawing values: level -1 at 5.36, -2 at 12.06, A/D at 28, B at 42. They don't yet match the Profiles editor's levels at Fountain Square (rail: Line 1 160.9 m, Line 2 153.4 m, RER-1 156.56 m, RER-2 140.59 m).
- **Stacking.** Whether stacked, spread or half-stacked platforms suit 1903-1913 is paused, pending Ben.
- **Line 7** isn't in the Profiles editor's saved alignments yet.
