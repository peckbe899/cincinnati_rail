"""Ground elevation along an alignment, from several sources.

Priority (first available wins, configurable):
  1. 'csv'   - output of the legacy Elevation_Profile_Extraction notebook
               (columns Latitude, Longitude, Elevation_ft or Elevation_m)
  2. 'kmz'   - altitudes stored in the KMZ LineString coordinates (absolute, metres)
  3. 'usgs'  - USGS 3DEP bare-earth DEM via the Elevation Point Query Service (EPQS);
               one consistent datum (NAVD88) and no trees/buildings, unlike SRTM/Copernicus
               surface models. Results are cached on disk, so each point is fetched once.
  4. 'terrain' - AWS Terrain Tiles (Terrarium PNG, served from S3): in the US these are
               resampled USGS 3DEP DEMs (bare earth), so the same ground as 'usgs' at
               ~15 m (zoom 13) without the per-point service. Tiles are cached on disk.
  5. flat    - zero everywhere (a warning is printed)

Everything returned is ground elevation in metres at the requested chainages; the track
profile itself is designed from it in profile.py.
"""

from __future__ import annotations

import csv
import json
import math
import os
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional, Sequence

import numpy as np

from .geo import FT, project_point_to_polyline

EPQS_URL = "https://epqs.nationalmap.gov/v1/json"


def _project_samples(lat, lon, z, proj, align_xy, align_s, max_offset=60.0):
    x, y = proj.to_xy(lat, lon)
    ch, val = [], []
    for xi, yi, zi in zip(np.atleast_1d(x), np.atleast_1d(y), z):
        if zi is None or (isinstance(zi, float) and math.isnan(zi)):
            continue
        c, d, _ = project_point_to_polyline(float(xi), float(yi), align_xy, align_s)
        if d <= max_offset:
            ch.append(c)
            val.append(float(zi))
    if len(ch) < 2:
        return None
    order = np.argsort(ch)
    return np.asarray(ch)[order], np.asarray(val)[order]


def from_csv(path: str | Path, proj, align_xy, align_s, s_query) -> Optional[np.ndarray]:
    lat, lon, z = [], [], []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("Elevation_m") not in (None, "", "nan"):
                zz = float(row["Elevation_m"])
            elif row.get("Elevation_ft") not in (None, "", "nan"):
                zz = float(row["Elevation_ft"]) * FT
            else:
                continue
            lat.append(float(row["Latitude"]))
            lon.append(float(row["Longitude"]))
            z.append(zz)
    res = _project_samples(np.array(lat), np.array(lon), z, proj, align_xy, align_s)
    if res is None:
        return None
    return np.interp(s_query, res[0], res[1])


def from_kmz_lines(lines_latlonz: Sequence[Sequence[tuple]], proj, align_xy, align_s, s_query):
    lat, lon, z = [], [], []
    for line in lines_latlonz:
        for la, lo, zz in line:
            if zz != 0.0:
                lat.append(la)
                lon.append(lo)
                z.append(zz)
    if len(z) < 2:
        return None
    res = _project_samples(np.array(lat), np.array(lon), z, proj, align_xy, align_s)
    if res is None:
        return None
    return np.interp(s_query, res[0], res[1])


