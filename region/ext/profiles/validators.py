"""The profile feature's validator (section 4, validation step 7): a profile's platform keys belong to its section.

Every key of ``st``, ``sg``, ``so``, ``stt`` and ``mode``, and every item of ``del`` and ``gapfill``, must be the id
of a platform on the profile's own section, and a section has at most one profile.
"""

from __future__ import annotations

from typing import Any

from region.core.protocols import ValidateCtx

KEYED = ("st", "sg", "so", "stt", "mode")
LISTED = ("del", "gapfill")
RULE = None


def platform_keys(rec: dict[str, Any], ctx: ValidateCtx) -> list[dict[str, Any]]:
    data = rec.get("data") or {}
    section = data.get("section")
    if not isinstance(section, str):
        return []
    errors: list[dict[str, Any]] = []
    others = [p["id"] for p in ctx.list("profile", parent=section) if p["id"] != rec["id"]]
    if others:
        errors.append(
            {"path": "/data/section", "message": f"section {section} already has profile {others[0]}", "rule": RULE}
        )
    on_section = {p["id"] for p in ctx.list("platform", parent=section)}
    for f in KEYED:
        for pid in sorted((data.get(f) or {}).keys()):
            if pid not in on_section:
                errors.append(
                    {
                        "path": f"/data/{f}/{pid}",
                        "message": f"{pid} is not a platform of section {section}",
                        "rule": RULE,
                    }
                )
    for f in LISTED:
        for i, pid in enumerate(data.get(f) or []):
            if pid not in on_section:
                errors.append(
                    {"path": f"/data/{f}/{i}", "message": f"{pid} is not a platform of section {section}", "rule": RULE}
                )
    return errors


VALIDATORS = {"profile": platform_keys}

__all__ = ["VALIDATORS", "platform_keys"]
