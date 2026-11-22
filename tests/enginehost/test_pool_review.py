"""Pool behaviour found in the increment-1 review: a call that shares a sidecar with one that times out is sent
again rather than failed (server-3, compute-6), and a refusal no waiting can change is answered at once
(compute-9)."""

from __future__ import annotations

import threading
import time

import pytest

from region.core.errors import EngineUnavailable
from region.enginehost import Pool
from tests.enginehost.helpers import fake_sidecar_argv


def test_a_call_on_a_sidecar_killed_for_another_calls_timeout_is_sent_again() -> None:
    with Pool(size=1, argv=fake_sidecar_argv("--threads"), backoff_s=(0.01, 0.01)) as p:
        assert p.call("engine.echo", {"warm": 1}) == {"warm": 1}
        got: dict[str, object] = {}

        def innocent() -> None:
            try:
                got["fast"] = p.call("test.sleep", {"s": 1.5}, timeout_s=10)
            except EngineUnavailable as e:
                got["fast"] = e

        t = threading.Thread(target=innocent)
        t.start()
        time.sleep(0.2)  # the innocent call is open on the sidecar when the other one times out
        with pytest.raises(EngineUnavailable) as info:
            p.call("test.hang", {}, timeout_s=0.8)
        assert info.value.reason == "timeout"
        t.join(timeout=15)
        assert got["fast"] == {"s": 1.5}, got["fast"]


def test_no_node_is_refused_at_once_every_time() -> None:
    p = Pool(size=2, node="nodexyz-missing-for-this-test")
    try:
        took = []
        for _ in range(8):
            t0 = time.monotonic()
            with pytest.raises(EngineUnavailable) as info:
                p.hello()
            took.append(time.monotonic() - t0)
            assert info.value.reason == "no_node"
        assert max(took) < 0.5, took
    finally:
        p.close()


def test_a_cancelled_call_ends_a_second_after_the_cancel() -> None:
    """compute-12: a superseded engine job kept its slot and its sidecar until the call's timeout; its call now ends
    1 s after the cancel (as a process job is killed), and the sidecar's other calls are sent again."""
    with Pool(size=1, argv=fake_sidecar_argv("--threads"), backoff_s=(0.01, 0.01)) as p:
        assert p.supports_cancel and p.call("engine.echo", 1) == 1
        cancel = threading.Event()
        threading.Timer(0.2, cancel.set).start()
        t0 = time.monotonic()
        with pytest.raises(EngineUnavailable) as info:
            p.call("test.hang", {}, timeout_s=20, cancel=cancel)
        took = time.monotonic() - t0
        assert info.value.reason == "cancelled" and 1.0 <= took < 5, took
        assert p.call("engine.echo", 2) == 2


def test_the_engine_host_passes_the_jobs_cancel_token() -> None:
    from region.jobs.hosts import _DeadlineEngine

    seen = {}

    class Engine:
        supports_cancel = True

        def call(self, method, params, *, timeout_s=30.0, cancel=None):
            seen["cancel"] = cancel
            return {}

    token = threading.Event()
    _DeadlineEngine(Engine(), time.monotonic() + 10, token).call("vertical.rail", {})
    assert seen["cancel"] is token
