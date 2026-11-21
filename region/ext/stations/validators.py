"""The stations feature's validators: a stop sits on its section, and a platform on its stop's section."""

from __future__ import annotations

from typing import Any

from region.core.protocols import ValidateCtx

TOLERANCE_M = 1.0
"""How far past either end of its section a stop's point may lie (the line files round chainage to 0.1 m)."""


def stop_on_section(rec: dict[str, Any], ctx: ValidateCtx) -> list[dict[str, Any]]:
    data = rec.get("data") or {}
    section = ctx.get("section", data.get("section")) if isinstance(data.get("section"), str) else None
    if section is None:
        return []
    length = (section.get("data") or {}).get("length_m")
    c = data.get("c")
    if isinstance(length, (int, float)) and isinstance(c, (int, float)):
        if not -TOLERANCE_M <= c <= length + TOLERANCE_M:
            return [
                {"path": "/data/c", "message": f"{c} m is off section {section['id']} (0 to {length} m)", "rule": None}
            ]
    return []


def platform_on_stop(rec: dict[str, Any], ctx: ValidateCtx) -> list[dict[str, Any]]:
    data = rec.get("data") or {}
    stop = ctx.get("stop", data.get("stop")) if isinstance(data.get("stop"), str) else None
    if stop is None:
        return []
    want = (stop.get("data") or {}).get("section")
    if data.get("section") != want:
        return [
            {"path": "/data/section", "message": f"the platform's stop {stop['id']} is on section {want}", "rule": None}
        ]
    return []


VALIDATORS = {"stop": stop_on_section, "platform": platform_on_stop}

__all__ = ["TOLERANCE_M", "VALIDATORS", "platform_on_stop", "stop_on_section"]
