"""Reads beyond the exit list: the view's instant, the list filters, threads, the attached cache, data_version."""

from __future__ import annotations

import threading

from region.core.protocols import Op
from region.core.view import View
from tests.model.helpers import node, note, raw, tag


def _feat(store, name, opened=None, closed=None, geom="POINT (715000 4331000)", **extra):
    return store.put(
        {
            "kind": "feature",
            "id": None,
            "data": {"name": name, "class": "track", "opened": opened, "closed": closed, **extra},
            "geom": geom,
        },
        View(),
        if_match=None,
        by="ben",
    )


def test_list_follows_the_view_instant(store):
    old = _feat(store, "1890 to 1931", "1890", "1931-09")
    new = _feat(store, "since 1985", 1985)
    undated = _feat(store, "undated")

    def names(**v):
        return {r["data"]["name"] for r in store.list("feature", View(**v))[0]}

    assert names() == {"since 1985", "undated"}
    assert names(year=1900) == {"1890 to 1931"}
    assert names(year=1931) == set()  # the closing year started before the end of 1931
    assert names(year=1931, month=8) == {"1890 to 1931"}
    assert names(year=1931, month=9) == set()
    assert names(year=1985) == {"since 1985"}
    # kinds without dates are not built things: every year sees them
    n = note(store, "always")
    assert [r["id"] for r in store.list("note", View(year=1900))[0]] == [n["id"]]
    assert old["id"] and new["id"] and undated["id"]


def test_list_filters(store):
    a, b = node(store, "Sycamore", 715000), node(store, "Elm", 716000)
    s1 = store.put(
        {
            "kind": "t_section",
            "id": None,
            "data": {"name": "S1", "node_a": a["id"], "node_b": b["id"]},
            "geom": "LINESTRING (715000 4331000, 716000 4331000)",
        },
        View(),
        if_match=None,
        by="ben",
    )
    st = store.put(
        {"kind": "t_stop", "id": None, "data": {"name": "Stop 1", "section": s1["id"], "c_m": 5}, "geom": None},
        View(),
        if_match=None,
        by="ben",
    )
    assert [r["id"] for r in store.list("t_node", View(), q="syca")[0]] == [a["id"]]
    assert store.list("t_node", View(), q="%")[0] == []
    assert [r["id"] for r in store.list("t_stop", View(), parent=s1["id"])[0]] == [st["id"]]
    assert [r["id"] for r in store.list("t_section", View(), ref=b["id"])[0]] == [s1["id"]]
    assert [r["id"] for r in store.list("t_node", View(), ids=[b["id"], "01ARZ3NDEKTSV4RRFFQ69G5FAV"])[0]] == [b["id"]]
    # in a scenario the section points elsewhere: the ref filter follows the winning revision
    store.create_layer("try", by="ben")
    c = node(store, "Oak", 717000, view=View(layer="try"))
    store.patch(
        "t_section",
        s1["id"],
        [{"op": "replace", "path": "/data/node_b", "value": c["id"]}],
        View(layer="try"),
        if_match=tag(s1),
        by="ben",
    )
    assert store.list("t_section", View(layer="try"), ref=b["id"])[0] == []
    assert [r["id"] for r in store.list("t_section", View(), ref=b["id"])[0]] == [s1["id"]]
    assert {r["id"] for r in store.refs_to(c["id"], View(layer="try"))} == {s1["id"]}
    assert sorted(store.diff_layers("try"), key=lambda d: d["kind"]) == [
        {
            "kind": "t_node",
            "id": c["id"],
            "op": "create",
            "fields": ["data.name", "data.system", "geom"],
            "ours": '"try:1"',
            "theirs": None,
        },
        {
            "kind": "t_section",
            "id": s1["id"],
            "op": "put",
            "fields": ["data.node_b"],
            "ours": '"try:1"',
            "theirs": '"main:1"',
        },
    ]


def test_threads_write_and_read(store):
    rec = note(store, "0")
    errors = []

    def writer(n: int) -> None:
        try:
            for i in range(20):
                store.write(
                    [Op("create", "note", None, None, body={"data": {"text": f"{n}-{i}"}, "geom": None})],
                    View(),
                    by=f"w{n}",
                    message="",
                )
        except Exception as e:  # pragma: no cover - reported below
            errors.append(e)

    def reader() -> None:
        try:
            for _ in range(50):
                store.get("note", rec["id"], View())
                store.list("note", View(), limit=5)
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)] + [
        threading.Thread(target=reader) for _ in range(2)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(store.list("note", View(), limit=1000)[0]) == 81
    assert len(store.changesets(limit=1000)) == 81
    seqs = [e["seq"] for e in store.events_since(0, limit=10_000)]
    assert seqs == sorted(seqs) and len(seqs) == 2 * 81


def test_out_of_process_write_changes_data_version(store):
    before = store.data_version()
    con = raw(store)
    con.execute("INSERT INTO meta (key, value) VALUES ('probe', 'x')")
    con.close()
    assert store.data_version() != before
    assert store.meta()["probe"] == "x"


def test_two_stores_share_the_writer_and_cache_attaches(make_store, write_root):
    from region.model import db as D

    one = make_store("same.db", cache=write_root / "cache.db")
    two = make_store("same.db")
    assert one._writer is two._writer
    names = [r[1] for r in one._reader().execute("PRAGMA database_list")]
    assert "cache" in names
    r = note(one, "from one")
    assert two.get("note", r["id"], View()) == r
    two.close()
    note(one, "the writer outlives the second store")
    assert D._writers  # still running for the first


def test_cache_write_proceeds_while_a_truth_write_is_open(make_store, write_root):
    """The writer has no cache attached, so a truth write transaction does not take cache.db's write lock and the
    scheduler's cache writes go ahead while it is open."""
    import sqlite3

    from region.jobs import cache as C

    cache_db = write_root / "cache" / "cache.db"
    store = make_store("truth.db", cache=cache_db)
    C.migrate(cache_db)
    writer_dbs = store._writer.run(lambda con: [r[1] for r in con.execute("PRAGMA database_list")], transaction=False)
    assert "cache" not in writer_dbs
    assert "cache" in [r[1] for r in store._reader().execute("PRAGMA database_list")]

    inside, release = threading.Event(), threading.Event()

    def hold(con):
        con.execute("INSERT INTO meta (key, value) VALUES ('held', 'x')")
        inside.set()
        assert release.wait(10)

    t = threading.Thread(target=lambda: store._writer.run(hold))
    t.start()
    try:
        assert inside.wait(10)
        cache = C.connect(cache_db)
        cache.execute("PRAGMA busy_timeout=200")
        try:
            cache.execute("BEGIN IMMEDIATE")
            cache.execute("CREATE TABLE probe (x INTEGER)")
            cache.execute("INSERT INTO probe (x) VALUES (1)")
            cache.execute("COMMIT")
        except sqlite3.OperationalError as e:  # "database is locked" when the writer holds cache.db too
            raise AssertionError(f"a cache write was blocked by an open truth write: {e}") from None
        finally:
            cache.close()
    finally:
        release.set()
        t.join(10)
    assert store.meta()["held"] == "x"
    assert store._reader().execute("SELECT x FROM cache.probe").fetchall() == [(1,)]
