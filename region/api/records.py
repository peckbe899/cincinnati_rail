"""Record routes (section 5): ``/k/{kind}`` lists and creates, ``/k/{kind}/{id}`` reads, replaces, patches and
deletes, plus history, diff, restore, reverse refs and legacy keys.

Decision 9.13 as served here:

- **PUT** replaces the whole body (``{data, geom}``) and needs ``If-Match`` (428 without it, 412 when stale, with
  the current record, its ``by`` and a diff).
- **PATCH** is RFC 6902 JSON Patch only, sent as ``application/json-patch+json`` (415 for any other type), with
  ``If-Match``. Nulls in the data are kept.
- **DELETE** writes a tombstone and needs ``If-Match``. **POST** creates; ``Idempotency-Key`` makes a retry safe.
- **ETags.** A record's is ``"<layer>:<version>"``; a list's is ``"seq:<N>"``, the newest outbox seq when the read
  began, so a write anywhere changes it. Both answer ``If-None-Match`` with 304.

A path's kind must be a known kind and its id a ULID; anything else is a 404. Every read takes the view (``layer``,
``year``, ``month``, ``tl``); a write goes to ``layer``.

Lists also serve GeoJSON (``format=geojson``), in EPSG:26916 or, with ``crs=4326``, in longitude and latitude, each
feature carrying ``id``, ``kind``, ``layer``, ``version``, ``name``, ``system``, ``parent`` and the month intervals
``open_lo``, ``open_hi``, ``close_lo``, ``close_hi`` for the app's era filter (null when undated). With ``crs=4326``
a ``bbox`` is in longitude and latitude too.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, Header, Path, Query, Request
from fastapi.responses import Response

from region.core import ids
from region.core.errors import HubError, Invalid, NotFound, PreconditionRequired
from region.core.protocols import Op
from region.core.protocols import etag as record_etag
from region.core.view import View

from . import models as M
from .context import KIND_RE, fingerprint, hub_of, view_of, writer_of
from .http import etag_matches, json_response, not_modified

router = APIRouter(tags=["records"])

ViewDep = Annotated[View, Depends(view_of)]

MAX_LIMIT = 10000


class UnsupportedMediaType(HubError):
    status = 415
    code = "unsupported_media_type"
    title = "Unsupported media type"


def check_kind(request: Request, kind: str) -> Any:
    """The kind of a path (``NotFound`` for a malformed or unknown name)."""
    if not KIND_RE.match(kind):
        raise NotFound(f"unknown kind {kind!r}", kind=kind)
    return hub_of(request).store.kinds[kind]


def check_id(id: str) -> str:
    if not ids.is_ulid(id):
        raise NotFound(f"no record {id!r} (record ids are ULIDs)", id=id)
    return id


def json_patch_type(request: Request) -> None:
    """A dependency: PATCH bodies are ``application/json-patch+json`` (checked before the body is validated)."""
    ctype = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if ctype != "application/json-patch+json":
        raise UnsupportedMediaType("PATCH takes RFC 6902 JSON Patch as application/json-patch+json", code="json_patch")


def _require_if_match(value: str | None, what: str) -> str:
    if not value:
        raise PreconditionRequired(f"{what} needs If-Match (the record's ETag)")
    return value


def _record_response(rec: dict[str, Any], status: int = 200, headers: dict[str, str] | None = None) -> Response:
    return json_response(rec, status, etag=record_etag(rec["layer"], rec["version"]), headers=headers)


def _body(b: M.Body) -> dict[str, Any]:
    raw = b.model_dump(exclude_unset=True)
    out: dict[str, Any] = {"data": raw["data"], "geom": raw.get("geom")}
    for k in ("kv", "source"):
        if raw.get(k) is not None:
            out[k] = raw[k]
    return out


# ------------------------------------------------------------------------------------------------- coordinates


@lru_cache(maxsize=2)
def _transformer(src: int, dst: int) -> Any:
    from pyproj import Transformer

    return Transformer.from_crs(src, dst, always_xy=True)


def _bbox(text: str | None, crs: str) -> tuple[float, float, float, float] | None:
    if text is None or text == "":
        return None
    try:
        x0, y0, x1, y1 = (float(v) for v in text.split(","))
    except ValueError:
        raise Invalid("bbox is x0,y0,x1,y1", errors=[{"path": "/query/bbox", "message": "four numbers"}]) from None
    if crs == "4326":
        tf = _transformer(4326, 26916)
        xs, ys = tf.transform([x0, x1, x0, x1], [y0, y0, y1, y1])
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def _geometry(wkt: str | None, crs: str) -> dict[str, Any] | None:
    if wkt is None:
        return None
    import numpy as np
    import shapely
    from shapely.geometry import mapping

    g = shapely.from_wkt(wkt)
    if crs == "4326":
        tf = _transformer(26916, 4326)

        def fn(xy: Any) -> Any:
            lon, lat = tf.transform(xy[:, 0], xy[:, 1])
            return np.round(np.column_stack([lon, lat]), 7)

        g = shapely.transform(g, fn)
    return dict(mapping(g))


def _fields(text: str | None) -> list[str] | None:
    if not text:
        return None
    return [f for f in (p.strip() for p in text.split(",")) if f]


def _project(rec: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    if fields is None or not isinstance(rec.get("data"), dict):
        return rec
    out = dict(rec)
    out["data"] = {f: rec["data"][f] for f in fields if f in rec["data"]}
    return out


def _feature(kind: Any, rec: dict[str, Any], crs: str, fields: list[str] | None) -> dict[str, Any]:
    data = rec.get("data") or {}
    cols = kind.columns_of(data)
    try:
        opened, closed = kind.dates_of(data)
    except Invalid:
        opened = closed = None
    props: dict[str, Any] = {
        "id": rec["id"],
        "kind": rec["kind"],
        "layer": rec["layer"],
        "version": rec["version"],
        "name": cols.get("name") if cols.get("name") is not None else data.get("name"),
        "system": cols.get("system") if cols.get("system") is not None else data.get("system"),
        "parent": cols.get("parent"),
        "phase": cols.get("phase"),
        "open_lo": opened[0] if opened else None,
        "open_hi": opened[1] if opened else None,
        "close_lo": closed[0] if closed else None,
        "close_hi": closed[1] if closed else None,
    }
    for f in fields or ():
        if f in data and f not in props:
            props[f] = data[f]
    return {"type": "Feature", "id": rec["id"], "geometry": _geometry(rec.get("geom"), crs), "properties": props}


# ------------------------------------------------------------------------------------------------------- reads


@router.get(
    "/k/{kind}",
    response_model=M.RecordPage,
    responses=M.problems(404, 422),
    summary="List records of a kind",
    description="Records of the kind resolved in the view and open at its instant, ordered by id. ETag "
    '"seq:N"; format=geojson gives a FeatureCollection (crs=4326 for longitude and latitude).',
)
def list_records(
    request: Request,
    kind: str,
    view: ViewDep,
    bbox: str | None = Query(None, description="x0,y0,x1,y1 in EPSG:26916 (longitude and latitude with crs=4326)"),
    parent: str | None = Query(None, description="the promoted parent column"),
    ref: str | None = Query(None, description="records that reference this id"),
    ids_: str | None = Query(None, alias="ids", description="comma-separated ids"),
    q: str | None = Query(None, description="search names"),
    fields: str | None = Query(None, description="comma-separated data members to keep"),
    limit: int = Query(500, ge=1, le=MAX_LIMIT),
    after: str | None = Query(None, description="the next value of the previous page"),
    format: Literal["json", "geojson"] = "json",
    crs: Literal["26916", "4326"] = "26916",
    tag: str | None = Query(None, description="read the layer as of one of its tags"),
) -> Response:
    hub = hub_of(request)
    k = check_kind(request, kind)
    tag_ = f'"seq:{hub.store.last_seq()}"'
    if etag_matches(request.headers.get("if-none-match"), tag_):
        return not_modified(tag_)
    kw: dict[str, Any] = {
        "bbox": _bbox(bbox, crs),
        "parent": parent,
        "ref": ref,
        "ids": [i for i in ids_.split(",") if i] if ids_ else None,
        "q": q,
        "limit": limit,
        "after": after,
    }
    if tag:
        kw["tag"] = tag
    items, nxt = hub.store.list(kind, view, **kw)
    keep = _fields(fields)
    if format == "geojson":
        body: dict[str, Any] = {
            "type": "FeatureCollection",
            "features": [_feature(k, r, crs, keep) for r in items],
            "next": nxt,
        }
        return json_response(body, etag=tag_, headers={"Content-Type": "application/geo+json"})
    return json_response({"items": [_project(r, keep) for r in items], "next": nxt}, etag=tag_)


@router.get(
    "/k/{kind}/{id}",
    response_model=M.Record,
    responses=M.problems(404),
    summary="One record",
    description='The record as it resolves in the view (at=version reads a past version). ETag "layer:version".',
)
def get_record(
    request: Request,
    kind: str,
    id: str,
    view: ViewDep,
    at: int | None = Query(None, ge=1, description="a past version of the revision"),
    tag: str | None = Query(None, description="read the layer as of one of its tags"),
) -> Response:
    hub = hub_of(request)
    check_kind(request, kind)
    check_id(id)
    kw: dict[str, Any] = {"at": at}
    if tag:
        kw["tag"] = tag
    rec = hub.store.get(kind, id, view, **kw)
    tag_ = record_etag(rec["layer"], rec["version"])
    if etag_matches(request.headers.get("if-none-match"), tag_):
        return not_modified(tag_)
    return json_response(rec, etag=tag_)


@router.get("/k/{kind}/{id}/history", response_model=M.History, responses=M.problems(404), summary="History")
def history(request: Request, kind: str, id: str, view: ViewDep) -> Response:
    """Every revision of the record on the view's layer and below, newest first."""
    check_kind(request, kind)
    check_id(id)
    return json_response({"items": hub_of(request).store.history(kind, id, view)})


