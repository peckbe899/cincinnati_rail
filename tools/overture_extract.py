"""Extract Overture Maps features (OpenStreetMap-derived) in a bounding box to KML.

The OSM APIs are unreachable from the build sandbox, but Overture's GeoParquet releases on
S3 are. Only the row groups whose bbox statistics overlap the area are fetched, with HTTP
range requests, so a city takes a few MB rather than the whole 50 GB theme.

    python tools/overture_extract.py rail  --bbox -84.75 38.95 -84.30 39.30 \
        --out data/reference/overture_rail_cincinnati.kml
    python tools/overture_extract.py water --bbox ... --out ...

Kinds: rail (transportation/segment, subtype rail), water (base/water polygons and lines).
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyarrow.parquet as pq
import shapely

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from railsim.kml import KmlWriter  # noqa: E402

BUCKET = "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com"
KINDS = {"rail": ("transportation", "segment"), "water": ("base", "water")}


class RangeFile(io.RawIOBase):
    """Seekable read-only file over HTTP range requests (enough for pyarrow.parquet)."""

    def __init__(self, url: str, size: int):
        self.url, self.size, self.pos = url, size, 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.pos + n, self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                break
            except OSError:
                if attempt == 3:
                    raise
        self.pos += len(data)
        return data

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def latest_release() -> str:
    xml = urllib.request.urlopen(f"{BUCKET}/?list-type=2&prefix=release/&delimiter=/", timeout=60).read().decode()
    return sorted(re.findall(r"<Prefix>(release/[^<]+/)</Prefix>", xml))[-1]


def list_files(prefix: str):
    out, token = [], None
    while True:
        url = f"{BUCKET}/?list-type=2&prefix={prefix}" + (f"&continuation-token={token}" if token else "")
        xml = urllib.request.urlopen(url, timeout=60).read().decode()
        out += [(k, int(s)) for k, s in re.findall(r"<Key>([^<]+\.parquet)</Key>.*?<Size>(\d+)</Size>", xml)]
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", xml)
        if not m:
            return out
        token = urllib.parse.quote(m.group(1), safe="")


def _overlaps(rg, cols, bbox):
    x0, y0, x1, y1 = bbox
    st = {}
    for i, name in cols.items():
        s = rg.column(i).statistics
        if s is None or not s.has_min_max:
            return True
        st[name] = (s.min, s.max)
    return not (st["xmin"][0] > x1 or st["xmax"][1] < x0 or st["ymin"][0] > y1 or st["ymax"][1] < y0)


def extract(kind: str, bbox, release=None, workers=16):
    theme, typ = KINDS[kind]
    release = release or latest_release()
    files = list_files(f"{release}theme={theme}/type={typ}/")
    print(f"{release}: {len(files)} files")

    def scan(item):
        key, size = item
        f = pq.ParquetFile(RangeFile(f"{BUCKET}/{key}", size))
        names = f.schema_arrow.names
        paths = {i: f.metadata.row_group(0).column(i).path_in_schema
                 for i in range(f.metadata.num_columns)}
        cols = {i: p.split(".")[-1] for i, p in paths.items()
                if p in ("bbox.xmin", "bbox.xmax", "bbox.ymin", "bbox.ymax")}
        rgs = [r for r in range(f.num_row_groups) if _overlaps(f.metadata.row_group(r), cols, bbox)]
        want = [c for c in ("id", "geometry", "subtype", "class", "names") if c in names]
        rows = []
        for r in rgs:
            t = f.read_row_group(r, columns=want + ["bbox"]).to_pylist()
            for row in t:
                b = row["bbox"]
                if b["xmin"] > bbox[2] or b["xmax"] < bbox[0] or b["ymin"] > bbox[3] or b["ymax"] < bbox[1]:
                    continue
                if kind == "rail" and row.get("subtype") != "rail":
                    continue
                rows.append(row)
        return rows

    with ThreadPoolExecutor(max_workers=workers) as ex:
        rows = [r for part in ex.map(scan, files) for r in part]
    print(f"{len(rows)} {kind} features")
    return rows


def to_kml(rows, kind, out):
    kw = KmlWriter(f"Overture {kind}")
    kw.open_folder(f"Overture {kind}")
    for row in rows:
        g = shapely.from_wkb(row["geometry"])
        name = ((row.get("names") or {}).get("primary") or row.get("class") or kind)
        parts = getattr(g, "geoms", [g])
        for p in parts:
            if p.geom_type == "Polygon":
                p = p.exterior
            if p.geom_type in ("LineString", "LinearRing"):
                kw.line(f"{name} [{row.get('class') or ''}]",
                        [(y, x, 0.0) for x, y, *_ in p.coords], "ff00ffff" if kind == "rail" else "ffff8000", 2.0)
    kw.close_folder()
    kw.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=list(KINDS))
    ap.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("W", "S", "E", "N"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--release")
    a = ap.parse_args()
    rows = extract(a.kind, a.bbox, a.release)
    to_kml(rows, a.kind, ROOT / a.out)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
