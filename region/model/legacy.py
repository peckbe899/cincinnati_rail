"""Old keys and stable ids: the legacy index, ``IdLookupImpl`` (match before mint, 9.17) and the id ledger.

Old keys carry names and ordinals (``Line_8|Cincinnati State#2``, ``metro:Syacmore:715445:4331182``), so hashing them
would re-key a record on a rename. ``IdLookupImpl.id_for(lkind, key, kind=..., match=...)`` therefore tries, in order:

1. the persisted legacy index (table ``legacy``), then the namespace's id ledger in git;
2. ``match``, called with the orphans: the records of ``kind`` on the import layer that no key of this run has
   claimed. It returns the id of the one that is this key renamed (by geometry, chainage, neighbours), or ``None``;
3. only then ``ids.stable(namespace, key)``.

New mappings are buffered until ``flush()`` (``SqliteStore.apply_import(..., ids=lookup)`` flushes in the import's
own transaction, so a dry run persists nothing). A flush writes the legacy index rows and appends the new lines to
the ledger ``region/ids/<namespace>.tsv``: one line per key, ``<lkind> TAB <key> TAB <id>``, sorted, LF, with tab,
newline and backslash escaped. Two sessions running the same import add the same lines, so git merges them cleanly,
and a fresh database on another machine gets the same ids for renamed keys from the ledger.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from region.core import fsio, ids
from region.core.errors import Invalid

if TYPE_CHECKING:
    from .store import SqliteStore

LEDGER_HEADER = (
    "# id ledger (decision 9.17): <lkind> TAB <key> TAB <id>, one line per key and alias, sorted, LF.\n"
    "# Written by region.model.legacy.IdLookupImpl; never edit an id by hand.\n"
)
STATUSES = ("current", "alias")


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def _unesc(text: str) -> str:
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            out.append({"t": "\t", "n": "\n", "r": "\r", "\\": "\\"}.get(nxt, nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def ledger_path(namespace: str, ledger_dir: Path | None = None) -> Path:
    """``<ledger_dir>/<namespace>.tsv`` (default ``region/ids/``)."""
    return (Path(ledger_dir) if ledger_dir is not None else ids.NAMESPACES_FILE.parent) / f"{namespace}.tsv"


def read_ledger(path: Path) -> dict[tuple[str, str], str]:
    """``{(lkind, key): id}`` from a ledger file (an absent file is empty; CRLF reads the same)."""
    out: dict[tuple[str, str], str] = {}
    if not Path(path).is_file():
        return out
    for line in fsio.read_text(path).splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            raise Invalid(f"{path}: ledger line {line!r} is not lkind TAB key TAB id")
        k = (_unesc(parts[0]), _unesc(parts[1]))
        if k in out and out[k] != parts[2]:
            # two sessions mapped one old key to two ids (a merge kept both lines): a database built from git would
            # use one and Ben's the other, so their seeds would name ids the other lacks
            raise Invalid(
                f"{path}: {k[0]} {k[1]!r} maps to two ids, {out[k]} and {parts[2]}; keep the line of the id your "
                "database uses (crhub rec legacy shows it) and delete the other",
                errors=[{"path": str(path), "message": f"{k[0]} {k[1]!r}: {out[k]} and {parts[2]}"}],
            )
        out[k] = parts[2]
    return out


def ledger_text(entries: dict[tuple[str, str], str]) -> str:
    """The ledger file's text for ``entries``: the header then the sorted lines."""
    lines = sorted(f"{_esc(lk)}\t{_esc(k)}\t{v}" for (lk, k), v in entries.items())
    return LEDGER_HEADER + "".join(line + "\n" for line in lines)


def append_ledger(path: Path, new: dict[tuple[str, str], str]) -> bool:
    """Add ``new`` lines to a ledger (existing keys keep their id); write only when something was added."""
    have = read_ledger(path)
    added = {k: v for k, v in new.items() if k not in have}
    if not added and Path(path).is_file():
        return False
    have.update(added)
    fsio.write_atomic(path, ledger_text(have))
    return True


# ---------------------------------------------------------------------------------------------- legacy index


def lookup(con: sqlite3.Connection, lkind: str, key: str) -> str | None:
    row = con.execute("SELECT id FROM legacy WHERE lkind = ? AND key = ?", (lkind, key)).fetchone()
    return row[0] if row else None


def keys_of(con: sqlite3.Connection, id: str) -> list[dict[str, Any]]:
    """Every old key of ``id``: ``[{"lkind", "key", "status"}]``."""
    rows = con.execute("SELECT lkind, key, status FROM legacy WHERE id = ? ORDER BY lkind, key", (id,)).fetchall()
    return [{"lkind": r[0], "key": r[1], "status": r[2]} for r in rows]


def put(con: sqlite3.Connection, lkind: str, key: str, id: str, status: str = "current") -> None:
    """Insert or move one old key (inside the caller's write transaction)."""
    if status not in STATUSES:
        raise Invalid(f"legacy status {status!r} is not current or alias")
    if not ids.is_ulid(id):
        raise Invalid(f"{id!r} is not a ULID")
    con.execute(
        "INSERT INTO legacy (lkind, key, id, status) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (lkind, key) DO UPDATE SET id = excluded.id, status = excluded.status",
        (lkind, key, id, status),
    )


