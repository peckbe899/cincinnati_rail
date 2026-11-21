"""Logging: JSON lines in ``var/logs/hub-YYYY-MM-DD.jsonl``, kept 30 days, with ``request_id`` and ``job_id``.

Call ``setup()`` once per process (the server, a CLI command, a worker). Then log with the standard library:

    log = logging.getLogger("region.api")
    with log_context(request_id=new_request_id()):
        log.info("record written", extra={"kind": "profile", "id": rid})

Every line is one JSON object: ``at`` (local time with its UTC offset), ``level``, ``logger``, ``msg``, the
``request_id`` and ``job_id`` of the current context (``None`` outside one), ``exc`` for an exception, and any
``extra`` members. The file is chosen by the local date of each line, so a long-running server rolls over at
midnight; files older than ``keep_days`` are deleted at setup and on rollover. Browser errors reach the same file
through ``/client-log`` (``client_log``).
"""

from __future__ import annotations

import contextlib
import contextvars
import datetime as dt
import json
import logging
import secrets
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

REQUEST_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
JOB_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar("job_id", default=None)

PREFIX = "hub-"
SUFFIX = ".jsonl"
KEEP_DAYS = 30

# LogRecord attributes that are not "extra" members
_STANDARD = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime", "taskName"}


def new_request_id() -> str:
    """A short random id for one request or one CLI run (12 hex characters)."""
    return secrets.token_hex(6)


@contextlib.contextmanager
def log_context(*, request_id: str | None = None, job_id: str | None = None) -> Iterator[None]:
    """Set ``request_id`` and/or ``job_id`` for every log line written in the block (thread and task local)."""
    tokens = []
    if request_id is not None:
        tokens.append((REQUEST_ID, REQUEST_ID.set(request_id)))
    if job_id is not None:
        tokens.append((JOB_ID, JOB_ID.set(job_id)))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


def current_request_id() -> str | None:
    """The request id of the current context, or ``None``."""
    return REQUEST_ID.get()


def current_job_id() -> str | None:
    """The job id of the current context, or ``None``."""
    return JOB_ID.get()


def log_file(folder: Path, day: dt.date) -> Path:
    """``<folder>/hub-YYYY-MM-DD.jsonl``."""
    return Path(folder) / f"{PREFIX}{day.isoformat()}{SUFFIX}"


def prune(folder: Path, keep_days: int = KEEP_DAYS, today: dt.date | None = None) -> list[Path]:
    """Delete log files older than ``keep_days``; return those deleted. A file in use is left for next time."""
    today = today or dt.date.today()
    cutoff = today - dt.timedelta(days=keep_days)
    removed = []
    for p in Path(folder).glob(f"{PREFIX}*{SUFFIX}"):
        try:
            day = dt.date.fromisoformat(p.name[len(PREFIX) : -len(SUFFIX)])
        except ValueError:
            continue
        if day < cutoff:
            try:
                p.unlink()
                removed.append(p)
            except OSError:
                pass
    return removed


class JsonlHandler(logging.Handler):
    """A handler appending one JSON object per line to the day's file in ``folder``."""

    def __init__(self, folder: Path, *, keep_days: int = KEEP_DAYS, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self.folder = Path(folder)
        self.keep_days = keep_days
        self._day: dt.date | None = None
        self._stream: TextIO | None = None

    def _open(self, day: dt.date) -> TextIO:
        if self._stream is not None and self._day == day:
            return self._stream
        if self._stream is not None:
            self._stream.close()
        self.folder.mkdir(parents=True, exist_ok=True)
        # newline="\n": LF on Windows too
        self._stream = open(log_file(self.folder, day), "a", encoding="utf-8", newline="\n")
        self._day = day
        prune(self.folder, self.keep_days, day)
        return self._stream

    def format_line(self, record: logging.LogRecord) -> str:
        """The JSON line for one log record (without the newline)."""
        at = dt.datetime.fromtimestamp(record.created).astimezone()
        line: dict[str, Any] = {
            "at": at.isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or REQUEST_ID.get(),
            "job_id": getattr(record, "job_id", None) or JOB_ID.get(),
        }
        if record.exc_info:
            line["exc"] = logging.Formatter().formatException(record.exc_info)
        for key, value in vars(record).items():
            if key not in _STANDARD and key not in line:
                line[key] = value
        return json.dumps(line, ensure_ascii=False, default=str)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = self.format_line(record)
            stream = self._open(dt.date.fromtimestamp(record.created))
            stream.write(text + "\n")
            stream.flush()
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        self.acquire()
        try:
            if self._stream is not None:
                self._stream.close()
                self._stream = None
        finally:
            self.release()
        super().close()


_handler: JsonlHandler | None = None


def setup(
    folder: Path | None = None,
    *,
    level: int | str = logging.INFO,
    keep_days: int = KEEP_DAYS,
    stderr: bool = True,
) -> JsonlHandler:
    """Send the ``region`` loggers to ``folder`` (default ``var/logs``) as JSON lines, and to stderr as plain text.

    Idempotent: a second call replaces the first handler. The folder must be inside the write roots
    (``fsio.check_write``).
    """
    global _handler
    from . import fsio, paths

    folder = Path(folder) if folder is not None else paths.var_path("logs")
    fsio.check_write(folder / "probe")
    logger = logging.getLogger("region")
    logger.setLevel(level)
    if _handler is not None:
        logger.removeHandler(_handler)
        _handler.close()
    _handler = JsonlHandler(folder, keep_days=keep_days)
    logger.addHandler(_handler)
    if stderr and not any(getattr(h, "_cr_stderr", False) for h in logger.handlers):
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        h._cr_stderr = True  # type: ignore[attr-defined]
        h.setLevel(logging.WARNING)
        logger.addHandler(h)
    prune(folder, keep_days)
    return _handler


def get_logger(name: str) -> logging.Logger:
    """``logging.getLogger("region.<name>")``."""
    return logging.getLogger(name if name.startswith("region") else f"region.{name}")


def client_log(entry: dict[str, Any]) -> None:
    """Write one browser log entry (``/client-log``) to the hub log, under the logger ``region.client``."""
    level = logging.getLevelName(str(entry.get("level", "ERROR")).upper())
    if not isinstance(level, int):
        level = logging.ERROR
    extra = {f"client_{k}": v for k, v in entry.items() if k not in ("level", "msg")}
    get_logger("client").log(level, str(entry.get("msg", "")), extra=extra)


__all__ = [
    "JOB_ID",
    "JsonlHandler",
    "KEEP_DAYS",
    "REQUEST_ID",
    "client_log",
    "current_job_id",
    "current_request_id",
    "get_logger",
    "log_context",
    "log_file",
    "new_request_id",
    "prune",
    "setup",
]
