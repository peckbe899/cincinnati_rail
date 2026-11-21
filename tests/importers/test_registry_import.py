"""``registry@1``: ``rules/registry.yaml`` into ``import:registry`` (section 10, WP5; decision 9.25)."""

from __future__ import annotations

import shutil

import yaml

from region.core import fsio
from region.core.view import View
from region.ext.rules.importers import REGISTRY, read_registry, registry_of
from region.ext.rules.params import resolve
from tests.importers.fakes import FakeIds
from tests.importers.helpers import MAIN, all_records, fresh_copy, import_all, read_only
from tests.importers.helpers import REGISTRY as REGISTRY_FILE


def _iso(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _iso(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_iso(x) for x in v]
    return v


def test_rules_and_params_import():
    records = list(REGISTRY.records({"registry": REGISTRY_FILE}, FakeIds("registry")))
    assert records == list(REGISTRY.records({"registry": REGISTRY_FILE}, FakeIds("registry")))  # pure
    rules = [r for r in records if r["kind"] == "rule"]
    params = [r for r in records if r["kind"] == "param"]
    assert len(rules) == 137 and len(params) == 163
    # the inputs round trip: the registry's lists come back (dates as ISO text, feet restored)
    doc = read_registry(REGISTRY_FILE)
    back = registry_of(records)
    assert back["rules"] == _iso(doc["rules"])
    assert back["params"] == doc["params"]
    with read_only() as store:
        stored_rules = all_records(store, "rule")
        stored_params = [p for p in all_records(store, "param") if p["data"]["scope"] is None]
        assert len(stored_rules) == 137 and len(stored_params) == 163
        assert {r["layer"] for r in stored_rules + stored_params} == {"import:registry"}
        assert resolve(store, MAIN, "settings.platform") == 121.92
        assert resolve(store, MAIN, "settings_rer.vcRadius") == 3000
        pool = next(p for p in stored_params if p["data"]["path"] == "settings.poolFt")
        assert pool["data"]["unit"] == "m" and pool["data"]["value"] == 138.684  # 455 ft, stored in metres (9.15)
        assert pool["data"]["attrs"] == {"source_value": 455.0, "source_unit": "ft"}
        rid = store.legacy("rule", "geometry.method.per_stretch")
        rule = store.get("rule", rid, MAIN)
        assert rule["data"]["status"] == "ratified" and rule["data"]["ruling"]["date"] == "2026-11-04"
        assert store.legacy("param", "settings.vcMinLen") is not None


def test_override_divergence_listed(write_root):
    """Ben's override of a registry value is a main revision citing a ruling; when the registry later changes that
    value, the import lists an authority_divergence conflict and Ben's value stays on read (9.25)."""
    reg = write_root / "registry.yaml"
    shutil.copyfile(REGISTRY_FILE, reg)
    store = fresh_copy(write_root)
    first = import_all(store, write_root, ["registry"], overrides={"registry": reg})["registry"].report
    assert first.errors == [] and first.counts["updated"] == 0
    ruling = store.put(
        {
            "kind": "ruling",
            "id": None,
            "geom": None,
            "data": {
                "title": "Metro vertical curves 1600 m",
                "date": "2026-11-21",
                "by": "Ben",
                "words": None,
                "source": "test",
                "rules": [],
                "params": ["settings.vcRadius"],
            },
        },
        MAIN,
        if_match=None,
        by="ben",
    )
    pid = store.legacy("param", "settings.vcRadius")
    param = store.get("param", pid, MAIN)
    ours = store.put(
        {**param, "data": {**param["data"], "value": 1600, "ruling": ruling["id"]}},
        MAIN,
        if_match=f'"{param["layer"]}:{param["version"]}"',
        by="ben",
    )
    assert ours["layer"] == "main" and resolve(store, MAIN, "settings.vcRadius") == 1600
    doc = yaml.safe_load(reg.read_text(encoding="utf-8"))
    for p in doc["params"]:
        if p["path"] == "settings.vcRadius":
            p["value"] = 1550
        if p["path"] == "settings.drainMin":  # a value Ben did not touch: that one changes quietly
            p["value"] = 4
    fsio.write_text(reg, yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    report = import_all(store, write_root, ["registry"], overrides={"registry": reg})["registry"].report
    assert report.errors == [] and report.counts["updated"] == 2
    (conflict,) = report.conflicts
    assert conflict["reason"] == "authority_divergence" and conflict["rec_id"] == pid
    assert resolve(store, MAIN, "settings.vcRadius") == 1600  # Ben's value stays on read
    assert resolve(store, View(layer="import:registry"), "settings.vcRadius") == 1550
    assert resolve(store, MAIN, "settings.drainMin") == 4
    assert [c["rec_id"] for c in store.conflicts(state="open")] == [pid]
    store.close()
