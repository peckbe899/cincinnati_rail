"""The declared fallbacks: what the records do not hold yet, read from railsim's own files through ``ctx.file``.

Every Metro route has a line config ``configs/metro/<stem>.yaml`` (``config_stem``: ``Line_6`` is ``cin_line_6``,
``CVG_Express`` is ``cvg_express``). From it, and from the era file it names and the rolling stock library, the
jobs take:

- station dwell classes and PSD (``stations.info``, ``stations.defaults``), until they are platform or service
  records (I2.4);
- the era of the view's year (``load_era``'s rule: the era whose ``years`` cover it; the default train is the latest
  fleet entry at or before it) and its overlay;
- the train, load factor, rail condition, driver, dwell model, padding, turnback and reference times.

``merged_config`` is railsim's own merge (``app.deep_merge``: program defaults < era overlay < line config) with the
blocks that reach a KMZ, a DEM or the network dropped (``kmz``, ``track``, ``profile``), so nothing downstream can.
Each file is read through ``ctx.file`` (its sha256 enters the key) and parsed here; ``run`` gets plain dicts.

A param that is not registered yet (``railsim.*``) raises ``NotFound`` and records no dependency; its value then
comes from the file this module already read, so the key still names what was read (section 5 of the plan).
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from region.core.errors import Invalid, NotFound

CONFIG = "repo://configs/metro/{stem}.yaml"
ROLLING_STOCK = "repo://data/rollingstock/metro.yaml"
DROPPED = ("kmz", "track", "profile")
"""Line config blocks the run never reads: the KMZ, its track folders, and the ground and Metro profile sources."""
PRESENT_YEAR = 2026
"""The year of a view at the present when the era file names no ``default_year``."""

_memo: dict[tuple[str, int, int], Any] = {}
_memo_lock = threading.Lock()


def config_stem(route_key: str) -> str:
    """The line config of a route key: ``Line_6`` to ``cin_line_6``, ``Line_2b`` to ``cin_line_2b``,
    ``CVG_Express`` to ``cvg_express``."""
    key = str(route_key)
    if key.startswith("Line_"):
        return "cin_line_" + key[len("Line_") :].lower()
    return key.lower()


def read_yaml(path: Path) -> Any:
    """A YAML file parsed once per (path, size, mtime) in this process; a deep copy each time."""
    import yaml

    p = Path(path)
    try:
        st = p.stat()
    except FileNotFoundError:
        raise NotFound(f"{p.name} is missing", kind="file", id=str(p)) from None
    k = (str(p), st.st_size, st.st_mtime_ns)
    with _memo_lock:
        hit = _memo.get(k)
    if hit is None:
        loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
        hit = yaml.load(p.read_text(encoding="utf-8"), Loader=loader)  # noqa: S506 - a safe loader
        with _memo_lock:
            if len(_memo) > 64:
                _memo.clear()
            _memo[k] = hit
    return copy.deepcopy(hit)


def line_config(ctx: Any, route_key: str) -> tuple[str, dict[str, Any]]:
    """``(stem, config)`` of a route's line config, read through ``ctx.file``; ``Invalid`` when there is none."""
    stem = config_stem(route_key)
    uri = CONFIG.format(stem=stem)
    path = ctx.file(uri)
    if not Path(path).is_file():
        raise Invalid(f"route {route_key} has no line config ({uri}); railsim has nothing to run it with")
    cfg = read_yaml(path)
    if not isinstance(cfg, dict):
        raise Invalid(f"{uri} is not a YAML mapping")
    return stem, cfg


def era_of(ops: Mapping[str, Any], year: int | None) -> tuple[dict[str, Any], str | None, int, str]:
    """``(era, default train, year, year_source)``: railsim's ``operations.load_era`` on a parsed era file."""
    source = "view"
    if year is None:
        year = ops.get("default_year")
        source = "default_year"
        if year is None:
            year, source = PRESENT_YEAR, "present"
    year = int(year)
    era = next((e for e in ops.get("eras", []) or [] if e["years"][0] <= year <= e["years"][1]), None)
    if era is None:
        raise Invalid(f"{ops.get('system', 'the era file')} has no operating era covering {year}")
    train = None
    for f in sorted(ops.get("fleet", []) or [], key=lambda f: f["from"]):
        if f["from"] <= year:
            train = f["train"]
    return copy.deepcopy(era), train, year, source


def merged_config(user: Mapping[str, Any], era: Mapping[str, Any] | None) -> dict[str, Any]:
    """railsim's merge for the Metro program (defaults < era overlay < line config), less ``DROPPED``."""
    from railsim import app, metro

    cfg = app.deep_merge(app.deep_merge(metro.DEFAULTS, dict((era or {}).get("overlay") or {})), dict(user))
    for k in DROPPED:
        cfg.pop(k, None)
    return cfg


def _param(ctx: Any, path: str, scope: str | None, fallback: Any) -> Any:
    try:
        return ctx.param(path, scope)
    except NotFound:
        return fallback


