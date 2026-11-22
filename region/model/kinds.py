"""Record kinds: load and check the kind YAML files, validate data, derive columns, dates and refs, upgrade data.

A kind file (decision 9.12) is one YAML file per kind: ``region/kinds/<kind>.yaml`` for the core kinds and
``region/ext/<feature>/kinds/<kind>.yaml`` for a feature's. Each is checked by ``region.core.features.check_kind_file``
against ``region/kinds/_meta.schema.json``; ``load`` refuses the whole set when any file has a problem, when two files
declare the same kind, or when a ref names a kind the set does not hold.

    reg = kinds.load()                      # core kinds plus every feature's (region.core.features.kind_files)
    k = reg["section"]
    errors = k.validate(data)               # [{"path": "/data/pvi/3/z_m", "message": ...}]
    data = k.upgrade(data, kv=1)            # up_1, up_2, ... to k.version
    k.columns_of(data)                      # {"name": ..., "c0": ...}: the promoted columns
    k.dates_of(data)                        # ((lo, hi) | None, (lo, hi) | None): month intervals
    k.refs_of(data)                         # [(role, dst id, RefSpec), ...]

**Upgraders.** A kind at version n > 1 needs ``up_1`` to ``up_<n-1>``, each a pure ``up_<i>(data) -> data`` taking
version i to i + 1, in ``upgrade/<kind>.py`` beside the ``kinds/`` folder that holds the kind file
(``region/ext/<feature>/upgrade/<kind>.py``; for core kinds ``region/kinds/upgrade/<kind>.py``).

**Vocabularies.** A string node with ``x-vocab: <list>`` must hold a value of that list of ``region/kinds/_vocab.yaml``;
the store checks this with the JSON Schema validation.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

from region.core import features, fsio, view
from region.core.errors import Invalid, NotFound

MISSING = object()


# ------------------------------------------------------------------------------------------------- JSON pointers


def pointer_parts(pointer: str) -> tuple[str, ...]:
    """The unescaped segments of an RFC 6901 pointer (``"/a~1b/0"`` gives ``("a/b", "0")``)."""
    if pointer == "":
        return ()
    if not pointer.startswith("/"):
        raise Invalid(f"{pointer!r} is not a JSON pointer")
    return tuple(p.replace("~1", "/").replace("~0", "~") for p in pointer[1:].split("/"))


def pointer_get(doc: Any, parts: Iterable[str], default: Any = None) -> Any:
    """The value at ``parts`` in ``doc``, or ``default`` when any step is absent."""
    node = doc
    for part in parts:
        if isinstance(node, dict):
            if part not in node:
                return default
            node = node[part]
        elif isinstance(node, list):
            if not part.isdigit() or int(part) >= len(node):
                return default
            node = node[int(part)]
        else:
            return default
    return node


def pointer_text(parts: Iterable[Any]) -> str:
    """An RFC 6901 pointer from segments."""
    out = "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)
    return out


def _star_walk(node: Any, parts: tuple[str, ...], at: tuple[Any, ...]) -> Iterator[tuple[tuple[Any, ...], Any]]:
    if not parts:
        yield at, node
        return
    head, rest = parts[0], parts[1:]
    if head == "*":
        if isinstance(node, dict):
            for k in sorted(node):
                yield from _star_walk(node[k], rest, at + (k,))
        elif isinstance(node, list):
            for i, item in enumerate(node):
                yield from _star_walk(item, rest, at + (i,))
        return
    if isinstance(node, dict):
        if head in node:
            yield from _star_walk(node[head], rest, at + (head,))
    elif isinstance(node, list) and head.isdigit() and int(head) < len(node):
        yield from _star_walk(node[int(head)], rest, at + (int(head),))


# ----------------------------------------------------------------------------------------------------- the kinds


@dataclass(frozen=True)
class RefSpec:
    """One declared reference of a kind: ``path`` (a pointer with ``*`` segments), the target kinds, the role in the
    ref table, what deleting the target does, and whether a null or absent ref is invalid."""

    path: str
    parts: tuple[str, ...]
    kinds: tuple[str, ...]
    role: str
    on_delete: str
    required: bool = False

    def values(self, data: Any) -> list[tuple[tuple[Any, ...], Any]]:
        """Every ``(location, value)`` the path reaches in ``data`` (a list value counts item by item)."""
        out: list[tuple[tuple[Any, ...], Any]] = []
        for at, value in _star_walk(data, self.parts, ()):
            if isinstance(value, list):
                out.extend((at + (i,), v) for i, v in enumerate(value))
            else:
                out.append((at, value))
        return out


@lru_cache(maxsize=1)
def _validator_class() -> Any:
    from jsonschema import Draft202012Validator, validators
    from jsonschema.exceptions import ValidationError

    vocab = features.load_vocab()

    def x_vocab(validator: Any, name: str, instance: Any, schema: Any) -> Iterator[Any]:
        values = vocab.get(name)
        if isinstance(instance, str) and isinstance(values, list) and instance not in values:
            yield ValidationError(f"{instance!r} is not in the vocabulary {name!r}")

    return validators.extend(Draft202012Validator, {"x-vocab": x_vocab})


@dataclass
class Kind:
    """One record kind as loaded from its file. ``spec`` is the parsed YAML; the rest are its parts, checked."""

    name: str
    version: int
    geometry: str
    schema: dict[str, Any]
    path: Path
    spec: dict[str, Any]
    sha256: str
    feature: str | None = None
    title: str = ""
    description: str = ""
    columns: dict[str, tuple[str, ...]] = field(default_factory=dict)
    dates: dict[str, tuple[str, ...]] = field(default_factory=dict)
    refs: tuple[RefSpec, ...] = ()
    merge_unit: str = "field"
    rebase: str = "auto"
    guard: tuple[tuple[str, ...], ...] = ()
    frame: tuple[str, ...] = ()
    legacy: tuple[str, ...] = ()
    seeded: bool = True
    upgraders: dict[int, Callable[[Any], Any]] = field(default_factory=dict)
    _validator: Any = None

    # ---- validation

    @property
    def validator(self) -> Any:
        if self._validator is None:
            self._validator = _validator_class()(self.schema)
        return self._validator

    def validate(self, data: Any, *, prefix: str = "/data") -> list[dict[str, Any]]:
        """Schema errors of ``data`` as ``{"path", "message"}`` (paths are pointers under ``prefix``)."""
        errors = []
        for err in sorted(self.validator.iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path]):
            errors.append({"path": prefix + pointer_text(err.absolute_path), "message": err.message})
        return errors

    def upgrade(self, data: Any, kv: int) -> Any:
        """``data`` of version ``kv`` taken to the current version through ``up_<kv>`` ... ``up_<version - 1>``."""
        if kv == self.version:
            return data
        if not isinstance(kv, int) or isinstance(kv, bool) or kv < 1 or kv > self.version:
            raise Invalid(
                f"{self.name}: data version {kv!r} is not 1 to {self.version}",
                errors=[{"path": "/kv", "message": f"1 to {self.version}"}],
            )
        for n in range(kv, self.version):
            up = self.upgraders.get(n)
            if up is None:
                raise Invalid(f"{self.name}: no upgrader up_{n} to take data from version {n} to {n + 1}")
            data = up(data)
        return data

    # ---- derived parts

    def columns_of(self, data: Any) -> dict[str, Any]:
        """The promoted columns derived from ``data`` (absent pointers give ``None``)."""
        out: dict[str, Any] = {}
        for col, parts in self.columns.items():
            value = pointer_get(data, parts)
            if col in ("c0", "c1"):
                value = float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
            elif value is not None and not isinstance(value, str):
                value = str(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
            out[col] = value
        return out

    def dates_of(self, data: Any) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
        """The opening and closing month intervals (``None`` for undated). ``Invalid`` for a bad partial date."""
        out: list[tuple[int, int] | None] = []
        for which in ("open", "close"):
            parts = self.dates.get(which)
            if parts is None:
                out.append(None)
                continue
            value = pointer_get(data, parts)
            try:
                out.append(view.date_interval(value))
            except Invalid as e:
                raise Invalid(str(e), errors=[{"path": "/data" + pointer_text(parts), "message": str(e)}]) from None
        return out[0], out[1]

    @property
    def dated(self) -> bool:
        """Whether records of this kind are built things with dates (lists filter them by the view's instant)."""
        return bool(self.dates)

    def refs_of(self, data: Any) -> list[tuple[str, Any, RefSpec, tuple[Any, ...]]]:
        """Every ref in ``data``: ``(role, value, spec, location)``; ``value`` may be ``None`` (a null ref)."""
        out = []
        for spec in self.refs:
            for at, value in spec.values(data):
                out.append((spec.role, value, spec, at))
        return out

    def guard_changed(self, a: Any, b: Any) -> list[str]:
        """The guarded pointers whose values differ between data ``a`` and ``b``."""
        out = []
        for parts in self.guard:
            if pointer_get(a, parts, MISSING) != pointer_get(b, parts, MISSING):
                out.append(pointer_text(parts))
        return out

    def describe(self) -> dict[str, Any]:
        """The kind as served by ``/meta``: its file's members plus where it came from."""
        out = dict(self.spec)
        out["feature"] = self.feature
        out["sha256"] = self.sha256
        return out


class KindRegistry(Mapping[str, Kind]):
    """The loaded kinds by name. ``reg[name]`` raises ``NotFound`` for an unknown kind."""

    def __init__(self, kinds: Iterable[Kind]) -> None:
        self._kinds: dict[str, Kind] = {k.name: k for k in kinds}
        self._lkinds: dict[str, str] = {}
        for k in self._kinds.values():
            for lk in k.legacy:
                self._lkinds.setdefault(lk, k.name)
        self.sha256 = fsio.sha256_hex(
            "\n".join(f"{k.name} {k.sha256}" for k in sorted(self._kinds.values(), key=lambda k: k.name))
        )

    def __getitem__(self, name: str) -> Kind:
        try:
            return self._kinds[name]
        except KeyError:
            raise NotFound(f"unknown kind {name!r}", kind=name) from None

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._kinds))

    def __len__(self) -> int:
        return len(self._kinds)

    def __contains__(self, name: object) -> bool:
        return name in self._kinds

    def get(self, name: str, default: Any = None) -> Any:  # type: ignore[override]
        return self._kinds.get(name, default)

    def names(self) -> list[str]:
        return sorted(self._kinds)

    def for_lkind(self, lkind: str) -> Kind | None:
        """The kind that declares legacy kind ``lkind``, or ``None``."""
        name = self._lkinds.get(lkind)
        return self._kinds[name] if name else None


