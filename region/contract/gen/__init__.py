"""Pydantic models of engine contract v0, generated from engine/schema/v0 by datamodel-code-generator.

Do not edit: run ``python -m region.enginehost.codegen``. tests/enginehost/test_contract_gen.py regenerates
these files and fails on any difference. ``CONTRACTS`` are the contract majors these models describe: the
engine host refuses an engine whose hello names another major.
"""

from .flag import Flag
from .hello import Hello
from .request import Request
from .response import Response
from .section_input import SectionInput
from .vertical_rail import VerticalRail

SCHEMA_VERSION = "v0"
CONTRACTS: dict[str, int] = {"section_input": 0, "vertical_rail": 0}

__all__ = ["CONTRACTS", "SCHEMA_VERSION", "Flag", "Hello", "Request", "Response", "SectionInput", "VerticalRail"]
