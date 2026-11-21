"""Layers (decision 9.10): one copy-on-write mechanism for imports, the old hub, Ben's design and scenarios.

The tiers are fixed. ``import:*`` layers are siblings at the bottom, each owning a disjoint id namespace. Above them
sits ``legacy:old_hub``, above that ``main``, and scenario and proposal layers form a tree under main. Named
versions are tags.

**The chain** of a layer is where a read looks, in order: the layer, its ancestors up to ``main``, then every legacy
layer, then every import layer. The first revision found wins; a tombstone hides the record. An import layer's chain
is itself then the other import layers; a legacy layer's is itself, the other legacy layers, then the imports.

This module also holds the layer operations: create, promote, tag, the as-of read of a tag, and the layer diff.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from region.core import ids
from region.core.errors import Conflict, Invalid, NotFound
from region.core.view import LAYER_RE

from .db import now
from .records import SELECT, Rev, rev_of

TIERS = ("import", "legacy", "main", "scenario", "proposal")
STATES = ("open", "promoted", "archived")
_DEPTH = {"import": 0, "legacy": 1, "main": 2}


@dataclass(frozen=True)
class Layer:
    """One row of the layer table."""

    id: int
    slug: str
    tier: str
    parent: int | None
    namespace: str | None
    state: str
    title: str | None
    note: str | None
    created: str | None
    by: str | None

    def describe(self, slugs: dict[int, str]) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "tier": self.tier,
            "parent": slugs.get(self.parent) if self.parent else None,
            "namespace": self.namespace,
            "state": self.state,
            "title": self.title,
            "note": self.note,
            "created": self.created,
            "by": self.by,
        }


class Layers:
    """A snapshot of the layer table with chain resolution."""

    def __init__(self, rows: list[Layer]) -> None:
        self.by_id = {r.id: r for r in rows}
        self.by_slug = {r.slug: r for r in rows}
        self.slugs = {r.id: r.slug for r in rows}

    def get(self, slug: str) -> Layer:
        found = self.by_slug.get(slug)
        if found is None:
            raise NotFound(f"no layer {slug!r}", layer=slug)
        return found

    def of_tier(self, tier: str) -> list[Layer]:
        return sorted((r for r in self.by_id.values() if r.tier == tier), key=lambda r: r.id)

    def chain(self, slug: str) -> list[Layer]:
        """The read chain of ``slug`` (see the module doc)."""
        layer = self.get(slug)
        imports = self.of_tier("import")
        legacy = self.of_tier("legacy")
        if layer.tier == "import":
            return [layer] + [r for r in imports if r.id != layer.id]
        if layer.tier == "legacy":
            return [layer] + [r for r in legacy if r.id != layer.id] + imports
        out: list[Layer] = []
        seen: set[int] = set()
        cur: Layer | None = layer
        while cur is not None and cur.id not in seen:
            out.append(cur)
            seen.add(cur.id)
            if cur.tier == "main":
                break
            cur = self.by_id.get(cur.parent) if cur.parent is not None else None
        if not any(r.tier == "main" for r in out):
            out.extend(self.of_tier("main"))
        return out + legacy + imports

    def depth(self, layer: Layer) -> int:
        """0 for imports, 1 for legacy, 2 for main, then one more per step below main."""
        if layer.tier in _DEPTH:
            return _DEPTH[layer.tier]
        n, cur, seen = 2, layer, set()
        while cur.parent is not None and cur.id not in seen:
            seen.add(cur.id)
            cur = self.by_id[cur.parent]
            n += 1
            if cur.tier == "main":
                break
        return n

    def above(self, layer: Layer) -> list[Layer]:
        """The layers whose chain holds ``layer`` (excluding itself), lowest first: those a change to it can make
        stale."""
        out = [r for r in self.by_id.values() if r.id != layer.id and layer.id in {c.id for c in self.chain(r.slug)}]
        return sorted(out, key=lambda r: (self.depth(r), r.id))


def load(con: sqlite3.Connection) -> Layers:
    """The layer table as a ``Layers`` snapshot."""
    rows = con.execute(
        "SELECT id, slug, tier, parent, namespace, state, title, note, created, by FROM layer ORDER BY id"
    ).fetchall()
    return Layers([Layer(*r) for r in rows])


def tier_of(slug: str) -> str:
    """The tier a new layer's slug implies: ``import:*``, ``legacy:*``, ``main``, ``proposal:*``, else scenario."""
    if slug == "main":
        return "main"
    head = slug.split(":", 1)[0] if ":" in slug else ""
    return {"import": "import", "legacy": "legacy", "proposal": "proposal"}.get(head, "scenario")


