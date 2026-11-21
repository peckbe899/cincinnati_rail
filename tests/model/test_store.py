"""The store's record semantics: no-op writes, If-Match, JSON Patch, tombstones, restore, history, R-tree, versions."""

from __future__ import annotations

import sqlite3

import pytest

from region.core.errors import NotFound, PreconditionFailed, PreconditionRequired
from region.core.protocols import Op, Record, Store, etag
from region.core.view import View
from tests.model.helpers import node, note, raw, tag


def test_store_implements_the_protocol(store):
    assert isinstance(store, Store)


def test_identical_write_is_noop(store, main):
    r = note(store, "a", title="T")
    seq = store.last_seq()
    same = store.put(
        {"kind": "note", "id": r["id"], "data": {"title": "T", "text": "a"}, "geom": None},
        main,
        if_match=tag(r),
        by="someone-else",
    )
    assert same == r
    res = store.write(
        [Op("put", "note", r["id"], tag(r), body={"data": {"text": "a", "title": "T"}, "geom": None})],
        main,
        by="x",
        message="again",
    )
    assert res.changeset is None and res.seq is None and res.records == [r]
    p = store.patch(
        "note", r["id"], [{"op": "replace", "path": "/data/text", "value": "a"}], main, if_match=tag(r), by="x"
    )
    assert p["version"] == 1
    assert store.last_seq() == seq
    assert len(store.history("note", r["id"], main)) == 1
    # a float equal to an int is the same content (RFC 8785 writes 1.0 as 1)
    n = store.put(
        {"kind": "t_node", "id": None, "data": {"name": "n", "level_m": 1}, "geom": "POINT (1 2)"},
        main,
        if_match=None,
        by="ben",
    )
    n2 = store.put(
        {"kind": "t_node", "id": n["id"], "data": {"name": "n", "level_m": 1.0}, "geom": "POINT (1.0004 2)"},
        main,
        if_match=tag(n),
        by="ben",
    )
    assert n2["version"] == 1


def test_missing_if_match_428_error(store, main):
    r = note(store)
    body = {"data": {"text": "b"}, "geom": None}
    with pytest.raises(PreconditionRequired) as e:
        store.put({"kind": "note", "id": r["id"], **body}, main, if_match=None, by="ben")
    assert e.value.status == 428 and e.value.to_problem()["code"] == "precondition_required"
    with pytest.raises(PreconditionRequired):
        store.patch(
            "note", r["id"], [{"op": "replace", "path": "/data/text", "value": "b"}], main, if_match=None, by="ben"
        )
    with pytest.raises(PreconditionRequired):
        store.write([Op("delete", "note", r["id"], None)], main, by="ben", message="")
    assert store.get("note", r["id"], main) == r


def test_stale_if_match_412_error(store, main):
    r1 = note(store, "one")
    r2 = store.patch(
        "note", r1["id"], [{"op": "replace", "path": "/data/text", "value": "two"}], main, if_match=tag(r1), by="anna"
    )
    with pytest.raises(PreconditionFailed) as e:
        store.patch(
            "note",
            r1["id"],
            [{"op": "replace", "path": "/data/text", "value": "mine"}],
            main,
            if_match=tag(r1),
            by="ben",
        )
    err = e.value
    assert err.status == 412
    assert err.current == r2 and err.by == "anna"
    assert err.diff == [{"op": "replace", "path": "/data/text", "value": "two"}]
    assert err.stale == [{"index": 0, "kind": "note", "id": r1["id"], "if_match": '"main:1"', "etag": '"main:2"'}]
    problem = err.to_problem("req-1")
    assert problem["current"]["version"] == 2 and problem["request_id"] == "req-1"
    # a changeset lists every stale op, and writes nothing
    other = note(store, "x")
    other2 = store.patch(
        "note",
        other["id"],
        [{"op": "replace", "path": "/data/text", "value": "y"}],
        main,
        if_match=tag(other),
        by="anna",
    )
    fresh = note(store, "z")
    ops = [
        Op("patch", "note", r1["id"], tag(r1), patch=[{"op": "replace", "path": "/data/text", "value": "q"}]),
        Op("patch", "note", fresh["id"], tag(fresh), patch=[{"op": "replace", "path": "/data/text", "value": "q"}]),
        Op("delete", "note", other["id"], tag(other)),
    ]
    with pytest.raises(PreconditionFailed) as e2:
        store.write(ops, main, by="ben", message="three")
    assert [s["index"] for s in e2.value.stale] == [0, 2]
    assert store.get("note", fresh["id"], main)["data"]["text"] == "z"
    assert store.get("note", other["id"], main) == other2


