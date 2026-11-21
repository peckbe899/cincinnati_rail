"""Layer and review-queue routes: ``/layers`` (list; create a scenario or proposal), promote, tags, state and the
record diff of a layer, then ``/conflicts`` and their resolution (decisions 9.10, 9.11)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from . import models as M
from .changesets import write_result
from .context import hub_of, writer_of
from .http import json_response

router = APIRouter(tags=["layers"])


@router.get("/layers", response_model=M.LayerList, summary="Every layer")
def list_layers(request: Request) -> Response:
    return json_response({"items": hub_of(request).store.layers()})


@router.post("/layers", status_code=201, response_model=M.Layer, responses=M.problems(404, 409, 422))
def create_layer(request: Request, body: M.LayerIn) -> Response:
    """Create a scenario or proposal under ``parent`` (main by default)."""
    w = writer_of(request)
    lay = hub_of(request).store.create_layer(
        body.slug, tier=body.tier, parent=body.parent, title=body.title, note=body.note, by=w.by
    )
    return json_response(lay, 201, headers={"Location": f"/api/v1/layers/{lay['slug']}"})


@router.get("/layers/{slug}", response_model=M.Layer, responses=M.problems(404))
def get_layer(request: Request, slug: str) -> Response:
    return json_response(hub_of(request).store.layer(slug))


@router.post("/layers/{slug}/promote", response_model=M.WriteResult, responses=M.problems(404, 409, 422))
def promote(request: Request, slug: str, body: M.PromoteIn | None = None) -> Response:
    """Write the layer's revisions to its parent as one changeset; 409 lists every record changed there since."""
    w = writer_of(request)
    res = hub_of(request).store.promote(slug, by=w.by, message=(body.message if body else ""), client=w.client)
    return json_response(write_result(res))


@router.get("/layers/{slug}/tags", response_model=M.TagList, responses=M.problems(404))
def list_tags(request: Request, slug: str) -> Response:
    return json_response({"items": hub_of(request).store.tags(slug)})


@router.post("/layers/{slug}/tags", status_code=201, response_model=M.Tag, responses=M.problems(404, 409))
def tag(request: Request, slug: str, body: M.TagIn) -> Response:
    """Name the layer as it stands now (read back with ``tag=`` on any read)."""
    w = writer_of(request)
    return json_response(hub_of(request).store.tag(slug, body.name, by=w.by, note=body.note), 201)


@router.post("/layers/{slug}/state", response_model=M.Layer, responses=M.problems(404, 422))
def set_state(request: Request, slug: str, body: M.StateIn) -> Response:
    """Archive or reopen a scenario or proposal."""
    writer_of(request)
    return json_response(hub_of(request).store.set_layer_state(slug, body.state))


@router.get("/layers/{slug}/diff", response_model=M.LayerDiff, responses=M.problems(404))
def layer_diff(
    request: Request, slug: str, against: str | None = Query(None, description="default: the parent's view")
) -> Response:
    """What the layer's own revisions change, record by record."""
    return json_response({"items": hub_of(request).store.diff_layers(slug, against)})


@router.get("/conflicts", response_model=M.ConflictList, summary="The review queue")
def conflicts(
    request: Request,
    state: str = Query("open", description="open, resolved, dismissed, or all"),
    layer: str | None = None,
    import_run: int | None = None,
) -> Response:
    items = hub_of(request).store.conflicts(
        state=None if state == "all" else state, layer=layer, import_run=import_run
    )
    return json_response({"items": items})


@router.post("/conflicts/{id}/resolve", responses=M.problems(404, 409, 412, 422))
def resolve(request: Request, id: str, body: M.ResolveIn) -> Response:
    """Take ``ours``, ``theirs`` or a ``merged`` body."""
    w = writer_of(request)
    merged = body.body.model_dump(exclude_unset=True) if body.body is not None else None
    return json_response(hub_of(request).store.resolve_conflict(id, body.take, merged, by=w.by))


__all__ = ["router"]
