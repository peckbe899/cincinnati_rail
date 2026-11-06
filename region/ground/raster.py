"""Reading the ground rasters onto one target grid (a bbox on the 2 m lattice), and writing results."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.windows import from_bounds

from .layers import ND, STEP


@dataclass
class Target:
    """A grid: bbox (x0, y0, x1, y1) in EPSG:26916 metres, snapped outward to the 2 m lattice."""
    x0: float
    y0: float
    x1: float
    y1: float
    step: float = STEP

    def __post_init__(self):
        s = self.step
        self.x0, self.y0 = np.floor(self.x0 / s) * s, np.floor(self.y0 / s) * s
        self.x1, self.y1 = np.ceil(self.x1 / s) * s, np.ceil(self.y1 / s) * s

    @property
    def width(self) -> int:
        return int(round((self.x1 - self.x0) / self.step))

    @property
    def height(self) -> int:
        return int(round((self.y1 - self.y0) / self.step))

    @property
    def shape(self):
        return (self.height, self.width)

    @property
    def transform(self):
        return from_origin(self.x0, self.y1, self.step, self.step)

    @property
    def bounds(self):
        return (self.x0, self.y0, self.x1, self.y1)


def read(path: Path, tgt: Target, nodata=ND, dtype=np.int16, resampling=Resampling.nearest) -> np.ndarray:
    """The raster's values on the target grid (nodata where the raster has none, or does not reach)."""
    out = np.full(tgt.shape, nodata, dtype)
    with rasterio.open(path) as r:
        bx = (max(tgt.x0, r.bounds.left), max(tgt.y0, r.bounds.bottom), min(tgt.x1, r.bounds.right), min(tgt.y1, r.bounds.top))
        if bx[0] >= bx[2] or bx[1] >= bx[3]:
            return out
        w = from_bounds(*bx, transform=r.transform)
        rows = int(round((bx[3] - bx[1]) / tgt.step)); cols = int(round((bx[2] - bx[0]) / tgt.step))
        if rows <= 0 or cols <= 0:
            return out
        a = r.read(1, window=w, out_shape=(rows, cols), resampling=resampling, boundless=True, fill_value=r.nodata if r.nodata is not None else 0)
        rnd = r.nodata
        if rnd is not None and rnd != nodata:
            a = np.where(a == rnd, nodata, a)
        i0 = int(round((tgt.y1 - bx[3]) / tgt.step)); j0 = int(round((bx[0] - tgt.x0) / tgt.step))
        out[i0:i0 + rows, j0:j0 + cols] = a.astype(dtype)
    return out


def write(path: Path, arr: np.ndarray, tgt: Target, nodata=ND, dtype="int16"):
    """A tiled, deflate-compressed GeoTIFF on the target grid (the same conventions as the ground/ rasters)."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", height=tgt.height, width=tgt.width, count=1, dtype=dtype, crs="EPSG:26916",
                       transform=tgt.transform, nodata=nodata, compress="deflate", predictor=2, tiled=True, blockxsize=512, blockysize=512) as d:
        d.write(arr.astype(dtype), 1)


def raster_bounds(path: Path):
    with rasterio.open(path) as r:
        return (r.bounds.left, r.bounds.bottom, r.bounds.right, r.bounds.top)
