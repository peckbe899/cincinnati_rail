"""``crhub doctor``: check this machine, the hub's folders and its data, and say what to do about each problem.

    crhub doctor            the checks below, as a short table
    crhub doctor --data     also validate every record of var/region.db again (slower)
    crhub doctor --json     the same as one JSON object

Each check gives one row: ``ok``, ``info``, ``skip``, ``warn`` or ``FAIL``, a short detail and, for a warning or a
failure, a hint on the next line. Doctor exits 1 only when a check FAILs (something that stops the hub from running
or puts the data at risk); warnings and missing optional tiers never fail it.

The checks, in order:

- **python**: 3.12 or later, 64-bit (the locked wheels are 64-bit).
- **packages**: every package of ``requirements.lock`` installed at its locked version. A missing direct runtime
  dependency of ``pyproject.toml`` fails; any other difference warns.
- **uv**: whether uv is installed (setup and the launchers use it when it is, else ``.venv``).
- **sqlite**: the SQLite build Python carries, 3.38 or later, with JSON functions and window functions.
- **rtree**: SQLite's R-tree module (the store's spatial index). Ben's Windows build is the one to verify.
- **node**: Node 22.18 or later (``engine.node`` in the config) that strips TypeScript types itself.
- **npm**: ``node_modules`` installed by ``npm ci``, the workspaces ``@cr/engine`` and ``@cr/app`` linked to this
  repo, and every package at the version ``package-lock.json`` pins.
- **var**: the ``var`` folder is not inside a synced folder (OneDrive, Dropbox, Google Drive, iCloud: by path, by
  their marker files, and on Windows by the cloud-file attributes) and not on a network share; SQLite's WAL breaks
  there. **var write**: a probe file can be written there, and the disk has room.
- **repo**: a warning when the repo itself is in a synced folder.
- **port 8766**: the new hub's port (``port`` in the config) is free or is this hub; **port 8765**: whether the old
  hub is running (information only: both hubs run side by side).
- **tier <name>**: each data tier of ``configs/hub_paths.json`` with its handshake (``region.tiers``). A missing
  required tier fails; a missing optional tier warns; a partial one is information (warns when required).
- **sources <feature>**: the files a feature's ``SOURCES`` names, when features declare any.
- **app**: ``app/dist`` is built and not older than ``app/src``, ``engine/src`` and the app's config.
- **database**: ``var/region.db`` passes ``quick_check`` and its pending migrations are listed (with ``--data``,
  every record is validated again, on a checked copy, and only when no migration is pending).

Doctor reads and changes nothing. It never opens the database for writing and never migrates it. It writes only one
probe file in ``var`` and, with ``--data``, a copy of the database in ``var/tmp``, and deletes both again, along with
any folder it had to create for them.
"""

from __future__ import annotations

import argparse
import http.client
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import shutil
import socket
import sqlite3
import struct
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Status = Literal["ok", "info", "skip", "warn", "fail"]
LABELS: dict[str, str] = {"ok": "ok", "info": "info", "skip": "skip", "warn": "warn", "fail": "FAIL"}

PYTHON_MIN = (3, 12)
SQLITE_MIN = (3, 38, 0)
NODE_MIN_DEFAULT = "22.18"
FREE_SPACE_WARN = 2 * 1024**3  # bytes
HTTP_TIMEOUT_S = 1.0

# The files the app build is made from: app/dist must not be older than any of them.
APP_SOURCES = (
    "app/src",
    "app/public",
    "app/index.html",
    "app/vite.config.ts",
    "app/package.json",
    "app/tsconfig.json",
    "engine/src",
    "engine/package.json",
)

# A process runner: argv -> (exit code, stdout and stderr). Tests pass a fake.
Runner = Callable[[Sequence[str]], tuple[int, str]]


@dataclass
class Check:
    """One row of the doctor's table."""

    name: str
    status: Status
    detail: str
    hint: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail, "hint": self.hint}


def run_process(argv: Sequence[str], *, timeout: float = 30.0, cwd: Path | None = None) -> tuple[int, str]:
    """Run ``argv`` (a list, never a shell string) and return ``(exit code, stdout + stderr)``."""
    try:
        done = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError as e:
        return 127, str(e)
    except OSError as e:
        return 126, str(e)
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout:g} s"
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def module_absent(name: str) -> bool:
    """Whether module ``name`` is not in this checkout at all, as opposed to present but failing to import.

    Doctor and setup skip what a package still being built in parallel has not delivered; a module that is here but
    cannot be imported (a missing dependency, a bug) is an error, never a skip.
    """
    try:
        return importlib.util.find_spec(name) is None
    except ModuleNotFoundError as e:  # a parent package is missing, or a dependency of one
        missing = e.name or ""
        return bool(missing) and (name == missing or name.startswith(missing + "."))
    except (ImportError, ValueError):
        return False


def _version_tuple(text: str) -> tuple[int, ...]:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not m:
        return ()
    return tuple(int(g) for g in m.groups() if g is not None)


# ---------------------------------------------------------------------------------------------------------- python


def check_python(version: Sequence[int] | None = None, executable: str | None = None, bits: int | None = None) -> Check:
    """Python 3.12 or later, 64-bit."""
    v = tuple(version if version is not None else sys.version_info[:3])
    exe = executable or sys.executable
    bits = bits or struct.calcsize("P") * 8
    shown = ".".join(str(x) for x in v)
    if v[:2] < PYTHON_MIN:
        return Check(
            "python",
            "fail",
            f"Python {shown} is too old; the hub needs 3.12 or later ({exe})",
            "Install Python 3.12 from python.org, then run crhub setup again.",
        )
    if bits != 64:
        return Check(
            "python",
            "fail",
            f"Python {shown} is {bits}-bit; the locked packages are 64-bit ({exe})",
            "Install the 64-bit Python 3.12 from python.org, then run crhub setup again.",
        )
    note = "" if v[:2] == PYTHON_MIN else " (.python-version pins 3.12; this works too)"
    return Check("python", "ok", f"{shown}, 64-bit, {exe}{note}")


