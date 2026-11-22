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
from region.core.errors import NotFound
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


def _parent_pid(pid: int) -> int | None:
    """The parent of a Windows process (Toolhelp32 snapshot), or None when it is not running."""
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):  # PROCESSENTRY32W
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]  # fmt: skip

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if not snap or snap == ctypes.c_void_p(-1).value:
        return None
    try:
        e = Entry()
        e.dwSize = ctypes.sizeof(Entry)
        ok = k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            if e.th32ProcessID == pid:
                return int(e.th32ParentProcessID)
            ok = k32.Process32NextW(snap, ctypes.byref(e))
    finally:
        k32.CloseHandle(snap)
    return None


def _is_the_hub(pid: int, proc: subprocess.Popen) -> bool:
    """Whether ``pid`` (as the hub reports it) is the process ``proc`` started. On Windows a venv's
    ``Scripts\\python.exe`` is a launcher that runs the base interpreter as its child, so there the hub is
    ``proc``'s child and ``proc.pid`` is the launcher's (Ben's ``.venv`` and CI's are such venvs)."""
    if pid == proc.pid:
        return True
    return sys.platform == "win32" and _parent_pid(pid) == proc.pid


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
    assert not lock.path_of(hub_var).exists()  # nor taken: the database is looked for first


def test_refuses_missing_db_without_making_var(tmp_path, monkeypatch):
    """A first ``crhub serve`` before ``crhub setup`` says to run setup and leaves no var folder behind."""
    var = tmp_path / "fresh" / "var"
    monkeypatch.setenv(paths.VAR_ENV, str(var))
    srv = Serve(port=free_port(), engine=False, seeds=False, out=lambda _line: None)
    with pytest.raises(NotFound) as e:
        srv.prepare()
    assert "crhub setup" in e.value.detail
    assert not (tmp_path / "fresh").exists()


def test_second_instance_names_first(hub_var):
    _make_db(hub_var)
    port = free_port()
    first = _popen(port, hub_var)
    try:
        assert _healthy(port, first, 60) is not None, first.stderr.read() if first.poll() is not None else ""
        holder = lock.reader(hub_var)
        assert holder is not None and _is_the_hub(holder.pid, first) and holder.port == port
        assert httpx.get(f"http://127.0.0.1:{port}/api/v1/health").json()["pid"] == holder.pid
        second = subprocess.run(_cmd(free_port()), cwd=paths.REPO, env=_env(hub_var), capture_output=True, text=True,
                                encoding="utf-8", timeout=120)
        assert second.returncode == 1
        assert f"pid {holder.pid}" in second.stderr and f"port {port}" in second.stderr, second.stderr
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
        assert body["ok"] is True and _is_the_hub(body["pid"], proc)
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
        # the jobs resolve params as the profiles router does: the rules feature's resolver (9.25)
        from region.ext.rules.params import resolve

        assert srv.jobs.planner.params is resolve
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


def test_a_stream_open_before_the_engine_answers_gets_an_engine_event(hub_var, monkeypatch):
    """A tab that connects while the pool is still starting gets ``engine_build: null`` in its hello; when the pool
    answers, the server sends that stream an ``engine`` event with the build (the app's local solves use it)."""
    import threading

    import region.enginehost as EH
    from tests.api.sse import Stream

    hello = {"engine_version": "0.0.0", "engine_build": "c" * 64, "contracts": {"section_input": 0,
             "vertical_rail": 0}, "methods": ["vertical.rail@1"]}  # fmt: skip
    go = threading.Event()

    class Pool:
        size = 1

        def __init__(self, size=None, timeout_s=None):
            pass

        def start(self):
            assert go.wait(20), "the test never let the pool answer"
            return dict(hello)

        def hello(self):
            return dict(hello)

        def close(self):
            pass

    monkeypatch.setattr(EH, "Pool", Pool)
    _make_db(hub_var)
    srv = Serve(port=free_port(), engine=True, seeds=False, out=lambda _line: None)
    url = srv.start()
    try:
        with Stream(url) as s:
            first = s.next()
            assert first["event"] == "hello" and first["data"]["engine_build"] is None
            go.set()
            got = s.until(lambda m: m["event"] == "engine")
            assert got["data"] == {"engine_build": "c" * 64, "error": None} and got["id"] is None
        assert httpx.get(url + "/api/v1/meta").json()["engine"] == hello
    finally:
        go.set()
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
    assert steps[:5] == ["lock", "database", "migrate", "backups", "tiers"] and "serving" not in steps
    assert sorted(p.name.rsplit("-", 1)[1] for p in (elsewhere / "backups").glob("*.db")) == ["daily.db", "weekly.db"]
    assert "jobs" in steps and steps[-1] == "stopped"


def test_openapi_drift():
    from region.api import openapi

    assert not openapi.stale(), (
        "region/api/openapi.json is stale: run python -m region.api.openapi --write, then npm run gen:api -w app, "
        "and commit both"
    )


def test_model_commands_go_through_a_serving_hub(hub_var, write_root, monkeypatch, capsys):
    """9.28: while a serve holds the lock its database is written only through it. ``crhub export`` and
    ``crhub backup`` (and ``crhub model export``) go through its HTTP API; ``import`` and ``migrate`` refuse and say
    what to do; an explicit ``--db`` writes directly, which needs the lock, so it is refused too."""
    from region.cli import main as cli_main
    from region.model import seed

    out = write_root / "seed"
    monkeypatch.setattr(seed, "SEED", out)
    monkeypatch.setattr(seed.export, "__defaults__", (out,))
    db = _make_db(hub_var)
    srv = Serve(port=free_port(), engine=False, seeds=False, out=lambda _line: None)
    url = srv.start()
    try:
        made = httpx.post(url + "/api/v1/k/note", json={"data": {"text": "through"}, "geom": None}, headers=H)
        assert made.status_code == 201, made.text
        capsys.readouterr()
        for argv in (["export"], ["model", "export"]):
            assert cli_main(argv) == 0
            said = capsys.readouterr().out
            assert f"through the hub serving at {url}" in said and "main" in said, said
        assert (out / "main" / "note" / f"{made.json()['id']}.json").is_file()
        assert cli_main(["backup"]) == 0
        cap = capsys.readouterr()
        backup = Path(cap.out.strip())
        assert backup.is_file() and backup.parent == hub_var / "backups" and "through the hub" in cap.err

        refused = {
            ("export", "--out", str(write_root / "elsewhere")): "Drop --out",
            ("model", "import"): "run crhub export",
            ("model", "migrate"): "Stop it to migrate",
            ("backup", "--reason", "weekly"): "Drop --reason",
            ("export", "--db", str(db)): "crhub serve (pid",
            ("model", "import", "--db", str(db)): "crhub serve (pid",
        }
        for argv, why in refused.items():
            assert cli_main(list(argv)) == 1, argv
            assert why in capsys.readouterr().err, argv
        assert not (write_root / "elsewhere").exists()
    finally:
        srv.stop()
    # with no hub serving, the same commands open the database themselves, holding the lock while they write
    assert cli_main(["model", "import"]) == 0
    assert cli_main(["export"]) == 0
    assert "through the hub" not in capsys.readouterr().out
    assert lock.reader(hub_var) is None
