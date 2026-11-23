"""The live hub's budgets as tests (checklist I2.0, item 5), over a copy of the imported database with a real
engine: a saved line file reaches the hub in under 3 s, a burst of 50 writes is one import and one solve, one line's
change re-solves only that line, an unchanged re-save and a note edit run nothing, an import never overrides Ben's
edit, Undo this import reverts it and holds the files, and the 1912 handshake turning done makes its ground layer
available and re-plans the ground-dependent results with the focused section first."""

from __future__ import annotations

import json
import os
import threading
import time

from region.core.view import View
from tests.live.conftest import REPO, Env, until

LINE = "Line_3"


def _move_two_stations(doc: dict) -> None:
    doc["stations"][2]["c"] += 5.0
    doc["stations"][3]["c"] += 5.0


def _source_events(env: Env, source: str) -> list[dict]:
    return [p for _t, p in env.since("source") if p["source"] == source]


def test_a_saved_line_file_is_taken_in_and_solved_in_under_3_s(env: Env) -> None:
    """Budget: from Ben's save of one line file to the import applied (what the open sheet reads) and the server's
    solve of that line, under 3 s with the default 1.5 s settle period."""
    sid = env.section(LINE)
    env.mark()
    t0 = time.monotonic()
    env.edit(LINE, _move_two_stations)
    applied = until(
        lambda: next((t for t, p in env.since("source") if p["source"] == "import:profile_lines" and p["toast"]), None),
        what="the import's source event",
    )
    solved = until(
        lambda: next(
            (t for t, p in env.since("result") if p["scope"] == sid and p["type"] == "profiles.solve_section"), None
        ),
        what="the solve of Line 3",
    )
    taken, done = applied - t0, solved - t0
    print(f"\nline file saved -> import applied {taken:.2f} s, -> solved {done:.2f} s")
    assert taken < 3.0 and done < 3.0
    ev = _source_events(env, "import:profile_lines")[-1]
    assert ev["text"].startswith("Line 3 updated from the line files: 2 stations moved, re-solving"), ev["text"]
    assert ev["sections"] == [sid] and ev["undo"] is True
    assert ev["live"]["paused"] is False


def test_only_the_applied_change_names_its_sections(env: Env) -> None:
    """The open sheet reads its inputs again when a source event names its section. The event that says an import
    has started (and any that applies nothing) names none: the sections of the import before it, sent again with the
    "reading" event, had every open sheet read its inputs while the import ran, which took the import's time from
    2.4 s to over 4 s. Only the applied change names Line 3."""
    sid = env.section(LINE)
    env.edit(LINE, _move_two_stations)
    until(lambda: env.settle(), what="the first import")
    env.mark()
    env.edit(LINE, lambda d: d["stations"][2].__setitem__("c", d["stations"][2]["c"] + 1.0))
    until(lambda: any(p["toast"] for p in _source_events(env, "import:profile_lines")), what="the second import")
    evs = _source_events(env, "import:profile_lines")
    assert "importing" in [e["state"] for e in evs]
    for e in evs:
        assert e["sections"] == ([sid] if e["toast"] and e["state"] in ("applied", "review") else []), e
    assert env.settle()
    env.mark()
    f = env.line(LINE)
    f.write_bytes(f.read_bytes())
    os.utime(f, None)
    until(lambda: any(p["state"] == "idle" for p in _source_events(env, "import:profile_lines")), what="the re-save")
    assert all(e["sections"] == [] for e in _source_events(env, "import:profile_lines"))


def test_the_next_import_waits_while_open_sheets_read_the_applied_change(env: Env) -> None:
    """A line file feeds two importers (the line files' and the old hub's, whose profiles hang on the line files).
    Once the first has applied its change, the open sheets read their inputs again at once; the second import waits
    ``yield_s`` (0.4 s) before it starts, so it does not compete with those reads for the hub's time."""
    env.mark()
    env.edit(LINE, _move_two_stations)
    until(lambda: any(p["toast"] for p in _source_events(env, "import:profile_lines")), what="the line files' import")
    assert env.settle()
    applied = next(t for t, p in env.since("source") if p["source"] == "import:profile_lines" and p["toast"])
    started = [t for t, p in env.since("source") if p["source"] == "import:old_hub" and p["state"] == "importing"]
    assert started, "the old hub's import never started"
    assert started[0] - applied >= env.live.yield_s - 0.05, started[0] - applied


