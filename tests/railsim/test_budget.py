"""Budgets of the railsim lane (plan section 1.7). Slow; like tests/perf, a number over its budget on a loaded CI
runner is a warning there, a failure here.

- ``railsim.run`` of Line 6, both directions, in a warm process: under 1.0 s; ``route.assemble`` under 200 ms;
  ``route.horizontal`` under 1.5 s;
- a draft, warm: under 1.5 s from the request to the answer;
- a saved PVI edit to the new ``railsim.run`` result through the scheduler, its chain warm: under 10 s (target 3 s).
"""

from __future__ import annotations

import statistics
import threading
import time
from typing import Any

import pytest

from region.core.view import View
from tests.importers.helpers import MAIN, all_records, fresh_copy, read_only, section_of
from tests.railsim.conftest import Chain, route_of

pytestmark = pytest.mark.slow


def _timed_run(ch: Chain, plan: Any, n: int = 5) -> float:
    """The median seconds of ``n`` runs of a planned job, in this process (as its warm worker runs it)."""
    from region.jobs.hosts import NoEngine, RunContext

    jt = ch.reg.get(plan.type)
    upstream = {ref: ch.results[key] for ref, key in plan.upstream_keys.items()}
    eng = ch.engine if jt.host == "engine" else NoEngine()
    times = []
    for _ in range(n):
        t = time.perf_counter()
        jt.run(plan.inputs, RunContext(eng, lambda f, m: None, threading.Event(), upstream))
        times.append(time.perf_counter() - t)
    return statistics.median(times)


def test_warm_job_costs(pool):
    with read_only() as store:
        rid = route_of(store, "Line_6")["id"]
        sid = section_of(store, "Line_6")["id"]
        ch = Chain(store, pool)
        ch.compute("railsim.run", rid, MAIN)
        run = _timed_run(ch, ch.plan("railsim.run", rid, MAIN))
        asm = _timed_run(ch, ch.plan("route.assemble", rid, MAIN))
        fit = _timed_run(ch, ch.plan("route.horizontal", sid, MAIN), n=3)
    print(f"railsim.run {run * 1000:.0f} ms, route.assemble {asm * 1000:.0f} ms, route.horizontal {fit * 1000:.0f} ms")
    assert run < 1.0
    assert asm < 0.2
    assert fit < 1.5


def test_a_saved_pvi_edit_reaches_the_run_and_a_draft_is_quick(pool, tmp_path_factory):
    from fastapi.testclient import TestClient

    from region.core import fsio
    from region.ext.rules.params import resolve
    from region.jobs import Scheduler
    from tests.railsim.test_draft import BASE, H, _app

    root = tmp_path_factory.mktemp("budget")
    with fsio.allow_writes(root):
        store = fresh_copy(root)
        store.create_layer("try", tier="scenario", parent="main", by="ben")
        view = View(layer="try")
        sched = Scheduler(store, root / "cache" / "cache.db", pool, params=resolve, poll_s=0.05).start()
        try:
            rid = route_of(store, "Line_6", view)["id"]
            sid = section_of(store, "Line_6")["id"]
            sched.watch_goal("profiles.solve_section", sid, view, priority=0, ttl_s=600)
            sched.watch_goal("railsim.run", rid, view, priority=2, ttl_s=600)
            deadline = time.monotonic() + 400
            while sched.result("railsim.run", rid, view) is None:
                assert time.monotonic() < deadline, "the chain did not finish"
                time.sleep(1.0)
            took = []
            for rep in range(3):
                k0 = sched.cache.one(
                    "SELECT latest_key FROM goal WHERE type = 'railsim.run' AND scope = ? AND view = ?",
                    (rid, view.token()),
                )[0]
                prof = all_records(store, "profile", view, parent=sid)[0]
                k = len(prof["data"]["pvi"]) // 2
                z = prof["data"]["pvi"][k][1]
                t = time.monotonic()
                store.patch(
                    "profile",
                    prof["id"],
                    [{"op": "replace", "path": f"/data/pvi/{k}/1", "value": z + (2.0 if rep % 2 == 0 else -2.0)}],
                    view,
                    if_match=f'"{prof["layer"]}:{prof["version"]}"',
                    by="ben",
                )
                sched.notify()
                while True:
                    row = sched.cache.one(
                        "SELECT latest_key FROM goal WHERE type = 'railsim.run' AND scope = ? AND view = ?",
                        (rid, view.token()),
                    )
                    if row and row[0] != k0:
                        break
                    assert time.monotonic() - t < 60, "the run did not follow the edit"
                    time.sleep(0.05)
                took.append(time.monotonic() - t)
            app, rs = _app(store, sched, pool)
            q = {"layer": "try"}
            with TestClient(app) as c:
                si = c.get(f"{BASE}/profiles/sections/{sid}/input", params=q).json()
                drafts = []
                for rep in range(4):
                    body = dict(si, pvi=[dict(p) for p in si["pvi"]])
                    body["pvi"][len(body["pvi"]) // 2]["z_m"] += 1.0 + rep
                    t = time.perf_counter()
                    r = c.post(
                        f"{BASE}/railsim/sections/{sid}/draft", params=q, json={"section_input": body}, headers=H
                    )
                    drafts.append(time.perf_counter() - t)
                    assert r.status_code == 200, r.text
            rs.draft_runner.close()
        finally:
            sched.stop()
            store.close()
    edits = ", ".join(f"{x:.2f}" for x in took)
    print(f"saved PVI edit to run: {edits} s; drafts {', '.join(f'{x:.2f}' for x in drafts)} s")
    assert max(took) < 10.0
    assert max(drafts[1:]) < 1.5  # the first one starts the worker