def test_json_patch_keeps_nulls(store, main):
    data = {
        "mode": None,
        "ready": None,
        "st": {"p1": None, "p2": 160.25, "p3": None},
        "sg": {"p1": None},
        "pvi": [{"c_m": 0, "z_m": None}, {"c_m": 100.5, "z_m": 161.0}],
    }
    r = store.put({"kind": "t_profile", "id": None, "data": data, "geom": None}, main, if_match=None, by="ben")
    p = store.patch(
        "t_profile",
        r["id"],
        [
            {"op": "replace", "path": "/data/st/p2", "value": 159.0},
            {"op": "add", "path": "/data/st/p4", "value": None},
            {"op": "remove", "path": "/data/sg/p1"},
            {"op": "test", "path": "/data/pvi/0/z_m", "value": None},
        ],
        main,
        if_match=tag(r),
        by="ben",
    )
    st = p["data"]["st"]
    assert st == {"p1": None, "p2": 159.0, "p3": None, "p4": None}
    assert "p1" not in p["data"]["sg"] and p["data"]["sg"] == {}
    assert p["data"]["mode"] is None and "mode" in p["data"] and p["data"]["pvi"][0] == {"c_m": 0, "z_m": None}
    assert store.get("t_profile", r["id"], main)["data"] == p["data"]
    # a patch cannot reach bookkeeping, and a failed test op writes nothing
    from region.core.errors import Invalid

    with pytest.raises(Invalid):
        store.patch(
            "t_profile", r["id"], [{"op": "replace", "path": "/version", "value": 9}], main, if_match=tag(p), by="ben"
        )
    with pytest.raises(Invalid):
        store.patch(
            "t_profile", r["id"], [{"op": "test", "path": "/data/mode", "value": "x"}], main, if_match=tag(p), by="ben"
        )
    assert store.get("t_profile", r["id"], main)["version"] == 2


def test_tombstone_keeps_data_hides_on_read(store, main):
    r = note(store, "keep me")
    d = store.delete("note", r["id"], main, if_match=tag(r), by="ben")
    assert d["deleted"] is True and d["version"] == 2 and d["data"] == r["data"]
    with pytest.raises(NotFound):
        store.get("note", r["id"], main)
    assert store.list("note", main)[0] == []
    assert store.hash_of(f"rec:{r['id']}", main) is None
    hist = store.history("note", r["id"], main)
    assert [h["deleted"] for h in hist] == [True, False] and hist[0]["data"] == r["data"]
    assert store.get("note", r["id"], main, at=1) == r
    with pytest.raises(NotFound):
        store.patch("note", r["id"], [], main, if_match=tag(d), by="ben")
    con = raw(store)
    assert con.execute("SELECT deleted, data FROM rec WHERE id = ?", (r["id"],)).fetchone()[0] == 1
    con.close()
    # a put without If-Match brings it back as a new version
    back = store.put(
        {"kind": "note", "id": r["id"], "data": {"text": "again"}, "geom": None}, main, if_match=None, by="ben"
    )
    assert back["version"] == 3 and not back["deleted"]


def test_restore_is_new_version(store, main):
    r1 = note(store, "first")
    r2 = store.patch(
        "note", r1["id"], [{"op": "replace", "path": "/data/text", "value": "second"}], main, if_match=tag(r1), by="ben"
    )
    r3 = store.restore("note", r1["id"], 1, main, if_match=tag(r2), by="ben")
    assert r3["version"] == 3 and r3["data"] == r1["data"] and r3["hash"] == r1["hash"]
    assert [h["version"] for h in store.history("note", r1["id"], main)] == [3, 2, 1]
    ev = store.events_since(0)
    assert [e["data"]["op"] for e in ev if e["type"] == "record"] == ["create", "patch", "restore"]
    with pytest.raises(PreconditionFailed):
        store.restore("note", r1["id"], 2, main, if_match=tag(r2), by="ben")
    with pytest.raises(NotFound):
        store.restore("note", r1["id"], 9, main, if_match=tag(r3), by="ben")


def test_history_rows_have_get_shape(store, main):
    r = node(store, "A")
    r = store.patch(
        "t_node",
        r["id"],
        [{"op": "replace", "path": "/geom", "value": "POINT (715100 4331000)"}],
        main,
        if_match=tag(r),
        by="anna",
    )
    r = store.delete("t_node", r["id"], main, if_match=tag(r), by="ben")
    hist = store.history("t_node", r["id"], main)
    assert len(hist) == 3
    for h in hist:
        assert set(h) == set(Record.__annotations__)
        assert isinstance(h["data"], dict) and isinstance(h["deleted"], bool)
        assert h == store.get("t_node", r["id"], main, at=h["version"])
    assert hist[0] == r
    assert hist[1]["geom"] == "POINT (715100 4331000)" and hist[1]["by"] == "anna"


