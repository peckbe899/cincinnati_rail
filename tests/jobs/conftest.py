"""Fixtures for the jobs tests: a scheduler factory over a fake store, with writes allowed under ``tmp_path``."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from region.jobs.scheduler import Scheduler
from tests.jobs import jobtypes
from tests.jobs.fakes import FakeStore


@pytest.fixture(autouse=True)
def _reset_counters() -> Iterator[None]:
    jobtypes.reset()
    yield
    jobtypes.reset()


@pytest.fixture
def cache_path(write_root: Path) -> Path:
    return write_root / "var" / "cache" / "cache.db"


@pytest.fixture
def make_sched(cache_path: Path) -> Iterator[Callable[..., Scheduler]]:
    """``make_sched(store=None, engine=None, start=True, **kwargs)``: a scheduler on the test's cache, stopped at the
    end of the test. Polls the outbox every 20 ms."""
    made: list[Scheduler] = []

    def make(
        store: Any = None, engine: Any = None, *, start: bool = True, path: Path | None = None, **kwargs: Any
    ) -> Scheduler:
        kwargs.setdefault("poll_s", 0.02)
        kwargs.setdefault("registry", jobtypes.make_registry())
        sched = Scheduler(store if store is not None else FakeStore(), path or cache_path, engine, **kwargs)
        made.append(sched)
        return sched.start() if start else sched

    yield make
    for sched in made:
        sched.stop()