class EpqsCache:
    """Disk cache of EPQS answers keyed by coordinates rounded to ~1 m."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.data = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                self.data = {}

    @staticmethod
    def key(lat, lon):
        return f"{lat:.5f},{lon:.5f}"

    def get(self, lat, lon):
        return self.data.get(self.key(lat, lon))

    def put(self, lat, lon, z):
        with self._lock:
            self.data[self.key(lat, lon)] = z

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data))
        os.replace(tmp, self.path)


def _epqs_query(lat: float, lon: float, timeout=20.0) -> Optional[float]:
    q = urllib.parse.urlencode({"x": f"{lon:.6f}", "y": f"{lat:.6f}", "wkid": 4326,
                                "units": "Meters", "includeDate": "false"})
    req = urllib.request.Request(f"{EPQS_URL}?{q}", headers={"User-Agent": "railsim/10"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                val = json.loads(r.read().decode()).get("value")
                if val is None:
                    return None
                val = float(val)
                return None if val < -1000 else val  # EPQS uses -1000000 for no data
        except (OSError, ValueError):
            continue
    return None


def from_usgs(proj, align_xy, align_s, s_query, cache_path, spacing=25.0,
              workers=8, query: Callable = _epqs_query, progress=print) -> Optional[np.ndarray]:
    s_samp = np.arange(0.0, align_s[-1] + spacing, spacing)
    s_samp[-1] = min(s_samp[-1], align_s[-1])
    x = np.interp(s_samp, align_s, align_xy[:, 0])
    y = np.interp(s_samp, align_s, align_xy[:, 1])
    lat, lon = proj.to_latlon(x, y)
    cache = EpqsCache(cache_path)
    todo = [i for i in range(len(s_samp)) if cache.get(lat[i], lon[i]) is None]
    if todo:
        progress(f"  USGS EPQS: fetching {len(todo)} of {len(s_samp)} points (cache: {cache_path})")

        def work(i):
            cache.put(lat[i], lon[i], _q(i))

        def _q(i):
            return query(float(lat[i]), float(lon[i]))

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for n, _ in enumerate(ex.map(work, todo)):
                if (n + 1) % 200 == 0:
                    cache.save()
        cache.save()
    z = np.array([cache.get(lat[i], lon[i]) for i in range(len(s_samp))], dtype=object)
    ok = np.array([v is not None for v in z])
    if ok.sum() < 2:
        return None
    zz = np.array([float(v) for v in z[ok]])
    return np.interp(s_query, s_samp[ok], zz)


TERRAIN_URL = "https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png"


def _fetch_tile(z: int, x: int, y: int, cache_dir: Path, timeout=30.0) -> Optional[np.ndarray]:
    """Terrarium tile as a 256x256 elevation array (m), from the disk cache or S3."""
    from PIL import Image
    import io
    path = cache_dir / str(z) / str(x) / f"{y}.png"
    if not path.exists():
        req = urllib.request.Request(TERRAIN_URL.format(z=z, x=x, y=y),
                                     headers={"User-Agent": "railsim/10"})
        data = None
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    data = r.read()
                break
            except OSError:
                time.sleep(0.5 * 2 ** attempt)
        if data is None:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=float)
    return rgb[..., 0] * 256.0 + rgb[..., 1] + rgb[..., 2] / 256.0 - 32768.0


def from_terrain_tiles(proj, align_xy, align_s, s_query, cache_dir, zoom: int = 13,
                       spacing: float = 10.0, workers: int = 16,
                       progress=print) -> Optional[np.ndarray]:
    """Ground elevation along the alignment from Terrarium tiles, bilinear-sampled every
    `spacing` m (Web Mercator tile maths)."""
    cache_dir = Path(cache_dir)
    s_samp = np.arange(0.0, align_s[-1] + spacing, spacing)
    s_samp[-1] = min(s_samp[-1], align_s[-1])
    x = np.interp(s_samp, align_s, align_xy[:, 0])
    y = np.interp(s_samp, align_s, align_xy[:, 1])
    lat, lon = proj.to_latlon(x, y)
    n = 2 ** zoom
    px = (np.asarray(lon) + 180.0) / 360.0 * n * 256.0
    lr = np.radians(np.asarray(lat))
    py = (1.0 - np.arcsinh(np.tan(lr)) / math.pi) / 2.0 * n * 256.0
    # pixel centres: sample between the four surrounding pixels
    fx, fy = px - 0.5, py - 0.5
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    need = set()
    for dx in (0, 1):
        for dy in (0, 1):
            for tx, ty in zip((x0 + dx) // 256, (y0 + dy) // 256):
                need.add((int(tx) % n, int(ty)))
    tiles = {}
    todo = [t for t in need if not (cache_dir / str(zoom) / str(t[0]) / f"{t[1]}.png").exists()]
    if todo:
        progress(f"  Terrain tiles: fetching {len(todo)} of {len(need)} (zoom {zoom}, cache {cache_dir})")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for t, arr in zip(need, ex.map(lambda t: _fetch_tile(zoom, t[0], t[1], cache_dir), need)):
            tiles[t] = arr
    missing = sum(v is None for v in tiles.values())
    if missing > 0.05 * len(tiles):
        return None  # too much missing: let the next source (or flat) take over
    if missing:
        progress(f"  Terrain tiles: {missing} tile(s) unavailable, interpolating across them")

    def pix(xx, yy):
        out = np.empty(len(xx))
        for i, (a, b) in enumerate(zip(xx, yy)):
            t = tiles[(int(a // 256) % n, int(b // 256))]
            out[i] = np.nan if t is None else t[b % 256, a % 256]
        return out

    wx, wy = fx - x0, fy - y0
    z = ((1 - wx) * (1 - wy) * pix(x0, y0) + wx * (1 - wy) * pix(x0 + 1, y0)
         + (1 - wx) * wy * pix(x0, y0 + 1) + wx * wy * pix(x0 + 1, y0 + 1))
    ok = np.isfinite(z)
    if ok.sum() < 2:
        return None
    return np.interp(s_query, s_samp[ok], z[ok])


# ----------------------------------------------------------------------------- USGS 1 m LiDAR
LIDAR_BASE = "https://prd-tnm.s3.amazonaws.com"
LIDAR_PREFIX = "StagedProducts/Elevation/1m/Projects/{p}/TIFF/"


def _lidar_index(projects: Sequence[str], cache_path: Path) -> dict:
    """{(zone, x10km, y10km): [url, ...]} for the listed USGS 1 m DEM projects (S3 listing,
    cached). Tile names are USGS_1M_<zone>_x<E/10 km>y<N_top/10 km>_<project>.tif."""
    import re
    cache_path = Path(cache_path)
    idx = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    for p in projects:
        if p in idx:
            continue
        keys, token = [], None
        while True:
            q = f"?list-type=2&prefix={urllib.parse.quote(LIDAR_PREFIX.format(p=p))}"
            if token:
                q += f"&continuation-token={urllib.parse.quote(token, safe='')}"
            xml = urllib.request.urlopen(LIDAR_BASE + "/" + q, timeout=60).read().decode()
            keys += re.findall(r"<Key>([^<]+\.tif)</Key>", xml)
            m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", xml)
            if not m:
                break
            token = m.group(1)
        idx[p] = keys
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(idx))
    out = {}
    for p in projects:  # earlier projects in the list win
        for k in idx.get(p, []):
            m = re.search(r"USGS_1M_(\d+)_x(\d+)y(\d+)_", k)
            if m:
                out.setdefault((int(m.group(1)), int(m.group(2)), int(m.group(3))), []).append(
                    f"{LIDAR_BASE}/{k}")
    return out


def from_lidar(proj, align_xy, align_s, s_query, projects: Sequence[str], cache_dir,
               spacing: float = 5.0, workers: int = 8, progress=print,
               fallback: Optional[Callable] = None) -> Optional[np.ndarray]:
    """Ground elevation from USGS 1 m LiDAR DEMs, reading only the COG blocks under the
    line's sample points (no whole-tile downloads). Points without LiDAR are filled from
    `fallback(s)` (e.g. terrain tiles) or interpolated."""
    try:
        import rasterio
        from pyproj import Transformer
    except ImportError:
        progress("  LiDAR: rasterio/pyproj not installed (pip install rasterio pyproj)")
        return None
    cache_dir = Path(cache_dir)
    index = _lidar_index(projects, cache_dir / "lidar_index.json")
    s_samp = np.arange(0.0, align_s[-1] + spacing, spacing)
    s_samp[-1] = min(s_samp[-1], align_s[-1])
    x = np.interp(s_samp, align_s, align_xy[:, 0])
    y = np.interp(s_samp, align_s, align_xy[:, 1])
    lat, lon = proj.to_latlon(x, y)
    lat, lon = np.asarray(lat), np.asarray(lon)
    z = np.full(len(s_samp), np.nan)
    groups = {}
    for zone in sorted({k[0] for k in index}):
        tr = Transformer.from_crs(4326, 26900 + zone, always_xy=True)
        E, N = tr.transform(lon, lat)
        for i in range(len(s_samp)):
            key = (zone, int(E[i] // 10000), int(math.ceil(N[i] / 10000)))
            if key in index:
                groups.setdefault(key, []).append((i, E[i], N[i]))
    pts_cache = cache_dir / "lidar_points.json"
    cache = json.loads(pts_cache.read_text()) if pts_cache.exists() else {}

    def ck(i):
        return f"{lat[i]:.6f},{lon[i]:.6f}"

    todo = {k: [p for p in v if ck(p[0]) not in cache] for k, v in groups.items()}
    todo = {k: v for k, v in todo.items() if v}
    if todo:
        progress(f"  LiDAR 1 m: sampling {sum(len(v) for v in todo.values())} points "
                 f"from {len(todo)} tile(s) (block reads only)")
    ca = next((c for c in (os.environ.get("CURL_CA_BUNDLE"), os.environ.get("SSL_CERT_FILE"),
                           os.environ.get("REQUESTS_CA_BUNDLE"), "/root/.ccr/ca-bundle.crt")
               if c and Path(c).exists()), None)

    def read(item):
        key, pts = item
        res = {}
        env = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR"}
        if ca:
            env["CURL_CA_BUNDLE"] = ca
        for url in index[key]:
            pend = [p for p in pts if ck(p[0]) not in res]
            if not pend:
                break
            try:
                with rasterio.Env(**env), rasterio.open("/vsicurl/" + url) as ds:
                    nod = ds.nodata
                    for (i, e, n), v in zip(pend, ds.sample([(e, n) for _, e, n in pend])):
                        val = float(v[0])
                        if (nod is None or val != nod) and val > -1000:
                            res[ck(i)] = val
            except Exception as e:  # missing tile, network error: try the next project
                errors.append(f"{url.rsplit('/', 1)[-1]}: {e}")
                continue
        return res  # only hits are cached: a project added later can fill the gaps

    errors: list = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(read, todo.items()):
            cache.update(res)
    if errors:
        progress(f"  LiDAR 1 m: {len(errors)} tile read(s) failed, e.g. {errors[0][:160]}")
    if todo:
        pts_cache.parent.mkdir(parents=True, exist_ok=True)
        pts_cache.write_text(json.dumps(cache))
    for i in range(len(s_samp)):
        v = cache.get(ck(i))
        if v is not None:
            z[i] = v
    ok = np.isfinite(z)
    if ok.sum() < 2:
        return None
    if not ok.all():
        progress(f"  LiDAR 1 m covers {ok.mean():.0%} of the line; filling the rest")
        if fallback is not None:
            fb = fallback(s_samp[~ok])
            if fb is not None:
                z[~ok] = fb
                ok = np.isfinite(z)
    return np.interp(s_query, s_samp[ok], z[ok])


def from_dem(proj, align_xy, align_s, s_query, path, scale: float = 1.0,
             spacing: float = 5.0, progress=print,
             fallback: Optional[Callable] = None) -> Optional[np.ndarray]:
    """Ground elevation from a local DEM raster (e.g. an alternate-history terrain in
    decimetres: scale 0.1), read only at the line's sample points. Points outside the raster
    or on nodata are filled from `fallback(s)` (e.g. LiDAR, then terrain tiles)."""
    try:
        import rasterio
        from pyproj import Transformer
    except ImportError:
        progress("  DEM: rasterio/pyproj not installed (pip install rasterio pyproj)")
        return None
    s_samp = np.arange(0.0, align_s[-1] + spacing, spacing)
    s_samp[-1] = min(s_samp[-1], align_s[-1])
    x = np.interp(s_samp, align_s, align_xy[:, 0])
    y = np.interp(s_samp, align_s, align_xy[:, 1])
    lat, lon = proj.to_latlon(x, y)
    z = np.full(len(s_samp), np.nan)
    with rasterio.open(path) as ds:
        tr = Transformer.from_crs(4326, ds.crs, always_xy=True)
        X, Y = tr.transform(np.asarray(lon), np.asarray(lat))
        b = ds.bounds
        inside = (X >= b.left) & (X <= b.right) & (Y >= b.bottom) & (Y <= b.top)
        idx = np.nonzero(inside)[0]
        nod = ds.nodata
        for i, v in zip(idx, ds.sample(list(zip(X[idx], Y[idx])))):
            val = float(v[0])
            if nod is None or val != nod:
                z[i] = val * scale
    ok = np.isfinite(z)
    progress(f"  DEM {Path(path).name}: covers {ok.mean():.0%} of the line")
    if not ok.all() and fallback is not None:
        fb = fallback(s_samp[~ok])
        if fb is not None:
            z[~ok] = fb
            ok = np.isfinite(z)
    if ok.sum() < 2:
        return None
    return np.interp(s_query, s_samp[ok], z[ok])
