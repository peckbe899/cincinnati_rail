"""A store-free ``IdLookup`` for testing importers as pure functions (section 10, WP5: importers are tested first
without a store)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from region.core import ids as core_ids


class FakeIds:
    """Match before mint over a dict: the known keys, then ``match`` over the given orphans, then
    ``ids.stable(namespace, key)``. ``orphans`` maps a kind to the records a rename match may claim."""

    def __init__(
        self,
        namespace: str,
        known: dict[tuple[str, str], str] | None = None,
        orphans: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.namespace = namespace
        self.known = dict(known or {})
        self.orphans = {k: list(v) for k, v in (orphans or {}).items()}
        self.asked: list[tuple[str, str, str]] = []
        self.claimed: set[str] = set()

    def id_for(
        self, lkind: str, key: str, *, kind: str, match: Callable[[list[dict[str, Any]]], str | None] | None = None
    ) -> str:
        self.asked.append((lkind, key, kind))
        found = self.known.get((lkind, key))
        if found is None and match is not None:
            free = [o for o in self.orphans.get(kind, []) if o["id"] not in self.claimed]
            found = match(free)
        if found is None:
            found = core_ids.stable(self.namespace, key)
        self.known[(lkind, key)] = found
        self.claimed.add(found)
        return found