_LOCK_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)==([^\s;]+)\s*(?:;\s*(.+))?$")
_REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.\-]*)")


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _marker_applies(marker: str | None) -> bool | None:
    """Whether an environment marker holds here; ``None`` when it cannot be evaluated (no ``packaging``)."""
    if not marker:
        return True
    try:
        from packaging.markers import Marker
    except ImportError:
        return None
    try:
        return bool(Marker(marker).evaluate())
    except Exception:
        return None


def locked_packages(lock: Path) -> dict[str, tuple[str, str]]:
    """``{normalised name: (name, version)}`` of the packages ``requirements.lock`` pins for this machine."""
    out: dict[str, tuple[str, str]] = {}
    with open(lock, encoding="utf-8-sig") as f:
        for raw in f:
            m = _LOCK_LINE.match(raw.strip())
            if not m:
                continue
            name, version, marker = m.groups()
            if _marker_applies(marker) is not True:  # a marker that cannot be read here is left out
                continue
            out[_norm(name)] = (name, version)
    return out


def runtime_dependencies(pyproject: Path) -> set[str]:
    """The normalised names of ``[project] dependencies`` in ``pyproject.toml``."""
    with open(pyproject, "rb") as f:
        doc = tomllib.load(f)
    names = set()
    for req in doc.get("project", {}).get("dependencies", []):
        m = _REQ_NAME.match(req)
        if m:
            names.add(_norm(m.group(1)))
    return names


def check_packages(repo: Path, version_of: Callable[[str], str | None] | None = None) -> Check:
    """The installed packages against ``requirements.lock``."""

    def _installed(name: str) -> str | None:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return None

    version_of = version_of or _installed
    lock = repo / "requirements.lock"
    if not lock.is_file():
        return Check("packages", "warn", "requirements.lock not found", "Restore it with git checkout.")
    try:
        pinned = locked_packages(lock)
        runtime = runtime_dependencies(repo / "pyproject.toml") if (repo / "pyproject.toml").is_file() else set()
    except (OSError, ValueError) as e:
        return Check("packages", "warn", f"cannot read the lock or pyproject.toml: {e}")
    missing: list[str] = []
    differ: list[str] = []
    for _key, (name, want) in sorted(pinned.items()):
        have = version_of(name)
        if have is None:
            missing.append(name)
        elif have != want:
            differ.append(f"{name} {have} (locked {want})")
    hard = [n for n in missing if _norm(n) in runtime]
    hint = "Run crhub setup (uv sync --locked --inexact, or pip install -r requirements.lock -e .)."
    if hard:
        return Check("packages", "fail", f"missing runtime packages: {', '.join(hard)}", hint)
    if missing or differ:
        parts = []
        if missing:
            parts.append(f"{len(missing)} missing ({', '.join(missing[:4])}{', ...' if len(missing) > 4 else ''})")
        if differ:
            parts.append(f"{len(differ)} differ ({', '.join(differ[:3])}{', ...' if len(differ) > 3 else ''})")
        return Check("packages", "warn", f"{len(pinned)} locked; " + "; ".join(parts), hint)
    return Check("packages", "ok", f"{len(pinned)} packages at their requirements.lock versions")


def check_uv(runner: Runner) -> Check:
    """Whether uv is installed. Information only: without it the launchers use ``.venv``."""
    uv = shutil.which("uv")
    if not uv:
        return Check("uv", "info", "not installed; crhub uses .venv and pip with requirements.lock")
    code, out = runner([uv, "--version"])
    return Check("uv", "info", _first_line(out) if code == 0 else f"{uv} did not run: {_first_line(out)}")


# ---------------------------------------------------------------------------------------------------------- sqlite


def check_sqlite(connect: Callable[[str], sqlite3.Connection] = sqlite3.connect) -> list[Check]:
    """The SQLite build: version, JSON and window functions, then the R-tree module (its own row)."""
    version = sqlite3.sqlite_version
    vt = _version_tuple(version)
    rows: list[Check] = []
    con = connect(":memory:")
    try:
        missing = []
        try:
            con.execute("SELECT json_extract('{\"a\": 1}', '$.a'), (SELECT count(*) FROM json_each('[1, 2]'))")
        except sqlite3.Error:
            missing.append("JSON functions")
        try:
            con.execute("SELECT row_number() OVER (ORDER BY x) FROM (SELECT 1 AS x)")
        except sqlite3.Error:
            missing.append("window functions")
        if vt < SQLITE_MIN or missing:
            why = f"SQLite {version}" + (f" lacks {' and '.join(missing)}" if missing else " is older than 3.38")
            rows.append(
                Check("sqlite", "fail", why, "Install Python 3.12 from python.org; its SQLite has everything needed.")
            )
        else:
            rows.append(Check("sqlite", "ok", f"SQLite {version}, JSON and window functions"))
        try:
            con.execute("CREATE VIRTUAL TABLE temp.doctor_rtree USING rtree(id, x0, x1, y0, y1)")
            con.execute("INSERT INTO temp.doctor_rtree VALUES (1, 0, 10, 0, 10)")
            hit = con.execute("SELECT id FROM temp.doctor_rtree WHERE x0 <= 5 AND x1 >= 5").fetchall()
            if hit != [(1,)]:
                raise sqlite3.OperationalError(f"a test query returned {hit}")
            rows.append(Check("rtree", "ok", f"R-tree module works in SQLite {version}"))
        except sqlite3.Error as e:
            rows.append(
                Check(
                    "rtree",
                    "fail",
                    f"SQLite {version} has no working R-tree module: {e}",
                    "The store's spatial index needs it. Use the python.org build of Python 3.12, whose SQLite "
                    "includes R-tree.",
                )
            )
    finally:
        con.close()
    return rows


