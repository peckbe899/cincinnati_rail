"""``ground.profile@1``: a section's ground sampled from region.ground at the view's year and timeline (I2.1).

The job reads the section record and names every file compose reads for the year in its key; it samples the
section's path every step in windows of ``ground.sample_window_m`` (1 km), so memory stays bounded on a 30 km
line; the line file's ground (map 3 ground) is the reference it is checked against; a run writes nothing and opens
no socket.
"""

from __future__ import annotations

import math
import os
import socket
import threading
from pathlib import Path

import numpy as np
import pytest

from region.core import fsio, paths
from region.core.view import View
from region.ext.profiles.inputs import StoreReads
from region.ground import layers as L
from region.jobs.contract import check_contract
from region.jobs.hosts import RunContext
from region.jobs.plan import Planner
from region.jobs.registry import Registry
from tests.importers.helpers import MAIN, METRO, all_records, read_only, section_of

REPO = paths.repo_root()


def _jobs():
    from region.ext.terrain import jobs

    return jobs


def _profile():
    from region.ext.terrain import profile

    return profile


def _rt() -> RunContext:
    from region.jobs.hosts import NoEngine

    return RunContext(NoEngine(), lambda f, m: None, threading.Event(), {})


def _run(store, sid: str, view: View = MAIN):
    jt = _jobs().GROUND_PROFILE
    return jt.run(jt.plan(StoreReads(store, view), sid), _rt())


def _planner(store, file_hash=None) -> Planner:
    reg = Registry([_jobs().GROUND_PROFILE])
    return Planner(
        store,
        registry=reg,
        file_hash=file_hash or (lambda p: fsio.sha256_file(p) if Path(p).is_file() else None),
        upstream_output=lambda k: None,
        engine_info=lambda: ("none", {}),
    )


def _line_ground(store, sid: str) -> np.ndarray:
    (g,) = all_records(store, "ground_profile", parent=sid)
    return np.array([np.nan if v is None else v / 10 for v in g["data"]["z_dm"]], dtype=float)


# --------------------------------------------------------------------------------------------- registration


def test_the_job_type_is_discovered_with_its_axes_and_host():
    """The terrain feature's ``JOB_TYPES`` holds ``ground.profile@1``; the default registry finds it (no edit of
    region/jobs/registry.py): a process job of a section, priority 6, 120 s, reading the year and the timeline."""
    from region.jobs.registry import default_registry

    jt = default_registry().get("ground.profile")
    assert jt is _jobs().GROUND_PROFILE
    assert (jt.version, jt.scope, jt.host, jt.priority, jt.timeout_s) == ("1", "section", "process", 6, 120.0)
    assert set(jt.axes) == {"year", "timeline"}
    code = {str(f) for f in jt.code_files}
    assert {"repo://region/ext/terrain/profile.py", "repo://region/ground"} <= code


# ------------------------------------------------------------------------------------------------ the files


