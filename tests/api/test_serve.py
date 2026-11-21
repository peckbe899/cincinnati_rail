"""``crhub serve`` (decision 9.22): it refuses a missing database, a second instance names the first, health answers
within 2 s of start, shutdown truncates the WAL, and the committed OpenAPI matches the routes."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from region.api.serve import Serve
from region.core import lock, paths
from tests.api.conftest import H, free_port


def _cmd(port: int, *extra: str) -> list[str]:
    return [sys.executable, "-m", "region", "serve", "--no-browser", "--no-engine", "--no-seeds", "--port", str(port),
            *extra]


def _env(var: Path) -> dict[str, str]:
    return {**os.environ, paths.VAR_ENV: str(var), "PYTHONUTF8": "1"}


def _make_db(var: Path) -> Path:
    from region.model import open_store

    db = var / "region.db"
    open_store(db).close()
    return db


def _popen(port: int, var: Path, *extra: str) -> subprocess.Popen:
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    return subprocess.Popen(
        _cmd(port, *extra), cwd=paths.REPO, env=_env(var), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", creationflags=flags,
    )


def _healthy(port: int, proc: subprocess.Popen, timeout: float) -> float | None:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if proc.poll() is not None:
            return None
        try:
            if httpx.get(f"http://127.0.0.1:{port}/api/v1/health", timeout=0.5).status_code == 200:
                return time.monotonic() - t0
        except httpx.HTTPError:
            pass
        time.sleep(0.02)
    return None


def _interrupt(proc: subprocess.Popen) -> tuple[str, str]:
    """Stop a serve as Ctrl+C (Ctrl+Break on Windows) would; its output."""
    if sys.platform == "win32":
        proc.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        proc.send_signal(signal.SIGINT)
    try:
        return proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        return proc.communicate()


def test_refuses_missing_db(hub_var):
    out = subprocess.run(_cmd(free_port()), cwd=paths.REPO, env=_env(hub_var), capture_output=True, text=True,
                         encoding="utf-8", timeout=120)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "no database at" in out.stderr and "crhub setup" in out.stderr
    assert not (hub_var / "region.db").exists()
    assert lock.reader(hub_var) is None  # the lock was let go


def test_second_instance_names_first(hub_var):
    _make_db(hub_var)
    port = free_port()
    first = _popen(port, hub_var)
    try:
        assert _healthy(port, first, 60) is not None, first.stderr.read() if first.poll() is not None else ""
        holder = lock.reader(hub_var)
        assert holder is not None and holder.pid == first.pid and holder.port == port
        second = subprocess.run(_cmd(free_port()), cwd=paths.REPO, env=_env(hub_var), capture_output=True, text=True,
                                encoding="utf-8", timeout=120)
        assert second.returncode == 1
        assert f"pid {first.pid}" in second.stderr and f"port {port}" in second.stderr, second.stderr
        assert "crhub serve" in second.stderr
        out, _err = _interrupt(first)
        assert first.returncode == 0, _err
        assert "stopped" in out and "WAL truncated" in out
        assert lock.reader(hub_var) is None
    finally:
        if first.poll() is None:
            first.kill()
            first.communicate()


def test_health_within_2s(hub_var):
    _make_db(hub_var)
    port = free_port()
    proc = _popen(port, hub_var)
    try:
        took = _healthy(port, proc, 30)
        assert took is not None, proc.stderr.read() if proc.poll() is not None else "no answer"
        assert took < 2.0, f"health answered after {took:.2f} s"
        body = httpx.get(f"http://127.0.0.1:{port}/api/v1/health").json()
        assert body["ok"] is True and body["pid"] == proc.pid
    finally:
        _interrupt(proc)


def test_shutdown_truncates_wal(hub_var):
    from region.api.serve import Serve
    from region.core.view import View
    from region.model import open_store

    db = _make_db(hub_var)
    lines: list[str] = []
    srv = Serve(port=free_port(), engine=False, seeds=False, out=lines.append)
    url = srv.start()
    try:
        assert lock.reader(hub_var) is not None
        r = httpx.post(url + "/api/v1/k/note", json={"data": {"text": "kept"}, "geom": None}, headers=H)
        assert r.status_code == 201
        wal = db.with_name(db.name + "-wal")
        assert wal.is_file() and wal.stat().st_size > 0
    finally:
        srv.stop()
    assert not wal.exists() or wal.stat().st_size == 0
    assert lock.reader(hub_var) is None
    assert any(line.startswith("stopped") and "WAL truncated" in line for line in lines)
    with open_store(db, readonly=True) as store:
        assert store.get("note", r.json()["id"], View())["data"] == {"text": "kept"}


@pytest.mark.parametrize("late", ["app", "engine"])
def test_engine_hello_reaches_meta_and_sse_whichever_is_late(hub_var, monkeypatch, late):
    """The pool starts in the background while serve makes the app; the hello must reach the hub either way, even
    when the app is made seconds after the pool answered (a cold start on Windows)."""
    import region.enginehost as EH
    from region.api import serve as S
    from region.core.errors import EngineUnavailable
    from tests.api.sse import Stream

    hello = {"engine_version": "0.0.0", "engine_build": "b" * 64, "contracts": {"section_input": 0,
             "vertical_rail": 0}, "methods": ["vertical.rail@1"]}

    class Pool:
        size = 1

        def __init__(self, size=None, timeout_s=None):
            pass

        def start(self):
            if late == "engine":
                time.sleep(0.5)
            return dict(hello)

        def hello(self):
            return dict(hello)

        def call(self, method, params, *, timeout_s=None, key=None, progress=None):
            raise EngineUnavailable("no engine in this test", reason="no_node")

        def close(self):
            pass

    monkeypatch.setattr(EH, "Pool", Pool)
    if late == "app":
        app_state = S.Serve._app_state

        def slow_app_state(self):
            time.sleep(2.5)  # longer than any fixed wait for the app
            return app_state(self)

        monkeypatch.setattr(S.Serve, "_app_state", slow_app_state)
    _make_db(hub_var)
    srv = Serve(port=free_port(), engine=True, seeds=False, out=lambda _line: None)
    url = srv.start()
    try:
        deadline = time.monotonic() + 5
        meta = httpx.get(url + "/api/v1/meta").json()
        while meta["engine"] is None and time.monotonic() < deadline:
            time.sleep(0.05)
            meta = httpx.get(url + "/api/v1/meta").json()
        assert meta["engine"] == hello and meta["engine_error"] is None
        with Stream(url) as s:
            assert s.next()["data"]["engine_build"] == "b" * 64
    finally:
        srv.stop()


def test_start_up_report_and_db_outside_var(hub_var, tmp_path):
    from region.api.serve import Serve
    from region.model import open_store

    elsewhere = tmp_path / "fixture"
    elsewhere.mkdir()
    from region.core import fsio

    with fsio.allow_writes(elsewhere):
        open_store(elsewhere / "region.db").close()
    lines: list[str] = []
    srv = Serve(db=elsewhere / "region.db", port=free_port(), engine=False, seeds=False, out=lines.append)
    url = srv.start()
    try:
        r = httpx.post(url + "/api/v1/k/note", json={"data": {"text": "x"}, "geom": None}, headers=H)
        assert r.status_code == 201
        assert httpx.get(url + "/api/v1/tiers").status_code == 200
    finally:
        srv.stop()
    steps = [line.split()[0] for line in lines]
    assert steps[:4] == ["lock", "database", "migrate", "tiers"] and "serving" not in steps
    assert "jobs" in steps and steps[-1] == "stopped"


def test_openapi_drift():
    from region.api import openapi

    assert not openapi.stale(), (
        "region/api/openapi.json is stale: run python -m region.api.openapi --write, then npm run gen:api -w app, "
        "and commit both"
    )
