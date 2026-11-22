"""Fixtures for the live hub's tests (checklist I2.0): a copy of the imported database, a copy of the line files
and of the 1912 tier's handshake that the test may write, a real engine pool, the scheduler and the live hub.

``env`` gives an ``Env``: ``edit(route, fn)`` rewrites one line file, ``solves()`` lists the solve jobs that ran since
``mark()``, ``imports()`` the applied import runs since then, and ``events`` every event the hub published.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from region.core import fsio, paths
from tests.api.conftest import api, client  # noqa: F401 (the server fixtures, for test_api)
from tests.importers import helpers as H

REPO = paths.repo_root()


def until(fn: Callable[[], Any], timeout: float = 20.0, what: str = "the condition") -> Any:
    deadline = time.monotonic() + timeout
    while True:
        got = fn()
        if got:
            return got
        if time.monotonic() > deadline:
            raise AssertionError(f"timed out waiting for {what}")
        time.sleep(0.02)


@dataclass
class Env:
    root: Path
    profile: Path
    ground: Path
    cfg: dict[str, Any]
    store: Any
    sched: Any
    live: Any
    events: list[tuple[float, str, dict[str, Any]]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    _mark: int = 0
    _run_mark: int = 0

    def record(self, kind: str, payload: dict[str, Any]) -> None:
        with self.lock:
            self.events.append((time.monotonic(), kind, dict(payload)))

    def line(self, route: str) -> Path:
        return self.profile / "lines" / f"{route}.json"

    def edit(self, route: str, fn: Callable[[dict[str, Any]], None]) -> None:
        f = self.line(route)
        doc = json.loads(f.read_text(encoding="utf-8"))
        fn(doc)
        f.write_text(json.dumps(doc), encoding="utf-8")

    def section(self, route: str) -> str:
        return H.section_of(self.store, route)["id"]

    def mark(self) -> None:
        """Count jobs and imports from here on (after the hub settled)."""
        assert self.settle(), "the hub did not settle"
        with self.lock:
            self._mark = len(self.events)
        row = self.store._reader().execute("SELECT COALESCE(MAX(id), 0) FROM import_run").fetchone()
        self._run_mark = int(row[0])

    def since(self, kind: str) -> list[tuple[float, dict[str, Any]]]:
        with self.lock:
            return [(t, p) for t, k, p in self.events[self._mark :] if k == kind]

    def solves(self, type: str = "profiles.solve_section") -> list[str]:
        """The scopes of the jobs of ``type`` that ran since ``mark()``, in the order they started."""
        out, seen = [], set()
        for _t, p in self.since("job"):
            if p.get("type") == type and p.get("state") == "running" and p["id"] not in seen:
                seen.add(p["id"])
                out.append(p["scope"])
        return out

    def imports(self, importer: str | None = None) -> list[dict[str, Any]]:
        con = self.store._reader()
        rows = con.execute(
            "SELECT id, importer, state, changeset FROM import_run WHERE id > ? AND dry_run = 0 ORDER BY id",
            (self._run_mark,),
        ).fetchall()
        return [
            {"id": r[0], "importer": r[1], "state": r[2], "changeset": r[3]}
            for r in rows
            if (importer is None or r[1] == importer) and r[2] == "applied"
        ]

    def settle(self, timeout: float = 60.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.live.wait_idle(0.5) and self.sched.wait_idle(5):
                time.sleep(0.1)
                if self.live.wait_idle(0.1) and self.sched._idle():
                    return True
        return False


@pytest.fixture(scope="module")
def pool() -> Iterator[Any]:
    if shutil.which("node") is None:
        pytest.skip("Node is not installed on this machine")
    from region.enginehost import Pool

    with Pool(size=2, timeout_s=30) as p:
        p.start()
        yield p


def make_env(
    root: Path, pool: Any, *, settle_s: float = 1.5, poll_s: float = 0.25, start: bool = True, hub_db: bool = False
) -> Env:
    from region.ext.rules.params import resolve
    from region.jobs.registry import default_registry
    from region.jobs.scheduler import Scheduler
    from region.live import Live
    from region.model import open_store
    from tests.live.jobtypes import GROUND

    profile = root / "profile"
    shutil.copytree(REPO / "data" / "profile", profile)
    ground = root / "ground_1912"
    ground.mkdir()
    for name in ("STATUS.json", "MANIFEST.csv"):
        shutil.copyfile(REPO / "ground" / "1912" / name, ground / name)
    H.copy_ledgers(root / "ids")
    H.copy_db(H.imported(), root / "region.db")
    # the whole process reads the tiers from the copies (the importers, the planner's file: refs, the tier scan)
    over = {
        "tiers": {"profile_lines": {"root": str(profile)}, "ground_1912_real": {"root": str(ground)}},
        "live": {"old_hub_db": str(root / "hub.db") if hub_db else None},
    }
    (root / "config.json").write_text(json.dumps(over), encoding="utf-8")
    os.environ[paths.CONFIG_ENV] = str(root / "config.json")
    paths.reload()
    cfg = paths.config()
    store = open_store(root / "region.db", cache=root / "var" / "cache.db")
    reg = default_registry()
    reg.register(GROUND)
    sched = Scheduler(store, root / "var" / "cache.db", pool, params=resolve, registry=reg, poll_s=0.05)
    env = Env(root=root, profile=profile, ground=ground, cfg=cfg, store=store, sched=sched, live=None)
    sched.subscribe(env.record)
    sched.start()
    env.live = Live(
        store,
        sched,
        cfg=cfg,
        publish=env.record,
        settle_s=settle_s,
        poll_s=poll_s,
        ledger_dir=root / "ids",
        work=root / "var" / "imports",
        state_path=root / "var" / "live" / "state.json",
    )
    if start:
        env.live.start()
    return env


def close_env(env: Env) -> None:
    env.live.stop()
    env.sched.stop()
    env.store.close()


@pytest.fixture
def env(hub_var: Path, tmp_path: Path, pool: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[Env]:
    """The live hub over a copy of the imported database, with the default settle period (1.5 s)."""
    root = tmp_path / "live"
    root.mkdir()
    H.imported()  # built with the repo's own config, before the test's takes over
    with monkeypatch.context() as m, fsio.allow_writes(root):
        m.delenv(paths.CONFIG_ENV, raising=False)
        e = make_env(root, pool)
        try:
            assert e.settle(), "the live hub did not settle after its start"
            yield e
        finally:
            close_env(e)
            os.environ.pop(paths.CONFIG_ENV, None)
    paths.reload()
