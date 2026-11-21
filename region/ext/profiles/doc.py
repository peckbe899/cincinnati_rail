"""The old alignment doc and the profile record: each is made from the other, value for value.

The old Profiles page saves one doc per route (``hub/seed/alignments/<route>.json``, ``serialize()`` at
``profiles.html`` 3213). The hub keeps the design as one ``profile`` record per section (section 4 of the spec):

- The fields keyed by station (``st``, ``sg``, ``so``, ``stt``, ``mode``; the lists ``del`` and ``gapfill``) are
  re-keyed from the doc's station keys (``Towne``, ``Cincinnati State#2``) to platform ids. A key that names no
  station of the line file is kept in ``attrs.unmatched`` (a list's key as ``[place, key]``, so the list rebuilds in
  its order), so nothing is lost.
- The fields keyed by chainage (``pvi``, ``ovr``, ``tf``, ``shafts``, ``gnd``) and ``ready`` are kept as they are.
- ``frame`` holds what the doc was drawn against: its ``length_m`` and the ``point_c`` of each live station, paired
  with the line file's stations by index and name as ``reframeDoc`` pairs them (``profiles.html`` 1839).
- The doc's header (``v``, ``platform_m``, ``reframed``; ``system``, ``line`` and ``route_chainage_m`` where they
  differ from the line file) goes to ``attrs``, with any member this module does not know (``attrs.extra``).
- ``stations``, ``summary`` and ``updated`` are derived by the old page and never stored.

A field the doc does not have is left out of the record, and ``doc_of`` writes only the fields the record has, so
``doc_of(profile_of(doc)) == doc`` without the derived members (``test_13_docs_round_trip_value_for_value``).
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

BY_STATION = ("st", "sg", "so", "stt", "mode")
"""Doc members that are objects keyed by station key."""
STATION_LISTS = ("del", "gapfill")
"""Doc members that are lists of station keys."""
BY_CHAINAGE = ("pvi", "ovr", "tf", "shafts", "gnd")
"""Doc members keyed by chainage, kept as they are."""
DERIVED = ("stations", "summary", "updated")
"""Doc members the old page derives on save; never stored."""
HEADER = ("v", "system", "line", "length_m", "platform_m", "route_chainage_m", "reframed")
DOC_ORDER = (
    "v",
    "system",
    "line",
    "length_m",
    "platform_m",
    "st",
    "pvi",
    "ovr",
    "gnd",
    "shafts",
    "tf",
    "ready",
    "sg",
    "gapfill",
    "stt",
    "so",
    "del",
    "mode",
    "route_chainage_m",
    "reframed",
)
"""The order ``serialize()`` writes, used for the rebuilt doc (order does not count in a comparison)."""
KNOWN = frozenset(DOC_ORDER) | frozenset(DERIVED)


def empty_profile(section_id: str) -> dict[str, Any]:
    """The profile of a section no doc was saved for (Line_10, 11 and 13 today): flagged ``attrs.no_doc``, so the
    level solver's default (``defaultAlign``, a pending port) is what such a section shows."""
    return {"section": section_id, "attrs": {"no_doc": True}}


def is_empty(data: Mapping[str, Any]) -> bool:
    """Whether a profile holds no design: no PVI and no station level."""
    return not data.get("pvi") and not data.get("st")


def _number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def profile_of(
    doc: Mapping[str, Any],
    *,
    section_id: str,
    keys: Sequence[str],
    names: Sequence[str],
    platforms: Mapping[str, str],
    route_name: str,
    system_name: str,
) -> dict[str, Any]:
    """The profile record's data for an old alignment doc.

    ``keys`` and ``names`` are the line file's station keys and names in file order; ``platforms`` maps each station
    key to its platform id; ``route_name`` and ``system_name`` are the line file's ``line`` and ``system``.
    """
    data: dict[str, Any] = {"section": section_id}
    attrs: dict[str, Any] = {}
    extra: dict[str, Any] = {}
    unmatched: dict[str, Any] = {}
    for f in BY_STATION:
        if f not in doc:
            continue
        value = doc[f]
        if not isinstance(value, Mapping):
            extra[f] = copy.deepcopy(value)
            continue
        data[f] = {platforms[k]: copy.deepcopy(v) for k, v in value.items() if k in platforms}
        lost = {k: copy.deepcopy(v) for k, v in value.items() if k not in platforms}
        if lost:
            unmatched[f] = lost
    for f in STATION_LISTS:
        if f not in doc:
            continue
        value = doc[f]
        if not isinstance(value, list) or not all(isinstance(k, str) for k in value):
            extra[f] = copy.deepcopy(value)
            continue
        data[f] = [platforms[k] for k in value if k in platforms]
        lost = [[i, k] for i, k in enumerate(value) if k not in platforms]
        if lost:
            unmatched[f] = lost  # with each key's place in the doc's list, so the list rebuilds in its order
    for f in BY_CHAINAGE:
        if f in doc:
            data[f] = copy.deepcopy(doc[f])
    if "ready" in doc:
        data["ready"] = doc["ready"]
    frame = _frame(doc, keys, names, platforms)
    if frame is not None:
        data["frame"] = frame
    elif "length_m" in doc:
        attrs["length_m"] = doc["length_m"]
    for f in ("v", "platform_m", "route_chainage_m", "reframed"):
        if f in doc:
            attrs[f] = copy.deepcopy(doc[f])
    if "system" in doc and doc["system"] != system_name:
        attrs["system"] = doc["system"]
    if "line" in doc and doc["line"] != route_name:
        attrs["line"] = doc["line"]
    for k, v in doc.items():
        if k not in KNOWN:
            extra[k] = copy.deepcopy(v)
    if unmatched:
        attrs["unmatched"] = unmatched
    if extra:
        attrs["extra"] = extra
    if attrs:
        data["attrs"] = attrs
    return data