def create(
    con: sqlite3.Connection,
    slug: str,
    *,
    tier: str | None = None,
    parent: str | None = "main",
    namespace: str | None = None,
    title: str | None = None,
    note: str | None = None,
    by: str = "",
) -> Layer:
    """Insert a layer row (inside the caller's write transaction) and return it."""
    if not isinstance(slug, str) or not LAYER_RE.match(slug):
        raise Invalid(f"{slug!r} is not a layer slug", errors=[{"path": "/slug", "message": "layer slug"}])
    tier = tier or tier_of(slug)
    if tier not in TIERS or tier == "main":
        raise Invalid(f"a new layer's tier is import, legacy, scenario or proposal, not {tier!r}")
    layers = load(con)
    if slug in layers.by_slug:
        raise Conflict(f"layer {slug!r} exists", reason="exists", conflicts=[{"kind": "layer", "id": slug}])
    parent_id = None
    if tier in ("scenario", "proposal"):
        p = layers.get(parent or "main")
        if p.tier not in ("main", "scenario", "proposal"):
            raise Invalid(f"a {tier} layer sits under main or another scenario, not {p.slug!r}")
        parent_id = p.id
        namespace = None
    elif tier == "import":
        if not namespace or namespace not in ids.namespaces():
            raise Invalid(f"import layer {slug!r} needs a namespace declared in region/ids/namespaces.yaml")
        taken = [r.slug for r in layers.of_tier("import") if r.namespace == namespace]
        if taken:
            raise Conflict(
                f"namespace {namespace!r} is owned by layer {taken[0]!r}",
                reason="namespace",
                conflicts=[{"kind": "layer", "id": taken[0]}],
            )
    cur = con.execute(
        "INSERT INTO layer (slug, tier, parent, namespace, state, title, note, created, by) "
        "VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?)",
        (slug, tier, parent_id, namespace, title, note, now(), by),
    )
    return load(con).by_id[int(cur.lastrowid or 0)]


def ensure_namespace_layers(con: sqlite3.Connection) -> list[str]:
    """Add a layer for every declared (non-test) namespace that has none; return the slugs added."""
    layers = load(con)
    added = []
    for ns in ids.namespaces().values():
        if ns.test or ns.layer in layers.by_slug:
            continue
        con.execute(
            "INSERT INTO layer (slug, tier, parent, namespace, state, title, created, by) "
            "VALUES (?, ?, NULL, ?, 'open', ?, ?, 'open_store')",
            (ns.layer, tier_of(ns.layer), ns.name, ns.about, now()),
        )
        added.append(ns.layer)
    return added


def set_state(con: sqlite3.Connection, layer: Layer, state: str) -> None:
    if state not in STATES:
        raise Invalid(f"layer state {state!r} is not one of {', '.join(STATES)}")
    con.execute("UPDATE layer SET state = ? WHERE id = ?", (state, layer.id))


# ------------------------------------------------------------------------------------------------------ reading


def resolve(con: sqlite3.Connection, chain: list[Layer], id: str) -> Rev | None:
    """The revision of ``id`` that wins in ``chain`` (a tombstone included), or ``None``."""
    if not chain:
        return None
    marks = ",".join("?" * len(chain))
    rows = con.execute(
        f"SELECT {SELECT} FROM rec r WHERE r.id = ? AND r.layer IN ({marks})", (id, *[c.id for c in chain])
    ).fetchall()
    if not rows:
        return None
    rank = {c.id: i for i, c in enumerate(chain)}
    return rev_of(min(rows, key=lambda r: rank[r[3]]))


