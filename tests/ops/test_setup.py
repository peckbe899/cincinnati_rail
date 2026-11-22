"""crhub setup (WP0b): the steps it plans on each kind of machine, and the ones it runs itself.

These tests never run uv, pip or npm: a fake runner records the commands. The migrate step runs for real, in a
test's own var folder.
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from region.cli import setup
from region.core import paths
from tests.ops.conftest import write

REPO = paths.repo_root()
FLAGS = ("dry_run", "skip_python", "skip_npm", "skip_build", "skip_migrate", "skip_imports", "no_doctor", "in_env")


def _args(**on: bool) -> argparse.Namespace:
    return argparse.Namespace(**{f: on.get(f, False) for f in FLAGS})


def _which(found: dict[str, str]):
    return lambda name: found.get(name)


def _repo(tmp_path: Path, *, app_src: bool = True) -> Path:
    repo = tmp_path / "cr test"  # a space, as on CI's Windows job
    write(repo / "package.json", "{}")
    if app_src:
        write(repo / "app" / "src" / "main.ts", "export {}\n")
    return repo


def test_with_uv_it_syncs_locked_and_inexact(tmp_path):
    repo = _repo(tmp_path)
    env_dir = repo / ".venv"
    p = setup.plan(
        _args(), repo=repo, environ={}, which=_which({"uv": "/bin/uv", "npm": "/bin/npm"}), prefix=str(env_dir)
    )
    assert [s.name for s in p.steps] == ["python", "npm", "build", "migrate", "imports", "doctor"]
    assert p.steps[0].argv == ["/bin/uv", "sync", "--locked", "--inexact"]
    assert p.steps[1].argv == ["/bin/npm", "ci"]
    assert p.steps[2].argv == ["/bin/npm", "run", "build", "-w", "app"]
    assert p.steps[3].action is setup.migrate_db
    assert p.reexec is None  # already running in the environment uv syncs


def test_uv_project_environment_is_honoured(tmp_path):
    repo = _repo(tmp_path)
    assert setup.uv_env_dir(repo, {"UV_PROJECT_ENVIRONMENT": "envs/hub"}) == repo / "envs" / "hub"
    assert setup.uv_env_dir(repo, {"UV_PROJECT_ENVIRONMENT": str(tmp_path / "x")}) == tmp_path / "x"
    assert setup.uv_env_dir(repo, {}) == repo / ".venv"


def test_without_uv_it_makes_a_venv_and_pip_installs_the_lock(tmp_path):
    repo = _repo(tmp_path)
    p = setup.plan(_args(), repo=repo, environ={}, which=_which({"npm": "/bin/npm"}), prefix=str(tmp_path / "sys"))
    py = str(setup.venv_python(repo / ".venv"))
    assert p.steps[0].argv == [sys.executable, "-m", "venv", str(repo / ".venv")]
    assert p.steps[1].argv == [py, "-m", "pip", "install", "-r", "requirements.lock", "-e", "."]
    # this process is not .venv's Python, so steps 4 to 6 run again there
    assert p.steps[-1].name == "env"
    assert p.reexec == [py, "-m", "region", "setup", "--in-env", "--skip-python", "--skip-npm", "--skip-build"]
    assert "migrate" not in [s.name for s in p.steps]


def test_a_venv_without_pip_gets_it_first(tmp_path):
    repo = _repo(tmp_path)
    py = setup.venv_python(repo / ".venv")
    write(py, "")
    p = setup.plan(_args(), repo=repo, environ={}, which=_which({}), prefix=str(repo / ".venv"))
    assert p.steps[0].argv == [str(py), "-m", "ensurepip", "--default-pip"]
    assert p.steps[1].argv[1:4] == ["-m", "pip", "install"]
    site = repo / ".venv" / ("Lib/site-packages/pip" if sys.platform == "win32" else "lib/python3.12/site-packages/pip")
    site.mkdir(parents=True)
    p = setup.plan(_args(), repo=repo, environ={}, which=_which({}), prefix=str(repo / ".venv"))
    assert p.steps[0].argv[1:4] == ["-m", "pip", "install"]


def test_build_is_skipped_until_app_src_exists_and_flags_skip(tmp_path):
    repo = _repo(tmp_path, app_src=False)
    p = setup.plan(_args(), repo=repo, environ={}, which=_which({"uv": "uv", "npm": "npm"}), prefix=str(repo / ".venv"))
    build = next(s for s in p.steps if s.name == "build")
    assert build.argv is None and "app/src does not exist yet" in build.describe()

    p = setup.plan(
        _args(skip_python=True, skip_npm=True, skip_build=True, skip_migrate=True, skip_imports=True, no_doctor=True),
        repo=repo,
        environ={},
        which=_which({"uv": "uv", "npm": "npm"}),
    )
    assert all(s.skip for s in p.steps)
    assert setup.execute(p, runner=lambda *a: pytest.fail("nothing should run")) == 0


def test_npm_missing_stops_setup_with_a_hint(tmp_path, capsys):
    repo = _repo(tmp_path)
    p = setup.plan(_args(skip_python=True), repo=repo, environ={}, which=_which({}))
    assert setup.execute(p, runner=lambda *a: 0) == 127
    err = capsys.readouterr().err
    assert "stopped at step 2 (npm)" in err and "nodejs.org" in err


def test_execute_runs_in_order_and_stops_at_the_first_failure(tmp_path, capsys):
    repo = _repo(tmp_path)
    p = setup.plan(
        _args(skip_migrate=True, skip_imports=True, no_doctor=True),
        repo=repo,
        environ={},
        which=_which({"uv": "uv", "npm": "npm"}),
        prefix=str(repo / ".venv"),
    )
    ran: list[tuple[list[str], Path, str]] = []

    def runner(argv, cwd, env):
        ran.append((list(argv), cwd, env.get("PYTHONUTF8", "")))
        return 3 if argv[:2] == ["npm", "ci"] else 0

    assert setup.execute(p, runner=runner) == 3
    assert [r[0][:2] for r in ran] == [["uv", "sync"], ["npm", "ci"]]  # the build never ran
    assert all(cwd == repo and utf8 == "1" for _, cwd, utf8 in ran)
    err = capsys.readouterr().err
    assert "stopped at step 2 (npm): exit code 3" in err and "node_modules" in err


def test_dry_run_runs_nothing():
    done = subprocess.run(
        [sys.executable, "-m", "region", "setup", "--dry-run"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    assert "dry run: nothing was run" in done.stdout
    assert "npm" in done.stdout and "ci" in done.stdout


@pytest.fixture(autouse=True)
def _no_hub_on_the_real_port(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ben may run the tests beside his own hub on 8766. Only the tests that start a fake hub may see a serving hub;
    every other test here sees none, so a real hub on the machine cannot fail them."""
    if "fake_hub" not in request.fixturenames:
        monkeypatch.setattr(setup, "hub_serving", lambda cfg=None: None)


