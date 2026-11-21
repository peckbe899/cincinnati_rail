"""``seed.import`` and ``seed.export``: the seeds of ``region/seed`` as jobs (decisions 9.24 and 9.29).

Both change the truth (records, or the seed files), so they use the one sanctioned way a job may: ``effect =
"truth"`` with an ``apply`` step. ``plan`` and ``run`` stay as pure as any job's: ``plan`` reads the seed files (each
a ``file:`` ref) and, for an export, every record of a seeded kind (``rec:`` refs) and the kind files that say which
kinds are seeded; ``run`` only counts. After the run the scheduler re-plans, and only when the key is unchanged
does it call ``apply``, which hands the real work to the store package (``region.model.seed.import_seed`` and
``region.model.seed.export``). A repeat with nothing changed is a cache hit and writes nothing.

The scope is the layer: ``main``, ``proposal:<slug>`` or ``all``. A seed import of ``all`` imports every seeded
layer folder; an export always writes every seeded layer, as ``region.model.seed.export`` does, so every export scope
plans the same reads and shares one result. Neither job puts the scope in its inputs: the key does not hold the scope,
so the output may depend only on what the plan read. ``apply`` gets the scope from the scheduler.

**A known limit of ``seed.export``.** A plan reads through one view (``PlanCtx``), so the export's key covers the seed
files and the seeded records as the job's view resolves them, while ``region.model.seed.export`` writes every seeded
layer. A change made only in a proposal layer therefore leaves the key of an export in ``main`` unchanged, and that
export is a cache hit that writes nothing. Submit the export in the proposal's own view (its chain includes main) to
export after a proposal edit, or call ``region.model.seed.export`` directly, as ``crhub model export`` does.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from region.core import features, fsio, paths
from region.core.errors import Invalid
from region.core.protocols import Output, PlanCtx, RunCtx, Store
from region.core.view import View

SEED_URI = "repo://region/seed"


def _folder_uri(base: str, scope_id: str) -> str:
    if scope_id in ("all", ""):
        return base
    if scope_id == "main":
        return f"{base}/main"
    tier, sep, slug = scope_id.partition(":")
    if tier == "proposal" and sep and slug:
        return f"{base}/proposals/{slug}"
    raise Invalid(f"seed jobs take the scope main, proposal:<slug> or all, not {scope_id!r}")


def _seed_files(ctx: PlanCtx, base: str, scope_id: str) -> list[str]:
    """Read every file of the scope's seed folder through ``ctx.file``; return their URIs, sorted.

    The folder itself is read too (a ``file:`` ref whose hash is ``None``): a key holds what the plan read and not
    the scope, so without it two scopes whose folders hold the same files (both empty, say) would share one result,
    and the second import would never be applied."""
    folder_uri = _folder_uri(base, scope_id)
    root = ctx.file(folder_uri)
    found: list[str] = []
    if root.is_dir():
        for p in sorted(root.rglob("*")):
            if p.is_file() and not p.name.startswith("."):
                uri = f"{folder_uri}/{p.relative_to(root).as_posix()}"
                ctx.file(uri)
                found.append(uri)
    return found


def _seeded_kinds(ctx: PlanCtx) -> list[str]:
    """The kinds whose kind file says ``seeded: true`` (each kind file read through ``ctx.file``)."""
    kinds = []
    for f in features.kind_files():
        local = ctx.file(paths.to_uri(f))
        doc = fsio.read_yaml(local) or {}
        if isinstance(doc, dict) and doc.get("seeded") is True and isinstance(doc.get("kind"), str):
            kinds.append(doc["kind"])
    return sorted(kinds)


class _SeedJob:
    version = "1"
    scope = "layer"
    host = "thread"
    priority = 5
    timeout_s = 600.0
    effect = "truth"

    def __init__(self, seed_api: Any = None, seed_uri: str = SEED_URI) -> None:
        self._api = seed_api
        self.seed_uri = seed_uri

    def api(self) -> Any:
        """The store package's seed module (``region.model.seed``), imported when first needed."""
        if self._api is None:
            self._api = importlib.import_module("region.model.seed")
        return self._api

    def root(self) -> Path:
        """The local seed folder (``region/seed``)."""
        return paths.resolve(self.seed_uri)

    def run(self, inputs: dict[str, Any], rt: RunCtx) -> Output:
        return Output(meta={k: (len(v) if isinstance(v, list) else v) for k, v in inputs.items()})


class SeedImport(_SeedJob):
    name = "seed.import"

    def plan(self, ctx: PlanCtx, scope_id: str) -> dict[str, Any]:
        return {"files": _seed_files(ctx, self.seed_uri, scope_id)}

    def apply(self, store: Store, scope_id: str, view: View, output: Output) -> dict[str, Any]:
        layer = None if scope_id in ("all", "") else scope_id
        return dict(self.api().import_seed(store, self.root(), layer=layer) or {})


class SeedExport(_SeedJob):
    name = "seed.export"

    def plan(self, ctx: PlanCtx, scope_id: str) -> dict[str, Any]:
        files = _seed_files(ctx, self.seed_uri, "all")
        records = []
        for kind in _seeded_kinds(ctx):
            records += [r["id"] for r in ctx.list(kind)]
        return {"files": files, "records": records}

    def apply(self, store: Store, scope_id: str, view: View, output: Output) -> dict[str, Any]:
        return dict(self.api().export(store, self.root()) or {})


SEED_IMPORT = SeedImport()
SEED_EXPORT = SeedExport()
JOB_TYPES = [SEED_IMPORT, SEED_EXPORT]
