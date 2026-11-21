"""A small HTTP client of a running hub, for commands that must write through the server while it holds the lock
(decision 9.28): ``crhub rec``, and any other command that should not open the database beside a serving hub.

    hub = running_hub()                    # a HubClient when a serve holds var's lock, else None
    rec = hub.request("GET", "/k/note/01K...", query={"layer": "try"})

Standard library only (``urllib``), so a command module can use it without importing third-party packages. Every
request carries ``X-CR-Client`` (``crhub-cli`` by default) and, for writes, a JSON content type; ``X-CR-By`` names
the writer when given. A problem answer is raised as the matching ``region.core.errors`` class, so callers handle
a remote 412 exactly as a local one.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from region.core import errors as E
from region.core import lock, paths

_BY_STATUS: dict[int, type[E.HubError]] = {
    404: E.NotFound,
    409: E.Conflict,
    412: E.PreconditionFailed,
    422: E.Invalid,
    428: E.PreconditionRequired,
    502: E.EngineError,
    503: E.EngineUnavailable,
}


class RemoteError(E.HubError):
    """A problem answer whose status has no class of its own (400, 403, 413, 415, 500)."""

    def __init__(self, status: int, detail: str, **extra: Any) -> None:
        super().__init__(detail, **extra)
        self.status = status


def error_of(status: int, body: Any) -> E.HubError:
    """The ``HubError`` a problem body stands for."""
    p = body if isinstance(body, dict) else {}
    detail = str(p.get("detail") or f"HTTP {status}")
    code = p.get("code")
    if status == 412:
        return E.PreconditionFailed(
            detail, current=p.get("current"), by=p.get("by"), diff=p.get("diff"), stale=p.get("stale"), code=code
        )
    if status == 409:
        return E.Conflict(detail, reason=p.get("reason") or "reference", conflicts=p.get("conflicts"), code=code)
    if status == 422:
        return E.Invalid(detail, errors=p.get("errors"), code=code)
    cls = _BY_STATUS.get(status)
    if cls is not None:
        return cls(detail, code=code)
    return RemoteError(status, detail, code=code or f"http_{status}")


class HubClient:
    """Requests to one hub at ``base`` (``http://127.0.0.1:8766``)."""

    def __init__(self, base: str, *, client: str = "crhub-cli", by: str | None = None, timeout: float = 60.0) -> None:
        self.base = base.rstrip("/")
        self.client = client
        self.by = by
        self.timeout = timeout

    def url(self, path: str, query: dict[str, Any] | None = None) -> str:
        q = {k: str(v) for k, v in (query or {}).items() if v is not None and v != ""}
        return f"{self.base}/api/v1{path}" + (("?" + urllib.parse.urlencode(q)) if q else "")

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        content_type: str = "application/json",
    ) -> tuple[int, dict[str, str], Any]:
        """``(status, headers, body)``; a problem answer raises its ``HubError``."""
        h = {"Accept": "application/json", "X-CR-Client": self.client, **(headers or {})}
        if self.by:
            h["X-CR-By"] = self.by
        data = None
        if method.upper() not in ("GET", "HEAD"):
            h["Content-Type"] = content_type
            data = json.dumps({} if json_body is None else json_body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.url(path, query), data=data, method=method.upper(), headers=h)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - loopback only
                raw = resp.read()
                return resp.status, dict(resp.headers.items()), _decode(raw, resp.headers.get("Content-Type"))
        except urllib.error.HTTPError as e:
            raw = e.read()
            raise error_of(e.code, _decode(raw, e.headers.get("Content-Type") if e.headers else None)) from None
        except urllib.error.URLError as e:
            detail = f"the hub at {self.base} did not answer ({e.reason})"
            raise RemoteError(503, detail, code="hub_unreachable") from None

    def json(self, method: str, path: str, **kw: Any) -> Any:
        return self.request(method, path, **kw)[2]


def _decode(raw: bytes, content_type: str | None) -> Any:
    if not raw:
        return None
    if content_type and "json" in content_type:
        return json.loads(raw.decode("utf-8"))
    return raw.decode("utf-8", "replace")


def running_hub(var: Path | None = None, **kw: Any) -> HubClient | None:
    """A client of the hub serving from ``var`` (by the holder of ``var/hub.lock``), or ``None`` when no serve holds
    it. A holder that serves nothing (``crhub jobs run``, port 0) gives ``None`` too; ``lock.reader`` names it."""
    holder = lock.reader(Path(var) if var is not None else paths.var_root())
    if holder is None or not holder.port or not holder.command.startswith("crhub serve"):
        return None
    return HubClient(f"http://127.0.0.1:{holder.port}", **kw)


__all__ = ["HubClient", "RemoteError", "error_of", "running_hub"]