# ------------------------------------------------------------------------------------------------------------ node

TS_PROBE = "const n: number = 1; console.log('ts ' + n + ' ' + String(process.features.typescript))"


def find_node(cfg: Mapping[str, Any]) -> str | None:
    """The Node executable from ``engine.node`` (a name on PATH or a path), or None."""
    name = str((cfg.get("engine") or {}).get("node") or "node")
    found = shutil.which(name)
    if found:
        return found
    p = Path(os.path.expandvars(os.path.expanduser(name)))
    return str(p) if p.is_file() else None


def check_node(cfg: Mapping[str, Any], runner: Runner) -> Check:
    """Node at least ``engine.node_min`` (22.18), and it runs TypeScript by stripping types."""
    engine = cfg.get("engine") or {}
    want = str(engine.get("node_min") or NODE_MIN_DEFAULT)
    hint = (
        f"Install Node 24 LTS (or 22.18 or later) from nodejs.org, or set engine.node in configs/local.json to "
        f"node.exe's path. The engine needs Node {want}+."
    )
    node = find_node(cfg)
    if not node:
        return Check("node", "fail", f"Node not found (engine.node is {engine.get('node') or 'node'!r})", hint)
    code, out = runner([node, "--version"])
    shown = _first_line(out)
    if code != 0:
        return Check("node", "fail", f"{node} --version failed: {shown}", hint)
    have = _version_tuple(shown)
    if not have or have[:2] < _version_tuple(want)[:2]:
        return Check("node", "fail", f"Node {shown} is older than {want} ({node})", hint)
    code, out = runner([node, "--input-type=module-typescript", "-e", TS_PROBE])
    probe = _first_line(out)
    if code != 0 or not probe.startswith("ts 1"):
        return Check(
            "node",
            "fail",
            f"Node {shown} did not strip TypeScript types: {probe or 'no output'}",
            "Node 22.18 or later strips types by default; check NODE_OPTIONS does not turn it off. " + hint,
        )
    mode = probe.split(" ", 2)[2] if probe.count(" ") >= 2 else ""
    how = " (transform mode)" if mode == "transform" else ""
    note = ", 24 LTS recommended" if have[0] < 24 else ""
    return Check("node", "ok", f"Node {shown}, strips TypeScript types{how}{note}, {node}")


# ------------------------------------------------------------------------------------------------------------- npm


def _read_json(path: Path) -> Any:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def check_npm(repo: Path, runner: Runner) -> Check:
    """``node_modules`` from ``npm ci``: workspaces linked to this repo, packages at their locked versions."""
    hint = "Run npm ci in the repo (crhub setup runs it). Close the old hub's and the new hub's Node processes first."
    nm = repo / "node_modules"
    if not nm.is_dir():
        return Check("npm", "fail", "node_modules is missing: npm ci has not run", hint)
    try:
        root_pkg = _read_json(repo / "package.json")
        lock = _read_json(repo / "package-lock.json")
    except (OSError, ValueError) as e:
        return Check("npm", "fail", f"cannot read package.json or package-lock.json: {e}", "Restore them with git.")
    problems: list[str] = []
    linked: list[str] = []
    for ws in root_pkg.get("workspaces") or []:
        try:
            name = _read_json(repo / ws / "package.json")["name"]
        except (OSError, ValueError, KeyError):
            problems.append(f"workspace {ws} has no package.json")
            continue
        link = nm.joinpath(*name.split("/"))
        if not link.exists():
            problems.append(f"{name} is not linked")
            continue
        if os.path.normcase(os.path.realpath(link)) != os.path.normcase(os.path.realpath(repo / ws)):
            problems.append(f"{name} points to {os.path.realpath(link)}, not this repo")
            continue
        linked.append(ws)
    if problems:
        return Check("npm", "fail", "workspaces: " + "; ".join(problems), hint)
    hidden = nm / ".package-lock.json"
    if not hidden.is_file():
        return Check("npm", "warn", "node_modules has no .package-lock.json, so it cannot be compared", hint)
    try:
        have = _read_json(hidden).get("packages") or {}
    except (OSError, ValueError) as e:
        return Check("npm", "warn", f"node_modules/.package-lock.json is unreadable: {e}", hint)
    want = lock.get("packages") or {}
    missing: list[str] = []
    differ: list[str] = []
    total = 0
    for key, entry in want.items():
        if not key.startswith("node_modules/") or entry.get("link"):
            continue
        got = have.get(key)
        if got is None:
            if not entry.get("optional"):  # optional packages exist only on their own platform
                missing.append(key.removeprefix("node_modules/"))
            continue
        total += 1
        if got.get("version") != entry.get("version"):
            differ.append(f"{key.removeprefix('node_modules/')} {got.get('version')} (locked {entry.get('version')})")
    npm = shutil.which("npm")
    npm_v = ""
    if npm:
        code, out = runner([npm, "--version"])
        npm_v = f"npm {_first_line(out)}, " if code == 0 else ""
    if missing or differ:
        parts = []
        if missing:
            parts.append(f"{len(missing)} missing ({', '.join(missing[:3])}{', ...' if len(missing) > 3 else ''})")
        if differ:
            parts.append(f"{len(differ)} differ ({', '.join(differ[:2])}{', ...' if len(differ) > 2 else ''})")
        return Check("npm", "warn", "node_modules is stale: " + "; ".join(parts), hint)
    matches = f"{total} package matches" if total == 1 else f"{total} packages match"
    detail = f"{npm_v}workspaces {' and '.join(linked)} linked, {matches} package-lock.json"
    if not npm:
        return Check(
            "npm", "warn", detail + "; npm itself is not on PATH", "crhub setup needs npm; it comes with Node."
        )
    return Check("npm", "ok", detail)


