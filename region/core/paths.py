"""Where things are: the repo, ``var``, the configs, and the lane-B data tiers named by ``tier://`` URIs.

**Config.** ``configs/hub.json`` (committed: port, var, pool sizes), then ``configs/hub_paths.json`` (committed: the
data tiers), then ``configs/local.json`` (this machine only, gitignored; see ``configs/local.example.json``), merged in
that order, then the file the ``CRHUB_CONFIG`` environment variable names, if any (a test hub that moves a tier's
root). ``config()`` caches the merge for the process; ``reload()`` drops the cache.

**var.** The folder for the databases, cache, blobs, logs and backups. In order of precedence: the ``CRHUB_VAR``
environment variable, ``"var"`` in ``configs/local.json``, ``"var"`` in ``configs/hub.json``, then the platform
default: ``%LOCALAPPDATA%\\CincinnatiRail\\hub`` on Windows (9.22: not the repo, which OneDrive often syncs) and
``<repo>/var`` elsewhere. A relative value is relative to the repo root; ``~`` and environment variables expand.

**URIs.** Records and job keys never hold absolute paths (9.26). Three schemes resolve to files:

- ``tier://<tier>/<path>``: a file in a data tier of ``configs/hub_paths.json``;
- ``repo://<path>``: a file in the repo (``repo://rules/registry.yaml``);
- ``var://<path>``: a file under ``var``.

``<path>`` is POSIX relative and passes ``check_relpath``: no ``..``, backslash, ``%5c`` or other leftover escape,
drive letter, UNC prefix, ``:`` (alternate data streams), Windows reserved name (``CON``, ``NUL``, ``COM1``) or
trailing dot or space. Resolution is contained by realpath and commonpath, so a symlink cannot lead out of its root.

A tier whose root is absent resolves to ``TierMissing``, a ``NotFound`` that carries a plain reason for status chips
and a map layer's ``available()``; it is never a crash. The full tier scan (manifest, handshake, counts) is
``region/tiers`` (WP0b); this module only finds roots.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from .errors import Invalid, NotFound

REPO: Path = Path(__file__).resolve().parents[2]
CONFIG_FILES = ("configs/hub.json", "configs/hub_paths.json", "configs/local.json")
VAR_ENV = "CRHUB_VAR"
CONFIG_ENV = "CRHUB_CONFIG"
SCHEMES = ("tier", "repo", "var")

# Windows device names, reserved with any extension and in any case (CON.txt, nul, COM1.log, LPT¹).
_DIGITS = "0123456789¹²³"
RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {f"COM{d}" for d in _DIGITS} | {f"LPT{d}" for d in _DIGITS}
)
_BAD_CHARS = frozenset('<>:"|?*\\/')
_ESCAPE_RE = re.compile(r"%[0-9a-fA-F]{2}")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_URI_RE = re.compile(r"^(tier|repo|var)://(.*)$", re.S)


class UnsafePath(NotFound):
    """A path that could escape its root or that Windows cannot hold. Reported as 404, never as the reason."""

    code = "unsafe_path"
    title = "Not found"


class TierMissing(NotFound):
    """A ``tier://`` URI whose tier is unknown or whose root is not on this machine.

    ``tier`` names the tier and ``reason`` says what is missing in one plain sentence.
    """

    code = "tier_missing"
    title = "Data tier missing"

    def __init__(self, tier: str, reason: str) -> None:
        super().__init__(reason, tier=tier)
        self.tier = tier
        self.reason = reason


# ---------------------------------------------------------------------------------------------------------- names


def check_name(name: str) -> str:
    """Refuse one path component that is unsafe on any platform; return it unchanged when it is fine."""
    if not isinstance(name, str) or name in ("", ".", ".."):
        raise UnsafePath(f"path component {name!r} is not allowed")
    for ch in name:
        if ch in _BAD_CHARS or ord(ch) < 32 or ord(ch) == 127:
            raise UnsafePath(f"path component {name!r} holds the character {ch!r}")
    if name[-1] in ". ":
        raise UnsafePath(f"path component {name!r} ends in a dot or a space")
    stem = name.split(".", 1)[0].rstrip(" ").upper()
    if stem in RESERVED_NAMES:
        raise UnsafePath(f"path component {name!r} is a reserved Windows name")
    return name


def check_relpath(rel: str) -> PurePosixPath:
    """A safe POSIX relative path, or ``UnsafePath``. ``""`` is the root itself; one trailing ``/`` is allowed."""
    if not isinstance(rel, str):
        raise UnsafePath(f"path {rel!r} is not a string")
    if "\\" in rel:
        raise UnsafePath(f"path {rel!r} holds a backslash")
    if _ESCAPE_RE.search(rel):
        raise UnsafePath(f"path {rel!r} holds a percent escape")
    if rel.startswith("/"):
        raise UnsafePath(f"path {rel!r} is absolute or a UNC path")
    if _DRIVE_RE.match(rel):
        raise UnsafePath(f"path {rel!r} names a drive")
    if rel in ("", "/"):
        return PurePosixPath(".")
    body = rel[:-1] if rel.endswith("/") else rel
    for part in body.split("/"):
        check_name(part)
    return PurePosixPath(body)


def _components(path: str) -> tuple[str, str, list[str]]:
    drive, root, rest = os.path.splitroot(os.path.normpath(path))
    rest = rest.replace(os.altsep, os.sep) if os.altsep else rest
    return drive, root, [p for p in rest.split(os.sep) if p and p != "."]


def names_below(root: str | os.PathLike[str], target: str | os.PathLike[str]) -> tuple[str, ...] | None:
    """The components of ``target`` below ``root`` (``()`` for the root itself), or ``None`` when it is not inside.

    Purely lexical: call ``realpath`` on both first to follow links. Nothing here asks the OS, so a path on another
    drive or share is simply not inside, never a ``ValueError``. That matters on Windows, where ``os.path.relpath``
    calls ``abspath``, which turns ``C:\\x\\NUL`` into the device path ``\\\\.\\NUL`` and then raises because that
    is "on another mount".
    """
    r_drive, r_root, r_parts = _components(os.fspath(root))
    t_drive, t_root, t_parts = _components(os.fspath(target))
    if os.path.normcase(r_drive + r_root) != os.path.normcase(t_drive + t_root) or len(t_parts) < len(r_parts):
        return None
    for a, b in zip(r_parts, t_parts, strict=False):
        if os.path.normcase(a) != os.path.normcase(b):
            return None
    below = tuple(t_parts[len(r_parts) :])
    # normpath keeps a leading ".." of a relative path ("." and "../x"): that climbs out, so it is not inside
    return None if ".." in below else below


def contained(root: Path, rel: str) -> Path:
    """``root / rel`` after ``check_relpath``, refused when its realpath leaves ``root``'s realpath."""
    parts = check_relpath(rel).parts
    base = os.path.realpath(root)
    target = os.path.realpath(os.path.join(base, *[p for p in parts if p != "."]))
    if names_below(base, target) is None:  # another folder, drive or device
        raise UnsafePath(f"path {rel!r} leads out of its root")
    return Path(target)


