"""The security rules of section 9: the host allowlist, writes needing X-CR-Client and JSON, foreign origins,
path containment (a fuzz test over raw ASGI paths, so no client normalises them first), the body cap and the CSP."""

from __future__ import annotations

import asyncio
import string
from urllib.parse import unquote

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from region.api.security import CSP
from tests.api.conftest import BASE, H

SECRET = b"TOP-SECRET-OUTSIDE-EVERY-ROOT"


def test_bad_host_400(client):
    for host in ("evil.example", "127.0.0.2:8766", "localhost.evil.example", "", "[::2]:8766", "127.0.0.1:8766@x"):
        r = client.get("/api/v1/health", headers={"Host": host})
        assert r.status_code == 400, host
        assert r.json()["code"] == "bad_host"
    for host in ("127.0.0.1:8766", "localhost:8766", "[::1]:8766", "LOCALHOST", "127.0.0.1"):
        assert client.get("/api/v1/health", headers={"Host": host}).status_code == 200, host


def test_write_without_client_header_403(client):
    body = {"data": {"text": "a"}, "geom": None}
    r = client.post("/api/v1/k/note", json=body)
    assert r.status_code == 403 and r.json()["code"] == "client_required"
    for method in ("PUT", "PATCH", "DELETE"):
        r = client.request(method, "/api/v1/k/note/01M7ZVJNXS9TJVYCAMWJS3XVSS", json=body)
        assert r.status_code == 403, method
    r = client.post("/api/v1/k/note", json=body, headers={"X-CR-Client": "bad client!"})
    assert r.status_code == 400 and r.json()["code"] == "bad_client"
    # a form (what another page could make a browser send) is refused for its type
    r = client.post("/api/v1/k/note", content=b"data=x", headers={"X-CR-Client": "t",
                    "Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 415 and r.json()["code"] == "json_required"
    r = client.post("/api/v1/k/note", content=b"{}", headers={"X-CR-Client": "t", "Content-Type": "text/plain"})
    assert r.status_code == 415
    assert client.post("/api/v1/k/note", json=body, headers=H).status_code == 201
    # reads need neither
    assert client.get("/api/v1/k/note").status_code == 200


def test_foreign_origin_403(client):
    for origin in ("http://evil.example", "null", "http://127.0.0.1:8765", "https://127.0.0.1:8766",
                   "http://localhost:8766"):
        r = client.get("/api/v1/meta", headers={"Origin": origin})
        assert r.status_code == 403, origin
        assert r.json()["code"] == "foreign_origin"
        r = client.post("/api/v1/k/note", json={"data": {"text": "x"}}, headers={**H, "Origin": origin})
        assert r.status_code == 403, origin
    same = client.post("/api/v1/k/note", json={"data": {"text": "x"}}, headers={**H, "Origin": BASE})
    assert same.status_code == 201
    r = client.get("/api/v1/meta", headers={"Origin": BASE})
    assert r.status_code == 200
    assert not any(k.lower().startswith("access-control-") for k in r.headers)


def _get_raw(app, raw_path: str) -> tuple[int, bytes]:
    """GET a raw path through the app's ASGI interface, exactly as uvicorn would hand it over (no normalisation)."""
    path_bytes = raw_path.encode("latin-1", "replace")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": unquote(raw_path, encoding="latin-1"),
        "raw_path": path_bytes,
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"127.0.0.1:8766")],
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8766),
    }
    out: dict = {"status": None, "body": b"", "asked": False}

    async def run() -> None:
        done = asyncio.Event()

        async def receive():
            if not out["asked"]:
                out["asked"] = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await done.wait()  # the client hangs up once the response is complete
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.start":
                out["status"] = message["status"]
            elif message["type"] == "http.response.body":
                out["body"] += message.get("body", b"")
                if not message.get("more_body", False):
                    done.set()

        await asyncio.wait_for(app(scope, receive, send), timeout=10)

    asyncio.run(run())
    return out["status"], out["body"]


