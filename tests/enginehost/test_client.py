"""The engine host (WP4): Pool, OneShot and Fake against the real Node sidecar and CLI, and against sidecars that
misbehave on purpose (tests/enginehost/sidecar_fixture.mts, tests/enginehost/fake_sidecar.py)."""

from __future__ import annotations

import io
import statistics
import subprocess
import threading
import time

import pytest

from region.core import fsio
from region.core.errors import EngineError, EngineUnavailable, Invalid
from region.core.protocols import EngineClient
from region.enginehost import Fake, OneShot, Pool, engine_build
from region.enginehost import build as hostbuild
from region.enginehost import client as hostclient
from region.enginehost.client import _Ring
from tests.enginehost.helpers import fake_sidecar_argv, golden, golden_input


def _without_build(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "engine_build"}


def _wait_until(pred, timeout_s: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.01)
    return pred()


# ------------------------------------------------------------------------------------------------- the exit tests


def test_pool_matches_golden_bytes(pool: Pool) -> None:
    """Every committed route input gives the committed output bytes (sha256 of the RFC 8785 JSON without
    engine_build), and Python's input hash equals the engine's."""
    gold = golden()
    assert len(gold["routes"]) == 41
    build = engine_build()
    for route, want in sorted(gold["routes"].items()):
        params = golden_input(route)
        out = pool.call("vertical.rail", params)
        assert out["engine_build"] == build, route
        assert out["input_hash"] == fsio.content_hash(params) == want["input_hash"], route
        assert out["grid"]["n"] == want["n"] == len(out["rail_m"]) == len(out["grade_permille"]), route
        assert fsio.content_hash(_without_build(out)) == want["output_sha256"], route


def test_warm_round_trip_under_5ms(pool: Pool) -> None:
    """An echo round trip through a warm sidecar, the median of 200 calls, under 5 ms."""
    for _ in range(20):
        pool.call("engine.echo", {"warm": True}, key="budget")
    times = []
    for i in range(200):
        t0 = time.perf_counter()
        assert pool.call("engine.echo", {"i": i}, key="budget") == {"i": i}
        times.append(time.perf_counter() - t0)
    median_ms = statistics.median(times) * 1000
    assert median_ms < 5.0, f"median round trip {median_ms:.2f} ms"


def test_killed_worker_respawns_job_fails_cleanly(fixture_pool: Pool) -> None:
    """A sidecar killed mid-call fails that call with EngineUnavailable(crashed), and the next call gets a new
    sidecar."""
    p = fixture_pool
    assert p.call("engine.echo", {"a": 1}) == {"a": 1}
    pid = p.pids()[0]
    errors: list[BaseException] = []

    def hang() -> None:
        try:
            p.call("test.hang", {}, timeout_s=30)
        except BaseException as e:  # the test inspects it
            errors.append(e)

    t = threading.Thread(target=hang)
    t.start()
    sc = p._slots[0]
    assert sc is not None
    assert _wait_until(lambda: bool(sc._pending))
    sc.proc.kill()  # what a crash or the task manager does
    t.join(timeout=10)
    assert not t.is_alive()
    assert len(errors) == 1 and isinstance(errors[0], EngineUnavailable)
    assert errors[0].reason == "crashed"
    assert p.call("engine.echo", {"b": 2}) == {"b": 2}
    assert p.pids()[0] not in (None, pid)


def test_timeout_kills_and_respawns(fixture_pool: Pool) -> None:
    """A call over its timeout kills its sidecar and fails with EngineUnavailable(timeout); the next call runs on a
    new sidecar."""
    p = fixture_pool
    p.call("engine.echo", 0)
    pid = p.pids()[0]
    old = p._slots[0]
    t0 = time.monotonic()
    with pytest.raises(EngineUnavailable) as info:
        p.call("test.hang", {}, timeout_s=0.5)
    assert info.value.reason == "timeout"
    assert 0.4 < time.monotonic() - t0 < 5
    assert old is not None and _wait_until(lambda: old.proc.poll() is not None)
    assert p.call("engine.echo", {"after": True}) == {"after": True}
    assert p.pids()[0] not in (None, pid)