@router.get("/k/{kind}/{id}/history/{version}", response_model=M.Record, responses=M.problems(404))
def history_version(
    request: Request, kind: str, id: str, view: ViewDep, version: int = Path(ge=1)
) -> Response:
    """One past version of the record's revision."""
    check_kind(request, kind)
    check_id(id)
    return _record_response(hub_of(request).store.get(kind, id, view, at=version))


@router.get("/k/{kind}/{id}/diff", response_model=M.Diff, responses=M.problems(404))
def diff(
    request: Request,
    kind: str,
    id: str,
    view: ViewDep,
    from_: int = Query(alias="from", ge=1),
    to: int = Query(ge=1),
) -> Response:
    """The RFC 6902 patch from one version of the record's body to another."""
    check_kind(request, kind)
    check_id(id)
    return json_response({"items": hub_of(request).store.diff(kind, id, view, from_, to)})


@router.get("/refs/{id}", response_model=M.RefList, summary="What references a record")
def refs(request: Request, id: str, view: ViewDep) -> Response:
    check_id(id)
    return json_response({"items": hub_of(request).store.refs_to(id, view)})


@router.get("/legacy/{lkind}/{key:path}", response_model=M.LegacyHit, responses=M.problems(404))
def legacy(request: Request, lkind: str, key: str) -> Response:
    """The record an old key maps to (``Line_8|Cincinnati State#2``)."""
    hit = hub_of(request).store.legacy_record(lkind, key)
    if hit is None:
        raise NotFound(f"no record for {lkind} {key!r}", lkind=lkind, key=key)
    return json_response(hit)


