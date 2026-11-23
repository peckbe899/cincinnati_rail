"""Upgraders of the ``profile`` kind (``region.model.kinds``: ``up_<n>(data) -> data`` takes version n to n + 1)."""

from __future__ import annotations

from typing import Any


def up_1(data: Any) -> Any:
    """Version 1 to 2: ``access`` (Ben's access choice per platform) is new and optional, so a version 1 profile is
    a version 2 profile as it is: the rules decide every station's access until Ben chooses one."""
    return data


__all__ = ["up_1"]