def _rtree(store, rid_of: str) -> list[tuple]:
    con = raw(store)
    try:
        return con.execute(
            "SELECT t.x0, t.y0, t.x1, t.y1 FROM rec_rtree t JOIN rec r ON r.rid = t.rid WHERE r.id = ?", (rid_of,)
        ).fetchall()
    finally:
        con.close()


def test_rtree_follows_geom_including_none(store, main):
    box_a = (714900, 4330900, 715100, 4331100)
    box_b = (719900, 4334900, 720100, 4335100)
    r = store.put(
        {"kind": "feature", "id": None, "data": {"name": "Mark", "class": "mark"}, "geom": "POINT (715000 4331000)"},
        main,
        if_match=None,
        by="ben",
    )
    assert [x["id"] for x in store.list("feature", main, bbox=box_a)[0]] == [r["id"]]
    r = store.patch(
        "feature",
        r["id"],
        [{"op": "replace", "path": "/geom", "value": "POINT (720000 4335000)"}],
        main,
        if_match=tag(r),
        by="ben",
    )
    assert store.list("feature", main, bbox=box_a)[0] == []
    assert [x["id"] for x in store.list("feature", main, bbox=box_b)[0]] == [r["id"]]
    r = store.patch(
        "feature", r["id"], [{"op": "replace", "path": "/geom", "value": None}], main, if_match=tag(r), by="ben"
    )
    assert store.list("feature", main, bbox=box_b)[0] == [] and _rtree(store, r["id"]) == []
    assert [x["id"] for x in store.list("feature", main)[0]] == [r["id"]]
    # raw SQL is followed too: an update of the bbox, and a delete of the row
    con = raw(store)
    con.execute(
        "UPDATE rec SET version = version + 1, geom = 'POINT (1 1)', x0 = 1, y0 = 1, x1 = 1, y1 = 1 WHERE id = ?",
        (r["id"],),
    )
    assert len(_rtree(store, r["id"])) == 1
    con.execute(
        "UPDATE rec SET version = version + 1, geom = NULL, x0 = NULL, y0 = NULL, x1 = NULL, y1 = NULL WHERE id = ?",
        (r["id"],),
    )
    assert _rtree(store, r["id"]) == []
    con.execute(
        "UPDATE rec SET version = version + 1, geom = 'POINT (2 2)', x0 = 2, y0 = 2, x1 = 2, y1 = 2 WHERE id = ?",
        (r["id"],),
    )
    rid = con.execute("SELECT rid FROM rec WHERE id = ?", (r["id"],)).fetchone()[0]
    con.execute("DELETE FROM rec WHERE id = ?", (r["id"],))
    assert con.execute("SELECT count(*) FROM rec_rtree WHERE rid = ?", (rid,)).fetchone()[0] == 0
    con.close()


def test_raw_sql_cannot_skip_versions(store, main):
    r = note(store)
    con = raw(store)
    with pytest.raises(sqlite3.IntegrityError, match="step by one"):
        con.execute("UPDATE rec SET version = version + 2 WHERE id = ?", (r["id"],))
    with pytest.raises(sqlite3.IntegrityError, match="step by one"):
        con.execute("UPDATE rec SET version = version WHERE id = ?", (r["id"],))
    with pytest.raises(sqlite3.IntegrityError, match="needs a new version"):
        con.execute('UPDATE rec SET data = \'{"text": "sneaky"}\' WHERE id = ?', (r["id"],))
    with pytest.raises(sqlite3.IntegrityError, match="keeps its id"):
        con.execute("UPDATE rec SET kind = 'feature', version = version + 1 WHERE id = ?", (r["id"],))
    con.execute('UPDATE rec SET version = version + 1, data = \'{"text": "b"}\' WHERE id = ?', (r["id"],))
    assert con.execute("SELECT version FROM rec WHERE id = ?", (r["id"],)).fetchone()[0] == 2
    con.close()


def test_etags_and_views(store):
    r = note(store)
    assert etag(r["layer"], r["version"]) == '"main:1"'
    with pytest.raises(NotFound):
        store.get("note", r["id"], View(layer="nope"))
    with pytest.raises(NotFound):
        store.get("no_such_kind", r["id"], View())
    with pytest.raises(NotFound):
        store.get("feature", r["id"], View())
    assert store.hash_of(f"rec:{r['id']}", View()) == r["hash"]
