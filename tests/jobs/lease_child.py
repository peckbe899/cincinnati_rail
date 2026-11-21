"""A scheduler that starts one job and is then killed (``test_lease_expiry_requeues``).

    python -m tests.jobs.lease_child <cache.db> <write root> [job type]

Prints ``RUNNING <job id> <worker pid>`` once the job runs, then waits to be killed. Its lease is 1 s, so the lease
expires soon after the kill. The job type is ``t.gated`` (a thread job) or ``t.proc_sleep`` (a process job).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from region.core import fsio
from region.core.view import View
from region.jobs.scheduler import Scheduler
from tests.jobs.fakes import FakeStore
from tests.jobs.jobtypes import make_registry


def main() -> None:
    cache_path, root = Path(sys.argv[1]), Path(sys.argv[2])
    store = FakeStore()
    store.set("thing", "A", {"v": 7, "wait": 600})
    with fsio.allow_writes(root):
        sched = Scheduler(store, cache_path, None, registry=make_registry(), lease_s=1.0, heartbeat_s=0.2, poll_s=0.02)
        sched.start()
        job_type = sys.argv[3] if len(sys.argv) > 3 else "t.gated"
        out = sched.submit(job_type, "A", View())
        while sched.job(out["job"])["state"] != "running" or (
            job_type == "t.proc_sleep" and not sched.job(out["job"])["pid"]
        ):
            time.sleep(0.01)
        print(f"RUNNING {out['job']} {sched.job(out['job'])['pid']}", flush=True)
        time.sleep(600)


if __name__ == "__main__":
    main()
