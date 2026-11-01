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
    assert trigger_for("alignments/Line_8") == "platform_tie" and trigger_for("config/settings_rer") == "3d"
    assert trigger_for("snapshots/region") is None and trigger_for("roadmap/r1") is None
    assert trigger_for("chronology/segments") == "3d" and trigger_for("params/metro_structure") == "3d"
    html = (Path(__file__).resolve().parent.parent / "data/profile/profiles.html").read_text(encoding="utf8")
    assert js_object(html, "METRO_DEFAULTS")["platform"] == 121.92 and js_object(html, "RER_DEFAULTS")["platform"] == 204.2


def test_store_merges_a_pulled_seed(tmp_path):
    from store import Store
    def write(root, path, data):
        f = root / (path + '.json'); f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(data))
    old, new = tmp_path / 'old', tmp_path / 'new'
    write(old, 'deck/layout', {'streets': {'A': {'c': 1}, 'B': {'c': 1}}, 'stations': {'K': {'o': 0}}})
    write(old, 'alignments/L1', {'pvi': [1]})
    write(old, 'alignments/L2', {'pvi': [1]})
    st = Store(str(tmp_path / 'db.sqlite'))
    st.load_dir(str(old))                      # a database seeded before seed_base existed
    st.set('deck/layout', {'streets': {'A': {'c': 1}, 'B': {'c': 9}}, 'stations': {'K': {'o': 5}}}, 'Ben')
    st.set('alignments/L2', {'pvi': [7]}, 'page')
    write(new, 'deck/layout', {'streets': {'A': {'c': 2}, 'B': {'c': 3}}, 'stations': {'K': {'o': 0}}})
    write(new, 'alignments/L1', {'pvi': [2]})
    write(new, 'alignments/L2', {'pvi': [1]})
    write(new, 'chronology/segments', {'segments': {}})
    rep = st.merge_dir(str(new))
    lay = st.get('deck/layout')['data']
    assert lay['streets']['A'] == {'c': 2}        # only the seed changed it
    assert lay['streets']['B'] == {'c': 9}        # both changed it: Ben's kept, listed
    assert lay['stations']['K'] == {'o': 5}       # only Ben changed it
    assert st.get('alignments/L1')['data'] == {'pvi': [2]} and st.get('alignments/L2')['data'] == {'pvi': [7]}
    assert rep['added'] == ['chronology/segments'] and rep['conflicts'] == [{'path': 'deck/layout', 'keys': ['streets']}]
    assert not any(st.merge_dir(str(new))[k] for k in ('added', 'updated', 'merged'))   # a second start changes nothing
    st.set('alignments/L3', {'pvi': [5]}, 'Ben')   # no seed base for it: reported once, then not again
    write(new, 'alignments/L3', {'pvi': [6]})
    assert any(c['path'] == 'alignments/L3' for c in st.merge_dir(str(new))['conflicts'])
    assert not any(c['path'] == 'alignments/L3' for c in st.merge_dir(str(new))['conflicts']) and st.get('alignments/L3')['data'] == {'pvi': [5]}


def test_chronology_months_and_timeline():
    import subprocess
    js = r"""
const C = require('./hub/static/chronology_rules.js');
const r = { id: 'L', name: 'Line X', sys: 'metro', segments: ['a', 'b'], stations: [{ name: 'P', c: 0 }, { name: 'Q', c: 1 }, { name: 'R', c: 2 }], path: [[0, 0, 0]] };
const rec = { phase_years: [[1800, 2200, '1']], segments: { a: { year: 1930, month: 6 }, b: { year: 1925, month: 9 } }, stations: {} };
const ed = C.applyEdit([r], rec, { segments: { b: { year: 1920 } } });   // no order rules: any year is taken
console.log(ed.rec.segments.b.year === 1920 && !('violations' in ed.analysis));
const md = C.timeline([r], rec);
console.log(md.includes('**June**') && md.includes('**September**') && md.indexOf('1925') < md.indexOf('1930') && md.includes('P to Q'));
"""
    out = subprocess.run(['node', '-e', js], cwd=str(Path(__file__).resolve().parent.parent), capture_output=True, text=True).stdout.split()
    assert out == ['true', 'true']


