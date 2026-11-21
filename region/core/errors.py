"""The hub's shared errors, one class per outcome a caller must tell apart.

Every package raises these, never bare ``ValueError`` or ``KeyError``, for outcomes a user or a client can cause. The
server (WP2) maps each class to its HTTP status and an RFC 9457 problem body with ``to_problem()``; the CLI prints
``str(err)`` and exits with ``err.exit_code``.

    NotFound              404  unknown kind, record, layer, tier, file
    PreconditionRequired  428  a write without If-Match
    PreconditionFailed    412  a stale If-Match; carries the current record, its ``by`` and a diff
    Conflict              409  reference, namespace, authority, rebase and revert conflicts
    Invalid               422  data that fails its kind's schema or a validator
    EngineUnavailable     503  no Node, a dead sidecar, a timeout, an unknown contract major
    EngineError           502  the engine answered ``ok: false``

Bugs stay ordinary exceptions and surface as 500.
"""

from __future__ import annotations

from typing import Any, Literal

ConflictReason = Literal["reference", "namespace", "authority", "rebase", "revert", "exists", "layer", "seed"]


class HubError(Exception):
    """Base of every expected hub error.

    ``code`` is a stable machine-readable slug (it goes into the problem body and the client's toast). ``detail`` is
    one plain sentence for Ben. ``extra`` holds any further members of the problem body.
    """

    status: int = 500
    code: str = "error"
    title: str = "Hub error"
    exit_code: int = 1

    def __init__(self, detail: str = "", *, code: str | None = None, **extra: Any) -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title
        if code is not None:
            self.code = code
        self.extra: dict[str, Any] = extra

    def to_problem(self, request_id: str | None = None, instance: str | None = None) -> dict[str, Any]:
        """The RFC 9457 ``application/problem+json`` body for this error.

        Always carries ``type``, ``title``, ``status``, ``detail``, ``code`` and ``request_id``; subclasses add their
        own members (``conflicts``, ``current``, ``errors``).
        """
        body: dict[str, Any] = {
            "type": f"https://cincinnati-rail.invalid/problems/{self.code}",
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "code": self.code,
            "request_id": request_id,
        }
        if instance is not None:
            body["instance"] = instance
        body.update(self._members())
        for key, value in self.extra.items():
            body.setdefault(key, value)
        return body

    def _members(self) -> dict[str, Any]:
        return {}


class NotFound(HubError):
    """A kind, record, layer, tier, job, result or file that does not exist (404).

    A tombstoned record reads as NotFound unless the caller asks for history.
    """

    status = 404
    code = "not_found"
    title = "Not found"


class PreconditionRequired(HubError):
    """A write that names no If-Match (428). Every put, patch, delete and restore of an existing record needs one."""

    status = 428
    code = "precondition_required"
    title = "If-Match required"


class PreconditionFailed(HubError):
    """A write whose If-Match is stale (412).

    ``current`` is the record as it now resolves in the view (get() shape), ``by`` who wrote it, and ``diff`` the RFC
    6902 patch from the client's base to ``current`` when the store can compute it. For a changeset, ``stale`` lists
    every stale op as ``{"index", "kind", "id", "if_match", "etag"}``.
    """

    status = 412
    code = "precondition_failed"
    title = "Stale If-Match"

    def __init__(
        self,
        detail: str = "",
        *,
        current: dict[str, Any] | None = None,
        by: str | None = None,
        diff: list[dict[str, Any]] | None = None,
        stale: list[dict[str, Any]] | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(detail, **extra)
        self.current = current
        self.by = by
        self.diff = diff
        self.stale = stale or []

    def _members(self) -> dict[str, Any]:
        return {"current": self.current, "by": self.by, "diff": self.diff, "stale": self.stale}


class Conflict(HubError):
    """A write refused because of the state of other records (409).

    ``reason`` is one of ``reference`` (a restrict ref, a dangling ref), ``namespace`` (an import layer writing outside
    its namespace), ``authority`` (legacy owns the kind), ``rebase`` and ``revert`` (a later edit stands in the way),
    ``exists`` (a create whose id, layer slug or tag name is taken), ``layer`` (the layer is not open: frozen,
    promoted or archived) and ``seed`` (export refused while seed changes are unmerged). ``conflicts`` lists the
    particulars, one dict per record (or layer, or tag), each with at least ``kind`` and ``id``.
    """

    status = 409
    code = "conflict"
    title = "Conflict"

    def __init__(
        self,
        detail: str = "",
        *,
        reason: ConflictReason | str = "reference",
        conflicts: list[dict[str, Any]] | None = None,
        **extra: Any,
    ) -> None:
        code = extra.pop("code", None) or f"conflict_{reason}"
        super().__init__(detail, code=code, **extra)
        self.reason = reason
        self.conflicts = conflicts or []

    def _members(self) -> dict[str, Any]:
        return {"reason": self.reason, "conflicts": self.conflicts}


class Invalid(HubError):
    """Data that fails validation (422).

    ``errors`` lists each failure as ``{"path": "/data/pvi/3/z_m", "message": "...", "rule": optional}``, where path
    is a JSON pointer into the record (get() shape) or into the request body.
    """

    status = 422
    code = "invalid"
    title = "Invalid data"
    exit_code = 2

    def __init__(self, detail: str = "", *, errors: list[dict[str, Any]] | None = None, **extra: Any) -> None:
        super().__init__(detail, **extra)
        self.errors = errors or []

    def _members(self) -> dict[str, Any]:
        return {"errors": self.errors}


class EngineUnavailable(HubError):
    """The engine cannot be reached (503): Node missing or too old, a sidecar that died or timed out, or a hello whose
    contract majors Python does not know. ``reason`` is one of ``no_node``, ``node_version``, ``crashed``, ``timeout``,
    ``contract``, ``closed``. ``stderr_tail`` is the last lines the process wrote to stderr: it goes into the job log
    and the hub log, never into the problem body."""

    status = 503
    code = "engine_unavailable"
    title = "Engine unavailable"

    def __init__(self, detail: str = "", *, reason: str = "crashed", stderr_tail: str = "", **extra: Any) -> None:
        super().__init__(detail, **extra)
        self.reason = reason
        self.stderr_tail = stderr_tail

    def _members(self) -> dict[str, Any]:
        return {"reason": self.reason}


class EngineError(HubError):
    """The engine answered ``{"ok": false}`` (502). ``engine_code`` is the engine's own code (``invalid_input``,
    ``unknown_method``, ``internal``); ``stack`` is the engine's stack trace and ``stderr_tail`` the last lines its
    process wrote to stderr, both logged but never shown to Ben. ``issues`` is the list zod reported for an
    ``invalid_input`` reply (``None`` when the engine sent none); it goes into the job log, not the problem body."""

    status = 502
    code = "engine_error"
    title = "Engine error"

    def __init__(
        self,
        detail: str = "",
        *,
        engine_code: str = "internal",
        stack: str = "",
        stderr_tail: str = "",
        issues: list[Any] | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(detail, **extra)
        self.engine_code = engine_code
        self.stack = stack
        self.stderr_tail = stderr_tail
        self.issues = issues

    def _members(self) -> dict[str, Any]:
        return {"engine_code": self.engine_code}


__all__ = [
    "ConflictReason",
    "HubError",
    "NotFound",
    "PreconditionRequired",
    "PreconditionFailed",
    "Conflict",
    "Invalid",
    "EngineUnavailable",
    "EngineError",
]
