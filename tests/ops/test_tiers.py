"""The data tier scan (region.tiers, 9.26): missing, partial and present, with the reason for each."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from region import tiers
from region.core import paths
from tests.ops.conftest import make_repo, write

VRT = """<VRTDataset rasterXSize="2" rasterYSize="1">
  <VRTRasterBand dataType="Int16" band="1">
    <SimpleSource><SourceFilename relativeToVRT="1">a.tif</SourceFilename></SimpleSource>
    <SimpleSource><SourceFilename relativeToVRT="1">b.tif</SourceFilename></SimpleSource>
  </VRTRasterBand>
</VRTDataset>
"""


def _tier(name: str, root: str, **kw):
    spec = {
        "name": name,
        "about": f"the {name} tier",
        "lane": "B",
        "root": root,
        "manifest": None,
        "index": None,
        "handshake": None,
        "required": False,
        "mount": False,
    }
    spec.update(kw)
    return spec


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    hs = {"file": "STATUS.json", "done": "done", "detail": "stage"}
    make_repo(
        repo,
        [
            _tier("done", "t/done", manifest="MANIFEST.csv", handshake=hs, required=True),
            _tier("contours", "t/contours", manifest="MANIFEST.csv", handshake=hs),
            _tier("no_index", "t/no_index", index="index.json", mount=True),
            _tier("bad_json", "t/bad_json", index="index.json"),
            _tier("vrt_gap", "t/vrt_gap", index="dem.vrt"),
            _tier("vrt_full", "t/vrt_full", index="dem.vrt"),
            _tier("empty_dir", "t/empty_dir", index="alignments"),
            _tier("no_status", "t/no_status", handshake=hs),
            _tier("blocked", "t/blocked", handshake=hs),
            _tier("bare", "t/bare"),
            _tier("gone", "t/gone"),
            _tier("gone_required", "t/gone_required", index="x.json", required=True),
            _tier("moved", "t/not_here", index="index.json"),
            {"name": "rootless", "about": "a tier with no root"},
        ],
    )
    t = repo / "t"
    write(t / "done" / "MANIFEST.csv", "path,bytes\na,1\nb,2\nc,3\n")
    write(t / "done" / "STATUS.json", json.dumps({"stage": "done", "done": True, "updated": "2026-11-21T00:00:00Z"}))
    write(t / "contours" / "MANIFEST.csv", "path,bytes\na,1\n")
    write(
        t / "contours" / "STATUS.json",
        json.dumps({"stage": "contours", "done": False, "blocked_on": None, "updated": "2026-11-06T05:35:34+00:00"}),
    )
    write(t / "no_index" / "README.md", "the index has not been written yet\n")
    write(t / "bad_json" / "index.json", '{"tiles": [1, 2')
    write(t / "vrt_gap" / "dem.vrt", VRT)
    write(t / "vrt_gap" / "a.tif", b"II*\x00")
    write(t / "vrt_full" / "dem.vrt", VRT)
    write(t / "vrt_full" / "a.tif", b"II*\x00")
    write(t / "vrt_full" / "b.tif", b"II*\x00")
    (t / "empty_dir" / "alignments").mkdir(parents=True)
    write(t / "no_status" / "data.bin", b"x")
    write(t / "blocked" / "STATUS.json", json.dumps({"stage": "blocked", "done": False, "blocked_on": "sheet s017"}))
    (t / "bare").mkdir(parents=True)
    write(t / "elsewhere" / "index.json", json.dumps([{"id": 1}, {"id": 2}]))
    # local.json moves one tier's root on this machine only
    write(repo / "configs" / "local.json", json.dumps({"tiers": {"moved": {"root": str(t / "elsewhere")}}}))
    return repo


def test_tiers_report_present_partial_missing(tmp_path):
    repo = _fixture_repo(tmp_path)
    cfg = paths.load_config(repo)
    reports = tiers.scan(cfg)
    assert list(reports) == [
        "done",
        "contours",
        "no_index",
        "bad_json",
        "vrt_gap",
        "vrt_full",
        "empty_dir",
        "no_status",
        "blocked",
        "bare",
        "gone",
        "gone_required",
        "moved",
        "rootless",
    ]
    status = {name: r.status for name, r in reports.items()}
    assert status == {
        "done": "present",
        "contours": "partial",
        "no_index": "partial",
        "bad_json": "partial",
        "vrt_gap": "partial",
        "vrt_full": "present",
        "empty_dir": "partial",
        "no_status": "partial",
        "blocked": "partial",
        "bare": "partial",
        "gone": "missing",
        "gone_required": "missing",
        "moved": "present",
        "rootless": "missing",
    }

    # the detail says why, in the words the status chips and the tier event carry
    assert reports["done"].detail == "MANIFEST.csv 3 rows; stage done"
    assert reports["contours"].detail == "stage contours"
    assert reports["contours"].handshake == {
        "file": "STATUS.json",
        "done": False,
        "detail": "contours",
        "updated": "2026-11-06T05:35:34+00:00",
        "blocked_on": None,
    }
    assert reports["no_index"].detail == "index index.json missing"
    assert reports["bad_json"].detail.startswith("index index.json unreadable:")
    assert reports["vrt_gap"].detail == "dem.vrt names 1 missing file(s): b.tif"
    assert reports["vrt_full"].detail == "dem.vrt 2 sources"
    assert reports["empty_dir"].detail == "index alignments/ is empty"
    assert reports["no_status"].detail == "handshake STATUS.json missing"
    assert reports["blocked"].detail == "stage blocked, blocked on sheet s017"
    assert reports["bare"].detail == "the root is empty"
    assert "t/gone" in reports["gone"].detail.replace("\\", "/")
    assert "configs/local.json" in reports["gone"].detail
    assert reports["moved"].detail == "index.json 2 items"
    assert Path(reports["moved"].root) == repo / "t" / "elsewhere"
    assert "no root" in reports["rootless"].detail

    # flags travel with the report; a missing required tier is what doctor fails on
    assert reports["done"].required and reports["no_index"].mount
    assert [r.name for r in tiers.required_missing(reports.values())] == ["gone_required"]
    assert tiers.counts(reports) == {"missing": 3, "partial": 8, "present": 3}

    # GET /tiers and the tier event
    body = tiers.as_json(reports)
    assert body["counts"] == tiers.counts(reports)
    by_name = {t["name"]: t for t in body["tiers"]}
    assert by_name["contours"]["uri"] == "tier://contours/"
    assert by_name["contours"]["findings"][1] == {
        "what": "handshake",
        "file": "STATUS.json",
        "ok": False,
        "detail": "stage contours",
    }
    json.dumps(body)  # all of it is JSON
    assert reports["contours"].event() == {"tier": "contours", "status": "partial", "detail": "stage contours"}


def test_tier_events_follow_changes(tmp_path):
    repo = _fixture_repo(tmp_path)
    cfg = paths.load_config(repo)
    first = tiers.scan(cfg)
    assert len(tiers.changes(None, first)) == len(first)  # the first scan announces every tier
    assert tiers.changes(first, tiers.scan(cfg)) == []  # nothing changed, nothing sent

    # lane B finishes the contours stage and says done: one event, present
    status = repo / "t" / "contours" / "STATUS.json"
    status.write_text(json.dumps({"stage": "done", "done": True}), encoding="utf-8")
    tiers.clear_cache()
    second = tiers.scan(cfg)
    assert second["contours"].status == "present"
    assert tiers.changes(first, second) == [
        {"tier": "contours", "status": "present", "detail": "MANIFEST.csv 1 row; stage done"}
    ]

    # a tier taken out of the config is announced as missing
    cfg["tiers"].pop("bare")
    third = tiers.scan(cfg)
    assert {"tier": "bare", "status": "missing", "detail": "no longer declared in the config"} in tiers.changes(
        second, third
    )


def test_unsafe_tier_file_names_are_refused(tmp_path):
    repo = tmp_path / "repo"
    make_repo(repo, [_tier("sneaky", "t/sneaky", index="../../outside.json"), _tier("dev", "t/dev", manifest="CON")])
    write(repo / "t" / "sneaky" / "x", "x")
    write(repo / "t" / "dev" / "x", "x")
    write(tmp_path / "outside.json", "{}")
    reports = tiers.scan(paths.load_config(repo))
    assert reports["sneaky"].status == "partial" and "refused" in reports["sneaky"].detail
    assert reports["dev"].status == "partial" and "refused" in reports["dev"].detail


def test_this_repo_scans_and_the_required_tiers_are_here():
    reports = tiers.scan()
    assert set(reports) == set(paths.config()["tiers"])
    for r in reports.values():
        assert r.status in tiers.STATUSES and r.detail
    # the required tiers are in git, so every clone has them
    assert tiers.required_missing(reports.values()) == []
    # the 1912 surface reads its handshake whatever stage lane B is at
    hs = reports["ground_1912_real"].handshake
    assert hs is not None and hs["file"] == "STATUS.json" and isinstance(hs["done"], bool)


def test_module_prints_the_scan():
    out = subprocess.run(
        [sys.executable, "-m", "region.tiers", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=paths.repo_root(),
        check=True,
    ).stdout
    body = json.loads(out)
    assert {t["name"] for t in body["tiers"]} == set(paths.config()["tiers"])


def test_a_tier_entry_that_is_not_an_object_is_reported_not_raised(tmp_path):
    repo = _fixture_repo(tmp_path)
    # a common slip in local.json: {"tiers": {"done": "D:/cr/root/done"}} instead of {"done": {"root": ...}}
    write(repo / "configs" / "local.json", json.dumps({"tiers": {"done": "D:/cr/root/done", "bare": 7}}))
    reports = tiers.scan(paths.load_config(repo))
    assert reports["done"].status == "missing" and "not an object" in reports["done"].detail
    assert reports["bare"].status == "missing"
    assert reports["contours"].status == "partial" and reports["vrt_full"].status == "present"  # the rest still scan
    json.dumps(tiers.as_json(reports))
