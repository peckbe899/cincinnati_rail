"""Merge and seed defects found in the increment-1 review: a proposal pulled with a stale base (data-5), a conflict
Ben merged by hand (data-6), a kind version bump (data-8) and an undone edit of an imported record (data-10)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from region.core import features, ids
from region.core.errors import Conflict
from region.core.protocols import ImportRun, etag
from region.core.view import View
from region.model import seed as S
from tests.model.helpers import raw, tag

KV = Path(__file__).resolve().parent / "fixtures_kv"


def _put(store, x, data, view=None):
    view = view or View()
    cur = store.get(x["kind"], x["id"], view)
    return store.put(
        {"kind": x["kind"], "id": x["id"], "data": data, "geom": cur["geom"]}, view, if_match=tag(cur), by="ben"
    )


def test_a_proposal_pulled_with_a_stale_base_merges_and_promotes(make_store, write_root):
    """data-5: a cloud session builds from Ben's seed and edits a note's title in proposal:gate; meanwhile Ben edits
    its text in main. The pulled proposal is rebased at import, so it merges and promotes."""
    ben = make_store("ben.db")
    root = write_root / "seed"
    x = ben.put({"kind": "note", "id": None, "data": {"text": "v1", "title": "t"}, "geom": None}, View(),
                if_match=None, by="ben")  # fmt: skip
    S.export(ben, root)
    cloud = make_store("cloud.db")
    S.import_seed(cloud, root)
    cloud.create_layer("proposal:gate", by="cloud")
    _put(cloud, x, {"text": "v1", "title": "cloud title"}, View(layer="proposal:gate"))
    croot = write_root / "cloudseed"
    S.export(cloud, croot)
    _put(ben, x, {"text": "v2 Ben", "title": "t"})
    S.export(ben, root)
    shutil.copytree(croot / "proposals", root / "proposals")
    got = S.import_seed(ben, root)["layers"]["proposal:gate"]
    assert got["added"] == 1 and got["rebased"]["changesets"]
    merged = ben.get("note", x["id"], View(layer="proposal:gate"))["data"]
    assert merged == {"text": "v2 Ben", "title": "cloud title"}
    ben.promote("proposal:gate", by="ben")
    assert ben.get("note", x["id"], View())["data"] == {"text": "v2 Ben", "title": "cloud title"}


def test_a_promote_blocked_by_a_stale_copy_opens_a_conflict(make_store):
    """data-5: a stale copy whose change overlaps Ben's is a conflict row the refusal names, not a dead end."""
    s = make_store()
    s.create_layer("proposal:gate", by="ben")
    x = s.put({"kind": "note", "id": None, "data": {"text": "v1"}, "geom": None}, View(), if_match=None, by="ben")
    _put(s, x, {"text": "proposal text"}, View(layer="proposal:gate"))
    con = raw(s)
    # main changes the same field under the proposal without a rebase (as a seed pulled from elsewhere leaves it)
    con.execute("UPDATE rec SET base_hash = 'stale' WHERE layer = (SELECT id FROM layer WHERE slug = 'proposal:gate')")
    con.close()
    with pytest.raises(Conflict) as e:
        s.promote("proposal:gate", by="ben")
    assert "crhub conflicts list" in e.value.detail
    assert [c["rec_id"] for c in s.conflicts(layer="proposal:gate")] == [x["id"]]


def test_a_conflict_ben_merged_by_hand_closes_and_the_scenario_promotes(make_store):
    """data-6: main changes a note's text under Ben's scenario edit (a both_changed conflict). Ben merges by hand in
    the scenario; the conflict follows his revision: it closes, its base moves, and promote goes through."""
    s = make_store()
    s.create_layer("try", by="ben")
    x = s.put({"kind": "note", "id": None, "data": {"text": "v1", "title": "a"}, "geom": None}, View(),
              if_match=None, by="ben")  # fmt: skip
    _put(s, x, {"text": "scenario text", "title": "a"}, View(layer="try"))
    _put(s, x, {"text": "main text", "title": "a"})
    (c,) = s.conflicts(layer="try")
    assert c["reason"] == "both_changed"
    _put(s, x, {"text": "main text", "title": "a"}, View(layer="try"))  # Ben takes main's text by hand
    assert s.conflicts(layer="try") == []
    s.promote("try", by="ben")
    # and a hand edit that still overlaps refreshes the conflict, so it stays resolvable
    s.create_layer("try2", by="ben")
    _put(s, x, {"text": "try2 text", "title": "a"}, View(layer="try2"))
    _put(s, x, {"text": "main again", "title": "a"})
    _put(s, x, {"text": "try2 text, edited", "title": "a"}, View(layer="try2"))
    (c2,) = s.conflicts(layer="try2")
    s.resolve_conflict(c2["id"], "ours", by="ben")
    s.promote("try2", by="ben")
    assert s.get("note", x["id"], View())["data"]["text"] == "try2 text, edited"


def test_a_kind_version_bump_raises_no_false_seed_conflict(make_store, write_root):
    """data-8: a pull brings kind version 2 with its upgrader and leaves the seed files alone. Ben's record edited
    since his export is kept (no conflict), the unedited one is the same, and export goes through."""
    v1 = make_store(kinds_paths=[features.CORE_KINDS, KV / "v1" / "kinds"])
    root = write_root / "seed"
    a = v1.put({"kind": "t_up", "id": None, "data": {"text": "a", "title": None}, "geom": None}, View(),
               if_match=None, by="ben")  # fmt: skip
    b = v1.put({"kind": "t_up", "id": None, "data": {"text": "b", "title": None}, "geom": None}, View(),
               if_match=None, by="ben")  # fmt: skip
    S.export(v1, root)
    _put(v1, b, {"text": "b edited", "title": None})
    db = v1.path
    v1.close()
    from region.model import open_store

    with open_store(db, kinds_paths=[features.CORE_KINDS, KV / "v2" / "kinds"]) as v2:
        got = S.import_seed(v2, root)["layers"]["main"]
        assert got["conflicts"] == [] and got["taken"] == 0
        assert got["kept"] == 1 and got["same"] == 1
        assert v2.get("t_up", b["id"], View())["data"]["text"] == "b edited"
        S.export(v2, root)
        assert v2.get("t_up", a["id"], View())["data"]["text"] == "a"


