"""Fixtures for the engine host's tests: Node, a pool on the real sidecar and a pool on the misbehaving fixture
sidecar. Helpers (the golden files, the fake sidecar's command) are in tests/enginehost/helpers.py."""

from __future__ import annotations

import shutil
from collections.abc import Iterator

import pytest

from region.enginehost import Pool
from tests.enginehost.helpers import FIXTURE_SIDECAR


@pytest.fixture(scope="session")
def node() -> str:
    """The Node executable; the tests that run the engine skip where there is none."""
    exe = shutil.which("node")
    if exe is None:
        pytest.skip("Node is not installed on this machine")
    return exe


@pytest.fixture(scope="module")
def pool(node: str) -> Iterator[Pool]:
    """A pool of two real sidecars, shared by a module's tests."""
    with Pool(size=2, timeout_s=30, node=node) as p:
        p.start()
        yield p


@pytest.fixture
def fixture_pool(node: str) -> Iterator[Pool]:
    """A one-sidecar pool on tests/enginehost/sidecar_fixture.mts (the real loop plus test.hang, test.exit and
    test.progress), with a short timeout and a quick backoff."""
    with Pool(size=1, timeout_s=10, argv=[node, str(FIXTURE_SIDECAR)], backoff_s=(0.05, 0.2)) as p:
        yield p
