"""Files from the mounted data tiers and the app build: Range, ETag, gzip for JSON (never webp or PMTiles), and the
app's paths, types and cache rules."""

from __future__ import annotations

import json
import os

import pytest


@pytest.fixture
def tier(api):
    root = api.root / "tier_files"
    doc = {"tiles": [{"i": i, "corners": [715000.0 + i, 4331000.0, 715512.0 + i, 4331512.0]} for i in range(200)]}
    (root / "index.json").write_text(json.dumps(doc), encoding="utf-8")
    (root / "tile.webp").write_bytes(os.urandom(64) + b"RIFF" * 2000)
    (root / "base.pmtiles").write_bytes(b"PMTiles" + bytes(range(256)) * 40)
    (root / "plain.bin").write_bytes(bytes(range(256)) * 8)
    return root


def test_range_206(client, tier):
    whole = (tier / "plain.bin").read_bytes()
    r = client.get("/api/v1/data/files/plain.bin", headers={"Range": "bytes=10-19"})
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 10-19/{len(whole)}"
    assert r.content == whole[10:20]
    r = client.get("/api/v1/data/files/plain.bin", headers={"Range": "bytes=-16"})
    assert r.status_code == 206 and r.content == whole[-16:]
    r = client.get("/api/v1/data/files/base.pmtiles", headers={"Range": "bytes=0-6"})
    assert r.status_code == 206 and r.content == b"PMTiles"
    assert r.headers.get("content-encoding") is None
    assert client.get("/api/v1/data/files/plain.bin").headers["accept-ranges"] == "bytes"


def test_etag_304(client, tier):
    r = client.get("/api/v1/data/files/index.json")
    assert r.status_code == 200
    tag = r.headers["etag"]
    assert tag.startswith('"') and r.headers["cache-control"] == "no-cache"
    again = client.get("/api/v1/data/files/index.json", headers={"If-None-Match": tag})
    assert again.status_code == 304 and again.content == b"" and again.headers["etag"] == tag
    (tier / "index.json").write_text("{}", encoding="utf-8")
    changed = client.get("/api/v1/data/files/index.json", headers={"If-None-Match": tag})
    assert changed.status_code == 200 and changed.headers["etag"] != tag


def test_gzip_json_not_webp(client, tier):
    gz = {"Accept-Encoding": "gzip"}
    r = client.get("/api/v1/data/files/index.json", headers=gz)
    assert r.status_code == 200
    assert r.headers["content-encoding"] == "gzip" and r.headers["content-type"].startswith("application/json")
    assert json.loads(r.content)["tiles"][3]["i"] == 3  # httpx decodes it
    for name in ("tile.webp", "base.pmtiles"):
        r = client.get(f"/api/v1/data/files/{name}", headers=gz)
        assert r.status_code == 200 and "content-encoding" not in r.headers, name
        assert r.content == (tier / name).read_bytes()
    assert client.get("/api/v1/data/files/tile.webp").headers["content-type"] == "image/webp"
    # JSON API answers are gzipped too
    big = client.get("/api/v1/meta", headers=gz)
    assert big.headers["content-encoding"] == "gzip"
    raw = client.get("/api/v1/data/files/index.json", headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in raw.headers


def test_mounts_and_missing_tiers(client, tier, api):
    (api.root / "tier_hidden" / "x.json").write_text("{}", encoding="utf-8")
    assert client.get("/api/v1/data/hidden/x.json").status_code == 404  # not mounted
    gone = client.get("/api/v1/data/gone/x.json")
    assert gone.status_code == 404 and "not on this machine" in gone.json()["detail"]
    assert client.get("/api/v1/data/nope/x.json").status_code == 404
    head = client.head("/api/v1/data/files/plain.bin")
    assert head.status_code == 200 and head.content == b""
    tiers = client.get("/api/v1/tiers").json()
    assert {t["name"]: t["status"] for t in tiers["tiers"]}["gone"] == "missing"


def test_app_dist(client, api):
    dist = api.root / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "map" / "glyphs").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>hub</title>" + "<!-- -->" * 300, encoding="utf-8")
    (dist / "assets" / "index-abc123.js").write_text("export const x = 1;\n" * 200, encoding="utf-8")
    (dist / "assets" / "worker-abc.mjs").write_text("self.onmessage = () => {};\n", encoding="utf-8")
    (dist / "map" / "style.json").write_text('{"version": 8}', encoding="utf-8")
    (dist / "map" / "glyphs" / "0-255.pbf").write_bytes(b"\x0a\x00" * 10)
    for path in ("/", "/w/design", "/w/design/deep?layer=try"):
        r = client.get(path)
        assert r.status_code == 200 and r.text.startswith("<!doctype html>"), path
        assert r.headers["cache-control"] == "no-cache" and r.headers["content-type"].startswith("text/html")
    js = client.get("/assets/index-abc123.js", headers={"Accept-Encoding": "gzip"})
    assert js.headers["content-type"].startswith("text/javascript")
    assert js.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert js.headers["content-encoding"] == "gzip"
    assert client.get("/assets/worker-abc.mjs").headers["content-type"].startswith("text/javascript")
    assert client.get("/map/glyphs/0-255.pbf").headers["content-type"] == "application/x-protobuf"
    assert client.get("/map/style.json").json() == {"version": 8}
    assert client.get("/assets/missing.js").status_code == 404
    assert client.get("/nothing-here").status_code == 404
    assert client.get("/api/v1/nothing").json()["code"] == "not_found"


def test_app_not_built(client):
    r = client.get("/")
    assert r.status_code == 503 and "crhub setup" in r.text

