"""WP0a exit tests (section 10): the frozen core contracts, the CLI and the packaging around them."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from region.core import errors, events, features, fsio, ids, paths, protocols
from region.core.view import View, date_interval, date_uncertain, is_open, month_index

REPO = paths.repo_root()


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    return env


# ------------------------------------------------------------------------------------------------------------ view


def test_view_instant_and_token():
    present = View()
    assert (present.layer, present.year, present.month, present.timeline) == ("main", None, None, "canon")
    assert present.instant() is None
    assert present.token() == "main|-|canon"

    year = View(year=1931)
    assert year.instant() == 1931 * 12 + 11  # the end of its year
    assert year.token() == "main|1931|canon"

    month = View("try", 1931, 9, "real")
    assert month.instant() == month_index(1931, 9) == 1931 * 12 + 8  # the end of its month
    assert month.token() == "try|1931-09|real"
    for v in (present, year, month, View("legacy:old_hub"), View("import:profiles", 2026)):
        assert View.parse(v.token()) == v
        assert View.from_query(v.query()) == v
    assert {month: 1}[View("try", 1931, 9, "real")] == 1  # frozen and hashable

    for bad in (
        dict(month=9),  # a month needs a year
        dict(year=1931, month=13),
        dict(timeline="future"),
        dict(layer="Main"),
        dict(layer=""),
        dict(year="1931"),
        dict(year=10000),  # beyond what a partial ISO date (and so token()) can write
    ):
        with pytest.raises(errors.Invalid):
            View(**bad)

    # dates are month intervals; a year-only date is open all through its year, with an uncertain mark in a month view
    assert date_interval("1931") == (1931 * 12, 1931 * 12 + 11)
    assert date_interval("1931-09") == (1931 * 12 + 8, 1931 * 12 + 8)
    assert date_interval(1931) == date_interval("1931")
    assert date_interval(None) is None and date_interval("") is None
    with pytest.raises(errors.Invalid):
        date_interval("Sept 1931")
    opened = date_interval("1931")
    assert is_open(View(year=1931).instant(), opened, None)
    assert is_open(View(year=1931, month=1).instant(), opened, None)
    assert not is_open(View(year=1930).instant(), opened, None)
    assert date_uncertain(9, opened) and not date_uncertain(None, opened)
    assert not date_uncertain(9, date_interval("1931-09"))
    closed = date_interval("1960-06")
    assert is_open(View(year=1960, month=5).instant(), opened, closed)
    assert not is_open(View(year=1960, month=6).instant(), opened, closed)
    # undated built records count only at the present
    assert is_open(None, None, None) and not is_open(View(year=2026).instant(), None, None)
    assert not is_open(None, opened, closed)

    # only declared axes enter a cache key, never the layer
    assert month.key_axes(["year"]) == {"year": 1931}
    assert month.key_axes(["timeline", "month"]) == {"month": 9, "timeline": "real"}
    assert month.key_axes([]) == {}
    with pytest.raises(errors.Invalid):
        month.key_axes(["layer"])


# ------------------------------------------------------------------------------------------------------------- ids


def test_ids_stable_is_deterministic_sortable_ulid():
    from ulid import ULID

    a = ids.stable("profiles", "Line_6")
    assert a == ids.stable("profiles", "Line_6")
    # pinned: two machines and every future version must mint this same id for this key
    assert a == "01DXF6DT00G2RN476ZR8N14PM3"
    assert ids.is_ulid(a) and len(a) == 26
    assert str(ULID.from_str(a)) == a
    ns = ids.namespaces()["profiles"]
    assert ids.timestamp_ms(a) == ns.epoch_ms == ULID.from_str(a).milliseconds
    assert ids.namespace_of(a) == "profiles"
    assert ids.stable("profiles", "Line_8") != a
    assert ids.stable("registry", "Line_6") != a
    assert ids.namespace_of(ids.stable("registry", "x")) == "registry"
    assert ids.stable("profiles", "Caf\u00e9") == ids.stable("profiles", "Cafe\u0301")  # NFC
    assert ids.stable("profiles", "Line_8|Cincinnati State#2") == ids.stable("profiles", "Line_8|Cincinnati State#2")
    with pytest.raises(errors.Invalid):
        ids.stable("nowhere", "x")
    with pytest.raises(errors.Invalid):
        ids.stable("profiles", "")

    # stable ids of a namespace sort together, and before every authored id
    imported = sorted(ids.stable("profiles", f"k{i}") for i in range(50))
    assert all(ids.timestamp_ms(x) == ns.epoch_ms for x in imported)
    minted = [ids.new() for _ in range(2000)]
    assert minted == sorted(minted) and len(set(minted)) == len(minted)  # monotonic within the process
    assert all(ids.is_ulid(x) and str(ULID.from_str(x)) == x for x in minted[:50])
    assert max(imported) < min(minted)
    assert ids.namespace_of(minted[0]) is None
    assert ids.decode(ids.encode(12345)) == 12345
    assert not ids.is_ulid("01dxf6dt00g2rn476zr8n14pm3") and not ids.is_ulid("8ZZZZZZZZZZZZZZZZZZZZZZZZZ")

    # the namespaces file: distinct epochs, layers are layer slugs, the test namespace is marked
    loaded = ids.load_namespaces()
    assert {"profiles", "registry", "old_hub", "test"} <= set(loaded)
    assert len({n.epoch_ms for n in loaded.values()}) == len(loaded)
    assert loaded["test"].test and not loaded["profiles"].test
    assert loaded["profiles"].layer == "import:profiles"
    assert loaded["profiles"].ledger == REPO / "region" / "ids" / "profiles.tsv"


# ------------------------------------------------------------------------------------------------------------ fsio


def test_write_atomic_survives_open_reader(write_root, monkeypatch):
    target = write_root / "seed" / "profile" / "a.json"
    fsio.write_atomic(target, '{"v": 1}\n')
    reader = open(target, encoding="utf-8")
    assert reader.read(3) == '{"v'
    if os.name == "nt":
        # Windows refuses to replace a file another handle holds open: the write retries until the reader closes
        threading.Timer(0.3, reader.close).start()
        fsio.write_atomic(target, '{"v": 2, "longer": true}\n')
    else:
        fsio.write_atomic(target, '{"v": 2, "longer": true}\n')
        assert reader.read() == '": 1}\n'  # the open reader keeps the old file
        reader.close()
    assert fsio.read_text(target) == '{"v": 2, "longer": true}\n'
    assert sorted(p.name for p in target.parent.iterdir()) == ["a.json"]  # no temp file left

    # a Windows sharing violation (WinError 32) or access denied (5) is retried until the other handle closes
    real = os.replace
    calls = []

    def flaky(src, dst):
        calls.append(dst)
        if len(calls) < 3:
            e = PermissionError(13, "The process cannot access the file")
            e.winerror = 32 if len(calls) == 1 else 5
            raise e
        return real(src, dst)

    monkeypatch.setattr(fsio.os, "replace", flaky)
    fsio.write_atomic(target, b"three\n")
    assert len(calls) == 3 and target.read_bytes() == b"three\n"

    # any other permission error is raised at once, and the target and folder are left as they were
    def denied(src, dst):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(fsio.os, "replace", denied)
    with pytest.raises(PermissionError):
        fsio.write_atomic(target, b"four\n")
    assert target.read_bytes() == b"three\n"
    assert sorted(p.name for p in target.parent.iterdir()) == ["a.json"]
    monkeypatch.setattr(fsio.os, "replace", real)

    # text is written as UTF-8 with LF line endings on every platform; reads drop a BOM and read CRLF as LF
    fsio.write_text(target, "caf\u00e9\r\nline\n")
    assert target.read_bytes() == "caf\u00e9\nline\n".encode()
    crlf = write_root / "crlf.json"
    crlf.write_bytes(b'\xef\xbb\xbf{"a":\r\n 1}\r\n')
    assert fsio.read_text(crlf) == '{"a":\n 1}\n' and fsio.read_json(crlf) == {"a": 1}
    fsio.write_json(write_root / "j.json", {"b": [1, None], "a": "\u00e9"})
    assert (write_root / "j.json").read_bytes() == '{\n "a": "\u00e9",\n "b": [\n  1,\n  null\n ]\n}\n'.encode()
    assert fsio.sha256_file(write_root / "j.json") == fsio.sha256_hex((write_root / "j.json").read_bytes())


def test_write_guard_refuses_outside_roots(tmp_path, hub_var):
    outside = tmp_path / "elsewhere" / "x.json"
    with pytest.raises(fsio.WriteRefused):
        fsio.write_atomic(outside, b"no")
    assert not outside.exists()
    with fsio.allow_writes(tmp_path / "elsewhere"):
        fsio.write_atomic(outside, b"yes")
    assert outside.read_bytes() == b"yes"
    with pytest.raises(fsio.WriteRefused):
        fsio.write_atomic(outside, b"again")

    # the default roots: var (here CRHUB_VAR), app/dist, region/seed, region/ids
    roots = fsio.default_write_roots()
    assert roots == (hub_var, REPO / "app" / "dist", REPO / "region" / "seed", REPO / "region" / "ids")
    fsio.write_atomic(hub_var / "logs" / "ok.txt", "ok\n")
    assert fsio.check_write(REPO / "region" / "seed" / "main" / "x.json") == (REPO / "region/seed/main/x.json")
    for bad in (
        REPO / "README.md",
        REPO / "hub" / "seed" / "x.json",
        REPO / "region" / "core" / "view.py",
        REPO / "region" / "seed" / ".." / "rules.py",
        hub_var / ".." / "escape.txt",
    ):
        with pytest.raises(fsio.WriteRefused):
            fsio.check_write(bad)

    # a symlink inside a root that leads out of it is refused
    link = hub_var / "link"
    try:
        link.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    except (OSError, NotImplementedError):
        return  # creating symlinks needs a privilege on Windows; the checks above still ran
    with pytest.raises(fsio.WriteRefused):
        fsio.write_atomic(link / "x.json", b"no")


def test_reserved_windows_names_rejected(write_root, monkeypatch):
    bad = [
        "CON", "con", "Con.txt", "NUL", "nul.json", "PRN.x", "AUX", "COM1", "com9.log", "LPT1", "LPT9.tar.gz",
        "COM\u00b9", "CONIN$", "conout$.txt", "CON .txt", "a.", "a ", "a:b", "ads.json:stream", "a<b", "a>b",
        'a"b', "a|b", "a?b", "a*b", "a\\b", "x\x01", "", ".", "..",
    ]  # fmt: skip
    for name in bad:
        with pytest.raises(paths.UnsafePath):
            paths.check_name(name)
        if name and "\\" not in name:
            with pytest.raises(paths.UnsafePath):
                paths.check_relpath(f"tiles/{name}")
        # on Windows a backslash is a separator, so "a\\b" is the path a/b there, not one name
        if name not in ("", ".", "..") and not (os.name == "nt" and "\\" in name):
            with pytest.raises(fsio.WriteRefused):
                fsio.write_atomic(write_root / "d" / name, b"x")
    assert not (write_root / "d").exists() or not any((write_root / "d").iterdir())

    # Windows path normalisation drops a trailing dot or space ("a." resolves to "a"); the guard checks the names as
    # given too, so the write is still refused. Emulated here so every platform runs the check.
    def windows_like(p, *args, **kwargs):
        return os.path.join(*[part.rstrip(". ") or part for part in Path(os.path.abspath(p)).parts])

    if os.name != "nt":
        with monkeypatch.context() as m:
            m.setattr(fsio.os.path, "realpath", windows_like)
            for name in ("a.", "a ", "notes...", "dir./x.json"):
                with pytest.raises(fsio.WriteRefused):
                    fsio.write_atomic(write_root / "w" / name, b"x")
            assert fsio.check_write(write_root / "w" / "ok.json") == write_root / "w" / "ok.json"
        assert not (write_root / "w").exists()

    good = ["CONSOLE.txt", "con1.txt", "COM10", "nul_report.json", "auxiliary", "LPT", "a.b.c", "index.json"]
    for name in good:
        assert paths.check_name(name) == name
        fsio.write_atomic(write_root / "ok" / name, b"x")

    for rel in (
        "../x", "a/../b", "a/./b", "/abs", "//server/share/x", "C:/x", "c:x", "a\\b", "a%5cb", "a%5Cb",
        "%2e%2e/x", "a//b", "a/CON/b",
    ):  # fmt: skip
        with pytest.raises(paths.UnsafePath):
            paths.check_relpath(rel)
    assert paths.check_relpath("tiles_22/index.json").as_posix() == "tiles_22/index.json"
    assert paths.check_relpath("").as_posix() == "."
    assert paths.check_relpath("lines/").as_posix() == "lines"
    assert isinstance(paths.UnsafePath("x"), errors.NotFound)  # served as 404, never with the reason


# ----------------------------------------------------------------------------------------------------------- paths


def _fake_repo(root: Path) -> Path:
    (root / "configs").mkdir(parents=True)
    (root / "lane_b" / "present" / "sub").mkdir(parents=True)
    (root / "lane_b" / "present" / "sub" / "file.json").write_text("{}", encoding="utf-8")
    (root / "moved").mkdir()
    spec = {
        "tiers": [
            {"name": "present", "root": "lane_b/present", "manifest": None, "index": "sub/file.json",
             "handshake": None, "required": True, "mount": True},
            {"name": "missing", "root": "lane_b/not_here", "manifest": "MANIFEST.csv", "index": None,
             "handshake": {"file": "STATUS.json", "done": "done", "detail": "stage"}, "required": False,
             "mount": False},
            {"name": "local_only", "root": "lane_b/nowhere", "manifest": None, "index": None,
             "handshake": None, "required": False, "mount": False},
        ]
    }  # fmt: skip
    (root / "configs" / "hub.json").write_text(json.dumps({"port": 9999, "var": "state"}), encoding="utf-8")
    (root / "configs" / "hub_paths.json").write_text(json.dumps(spec), encoding="utf-8")
    local = {"tiers": {"local_only": {"root": str(root / "moved")}}, "port": 8800}
    (root / "configs" / "local.json").write_text(json.dumps(local), encoding="utf-8")
    return root


def test_device_paths_are_refused_never_a_value_error(write_root, tmp_path, monkeypatch):
    """On Windows ``relpath`` calls ``abspath``, which turns ``C:\\x\\d\\NUL`` into the device path ``\\\\.\\NUL``,
    and then raises ``ValueError`` ("path is on mount '\\\\\\\\.\\\\NUL', start on mount 'C:'"); ``commonpath`` is
    lexical and lets it through. Emulated here on every platform: the path helpers must answer ``WriteRefused``,
    ``UnsafePath`` or a URI, and never let the ValueError out."""

    def device(p):
        return Path(os.fspath(p)).name.split(".", 1)[0].upper() in paths.RESERVED_NAMES

    real_relpath = os.path.relpath

    def relpath(p, start=os.curdir):
        if device(p) or device(start):
            raise ValueError(f"path is on mount '\\\\\\\\.\\\\NUL', start on mount {os.fspath(start)!r}")
        return real_relpath(p, start)

    monkeypatch.setattr(os.path, "relpath", relpath)
    for name in ("NUL", "con", "COM1.log", "LPT9.tar.gz"):
        with pytest.raises(fsio.WriteRefused):
            fsio.write_atomic(write_root / "d" / name, b"x")
        with pytest.raises(fsio.WriteRefused):
            fsio.check_write(write_root / name)
    assert not (write_root / "d").exists()
    assert fsio.check_write(write_root / "d" / "ok.json").name == "ok.json"  # a safe name is still taken

    # the lexical containment that replaced relpath: inside, the root itself, outside, another drive or device
    assert paths.names_below(write_root, write_root / "a" / "b.json") == ("a", "b.json")
    assert paths.names_below(write_root, write_root) == ()
    assert paths.names_below(write_root / "a", write_root / "ab") is None
    assert paths.names_below(write_root, write_root.parent) is None
    assert paths.names_below(write_root, "//./NUL") is None
    assert paths.names_below(".", "../x") is None and paths.names_below("a", "a/../../x") is None  # relative climbs

    repo = _fake_repo(tmp_path / "repo")
    cfg = paths.load_config(repo)
    assert paths.to_uri(repo / "configs" / "NUL", cfg) == "repo://configs/NUL"
    with pytest.raises(paths.UnsafePath):
        paths.resolve("repo://configs/NUL", cfg)


def test_tier_uri_resolves_and_missing_tier_reports(tmp_path, monkeypatch):
    monkeypatch.delenv(paths.VAR_ENV, raising=False)
    repo = _fake_repo(tmp_path / "repo")
    cfg = paths.load_config(repo)
    assert cfg["port"] == 8800  # local.json wins
    assert paths.var_root(cfg) == repo / "state"  # relative var is relative to the repo
    monkeypatch.setenv(paths.VAR_ENV, str(tmp_path / "v"))
    assert paths.describe_var(cfg) == (tmp_path / "v", "env CRHUB_VAR")
    monkeypatch.delenv(paths.VAR_ENV)

    # a present tier resolves, contained in its root
    p = paths.resolve("tier://present/sub/file.json", cfg)
    assert p == (repo / "lane_b" / "present" / "sub" / "file.json").resolve() and p.is_file()
    assert paths.resolve("tier://present/", cfg) == (repo / "lane_b" / "present").resolve()
    assert paths.available("present", cfg) is True
    assert paths.to_uri(p, cfg) == "tier://present/sub/file.json"
    t = paths.tiers(cfg)["present"]
    assert (t.index, t.required, t.mount, t.handshake) == ("sub/file.json", True, True, None)
    assert paths.tiers(cfg)["missing"].handshake == paths.Handshake("STATUS.json", "done", "stage")

    # a missing tier reports a plain reason, as a NotFound, never a crash
    with pytest.raises(paths.TierMissing) as missing:
        paths.resolve("tier://missing/STATUS.json", cfg)
    assert missing.value.tier == "missing" and "not on this machine" in missing.value.reason
    assert isinstance(missing.value, errors.NotFound) and missing.value.status == 404
    assert missing.value.to_problem("r1")["code"] == "tier_missing"
    reason = paths.available("missing", cfg)
    assert isinstance(reason, str) and "lane_b" in reason and "configs/local.json" in reason
    with pytest.raises(paths.TierMissing):
        paths.resolve("tier://unknown/x", cfg)
    assert "no data tier named" in paths.available("unknown", cfg)

    # configs/local.json moves a root on one machine
    assert paths.available("local_only", cfg) is True
    assert paths.resolve("tier://local_only/a.txt", cfg) == (repo / "moved" / "a.txt").resolve()

    # unsafe paths and other schemes
    for uri in ("tier://present/../x", "tier://present/sub/CON", "tier://present/a\\b", "repo://../x"):
        with pytest.raises(paths.UnsafePath):
            paths.resolve(uri, cfg)
    with pytest.raises(errors.Invalid):
        paths.resolve("file:///etc/passwd", cfg)
    assert paths.resolve("repo://configs/hub.json", cfg) == (repo / "configs" / "hub.json").resolve()
    assert paths.resolve("var://logs/x.jsonl", cfg) == (repo / "state" / "logs" / "x.jsonl").resolve()
    assert paths.to_uri(repo / "configs" / "hub.json", cfg) == "repo://configs/hub.json"
    with pytest.raises(errors.Invalid):
        paths.to_uri(tmp_path / "outside.txt", cfg)

    # the committed tiers: every one declares name, root, manifest or index, handshake, required, mount
    with open(REPO / "configs" / "hub_paths.json", encoding="utf-8") as f:
        committed = json.load(f)["tiers"]
    names = [t["name"] for t in committed]
    assert len(names) == len(set(names))
    assert {"ground_1912_real", "ground_2026", "sanborn_tiles_22", "deck", "old_hub_seed", "profile_lines"} <= set(
        names
    )
    for t in committed:
        assert {"name", "root", "manifest", "index", "handshake", "required", "mount"} <= set(t), t["name"]
        assert t["manifest"] or t["index"], t["name"]
        assert not Path(t["root"]).is_absolute(), t["name"]
    real = {t["name"]: t for t in committed}
    assert real["ground_1912_real"]["root"] == "ground/1912"
    assert real["ground_1912_real"]["handshake"]["file"] == "STATUS.json"
    here = paths.load_config(REPO)
    assert paths.resolve("tier://profile_lines/lines/index.json", here).is_file()
    assert paths.resolve("tier://old_hub_seed/alignments", here).is_dir()


# -------------------------------------------------------------------------------------------------------- features

_KIND = """\
kind: a_thing
version: 2
title: A thing
geometry: LineString
columns: {name: /name, c0: /c0}
refs:
  - {path: /stops/*/platform, kind: platform, on_delete: restrict}
merge: {unit: atomic, rebase: proposal, guard: [/c0]}
legacy: [old_thing]
seeded: true
schema:
  type: object
  additionalProperties: false
  properties:
    name: {type: string}
    c0: {type: number, x-unit: m}
    level_m: {type: [number, "null"], x-unit: m}
    system: {type: string, x-vocab: systems}
    stops: {type: array, items: {type: object, properties: {platform: {type: string}}}}
    attrs: {type: object}
"""


def _feature_tree(root: Path) -> Path:
    alpha = root / "alpha"
    for sub in ("kinds", "upgrade"):
        (alpha / sub).mkdir(parents=True)
    (alpha / "kinds" / "a_thing.yaml").write_text(_KIND, encoding="utf-8")
    (alpha / "kinds" / "_draft.yaml").write_text("ignored", encoding="utf-8")
    files = {
        "upgrade/a_thing.py": "def up_1(data):\n    return {**data, 'v2': True}\n",
        "helpers.py": "NAME = 'alpha.noop'\n",
        "jobs.py": "from .helpers import NAME\n\nclass Noop:\n    name = NAME\n\nJOB_TYPES = [Noop()]\n",
        "importers.py": "class Imp:\n    name = 'alpha_import'\n\nIMPORTERS = [Imp()]\n",
        "router.py": "router = 'a router'\n",
        "validators.py": "VALIDATORS = {'a_thing': lambda rec, ctx: []}\n",
        "sources.py": "SOURCES = {'lines': 'tier://profile_lines/lines/index.json'}\n",
    }
    for rel, text in files.items():
        (alpha / rel).write_text(text, encoding="utf-8")
    (root / "beta").mkdir()
    for ignored in ("_private", ".hidden", "__pycache__"):
        (root / ignored).mkdir()
    (root / "README.md").write_text("not a feature", encoding="utf-8")
    return root


def test_features_discover_folders(tmp_path):
    root = _feature_tree(tmp_path / "ext")
    found = features.discover(root)
    assert [f.name for f in found] == ["alpha", "beta"]
    alpha, beta = found
    assert alpha.kinds == (root / "alpha" / "kinds" / "a_thing.yaml",)
    assert alpha.upgraders == (("a_thing", root / "alpha" / "upgrade" / "a_thing.py"),)
    assert alpha.modules == ("importers", "jobs", "router", "validators", "sources")
    assert [j.name for j in alpha.job_types()] == ["alpha.noop"]  # relative imports work
    assert [i.name for i in alpha.importers()] == ["alpha_import"]
    assert alpha.router() == "a router"
    assert list(alpha.validators()) == ["a_thing"]
    assert alpha.sources() == {"lines": "tier://profile_lines/lines/index.json"}
    assert alpha.upgrader("a_thing").up_1({"a": 1}) == {"a": 1, "v2": True}
    assert alpha.upgrader("other") is None
    assert alpha.load("helpers").NAME == "alpha.noop"
    assert (beta.kinds, beta.upgraders, beta.modules) == ((), (), ())
    empty = (beta.importers(), beta.job_types(), beta.router(), beta.validators(), beta.sources())
    assert empty == ([], [], None, {}, {})
    assert features.discover(root) == found  # discovery is repeatable and imports nothing new

    # kind files: core kinds first, then each feature's
    core = tmp_path / "kinds"
    core.mkdir()
    (core / "note.yaml").write_text(_KIND.replace("a_thing", "note"), encoding="utf-8")
    (core / "_vocab.yaml").write_text("{}", encoding="utf-8")
    assert features.kind_files(root, core) == [core / "note.yaml", root / "alpha" / "kinds" / "a_thing.yaml"]
    assert features.check_kind_file(root / "alpha" / "kinds" / "a_thing.yaml") == []

    # a feature folder must be a lowercase identifier; a missing root has no features
    (root / "Bad-Name").mkdir()
    with pytest.raises(errors.Invalid):
        features.discover(root)
    assert features.discover(tmp_path / "absent") == []
    features.discover()  # the repo's region/ext, absent or not, never raises


def test_kind_meta_schema_checks_units_and_vocab(tmp_path):
    import yaml

    good = yaml.safe_load(_KIND)
    assert features.check_kind(good) == []
    assert features.check_kind(good, name="other") == ["/kind: 'a_thing' differs from the file name 'other'"]
    no_unit = yaml.safe_load(_KIND.replace("c0: {type: number, x-unit: m}", "c0: {type: number}"))
    assert any("x-unit" in p for p in features.check_kind(no_unit))
    nested = yaml.safe_load(_KIND.replace("platform: {type: string}", "platform: {type: integer}"))
    assert any("/stops/items/properties/platform" in p for p in features.check_kind(nested))
    bad_unit = yaml.safe_load(_KIND.replace("x-unit: m}", "x-unit: ft}"))
    assert any("x-unit 'ft'" in p for p in features.check_kind(bad_unit))
    bad_vocab = yaml.safe_load(_KIND.replace("x-vocab: systems", "x-vocab: planets"))
    assert any("x-vocab 'planets'" in p for p in features.check_kind(bad_vocab))
    for broken in (
        {**good, "geometry": "Curve"},
        {**good, "columns": {"colour": "/c"}},
        {**good, "refs": [{"path": "/a", "kind": "x", "on_delete": "ignore"}]},
        {**good, "merge": {"unit": "deep"}},
        {**good, "schema": {"type": "thing"}},
        {**good, "extra": 1},
        {k: v for k, v in good.items() if k != "schema"},
    ):
        assert features.check_kind(broken), broken
    (tmp_path / "x.yaml").write_text("kind: [unclosed", encoding="utf-8")
    assert features.check_kind_file(tmp_path / "x.yaml")[0].startswith("not valid YAML")

    # the meta-schema's closed lists and the vocabulary agree
    meta = features.load_meta_schema()["properties"]
    vocab = features.load_vocab()
    assert meta["geometry"]["enum"] == vocab["geometry"]
    assert meta["refs"]["items"]["properties"]["on_delete"]["enum"] == vocab["on_delete"]
    assert meta["merge"]["properties"]["unit"]["enum"] == vocab["merge_units"]
    assert meta["merge"]["properties"]["rebase"]["enum"] == vocab["rebase_policies"]
    assert meta["columns"]["propertyNames"]["enum"] == vocab["promoted_columns"]
    assert "ft" not in vocab["units"] and "m" in vocab["units"]

    # every committed kind file is valid
    for path in features.kind_files():
        assert features.check_kind_file(path) == [], path


# ------------------------------------------------------------------------------------------------------------- cli


def test_cli_lists_every_command():
    from region import cli

    on_disk = sorted(p.stem for p in (REPO / "region" / "cli").glob("*.py") if not p.name.startswith("_"))
    assert on_disk and cli.commands() == on_disk
    _, broken = cli.build_parser()
    assert broken == {}, "commands that fail to load: " + ", ".join(broken)

    run = subprocess.run(
        [sys.executable, "-m", "region", "--help"], cwd=REPO, env=_env(), capture_output=True, text=True, timeout=120
    )
    assert run.returncode == 0, run.stderr
    for name in on_disk:
        assert name in run.stdout, f"{name} is missing from crhub --help"
        sub = subprocess.run(
            [sys.executable, "-m", "region", name, "--help"],
            cwd=REPO,
            env=_env(),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert sub.returncode == 0, f"crhub {name} --help: {sub.stderr}"

    info = subprocess.run(
        [sys.executable, "-m", "region", "info", "--json"], cwd=REPO, env=_env(), capture_output=True, text=True
    )
    assert info.returncode == 0, info.stderr
    facts = json.loads(info.stdout)
    assert facts["commands"] == on_disk and facts["repo"] == str(REPO)
    assert set(facts["tiers"]) >= {"ground_1912_real", "profile_lines"}


def test_runbook_aliases_run_the_model_actions(hub_var, capsys):
    """``crhub export``, ``crhub backup`` and ``crhub restore`` (section 9's runbook) are ``crhub model``'s actions
    under shorter names: same arguments, same work; restore refuses while the hub lock is held."""
    from region.cli import build_parser
    from region.cli import main as cli_main
    from region.core import lock
    from region.model import open_store

    parser, broken = build_parser()
    assert broken == {}
    sub = next(a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction")
    model_sub = next(a for a in sub.choices["model"]._actions if a.__class__.__name__ == "_SubParsersAction")
    for name in ("export", "backup", "restore"):
        alias = sorted(a.dest for a in sub.choices[name]._actions)
        assert alias == sorted(a.dest for a in model_sub.choices[name]._actions), name

    db = hub_var / "region.db"
    with open_store(db) as store:
        rec = store.put(
            {"kind": "note", "id": None, "data": {"text": "kept"}, "geom": None}, View(), if_match=None, by="ben"
        )
    out = hub_var / "seed"
    assert cli_main(["export", "--db", str(db), "--out", str(out)]) == 0
    assert (out / "main" / "note" / f"{rec['id']}.json").is_file()

    capsys.readouterr()
    assert cli_main(["backup", "--db", str(db), "--reason", "manual"]) == 0
    made = Path(capsys.readouterr().out.strip())
    assert made.is_file() and made.parent == hub_var / "backups" and made.name.endswith("-manual.db")

    with open_store(db) as store:
        store.delete("note", rec["id"], View(), if_match=f'"main:{rec["version"]}"', by="ben")
    with lock.acquire(hub_var, 8766):
        assert cli_main(["restore", str(made), "--db", str(db)]) == 1
        assert "crhub serve (pid" in capsys.readouterr().err
    assert cli_main(["restore", str(made), "--db", str(db)]) == 0
    with open_store(db, readonly=True) as store:
        assert store.get("note", rec["id"], View())["data"]["text"] == "kept"
    assert any(f.name.endswith("-pre-restore.db") for f in (hub_var / "backups").iterdir())
    assert lock.reader(hub_var) is None


# ------------------------------------------------------------------------------------- the rest of the core contract


def test_canonical_json_agrees_with_engine():
    with open(REPO / "engine" / "test" / "contract.jcs.json", encoding="utf-8") as f:
        vectors = json.load(f)
    assert vectors
    for value, want in vectors:
        assert fsio.canonical_json(value).decode("utf-8") == want
    assert fsio.canonical_json({"b": 1.0, "a": [True, None]}) == b'{"a":[true,null],"b":1}'
    assert fsio.content_hash({"a": 1}) == fsio.content_hash({"a": 1.0})
    for bad in (float("nan"), float("inf"), 2**60, {1: "x"}, object()):
        with pytest.raises((ValueError, TypeError)):
            fsio.canonical_json(bad)


def test_errors_carry_status_and_problem_body():
    cases = [
        (errors.NotFound("no such kind"), 404, "not_found"),
        (errors.PreconditionRequired(), 428, "precondition_required"),
        (errors.PreconditionFailed("stale", current={"id": "x"}, by="ben", diff=[]), 412, "precondition_failed"),
        (errors.Conflict("legacy owns profile", reason="authority", conflicts=[{"kind": "profile"}]), 409,
         "conflict_authority"),
        (errors.Invalid("bad", errors=[{"path": "/data/x", "message": "m"}]), 422, "invalid"),
        (errors.EngineUnavailable("no node", reason="no_node"), 503, "engine_unavailable"),
        (errors.EngineError("boom", engine_code="internal", stack="s"), 502, "engine_error"),
    ]  # fmt: skip
    for err, status, code in cases:
        assert isinstance(err, errors.HubError)
        body = err.to_problem("req-1", "/api/v1/k/profile/x")
        assert (err.status, body["status"], body["code"], body["request_id"]) == (status, status, code, "req-1")
        assert {"type", "title", "detail", "instance"} <= set(body)
    assert cases[2][0].to_problem()["current"] == {"id": "x"} and cases[2][0].to_problem()["by"] == "ben"
    assert cases[3][0].to_problem()["conflicts"] == [{"kind": "profile"}]
    assert cases[4][0].to_problem()["errors"][0]["path"] == "/data/x"
    assert "stack" not in cases[6][0].to_problem()
    assert errors.Conflict("x", reason="namespace", code="conflict_layer").to_problem()["code"] == "conflict_layer"


def test_engine_errors_carry_stderr_tail_and_issues_outside_the_problem():
    issues = [{"code": "invalid_type", "path": ["c0_m"], "message": "Expected number"}]
    e = errors.EngineError("bad input", engine_code="invalid_input", stack="s", stderr_tail="tail\n", issues=issues)
    assert (e.stderr_tail, e.issues, e.engine_code) == ("tail\n", issues, "invalid_input")
    assert errors.EngineError("x").stderr_tail == "" and errors.EngineError("x").issues is None
    u = errors.EngineUnavailable("died", reason="crashed", stderr_tail="last words")
    assert u.stderr_tail == "last words" and errors.EngineUnavailable("x").stderr_tail == ""
    for err in (e, u):
        body = err.to_problem()
        assert not {"stderr_tail", "issues", "stack"} & set(body)


def test_protocol_shapes():
    assert protocols.etag("main", 8) == '"main:8"'
    assert protocols.parse_etag('"import:profiles:12"') == ("import:profiles", 12)
    assert protocols.parse_etag('W/"main:3"') == ("main", 3)
    for bad in ('"main"', '"main:x"', '":3"'):
        with pytest.raises(errors.Invalid):
            protocols.parse_etag(bad)
    assert protocols.ref_rec("01K") == "rec:01K"
    assert protocols.parse_ref(protocols.ref_job("profiles.solve_section", "01K")) == (
        "job",
        "profiles.solve_section/01K",
    )
    assert protocols.parse_ref(protocols.ref_file("tier://deck/basin.json")) == ("file", "tier://deck/basin.json")
    with pytest.raises(errors.Invalid):
        protocols.parse_ref("blob:x")
    op = protocols.Op("patch", "profile", "01K", '"main:3"', patch=[{"op": "replace", "path": "/data/x", "value": 1}])
    assert op.body is None and op.patch[0]["op"] == "replace"
    out = protocols.Output()
    assert (out.meta, out.arrays, out.blobs, out.issues) == ({}, {}, {}, [])
    assert protocols.ImportRun("profile_lines", "1", "import:profiles", "profiles").by == "import:profile_lines"
    assert protocols.WriteResult(None).records == []

    class FakeEngine:
        def hello(self):
            return {}

        def call(self, method, params, *, timeout_s=30.0):
            return {}

        def close(self):
            pass

    assert isinstance(FakeEngine(), protocols.EngineClient)
    assert not isinstance(FakeEngine(), protocols.Store)
    assert {"get", "list", "write", "put", "patch", "delete", "revert", "history", "restore", "hash_of",
            "events_since", "legacy", "apply_import"} <= set(dir(protocols.Store))  # fmt: skip


def test_event_payloads_match_section_5():
    record = {"seq": 18342, "op": "patch", "kind": "profile", "id": "01K", "layer": "main", "version": 8, "hash": "h",
              "by": "ben", "client": "tab-3f2c", "changeset": "01K", "fields": ["data.pvi"],
              "bbox": [713100, 4330200, 716900, 4341800]}  # fmt: skip
    assert events.required_keys("record") == set(record)
    assert events.required_keys("changeset") == {"seq", "id", "layer", "by", "count", "kinds", "bbox", "summary"}
    assert events.required_keys("job") == {"id", "type", "scope", "state", "progress", "msg"}
    assert events.required_keys("result") == {"key", "type", "scope", "view", "status", "changed"}
    assert events.required_keys("tier") == {"tier", "status", "detail"}
    assert events.required_keys("engine") == {"engine_build", "error"}
    assert events.required_keys("resync") == {"reason", "seq"}
    assert events.required_keys("hello") == {"epoch", "seq", "engine_build"}
    assert events.DURABLE | events.EPHEMERAL | events.CONTROL == set(events.EVENT_PAYLOADS)
    assert events.BULK_THRESHOLD == 200


def test_log_writes_json_lines_with_request_id(hub_var):
    import datetime as dt
    import logging

    from region.core import log

    handler = log.setup(level="INFO", stderr=False)
    try:
        lg = log.get_logger("api")
        with log.log_context(request_id="req-9", job_id="job-1"):
            lg.info("record written", extra={"kind": "profile"})
        lg.warning("outside")
        try:
            raise ValueError("boom")
        except ValueError:
            lg.exception("failed")
        log.client_log({"level": "error", "msg": "pane crashed", "pane": "map"})
    finally:
        logging.getLogger("region").removeHandler(handler)
        handler.close()
    today = log.log_file(hub_var / "logs", dt.date.today())
    lines = [json.loads(x) for x in today.read_text(encoding="utf-8").splitlines()]
    assert [x["msg"] for x in lines] == ["record written", "outside", "failed", "pane crashed"]
    assert lines[0]["request_id"] == "req-9" and lines[0]["job_id"] == "job-1" and lines[0]["kind"] == "profile"
    assert lines[1]["request_id"] is None and lines[1]["level"] == "WARNING"
    assert "ValueError: boom" in lines[2]["exc"]
    assert lines[3]["logger"] == "region.client" and lines[3]["client_pane"] == "map"
    assert b"\r\n" not in today.read_bytes()

    old = log.log_file(hub_var / "logs", dt.date.today() - dt.timedelta(days=31))
    keep = log.log_file(hub_var / "logs", dt.date.today() - dt.timedelta(days=29))
    old.write_text("", encoding="utf-8")
    keep.write_text("", encoding="utf-8")
    assert log.prune(hub_var / "logs") == [old]
    assert keep.exists() and today.exists()


def test_engine_schemas_validate_in_python():
    from jsonschema import Draft202012Validator

    schema_dir = REPO / "engine" / "schema" / "v0"
    with open(schema_dir / "contracts.json", encoding="utf-8") as f:
        contracts = json.load(f)
    assert contracts["contracts"] == {"section_input": 0, "vertical_rail": 0}
    with open(schema_dir / "section_input.json", encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    good = {
        "contract": "section_input/0", "section_id": ids.stable("test", "Line_6"), "length_m": 29539.6,
        "chainage_basis": "grid:26916", "scale": 0.99983, "step_m": 2.0,
        "params": {"platform_m": 120.0, "vc_radius_m": 2000.0, "vc_min_len_m": 20.0},
        "stations": [{"platform_id": ids.stable("test", "p1"), "order": 0, "c_m": 60.0, "level_m": None,
                      "grade_permille": 0.0}],
        "pvi": [{"c_m": 1000.0, "z_m": 150.25}],
    }  # fmt: skip
    v = Draft202012Validator(schema)
    assert list(v.iter_errors(good)) == []
    assert list(v.iter_errors({**good, "chainage_basis": "ground"}))
    assert list(v.iter_errors({**good, "extra": True}))
    for name in contracts["schemas"]:
        with open(schema_dir / name, encoding="utf-8") as f:
            Draft202012Validator.check_schema(json.load(f))


def test_known_failures_are_strict_xfail(request):
    from tests.conftest import load_known_failures

    known = load_known_failures()
    assert "tests/test_core.py::test_rer_routes_follow_deck" in known
    assert all("::" in node and node.startswith("tests/") for node in known)


def test_launchers():
    cmd = (REPO / "crhub.cmd").read_bytes()
    assert b"\r\n" in cmd and b"\n" not in cmd.replace(b"\r\n", b"")  # CRLF throughout
    text = cmd.decode("ascii")
    assert "PYTHONUTF8=1" in text and "-m region %*" in text and "uv" in text and ".venv" in text
    sh = (REPO / "crhub").read_bytes()
    assert b"\r" not in sh and sh.startswith(b"#!/bin/sh")
    assert b"PYTHONUTF8=1" in sh and b'-m region "$@"' in sh
    if os.name == "posix":
        assert os.access(REPO / "crhub", os.X_OK)
    assert (REPO / ".python-version").read_text(encoding="utf-8").strip() == "3.12"
