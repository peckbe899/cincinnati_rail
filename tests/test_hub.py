"""The hub's store: records addressed as the pages address them, versions, history, live events, seed and export."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hub"))


def test_store_records_versions_history_events(tmp_path):
    from store import Store
    s = Store(str(tmp_path / "hub.db"))
    ev = []
    s.listeners.append(ev.append)
    assert s.set("alignments/Line_1", {"pvi": [[0, 1]]}) == 1
    assert s.set("alignments/Line_1", {"pvi": [[0, 1]]}) == 1          # unchanged: no new version
    assert s.set("alignments/Line_1", {"pvi": [[0, 2]]}) == 2
    assert s.set("alignments/Line_1", {"pvi": [[0, 3]]}, if_version=1) is None   # stale write refused
    assert [h["version"] for h in s.history("alignments/Line_1")] == [1]
    assert s.restore("alignments/Line_1", 1) == 3 and s.get("alignments/Line_1")["data"] == {"pvi": [[0, 1]]}
    s.update("roadmap/r1", {"title": "a", "phase": "1"})
    s.update("roadmap/r1", {"phase": {"__delete__": True}})
    assert s.get("roadmap/r1")["data"] == {"title": "a"}
    assert [r["path"] for r in s.list("alignments")] == ["alignments/Line_1"]
    assert s.list("snapshots/region/parts") == []
    assert {e["p"] for e in ev if e["t"] == "doc"} == {"alignments/Line_1", "roadmap/r1"}


def test_store_seed_and_export_round_trip(tmp_path):
    from store import Store
    seed = tmp_path / "seed"
    (seed / "deck").mkdir(parents=True)
    (seed / "deck" / "layout.json").write_text(json.dumps({"transit": {"x": {"c": [[0, 0], [1, 1]]}}}))
    s = Store(str(tmp_path / "hub.db"))
    assert s.load_dir(str(seed)) == 1 and s.load_dir(str(seed)) == 0
    s.set("snapshots/region", {"json": "{}"})     # derived: not exported
    s.set("roadmap/r1", {"title": "t"})
    out = tmp_path / "out"
    assert s.export_dir(str(out)) == 2
    assert json.loads((out / "deck" / "layout.json").read_text())["transit"]["x"]["c"] == [[0, 0], [1, 1]]
    assert not (out / "snapshots").exists()


def test_pipeline_triggers():
    from pipeline import trigger_for, js_object
    assert trigger_for("deck/layout") == "deck_tie"
    assert trigger_for("alignments/Line_8") == "3d" and trigger_for("config/settings_rer") == "3d"
    assert trigger_for("snapshots/region") is None and trigger_for("roadmap/r1") is None
    html = (Path(__file__).resolve().parent.parent / "data/profile/profiles.html").read_text(encoding="utf8")
    assert js_object(html, "METRO_DEFAULTS")["platform"] == 121.92 and js_object(html, "RER_DEFAULTS")["platform"] == 204.2
