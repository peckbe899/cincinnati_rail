"""Changesets, layers and the review queue over HTTP (decisions 9.10, 9.13)."""

from __future__ import annotations

from tests.api.conftest import H


def _note(client, text):
    r = client.post("/api/v1/k/note", json={"data": {"text": text}, "geom": None}, headers=H)
    assert r.status_code == 201
    return r.json()


def test_changeset_lists_every_conflict(client):
    a, b, c = _note(client, "a"), _note(client, "b"), _note(client, "c")
    for rec in (a, b):  # someone else moves a and b on
        r = client.put(f"/api/v1/k/note/{rec['id']}", json={"data": {"text": rec["data"]["text"] + "2"}, "geom": None},
                       headers={**H, "If-Match": '"main:1"'})
        assert r.status_code == 200
    ops = [
        {"op": "put", "kind": "note", "id": rec["id"], "if_match": '"main:1"', "body": {"data": {"text": "mine"}}}
        for rec in (a, b, c)
    ]
    r = client.post("/api/v1/changesets", json={"layer": "main", "message": "three", "ops": ops}, headers=H)
    assert r.status_code == 412
    stale = r.json()["stale"]
    assert [(s["index"], s["id"], s["etag"]) for s in stale] == [(0, a["id"], '"main:2"'), (1, b["id"], '"main:2"')]
    # nothing was written: c is untouched
    assert client.get(f"/api/v1/k/note/{c['id']}").json()["version"] == 1
    # a conflict of references lists each record too, with 409
    ops = [{"op": "create", "kind": "note", "id": a["id"], "body": {"data": {"text": "dup"}}},
           {"op": "create", "kind": "note", "body": {"data": {"text": "new"}}}]
    r = client.post("/api/v1/changesets", json={"layer": "main", "ops": ops}, headers=H)
    assert r.status_code == 409 and r.json()["reason"] == "exists"
    assert r.json()["conflicts"][0]["id"] == a["id"]


def test_changeset_commits_atomically_and_lists(client):
    ops = [{"op": "create", "kind": "note", "body": {"data": {"text": str(i)}}} for i in range(3)]
    r = client.post("/api/v1/changesets", json={"layer": "main", "message": "bulk", "ops": ops}, headers=H)
    assert r.status_code == 200
    res = r.json()
    assert res["changeset"] and res["seq"] and len(res["records"]) == 3
    listed = client.get("/api/v1/changesets", params={"layer": "main"}).json()["items"]
    assert listed[0]["id"] == res["changeset"] and listed[0]["message"] == "bulk" and listed[0]["client"] == "test-tab"
    one = client.get(f"/api/v1/changesets/{res['changeset']}").json()
    assert len(one["records"]) == 3
    bad = client.post("/api/v1/changesets", json={"layer": "main", "ops": [{"op": "zap", "kind": "note"}]}, headers=H)
    assert bad.status_code == 422
    assert client.post("/api/v1/changesets", json={"layer": "main", "ops": []}, headers=H).status_code == 422


def test_revert_conflict_409(client):
    rec = _note(client, "one")
    path = f"/api/v1/k/note/{rec['id']}"
    edit = client.put(path, json={"data": {"text": "two"}, "geom": None}, headers={**H, "If-Match": '"main:1"'}).json()
    later = client.put(path, json={"data": {"text": "three"}, "geom": None}, headers={**H, "If-Match": '"main:2"'})
    assert later.status_code == 200
    r = client.post(f"/api/v1/changesets/{edit['changeset']}/revert", headers=H)
    assert r.status_code == 409
    body = r.json()
    assert body["code"] == "conflict_revert" and body["reason"] == "revert"
    (c,) = body["conflicts"]
    assert c["id"] == rec["id"] and c["diff"] == [{"op": "replace", "path": "/data/text", "value": "three"}]
    # the latest changeset reverts cleanly: undo gives back version 2's content as version 4
    ok = client.post(f"/api/v1/changesets/{later.json()['changeset']}/revert", headers=H)
    assert ok.status_code == 200
    assert ok.json()["records"][0]["version"] == 4 and ok.json()["records"][0]["data"] == {"text": "two"}


def test_layers_promote_tags_and_review_queue(client):
    rec = _note(client, "base")
    assert client.post("/api/v1/layers", json={"slug": "try", "tier": "scenario"}, headers=H).status_code == 201
    dup = client.post("/api/v1/layers", json={"slug": "try", "tier": "scenario"}, headers=H)
    assert dup.status_code == 409
    assert client.post("/api/v1/layers", json={"slug": "x", "tier": "import"}, headers=H).status_code == 422
    # a proposal is named proposal:<name> (its seed folder is read back as that slug); a plain name is refused
    plain = client.post("/api/v1/layers", json={"slug": "gate", "tier": "proposal"}, headers=H)
    assert plain.status_code == 422 and "proposal:<name>" in plain.json()["detail"]
    slugs = [la["slug"] for la in client.get("/api/v1/layers").json()["items"]]
    assert "main" in slugs and "try" in slugs and "gate" not in slugs
    path = f"/api/v1/k/note/{rec['id']}"
    client.put(path, params={"layer": "try"}, json={"data": {"text": "tried"}, "geom": None},
               headers={**H, "If-Match": '"main:1"'})
    diff = client.get("/api/v1/layers/try/diff").json()["items"]
    # the copy-up continues main's version 1 as the scenario's version 2
    assert diff == [{"kind": "note", "id": rec["id"], "op": "put", "fields": ["data.text"], "ours": '"try:2"',
                     "theirs": '"main:1"'}]
    tag = client.post("/api/v1/layers/try/tags", json={"name": "v1"}, headers=H)
    assert tag.status_code == 201 and tag.json()["name"] == "v1"
    assert [t["name"] for t in client.get("/api/v1/layers/try/tags").json()["items"]] == ["v1"]
    r = client.post("/api/v1/layers/try/promote", json={"message": "take it"}, headers=H)
    assert r.status_code == 200 and r.json()["changeset"]
    assert client.get(path).json()["data"] == {"text": "tried"}
    assert client.get("/api/v1/layers/try").json()["state"] == "promoted"
    assert client.get("/api/v1/conflicts").json()["items"] == []
    assert client.get("/api/v1/conflicts", params={"state": "all"}).status_code == 200
    assert client.post("/api/v1/conflicts/nope/resolve", json={"take": "ours"}, headers=H).status_code == 404