def test_contract_major_mismatch_refused() -> None:
    """A hello naming a contract major this hub does not know is refused, and the process stopped."""
    with Pool(size=1, argv=fake_sidecar_argv("--major", "1"), backoff_s=(0.01, 0.01)) as p:
        with pytest.raises(EngineUnavailable) as info:
            p.call("engine.echo", {})
        assert info.value.reason == "contract"
        assert "section_input" in info.value.detail
        assert p.pids() == [None]
    with Pool(size=1, argv=fake_sidecar_argv("--major", "0")) as p:
        assert p.call("engine.echo", {"ok": 1}) == {"ok": 1}
    with pytest.raises(EngineUnavailable) as info:
        hostbuild.check_hello({"hello": {"contracts": {"section_input": 0}}})
    assert info.value.reason == "contract"


def test_respawned_sidecar_with_another_build_refused() -> None:
    """A sidecar started after the engine source changed (another engine_build than the pool's first) is refused,
    so no answer is ever given under the keys of a build that did not compute it."""
    with Pool(size=1, argv=fake_sidecar_argv(), backoff_s=(0.01, 0.01)) as p:
        assert p.call("engine.echo", {"a": 1}) == {"a": 1}
        assert p.hello()["engine_build"] == "0" * 64
        first = p._slots[0]
        assert first is not None
        p._argv = fake_sidecar_argv("--build", "1" * 64)  # what a git pull under a running hub does to the next spawn
        first.proc.kill()
        assert _wait_until(lambda: not first.alive)
        with pytest.raises(EngineUnavailable) as info:
            p.call("engine.echo", {"a": 2})
        assert info.value.reason == "contract"
        assert "restart the hub" in info.value.detail
        assert p.pids() == [None]
        p._argv = fake_sidecar_argv()
        assert p.call("engine.echo", {"a": 3}) == {"a": 3}


def test_oneshot_equals_pool(pool: Pool, node: str) -> None:
    """The CLI and the sidecar give the same bytes for the same input."""
    one = OneShot(node=node)
    for route in ("Line_6", "RER_A_cumminsville"):
        params = golden_input(route)
        assert fsio.canonical_json(one.call("vertical.rail", params)) == fsio.canonical_json(
            pool.call("vertical.rail", params)
        )
    assert one.hello() == pool.hello()
    with pytest.raises(EngineError) as info:
        one.call("vertical.rail", {"contract": "section_input/0"})
    assert info.value.engine_code == "invalid_input"
    # a result computed by other source than the hello names (the files changed in between) is refused
    one._hello = {**one.hello(), "engine_build": "f" * 64}
    with pytest.raises(EngineUnavailable) as gone:
        one.call("vertical.rail", golden_input("Line_6"))
    assert gone.value.reason == "contract"


