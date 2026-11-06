"""Compose the ground for a year from the canon 1912 base and the works built by then."""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
from pyproj import Transformer
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt
from shapely.geometry import shape
import shapely
from shapely.ops import unary_union
from shapely.validation import make_valid

from . import layers as L
from .raster import Target, read

FEATHER_M = 16.0          # blend width inside a zone cut out of the 2026 ground


@dataclass
class Grid:
    target: Target
    z: np.ndarray            # float32 metres NAVD88, nan where no layer has a value
    src: np.ndarray          # uint8 layer code per cell (layers.SRC and Work.code)
    year: int
    timeline: str
    applied: list            # [(work id, how)] in order
    skipped: list            # [(work id, why)]

    @property
    def transform(self):
        return self.target.transform

    def code_names(self) -> dict:
        names = {v: k for k, v in L.SRC.items()}
        for w in L.load_ledger():
            names[w.code] = w.id
        return names


def works_for_year(year: int, timeline: str = "canon", ledger=None):
    """(present, skipped): the works that count at `year`, and those left out with the reason."""
    ledger = ledger or L.load_ledger()
    present, skipped = [], []
    for w in ledger:
        if w.timeline not in (timeline, "both"):
            skipped.append((w.id, "timeline " + w.timeline)); continue
        if w.kind in ("model", "none"):
            skipped.append((w.id, w.kind)); continue
        y = w.year
        if y is None:
            if year >= L.PRESENT:
                present.append(w)             # undated works are in the 2026 canon ground
            else:
                skipped.append((w.id, "undated"))
        elif y <= year:
            present.append(w)
        else:
            skipped.append((w.id, "built %s" % y))
    return present, skipped


_ZONES = {}


def _zones_geom(zones_path, minus_path=None):
    """The zone polygons in EPSG:26916 (made valid), minus the removed ones; cached per path pair."""
    key = (str(zones_path), str(minus_path))
    if key not in _ZONES:
        tr = Transformer.from_crs("EPSG:4326", "EPSG:26916", always_xy=True)
        def load(p):
            fc = json.loads(open(p).read())
            return unary_union([make_valid(shapely.transform(shape(f["geometry"]), lambda a: np.column_stack(tr.transform(a[:, 0], a[:, 1])))) for f in fc["features"]])
        g = load(zones_path)
        if minus_path:
            g = g.difference(load(minus_path))
        _ZONES[key] = g
    return _ZONES[key]


def _zones_mask(tgt: Target, zones_path, minus_path=None) -> np.ndarray:
    g = _zones_geom(zones_path, minus_path)
    if g.is_empty:
        return np.zeros(tgt.shape, bool)
    return rasterize([(g, 1)], out_shape=tgt.shape, transform=tgt.transform, fill=0, dtype="uint8").astype(bool)


def _feather(mask: np.ndarray, step: float, width: float) -> np.ndarray:
    """Weight 1 deep inside the mask, falling to 0 at its edge over `width` metres."""
    if not mask.any():
        return np.zeros(mask.shape, np.float32)
    d = distance_transform_edt(mask) * step
    return np.clip(d / width, 0, 1).astype(np.float32)


def compose(year: int, bbox, timeline: str = "canon", step: float = L.STEP, extra_works=None) -> Grid:
    """The ground at `year` over `bbox` (x0, y0, x1, y1 in EPSG:26916 metres).

    timeline 'canon' (the alternate history) or 'real' (today's history up to 1912 only, for now).
    extra_works: parametric works (earthworks.Pad / Corridor) applied after the ledger's, in order.
    """
    tgt = Target(*bbox, step=step)
    z = read(L.CANON_1912, tgt).astype(np.float32)
    src = np.where(z != L.ND, L.SRC["canon_1912"], L.SRC["none"]).astype(np.uint8)
    applied, skipped = [], []
    if timeline == "real":
        d = read(L.RIVERWORKS_1912_DELTA, tgt)
        m = (d != L.ND) & (d != 0) & (z != L.ND)
        z[m] -= d[m]; src[m] = L.SRC["real_1912"]
        applied.append(("real_1912", "canon 1912 minus the 1912 riverworks delta"))
    # outside the 1912 raster the only ground is the 2026 canon ground, labelled as such
    m3 = read(L.MAP3, tgt).astype(np.float32)
    gap = (z == L.ND) & (m3 != L.ND)
    if gap.any():
        z[gap] = m3[gap]; src[gap] = L.SRC["map3_outside_1912"]
    z[z == L.ND] = np.nan
    m3[m3 == L.ND] = np.nan

    present, skipped_w = works_for_year(year, timeline)
    skipped.extend(skipped_w)
    done = set()
    for w in present:
        key = w.files.get("target") or w.files.get("delta") or w.files.get("raster") or w.files.get("zones")
        if key in done:
            applied.append((w.id, "shares a layer already applied")); continue
        done.add(key)
        if w.kind == "target_mode":
            t = read(w.files["target"], tgt).astype(np.float32); mode = read(w.files["mode"], tgt, nodata=0, dtype=np.uint8)
            ok = t != L.ND
            force = ok & (mode == 1); fill = ok & (mode == 2) & ~np.isnan(z)
            z[force] = t[force]; src[force] = w.code
            raised = fill & (t > z); z[raised] = t[raised]; src[raised] = w.code
            applied.append((w.id, "target and mode: %d forced, %d filled" % (force.sum(), raised.sum())))
        elif w.kind == "map3_footprint":
            d = read(w.files["delta"], tgt)
            m = (d != L.ND) & (d != 0) & ~np.isnan(m3)
            z[m] = m3[m]; src[m] = w.code
            applied.append((w.id, "2026 canon ground inside the delta footprint: %d cells" % m.sum()))
        elif w.kind == "map3_zones":
            m = _zones_mask(tgt, w.files["zones"], w.files.get("minus")) & ~np.isnan(m3)
            wgt = _feather(m, step, FEATHER_M)
            z = np.where(m & ~np.isnan(z), z * (1 - wgt) + m3 * wgt, np.where(m, m3, z)); src[m] = w.code
            applied.append((w.id, "2026 canon ground inside %d zone cells, feathered %g m" % (m.sum(), FEATHER_M)))
        elif w.kind == "raster":
            r = read(w.files["raster"], tgt).astype(np.float32)
            m = r != L.ND
            z[m] = r[m]; src[m] = w.code
            applied.append((w.id, "surface replaces the ground on %d cells" % m.sum()))
    z = z / 10.0            # decimetres to metres
    for ew in extra_works or []:
        z, m = ew.apply(z, tgt)
        src[m] = ew.code
        applied.append((ew.id, "parametric %s: %d cells" % (type(ew).__name__.lower(), m.sum())))
    return Grid(tgt, z, src, year, timeline, applied, skipped)