# ------------------------------------------------------------------------------------------------------------- var

# Marker files a sync client leaves in the root of the folder it syncs.
SYNC_MARKERS: tuple[tuple[str, str], ...] = (
    (".849C9593-D756-4E56-8D6E-42412F2A707B", "OneDrive"),
    (".dropbox", "Dropbox"),
    (".dropbox.cache", "Dropbox"),
    (".tmp.drivedownload", "Google Drive"),
    (".tmp.driveupload", "Google Drive"),
)
# Markers that count only as files. On Linux and macOS the Dropbox client keeps its settings in the folder
# ~/.dropbox, so a .dropbox folder marks the home folder, not a synced root; the synced root holds a .dropbox file.
_FILE_MARKERS = frozenset({".dropbox"})
ONEDRIVE_ENV = ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")
# Windows file attributes of folders managed by a cloud sync client (the Cloud Files API).
_FILE_ATTRIBUTE_OFFLINE = 0x00001000
_FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
_FILE_ATTRIBUTE_PINNED = 0x00080000
_FILE_ATTRIBUTE_UNPINNED = 0x00100000
_FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
_CLOUD_ATTRIBUTES = (
    _FILE_ATTRIBUTE_OFFLINE
    | _FILE_ATTRIBUTE_RECALL_ON_OPEN
    | _FILE_ATTRIBUTE_PINNED
    | _FILE_ATTRIBUTE_UNPINNED
    | _FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
)
_IO_REPARSE_TAG_CLOUD = 0x9000001A
_IO_REPARSE_TAG_CLOUD_MASK = 0xFFFF0FFF
_NETWORK_FS = frozenset({"nfs", "nfs4", "cifs", "smb3", "smbfs", "fuse.sshfs", "sshfs", "afpfs", "webdav"})


def _folder_name_sync(part: str) -> str | None:
    """The sync client a folder name belongs to, or None."""
    low = part.casefold()
    if low.startswith("onedrive"):  # OneDrive, "OneDrive - Contoso", macOS "OneDrive-Personal"
        return "OneDrive"
    if low == "dropbox" or low.startswith("dropbox (") or low.startswith("dropbox-"):
        return "Dropbox"
    if low in {"my drive", "shared drives", "google drive", "googledrive"} or low.startswith("googledrive-"):
        return "Google Drive"
    if low in {"icloud drive", "iclouddrive", "mobile documents", "com~apple~clouddocs"}:
        return "iCloud Drive"
    if low == "cloudstorage":  # macOS ~/Library/CloudStorage holds every File Provider sync root
        return "a macOS cloud storage provider"
    return None


def _under(path: str, root: str) -> bool:
    try:
        common = os.path.commonpath([os.path.normcase(path), os.path.normcase(root)])
    except ValueError:  # different drives
        return False
    return common == os.path.normcase(os.path.normpath(root))


def _dropbox_roots(env: Mapping[str, str]) -> list[str]:
    """The folders the Dropbox client says it syncs (``info.json`` under APPDATA or LOCALAPPDATA, or ~/.dropbox)."""
    places = [Path(env[k]) / "Dropbox" / "info.json" for k in ("APPDATA", "LOCALAPPDATA") if env.get(k)]
    home = env.get("HOME") or env.get("USERPROFILE")
    if home:
        places.append(Path(home) / ".dropbox" / "info.json")
    roots: list[str] = []
    for p in places:
        try:
            doc = _read_json(p)
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict):
            for acct in doc.values():
                if isinstance(acct, dict) and acct.get("path"):
                    roots.append(str(acct["path"]))
    return roots


def _windows_cloud_marks(folder: Path) -> bool:
    try:
        st = os.lstat(folder)
    except OSError:
        return False
    attrs = getattr(st, "st_file_attributes", 0) or 0
    tag = getattr(st, "st_reparse_tag", 0) or 0
    return bool(attrs & _CLOUD_ATTRIBUTES) or (tag & _IO_REPARSE_TAG_CLOUD_MASK) == _IO_REPARSE_TAG_CLOUD


def synced_folder(path: str | os.PathLike[str], env: Mapping[str, str] | None = None) -> str | None:
    """Why ``path`` is inside a folder a sync client manages, or None when it is not.

    Looks at the path as given and as resolved: the OneDrive environment variables, the Dropbox client's own list,
    the folder names the clients use (OneDrive, Dropbox, My Drive, iCloudDrive, Mobile Documents, CloudStorage), the
    marker files they leave in the root they sync, and on Windows the cloud-file attributes and reparse tags.
    """
    env = os.environ if env is None else env
    given = os.path.abspath(os.fspath(path))
    forms = [given]
    resolved = os.path.realpath(given)
    if os.path.normcase(resolved) != os.path.normcase(given):
        forms.append(resolved)
    roots = [(f"%{k}%", env[k]) for k in ONEDRIVE_ENV if env.get(k)]
    roots += [("the Dropbox folder", r) for r in _dropbox_roots(env)]
    for form in forms:
        for label, root in roots:
            if _under(form, root):
                return f"it is inside {label} ({root})"
        for part in Path(form).parts:
            client = _folder_name_sync(part)
            if client:
                return f"it is inside a folder named {part!r} ({client})"
        folder = Path(form)
        for anc in (folder, *folder.parents):
            if not anc.is_dir():
                continue
            for marker, client in SYNC_MARKERS:
                mark = anc / marker
                if mark.is_file() if marker in _FILE_MARKERS else mark.exists():
                    return f"{anc} holds {marker}, the mark of {client}'s synced folder"
            if sys.platform == "win32" and _windows_cloud_marks(anc):
                return f"Windows marks {anc} as a cloud-synced folder (OneDrive, Dropbox, iCloud or Google Drive)"
    return None


