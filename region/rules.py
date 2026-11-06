"""The rule registry: rules/registry.yaml loaded, validated and queried.

Every rule the engines apply is an entry here with its ruling, status, rank inside its decision, the parameters it
reads (by record path, never a literal) and the tests that hold it as an invariant. The engines cite rule ids on
every stretch and flag; a branch without an id fails a test, and so does a rule without a test (once the engine
exists; until then `tests` may be empty and the test only warns).

    from region.rules import load, Registry
    reg = load()
    reg.rule("struct.method.paint_final").status
    reg.decision("method_per_stretch")     # rules in rank order
    reg.unratified()                       # what Ben has not ruled on
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "rules" / "registry.yaml"

DOMAINS = {"geometry", "ground", "structure", "station", "platform", "clearance", "era", "network", "river", "road", "access"}
STATUSES = {"ratified", "provisional", "unratified", "superseded"}
SYSTEMS = {"metro", "tri", "apex"}
ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,3}$")


@dataclass
class Param:
    path: str
    value: object
    unit: str
    meaning: str
    source: str
    status: str                     # recorded | literal_in_code


@dataclass
class Rule:
    id: str
    domain: str
    text: str
    status: str
    ruling: dict
    decision: str | None
    rank: int | None
    params: list = field(default_factory=list)
    applies_to: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    tests: list = field(default_factory=list)
    history: list = field(default_factory=list)
    notes: str | None = None
    superseded_by: str | None = None


@dataclass
class Registry:
    params: dict
    rules: dict
    path: Path

    def rule(self, rid: str) -> Rule:
        return self.rules[rid]

    def decision(self, name: str) -> list[Rule]:
        return sorted((r for r in self.rules.values() if r.decision == name and r.status != "superseded"), key=lambda r: r.rank or 0)

    def decisions(self) -> dict:
        return {d: self.decision(d) for d in sorted({r.decision for r in self.rules.values() if r.decision})}

    def unratified(self) -> list[Rule]:
        return [r for r in self.rules.values() if r.status in ("unratified", "provisional")]

    def by_domain(self, domain: str) -> list[Rule]:
        return [r for r in self.rules.values() if r.domain == domain]

    def validate(self) -> list[str]:
        """Every problem as a sentence; an empty list means the registry is well formed."""
        errs = []
        for p in self.params.values():
            if p.status not in ("recorded", "literal_in_code"):
                errs.append("param %s: status %r" % (p.path, p.status))
        ranks = {}
        for r in self.rules.values():
            if not ID_RE.match(r.id):
                errs.append("rule %s: id is not dotted lowercase" % r.id)
            if r.domain not in DOMAINS:
                errs.append("rule %s: domain %r" % (r.id, r.domain))
            if r.status not in STATUSES:
                errs.append("rule %s: status %r" % (r.id, r.status))
            if r.status == "ratified" and not (r.ruling and r.ruling.get("date") and r.ruling.get("words")):
                errs.append("rule %s: ratified without a dated quotation" % r.id)
            if r.status == "superseded" and not r.superseded_by:
                errs.append("rule %s: superseded without superseded_by" % r.id)
            if r.superseded_by and r.superseded_by not in self.rules:
                errs.append("rule %s: superseded_by %s is not a rule" % (r.id, r.superseded_by))
            if (r.decision is None) != (r.rank is None):
                errs.append("rule %s: decision and rank go together" % r.id)
            if r.decision:
                key = (r.decision, r.rank)
                if key in ranks and r.status != "superseded":
                    errs.append("rule %s: rank %s in %s already used by %s" % (r.id, r.rank, r.decision, ranks[key]))
                ranks.setdefault(key, r.id)
            for s in r.applies_to:
                if s not in SYSTEMS:
                    errs.append("rule %s: applies_to %r" % (r.id, s))
            for p in r.params:
                if p not in self.params and not any(p.endswith(".*") and q.startswith(p[:-1]) for q in self.params):
                    errs.append("rule %s: param %s is not in params" % (r.id, p))
            if re.search(r"\b\d+(\.\d+)?\s*(m|ft|%|‰|mm|km/h|mph)\b", r.text):
                errs.append("rule %s: a number with a unit in the text; use a param path" % r.id)
        return errs


def load(path: Path = REGISTRY) -> Registry:
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    params = {p["path"]: Param(**{k: p.get(k) for k in ("path", "value", "unit", "meaning", "source", "status")}) for p in d.get("params", [])}
    rules = {}
    for r in d.get("rules", []):
        r = dict(r)
        r.setdefault("ruling", {}); r.setdefault("decision", None); r.setdefault("rank", None)
        for k in ("params", "applies_to", "flags", "tests", "history"):
            r.setdefault(k, [])
            r[k] = r[k] or []
        if isinstance(r.get("status"), str) and r["status"].startswith("superseded"):
            r["status"] = "superseded"
        rules[r["id"]] = Rule(**{k: r.get(k) for k in Rule.__dataclass_fields__})
    return Registry(params, rules, path)


def report(reg: Registry) -> str:
    lines = ["%d rules, %d params (%d literals still in code)" % (len(reg.rules), len(reg.params), sum(p.status == "literal_in_code" for p in reg.params.values()))]
    for st in ("ratified", "provisional", "unratified", "superseded"):
        lines.append("  %-12s %d" % (st, sum(r.status == st for r in reg.rules.values())))
    for name, rs in reg.decisions().items():
        lines.append("decision %s:" % name)
        for r in rs:
            lines.append("  %2s %-40s %s" % (r.rank, r.id, r.status))
    return "\n".join(lines)


if __name__ == "__main__":
    reg = load()
    print(report(reg))
    for e in reg.validate():
        print("PROBLEM", e)
