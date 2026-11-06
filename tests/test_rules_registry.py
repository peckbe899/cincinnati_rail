"""The rule registry is well formed, every number is a parameter, and every rule is traceable."""
import warnings

import pytest

from region.rules import REGISTRY, load


@pytest.fixture(scope="module")
def reg():
    if not REGISTRY.exists():
        pytest.skip("rules/registry.yaml not written yet")
    return load()


def test_registry_is_well_formed(reg):
    errs = reg.validate()
    assert not errs, "\n".join(errs)


def test_every_rule_has_a_source(reg):
    missing = [r.id for r in reg.rules.values() if not (r.ruling and r.ruling.get("source"))]
    assert not missing, missing


def test_ranked_decisions_are_contiguous(reg):
    for name, rs in reg.decisions().items():
        ranks = [r.rank for r in rs]
        assert ranks == list(range(1, len(ranks) + 1)), (name, ranks)


def test_every_rule_will_have_a_test(reg):
    """Warns until the engine exists; becomes an assertion in slice 1."""
    untested = [r.id for r in reg.rules.values() if r.status != "superseded" and not r.tests]
    if untested:
        warnings.warn("%d rules without an invariant test yet" % len(untested))