def test_store_merge_skips_an_unreadable_seed_file(tmp_path):
    from store import Store
    root = tmp_path / 'seed'; (root / 'deck').mkdir(parents=True)
    (root / 'deck' / 'layout.json').write_text('<<<<<<< HEAD\n{"a": 1}\n=======\n{"a": 2}\n>>>>>>> theirs\n')
    st = Store(str(tmp_path / 'db.sqlite')); st.set('deck/layout', {'a': 0}, 'Ben')
    rep = st.merge_dir(str(root))   # no exception: the record is kept and the file listed
    assert st.get('deck/layout')['data'] == {'a': 0} and rep['conflicts'][0]['path'] == 'deck/layout'


def test_pipeline_runs_the_platform_tie_on_a_profile_save():
    from pipeline import trigger_for
    assert trigger_for('alignments/Line_5') == 'platform_tie' and trigger_for('deck/layout') == 'deck_tie'
    assert trigger_for('params/metro_structure') == '3d'


def test_seed_merge_keeps_a_profile_whole(tmp_path):
    """a profile changed here and in the seed is kept as saved here, not mixed key by key (realism audit A7)"""
    from store import Store
    def write(root, path, data):
        f = root / (path + '.json'); f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(data))
    old, new = tmp_path / 'old', tmp_path / 'new'
    write(old, 'alignments/L9', {'pvi': [[0, 1]], 'st': {'A': 5}})
    st = Store(str(tmp_path / 'db.sqlite'))
    st.load_dir(str(old))
    st.set('alignments/L9', {'pvi': [[0, 2]], 'st': {'A': 5}}, 'page')          # Ben moved a bend
    write(new, 'alignments/L9', {'pvi': [[0, 1]], 'st': {'A': 8}})            # the seed moved the station
    rep = st.merge_dir(str(new))
    assert st.get('alignments/L9')['data'] == {'pvi': [[0, 2]], 'st': {'A': 5}}
    assert 'alignments/L9' in rep['kept'] and any(c['path'] == 'alignments/L9' for c in rep['conflicts'])


def test_saved_profile_read_in_its_own_frame():
    """a profile saved against older station points is mapped onto the current ones, platform centres kept (A1)"""
    import importlib.util, os
    spec = importlib.util.spec_from_file_location('rdr', os.path.join(str(Path(__file__).resolve().parent.parent), 'tools', 'rer_deck_routes.py'))
    rdr = importlib.util.module_from_spec(spec); spec.loader.exec_module(rdr)
    route = {'length_m': 1020.0, 'stations': [{'name': 'A', 'c': 120.0}, {'name': 'B', 'c': 620.0}]}
    doc = {'length_m': 1000.0, 'so': {'B': 30.0}, 'pvi': [[0, 1], [100, 2], [600, 3], [1000, 4]], 'ovr': [[90, 130, 'cutcover']], 'tf': [[200, 500, 'twin']],
           'stations': [{'name': 'A', 'point_c': 100.0, 'c': 100.0}, {'name': 'B', 'point_c': 600.0, 'c': 630.0}]}
    out = rdr.reframe_doc(dict(doc), route)
    assert out['reframed'] and out['length_m'] == 1020.0
    assert out['so'] == {'B': 30.0}                      # the slide follows its point: the centre stays 30 m past it
    assert [p[0] for p in out['pvi']] == [0, 120.0, 620.0, 1020.0] and out['ovr'][0][:2] == [108.0, 150.0] and out['tf'][0][:2] == [220.0, 520.0]
    same = rdr.reframe_doc(dict(doc, stations=[{'name': 'A', 'point_c': 120.0, 'c': 120.0}, {'name': 'B', 'point_c': 620.0, 'c': 650.0}]), route)
    assert 'reframed' not in same                         # already in the route's frame: untouched
