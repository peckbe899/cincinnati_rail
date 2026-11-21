"""Files: atomic writes behind a write guard, UTF-8 reads, canonical JSON and content hashes (section 9, Files).

**Writes.** Every file the hub writes goes through ``write_atomic``: a temp file in the same folder, flush and fsync,
then ``os.replace``. On Windows the replace fails with WinError 5 (access denied) or 32 (sharing violation) while
another process (an editor, OneDrive, a virus scanner, a reader) holds the target open; it is retried with backoff
for about two seconds before the error is raised. Text is written as UTF-8 bytes, so line endings are exactly the
ones given (LF) on every platform.

**The write guard.** Writes are allowed only under ``var/``, ``app/dist``, ``region/seed/`` and ``region/ids/``
(``write_roots()``), and every component below the root, as given and as resolved, must pass ``paths.check_name``
(no reserved Windows name, no trailing dot or space). Anything else raises ``WriteRefused``. Tests and tools add
roots for a block with ``allow_writes(tmp_path)``.

**Reads.** ``read_text`` and friends decode UTF-8 (a BOM is dropped) with universal newlines, so a CRLF file reads
the same as an LF one.

**Canonical JSON.** ``canonical_json`` is RFC 8785 (JCS): keys sorted by UTF-16 code units, no whitespace, numbers
in ECMAScript form (``1.0`` is ``1``, ``1e-7`` is ``1e-7``), so Python and the TypeScript engine produce the same
bytes for the same value (``engine/src/contract/common.ts`` ``canonicalJson``). Content hashes and job keys are
``sha256_hex(canonical_json(value))``.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from . import paths

RETRY_WINERRORS = frozenset({5, 32})
RETRY_TOTAL_S = 2.0


class WriteRefused(PermissionError):
    """A write outside the guarded roots, or to a name Windows cannot hold."""


# ----------------------------------------------------------------------------------------------------------- guard

_extra_roots: list[Path] = []
_guard_lock = threading.Lock()


def default_write_roots() -> tuple[Path, ...]:
    """``var``, ``app/dist``, ``region/seed`` and ``region/ids`` of this repo."""
    repo = paths.repo_root()
    return (paths.var_root(), repo / "app" / "dist", repo / "region" / "seed", repo / "region" / "ids")


def write_roots() -> tuple[Path, ...]:
    """Every root a write may land under: the defaults plus any added by ``allow_writes``."""
    with _guard_lock:
        extra = tuple(_extra_roots)
    return default_write_roots() + extra


@contextlib.contextmanager
def allow_writes(*roots: str | os.PathLike[str]) -> Iterator[None]:
    """Allow writes under ``roots`` for the duration of the block (tests, ``crhub rebuild`` into a scratch folder)."""
    added = [Path(r) for r in roots]
    with _guard_lock:
        _extra_roots.extend(added)
    try:
        yield
    finally:
        with _guard_lock:
            for r in added:
                _extra_roots.remove(r)


def _within(root: str, target: str) -> bool:
    try:
        common = os.path.commonpath([root, target])
    except ValueError:
        return False
    return os.path.normcase(common) == os.path.normcase(root)


def _names_below(root: str, target: str) -> tuple[str, ...] | None:
    """The components of ``target`` below ``root``, or ``None`` when ``target`` is not inside ``root``."""
    if not _within(root, target):
        return None
    rel = os.path.relpath(target, root)
    return () if rel == "." else Path(rel).parts


def check_write(path: str | os.PathLike[str]) -> Path:
    """The absolute path to write, or ``WriteRefused`` when it is outside every write root or has an unsafe name.

    The names below the root are checked twice: as resolved, and as given. The second check matters on Windows, whose
    path normalisation (``abspath``, ``realpath``) silently drops a trailing dot or space, so ``notes.`` would
    otherwise be written as ``notes``.
    """
    raw = os.fspath(path)
    # made absolute by string operations only, so Windows cannot rewrite the names
    given = os.path.normpath(raw if os.path.isabs(raw) else os.path.join(os.getcwd(), raw))
    target = os.path.realpath(given)
    for root in write_roots():
        root_given = os.path.normpath(os.path.abspath(root))
        below = _names_below(os.path.realpath(root_given), target)
        if below is None:
            continue
        lexical = _names_below(root_given, given)
        names = list(below) + list(lexical if lexical is not None else (os.path.basename(given),))
        for part in names:
            if part == "":
                continue
            try:
                paths.check_name(part)
            except paths.UnsafePath as e:
                raise WriteRefused(f"refused to write {path}: {e.detail}") from None
        return Path(target)
    raise WriteRefused(f"refused to write {path}: outside the write roots ({', '.join(str(r) for r in write_roots())})")


# ---------------------------------------------------------------------------------------------------------- writes


def _replace(src: str, dst: str) -> None:
    deadline = time.monotonic() + RETRY_TOTAL_S
    delay = 0.01
    while True:
        try:
            os.replace(src, dst)
            return
        except OSError as e:  # on Windows both arrive as PermissionError; any OSError carrying them is retried
            if getattr(e, "winerror", None) not in RETRY_WINERRORS or time.monotonic() >= deadline:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 0.2)


def _fsync_dir(folder: Path) -> None:
    if sys.platform == "win32":
        return
    try:
        fd = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def write_atomic(path: str | os.PathLike[str], data: bytes | str) -> Path:
    """Write ``data`` (bytes, or text encoded as UTF-8 with its newlines unchanged) to ``path`` atomically.

    A reader never sees a partial file: it sees the old content or the new. Readers holding the old file open keep
    reading the old content. The parent folders are created. Returns the absolute path written.
    """
    target = check_write(path)
    payload = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = target.stat().st_mode & 0o777
    except FileNotFoundError:
        mode = 0o644
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        if sys.platform != "win32":
            os.chmod(tmp, mode)
        _replace(tmp, str(target))
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    _fsync_dir(target.parent)
    return target


def write_text(path: str | os.PathLike[str], text: str) -> Path:
    """``write_atomic`` for text, with every line ending normalised to LF."""
    return write_atomic(path, text.replace("\r\n", "\n").replace("\r", "\n"))


def write_json(path: str | os.PathLike[str], value: Any, *, indent: int | None = 1) -> Path:
    """Pretty JSON for files people read and diff: sorted keys, UTF-8, LF, a final newline."""
    text = json.dumps(value, indent=indent, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return write_atomic(path, text + "\n")


# ----------------------------------------------------------------------------------------------------------- reads


def read_text(path: str | os.PathLike[str]) -> str:
    """The text of a UTF-8 file, BOM dropped, CRLF and CR read as LF."""
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def read_json(path: str | os.PathLike[str]) -> Any:
    """A JSON file read as UTF-8 (BOM dropped)."""
    return json.loads(read_text(path))


def read_yaml(path: str | os.PathLike[str]) -> Any:
    """A YAML file read as UTF-8 with ``yaml.safe_load``."""
    import yaml

    return yaml.safe_load(read_text(path))


# ------------------------------------------------------------------------------------------- canonical JSON, hashes

_MAX_SAFE_INT = 2**53


def _js_number(x: float) -> str:
    """ECMAScript Number::toString of a finite double (what JSON.stringify writes)."""
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    # repr gives the shortest round-trip digits, as ECMAScript does; only the layout differs.
    mant, _, exp = repr(abs(x)).partition("e")
    whole, _, frac = mant.partition(".")
    raw = whole + frac
    digits = raw.lstrip("0")
    # the value is 0.<digits> times 10**n
    n = len(whole) + int(exp or 0) - (len(raw) - len(digits))
    digits = digits.rstrip("0")
    k = len(digits)
    if k <= n <= 21:
        out = digits + "0" * (n - k)
    elif 0 < n <= 21:
        out = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        out = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        es = ("+" if e > 0 else "-") + str(abs(e))
        out = digits + "e" + es if k == 1 else digits[0] + "." + digits[1:] + "e" + es
    return sign + out


def _jcs(value: Any, out: list[str]) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, int):
        if abs(value) > _MAX_SAFE_INT:
            raise ValueError(f"integer {value} is beyond 2**53 and has no exact JSON number")
        out.append(str(value))
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN and infinity have no JSON form")
        out.append(_js_number(value))
    elif isinstance(value, str):
        out.append(json.dumps(value, ensure_ascii=False))
    elif isinstance(value, dict):
        items = []
        for key in value:
            if not isinstance(key, str):
                raise TypeError(f"object key {key!r} is not a string")
            items.append(key)
        items.sort(key=lambda s: s.encode("utf-16-be"))
        out.append("{")
        for i, key in enumerate(items):
            if i:
                out.append(",")
            out.append(json.dumps(key, ensure_ascii=False))
            out.append(":")
            _jcs(value[key], out)
        out.append("}")
    elif isinstance(value, (list, tuple)):
        out.append("[")
        for i, item in enumerate(value):
            if i:
                out.append(",")
            _jcs(item, out)
        out.append("]")
    else:
        # numpy scalars and other number-likes
        if hasattr(value, "item"):
            _jcs(value.item(), out)
            return
        raise TypeError(f"{type(value).__name__} has no canonical JSON form")


def canonical_json(value: Any) -> bytes:
    """The RFC 8785 (JCS) bytes of a JSON value: the same bytes the engine's ``canonicalJson`` gives."""
    out: list[str] = []
    _jcs(value, out)
    return "".join(out).encode("utf-8")


def sha256_hex(data: bytes | str) -> str:
    """The lowercase hex sha256 of bytes (text is UTF-8 encoded)."""
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def content_hash(value: Any) -> str:
    """``sha256_hex(canonical_json(value))``: the hash of a JSON value, for records, inputs and keys."""
    return sha256_hex(canonical_json(value))


def sha256_file(path: str | os.PathLike[str], *, chunk: int = 1 << 20) -> str:
    """The sha256 of a file's bytes, read in 1 MiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


__all__ = [
    "RETRY_WINERRORS",
    "WriteRefused",
    "allow_writes",
    "canonical_json",
    "check_write",
    "content_hash",
    "default_write_roots",
    "read_json",
    "read_text",
    "read_yaml",
    "sha256_file",
    "sha256_hex",
    "write_atomic",
    "write_json",
    "write_roots",
    "write_text",
]