def test_build_hash_matches_hello(pool: Pool, node: str) -> None:
    """engine_build computed in Python equals the hello of the sidecar and of the one-shot client."""
    build = engine_build()
    assert len(build) == 64
    assert pool.hello()["engine_build"] == build
    assert OneShot(node=node).hello()["engine_build"] == build
    files = hostbuild.build_files()
    assert files[0] == "package.json" and "src/index.ts" in files and files == sorted(files)
    node_files = subprocess.run(
        [node, "-e", "import('./src/build.ts').then(m => console.log(JSON.stringify(m.buildFiles())))"],
        cwd=str(hostbuild.ENGINE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert files == __import__("json").loads(node_files.stdout)


def test_no_node_raises_engine_unavailable(tmp_path) -> None:
    """With no Node, every client raises EngineUnavailable(no_node) and nothing hangs."""
    missing = tmp_path / "node-not-here"
    for client in (Pool(size=1, node=missing), OneShot(node=missing)):
        with pytest.raises(EngineUnavailable) as info:
            client.call("engine.echo", {})
        assert info.value.reason == "no_node"
        client.close()
    with pytest.raises(EngineUnavailable) as info:
        hostbuild.find_node("no-such-node-executable-on-path")
    assert info.value.reason == "no_node"


# ------------------------------------------------------------------------------------------------- the rest


def test_clients_are_engine_clients(node: str) -> None:
    for client in (Pool(size=1, node=node), OneShot(node=node), Fake({})):
        assert isinstance(client, EngineClient)
        client.close()


def test_engine_error_carries_the_engine_code(pool: Pool) -> None:
    with pytest.raises(EngineError) as info:
        pool.call("vertical.rail", {"contract": "section_input/0"})
    assert info.value.engine_code == "invalid_input"
    assert info.value.status == 502
    assert info.value.issues  # zod's issues, for the job log
    with pytest.raises(EngineError) as info:
        pool.call("no.such.method", {})
    assert info.value.engine_code == "unknown_method"
    with pytest.raises(Invalid):
        pool.call("engine.echo", {"x": float("nan")})
    assert pool.call("engine.echo", {"still": "fine"}) == {"still": "fine"}


def test_stderr_tail_reaches_the_error(fixture_pool: Pool) -> None:
    with pytest.raises(EngineUnavailable) as info:
        fixture_pool.call("test.exit", {})
    assert info.value.reason == "crashed"
    assert "fixture: about to exit" in info.value.stderr_tail
    assert "stderr_tail" not in info.value.to_problem()  # logged, never shown to Ben
    assert fixture_pool.call("engine.echo", 5) == 5


def test_call_racing_a_dying_sidecar_is_sent_again(fixture_pool: Pool, monkeypatch: pytest.MonkeyPatch) -> None:
    """A sidecar that dies after a call has taken its id, but before the call is registered, must not leave the
    call waiting for its whole timeout: the call goes to a fresh sidecar instead."""
    p = fixture_pool
    assert p.call("engine.echo", 1) == 1
    sc = p._slots[0]
    assert sc is not None
    real_dumps = hostclient.json.dumps

    def dumps(obj: object, *args: object, **kwargs: object) -> str:
        if isinstance(obj, dict) and obj.get("params") == {"race": True} and sc._dead is None:
            sc.proc.kill()
            # _died sets _dead in the same locked step that drains the open calls
            assert _wait_until(lambda: sc._dead is not None)
            # a pipe that still takes bytes, so the lost request is not caught by a failed write
            sc.proc.stdin = io.BytesIO()
        return real_dumps(obj, *args, **kwargs)

    monkeypatch.setattr(hostclient.json, "dumps", dumps)
    t0 = time.monotonic()
    # unfixed, the call waits out its whole timeout and fails with EngineUnavailable(timeout)
    assert p.call("engine.echo", {"race": True}, timeout_s=10) == {"race": True}
    assert time.monotonic() - t0 < 8
    assert p._slots[0] is not sc


def test_sidecar_that_outlives_its_stdout_is_killed(fixture_pool: Pool) -> None:
    """A sidecar whose stdout closes while it keeps running fails its open call as crashed and is killed, so no
    process is left behind without a reader."""
    p = fixture_pool
    assert p.call("engine.echo", 1) == 1
    sc = p._slots[0]
    assert sc is not None
    with pytest.raises(EngineUnavailable) as info:
        p.call("test.close_stdout", {}, timeout_s=10)
    assert info.value.reason == "crashed"
    assert _wait_until(lambda: sc.proc.poll() is not None)
    assert p.call("engine.echo", 2) == 2


def test_progress_lines_reach_the_callback(fixture_pool: Pool) -> None:
    seen: list[tuple[float, str]] = []
    out = fixture_pool.call("test.progress", {}, progress=lambda f, stage: seen.append((f, stage)))
    assert out == {"done": True}
    assert [f for f, _ in seen] == [0.25, 0.5, 0.75]


def test_concurrent_calls_share_sidecars(pool: Pool) -> None:
    params = golden_input("Line_2b")
    want = fsio.canonical_json(pool.call("vertical.rail", params))
    results: list[bytes] = []
    lock = threading.Lock()

    def work(i: int) -> None:
        out = pool.call("vertical.rail", {**params, "section_id": f"s{i % 7}"})
        with lock:
            results.append(fsio.canonical_json({**out, "input_hash": None}))

    threads = [threading.Thread(target=work, args=(i,)) for i in range(24)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert len(results) == 24
    first = fsio.canonical_json({**__import__("json").loads(want), "input_hash": None})
    assert all(r == first for r in results)


def test_children_exit_on_stdin_eof(node: str) -> None:
    proc = subprocess.Popen(
        [node, str(hostbuild.ENGINE_DIR / hostbuild.SIDECAR)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(hostbuild.ENGINE_DIR.parent),
    )
    assert proc.stdout is not None and proc.stdin is not None
    hello = proc.stdout.readline()
    assert b'"hello"' in hello
    proc.stdin.close()
    assert proc.wait(timeout=10) == 0


def test_close_stops_every_sidecar(node: str) -> None:
    p = Pool(size=2, node=node)
    p.start()
    procs = [sc.proc for sc in p._slots if sc is not None]
    assert len(procs) == 2
    p.close()
    assert all(pr.poll() is not None for pr in procs)
    with pytest.raises(EngineUnavailable) as info:
        p.call("engine.echo", {})
    assert info.value.reason == "closed"


def test_ring_is_consistent() -> None:
    """A key always maps to the same slot, keys spread over every slot, and growing the pool moves few keys."""
    keys = [f"01SECTION{i:04d}" for i in range(2000)]
    two, three = _Ring(2), _Ring(3)
    a = [two.slot(k) for k in keys]
    assert a == [_Ring(2).slot(k) for k in keys]
    assert set(a) == {0, 1}
    assert min(a.count(0), a.count(1)) > 600
    b = [three.slot(k) for k in keys]
    moved = sum(1 for x, y in zip(a, b, strict=True) if x != y)
    assert all(y == 2 for x, y in zip(a, b, strict=True) if x != y)  # only to the new slot
    assert moved < 1000


def test_pool_routes_by_section_id(pool: Pool) -> None:
    params = golden_input("Line_2b")
    slot = pool.slot_of(params["section_id"])
    pool.call("vertical.rail", params)
    assert pool.pids()[slot] is not None


def test_fake_answers_from_its_table() -> None:
    fake = Fake(
        {
            "vertical.rail": lambda params: {"contract": "vertical_rail/0", "echo": params["section_id"]},
            "engine.echo@1": {"fixed": True},
            "broken": EngineError("engine: boom", engine_code="internal"),
        },
        validate=True,
    )
    assert isinstance(fake, EngineClient)
    assert fake.hello()["contracts"] == hostbuild.known_contracts()
    assert fake.call("vertical.rail@1", golden_input("Line_2b"))["echo"] == "Line_2b"
    assert fake.call("engine.echo", {}) == {"fixed": True}
    with pytest.raises(EngineError):
        fake.call("broken", {})
    with pytest.raises(EngineError) as info:
        fake.call("nothing", {})
    assert info.value.engine_code == "unknown_method"
    with pytest.raises(EngineError) as info:
        fake.call("vertical.rail", {"contract": "section_input/0"})
    assert info.value.engine_code == "invalid_input"
    assert [m for m, _ in fake.calls] == ["vertical.rail@1", "engine.echo", "broken", "nothing", "vertical.rail"]
    fake.close()
    with pytest.raises(EngineUnavailable):
        fake.call("engine.echo", {})


def test_node_version_is_checked(node: str, monkeypatch: pytest.MonkeyPatch) -> None:
    assert hostbuild.node_version(node) >= (22, 18, 0)
    assert hostbuild.check_node(node) == node
    monkeypatch.setattr(hostbuild, "node_min", lambda: (99, 0))
    with pytest.raises(EngineUnavailable) as info:
        hostbuild.check_node(node)
    assert info.value.reason == "node_version"