def test_the_first_save_after_the_start_hashes_only_what_changed(env: Env, monkeypatch) -> None:
    """The hub learns each importer's records at its start (in the background, after the catch-up), so the first
    line file Ben saves is not slower than the next: its import hashes the records that changed, not all 1,400."""
    from region.model import imports as IM

    hashed: list[str] = []
    real = IM.content_hash
    monkeypatch.setattr(IM, "content_hash", lambda *a, **k: hashed.append(a[0]) or real(*a, **k))
    env.mark()
    env.edit(LINE, _move_two_stations)
    until(lambda: any(p["toast"] for p in _source_events(env, "import:profile_lines")), what="the import")
    assert env.settle()
    assert 0 < len(hashed) < 50, len(hashed)


def test_a_burst_of_50_writes_is_one_import_and_one_solve(env: Env) -> None:
    """Budget: 50 writes to one line file over 1 s (a Deck tie, a half-written file) give exactly one import and one
    solve of the line they touch."""
    sid = env.section(LINE)
    env.mark()
    for i in range(50):
        env.edit(LINE, lambda d, i=i: d["stations"][2].__setitem__("c", d["stations"][2]["c"] + 0.1))
        time.sleep(0.02)
    assert env.settle()
    assert len(env.imports("profile_lines")) == 1
    assert env.solves() == [sid]


def test_one_line_changed_re_solves_only_that_line(env: Env) -> None:
    """Budget: a change to one line file re-solves exactly that line's section (job count), not the other 15."""
    sid = env.section(LINE)
    env.mark()
    env.edit(LINE, _move_two_stations)
    until(lambda: env.solves(), what="a solve")
    assert env.settle()
    assert env.solves() == [sid]
    assert [i["importer"] for i in env.imports()] == ["profile_lines"]


def test_an_unchanged_re_save_runs_nothing(env: Env) -> None:
    """Budget: saving a line file again with the same bytes runs no import and no job."""
    env.mark()
    f = env.line(LINE)
    f.write_bytes(f.read_bytes())
    os.utime(f, None)
    until(lambda: any(p["source"] == "import:profile_lines" and p["state"] == "idle" for _t, p in env.since("source")),
          what="the re-save to be looked at")  # fmt: skip
    assert env.settle()
    assert env.imports() == []
    assert env.solves() == []
    assert [p for _t, p in env.since("job")] == []


def test_a_note_edit_re_solves_nothing(env: Env) -> None:
    """A note is truth that no job reads: editing one plans nothing that runs."""
    env.mark()
    env.store.put({"kind": "note", "id": None, "data": {"text": "check the portal"}, "geom": None}, View(),
                  if_match=None, by="ben")  # fmt: skip
    time.sleep(0.5)
    assert env.settle()
    assert [p for _t, p in env.since("job")] == []


def test_an_import_that_would_override_ben_is_not_applied_over_him_and_waits_in_review(env: Env) -> None:
    """Design rule 3: Ben edits Line 3's profile in scenario try; the line file then moves two of its stations.
    The import is taken in below him, his profile stays exactly as he left it, and the change that touches it is
    in the review queue, which the toast says."""
    from region.core.protocols import etag

    store = env.store
    store.create_layer("try", by="ben")
    tv = View(layer="try")
    sid = env.section(LINE)
    (prof,) = store.list("profile", tv, parent=sid)[0]
    pvi = prof["data"]["pvi"]
    edit = [{"op": "replace", "path": "/data/pvi/1", "value": [pvi[1][0], pvi[1][1] + 0.5]}]
    store.patch("profile", prof["id"], edit, tv, if_match=etag(prof["layer"], prof["version"]), by="ben")
    mine = store.get("profile", prof["id"], tv)
    env.mark()
    env.edit(LINE, _move_two_stations)
    ev = until(lambda: next((p for p in _source_events(env, "import:profile_lines") if p["toast"]), None),
               what="the import")  # fmt: skip
    assert env.settle()
    after = store.get("profile", prof["id"], tv)
    assert after["hash"] == mine["hash"] and after["data"]["pvi"][1][1] == pvi[1][1] + 0.5
    mine_open = [c for c in store.conflicts(layer="try") if c["rec_id"] == prof["id"]]
    assert [c["reason"] for c in mine_open] == ["geometry_under_edit"]
    assert ev["state"] == "review" and ev["review"] >= 1
    assert "touches your edits and waits in Review" in ev["text"], ev["text"]