def run_settings(ctx: Any, route: Mapping[str, Any], year: int | None) -> dict[str, Any]:
    """Everything ``railsim.run`` takes besides the RouteInput: the merged config, the era, the train (its rolling
    stock entry) and the run options, from the line config, the era file and the rolling stock (all through
    ``ctx.file``) and the ``railsim.*`` params where Ben has registered them."""
    rd = route.get("data") or {}
    rid = route.get("id")
    stem, user = line_config(ctx, str(rd.get("key")))
    era: dict[str, Any] | None = None
    era_train = None
    ops_uri = None
    hint = "view" if year is not None else ("config" if user.get("year") is not None else None)
    year = year if year is not None else user.get("year")
    year_source = hint or "none"
    if user.get("operations"):
        ops_uri = "repo://" + str(user["operations"]).replace("\\", "/")
        ops = read_yaml(ctx.file(ops_uri))
        era, era_train, year, year_source = era_of(ops, year)
        year_source = hint or year_source
    valid = user.get("years")
    if valid and year is not None and not (valid[0] <= int(year) <= valid[1]):
        raise Invalid(f"{user.get('name', stem)} only runs in {valid[0]} to {valid[1]}, not in {year}")
    cfg = merged_config(user, era)
    key = cfg.get("train") or era_train
    if not key:
        raise Invalid(f"{stem}: no train for {year} (no `train:` in the config, no fleet entry in the era file)")
    library = read_yaml(ctx.file(ROLLING_STOCK))
    if not isinstance(library, dict) or not isinstance(library.get(key), dict):
        raise Invalid(f"{stem}: train {key!r} is not in {ROLLING_STOCK}")
    st = cfg.get("stations") or {}
    options = {
        "load_factor": float(_param(ctx, "railsim.load_factor", rid, cfg.get("load_factor", 0.5))),
        "rail_condition": str(_param(ctx, "railsim.rail_condition", rid, cfg.get("rail_condition", "dry"))),
        "grid_m": float(_param(ctx, "railsim.grid_m", rid, 2.0)),
        "stop_position": str(_param(ctx, "railsim.stop_position", rid, st.get("stop_position", "far_end"))),
        "reversal_min_s": float(_param(ctx, "railsim.reversal_min_s", rid, st.get("reversal_min_s", 240.0))),
    }
    pad = dict(cfg.get("padding") or {})
    pad["percent"] = float(_param(ctx, "railsim.padding.percent", rid, pad.get("percent", 0.0)))
    pad["final_leg_s"] = float(_param(ctx, "railsim.padding.final_leg_s", rid, pad.get("final_leg_s", 0.0)))
    cfg["padding"] = pad
    sources = {
        "config": CONFIG.format(stem=stem).replace("repo://", ""),
        "train": ROLLING_STOCK.replace("repo://", ""),
        "classes": CONFIG.format(stem=stem).replace("repo://", ""),
    }
    if ops_uri:
        sources["era"] = ops_uri.replace("repo://", "")
    return {
        "config": stem,
        "name": cfg.get("name", stem),
        "year": year,
        "year_source": year_source,
        "era": None
        if era is None
        else {
            "name": era.get("name"),
            "goa": era.get("goa"),
            "years": list(era.get("years") or []),
            "signalling": ((era.get("overlay") or {}).get("signalling") or {}).get("system"),
        },
        "train_key": key,
        "train": library[key],
        "cfg": cfg,
        "options": options,
        "sources": sources,
    }


def geometry_config(ctx: Any, route_key: str) -> dict[str, Any]:
    """The geometry block the horizontal fit reads: metro defaults < the line config's ``geometry``, with the
    ``railsim.geometry.*`` params where registered. The eras never overlay geometry, so the fit has no year."""
    from railsim import app, metro

    _stem, user = line_config(ctx, route_key)
    g = app.deep_merge(metro.DEFAULTS["geometry"], dict(user.get("geometry") or {}))
    for name in (
        "min_spiral_m",
        "min_reverse_tangent_m",
        "min_radius_m",
        "group_dev_tol_m",
        "corner_offset_tol_m",
        "simplify_tol_m",
    ):
        try:
            g[name] = float(ctx.param(f"railsim.geometry.{name[:-2]}_m", None))
        except NotFound:
            pass
    try:
        g = app.deep_merge(g, {"line_speed_mph": float(ctx.param("railsim.geometry.line_speed", None))})
    except NotFound:
        pass
    return g


def station_info(cfg: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """``(defaults, info by station name)`` of the line config's ``stations`` block."""
    st = cfg.get("stations") or {}
    return dict(st.get("defaults") or {}), {str(k): dict(v or {}) for k, v in (st.get("info") or {}).items()}


__all__ = [
    "CONFIG",
    "DROPPED",
    "ROLLING_STOCK",
    "config_stem",
    "era_of",
    "geometry_config",
    "line_config",
    "merged_config",
    "read_yaml",
    "run_settings",
    "station_info",
]
