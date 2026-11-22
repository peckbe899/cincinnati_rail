"""Small HTTP helpers shared by the routes: JSON bodies, ETag matching, byte ranges and media types.

- ``json_response`` writes JSON with ``ensure_ascii=False`` and ``allow_nan=False`` (the store and the cache never
  hold NaN, so one reaching a response is a bug and surfaces as a 500), turning dates and paths into text.
- ``etag_matches`` reads ``If-None-Match`` and ``If-Match`` lists (``"a", W/"b"``, ``*``) the way RFC 9110 compares
  for a GET: weakly.
- ``byte_range`` parses one ``Range: bytes=`` range; ``bytes_response`` serves an in-memory body with ranges
  (result arrays).
- ``media_type`` names the types the app and the data tiers need, beyond what ``mimetypes`` knows on every
  platform (Windows reads its registry, so ``.js`` can come back as ``text/plain`` there).
"""

from __future__ import annotations

import datetime as dt
import json
import mimetypes
import re
from pathlib import Path, PurePath
from typing import Any

from starlette.responses import JSONResponse, Response

PROBLEM_JSON = "application/problem+json"

MEDIA_TYPES = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".html": "text/html",
    ".json": "application/json",
    ".geojson": "application/geo+json",
    ".map": "application/json",
    ".webmanifest": "application/manifest+json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pbf": "application/x-protobuf",
    ".pmtiles": "application/vnd.pmtiles",
    ".wasm": "application/wasm",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".xml": "application/xml",
    ".vrt": "application/xml",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".glb": "model/gltf-binary",
    ".gltf": "model/gltf+json",
    ".bin": "application/octet-stream",
}

# Types never gzipped: already compressed, or binary that gains little (section 9: not webp or pmtiles).
NO_GZIP = (
    "application/gzip",
    "application/x-gzip",
    "application/zip",
    "application/vnd.pmtiles",
    "application/octet-stream",
    "application/wasm",
    "application/grpc",
    "audio/*",
    "video/*",
    "font/woff",
    "font/woff2",
    "image/avif",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
    "model/gltf-binary",
    "text/event-stream",
)


def media_type(path: str | PurePath) -> str:
    """The media type of a file by its suffix (``application/octet-stream`` when unknown)."""
    suffix = PurePath(path).suffix.lower()
    found = MEDIA_TYPES.get(suffix)
    if found:
        return found
    guess, _ = mimetypes.guess_type(str(path), strict=False)
    return guess or "application/octet-stream"


def _default(value: Any) -> Any:
    if isinstance(value, (dt.date, dt.datetime, dt.time)):
        return value.isoformat()
    if isinstance(value, (Path, PurePath)):
        return value.as_posix()
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if hasattr(value, "__dataclass_fields__"):
        import dataclasses

        return dataclasses.asdict(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def dumps(value: Any) -> bytes:
    """The JSON bytes of a response body."""
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), default=_default).encode(
        "utf-8"
    )


class Json(JSONResponse):
    """A JSON response written by ``dumps``."""

    def render(self, content: Any) -> bytes:
        return dumps(content)


class ProblemJson(Json):
    """An RFC 9457 problem response."""

    media_type = PROBLEM_JSON


def json_response(
    value: Any, status: int = 200, *, headers: dict[str, str] | None = None, etag: str | None = None
) -> Json:
    """``value`` as JSON; ``etag`` (quotes included) goes into the ``ETag`` header."""
    h = dict(headers or {})
    if etag is not None:
        h["ETag"] = etag
    return Json(value, status_code=status, headers=h)


def not_modified(etag: str, *, cache_control: str | None = None) -> Response:
    """A 304 carrying the ETag (and the cache policy, as RFC 9111 asks)."""
    h = {"ETag": etag}
    if cache_control:
        h["Cache-Control"] = cache_control
    return Response(status_code=304, headers=h)


def _tags(header: str) -> list[str]:
    out = []
    for part in re.findall(r'\s*(W/)?("[^"]*"|\*)\s*(?:,|$)', header):
        out.append(part[1])
    return out


def etag_matches(header: str | None, etag: str) -> bool:
    """Whether an ``If-None-Match`` value names ``etag`` (weak comparison; ``*`` matches anything)."""
    if not header:
        return False
    target = etag[2:] if etag.startswith("W/") else etag
    for tag in _tags(header):
        if tag == "*" or tag == target:
            return True
    return False


class RangeNotSatisfiable(Exception):
    """A ``Range`` that lies past the end of the body."""


def range_problem(size: int, headers: dict[str, str] | None = None, request_id: str | None = None) -> Response:
    """The 416 answer as RFC 9457 ``problem+json`` (like every other error), with ``Content-Range: bytes */size``.
    The request id is also in ``X-Request-ID``, which the security middleware adds."""
    from . import problem

    resp = problem.response(
        416, "range_not_satisfiable", f"the range asked for lies past the end of the body ({size} bytes)", request_id
    )
    for k, v in (headers or {}).items():
        if k.lower() not in ("content-type", "content-length"):
            resp.headers[k] = v
    resp.headers["Content-Range"] = f"bytes */{size}"
    return resp


def byte_range(header: str | None, size: int) -> tuple[int, int] | None:
    """The one range ``(start, end_exclusive)`` a ``Range: bytes=`` header asks for, or ``None`` for the whole body.

    A malformed header, another unit or several ranges give ``None`` (the whole body, as RFC 9110 allows); a range
    that starts past the end raises ``RangeNotSatisfiable``."""
    if not header:
        return None
    unit, _, spec = header.partition("=")
    if unit.strip().lower() != "bytes" or "," in spec:
        return None
    first, dash, last = spec.strip().partition("-")
    if not dash:
        return None
    try:
        if first == "":
            n = int(last)
            if n <= 0:
                raise RangeNotSatisfiable
            return max(0, size - n), size
        start = int(first)
        end = int(last) + 1 if last else size
    except ValueError:
        return None
    if start < 0 or (last and end <= start):
        return None
    if start >= size:
        raise RangeNotSatisfiable
    return start, min(end, size)


def bytes_response(
    request_headers: Any,
    body: bytes,
    *,
    media_type: str,
    etag: str,
    headers: dict[str, str] | None = None,
    cache_control: str | None = None,
) -> Response:
    """An in-memory body with ``ETag``, ``If-None-Match`` (304) and one ``Range`` (206, or 416)."""
    h = {"ETag": etag, "Accept-Ranges": "bytes", **(headers or {})}
    if cache_control:
        h["Cache-Control"] = cache_control
    if etag_matches(request_headers.get("if-none-match"), etag):
        return not_modified(etag, cache_control=cache_control)
    rng_header = request_headers.get("range")
    if_range = request_headers.get("if-range")
    if rng_header and if_range and if_range.strip() != etag:
        rng_header = None
    try:
        rng = byte_range(rng_header, len(body))
    except RangeNotSatisfiable:
        return range_problem(len(body), h)
    if rng is None:
        return Response(body, media_type=media_type, headers=h)
    start, end = rng
    h["Content-Range"] = f"bytes {start}-{end - 1}/{len(body)}"
    return Response(body[start:end], status_code=206, media_type=media_type, headers=h)


__all__ = [
    "Json",
    "MEDIA_TYPES",
    "NO_GZIP",
    "PROBLEM_JSON",
    "ProblemJson",
    "RangeNotSatisfiable",
    "byte_range",
    "bytes_response",
    "dumps",
    "etag_matches",
    "json_response",
    "media_type",
    "not_modified",
    "range_problem",
]
