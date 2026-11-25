"""A section's ground sampled from region.ground: pure functions, no records and no writes (``ground.profile@1``).

- ``chainages(length_m, step_m)``: the section's grid, ``c = i * step_m`` from 0 to the first sample at or past the
  end (a line file's ground covers the same span);
- ``section_xy(path, c)``: the points of the drawn path (``[c, lon, lat]``, chainage rising) at each chainage, in
  EPSG:26916 metres, by straight lines between the path's points;
- ``sample_path(path, length_m, step_m, year, timeline, window_m)``: the ground at each sample, in windows of
  ``window_m`` along the line (one ``compose`` over each window's points plus ``MARGIN_M``, then bilinear
  ``sample_grid``), so memory stays bounded on a 30 km line. The margin is wider than the zones' feather, so a cell
  near a window's edge is composed as one compose over the whole line would compose it;
- ``ground_files(year, timeline)``: every file compose reads for that year and timeline, as URIs (the ground tiers'
  files by ``tier://``, the rest of ``ground/`` by ``repo://``), for the job's key.

Ground at a year is region.ground's rule (``region/ground``): the canon 1912 base, then each work built by that year
in ledger order. Nothing here changes it.
"""

from __future__ import annotations

import math
import os
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from region.ground import layers as L

WINDOW_M = 1000.0
"""The length of line one compose covers (param ``ground.sample_window_m`` once registered)."""
MARGIN_M = 20.0
"""Around each window's points: more than the zones' feather (16 m) plus a cell, so windows join without a seam."""
GROUND_TIERS = ("ground_1912_real", "ground_2026")
"""The data tiers whose files compose reads, named by tier in a key (the live hub watches tiers)."""


def chainages(length_m: float, step_m: float) -> np.ndarray:
    """``c = i * step_m`` for i from 0 to the first sample at or past ``length_m``."""
    n = int(math.ceil(float(length_m) / float(step_m) - 1e-9)) + 1
    return np.arange(n, dtype=float) * float(step_m)


@lru_cache(maxsize=1)
def _to_utm() -> Any:
    from pyproj import Transformer

    return Transformer.from_crs("EPSG:4326", "EPSG:26916", always_xy=True)


def section_xy(path: Sequence[Sequence[float]], c: np.ndarray) -> np.ndarray:
    """``[[x, y]]`` in EPSG:26916 at each chainage of ``c`` along the drawn path (clamped to its ends)."""
    p = np.asarray(path, dtype=float)
    if p.ndim != 2 or p.shape[0] < 2 or p.shape[1] < 3:
        raise ValueError("a section path is at least two [c, lon, lat] points")
    x, y = _to_utm().transform(p[:, 1], p[:, 2])
    return np.column_stack([np.interp(c, p[:, 0], x), np.interp(c, p[:, 0], y)])


def sample_path(
    path: Sequence[Sequence[float]],
    length_m: float,
    step_m: float,
    year: int,
    timeline: str,
    *,
    window_m: float = WINDOW_M,
    cancelled: Any = None,
) -> tuple[np.ndarray, np.ndarray, dict[int, str]]:
    """``(ground_m, src, names)``: the ground (f8, NaN where no layer has a value) and the layer code of the
    nearest cell (u1) at each sample of the section's grid, and the names of the codes found."""
    from region.ground.compose import compose
    from region.ground.sample import sample_grid

    c = chainages(length_m, step_m)
    xy = section_xy(path, c)
    per = max(1, int(round(float(window_m) / float(step_m))))
    z = np.full(len(c), np.nan, dtype="<f8")
    src = np.zeros(len(c), dtype="u1")
    names: dict[int, str] = {}
    for i in range(0, len(c), per):
        if cancelled is not None and cancelled():
            raise InterruptedError("cancelled")
        pts = xy[i : i + per]
        bbox = (
            float(pts[:, 0].min()) - MARGIN_M,
            float(pts[:, 1].min()) - MARGIN_M,
            float(pts[:, 0].max()) + MARGIN_M,
            float(pts[:, 1].max()) + MARGIN_M,
        )
        g = compose(int(year), bbox, timeline)
        z[i : i + per] = sample_grid(g, pts)
        t = g.target
        jj = np.clip(np.floor((pts[:, 0] - t.x0) / t.step).astype(int), 0, t.width - 1)
        ii = np.clip(np.floor((t.y1 - pts[:, 1]) / t.step).astype(int), 0, t.height - 1)
        codes = g.src[ii, jj]
        src[i : i + per] = codes
        found = set(int(v) for v in np.unique(codes))
        if found - set(names):
            all_names = g.code_names()
            for code in found:
                names.setdefault(code, str(all_names.get(code, code)))
    return z, src, dict(sorted(names.items()))


def vrt_sources(vrt: Path) -> list[Path]:
    """The rasters a VRT points at (``SourceFilename``), as paths."""
    root = ET.parse(vrt).getroot()
    out = []
    for el in root.iter("SourceFilename"):
        name = (el.text or "").strip()
        if not name:
            continue
        rel = el.get("relativeToVRT") == "1"
        out.append((vrt.parent / name) if rel else Path(name))
    return out


def _with_sources(path: Path) -> list[Path]:
    return [path, *vrt_sources(path)] if path.suffix.lower() == ".vrt" and path.is_file() else [path]


def files_read(year: int, timeline: str) -> list[Path]:
    """Every file compose reads for ``year`` and ``timeline``: the ledger, both bases (with a VRT's rasters), the
    real timeline's 1912 riverworks delta, and each present work's layers."""
    from region.ground.compose import works_for_year

    files: list[Path] = [L.GROUND / "works_ledger.json"]
    files += _with_sources(Path(L.CANON_1912))
    files += _with_sources(Path(L.MAP3))
    if timeline == "real":
        files.append(Path(L.RIVERWORKS_1912_DELTA))
    present, _skipped = works_for_year(int(year), timeline)
    for w in present:
        for key in L.FILE_KEYS:
            if key in w.files:
                files.extend(_with_sources(Path(w.files[key])))
    return files


def uri_of(path: Path) -> str:
    """A ground file's URI: by its ground tier when the tier's root holds this very file, else by the repo."""
    from region.core import paths

    real = os.path.realpath(path)
    for name in GROUND_TIERS:
        try:
            root = paths.tier(name).root
        except Exception:  # noqa: BLE001 - a tier not declared or absent: the repo names the file
            continue
        below = paths.names_below(os.path.realpath(root), real)
        if below:
            uri = f"tier://{name}/" + "/".join(below)
            try:
                if os.path.realpath(paths.resolve(uri)) == real:
                    return uri
            except Exception:  # noqa: BLE001
                pass
    below = paths.names_below(os.path.realpath(paths.repo_root()), real)
    if not below:
        raise ValueError(f"{path} lies outside the repo")
    return "repo://" + "/".join(below)


def ground_files(year: int, timeline: str) -> list[str]:
    """``files_read`` as sorted, distinct URIs (see the module doc)."""
    return sorted({uri_of(p) for p in files_read(year, timeline)})


__all__ = [
    "GROUND_TIERS",
    "MARGIN_M",
    "WINDOW_M",
    "chainages",
    "files_read",
    "ground_files",
    "sample_path",
    "section_xy",
    "uri_of",
    "vrt_sources",
]
