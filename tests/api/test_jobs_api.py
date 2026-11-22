"""Jobs, results and the ops routes over the real scheduler: /compute, /results (200 with a null key, immutable
results, array bytes with dtype, shape and ranges), /jobs, /meta, /health, /export, /backup, /client-log."""

from __future__ import annotations

import json
import logging

import numpy as np

from tests.api.conftest import H


def _compute(client, scope, type="t.api_arr", view="main|-|canon"):
    r = client.post("/api/v1/compute", json={"type": type, "scope": scope, "view": view}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def test_compute_then_result_and_array(api, client):
    rec = api.note("hello")
    scope = f"note/{rec['id']}"
    latest = client.get("/api/v1/results", params={"type": "t.api_arr", "scope": scope, "view": "main|-|canon"})
    assert latest.status_code == 200 and latest.json() == {"key": None}
    first = _compute(client, scope)
    assert first["state"] in ("queued", "running") and first["job"] and first["key"]
    assert api.jobs.wait_idle(10)
    again = _compute(client, scope, view={"layer": "main", "tl": "canon"})
    assert again == {"key": first["key"], "state": "hit", "job": None}
    key = client.get("/api/v1/results", params={"type": "t.api_arr", "scope": scope}).json()["key"]
    assert key == first["key"]
    meta = client.get(f"/api/v1/results/{key}")
    assert meta.status_code == 200 and meta.json()["meta"]["n"] == 5 and meta.json()["status"] == "ok"
    assert meta.headers["etag"] == f'"{key}"' and "immutable" in meta.headers["cache-control"]
    assert client.get(f"/api/v1/results/{key}", headers={"If-None-Match": f'"{key}"'}).status_code == 304
    arr = client.get(f"/api/v1/results/{key}/a/v")
    assert arr.status_code == 200 and arr.headers["x-dtype"] == "<f8" and arr.headers["x-shape"] == "10"
    assert np.array_equal(np.frombuffer(arr.content, dtype="<f8"), np.full(10, 5.0))
    part = client.get(f"/api/v1/results/{key}/a/v", headers={"Range": "bytes=8-15"})
    assert part.status_code == 206 and np.frombuffer(part.content, dtype="<f8").tolist() == [5.0]
    assert part.headers["content-range"] == "bytes 8-15/80"
    assert client.get(f"/api/v1/results/{key}/a/v", headers={"Range": "bytes=900-"}).status_code == 416
    assert client.get(f"/api/v1/results/{key}/a/nope").status_code == 404
    assert client.get("/api/v1/results/nokey").status_code == 404


def test_jobs_routes(api, client):
    rec = api.note("x")
    out = _compute(client, f"note/{rec['id']}")
    assert api.jobs.wait_idle(10)
    jobs = client.get("/api/v1/jobs").json()["items"]
    assert jobs[0]["id"] == out["job"] and jobs[0]["state"] == "done"
    assert client.get("/api/v1/jobs", params={"active": 1}).json()["items"] == []
    one = client.get(f"/api/v1/jobs/{out['job']}").json()
    assert one["type"] == "t.api_arr" and one["key"] == out["key"]
    assert isinstance(client.get(f"/api/v1/jobs/{out['job']}/log").json()["items"], list)
    assert client.get("/api/v1/jobs/nope").status_code == 404
    assert client.post("/api/v1/jobs/nope/cancel", headers=H).status_code == 404
    bad = client.post("/api/v1/compute", json={"type": "nope", "scope": "x"}, headers=H)
    assert bad.status_code == 404
    bad = client.post("/api/v1/compute", json={"type": "noop", "scope": "x", "view": "not a view"}, headers=H)
    assert bad.status_code == 422


def test_meta_and_health(api, client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["ok"] is True and r.headers["cache-control"] == "no-store"
    meta = client.get("/api/v1/meta").json()
    names = {k["kind"] for k in meta["kinds"]}
    assert {"note", "feature", "t_section"} <= names
    note = next(k for k in meta["kinds"] if k["kind"] == "note")
    assert note["schema"]["required"] == ["text"] and note["version"] == 1
    assert {"main", "import:profiles", "legacy:old_hub"} <= {la["slug"] for la in meta["layers"]}
    assert meta["epoch"] == r.json()["epoch"] and meta["db_epoch"] == api.store.epoch()
    assert meta["engine"]["engine_build"] and meta["engine_error"] is None  # the Fake's hello
    assert {"noop", "t.api_arr"} <= {j["name"] for j in meta["job_types"]}
    assert meta["schema_version"] >= 2 and meta["old_hub"].startswith("http://127.0.0.1")
    assert isinstance(meta["importers"], list) and isinstance(meta["features"], list)


def test_backup_and_client_log(api, client, caplog):
    r = client.post("/api/v1/backup", headers=H)
    assert r.status_code == 200
    from pathlib import Path

    assert Path(r.json()["path"]).is_file()
    with caplog.at_level(logging.ERROR, logger="region.client"):
        r = client.post("/api/v1/client-log", json={"level": "error", "msg": "boom", "url": "/w/design"}, headers=H)
    assert r.status_code == 204
    found = [rec for rec in caplog.records if rec.name == "region.client"]
    assert found and found[-1].getMessage() == "boom" and found[-1].client_url == "/w/design"


def test_export_writes_seeds(api, client, write_root, monkeypatch):
    from region.model import seed

    out = write_root / "seed"
    monkeypatch.setattr(seed, "SEED", out)
    monkeypatch.setattr(seed.export, "__defaults__", (out,))
    api.note("seeded")
    r = client.post("/api/v1/export", headers=H)
    assert r.status_code == 200, r.text
    assert r.json()["layers"]["main"]["records"] == 1
    files = [p for p in out.rglob("*") if p.is_file() and p.suffix == ".json"]
    assert files and any(json.loads(p.read_text(encoding="utf-8")).get("kind") == "note" for p in files)


def test_only_ok_results_are_immutable_and_a_range_past_the_end_is_a_problem(api, client):
    """server-8, compute-14: an error row was served immutable for a year (and 304 to If-None-Match), though the key
    can become ok when it runs again. server-9: a 416 had no problem+json body."""
    with api.jobs.cache.tx() as con:
        con.execute(
            "INSERT INTO result (key, type, scope, view, status, error, created, last_used) "
            "VALUES ('errkey', 't.api_arr', 'note/x', 'main|-|canon', 'error', 'engine down', '2026-11-22', 0)"
        )
    r = client.get("/api/v1/results/errkey")
    assert r.status_code == 200 and r.json()["status"] == "error"
    assert r.headers["cache-control"] == "no-store" and "etag" not in r.headers
    assert client.get("/api/v1/results/errkey", headers={"If-None-Match": '"errkey"'}).status_code == 200
    rec = api.note("hello")
    key = _compute(client, f"note/{rec['id']}")["key"]
    assert api.jobs.wait_idle(10)
    far = client.get(f"/api/v1/results/{key}/a/v", headers={"Range": "bytes=900-"})
    assert far.status_code == 416 and far.headers["content-type"].startswith("application/problem+json")
    body = far.json()
    assert body["code"] == "range_not_satisfiable" and body["status"] == 416
    assert far.headers["content-range"] == "bytes */80" and far.headers["x-request-id"]


def test_api_answers_are_not_kept_by_the_browser_and_no_page_can_frame_the_hub(api, client):
    """server-1: a record ETag ("<layer>:<version>") repeats after a restore, and the browser's cache served the
    old body under it; API answers without a cache policy of their own are no-store. server-7: X-Frame-Options."""
    rec = api.note("x")
    r = client.get(f"/api/v1/k/note/{rec['id']}")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    listed = client.get("/api/v1/k/note")
    assert listed.headers["cache-control"] == "no-store" and listed.headers["etag"].startswith('"seq:')
    assert r.headers["x-frame-options"] == "DENY"
    assert client.get("/api/v1/health").headers["cache-control"] == "no-store"
