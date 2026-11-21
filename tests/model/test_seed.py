"""Seeds v2: byte-identical round trips, CRLF, refs in any order, atomic imports, no bookkeeping, per layer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from region.core.errors import Conflict, Invalid
from region.core.view import View
from region.model import seed as S
from tests.model.helpers import feature, node, note, raw, run, tag, tid


def _files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*.json"))}


def _fill(store) -> dict:
    """A main layer with nulls, geometry, refs, a tombstone and a copy-up of an import record."""
    a = node(store, "A", 715000.0, 4331000.125)
    b = node(store, "B", 715100.0, 4331000.0)
    s = store.put(
        {
            "kind": "t_section",
            "id": None,
            "data": {"name": "S", "node_a": a["id"], "node_b": b["id"], "length_m": 100.0, "width_m": None},
            "geom": "LINESTRING (715000 4331000.125, 715100 4331000)",
        },
        View(),
        if_match=None,
        by="ben",
    )
    gone = note(store, "deleted later")
    store.delete("note", gone["id"], View(), if_match=tag(gone), by="ben")
    store.put(
        {"kind": "t_profile", "id": None, "data": {"st": {"p1": None, "p2": 160.5}, "mode": None}, "geom": None},
        View(),
        if_match=None,
        by="ben",
    )
    return {"a": a, "b": b, "s": s}


def test_round_trip_byte_identical_two_dbs(make_store, write_root):
    one = make_store("one.db")
    one.create_layer("import:test", namespace="test", by="t")
    one.apply_import(run(), [feature("f")], dry_run=False)
    cur = one.get("feature", tid("f"), View())
    one.patch(
        "feature",
        tid("f"),
        [{"op": "replace", "path": "/data/name", "value": "Ben's"}],
        View(),
        if_match=tag(cur),
        by="ben",
    )
    _fill(one)
    out1 = write_root / "seed1"
    rep = S.export(one, out1)
    assert rep["layers"]["main"]["records"] == 6 and rep["layers"]["main"]["written"] == 6
    files1 = _files(out1)
    assert all("\r" not in b.decode("utf-8") and b.endswith(b"\n") for b in files1.values())
    two = make_store("two.db")
    got = S.import_seed(two, out1)
    assert got["layers"]["main"]["added"] == 6 and got["layers"]["main"]["conflicts"] == []
    out2 = write_root / "seed2"
    S.export(two, out2)
    assert _files(out2) == files1
    # an export run twice in a row writes the same bytes and nothing new
    again = S.export(one, out1)
    assert again["layers"]["main"]["written"] == 0 and _files(out1) == files1
    copied = json.loads(files1[f"main/feature/{tid('f')}.json"])
    assert copied["base"] == cur["hash"] and copied["data"]["name"] == "Ben's"


def test_crlf_input_reads_same(make_store, write_root):
    one = make_store("one.db")
    _fill(one)
    out = write_root / "seed"
    S.export(one, out)
    lf = _files(out)
    for p in out.rglob("*.json"):
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
    two = make_store("two.db")
    S.import_seed(two, out)
    out2 = write_root / "seed2"
    S.export(two, out2)
    assert _files(out2) == lf
    # importing the CRLF copy into the first database finds nothing changed
    rep = S.import_seed(one, out)
    assert rep["layers"]["main"]["taken"] == 0 and rep["layers"]["main"]["conflicts"] == []


def test_out_of_order_refs_one_transaction(make_store, write_root, monkeypatch):
    one = make_store("one.db")
    made = _fill(one)
    out = write_root / "seed"
    S.export(one, out)
    two = make_store("two.db")
    seq = two.last_seq()
    rep = S.import_seed(two, out)
    cs = rep["layers"]["main"]["changeset"]
    assert cs and [c["id"] for c in two.changesets(since=seq)] == [cs]
    assert two.changeset(cs)["kind"] == "seed"
    assert two.get("t_section", made["s"]["id"], View())["data"]["node_a"] == made["a"]["id"]
    # the folders are read in name order (t_node before t_section), so read the files backwards to put every
    # referrer before its target: the import still succeeds, in one transaction
    order = [p.parent.name for p in sorted(out.rglob("*.json"))]
    assert order.index("t_node") < order.index("t_section")
    real = S._read_layer

    def backwards(d):
        objs, meta = real(d)
        return list(reversed(objs)), meta

    monkeypatch.setattr(S, "_read_layer", backwards)
    three = make_store("three.db")
    rep3 = S.import_seed(three, out)
    assert len(three.changesets(kind="seed")) == 1 and rep3["layers"]["main"]["added"] == 5
    assert three.get("t_section", made["s"]["id"], View())["data"]["node_b"] == made["b"]["id"]


def test_failed_import_leaves_db_unchanged(make_store, write_root):
    one = make_store("one.db")
    _fill(one)
    out = write_root / "seed"
    S.export(one, out)
    bad = next(out.glob("main/t_node/*.json"))
    obj = json.loads(bad.read_text(encoding="utf-8"))
    obj["data"]["name"] = 12
    bad.write_text(json.dumps(obj), encoding="utf-8")
    two = make_store("two.db")
    con = raw(two)
    before = [
        con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        for t in ("rec", "rec_hist", "event", "changeset", "seed_base", "import_run", "layer")
    ]
    with pytest.raises(Invalid):
        S.import_seed(two, out)
    after = [
        con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        for t in ("rec", "rec_hist", "event", "changeset", "seed_base", "import_run", "layer")
    ]
    con.close()
    assert after == before
    # a file whose name disagrees with its id is refused too, before anything is read into the database
    bad.unlink()
    (out / "main" / "t_node" / "01ARZ3NDEKTSV4RRFFQ69G5FAV.json").write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(Invalid):
        S.import_seed(two, out)


def test_bookkeeping_not_in_seed_or_hash(make_store, write_root):
    one = make_store("one.db")
    a = node(one, "A")
    one.patch(
        "t_node", a["id"], [{"op": "replace", "path": "/data/name", "value": "A2"}], View(), if_match=tag(a), by="anna"
    )
    out = write_root / "seed"
    S.export(one, out)
    (f,) = out.glob("main/t_node/*.json")
    obj = json.loads(f.read_text(encoding="utf-8"))
    assert set(obj) == {"id", "kind", "kv", "geom", "data"}
    two = make_store("two.db")
    b = two.put(
        {"kind": "t_node", "id": a["id"], "data": {"name": "A2", "system": "metro"}, "geom": "POINT (715000 4331000)"},
        View(),
        if_match=None,
        by="someone else",
    )
    got = one.get("t_node", a["id"], View())
    assert b["version"] == 1 and got["version"] == 2 and b["by"] != got["by"]
    assert b["hash"] == got["hash"]


def test_take_then_seed_only_change_no_conflict(make_store, write_root):
    one = make_store("one.db")
    a = node(one, "A")
    out = write_root / "seed"
    S.export(one, out)
    two = make_store("two.db")
    assert S.import_seed(two, out)["layers"]["main"]["added"] == 1
    f = out / "main" / "t_node" / f"{a['id']}.json"
    for name in ("A from the seed", "A from the seed again"):
        obj = json.loads(f.read_text(encoding="utf-8"))
        obj["data"]["name"] = name
        f.write_text(S.seed_text(obj), encoding="utf-8")
        rep = S.import_seed(two, out)["layers"]["main"]
        assert rep["taken"] == 1 and rep["conflicts"] == []
        assert two.get("t_node", a["id"], View())["data"]["name"] == name
    # Ben's own change is kept against an unchanged seed; both changing is a conflict that blocks export
    cur = two.get("t_node", a["id"], View())
    two.patch(
        "t_node",
        a["id"],
        [{"op": "replace", "path": "/data/name", "value": "Ben's A"}],
        View(),
        if_match=tag(cur),
        by="ben",
    )
    rep = S.import_seed(two, out)["layers"]["main"]
    assert rep["kept"] == 1 and two.get("t_node", a["id"], View())["data"]["name"] == "Ben's A"
    obj = json.loads(f.read_text(encoding="utf-8"))
    obj["data"]["name"] = "seed's A"
    f.write_text(S.seed_text(obj), encoding="utf-8")
    rep = S.import_seed(two, out)["layers"]["main"]
    assert [c["reason"] for c in rep["conflicts"]] == ["both_changed"]
    assert two.get("t_node", a["id"], View())["data"]["name"] == "Ben's A"
    with pytest.raises(Conflict):
        S.export(two, out)
    two.resolve_conflict(rep["conflicts"][0]["id"], "theirs", by="ben")
    assert two.get("t_node", a["id"], View())["data"]["name"] == "seed's A"
    S.export(two, out)


def test_only_main_and_proposals_seeded(make_store, write_root):
    one = make_store("one.db")
    one.create_layer("import:test", namespace="test", by="t")
    one.apply_import(run(), [feature("imported")], dry_run=False)
    note(one, "in main")
    one.put({"kind": "t_derived", "id": None, "data": {"n": 1}, "geom": None}, View(), if_match=None, by="ben")
    one.create_layer("try", by="ben")
    note(one, "in a scenario", view=View(layer="try"))
    one.create_layer("proposal:pvi-fix", tier="proposal", title="PVI fix", by="claude")
    note(one, "in a proposal", view=View(layer="proposal:pvi-fix"))
    out = write_root / "seed"
    rep = S.export(one, out)
    assert set(rep["layers"]) == {"main", "proposal:pvi-fix"}
    tree = sorted(_files(out))
    assert [t.split("/")[:2] for t in tree] == [["main", "note"], ["proposals", "pvi-fix"], ["proposals", "pvi-fix"]]
    assert "proposals/pvi-fix/_layer.json" in tree
    two = make_store("two.db")
    got = S.import_seed(two, out)
    assert set(got["layers"]) == {"main", "proposal:pvi-fix"}
    assert two.layer("proposal:pvi-fix")["title"] == "PVI fix"
    assert sorted(r["data"]["text"] for r in two.list("note", View(layer="proposal:pvi-fix"))[0]) == [
        "in a proposal",
        "in main",
    ]
