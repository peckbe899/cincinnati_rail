"""Side-effect free runs (plan section 6, lane railsim): the railsim chain from the records, run and attribution,
opens no network connection, reaches none of railsim's legacy readers and writers (the KMZ, the ground sources,
the Metro profile loader, the report and plot writers, ``app.main``, ``build_route``), and leaves the repository
tree, ``data/elevation_cache``, ``output/`` and the store as they were."""

from __future__ import annotations

import socket
import subprocess
from pathlib import Path
from typing import Any

import pytest

from region.core import paths
from tests.importers.helpers import MAIN, read_only
from tests.railsim.conftest import Chain, route_of

REPO = paths.repo_root()


def _tree(root: Path) -> dict[str, tuple[int, int]]:
    if not root.exists():
        return {}
    return {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}


WATCHED = ("data", "configs", "railsim", "hub", "tests/baseline", "rules", "design", "output", "ground")
"""The parts of the tree a run could touch and no build lane edits (the lanes edit region/, app/ and tests/ beside
this test, so the whole tree's status is not stable while they work)."""


def _git_status() -> str:
    return subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *WATCHED],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@pytest.mark.slow
def test_the_chain_has_no_side_effects(pool, monkeypatch):
    import railsim.app as A
    import railsim.elevation as E
    import railsim.kml as K
    import railsim.line as L
    import railsim.metro_profile as MP
    import railsim.report as R

    def refuse(*a: Any, **k: Any) -> Any:
        raise AssertionError("the railsim chain reached a legacy reader, writer or the network")

    status = _git_status()
    trees = {name: _tree(REPO / name) for name in ("data/elevation_cache", "output")}
    for mod, names in (
        (L, ("build_route",)),
        (A, ("main", "build_route")),
        (K, ("read_kmz",)),
        (E, ("from_dem", "from_lidar", "from_terrain_tiles", "from_usgs", "from_csv", "from_kmz_lines")),
        (R, ("write_csv", "write_kml", "plot_run", "write_summary")),
    ):
        for n in names:
            if hasattr(mod, n):
                monkeypatch.setattr(mod, n, refuse)
    monkeypatch.setattr(MP.MetroProfile, "load", classmethod(lambda cls, *a, **k: refuse()))
    monkeypatch.setattr(socket.socket, "connect", lambda self, *a, **k: refuse())
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, *a, **k: refuse())
    monkeypatch.setattr(socket, "create_connection", refuse)
    with read_only() as store:
        seq = store.last_seq()
        rid = route_of(store, "Line_6")["id"]
        ch = Chain(store, pool)
        _p, run = ch.compute("railsim.run", rid, MAIN)
        _q, att = ch.compute("railsim.attribution", rid, MAIN)
        assert store.last_seq() == seq
    assert run.meta["directions"] and att.meta["directions"]
    assert _git_status() == status
    for name, before in trees.items():
        assert _tree(REPO / name) == before, name