def test_undo_this_import_reverts_it_and_holds_the_files(env: Env) -> None:
    """Undo this import reverts the import's changeset (the stations go back), and the same files are not taken in
    again until they change; Apply takes them anyway."""
    sid = env.section(LINE)
    stops = {s["id"]: s["data"]["c"] for s in env.store.list("stop", View(), parent=sid)[0]}
    env.mark()
    env.edit(LINE, _move_two_stations)
    until(lambda: env.imports("profile_lines"), what="the import")
    assert env.settle()
    moved = {s["id"]: s["data"]["c"] for s in env.store.list("stop", View(), parent=sid)[0]}
    assert sum(1 for k in stops if stops[k] != moved[k]) == 2
    st = env.live.undo("import:profile_lines", by="ben")
    assert st["state"] == "held"
    assert env.settle()
    back = {s["id"]: s["data"]["c"] for s in env.store.list("stop", View(), parent=sid)[0]}
    assert back == stops
    # a re-save of the same files stays held
    env.mark()
    f = env.line(LINE)
    f.write_bytes(f.read_bytes())
    until(lambda: any(p["state"] == "held" for p in _source_events(env, "import:profile_lines")), what="held")
    assert env.imports() == []
    # Apply takes them anyway
    env.live.apply_held("import:profile_lines")
    until(lambda: env.imports("profile_lines"), what="the held files applied")
    assert env.settle()
    again = {s["id"]: s["data"]["c"] for s in env.store.list("stop", View(), parent=sid)[0]}
    assert again == moved


def test_pause_holds_changes_and_resume_takes_them_in(env: Env) -> None:
    env.mark()
    env.live.pause()
    env.edit(LINE, _move_two_stations)
    until(lambda: env.live.summary()["pending"] >= 1, what="the change to wait")
    time.sleep(2.0)
    assert env.imports() == [] and env.live.summary()["paused"] is True
    env.live.resume()
    until(lambda: env.imports("profile_lines"), what="the import after resume")
    assert env.settle()
    assert env.live.summary() == {**env.live.summary(), "paused": False, "pending": 0}


def test_the_1912_handshake_turning_done_makes_the_ground_layer_available_focused_section_first(env: Env) -> None:
    """Ground: the 1912 tier's handshake turning done imports the real_1912 ground_layer record as available and
    re-plans every result that read it (here t.ground, standing for increment 2's ground.profile), the focused
    section's first; the sections show pending marks meanwhile."""
    from region.jobs.plan import all_records

    sched, view = env.sched, View()
    sections = [r["id"] for r in all_records(env.store, "section", view)]
    focused = env.section("Line_6")
    for s in sections:
        sched.watch_goal("t.ground", s, view, priority=0 if s == focused else 5)
    assert env.settle()
    (layer,) = all_records(env.store, "ground_layer", view)
    assert layer["data"]["key"] == "real_1912" and layer["data"]["available"] is False
    env.mark()
    marks: list[list[dict]] = []
    env.live.publish_fn = lambda k, p: (env.record(k, p), marks.append(p["items"]) if k == "pending" else None)
    status = json.loads((env.ground / "STATUS.json").read_text(encoding="utf-8"))
    status.update({"done": True, "stage": "surface"})
    (env.ground / "STATUS.json").write_text(json.dumps(status), encoding="utf-8")
    until(lambda: set(env.solves("t.ground")) >= set(sections), what="every ground result re-planned", timeout=30)
    assert env.settle()
    order = env.solves("t.ground")
    # each re-planned, the focused section first (a result can be planned twice: once for the handshake file, once
    # for the ground layer record its import changes a moment later, when the first job has already started)
    assert order[0] == focused and sorted(set(order)) == sorted(sections)
    (layer,) = all_records(env.store, "ground_layer", view)
    assert layer["data"]["available"] is True and layer["data"]["stage"] == "surface"
    texts = [p["text"] for p in _source_events(env, "tier:ground_1912_real")]
    assert any(t.startswith("1912 ground: stage contours to surface, ready to use") for t in texts), texts
    # (the rails of the lines with no saved design read the ground too: their marks come in the same events)
    assert any(any(i["type"] == "t.ground" for i in m) for m in marks), "no pending marks were sent"
    assert env.live.marks() == []


