"""The server's security rules (section 9, Security), as one ASGI middleware in front of everything.

- **Host allowlist.** The server binds to 127.0.0.1 only, and a request whose ``Host`` is not ``localhost``,
  ``127.0.0.1`` or ``[::1]`` (any port) gets 400: a DNS-rebinding page cannot reach it under its own name.
- **Origin.** A request carrying an ``Origin`` that is not this server's own (``http://`` plus the ``Host`` it was
  sent to) gets 403, whatever its method. There is no CORS: no ``Access-Control-*`` header is ever sent.
- **Writes** (POST, PUT, PATCH, DELETE) need ``X-CR-Client`` (403 without it, 400 when it is not a short token) and
  a JSON content type (``application/json`` or ``application/*+json``; 415 otherwise). An HTML form can send
  neither, so a page elsewhere cannot write through Ben's browser.
- **Bodies** are capped (``body_cap_mb`` of the config, 32 MB): a larger ``Content-Length`` gets 413 before the body
  is read, and a body that grows past the cap while it streams is cut off with 413.
- **Headers on every response:** the CSP of section 9, ``X-Content-Type-Options: nosniff``, ``Referrer-Policy:
  same-origin``, ``Cross-Origin-Resource-Policy: same-origin`` (another site cannot embed the hub's files) and
  ``X-Request-ID``.
- **Request ids.** Each request gets a ``request_id`` (``X-Request-ID`` when the client sent a sane one), which every
  log line of the request carries (``region.core.log``) and every problem body names.
- **Paths** holding a control character once decoded (``%0a``, ``%00``) get 404 before routing.
- **Errors that escape the app** (bugs) become a 500 problem naming the request id; the traceback goes to the log.

Path containment for files (``..``, ``%5c``, drive letters, UNC, ``:``, reserved names, trailing dots and spaces)
is ``region.core.paths.contained``, applied by ``region.api.files`` per mount; kinds and ULIDs are checked by the
record routes. Each refusal is a 404 that does not say why.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from starlette.exceptions import HTTPException as StarletteHTTPException

from region.core.log import log_context, new_request_id

from . import problem

log = logging.getLogger("region.api")

CSP = "default-src 'self'; worker-src 'self' blob:; img-src 'self' blob: data:"
ALLOWED_HOSTS = ("localhost", "127.0.0.1", "[::1]")
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CLIENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,63}$")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_HOST_RE = re.compile(r"^(\[[0-9a-fA-F:.]+\]|[A-Za-z0-9.-]+)(?::(\d{1,5}))?$")

SECURITY_HEADERS = (
    (b"content-security-policy", CSP.encode()),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"same-origin"),
    (b"cross-origin-resource-policy", b"same-origin"),
)

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class BodyTooLarge(StarletteHTTPException):
    """A streamed request body grew past the cap. An HTTP 413, so FastAPI's body reader passes it on as it is."""

    def __init__(self, cap: int) -> None:
        super().__init__(413, f"the body is over the cap of {cap} bytes")


def host_name(host: str) -> str | None:
    """The host part of a ``Host`` header, lower case (``[::1]`` keeps its brackets), or ``None`` when malformed."""
    m = _HOST_RE.match(host.strip())
    if not m:
        return None
    return m.group(1).lower()


def host_allowed(host: str | None, allowed: tuple[str, ...] = ALLOWED_HOSTS) -> bool:
    if not host:
        return False
    name = host_name(host)
    return name is not None and name in allowed


def origin_allowed(origin: str, host: str, scheme: str = "http") -> bool:
    """Whether ``Origin`` is this server's own: the scheme and the exact ``Host`` the request was sent to."""
    return origin.strip().lower() == f"{scheme}://{host.strip()}".lower()


def is_json(content_type: str | None) -> bool:
    """``application/json`` or ``application/<x>+json`` (parameters such as ``charset`` allowed)."""
    if not content_type:
        return False
    main = content_type.split(";", 1)[0].strip().lower()
    kind, _, sub = main.partition("/")
    return kind == "application" and (sub == "json" or sub.endswith("+json"))


def _header(scope: Scope, name: bytes) -> str | None:
    for k, v in scope.get("headers") or []:
        if k.lower() == name:
            return v.decode("latin-1")
    return None


class Guard:
    """The security middleware (see the module doc). ``body_cap`` is in bytes."""

    def __init__(self, app: ASGIApp, *, body_cap: int, allowed_hosts: tuple[str, ...] = ALLOWED_HOSTS) -> None:
        self.app = app
        self.body_cap = int(body_cap)
        self.allowed_hosts = tuple(h.lower() for h in allowed_hosts)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return
        if scope["type"] != "http":  # the hub serves no websockets
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            return
        given = _header(scope, b"x-request-id")
        rid = given if given and _REQUEST_ID_RE.match(given) else new_request_id()
        scope.setdefault("state", {})["request_id"] = rid
        started = False

        async def send_with_headers(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = list(message.get("headers") or [])
                present = {k.lower() for k, _ in headers}
                for k, v in SECURITY_HEADERS:
                    if k not in present:
                        headers.append((k, v))
                headers.append((b"x-request-id", rid.encode()))
                message["headers"] = headers
            await send(message)

        async def refuse(status: int, code: str, detail: str) -> None:
            resp = problem.response(status, code, detail, rid)
            await resp(scope, receive, send_with_headers)

        path = scope.get("path") or ""
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in path):  # a decoded %0a would match a route's "$"
            await refuse(404, "not_found", "no such path")
            return
        host = _header(scope, b"host")
        if not host_allowed(host, self.allowed_hosts):
            await refuse(400, "bad_host", "this server answers only to localhost, 127.0.0.1 and [::1]")
            return
        origin = _header(scope, b"origin")
        if origin is not None and not origin_allowed(origin, host or "", scope.get("scheme", "http")):
            await refuse(403, "foreign_origin", "requests from another origin are refused")
            return
        method = scope.get("method", "GET").upper()
        if method in WRITE_METHODS:
            client = _header(scope, b"x-cr-client")
            if not client:
                await refuse(403, "client_required", "a write needs the X-CR-Client header")
                return
            if not CLIENT_RE.match(client):
                await refuse(400, "bad_client", "X-CR-Client is a short token (letters, digits, . _ : @ -)")
                return
            if not is_json(_header(scope, b"content-type")):
                await refuse(415, "json_required", "a write needs a JSON content type (application/json)")
                return
        length = _header(scope, b"content-length")
        if length is not None:
            try:
                n = int(length)
            except ValueError:
                await refuse(400, "bad_request", "Content-Length is not a number")
                return
            if n > self.body_cap:
                await refuse(413, "body_too_large", f"the body is over the cap of {self.body_cap} bytes")
                return
        seen = 0

        async def capped_receive() -> Message:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.body_cap:
                    raise BodyTooLarge(self.body_cap)
            return message

        try:
            with log_context(request_id=rid):
                await self.app(scope, capped_receive, send_with_headers)
        except BodyTooLarge:
            if not started:
                await refuse(413, "body_too_large", f"the body is over the cap of {self.body_cap} bytes")
        except Exception:
            log.exception("%s %s failed (request %s)", method, scope.get("path"), rid)
            if not started:
                await refuse(500, "internal", f"the hub failed on this request; its log names request {rid}")


__all__ = [
    "ALLOWED_HOSTS",
    "CLIENT_RE",
    "CSP",
    "Guard",
    "WRITE_METHODS",
    "host_allowed",
    "host_name",
    "is_json",
    "origin_allowed",
]
