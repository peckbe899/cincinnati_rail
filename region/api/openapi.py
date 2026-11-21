"""The committed OpenAPI of the hub's routes, ``region/api/openapi.json`` (decision 9.21).

    python -m region.api.openapi --write     regenerate the file (after a route changes)
    python -m region.api.openapi --check     exit 1 when the file is stale

The file is generated from the routes FastAPI builds (``create_app`` without a store), feature routers included,
written with sorted keys and LF line endings so it is the same on every machine. ``app/src/api/gen`` is generated
from it (``npm run gen:api -w app``); both have drift tests (``tests/api/test_serve.py::test_openapi_drift`` and the
app's ``test/unit/api_drift.test.ts``), so after a route change run both generators and commit their output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from region.core import fsio

SPEC = Path(__file__).resolve().with_name("openapi.json")


def build() -> dict[str, Any]:
    """The OpenAPI document of every route."""
    from .app import create_app

    return create_app(None, None, None).openapi()


def text() -> str:
    """``build()`` as the committed text."""
    return json.dumps(build(), indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def stale(path: Path = SPEC) -> bool:
    """Whether the committed file differs from what the routes give now."""
    return not path.is_file() or fsio.read_text(path) != text()


def write(path: Path = SPEC) -> Path:
    """Rewrite the file (outside the hub's write roots, so the guard is opened for that one path)."""
    with fsio.allow_writes(path):
        fsio.write_text(path, text())
    return path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m region.api.openapi", description=__doc__.split("\n\n")[0])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="rewrite region/api/openapi.json")
    g.add_argument("--check", action="store_true", help="exit 1 when region/api/openapi.json is stale")
    args = p.parse_args(argv)
    if args.write:
        print(f"wrote {write()}")
        return 0
    if args.check:
        if stale():
            print(f"{SPEC} is stale: run python -m region.api.openapi --write, then npm run gen:api -w app")
            return 1
        print(f"{SPEC} is current")
        return 0
    sys.stdout.write(text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