# ------------------------------------------------------------------------------------------------------ writes


@router.post(
    "/k/{kind}",
    status_code=201,
    response_model=M.Record,
    responses=M.problems(404, 409, 422),
    summary="Create a record",
    description="Idempotency-Key makes a retry return the first answer instead of a second record.",
)
def create_record(
    request: Request,
    kind: str,
    body: M.CreateBody,
    view: ViewDep,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=255),
) -> Response:
    hub = hub_of(request)
    w = writer_of(request)
    check_kind(request, kind)
    rid = body.id
    if rid is not None and not ids.is_ulid(rid):
        raise Invalid(f"{rid!r} is not a ULID", errors=[{"path": "/body/id", "message": "a ULID"}])
    op_body = _body(body)

    def do() -> dict[str, Any]:
        res = hub.store.write(
            [Op("create", kind, rid, None, body=op_body)], view, by=w.by, message=f"create {kind}", client=w.client
        )
        return res.records[0]

    replayed = False
    if idempotency_key:
        fp = fingerprint("create", kind, view.token(), rid, op_body)
        replayed, rec = hub.idempotency.run(w.client or "", idempotency_key, fp, do)
    else:
        rec = do()
    headers = {"Location": f"/api/v1/k/{kind}/{rec['id']}?layer={rec['layer']}"}
    if replayed:
        headers["Idempotent-Replayed"] = "true"
    return _record_response(rec, 201, headers)


