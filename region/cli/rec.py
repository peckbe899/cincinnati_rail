"""``crhub rec``: read and write single records from the command line (decision 9.28).

    crhub rec get     KIND ID            [--layer L --year Y --month M --tl canon|real] [--at VERSION]
    crhub rec list    KIND               [view] [--parent ID] [--ref ID] [--q TEXT] [--ids A,B] [--limit N] [--after ID]
    crhub rec history KIND ID            [view]
    crhub rec legacy  LKIND KEY
    crhub rec create  KIND FILE|-        [--layer L] [--id ULID]
    crhub rec put     KIND ID FILE|-     (--if-match ETAG | --latest) [--layer L]
    crhub rec patch   KIND ID FILE|-     (--if-match ETAG | --latest) [--layer L]
    crhub rec delete  KIND ID            (--if-match ETAG | --latest) [--layer L]
    crhub rec revert  CHANGESET

``FILE`` holds JSON: the record's body ``{"data": {...}, "geom": null}`` for ``create`` and ``put``, an RFC 6902
patch (a list of operations) for ``patch``; ``-`` reads it from stdin. A file may be UTF-8 (with or without a BOM)
or UTF-16, as Windows PowerShell writes them. In Windows PowerShell 5.1 pass a file, not a pipe: its pipe turns
every character outside ASCII into ``?`` before the hub sees it. ``--latest`` takes the record's current ETag
first (read, then write; a write that lands in between still makes the write a 412). Output is the JSON answer.

**Where it goes.** While a serving hub holds ``var``'s lock, every command goes through that hub's HTTP API, so the
server stays the one writer and its clients see the change at once. Otherwise reads open the database read-only and
writes take the lock themselves (a hub cannot start under them). ``--db`` names another database, opened directly.
``--by`` names the writer (default: the config's ``user``, ``ben``).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any

WRITES = ("create", "put", "patch", "delete", "revert")


def _view_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--layer", default="main")
    p.add_argument("--year", type=int, default=None)
    p.add_argument("--month", type=int, default=None)
    p.add_argument("--tl", default="canon", choices=("canon", "real"))


def _match_args(p: argparse.ArgumentParser) -> None:
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--if-match", default=None, help='the ETag the write is based on ("main:3")')
    g.add_argument("--latest", action="store_true", help="use the record's current ETag")


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("rec", help="read and write records (through the hub while it serves)")
    p.add_argument("--db", type=Path, default=None, help="open this database directly")
    p.add_argument("--by", default=None, help="who writes (default: the config's user)")
    sub = p.add_subparsers(dest="action", metavar="<action>")
    g = sub.add_parser("get", help="one record")
    g.add_argument("kind")
    g.add_argument("id")
    g.add_argument("--at", type=int, default=None)
    _view_args(g)
    li = sub.add_parser("list", help="records of a kind")
    li.add_argument("kind")
    for name in ("--parent", "--ref", "--q", "--ids", "--after"):
        li.add_argument(name, default=None)
    li.add_argument("--limit", type=int, default=500)
    _view_args(li)
    h = sub.add_parser("history", help="every revision of a record")
    h.add_argument("kind")
    h.add_argument("id")
    _view_args(h)
    lg = sub.add_parser("legacy", help="the record an old key maps to")
    lg.add_argument("lkind")
    lg.add_argument("key")
    c = sub.add_parser("create", help="create a record from a body file")
    c.add_argument("kind")
    c.add_argument("file")
    c.add_argument("--id", default=None)
    c.add_argument("--layer", default="main")
    for action, about in (("put", "replace a record's body"), ("patch", "apply an RFC 6902 patch")):
        w = sub.add_parser(action, help=about)
        w.add_argument("kind")
        w.add_argument("id")
        w.add_argument("file")
        w.add_argument("--layer", default="main")
        _match_args(w)
    d = sub.add_parser("delete", help="tombstone a record")
    d.add_argument("kind")
    d.add_argument("id")
    d.add_argument("--layer", default="main")
    _match_args(d)
    r = sub.add_parser("revert", help="undo a changeset")
    r.add_argument("changeset")
    p.set_defaults(func=run)


def decode_body(raw: bytes, where: str) -> str:
    """The text of a body file's bytes, by its byte order mark: UTF-8 (with or without a BOM, which Windows
    PowerShell's ``Out-File -Encoding utf8`` writes) or UTF-16 (what its ``>`` writes). ``Invalid`` otherwise, so a
    file in another encoding is never read as wrong characters. A U+FFFD or a ``?`` where PowerShell 5.1's pipe
    replaced a character cannot be told apart here; a file is the safe way to pass a body there."""
    from region.core.errors import Invalid

    try:
        if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
            return raw.decode("utf-16")
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise Invalid(f"{where} is not UTF-8 or UTF-16 text: {e}") from None


def _read_json(name: str) -> Any:
    from region.core.errors import Invalid

    where = "the body on stdin" if name == "-" else name
    try:
        if name == "-":
            buf = getattr(sys.stdin, "buffer", None)
            raw = buf.read() if buf is not None else sys.stdin.read().encode("utf-8")
        else:
            raw = Path(name).read_bytes()
    except OSError as e:
        raise Invalid(f"cannot read {where}: {e}") from None
    try:
        return json.loads(decode_body(raw, where))
    except json.JSONDecodeError as e:
        raise Invalid(f"{where} is not JSON: {e}") from None


def _body(doc: Any) -> dict[str, Any]:
    from region.core.errors import Invalid

    if not isinstance(doc, dict) or not isinstance(doc.get("data"), dict):
        raise Invalid('the body file holds {"data": {...}, "geom": ...}')
    return {k: doc[k] for k in ("data", "geom", "kv", "source") if k in doc}


def _view(args: argparse.Namespace) -> Any:
    from region.core.view import View

    return View(
        layer=getattr(args, "layer", "main") or "main",
        year=getattr(args, "year", None),
        month=getattr(args, "month", None),
        timeline=getattr(args, "tl", "canon") or "canon",
    )


class _Http:
    """The commands through a serving hub."""

    def __init__(self, client: Any) -> None:
        self.c = client

    def etag(self, kind: str, id: str, view: Any) -> str:
        _s, headers, _b = self.c.request("GET", f"/k/{kind}/{id}", query=view.query())
        return headers.get("ETag") or headers.get("etag") or ""

    def do(self, args: argparse.Namespace) -> Any:
        a = args.action
        view = _view(args)
        q = view.query()
        if a == "get":
            return self.c.json("GET", f"/k/{args.kind}/{args.id}", query={**q, "at": args.at})
        if a == "list":
            f = {k: getattr(args, k) for k in ("parent", "ref", "q", "ids", "after")}
            return self.c.json("GET", f"/k/{args.kind}", query={**q, **f, "limit": args.limit})
        if a == "history":
            return self.c.json("GET", f"/k/{args.kind}/{args.id}/history", query=q)
        if a == "legacy":
            from urllib.parse import quote

            return self.c.json("GET", f"/legacy/{quote(args.lkind, safe='')}/{quote(args.key, safe='')}")
        if a == "revert":
            return self.c.json("POST", f"/changesets/{args.changeset}/revert")
        if a == "create":
            body = _body(_read_json(args.file))
            if args.id:
                body["id"] = args.id
            return self.c.json("POST", f"/k/{args.kind}", query=q, json_body=body)
        tag = self.etag(args.kind, args.id, view) if args.latest else args.if_match
        h = {"If-Match": tag}
        path = f"/k/{args.kind}/{args.id}"
        if a == "put":
            return self.c.json("PUT", path, query=q, json_body=_body(_read_json(args.file)), headers=h)
        if a == "patch":
            return self.c.json(
                "PATCH", path, query=q, json_body=_read_json(args.file), headers=h,
                content_type="application/json-patch+json",
            )
        return self.c.json("DELETE", path, query=q, headers=h)


class _Direct:
    """The commands on a database opened here."""

    def __init__(self, store: Any, by: str) -> None:
        self.s = store
        self.by = by

    def do(self, args: argparse.Namespace) -> Any:
        import dataclasses

        from region.core.protocols import Op, etag

        a = args.action
        view = _view(args)
        s = self.s
        if a == "get":
            return s.get(args.kind, args.id, view, at=args.at)
        if a == "list":
            ids = args.ids.split(",") if args.ids else None
            items, nxt = s.list(
                args.kind, view, parent=args.parent, ref=args.ref, ids=ids, q=args.q, limit=args.limit,
                after=args.after,
            )
            return {"items": items, "next": nxt}
        if a == "history":
            return {"items": s.history(args.kind, args.id, view)}
        if a == "legacy":
            from region.core.errors import NotFound

            hit = s.legacy_record(args.lkind, args.key)
            if hit is None:
                raise NotFound(f"no record for {args.lkind} {args.key!r}")
            return hit
        client = "crhub-rec"
        if a == "revert":
            return dataclasses.asdict(s.revert(args.changeset, by=self.by, client=client))
        if a == "create":
            body = _body(_read_json(args.file))
            res = s.write(
                [Op("create", args.kind, args.id, None, body=body)], view, by=self.by,
                message=f"create {args.kind}", client=client,
            )
            return res.records[0]
        if args.latest:
            cur = s.get(args.kind, args.id, view)
            tag = etag(cur["layer"], cur["version"])
        else:
            tag = args.if_match
        if a == "put":
            rec = {"kind": args.kind, "id": args.id, **_body(_read_json(args.file))}
            return s.put(rec, view, if_match=tag, by=self.by, client=client)
        if a == "patch":
            return s.patch(args.kind, args.id, _read_json(args.file), view, if_match=tag, by=self.by, client=client)
        return s.delete(args.kind, args.id, view, if_match=tag, by=self.by, client=client)


def run(args: argparse.Namespace) -> int:
    from region.core import lock, paths

    if getattr(args, "action", None) is None:
        print("crhub rec: name an action (get, list, history, legacy, create, put, patch, delete, revert)",
              file=sys.stderr)
        return 2
    cfg = paths.config()
    by = args.by or str(cfg.get("user") or "ben")
    var = paths.var_root(cfg)
    write = args.action in WRITES
    if args.db is None:
        from region.api.client import running_hub

        hub = running_hub(var, client="crhub-rec", by=args.by)
        if hub is not None:
            out = _Http(hub).do(args)
            print(json.dumps(out, indent=1, ensure_ascii=False))
            return 0
    db = Path(args.db) if args.db is not None else var / "region.db"
    from region.core import fsio
    from region.model import open_store

    if not write:
        with open_store(db, readonly=True) as store:
            out = _Direct(store, by).do(args)
    else:
        with lock.acquire(var, 0, command="crhub rec"):
            allow = fsio.allow_writes(db.parent) if args.db is not None else contextlib.nullcontext()
            with allow, open_store(db, create=False) as store:
                out = _Direct(store, by).do(args)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0