def windows_unc(path: str) -> tuple[bool, str]:
    """``(is a UNC path, the path with any ``\\\\?\\`` or ``\\\\.\\`` device prefix removed)`` for a Windows path.

    ``\\\\server\\share`` and ``\\\\?\\UNC\\server\\share`` are network paths; ``\\\\?\\C:\\...`` is an extended-length
    local path, not a share.
    """
    p = path.replace("/", "\\")
    if p.startswith(("\\\\?\\", "\\\\.\\")):
        rest = p[4:]
        if rest[:4].upper() == "UNC\\":
            return True, "\\\\" + rest[4:]
        return False, rest
    return p.startswith("\\\\"), p


def network_folder(path: str | os.PathLike[str]) -> str | None:
    """Why ``path`` is on a network share (where SQLite's WAL is unsafe), or None."""
    p = os.path.abspath(os.fspath(path))
    if sys.platform == "win32":
        unc, p = windows_unc(p)
        if unc:
            return "it is a UNC network path"
        try:
            import ctypes

            drive = os.path.splitdrive(p)[0]
            if drive and ctypes.windll.kernel32.GetDriveTypeW(drive + "\\") == 4:  # DRIVE_REMOTE
                return f"drive {drive} is a network drive"
        except (OSError, AttributeError, ValueError):
            return None
        return None
    try:
        with open("/proc/self/mounts", encoding="utf-8") as f:
            mounts = [line.split()[:3] for line in f if line.strip()]
    except OSError:
        return None
    best = ("", "")
    real = os.path.realpath(p)
    for fields in mounts:
        if len(fields) < 3:
            continue
        point = fields[1].replace("\\040", " ")
        if _under(real, point) and len(point) > len(best[0]):
            best = (point, fields[2])
    if best[1] in _NETWORK_FS:
        return f"it is on a {best[1]} network mount ({best[0]})"
    return None


def _nearest_existing(path: Path) -> Path:
    for anc in (path, *path.parents):
        if anc.exists():
            return anc
    return path


def check_var(cfg: Mapping[str, Any], env: Mapping[str, str] | None = None) -> list[Check]:
    """``var`` not synced and not on a network share; then a probe write and the free space."""
    from region.core import fsio, paths

    var, origin = paths.describe_var(cfg)
    where = f"{var} ({origin})"
    move = (
        'Set "var" in configs/local.json (or the CRHUB_VAR environment variable) to a local folder that is not '
        "synced, such as %LOCALAPPDATA%\\CincinnatiRail\\hub on Windows (the default)."
    )
    synced = synced_folder(var, env)
    if synced:
        return [
            Check(
                "var", "fail", f"{where} is in a synced folder: {synced}", "SQLite breaks under sync clients. " + move
            ),
            Check("var write", "skip", "not tried: var is in a synced folder"),
        ]
    remote = network_folder(var)
    if remote:
        return [
            Check(
                "var", "fail", f"{where} is on a network share: {remote}", "SQLite's WAL needs a local disk. " + move
            ),
            Check("var write", "skip", "not tried: var is on a network share"),
        ]
    rows = [Check("var", "ok", f"{where}, not in a synced folder")]
    probe = var / f".doctor-probe-{os.getpid()}"
    created = [anc for anc in (var, *var.parents) if not anc.exists()]  # removed again after the probe
    try:
        try:
            fsio.write_atomic(probe, b"doctor\n")
            probe.unlink()
        finally:
            for folder in created:  # deepest first
                try:
                    folder.rmdir()
                except OSError:
                    break
    except fsio.WriteRefused as e:
        rows.append(Check("var write", "fail", f"the write guard refused var: {e}", move))
        return rows
    except OSError as e:
        rows.append(
            Check("var write", "fail", f"cannot write in {var}: {e}", "Check the folder's permissions. " + move)
        )
        return rows
    try:
        free = shutil.disk_usage(_nearest_existing(var)).free
    except OSError:
        free = None
    if free is not None and free < FREE_SPACE_WARN:
        rows.append(
            Check(
                "var write",
                "warn",
                f"writable, but only {free / 1024**3:.1f} GB free",
                "Free some space: backups and the cache grow.",
            )
        )
    else:
        rows.append(Check("var write", "ok", "writable" + (f", {free / 1024**3:.0f} GB free" if free else "")))
    return rows


def check_repo(repo: Path, env: Mapping[str, str] | None = None) -> Check:
    """A warning when the repo is in a synced folder (git and sync clients fight over ``.git``)."""
    synced = synced_folder(repo, env)
    if synced:
        return Check(
            "repo",
            "warn",
            f"{repo} is in a synced folder: {synced}",
            "The hub keeps its databases in var, not here, but sync clients can damage .git and node_modules. "
            "Consider a clone outside the synced folder.",
        )
    return Check("repo", "ok", f"{repo}, not in a synced folder")


# ----------------------------------------------------------------------------------------------------------- ports


def _http_json(url: str) -> Any:
    """GET ``url`` without any proxy; the parsed JSON body, or None.

    A program that is not an HTTP server (it sends a banner, or garbage) makes ``http.client`` raise
    ``HTTPException``, which urllib does not wrap; that is an answer of "not a hub" too, never a crash.
    """
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=HTTP_TIMEOUT_S) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read(1 << 20).decode("utf-8", "replace"))
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
        return None


