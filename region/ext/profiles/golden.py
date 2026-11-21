"""The golden diff's comparison and classes (section 7, the baseline of checklist 2.0.10), as pure functions.

``tests/baseline/profiles/<route>.json`` holds the old page's rail every 5 m and its normalised input (``align``:
arrays by kept station index, after ``reframeDoc``, ``defaultAlign``, locks and junction PVIs). A section's rail
from its records is compared with it, and the difference is classed (``golden.yaml``):

- **same**: every sample within ``tol_m``;
- **rule_fix**: a difference ``golden.yaml`` lists with the rule whose fix makes it;
- **pending_port**: the record input differs from the page's ``align`` and a known unported normalisation explains
  it: ``defaultAlign`` (no doc was saved: the profile is empty) or ``reframeDoc`` (the profile's frame differs from
  the stops it is now read against);
- **unexplained**: anything else, including a rail that differs while the input equals the page's.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .doc import is_empty

FRAME_TOL_M = 0.05
"""reframeDoc's own threshold: a stop moved by more than this re-frames the doc (profiles.html 1849)."""


def compare(rail: Sequence[float], want: Sequence[float], step_m: float, tol_m: float) -> dict[str, Any]:
    """Samples off by more than ``tol_m``: ``{bad, worst_m, at_m}`` (a missing sample counts as off)."""
    bad, worst, at = 0, 0.0, None
    for i, w in enumerate(want):
        r = rail[i] if i < len(rail) else math.nan
        d = abs(r - w)
        if not d <= tol_m:
            bad += 1
        if not d <= worst:
            worst = d if math.isfinite(d) else math.inf
            at = i * step_m
    return {"bad": bad, "worst_m": round(worst, 6) if math.isfinite(worst) else None, "at_m": at}


def input_diffs(si: Mapping[str, Any], align: Mapping[str, Any], stops_c: Sequence[float], kept: int) -> list[str]:
    """How the record input ``si`` differs from the page's ``align`` (``[]`` when it is the page's input).

    ``stops_c`` are the station points of the stops the align keeps (the line file minus ``align.del``), in order,
    and ``kept`` their count; the page's platform centre is the point plus ``align.so``.
    """
    out = []
    st, sg, so = align.get("st") or [], align.get("sg") or [], align.get("so") or []
    stations = si.get("stations") or []
    if len(stations) != kept:
        out.append("stations")
    pairs = list(zip(stations, range(min(len(stations), kept)), strict=False))

    def num(xs: Sequence[Any], i: int) -> float | None:
        v = xs[i] if i < len(xs) else None
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None

    if any(s["c_m"] != stops_c[i] + (num(so, i) or 0) for s, i in pairs):
        out.append("slides")
    if any(s["level_m"] != num(st, i) for s, i in pairs):
        out.append("levels")
    if any((s["grade_permille"] or 0) != (num(sg, i) or 0) for s, i in pairs):
        out.append("grades")
    page = sorted((float(p["c"]), float(p["z"])) for p in align.get("pvi") or [])
    ours = sorted((float(p["c_m"]), float(p["z_m"])) for p in si.get("pvi") or [])
    if len(page) != len(ours):
        out.append("pvi count")
    elif page != ours:
        out.append("pvi chainages")
    return out


def causes(profile: Mapping[str, Any] | None, length_m: float, stop_c: Mapping[str, float]) -> list[str]:
    """The unported normalisations that apply to a profile: ``defaultAlign`` for an empty one, ``reframeDoc`` when
    its frame differs from the stops (``stop_c`` maps platform id to its stop's point)."""
    data = (profile or {}).get("data") or {}
    if not data or (data.get("attrs") or {}).get("no_doc") or is_empty(data):
        return ["defaultAlign"]
    frame = data.get("frame")
    if isinstance(frame, Mapping):
        moved = any(
            pid in stop_c and abs(float(c) - stop_c[pid]) > FRAME_TOL_M
            for pid, c in (frame.get("point_c") or {}).items()
        )
        if moved:
            return ["reframeDoc"]
    return []


def classify(
    route: str,
    cmp: Mapping[str, Any],
    diffs: Sequence[str],
    found: Sequence[str],
    table: Mapping[str, Any],
) -> dict[str, Any]:
    """The class of one route: ``{class, reason, rule, label}`` (``label`` is ``class`` or ``class:reason``)."""
    if not cmp["bad"]:
        return {"class": "same", "reason": None, "rule": None, "label": "same"}
    for fix in table.get("rule_fixes") or []:
        if fix.get("route") == route and (fix.get("max_m") is None or (cmp["worst_m"] or 0) <= fix["max_m"]):
            return {
                "class": "rule_fix",
                "reason": fix.get("note"),
                "rule": fix["rule"],
                "label": f"rule_fix:{fix['rule']}",
            }
    known = table.get("pending_ports") or {}
    if diffs and found and all(c in known for c in found):
        reason = "|".join(found)
        return {"class": "pending_port", "reason": reason, "rule": None, "label": f"pending_port:{reason}"}
    why = "the input is the page's, yet the rail differs" if not diffs else "differs in " + ", ".join(diffs)
    return {"class": "unexplained", "reason": why, "rule": None, "label": "unexplained"}


__all__ = ["FRAME_TOL_M", "causes", "classify", "compare", "input_diffs"]
