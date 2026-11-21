"""Kind files: every one valid, every one usable by the store, and upgraders that reach the current version."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from region.core import features
from region.core.errors import Invalid
from region.core.view import View
from region.model import kinds as K
from region.model.refs import set_at
from tests.model.conftest import FIXTURES, KINDS
from tests.model.helpers import tag

GEOMS = {
    "none": None,
    "any": "POINT (715000 4331000)",
    "Point": "POINT (715000 4331000)",
    "LineString": "LINESTRING (715000 4331000, 715100 4331000)",
    "Polygon": "POLYGON ((715000 4331000, 715100 4331000, 715100 4331100, 715000 4331000))",
    "MultiPoint": "MULTIPOINT ((715000 4331000), (715100 4331000))",
    "MultiLineString": "MULTILINESTRING ((715000 4331000, 715100 4331000), (715000 4331100, 715100 4331100))",
    "MultiPolygon": "MULTIPOLYGON (((715000 4331000, 715100 4331000, 715100 4331100, 715000 4331000)))",
}


def test_every_kind_file_is_valid(tmp_path):
    files = features.kind_files()
    names = {p.stem for p in files}
    assert {"authority", "waiver", "feature", "note"} <= names
    for f in files + sorted((FIXTURES / "kinds").glob("*.yaml")):
        assert features.check_kind_file(f) == [], f
    reg = K.load()
    assert sorted(reg) == sorted(names)
    fixture = K.load(KINDS)
    assert fixture["t_section"].refs[0].on_delete == "restrict" and fixture["t_stop"].feature == "fixtures"
    # the set is refused whole when one file is bad, or a ref names a kind the set lacks
    import yaml

    bad = {
        "kind": "t_bad",
        "version": 1,
        "geometry": "none",
        "schema": {"type": "object"},
        "refs": [{"path": "/x", "kind": "nowhere", "on_delete": "restrict"}],
    }
    (tmp_path / "t_bad.yaml").write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(Invalid, match="unknown kind 'nowhere'"):
        K.load([features.CORE_KINDS, tmp_path])
    unitless = {**bad, "refs": [], "schema": {"type": "object", "properties": {"n": {"type": "number"}}}}
    (tmp_path / "t_bad.yaml").write_text(yaml.safe_dump(unitless), encoding="utf-8")
    with pytest.raises(Invalid, match="x-unit"):
        K.load([tmp_path])
    (tmp_path / "t_bad.yaml").write_text(yaml.safe_dump({**bad, "refs": []}), encoding="utf-8")
    (tmp_path / "t_bad2.yaml").write_text(yaml.safe_dump({**bad, "refs": []}), encoding="utf-8")
    with pytest.raises(Invalid, match="differs from the file name"):
        K.load([tmp_path])


# ---------------------------------------------------------------------------------------- a generic round trip


def _synth(node: Any, root: dict[str, Any], vocab: dict[str, Any]) -> Any:
    """A small instance of a JSON Schema node: its first example, else the simplest value it admits."""
    if node is True or node == {} or node is None:
        return None
    if "$ref" in node:
        ref = node["$ref"]
        assert ref.startswith("#/"), f"only local refs: {ref}"
        target: Any = root
        for part in ref[2:].split("/"):
            target = target[part]
        return _synth(target, root, vocab)
    if node.get("examples"):
        return copy.deepcopy(node["examples"][0])
    for key in ("const", "default"):
        if key in node:
            return copy.deepcopy(node[key])
    if node.get("enum"):
        return node["enum"][0]
    for key in ("anyOf", "oneOf", "allOf"):
        if node.get(key):
            return _synth(node[key][0], root, vocab)
    t = node.get("type")
    if isinstance(t, list):
        t = "null" if "null" in t else t[0]
    if t == "null":
        return None
    if t == "object" or (t is None and "properties" in node):
        props = node.get("properties") or {}
        return {p: _synth(props.get(p, {}), root, vocab) for p in node.get("required") or []}
    if t == "array":
        return [_synth(node.get("items", {}), root, vocab) for _ in range(node.get("minItems", 0))]
    if t == "string":
        if node.get("x-vocab"):
            return vocab[node["x-vocab"]][0]
        return "x" * max(1, node.get("minLength", 1))
    if t == "integer":
        return int(node.get("minimum", 0))
    if t == "number":
        return float(node.get("minimum", 0))
    if t == "boolean":
        return False
    return None


def _make(store, reg: K.KindRegistry, name: str, depth: int = 0) -> dict[str, Any]:
    assert depth < 6, f"refs from {name} do not bottom out"
    k = reg[name]
    data = _synth(k.schema, k.schema, features.load_vocab())
    assert isinstance(data, dict), f"{name}: no object instance; give its schema an examples list"
    for spec in k.refs:
        for at, value in spec.values(data):
            if value is not None or spec.required:
                target = _make(store, reg, spec.kinds[0], depth + 1)
                data = set_at(data, at, target["id"]) if at else data
    for spec in k.refs:
        if spec.required and not spec.values(data):
            target = _make(store, reg, spec.kinds[0], depth + 1)
            data = set_at(data, spec.parts, target["id"]) if "*" not in spec.parts else data
    return store.put(
        {"kind": name, "id": None, "data": data, "geom": GEOMS[k.geometry]}, View(), if_match=None, by="round-trip"
    )


def _mutation(k: K.Kind, data: dict[str, Any]) -> list[dict[str, Any]] | None:
    props = (k.schema.get("properties") or {}) if isinstance(k.schema, dict) else {}
    for name in sorted(data):
        node = props.get(name) or {}
        t = node.get("type")
        types = t if isinstance(t, list) else [t]
        plain = not any(key in node for key in ("enum", "const", "pattern", "x-vocab", "format", "maxLength"))
        if "string" in types and plain and isinstance(data[name], str):
            return [{"op": "replace", "path": f"/data/{name}", "value": data[name] + " (edited)"}]
        if "number" in types and isinstance(data[name], (int, float)) and "maximum" not in node:
            return [{"op": "replace", "path": f"/data/{name}", "value": float(data[name]) + 1.5}]
    return None


def test_every_kind_round_trips_through_the_store(make_store):
    reg = K.load()
    store = make_store(kinds_paths=None, validators={})
    for name in reg:
        k = reg[name]
        rec = _make(store, reg, name)
        assert store.get(name, rec["id"], View()) == rec, name
        patch = _mutation(k, rec["data"])
        if patch is None:
            same = store.patch(
                name,
                rec["id"],
                [{"op": "test", "path": "/data", "value": rec["data"]}],
                View(),
                if_match=tag(rec),
                by="round-trip",
            )
            assert same["version"] == 1, name
            edited = same
        else:
            edited = store.patch(name, rec["id"], patch, View(), if_match=tag(rec), by="round-trip")
            assert edited["version"] == 2 and edited["data"] != rec["data"], name
        listed = store.list(name, View(), ids=[rec["id"]])[0]
        if not k.dated:
            assert listed == [edited], name
        gone = store.delete(name, rec["id"], View(), if_match=tag(edited), by="round-trip")
        hist = store.history(name, rec["id"], View())
        assert hist[0] == gone and hist[-1] == rec and gone["data"] == edited["data"], name


def test_upgraders_reach_current_version(make_store, tmp_path):
    for reg in (K.load(), K.load(KINDS)):
        for name in reg:
            k = reg[name]
            assert sorted(k.upgraders) == list(range(1, k.version)), name
    reg = K.load(KINDS)
    k = reg["t_upgraded"]
    assert k.version == 3 and K.upgrader_file(k.path, "t_upgraded") == FIXTURES / "upgrade" / "t_upgraded.py"
    assert k.upgrade({"length_ft": 100.0}, 1) == {"length_m": 30.48, "label": ""}
    assert k.upgrade({"length_m": 1.0}, 2) == {"length_m": 1.0, "label": ""}
    with pytest.raises(Invalid):
        k.upgrade({}, 4)
    store = make_store()
    rec = store.put(
        {"kind": "t_upgraded", "id": None, "kv": 1, "data": {"length_ft": 10.0}, "geom": None},
        View(),
        if_match=None,
        by="ben",
    )
    assert rec["kv"] == 3 and rec["data"] == {"length_m": 3.048, "label": ""}
    # a version without its upgrader is refused at load
    import shutil

    folder = tmp_path / "f" / "kinds"
    folder.mkdir(parents=True)
    shutil.copy(FIXTURES / "kinds" / "t_upgraded.yaml", folder / "t_upgraded.yaml")
    with pytest.raises(Invalid, match="up_1"):
        K.load([folder])