@router.put(
    "/k/{kind}/{id}",
    response_model=M.Record,
    responses=M.problems(404, 409, 412, 422, 428),
    summary="Replace a record",
)
def put_record(
    request: Request,
    kind: str,
    id: str,
    body: M.Body,
    view: ViewDep,
    if_match: str | None = Header(None, alias="If-Match"),
) -> Response:
    hub = hub_of(request)
    w = writer_of(request)
    check_kind(request, kind)
    check_id(id)
    tag = _require_if_match(if_match, f"PUT of {kind} {id}")
    rec = {"kind": kind, "id": id, **_body(body)}
    return _record_response(hub.store.put(rec, view, if_match=tag, by=w.by, client=w.client))


@router.patch(
    "/k/{kind}/{id}",
    response_model=M.Record,
    responses=M.problems(404, 409, 412, 415, 422, 428),
    summary="Patch a record (RFC 6902)",
)
def patch_record(
    request: Request,
    kind: str,
    id: str,
    _type: Annotated[None, Depends(json_patch_type)],
    ops: Annotated[list[M.PatchOp], Body(media_type="application/json-patch+json")],
    view: ViewDep,
    if_match: str | None = Header(None, alias="If-Match"),
) -> Response:
    hub = hub_of(request)
    w = writer_of(request)
    check_kind(request, kind)
    check_id(id)
    tag = _require_if_match(if_match, f"PATCH of {kind} {id}")
    patch = [o.raw() for o in ops]
    return _record_response(hub.store.patch(kind, id, patch, view, if_match=tag, by=w.by, client=w.client))


@router.delete(
    "/k/{kind}/{id}",
    response_model=M.Record,
    responses=M.problems(404, 409, 412, 428),
    summary="Delete a record (a tombstone)",
)
def delete_record(
    request: Request,
    kind: str,
    id: str,
    view: ViewDep,
    if_match: str | None = Header(None, alias="If-Match"),
) -> Response:
    hub = hub_of(request)
    w = writer_of(request)
    check_kind(request, kind)
    check_id(id)
    tag = _require_if_match(if_match, f"DELETE of {kind} {id}")
    return _record_response(hub.store.delete(kind, id, view, if_match=tag, by=w.by, client=w.client))


@router.post(
    "/k/{kind}/{id}/restore",
    response_model=M.Record,
    responses=M.problems(404, 409, 412, 428),
    summary="Restore a past version as a new version",
)
def restore(
    request: Request,
    kind: str,
    id: str,
    view: ViewDep,
    version: int = Query(ge=1),
    if_match: str | None = Header(None, alias="If-Match"),
) -> Response:
    hub = hub_of(request)
    w = writer_of(request)
    check_kind(request, kind)
    check_id(id)
    tag = _require_if_match(if_match, f"restore of {kind} {id}")
    return _record_response(hub.store.restore(kind, id, version, view, if_match=tag, by=w.by, client=w.client))


__all__ = ["UnsupportedMediaType", "check_id", "check_kind", "router"]