def identify(host: str, port: int) -> str | None:
    """``"hub"`` (answers ``/api/v1/health``), ``"old hub"`` (answers ``/api/runs``) or None."""
    base = f"http://{host if ':' not in host else '[' + host + ']'}:{port}"
    if _http_json(base + "/api/v1/health") is not None:
        return "hub"
    runs = _http_json(base + "/api/runs")
    if isinstance(runs, dict) and "runs" in runs:
        return "old hub"
    return None


def listening(host: str, port: int) -> bool:
    """Whether something accepts TCP connections on ``host:port``."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def bind_error(host: str, port: int) -> str | None:
    """Why ``host:port`` cannot be bound now (None when it can), using the options uvicorn uses."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    s = socket.socket(family, socket.SOCK_STREAM)
    try:
        if sys.platform == "win32":
            s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", -5), 1)
        else:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
    except OSError as e:
        if getattr(e, "winerror", None) == 10013:
            return "Windows reserves it (see: netsh interface ipv4 show excludedportrange protocol=tcp)"
        return str(e)
    finally:
        s.close()
    return None


def lock_holder(cfg: Mapping[str, Any]) -> Any:
    """The process holding ``var/hub.lock`` (``region.core.lock.Holder``), or None: no holder, or no lock to read."""
    from region.core import lock, paths

    try:
        return lock.reader(paths.var_root(cfg))
    except Exception:  # an unreadable var is check_var's to report
        return None


def check_hub_port(cfg: Mapping[str, Any]) -> Check | list[Check]:
    """The new hub's port is free, or this hub is already serving on it.

    The lock in ``var`` is asked first (``region.core.lock.reader``): it names the serving hub even on another port
    or while it is too busy to answer. HTTP (``/api/v1/health`` on the configured port) is the second check, for a
    hub serving from another ``var``. A command that holds the lock without serving (``crhub jobs run``, ``crhub
    restore``) is reported beside the port row, as information.
    """
    host = str(cfg.get("host") or "127.0.0.1")
    port = int(cfg.get("port") or 8766)
    name = f"port {port}"
    other = f'Stop the program using it, or set "port" in configs/local.json to a free port (the hub uses {port}).'
    holder = lock_holder(cfg)
    if holder is not None and holder.command.startswith("crhub serve") and holder.port:
        return Check(name, "ok", f"the hub is serving at http://{host}:{holder.port}: {holder.describe()}")
    rows = [Check("hub lock", "info", f"{holder.describe()} holds var/hub.lock")] if holder is not None else []
    rows.append(_hub_port_by_http(host, port, name, other))
    return rows if len(rows) > 1 else rows[0]


def _hub_port_by_http(host: str, port: int, name: str, other: str) -> Check:
    if listening(host, port):
        who = identify(host, port)
        if who == "hub":
            return Check(name, "ok", f"the hub is serving at http://{host}:{port}")
        if who == "old hub":
            return Check(
                name,
                "fail",
                f"the old hub is running on {port}, the new hub's port",
                "Start the old hub on its own port 8765 (python hub\\hub.py), or move the new hub's port.",
            )
        return Check(name, "fail", f"{host}:{port} is in use by another program", other)
    err = bind_error(host, port)
    if err:
        return Check(name, "fail", f"{host}:{port} cannot be used: {err}", other)
    return Check(name, "ok", f"{host}:{port} is free for the hub")


def check_old_hub_port(cfg: Mapping[str, Any]) -> Check | None:
    """Information only: whether the old hub (``old_hub`` in the config, 8765) is running beside the new one."""
    url = cfg.get("old_hub")
    if not url:
        return None
    u = urllib.parse.urlsplit(str(url))
    host, port = u.hostname or "127.0.0.1", u.port or 8765
    name = f"port {port}"
    if int(cfg.get("port") or 8766) == port:
        return Check(
            name,
            "warn",
            f"the old hub and the new hub are both set to port {port}",
            'Set "port" in configs/local.json to 8766.',
        )
    if listening(host, port):
        who = identify(host, port)
        if who == "old hub":
            return Check(name, "info", f"the old hub is running at {url}")
        if who == "hub":
            return Check(
                name,
                "warn",
                f"a new hub is serving on {port}, the old hub's port",
                "The old hub (python hub\\hub.py) uses 8765; the new hub belongs on 8766.",
            )
        return Check(name, "info", f"{host}:{port} is in use, not by the old hub")
    return Check(name, "info", f"{host}:{port} is free (the old hub is not running)")


# ----------------------------------------------------------------------------------------------------------- tiers


def check_tiers(cfg: Mapping[str, Any]) -> list[Check]:
    """One row per data tier of ``configs/hub_paths.json`` (``region.tiers``)."""
    from region import tiers

    rows: list[Check] = []
    for r in tiers.scan(cfg).values():
        name = f"tier {r.name}"
        if r.status == "present":
            rows.append(Check(name, "ok", f"present: {r.detail}"))
            continue
        detail = f"{r.status}: {r.detail}"
        if r.handshake and r.handshake.get("updated"):
            detail += f" ({r.handshake['file']} updated {str(r.handshake['updated'])[:10]})"
        if r.status == "partial":
            rows.append(
                Check(
                    name,
                    "warn" if r.required else "info",
                    detail,
                    "Lane B has not finished this tier; the hub shows it as partial." if r.required else "",
                )
            )
        elif r.required:
            rows.append(
                Check(
                    name,
                    "fail",
                    detail,
                    f"The hub needs this tier. Restore {r.root} (it is in git), or set "
                    f"tiers.{r.name}.root in configs/local.json.",
                )
            )
        else:
            rows.append(
                Check(
                    name,
                    "warn",
                    detail,
                    f"Optional: layers that read it say so. Set tiers.{r.name}.root "
                    "in configs/local.json if it lives elsewhere.",
                )
            )
    return rows


