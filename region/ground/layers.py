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

    @property
    def year(self) -> int | None:
        """The year the work counts as present: built_by, else built_from, else None (undated)."""
        return self.built_by if self.built_by is not None else self.built_from


# How each ledger work is applied. 'target_mode': the work's own target and mode rasters. 'map3_footprint': the 2026
# canon ground inside the non-zero cells of a delta raster (the delta was made against today's LiDAR, which the repo
# does not hold). 'map3_zones': the 2026 canon ground inside polygons. 'raster': a surface that replaces the ground
# where it has values. 'model': generated from the hub model, not here. Order is the order of application.
LAYERS = {
    "ohio_embankment_1912": dict(kind="target_mode", target="works/riverworks_1912_target_dm.tif", mode="works/riverworks_1912_mode.tif"),
    "ohio_embankment_rest": dict(kind="target_mode", target="works/riverworks_2026_target_dm.tif", mode="works/riverworks_2026_mode.tif"),
    "mill_creek_deck": dict(kind="target_mode", target="works/riverworks_2026_target_dm.tif", mode="works/riverworks_2026_mode.tif", shared="ohio_embankment_rest"),
    "lunken_levees": dict(kind="target_mode", target="works/riverworks_2026_target_dm.tif", mode="works/riverworks_2026_mode.tif", shared="ohio_embankment_rest"),
    "lunken_airfield_lift": dict(kind="target_mode", target="works/riverworks_2026_target_dm.tif", mode="works/riverworks_2026_mode.tif", shared="ohio_embankment_rest"),
    "ky_terraces": dict(kind="target_mode", target="works/ky_terraces_target_dm.tif", mode="works/ky_terraces_mode.tif"),
    "canon_interstates": dict(kind="map3_footprint", delta="works/canon_interstates_delta_dm.tif"),
    "ohio_bed_canon": dict(kind="raster", raster="works/ohio_bed_canon_dm.tif"),
    "real_works_removed": dict(kind="none", note="never built in canon; the 1912 base has none of them"),
    "real_works_kept": dict(kind="map3_zones", zones="zones/zones_post1912_works.geojson", minus="zones/zones_real_works_canon_removes.geojson"),
    "metro_tri_line_works": dict(kind="model"),
}


def load_ledger(path: Path = GROUND / "works_ledger.json") -> list[Work]:
    d = json.loads(path.read_text())
    out = []
    for i, w in enumerate(d["works"]):
        lay = dict(LAYERS.get(w["id"], {"kind": "none"}))
        kind = lay.pop("kind")
        files = {k: GROUND / v for k, v in lay.items() if k in ("target", "mode", "delta", "raster", "zones", "minus")}
        extra = {k: v for k, v in lay.items() if k not in files}
        out.append(Work(id=w["id"], name=w["name"], built_from=w.get("built_from"), built_by=w.get("built_by"), kind=kind,
                        files=files, timeline="canon" if w["id"] != "real_works_kept" else "both", source=w.get("source", ""),
                        note=(w.get("note") or "") + (" " + json.dumps(extra) if extra else ""), code=10 + i))
    return out


def conflicts(path: Path = GROUND / "works_ledger.json") -> list[str]:
    return json.loads(path.read_text()).get("conflicts", [])
