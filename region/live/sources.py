"""What the live hub watches: every importer's sources, every data tier, and Ben's old hub database.

``declared(cfg)`` gives one ``Source`` per importer (``import:<name>``) and one per data tier (``tier:<name>``):

- **an importer** watches each source it names (``Importer.sources``): a folder as a tree (the line files, the old
  hub's seed), a file by itself (the registry). ``old_hub`` also watches Ben's live ``hub/hub.db`` (``live.old_hub_db``
  in the config, relative to the repo), whose change is read through a backup-API snapshot, never the live file;
- **a tier** watches its root's own entries (one level, so a tile folder is listed, never walked) and its index,
  manifest and handshake files (``ground/1912/STATUS.json``, the Sanborn tiles' ``index.json``, ``deck.json``).

Every path is resolved through the config the server runs with, so a test (or ``configs/local.json``) that moves a
tier's root moves what is watched and what the importer reads with it.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from region.core import paths
from region.core.errors import HubError

from .watch import Source, Watch

log = logging.getLogger("region.live")

IMPORT_LABELS = {
    "registry": "Rule registry",
    "profile_lines": "Line files",
    "old_hub": "Old hub",
    "ground_layers": "Ground layers",
}
"""How Ben names each importer's source (the sources pane, the toasts)."""
ORIGIN_WORDS = {
    "registry": "the rule registry",
    "profile_lines": "the line files",
    "old_hub": "the old hub",
    "ground_layers": "the ground tiers",
}
"""What a toast says a change came from ("Line 3 updated from the old hub")."""
TIER_LABELS = {
    "ground_1912_real": "1912 ground",
    "ground_2026": "2026 ground",
    "sanborn_tiles_22": "Sanborn 1922 tiles",
    "deck": "Deck files",
    "old_hub_seed": "Old hub seed folder",
    "profile_lines": "Line files folder",
    "artifacts_3d": "3D artifacts",
}
TIER_IMPORTERS = {"ground_1912_real": ("ground_layers",), "ground_2026": ("ground_layers",)}
"""Importers a tier's change runs besides the tier's own rescan (the ground layer records follow the handshakes)."""

DEFAULT_OLD_HUB_DB = "hub/hub.db"


def _mode_of(uri: str, local: Path) -> str:
    if local.is_dir() or uri.endswith("/"):
        return "tree"
    if local.is_file() or local.suffix:
        return "file"
    return "tree"


def old_hub_db(cfg: Mapping[str, Any]) -> Path | None:
    """Ben's live old hub database (``live.old_hub_db``, default ``hub/hub.db``), or ``None`` when set to null."""
    live = cfg.get("live") or {}
    value = live.get("old_hub_db", DEFAULT_OLD_HUB_DB) if isinstance(live, Mapping) else DEFAULT_OLD_HUB_DB
    if not value:
        return None
    p = Path(str(value))
    return p if p.is_absolute() else Path(cfg.get("_repo") or paths.REPO) / p


def importer_sources(imp: Any, cfg: Mapping[str, Any]) -> tuple[list[Watch], dict[str, Path]]:
    """The watches of one importer and its sources' local paths by name (the overrides the live runner passes)."""
    watches: list[Watch] = []
    local: dict[str, Path] = {}
    for name, uri in sorted(imp.sources(paths).items()):
        try:
            p = paths.resolve(uri, cfg)
        except HubError as e:
            log.info("live: %s source %s is not here (%s); watched once it appears", imp.name, name, e.detail)
            continue
        local[name] = p
        watches.append(Watch(p, _mode_of(uri, p), name))  # type: ignore[arg-type]
    return watches, local


def import_source(imp: Any, cfg: Mapping[str, Any]) -> Source:
    watches, local = importer_sources(imp, cfg)
    info: dict[str, Any] = {"importer": imp.name, "overrides": local}
    if "seed" in imp.sources(paths):
        db = old_hub_db(cfg)
        if db is not None:
            watches.append(Watch(db, "db", "hub.db"))
            info["hub_db"] = db
    return Source(
        id=f"import:{imp.name}",
        label=IMPORT_LABELS.get(imp.name, imp.name.replace("_", " ")),
        watches=watches,
        kind="import",
        info=info,
    )


def tier_source(name: str, spec: Mapping[str, Any], cfg: Mapping[str, Any]) -> Source | None:
    try:
        tier = paths.tiers({"_repo": cfg.get("_repo"), "tiers": {name: spec}})[name]
    except (HubError, AttributeError, KeyError, TypeError, ValueError):
        return None
    watches = [Watch(tier.root, "dir", "root")]
    for what in ("index", "manifest"):
        rel = getattr(tier, what, None)
        if rel:
            try:
                p = paths.contained(tier.root, rel)  # named even while the root is absent: watched once it appears
            except HubError:
                continue
            watches.append(Watch(p, "dir" if p.is_dir() else "file", what))
    if tier.handshake is not None:
        try:
            watches.append(Watch(paths.contained(tier.root, tier.handshake.file), "file", "handshake"))
        except HubError:
            pass
    label = TIER_LABELS.get(name) or str(spec.get("title") or name.replace("_", " "))
    return Source(
        id=f"tier:{name}",
        label=label,
        watches=watches,
        kind="tier",
        info={"tier": name, "importers": list(TIER_IMPORTERS.get(name, ()))},
    )


def declared(cfg: Mapping[str, Any] | None = None, importers: Mapping[str, Any] | None = None) -> list[Source]:
    """Every source the live hub watches (see the module doc), importers first in run order, then tiers."""
    cfg = cfg if cfg is not None else paths.config()
    if importers is None:
        from region.cli import imports as I

        importers = I.importers()
    out = [import_source(imp, cfg) for imp in importers.values()]
    for name, spec in (cfg.get("tiers") or {}).items():
        if isinstance(spec, Mapping):
            s = tier_source(name, spec, cfg)
            if s is not None:
                out.append(s)
    return out


__all__ = [
    "DEFAULT_OLD_HUB_DB",
    "IMPORT_LABELS",
    "ORIGIN_WORDS",
    "TIER_IMPORTERS",
    "TIER_LABELS",
    "declared",
    "import_source",
    "importer_sources",
    "old_hub_db",
    "tier_source",
]
