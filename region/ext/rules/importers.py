"""``registry@1``: ``rules/registry.yaml`` into the ``import:registry`` layer, one record per rule and per param.

The registry is the one owner of each rule value (9.25). Each of its ``rules`` becomes a ``rule`` record (legacy
key: the rule id) and each of its ``params`` a system-wide ``param`` record (legacy key: the path). Ben's change to
a value is a main-layer revision of that param citing a ruling; when the registry later changes a value Ben
overrode, the import's rebase raises an ``authority_divergence`` conflict (the param kind's ``x-conflict``) and
Ben's value stays on read.

Two values are written in the hub's units rather than as the YAML spells them (9.15: feet only at the edges): a
param in ``ft`` is stored in metres, with the YAML's value and unit in ``attrs``; and a ruling's ``date`` (which YAML
may parse as a date) is stored as ISO text. ``registry_of`` writes the YAML's lists back from the records.
"""

from __future__ import annotations

import copy
import datetime as dt
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from region.core import fsio
from region.core.errors import Invalid
from region.core.protocols import IdLookup, PathResolver

FT_M = 0.3048
RULE_FIELDS = (
    "domain",
    "text",
    "status",
    "ruling",
    "decision",
    "rank",
    "params",
    "applies_to",
    "flags",
    "tests",
    "history",
    "notes",
)
PARAM_FIELDS = ("meaning", "source", "status")


def _iso(value: Any) -> Any:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _iso(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_iso(v) for v in value]
    return value


def read_registry(path: Path) -> dict[str, Any]:
    doc = fsio.read_yaml(path)
    if not isinstance(doc, dict) or not isinstance(doc.get("rules"), list) or not isinstance(doc.get("params"), list):
        raise Invalid(f"{path} holds no rules and params lists")
    return doc


def rule_data(rule: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"rule": rule["id"]}
    for f in RULE_FIELDS:
        if f in rule:
            out[f] = _iso(copy.deepcopy(rule[f]))
    return out


def param_data(param: Mapping[str, Any]) -> dict[str, Any]:
    value, unit = copy.deepcopy(param["value"]), str(param["unit"])
    out: dict[str, Any] = {"path": param["path"], "value": value, "unit": unit}
    if unit == "ft" and isinstance(value, (int, float)) and not isinstance(value, bool):
        out["value"] = round(value * FT_M, 6)
        out["unit"] = "m"
        out["attrs"] = {"source_value": value, "source_unit": "ft"}
    for f in PARAM_FIELDS:
        if f in param:
            out[f] = _iso(copy.deepcopy(param[f]))
    out["scope"] = None
    out["years"] = None
    out["ruling"] = None
    return out


class Registry:
    """``registry@1`` (see the module doc)."""

    name = "registry"
    version = "1"
    namespace = "registry"
    layer = "import:registry"

    def sources(self, paths: PathResolver) -> dict[str, str]:
        return {"registry": "repo://rules/registry.yaml"}

    def records(self, src: Mapping[str, Path], ids: IdLookup) -> Iterator[dict[str, Any]]:
        doc = read_registry(Path(src["registry"]))
        source = "repo://rules/registry.yaml"
        seen: dict[str, str] = {}
        for rule in doc["rules"]:
            key = str(rule["id"])
            if seen.setdefault(key, "rule") != "rule":
                raise Invalid(f"registry: {key!r} is both a rule id and a param path")
            yield {
                "kind": "rule",
                "id": ids.id_for("rule", key, kind="rule"),
                "data": rule_data(rule),
                "geom": None,
                "source": source,
            }
        for param in doc["params"]:
            key = str(param["path"])
            if seen.setdefault(key, "param") != "param":
                raise Invalid(f"registry: {key!r} is both a rule id and a param path")
            yield {
                "kind": "param",
                "id": ids.id_for("param", key, kind="param"),
                "data": param_data(param),
                "geom": None,
                "source": source,
            }


def registry_of(records: list[dict[str, Any]]) -> dict[str, Any]:
    """The registry's ``rules`` and ``params`` lists the records stand for (dates as ISO text; feet restored)."""
    rules, params = [], []
    for r in records:
        d = r["data"]
        if r["kind"] == "rule":
            rule = {"id": d["rule"]}
            rule.update({f: d[f] for f in RULE_FIELDS if f in d})
            rules.append(rule)
        elif r["kind"] == "param" and d.get("scope") is None:
            attrs = d.get("attrs") or {}
            p = {f: d[f] for f in PARAM_FIELDS if f in d}
            p.update(
                {
                    "path": d["path"],
                    "value": attrs.get("source_value", d["value"]),
                    "unit": attrs.get("source_unit", d["unit"]),
                }
            )
            params.append(p)
    return {"params": params, "rules": rules}


REGISTRY = Registry()
IMPORTERS = [REGISTRY]

__all__ = ["IMPORTERS", "REGISTRY", "Registry", "param_data", "read_registry", "registry_of", "rule_data"]
