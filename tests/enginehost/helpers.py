"""Helpers for the engine host's tests: the committed golden files and the stand-in sidecars."""

from __future__ import annotations

import sys
from pathlib import Path

from region.core import fsio, paths

HERE = Path(__file__).resolve().parent
GOLDEN = paths.REPO / "engine" / "test" / "golden"
FIXTURE_SIDECAR = HERE / "sidecar_fixture.mts"
FAKE_SIDECAR = HERE / "fake_sidecar.py"


def fake_sidecar_argv(*args: str) -> list[str]:
    """The command of tests/enginehost/fake_sidecar.py with ``args``."""
    return [sys.executable, str(FAKE_SIDECAR), *args]


def golden() -> dict:
    """engine/test/golden/vertical_rail.json."""
    return fsio.read_json(GOLDEN / "vertical_rail.json")


def golden_input(route: str) -> dict:
    """The committed SectionInput of a route (the 2 m grid)."""
    return fsio.read_json(GOLDEN / "inputs" / f"{route}.json")
