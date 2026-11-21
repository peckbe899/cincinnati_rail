"""The lane-B data tiers (9.26): which tiers of ``configs/hub_paths.json`` are missing, partial or present here.

    from region import tiers
    reports = tiers.scan()                      # {name: TierReport}, in config order
    reports["ground_1912_real"].status          # "partial"
    reports["ground_1912_real"].detail          # "stage contours"
    tiers.as_json(reports)                      # the body of GET /tiers
    tiers.changes(before, reports)              # the tier events between two scans

``crhub doctor`` shows one row per tier; ``python -m region.tiers`` prints the scan (``--json`` for the API body).
The rules are in ``region/tiers/scan.py``. ``region.core.paths`` resolves ``tier://`` URIs; this package looks inside
the roots and never writes.
"""

from .scan import (
    STATUSES,
    Finding,
    TierReport,
    as_json,
    changes,
    clear_cache,
    counts,
    required_missing,
    scan,
    scan_tier,
)

__all__ = [
    "Finding",
    "STATUSES",
    "TierReport",
    "as_json",
    "changes",
    "clear_cache",
    "counts",
    "required_missing",
    "scan",
    "scan_tier",
]