def check_sources(cfg: Mapping[str, Any] | None = None) -> list[Check]:
    """The files each feature's ``SOURCES`` names (features are WP5's; none may exist yet), resolved in ``cfg``."""
    from region.core import features, paths
    from region.core.errors import HubError

    rows: list[Check] = []
    try:
        found = features.discover()
    except HubError as e:
        return [Check("features", "warn", f"feature discovery failed: {e}")]
    for f in found:
        if not f.has("sources"):
            continue
        try:
            sources = f.sources()
        except Exception as e:
            rows.append(Check(f"sources {f.name}", "warn", f"sources.py failed to load: {type(e).__name__}: {e}"))
            continue
        missing = []
        for name, uri in sources.items():
            try:
                if not paths.resolve(uri, cfg).exists():
                    missing.append(name)
            except HubError:
                missing.append(name)
        if missing:
            rows.append(
                Check(
                    f"sources {f.name}",
                    "warn",
                    f"{len(missing)} of {len(sources)} missing: {', '.join(missing[:4])}",
                    "See the tier rows above for the folders they live in.",
                )
            )
        else:
            rows.append(Check(f"sources {f.name}", "ok", f"{len(sources)} files present"))
    return rows


# ------------------------------------------------------------------------------------------------------------- app


def _newest(paths_: Sequence[Path]) -> tuple[Path | None, float]:
    best: tuple[Path | None, float] = (None, 0.0)
    for p in paths_:
        if p.is_file():
            files = [p]
        elif p.is_dir():
            files = [q for q in p.rglob("*") if q.is_file()]
        else:
            continue
        for q in files:
            try:
                m = q.stat().st_mtime
            except OSError:
                continue
            if m > best[1]:
                best = (q, m)
    return best


def app_build(repo: Path) -> dict[str, Any]:
    """The state of the app build, for doctor and for serve's banner.

    ``{"source": bool, "built": bool, "built_at": float | None, "newest": str | None, "newest_at": float | None,
    "stale": bool}``: ``source`` is whether ``app/src`` exists, ``built`` whether ``app/dist/index.html`` does,
    ``newest`` the newest source file (repo-relative, POSIX) and ``stale`` whether it is newer than the build.
    """
    src = (repo / "app" / "src").is_dir()
    index = repo / "app" / "dist" / "index.html"
    built_at = index.stat().st_mtime if index.is_file() else None
    newest, newest_at = _newest([repo / p for p in APP_SOURCES]) if src else (None, 0.0)
    rel = newest.relative_to(repo).as_posix() if newest else None
    stale = bool(built_at is not None and newest is not None and newest_at > built_at + 1.0)
    return {
        "source": src,
        "built": built_at is not None,
        "built_at": built_at,
        "newest": rel,
        "newest_at": newest_at if newest else None,
        "stale": stale,
    }


def _when(t: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t))


def check_app(repo: Path) -> Check:
    """``app/dist`` built, and not older than its source."""
    state = app_build(repo)
    hint = "Run npm run build -w app (crhub setup runs it)."
    if not state["source"]:
        return Check("app", "skip", "app/src does not exist yet, so there is nothing to build")
    if not state["built"]:
        return Check("app", "fail", "app/dist is not built, so the hub has no pages to serve", hint)
    if state["stale"]:
        return Check(
            "app",
            "warn",
            f"app/dist (built {_when(state['built_at'])}) is older than {state['newest']} "
            f"(changed {_when(state['newest_at'])})",
            hint + " Until then serve shows a banner.",
        )
    return Check("app", "ok", f"app/dist built {_when(state['built_at'])}, not older than its source")


# -------------------------------------------------------------------------------------------------------- database


def check_database(cfg: Mapping[str, Any], *, data: bool = False) -> list[Check]:
    """``var/region.db``: ``quick_check``, the schema version and pending migrations; with ``data``, every record."""
    from region.core import paths

    db = paths.var_path("region.db", cfg=cfg)
    try:
        from region.model import backup as model_backup
        from region.model import migrate as model_migrate
    except Exception as e:
        why = f"{type(e).__name__}: {e}"
        if module_absent("region.model.migrate"):  # the store is not in this checkout yet
            return [Check("database", "skip", f"region.model is not here yet, so {db} is not checked ({why})")]
        return [
            Check(
                "database",
                "fail",
                f"the store (region.model) cannot be loaded, so the hub cannot open {db}: {why}",
                "Run crhub setup. If this row stays, copy it into a session: it is a bug.",
            )
        ]
    if not db.is_file():
        return [Check("database", "info", f"no database yet at {db}; crhub setup creates it")]
    problems = model_backup.quick_check(db)
    if problems:
        return [
            Check(
                "database",
                "fail",
                f"{db} fails quick_check: {'; '.join(problems[:3])}",
                "Stop the hub, then restore the newest backup: crhub model restore <file in var/backups>.",
            )
        ]
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        version = model_migrate.current_version(con)
        todo = model_migrate.pending(con)
    except sqlite3.Error as e:
        return [
            Check(
                "database",
                "fail",
                f"{db} cannot be read: {e}",
                "Stop the hub, then restore a backup with crhub model restore <file>.",
            )
        ]
    finally:
        con.close()
    rows = []
    if todo:
        rows.append(
            Check(
                "database",
                "warn",
                f"{db}: schema {version}, {len(todo)} migration(s) pending ({', '.join(str(m.version) for m in todo)})",
                "crhub serve (or crhub setup) backs the database up, then migrates.",
            )
        )
        if data:
            rows.append(
                Check(
                    "records",
                    "skip",
                    "not validated while a migration is pending (doctor never migrates); run crhub setup first",
                )
            )
        return rows
    rows.append(Check("database", "ok", f"{db}: quick_check ok, schema {version}"))
    if data:
        rows.append(_check_records(db, cfg))
    return rows