def _frame(
    doc: Mapping[str, Any], keys: Sequence[str], names: Sequence[str], platforms: Mapping[str, str]
) -> dict[str, Any] | None:
    stations = doc.get("stations")
    if not isinstance(stations, list) or not stations or not _number(doc.get("length_m")):
        return None
    deleted = set(doc.get("del") or []) if isinstance(doc.get("del"), list) else set()
    live = [(k, n) for k, n in zip(keys, names, strict=True) if k not in deleted]
    point_c: dict[str, Any] = {}
    for i, x in enumerate(stations):
        if not isinstance(x, Mapping) or i >= len(live):
            continue
        key, name = live[i]
        if x.get("name") == name and _number(x.get("point_c")) and key in platforms:
            point_c[platforms[key]] = x["point_c"]
    return {"length_m": doc["length_m"], "point_c": point_c}


def doc_of(
    data: Mapping[str, Any],
    *,
    keys_of: Mapping[str, str],
    route_name: str,
    system_name: str,
    length_m: float,
    platform_m: float | None,
) -> dict[str, Any]:
    """The old alignment doc a profile record stands for, without the derived members.

    ``keys_of`` maps each platform id of the section to its station key; ``length_m`` is the section's length and
    ``platform_m`` the platform length param, used where the profile carries no doc value of its own (a profile no
    doc was saved for).
    """
    attrs = data.get("attrs") or {}
    unmatched = attrs.get("unmatched") or {}
    out: dict[str, Any] = {}
    out["v"] = attrs.get("v", 1)
    out["system"] = attrs.get("system", system_name)
    out["line"] = attrs.get("line", route_name)
    frame = data.get("frame")
    out["length_m"] = frame["length_m"] if isinstance(frame, Mapping) else attrs.get("length_m", length_m)
    if "platform_m" in attrs or platform_m is not None:
        out["platform_m"] = attrs.get("platform_m", platform_m)
    for f in BY_STATION:
        if f in data:
            value = {keys_of.get(pid, pid): copy.deepcopy(v) for pid, v in data[f].items()}
            value.update(copy.deepcopy(unmatched.get(f) or {}))
            out[f] = value
    for f in STATION_LISTS:
        if f in data:
            out[f] = _with_unmatched([keys_of.get(pid, pid) for pid in data[f]], unmatched.get(f) or [])
    for f in BY_CHAINAGE:
        if f in data:
            out[f] = copy.deepcopy(data[f])
    if "ready" in data:
        out["ready"] = data["ready"]
    for f in ("route_chainage_m", "reframed"):
        if f in attrs:
            out[f] = copy.deepcopy(attrs[f])
    for k, v in (attrs.get("extra") or {}).items():
        out[k] = copy.deepcopy(v)
    order = {k: i for i, k in enumerate(DOC_ORDER)}
    return {k: out[k] for k in sorted(out, key=lambda k: (order.get(k, len(order)), k))}


def _with_unmatched(keys: list[Any], lost: Sequence[Any]) -> list[Any]:
    """A station list with its unmatched keys put back at their places (``[place, key]`` pairs, in place order)."""
    out = list(keys)
    for item in sorted((x for x in lost if isinstance(x, list) and len(x) == 2), key=lambda x: x[0]):
        out.insert(min(int(item[0]), len(out)), item[1])
    return out


def without_derived(doc: Mapping[str, Any]) -> dict[str, Any]:
    """A doc without the members the old page derives (``stations``, ``summary``, ``updated``)."""
    return {k: copy.deepcopy(v) for k, v in doc.items() if k not in DERIVED}


def pvi_points(data: Mapping[str, Any]) -> list[tuple[float, float]]:
    """The profile's PVIs as ``(c, z)`` pairs, whichever shape the record holds them in (pairs or ``{c_m, z_m}``)."""
    out = []
    for p in data.get("pvi") or []:
        if isinstance(p, Mapping):
            out.append((float(p["c_m"]), float(p["z_m"])))
        else:
            out.append((float(p[0]), float(p[1])))
    return out


__all__ = [
    "BY_CHAINAGE",
    "BY_STATION",
    "DERIVED",
    "DOC_ORDER",
    "STATION_LISTS",
    "doc_of",
    "empty_profile",
    "is_empty",
    "profile_of",
    "pvi_points",
    "without_derived",
]
