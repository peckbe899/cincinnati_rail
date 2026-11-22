"""What a live change did, in Ben's words: the text of the ``source`` event and its toast.

    "Line 3 updated from the old hub: 2 stations moved, re-solving"
    "16 lines updated from the line files: 445 stations moved, ground changed on 16, re-solving"
    "Rule registry updated: 3 params changed"
    "1912 ground: stage contours to surface"

``describe(...)`` is pure: it takes the import's changes (``ImportReport.changes``), what each changed record is
(kind, name and section) and, for profiles, the data before and after, and returns the text with the sections it
touched. Nothing here reads the store.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

SECTION_CHILDREN = frozenset({"stop", "platform", "ground_profile", "profile", "track"})
"""Kinds whose ``parent`` column is their section (the line sheet's inputs)."""


@dataclass
class Described:
    text: str
    sections: list[str] = field(default_factory=list)
    phrases: dict[str, list[str]] = field(default_factory=dict)


def _n(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _keys_changed(a: Any, b: Any) -> int:
    a = a if isinstance(a, Mapping) else {}
    b = b if isinstance(b, Mapping) else {}
    return sum(1 for k in set(a) | set(b) if a.get(k) != b.get(k))


def profile_phrases(before: Mapping[str, Any] | None, after: Mapping[str, Any] | None) -> list[str]:
    """What changed in a profile, station by station: levels (``st``), slides (``so``), grades, PVIs."""
    b, a = before or {}, after or {}
    out: list[str] = []
    moved = _keys_changed(b.get("so"), a.get("so"))
    if moved:
        out.append(f"{_n(moved, 'station')} moved")
    levels = _keys_changed(b.get("st"), a.get("st"))
    if levels:
        out.append(f"{_n(levels, 'station level')} changed")
    if (b.get("pvi") or []) != (a.get("pvi") or []):
        nb, na = len(b.get("pvi") or []), len(a.get("pvi") or [])
        out.append(f"PVIs changed ({nb} to {na})" if nb != na else "PVIs changed")
    if not out:
        out.append("profile changed")
    return out


def _phrases(items: list[dict[str, Any]], bodies: Mapping[str, tuple[Any, Any]]) -> list[str]:
    """The phrases of one section's (or one origin's) changes."""
    count: Counter[str] = Counter()
    extra: list[str] = []
    for ch in items:
        kind, op, fields = ch["kind"], ch["op"], set(ch.get("fields") or [])
        if kind == "stop":
            if op == "create":
                count["stations added"] += 1
            elif op == "delete":
                count["stations removed"] += 1
            elif "data.c" in fields or "geom" in fields:
                count["stations moved"] += 1
            else:
                count["station details changed"] += 1
        elif kind == "platform":
            if op == "put":
                count["platforms changed"] += 1
        elif kind == "ground_profile":
            count["ground changed"] += 1
        elif kind == "section":
            if "geom" in fields or "data.path" in fields:
                count["track moved"] += 1
            elif op == "create":
                count["lines added"] += 1
            elif op == "delete":
                count["lines removed"] += 1
            else:
                count["line details changed"] += 1
        elif kind == "profile":
            before, after = bodies.get(ch["id"], (None, None))
            extra.extend(profile_phrases(before, after))
        elif kind == "param":
            count["params changed"] += 1
        elif kind in ("rule", "ruling"):
            count["rules changed" if op != "create" else "rules added"] += 1
        elif kind == "station":
            count["stations renamed" if "data.name" in fields else "station details changed"] += 1
        elif kind == "ground_layer":
            count["ground layers changed"] += 1
        elif kind in ("route", "node"):
            continue  # follows the section's own change
        else:
            count[f"{kind.replace('_', ' ')}s changed"] += 1
    out: list[str] = []
    order = (
        "stations moved",
        "stations added",
        "stations removed",
        "track moved",
        "ground changed",
        "platforms changed",
        "stations renamed",
        "station details changed",
        "lines added",
        "lines removed",
        "line details changed",
        "params changed",
        "rules added",
        "rules changed",
        "ground layers changed",
    )
    for key in list(order) + sorted(k for k in count if k not in order):
        n = count.get(key, 0)
        if not n:
            continue
        noun, _, verb = key.partition(" ")
        singular = noun[:-1] if noun.endswith("s") else noun
        if key == "ground changed":
            out.append("ground changed")
        elif key == "track moved":
            out.append("track moved")
        else:
            out.append(f"{n} {singular if n == 1 else noun} {verb}")
    return extra + out


def describe(
    *,
    label: str,
    origin: str,
    changes: Iterable[dict[str, Any]],
    records: Mapping[str, dict[str, Any]],
    names: Mapping[str, str],
    bodies: Mapping[str, tuple[Any, Any]] | None = None,
    review: int = 0,
    review_other: int = 0,
    resolving: bool = True,
) -> Described:
    """The words for an applied import (see the module doc).

    ``records`` maps a changed id to ``{"kind", "parent"}`` (its section for the kinds in ``SECTION_CHILDREN``);
    ``names`` maps a section id to its name ("Line 3"); ``bodies`` maps a profile id to its data before and after;
    ``review`` counts the conflicts in Ben's layers and ``review_other`` those over the old hub's revisions."""
    bodies = bodies or {}
    by_section: dict[str, list[dict[str, Any]]] = defaultdict(list)
    loose: list[dict[str, Any]] = []
    for ch in changes:
        if ch.get("op") not in ("create", "put", "delete"):
            continue
        rec = records.get(ch["id"]) or {}
        kind = ch.get("kind") or rec.get("kind")
        sid = None
        if kind == "section":
            sid = ch["id"]
        elif kind in SECTION_CHILDREN:
            sid = rec.get("parent")
        if sid:
            by_section[sid].append(ch)
        else:
            loose.append(ch)
    phrases = {sid: _phrases(items, bodies) for sid, items in by_section.items()}
    sections = sorted(by_section, key=lambda s: names.get(s) or s)
    tail = ", re-solving" if resolving and sections else ""
    if len(sections) == 1:
        sid = sections[0]
        text = f"{names.get(sid) or 'A line'} updated from {origin}: {', '.join(phrases[sid])}{tail}"
    elif sections:
        if len(sections) <= 3:
            who = " and ".join(
                [", ".join(names.get(s) or "a line" for s in sections[:-1]), names.get(sections[-1]) or "a line"]
            )
        else:
            who = f"{len(sections)} lines"
        merged = _phrases([c for s in sections for c in by_section[s]], bodies)
        text = f"{who} updated from {origin}: {', '.join(merged)}{tail}"
    else:
        text = ""
    if loose:
        rest = ", ".join(_phrases(loose, bodies))
        text = f"{text}; also {rest}" if text else f"{label} updated: {rest}"
    if not text:
        text = f"{label}: nothing changed"
    if review:
        text += f"; {_n(review, 'change')} {'touches' if review == 1 else 'touch'} your edits and "
        text += "waits in Review" if review == 1 else "wait in Review"
    if review_other:
        text += f"; {_n(review_other, 'change')} {'touches' if review_other == 1 else 'touch'} the old hub's "
        text += "profiles and waits in Review" if review_other == 1 else "profiles and wait in Review"
    return Described(text=text, sections=sections, phrases=phrases)


def tier_text(label: str, before: Mapping[str, Any] | None, after: Mapping[str, Any], changed: list[str]) -> str:
    """A tier's change: its handshake stage (``"1912 ground: stage contours to surface"``), its status, or the files
    that moved (``"Deck files: plots.json and basin.json changed"``)."""
    b_hs = (before or {}).get("handshake") or {}
    a_hs = after.get("handshake") or {}
    if b_hs.get("detail") != a_hs.get("detail") and a_hs.get("detail") is not None:
        was = b_hs.get("detail")
        text = f"{label}: stage {was} to {a_hs['detail']}" if was else f"{label}: stage {a_hs['detail']}"
        if a_hs.get("done") and not b_hs.get("done"):
            text += ", ready to use"
        return text
    if a_hs.get("done") and not b_hs.get("done"):
        return f"{label}: ready to use"
    if before is not None and before.get("status") != after.get("status"):
        return f"{label}: {before.get('status')} to {after.get('status')} ({after.get('detail')})"
    names = [c.rsplit("/", 1)[-1] for c in changed if c]
    if not names:
        return f"{label}: changed"
    if len(names) <= 3:
        shown = " and ".join([", ".join(names[:-1]), names[-1]]) if len(names) > 1 else names[0]
        return f"{label}: {shown} changed"
    return f"{label}: {len(names)} files changed"


__all__ = ["Described", "SECTION_CHILDREN", "describe", "profile_phrases", "tier_text"]
