"""Ground elevation along an alignment, from several sources.

Priority (first available wins, configurable):
  1. 'csv'   - output of the legacy Elevation_Profile_Extraction notebook
               (columns Latitude, Longitude, Elevation_ft or Elevation_m)
  2. 'kmz'   - altitudes stored in the KMZ LineString coordinates (absolute, metres)
  3. 'usgs'  - USGS 3DEP bare-earth DEM via the Elevation Point Query Service (EPQS);
               one consistent datum (NAVD88) and no trees/buildings, unlike SRTM/Copernicus
               surface models. Results are cached on disk, so each point is fetched once.
  4. flat    - zero everywhere (a warning is printed)

Everything returned is ground elevation in metres at the requested chainages; the track
profile itself is designed from it in profile.py.
"""

from __future__ import annotations

import csv
import json
import math
import os
import threading
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
