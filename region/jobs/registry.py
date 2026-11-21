"""The job types a scheduler knows: the built-in ones (``region/jobs/types``) and every feature's ``JOB_TYPES``.

A job type is a module-level object (``region.core.protocols.JobType``) with ``name``, ``version``, ``scope``,
``host``, ``priority``, ``timeout_s``, ``plan(ctx, scope_id)`` and ``run(inputs, rt)``. Optional members:

- ``axes``: view axes always read (``("timeline",)``), on top of those ``plan`` declares with ``ctx.axis``;
- ``code``: a fixed code hash (tests pin keys with it); ``code_files``: more sources whose change reruns the job
  (railsim's tree for railsim jobs), as paths or ``repo://`` URIs;
- ``effect`` and ``apply(store, scope_id, view, output) -> dict``: see ``region/jobs/types/seed.py``. Only a type
  whose ``effect`` is ``"truth"`` has its ``apply`` called, by the scheduler, after the key check, never inside
  ``plan`` or ``run``.

``check_job_type`` states the contract; ``Registry.register`` refuses a type that breaks it. A process worker finds
its job type again by module and name with ``find``.

A key holds what ``plan`` read (decision 9.19), never the scope id itself, so ``plan`` must not return anything taken
from ``scope_id`` that it did not read for it: a job whose scope is a record id reads that record. Otherwise two
scopes make the same key and share one result. ``contract.check_contract`` probes for this.
"""

from __future__ import annotations

import importlib
import logging
import re
from collections.abc import Iterable, Iterator
from typing import Any

from region.core.errors import Invalid, NotFound
from region.core.protocols import HOSTS
from region.core.view import AXES

log = logging.getLogger("region.jobs")

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
EFFECTS = ("truth",)


def check_job_type(jt: Any) -> list[str]:
    """Every way ``jt`` breaks the job type contract, as plain strings; ``[]`` when it is a valid job type."""
    problems: list[str] = []
    name = getattr(jt, "name", None)
    if not isinstance(name, str) or not NAME_RE.match(name):
        problems.append(f"name {name!r} is not a dotted lowercase name (profiles.solve_section)")
    version = getattr(jt, "version", None)
    if not isinstance(version, str) or not version:
        problems.append(f"version {version!r} is not a non-empty string ('1')")
    scope = getattr(jt, "scope", None)
    if not isinstance(scope, str) or not scope:
        problems.append(f"scope {scope!r} is not a non-empty string (section, route, network)")
    host = getattr(jt, "host", None)
    if host not in HOSTS:
        problems.append(f"host {host!r} is not one of {', '.join(HOSTS)}")
    priority = getattr(jt, "priority", None)
    if isinstance(priority, bool) or not isinstance(priority, int) or not 0 <= priority <= 9:
        problems.append(f"priority {priority!r} is not an integer 0 to 9")
    timeout = getattr(jt, "timeout_s", None)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not timeout > 0:
        problems.append(f"timeout_s {timeout!r} is not a positive number")
    for method in ("plan", "run"):
        if not callable(getattr(jt, method, None)):
            problems.append(f"{method} is not callable")
    axes = getattr(jt, "axes", ()) or ()
    if isinstance(axes, str) or any(a not in AXES for a in axes):
        problems.append(f"axes {axes!r} are not view axes ({', '.join(AXES)})")
    effect = getattr(jt, "effect", None)
    if effect is not None:
        if effect not in EFFECTS:
            problems.append(f"effect {effect!r} is not one of {', '.join(EFFECTS)}")
        if not callable(getattr(jt, "apply", None)):
            problems.append("a job type with an effect needs apply(store, scope_id, view, output)")
    return problems


def module_of(jt: Any) -> str:
    """The module a worker process imports to find ``jt`` again."""
    return getattr(jt, "job_module", None) or type(jt).__module__


def _candidates(module: Any) -> Iterator[Any]:
    yield from getattr(module, "JOB_TYPES", ()) or ()
    for value in vars(module).values():
        if not isinstance(value, type) and hasattr(value, "name") and callable(getattr(value, "run", None)):
            yield value


def find(module: str, name: str) -> Any:
    """The job type called ``name`` defined in ``module`` (by ``JOB_TYPES`` or a module attribute)."""
    mod = importlib.import_module(module)
    for jt in _candidates(mod):
        if getattr(jt, "name", None) == name:
            return jt
    raise NotFound(f"no job type {name!r} in module {module}")


class Registry:
    """Job types by name."""

    def __init__(self, types: Iterable[Any] = ()) -> None:
        self._types: dict[str, Any] = {}
        for jt in types:
            self.register(jt)

    def register(self, jt: Any, *, replace: bool = False) -> Any:
        problems = check_job_type(jt)
        if problems:
            raise Invalid(f"job type {getattr(jt, 'name', jt)!r} is invalid: " + "; ".join(problems))
        if jt.name in self._types and self._types[jt.name] is not jt and not replace:
            raise Invalid(f"two job types are named {jt.name!r}")
        self._types[jt.name] = jt
        return jt

    def get(self, name: str) -> Any:
        try:
            return self._types[name]
        except KeyError:
            raise NotFound(f"no job type {name!r}") from None

    def __contains__(self, name: object) -> bool:
        return name in self._types

    def __iter__(self) -> Iterator[Any]:
        return iter(self._types[n] for n in sorted(self._types))

    def __len__(self) -> int:
        return len(self._types)

    def names(self) -> list[str]:
        return sorted(self._types)

    def describe(self) -> list[dict[str, Any]]:
        """The job types for ``/meta`` and ``crhub jobs types``."""
        return [
            {
                "name": jt.name,
                "version": jt.version,
                "scope": jt.scope,
                "host": jt.host,
                "priority": jt.priority,
                "timeout_s": jt.timeout_s,
                "axes": list(getattr(jt, "axes", ()) or ()),
                "effect": getattr(jt, "effect", None),
                "module": module_of(jt),
            }
            for jt in self
        ]


def builtin_types() -> list[Any]:
    """``noop``, ``seed.import`` and ``seed.export``."""
    from .types import noop, seed

    return [*noop.JOB_TYPES, *seed.JOB_TYPES]


def default_registry(*, features: bool = True) -> Registry:
    """The built-in job types plus every feature's ``JOB_TYPES`` (a feature whose ``jobs.py`` fails to load is
    logged and skipped, so one broken feature does not stop the scheduler)."""
    reg = Registry(builtin_types())
    if not features:
        return reg
    from region.core import features as feats

    for feature in feats.discover():
        if not feature.has("jobs"):
            continue
        try:
            types = feature.job_types()
        except Exception:
            log.exception("feature %s: jobs.py failed to load; its job types are skipped", feature.name)
            continue
        for jt in types:
            try:
                reg.register(jt)
            except Invalid:
                log.exception("feature %s: job type skipped", feature.name)
    return reg


__all__ = ["EFFECTS", "NAME_RE", "Registry", "builtin_types", "check_job_type", "default_registry", "find", "module_of"]
