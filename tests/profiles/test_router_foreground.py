"""The sheet's reads of a section hold the scheduler's foreground over their store reads (I2.1, found by
``app/e2e/sheet.spec.ts`` "second context updates within 1 s"): background planning (a sheet's run chain) stops at
its next step while they run, so another tab following Ben's save is not kept waiting behind it. The region ground's
plan and ask are left outside the hold, so a plan the request makes itself never waits on a background plan."""

from __future__ import annotations

import contextlib

import pytest

fastapi = pytest.importorskip("fastapi")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from region.ext.profiles import router as profiles_router  # noqa: E402
from tests.importers.helpers import read_only, section_of  # noqa: E402

BASE = "/api/v1/x/profiles"


class Jobs:
    """A scheduler with a foreground only: how many holds are on now."""

    def __init__(self) -> None:
        self.held = 0

    @contextlib.contextmanager
    def foreground(self):
        self.held += 1
        try:
            yield
        finally:
            self.held -= 1


@pytest.mark.parametrize(
    ("path", "fn"),
    [("input", "section_input"), ("stations", "station_input"), ("solve", "section_solve_input")],
)
def test_a_section_read_holds_the_foreground(monkeypatch, path, fn):
    jobs = Jobs()
    seen: list[int] = []
    orig = getattr(profiles_router, fn)

    def spy(*a, **k):
        seen.append(jobs.held)
        return orig(*a, **k)

    monkeypatch.setattr(profiles_router, fn, spy)
    app = FastAPI()
    app.include_router(profiles_router.router, prefix=BASE)
    with read_only() as store:
        app.state.store = store
        app.state.jobs = jobs
        sec = section_of(store, "Line_6")
        with TestClient(app) as c:
            r = c.get(f"{BASE}/sections/{sec['id']}/{path}", params={"layer": "main"})
    assert r.status_code == 200, r.text
    assert seen == [1], "the read ran without the foreground"
    assert jobs.held == 0
