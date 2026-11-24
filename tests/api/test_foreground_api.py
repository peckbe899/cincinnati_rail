"""A save and the reads that follow it come before background work (I2.1, found by ``app/e2e/sheet.spec.ts`` "second
context updates within 1 s").

Ben saves a level in one tab; the other tab is to show it within a second: the save, its record event, and the other
tab's reads of the section's input and stations. On the I2.1 hub that half the time took longer, because both tabs'
run chains for the new scenario were being planned at the same time on the hub's one Python thread pool. Now a record
write holds the scheduler's foreground as a live import does, and so do the sheet's reads of a section: background
planning stops at its next step and no background job starts until they are done and the invalidator has taken in
what the write wrote. A watch (``POST /compute`` with ``watch_s``) plans its job once, and a second ask finds that
plan."""

from __future__ import annotations

import json
import time

import pytest

from tests.api import jobtypes
from tests.api.conftest import H

PATCH = {**H, "Content-Type": "application/json-patch+json"}


def _create(client, text="a"):
    r = client.post("/api/v1/k/note", json={"data": {"text": text}, "geom": None}, headers=H)
    assert r.status_code == 201, r.text
    return r.json(), r.headers["etag"]


def _spy(api, monkeypatch, name: str) -> list[bool]:
    """Whether the background waited (``_foreground_busy``) while the store's ``name`` ran, once per call."""
    seen: list[bool] = []
    orig = getattr(api.store, name)

    def spy(*a, **k):
        seen.append(api.jobs._foreground_busy(jobs=False))
        return orig(*a, **k)

    monkeypatch.setattr(api.store, name, spy)
    return seen


def _free(api) -> bool:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not api.jobs._foreground_busy(jobs=False):
            return True
        time.sleep(0.02)
    return False


@pytest.mark.parametrize("how", ["create", "put", "patch", "delete", "restore", "changeset", "revert", "promote"])
def test_a_record_write_holds_the_foreground(api, client, monkeypatch, how):
    rec, tag = _create(client)
    path = f"/api/v1/k/note/{rec['id']}"
    if how in ("restore", "revert"):
        r = client.put(path, json={"data": {"text": "two"}, "geom": None}, headers={**H, "If-Match": tag})
        assert r.status_code == 200
        tag, edit = r.headers["etag"], r.json()
    if how == "promote":
        assert client.post("/api/v1/layers", json={"slug": "try", "tier": "scenario"}, headers=H).status_code == 201
        r = client.put(
            path,
            params={"layer": "try"},
            json={"data": {"text": "tried"}, "geom": None},
            headers={**H, "If-Match": tag},
        )
        assert r.status_code == 200
    assert _free(api)
    store_call = {"create": "write", "changeset": "write"}.get(how, how)
    seen = _spy(api, monkeypatch, store_call)
    if how == "create":
        r = client.post("/api/v1/k/note", json={"data": {"text": "b"}, "geom": None}, headers=H)
    elif how == "put":
        r = client.put(path, json={"data": {"text": "b"}, "geom": None}, headers={**H, "If-Match": tag})
    elif how == "patch":
        ops = [{"op": "replace", "path": "/data/text", "value": "b"}]
        r = client.patch(path, content=json.dumps(ops), headers={**PATCH, "If-Match": tag})
    elif how == "delete":
        r = client.delete(path, headers={**H, "If-Match": tag})
    elif how == "restore":
        r = client.post(path + "/restore", params={"version": 1}, headers={**H, "If-Match": tag})
    elif how == "changeset":
        ops = [{"op": "put", "kind": "note", "id": rec["id"], "if_match": tag, "body": {"data": {"text": "b"}}}]
        r = client.post("/api/v1/changesets", json={"layer": "main", "message": "one", "ops": ops}, headers=H)
    elif how == "revert":
        r = client.post(f"/api/v1/changesets/{edit['changeset']}/revert", headers=H)
    else:
        r = client.post("/api/v1/layers/try/promote", json={"message": "take it"}, headers=H)
    assert r.status_code in (200, 201), r.text
    assert seen and all(seen), "the background was free while the write ran"
    # and it is given back once the invalidator has taken the write in
    assert _free(api)


@pytest.mark.parametrize("how", ["get", "list"])
def test_a_record_read_holds_the_foreground(api, client, monkeypatch, how):
    rec, _tag = _create(client)
    assert _free(api)
    seen = _spy(api, monkeypatch, how)
    if how == "get":
        r = client.get(f"/api/v1/k/note/{rec['id']}")
    else:
        r = client.get("/api/v1/k/note")
    assert r.status_code == 200, r.text
    assert seen and all(seen), "the background was free while the read ran"
    assert _free(api)


def test_a_failed_write_gives_the_foreground_back(api, client):
    rec, _tag = _create(client)
    r = client.put(
        f"/api/v1/k/note/{rec['id']}", json={"data": {"text": "b"}, "geom": None}, headers={**H, "If-Match": '"main:9"'}
    )
    assert r.status_code == 412
    assert _free(api)
    assert api.jobs._fg_holds == 0


def test_a_watched_compute_plans_its_job_once(api, client, monkeypatch):
    rec = api.note("hello")
    scope = f"note/{rec['id']}"
    plans: list[str] = []
    orig = jobtypes.Arr.plan

    def counting(self, ctx, scope_id):
        plans.append(scope_id)
        return orig(self, ctx, scope_id)

    monkeypatch.setattr(jobtypes.Arr, "plan", counting)
    # the job is not run here (its commit plans it again to check its key): only the asks plan it
    monkeypatch.setattr(api.jobs.hosts["inline"], "free", lambda: 0)
    body = {"type": "t.api_arr", "scope": scope, "view": "main|-|canon", "priority": 2, "watch_s": 60}
    first = client.post("/api/v1/compute", json=body, headers=H)
    assert first.status_code == 200 and first.json()["key"]
    assert len(plans) == 1, "the submit and the watch each planned the job"
    # the other tab asks for the same job: the kept plan answers
    second = client.post("/api/v1/compute", json={**body, "priority": 3}, headers={**H, "X-CR-Client": "tab-2"})
    assert second.status_code == 200 and second.json()["key"] == first.json()["key"]
    assert len(plans) == 1
