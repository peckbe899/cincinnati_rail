"""Authority defaults (decision 9.23): the record kinds the old hub still edits are owned by legacy.

While legacy owns a kind, the main and legacy layers refuse writes to it (409 authority) except from the legacy
importer, and promote is refused; scenarios stay writable, so Ben can try designs in the new hub without forking the
truth. ``crhub`` flips a kind to model with ``store.flip_authority(kind, ...)``, which squashes its legacy revisions
into main.

The old hub edits the Metro alignments (``profile``, with Ben's access choices), the platforms' side or island
(``platform``, params/station_platforms), the station complexes (``station_complex``), the Chronology
(``chronology``), the roadmap (``roadmap_item``), the 3D camera and saved views (``camera``, ``view``); and plan
geometry has legacy authority until the Deck adapter lands (9.27), so the kinds the line files (Deck-tie output) make
are legacy's too. Params are not: the registry is their owner and Ben's overrides
are main revisions (9.25).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from region.core.protocols import IdLookup

LEGACY_KINDS = (
    "profile",
    "section",
    "route",
    "node",
    "station",
    "stop",
    "platform",
    "ground_profile",
    "roadmap_item",
    "camera",
    "view",
    "station_complex",
    "chronology",
)
RULING = "9.23 strangler: the old hub owns what it still edits; plan geometry legacy until the Deck adapter (9.27)"


def authority_key(kind: str) -> str:
    """The legacy key of a kind's authority record, so its id is ``ids.stable("old_hub", "authority:<kind>")``."""
    return f"authority:{kind}"


def authority_records(ids: IdLookup) -> Iterator[dict[str, Any]]:
    """One ``authority`` record per legacy-owned kind, owner ``legacy``."""
    for kind in LEGACY_KINDS:
        yield {
            "kind": "authority",
            "id": ids.id_for("authority", authority_key(kind), kind="authority"),
            "data": {"kind": kind, "owner": "legacy", "ruling": None, "note": RULING},
            "geom": None,
            "source": "region/ext/legacy/authority.py",
        }


__all__ = ["LEGACY_KINDS", "RULING", "authority_key", "authority_records"]
