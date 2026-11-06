"""The ground layers in ground/: where each file is, what kind of layer it is, and the works ledger.

Every raster is EPSG:26916 on the LiDAR 2 m lattice (the bed rasters 4 m), int16 decimetres NAVD88, nodata -32768,
except the mode rasters (uint8: 0 untouched, 1 force the target, 2 fill only). Zones are EPSG:4326 polygons.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GROUND = ROOT / "ground"
ND = -32768
STEP = 2.0
PRESENT = 2026            # the year of the 2026 canon ground (map 3)

# the base surfaces
CANON_1912 = GROUND / "1912" / "canon_1912_ground_dm.vrt"
SURVEY_COVER = GROUND / "1912" / "survey_cover_1912.tif"
MAP3 = GROUND / "2026" / "map3_profile_dem_dm.vrt"
MAP3_WATER = GROUND / "2026" / "map3_profile_dem_dm_water.tif"
RIVERWORKS_1912_DELTA = GROUND / "works" / "riverworks_1912_delta_dm.tif"     # canon 1912 minus real 1912

# layer codes written into Grid.src (provenance per cell)
SRC = {"none": 0, "canon_1912": 1, "real_1912": 2, "map3_outside_1912": 3}


@dataclass
class Work:
    id: str
    name: str
    built_from: int | None
    built_by: int | None
    kind: str                       # 'target_mode' | 'map3_footprint' | 'map3_zones' | 'raster' | 'model' | 'none'
    files: dict = field(default_factory=dict)
    timeline: str = "canon"         # 'canon' | 'real' | 'both'
    source: str = ""
    note: str = ""
    code: int = 0
    part_value: int | None = None

    @property
    def year(self) -> int | None:
        """The year the work counts as present: built_by, else built_from, else None (undated)."""
        return self.built_by if self.built_by is not None else self.built_from


FILE_KEYS = ("target", "mode", "delta", "raster", "zones", "minus", "part", "years")


def load_ledger(path: Path = GROUND / "works_ledger.json") -> list[Work]:
    """The works as the ledger has them. The ledger's `apply` block says how each is applied; nothing here is hard-coded."""
    d = json.loads(path.read_text())
    out = []
    for i, w in enumerate(d["works"]):
        lay = dict(w.get("apply") or {"kind": "none"})
        files = {k: GROUND / v for k, v in lay.items() if k in FILE_KEYS}
        out.append(Work(id=w["id"], name=w["name"], built_from=w.get("built_from"), built_by=w.get("built_by"), kind=lay.get("kind", "none"),
                        files=files, timeline=w.get("timeline", "canon"), source=w.get("source", ""), note=w.get("note") or "",
                        code=10 + i, part_value=lay.get("part_value")))
    return out


def conflicts(path: Path = GROUND / "works_ledger.json") -> list[str]:
    return json.loads(path.read_text()).get("conflicts", [])
