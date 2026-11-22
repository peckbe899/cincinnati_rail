"""Shared pytest set-up for the whole suite.

- **Known failures.** Every node id listed in ``tests/known_failures.txt`` is marked ``xfail(strict=True)``, so it
  must keep failing; the day it passes the suite fails and the line must be removed.
- **Markers.** ``slow`` and ``local`` are declared in ``pyproject.toml``. CI runs ``-m "not slow and not local"``.
- **Fixtures for every package.** ``hub_var`` gives a test its own ``var`` folder (``CRHUB_VAR``) with writes
  allowed there; ``write_root`` allows writes under ``tmp_path``.
- **No forced colour.** Every test runs without ``FORCE_COLOR`` (CI sets it), so the output of a child it starts
  is plain text.

Test folders are packages (``tests/__init__.py``, ``tests/<area>/__init__.py``), so a module is imported as
``tests.<area>.test_x`` and the same file name may appear in two folders. A new ``tests/<area>/`` needs its
``__init__.py``; helpers there are imported as ``from tests.<area>.fakes import ...``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

KNOWN_FAILURES = Path(__file__).resolve().parent / "known_failures.txt"


def load_known_failures(path: Path = KNOWN_FAILURES, platform: str | None = None) -> dict[str, str]:
    """``{node id: reason}`` from a known-failures file (blank lines and ``#`` comments skipped). A line that starts
    with ``[<platform>]`` (a ``sys.platform`` value, such as ``[win32]``) applies on that platform only."""
    import sys

    platform = sys.platform if platform is None else platform
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            body, _, reason = line.partition("#")
            node = body.strip()
            if node.startswith("["):
                only, _, node = node[1:].partition("]")
                node = node.strip()
                if only.strip() != platform:
                    continue
            if node:
                out[node] = reason.strip() or "listed in tests/known_failures.txt"
    return out


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    known = load_known_failures()
    if not known:
        return
    for item in items:
        reason = known.get(item.nodeid)
        if reason is not None:
            item.add_marker(pytest.mark.xfail(reason=f"known failure: {reason}", strict=True))


@pytest.fixture(autouse=True)
def _no_forced_colour(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test without ``FORCE_COLOR``. CI sets it for its logs (``.github/workflows/hub.yml``), and a child a
    test starts (node, npm) then colours its output even into a pipe, so a test that reads that output sees escape
    codes. Done here, so the old hub's tests (``tests/test_*.py``) stay untouched. pytest's own output keeps its
    colour: its terminal was set up before any test ran."""
    monkeypatch.delenv("FORCE_COLOR", raising=False)


@pytest.fixture
def write_root(tmp_path: Path):
    """Allow ``fsio`` writes under ``tmp_path`` for the test; yields ``tmp_path``."""
    from region.core import fsio

    with fsio.allow_writes(tmp_path):
        yield tmp_path


@pytest.fixture
def hub_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A fresh ``var`` folder for the test: ``CRHUB_VAR`` points at it and writes there are allowed."""
    from region.core import fsio, paths

    var = tmp_path / "var"
    var.mkdir()
    monkeypatch.setenv(paths.VAR_ENV, str(var))
    with fsio.allow_writes(var):
        yield var