def test_editing_stays_smooth_while_a_background_import_runs(env: Env) -> None:
    """Budget: while every line file is imported (all 16 changed, as a Deck tie writes them), reads and writes of
    the store answer within 200 ms."""
    from region.core.protocols import etag

    store = env.store
    store.create_layer("try", by="ben")
    tv = View(layer="try")
    sid = env.section("Line_6")
    env.mark()

    def shift(doc: dict) -> None:
        for s in doc["stations"]:
            s["offset"] = (s.get("offset") or 0) + 0.1

    for f in sorted((env.profile / "lines").glob("Line_*.json")):
        env.edit(f.stem, shift)
    worst = total = 0.0
    stop = threading.Event()
    n = 0

    def edits() -> None:
        nonlocal worst, total, n
        while not stop.is_set():
            t = time.perf_counter()
            (prof,) = store.list("profile", tv, parent=sid)[0]
            store.patch("profile", prof["id"], [{"op": "replace", "path": "/data/pvi/1/1",
                                                  "value": prof["data"]["pvi"][1][1] + 0.01}],
                        tv, if_match=etag(prof["layer"], prof["version"]), by="ben")  # fmt: skip
            worst = max(worst, time.perf_counter() - t)
            total += time.perf_counter() - t
            n += 1
            time.sleep(0.05)

    th = threading.Thread(target=edits)
    th.start()
    try:
        until(lambda: env.imports("profile_lines"), what="the big import", timeout=30)
    finally:
        stop.set()
        th.join()
    assert env.settle()
    mean = total / max(n, 1)
    print(f"\n{n} edits while importing 16 lines; slowest {worst * 1000:.0f} ms, mean {mean * 1000:.0f} ms")
    assert n > 10 and worst < 0.2


def test_repo_sources_are_declared() -> None:
    """Every importer's sources and every tier of the repo's config are watched, and the old hub's live database
    with the old hub."""
    from region.core import paths
    from region.live.sources import declared

    srcs = {s.id: s for s in declared(paths.config())}
    assert {"import:registry", "import:profile_lines", "import:old_hub", "import:ground_layers"} <= set(srcs)
    assert {f"tier:{t}" for t in paths.config()["tiers"]} <= set(srcs)
    db = [w for w in srcs["import:old_hub"].watches if w.mode == "db"]
    assert db and db[0].path == REPO / "hub" / "hub.db"
    hs = [w for w in srcs["tier:ground_1912_real"].watches if w.label == "handshake"]
    assert hs and hs[0].path.name == "STATUS.json"


