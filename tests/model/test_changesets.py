"""Changesets: atomic, validated before anything is written, revertible, with the outbox in the same transaction."""

from __future__ import annotations

import sqlite3

import pytest

from region.core.errors import Conflict, Invalid
from region.core.events import BULK_THRESHOLD, required_keys
from region.core.protocols import Op
from tests.model.helpers import node, note, raw, tag


def _counts(store) -> tuple[int, int, int, int]:
    con = raw(store)
    try:
        return tuple(
            con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # type: ignore[return-value]
            for t in ("rec", "rec_hist", "event", "changeset")
        )
    finally:
        con.close()


def test_one_invalid_op_writes_nothing(store, main):
    a = node(store, "A")
    before = _counts(store)
    ok = {"data": {"text": "fine"}, "geom": None}
    bad = {"data": {"text": 7}, "geom": None}
    with pytest.raises(Invalid) as e:
        store.write(
            [
                Op("create", "note", None, None, body=ok),
                Op("create", "note", None, None, body=bad),
                Op("delete", "t_node", a["id"], tag(a)),
            ],
            main,
            by="ben",
            message="three ops",
        )
    assert e.value.status == 422 and e.value.errors[0]["path"] == "/data/text"
    assert _counts(store) == before
    assert store.get("t_node", a["id"], main) == a
    # a dangling ref, a required ref left null, a geometry of the wrong type: each refuses the whole changeset
    sec = {"name": "S", "node_a": "01ARZ3NDEKTSV4RRFFQ69G5FAV"}
    with pytest.raises(Conflict) as c:
        store.write(
            [
                Op("create", "note", None, None, body=ok),
                Op("create", "t_section", None, None, body={"data": sec, "geom": "LINESTRING (0 0, 1 0)"}),
            ],
            main,
            by="ben",
            message="",
        )
    assert c.value.reason == "reference" and c.value.conflicts[0]["role"] == "node_a"
    with pytest.raises(Invalid):
        store.write(
            [
                Op(
                    "create",
                    "t_section",
                    None,
                    None,
                    body={"data": {"name": "S", "node_a": None}, "geom": "LINESTRING (0 0, 1 0)"},
                )
            ],
            main,
            by="ben",
            message="",
        )
    with pytest.raises(Invalid):
        store.write(
            [Op("create", "t_node", None, None, body={"data": {"name": "N"}, "geom": "LINESTRING (0 0, 1 0)"})],
            main,
            by="ben",
            message="",
        )
    # the feature validator runs on the changeset's final state
    s = store.put(
        {
            "kind": "t_section",
            "id": None,
            "data": {"name": "S", "node_a": a["id"], "length_m": 50.0},
            "geom": "LINESTRING (0 0, 50 0)",
        },
        main,
        if_match=None,
        by="ben",
    )
    with pytest.raises(Invalid) as v:
        store.put(
            {"kind": "t_stop", "id": None, "data": {"name": "far", "section": s["id"], "c_m": 80.0}, "geom": None},
            main,
            if_match=None,
            by="ben",
        )
    assert v.value.errors[0]["path"] == "/data/c_m"
    assert _counts(store)[0] == before[0] + 1
    # refs resolve in the changeset's final state, in any order
    res = store.write(
        [
            Op(
                "create",
                "t_stop",
                None,
                None,
                body={"data": {"name": "ok", "section": s["id"], "c_m": 10.0}, "geom": None},
            )
        ],
        main,
        by="ben",
        message="",
    )
    assert res.changeset


def test_on_delete_restrict_cascade_nullify(store, main):
    a, b = node(store, "A"), node(store, "B", 715100)
    s = store.put(
        {
            "kind": "t_section",
            "id": None,
            "data": {"name": "S", "node_a": a["id"], "node_b": b["id"]},
            "geom": "LINESTRING (715000 4331000, 715100 4331000)",
        },
        main,
        if_match=None,
        by="ben",
    )
    stop = store.put(
        {"kind": "t_stop", "id": None, "data": {"name": "st", "section": s["id"], "c_m": 1.0}, "geom": None},
        main,
        if_match=None,
        by="ben",
    )
    lab = store.put(
        {"kind": "t_tag", "id": None, "data": {"label": "L", "targets": [s["id"], None]}, "geom": None},
        main,
        if_match=None,
        by="ben",
    )
    with pytest.raises(Conflict) as e:
        store.delete("t_node", a["id"], main, if_match=tag(a), by="ben")
    assert e.value.reason == "reference" and e.value.conflicts[0]["id"] == s["id"]
    assert [r["id"] for r in store.refs_to(s["id"], main)] == sorted([stop["id"], lab["id"]])
    res = store.write([Op("delete", "t_section", s["id"], tag(s))], main, by="ben", message="remove S")
    cs = store.changeset(res.changeset)
    assert {(r["kind"], r["deleted"]) for r in cs["records"]} == {
        ("t_section", True),
        ("t_stop", True),
        ("t_tag", False),
    }
    assert store.get("t_tag", lab["id"], main)["data"]["targets"] == [None, None]
    store.delete("t_node", a["id"], main, if_match=tag(a), by="ben")


