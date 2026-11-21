"""Feature folders and their discovery (decision 9.12): every way of growing the hub is a folder.

A feature is a folder ``region/ext/<feature>/`` (a lowercase identifier: it is also the URL segment
``/api/v1/x/<feature>/`` and the app plugin id ``app/src/plugins/<feature>/``). Every part is optional:

=========================  =========================================================================================
``kinds/<kind>.yaml``      record kinds, each valid against ``region/kinds/_meta.schema.json`` (``check_kind``)
``upgrade/<kind>.py``      pure upgraders ``up_<n>(data) -> data`` taking kind version n to n + 1
``importers.py``           ``IMPORTERS: list[Importer]``
``jobs.py``                ``JOB_TYPES: list[JobType]``
``router.py``              ``router``: a FastAPI ``APIRouter``, mounted under ``/api/v1/x/<feature>/``
``validators.py``          ``VALIDATORS: dict[kind, Validator]`` (``region.core.protocols.Validator``)
``sources.py``             ``SOURCES: dict[name, uri]``: the data files and tiers the feature reads, listed by doctor
=========================  =========================================================================================

``discover()`` only walks folders and imports nothing; a ``Feature`` imports a module when asked. Core kinds (not of
any feature) live in ``region/kinds/<kind>.yaml``; ``kind_files()`` lists them together with every feature's.
Files and folders whose names start with ``_`` or ``.`` are ignored everywhere.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.machinery
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

from .errors import Invalid

REGION = Path(__file__).resolve().parents[1]
EXT_ROOT = REGION / "ext"
CORE_KINDS = REGION / "kinds"
META_SCHEMA = CORE_KINDS / "_meta.schema.json"
VOCAB = CORE_KINDS / "_vocab.yaml"
FEATURE_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")

MODULES: tuple[str, ...] = ("importers", "jobs", "router", "validators", "sources")
EXPORTS: dict[str, str] = {
    "importers": "IMPORTERS",
    "jobs": "JOB_TYPES",
    "router": "router",
    "validators": "VALIDATORS",
    "sources": "SOURCES",
}


def _visible(p: Path) -> bool:
    return not p.name.startswith(("_", "."))


@dataclass(frozen=True)
class Feature:
    """One feature folder as found on disk. Loading a part imports ``<package>.<module>`` on demand."""

    name: str
    path: Path
    package: str
    kinds: tuple[Path, ...]
    upgraders: tuple[tuple[str, Path], ...]
    modules: tuple[str, ...]

    def has(self, module: str) -> bool:
        """Whether the folder has ``<module>.py``."""
        return module in self.modules

    def load(self, module: str) -> ModuleType:
        """Import one of the feature's modules (``"jobs"``, ``"inputs"``, or any other module of the folder)."""
        return importlib.import_module(f"{self.package}.{module}")

    def _export(self, module: str, default: Any) -> Any:
        if not self.has(module):
            return default
        mod = self.load(module)
        name = EXPORTS[module]
        if not hasattr(mod, name):
            raise Invalid(f"feature {self.name}: {module}.py defines no {name}")
        return getattr(mod, name)

    def importers(self) -> list[Any]:
        """``IMPORTERS`` of ``importers.py`` (empty without one)."""
        return list(self._export("importers", []))

    def job_types(self) -> list[Any]:
        """``JOB_TYPES`` of ``jobs.py`` (empty without one)."""
        return list(self._export("jobs", []))

    def router(self) -> Any | None:
        """``router`` of ``router.py``, or ``None``."""
        return self._export("router", None)

    def validators(self) -> dict[str, Any]:
        """``VALIDATORS`` of ``validators.py`` (empty without one)."""
        return dict(self._export("validators", {}))

    def sources(self) -> dict[str, str]:
        """``SOURCES`` of ``sources.py`` (empty without one)."""
        return dict(self._export("sources", {}))

    def upgrader(self, kind: str) -> ModuleType | None:
        """The upgrade module of ``kind`` (``upgrade/<kind>.py``), or ``None``."""
        for name, _ in self.upgraders:
            if name == kind:
                return importlib.import_module(f"{self.package}.upgrade.{kind}")
        return None


def _package_for(root: Path) -> str:
    """The import name of a features root: ``region.ext`` for the repo's, a synthetic namespace package otherwise."""
    if root.resolve() == EXT_ROOT.resolve():
        return "region.ext"
    name = "_crext_" + hashlib.sha1(str(root.resolve()).encode("utf-8")).hexdigest()[:12]
    if name not in sys.modules:
        spec = importlib.machinery.ModuleSpec(name, None, is_package=True)
        spec.submodule_search_locations = [str(root)]
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
    return name


