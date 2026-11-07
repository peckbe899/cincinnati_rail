"""region.model: migrations apply, records version with If-Match, history is kept, legacy keys resolve, the R-tree
finds things, and the seed round-trips byte-identical."""
import json

import pytest
from shapely.geometry import LineString, Point

from region.model import db as D
from region.model import seed as S


@pytest.fixture
def con():
    return D.open_db(":memory:")


def _two_nodes(con):
    a = D.put(con, "node", {"kind": "line_end", "name": "A", "system": "metro", "geom": Point(712000, 4331000)}, source="test")
    b = D.put(con, "node", {"kind": "stop", "name": "B", "system": "metro", "geom": Point(713000, 4331500)}, source="test")
    return a, b


def test_migrations_apply_once(con):
    assert [r[0] for r in con.execute("SELECT version FROM schema_version")] == [1]
    assert D.migrate(con) == []
    assert "section" in D.tables(con) and "legacy_key" in D.tables(con)


def test_put_get_version_and_conflict(con):
    a, b = _two_nodes(con)
    sid = D.put(con, "section", {"name": "Line 6, A to B", "system": "metro", "node_a": a, "node_b": b, "length_m": 1118.0,
                                 "geom": LineString([(712000, 4331000), (713000, 4331500)]), "st": {"B": 160.9}, "pvi": [[300, 161.2]]})
    rec = D.get(con, "section", sid)
    assert rec["version"] == 1 and rec["st"] == {"B": 160.9} and rec["pvi"] == [[300, 161.2]] and rec["geom"].length == pytest.approx(1118.03, abs=0.1)
    D.put(con, "section", {**rec, "name": "renamed"}, if_version=1)
    assert D.get(con, "section", sid)["version"] == 2
    with pytest.raises(D.Conflict):
        D.put(con, "section", {**rec, "name": "stale"}, if_version=1)
    h = D.history(con, "section", sid)
    assert len(h) == 1 and h[0]["version"] == 1 and h[0]["record"]["name"] == "Line 6, A to B"


def test_legacy_keys_resolve(con):
    a, _ = _two_nodes(con)
    st = D.put(con, "station", {"name": "Sycamore", "system": "metro", "geom": Point(715445, 4331182)})
    D.add_legacy(con, "deck_station", "metro:Syacmore:715445:4331182", "station", st, note="typo in the old key")
    assert D.legacy(con, "deck_station", "metro:Syacmore:715445:4331182") == st
    assert D.legacy(con, "deck_station", "nope") is None


def test_rtree_finds_by_bbox(con):
    a, b = _two_nodes(con)
    assert D.within(con, "node", (711900, 4330900, 712100, 4331100)) == [a]
    assert set(D.within(con, "node", (700000, 4300000, 720000, 4340000))) == {a, b}
    rec = D.get(con, "node", a)
    D.put(con, "node", {**rec, "geom": Point(720000, 4335000)}, if_version=rec["version"])
    assert D.within(con, "node", (711900, 4330900, 712100, 4331100)) == []
    assert D.within(con, "node", (719000, 4334000, 721000, 4336000)) == [a]


def test_seed_round_trip_is_byte_identical(con, tmp_path):
    a, b = _two_nodes(con)
    D.put(con, "section", {"name": "s", "system": "metro", "node_a": a, "node_b": b, "length_m": 10.0, "geom": LineString([(0, 0), (10, 0)]), "ovr": [[0, 5, "cutcover"]]})
    D.add_legacy(con, "k", "old", "node", a)
    n = S.export(con, tmp_path / "seed")
    assert n == 4
    files = {p.relative_to(tmp_path / "seed"): p.read_text() for p in (tmp_path / "seed").rglob("*.json")}
    con2 = D.open_db(":memory:")
    rep = S.import_seed(con2, tmp_path / "seed", conflicts=tmp_path / "conf")
    assert rep["added"] == 4 and not rep["conflicts"]
    S.export(con2, tmp_path / "seed2")
    files2 = {p.relative_to(tmp_path / "seed2"): p.read_text() for p in (tmp_path / "seed2").rglob("*.json")}
    assert files == files2


def test_import_merges_instead_of_overwriting(con, tmp_path):
    a, b = _two_nodes(con)
    S.export(con, tmp_path / "seed")
    # Ben edits node A locally; the seed changes node B; a second import must keep A and take B
    ra = D.get(con, "node", a); D.put(con, "node", {**ra, "name": "A edited by Ben"}, if_version=ra["version"])
    pb = tmp_path / "seed" / "node" / f"{b}.json"; rb = json.loads(pb.read_text()); rb["name"] = "B from the seed"; rb["version"] = 2
    pb.write_text(json.dumps(rb, sort_keys=True, indent=1) + "\n")
    rep = S.import_seed(con, tmp_path / "seed", conflicts=tmp_path / "conf")
    assert D.get(con, "node", a)["name"] == "A edited by Ben"
    assert D.get(con, "node", b)["name"] == "B from the seed"
    assert rep["kept"] >= 1 and rep["taken"] == 1 and not rep["conflicts"]
    # both sides change A: ours is kept and the seed's copy is listed
    pa = tmp_path / "seed" / "node" / f"{a}.json"; ra2 = json.loads(pa.read_text()); ra2["name"] = "A from the seed"; ra2["version"] = 2
    pa.write_text(json.dumps(ra2, sort_keys=True, indent=1) + "\n")
    rep = S.import_seed(con, tmp_path / "seed", conflicts=tmp_path / "conf")
    assert D.get(con, "node", a)["name"] == "A edited by Ben" and ("node", a) in rep["conflicts"]
    assert (tmp_path / "conf" / f"node__{a}.json").exists()