def test_ground_files_name_every_file_compose_reads():
    """``ground_files(year, timeline)`` names each file compose reads for that year and timeline, as URIs: the
    two base surfaces with the rasters each VRT points at, the ledger, each present work's layers (target, mode,
    part, delta, zones, minus, years), and on the real timeline the 1912 riverworks delta. Each URI resolves to the
    very file compose opens. Checked by recording what compose opens over a strip of Line 6."""
    import importlib

    C = importlib.import_module("region.ground.compose")  # the module (the package exports a function by its name)
    prof = _profile()
    opened: set[str] = set()
    real_read, real_zones, real_years = C.read, C._load_zones, C.zone_years

    def read(path, *a, **k):
        opened.add(os.path.realpath(path))
        p = Path(path)
        if p.suffix == ".vrt":  # the VRT's own rasters
            for f in prof.vrt_sources(p):
                opened.add(os.path.realpath(f))
        return real_read(path, *a, **k)

    def zones(path):
        opened.add(os.path.realpath(path))
        return real_zones(path)

    def years(path):
        if path:
            opened.add(os.path.realpath(path))
        return real_years(path)

    with read_only() as store:
        sec = section_of(store, "Line_6")
    path = sec["data"]["path"]
    for year, tl in ((2026, "canon"), (1930, "canon"), (1912, "real")):
        opened.clear()
        C.read, C._load_zones, C.zone_years = read, zones, years
        try:
            prof.sample_path(path, 3000.0, 2.0, year, tl, window_m=1000.0)
        finally:
            C.read, C._load_zones, C.zone_years = real_read, real_zones, real_years
        uris = prof.ground_files(year, tl)
        named = {os.path.realpath(paths.resolve(u)) for u in uris}
        assert opened <= named, (year, tl, sorted(opened - named))
        assert os.path.realpath(L.GROUND / "works_ledger.json") in named
    # the URIs: the ground tiers by tier, the rest of ground/ by repo
    uris = prof.ground_files(2026, "canon")
    assert "tier://ground_1912_real/canon_1912_ground_dm.vrt" in uris
    assert "tier://ground_1912_real/canon_1912_ground_dm_n.tif" in uris
    assert "tier://ground_2026/map3_profile_dem_dm.vrt" in uris
    assert "tier://ground_2026/map3_profile_dem_dm_r1c1.tif" in uris
    assert "repo://ground/works_ledger.json" in uris
    assert "repo://ground/works/canon_interstates_delta_dm.tif" in uris
    assert "repo://ground/works/riverworks_1912_delta_dm.tif" not in uris  # canon: no real-timeline delta
    assert "repo://ground/works/riverworks_1912_delta_dm.tif" in prof.ground_files(2026, "real")
    assert "repo://ground/works/canon_interstates_delta_dm.tif" not in prof.ground_files(1930, "canon")
    assert uris == sorted(set(uris))


# -------------------------------------------------------------------------------------------------- the key


def test_the_key_holds_the_year_the_timeline_and_every_ground_file():
    """The key names the section record, the year and timeline axes and each file ``ground_files`` names; 1930
    and 2026 are two keys, real and canon are two keys, and a changed works file plans a new key."""
    prof = _profile()
    with read_only() as store:
        sid = section_of(store, "Line_6")["id"]
        planner = _planner(store)
        now = planner.plan("ground.profile", sid, View(year=2026))
        old = planner.plan("ground.profile", sid, View(year=1930))
        real = planner.plan("ground.profile", sid, View(year=2026, timeline="real"))
        assert now.key and old.key and real.key and len({now.key, old.key, real.key}) == 3
        assert now.axes == {"year": 2026, "timeline": "canon"}
        refs = {r for r, _h in now.deps}
        assert f"rec:{sid}" in refs
        assert {f"file:{u}" for u in prof.ground_files(2026, "canon")} <= refs
        assert all(h is not None for r, h in now.deps if r.startswith("file:"))
        # the inputs carry what was read, never the scope id
        assert sid not in str(now.inputs)
        # a works file rewritten: a new key
        target = os.path.realpath(paths.resolve("repo://ground/works/ky_terraces_target_dm.tif"))

        def moved(p):
            h = fsio.sha256_file(p) if Path(p).is_file() else None
            return "0" * 64 if os.path.realpath(p) == target else h

        again = _planner(store, moved).plan("ground.profile", sid, View(year=2026))
        assert again.key != now.key
        # the same content in a scenario layer: the same key (a layer is never an axis)
        assert _planner(store).plan("ground.profile", sid, View(layer="main", year=2026)).key == now.key


def test_the_contract_on_line_2b():
    """``check_contract``: a stable key, two runs give one output hash, and nothing was written to the store."""
    with read_only() as store:
        sid = section_of(store, "Line_2b")["id"]
        out = check_contract(_jobs().GROUND_PROFILE, store, sid, MAIN)
        assert len(out["key"]) == 64 and len(out["output_hash"]) == 64


# ---------------------------------------------------------------------------------------------- the samples


