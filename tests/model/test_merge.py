"""Rebase (9.11): disjoint changes below apply as a listed changeset; geometry and overlaps become proposals."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from region.core.fsio import canonical_json
from region.core.view import View
from region.model.merge import merge3
from tests.model.helpers import feature, raw, run, tag, tid


def _ben_edits(store, key, path, value):
    cur = store.get("feature", tid(key), View())
    return store.patch(
        "feature", tid(key), [{"op": "replace", "path": path, "value": value}], View(), if_match=tag(cur), by="ben"
    )


def test_disjoint_field_rebase_is_listed_changeset(store, imp_layer):
    store.apply_import(run(), [feature("a", "Road A", level=150.0), feature("b", "Road B")], dry_run=False)
    mine = _ben_edits(store, "a", "/data/name", "Road A (Ben)")
    assert mine["layer"] == "main"
    rep = store.apply_import(run(), [feature("a", "Road A", level=151.5), feature("b", "Road B")], dry_run=False)
    assert rep.counts["updated"] == 1 and rep.conflicts == []
    got = store.get("feature", tid("a"), View())
    assert got["layer"] == "main" and got["version"] == 2
    assert got["data"]["name"] == "Road A (Ben)" and got["data"]["level_m"] == 151.5
    rebases = store.changesets(kind="rebase")
    assert len(rebases) == 1 and rebases[0]["layer"] == "main" and rebases[0]["count"] == 1
    assert [c for c in rep.changes if c["op"] == "rebase"] == [
        {
            "op": "rebase",
            "kind": "feature",
            "id": tid("a"),
            "layer": "main",
            "changeset": rebases[0]["id"],
            "fields": ["data.level_m"],
        }
    ]
    assert store.get("feature", tid("a"), View(layer="import:test"))["data"]["name"] == "Road A"
    # the rebase is revertible like any changeset
    store.revert(rebases[0]["id"], by="ben")
    assert store.get("feature", tid("a"), View())["data"]["level_m"] == 150.0


def test_geometry_under_edit_becomes_proposal(store, imp_layer):
    store.apply_import(run(), [feature("a", "Road A", x=715000)], dry_run=False)
    mine = _ben_edits(store, "a", "/data/level_m", 149.0)
    rep = store.apply_import(run(), [feature("a", "Road A", x=715050)], dry_run=False)
    assert [c["reason"] for c in rep.conflicts] == ["geometry_under_edit"]
    c = rep.conflicts[0]
    assert c["layer"] == "main" and c["rec_id"] == tid("a") and c["state"] == "open"
    assert c["proposed"]["geom"] == "POINT (715050 4331000)" and c["proposed"]["data"]["level_m"] == 149.0
    assert store.get("feature", tid("a"), View()) == mine
    assert store.changesets(kind="rebase") == []
    assert [x["id"] for x in store.conflicts()] == [c["id"]]
    # Ben accepts the proposal
    out = store.resolve_conflict(c["id"], "merged", c["proposed"], by="ben")
    got = store.get("feature", tid("a"), View())
    assert out["changeset"] and got["geom"] == "POINT (715050 4331000)" and got["data"]["level_m"] == 149.0
    assert store.conflicts() == []
    # a guarded pointer (chainage) changing below is a proposal too, as geometry is
    from region.core import ids

    n = {"kind": "t_node", "id": tid("n"), "data": {"name": "N"}, "geom": "POINT (0 0)"}
    sec = {
        "kind": "t_section",
        "id": tid("s"),
        "data": {"name": "S", "node_a": tid("n"), "length_m": 100.0},
        "geom": "LINESTRING (0 0, 100 0)",
    }
    store.apply_import(run(), [feature("a", "Road A", x=715050), n, sec], dry_run=False)
    cur = store.get("t_section", tid("s"), View())
    store.patch(
        "t_section",
        tid("s"),
        [{"op": "add", "path": "/data/width_m", "value": 9.0}],
        View(),
        if_match=tag(cur),
        by="ben",
    )
    sec2 = {**sec, "data": {**sec["data"], "length_m": 101.0}}
    rep = store.apply_import(run(), [feature("a", "Road A", x=715050), n, sec2], dry_run=False)
    assert [c["reason"] for c in rep.conflicts] == ["geometry_under_edit"]
    assert ids.is_ulid(rep.conflicts[0]["id"])


def test_overlap_conflict_keeps_ours(store, imp_layer):
    store.apply_import(run(), [feature("a", "Road A", level=150.0)], dry_run=False)
    mine = _ben_edits(store, "a", "/data/level_m", 149.0)
    rep = store.apply_import(run(), [feature("a", "Road A", level=152.0)], dry_run=False)
    assert [(c["reason"], c["fields"]) for c in rep.conflicts] == [("both_changed", ["data.level_m"])]
    assert rep.conflicts[0]["proposed"]["data"]["level_m"] == 152.0
    assert store.get("feature", tid("a"), View()) == mine
    # keeping ours moves its base, so the same import raises nothing again
    store.resolve_conflict(rep.conflicts[0]["id"], "ours", by="ben")
    assert store.get("feature", tid("a"), View()) == mine
    again = store.apply_import(run(), [feature("a", "Road A", level=152.0)], dry_run=False)
    assert again.conflicts == [] and store.conflicts() == []
    # a kind can name its overlap reason: a param Ben overrode is an authority divergence (9.25)
    p = {"kind": "t_param", "id": tid("p"), "data": {"path": "settings.platform_m", "value": 120.0}, "geom": None}
    store.apply_import(run(), [feature("a", "Road A", level=152.0), p], dry_run=False)
    cur = store.get("t_param", tid("p"), View())
    store.patch(
        "t_param",
        tid("p"),
        [{"op": "replace", "path": "/data/value", "value": 125.0}],
        View(),
        if_match=tag(cur),
        by="ben",
    )
    p2 = {**p, "data": {**p["data"], "value": 118.0}}
    rep = store.apply_import(run(), [feature("a", "Road A", level=152.0), p2], dry_run=False)
    assert [c["reason"] for c in rep.conflicts] == ["authority_divergence"]


def test_orphans_listed(store, imp_layer):
    n = {"kind": "t_node", "id": tid("n"), "data": {"name": "N"}, "geom": "POINT (0 0)"}
    sec = {
        "kind": "t_section",
        "id": tid("s"),
        "data": {"name": "S", "node_a": tid("n")},
        "geom": "LINESTRING (0 0, 100 0)",
    }
    store.apply_import(run(), [feature("a"), feature("b"), n, sec], dry_run=False)
    _ben_edits(store, "a", "/data/name", "kept by Ben")
    stop = store.put(
        {"kind": "t_stop", "id": None, "data": {"name": "Ben's stop", "section": tid("s"), "c_m": 5.0}, "geom": None},
        View(),
        if_match=None,
        by="ben",
    )
    rep = store.apply_import(run(), [feature("b"), n], dry_run=False)
    assert rep.counts["deleted"] == 2
    reasons = sorted((c["reason"], c["rec_id"]) for c in rep.conflicts)
    assert reasons == sorted([("orphan", tid("a")), ("dangling_ref", stop["id"])])
    assert store.get("feature", tid("a"), View())["data"]["name"] == "kept by Ben"
    assert {c["reason"] for c in store.conflicts(layer="main")} == {"orphan", "dangling_ref"}
    orphan = next(c for c in rep.conflicts if c["reason"] == "orphan")
    store.resolve_conflict(orphan["id"], "theirs", by="ben")
    import pytest

    from region.core.errors import NotFound

    with pytest.raises(NotFound):
        store.get("feature", tid("a"), View())
    con = raw(store)
    assert con.execute("SELECT count(*) FROM conflict WHERE state = 'open'").fetchone()[0] == 1
    con.close()


json_leaf = st.one_of(st.none(), st.booleans(), st.integers(-5, 5), st.sampled_from(["a", "b", ""]))
json_val = st.recursive(
    json_leaf,
    lambda inner: st.lists(inner, max_size=2) | st.dictionaries(st.sampled_from(["x", "y"]), inner, max_size=2),
    max_leaves=4,
)
datas = st.dictionaries(st.sampled_from(["p", "q", "r", "s"]), json_val, max_size=4)
geoms = st.sampled_from([None, "POINT (0 0)", "POINT (1 1)"])
bodies = st.builds(lambda d, g: {"data": d, "geom": g}, datas, geoms)


@settings(max_examples=300, deadline=None)
@given(base=bodies, x=bodies, y=bodies, unit=st.sampled_from(["field", "atomic"]))
def test_merge3_laws(base, x, y, unit):
    assert merge3(base, x, x, unit=unit)[0] == x
    assert merge3(base, base, y, unit=unit) == (y, [])
    assert merge3(base, x, base, unit=unit) == (x, [])
    merged, overlaps = merge3(base, x, y, unit=unit)
    if unit == "field":

        def part(body, key):
            if key == "geom":
                return body["geom"]
            return body["data"].get(key[5:], "<absent>")

        def same(a, b):  # JSON equality: true is not 1
            return canonical_json(a) == canonical_json(b)

        keys = {"geom"} | {f"data.{k}" for k in set(base["data"]) | set(x["data"]) | set(y["data"])}
        for k in keys:
            ox, oy, ob, om = part(x, k), part(y, k), part(base, k), part(merged, k)
            if k in overlaps:
                assert same(om, ox)  # ours wins an overlap by default
            elif not same(ox, ob):
                assert same(om, ox), f"ours changed {k} and lost it"
            elif not same(oy, ob):
                assert same(om, oy), f"theirs changed {k} and lost it"
            else:
                assert same(om, ob)
        # null and absent stay distinct
        for k, v in merged["data"].items():
            assert v is not None or any(k in b["data"] and b["data"][k] is None for b in (base, x, y))
