"""apply_import: dry runs count, reruns write nothing, removals are import tombstones, duplicate ids are refused."""

from __future__ import annotations

import pytest

from region.core.errors import Conflict, Invalid, NotFound
from region.core.view import View
from tests.model.helpers import feature, raw, run, tid


def test_dry_run_counts(store, imp_layer):
    store.apply_import(run(), [feature("a"), feature("b"), feature("c")], dry_run=False)
    seq = store.last_seq()
    recs = [feature("a"), feature("b", "Road B renamed"), feature("d")]
    rep = store.apply_import(run(), recs, dry_run=True)
    assert rep.dry_run and rep.changeset is None and rep.errors == []
    assert rep.counts == {"created": 1, "updated": 1, "unchanged": 1, "deleted": 1, "conflicts": 0}
    assert rep.by_kind == {"feature": rep.counts}
    assert sorted((c["op"], c["id"]) for c in rep.changes) == sorted(
        [("create", tid("d")), ("put", tid("b")), ("delete", tid("c"))]
    )
    assert next(c for c in rep.changes if c["op"] == "put")["fields"] == ["data.name"]
    assert store.last_seq() == seq
    assert store.get("feature", tid("b"), View())["data"]["name"] == "Road"
    with pytest.raises(NotFound):
        store.get("feature", tid("d"), View())
    stored = store.import_run(rep.run)
    assert stored["state"] == "planned" and stored["dry_run"] and stored["counts"]["created"] == 1
    # a dry run reports what an apply would refuse
    bad = store.apply_import(
        run(), [feature("a"), {**feature("e"), "data": {"name": 5, "class": "road"}}], dry_run=True
    )
    assert bad.errors and bad.errors[0]["id"] == tid("e") and bad.errors[0]["path"] == "/data/name"


def test_rerun_writes_nothing(store, imp_layer):
    recs = [
        feature("a"),
        feature("b"),
        {"kind": "t_node", "id": tid("n"), "data": {"name": "N"}, "geom": "POINT (1 2)"},
    ]
    first = store.apply_import(run(), recs, dry_run=False)
    assert first.counts["created"] == 3 and first.changeset
    seq = store.last_seq()
    con = raw(store)
    before = con.execute("SELECT count(*) FROM rec_hist").fetchone()[0]
    again = store.apply_import(run(), list(reversed(recs)), dry_run=False)
    assert again.counts == {"created": 0, "updated": 0, "unchanged": 3, "deleted": 0, "conflicts": 0}
    assert again.changeset is None and again.changes == []
    assert store.last_seq() == seq
    assert con.execute("SELECT count(*) FROM rec_hist").fetchone()[0] == before
    con.close()
    assert store.import_run(again.run)["state"] == "unchanged"


def test_removal_is_import_tombstone(store, imp_layer):
    store.apply_import(run(), [feature("a"), feature("b")], dry_run=False)
    rep = store.apply_import(run(), [feature("a")], dry_run=False)
    assert rep.counts["deleted"] == 1
    hist = store.history("feature", tid("b"), View(layer="import:test"))
    assert hist[0]["deleted"] is True and hist[0]["origin"] == "import" and hist[0]["by"] == "import:t"
    with pytest.raises(NotFound):
        store.get("feature", tid("b"), View())
    # it comes back as a new version when the source has it again
    back = store.apply_import(run(), [feature("a"), feature("b")], dry_run=False)
    assert back.counts["created"] == 1
    assert store.get("feature", tid("b"), View())["version"] == 3


def test_duplicate_ids_refused(store, imp_layer):
    seq = store.last_seq()
    with pytest.raises(Invalid) as e:
        store.apply_import(run(), [feature("a"), feature("b"), feature("a", "again")], dry_run=False)
    assert "duplicate id" in e.value.errors[0]["message"]
    assert store.last_seq() == seq and store.list("feature", View())[0] == []
    rep = store.apply_import(run(), [feature("a"), feature("a")], dry_run=True)
    assert rep.errors and rep.changeset is None
    # an id outside the layer's namespace is refused as a whole
    from region.core import ids

    stray = {**feature("x"), "id": ids.stable("profiles", "x")}
    with pytest.raises(Conflict) as c:
        store.apply_import(run(), [feature("a"), stray], dry_run=False)
    assert c.value.reason == "namespace"
    assert store.list("feature", View())[0] == []
