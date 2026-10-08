"""Fetch the 1950s USGS 1:24,000 topographic sheets for Cincinnati, Covington and Newport.

These are the same georeferenced scans as in the project Drive (USGS Historical Topographic
Map Collection) and show the 1950s street grid and railroads (L&N bridge, C&O viaduct,
riverfront lines). They are served from the USGS S3 bucket, which is reachable where the
Drive is not. Saved to data/reference/topo/ (git-ignored; ~15 MB each).

    python tools/fetch_historic_topo.py
"""

from __future__ import annotations

import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/"
SHEETS = [
    "OH/OH_Cincinnati East_224429_1953_24000_geo.tif",
    "OH/OH_Cincinnati West_224435_1953_24000_geo.tif",
    "KY/KY_Covington_708443_1955_24000_geo.tif",
    "KY/KY_Newport_709396_1955_24000_geo.tif",
]


def main():
    out = ROOT / "data/reference/topo"
    out.mkdir(parents=True, exist_ok=True)
    for key in SHEETS:
        dest = out / Path(key).name
        if dest.exists():
            print(f"have {dest.name}")
            continue
        url = BASE + urllib.parse.quote(key)
        with urllib.request.urlopen(url, timeout=300) as r:
            dest.write_bytes(r.read())
        print(f"got  {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
