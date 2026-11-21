"""Fixtures for the ops tests: a throwaway repo with its own configs and tiers, fake servers on free ports."""

from __future__ import annotations

import http.server
import json
import os
import socket
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest


def write(path: Path, text: str | bytes) -> Path:
    """A test file (outside the hub's write roots, so plain writes, not ``fsio``)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def make_repo(root: Path, tiers: list[dict[str, Any]], *, hub: dict[str, Any] | None = None) -> Path:
    """A repo-like folder with ``configs/hub.json`` and ``configs/hub_paths.json`` holding ``tiers``."""
    write(root / "configs" / "hub.json", json.dumps(hub or {"host": "127.0.0.1", "port": 8766}))
    write(root / "configs" / "hub_paths.json", json.dumps({"version": 1, "tiers": tiers}))
    return root


def link_dir(link: Path, target: Path) -> None:
    """A directory link (a symlink, or a junction on Windows without the symlink privilege), as npm makes them."""
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        if sys.platform != "win32":
            raise
        import _winapi

        _winapi.CreateJunction(str(target), str(link))


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Handler(http.server.BaseHTTPRequestHandler):
    routes: dict[str, Any] = {}

    def do_GET(self) -> None:  # noqa: N802 (the http.server name)
        body = self.routes.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:  # quiet
        pass


def serve(routes: dict[str, Any]) -> tuple[http.server.ThreadingHTTPServer, int]:
    handler = type("Handler", (_Handler,), {"routes": routes})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


@pytest.fixture
def fake_hub() -> Iterator[int]:
    """A server on a free port that answers ``/api/v1/health`` as the new hub does; yields the port."""
    server, port = serve({"/api/v1/health": {"ok": True}})
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def fake_old_hub() -> Iterator[int]:
    """A server on a free port that answers ``/api/runs`` as the old hub does; yields the port."""
    server, port = serve({"/api/runs": {"runs": [], "current": None, "pending": []}})
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def busy_port() -> Iterator[int]:
    """A port held by a plain listening socket that speaks no HTTP; yields the port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    try:
        yield s.getsockname()[1]
    finally:
        s.close()


@pytest.fixture
def banner_port() -> Iterator[int]:
    """A port held by a program that is not an HTTP server: it sends a banner line and hangs up; yields the port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(8)
    stop = threading.Event()

    def answer() -> None:
        while not stop.is_set():
            try:
                c, _ = s.accept()
            except OSError:
                return
            with c:
                try:
                    c.sendall(b"SSH-2.0-OpenSSH_9.6\r\n")
                except OSError:
                    pass

    threading.Thread(target=answer, daemon=True).start()
    try:
        yield s.getsockname()[1]
    finally:
        stop.set()
        s.close()
