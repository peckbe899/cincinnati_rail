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
    # and an export over the CRLF copy rewrites every file as LF, on every platform
    S.export(one, out)
    assert _files(out) == lf


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
        f.write_text(S.seed_text(obj), encoding="utf-8", newline="\n")  # a seed is LF on every platform
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
    f.write_text(S.seed_text(obj), encoding="utf-8", newline="\n")  # a seed is LF on every platform
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


def test_two_exports_with_a_proposal_are_byte_identical(make_store, write_root):
    """The second export imports the first one's proposal folder back as the same layer, so it writes nothing and
    makes no layer (a plain-named proposal used to come back as a second layer, proposal:<name>, sharing the folder,
    and the second export rewrote its _layer.json)."""
    one = make_store("one.db")
    note(one, "in main")
    one.create_layer("proposal:gate", tier="proposal", title="gate", by="ben")
    note(one, "in the proposal", view=View(layer="proposal:gate"))
    out = write_root / "seed"
    S.export(one, out)
    first = _files(out)
    layers = one.layers()
    again = S.export(one, out)
    assert _files(out) == first
    assert {slug: st["written"] for slug, st in again["layers"].items()} == {"main": 0, "proposal:gate": 0}
    assert one.layers() == layers


def test_a_proposal_whose_parent_is_missing_is_skipped_not_fatal(make_store, write_root):
    """A proposal made on a scenario of one machine reaches a database without that scenario: it is skipped and
    listed, the other layers still import, and export still runs (leaving the skipped folder as it is)."""
    one = make_store("one.db")
    note(one, "in main")
    one.create_layer("try", by="ben")  # a scenario: never seeded
    one.create_layer("proposal:on-try", tier="proposal", parent="try", title="on a scenario", by="claude")
    note(one, "on the scenario's proposal", view=View(layer="proposal:on-try"))
    one.create_layer("proposal:plain", tier="proposal", by="claude")
    note(one, "in the plain proposal", view=View(layer="proposal:plain"))
    out = write_root / "seed"
    S.export(one, out)
    assert json.loads((out / "proposals" / "on-try" / "_layer.json").read_text(encoding="utf-8"))["parent"] == "try"
    before = _files(out)

    two = make_store("two.db")
    got = S.import_seed(two, out)
    assert got["skipped"] == [
        {
            "layer": "proposal:on-try",
            "path": (out / "proposals" / "on-try").as_posix(),
            "reason": "its parent layer try is not in this database",
        }
    ]
    assert got["layers"]["proposal:on-try"]["missing"] is True
    assert got["layers"]["main"]["added"] == 1 and got["layers"]["proposal:plain"]["added"] == 1
    assert "proposal:on-try" not in {la["slug"] for la in two.layers()}
    assert "in the plain proposal" in {r["data"]["text"] for r in two.list("note", View(layer="proposal:plain"))[0]}

    rep = S.export(two, out)  # export imports first, so it meets the same proposal; it must not fail
    assert rep["imported"]["skipped"][0]["layer"] == "proposal:on-try"
    assert set(rep["layers"]) == {"main", "proposal:plain"}
    assert _files(out) == before, "the skipped proposal's folder is left as it is, and the rest is unchanged"

    # once the parent exists here, the proposal imports under it
    two.create_layer("try", by="ben")
    again = S.import_seed(two, out)
    assert again["skipped"] == [] and again["layers"]["proposal:on-try"]["added"] == 1
    assert two.chain(View(layer="proposal:on-try"))[:2] == ["proposal:on-try", "try"]


