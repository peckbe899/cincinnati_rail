"""RFC 9457 problem responses (section 5: ``application/problem+json`` carrying ``code``, ``request_id`` and
``conflicts``).

Every error the server answers with goes through here:

- a ``region.core.errors.HubError`` keeps its own status and body (``to_problem``): 404, 412, 409, 422, 428, 502,
  503 and the rest;
- a request that fails FastAPI's validation (a body or query of the wrong shape) is a 422 ``invalid`` whose
  ``errors`` point into the request (``/body/ops/0/op``, ``/query/limit``);
- Starlette's own 404 and 405 (an unknown route, a wrong method) keep their status;
- anything else is a bug: a 500 ``internal`` that names only the request id (the traceback goes to the hub log).

``conflicts`` is always present (empty when the error has none), so a client can read it without checking.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from region.core.errors import HubError

from .http import ProblemJson

log = logging.getLogger("region.api")

TYPE_BASE = "https://cincinnati-rail.invalid/problems/"
_HTTP_CODES = {
    400: ("bad_request", "Bad request"),
    403: ("forbidden", "Forbidden"),
    404: ("not_found", "Not found"),
    405: ("method_not_allowed", "Method not allowed"),
    406: ("not_acceptable", "Not acceptable"),
    413: ("body_too_large", "Body too large"),
    415: ("unsupported_media_type", "Unsupported media type"),
    416: ("range_not_satisfiable", "Range not satisfiable"),
    500: ("internal", "Internal error"),
    503: ("unavailable", "Unavailable"),
}


def request_id_of(request: Request | None) -> str | None:
    if request is None:
        return None
    return getattr(request.state, "request_id", None) or request.scope.get("state", {}).get("request_id")


def body(status: int, code: str, title: str, detail: str, request_id: str | None, **extra: Any) -> dict[str, Any]:
    """A problem body with the members every problem carries."""
    out: dict[str, Any] = {
        "type": TYPE_BASE + code,
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "request_id": request_id,
        "conflicts": [],
    }
    out.update(extra)
    return out


def of_error(err: HubError, request_id: str | None) -> dict[str, Any]:
    """The body of a ``HubError``."""
    out = err.to_problem(request_id)
    out.setdefault("conflicts", [])
    return out


def response(status: int, code: str, detail: str, request_id: str | None = None, **extra: Any) -> ProblemJson:
    """A problem response for a status the server answers itself (400, 403, 413, 415, 500)."""
    title = _HTTP_CODES.get(status, (code, "Error"))[1]
    return ProblemJson(body(status, code, title, detail, request_id, **extra), status_code=status)


def error_response(err: HubError, request_id: str | None) -> ProblemJson:
    headers = {}
    if err.status == 503:
        headers["Retry-After"] = "5"
    return ProblemJson(of_error(err, request_id), status_code=err.status, headers=headers)


def _pointer(loc: Any) -> str:
    return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in loc)


def install(app: FastAPI) -> None:
    """Register the problem handlers on ``app``."""

    @app.exception_handler(HubError)
    async def _hub_error(request: Request, exc: HubError) -> ProblemJson:
        if exc.status >= 500:
            log.warning("%s %s: %s", request.method, request.url.path, exc.detail)
        return error_response(exc, request_id_of(request))

    @app.exception_handler(RequestValidationError)
    async def _invalid(request: Request, exc: RequestValidationError) -> ProblemJson:
        errors = [{"path": _pointer(e.get("loc", ())), "message": str(e.get("msg", ""))} for e in exc.errors()]
        detail = "the request is invalid: " + "; ".join(f"{e['path']}: {e['message']}" for e in errors[:5])
        out = body(422, "invalid", "Invalid data", detail, request_id_of(request), errors=errors)
        return ProblemJson(out, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> ProblemJson:
        code, title = _HTTP_CODES.get(exc.status_code, (f"http_{exc.status_code}", "Error"))
        detail = exc.detail if isinstance(exc.detail, str) else title
        if exc.status_code == 404:
            detail = f"no route {request.method} {request.url.path}"
        out = body(exc.status_code, code, title, detail, request_id_of(request))
        return ProblemJson(out, status_code=exc.status_code, headers=dict(exc.headers or {}))


__all__ = ["TYPE_BASE", "body", "error_response", "install", "of_error", "request_id_of", "response"]
