"""The CLI's client of a running hub: no proxy for loopback (server-4, windows-7), the host the serve recorded
(server-10), and a hub of another checkout is not used for export (windows-2)."""

from __future__ import annotations

import http.server
import json
import threading

import pytest

from region.api.client import HubClient, running_hub
from region.core import lock


class _Ok(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - the stdlib's name
        body = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        pass


def test_loopback_requests_never_use_a_proxy(monkeypatch):
    """With HTTP_PROXY set and NO_PROXY unset (or a Windows system proxy, whose "<local>" bypass does not cover
    127.0.0.1), the client still reaches the hub directly."""
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Ok)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        for name in ("no_proxy", "NO_PROXY"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
        client = HubClient(f"http://127.0.0.1:{srv.server_address[1]}")
        assert client.json("GET", "/health") == {"ok": True}
    finally:
        srv.shutdown()
        srv.server_close()


def test_the_lock_records_host_and_checkout_and_the_client_dials_that_host(hub_var):
    held = lock.acquire(hub_var, 8766, host="::1")
    try:
        holder = lock.reader(hub_var)
        assert holder is not None and holder.host == "::1" and holder.repo == lock.this_repo()
        hub = running_hub(hub_var)
        assert hub is not None and hub.base == "http://[::1]:8766" and hub.holder == holder
        assert "from " + lock.this_repo() in holder.describe()
    finally:
        held.release()
    held = lock.acquire(hub_var, 8766)
    try:
        assert running_hub(hub_var).base == "http://127.0.0.1:8766"
    finally:
        held.release()
    # a lock written before host and repo were recorded still reads
    assert lock.Holder(1, 8766, "", "crhub serve").url() == "http://127.0.0.1:8766"


def test_export_refuses_a_hub_serving_from_another_checkout(hub_var, monkeypatch, capsys):
    """windows-2: two checkouts share var on Windows. crhub export in checkout A must not post /export to a hub
    serving from checkout B: that writes B's region/seed, and git add in A would commit nothing."""
    from region.cli import main as cli_main

    held = lock.acquire(hub_var, 8766)
    try:
        monkeypatch.setattr(lock, "this_repo", lambda: "/elsewhere/cincinnati_rail")
        assert cli_main(["export"]) == 1
        err = capsys.readouterr().err
        assert "another checkout" in err and "/elsewhere/cincinnati_rail" in err
    finally:
        held.release()


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_holder_url_for_ipv4_hosts(host):
    assert lock.Holder(1, 8766, "", "crhub serve", host).url() == "http://127.0.0.1:8766"
