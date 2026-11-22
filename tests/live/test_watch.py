"""The source watcher (``region/live/watch.py``): settling, bursts, pause, the old hub's database, and its cost."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from region.core import paths
from region.live.watch import Source, Watch, Watcher, dir_sig, tree_sig


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def _watcher(tmp: Path, *watches: Watch, settle: float = 1.5) -> tuple[Watcher, list, Clock]:
    got: list = []
    clock = Clock()
    w = Watcher([Source("s", "S", list(watches))], on_settled=lambda s, c: got.append(c), settle_s=settle, clock=clock)
    return w, got, clock


def test_a_burst_of_50_writes_settles_into_one_change(tmp_path: Path) -> None:
    f = tmp_path / "lines" / "Line_3.json"
    f.parent.mkdir()
    f.write_text("{}", encoding="utf-8")
    w, got, clock = _watcher(tmp_path, Watch(f.parent, "tree", "lines"))
    for i in range(50):  # 50 writes over 1 s, a poll every 20 ms
        f.write_text(json.dumps({"i": i, "pad": "x" * i}), encoding="utf-8")
        clock.t += 0.02
        w.poll_once()
    assert got == []  # still changing
    clock.t += 1.0
    w.poll_once()
    assert got == []  # quiet for 1.0 s only
    clock.t += 0.6
    w.poll_once()
    assert got == [{"lines": ["Line_3.json"]}]
    clock.t += 10
    w.poll_once()
    assert len(got) == 1


def test_a_file_put_back_as_it_was_is_no_change(tmp_path: Path) -> None:
    f = tmp_path / "a.json"
    f.write_text("one", encoding="utf-8")
    st = f.stat()
    w, got, clock = _watcher(tmp_path, Watch(f, "file", "a"))
    f.write_text("two", encoding="utf-8")
    w.poll_once()
    f.write_text("one", encoding="utf-8")
    import os

    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
    clock.t += 0.1
    w.poll_once()
    clock.t += 2
    w.poll_once()
    assert got == []


def test_pause_holds_a_change_and_resume_acts_on_it(tmp_path: Path) -> None:
    f = tmp_path / "a.json"
    f.write_text("one", encoding="utf-8")
    w, got, clock = _watcher(tmp_path, Watch(f, "file", "a"))
    w.pause()
    f.write_text("two!", encoding="utf-8")
    w.poll_once()
    clock.t += 5
    w.poll_once()
    assert got == [] and w.pending() == ["s"]
    w.resume()
    clock.t += 0.01
    w.poll_once()
    assert got == [{"a": [""]}] and w.pending() == []


def test_a_tile_folder_is_listed_not_walked(tmp_path: Path) -> None:
    (tmp_path / "tiles" / "deep").mkdir(parents=True)
    (tmp_path / "tiles" / "deep" / "t.png").write_bytes(b"x")
    (tmp_path / "tiles" / "index.json").write_text("[]", encoding="utf-8")
    assert set(dir_sig(tmp_path / "tiles")) == {"deep", "index.json"}
    assert set(tree_sig(tmp_path / "tiles")) == {"deep/t.png", "index.json"}


def test_the_old_hubs_database_is_seen_through_data_version(tmp_path: Path) -> None:
    """A commit by the old hub is seen even when the file's size and time stay as they were (a WAL write, or NTFS
    updating the time lazily): ``PRAGMA data_version`` on the watcher's read-only connection moves."""
    db = tmp_path / "hub.db"
    con = sqlite3.connect(db)
    con.execute("PRAGMA journal_mode=wal")
    con.execute("CREATE TABLE docs (path TEXT PRIMARY KEY, data TEXT)")
    con.commit()
    w, got, clock = _watcher(tmp_path, Watch(db, "db", "hub.db"))
    before = w._sigs(w.sources[0])[0]
    assert "data_version" in before
    con.execute("INSERT INTO docs VALUES ('alignments/Line_3', '{}')")
    con.commit()
    w.poll_once()
    clock.t += 2
    w.poll_once()
    assert got and "hub.db" in got[0] and "data_version" in got[0]["hub.db"]
    w.stop()
    con.close()


def test_pausing_lets_go_of_the_old_hubs_database_and_moves_nothing(tmp_path: Path) -> None:
    """Pause live closes the probe's connection and keeps it closed (the old hub may replace hub.db), and neither the
    pause nor the reconnect at resume counts as a change: ``data_version`` restarts with each connection."""
    db = tmp_path / "hub.db"
    con = sqlite3.connect(db)
    con.execute("PRAGMA journal_mode=wal")
    con.execute("CREATE TABLE docs (path TEXT PRIMARY KEY, data TEXT)")
    con.commit()
    w, got, clock = _watcher(tmp_path, Watch(db, "db", "hub.db"))
    for i in range(3):  # commits seen by the probe's connection: its data_version moves past a new one's first
        con.execute("INSERT INTO docs VALUES (?, '{}')", (f"a/{i}",))
        con.commit()
        w.poll_once()
    clock.t += 2
    w.poll_once()
    got.clear()
    w.pause()
    for _ in range(3):
        clock.t += 1
        w.poll_once()
    probe = w._probes[db]
    assert probe._con is None and w.pending() == []
    w.resume()
    for _ in range(3):
        clock.t += 1
        w.poll_once()
    assert probe._con is not None
    assert got == [] and w.pending() == []
    w.stop()
    con.close()


