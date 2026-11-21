"""Plans: what a job read through ``PlanCtx``, and the key that makes (decisions 9.16 and 9.19).

A job type's ``plan(ctx, scope_id)`` reads only through the ``PlanContext`` it is given. Every read is recorded as
a ref with its content hash, and exactly those refs make the job's key and, once a result is committed, its rows in
``result_dep``:

- ``read(kind, id)`` gives ``rec:<id>`` with the record's content hash (``None`` when it does not resolve: an
  absence is a dependency too, so creating the record invalidates the plan);
- ``list(kind, **filters)`` gives ``rec:<id>`` for each record returned, plus one query ref
  ``rec:<kind>?<filters as canonical JSON>`` hashed over the ``[id, hash]`` pairs, so a record joining or leaving
  the answer changes the key;
- ``param(path, scope)`` gives ``param:<path>`` (``param:<path>@<scope>`` when scoped) with the hash of the value;
- ``file(uri)`` gives ``file:<uri>`` with the file's sha256 (``None`` when it is missing);
- ``need(type, scope)`` gives ``job:<type>/<scope>`` with the upstream result's ``output_hash`` (early cutoff);
- ``axis(name)`` declares a view axis; only declared axes (and a type's static ``axes``) enter the key.

**Plans never write.** The store a plan reads through is a ``ReadOnlyStore``: it forwards reads and refuses every
write with ``JobWriteRefused``. ``PlanContext`` and ``hosts.RunContext`` have no write method at all.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from region.core import fsio, paths
from region.core.errors import EngineUnavailable, Invalid, NotFound
from region.core.protocols import Store, ref_file, ref_job, ref_param, ref_rec
from region.core.view import AXES, View

from . import keys

PARAM_KIND = "param"
"""The record kind whose events invalidate every ``param:`` dependency."""


class JobWriteRefused(PermissionError):
    """A job tried to write through what its plan or run context gave it. Jobs return outputs; they never write."""


_WRITE_METHODS = ("write", "put", "patch", "delete", "revert", "restore", "apply_import")


class ReadOnlyStore:
    """The only face of the ``Store`` a plan sees: ``get``, ``list``, ``hash_of``, ``legacy`` and ``history`` are
    forwarded; ``write``, ``put``, ``patch``, ``delete``, ``revert``, ``restore`` and ``apply_import`` raise
    ``JobWriteRefused``. The real store is held in closures, not in an attribute."""

    __slots__ = ("get", "list", "hash_of", "legacy", "history")

    def __init__(self, store: Store) -> None:
        def get(kind: str, id: str, view: View, *, at: int | None = None) -> dict[str, Any]:
            return store.get(kind, id, view, at=at)

        def list_(kind: str, view: View, **filters: Any) -> tuple[list[dict[str, Any]], str | None]:
            return store.list(kind, view, **filters)

        def hash_of(ref: str, view: View) -> str | None:
            return store.hash_of(ref, view)

        def legacy(lkind: str, key: str) -> str | None:
            return store.legacy(lkind, key)

        def history(kind: str, id: str, view: View) -> list[dict[str, Any]]:
            return store.history(kind, id, view)

        object.__setattr__(self, "get", get)
        object.__setattr__(self, "list", list_)
        object.__setattr__(self, "hash_of", hash_of)
        object.__setattr__(self, "legacy", legacy)
        object.__setattr__(self, "history", history)

    def __setattr__(self, name: str, value: Any) -> None:
        raise JobWriteRefused("a job's store is read-only")

    def _refuse(self, *args: Any, **kwargs: Any) -> Any:
        raise JobWriteRefused("jobs never write input tables: return outputs from run instead")

    write = put = patch = delete = revert = restore = apply_import = _refuse


ParamResolver = Callable[[ReadOnlyStore, View, str, "str | None"], Any]
"""Resolves a param for a plan: ``(store, view, path, scope) -> value``; raises ``NotFound`` for an unknown path."""


def all_records(store: ReadOnlyStore | Store, kind: str, view: View, **filters: Any) -> list[dict[str, Any]]:
    """Every record of ``kind`` in ``view`` (following ``list``'s pages)."""
    out: list[dict[str, Any]] = []
    after = filters.pop("after", None)
    limit = filters.pop("limit", None)
    while True:
        page, after = store.list(kind, view, **filters, limit=limit or 500, after=after)
        out.extend(page)
        if limit is not None or after is None:
            return out


def _scope_id(scope: Any) -> str | None:
    if scope is None or scope in ("", "system"):
        return None
    if isinstance(scope, dict):
        return scope.get("id") or scope.get("section") or scope.get("route")
    return str(scope)


def resolve_param(store: ReadOnlyStore, view: View, path: str, scope: str | None = None) -> Any:
    """The default param resolver, over records of kind ``param`` whose data has ``path`` and ``value``.

    A record whose ``scope`` (a string id, or ``{"id": ...}``) equals ``scope`` beats one with no scope (system
    wide); a record scoped elsewhere is skipped. With a view year, a record carrying ``years: [lo, hi]`` (either end
    may be null) counts only inside that range. The rules feature (WP5) can pass its own resolver to the scheduler.
    """
    best: tuple[int, Any] | None = None
    for rec in all_records(store, PARAM_KIND, view):
        data = rec.get("data") or {}
        if data.get("path") != path:
            continue
        sid = _scope_id(data.get("scope"))
        if sid is None:
            rank = 0
        elif scope is not None and sid == scope:
            rank = 2
        else:
            continue
        years = data.get("years")
        if view.year is not None and isinstance(years, list) and len(years) == 2:
            lo, hi = years
            if (lo is not None and view.year < lo) or (hi is not None and view.year > hi):
                continue
        if best is None or rank > best[0]:
            best = (rank, data.get("value"))
    if best is None:
        raise NotFound(f"no param {path}" + (f" for {scope}" if scope else ""))
    return best[1]


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(v) for v in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def query_ref(kind: str, filters: dict[str, Any]) -> str:
    """The ref of a list query: ``rec:<kind>?<filters as canonical JSON>`` (ids are ULIDs, so no id holds ``?``)."""
    f = {k: v for k, v in filters.items() if v is not None}
    if "ids" in f:
        f["ids"] = sorted(str(i) for i in f["ids"])
    return f"rec:{kind}?" + fsio.canonical_json(_jsonable(f)).decode("utf-8")


def query_prefix(kind: str) -> tuple[str, str]:
    """The ref range ``[lo, hi)`` holding every query ref of ``kind`` (``?`` sorts just before ``@``)."""
    return f"rec:{kind}?", f"rec:{kind}@"


@dataclass
class Plan:
    """What one ``plan`` call read and returned, and the key it makes (``None`` while an upstream is missing)."""

    type: str
    version: str
    scope: str
    view: View
    host: str
    priority: int
    inputs: Any
    deps: list[list[Any]]
    kinds: dict[str, str]
    axes: dict[str, Any]
    needs: dict[str, tuple[str, str]]
    missing: list[str]
    code: str
    engine_build: str | None
    contracts: dict[str, Any]
    key: str | None
    upstream_keys: dict[str, str] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return self.key is not None


class PlanContext:
    """``region.core.protocols.PlanCtx`` for one plan. Records every read; offers no write."""

    __slots__ = (
        "view",
        "__planner",
        "__type",
        "__scope",
        "__stack",
        "__deps",
        "__kinds",
        "__axes",
        "__needs",
        "__missing",
        "__upkeys",
    )

    def __init__(self, planner: Planner, job_type: Any, scope: str, view: View, stack: tuple) -> None:
        self.view = view
        self.__planner = planner
        self.__type = job_type
        self.__scope = scope
        self.__stack = stack
        self.__deps: list[tuple[str, str | None]] = []
        self.__kinds: dict[str, str] = {}
        self.__axes: set[str] = set()
        self.__needs: dict[str, tuple[str, str]] = {}
        self.__missing: list[str] = []
        self.__upkeys: dict[str, str] = {}

    def _dep(self, ref: str, h: str | None, kind: str | None) -> None:
        self.__deps.append((ref, h))
        if kind is not None:
            self.__kinds[ref] = kind

    def read(self, kind: str, id: str) -> dict[str, Any] | None:
        try:
            rec = self.__planner.store.get(kind, id, self.view)
        except NotFound:
            rec = None
        self._dep(ref_rec(id), rec["hash"] if rec is not None else None, kind)
        return rec

    def list(self, kind: str, **filters: Any) -> list[dict[str, Any]]:
        recs = all_records(self.__planner.store, kind, self.view, **dict(filters))
        for r in recs:
            self._dep(ref_rec(r["id"]), r["hash"], r.get("kind") or kind)
        listing = [[r["id"], r["hash"]] for r in recs]
        self._dep(query_ref(kind, filters), fsio.content_hash(listing), kind)
        return recs

    def param(self, path: str, scope: str | None = None) -> Any:
        value = self.__planner.params(self.__planner.store, self.view, path, scope)
        ref = ref_param(path if scope is None else f"{path}@{scope}")
        self._dep(ref, keys.value_hash(value), None)
        return copy.deepcopy(value)

    def file(self, uri: str) -> Path:
        local = paths.resolve(uri)
        self._dep(ref_file(uri), self.__planner.file_hash(local), None)
        return local

    def need(self, job_type: str, scope_id: str) -> str:
        ref = ref_job(job_type, scope_id)
        stack = self.__stack + ((self.__type.name, self.__scope),)
        up_key, h = self.__planner.upstream(job_type, scope_id, self.view, stack)
        if h is None:
            self.__missing.append(ref)
        elif up_key is not None:
            self.__upkeys[ref] = up_key
        self.__needs[ref] = (job_type, scope_id)
        self._dep(ref, h, None)
        return ref

    def axis(self, name: str) -> Any:
        if name not in AXES:
            raise Invalid(f"{name!r} is not a view axis ({', '.join(AXES)})")
        self.__axes.add(name)
        return getattr(self.view, name)

    def _collected(self) -> tuple[list, dict, set, dict, list, dict]:
        return self.__deps, self.__kinds, self.__axes, self.__needs, self.__missing, self.__upkeys


class Planner:
    """Runs plans over a store (read-only) and the cache (file hashes, upstream results)."""

    def __init__(
        self,
        store: Store,
        *,
        registry: Any,
        file_hash: Callable[[Path], str | None],
        upstream_output: Callable[[str], str | None],
        engine_info: Callable[[], tuple[str, dict[str, Any]]],
        params: ParamResolver | None = None,
    ) -> None:
        self.store = ReadOnlyStore(store)
        self.registry = registry
        self.file_hash = file_hash
        self.upstream_output = upstream_output
        self.engine_info = engine_info
        self.params: ParamResolver = params or resolve_param

    def plan(self, type_name: str, scope: str, view: View, stack: tuple = ()) -> Plan:
        """Plan ``type_name`` for ``scope`` in ``view``: run its ``plan`` and compute the key."""
        jt = self.registry.get(type_name)
        ctx = PlanContext(self, jt, scope, view, stack)
        inputs = jt.plan(ctx, scope)
        deps, kinds, axes_read, needs, missing, upkeys = ctx._collected()
        declared = set(getattr(jt, "axes", ()) or ()) | axes_read
        axes = view.key_axes(declared)
        code = keys.code_hash(jt)
        if jt.host == "engine":
            engine_build, contracts = self.engine_info()
        else:
            engine_build, contracts = None, {}
        refs = keys.normalize_refs(deps)
        key = None
        if not missing:
            key = keys.key(jt.name, jt.version, code, refs, axes, engine_build, contracts)
        return Plan(
            type=jt.name,
            version=jt.version,
            scope=scope,
            view=view,
            host=jt.host,
            priority=int(jt.priority),
            inputs=inputs,
            deps=refs,
            kinds=dict(kinds),
            axes=axes,
            needs=dict(needs),
            missing=list(dict.fromkeys(missing)),
            code=code,
            engine_build=engine_build,
            contracts=dict(contracts),
            key=key,
            upstream_keys=dict(upkeys),
        )

    def upstream(self, type_name: str, scope: str, view: View, stack: tuple) -> tuple[str | None, str | None]:
        """``(upstream key, output_hash)`` of an upstream job in ``view``: ``output_hash`` is ``None`` until an ok
        result exists for the upstream's current key."""
        if (type_name, scope) in stack:
            chain = " -> ".join(f"{t}/{s}" for t, s in stack + ((type_name, scope),))
            raise Invalid(f"job dependency cycle: {chain}")
        up = self.plan(type_name, scope, view, stack)
        if up.key is None:
            return None, None
        return up.key, self.upstream_output(up.key)


def no_engine_info() -> tuple[str, dict[str, Any]]:
    raise EngineUnavailable("no engine is configured for this hub", reason="closed")


def iter_deps(plan: Plan) -> Iterable[tuple[str, str | None, str | None]]:
    """``(ref, hash, kind)`` rows for ``result_dep``."""
    for ref, h in plan.deps:
        yield ref, h, plan.kinds.get(ref)


__all__ = [
    "JobWriteRefused",
    "PARAM_KIND",
    "ParamResolver",
    "Plan",
    "PlanContext",
    "Planner",
    "ReadOnlyStore",
    "all_records",
    "iter_deps",
    "no_engine_info",
    "query_prefix",
    "query_ref",
    "resolve_param",
]