def test_line_6_against_the_line_file_ground():
    """Line 6 at the present (2026, canon), every 2 m: no NaN, the grid the section's (c = i * 2 m, covering the
    end), and within 3 m of the line file's map 3 ground at the 95th percentile (the line file is map 3 ground
    sampled by the Deck tie; region.ground at 2026 is the canon 1912 base with every work built by 2026)."""
    with read_only() as store:
        sec = section_of(store, "Line_6")
        out = _run(store, sec["id"])
        lf = _line_ground(store, sec["id"])
    z = out.arrays["ground_m"]
    meta = out.meta
    assert z.dtype == np.dtype("<f8") and out.arrays["src"].dtype == np.dtype("u1")
    step = float(sec["data"]["step_m"])
    assert meta["grid"] == {"c0": 0.0, "step_m": step, "n": len(z)}
    assert len(z) == math.ceil(float(sec["data"]["length_m"]) / step - 1e-9) + 1
    assert meta["year"] == 2026 and meta["year_source"] == "present" and meta["timeline"] == "canon"
    assert meta["missing"] == 0 and not np.isnan(z).any()
    n = min(len(z), len(lf))
    d = np.abs(z[:n] - lf[:n])
    assert float(np.percentile(d, 95)) <= 3.0
    assert abs(float(np.mean(z[:n] - lf[:n]))) <= 0.5
    assert set(meta["layers"].values()) >= {"canon_1912"}


def test_1930_leaves_the_later_works_out():
    """At 1930 the interstates (1940 to 1965) and the Lunken works (1937 to 1941) are not in the ground, and the
    meta says why; at 2026 they are."""
    with read_only() as store:
        sid = section_of(store, "Line_2b")["id"]
        old = _run(store, sid, View(year=1930))
        now = _run(store, sid, View(year=2026))
    skipped = dict((w, why) for w, why in old.meta["works"]["skipped"])
    assert skipped["canon_interstates"] == "built 1965"
    assert "lunken_levees" in skipped
    assert "canon_interstates" in now.meta["works"]["present"]
    assert old.meta["year"] == 1930 and old.meta["year_source"] == "view"


def test_windows_equal_one_compose():
    """Sampling in 1 km windows gives the same levels as one compose over the whole of Line 2b (5 km): each window
    takes a margin wider than the zones' feather, so no cell near a window's edge is composed differently."""
    from region.ground.compose import compose
    from region.ground.sample import sample_grid

    prof = _profile()
    with read_only() as store:
        sec = section_of(store, "Line_2b")
    d = sec["data"]
    z, _src, _ = prof.sample_path(d["path"], float(d["length_m"]), float(d["step_m"]), 2026, "canon", window_m=1000)
    xy = prof.section_xy(d["path"], prof.chainages(float(d["length_m"]), float(d["step_m"])))
    m = prof.MARGIN_M
    g = compose(2026, (xy[:, 0].min() - m, xy[:, 1].min() - m, xy[:, 0].max() + m, xy[:, 1].max() + m))
    one = sample_grid(g, xy)
    assert np.allclose(z, one, atol=1e-6, equal_nan=True)


# ----------------------------------------------------------------------------------------------- no effects


def _ground_state() -> list[str]:
    """Every file under ground/ with its size and mtime: GDAL writes side files (``.aux.xml``, overviews) beside
    the rasters it reads, so a write by the sampler, from Python or from C, shows here."""
    return sorted(f"{p}:{p.stat().st_size}:{p.stat().st_mtime_ns}" for p in (REPO / "ground").rglob("*") if p.is_file())


def _var_state() -> list[str]:
    var = paths.var_root()
    return sorted(str(p) for p in var.rglob("*")) if var.exists() else []


