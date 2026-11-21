"""Importer routes: a dry run reports and writes nothing, its apply commits, an apply after the sources changed is a
409, and the stored report reads back. Both the shared runner (``region.cli.imports``) and the server's plain one."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from region.core import ids
from region.core.view import View
from tests.api.conftest import H


class NoteImporter:
    """Notes from a JSON list of ``{key, text}`` in ``var://imp/notes.json``, ids stable in the test namespace."""

    name = "t_notes"
    version = "1"
    namespace = "test"
    layer = "import:test"

    def sources(self, paths):
        return {"notes": "var://imp/notes.json"}

    def records(self, src, ids_):
        for row in json.loads(Path(src["notes"]).read_text(encoding="utf-8")):
            yield {"kind": "note", "id": ids.stable("test", row["key"]), "data": {"text": row["text"]}, "geom": None}


@pytest.fixture(params=["shared", "plain"])
def importer(request, api, hub_var, monkeypatch):
    from region.api import imports as I

    api.store.create_layer("import:test", namespace="test", by="test")
    (hub_var / "imp").mkdir()
    src = hub_var / "imp" / "notes.json"
    src.write_text(json.dumps([{"key": "a", "text": "one"}, {"key": "b", "text": "two"}]), encoding="utf-8")
    imp = NoteImporter()
    monkeypatch.setattr(I, "discover_importers", lambda: [("tfeat", imp)])
    if request.param == "plain":
        monkeypatch.setattr(I, "_runner", lambda: None)
    return src


def test_dry_run_then_apply(api, client, importer):
    listed = client.get("/api/v1/importers").json()["items"]
    assert listed == [{"name": "t_notes", "version": "1", "namespace": "test", "layer": "import:test",
                       "feature": "tfeat"}]
    r = client.post("/api/v1/imports", json={"importer": "t_notes"}, headers=H)
    assert r.status_code == 200, r.text
    dry = r.json()
    assert dry["dry_run"] is True and dry["counts"]["created"] == 2 and dry["changeset"] is None
    assert api.store.list("note", View(layer="import:test"))[0] == []
    stored = client.get(f"/api/v1/imports/{dry['id']}").json()
    assert stored["state"] == "planned" and stored["importer"] == "t_notes"
    applied = client.post(f"/api/v1/imports/{dry['id']}/apply", headers=H)
    assert applied.status_code == 200, applied.text
    assert applied.json()["changeset"] and applied.json()["counts"]["created"] == 2
    assert len(api.store.list("note", View())[0]) == 2  # import layers are in main's chain
    again = client.post(f"/api/v1/imports/{applied.json()['id']}/apply", headers=H)
    assert again.status_code == 409  # not a dry run


def test_apply_refused_after_the_sources_changed(client, importer):
    dry = client.post("/api/v1/imports", json={"importer": "t_notes", "dry_run": True}, headers=H).json()
    importer.write_text(json.dumps([{"key": "a", "text": "changed"}]), encoding="utf-8")
    r = client.post(f"/api/v1/imports/{dry['id']}/apply", headers=H)
    assert r.status_code == 409 and "changed since the dry run" in r.json()["detail"]
    assert client.post("/api/v1/imports", json={"importer": "nope"}, headers=H).status_code == 404
    assert client.get("/api/v1/imports/999").status_code == 404
