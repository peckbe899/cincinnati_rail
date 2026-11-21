"""The hub's frozen shared contracts (WP0): every other package codes against these modules.

- ``view``: ``View(layer, year, month, timeline)`` and the month-interval dates.
- ``protocols``: ``Store``, ``Op``, ``JobType``, ``PlanCtx``, ``RunCtx``, ``Output``, ``Scheduler``,
  ``EngineClient``, ``Importer``, ``IdLookup`` and the record shapes.
- ``errors``: ``NotFound``, ``PreconditionRequired``, ``PreconditionFailed``, ``Conflict``, ``Invalid``,
  ``EngineUnavailable`` (and ``EngineError``).
- ``events``: the event payloads of section 5.
- ``ids``: ``new()`` and ``stable(namespace, key)``.
- ``features``: ``discover()`` of ``region/ext/*/`` and the kind meta-schema check.
- ``fsio``: ``write_atomic``, the write guard, UTF-8 reads, canonical JSON.
- ``paths``: the repo, ``var``, configs and ``tier://`` resolution.
- ``log``: JSON lines per day with ``request_id`` and ``job_id``.

See ``region/core/README.md`` for the conventions and the choices made where the spec is silent.
"""

from .view import View

__all__ = ["View"]
