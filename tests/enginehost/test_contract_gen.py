"""region/contract/gen is generated from engine/schema/v0 (python -m region.enginehost.codegen) and committed: it must
match a fresh generation, and the models must accept what the engine takes and gives."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from region.contract import gen
from region.core import fsio
from region.enginehost import codegen
from tests.enginehost.helpers import GOLDEN, golden_input


def test_generated_models_match_the_schemas() -> None:
    pytest.importorskip("datamodel_code_generator", reason="datamodel-code-generator is in the dev dependencies")
    stale = codegen.stale()
    assert stale == [], f"region/contract/gen is stale ({stale}): run python -m region.enginehost.codegen"


def test_contract_majors_follow_the_schema_index() -> None:
    index = fsio.read_json(codegen.SCHEMA_DIR / "contracts.json")
    assert gen.CONTRACTS == index["contracts"]
    assert gen.SCHEMA_VERSION == "v0"


def test_models_take_the_golden_inputs() -> None:
    for path in sorted((GOLDEN / "inputs").glob("*.json")):
        model = gen.SectionInput.model_validate(fsio.read_json(path))
        assert model.contract == "section_input/0"
    bad = {**golden_input("Line_2b"), "extra": 1}
    with pytest.raises(ValidationError):
        gen.SectionInput.model_validate(bad)


def test_models_take_an_engine_output(pool) -> None:
    out = pool.call("vertical.rail", golden_input("Line_2b"))
    model = gen.VerticalRail.model_validate(out)
    assert model.grid.n == len(model.rail_m)
    hello = gen.Hello.model_validate({"hello": pool.hello()})
    assert "vertical.rail@1" in [m.root for m in hello.hello.methods]
