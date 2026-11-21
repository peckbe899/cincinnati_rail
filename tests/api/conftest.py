"""Fixtures for the server's tests: a real store, scheduler and fake engine behind ``create_app``.

- ``api``: an ``Api`` holding the store (core kinds plus the store tests' fixture kinds), a scheduler on the test's
  own cache, a ``Fake`` engine, and a config whose data tiers are folders of the test (``files`` mounted, ``hidden``
  not) and whose app is ``tmp/dist``. ``api.app(**cfg)`` makes an app over them.
- ``client``: a ``TestClient`` of that app (its lifespan running), sending ``Host: 127.0.0.1:8766``.
- ``live``: the app served by uvicorn on a free port in a thread, for SSE (``live.url``).
- ``H``: the headers of a write (``X-CR-Client`` and a JSON content type).
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from region.core import features, paths

FIXTURE_KINDS = Path(__file__).resolve().parents[1] / "model" / "fixtures" / "kinds"
KINDS = [features.CORE_KINDS, FIXTURE_KINDS]
BASE = "http://127.0.0.1:8766"
H = {"X-CR-Client": "test-tab", "Content-Type": "application/json"}


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass
class Api:
    root: Path
    store: Any
    jobs: Any
    engine: Any
    cfg: dict[str, Any]
    apps: list[Any] = field(default_factory=list)

    def app(self, **over: Any) -> Any:
        from region.api import create_app

        app = create_app(self.store, self.jobs, self.engine, {**self.cfg, **over})
        self.apps.append(app)
        return app

    def note(self, text: str = "a", layer: str = "main") -> dict[str, Any]:
        from region.core.view import View

        return self.store.put({"kind": "note", "id": None, "data": {"text": text}, "geom": None}, View(layer=layer),
                              if_match=None, by="test")


@pytest.fixture
def api(hub_var: Path, tmp_path: Path) -> Iterator[Api]:
    from region.enginehost import Fake
    from region.jobs.scheduler import Scheduler
    from region.model import open_store
    from tests.api import jobtypes

    store = open_store(hub_var / "region.db", kinds_paths=KINDS)
    jobs = Scheduler(store, hub_var / "cache" / "cache.db", None, registry=jobtypes.registry(), poll_s=0.05).start()
    files = tmp_path / "tier_files"
    hidden = tmp_path / "tier_hidden"
    files.mkdir()
    hidden.mkdir()
    cfg = {
        **paths.config(),
        "tiers": {
            "files": {"root": str(files), "mount": True, "lane": "B"},
            "hidden": {"root": str(hidden), "mount": False, "lane": "B"},
            "gone": {"root": str(tmp_path / "absent"), "mount": True, "lane": "B"},
        },
        "app_dist": str(tmp_path / "dist"),
        "events": {"poll_s": 0.1, "heartbeat_s": 0.5, "tiers_s": 3600},
    }
    a = Api(tmp_path, store, jobs, Fake(), cfg)
    yield a
    jobs.stop()
    store.close()


@pytest.fixture
def client(api: Api) -> Iterator[Any]:
    from fastapi.testclient import TestClient

    with TestClient(api.app(), base_url=BASE) as c:
        yield c


class Live:
    """An app served by uvicorn on a free port, in a thread."""

    def __init__(self, app: Any) -> None:
        import uvicorn

        self.app = app
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        config = uvicorn.Config(
            app, host="127.0.0.1", port=self.port, log_level="warning", lifespan="on", ws="none", http="h11",
            loop="asyncio", timeout_graceful_shutdown=2,
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 20
        while not self.server.started:
            assert time.monotonic() < deadline, "the live server did not start"
            time.sleep(0.01)

    def stop(self) -> None:
        self.app.state.hub.events.close_streams()
        self.server.should_exit = True
        self.thread.join(timeout=20)


@pytest.fixture
def live(api: Api) -> Iterator[Live]:
    server = Live(api.app())
    yield server
    server.stop()