def test_revert_after_later_edit_conflicts(store, main):
    r = note(store, "v1")
    first = store.write(
        [Op("patch", "note", r["id"], tag(r), patch=[{"op": "replace", "path": "/data/text", "value": "v2"}])],
        main,
        by="ben",
        message="edit 1",
    )
    r2 = first.records[0]
    second = store.write(
        [Op("patch", "note", r["id"], tag(r2), patch=[{"op": "replace", "path": "/data/text", "value": "v3"}])],
        main,
        by="anna",
        message="edit 2",
    )
    with pytest.raises(Conflict) as e:
        store.revert(first.changeset, by="ben")
    err = e.value
    assert err.reason == "revert" and err.status == 409
    assert err.conflicts[0]["id"] == r["id"] and err.conflicts[0]["etag"] == '"main:3"'
    assert err.conflicts[0]["diff"] == [{"op": "replace", "path": "/data/text", "value": "v3"}]
    assert store.get("note", r["id"], main)["version"] == 3
    undo2 = store.revert(second.changeset, by="anna")
    assert undo2.records[0]["data"]["text"] == "v2" and undo2.records[0]["version"] == 4
    assert store.changeset(undo2.changeset)["reverts"] == second.changeset
    undo1 = store.revert(first.changeset, by="ben")
    assert undo1.records[0]["data"] == r["data"]
    # a create is reverted by a tombstone, a delete by bringing the record back
    made = store.write(
        [Op("create", "note", None, None, body={"data": {"text": "new"}, "geom": None})], main, by="ben", message=""
    )
    store.revert(made.changeset, by="ben")
    assert store.list("note", main, ids=[made.records[0]["id"]])[0] == []
    cur = store.get("note", r["id"], main)
    gone = store.write([Op("delete", "note", r["id"], tag(cur))], main, by="ben", message="")
    store.revert(gone.changeset, by="ben")
    assert store.get("note", r["id"], main)["data"] == r["data"]


def test_event_in_same_transaction(store, main):
    r = note(store)
    con = raw(store)
    con.execute("CREATE TRIGGER boom BEFORE INSERT ON event BEGIN SELECT RAISE(ABORT, 'outbox down'); END")
    before = _counts(store)
    with pytest.raises(sqlite3.IntegrityError, match="outbox down"):
        store.patch(
            "note", r["id"], [{"op": "replace", "path": "/data/text", "value": "b"}], main, if_match=tag(r), by="ben"
        )
    assert _counts(store) == before and store.get("note", r["id"], main) == r
    con.execute("DROP TRIGGER boom")
    con.execute("CREATE TRIGGER boom2 BEFORE INSERT ON rec_hist BEGIN SELECT RAISE(ABORT, 'history down'); END")
    with pytest.raises(sqlite3.IntegrityError):
        store.patch(
            "note", r["id"], [{"op": "replace", "path": "/data/text", "value": "b"}], main, if_match=tag(r), by="ben"
        )
    assert _counts(store) == before
    con.execute("DROP TRIGGER boom2")
    con.close()
    res = store.write(
        [Op("patch", "note", r["id"], tag(r), patch=[{"op": "replace", "path": "/data/text", "value": "b"}])],
        main,
        by="ben",
        message="m",
        client="tab-1",
    )
    events = store.events_since(res.seq - 2)
    assert [e["type"] for e in events] == ["record", "changeset"] and events[-1]["seq"] == res.seq
    rec_ev, cs_ev = events[0]["data"], events[1]["data"]
    assert required_keys("record") <= set(rec_ev) and required_keys("changeset") <= set(cs_ev)
    assert rec_ev["changeset"] == res.changeset == cs_ev["id"] and rec_ev["fields"] == ["data.text"]
    assert rec_ev["client"] == "tab-1" and rec_ev["version"] == 2 and cs_ev["summary"] is False
    assert store.changeset(res.changeset)["seq"] == res.seq


def test_bulk_changeset_summary_event(store, main):
    def make(n):
        return store.write(
            [Op("create", "note", None, None, body={"data": {"text": f"n{i}"}, "geom": None}) for i in range(n)],
            main,
            by="ben",
            message=f"{n} notes",
        )

    small = make(BULK_THRESHOLD)
    types = [e["type"] for e in store.events_since(small.seq - BULK_THRESHOLD - 1)]
    assert types.count("record") == BULK_THRESHOLD and types[-1] == "changeset"
    seq = store.last_seq()
    big = make(BULK_THRESHOLD + 1)
    events = store.events_since(seq)
    assert [e["type"] for e in events] == ["changeset"]
    ev = events[0]["data"]
    assert ev["summary"] is True and ev["count"] == BULK_THRESHOLD + 1 and ev["kinds"] == {"note": BULK_THRESHOLD + 1}
    assert ev["seq"] == big.seq and len(big.records) == BULK_THRESHOLD + 1