def test_a_run_writes_nothing_and_opens_no_socket(monkeypatch):
    """During a run every socket refuses to connect and every Python open for writing is refused; after it ground/
    (GDAL's side files would land there) and var are as they were. Other lanes edit the tree at the same time, so
    the repo is not compared as a whole: Python writes anywhere are refused instead."""
    import builtins
    import io

    _jobs()  # imported (and its bytecode cached) before the snapshot

    def refuse(*a, **k):
        raise AssertionError("ground.profile opened a network connection")

    real_open = builtins.open

    def guarded(file, mode="r", *a, **k):
        if any(c in str(mode) for c in "wax+"):
            raise AssertionError(f"ground.profile opened {file} for writing")
        return real_open(file, mode, *a, **k)

    real_os_open = os.open

    def guarded_os(path, flags, *a, **k):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC):
            raise AssertionError(f"ground.profile opened {path} for writing")
        return real_os_open(path, flags, *a, **k)

    with read_only() as store:
        sid = section_of(store, "Line_2b")["id"]
        jt = _jobs().GROUND_PROFILE
        inputs = jt.plan(StoreReads(store, MAIN), sid)
        before_ground, before_var = _ground_state(), _var_state()
        with monkeypatch.context() as mp:  # undone at its end, leaving the suite's own CRHUB_VAR in place
            mp.setattr(socket.socket, "connect", refuse)
            mp.setattr(socket, "create_connection", refuse)
            mp.setattr(builtins, "open", guarded)
            mp.setattr(io, "open", guarded)
            mp.setattr(os, "open", guarded_os)
            out = jt.run(inputs, _rt())
    assert out.meta["missing"] == 0
    assert _ground_state() == before_ground
    assert _var_state() == before_var


# ---------------------------------------------------------------------------------- every Metro line (report)


MAP3_LAYERS = {"map3_outside_1912", "ohio_bed_canon", "canon_interstates"}
"""The layers that are the 2026 canon ground (map 3) itself: outside the 1912 raster, and the works applied as map 3
inside their footprint. The line files' ground is map 3 too, so these must agree."""


def _outside_bases(xy: np.ndarray) -> np.ndarray:
    from region.ground.raster import raster_bounds

    inside = np.zeros(len(xy), bool)
    for f in (L.CANON_1912, L.MAP3):
        x0, y0, x1, y1 = raster_bounds(f)
        inside |= (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
    return ~inside


@pytest.mark.slow
def test_every_metro_line_against_its_line_file(capsys):
    """All 16 Metro sections at 2026, each against its line file's ground (map 3). Where region.ground takes the
    map 3 ground itself the two agree (95th percentile within 0.25 m); on the canon 1912 base they differ by what
    the works do not govern, which is printed (the lane's report). The only samples with no ground lie outside
    both base rasters (Line 14's last 1.46 km runs east of map 3's extent): the line file fills them there."""
    prof = _profile()
    rows = []
    with read_only() as store:
        for route in METRO:
            sec = section_of(store, route)
            d = sec["data"]
            out = _run(store, sec["id"])
            z, src = out.arrays["ground_m"], out.arrays["src"]
            names = {int(k): v for k, v in out.meta["layers"].items()}
            lf = _line_ground(store, sec["id"])
            n = min(len(z), len(lf))
            dd = z[:n] - lf[:n]
            ok = ~np.isnan(dd)
            m3 = ok & np.isin(src[:n], [c for c, v in names.items() if v in MAP3_LAYERS])
            nan = np.isnan(z)
            xy = prof.section_xy(d["path"], prof.chainages(float(d["length_m"]), float(d["step_m"])))
            assert not (nan & ~_outside_bases(xy)).any(), route
            p95_m3 = float(np.percentile(np.abs(dd[m3]), 95)) if m3.any() else 0.0
            rows.append(
                (
                    route,
                    len(z),
                    int(nan.sum()),
                    float(np.mean(dd[ok])),
                    float(np.percentile(np.abs(dd[ok]), 95)),
                    float(np.max(np.abs(dd[ok]))),
                    int(m3.sum()),
                    p95_m3,
                )
            )
    with capsys.disabled():
        print("\nroute n nan mean_m p95_abs_m max_abs_m map3_samples map3_p95_m")
        for r in rows:
            print("{:<12} {:6d} {:4d} {:+.2f} {:.2f} {:.2f} {:6d} {:.2f}".format(*r))
    assert [r[0] for r in rows if r[2]] == ["Line_14"]
    assert all(r[7] <= 0.25 for r in rows), [r for r in rows if r[7] > 0.25]
