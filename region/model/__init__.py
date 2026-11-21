"""The record store (WP1): one truth database of versioned records in layers, with changesets and an outbox.

    from region.model import open_store
    store = open_store(var / "region.db")

What the spec's WP1 exposes, and where:

- ``open_store(path, *, cache=None, kinds_paths=None, ..., readonly=False) -> SqliteStore`` (here, from ``store``;
  ``readonly=True`` reads an existing file and changes nothing);
- ``region.model.migrate.migrate(con, *, backup_dir) -> list[int]``;
- ``region.model.backup.backup(db, dest, reason) -> Path`` and ``region.model.backup.restore(src, db)``;
- ``region.model.seed.export(store, out) -> dict`` and ``region.model.seed.import_seed(store, seed) -> dict``;
- ``region.model.kinds.load(paths) -> KindRegistry`` and ``region.model.legacy.IdLookupImpl``.

The functions ``migrate``, ``backup`` and ``restore`` are not re-exported here, so the module names stay modules.

Modules: ``db`` (connections, the writer thread), ``migrate``, ``kinds``, ``records``, ``geom``, ``layers``,
``changesets``, ``merge``, ``refs``, ``query``, ``legacy``, ``imports``, ``seed``, ``backup`` and ``store``.
See ``claude/Hub_Region_Architecture.md`` sections 2 (9.9 to 9.13, 9.17, 9.18, 9.24, 9.25, 9.28, 9.29) and 4.
"""

from . import kinds, legacy, seed
from .kinds import KindRegistry
from .legacy import IdLookupImpl
from .store import SqliteStore, open_store

__all__ = ["IdLookupImpl", "KindRegistry", "SqliteStore", "kinds", "legacy", "open_store", "seed"]
