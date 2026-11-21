"""The CI workflow (section 9, CI) has the jobs the spec names, and the tree passes the hygiene job's rules."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from region.core import fsio, paths

REPO = paths.repo_root()
WORKFLOW = REPO / ".github" / "workflows" / "hub.yml"
MAX_BYTES = 25 * 1024 * 1024


def _workflow() -> dict:
    doc = fsio.read_yaml(WORKFLOW)
    assert isinstance(doc, dict)
    return doc


def _commands(job: dict) -> str:
    return "\n".join(str(step.get("run", "")) for step in job["steps"])


def test_workflow_has_the_five_jobs():
    jobs = _workflow()["jobs"]
    assert list(jobs) == ["py", "engine", "e2e", "windows", "hygiene"]

    py = jobs["py"]
    assert py["runs-on"] == "ubuntu-latest"
    assert py["strategy"]["matrix"]["python"] == ["3.12", "3.13"]
    run = _commands(py)
    assert "uv lock --check" in run and "ruff check" in run and 'pytest -m "not slow and not local"' in run

    engine = jobs["engine"]
    assert engine["strategy"]["matrix"]["node"] == ["22.18", "24"]
    run = _commands(engine)
    assert "npm ci" in run and "typecheck -w engine" in run and "npm test -w engine" in run

    windows = jobs["windows"]
    assert windows["runs-on"].startswith("windows")
    assert windows["steps"][0]["with"]["path"] == "cr test"
    assert windows["defaults"]["run"]["working-directory"] == "cr test"
    run = _commands(windows)
    for area in ("tests/core", "tests/model", "tests/api", "tests/enginehost"):
        assert area in run
    assert "requirements.lock" in run and "crhub.cmd setup" in run

    run = _commands(jobs["hygiene"])
    assert "26214400" in run and "node_modules" in run and "region/seed" in run


def _git(*args: str) -> str:
    if not shutil.which("git"):
        pytest.skip("git is not installed")
    done = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        pytest.skip(f"not a git checkout: {done.stderr.strip()}")
    return done.stdout


def test_tree_passes_the_hygiene_rules():
    big = []
    for line in _git("ls-tree", "-r", "-l", "HEAD").splitlines():
        meta, _, name = line.partition("\t")
        fields = meta.split()
        if len(fields) == 4 and fields[1] == "blob" and int(fields[3]) > MAX_BYTES:
            big.append(name)
    assert big == [], f"files over 25 MiB in git: {big}"

    tracked = _git("ls-files").splitlines()
    banned = [
        f
        for f in tracked
        if f.endswith((".db", ".db-wal", ".db-shm", ".db-journal"))
        or any(part in ("var", "dist", "node_modules") for part in f.split("/")[:-1])
    ]
    assert banned == [], f"must not be in git: {banned}"

    crlf = [
        line
        for line in _git("ls-files", "--eol", "--", "region/seed").splitlines()
        if line.startswith(("i/crlf", "i/mixed"))
    ]
    assert crlf == [], f"region/seed must be LF: {crlf}"
