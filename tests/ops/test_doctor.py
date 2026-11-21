"""crhub doctor (WP0b): passes here, refuses a synced var, reports SQLite's R-tree and Node, and says why."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from region.cli import doctor
from region.core import paths
from tests.ops.conftest import link_dir, make_repo, write

REPO = paths.repo_root()


def _env(**extra: str) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env.update(extra)
    return env


def _by_name(checks: list[doctor.Check]) -> dict[str, doctor.Check]:
    return {c.name: c for c in checks}


def _cfg_with(**members) -> dict:
    cfg = paths.config()
    cfg.update(members)
    return cfg


# ------------------------------------------------------------------------------------------------------ exit tests


def test_doctor_passes_here(hub_var):
    checks = doctor.run_checks()
    failing = [c for c in checks if c.status == "fail"]
    assert failing == [], doctor.render(checks)
    rows = _by_name(checks)
    for name in ("python", "packages", "sqlite", "rtree", "node", "npm", "var", "var write", "app", "database"):
        assert name in rows, f"doctor has no {name} row"
    assert f"port {paths.config()['port']}" in rows
    assert {f"tier {t}" for t in paths.config()["tiers"]} <= set(rows)
    assert rows["var"].status == "ok" and str(hub_var) in rows["var"].detail
    assert list(hub_var.iterdir()) == []  # the write probe was removed again

    # the command itself: a short table, exit code 0
    done = subprocess.run(
        [sys.executable, "-m", "region", "doctor"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO,
        env=_env(CRHUB_VAR=str(hub_var)),
        timeout=120,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "FAIL" not in done.stdout
    assert "the hub can run here" in done.stdout.splitlines()[-1]
    assert len(done.stdout.splitlines()) < 50  # short

    js = subprocess.run(
        [sys.executable, "-m", "region", "doctor", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO,
        env=_env(CRHUB_VAR=str(hub_var)),
        timeout=120,
    )
    body = json.loads(js.stdout)
    assert body["ok"] is True and {c["name"] for c in body["checks"]} >= {"rtree", "node", "var"}


SYNCED = [
    ("OneDrive", lambda base, env: (base / "OneDrive" / "CincinnatiRail" / "hub", env)),
    ("OneDrive", lambda base, env: (base / "OneDrive - Contoso" / "hub", env)),
    ("OneDrive", lambda base, env: (base / "Ben" / "Documents" / "hub", {**env, "OneDrive": str(base / "Ben")})),
    ("OneDrive", lambda base, env: _marked(base / "od", ".849C9593-D756-4E56-8D6E-42412F2A707B", env)),
    ("Dropbox", lambda base, env: (base / "Dropbox" / "hub", env)),
    ("Dropbox", lambda base, env: _marked(base / "box", ".dropbox", env)),
    ("Dropbox", lambda base, env: _dropbox_info(base, env)),
    ("Google Drive", lambda base, env: (base / "G" / "My Drive" / "hub", env)),
    ("Google Drive", lambda base, env: _marked(base / "gd", ".tmp.drivedownload", env)),
    ("iCloud", lambda base, env: (base / "iCloudDrive" / "hub", env)),
    ("iCloud", lambda base, env: (base / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "hub", env)),
]


def _marked(root: Path, marker: str, env):
    write(root / marker, "")
    return root / "work" / "hub", env


def _dropbox_info(base: Path, env):
    appdata = base / "AppData" / "Roaming"
    synced = base / "Team Files"
    write(appdata / "Dropbox" / "info.json", json.dumps({"business": {"path": str(synced), "host": 1}}))
    return synced / "hub", {**env, "APPDATA": str(appdata)}


def _clean_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in doctor.ONEDRIVE_ENV and k not in ("APPDATA", "LOCALAPPDATA")}
    env["HOME"] = env["USERPROFILE"] = "/nonexistent-home-for-doctor-tests"
    return env


@pytest.mark.parametrize("client,make", SYNCED, ids=[f"{c}-{i}" for i, (c, _) in enumerate(SYNCED)])
def test_doctor_refuses_synced_var(tmp_path, monkeypatch, client, make):
    var, env = make(tmp_path, _clean_env())
    reason = doctor.synced_folder(var, env)
    assert reason is not None, f"{var} should read as synced by {client}"

    monkeypatch.setenv(paths.VAR_ENV, str(var))
    rows = doctor.check_var(paths.config(), env)
    assert [r.name for r in rows] == ["var", "var write"]
    assert rows[0].status == "fail" and "synced folder" in rows[0].detail and reason in rows[0].detail
    assert "configs/local.json" in rows[0].hint and "CRHUB_VAR" in rows[0].hint
    assert rows[1].status == "skip"
    assert not var.exists()  # nothing was written into the synced folder


def test_doctor_refuses_synced_var_through_the_command(tmp_path):
    var = tmp_path / "OneDrive" / "CincinnatiRail" / "hub"
    done = subprocess.run(
        [sys.executable, "-m", "region", "doctor"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO,
        env=_env(CRHUB_VAR=str(var)),
        timeout=120,
    )
    assert done.returncode == 1, done.stdout
    line = next(x for x in done.stdout.splitlines() if " var " in f" {x} " and "FAIL" in x)
    assert "synced folder" in line and "OneDrive" in line
    assert "problem the hub cannot run with" in done.stdout.splitlines()[-1]
    assert not var.exists()


def test_local_folders_are_not_synced(tmp_path):
    env = _clean_env()
    assert doctor.synced_folder(tmp_path / "AppData" / "Local" / "CincinnatiRail" / "hub", env) is None
    assert doctor.synced_folder(tmp_path / "Documents" / "drive-notes" / "hub", env) is None


def test_doctor_reports_rtree_and_node():
    checks = _by_name(doctor.run_checks())
    rtree = checks["rtree"]
    assert rtree.status == "ok" and "R-tree" in rtree.detail and sqlite3.sqlite_version in rtree.detail
    sqlite_row = checks["sqlite"]
    assert sqlite_row.status == "ok" and sqlite3.sqlite_version in sqlite_row.detail
    node = checks["node"]
    version = subprocess.run(
        [shutil.which("node") or "node", "--version"], capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()
    assert node.status == "ok" and version in node.detail and "strips TypeScript types" in node.detail


def test_rtree_missing_fails_with_a_hint():
    class NoRtree(sqlite3.Connection):
        def execute(self, sql, *args):
            if "USING rtree" in sql:
                raise sqlite3.OperationalError("no such module: rtree")
            return super().execute(sql, *args)

    rows = _by_name(doctor.check_sqlite(lambda name: sqlite3.connect(name, factory=NoRtree)))
    assert rows["sqlite"].status == "ok"
    assert rows["rtree"].status == "fail" and "no such module: rtree" in rows["rtree"].detail
    assert "python.org" in rows["rtree"].hint
    assert doctor.exit_code(list(rows.values())) == 1


def _fake_node(version: str, probe: tuple[int, str] = (0, "ts 1 strip")):
    calls: list[list[str]] = []

    def runner(argv):
        calls.append(list(argv))
        if argv[1:] == ["--version"]:
            return 0, version + "\n"
        if argv[1] == "--input-type=module-typescript":
            return probe
        return 1, "unexpected"

    return runner, calls


def test_node_missing_old_or_without_type_stripping_fails(tmp_path):
    node_file = write(tmp_path / "bin" / ("node.exe" if sys.platform == "win32" else "node"), "")
    cfg = _cfg_with(engine={"node": str(node_file), "node_min": "22.18"})

    runner, calls = _fake_node("v22.23.4")
    ok = doctor.check_node(cfg, runner)
    assert ok.status == "ok" and "v22.23.4" in ok.detail and "24 LTS recommended" in ok.detail
    assert calls[1][1:3] == ["--input-type=module-typescript", "-e"]

    runner, _ = _fake_node("v24.11.0")
    assert "recommended" not in doctor.check_node(cfg, runner).detail

    runner, _ = _fake_node("v20.11.1")
    old = doctor.check_node(cfg, runner)
    assert old.status == "fail" and "older than 22.18" in old.detail and "nodejs.org" in old.hint

    runner, _ = _fake_node("v22.17.0")
    assert doctor.check_node(cfg, runner).status == "fail"

    runner, _ = _fake_node("v23.3.0", (9, "node: bad option: --input-type=module-typescript"))
    nots = doctor.check_node(cfg, runner)
    assert nots.status == "fail" and "did not strip TypeScript types" in nots.detail and "bad option" in nots.detail

    gone = doctor.check_node(_cfg_with(engine={"node": str(tmp_path / "no" / "node")}), runner)
    assert gone.status == "fail" and "Node not found" in gone.detail and "engine.node" in gone.hint


# ------------------------------------------------------------------------------------------------- the other checks


def test_python_version_and_bits():
    assert doctor.check_python((3, 12, 10), "py", 64).status == "ok"
    assert doctor.check_python((3, 13, 1), "py", 64).status == "ok"
    old = doctor.check_python((3, 11, 9), "py", 64)
    assert old.status == "fail" and "3.12" in old.detail
    assert doctor.check_python((3, 12, 10), "py", 32).status == "fail"


def test_packages_against_the_lock(tmp_path):
    write(
        tmp_path / "requirements.lock",
        "# header\nfastapi==1.0\n    # via x\nruff==0.9 ; python_version >= '3'\n"
        "colorama==0.4.6 ; sys_platform == 'nonexistent-os'\n",
    )
    write(tmp_path / "pyproject.toml", '[project]\nname = "x"\ndependencies = ["fastapi>=0.1", "numpy>=1"]\n')
    have = {"fastapi": "1.0", "ruff": "0.9"}
    assert doctor.check_packages(tmp_path, have.get).status == "ok"
    differ = doctor.check_packages(tmp_path, {"fastapi": "1.0", "ruff": "0.8"}.get)
    assert differ.status == "warn" and "ruff 0.8 (locked 0.9)" in differ.detail
    dev_missing = doctor.check_packages(tmp_path, {"fastapi": "1.0"}.get)
    assert dev_missing.status == "warn" and "ruff" in dev_missing.detail
    runtime_missing = doctor.check_packages(tmp_path, {"ruff": "0.9"}.get)
    assert runtime_missing.status == "fail" and "fastapi" in runtime_missing.detail
    assert "crhub setup" in runtime_missing.hint


def _npm_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    write(repo / "package.json", json.dumps({"workspaces": ["engine", "app"]}))
    write(repo / "engine" / "package.json", json.dumps({"name": "@cr/engine"}))
    write(repo / "app" / "package.json", json.dumps({"name": "@cr/app"}))
    lock = {
        "packages": {
            "": {},
            "node_modules/@cr/engine": {"resolved": "engine", "link": True},
            "node_modules/@cr/app": {"resolved": "app", "link": True},
            "node_modules/zod": {"version": "4.6.7"},
            "node_modules/@esbuild/win32-x64": {"version": "0.25.0", "optional": True},
        }
    }
    write(repo / "package-lock.json", json.dumps(lock))
    link_dir(repo / "node_modules" / "@cr" / "engine", repo / "engine")
    link_dir(repo / "node_modules" / "@cr" / "app", repo / "app")
    hidden = {"packages": {"node_modules/zod": {"version": "4.6.7"}}}
    write(repo / "node_modules" / ".package-lock.json", json.dumps(hidden))
    return repo


def test_npm_workspaces_installed(tmp_path):
    repo = _npm_repo(tmp_path)

    def runner(argv):
        return 0, "10.9.9\n"

    ok = doctor.check_npm(repo, runner)
    assert ok.status in ("ok", "warn"), ok  # warn only when npm itself is not on PATH
    assert "engine and app linked" in ok.detail and "1 package matches" in ok.detail

    hidden = repo / "node_modules" / ".package-lock.json"
    hidden.write_text(json.dumps({"packages": {"node_modules/zod": {"version": "4.0.0"}}}), encoding="utf-8")
    stale = doctor.check_npm(repo, runner)
    assert stale.status == "warn" and "zod 4.0.0 (locked 4.6.7)" in stale.detail and "npm ci" in stale.hint

    hidden.write_text(json.dumps({"packages": {}}), encoding="utf-8")
    assert "1 missing (zod)" in doctor.check_npm(repo, runner).detail

    shutil.rmtree(repo / "node_modules")
    gone = doctor.check_npm(repo, runner)
    assert gone.status == "fail" and "node_modules is missing" in gone.detail


def test_npm_workspace_linked_to_another_checkout_fails(tmp_path):
    repo = _npm_repo(tmp_path)
    other = tmp_path / "old clone" / "engine"
    other.mkdir(parents=True)
    link = repo / "node_modules" / "@cr" / "engine"
    if link.is_symlink():
        link.unlink()
    else:
        os.rmdir(link)  # a junction
    link_dir(link, other)
    bad = doctor.check_npm(repo, lambda argv: (0, "10\n"))
    assert bad.status == "fail" and "@cr/engine points to" in bad.detail


def test_hub_port_free_busy_or_this_hub(busy_port, fake_hub, fake_old_hub):
    from tests.ops.conftest import free_port

    free = doctor.check_hub_port({"host": "127.0.0.1", "port": free_port()})
    assert free.status == "ok" and "free" in free.detail

    busy = doctor.check_hub_port({"host": "127.0.0.1", "port": busy_port})
    assert busy.status == "fail" and "another program" in busy.detail and "configs/local.json" in busy.hint

    ours = doctor.check_hub_port({"host": "127.0.0.1", "port": fake_hub})
    assert ours.status == "ok" and "the hub is serving" in ours.detail

    old_here = doctor.check_hub_port({"host": "127.0.0.1", "port": fake_old_hub})
    assert old_here.status == "fail" and "old hub" in old_here.detail


def test_old_hub_port_is_information_only(fake_old_hub, fake_hub):
    from tests.ops.conftest import free_port

    running = doctor.check_old_hub_port({"port": 8766, "old_hub": f"http://127.0.0.1:{fake_old_hub}"})
    assert running.status == "info" and "the old hub is running" in running.detail
    port = free_port()
    stopped = doctor.check_old_hub_port({"port": 8766, "old_hub": f"http://127.0.0.1:{port}"})
    assert stopped.status == "info" and "not running" in stopped.detail
    clash = doctor.check_old_hub_port({"port": 8765, "old_hub": "http://127.0.0.1:8765"})
    assert clash.status == "warn"
    swapped = doctor.check_old_hub_port({"port": 8766, "old_hub": f"http://127.0.0.1:{fake_hub}"})
    assert swapped.status == "warn" and "new hub" in swapped.detail


def test_tier_rows_fail_only_for_a_missing_required_tier(tmp_path):
    repo = tmp_path / "repo"
    make_repo(
        repo,
        [
            {"name": "need", "root": "t/need", "required": True},
            {"name": "want", "root": "t/want"},
            {"name": "half", "root": "t/half", "handshake": {"file": "STATUS.json", "detail": "stage"}},
            {"name": "half_need", "root": "t/hn", "index": "i.json", "required": True},
            {"name": "here", "root": "t/here", "index": "i.json"},
        ],
    )
    write(
        repo / "t" / "half" / "STATUS.json", json.dumps({"stage": "contours", "done": False, "updated": "2026-11-06"})
    )
    write(repo / "t" / "hn" / "x", "x")
    write(repo / "t" / "here" / "i.json", "[]")
    rows = _by_name(doctor.check_tiers(paths.load_config(repo)))
    assert rows["tier need"].status == "fail" and "configs/local.json" in rows["tier need"].hint
    assert rows["tier want"].status == "warn"
    assert rows["tier half"].status == "info"
    assert rows["tier half"].detail == "partial: stage contours (STATUS.json updated 2026-11-06)"
    assert rows["tier half_need"].status == "warn"
    assert rows["tier here"].status == "ok"


def test_app_build_present_and_not_older_than_source(tmp_path):
    repo = tmp_path / "repo"
    assert doctor.check_app(repo).status == "skip"  # no app/src yet

    src = write(repo / "app" / "src" / "main.ts", "export {}\n")
    missing = doctor.check_app(repo)
    assert missing.status == "fail" and "not built" in missing.detail and "npm run build -w app" in missing.hint

    built = write(repo / "app" / "dist" / "index.html", "<!doctype html>\n")
    old = time.time() - 3600
    os.utime(src, (old, old))
    assert doctor.check_app(repo).status == "ok"

    engine = write(repo / "engine" / "src" / "methods.ts", "export {}\n")
    os.utime(built, (old, old))
    os.utime(engine, (old + 600, old + 600))
    stale = doctor.check_app(repo)
    assert stale.status == "warn" and "engine/src/methods.ts" in stale.detail and "banner" in stale.hint
    state = doctor.app_build(repo)
    assert state["stale"] and state["newest"] == "engine/src/methods.ts"


def test_database_rows(hub_var):
    cfg = paths.config()
    assert _by_name(doctor.check_database(cfg))["database"].status == "info"
    pytest.importorskip("region.model.migrate")
    from region.model.db import connect
    from region.model.migrate import migrate

    con = connect(hub_var / "region.db")
    migrate(con, backup_dir=None)
    con.close()
    row = _by_name(doctor.check_database(cfg))["database"]
    assert row.status == "ok" and "quick_check ok" in row.detail

    write(hub_var / "broken.db", b"this is not a database at all" * 100)
    (hub_var / "region.db").unlink()
    (hub_var / "broken.db").rename(hub_var / "region.db")
    bad = _by_name(doctor.check_database(cfg))["database"]
    assert bad.status == "fail" and "crhub model restore" in bad.hint


def test_doctor_data_validates_a_copy_and_never_changes_the_database(hub_var, tmp_path):
    pytest.importorskip("region.model.migrate")
    from region.core import features, fsio
    from region.core.view import View
    from region.model import open_store

    # a record of a kind this checkout no longer declares: --data must find it
    kinds = tmp_path / "kinds"
    write(kinds / "t_ops.yaml", fsio.read_text(features.CORE_KINDS / "note.yaml").replace("kind: note", "kind: t_ops"))
    db = hub_var / "region.db"
    with open_store(db, kinds_paths=[features.CORE_KINDS, kinds], validators={}) as store:
        rec = store.put(
            {"kind": "t_ops", "id": None, "data": {"text": "a"}, "geom": None}, View(), if_match=None, by="t"
        )
    before = fsio.sha256_file(db)

    rows = _by_name(doctor.check_database(paths.config(), data=True))
    assert rows["database"].status == "ok"
    records = rows["records"]
    assert records.status == "fail" and rec["id"] in records.detail and "unknown kind" in records.detail

    # the live file is byte for byte the same: no migration, no kind table rewrite, no backup, no copy left behind
    assert fsio.sha256_file(db) == before
    con = sqlite3.connect(db)
    try:
        assert con.execute("SELECT name FROM kind WHERE name = 't_ops'").fetchall() == [("t_ops",)]
    finally:
        con.close()
    assert not (hub_var / "tmp").exists() and not (hub_var / "backups").exists()


def test_doctor_data_never_migrates(hub_var):
    pytest.importorskip("region.model.migrate")
    from region.model.db import connect
    from region.model.migrate import current_version, discover, migrate

    versions = [m.version for m in discover()]
    if len(versions) < 2:
        pytest.skip("only one migration exists, so no database can be older than the newest")
    con = connect(hub_var / "region.db")
    migrate(con, target=versions[-2])
    con.close()

    rows = _by_name(doctor.check_database(paths.config(), data=True))
    assert rows["database"].status == "warn" and "pending" in rows["database"].detail
    assert rows["records"].status == "skip" and "never migrates" in rows["records"].detail
    con = sqlite3.connect(hub_var / "region.db")
    try:
        assert current_version(con) == versions[-2]  # serve and setup migrate, after their backup; doctor does not
    finally:
        con.close()
    assert not (hub_var / "backups").exists()


def test_a_program_that_does_not_speak_http_is_another_program(banner_port):
    assert doctor.identify("127.0.0.1", banner_port) is None  # no crash on a banner instead of an HTTP reply
    hub = doctor.check_hub_port({"host": "127.0.0.1", "port": banner_port})
    assert hub.status == "fail" and "another program" in hub.detail
    old = doctor.check_old_hub_port({"port": 8766, "old_hub": f"http://127.0.0.1:{banner_port}"})
    assert old.status == "info" and "not by the old hub" in old.detail  # information only, never a failure


def test_the_dropbox_settings_folder_does_not_mark_home_as_synced(tmp_path):
    home = tmp_path / "home" / "ben"
    # on Linux and macOS the Dropbox client keeps its settings in ~/.dropbox, a folder
    write(home / ".dropbox" / "info.json", json.dumps({"personal": {"path": str(home / "Dropbox")}}))
    write(home / "Team Files" / ".dropbox", "{}")  # a synced root holds a .dropbox file
    env = {**_clean_env(), "HOME": str(home)}
    assert doctor.synced_folder(home / "src" / "cincinnati_rail" / "var", env) is None
    assert "Dropbox" in (doctor.synced_folder(home / "Dropbox" / "hub", env) or "")
    assert ".dropbox" in (doctor.synced_folder(home / "Team Files" / "hub", env) or "")


def test_windows_unc_and_extended_length_paths():
    assert doctor.windows_unc(r"\\server\share\hub") == (True, r"\\server\share\hub")
    assert doctor.windows_unc(r"\\?\UNC\server\share\hub") == (True, r"\\server\share\hub")
    assert doctor.windows_unc(r"\\?\C:\Users\Ben\AppData\Local\hub") == (False, r"C:\Users\Ben\AppData\Local\hub")
    assert doctor.windows_unc("C:/Users/Ben/hub") == (False, r"C:\Users\Ben\hub")


def test_a_broken_check_does_not_hide_the_others(monkeypatch, hub_var):
    def boom(*a, **k):
        raise RuntimeError("simulated")

    monkeypatch.setattr(doctor, "check_app", boom)
    checks = doctor.run_checks()
    rows = _by_name(checks)
    assert rows["app"].status == "fail" and "simulated" in rows["app"].detail
    assert rows["rtree"].status == "ok"  # the rest still ran


def test_render_is_a_short_table_with_hints():
    checks = [
        doctor.Check("python", "ok", "3.12.10"),
        doctor.Check("var", "fail", "in OneDrive", "move it"),
        doctor.Check("tier x", "info", "partial: stage contours"),
        doctor.Check("app", "warn", "stale", "rebuild"),
    ]
    text = doctor.render(checks)
    lines = text.splitlines()
    assert lines[0].split()[:2] == ["ok", "python"]
    assert lines[1].split()[:2] == ["FAIL", "var"]
    assert lines[2].strip() == "-> move it"
    assert "-> rebuild" in text
    assert lines[-1] == "1 ok, 1 warning(s), 1 failure(s): doctor found a problem the hub cannot run with"
    assert doctor.exit_code(checks) == 1
    assert doctor.exit_code(checks[2:]) == 0  # warnings and information never fail it
