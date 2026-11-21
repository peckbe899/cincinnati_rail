"""Jobs and the cache (WP3; decisions 9.18 and 9.19, section 6 of claude/Hub_Region_Architecture.md).

- ``keys``: ``key(type, version, code, refs, axes, engine_build, contracts)``, the content-addressed job key.
- ``plan``: ``PlanContext`` (``PlanCtx``) records every read as a ref with its hash; ``ReadOnlyStore``.
- ``scheduler``: ``Scheduler(store, cache_path, engine, *, threads=4, processes=2)``, the ``Scheduler`` protocol.
- ``hosts``: inline, thread, process (spawn) and engine hosts; ``RunContext`` (``RunCtx``).
- ``cache``: ``cache.db`` (``migrations/0001_cache.sql``), content-addressed blobs, ``read_array(key, name)``.
- ``goals``: the goal rows; ``registry``: the job types; ``types``: ``noop``, ``seed.import``, ``seed.export``.

Names are imported on first use, so a worker process that only needs ``hosts`` stays light.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "Scheduler": "scheduler",
    "changed_ranges": "scheduler",
    "Cache": "cache",
    "read_array": "cache",
    "default_cache_path": "cache",
    "key": "keys",
    "code_hash": "keys",
    "Registry": "registry",
    "default_registry": "registry",
    "check_job_type": "registry",
    "JobWriteRefused": "plan",
    "ReadOnlyStore": "plan",
}


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module 'region.jobs' has no attribute {name!r}")
    return getattr(import_module(f"{__name__}.{module}"), name)


__all__ = sorted(_EXPORTS)
