"""Record ids: ULIDs, random for authored records and stable for imported ones (decision 9.17).

Every record id is a ULID: 26 Crockford base32 characters holding a 48-bit millisecond time and 80 random bits.

- ``new()`` mints a random ULID for an authored record. It is monotonic within one process: two ids minted in the
  same millisecond still sort in minting order.
- ``stable(namespace, key)`` mints the same id for the same source key on every machine. Its time part is the
  namespace's fixed epoch from ``region/ids/namespaces.yaml`` and its 80 bits are the first 80 bits of
  ``sha256("<namespace>:<key>")`` (the key NFC-normalised, UTF-8). The time part tells which namespace an id belongs
  to, which is how an import layer's namespace is enforced on write (``namespace_of``).

Callers that import should not call ``stable`` directly: ``IdLookup.id_for`` matches before it mints (the persisted
legacy index, then a declared rename match, and only then ``stable``), so a renamed source keeps its id.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from .errors import Invalid

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ULID_RE = re.compile(r"^[0-7][0-9A-HJKMNP-TV-Z]{25}$")
NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_DECODE = {c: i for i, c in enumerate(ALPHABET)}
_RAND_BITS = 80
_RAND_MAX = (1 << _RAND_BITS) - 1

NAMESPACES_FILE = Path(__file__).resolve().parents[1] / "ids" / "namespaces.yaml"


def encode(value: int) -> str:
    """The 26-character Crockford base32 form of a 128-bit integer."""
    if not 0 <= value < (1 << 128):
        raise ValueError("a ULID is a 128-bit unsigned integer")
    out = []
    for _ in range(26):
        out.append(ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(out))


def decode(text: str) -> int:
    """The 128-bit integer of a ULID string. Raises ``Invalid`` for anything that is not a canonical ULID."""
    if not is_ulid(text):
        raise Invalid(f"{text!r} is not a ULID", errors=[{"path": "/id", "message": "26-character ULID"}])
    value = 0
    for ch in text:
        value = (value << 5) | _DECODE[ch]
    return value


def is_ulid(text: object) -> bool:
    """True for a canonical (upper-case, 26-character) ULID string."""
    return isinstance(text, str) and ULID_RE.match(text) is not None


def timestamp_ms(text: str) -> int:
    """The 48-bit time part of a ULID, in milliseconds since the Unix epoch."""
    return decode(text) >> _RAND_BITS


def from_parts(ms: int, rand: int) -> str:
    """A ULID from its time part (ms) and its 80-bit random part."""
    if not 0 <= ms < (1 << 48):
        raise ValueError("ULID time out of range")
    if not 0 <= rand <= _RAND_MAX:
        raise ValueError("ULID random part out of range")
    return encode((ms << _RAND_BITS) | rand)


class _Monotonic:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ms = -1
        self._rand = 0

    def __call__(self) -> str:
        with self._lock:
            ms = time.time_ns() // 1_000_000
            if ms <= self._ms:
                ms = self._ms
                self._rand += 1
                if self._rand > _RAND_MAX:
                    ms += 1
                    self._rand = secrets.randbits(_RAND_BITS - 1)
            else:
                # one bit of headroom so increments in a burst cannot overflow
                self._rand = secrets.randbits(_RAND_BITS - 1)
            self._ms = ms
            return from_parts(ms, self._rand)


_new = _Monotonic()


def new() -> str:
    """A new random ULID for an authored record (or a changeset, a conflict, a request). Monotonic per process."""
    return _new()


@dataclass(frozen=True)
class Namespace:
    """One id namespace from ``region/ids/namespaces.yaml``."""

    name: str
    epoch_ms: int
    layer: str
    about: str = ""
    test: bool = False

    @property
    def ledger(self) -> Path:
        """The id ledger of this namespace: ``region/ids/<namespace>.tsv``."""
        return NAMESPACES_FILE.parent / f"{self.name}.tsv"


def _epoch_ms(text: str) -> int:
    dt = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"epoch {text!r} needs a UTC offset (end it with Z)")
    return int(dt.timestamp() * 1000)


def load_namespaces(path: Path | None = None) -> dict[str, Namespace]:
    """Read and check a namespaces file (default ``region/ids/namespaces.yaml``).

    Checks: names are slugs, every epoch parses, no two namespaces share an epoch, layers are layer slugs.
    """
    import yaml

    from .view import LAYER_RE

    path = path or NAMESPACES_FILE
    with open(path, encoding="utf-8-sig") as f:
        doc = yaml.safe_load(f) or {}
    out: dict[str, Namespace] = {}
    seen: dict[int, str] = {}
    for name, spec in (doc.get("namespaces") or {}).items():
        if not NAMESPACE_RE.match(str(name)):
            raise Invalid(f"{path}: namespace {name!r} is not a slug")
        ms = _epoch_ms(spec["epoch"])
        if ms in seen:
            raise Invalid(f"{path}: namespaces {seen[ms]!r} and {name!r} share an epoch")
        seen[ms] = name
        layer = str(spec["layer"])
        if not LAYER_RE.match(layer):
            raise Invalid(f"{path}: namespace {name!r} names layer {layer!r}, which is not a layer slug")
        out[name] = Namespace(name, ms, layer, str(spec.get("about", "")).strip(), bool(spec.get("test", False)))
    return out


@lru_cache(maxsize=1)
def namespaces() -> dict[str, Namespace]:
    """The committed namespaces, read once per process."""
    return load_namespaces()


def stable(namespace: str, key: str) -> str:
    """The stable id of ``key`` in ``namespace``: the namespace epoch plus 80 bits of sha256 (see the module doc).

    Raises ``Invalid`` for a namespace that ``region/ids/namespaces.yaml`` does not declare.
    """
    ns = namespaces().get(namespace)
    if ns is None:
        raise Invalid(f"unknown id namespace {namespace!r}; declare it in region/ids/namespaces.yaml")
    if not isinstance(key, str) or key == "":
        raise Invalid("a stable id needs a non-empty string key")
    text = f"{namespace}:{unicodedata.normalize('NFC', key)}"
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return from_parts(ns.epoch_ms, int.from_bytes(digest[:10], "big"))


def namespace_of(text: str) -> str | None:
    """The namespace whose epoch is this id's time part, or ``None`` for an authored (random) id."""
    ms = timestamp_ms(text)
    for ns in namespaces().values():
        if ns.epoch_ms == ms:
            return ns.name
    return None


__all__ = [
    "ALPHABET",
    "NAMESPACES_FILE",
    "Namespace",
    "ULID_RE",
    "decode",
    "encode",
    "from_parts",
    "is_ulid",
    "load_namespaces",
    "namespace_of",
    "namespaces",
    "new",
    "stable",
    "timestamp_ms",
]
