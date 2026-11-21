"""The engine's build hash, its Node, and the contract majors this Python knows (engine/PROTOCOL.md, decision 9.20).

**engine_build** is the sha256 of ``engine/src/**`` and ``engine/package.json``: every regular file under
``engine/src`` plus ``engine/package.json``, named by its POSIX path relative to ``engine/``, sorted by that path;
for each, the line ``<path>\\n`` and then the file's bytes, all hashed in one stream. ``engine/src/build.ts`` computes
the same value in Node and the sidecar sends it in its hello (``test_build_hash_matches_hello``). It enters the key of
every engine job (9.19). The files are LF on every platform (``.gitattributes``: ``engine/** eol=lf``), so the hash
does not depend on the checkout.

**Node** is ``engine.node`` of the merged config (``configs/hub.json``, overridden by ``configs/local.json``), found
on ``PATH`` when it is a bare name. Node ``engine.node_min`` (22.18) or later runs the ``.ts`` source directly.

**Contract majors.** ``known_contracts()`` gives the majors of the pydantic models generated from ``engine/schema/v0``
(``region.contract.gen``). An engine whose hello names another major for one of them is refused.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from region.core import paths
from region.core.errors import EngineUnavailable

ENGINE_DIR: Path = paths.REPO / "engine"
SIDECAR = "src/sidecar.ts"
CLI = "src/cli.ts"
DEFAULT_NODE_MIN = (22, 18)

# The subprocess flag that keeps a child from opening a console window on Windows (0 elsewhere).
NO_WINDOW: int = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def known_contracts() -> dict[str, int]:
    """The contract majors this Python's generated models describe: ``{"section_input": 0, "vertical_rail": 0}``."""
    from region.contract.gen import CONTRACTS

    return dict(CONTRACTS)


# ---------------------------------------------------------------------------------------------------- engine_build


def build_files(engine_dir: Path | None = None) -> list[str]:
    """The files ``engine_build`` covers, as POSIX paths relative to ``engine/``, sorted."""
    root = Path(engine_dir or ENGINE_DIR)
    out = ["package.json"]

    def walk(rel: str) -> None:
        with os.scandir(root.joinpath(*rel.split("/"))) as it:
            for ent in it:
                child = f"{rel}/{ent.name}"
                if ent.is_dir(follow_symlinks=False):
                    walk(child)
                elif ent.is_file(follow_symlinks=False):
                    out.append(child)

    walk("src")
    return sorted(out)


_build_cache: dict[tuple[str, tuple[tuple[str, int, int], ...]], str] = {}
_build_lock = threading.Lock()


def engine_build(engine_dir: Path | None = None) -> str:
    """The engine_build of the engine at ``engine_dir`` (the repo's ``engine/`` by default).

    The hash is cached by each file's path, size and mtime, so calling this for every job key costs a folder walk.
    """
    root = Path(engine_dir or ENGINE_DIR)
    files = build_files(root)
    sig_parts = []
    for rel in files:
        st = root.joinpath(*rel.split("/")).stat()
        sig_parts.append((rel, st.st_size, st.st_mtime_ns))
    sig = (str(root), tuple(sig_parts))
    with _build_lock:
        hit = _build_cache.get(sig)
    if hit is not None:
        return hit
    h = hashlib.sha256()
    for rel in files:
        h.update(f"{rel}\n".encode())
        with open(root.joinpath(*rel.split("/")), "rb") as f:
            h.update(f.read())
    value = h.hexdigest()
    with _build_lock:
        _build_cache.clear()
        _build_cache[sig] = value
    return value


def engine_version(engine_dir: Path | None = None) -> str:
    """The ``version`` of ``engine/package.json``."""
    from region.core import fsio

    return str(fsio.read_json(Path(engine_dir or ENGINE_DIR) / "package.json")["version"])


# ------------------------------------------------------------------------------------------------------------ node


def _engine_cfg() -> dict[str, Any]:
    cfg = paths.config().get("engine") or {}
    return cfg if isinstance(cfg, dict) else {}


def node_min() -> tuple[int, int]:
    """The oldest Node the engine runs on, from ``engine.node_min`` (``"22.18"``)."""
    raw = str(_engine_cfg().get("node_min") or "")
    m = re.match(r"^(\d+)\.(\d+)", raw)
    return (int(m.group(1)), int(m.group(2))) if m else DEFAULT_NODE_MIN


def find_node(node: str | os.PathLike[str] | None = None) -> str:
    """The Node executable: ``node`` as given, else ``engine.node`` of the config, found on PATH when it is a bare
    name. ``EngineUnavailable(reason="no_node")`` when there is none."""
    want = os.fspath(node) if node is not None else str(_engine_cfg().get("node") or "node")
    if os.path.dirname(want):
        if os.path.isfile(want):
            return want
        raise EngineUnavailable(f"Node is not at {want} (engine.node in configs/local.json)", reason="no_node")
    found = shutil.which(want)
    if not found:
        raise EngineUnavailable(
            f"Node ({want}) is not on PATH: install Node 22.18 or later, or set engine.node in configs/local.json",
            reason="no_node",
        )
    return found


_version_cache: dict[str, tuple[int, int, int]] = {}


def node_version(node: str) -> tuple[int, int, int]:
    """``node --version`` as (major, minor, patch), cached per executable."""
    if node in _version_cache:
        return _version_cache[node]
    try:
        r = subprocess.run(
            [node, "--version"], capture_output=True, text=True, encoding="utf-8", timeout=30, creationflags=NO_WINDOW
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise EngineUnavailable(f"Node at {node} did not run: {e}", reason="no_node") from None
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", (r.stdout or "").strip())
    if r.returncode != 0 or not m:
        raise EngineUnavailable(f"Node at {node} gave no version", reason="no_node", stderr_tail=r.stderr or "")
    version = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    _version_cache[node] = version
    return version


def check_node(node: str | os.PathLike[str] | None = None) -> str:
    """The Node executable, checked to be ``engine.node_min`` or later; ``EngineUnavailable`` otherwise."""
    exe = find_node(node)
    version = node_version(exe)
    low = node_min()
    if version[:2] < low:
        have = ".".join(map(str, version))
        raise EngineUnavailable(
            f"Node {have} at {exe} is too old: the engine needs {low[0]}.{low[1]} or later", reason="node_version"
        )
    return exe


# ------------------------------------------------------------------------------------------------------- contracts


def check_hello(hello: Any) -> dict[str, Any]:
    """The hello's body when this Python can use the engine; ``EngineUnavailable(reason="contract")`` when the
    engine names a major this Python does not know for one of its contracts, or lacks one it needs."""
    body = hello.get("hello") if isinstance(hello, dict) else None
    if not isinstance(body, dict) or not isinstance(body.get("contracts"), dict):
        raise EngineUnavailable("the engine's first line is not a hello", reason="contract")
    theirs = body["contracts"]
    for name, major in known_contracts().items():
        if theirs.get(name) != major:
            raise EngineUnavailable(
                f"the engine speaks {name} major {theirs.get(name)}, this hub knows major {major}: "
                "update both from the same checkout",
                reason="contract",
            )
    return body


__all__ = [
    "CLI",
    "ENGINE_DIR",
    "NO_WINDOW",
    "SIDECAR",
    "build_files",
    "check_hello",
    "check_node",
    "engine_build",
    "engine_version",
    "find_node",
    "known_contracts",
    "node_min",
    "node_version",
]
