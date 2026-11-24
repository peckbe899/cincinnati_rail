"""Each section's rail as the lines crossing it read it, kept ready on the hub and read without planning a job.

The ``profiles.neighbour`` job gives one section's neighbour view (``solve_input.neighbour_view``): its live stations
with their rail levels, its bend points, drawn ground, streets and settings. For a line with saved levels the view is
built from its records; for one without (Lines 10, 11 and 13) the job solves the line's own default design
(``section.solve@1``, the old page's ``defaultAlign``) and the view carries its levels and bend points.

The live hub keeps a background goal of that job for every section whose view needs it (``needs_rail``: a live
station with no saved level, or a profile in another frame; ``Live.watch_all_sections``, and again for the sections
an import touched), so the scheduler re-plans it when one of its records changes, caches it by its content (the job
key) and stops the chain when the view comes out the same (early cutoff). A line whose levels are all saved, in its
own frame, needs no job: its view is built from its records on each request, and the structure solves need its job
only when they run. A change on Line 6 re-solves the lines crossing Line 6 only when the view of Line 6 they read
changed.

``warm_view(jobs, section, view)`` reads the goal's newest ok result straight from the job cache: no plan, no job,
so the sheet's request (``GET /sections/{id}/solve``) costs a cache read per crossing line. ``None`` when the hub
has no scheduler, no goal for the section or no result yet.
"""

from __future__ import annotations

from typing import Any

from region.core.view import View

NEIGHBOUR_JOB = "profiles.neighbour"


def warm_meta(jobs: Any, section_id: str, view: View) -> dict[str, Any] | None:
    """The meta of the newest ok ``profiles.neighbour`` result of the section's goal: ``neighbour`` (its view) and,
    when its own solve ran, ``design`` (``solve_input.design_of``). Never planned; None when there is none."""
    cache = getattr(jobs, "cache", None)
    if cache is None:
        return None
    try:
        row = cache.one(
            "SELECT r.meta FROM goal g JOIN result r ON r.key = g.latest_key "
            "WHERE g.type = ? AND g.scope = ? AND g.view = ? AND r.status = 'ok'",
            (NEIGHBOUR_JOB, section_id, view.token()),
        )
    except Exception:  # noqa: BLE001 - a cache this cannot read: the request goes on without the view
        return None
    if row is None:
        return None
    import json

    meta = json.loads(row[0]) if isinstance(row[0], str) else (row[0] or {})
    return meta if isinstance(meta, dict) else None


def warm_view(jobs: Any, section_id: str, view: View) -> dict[str, Any] | None:
    """The neighbour view of ``section_id`` from its goal's newest ok result (see the module doc)."""
    nb = (warm_meta(jobs, section_id, view) or {}).get("neighbour")
    return nb if isinstance(nb, dict) else None


def warm_design(jobs: Any, section_id: str, view: View) -> dict[str, Any] | None:
    """The design the section's rail is drawn with when it is not its saved profile as it stands (no saved level,
    another frame): ``solve_input.design_of`` of its own solve, from the warm result. None otherwise."""
    d = (warm_meta(jobs, section_id, view) or {}).get("design")
    return d if isinstance(d, dict) else None


def needs_rail(store: Any, view: View, section_id: str, *, reframe: bool = True) -> bool:
    """Whether the section's neighbour view needs the job: a live station with no saved level, or (``reframe``) a
    profile saved in another frame (``solve_input.needs_design``)."""
    from .inputs import StoreReads
    from .solve_input import needs_design, needs_levels

    try:
        ctx = StoreReads(store, view)
        return needs_design(ctx, section_id) if reframe else needs_levels(ctx, section_id)
    except Exception:  # noqa: BLE001 - a section that cannot be read has no rail to keep
        return False


__all__ = ["NEIGHBOUR_JOB", "needs_rail", "warm_design", "warm_meta", "warm_view"]