def discover(root: Path | None = None) -> list[Feature]:
    """Every feature folder under ``root`` (default ``region/ext``), sorted by name. A missing root gives ``[]``.

    Raises ``Invalid`` for a visible folder whose name is not a lowercase identifier.
    """
    root = Path(root) if root is not None else EXT_ROOT
    if not root.is_dir():
        return []
    package = _package_for(root)
    found = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and _visible(p)):
        if not FEATURE_RE.match(folder.name):
            raise Invalid(f"feature folder {folder} is not a lowercase identifier (a-z, 0-9, _)")
        kinds_dir = folder / "kinds"
        kinds = tuple(sorted(p for p in kinds_dir.glob("*.yaml") if _visible(p))) if kinds_dir.is_dir() else ()
        up_dir = folder / "upgrade"
        upgraders = tuple((p.stem, p) for p in sorted(up_dir.glob("*.py")) if _visible(p)) if up_dir.is_dir() else ()
        modules = tuple(m for m in MODULES if (folder / f"{m}.py").is_file())
        found.append(Feature(folder.name, folder, f"{package}.{folder.name}", kinds, upgraders, modules))
    return found


def kind_files(root: Path | None = None, core: Path | None = None) -> list[Path]:
    """Every kind file: the core kinds of ``region/kinds`` then each feature's, in discovery order."""
    core = Path(core) if core is not None else CORE_KINDS
    files = sorted(p for p in core.glob("*.yaml") if _visible(p)) if core.is_dir() else []
    for feature in discover(root):
        files.extend(feature.kinds)
    return files


# ----------------------------------------------------------------------------------------------- kind meta-schema


@lru_cache(maxsize=1)
def load_meta_schema() -> dict[str, Any]:
    """``region/kinds/_meta.schema.json``."""
    with open(META_SCHEMA, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_vocab() -> dict[str, Any]:
    """``region/kinds/_vocab.yaml``: ``units`` (a dict unit -> meaning) and the closed lists."""
    import yaml

    with open(VOCAB, encoding="utf-8-sig") as f:
        return yaml.safe_load(f)


def _walk(node: Any, path: str, out: list[tuple[str, dict[str, Any]]]) -> None:
    if isinstance(node, dict):
        out.append((path, node))
        for key, value in node.items():
            if key in ("properties", "patternProperties", "$defs", "dependentSchemas") and isinstance(value, dict):
                for name, sub in value.items():
                    _walk(sub, f"{path}/{key}/{name}", out)
            elif key in ("allOf", "anyOf", "oneOf", "prefixItems") and isinstance(value, list):
                for i, sub in enumerate(value):
                    _walk(sub, f"{path}/{key}/{i}", out)
            elif key in (
                "items",
                "additionalProperties",
                "unevaluatedProperties",
                "propertyNames",
                "unevaluatedItems",
                "contains",
                "not",
                "if",
                "then",
                "else",
            ):
                _walk(value, f"{path}/{key}", out)


def check_kind(doc: Any, *, name: str | None = None) -> list[str]:
    """Every problem with a kind document (parsed YAML), as plain strings; ``[]`` when it is valid.

    Checks the meta-schema, that ``schema`` is a valid JSON Schema 2020-12, every ``x-unit`` and ``x-vocab`` against
    the vocabulary, and, when ``name`` is given (the file stem), that ``kind`` equals it.
    """
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError

    problems: list[str] = []
    meta = Draft202012Validator(load_meta_schema())
    for err in sorted(meta.iter_errors(doc), key=lambda e: list(map(str, e.absolute_path))):
        where = "/" + "/".join(str(p) for p in err.absolute_path)
        problems.append(f"{where}: {err.message}")
    if not isinstance(doc, dict):
        return problems or ["a kind file holds a mapping"]
    if name is not None and doc.get("kind") != name:
        problems.append(f"/kind: {doc.get('kind')!r} differs from the file name {name!r}")
    schema = doc.get("schema")
    if isinstance(schema, (dict, bool)):
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as e:
            problems.append(f"/schema: not a valid JSON Schema 2020-12: {e.message}")
    vocab = load_vocab()
    nodes: list[tuple[str, dict[str, Any]]] = []
    _walk(schema, "/schema", nodes)
    for where, node in nodes:
        unit = node.get("x-unit")
        if unit is not None and unit not in vocab["units"]:
            problems.append(f"{where}: x-unit {unit!r} is not a unit of region/kinds/_vocab.yaml")
        vname = node.get("x-vocab")
        if vname is not None and not isinstance(vocab.get(vname), list):
            problems.append(f"{where}: x-vocab {vname!r} is not a list of region/kinds/_vocab.yaml")
    return problems


def check_kind_file(path: Path) -> list[str]:
    """``check_kind`` of a kind YAML file, with the file name as the expected kind."""
    import yaml

    try:
        with open(path, encoding="utf-8-sig") as f:
            doc = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"not valid YAML: {e}"]
    return check_kind(doc, name=Path(path).stem)


__all__ = [
    "CORE_KINDS",
    "EXPORTS",
    "EXT_ROOT",
    "FEATURE_RE",
    "Feature",
    "META_SCHEMA",
    "MODULES",
    "VOCAB",
    "check_kind",
    "check_kind_file",
    "discover",
    "kind_files",
    "load_meta_schema",
    "load_vocab",
]