def test_migrate_backs_up_an_older_database_first(hub_var, capsys):
    pytest.importorskip("region.model.migrate")
    from region.model.db import connect
    from region.model.migrate import current_version, discover, migrate

    versions = [m.version for m in discover()]
    if len(versions) < 2:
        pytest.skip("only one migration exists, so no database can be older than the newest")
    con = connect(hub_var / "region.db")
    migrate(con, target=versions[-2])  # a database one migration behind
    con.close()

    assert setup.migrate_db() == 0
    out = capsys.readouterr().out
    assert f"from schema {versions[-2]} to {versions[-1]}" in out
    backups = list((hub_var / "backups").glob("region-*-pre-migrate.db"))
    assert len(backups) == 1  # the checked copy taken before the migration
    con = sqlite3.connect(backups[0])
    try:
        assert current_version(con) == versions[-2]
    finally:
        con.close()


def test_migrate_creates_the_database_then_is_up_to_date(hub_var, capsys):
    pytest.importorskip("region.model.migrate")
    assert setup.migrate_db() == 0
    assert (hub_var / "region.db").is_file()
    assert "created" in capsys.readouterr().out
    assert setup.migrate_db() == 0
    assert "up to date" in capsys.readouterr().out
    assert not (hub_var / "backups").exists() or not any((hub_var / "backups").iterdir())  # nothing was pending


def test_migrate_refuses_while_a_hub_is_serving(hub_var, fake_hub, capsys):
    pytest.importorskip("region.model.migrate")
    cfg = paths.config()
    cfg["port"] = fake_hub
    assert setup.migrate_db(cfg) == 1
    assert "stop it before migrating" in capsys.readouterr().err
    assert not (hub_var / "region.db").exists()


def test_migrate_and_imports_skip_while_their_packages_are_missing(hub_var, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "region.model.migrate", None)  # import fails as if WP1 had not landed
    assert setup.migrate_db() == 0
    assert "region.model is not in this checkout yet" in capsys.readouterr().out
    assert not (hub_var / "region.db").exists()

    monkeypatch.setitem(sys.modules, "region.cli.imports", None)
    assert setup.first_imports() == 0
    assert "skipped" in capsys.readouterr().out


