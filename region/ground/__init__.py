"""Ground by year: the canon 1912 base and every work after it, composed on demand.

    from region.ground import compose, sample
    g = compose(1930, bbox=(712000, 4330000, 716000, 4334000))      # Grid: .z (m), .src (layer code), .transform
    z = sample(1930, [(712500, 4331000), (712600, 4331050)])          # metres NAVD88 along a polyline

Layers live in ground/ (see ground/README.md and ground/works_ledger.json). Rule: ground(Y) is the canon 1912
ground, then each work built by Y applied in ledger order by its own layer (target and mode, or the 2026 canon
ground inside its footprint). New works are parametric (earthworks.Pad, earthworks.Corridor) and compose the same way.
"""
from .compose import compose, Grid, works_for_year
from .sample import sample
from .earthworks import Pad, Corridor

__all__ = ["compose", "Grid", "works_for_year", "sample", "Pad", "Corridor"]
