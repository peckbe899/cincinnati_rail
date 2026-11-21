"""Files: the mounted data tiers at ``/api/v1/data/{tier}/{path}`` and the app at ``/`` (section 5, section 9).

**Mounts.** A tier of ``configs/hub_paths.json`` with ``mount: true`` is served read-only. The path is contained by
``region.core.paths.contained`` (realpath plus commonpath against the tier's root, after ``check_relpath`` refuses
``..``, backslashes and leftover escapes such as ``%5c``, drive letters, UNC prefixes, ``:``, reserved names and
trailing dots and spaces). Every refusal, an unknown or unmounted tier, a missing file and a folder are the same 404,
which never says which it was. A tier whose root is absent answers 404 with its plain reason, as a status chip
shows it.

**Responses.** Every file has an ``ETag`` (size and modification time) answered by ``If-None-Match`` with 304, and
``Range`` requests get 206 (Starlette's ``FileResponse``). Compressible types (JSON, text, SVG, protobuf glyphs) are
gzipped by the app's ``GZipMiddleware`` when the client accepts it and asked for no range; webp, PMTiles and other
compressed or binary types never are (``http.NO_GZIP``).

**The app.** ``app/dist`` is served at its own paths: ``/`` and ``/w/...`` give ``index.html`` (no-cache), the
hashed files under ``/assets/`` are immutable, everything else (``/map/...``, icons) revalidates by ETag. ``.mjs`` is
``text/javascript`` (the MapLibre worker and the app's module workers need it) and ``.pbf`` is
``application/x-protobuf``. Without a build, ``/`` says how to build one.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from region.core import paths
from region.core.errors import NotFound

from .context import hub_of
from .http import etag_matches, media_type, not_modified

router = APIRouter(tags=["files"])
app_router = APIRouter(include_in_schema=False)

IMMUTABLE = "public, max-age=31536000, immutable"
REVALIDATE = "no-cache"

NOT_BUILT = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Cincinnati Rail hub</title></head>
<body><h1>The app is not built</h1>
<p>The hub is running, but <code>app/dist</code> does not exist. Run <code>crhub setup</code> (or
<code>npm run build -w app</code>), then reload this page.</p></body></html>
"""


class FileNotFound(NotFound):
    """A file that is not served: never says whether it is missing, outside the root, or refused by name."""

    code = "not_found"


def file_etag(path: Path) -> str:
    st = path.stat()
    return f'"{st.st_size:x}-{st.st_mtime_ns:x}"'


def file_response(request: Request, path: Path, *, cache_control: str = REVALIDATE) -> Response:
    """A file with ETag, 304 and Range; ``media_type`` by suffix."""
    try:
        st = path.stat()
    except OSError:
        raise FileNotFound("no such file") from None
    tag = f'"{st.st_size:x}-{st.st_mtime_ns:x}"'
    if etag_matches(request.headers.get("if-none-match"), tag):
        return not_modified(tag, cache_control=cache_control)
    return FileResponse(
        path,
        media_type=media_type(path),
        headers={"ETag": tag, "Cache-Control": cache_control},
        stat_result=st,
    )


def contained_file(root: Path, rel: str) -> Path:
    """The file ``rel`` under ``root``, contained; ``FileNotFound`` for anything else."""
    try:
        target = paths.contained(root, rel)
    except NotFound:
        raise FileNotFound("no such file") from None
    if not target.is_file():
        raise FileNotFound("no such file")
    return target


@router.head("/data/{tier}/{path:path}", include_in_schema=False)
@router.get(
    "/data/{tier}/{path:path}",
    response_class=Response,
    responses={200: {"description": "the file"}, 206: {"description": "the range asked for"}, 304: {}, 404: {}},
    summary="A file of a mounted data tier",
)
def data_file(request: Request, tier: str, path: str) -> Response:
    hub = hub_of(request)
    try:
        t = paths.tier(tier, hub.cfg)
    except NotFound:
        raise FileNotFound("no such file") from None
    if not t.mount:
        raise FileNotFound("no such file")
    ok = t.available()
    if ok is not True:
        raise NotFound(ok, tier=tier)
    return file_response(request, contained_file(t.root, path))


def _dist(request: Request) -> Path:
    return Path(hub_of(request).cfg.get("app_dist") or (paths.REPO / "app" / "dist"))


def _index(request: Request) -> Response:
    index = _dist(request) / "index.html"
    if not index.is_file():
        return HTMLResponse(NOT_BUILT, status_code=503, headers={"Cache-Control": "no-store"})
    return file_response(request, index, cache_control=REVALIDATE)


@app_router.api_route("/", methods=["GET", "HEAD"])
def app_root(request: Request) -> Response:
    return _index(request)


@app_router.api_route("/w/{rest:path}", methods=["GET", "HEAD"])
def app_workspace(request: Request, rest: str) -> Response:
    return _index(request)


@app_router.api_route("/{path:path}", methods=["GET", "HEAD"])
def app_file(request: Request, path: str) -> Response:
    if path == "api" or path.startswith("api/"):
        raise FileNotFound(f"no route {request.method} /{path}")
    target = contained_file(_dist(request), path)
    cache = IMMUTABLE if path.startswith("assets/") else REVALIDATE
    return file_response(request, target, cache_control=cache)


__all__ = ["FileNotFound", "app_router", "contained_file", "file_etag", "file_response", "router"]
