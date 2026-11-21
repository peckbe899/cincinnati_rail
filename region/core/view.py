"""The view every read and every job runs in: ``View(layer, year, month, timeline)`` (decision 9.16).

- ``layer`` is a layer slug: ``main``, ``legacy:old_hub``, ``import:profiles``, or a scenario or proposal slug.
- ``year`` and ``month`` pick the instant. ``year=None`` is the present: no time filter, and undated built records
  count (the 6 November ruling). A month needs a year. A year is -9999 to 9999, what a partial ISO date can write.
- ``timeline`` is ``canon`` or ``real``, as ``region/ground`` already has.

Dates in records are partial ISO strings (``"1931"``, ``"1931-09"``) stored as month intervals: a pair of month
indices ``(lo, hi)``, inclusive, counted in months since year 0 (``index = year * 12 + month - 1``). ``"1931"`` is
``(23172, 23183)`` and ``"1931-09"`` is ``(23180, 23180)``. The instant of a view is the last month it covers: the
end of its year, or of its month. ``is_open`` states the rule in one place.

The HTTP query names are ``layer``, ``year``, ``month`` and ``tl``; ``View.from_query`` and ``View.query`` convert.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any, Literal

from .errors import Invalid

Timeline = Literal["canon", "real"]
Axis = Literal["year", "month", "timeline"]

TIMELINES: tuple[str, ...] = ("canon", "real")
AXES: tuple[str, ...] = ("year", "month", "timeline")

# A layer slug: "main", "legacy:old_hub", "import:profiles", "try", "fs-stacked", "proposal:2026-11-21-pvi".
LAYER_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}(:[a-z0-9][a-z0-9_.-]{0,63})?$")
_DATE_RE = re.compile(r"^(-?\d{1,4})(?:-(\d{2}))?$")


def month_index(year: int, month: int = 1) -> int:
    """Months since year 0 for the first day of ``year-month`` (``month`` 1 to 12)."""
    if not 1 <= month <= 12:
        raise Invalid(f"month {month} is not 1 to 12", errors=[{"path": "/month", "message": "1 to 12"}])
    return year * 12 + month - 1


def date_interval(value: str | int | None) -> tuple[int, int] | None:
    """The month interval of a partial ISO date: ``"1931"`` is its twelve months, ``"1931-09"`` one month.

    ``None`` and ``""`` are undated and give ``None``. An int is read as a year. Anything else raises ``Invalid``.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise Invalid(f"date {value!r} is not a partial ISO date")
    if isinstance(value, int):
        return value * 12, value * 12 + 11
    m = _DATE_RE.match(str(value).strip())
    if not m:
        raise Invalid(f"date {value!r} is not a partial ISO date (YYYY or YYYY-MM)")
    year = int(m.group(1))
    if m.group(2) is None:
        return year * 12, year * 12 + 11
    lo = month_index(year, int(m.group(2)))
    return lo, lo


def is_open(instant: int | None, opened: tuple[int, int] | None, closed: tuple[int, int] | None) -> bool:
    """Whether a dated thing exists at ``instant`` (decision 9.16).

    - At the present (``instant is None``) everything not closed counts, undated things included.
    - Otherwise an undated opening does not count (it counts only at the present).
    - It is open when its opening interval starts at or before the instant and its closing interval, if any, has not
      started by then.
    """
    if instant is None:
        return closed is None
    if opened is None:
        return False
    if opened[0] > instant:
        return False
    return closed is None or closed[0] > instant


def date_uncertain(view_month: int | None, interval: tuple[int, int] | None) -> bool:
    """True when a year-only date is seen in a month view: the app marks it with an uncertain-date sign."""
    return view_month is not None and interval is not None and interval[1] > interval[0]


