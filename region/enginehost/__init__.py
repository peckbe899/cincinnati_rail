"""The engine host (WP4): Python's clients of the TypeScript engine and its build hash (decision 9.20).

    from region.enginehost import Pool, OneShot, Fake, engine_build

    with Pool(size=2, timeout_s=30) as engine:
        engine.hello()                                   # {"engine_version", "engine_build", "contracts", "methods"}
        out = engine.call("vertical.rail", section_input) # VerticalRail v0

Each client implements ``region.core.protocols.EngineClient``. See ``client.py`` for the three, ``build.py`` for the
build hash, Node and the contract majors, ``codegen.py`` for ``region/contract/gen``, and ``engine/PROTOCOL.md`` for
the wire protocol.
"""

from .build import engine_build
from .client import Fake, OneShot, Pool

__all__ = ["Fake", "OneShot", "Pool", "engine_build"]
