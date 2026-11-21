"""Job keys (WP3 exit tests ``test_keys.py``): content-addressed, stable across databases and processes."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from region.core.view import View
from region.jobs import keys
from region.jobs.plan import Planner
from tests.jobs.fakes import FakeEngine, FakeStore
from tests.jobs.jobtypes import make_registry

REPO = Path(__file__).resolve().parents[2]


def planner(store: FakeStore, engine: FakeEngine | None = None) -> Planner:
    eng = engine or FakeEngine()

    def info() -> tuple[str, dict]:
        h = eng.hello()
        return h["engine_build"], h["contracts"]

    return Planner(
        store, registry=make_registry(), file_hash=lambda p: None, upstream_output=lambda k: None, engine_info=info
    )


def build(order: list[str], *, by: str, churn: bool) -> FakeStore:
    """The same content (A, B) written in another order, by another author, with extra versions when ``churn``."""
    store = FakeStore(by=by)
    values = {"A": {"v": 1, "name": "a"}, "B": {"v": 2, "name": "b", "note": None}}
    for rid in order:
        if churn:
            store.set("thing", rid, {"v": 99})
            store.set("thing", rid, {"v": 98})
        store.set("thing", rid, values[rid])
    return store


def test_key_stable_across_dbs():
    one = build(["A", "B"], by="ben", churn=False)
    two = build(["B", "A"], by="cloud", churn=True)
    assert one.get("thing", "A", View())["version"] == 1
    assert two.get("thing", "A", View())["version"] == 3
    k1 = planner(one).plan("t.sum", "A+B", View()).key
    k2 = planner(two).plan("t.sum", "A+B", View()).key
    assert k1 is not None and k1 == k2

    # the formula is pinned: the same body gives the same key in another interpreter and on every machine
    args = ("t.sum", "1", "c" * 64, [("rec:B", "h2"), ("rec:A", "h1")], {"year": 1931}, None, {})
    here = keys.key(*args)
    code = (
        "import json, sys\n"
        "from region.jobs import keys\n"
        "a = json.loads(sys.argv[1])\n"
        "print(keys.key(a[0], a[1], a[2], [tuple(p) for p in a[3]], a[4], a[5], a[6]))\n"
    )
    other = subprocess.run(
        [sys.executable, "-c", code, json.dumps(args)], cwd=REPO, capture_output=True, text=True, timeout=60
    )
    assert other.returncode == 0, other.stderr
    assert other.stdout.strip() == here
    assert here == keys.key(
        "t.sum", "1", "c" * 64, [("rec:A", "h1"), ("rec:B", "h2"), ("rec:A", "h1")], {"year": 1931}, None, {}
    )
    spelled = (
        b'{"axes":{"year":1931},"c":{},"code":"' + b"c" * 64 + b'","e":null,"in":[["rec:A","h1"],["rec:B","h2"]],'
        b'"t":"t.sum","tv":"1"}'
    )
    assert here == hashlib.sha256(spelled).hexdigest()
    assert here == "6b96937783197b67f75b4d963ce88aa592a9a8a3a8b24acc7d9c5a80692063b1"


def test_key_ignores_bookkeeping():
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    p = planner(store)
    before = p.plan("t.sum", "A", View()).key
    # a new version with the same content, by someone else, in another changeset: the store makes no version for an
    # identical write, so make one by changing and changing back
    store.set("thing", "A", {"v": 2}, by="ben")
    changed = p.plan("t.sum", "A", View()).key
    store.set("thing", "A", {"v": 1}, by="cloud")
    rec = store.get("thing", "A", View())
    assert rec["version"] == 3 and rec["by"] == "cloud"
    assert p.plan("t.sum", "A", View()).key == before
    assert changed != before

    # the key body holds content hashes only: no version, changeset, author or time
    body = keys.key_body("t.sum", "1", "c" * 64, p.plan("t.sum", "A", View()).deps, {}, None, {})
    text = json.dumps(body)
    for word in (rec["changeset"], rec["updated"], "cloud", '"version"'):
        assert word not in text

    # an engine job's key carries the engine build and contract majors; another build is another key
    eng1, eng2 = FakeEngine(build="1" * 64), FakeEngine(build="2" * 64)
    k1 = planner(store, eng1).plan("t.engine", "A", View()).key
    assert planner(store, eng1).plan("t.engine", "A", View()).key == k1
    assert planner(store, eng2).plan("t.engine", "A", View()).key != k1
    eng3 = FakeEngine(build="1" * 64, contracts={"section_input": 1, "vertical_rail": 0})
    assert planner(store, eng3).plan("t.engine", "A", View()).key != k1


def test_axes_only_when_declared():
    store = FakeStore()
    store.set("thing", "A", {"v": 1})
    store.add_layer("try")
    p = planner(store)
    views = [View(), View(year=1931), View(year=1931, month=9), View(timeline="real"), View("try", 1950)]

    # declares no axis: one key for every view whose content is the same (the layer is never an axis)
    timeless = {p.plan("t.timeless", "A", v).key for v in views}
    assert len(timeless) == 1

    # reads the timeline in plan: canon and real differ, years do not
    timed = {v: p.plan("t.timed", "A", v).key for v in views}
    assert timed[View()] == timed[View(year=1931)] == timed[View("try", 1950)]
    assert timed[View()] != timed[View(timeline="real")]
    assert p.plan("t.timed", "A", View(timeline="real")).axes == {"timeline": "real"}

    # declares the year statically: years differ, a month does not, the timeline does not
    yearly = {v: p.plan("t.yearly", "A", v).key for v in views}
    assert yearly[View()] != yearly[View(year=1931)]
    assert yearly[View(year=1931)] == yearly[View(year=1931, month=9)]
    assert yearly[View()] == yearly[View(timeline="real")]
    assert p.plan("t.yearly", "A", View(year=1931, month=9)).axes == {"year": 1931}
