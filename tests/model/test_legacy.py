"""Match before mint (9.17): renamed keys keep their ids; the ledger is deterministic; old keys work both ways."""

from __future__ import annotations

from region.core import ids
from region.core.view import View
from region.model.legacy import IdLookupImpl, ledger_text, read_ledger
from tests.model.helpers import run

KEY = "Line_8|Cincinnati State#2"
RENAMED = "Line_8|Cincinnati St.#2"


def _station(rid: str, name: str, x: float) -> dict:
    return {"kind": "t_node", "id": rid, "data": {"name": name}, "geom": f"POINT ({x} 4331000)"}


def _by_position(x: float):
    def match(orphans):
        for r in orphans:
            if r["geom"] == f"POINT ({x} 4331000)":
                return r["id"]
        return None

    return match


def test_match_before_mint_keeps_id_on_rename(store, imp_layer, tmp_path):
    ledger = tmp_path / "ids"
    look = IdLookupImpl(store, layer="import:test", namespace="test", ledger_dir=ledger)
    first = look.id_for("t_node_key", KEY, kind="t_node")
    assert first == ids.stable("test", KEY)
    other = look.id_for("t_node_key", "Line_8|Elsewhere#1", kind="t_node")
    store.apply_import(
        run(),
        [_station(first, "Cincinnati State", 715000), _station(other, "Elsewhere", 716000)],
        dry_run=False,
        ids=look,
    )
    assert store.legacy("t_node_key", KEY) == first
    # the next run sees the key renamed: the legacy index has no entry, so match runs over the orphans
    look2 = IdLookupImpl(store, layer="import:test", namespace="test", ledger_dir=ledger)
    assert look2.id_for("t_node_key", "Line_8|Elsewhere#1", kind="t_node") == other
    renamed = look2.id_for("t_node_key", RENAMED, kind="t_node", match=_by_position(715000))
    assert renamed == first and renamed != ids.stable("test", RENAMED)
    rep = store.apply_import(
        run(),
        [_station(renamed, "Cincinnati St.", 715000), _station(other, "Elsewhere", 716000)],
        dry_run=False,
        ids=look2,
    )
    assert rep.counts["updated"] == 1 and rep.counts["created"] == 0 and rep.counts["deleted"] == 0
    assert store.legacy("t_node_key", RENAMED) == first and store.legacy("t_node_key", KEY) == first
    # without a match, a new key mints its stable id; a claimed record is no orphan
    look3 = IdLookupImpl(store, layer="import:test", namespace="test", ledger_dir=ledger)
    look3.id_for("t_node_key", RENAMED, kind="t_node")
    assert look3.id_for("t_node_key", "new", kind="t_node", match=_by_position(715000)) == ids.stable("test", "new")
    # a fresh database on another machine gets the renamed key's id from the ledger in git
    assert read_ledger(ledger / "test.tsv")[("t_node_key", RENAMED)] == first


def test_ledger_append_deterministic(make_store, tmp_path):
    keys = [f"Line_{i}|Station {j}#1" for i in (1, 6, 8) for j in "ABC"] + ["tab\there", "line\nbreak", "back\\slash"]
    texts = []
    for n, order in enumerate((keys, list(reversed(keys)))):
        s = make_store(f"db{n}.db")
        s.create_layer("import:test", namespace="test", by="t")
        ledger = tmp_path / f"ledger{n}"
        look = IdLookupImpl(s, layer="import:test", namespace="test", ledger_dir=ledger)
        got = [look.id_for("t_node_key", k, kind="t_node") for k in order]
        look.flush()
        assert got == [ids.stable("test", k) for k in order]
        texts.append((ledger / "test.tsv").read_bytes())
        # flushing the same keys again changes nothing
        again = IdLookupImpl(s, layer="import:test", namespace="test", ledger_dir=ledger)
        for k in keys:
            again.id_for("t_node_key", k, kind="t_node")
        again.flush()
        assert (ledger / "test.tsv").read_bytes() == texts[-1]
    assert texts[0] == texts[1]
    body = texts[0].decode("utf-8")
    assert "\r" not in body and body.endswith("\n")
    lines = [ln for ln in body.splitlines() if not ln.startswith("#")]
    assert lines == sorted(lines) and len(lines) == len(keys)
    entries = read_ledger(tmp_path / "ledger0" / "test.tsv")
    assert entries[("t_node_key", "tab\there")] == ids.stable("test", "tab\there")
    assert ledger_text(entries).encode("utf-8") == texts[0]


def test_legacy_both_ways(store, imp_layer, tmp_path):
    look = IdLookupImpl(store, layer="import:test", namespace="test", ledger_dir=tmp_path)
    rid = look.id_for("t_node_key", KEY, kind="t_node")
    store.apply_import(run(), [_station(rid, "Cincinnati State", 715000)], dry_run=False, ids=look)
    store.add_legacy("deck_station", "metro:Syacmore:715445:4331182", rid)
    assert store.legacy("t_node_key", KEY) == rid
    assert store.legacy("deck_station", "metro:Syacmore:715445:4331182") == rid
    assert store.legacy("t_node_key", "nope") is None
    assert store.legacy_keys(rid) == [
        {"lkind": "deck_station", "key": "metro:Syacmore:715445:4331182", "status": "current"},
        {"lkind": "t_node_key", "key": KEY, "status": "current"},
    ]
    assert store.legacy_record("t_node_key", KEY) == {"kind": "t_node", "id": rid}
    assert store.get("t_node", rid, View())["data"]["name"] == "Cincinnati State"
    # a dry run persists nothing
    look2 = IdLookupImpl(store, layer="import:test", namespace="test", ledger_dir=tmp_path / "dry")
    other = look2.id_for("t_node_key", "dry key", kind="t_node")
    store.apply_import(
        run(), [_station(rid, "Cincinnati State", 715000), _station(other, "D", 1)], dry_run=True, ids=look2
    )
    assert store.legacy("t_node_key", "dry key") is None and not (tmp_path / "dry" / "test.tsv").exists()
