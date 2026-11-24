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
from .section_proposal import SectionProposal
from .section_propose_input import SectionProposeInput
from .section_solve_input import SectionSolveInput
from .solved_section import SolvedSection
from .station_facts import StationFacts
from .station_input import StationInput
from .vertical_rail import VerticalRail

SCHEMA_VERSION = "v0"
CONTRACTS: dict[str, int] = {
    "section_input": 0,
    "section_proposal": 0,
    "section_propose_input": 0,
    "section_solve_input": 0,
    "solved_section": 0,
    "station_facts": 0,
    "station_input": 0,
    "vertical_rail": 0,
}

__all__ = [
    "CONTRACTS",
    "SCHEMA_VERSION",
    "Flag",
    "Hello",
    "Request",
    "Response",
    "SectionInput",
    "SectionProposal",
    "SectionProposeInput",
    "SectionSolveInput",
    "SolvedSection",
    "StationFacts",
    "StationInput",
    "VerticalRail",
]
