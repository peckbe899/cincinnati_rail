"""The hub's HTTP server (WP2): ``create_app(store, jobs, engine, cfg)``, the routes of section 5, SSE, the mounted
data tiers and the app, behind the security rules of section 9. ``crhub serve`` (``region.api.serve``) runs it.

``openapi.json`` beside this file is the committed OpenAPI of every route; ``python -m region.api.openapi --write``
regenerates it and ``tests/api/test_serve.py::test_openapi_drift`` fails while it is stale. The app's types
(``app/src/api/gen``) are generated from it with ``npm run gen:api -w app``.

``create_app`` and ``Hub`` are imported on first use, so ``region.api.client`` (standard library only) can be used
without loading FastAPI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import API, create_app
    from .context import Hub

__all__ = ["API", "Hub", "create_app"]


def __getattr__(name: str) -> Any:
    if name in ("API", "create_app"):
        from . import app

        return getattr(app, name)
    if name == "Hub":
        from .context import Hub

        return Hub
    raise AttributeError(f"module 'region.api' has no attribute {name!r}")