def test_a_proposal_on_a_proposal_imports_after_its_parent(make_store, write_root):
    one = make_store("one.db")
    # "a-child" sorts before "z-base", so name order alone would import the child first
    one.create_layer("proposal:z-base", tier="proposal", by="claude")
    note(one, "in the base", view=View(layer="proposal:z-base"))
    one.create_layer("proposal:a-child", tier="proposal", parent="proposal:z-base", by="claude")
    note(one, "in the child", view=View(layer="proposal:a-child"))
    out = write_root / "seed"
    S.export(one, out)
    two = make_store("two.db")
    got = S.import_seed(two, out)
    assert got["skipped"] == []
    assert list(got["layers"]) == ["proposal:z-base", "proposal:a-child"]
    assert two.chain(View(layer="proposal:a-child"))[:2] == ["proposal:a-child", "proposal:z-base"]
    texts = sorted(r["data"]["text"] for r in two.list("note", View(layer="proposal:a-child"))[0])
    assert texts == ["in the base", "in the child"]


def test_a_dangling_ref_does_not_block_the_rest_of_the_seed(make_store, write_root):
    """data-9: an import below drops a node Ben's section refers to (allowed, and listed as dangling_ref). In a fresh
    database the seed of main still imports: the section is written as the seed has it with a dangling_ref conflict,
    and Ben's unrelated records come in too."""
    n1, n2 = tid("n1"), tid("n2")

    def nodes(*which):
        return [
            {"kind": "t_node", "id": i, "data": {"name": nm, "system": "metro"}, "geom": "POINT (715000 4330000)"}
            for i, nm in which
        ]

    live = make_store("live.db")
    live.create_layer("import:test", namespace="test", by="t")
    live.apply_import(run(), nodes((n1, "A"), (n2, "B")), dry_run=False)
    sec = live.put(
        {
            "kind": "t_section",
            "id": None,
            "data": {"name": "Ben's spur", "node_a": n1, "node_b": n2},
            "geom": "LINESTRING (715000 4330000, 716000 4331000)",
        },
        View(),
        if_match=None,
        by="ben",
    )
    other = note(live, "Ben's other work")
    rep = live.apply_import(run(), nodes((n1, "A")), dry_run=False)
    assert [c["reason"] for c in rep.conflicts] == ["dangling_ref"]
    out = write_root / "seed"
    S.export(live, out)
    fresh = make_store("fresh.db")
    fresh.create_layer("import:test", namespace="test", by="t")
    fresh.apply_import(run(), nodes((n1, "A")), dry_run=False)
    got = S.import_seed(fresh, out)["layers"]["main"]
    assert got["added"] == 2 and got["conflicts"] == []
    assert [(c["rec_id"], c["reason"], c["fields"]) for c in got["dangling"]] == [
        (sec["id"], "dangling_ref", ["node_b"])
    ]
    assert fresh.get("note", other["id"], View())["data"]["text"] == "Ben's other work"
    assert fresh.get("t_section", sec["id"], View())["data"]["node_b"] == n2
    assert [c["reason"] for c in fresh.conflicts()] == ["dangling_ref"]
    # it is listed, not an unmerged seed change: export goes on, and gives the same files
    assert S.open_seed_conflicts(fresh) == []
    before = _files(out)
    S.export(fresh, out)
    assert _files(out) == before


def test_a_seed_folder_from_another_checkout_reverts_nothing(make_store, write_root):
    """windows-1, data-1: two checkouts share one var (the Windows default). Ben exports v-new in checkout A; then
    a serve from checkout B, whose region/seed still holds v-old, imports B's folder. Nothing is taken: the record
    stays v-new and the difference is a listed seed conflict."""
    store = make_store()
    a, b = write_root / "cr_hub" / "region" / "seed", write_root / "cincinnati_rail" / "region" / "seed"
    x = note(store, "v-old")
    S.export(store, b)  # checkout B exported once, long ago
    cur = store.get("note", x["id"], View())
    store.patch(
        "note", x["id"], [{"op": "replace", "path": "/data/text", "value": "v-new"}], View(), if_match=tag(cur),
        by="ben",
    )
    S.export(store, a)  # Ben's latest export, in checkout A
    got = S.import_seed(store, b)["layers"]["main"]  # serve from checkout B
    assert got["taken"] == 0 and got["foreign_root"] == S.root_key(a / "main")
    assert [c["rec_id"] for c in got["conflicts"]] == [x["id"]]
    assert store.get("note", x["id"], View())["data"]["text"] == "v-new"
    with pytest.raises(Conflict):  # and export cannot write v-old over it either
        S.export(store, b)
    assert json.loads((b / "main" / "note" / f"{x['id']}.json").read_text(encoding="utf-8"))["data"]["text"] == "v-old"
    # back in checkout A, whose folder agrees with the database: the conflict closes, nothing else changes
    back = S.import_seed(store, a)["layers"]["main"]
    assert back["same"] == 1 and back["conflicts"] == [] and S.open_seed_conflicts(store) == []
    assert S.seed_roots(store) == {"main": S.root_key(a / "main")}


