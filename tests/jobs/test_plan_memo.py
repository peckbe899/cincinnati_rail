"""The planner keeps an upstream's plan while nothing it read moved (I2.1).

Planning a job plans its whole chain (each ``need`` plans the upstream to learn its key). On a long chain (the run
time of a line: ``railsim.run`` needs ``route.assemble``, which needs the rail, the structure solve with its eleven
crossing lines, and the fit) each re-plan cost seconds, and the scheduler re-plans every level as each upstream lands,
so a saved PVI edit took some 40 s to reach the run. A plan is a pure function of the store, the files it read, the
engine build and its upstreams' outputs, so the planner reuses an upstream's plan while the store's seq and epoch, the
hashes of those files, the engine build and its own upstreams (recursively, with their output hashes) are as they
were."""

from __future__ import annotations

from pathlib import Path

from region.core import fsio
from region.core.view import View
from region.jobs.plan import Planner
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeStore

MAIN = View()


def _planner(store, outputs: dict[str, str], file_hash=None) -> Planner:
    return Planner(
        store,
        registry=jt.make_registry(),
        file_hash=file_hash or (lambda p: fsio.sha256_file(p) if Path(p).is_file() else None),
        upstream_output=outputs.get,
        engine_info=lambda: ("build-1", {}),
    )


def test_an_unchanged_upstream_is_planned_once():
    store = FakeStore()
    store.set("thing", "P", {"v": 3})
    store.set("note", "N", {"text": "a"})
    outputs: dict[str, str] = {}
    pl = _planner(store, outputs)
    up = pl.plan("t.up", "P:N", MAIN)
    outputs[up.key] = "h1"
    first = pl.plan("t.down", "P:N", MAIN)
    n = jt.PLANS[("t.up", "P:N")]
    second = pl.plan("t.down", "P:N", MAIN)
    assert second.key == first.key
    assert jt.PLANS[("t.up", "P:N")] == n
    assert jt.PLANS[("t.down", "P:N")] == 2  # the goal's own plan always runs


def test_a_write_plans_the_upstream_again():
    store = FakeStore()
    store.set("thing", "P", {"v": 3})
    store.set("note", "N", {"text": "a"})
    outputs: dict[str, str] = {}
    pl = _planner(store, outputs)
    outputs[pl.plan("t.up", "P:N", MAIN).key] = "h1"
    a = pl.plan("t.down", "P:N", MAIN)
    store.set("thing", "P", {"v": 4})
    b = pl.plan("t.down", "P:N", MAIN)
    assert b.key != a.key or b.missing


def test_a_new_upstream_output_reaches_the_downstream():
    """The upstream's output hash is read fresh on every plan, memo or not: early cutoff and new results work."""
    store = FakeStore()
    store.set("thing", "P", {"v": 3})
    store.set("note", "N", {"text": "a"})
    outputs: dict[str, str] = {}
    pl = _planner(store, outputs)
    up = pl.plan("t.up", "P:N", MAIN)
    assert pl.plan("t.down", "P:N", MAIN).missing  # no output yet
    outputs[up.key] = "h1"
    a = pl.plan("t.down", "P:N", MAIN)
    assert a.key is not None
    outputs[up.key] = "h2"
    assert pl.plan("t.down", "P:N", MAIN).key != a.key


def test_a_changed_file_plans_the_upstream_again(tmp_path):
    hashes = {"x": "1"}
    store = FakeStore()
    outputs: dict[str, str] = {}
    pl = _planner(store, outputs, file_hash=lambda p: hashes["x"])
    from region.jobs.plan import PlanContext  # noqa: F401 - the context reads files through file_hash

    class Reader:
        name, version, scope, host, priority, timeout_s = "t.reads_file", "1", "thing", "thread", 1, 10.0

        def plan(self, ctx, scope_id):
            jt.PLANS[(self.name, scope_id)] += 1
            ctx.file("repo://pyproject.toml")
            return {}

        def run(self, inputs, rt):  # pragma: no cover - never run here
            raise AssertionError

    class Over:
        name, version, scope, host, priority, timeout_s = "t.over_file", "1", "thing", "thread", 1, 10.0

        def plan(self, ctx, scope_id):
            return {"ref": ctx.need("t.reads_file", scope_id)}

        def run(self, inputs, rt):  # pragma: no cover - never run here
            raise AssertionError

    pl.registry.register(Reader())
    pl.registry.register(Over())
    outputs[pl.plan("t.reads_file", "A", MAIN).key] = "o1"
    pl.plan("t.over_file", "A", MAIN)
    n = jt.PLANS[("t.reads_file", "A")]
    pl.plan("t.over_file", "A", MAIN)
    assert jt.PLANS[("t.reads_file", "A")] == n
    hashes["x"] = "2"
    pl.plan("t.over_file", "A", MAIN)
    assert jt.PLANS[("t.reads_file", "A")] == n + 1