def _get(env: Env, path: str) -> dict:
    """GET a profiles route on the live hub's store and scheduler, as the sheet asks it."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from region.ext.profiles.router import router

    app = FastAPI()
    app.state.store = env.store
    app.state.jobs = env.sched
    app.include_router(router, prefix="/x/profiles")
    r = TestClient(app).get(path)
    assert r.status_code == 200, r.text
    return r.json()


def _solve_input(env: Env, route: str) -> dict:
    return _get(env, f"/x/profiles/sections/{env.section(route)}/solve")


def test_every_sheet_crosses_the_lines_with_no_saved_design(env: Env, pool) -> None:
    """Lines 10, 11 and 13 have no saved design: the hub keeps each line's rail as its crossings read it ready
    (``profiles.neighbour``, a background goal per section, cached by content and cut off early), and the sheet's
    solve input reads them without planning a job. Line 6 then shows Line 13 at 1.9 m, Line 10 at 4.3 m and Line 11
    at 0.2 m apart, as the old page does; the request starts no job; and a change of Line 3 (whose levels are all
    saved: its view is read from its records) runs no rail job, Line 3's or the others'."""
    # the rails are kept from the start (after rails_delay_s, 0 here): wait for them to be warm
    until(lambda: {"Line_10", "Line_11", "Line_13"} <= set(_solve_input(env, "Line_6")["neighbours"]), timeout=60,
          what="the rails of Lines 10, 11 and 13")  # fmt: skip
    env.mark()
    inp = _solve_input(env, "Line_6")
    assert [p for _t, p in env.since("job")] == [], "the request planned or ran a job"
    for wid in ("Line_10", "Line_11", "Line_13"):
        assert wid in inp["neighbours"], sorted(inp["neighbours"])
        assert inp["neighbours"][wid]["source"] == "default"
    out = pool.call("section.solve", inp)
    # Line 10's own sheet draws the same default design, marked as not saved
    design = _get(env, f"/x/profiles/sections/{env.section('Line_10')}/design")
    assert design["source"] == "default" and design["note"] == "default design (not saved)"
    assert len(design["pvi"]) == 2 and all(isinstance(z, float) for z in design["st"].values())
    assert _get(env, f"/x/profiles/sections/{env.section('Line_6')}/design") == {"source": "saved"}
    clear = {(x["wid"], round(x["c"], 1)): x["clear"] for x in out["crossings"]}
    assert abs(clear[("Line_13", 4833.9)] - 1.86) < 0.05
    assert abs(clear[("Line_10", 8652.6)] - 4.27) < 0.05
    assert abs(clear[("Line_11", 14950.9)] - 0.22) < 0.05
    env.mark()
    env.edit(LINE, _move_two_stations)
    until(lambda: env.solves(), what="a solve")
    assert env.settle()
    assert env.solves("profiles.neighbour") == []


def test_a_line_added_by_a_line_file_has_its_rail_kept(env: Env) -> None:
    """A line Ben adds (its file and its row in the index) makes a new section with no saved level: the hub
    keeps its rail (``profiles.neighbour``) at once, as for Lines 10, 11 and 13 at the start, so the lines crossing
    it read its levels without a restart. (The section was watched for its solve, but its rail goal waited in a list
    only the start reads.)"""
    doc = json.loads(env.line("Line_13").read_text(encoding="utf-8"))
    doc["id"] = "Line_99"
    doc["line"] = "Line 99"
    doc["crossings"] = []
    # a line of its own, 1 km north of Line 13 (the same ends would read as Line 13 renamed)
    doc["path"] = [[c, lon, lat + 0.009] for c, lon, lat in doc["path"]]
    for s in doc["stations"]:
        s["lat"] += 0.009
    env.mark()
    env.line("Line_99").write_text(json.dumps(doc), encoding="utf-8")
    index = env.profile / "lines" / "index.json"
    entries = json.loads(index.read_text(encoding="utf-8"))
    entries.append({"id": "Line_99", "line": "Line 99", "length_m": doc["length_m"], "stations": len(doc["stations"])})
    index.write_text(json.dumps(entries), encoding="utf-8")
    from region.jobs.plan import all_records

    until(lambda: "Line_99" in {r["data"]["key"] for r in all_records(env.store, "section", View())}, timeout=30,
          what="the new section")  # fmt: skip
    assert env.settle()
    sid = env.section("Line_99")
    assert sid in env.solves("profiles.neighbour"), env.solves("profiles.neighbour")
    design = _get(env, f"/x/profiles/sections/{sid}/design")
    assert design["source"] == "default", design