# ----------------------------------------------------------------------------------------------------------- load


def _files(paths: Iterable[Path] | None) -> list[Path]:
    if paths is None:
        return features.kind_files()
    out: list[Path] = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            out.extend(sorted(f for f in p.glob("*.yaml") if not f.name.startswith(("_", "."))))
        else:
            out.append(p)
    return out


def _feature_of(path: Path) -> str | None:
    folder = path.resolve().parent
    if folder == features.CORE_KINDS.resolve():
        return None
    if folder.name == "kinds" and folder.parent.parent.resolve() == features.EXT_ROOT.resolve():
        return folder.parent.name
    if folder.name == "kinds":
        return folder.parent.name
    return None


def _load_module(path: Path) -> ModuleType:
    name = "_crkind_up_" + fsio.sha256_hex(str(path.resolve()))[:16]
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Invalid(f"cannot import upgrader {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def upgrader_file(path: Path, kind: str) -> Path | None:
    """The upgrade module of ``kind`` for the kind file at ``path``, or ``None``."""
    folder = Path(path).resolve().parent
    for up in (folder.parent / "upgrade" / f"{kind}.py", folder / "upgrade" / f"{kind}.py"):
        if up.is_file():
            return up
    return None


def _upgraders(path: Path, kind: str, feature: str | None) -> dict[int, Callable[[Any], Any]]:
    up = upgrader_file(path, kind)
    if up is None:
        return {}
    module: ModuleType | None = None
    if feature is not None and up.resolve().parent.parent.parent == features.EXT_ROOT.resolve():
        for f in features.discover():
            if f.name == feature:
                module = f.upgrader(kind)
    if module is None:
        module = _load_module(up)
    out: dict[int, Callable[[Any], Any]] = {}
    for attr in dir(module):
        if attr.startswith("up_") and attr[3:].isdigit() and callable(getattr(module, attr)):
            out[int(attr[3:])] = getattr(module, attr)
    return out


def load_file(path: Path) -> Kind:
    """One kind file, checked (``Invalid`` listing every problem)."""
    path = Path(path)
    problems = features.check_kind_file(path)
    if problems:
        raise Invalid(
            f"kind file {path} is invalid: " + "; ".join(problems),
            errors=[{"path": str(path), "message": p} for p in problems],
        )
    raw = path.read_bytes()
    doc = fsio.read_yaml(path)
    name = doc["kind"]
    feature = _feature_of(path)
    refs = []
    for r in doc.get("refs") or []:
        parts = pointer_parts(r["path"])
        role = r.get("role") or next((p for p in reversed(parts) if p != "*"), parts[-1])
        kinds = (r["kind"],) if isinstance(r["kind"], str) else tuple(r["kind"])
        refs.append(RefSpec(r["path"], parts, kinds, role, r["on_delete"], bool(r.get("required", False))))
    merge = doc.get("merge") or {}
    kind = Kind(
        name=name,
        version=int(doc["version"]),
        geometry=doc["geometry"],
        schema=doc["schema"],
        path=path.resolve(),
        spec=doc,
        sha256=fsio.sha256_hex(raw.replace(b"\r\n", b"\n")),
        feature=feature,
        title=str(doc.get("title", "")),
        description=str(doc.get("description", "")),
        columns={c: pointer_parts(p) for c, p in (doc.get("columns") or {}).items()},
        dates={w: pointer_parts(p) for w, p in (doc.get("dates") or {}).items()},
        refs=tuple(refs),
        merge_unit=merge.get("unit", "field"),
        rebase=merge.get("rebase", "auto"),
        guard=tuple(pointer_parts(p) for p in merge.get("guard") or []),
        frame=tuple(merge.get("frame") or ()),
        legacy=tuple(doc.get("legacy") or ()),
        seeded=bool(doc.get("seeded", True)),
    )
    kind.upgraders = _upgraders(path, name, feature)
    return kind


def load(paths: Iterable[Path] | None = None) -> KindRegistry:
    """Every kind of ``paths`` (kind files, or folders of them; default: the core kinds and every feature's).

    Raises ``Invalid`` listing every problem: invalid files, a kind declared twice, a ref to a kind not in the set,
    a missing upgrader.
    """
    problems: list[dict[str, Any]] = []
    loaded: dict[str, Kind] = {}
    for f in _files(paths):
        try:
            k = load_file(f)
        except Invalid as e:
            problems.extend(e.errors or [{"path": str(f), "message": str(e)}])
            continue
        if k.name in loaded:
            problems.append({"path": str(f), "message": f"kind {k.name!r} is also declared by {loaded[k.name].path}"})
            continue
        loaded[k.name] = k
    for k in loaded.values():
        for r in k.refs:
            for target in r.kinds:
                if target not in loaded:
                    problems.append({"path": str(k.path), "message": f"ref {r.path} names unknown kind {target!r}"})
        for n in range(1, k.version):
            if n not in k.upgraders:
                problems.append(
                    {"path": str(k.path), "message": f"version {k.version} needs up_{n} in upgrade/{k.name}.py"}
                )
    if problems:
        raise Invalid("kind files are invalid: " + "; ".join(p["message"] for p in problems), errors=problems)
    return KindRegistry(loaded.values())


__all__ = [
    "Kind",
    "KindRegistry",
    "MISSING",
    "RefSpec",
    "load",
    "load_file",
    "pointer_get",
    "pointer_parts",
    "pointer_text",
    "upgrader_file",
]
