"""The data tier scan (9.26): is each tier of ``configs/hub_paths.json`` missing, partial or present here, and why.

A tier is

- **missing** when its root is not on this machine (or its entry in the config cannot be read);
- **partial** when its root is here but its manifest or index is absent or unreadable, a file its index names is
  absent, its handshake file is absent or unreadable or does not say done, or the root is empty;
- **present** otherwise.

``region.core.paths`` only finds roots; this module looks inside them. The scan reads files and never writes, never
raises for one tier (a tier that cannot be scanned is reported with the reason), and is cheap enough to run on every
``GET /tiers``: a JSON index is parsed once per size and mtime.

Each check of a tier is a ``Finding``. The tier's ``detail`` is the short text of its failing findings (or of its
passing ones when it is present), the same text the ``tier`` event and the status chips carry, for example
``"stage contours"`` for the 1912 surface while lane B is still at the contour stage.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from region.core import paths
from region.core.errors import HubError
from region.core.events import TierEvent, TierStatus

STATUSES: tuple[TierStatus, ...] = ("missing", "partial", "present")

# GDAL VRT sources: <SourceFilename relativeToVRT="1">name.tif</SourceFilename>
_VRT_SOURCE_RE = re.compile(
    r"<SourceFilename(?P<attrs>[^>]*)>(?P<name>[^<]+)</SourceFilename>",
    re.IGNORECASE,
)
_RELATIVE_RE = re.compile(r"""relativeToVRT\s*=\s*["']1["']""", re.IGNORECASE)
_MAX_LISTED = 3


@dataclass(frozen=True)
class Finding:
    """One check of a tier: ``what`` is ``root``, ``manifest``, ``index`` or ``handshake``.

    ``file`` is the path in the tier the check read (POSIX, relative to the root), ``ok`` whether it passed, and
    ``detail`` one short plain phrase (``"MANIFEST.csv 119 rows"``, ``"stage contours"``).
    """

    what: str
    file: str | None
    ok: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"what": self.what, "file": self.file, "ok": self.ok, "detail": self.detail}


@dataclass(frozen=True)
class TierReport:
    """The scan of one tier. ``as_dict()`` is its JSON for ``GET /tiers``; ``event()`` its ``tier`` event."""

    name: str
    status: TierStatus
    detail: str
    root: str
    about: str = ""
    lane: str = "B"
    required: bool = False
    mount: bool = False
    findings: tuple[Finding, ...] = ()
    handshake: dict[str, Any] | None = None

    @property
    def uri(self) -> str:
        """``tier://<name>/``, the URI of the tier's root."""
        return f"tier://{self.name}/"

    def event(self) -> TierEvent:
        """The ``tier`` event payload of this report (section 5)."""
        return TierEvent(tier=self.name, status=self.status, detail=self.detail)

    def as_dict(self) -> dict[str, Any]:
        """The report as JSON: name, uri, status, detail, root, about, lane, required, mount, findings, handshake."""
        return {
            "name": self.name,
            "uri": self.uri,
            "status": self.status,
            "detail": self.detail,
            "root": self.root,
            "about": self.about,
            "lane": self.lane,
            "required": self.required,
            "mount": self.mount,
            "findings": [f.as_dict() for f in self.findings],
            "handshake": self.handshake,
        }


# ------------------------------------------------------------------------------------------------ cached parsing

_json_cache: dict[str, tuple[int, int, Any]] = {}
_json_lock = threading.Lock()


def _load_json(path: Path) -> Any:
    """``json`` of a file, parsed once per (size, mtime): a scan on every ``GET /tiers`` stays cheap."""
    st = path.stat()
    key = os.path.normcase(str(path))
    with _json_lock:
        hit = _json_cache.get(key)
    if hit is not None and hit[0] == st.st_size and hit[1] == st.st_mtime_ns:
        return hit[2]
    with open(path, encoding="utf-8-sig") as f:
        value = json.load(f)
    with _json_lock:
        _json_cache[key] = (st.st_size, st.st_mtime_ns, value)
    return value


def clear_cache() -> None:
    """Forget every parsed JSON file (tests that rewrite a file within one mtime tick)."""
    with _json_lock:
        _json_cache.clear()


# ---------------------------------------------------------------------------------------------------- the checks


def _visible_entries(folder: Path) -> list[str]:
    try:
        return sorted(e.name for e in os.scandir(folder) if not e.name.startswith("."))
    except OSError:
        return []