@dataclass(frozen=True)
class View:
    """The view every read and job runs in. Frozen and hashable, so it can key caches and goals.

    ``View()`` is the main layer, the present, canon.
    """

    layer: str = "main"
    year: int | None = None
    month: int | None = None
    timeline: str = "canon"

    def __post_init__(self) -> None:
        errors = []
        if not isinstance(self.layer, str) or not LAYER_RE.match(self.layer):
            errors.append({"path": "/layer", "message": f"{self.layer!r} is not a layer slug"})
        if self.year is not None and (isinstance(self.year, bool) or not isinstance(self.year, int)):
            errors.append({"path": "/year", "message": f"{self.year!r} is not an integer year"})
        elif self.year is not None and not -9999 <= self.year <= 9999:
            errors.append({"path": "/year", "message": f"{self.year} is outside -9999 to 9999 (a partial ISO year)"})
        if self.month is not None:
            if self.year is None:
                errors.append({"path": "/month", "message": "a month needs a year"})
            if isinstance(self.month, bool) or not isinstance(self.month, int) or not 1 <= self.month <= 12:
                errors.append({"path": "/month", "message": f"{self.month!r} is not a month 1 to 12"})
        if self.timeline not in TIMELINES:
            errors.append({"path": "/timeline", "message": f"{self.timeline!r} is not one of {', '.join(TIMELINES)}"})
        if errors:
            raise Invalid("invalid view: " + "; ".join(e["message"] for e in errors), errors=errors)

    def instant(self) -> int | None:
        """The month index of the view's instant: the end of its year, or of its month. ``None`` at the present."""
        if self.year is None:
            return None
        if self.month is None:
            return self.year * 12 + 11
        return self.year * 12 + self.month - 1

    def token(self) -> str:
        """A stable text form: ``"main|-|canon"``, ``"try|1931|real"``, ``"main|1931-09|canon"``.

        Used in result rows, goals and events. ``View.parse(v.token()) == v``.
        """
        if self.year is None:
            when = "-"
        elif self.month is None:
            when = str(self.year)
        else:
            when = f"{self.year}-{self.month:02d}"
        return f"{self.layer}|{when}|{self.timeline}"

    @classmethod
    def parse(cls, token: str) -> View:
        """The inverse of ``token()``."""
        parts = token.split("|")
        if len(parts) != 3:
            raise Invalid(f"view token {token!r} is not layer|when|timeline")
        layer, when, timeline = parts
        if when == "-":
            return cls(layer, None, None, timeline)
        m = _DATE_RE.match(when)
        if not m:
            raise Invalid(f"view token {token!r} has no valid year")
        return cls(layer, int(m.group(1)), int(m.group(2)) if m.group(2) else None, timeline)

    def key_axes(self, declared: Iterable[str]) -> dict[str, Any]:
        """Only the axes a job declared, for its cache key (9.16): ``{"year": 1931}`` for a job that reads the year.

        ``layer`` is never an axis: a layer enters a key only through the content it resolves to.
        """
        names = set(declared)
        unknown = names - set(AXES)
        if unknown:
            raise Invalid(f"unknown view axes: {', '.join(sorted(unknown))}")
        out: dict[str, Any] = {}
        if "year" in names:
            out["year"] = self.year
        if "month" in names:
            out["month"] = self.month
        if "timeline" in names:
            out["timeline"] = self.timeline
        return out

    def with_layer(self, layer: str) -> View:
        """The same instant and timeline on another layer."""
        return replace(self, layer=layer)

    def query(self) -> dict[str, str]:
        """The HTTP query parameters for this view (defaults left out)."""
        q = {"layer": self.layer}
        if self.year is not None:
            q["year"] = str(self.year)
        if self.month is not None:
            q["month"] = str(self.month)
        if self.timeline != "canon":
            q["tl"] = self.timeline
        return q

    @classmethod
    def from_query(cls, q: Mapping[str, Any]) -> View:
        """A view from HTTP query parameters ``layer``, ``year``, ``month``, ``tl`` (``timeline`` is accepted too).

        Missing or empty values take the defaults. Raises ``Invalid`` for bad values.
        """

        def num(name: str) -> int | None:
            raw = q.get(name)
            if raw is None or raw == "":
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                errors = [{"path": f"/{name}", "message": "integer"}]
                raise Invalid(f"{name}={raw!r} is not an integer", errors=errors) from None

        return cls(
            layer=q.get("layer") or "main",
            year=num("year"),
            month=num("month"),
            timeline=q.get("tl") or q.get("timeline") or "canon",
        )


__all__ = [
    "AXES",
    "Axis",
    "LAYER_RE",
    "TIMELINES",
    "Timeline",
    "View",
    "date_interval",
    "date_uncertain",
    "is_open",
    "month_index",
]