class IdLookupImpl:
    """``region.core.protocols.IdLookup`` over a store's legacy index and the ledger of ``namespace``.

    ``layer`` is the import layer whose records are the orphans a ``match`` may claim. ``ledger_dir`` defaults to
    ``region/ids/``; tests point it at a scratch folder.
    """

    def __init__(self, store: SqliteStore, *, layer: str, namespace: str, ledger_dir: Path | None = None) -> None:
        if namespace not in ids.namespaces():
            raise Invalid(f"unknown id namespace {namespace!r}")
        self.store = store
        self.layer = layer
        self.namespace = namespace
        self.ledger = ledger_path(namespace, ledger_dir)
        self._ledger = read_ledger(self.ledger)
        self._new: dict[tuple[str, str], tuple[str, str]] = {}
        self._heal: dict[tuple[str, str], str] = {}
        self._claimed: set[str] = set()
        # the unclaimed records of each kind on the layer, read once per run (the layer does not change until the
        # run commits), so matching n keys against n records costs n list copies, not n queries
        self._orphans: dict[str, dict[str, dict[str, Any]]] = {}
        # the legacy index of each old-key kind, read once per run on first use (it changes only when the run
        # commits): the line files' importer asks for some 1,400 ids a run, one query each before
        self._index: dict[str, dict[str, str]] = {}

    def _legacy(self, lkind: str, key: str) -> str | None:
        idx = self._index.get(lkind)
        if idx is None:
            rows = self.store._reader().execute("SELECT key, id FROM legacy WHERE lkind = ?", (lkind,)).fetchall()
            idx = self._index[lkind] = {k: i for k, i in rows}
        return idx.get(key)

    def _claim(self, id: str) -> None:
        self._claimed.add(id)
        for unclaimed in self._orphans.values():
            unclaimed.pop(id, None)

    def id_for(
        self, lkind: str, key: str, *, kind: str, match: Callable[[list[dict[str, Any]]], str | None] | None = None
    ) -> str:
        if not isinstance(key, str) or not key:
            raise Invalid("an old key is a non-empty string")
        pend = self._new.get((lkind, key))
        if pend is not None:
            self._claim(pend[0])
            return pend[0]
        found = self._legacy(lkind, key)
        if found is not None and (lkind, key) not in self._ledger and ids.namespace_of(found) == self.namespace:
            # in the legacy index but not in the ledger (a ledger write lost after its import committed): the line
            # is written again with this run's, so the ledger heals
            self._heal[(lkind, key)] = found
        if found is None:
            found = self._ledger.get((lkind, key))
            if found is not None:
                self._new[(lkind, key)] = (found, "current")
        if found is None and match is not None:
            unclaimed = self._orphans.get(kind)
            if unclaimed is None:
                unclaimed = {
                    r["id"]: r for r in self.store.layer_records(self.layer, kind) if r["id"] not in self._claimed
                }
                self._orphans[kind] = unclaimed
            got = match(list(unclaimed.values()))
            if got is not None:
                if got not in unclaimed:
                    raise Invalid(f"match returned {got!r}, which is not one of the orphans")
                found = got
                self._new[(lkind, key)] = (found, "current")
        if found is None:
            found = ids.stable(self.namespace, key)
            self._new[(lkind, key)] = (found, "current")
        self._claim(found)
        return found

    @property
    def pending(self) -> dict[tuple[str, str], str]:
        """The mappings made since the last flush."""
        return {k: v[0] for k, v in self._new.items()}

    def flush_into(self, con: sqlite3.Connection) -> dict[tuple[str, str], str]:
        """Write the buffered mappings to the legacy index on ``con`` (in the caller's transaction); other keys of the
        same id become aliases. Returns what was written; ``write_ledger`` must follow once committed."""
        written = {}
        for (lkind, key), (id, status) in sorted(self._new.items()):
            con.execute("UPDATE legacy SET status = 'alias' WHERE id = ? AND lkind = ? AND key <> ?", (id, lkind, key))
            put(con, lkind, key, id, status)
            written[(lkind, key)] = id
        return written

    def write_ledger(self, written: dict[tuple[str, str], str]) -> None:
        lines = {**self._heal, **(written or {})}
        if lines:
            append_ledger(self.ledger, lines)
            self._ledger.update(lines)
        self._new.clear()
        self._heal.clear()
        self._orphans.clear()

    def flush(self) -> dict[tuple[str, str], str]:
        """Persist the buffered mappings now (index and ledger)."""
        written = self.store._writer.run(self.flush_into)
        self.write_ledger(written)
        return written


__all__ = [
    "IdLookupImpl",
    "LEDGER_HEADER",
    "append_ledger",
    "keys_of",
    "ledger_path",
    "ledger_text",
    "lookup",
    "put",
    "read_ledger",
]
