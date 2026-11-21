"""Job keys: one hash over the content a job's plan read (decision 9.19, section 6 "Key composition").

    key = sha256(canonical_json({t, tv, code, e, c, axes, in}))

- ``t`` is the job type and ``tv`` its version (a string, ``"1"``).
- ``code`` is the sha256 of the job type's source (``code_hash``), plus any ``code_files`` it declares (railsim's
  source for railsim jobs).
- ``e`` is the engine build, for engine jobs; ``None`` for the others.
- ``c`` is the engine contract majors, for engine jobs; ``{}`` for the others.
- ``axes`` holds only the view axes the job declared (``View.key_axes``). The layer is never an axis: a layer enters
  a key only through the content it resolves to, so equal scenario content shares a result.
- ``in`` is the sorted list of ``[ref, hash]`` pairs the plan read: ``rec:<id>`` with the record's content hash,
  ``file:<uri>`` with the file's sha256, ``param:<path>`` with the hash of the resolved value and
  ``job:<type>/<scope>`` with the upstream ``output_hash`` (early cutoff). ``None`` stands for an absence.

Record versions, changesets, authors and times never enter a key: the content hash of a record leaves them out
(9.29), so two databases holding the same content give the same keys. ``canonical_json`` is RFC 8785, so the bytes
and the key are the same on every machine and in every process.
"""

from __future__ import annotations

import hashlib
import inspect
import os
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from region.core import fsio, paths
from region.core.errors import Invalid

RefPair = tuple[str, str | None]


def normalize_refs(refs: Iterable[Sequence[Any]]) -> list[list[Any]]:
    """The ``in`` member of a key: ``[ref, hash]`` pairs with exact duplicates dropped, sorted by ref then hash.

    A ref read twice with two different hashes (the store moved during the plan) keeps both pairs, so the key
    still describes exactly what was read.
    """
    seen: set[tuple[str, str | None]] = set()
    for pair in refs:
        if len(pair) != 2:
            raise Invalid(f"a key input is a [ref, hash] pair, not {pair!r}")
        ref, h = pair[0], pair[1]
        if not isinstance(ref, str) or not ref:
            raise Invalid(f"a key ref is a non-empty string, not {ref!r}")
        if h is not None and not isinstance(h, str):
            raise Invalid(f"the hash of {ref} is a string or None, not {h!r}")
        seen.add((ref, h))
    return [[r, h] for r, h in sorted(seen, key=lambda p: (p[0], "" if p[1] is None else p[1]))]


def key_body(
    type: str,
    version: str,
    code: str,
    refs: Iterable[Sequence[Any]],
    axes: Mapping[str, Any],
    engine_build: str | None,
    contracts: Mapping[str, Any],
) -> dict[str, Any]:
    """The JSON object a key hashes (useful in a job log and when two keys differ unexpectedly)."""
    if not isinstance(type, str) or not type:
        raise Invalid("a job key needs the job type")
    if not isinstance(version, str):
        raise Invalid(f"job type {type}: version is a string ('1'), not {version!r}")
    return {
        "t": type,
        "tv": version,
        "code": code,
        "e": engine_build,
        "c": dict(contracts or {}),
        "axes": dict(axes or {}),
        "in": normalize_refs(refs),
    }


def key(
    type: str,
    version: str,
    code: str,
    refs: list[tuple[str, str]],
    axes: dict,
    engine_build: str | None,
    contracts: dict,
) -> str:
    """The cache key of a job: ``sha256(canonical_json({t, tv, code, e, c, axes, in}))`` in lowercase hex."""
    return fsio.content_hash(key_body(type, version, code, refs, axes, engine_build, contracts))


def value_hash(value: Any) -> str:
    """The hash of a resolved param (or any JSON value): ``content_hash`` of it."""
    return fsio.content_hash(value)


# ------------------------------------------------------------------------------------------------------ code hash


def _source_bytes(path: Path) -> bytes:
    # CRLF and LF checkouts of the same source give the same hash (Ben's Windows clone and this one)
    return path.read_bytes().replace(b"\r\n", b"\n")


def _module_file(module_name: str) -> Path | None:
    module = sys.modules.get(module_name)
    if module is None:
        return None
    try:
        found = inspect.getsourcefile(module)
    except TypeError:
        return None
    return Path(found) if found else None


def _relname(path: Path) -> str:
    """A machine-independent name for a source file: its path inside the repo, else its file name."""
    try:
        return Path(os.path.relpath(path.resolve(), paths.repo_root())).as_posix()
    except ValueError:  # another drive on Windows
        return path.name


def source_hash(files: Iterable[Path]) -> str:
    """sha256 over source files, each fed as ``<name>\\n`` then its bytes (CRLF read as LF), in name order.
    A folder stands for every ``.py`` file under it."""
    found: dict[str, Path] = {}
    for f in files:
        f = Path(f)
        if f.is_dir():
            for p in sorted(f.rglob("*.py")):
                if "__pycache__" not in p.parts:
                    found[_relname(p)] = p
        elif f.is_file():
            found[_relname(f)] = f
        else:
            raise Invalid(f"code file {f} does not exist")
    h = hashlib.sha256()
    for name in sorted(found):
        h.update(name.encode("utf-8") + b"\n")
        h.update(_source_bytes(found[name]))
    return h.hexdigest()


_code_cache: dict[int, tuple[object, str]] = {}


def code_hash(job_type: Any) -> str:
    """The ``code`` member of a job's key: the sha256 of the module that defines the job type's class, plus any
    ``code_files`` the type declares (paths, or ``repo://`` URIs; folders stand for their ``.py`` files).

    A type may instead set ``code`` to a fixed hex string (tests do, to pin keys). Computed once per object and
    process: a code change is picked up when the hub restarts.
    """
    fixed = getattr(job_type, "code", None)
    if isinstance(fixed, str) and fixed:
        return fixed
    cached = _code_cache.get(id(job_type))
    if cached is not None and cached[0] is job_type:
        return cached[1]
    files: list[Path] = []
    names = [job_type.__name__] if inspect.ismodule(job_type) else []
    names += [type(job_type).__module__, getattr(job_type, "__module__", None)]
    for module_name in dict.fromkeys(names):
        if not module_name:
            continue
        f = _module_file(module_name)
        if f is not None and f.is_file():
            files.append(f)
    for extra in getattr(job_type, "code_files", ()) or ():
        text = str(extra)
        files.append(paths.resolve(text) if "://" in text else Path(text))
    if not files:
        raise Invalid(f"job type {getattr(job_type, 'name', job_type)!r}: no source file to hash; set code")
    digest = source_hash(files)
    _code_cache[id(job_type)] = (job_type, digest)
    return digest


__all__ = ["RefPair", "code_hash", "key", "key_body", "normalize_refs", "source_hash", "value_hash"]
