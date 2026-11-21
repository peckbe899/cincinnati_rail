"""Fixtures for the store's tests: a fresh store per test over the core kinds and the fixture kinds.

``tests/model/fixtures`` is laid out as a feature folder (``kinds/``, ``upgrade/``, ``validators.py``), so the store
finds its validator and upgraders the way it finds a real feature's.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from region.core import features
from region.core.view import View

FIXTURES = Path(__file__).resolve().parent / "fixtures"
KINDS = [features.CORE_KINDS, FIXTURES / "kinds"]


@pytest.fixture
def make_store(write_root: Path):
    """``make_store(name="region.db", **open_store kwargs)``; every store made is closed after the test."""
    from region.model import open_store

    opened = []

    def make(name: str = "region.db", **kw):
        kw.setdefault("kinds_paths", KINDS)
        s = open_store(write_root / name, **kw)
        opened.append(s)
        return s

    yield make
    for s in opened:
        s.close()


@pytest.fixture
def store(make_store):
    return make_store()


@pytest.fixture
def imp_layer(store):
    """The import layer of the ``test`` namespace, ``import:test``."""
    store.create_layer("import:test", namespace="test", by="test")
    return "import:test"


@pytest.fixture
def main() -> View:
    return View()