def _n(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _listed(names: list[str]) -> str:
    shown = ", ".join(names[:_MAX_LISTED])
    more = len(names) - _MAX_LISTED
    return shown + (f" and {more} more" if more > 0 else "")


def _count_rows(path: Path) -> int:
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        lines = sum(1 for line in f if line.strip())
    return max(lines - 1, 0)  # the header


def _vrt_missing(vrt: Path) -> tuple[int, list[str]]:
    """``(number of sources, the sources not on disk)`` of a GDAL VRT."""
    with open(vrt, encoding="utf-8-sig", errors="replace") as f:
        text = f.read()
    sources: list[str] = []
    missing: list[str] = []
    for m in _VRT_SOURCE_RE.finditer(text):
        name = html.unescape(m.group("name").strip())
        if name in sources:
            continue
        sources.append(name)
        if name.startswith("/vsi"):  # GDAL virtual file systems are not checked
            continue
        relative = bool(_RELATIVE_RE.search(m.group("attrs")))
        target = (vrt.parent / name) if relative else Path(name)
        if not target.exists():
            missing.append(name)
    return len(sources), missing


def _check_file(tier: paths.Tier, what: str, rel: str) -> Finding:
    """A manifest or an index: present and readable, and for a VRT every source it names on disk."""
    try:
        target = tier.path(rel)
    except HubError as e:
        return Finding(what, rel, False, f"{what} {rel} refused: {e.detail}")
    if target.is_dir():
        entries = _visible_entries(target)
        if not entries:
            return Finding(what, rel, False, f"{what} {rel}/ is empty")
        return Finding(what, rel, True, f"{rel}/ {_n(len(entries), 'entry', 'entries')}")
    if not target.is_file():
        return Finding(what, rel, False, f"{what} {rel} missing")
    suffix = target.suffix.lower()
    try:
        if suffix == ".json":
            value = _load_json(target)
            if isinstance(value, list):
                return Finding(what, rel, True, f"{rel} {_n(len(value), 'item')}")
            if isinstance(value, dict):
                return Finding(what, rel, True, f"{rel} {_n(len(value), 'key')}")
            return Finding(what, rel, True, f"{rel} ok")
        if suffix == ".csv":
            return Finding(what, rel, True, f"{rel} {_n(_count_rows(target), 'row')}")
        if suffix == ".vrt":
            n, missing = _vrt_missing(target)
            if missing:
                return Finding(what, rel, False, f"{rel} names {len(missing)} missing file(s): {_listed(missing)}")
            return Finding(what, rel, True, f"{rel} {_n(n, 'source')}")
    except (OSError, ValueError) as e:  # json.JSONDecodeError is a ValueError
        return Finding(what, rel, False, f"{what} {rel} unreadable: {e}")
    return Finding(what, rel, True, f"{rel} ok")


def _check_handshake(tier: paths.Tier) -> tuple[Finding, dict[str, Any] | None]:
    """The handshake file (``STATUS.json``): JSON, and its ``done`` member truthy."""
    hs = tier.handshake
    assert hs is not None
    rel = hs.file
    try:
        target = tier.path(rel)
    except HubError as e:
        return Finding("handshake", rel, False, f"handshake {rel} refused: {e.detail}"), None
    if not target.is_file():
        return Finding("handshake", rel, False, f"handshake {rel} missing"), None
    try:
        doc = _load_json(target)
    except (OSError, ValueError) as e:
        return Finding("handshake", rel, False, f"handshake {rel} unreadable: {e}"), None
    if not isinstance(doc, dict):
        return Finding("handshake", rel, False, f"handshake {rel} is not a JSON object"), None
    done = bool(doc.get(hs.done))
    shown = doc.get(hs.detail) if hs.detail else None
    blocked = doc.get("blocked_on")
    info: dict[str, Any] = {
        "file": rel,
        "done": done,
        "detail": None if shown is None else str(shown),
        "updated": doc.get("updated"),
        "blocked_on": blocked,
    }
    words: list[str] = []
    if shown is not None and str(shown) != "":
        words.append(f"{hs.detail} {shown}")
    if blocked:
        words.append(f"blocked on {blocked}")
    if done:
        return Finding("handshake", rel, True, ", ".join(words) or f"{rel} done"), info
    return Finding("handshake", rel, False, ", ".join(words) or f"{rel} does not say {hs.done}"), info


def scan_tier(tier: paths.Tier) -> TierReport:
    """The report of one resolved tier. Never raises: a check that cannot run is a failing finding."""
    base: dict[str, Any] = {
        "name": tier.name,
        "root": str(tier.root),
        "about": tier.about,
        "lane": tier.lane,
        "required": tier.required,
        "mount": tier.mount,
    }
    ok = tier.available()
    if ok is not True:
        root_finding = Finding("root", None, False, ok)
        return TierReport(status="missing", detail=ok, findings=(root_finding,), **base)
    findings: list[Finding] = []
    handshake: dict[str, Any] | None = None
    try:
        declared = False
        if tier.manifest:
            declared = True
            findings.append(_check_file(tier, "manifest", tier.manifest))
        if tier.index:
            declared = True
            findings.append(_check_file(tier, "index", tier.index))
        if tier.handshake is not None:
            declared = True
            finding, handshake = _check_handshake(tier)
            findings.append(finding)
        if not declared:
            entries = _visible_entries(tier.root)
            findings.append(
                Finding(
                    "root",
                    None,
                    bool(entries),
                    _n(len(entries), "entry", "entries") if entries else "the root is empty",
                )
            )
    except Exception as e:  # a bug or an odd file system: report it, never take the scan down
        findings.append(Finding("scan", None, False, f"scan failed: {type(e).__name__}: {e}"))
    failing = [f for f in findings if not f.ok]
    status: TierStatus = "partial" if failing else "present"
    detail = "; ".join(f.detail for f in (failing or findings))
    return TierReport(status=status, detail=detail, findings=tuple(findings), handshake=handshake, **base)


def _broken(name: str, spec: Any, reason: str) -> TierReport:
    spec = spec if isinstance(spec, Mapping) else {}
    return TierReport(
        name=name,
        status="missing",
        detail=reason,
        root=str(spec.get("root", "")),
        about=str(spec.get("about", "")),
        lane=str(spec.get("lane", "B")),
        required=bool(spec.get("required", False)),
        mount=bool(spec.get("mount", False)),
        findings=(Finding("config", None, False, reason),),
    )


def scan(cfg: Mapping[str, Any] | None = None) -> dict[str, TierReport]:
    """Every declared tier's report, by name, in config order (default: this repo's merged config).

    A tier whose config entry cannot be resolved (no root, say) is reported missing with that reason, so one bad
    entry never hides the others.
    """
    cfg = cfg if cfg is not None else paths.config()
    out: dict[str, TierReport] = {}
    for name, spec in (cfg.get("tiers") or {}).items():
        if not isinstance(spec, Mapping):  # local.json gave a plain value where {"root": ...} belongs
            why = f'its entry is {type(spec).__name__} {spec!r}, not an object such as {{"root": "..."}}'
            out[name] = _broken(name, spec, f"tier {name} cannot be read from the config: {why}")
            continue
        try:
            one = paths.tiers({"_repo": cfg.get("_repo"), "tiers": {name: spec}})[name]
        except (HubError, AttributeError, KeyError, TypeError, ValueError) as e:
            detail = e.detail if isinstance(e, HubError) else f"{type(e).__name__}: {e}"
            out[name] = _broken(name, spec, f"tier {name} cannot be read from the config: {detail}")
            continue
        out[name] = scan_tier(one)
    return out


def counts(reports: Mapping[str, TierReport]) -> dict[str, int]:
    """``{"present": n, "partial": n, "missing": n}``."""
    out = dict.fromkeys(STATUSES, 0)
    for r in reports.values():
        out[r.status] += 1
    return out


def as_json(reports: Mapping[str, TierReport], *, at: dt.datetime | None = None) -> dict[str, Any]:
    """The body of ``GET /tiers``: ``{"at", "counts", "tiers": [report, ...]}``."""
    when = (at or dt.datetime.now(dt.UTC)).astimezone(dt.UTC).isoformat(timespec="seconds")
    return {"at": when, "counts": counts(reports), "tiers": [r.as_dict() for r in reports.values()]}


def changes(before: Mapping[str, TierReport] | None, after: Mapping[str, TierReport]) -> list[TierEvent]:
    """The ``tier`` events between two scans: every tier whose status or detail changed, was added or was removed.

    With ``before`` None (the first scan after start) every tier gets an event.
    """
    old = before or {}
    events: list[TierEvent] = []
    for name, r in after.items():
        prev = old.get(name)
        if prev is None or (prev.status, prev.detail) != (r.status, r.detail):
            events.append(r.event())
    for name in old:
        if name not in after:
            events.append(TierEvent(tier=name, status="missing", detail="no longer declared in the config"))
    return events


def required_missing(reports: Iterable[TierReport]) -> list[TierReport]:
    """The required tiers that are missing (what makes doctor fail)."""
    return [r for r in reports if r.required and r.status == "missing"]


__all__ = [
    "Finding",
    "STATUSES",
    "TierReport",
    "as_json",
    "changes",
    "clear_cache",
    "counts",
    "required_missing",
    "scan",
    "scan_tier",
]
