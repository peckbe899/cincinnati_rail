"""Record routes (section 5; decision 9.13): If-Match rules, 304s, JSON Patch only, idempotent creates, lists,
GeoJSON, history, restore, refs and legacy keys."""

from __future__ import annotations

import json

from region.core.view import View
from tests.api.conftest import H

PATCH = {**H, "Content-Type": "application/json-patch+json"}


def _create(client, text="a", layer="main", **headers):
    r = client.post("/api/v1/k/note", params={"layer": layer}, json={"data": {"text": text}, "geom": None},
                    headers={**H, **headers})
    assert r.status_code == 201, r.text
    return r.json(), r.headers["etag"]


def test_put_without_if_match_428(client):
    rec, _tag = _create(client)
    r = client.put(f"/api/v1/k/note/{rec['id']}", json={"data": {"text": "b"}, "geom": None}, headers=H)
    assert r.status_code == 428
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["code"] == "precondition_required" and body["request_id"] and body["conflicts"] == []
    assert client.get(f"/api/v1/k/note/{rec['id']}").json()["data"] == {"text": "a"}
    for method in ("PATCH", "DELETE"):
        r = client.request(method, f"/api/v1/k/note/{rec['id']}", content=b"[]", headers=PATCH)
        assert r.status_code == 428, method


def test_stale_412_body_current_by_diff(client):
    rec, tag = _create(client)
    ok = client.put(f"/api/v1/k/note/{rec['id']}", json={"data": {"text": "theirs"}, "geom": None},
                    headers={**H, "If-Match": tag, "X-CR-By": "other"})
    assert ok.status_code == 200 and ok.headers["etag"] == '"main:2"'
    r = client.put(f"/api/v1/k/note/{rec['id']}", json={"data": {"text": "mine"}, "geom": None},
                   headers={**H, "If-Match": tag})
    assert r.status_code == 412
    body = r.json()
    assert body["code"] == "precondition_failed"
    assert body["current"]["version"] == 2 and body["current"]["data"] == {"text": "theirs"}
    assert body["by"] == "other"
    assert body["diff"] == [{"op": "replace", "path": "/data/text", "value": "theirs"}]
    assert body["stale"][0]["etag"] == '"main:2"'


def test_get_304(client):
    rec, tag = _create(client)
    r = client.get(f"/api/v1/k/note/{rec['id']}")
    assert r.status_code == 200 and r.headers["etag"] == tag == '"main:1"'
    r = client.get(f"/api/v1/k/note/{rec['id']}", headers={"If-None-Match": tag})
    assert r.status_code == 304 and r.headers["etag"] == tag and r.content == b""
    page = client.get("/api/v1/k/note")
    assert page.headers["etag"] == '"seq:2"'
    assert client.get("/api/v1/k/note", headers={"If-None-Match": page.headers["etag"]}).status_code == 304
    _create(client, "b")
    again = client.get("/api/v1/k/note", headers={"If-None-Match": page.headers["etag"]})
    assert again.status_code == 200 and len(again.json()["items"]) == 2


def test_unknown_kind_404(client):
    for path in ("/api/v1/k/nope", "/api/v1/k/nope/01M7ZVJNXS9TJVYCAMWJS3XVSS", "/api/v1/k/Bad-Kind"):
        r = client.get(path)
        assert r.status_code == 404, path
        assert r.json()["code"] == "not_found"
    r = client.post("/api/v1/k/nope", json={"data": {}}, headers=H)
    assert r.status_code == 404
    assert client.get("/api/v1/k/note/not-a-ulid").status_code == 404
    assert client.get("/api/v1/k/note/01M7ZVJNXS9TJVYCAMWJS3XVSS").status_code == 404