def test_a_step_that_raises_stops_setup_with_its_reason(tmp_path, capsys):
    def broken() -> int:
        raise PermissionError("var is read-only")

    p = setup.Plan(repo=tmp_path, steps=[setup.Step("migrate", "migrate", action=broken, hint="see var/backups")])
    assert setup.execute(p, runner=lambda *a: 0) == 1
    err = capsys.readouterr().err
    assert "migrate failed: PermissionError: var is read-only" in err and "see var/backups" in err


def test_setup_refuses_to_start_while_a_hub_is_serving(fake_hub, monkeypatch, capsys):
    real = paths.config

    def cfg():
        c = real()
        c["port"] = fake_hub
        return c

    monkeypatch.setattr(paths, "config", cfg)
    assert setup.hub_serving() == f"http://127.0.0.1:{fake_hub}"
    ran = []
    monkeypatch.setattr(setup, "execute", lambda *a, **k: ran.append(a) or 0)
    assert setup.run(_args()) == 1
    assert ran == []  # not one step ran
    assert "stop it first" in capsys.readouterr().err


def test_setup_says_so_when_the_config_cannot_be_read(monkeypatch, capsys):
    def broken(cfg=None):
        raise ValueError("Expecting ',' delimiter: line 3 column 5 (char 41)")

    monkeypatch.setattr(setup, "hub_serving", broken)
    monkeypatch.setattr(setup, "execute", lambda *a, **k: pytest.fail("no step may run"))
    assert setup.run(_args()) == 1
    err = capsys.readouterr().err
    assert "the config cannot be read" in err and "configs/local.json" in err


def test_a_store_that_is_here_but_broken_stops_setup(hub_var, monkeypatch, capsys):
    """Only a store that is not in the checkout is skipped; one that fails to import is an error, never a skip."""
    pytest.importorskip("region.model.migrate")
    # region.model.migrate is here, but a module the step needs cannot be imported (a missing package, a bug)
    monkeypatch.setitem(sys.modules, "region.model.db", None)
    p = setup.Plan(repo=REPO, steps=[setup.Step("migrate", "migrate", action=setup.migrate_db, hint="see above")])
    assert setup.execute(p, runner=lambda *a: 0) == 1
    assert "migrate failed: ModuleNotFoundError" in capsys.readouterr().err
    assert not (hub_var / "region.db").exists()

    import region.model
    from region.cli import doctor

    monkeypatch.setitem(sys.modules, "region.model.backup", None)
    monkeypatch.delattr(region.model, "backup", raising=False)  # else "from region.model import backup" finds it
    row = doctor.check_database(paths.config())[0]
    assert row.status == "fail" and "cannot be loaded" in row.detail and "crhub setup" in row.hint


def test_setup_stops_when_another_program_runs_from_the_venv(tmp_path, capsys):
    """windows-3: the old hub runs from the repo's .venv and holds numpy's .pyd; pip would fail with WinError 5 and
    the hint blamed the network. Setup now says what holds the environment before it runs pip or uv."""
    repo = _repo(tmp_path)
    venv = repo / ".venv"
    py = setup.venv_python(venv)
    write(py, "")
    (venv / ("Lib/site-packages/pip" if sys.platform == "win32" else "lib/python3.12/site-packages/pip")).mkdir(
        parents=True
    )
    old_hub = [(4242, 1, str(py)), (4343, 1, str(tmp_path / "elsewhere" / "python.exe"))]
    for which in ({}, {"uv": "/bin/uv"}):
        steps, _env = setup.python_steps(repo, {}, _which(which), processes=lambda: old_hub)
        p = setup.Plan(repo=repo, steps=steps)
        ran: list[list[str]] = []

        def runner(argv, cwd, env, ran=ran):
            ran.append(list(argv))
            return 0

        assert setup.execute(p, runner=runner) == 1
        err = capsys.readouterr().err
        assert ran == [] and "pid 4242" in err and "4343" not in err and "Ctrl+C" in err, err
    # with nothing else running from it, the step runs as before
    steps, _env = setup.python_steps(repo, {}, _which({}), processes=lambda: [(4343, 1, "C:/other/python.exe")])
    ran = []
    assert setup.execute(setup.Plan(repo=repo, steps=steps), runner=lambda argv, cwd, env: ran.append(argv) or 0) == 0
    assert ran and ran[0][1:4] == ["-m", "pip", "install"]
    assert "WinError 5" in steps[-1].hint
