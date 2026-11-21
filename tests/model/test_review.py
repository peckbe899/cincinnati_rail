"""Regressions found in the independent review of WP1: each test names the defect it pins down."""

from __future__ import annotations

import importlib
import json
import sqlite3

import pytest

from region.core import ids
from region.core.errors import Conflict, Invalid, NotFound
from region.core.protocols import Op
from region.core.view import View
from region.model import seed as S
from region.model.db import connect, run_in_transaction
from tests.model.helpers import feature, node, run, tag, tid

M = importlib.import_module("region.model.migrate")


def _section(store, a, *, view=None):
    return store.put(
        {"kind": "t_section", "id": None, "data": {"name": "S", "node_a": a["id"]}, "geom": "LINESTRING (0 0, 10 0)"},
        view or View(),
        if_match=None,
        by="ben",
    )


def _set_name(store, kind, rid, name, view=None):
    cur = store.get(kind, rid, view or View())
    return store.patch(
        kind, rid, [{"op": "replace", "path": "/data/name", "value": name}], view or View(), if_match=tag(cur), by="ben"
    )


# ------------------------------------------------------------------------------------------------ on_delete


def test_on_delete_reaches_a_record_written_unchanged_in_the_same_changeset(store, main):
    """A referrer written unchanged in the changeset (a no-op) still gets its on_delete: before the fix the nullify
    and the cascade were dropped with the no-op, leaving a dangling ref and a live stop on a deleted section."""
    a = node(store, "A")
    s = _section(store, a)
    lab = store.put(
        {"kind": "t_tag", "id": None, "data": {"label": "L", "targets": [s["id"]]}, "geom": None},
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
    res = store.write(
        [
            Op("put", "t_tag", lab["id"], tag(lab), body={"data": lab["data"], "geom": None}),
            Op("put", "t_stop", stop["id"], tag(stop), body={"data": stop["data"], "geom": None}),
            Op("delete", "t_section", s["id"], tag(s)),
        ],
        main,
        by="ben",
        message="remove S",
    )
    assert store.get("t_tag", lab["id"], main)["data"]["targets"] == [None]
    with pytest.raises(NotFound):
        store.get("t_stop", stop["id"], main)
    assert [r["version"] for r in res.records] == [2, 2, 2]


# --------------------------------------------------------------------------------------------------- rebase


def test_upper_layer_state_never_fails_the_write_below(store, main):
    """A merged revision a scenario cannot take (its new ref points at a record deleted there) used to raise inside
    the main write's transaction, so Ben's edit in main was refused with a 409 about the scenario."""
    a, b = node(store, "A"), node(store, "B", 715100)
    s = _section(store, a)
    store.create_layer("try", by="ben")
    tried = View(layer="try")
    _set_name(store, "t_section", s["id"], "S in try", tried)
    store.delete("t_node", b["id"], tried, if_match=tag(b), by="ben")
    add_b = [{"op": "add", "path": "/data/node_b", "value": b["id"]}]
    got = store.patch("t_section", s["id"], add_b, main, if_match=tag(s), by="anna")
    assert got["version"] == 2 and got["data"]["node_b"] == b["id"]
    (c,) = store.conflicts(layer="try")
    assert c["reason"] == "dangling_ref" and c["rec_id"] == s["id"] and c["fields"] == ["data.node_b"]
    assert c["proposed"]["data"] == {"name": "S in try", "node_a": a["id"], "node_b": b["id"]}
    assert store.get("t_section", s["id"], tried)["data"]["name"] == "S in try"
    # once the scenario can take the merge, the next rebase applies it and closes the conflict
    store.restore("t_node", b["id"], 1, tried, if_match=tag(store.history("t_node", b["id"], tried)[0]), by="ben")
    store.rebase(lower="main")
    assert store.conflicts(layer="try") == []
    assert store.get("t_section", s["id"], tried)["data"]["node_b"] == b["id"]


def _legacy_owns_feature(store):
    auth = {
        "kind": "authority",
        "id": ids.stable("old_hub", "authority:feature"),
        "data": {"kind": "feature", "owner": "legacy", "ruling": None, "note": None},
        "geom": None,
    }
    store.apply_import(run("legacy:old_hub", "old_hub", "old_hub"), [auth], dry_run=False)
    return auth


def test_import_below_a_legacy_owned_copy_in_main_is_not_refused(store, imp_layer):
    """Main holds Ben's copy of a kind the old hub later came to own. An import changing another field below used to
    fail whole (409 authority from the rebase into main); now the merge waits as a conflict and the import lands."""
    store.apply_import(run(), [feature("a", "Road A", level=150.0)], dry_run=False)
    _set_name(store, "feature", tid("a"), "Ben's road")
    _legacy_owns_feature(store)
    rep = store.apply_import(run(), [feature("a", "Road A", level=151.0)], dry_run=False)
    assert rep.counts["updated"] == 1 and rep.changeset
    assert [(c["reason"], c["layer"]) for c in rep.conflicts] == [("invalid", "main")]
    assert rep.conflicts[0]["proposed"]["data"]["level_m"] == 151.0
    assert store.get("feature", tid("a"), View())["data"]["level_m"] == 150.0
    assert store.get("feature", tid("a"), View(layer="import:test"))["data"]["level_m"] == 151.0


def test_rebase_onto_the_legacy_layer_follows_the_imports(store, imp_layer):
    """The old hub's copy of an imported record follows a disjoint change below even while legacy owns its kind: the
    legacy layer is the old hub's, and the authority check guards it against edits, not against its base."""
    auth = _legacy_owns_feature(store)
    store.apply_import(run(), [feature("a", "Road A", level=150.0)], dry_run=False)
    old = {**feature("a", "Road A (old hub)", level=150.0)}
    store.apply_import(run("legacy:old_hub", "old_hub", "old_hub"), [auth, old], dry_run=False)
    assert store.get("feature", tid("a"), View())["layer"] == "legacy:old_hub"
    rep = store.apply_import(run(), [feature("a", "Road A", level=152.0)], dry_run=False)
    assert rep.conflicts == []
    got = store.get("feature", tid("a"), View())
    assert got["layer"] == "legacy:old_hub" and got["data"]["name"] == "Road A (old hub)"
    assert got["data"]["level_m"] == 152.0
    # Ben's own writes to the legacy layer are still refused
    with pytest.raises(Conflict) as e:
        _set_name(store, "feature", tid("a"), "Ben", View(layer="legacy:old_hub"))
    assert e.value.reason == "authority"


# ---------------------------------------------------------------------------------------------------- seeds


def _pulled(out, kind, rid, **data):
    f = out / "main" / kind / f"{rid}.json"
    obj = json.loads(f.read_text(encoding="utf-8"))
    obj["data"].update(data)
    f.write_text(S.seed_text(obj), encoding="utf-8", newline="\n")  # a seed is LF on every platform
    return f


def _seed_conflict_on_copied_record(make_store, write_root, name="one.db"):
    one = make_store(name)
    one.create_layer("import:test", namespace="test", by="t")
    one.apply_import(run(), [feature("f", level=150.0)], dry_run=False)
    _set_name(one, "feature", tid("f"), "Ben 1")
    out = write_root / "seed"
    S.export(one, out)
    f = _pulled(out, "feature", tid("f"), name="pulled")
    _set_name(one, "feature", tid("f"), "Ben 2")
    (c,) = S.import_seed(one, out)["layers"]["main"]["conflicts"]
    return one, out, f, c


def test_rebase_never_closes_or_replaces_a_seed_conflict(make_store, write_root):
    """A full rebase dismissed the open seed conflict (its base below was unchanged), and a rebase conflict on the
    same record replaced it; either way export stopped refusing and overwrote the pulled seed change."""
    one, out, f, c = _seed_conflict_on_copied_record(make_store, write_root)
    one.rebase()
    with pytest.raises(Conflict):
        S.export(one, out)
    one.apply_import(run(), [feature("f", "Road X", level=150.0)], dry_run=False)
    assert [x["reason"] for x in one.conflicts()] == ["both_changed", "both_changed"]
    (still,) = S.open_seed_conflicts(one)
    assert still["id"] == c["id"] and still["proposed"]["data"]["name"] == "pulled"
    with pytest.raises(Conflict):
        S.export(one, out)
    assert json.loads(f.read_text(encoding="utf-8"))["data"]["name"] == "pulled"


def test_seed_conflict_stays_resolvable_after_ben_edits_again(make_store, write_root):
    """Ben edited the record again after a seed conflict opened: the conflict could no longer be resolved (ours had
    changed) and every export was refused for ever. Each seed import now refreshes it."""
    one, out, f, _c = _seed_conflict_on_copied_record(make_store, write_root)
    _set_name(one, "feature", tid("f"), "Ben 3")
    with pytest.raises(Conflict):
        S.export(one, out)
    (c,) = one.conflicts()
    one.resolve_conflict(c["id"], "ours", by="ben")
    S.export(one, out)
    assert json.loads(f.read_text(encoding="utf-8"))["data"]["name"] == "Ben 3"
    # and a seed that comes to agree with the database closes its conflict
    one2, out2, f2, _c2 = _seed_conflict_on_copied_record(make_store, write_root / "two", "two.db")
    _pulled(out2, "feature", tid("f"), name="Ben 2")
    rep = S.import_seed(one2, out2)["layers"]["main"]
    assert rep["same"] == 1 and rep["conflicts"] == [] and one2.conflicts() == []


def test_minimal_seed_file_gives_no_false_conflict(make_store, write_root):
    """A hand-written or minimal seed file ({id, kind, data}) was hashed as written, unlike the database's form, so
    the next change to it looked like a change on both sides."""
    two = make_store("two.db")
    out = write_root / "seed"
    rid = ids.new()
    (out / "main" / "t_node").mkdir(parents=True)
    f = out / "main" / "t_node" / f"{rid}.json"
    f.write_text(
        json.dumps({"id": rid, "kind": "t_node", "data": {"name": "x"}, "geom": "POINT(715000.0001 4331000)"}),
        encoding="utf-8",
    )
    assert S.import_seed(two, out)["layers"]["main"]["added"] == 1
    assert S.import_seed(two, out)["layers"]["main"]["same"] == 1
    f.write_text(json.dumps({"id": rid, "kind": "t_node", "data": {"name": "y"}}), encoding="utf-8")
    rep = S.import_seed(two, out)["layers"]["main"]
    assert rep["conflicts"] == [] and rep["taken"] == 1
    assert two.get("t_node", rid, View())["data"]["name"] == "y"


def test_seeded_deletion_keeps_the_seeds_data(make_store, write_root):
    """A tombstone taken from the seed carries the seed's data, so the next export writes the file it read."""
    one = make_store("one.db")
    a = node(one, "A")
    out = write_root / "seed"
    S.export(one, out)
    two = make_store("two.db")
    S.import_seed(two, out)
    f = out / "main" / "t_node" / f"{a['id']}.json"
    obj = json.loads(f.read_text(encoding="utf-8"))
    obj["data"]["name"] = "A, then deleted"
    obj["deleted"] = True
    f.write_text(S.seed_text(obj), encoding="utf-8", newline="\n")  # a seed is LF on every platform
    before = f.read_bytes()
    assert S.import_seed(two, out)["layers"]["main"]["taken"] == 1
    assert two.history("t_node", a["id"], View())[0]["data"]["name"] == "A, then deleted"
    S.export(two, out)
    assert f.read_bytes() == before


# ------------------------------------------------------------------------------------------- smaller defects


def test_nan_or_infinite_geometry_is_invalid_not_a_crash(store, main):
    body = {"name": "x", "class": "road"}
    for geom in ({"type": "Point", "coordinates": [float("nan"), 1.0]}, "POINT (inf 1)"):
        with pytest.raises(Invalid):
            store.put({"kind": "feature", "id": None, "data": body, "geom": geom}, main, if_match=None, by="ben")


def test_two_connections_apply_each_migration_once(write_root):
    """Two processes opening a new database at once both saw 0001 pending; the second then failed on its CREATEs."""
    db = write_root / "race.db"
    a, b = connect(db), connect(db)
    todo = M.pending(b)
    assert M.migrate(a) == [1, 2]
    assert [M.apply_one(b, m) for m in todo] == [False, False] and not b.in_transaction
    assert M.applied(b) == [1, 2] and M.migrate(b) == []
    a.close()
    b.close()


def test_failed_commit_leaves_no_open_transaction(write_root):
    """A COMMIT that fails left the writer's connection inside the transaction, so every later write failed."""
    con = connect(write_root / "c.db")
    con.execute("CREATE TABLE p (id INTEGER PRIMARY KEY)")
    con.execute("CREATE TABLE c (p INTEGER REFERENCES p(id) DEFERRABLE INITIALLY DEFERRED)")
    with pytest.raises(sqlite3.IntegrityError):
        run_in_transaction(con, lambda c: c.execute("INSERT INTO c (p) VALUES (7)"))
    assert not con.in_transaction
    run_in_transaction(con, lambda c: c.execute("INSERT INTO p (id) VALUES (1)"))
    assert con.execute("SELECT count(*) FROM c").fetchone()[0] == 0
    con.close()


def test_match_reads_the_layer_once_per_run(store, imp_layer, write_root, monkeypatch):
    """``match`` re-read every record of the kind for every unmatched key (quadratic in the layer's size)."""
    store.apply_import(run(), [feature(f"f{i}", x=715000 + i) for i in range(50)], dry_run=False)
    look = store.id_lookup(layer=imp_layer, namespace="test", ledger_dir=write_root / "ids")
    reads = []
    real = store.layer_records
    monkeypatch.setattr(store, "layer_records", lambda *a, **k: reads.append(a) or real(*a, **k))
    seen = []

    def match(orphans):
        seen.append(len(orphans))
        return orphans[0]["id"] if len(seen) == 3 else None

    got = [look.id_for("feat", f"k{i}", kind="feature", match=match) for i in range(5)]
    assert len(reads) == 1 and seen == [50, 50, 50, 49, 49]
    assert got[2] in {tid(f"f{i}") for i in range(50)} and got[0] == ids.stable("test", "k0")


def test_tag_read_honours_the_ref_filter(store, main):
    """``list(..., tag=...)`` dropped the ``ref`` filter and listed every record of the kind."""
    a, b = node(store, "A"), node(store, "B", 715100)
    s = _section(store, a)
    _section(store, b)
    store.tag("main", "v1", by="ben")
    rows, _ = store.list("t_section", main, tag="v1", ref=a["id"])
    assert [r["id"] for r in rows] == [s["id"]]


def test_waiting_seed_conflict_closes_when_ben_takes_the_seed_and_it_moves_on(make_store, write_root):
    one, out, f, c = _seed_conflict_on_copied_record(make_store, write_root)
    _set_name(one, "feature", tid("f"), "pulled")  # Ben takes the pulled value by hand
    _pulled(out, "feature", tid("f"), name="pulled again")
    rep = S.import_seed(one, out)["layers"]["main"]
    assert rep["taken"] == 1 and rep["conflicts"] == [] and one.conflicts() == []
    assert one.get("feature", tid("f"), View())["data"]["name"] == "pulled again"
