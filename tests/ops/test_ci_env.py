"""CI runs with FORCE_COLOR=1 (``.github/workflows/hub.yml``); tests that read a child's output must not see colour."""

from __future__ import annotations

import os
import subprocess
import sys

from region.core import paths


def test_old_hub_chronology_test_passes_under_force_color() -> None:
    """node colours ``console.log(true)`` when FORCE_COLOR is set, which broke the old hub's chronology test in CI.
    ``tests/conftest.py`` drops FORCE_COLOR for every test, so that test passes as it is (it stays untouched). It runs
    here in a pytest of its own, with FORCE_COLOR=1 as CI sets it."""
    env = {**os.environ, "FORCE_COLOR": "1"}
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "tests/test_hub.py::test_chronology_months_and_timeline"],
        cwd=paths.REPO, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
    )  # fmt: skip
    assert run.returncode == 0, run.stdout[-3000:] + run.stderr[-2000:]