def test_a_source_that_never_stops_moving_is_acted_on_after_max_wait(tmp_path: Path) -> None:
    f = tmp_path / "log.txt"
    f.write_text("", encoding="utf-8")
    got: list = []
    clock = Clock()
    w = Watcher([Source("s", "S", [Watch(f, "file", "log")])], on_settled=lambda s, c: got.append(c), settle_s=1.5,
                max_wait_s=10, clock=clock)  # fmt: skip
    for i in range(60):  # a line every 0.5 s for 30 s: never quiet for 1.5 s
        f.write_text("x" * (i + 1), encoding="utf-8")
        clock.t += 0.5
        w.poll_once()
    assert len(got) == 2  # 10 s after the first write it saw, and 10 s after the next


def test_the_idle_watcher_costs_under_1_percent_of_a_cpu(tmp_path: Path) -> None:
    """Budget: the watcher over every source this repo declares (and an old hub database), idle for 10 s, uses under
    1 % of one CPU. Run in a process of its own so nothing else is counted."""
    db = tmp_path / "hub.db"
    sqlite3.connect(db).execute("CREATE TABLE docs (path TEXT, data TEXT)").connection.commit()
    script = textwrap.dedent(
        f"""
        import json, time
        from region.core import paths
        from region.live.sources import declared
        from region.live.watch import Watch, Watcher
        cfg = paths.config()
        cfg["live"] = {{"old_hub_db": {str(db)!r}}}
        srcs = declared(cfg)
        w = Watcher(srcs, on_settled=lambda s, c: None, settle_s=1.5, poll_s=0.25).start()
        time.sleep(1.0)
        c0, t0, r0 = time.process_time(), time.monotonic(), w.rounds
        time.sleep(10.0)
        c1, t1, r1 = time.process_time(), time.monotonic(), w.rounds
        w.stop()
        files = sum(len(w._sig(x)) for s in srcs for x in s.watches)
        print(json.dumps({{"cpu": (c1 - c0) / (t1 - t0), "rounds": r1 - r0, "sources": len(srcs), "entries": files}}))
        """
    )
    out = subprocess.run(
        [sys.executable, "-c", script], cwd=paths.repo_root(), capture_output=True, text=True, timeout=60, check=True
    )
    got = json.loads(out.stdout.strip().splitlines()[-1])
    print(f"\nidle watcher: {got['cpu'] * 100:.2f} % of a CPU, {got['rounds']} rounds over {got['sources']} sources "
          f"({got['entries']} entries)")  # fmt: skip
    assert got["rounds"] >= 30
    assert got["cpu"] < 0.01


def test_watch_rounds_find_a_change_in_a_real_thread(tmp_path: Path) -> None:
    f = tmp_path / "a.json"
    f.write_text("one", encoding="utf-8")
    got: list = []
    w = Watcher([Source("s", "S", [Watch(f, "file", "a")])], on_settled=lambda s, c: got.append(c), settle_s=0.2,
                poll_s=0.05).start()  # fmt: skip
    try:
        f.write_text("two!", encoding="utf-8")
        deadline = time.monotonic() + 5
        while not got and time.monotonic() < deadline:
            time.sleep(0.02)
        assert got == [{"a": [""]}]
    finally:
        w.stop()
    assert paths.repo_root().is_dir()


def test_a_folder_two_sources_watch_is_looked_at_once_per_round(tmp_path: Path, monkeypatch) -> None:
    """The line files are watched by the line files' importer and by the old hub's: one look per round serves both,
    and each still sees its own change."""
    import region.live.watch as WM

    lines = tmp_path / "lines"
    lines.mkdir()
    f = lines / "Line_3.json"
    f.write_text("{}", encoding="utf-8")
    looks: list[Path] = []
    real = WM.tree_sig
    monkeypatch.setattr(WM, "tree_sig", lambda p, *a, **k: (looks.append(p), real(p, *a, **k))[1])
    got: list = []
    clock = Clock()
    srcs = [Source(n, n, [Watch(lines, "tree", "lines")]) for n in ("a", "b")]
    w = Watcher(srcs, on_settled=lambda s, c: got.append((s.id, c)), settle_s=1.5, clock=clock)
    looks.clear()
    w.poll_once()
    assert looks == [lines]
    f.write_text('{"c": 1}', encoding="utf-8")
    for _ in range(8):
        clock.t += 0.25
        w.poll_once()
    assert sorted(got) == [("a", {"lines": ["Line_3.json"]}), ("b", {"lines": ["Line_3.json"]})]
    assert len(looks) == 9
