"""A change re-plans only the watched goals that can see it (I2.1 gate, found on a live hub).

The invalidator finds the goals whose results read a changed ref. Results are keyed by content, so two scenarios
holding the same records share their keys, and a ref names a record in every layer. A write in one scenario then
re-planned the same goals in every other scenario too, though none of them reads that layer: with the line sheet's
run chain watched in a few scenarios (each re-plan of a whole run chain costs seconds), the saved run of an edit took
6, 11, 16 and 20 s on four e2e runs in a row. A write in layer X can change only a view whose layer chain holds X,
and an upstream result that changed in one view moves only that view's downstream goals."""

from __future__ import annotations

from region.core.view import View
from tests.jobs.fakes import FakeStore
from tests.jobs.test_scheduler import meta, settle

MAIN = View()
S1 = View(layer="s1")
S2 = View(layer="s2")


def _replanned(sched):
    seen: list[tuple[str, str, str]] = []
    real = sched._affected

    def spy(*a, **kw):
        items = real(*a, **kw)
        seen.extend((g["type"], g["scope"], g["view"]) for _, g, _ in items)
        return items

    sched._affected = spy
    return seen


def test_a_scenario_write_replans_only_the_goals_that_see_it(make_sched):
    store = FakeStore()
    store.add_layer("s1")
    store.add_layer("s2")
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    for view in (MAIN, S1, S2):
        sched.watch_goal("t.sum", "A", view, priority=2, ttl_s=600)
    settle(sched)
    seen = _replanned(sched)
    store.set("thing", "A", {"v": 5}, layer="s1")
    sched.notify()
    settle(sched)
    assert ("t.sum", "A", S1.token()) in seen
    assert ("t.sum", "A", S2.token()) not in seen
    assert ("t.sum", "A", MAIN.token()) not in seen
    assert meta(sched, "t.sum", "A", S1)["sum"] == 5
    assert meta(sched, "t.sum", "A", S2)["sum"] == 1


def test_a_main_write_replans_every_view_below_it(make_sched):
    store = FakeStore()
    store.add_layer("s1")
    store.set("thing", "A", {"v": 1})
    sched = make_sched(store)
    for view in (MAIN, S1):
        sched.watch_goal("t.sum", "A", view, priority=2, ttl_s=600)
    settle(sched)
    seen = _replanned(sched)
    store.set("thing", "A", {"v": 7})
    sched.notify()
    settle(sched)
    assert {("t.sum", "A", MAIN.token()), ("t.sum", "A", S1.token())} <= set(seen)
    assert meta(sched, "t.sum", "A", S1)["sum"] == 7


def _upstream_replans(sched):
    seen: list[tuple[str, str, str]] = []
    real = sched._ready

    def spy(*a, **kw):
        items = real(*a, **kw)
        seen.extend((it[1]["type"], it[1]["scope"], it[1]["view"]) for it in items if it[0] == "replan")
        return items

    sched._ready = spy
    return seen


def test_an_upstream_result_in_one_scenario_replans_only_its_own_downstream_goals(make_sched):
    """When an upstream's result changes in one view, its downstream goals in that view are planned again; the same
    downstream goals in another scenario, whose upstream did not move, are not (each such re-plan of a run chain cost
    seconds on the live hub)."""
    store = FakeStore()
    store.add_layer("s1")
    store.add_layer("s2")
    store.set("thing", "P", {"v": 3})
    store.set("note", "N", {"text": "a"})
    sched = make_sched(store)
    for view in (S1, S2):
        sched.watch_goal("t.down", "P:N", view, priority=2, ttl_s=600)
    settle(sched)
    seen = _upstream_replans(sched)
    store.set("thing", "P", {"v": 5}, layer="s1")
    sched.notify()
    settle(sched)
    assert ("t.down", "P:N", S1.token()) in seen
    assert ("t.down", "P:N", S2.token()) not in seen
    assert meta(sched, "t.down", "P:N", S1)["double"] == 10
    assert meta(sched, "t.down", "P:N", S2)["double"] == 6
