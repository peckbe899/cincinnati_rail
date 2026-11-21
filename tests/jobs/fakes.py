"""Fakes for the jobs tests: a ``Store`` and an ``EngineClient`` of the frozen shapes (``region.core.protocols``).

``FakeStore`` keeps records in the get() shape per layer, resolves a view's layer up its parents to ``main``, hashes
content as the real store does (``{id, kind, kv, geom, data}`` only), makes no version and no event for an
identical write, and keeps an outbox of ``record`` events (one ``changeset`` summary event instead, for a changeset
of more than 200 records). Every ``write`` call is recorded in ``writes``, so a test can prove the scheduler made
none.
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Iterable
from typing import Any

import jsonpatch

from region.core import fsio, ids
from region.core.errors import NotFound, PreconditionFailed, PreconditionRequired
from region.core.events import BULK_THRESHOLD
from region.core.protocols import Op, WriteResult, etag, parse_etag, parse_ref
from region.core.view import View


def content_hash(rec: dict[str, Any]) -> str:
    return fsio.content_hash({k: rec[k] for k in ("id", "kind", "kv", "geom", "data")})


class FakeStore:
    """``region.core.protocols.Store``, just enough for the scheduler: get, list, hash_of, events_since, write."""

    def __init__(self, *, by: str = "test") -> None:
        self._lock = threading.RLock()
        self.parents: dict[str, str | None] = {"main": None}
        self.revs: dict[str, dict[str, dict[str, Any]]] = {"main": {}}
        self.outbox: list[dict[str, Any]] = []
        self.writes: list[dict[str, Any]] = []
        self.by = by
        self._clock = 0
        self._floor = 0  # the highest seq pruned: new events continue after it, as AUTOINCREMENT does

    # ------------------------------------------------------------------------------------------------ layers

    def add_layer(self, slug: str, parent: str = "main") -> None:
        with self._lock:
            self.parents[slug] = parent
            self.revs.setdefault(slug, {})

    def chain(self, layer: str) -> list[str]:
        out = []
        cur: str | None = layer
        while cur is not None:
            if cur not in self.parents:
                raise NotFound(f"no layer {cur}")
            out.append(cur)
            cur = self.parents[cur]
        return out

    def _resolve(self, id: str, view: View) -> dict[str, Any] | None:
        for layer in self.chain(view.layer):
            rec = self.revs[layer].get(id)
            if rec is not None:
                return rec
        return None

    # ------------------------------------------------------------------------------------------------- reads

    def get(self, kind: str, id: str, view: View, *, at: int | None = None) -> dict[str, Any]:
        with self._lock:
            rec = self._resolve(id, view)
            if rec is None or rec["deleted"] or rec["kind"] != kind:
                raise NotFound(f"no {kind} {id}")
            return copy.deepcopy(rec)

    def list(
        self,
        kind: str,
        view: View,
        *,
        bbox: Any = None,
        parent: str | None = None,
        ref: str | None = None,
        ids: Iterable[str] | None = None,
        q: str | None = None,
        limit: int = 500,
        after: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        with self._lock:
            every: set[str] = set()
            for layer in self.chain(view.layer):
                every.update(self.revs[layer])
            wanted = set(ids) if ids is not None else None
            out = []
            for rid in sorted(every):
                rec = self._resolve(rid, view)
                if rec is None or rec["deleted"] or rec["kind"] != kind:
                    continue
                if wanted is not None and rid not in wanted:
                    continue
                if parent is not None and rec["data"].get("parent") != parent:
                    continue
                if q is not None and q not in str(rec["data"].get("name", "")):
                    continue
                if after is not None and rid <= after:
                    continue
                out.append(copy.deepcopy(rec))
            page = out[:limit]
            cursor = page[-1]["id"] if len(out) > limit else None
            return page, cursor

    def hash_of(self, ref: str, view: View) -> str | None:
        kind, rest = parse_ref(ref)
        if kind != "rec":
            return None
        with self._lock:
            rec = self._resolve(rest, view)
            return None if rec is None or rec["deleted"] else rec["hash"]

    def events_since(self, seq: int, limit: int = 1000) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy([e for e in self.outbox if e["seq"] > seq][:limit])

    def last_seq(self) -> int:
        """The newest event seq (the SQLite store has this too; the scheduler uses it to notice a restore)."""
        with self._lock:
            return self.outbox[-1]["seq"] if self.outbox else 0

    def min_seq(self) -> int:
        """The oldest event seq still in the outbox (the SQLite store has this too)."""
        with self._lock:
            return self.outbox[0]["seq"] if self.outbox else 0

    def prune(self, upto: int) -> None:
        """Drop outbox events with seq up to ``upto``, as a store pruning its outbox would."""
        with self._lock:
            self.outbox = [e for e in self.outbox if e["seq"] > upto]
            self._floor = max(self._floor, upto)

    def legacy(self, lkind: str, key: str) -> str | None:
        return None

    def history(self, kind: str, id: str, view: View) -> list[dict[str, Any]]:
        return [self.get(kind, id, view)]

    # ------------------------------------------------------------------------------------------------ writes

    def _now(self) -> str:
        self._clock += 1
        return f"2026-11-21T00:00:{self._clock:06d}Z"

    def write(self, ops: list[Op], view: View, *, by: str, message: str, client: str | None = None) -> WriteResult:
        with self._lock:
            self.writes.append({"ops": copy.deepcopy(ops), "view": view, "by": by, "message": message})
            layer = view.layer
            changeset = ids.new()
            changed: list[tuple[dict[str, Any], str]] = []
            results = []
            for op in ops:
                rec, verb = self._apply(op, layer, by, changeset)
                results.append(copy.deepcopy(rec))
                if verb:
                    changed.append((rec, verb))
            if not changed:
                return WriteResult(None, results, None)
            if len(changed) > BULK_THRESHOLD:
                kinds: dict[str, int] = {}
                for rec, _ in changed:
                    kinds[rec["kind"]] = kinds.get(rec["kind"], 0) + 1
                seq = self._event(
                    "changeset",
                    {
                        "id": changeset,
                        "layer": layer,
                        "by": by,
                        "count": len(changed),
                        "kinds": kinds,
                        "bbox": None,
                        "summary": True,
                    },
                )
            else:
                seq = None
                for rec, verb in changed:
                    seq = self._event(
                        "record",
                        {
                            "op": verb,
                            "kind": rec["kind"],
                            "id": rec["id"],
                            "layer": layer,
                            "version": rec["version"],
                            "hash": rec["hash"],
                            "by": by,
                            "client": client,
                            "changeset": changeset,
                            "fields": ["data"],
                            "bbox": None,
                        },
                    )
            return WriteResult(changeset, results, seq)

    def _event(self, type: str, data: dict[str, Any]) -> int:
        seq = max(self.outbox[-1]["seq"] if self.outbox else 0, self._floor) + 1
        self.outbox.append({"seq": seq, "type": type, "data": {"seq": seq, **data}})
        return seq

    def _apply(self, op: Op, layer: str, by: str, changeset: str) -> tuple[dict[str, Any], str | None]:
        view = View(layer)
        current = self._resolve(op.id, view) if op.id else None
        live = current is not None and not current["deleted"]
        if op.op != "create" and live:
            if op.if_match is None:
                raise PreconditionRequired(f"{op.kind} {op.id}: If-Match required")
            if parse_etag(op.if_match) != (current["layer"], current["version"]):
                raise PreconditionFailed(f"{op.kind} {op.id}: stale If-Match", current=copy.deepcopy(current))
        if op.op == "patch":
            body = jsonpatch.apply_patch({"data": current["data"], "geom": current["geom"]}, op.patch or [])
        elif op.op == "delete":
            body = {"data": current["data"], "geom": current["geom"]}
        else:
            body = op.body or {}
        rid = op.id or ids.new()
        new = {
            "id": rid,
            "kind": op.kind,
            "kv": 1,
            "geom": body.get("geom"),
            "data": copy.deepcopy(body.get("data") or {}),
        }
        deleted = op.op == "delete"
        own = self.revs[layer].get(rid)
        if (
            current is not None
            and content_hash(new) == current["hash"]
            and bool(current["deleted"]) == deleted
            and (own is not None or not deleted)
        ):
            return current, None
        version = own["version"] + 1 if own is not None else 1
        stamp = self._now()
        rec = {
            **new,
            "layer": layer,
            "version": version,
            "hash": content_hash(new),
            "deleted": deleted,
            "origin": "authored",
            "source": None,
            "by": by,
            "changeset": changeset,
            "created": own["created"] if own is not None else stamp,
            "updated": stamp,
        }
        self.revs[layer][rid] = rec
        verb = "delete" if deleted else ("create" if not live else op.op)
        return rec, verb

    def put(self, rec: dict[str, Any], view: View, *, if_match: str | None, by: str) -> dict[str, Any]:
        op = Op("put", rec["kind"], rec["id"], if_match, body={"data": rec.get("data"), "geom": rec.get("geom")})
        return self.write([op], view, by=by, message="put").records[0]

    def patch(self, kind: str, id: str, patch: list[dict], view: View, *, if_match: str, by: str) -> dict[str, Any]:
        return self.write([Op("patch", kind, id, if_match, patch=patch)], view, by=by, message="patch").records[0]

    def delete(self, kind: str, id: str, view: View, *, if_match: str, by: str) -> dict[str, Any]:
        return self.write([Op("delete", kind, id, if_match)], view, by=by, message="delete").records[0]

    def revert(self, changeset: str, *, by: str) -> WriteResult:
        raise NotImplementedError

    def apply_import(self, run: Any, records: Iterable[dict[str, Any]], *, dry_run: bool) -> Any:
        raise NotImplementedError

    # ---------------------------------------------------------------------------------------- test helpers

    def set(
        self,
        kind: str,
        id: str,
        data: dict[str, Any],
        *,
        layer: str = "main",
        geom: str | None = None,
        by: str | None = None,
    ) -> dict[str, Any]:
        """Create or replace one record (an authored write, with If-Match from the record as it resolves)."""
        view = View(layer)
        with self._lock:
            cur = self._resolve(id, view)
            tag = etag(cur["layer"], cur["version"]) if cur is not None and not cur["deleted"] else None
        op = Op("put" if tag else "create", kind, id, tag, body={"data": data, "geom": geom})
        return self.write([op], view, by=by or self.by, message="test").records[0]

    def remove(self, kind: str, id: str, *, layer: str = "main") -> dict[str, Any]:
        view = View(layer)
        cur = self.get(kind, id, view)
        return self.delete(kind, id, view, if_match=etag(cur["layer"], cur["version"]), by=self.by)

    def bulk(self, kind: str, items: dict[str, dict[str, Any]], *, layer: str = "main") -> WriteResult:
        """One changeset of many records (over 200 gives one summary event)."""
        view = View(layer)
        ops = []
        with self._lock:
            for rid, data in items.items():
                cur = self._resolve(rid, view)
                tag = etag(cur["layer"], cur["version"]) if cur is not None and not cur["deleted"] else None
                ops.append(Op("put" if tag else "create", kind, rid, tag, body={"data": data, "geom": None}))
        return self.write(ops, view, by=self.by, message="bulk")

    def restore(self, *args: Any, **kwargs: Any) -> Any:
        """``Store.restore`` (a record version) is not faked; ``restore_db`` stands in for a database restore."""
        raise NotImplementedError

    def restore_db(self, revs: dict[str, Any], seq: int) -> None:
        """Stand in for a database restore: the records go back to ``revs`` and the outbox back to ``seq``."""
        with self._lock:
            self.revs = copy.deepcopy(revs)
            self.outbox = [e for e in self.outbox if e["seq"] <= seq]
            self._floor = min(self._floor, seq)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self.revs)


class FakeEngine:
    """``region.core.protocols.EngineClient`` answering from a function ``answer(method, params) -> dict``."""

    def __init__(self, build: str = "e" * 64, contracts: dict[str, int] | None = None, answer: Any = None) -> None:
        self.build = build
        self.contracts = dict(contracts or {"section_input": 0, "vertical_rail": 0})
        self.answer = answer or (lambda method, params: {"method": method, "echo": params})
        self.calls: list[tuple[str, dict[str, Any], float]] = []
        self.closed = False

    def hello(self) -> dict[str, Any]:
        return {
            "engine_version": "0.0.0-test",
            "engine_build": self.build,
            "contracts": dict(self.contracts),
            "methods": ["vertical.rail@1"],
        }

    def call(self, method: str, params: dict[str, Any], *, timeout_s: float = 30.0) -> dict[str, Any]:
        self.calls.append((method, copy.deepcopy(params), timeout_s))
        return self.answer(method, params)

    def close(self) -> None:
        self.closed = True
