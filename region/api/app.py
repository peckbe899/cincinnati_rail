"""``create_app(store, jobs, engine, cfg) -> FastAPI``: the hub's HTTP server (WP2, section 5).

    app = create_app(store, scheduler, pool, paths.config())

The app does not own its parts: ``crhub serve`` (``region.api.serve``) opens the store, starts the scheduler and the
engine pool, and stops them after the server ends. The app's lifespan starts and stops only the ``EventHub`` (the
outbox tailer behind SSE).

Layout, in matching order:

1. ``/api/v1/...``: meta, records, changesets, layers and conflicts, importers, jobs and results, the live hub,
   events, ops, tiers and the mounted data tiers
   (``region/api/{meta,records,changesets,layers,imports,jobs,live,events,ops,files}.py``);
2. ``/api/v1/x/<feature>/...``: the ``router`` of each feature folder that has a ``router.py``
   (``region.core.features.discover``); a router that fails to load is logged and left out, so one broken feature
   does not stop the hub;
3. the app (``app/dist``) at ``/``.

Middleware, outermost first: ``security.Guard`` (host allowlist, origin, write headers, body cap, the CSP and the
other headers, request ids, and a 500 problem for a bug), then gzip (``http.NO_GZIP`` types are left alone, as are
ranges and SSE).

``cfg`` is the merged config (``region.core.paths.config()``), whose ``tiers`` the files and tier routes read, plus
optional members: ``app_dist`` (a folder to serve as the app), ``user`` (the default ``by``), ``body_cap_mb``,
``old_hub`` and ``events`` (``poll_s``, ``heartbeat_s``, ``queue``, ``tiers_s``).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.gzip import GZipMiddleware

from region.core import features, paths

from . import changesets, events, files, imports, jobs, layers, live, meta, ops, problem, records
from .context import Hub
from .http import NO_GZIP
from .security import Guard

log = logging.getLogger("region.api")

API = "/api/v1"
TITLE = "Cincinnati Rail hub"
API_VERSION = "1"


def operation_id(route: APIRoute) -> str:
    """OpenAPI operation ids from the route functions' names (``list_records``), prefixed ``x_<feature>_`` for a
    feature's routes, so the app's generated types read well."""
    path = route.path_format
    prefix = ""
    if path.startswith(f"{API}/x/"):
        prefix = "x_" + path[len(API) + 3 :].split("/", 1)[0] + "_"
    return prefix + route.name


def mount_features(app: FastAPI, hub: Hub) -> list[dict[str, Any]]:
    """Include every feature's ``router`` under ``/api/v1/x/<feature>``; return what was found.

    ``router`` is a FastAPI ``APIRouter``, or a callable that takes the ``Hub`` and returns one."""
    found = []
    try:
        discovered = features.discover()
    except Exception:
        log.exception("features: discovery failed; no feature routes are mounted")
        return found
    for f in discovered:
        entry: dict[str, Any] = {"name": f.name, "modules": list(f.modules), "router": False}
        if f.has("router"):
            try:
                r = f.router()
                if r is not None and not isinstance(r, APIRouter) and callable(r):
                    r = r(hub)
                if isinstance(r, APIRouter):
                    app.include_router(r, prefix=f"{API}/x/{f.name}")
                    entry["router"] = True
                elif r is not None:
                    log.error("feature %s: router.py's router is not an APIRouter; left out", f.name)
            except Exception as e:
                log.exception("feature %s: router.py failed to load; its routes are left out", f.name)
                entry["error"] = f"{type(e).__name__}: {e}"
        found.append(entry)
    return found


def create_app(store: Any, jobs_: Any, engine: Any, cfg: dict[str, Any] | None = None) -> FastAPI:
    """The FastAPI app over ``store`` (a ``region.model.SqliteStore``), ``jobs_`` (a ``region.jobs.Scheduler``) and
    ``engine`` (an ``EngineClient`` or ``None``). See the module doc."""
    cfg = dict(cfg) if cfg is not None else paths.config()
    hub = Hub(store=store, jobs=jobs_, engine=engine, cfg=cfg, user=str(cfg.get("user") or "ben"))
    ev_cfg = cfg.get("events") or {}
    hub.events = events.EventHub(
        hub,
        poll_s=float(ev_cfg.get("poll_s", 0.5)),
        heartbeat_s=float(ev_cfg.get("heartbeat_s", 15.0)),
        queue_size=int(ev_cfg.get("queue", 2000)),
        tiers_s=float(ev_cfg.get("tiers_s", 60.0)),
    )
    hub.app = dict(cfg.get("_app") or {})

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if hub.store is not None:
            hub.events.start(asyncio.get_running_loop())
        try:
            yield
        finally:
            hub.events.stop()

    app = FastAPI(
        title=TITLE,
        version=API_VERSION,
        description="The hub's API (section 5 of claude/Hub_Region_Architecture.md). Errors are RFC 9457 problems.",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=f"{API}/openapi.json",
        generate_unique_id_function=operation_id,
    )
    app.state.hub = hub
    # the hub's parts by name too, for feature routers (region/ext/profiles/router.py reads app.state.store)
    app.state.store = store
    app.state.jobs = jobs_
    app.state.engine = engine
    app.state.cfg = cfg
    problem.install(app)
    for module in (meta, records, changesets, layers, imports, jobs, live, events, ops, files):
        app.include_router(module.router, prefix=API)
    hub.features = mount_features(app, hub)
    app.include_router(files.app_router)
    app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6, exclude_content_types=NO_GZIP)
    cap = int(float(cfg.get("body_cap_mb", 32)) * 1024 * 1024)
    app.add_middleware(Guard, body_cap=cap)
    return app


__all__ = ["API", "create_app", "mount_features"]