def _imp(store, recs):
    run = ImportRun(importer="t", version="1", layer="import:test", namespace="test", sources={}, by="import:t")
    return store.apply_import(run, recs, dry_run=False)


def test_an_undone_edit_of_an_imported_record_follows_the_next_re_path(make_store):
    """data-10: Ben edits an imported section on main and undoes it (main keeps a revision equal to its base). The
    next import re-paths the section: main follows it, with no conflict."""
    s = make_store()
    s.create_layer("import:test", namespace="test", by="t")
    n1, n2, sid = ids.stable("test", "n1"), ids.stable("test", "n2"), ids.stable("test", "s1")

    def node(i, nm):
        return {"kind": "t_node", "id": i, "data": {"name": nm}, "geom": "POINT (715000 4330000)"}

    def sec(g, length):
        return {"kind": "t_section", "id": sid, "data": {"name": "Line 6", "node_a": n1, "node_b": n2,
                "length_m": length}, "geom": g}  # fmt: skip

    _imp(s, [node(n1, "A"), node(n2, "B"), sec("LINESTRING (715000 4330000, 716000 4331000)", 1414.2)])
    cur = s.get("t_section", sid, View())
    from region.core.protocols import Op

    res = s.write(
        [Op("patch", "t_section", sid, etag(cur["layer"], cur["version"]),
            patch=[{"op": "add", "path": "/data/system", "value": "metro"}])],  # fmt: skip
        View(),
        by="ben",
        message="edit",
    )
    s.revert(res.changeset, by="ben")
    assert s.get("t_section", sid, View())["layer"] == "main"
    rep = _imp(s, [node(n1, "A"), node(n2, "B"), sec("LINESTRING (715000 4330000, 716500 4331500)", 2121.3)])
    assert rep.conflicts == []
    got = s.get("t_section", sid, View())
    assert got["data"]["length_m"] == 2121.3 and "716500" in got["geom"]


def test_authored_writes_to_import_and_legacy_layers_are_refused(make_store):
    """data-14: a note written on legacy:old_hub (or an edit on an import layer) was accepted, then tombstoned or
    overwritten by the next import without a conflict. It is refused, with reason layer."""
    s = make_store()
    s.create_layer("import:test", namespace="test", by="t")
    _imp(s, [{"kind": "note", "id": ids.stable("test", "n"), "data": {"text": "imported"}, "geom": None}])
    for view, body in (
        (View(layer="legacy:old_hub"), {"kind": "note", "id": None, "data": {"text": "Ben's"}, "geom": None}),
        (
            View(layer="import:test"),
            {"kind": "note", "id": ids.stable("test", "n"), "data": {"text": "x"}, "geom": None},
        ),
    ):
        cur = None
        if body["id"] is not None:
            cur = tag(s.get("note", body["id"], view))
        with pytest.raises(Conflict) as e:
            s.put(body, view, if_match=cur, by="ben")
        assert e.value.reason == "layer" and "rebuilt by its importer" in e.value.detail
    assert s.get("note", ids.stable("test", "n"), View())["data"]["text"] == "imported"


def test_a_ledger_with_two_ids_for_one_key_is_refused(write_root):
    """data-15 (a): two sessions mapped one old key to two ids and the merge kept both lines; reading it silently
    kept the last one, so a fresh database and Ben's used different ids."""
    from region.core.errors import Invalid
    from region.model.legacy import LEDGER_HEADER, read_ledger

    f = write_root / "metro.tsv"
    a, b = ids.stable("test", "a"), ids.stable("test", "b")
    f.write_text(LEDGER_HEADER + f"stop\tmetro:Sycamore#2\t{a}\nstop\tmetro:Sycamore#2\t{b}\n", encoding="utf-8")
    with pytest.raises(Invalid, match="maps to two ids"):
        read_ledger(f)
    f.write_text(LEDGER_HEADER + f"stop\tmetro:Sycamore#2\t{a}\nstop\tmetro:Sycamore#2\t{a}\n", encoding="utf-8")
    assert read_ledger(f) == {("stop", "metro:Sycamore#2"): a}


def test_a_ledger_line_lost_after_its_import_committed_is_written_again(make_store, write_root):
    """data-15 (b): the import committed (the key is in the legacy index) but the ledger write failed. The next run
    finds the key in the index and writes its ledger line again."""
    from region.model.legacy import IdLookupImpl, read_ledger

    s = make_store()
    s.create_layer("import:test", namespace="test", by="t")
    ledger = write_root / "ids"
    look = IdLookupImpl(s, layer="import:test", namespace="test", ledger_dir=ledger)
    rid = look.id_for("thing", "renamed key", kind="note", match=None)
    s._writer.run(look.flush_into)  # committed, but write_ledger never ran (a WinError on the .tsv)
    assert read_ledger(ledger / "test.tsv") == {}
    again = IdLookupImpl(s, layer="import:test", namespace="test", ledger_dir=ledger)
    assert again.id_for("thing", "renamed key", kind="note") == rid
    again.write_ledger(s._writer.run(again.flush_into))
    assert read_ledger(ledger / "test.tsv") == {("thing", "renamed key"): rid}
