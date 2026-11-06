"""Sample the ground for a year along points (bilinear), for profiles and the rules engine."""
from __future__ import annotations

import numpy as np

from .compose import Grid, compose


def sample_grid(g: Grid, xy) -> np.ndarray:
    xy = np.asarray(xy, float)
    t = g.target
    fj = (xy[:, 0] - t.x0) / t.step - 0.5; fi = (t.y1 - xy[:, 1]) / t.step - 0.5
    i0 = np.clip(np.floor(fi).astype(int), 0, t.height - 2); j0 = np.clip(np.floor(fj).astype(int), 0, t.width - 2)
    u = np.clip(fi - i0, 0, 1); v = np.clip(fj - j0, 0, 1)
    z = g.z
    return ((z[i0, j0] * (1 - u) + z[i0 + 1, j0] * u) * (1 - v) + (z[i0, j0 + 1] * (1 - u) + z[i0 + 1, j0 + 1] * u) * v)


def sample(year: int, xy, timeline: str = "canon", margin: float = 10.0, **kw) -> np.ndarray:
    """Ground in metres NAVD88 at each (x, y) for `year`; nan where there is no ground."""
    xy = np.asarray(xy, float)
    bbox = (xy[:, 0].min() - margin, xy[:, 1].min() - margin, xy[:, 0].max() + margin, xy[:, 1].max() + margin)
    return sample_grid(compose(year, bbox, timeline, **kw), xy)