# --------------------------------------------------------------------------------------------------------- config


def repo_root() -> Path:
    """The repository root (the folder holding ``pyproject.toml``, ``region/`` and ``configs/``)."""
    return REPO


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8-sig") as f:
        doc = json.load(f)
    if not isinstance(doc, dict):
        raise Invalid(f"{path} does not hold a JSON object")
    return doc


def _merge(base: dict[str, Any], over: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in over.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def load_config(repo: Path | None = None) -> dict[str, Any]:
    """Read and merge the three config files of ``repo`` (default: this repo). Missing files are skipped.

    The result is ``hub.json``'s members, plus ``tiers`` (a dict by tier name, from ``hub_paths.json``'s list), with
    ``local.json`` merged over both. ``_repo`` holds the repo root and ``_files`` the files read.
    """
    root = Path(repo) if repo is not None else REPO
    cfg: dict[str, Any] = {}
    files: list[str] = []
    hub = root / CONFIG_FILES[0]
    if hub.is_file():
        cfg = _read_json(hub)
        files.append(str(hub))
    tiers: dict[str, Any] = {}
    paths_file = root / CONFIG_FILES[1]
    if paths_file.is_file():
        for spec in _read_json(paths_file).get("tiers", []):
            tiers[spec["name"]] = dict(spec)
        files.append(str(paths_file))
    cfg["tiers"] = tiers
    local = root / CONFIG_FILES[2]
    if local.is_file():
        over = _read_json(local)
        over.pop("about", None)
        _merge(cfg, over)
        files.append(str(local))
    extra = os.environ.get(CONFIG_ENV)
    if extra and repo is None:
        over = _read_json(Path(extra))
        over.pop("about", None)
        _merge(cfg, over)
        files.append(str(extra))
    cfg["_repo"] = str(root)
    cfg["_files"] = files
    return cfg


@lru_cache(maxsize=1)
def _cached_config() -> dict[str, Any]:
    return load_config()


def config() -> dict[str, Any]:
    """The merged config of this repo, read once per process (a deep copy, safe to change)."""
    return copy.deepcopy(_cached_config())


def reload() -> None:
    """Forget the cached config (after a test or ``crhub setup`` changes a config file)."""
    _cached_config.cache_clear()


def _expand(value: str, repo: Path) -> Path:
    p = Path(os.path.expandvars(os.path.expanduser(value)))
    return p if p.is_absolute() else repo / p


def default_var(repo: Path | None = None) -> Path:
    """The platform default for ``var``: ``%LOCALAPPDATA%\\CincinnatiRail\\hub`` on Windows, else ``<repo>/var``."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "CincinnatiRail" / "hub"
    return (repo or REPO) / "var"


def describe_var(cfg: Mapping[str, Any] | None = None) -> tuple[Path, str]:
    """``(var root, where the choice came from)``: ``"env CRHUB_VAR"``, ``"config"`` or ``"default"``."""
    cfg = cfg if cfg is not None else _cached_config()  # read only: no copy
    repo = Path(cfg.get("_repo") or REPO)
    env = os.environ.get(VAR_ENV)
    if env:
        return _expand(env, repo), f"env {VAR_ENV}"
    if cfg.get("var"):
        return _expand(str(cfg["var"]), repo), "config"
    return default_var(repo), "default"


def var_root(cfg: Mapping[str, Any] | None = None) -> Path:
    """The ``var`` folder (see the module doc for the order of precedence). It may not exist yet."""
    return describe_var(cfg)[0]


def var_path(*parts: str, cfg: Mapping[str, Any] | None = None) -> Path:
    """A path under ``var``: ``var_path("logs")``, ``var_path("cache", "blobs")``."""
    return var_root(cfg).joinpath(*parts)


# ---------------------------------------------------------------------------------------------------------- tiers

TierStatus = Literal["missing", "partial", "present"]


@dataclass(frozen=True)
class Handshake:
    """A tier's handshake file: lane B writes it, the hub reads it (``ground/1912/STATUS.json``).

    ``done`` names the member whose truthy value means the tier is finished; ``detail`` the member shown as status
    detail (for example ``stage``).
    """

    file: str
    done: str = "done"
    detail: str | None = None


@dataclass(frozen=True)
class Tier:
    """One data tier of ``configs/hub_paths.json``, with its root resolved on this machine.

    ``manifest`` or ``index`` (relative to the root) is the file the tier's readers start from; ``required`` tiers
    make doctor fail when missing; ``mount`` tiers are served read-only at ``/api/v1/data/<name>/<path>``.
    """

    name: str
    root: Path
    about: str = ""
    lane: str = "B"
    manifest: str | None = None
    index: str | None = None
    handshake: Handshake | None = None
    required: bool = False
    mount: bool = False

    def available(self) -> Literal[True] | str:
        """``True`` when the root is on this machine, else the plain reason it is not."""
        if self.root.is_dir():
            return True
        return (
            f"data tier {self.name} is not on this machine: {self.root} not found "
            f"(set tiers.{self.name}.root in configs/local.json if it lives elsewhere)"
        )

    def path(self, rel: str = "") -> Path:
        """A file in this tier (contained; ``TierMissing`` when the root is absent)."""
        ok = self.available()
        if ok is not True:
            raise TierMissing(self.name, ok)
        return contained(self.root, rel)


def tiers(cfg: Mapping[str, Any] | None = None) -> dict[str, Tier]:
    """Every declared tier by name, roots resolved (relative roots are relative to the repo)."""
    cfg = cfg if cfg is not None else _cached_config()  # read only: no copy
    repo = Path(cfg.get("_repo") or REPO)
    out: dict[str, Tier] = {}
    for name, spec in (cfg.get("tiers") or {}).items():
        if "root" not in spec:
            raise Invalid(f"tier {name!r} has no root")
        hs = spec.get("handshake")
        out[name] = Tier(
            name=name,
            root=_expand(str(spec["root"]), repo),
            about=str(spec.get("about", "")),
            lane=str(spec.get("lane", "B")),
            manifest=spec.get("manifest"),
            index=spec.get("index"),
            handshake=Handshake(hs["file"], hs.get("done", "done"), hs.get("detail")) if hs else None,
            required=bool(spec.get("required", False)),
            mount=bool(spec.get("mount", False)),
        )
    return out


def tier(name: str, cfg: Mapping[str, Any] | None = None) -> Tier:
    """One tier by name; ``TierMissing`` when no such tier is declared."""
    found = tiers(cfg).get(name)
    if found is None:
        raise TierMissing(name, f"no data tier named {name!r} in configs/hub_paths.json")
    return found


def available(name: str, cfg: Mapping[str, Any] | None = None) -> Literal[True] | str:
    """``True`` when tier ``name`` is declared and its root is here, else the plain reason (for ``available()``)."""
    try:
        return tier(name, cfg).available()
    except TierMissing as e:
        return e.reason


# ----------------------------------------------------------------------------------------------------------- URIs


def parse_uri(uri: str) -> tuple[str, str | None, str]:
    """``(scheme, tier or None, relative path)`` of a ``tier://``, ``repo://`` or ``var://`` URI."""
    m = _URI_RE.match(uri) if isinstance(uri, str) else None
    if not m:
        raise Invalid(f"{uri!r} is not a tier://, repo:// or var:// URI")
    scheme, rest = m.group(1), m.group(2)
    if scheme != "tier":
        return scheme, None, rest
    name, _, rel = rest.partition("/")
    if not name:
        raise Invalid(f"{uri!r} names no tier")
    return scheme, name, rel


def resolve(uri: str, cfg: Mapping[str, Any] | None = None) -> Path:
    """The local path of a URI. The file need not exist; its root must (``TierMissing`` for an absent tier)."""
    cfg = cfg if cfg is not None else _cached_config()  # read only: no copy
    scheme, name, rel = parse_uri(uri)
    if scheme == "tier":
        assert name is not None
        return tier(name, cfg).path(rel)
    if scheme == "repo":
        return contained(Path(cfg.get("_repo") or REPO), rel)
    return contained(var_root(cfg), rel)


def to_uri(path: str | os.PathLike[str], cfg: Mapping[str, Any] | None = None) -> str:
    """The URI naming a local path: the deepest tier root holding it, else ``var://``, else ``repo://``.

    Raises ``Invalid`` for a path outside every root (it cannot be named portably).
    """
    cfg = cfg if cfg is not None else _cached_config()  # read only: no copy
    target = os.path.realpath(path)
    roots: list[tuple[str, str]] = [
        (f"tier://{t.name}/", os.path.realpath(t.root)) for t in tiers(cfg).values() if t.root.is_dir()
    ]
    roots.sort(key=lambda r: len(r[1]), reverse=True)
    roots.append(("var://", os.path.realpath(var_root(cfg))))
    roots.append(("repo://", os.path.realpath(cfg.get("_repo") or REPO)))
    for prefix, root in roots:
        below = names_below(root, target)  # None for another drive or a device path, never a ValueError
        if below is not None:
            return prefix + "/".join(below)
    raise Invalid(f"{path} lies outside the repo, var and every data tier")


__all__ = [
    "CONFIG_FILES",
    "Handshake",
    "REPO",
    "RESERVED_NAMES",
    "SCHEMES",
    "Tier",
    "TierMissing",
    "TierStatus",
    "UnsafePath",
    "VAR_ENV",
    "CONFIG_ENV",
    "available",
    "check_name",
    "check_relpath",
    "config",
    "contained",
    "default_var",
    "describe_var",
    "load_config",
    "names_below",
    "parse_uri",
    "reload",
    "repo_root",
    "resolve",
    "tier",
    "tiers",
    "to_uri",
    "var_path",
    "var_root",
]