def test_patch_needs_json_patch_type(client):
    rec, tag = _create(client)
    ops = [{"op": "replace", "path": "/data/text", "value": "b"}]
    r = client.patch(f"/api/v1/k/note/{rec['id']}", json=ops, headers={**H, "If-Match": tag})
    assert r.status_code == 415 and r.json()["code"] == "json_patch"
    r = client.patch(f"/api/v1/k/note/{rec['id']}", content=json.dumps(ops), headers={**PATCH, "If-Match": tag})
    assert r.status_code == 200 and r.json()["data"] == {"text": "b"} and r.headers["etag"] == '"main:2"'
    # a merge patch is not accepted either, and nulls survive a JSON Patch
    merge = {**H, "Content-Type": "application/merge-patch+json", "If-Match": '"main:2"'}
    assert client.patch(f"/api/v1/k/note/{rec['id']}", content=b"{}", headers=merge).status_code == 415
    ops = [{"op": "add", "path": "/data/title", "value": None}]
    r = client.patch(f"/api/v1/k/note/{rec['id']}", content=json.dumps(ops), headers={**PATCH, "If-Match": '"main:2"'})
    assert r.status_code == 200 and r.json()["data"] == {"text": "b", "title": None}


def test_create_idempotency_key(api, client):
    first, _ = _create(client, "once", **{"Idempotency-Key": "k-1"})
    again = client.post("/api/v1/k/note", json={"data": {"text": "once"}, "geom": None},
                        headers={**H, "Idempotency-Key": "k-1"})
    assert again.status_code == 201 and again.json() == first
    assert again.headers["idempotent-replayed"] == "true"
    assert len(api.store.list("note", View())[0]) == 1
    other = client.post("/api/v1/k/note", json={"data": {"text": "else"}, "geom": None},
                        headers={**H, "Idempotency-Key": "k-1"})
    assert other.status_code == 422 and other.json()["code"] == "idempotency_key_reused"
    # the key is per client: another tab's k-1 is its own
    mine = client.post("/api/v1/k/note", json={"data": {"text": "once"}, "geom": None},
                       headers={**H, "X-CR-Client": "tab-2", "Idempotency-Key": "k-1"})
    assert mine.status_code == 201 and mine.json()["id"] != first["id"]
    assert first["layer"] == "main" and again.headers["location"].endswith(f"/k/note/{first['id']}?layer=main")


def test_delete_history_diff_restore(client):
    rec, tag = _create(client, "one")
    path = f"/api/v1/k/note/{rec['id']}"
    put = client.put(path, json={"data": {"text": "two"}, "geom": None}, headers={**H, "If-Match": tag})
    tag2 = put.headers["etag"]
    hist = client.get(path + "/history").json()["items"]
    assert [h["version"] for h in hist] == [2, 1]
    assert client.get(path + "/history/1").json()["data"] == {"text": "one"}
    assert client.get(path, params={"at": 1}).json()["data"] == {"text": "one"}
    diff = client.get(path + "/diff", params={"from": 1, "to": 2}).json()["items"]
    assert diff == [{"op": "replace", "path": "/data/text", "value": "two"}]
    restored = client.post(path + "/restore", params={"version": 1}, headers={**H, "If-Match": tag2})
    assert restored.status_code == 200 and restored.json()["version"] == 3
    assert restored.json()["data"] == {"text": "one"}
    gone = client.delete(path, headers={**H, "If-Match": '"main:3"'})
    assert gone.status_code == 200 and gone.json()["deleted"] is True
    assert client.get(path).status_code == 404


def test_scenario_copies_up_and_lists_filter(client):
    rec, tag = _create(client, "base")
    r = client.post("/api/v1/layers", json={"slug": "try", "tier": "scenario"}, headers=H)
    assert r.status_code == 201
    path = f"/api/v1/k/note/{rec['id']}"
    assert client.get(path, params={"layer": "try"}).headers["etag"] == '"main:1"'
    r = client.put(path, params={"layer": "try"}, json={"data": {"text": "mine"}, "geom": None},
                   headers={**H, "If-Match": tag})
    assert r.status_code == 200 and r.json()["layer"] == "try"
    assert client.get(path).json()["data"] == {"text": "base"}
    assert client.get(path, params={"layer": "try"}).json()["data"] == {"text": "mine"}
    page = client.get("/api/v1/k/note", params={"layer": "try", "fields": "text", "limit": 1}).json()
    assert page["items"][0]["data"] == {"text": "mine"} and page["next"] is None
    assert client.get("/api/v1/k/note", params={"q": "zzz"}).json()["items"] == []
    assert client.get("/api/v1/k/note", params={"year": "abc"}).status_code == 422


