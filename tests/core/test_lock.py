"""``region.core.lock``: the single-instance lock of ``var`` (``var/hub.lock``), and the commands that respect it."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import pytest

from region.core import lock, paths

REPO = paths.repo_root()

CHILD = """
import json, sys
from pathlib import Path
from region.core import lock
held = lock.acquire(Path(sys.argv[1]), int(sys.argv[2]), command="crhub serve")
print(json.dumps({"pid": held.holder.pid, "started": held.holder.started}), flush=True)
sys.stdin.readline()
"""


def _child(var, port: int) -> tuple[subprocess.Popen, dict]:
    env = {**os.environ, paths.VAR_ENV: str(var), "PYTHONUTF8": "1"}
    proc = subprocess.Popen(
        [sys.executable, "-c", CHILD, str(var), str(port)],
        cwd=REPO,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    line = proc.stdout.readline()
    if not line:
        proc.kill()
        raise AssertionError(f"the child did not take the lock: {proc.stderr.read()}")
    return proc, json.loads(line)


def test_acquire_writes_the_holder_and_a_second_acquire_names_it(hub_var):
    held = lock.acquire(hub_var, 8766)
    try:
        assert held.held and held.holder.pid == os.getpid() and held.holder.port == 8766
        assert held.holder.command == "crhub serve" and held.holder.started
        assert not os.get_inheritable(held._fd), "a child process must never hold the hub's lock"
        assert lock.reader(hub_var) == held.holder
        with pytest.raises(lock.LockHeld) as info:
            lock.acquire(hub_var, 8798, wait_s=0.1)  # a second instance, even in this process
        assert info.value.holder == held.holder
        assert f"pid {os.getpid()}" in str(info.value) and "port 8766" in str(info.value)
        body = info.value.to_problem()
        assert (body["status"], body["code"], body["holder"]["port"]) == (409, "hub_running", 8766)
        with pytest.raises(lock.LockHeld, match="crhub setup refused"):
            lock.refuse_if_held(hub_var, "crhub setup")
    finally:
        held.release()
    assert not held.held
    held.release()  # twice is harmless
    assert lock.reader(hub_var) is None
    lock.refuse_if_held(hub_var, "crhub setup")
    assert lock.path_of(hub_var).is_file(), "the file stays; only the lock and the holder go"
    with lock.acquire(hub_var, 8767, command="crhub jobs run") as again:
        assert lock.reader(hub_var) == again.holder and again.holder.command == "crhub jobs run"


def test_reader_of_a_missing_lock_is_none_and_changes_nothing(hub_var):
    assert lock.reader(hub_var) is None
    assert not lock.path_of(hub_var).exists()


def test_a_lock_left_by_a_killed_process_is_taken_over(hub_var):
    proc, child = _child(hub_var, 8799)
    try:
        holder = lock.reader(hub_var)
        assert holder is not None and (holder.pid, holder.port) == (child["pid"], 8799)
        with pytest.raises(lock.LockHeld) as info:
            lock.acquire(hub_var, 8766, wait_s=0.2)
        assert info.value.holder.pid == child["pid"]  # test_second_instance_names_first, at the lock's level
    finally:
        proc.kill()  # SIGKILL here, TerminateProcess on Windows: no clean-up runs in the child
        proc.wait(10)
        proc.stdout.close()
        proc.stderr.close()
        if proc.stdin:
            proc.stdin.close()
    # the file still names the dead child: a stale lock, which the OS no longer holds
    assert lock._read_record(lock.path_of(hub_var)).pid == child["pid"]
    assert lock.reader(hub_var) is None
    with lock.acquire(hub_var, 8766) as mine:
        assert mine.holder.pid == os.getpid()
        assert lock._read_record(lock.path_of(hub_var)) == mine.holder


def test_a_hand_written_lock_file_with_no_lock_is_stale(hub_var):
    record = {"pid": 999_999, "port": 8766, "started": "2026-11-20T09:00:00+01:00", "command": "crhub serve"}
    lock.path_of(hub_var).write_text(json.dumps(record), encoding="utf-8")
    assert lock.reader(hub_var) is None
    with lock.acquire(hub_var, 8766) as held:
        assert held.holder.pid == os.getpid()


def test_jobs_run_and_wipe_refuse_while_the_lock_is_held(hub_var, capsys):
    from region.cli import main as cli_main
    from region.jobs import cache as C
    from region.model import open_store

    open_store(hub_var / "region.db").close()
    cache = hub_var / "cache" / "cache.db"
    C.migrate(cache)
    with lock.acquire(hub_var, 8766):
        capsys.readouterr()
        assert cli_main(["jobs", "wipe", "--yes"]) == 1
        err = capsys.readouterr().err
        assert f"crhub serve (pid {os.getpid()}, port 8766" in err and cache.exists()
        assert cli_main(["jobs", "run", "noop", "x"]) == 1
        assert "holds" in capsys.readouterr().err
    # once the server lets go, the commands run, holding the lock while they work
    assert cli_main(["jobs", "wipe", "--yes"]) == 0 and not cache.exists()
    assert lock.reader(hub_var) is None


def test_setup_refuses_while_the_lock_is_held(hub_var, monkeypatch, capsys):
    from region.cli import setup

    flags = ("dry_run", "skip_python", "skip_npm", "skip_build", "skip_migrate", "skip_imports", "no_doctor", "in_env")
    args = argparse.Namespace(**dict.fromkeys(flags, False))
    ran = []
    monkeypatch.setattr(setup, "execute", lambda *a, **k: ran.append(a) or 0)
    monkeypatch.setattr(setup, "hub_serving", lambda cfg=None: None)  # nothing answers on the port: only the lock
    with lock.acquire(hub_var, 8766):
        assert setup.lock_holder().pid == os.getpid()
        assert setup.run(args) == 1
        assert ran == []
        assert "holds the hub lock" in capsys.readouterr().err
        pytest.importorskip("region.model.migrate")
        assert setup.migrate_db() == 1
        assert "stop it before migrating" in capsys.readouterr().err
        assert not (hub_var / "region.db").exists()
    assert setup.lock_holder() is None
