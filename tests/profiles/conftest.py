"""Fixtures for the profiles feature's tests: a pool of real engine sidecars (skipped where there is no Node)."""

from __future__ import annotations

import shutil
from collections.abc import Iterator

import pytest


@pytest.fixture(scope="module")
def pool() -> Iterator[object]:
    if shutil.which("node") is None:
        pytest.skip("Node is not installed on this machine")
    from region.enginehost import Pool

    with Pool(size=2, timeout_s=30) as p:
        p.start()
        yield p