def test_export_writes_the_layers_without_a_seed_conflict(make_store, write_root):
    """data-7: a seed conflict on main blocks main's folder only; a proposal is still written, and the refusal says
    which layers were written and how to resolve."""
    from tests.model.test_review import _seed_conflict_on_copied_record

    one, out, f, _c = _seed_conflict_on_copied_record(make_store, write_root)
    one.create_layer("proposal:gate", by="ben")
    p = note(one, "in the proposal", view=View(layer="proposal:gate"))
    with pytest.raises(Conflict) as e:
        S.export(one, out)
    assert "main" in e.value.detail and "proposal:gate" in e.value.detail and "crhub conflicts" in e.value.detail
    assert (out / "proposals" / "gate" / "note" / f"{p['id']}.json").is_file()
    assert json.loads(f.read_text(encoding="utf-8"))["data"]["name"] == "pulled"
    assert e.value.extra["report"]["layers"]["main"]["skipped"]


def test_export_leaves_a_promoted_layers_changed_folder_alone(make_store, write_root):
    """data-3: after a promote, a cloud session pushes an edit and a new record into the proposal's folder. The
    layer takes no seed import, so export must not overwrite the edit or delete the new file."""
    one = make_store()
    one.create_layer("proposal:gate", by="ben")
    first = note(one, "one", view=View(layer="proposal:gate"))
    out = write_root / "seed"
    S.export(one, out)
    one.promote("proposal:gate", by="ben")
    d = out / "proposals" / "gate" / "note"
    edited = d / f"{first['id']}.json"
    obj = json.loads(edited.read_text(encoding="utf-8"))
    obj["data"]["text"] = "two (cloud edit)"
    edited.write_text(S.seed_text(obj), encoding="utf-8", newline="\n")
    new_id = "01K0000000000000000000000A"
    (d / f"{new_id}.json").write_text(
        S.seed_text({"id": new_id, "kind": "note", "kv": 1, "geom": None, "data": {"text": "new (cloud)"}}),
        encoding="utf-8",
        newline="\n",
    )
    rep = S.export(one, out)
    assert "promoted" in rep["layers"]["proposal:gate"]["skipped"]
    assert sorted(p.stem for p in d.glob("*.json")) == sorted([first["id"], new_id])
    assert json.loads(edited.read_text(encoding="utf-8"))["data"]["text"] == "two (cloud edit)"


def test_a_proposal_named_after_a_windows_device_is_refused_and_never_blocks_export(make_store, write_root):
    """windows-4: proposal:aux (or a name ending in a dot) is refused when it is made; a layer that has such a name
    anyway is skipped by export, and main is still exported and recorded."""
    one = make_store()
    for bad in ("proposal:aux", "proposal:con", "proposal:com1"):
        with pytest.raises(Invalid, match="cannot be a folder"):
            one.create_layer(bad, by="ben")
    x = note(one, "main's note")
    con = raw(one)
    con.execute(
        "INSERT INTO layer (slug, tier, parent, state, created, by) VALUES ('proposal:nul', 'proposal', "
        "(SELECT id FROM layer WHERE slug = 'main'), 'open', '2026-11-22', 'old')"
    )
    con.close()
    out = write_root / "seed"
    rep = S.export(one, out)
    assert "cannot be a folder" in rep["layers"]["proposal:nul"]["skipped"]
    assert (out / "main" / "note" / f"{x['id']}.json").is_file()
    assert one.meta().get("last_export")
