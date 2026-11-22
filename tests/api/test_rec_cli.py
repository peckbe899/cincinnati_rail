"""``crhub rec`` (decision 9.28): it writes through the serving hub while one holds the lock, and opens the database
itself (taking the lock for writes) otherwise."""

from __future__ import annotations

import json

import httpx
import pytest

from region.cli import main
from region.core import lock
from tests.api.conftest import free_port


def _run(capsys, *argv: str) -> dict:
    code = main(["rec", *argv])
    out = capsys.readouterr()
    assert code == 0, out.err
    return json.loads(out.out)


@pytest.fixture
def db(hub_var):
    from region.model import open_store

    path = hub_var / "region.db"
    open_store(path).close()
    return path


def test_rec_direct_when_no_hub_serves(db, hub_var, tmp_path, capsys):
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"data": {"text": "from the cli"}, "geom": None}), encoding="utf-8")
    rec = _run(capsys, "create", "note", str(body))
    assert rec["version"] == 1 and rec["by"] == "ben"
    assert lock.reader(hub_var) is None  # the write held the lock only while it ran
    patch = tmp_path / "patch.json"
    patch.write_text(json.dumps([{"op": "replace", "path": "/data/text", "value": "patched"}]), encoding="utf-8")
    out = _run(capsys, "--by", "claude", "patch", "note", rec["id"], str(patch), "--latest")
    assert out["version"] == 2 and out["by"] == "claude" and out["data"]["text"] == "patched"
    assert _run(capsys, "get", "note", rec["id"])["data"]["text"] == "patched"
    assert [r["id"] for r in _run(capsys, "list", "note")["items"]] == [rec["id"]]
    assert [h["version"] for h in _run(capsys, "history", "note", rec["id"])["items"]] == [2, 1]
    stale = main(["rec", "delete", "note", rec["id"], "--if-match", '"main:1"'])
    assert stale == 1 and "stale" in capsys.readouterr().err.lower()


def test_rec_goes_through_the_serving_hub(db, hub_var, tmp_path, capsys):
    from region.api.serve import Serve

    srv = Serve(port=free_port(), engine=False, seeds=False, out=lambda _line: None)
    url = srv.start()
    try:
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"data": {"text": "through http"}, "geom": None}), encoding="utf-8")
        rec = _run(capsys, "create", "note", str(body), "--layer", "main")
        assert rec["data"] == {"text": "through http"}
        cs = httpx.get(url + "/api/v1/changesets").json()["items"][0]
        assert cs["client"] == "crhub-rec"  # it came over HTTP, as the server's own write
        gone = _run(capsys, "delete", "note", rec["id"], "--latest")
        assert gone["deleted"] is True
        missing = main(["rec", "get", "note", rec["id"]])
        assert missing == 1 and "deleted" in capsys.readouterr().err
    finally:
        srv.stop()


def test_rec_body_files_in_windows_encodings(write_root):
    """windows-8: a body file with a UTF-8 BOM (PowerShell's Out-File -Encoding utf8) or in UTF-16 (its ">") crashed
    with a traceback; it is read, and a file in another encoding or not JSON is an Invalid naming it."""
    import json as _json

    import pytest as _pytest

    from region.cli.rec import _read_json
    from region.core.errors import Invalid

    body = {"data": {"text": "Gare de l'Est, café"}, "geom": None}
    text = _json.dumps(body, ensure_ascii=False)
    for name, raw in (
        ("bom.json", b"\xef\xbb\xbf" + text.encode("utf-8")),
        ("utf16.json", text.encode("utf-16")),
        ("plain.json", text.encode("utf-8")),
    ):
        f = write_root / name
        f.write_bytes(raw)
        assert _read_json(str(f)) == body, name
    bad = write_root / "cp1252.json"
    bad.write_bytes(text.encode("cp1252"))
    with _pytest.raises(Invalid, match="cp1252.json is not UTF-8"):
        _read_json(str(bad))
    junk = write_root / "junk.json"
    junk.write_text("{not json", encoding="utf-8")
    with _pytest.raises(Invalid, match="junk.json is not JSON"):
        _read_json(str(junk))