def _check_records(db: Path, cfg: Mapping[str, Any]) -> Check:
    """Every record validated again, on the live file opened read-only (``open_store(readonly=True)``).

    A read-only store never migrates, backs up or rewrites the kind table, and takes no write lock, so doctor can
    read the file a running hub holds (WAL lets readers in beside the writer). Only serve and setup migrate, after
    their own backup; ``check_database`` skips this row while a migration is pending.
    """
    try:
        from region.model import open_store

        with open_store(db, readonly=True) as store:
            problems = store.check_data()
    except Exception as e:
        return Check("records", "warn", f"could not validate the records: {type(e).__name__}: {e}")
    if problems:
        first = problems[0]
        return Check(
            "records",
            "fail",
            f"{len(problems)} record problem(s); first: {first.get('layer')} {first.get('kind')} {first.get('id')}: "
            f"{first.get('message')}",
            "crhub model check lists them all.",
        )
    return Check("records", "ok", "every record passes its kind's validation")


# --------------------------------------------------------------------------------------------------------- the run


def run_checks(
    cfg: Mapping[str, Any] | None = None,
    *,
    data: bool = False,
    runner: Runner | None = None,
    env: Mapping[str, str] | None = None,
) -> list[Check]:
    """Every check, in order. ``cfg`` defaults to the merged config; ``runner`` runs processes (tests pass a fake)."""
    from region.core import paths
    from region.core.errors import HubError

    runner = runner or run_process
    rows: list[Check] = []
    if cfg is None:
        try:
            cfg = paths.config()
        except (HubError, OSError, ValueError) as e:
            rows.append(Check("configs", "fail", f"the config cannot be read: {e}", "Fix configs/local.json."))
            cfg = {"_repo": str(paths.repo_root()), "tiers": {}}
    repo = Path(cfg.get("_repo") or paths.repo_root())

    def guarded(name: str, fn: Callable[[], Any]) -> None:
        try:
            out = fn()
        except Exception as e:  # one broken check never hides the others
            rows.append(Check(name, "fail", f"the check itself failed: {type(e).__name__}: {e}"))
            return
        if out is None:
            return
        rows.extend(out if isinstance(out, list) else [out])

    guarded("python", check_python)
    guarded("packages", lambda: check_packages(repo))
    guarded("uv", lambda: check_uv(runner))
    guarded("sqlite", check_sqlite)
    guarded("node", lambda: check_node(cfg, runner))
    guarded("npm", lambda: check_npm(repo, runner))
    guarded("var", lambda: check_var(cfg, env))
    guarded("repo", lambda: check_repo(repo, env))
    guarded("port", lambda: check_hub_port(cfg))
    guarded("port", lambda: check_old_hub_port(cfg))
    guarded("tiers", lambda: check_tiers(cfg))
    guarded("sources", lambda: check_sources(cfg))
    guarded("app", lambda: check_app(repo))
    guarded("database", lambda: check_database(cfg, data=data))
    return rows


def failed(checks: Sequence[Check]) -> bool:
    """Whether any check failed (doctor's exit code is 1 then)."""
    return any(c.status == "fail" for c in checks)


def exit_code(checks: Sequence[Check]) -> int:
    return 1 if failed(checks) else 0


def render(checks: Sequence[Check], *, header: str | None = None) -> str:
    """The short table doctor prints."""
    width = max([len(c.name) for c in checks] + [8])
    lines = [header] if header else []
    for c in checks:
        lines.append(f"  {LABELS[c.status]:5} {c.name:{width}}  {c.detail}")
        if c.hint and c.status in ("warn", "fail"):
            lines.append(f"  {'':5} {'':{width}}  -> {c.hint}")
    n_fail = sum(c.status == "fail" for c in checks)
    n_warn = sum(c.status == "warn" for c in checks)
    n_ok = sum(c.status == "ok" for c in checks)
    verdict = "doctor found a problem the hub cannot run with" if n_fail else "the hub can run here"
    lines.append(f"{n_ok} ok, {n_warn} warning(s), {n_fail} failure(s): {verdict}")
    return "\n".join(lines)


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("doctor", help="check this machine, var, ports, tiers, the app build and the database")
    p.add_argument("--data", action="store_true", help="also validate every record of var/region.db again")
    p.add_argument("--json", action="store_true", help="print one JSON object")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    from region.core import paths

    checks = run_checks(data=bool(getattr(args, "data", False)))
    if getattr(args, "json", False):
        print(
            json.dumps(
                {"ok": not failed(checks), "checks": [c.as_dict() for c in checks]}, indent=1, ensure_ascii=False
            )
        )
    else:
        header = f"crhub doctor: {paths.repo_root()} on {platform.system()} {platform.release()}"
        print(render(checks, header=header))
    return exit_code(checks)


__all__ = [
    "APP_SOURCES",
    "Check",
    "Runner",
    "app_build",
    "bind_error",
    "check_app",
    "check_database",
    "check_hub_port",
    "check_node",
    "check_npm",
    "check_old_hub_port",
    "check_packages",
    "check_python",
    "check_repo",
    "check_sources",
    "check_sqlite",
    "check_tiers",
    "check_uv",
    "check_var",
    "exit_code",
    "failed",
    "find_node",
    "identify",
    "listening",
    "module_absent",
    "network_folder",
    "register",
    "render",
    "run",
    "run_checks",
    "run_process",
    "synced_folder",
    "windows_unc",
]