def hist_row(con: sqlite3.Connection, layer_id: int, id: str, version: int) -> dict[str, Any] | None:
    """One past version (get() shape) of a revision, from ``rec_hist``."""
    row = con.execute(
        "SELECT row FROM rec_hist WHERE layer = ? AND id = ? AND version = ?", (layer_id, id, version)
    ).fetchone()
    return json.loads(row[0]) if row else None


def hist_by_hash(con: sqlite3.Connection, id: str, h: str) -> dict[str, Any] | None:
    """Some past revision (get() shape) of ``id`` whose content hash is ``h``: the base of a three-way merge."""
    row = con.execute(
        "SELECT row FROM rec_hist WHERE id = ? AND hash = ? ORDER BY rowid DESC LIMIT 1", (id, h)
    ).fetchone()
    return json.loads(row[0]) if row else None


def as_of_rows(
    con: sqlite3.Connection, chain: list[Layer], seq: int, *, kind: str | None = None, id: str | None = None
) -> list[dict[str, Any]]:
    """The records resolved in ``chain`` as of event ``seq``, from ``rec_hist`` (tombstones included, by id)."""
    rank = {c.id: i for i, c in enumerate(chain)}
    marks = ",".join("?" * len(chain))
    sql = (
        f"SELECT h.layer, h.id, h.version, h.row FROM rec_hist h JOIN changeset c ON c.id = h.changeset "
        f"WHERE h.layer IN ({marks}) AND c.seq IS NOT NULL AND c.seq <= ?"
    )
    args: list[Any] = [*[c.id for c in chain], seq]
    if id is not None:
        sql += " AND h.id = ?"
        args.append(id)
    if kind is not None:
        sql += " AND h.id IN (SELECT id FROM rec WHERE kind = ?)"
        args.append(kind)
    best: dict[str, tuple[int, int, str]] = {}
    for layer_id, rid, version, row in con.execute(sql, args):
        key = (rank[layer_id], -version)
        cur = best.get(rid)
        if cur is None or key < (cur[0], cur[1]):
            best[rid] = (key[0], key[1], row)
    return [json.loads(best[k][2]) for k in sorted(best)]


def tag(con: sqlite3.Connection, layer: Layer, name: str, *, by: str, note: str | None = None) -> dict[str, Any]:
    """Name the layer as it stands now (the newest event ``seq``)."""
    if not isinstance(name, str) or not name or len(name) > 64:
        raise Invalid("a tag name is 1 to 64 characters")
    if con.execute("SELECT 1 FROM tag WHERE layer = ? AND name = ?", (layer.id, name)).fetchone():
        raise Conflict(f"tag {name!r} exists on {layer.slug}", reason="exists", conflicts=[{"kind": "tag", "id": name}])
    seq = con.execute("SELECT coalesce(max(seq), 0) FROM event").fetchone()[0]
    t = now()
    con.execute(
        "INSERT INTO tag (layer, name, seq, note, created, by) VALUES (?, ?, ?, ?, ?, ?)",
        (layer.id, name, seq, note, t, by),
    )
    return {"layer": layer.slug, "name": name, "seq": seq, "note": note, "created": t, "by": by}


def tag_seq(con: sqlite3.Connection, layer: Layer, name: str) -> int:
    row = con.execute("SELECT seq FROM tag WHERE layer = ? AND name = ?", (layer.id, name)).fetchone()
    if not row:
        raise NotFound(f"no tag {name!r} on layer {layer.slug}")
    return int(row[0])


def tags(con: sqlite3.Connection, layer: Layer) -> list[dict[str, Any]]:
    rows = con.execute(
        "SELECT name, seq, note, created, by FROM tag WHERE layer = ? ORDER BY seq, name", (layer.id,)
    ).fetchall()
    return [{"layer": layer.slug, "name": r[0], "seq": r[1], "note": r[2], "created": r[3], "by": r[4]} for r in rows]


__all__ = [
    "Layer",
    "Layers",
    "STATES",
    "TIERS",
    "as_of_rows",
    "create",
    "ensure_namespace_layers",
    "hist_by_hash",
    "hist_row",
    "load",
    "resolve",
    "set_state",
    "tag",
    "tag_seq",
    "tags",
    "tier_of",
]
