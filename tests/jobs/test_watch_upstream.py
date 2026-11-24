"""A watched goal follows its upstreams' inputs even when its whole chain was already computed (I2.1).

The line sheet watches ``railsim.run``, whose chain (``route.assemble``, the solves, the fit) is often in the cache
already: computed for main, or for another pane, or by a submit that watched nothing. A watched goal is re-planned
when a ref its own result read changes, or when a watched upstream's output changes; so each upstream of a watched
goal must itself be watched, cached chain or not, or an edit of the upstream's records never reaches the run."""

from __future__ import annotations

from region.core.view import View
from tests.jobs import jobtypes as jt
from tests.jobs.fakes import FakeStore
from tests.jobs.test_scheduler import meta, settle

MAIN = View()


def _goal(sched, type_: str, scope: str, view: View = MAIN):
    return sched.cache.one(
        "SELECT watch, auto, priority FROM goal WHERE type = ? AND scope = ? AND view = ?", (type_, scope, view.token())
    )


def test_a_watched_goal_whose_chain_is_cached_follows_an_upstream_edit(make_sched):
    store = FakeStore()
    store.set("thing", "P", {"v": 3})
    store.set("note", "N", {"text": "a"})
    sched = make_sched(store)
    sched.submit("t.down", "P:N", MAIN)  # computed once, nothing watched
    settle(sched)
    assert meta(sched, "t.down", "P:N")["double"] == 6
    sched.watch_goal("t.down", "P:N", MAIN, priority=2, ttl_s=600)  # a cache hit, chain and all
    settle(sched)
    up = _goal(sched, "t.up", "P:N")
    assert up is not None and up["watch"] == 1 and up["auto"] == 1
    store.set("thing", "P", {"v": 5})
    sched.notify()
    settle(sched)
    assert meta(sched, "t.down", "P:N")["double"] == 10
    assert jt.RUNS[("t.down", "P:N")] == 2


def test_an_upstream_already_watched_keeps_its_own_priority(make_sched):
    """The pane in focus watches the rail at 0; the run's watch at 2 does not lower it."""
    store = FakeStore()
    store.set("thing", "P", {"v": 3})
    store.set("note", "N", {"text": "a"})
    sched = make_sched(store)
    sched.watch_goal("t.up", "P:N", MAIN, priority=0, ttl_s=600)
    settle(sched)
    sched.watch_goal("t.down", "P:N", MAIN, priority=2, ttl_s=600)
    settle(sched)
    assert _goal(sched, "t.up", "P:N")["priority"] == 0