def test_geojson_in_4326_with_dates(client):
    body = {"data": {"name": "Mill Creek", "class": "river", "system": None, "opened": "1931-09"},
            "geom": "LINESTRING (714000 4331000, 715000 4332000)"}
    r = client.post("/api/v1/k/feature", json=body, headers=H)
    assert r.status_code == 201, r.text
    fc = client.get("/api/v1/k/feature", params={"format": "geojson", "crs": "4326"})
    assert fc.status_code == 200 and fc.headers["etag"] == '"seq:2"'
    doc = fc.json()
    assert doc["type"] == "FeatureCollection" and len(doc["features"]) == 1
    f = doc["features"][0]
    assert f["geometry"]["type"] == "LineString"
    lon, lat = f["geometry"]["coordinates"][0]
    assert -84.6 < lon < -84.4 and 39.0 < lat < 39.2
    p = f["properties"]
    assert p["name"] == "Mill Creek" and p["kind"] == "feature" and p["open_lo"] == p["open_hi"] == 1931 * 12 + 8
    assert p["close_lo"] is None
    near = client.get("/api/v1/k/feature", params={"format": "geojson", "crs": "4326", "bbox": f"{lon - 0.01},"
                      f"{lat - 0.01},{lon + 0.01},{lat + 0.01}"}).json()
    assert len(near["features"]) == 1
    far = client.get("/api/v1/k/feature", params={"bbox": "0,0,10,10"}).json()
    assert far["items"] == []
    assert client.get("/api/v1/k/feature", params={"year": 1920}).json()["items"] == []


def test_refs_and_legacy(api, client):
    node = client.post("/api/v1/k/t_node", json={"data": {"name": "Sycamore"}, "geom": "POINT (715000 4331000)"},
                       headers=H).json()
    sec = client.post("/api/v1/k/t_section", json={"data": {"name": "S", "node_a": node["id"]},
                                                  "geom": "LINESTRING (715000 4331000, 715100 4331000)"},
                      headers=H).json()
    refs = client.get(f"/api/v1/refs/{node['id']}").json()["items"]
    assert refs == [{"kind": "t_section", "id": sec["id"], "role": "node_a", "layer": "main"}]
    blocked = client.delete(f"/api/v1/k/t_node/{node['id']}", headers={**H, "If-Match": '"main:1"'})
    assert blocked.status_code == 409 and blocked.json()["code"] == "conflict_reference"
    assert blocked.json()["conflicts"]
    api.store.add_legacy("t_node_key", "metro:Sycamore|1", node["id"])
    hit = client.get("/api/v1/legacy/t_node_key/metro:Sycamore|1")
    assert hit.status_code == 200 and hit.json() == {"kind": "t_node", "id": node["id"]}
    assert client.get("/api/v1/legacy/t_node_key/nothing").status_code == 404


def test_invalid_data_422(client):
    r = client.post("/api/v1/k/note", json={"data": {"text": 5}, "geom": None}, headers=H)
    assert r.status_code == 422 and r.json()["code"] == "invalid" and r.json()["errors"]
    r = client.post("/api/v1/k/note", json={"data": "not an object"}, headers=H)
    assert r.status_code == 422 and r.json()["errors"][0]["path"].startswith("/body")
    r = client.post("/api/v1/k/note", json={"data": {"text": "x"}, "id": "nope"}, headers=H)
    assert r.status_code == 422