PIECES = [
    "..", ".", "%2e%2e", "%2E%2e", "%2e", "%5c", "%5C", "%5c..", "..%5c", "%2f..", "..%2f", "%252e%252e", "%255c",
    "C:", "c:%5c", "%5c%5cserver", "server", "share", "CON", "nul", "aux.txt", "COM1", "lpt9.log", "CONIN$",
    "a.", "a ", "a%20", "a%2e", ":", "a:b", "file.json:stream", "%00", "%0a", "~", "secret.txt", "ok.json", "sub",
    "", "%c0%ae%c0%ae", "\u2025", "a<b", "a|b", "a?b",
]


def _fuzz_setup(api):
    root = api.root
    (root / "secret.txt").write_bytes(SECRET)
    files = root / "tier_files"
    (files / "ok.json").write_bytes(b'{"ok": true}')
    (files / "sub").mkdir()
    (files / "sub" / "ok.json").write_bytes(b'{"ok": true}')
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    (dist / "index.html").write_bytes(b"<!doctype html><title>hub</title>")
    (dist / "ok.json").write_bytes(b'{"ok": true}')
    try:
        (files / "escape").symlink_to(root)
    except OSError:  # Windows without the symlink privilege
        pass


def test_containment_fuzz_404(api):
    _fuzz_setup(api)
    app = api.app()
    good = {"ok.json", "sub/ok.json"}

    @settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.lists(st.sampled_from(PIECES), min_size=1, max_size=5), st.sampled_from(["/api/v1/data/files/", "/"]))
    def check(parts, prefix):
        rel = "/".join(parts)
        status, body = _get_raw(app, prefix + rel)
        assert SECRET not in body
        if rel in good:
            assert status == 200
        elif prefix == "/" and (rel == "" or rel.startswith("w/")):
            assert status == 200  # the app's index
        else:
            assert status == 404, (prefix + rel, status)

    check()
    for raw in ("/api/v1/data/files/escape/secret.txt", "/api/v1/data/files/..%2fsecret.txt",
                "/api/v1/data/files/%2e%2e/secret.txt", "/api/v1/data/hidden/x", "/api/v1/data/nope/ok.json",
                "/..%2f..%2fsecret.txt", "/api/v1/data/files/sub", "/api/v1/data/files/C:/secret.txt"):
        status, body = _get_raw(app, raw)
        assert status == 404 and SECRET not in body, raw
    assert _get_raw(app, "/api/v1/data/files/ok.json")[0] == 200


def test_body_cap_413(api):
    from fastapi.testclient import TestClient

    big = {"data": {"text": "x" * 5000}, "geom": None}
    with TestClient(api.app(body_cap_mb=0.001), base_url=BASE) as c:  # 1048 bytes
        r = c.post("/api/v1/k/note", json=big, headers=H)
        assert r.status_code == 413 and r.json()["code"] == "body_too_large"

        def chunks():  # no Content-Length: the cap applies while the body streams
            yield b'{"data": {"text": "'
            for _ in range(10):
                yield b"x" * 500
            yield b'"}}'

        r = c.post("/api/v1/k/note", content=chunks(), headers=H)
        assert r.status_code == 413
        assert c.post("/api/v1/k/note", json={"data": {"text": "small"}}, headers=H).status_code == 201


def test_csp_header(api, client):
    dist = api.root / "dist"
    dist.mkdir(exist_ok=True)
    (dist / "index.html").write_bytes(b"<!doctype html><title>hub</title>")
    for path in ("/api/v1/health", "/", "/w/design", "/api/v1/k/nope", "/api/v1/events/poll"):
        r = client.get(path)
        assert r.headers["content-security-policy"] == CSP, path
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-request-id"]
    assert CSP == "default-src 'self'; worker-src 'self' blob:; img-src 'self' blob: data:"
    refused = client.get("/api/v1/health", headers={"Host": "evil.example"})
    assert refused.headers["content-security-policy"] == CSP


def test_request_id_in_problem_and_header(client):
    r = client.get("/api/v1/k/nope", headers={"X-Request-ID": "abcdef0123456789"})
    assert r.headers["x-request-id"] == "abcdef0123456789" == r.json()["request_id"]
    r = client.get("/api/v1/k/nope", headers={"X-Request-ID": "no way"})
    assert r.headers["x-request-id"] != "no way" and set(r.json()["request_id"]) <= set(string.printable)
