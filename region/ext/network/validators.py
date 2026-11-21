"""The network feature's validators: a section's path runs forward to its length, and a ground profile covers its
section's grid."""

from __future__ import annotations

import math
from typing import Any

from region.core.protocols import ValidateCtx

TOLERANCE_M = 1.0


def section_path(rec: dict[str, Any], ctx: ValidateCtx) -> list[dict[str, Any]]:
    data = rec.get("data") or {}
    path = data.get("path") or []
    errors: list[dict[str, Any]] = []
    last = None
    for i, p in enumerate(path):
        c = p[0]
        if last is not None and c < last:
            errors.append(
                {"path": f"/data/path/{i}/0", "message": f"chainage {c} m runs back from {last} m", "rule": None}
            )
            break
        last = c
    length = data.get("length_m")
    if path and isinstance(length, (int, float)) and abs(path[-1][0] - length) > TOLERANCE_M:
        errors.append(
            {"path": "/data/length_m", "message": f"the path ends at {path[-1][0]} m, not {length} m", "rule": None}
        )
    return errors


def ground_covers(rec: dict[str, Any], ctx: ValidateCtx) -> list[dict[str, Any]]:
    data = rec.get("data") or {}
    section = ctx.get("section", data.get("section")) if isinstance(data.get("section"), str) else None
    if section is None:
        return []
    length, step = (section.get("data") or {}).get("length_m"), data.get("step_m")
    if not isinstance(length, (int, float)) or not isinstance(step, (int, float)) or step <= 0:
        return []
    need = math.floor(length / step) + 1
    have = len(data.get("z_dm") or [])
    if have < need:
        return [
            {
                "path": "/data/z_dm",
                "message": f"{have} levels do not cover {length} m at {step} m ({need})",
                "rule": None,
            }
        ]
    return []


VALIDATORS = {"section": section_path, "ground_profile": ground_covers}

__all__ = ["TOLERANCE_M", "VALIDATORS", "ground_covers", "section_path"]
