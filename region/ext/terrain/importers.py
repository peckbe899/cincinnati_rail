"""``ground_layers@1``: the ground surfaces lane B delivers, as ``ground_layer`` records in ``import:ground``.

For each ground tier with a handshake (``LAYERS``), the importer reads the handshake (``STATUS.json``) and yields one
record: the layer's key, its tier, whether it can be used now (``available``: the handshake's ``done``), the stage it
reports, when it was written, and the surface's datum, units and transform (9.15). ``records`` is pure: the same
handshake gives the same record, and a handshake that turns done changes exactly ``available`` and ``stage``, which
plans again every result that read the record (the ground jobs of increment 2).

The live hub runs this importer whenever the tier's handshake changes, so lane B's "done" reaches the hub without a
command.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from region.core.errors import Invalid
from region.core.protocols import IdLookup, PathResolver

LAYERS = {
    "status_1912": {
        "key": "real_1912",
        "title": "1912 ground (real timeline)",
        "tier": "ground_1912_real",
        "uri": "tier://ground_1912_real/STATUS.json",
        "done": "done",
        "stage": "stage",
        "vdatum": "navd88_m",
        "units": "dm",
        "transform": "1912 city datum, fitted offset to NAVD88 (report/fit_report.json)",
    },
}
"""The ground layers by source name: where each handshake is and what its surface holds (ground/1912/SPEC.md)."""


def _text(value: Any) -> str | None:
    return None if value is None or value == "" else str(value)


def record_of(spec: Mapping[str, Any], status: Mapping[str, Any], ids: IdLookup) -> dict[str, Any]:
    """The ``ground_layer`` record of one layer from its handshake document."""
    data = {
        "key": spec["key"],
        "title": spec["title"],
        "tier": spec["tier"],
        "available": bool(status.get(spec["done"])),
        "stage": _text(status.get(spec["stage"])),
        "blocked_on": _text(status.get("blocked_on")),
        "updated": _text(status.get("updated")),
        "commit": _text(status.get("commit")),
        "vdatum": spec["vdatum"],
        "units": spec["units"],
        "transform": spec["transform"],
    }
    return {
        "kind": "ground_layer",
        "id": ids.id_for("ground_layer", spec["key"], kind="ground_layer"),
        "data": data,
        "geom": None,
        "source": spec["uri"],
    }


class GroundLayers:
    """``ground_layers@1`` (see the module doc)."""

    name = "ground_layers"
    version = "1"
    namespace = "ground"
    layer = "import:ground"

    def sources(self, paths: PathResolver) -> dict[str, str]:
        return {name: spec["uri"] for name, spec in LAYERS.items()}

    def records(self, src: Mapping[str, Path], ids: IdLookup) -> Iterator[dict[str, Any]]:
        for name, spec in LAYERS.items():
            path = Path(src[name])
            try:
                with open(path, encoding="utf-8-sig") as f:
                    status = json.load(f)
            except json.JSONDecodeError as e:
                raise Invalid(f"{path} is not JSON yet (being written?): {e}") from None
            if not isinstance(status, Mapping):
                raise Invalid(f"{path} does not hold a JSON object")
            yield record_of(spec, status, ids)


GROUND_LAYERS = GroundLayers()
IMPORTERS = [GROUND_LAYERS]
