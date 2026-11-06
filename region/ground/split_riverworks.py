"""Split the combined 2026 riverworks layer into its works, so each can carry its own years.

The layer `works/riverworks_2026_*` holds four works in one raster (the rest of the Ohio Embankment, the Mill Creek deck,
the Lunken levees and the Lunken airfield lift). This writes `works/riverworks_2026_part.tif` (uint8 on the same
grid): 1 Embankment, 2 Mill Creek deck, 3 Lunken (levees and the airfield lift, both 1937-1941 by Ben's ruling).

Rule (geometry, checked by the areas it gives): a changed cell is the deck where it is nearer the deck axis than the
Embankment wall line and north of the deck's start on the Embankment; Lunken where it lies east of E 721,000 and
either its target is above the Embankment wall (the levee crest, 155.8 m) or it is more than 300 m from the wall line
(the airfield interior); the Embankment otherwise.

    python -m region.ground.split_riverworks
"""
from __future__ import annotations

import json

import numpy as np
import rasterio
from scipy.spatial import cKDTree
from shapely.geometry import LineString

from .layers import GROUND, ND

PARTS = {1: "ohio_embankment_rest", 2: "mill_creek_deck", 3: "lunken"}


def _dense(coords, step=4.0):
    ls = LineString(coords)
    n = max(2, int(ls.length / step))
    return np.array([ls.interpolate(i * ls.length / n).coords[0] for i in range(n + 1)])


def main():
    with rasterio.open(GROUND / "works/riverworks_2026_mode.tif") as m, rasterio.open(GROUND / "works/riverworks_2026_target_dm.tif") as t:
        mode = m.read(1); tgt = t.read(1); tr = m.transform; prof = m.profile
    ys, xs = np.nonzero(mode > 0)
    X = tr.c + (xs + 0.5) * tr.a; Y = tr.f + (ys + 0.5) * tr.e
    axis = json.loads((GROUND / "works/riverworks_params.json").read_text())["axis_utm"]
    wall = json.loads((GROUND / "works/embankment_wall_line.geojson").read_text())["coordinates"]
    d_axis = cKDTree(_dense(axis)).query(np.column_stack([X, Y]))[0]
    d_wall = cKDTree(_dense(wall)).query(np.column_stack([X, Y]))[0]
    tz = tgt[ys, xs] / 10.0
    part = np.ones(len(xs), np.uint8)
    deck = (d_axis < d_wall) & (Y > axis[0][1] - 50)
    part[deck] = 2
    lunken = (X > 721000) & ((tz > 152.5) | (d_wall > 300)) & ~deck
    part[lunken] = 3
    out = np.zeros(mode.shape, np.uint8); out[ys, xs] = part
    pr = dict(prof); pr.update(dtype="uint8", nodata=0, compress="deflate", count=1)
    with rasterio.open(GROUND / "works/riverworks_2026_part.tif", "w", **pr) as d:
        d.write(out, 1)
    for k, name in PARTS.items():
        n = int((part == k).sum())
        print("%-22s %8d cells  %6.2f km2" % (name, n, n * 4 / 1e6))


if __name__ == "__main__":
    main()
