"""Changeset routes: ``POST /changesets`` (atomic, every stale op listed in the 412), the list and one changeset,
and ``POST /changesets/{id}/revert`` (undo: a 409 with a diff for every record edited since, decision 9.13)."""

from __future__ import annotations

import dataclasses
from typing import Any

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import Response

from region.core.errors import Invalid
from region.core.protocols import Op
from region.core.view import View

from . import models as M
from .context import fingerprint, hub_of, writer_of
from .http import json_response
from .records import check_kind

router = APIRouter(tags=["changesets"])


def write_result(res: Any) -> dict[str, Any]:
    """A ``WriteResult`` as JSON."""
    return dataclasses.asdict(res) if dataclasses.is_dataclass(res) else dict(res)


def _op(request: Request, i: int, o: M.OpIn) -> Op:
    check_kind(request, o.kind)
    body = None
    if o.body is not None:
        raw = o.body.model_dump(exclude_unset=True)
        body = {"data": raw["data"], "geom": raw.get("geom")}
        for k in ("kv", "source"):
            if raw.get(k) is not None:
                body[k] = raw[k]
    patch = [p.raw() for p in o.patch] if o.patch is not None else None
    if o.op in ("create", "put") and body is None:
        raise Invalid(f"op {i} ({o.op}) needs a body", errors=[{"path": f"/body/ops/{i}/body", "message": "required"}])
    if o.op == "patch" and patch is None:
        raise Invalid(f"op {i} (patch) needs a patch", errors=[{"path": f"/body/ops/{i}/patch", "message": "required"}])
    return Op(o.op, o.kind, o.id, o.if_match, body=body, patch=patch)


@router.post(
    "/changesets",
    response_model=M.WriteResult,
    responses=M.problems(404, 409, 412, 422, 428),
    summary="Write a changeset",
    description="Every op is validated before any is written; a 412 lists every stale op in stale.",
)
def post_changeset(
    request: Request,
    cs: M.ChangesetIn,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=255),
) -> Response:
    hub = hub_of(request)
    w = writer_of(request)
    view = View(layer=cs.layer)
    ops = [_op(request, i, o) for i, o in enumerate(cs.ops)]

    def do() -> dict[str, Any]:
        res = hub.store.write(ops, view, by=w.by, message=cs.message or f"{len(ops)} op(s)", client=w.client)
        return write_result(res)

    if idempotency_key:
        fp = fingerprint("changeset", cs.model_dump(by_alias=True, exclude_unset=True))
        _replayed, out = hub.idempotency.run(w.client or "", idempotency_key, fp, do)
    else:
        out = do()
    return json_response(out)


@router.get("/changesets", response_model=M.ChangesetList, summary="Changesets, newest first")
def list_changesets(
    request: Request,
    by: str | None = None,
    since: str | None = Query(None, description="an event seq, or an ISO time"),
    layer: str | None = None,
    kind: str | None = Query(None, description="edit, import, seed, revert, rebase, promote, migration, legacy"),
    limit: int = Query(100, ge=1, le=1000),
) -> Response:
    s: int | str | None = int(since) if since is not None and since.isdigit() else since
    items = hub_of(request).store.changesets(by=by, since=s, layer=layer, kind=kind, limit=limit)
    return json_response({"items": items})


@router.get("/changesets/{id}", response_model=M.ChangesetFull, responses=M.problems(404))
def get_changeset(request: Request, id: str) -> Response:
    """One changeset with the records it wrote."""
    return json_response(hub_of(request).store.changeset(id))


@router.post(
    "/changesets/{id}/revert",
    response_model=M.WriteResult,
    responses=M.problems(404, 409),
    summary="Undo a changeset",
    description="A revert changeset with If-Match on what the original produced: a later edit makes it a 409 "
    "whose conflicts carry the diff.",
)
def revert(request: Request, id: str) -> Response:
    hub = hub_of(request)
    w = writer_of(request)
    return json_response(write_result(hub.store.revert(id, by=w.by, client=w.client)))


__all__ = ["router", "write_result"]
