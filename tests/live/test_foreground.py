"""A saved line file comes before a sheet's cold run (I2.1, found by ``app/e2e/live.spec.ts``).

On a fresh hub the line sheet asks for its run as it opens: the run's chain (the crossing lines, the structure, the
fit, the assemble and the run) is cold. Planned and run while Ben's saved line file was imported, it took the hub's
time from the import and from the solve of the section in front of him: the file reached the open sheet in 2.5 to
4.3 s against its 3 s budget. Now the import holds the scheduler's foreground: no job of the run's chain starts
before the focused section's solve of the new records has run, and the run still follows."""

from __future__ import annotations

import threading
import time

from region.core.view import View
from tests.live.conftest import Env, until

MAIN = View()
SOLVE = "profiles.solve_section"
RUN = "railsim.run"


def test_a_saved_line_file_comes_before_a_sheets_cold_run(env: Env) -> None:
    sid = env.section("Line_6")
    route = env.store.get("section", sid, MAIN)["data"]["route"]
    env.sched.watch_goal(SOLVE, sid, MAIN, priority=0, ttl_s=600)  # the sheet in focus
    env.mark()
    t0 = time.monotonic()
    since = env.sched.jobs(active=False, limit=1)[0]["created"]

    def third(doc: dict) -> None:
        doc["stations"][2]["c"] += 25.0

    env.edit("Line_6", third)
    until(
        lambda: any(
            p["source"] == "import:profile_lines" and p["state"] == "importing" for _t, p in env.since("source")
        ),
        what="the import to start",
    )

    def ask() -> None:
        # the sheet opened just before the save asks for its run, as runs.ts does
        env.sched.submit(RUN, route, MAIN, priority=2)
        env.sched.watch_goal(RUN, route, MAIN, priority=2, ttl_s=600)

    th = threading.Thread(target=ask)
    th.start()
    applied = until(
        lambda: next((t for t, p in env.since("source") if p["source"] == "import:profile_lines" and p["toast"]), None),
        what="the import's source event",
    )
    solved = until(
        lambda: next((t for t, p in env.since("result") if p["scope"] == sid and p["type"] == SOLVE), None),
        what="the solve of Line 6",
    )
    th.join(120)
    assert env.settle(180)
    print(f"\nline file saved -> import applied {applied - t0:.2f} s, -> solved {solved - t0:.2f} s")
    assert applied - t0 < 3.0 and solved - t0 < 3.0
    jobs = [j for j in env.sched.jobs(active=False, limit=1000) if j["created"] > since]
    pane = [j for j in jobs if j["type"] == SOLVE and j["scope"] == sid and j["priority"] == 0 and j["state"] == "done"]
    assert pane, "the focused section was not solved again"
    first_solve = min(j["finished"] for j in pane)
    early = [
        (j["type"], j["started"])
        for j in jobs
        if j["priority"] > 1 and j["started"] is not None and j["started"] < first_solve
    ]
    assert not early, f"background jobs started before the focused section's solve ended at {first_solve}: {early}"
    assert env.sched.result(RUN, route, MAIN) is not None, "the run did not follow"
