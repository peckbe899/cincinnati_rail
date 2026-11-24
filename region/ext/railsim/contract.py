"""The railsim feature's contracts as pydantic models: ``route_input/0`` (``route.assemble``'s meta), ``run_result/0``
(``railsim.run``'s meta, and the draft's answer), and the draft route's request and answer. The router's
``response_model``s, so ``openapi.json`` and the app's generated types carry them.

Members not listed here are allowed (``extra``), so an added field is not a breaking change; a removed or renamed one
is, and takes the contract to its next major.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

ROUTE_INPUT = "route_input/0"
RUN_RESULT = "run_result/0"


class _Open(BaseModel):
    model_config = ConfigDict(extra="allow")


class RunLeg(_Open):
    run_s: float = Field(description="Seconds from the departure before to this arrival.")
    vmax_kmh: float
    accel_s: float
    cruise_s: float
    coast_s: float
    brake_s: float


class RunStation(_Open):
    platform_id: str | None
    name: str
    c_m: float | None = Field(description="Section chainage of the platform centre.")
    s_m: float = Field(description="Run chainage of the platform centre (along the fit).")
    km: float = Field(description="Km from the first stop marker of the direction, as railsim reports it.")
    arrive_s: float
    depart_s: float
    dwell_s: float
    scheduled_arrive_s: float | None
    leg: RunLeg | None


class RunDirection(_Open):
    dir: int = Field(description="1 is rising section chainage, -1 falling.")
    label: str
    from_: str = Field(alias="from")
    to: str
    distance_m: float
    stops: int
    running_s: float
    dwell_s: float
    trip_s: float
    scheduled_s: float | None
    average_kmh: float
    max_kmh: float
    energy_traction_kwh: float
    energy_regen_kwh: float
    stations: list[RunStation]


class RunTrain(_Open):
    key: str
    name: str
    cars: int
    length_m: float
    load_factor: float
    mass_t: float
    rail_condition: str
    max_kmh: float


class RunEra(_Open):
    name: str | None
    goa: int | None
    years: list[int]
    signalling: str | None


class RunZone(_Open):
    c0_m: float
    c1_m: float
    kmh: float
    reason: str
    rule: str | None


class RunCurveLimit(_Open):
    c0_m: float
    c1_m: float
    radius_m: float
    spiral_m: float
    limit_kmh: float


class RunGrid(_Open):
    c0: float
    step_m: float
    n: int


class RunResult(_Open):
    """``run_result/0``: both directions of one route in one year."""

    contract: str = Field(RUN_RESULT, description="run_result/0")
    route_id: str | None
    route_key: str | None
    config: str | None
    year: int | None
    year_source: str | None
    era: RunEra | None
    train: RunTrain
    padding: dict[str, float]
    directions: list[RunDirection]
    round_trip_s: float
    turnback_s: list[float]
    speed_zones: list[RunZone]
    curves: list[RunCurveLimit]
    grid: RunGrid = Field(
        description="The section grid of the result's arrays (limit_ms, v_fwd_ms, v_rev_ms, t_fwd_s, t_rev_s)."
    )
    warnings: list[str]
    sources: dict[str, str]


class RouteStop(_Open):
    platform_id: str | None
    name: str
    c_m: float
    s_m: float
    platform_m: float
    class_: str = Field(alias="class")
    class_source: str
    psd: bool | None
    dwell_s: float | None = None
    terminal: bool
    removed: bool = False
    reverse: bool = False


class RouteRemoved(_Open):
    platform_id: str
    name: str
    c_m: float
    why: str


class RouteInput(_Open):
    """``route_input/0``: one route on the run grid (meta; the arrays ``s_m``, ``c_m``, ``rail_z_m``,
    ``curvature_per_m``, ``tunnel``, ``type`` are in the result's arrays, or lists in the input route)."""

    contract: str = Field(ROUTE_INPUT, description="route_input/0")
    route_id: str | None
    route_key: str | None
    name: str | None
    config: str
    section: dict[str, Any]
    run_grid: RunGrid
    length_m: float
    curves: list[dict[str, Any]]
    stops: list[RouteStop]
    removed: list[RouteRemoved]
    restrictions: list[dict[str, Any]]
    sources: dict[str, str]
    warnings: list[str]
    arrays: dict[str, list[float]] | None = Field(None, description="The run grid arrays (the input route only).")


class DraftIn(BaseModel):
    """A draft run: the sheet's SectionInput of its draft, the draft's structure types when it has them, and its edit
    revision (echoed)."""

    model_config = ConfigDict(extra="forbid")
    section_input: dict[str, Any] = Field(description="SectionInput v0 of the draft (the sheet's worker input).")
    type_runs: list[list[Any]] | None = Field(
        None, description="section.solve@1's type_runs for this edit; absent, the saved structure solve's are used."
    )
    edit_rev: int | None = None


class DraftBase(_Open):
    assemble: str | None
    run: str | None


class DraftOut(RunResult):
    """A draft's RunResult and where it came from."""

    draft: bool = True
    key: str = Field(description="sha256 of the run's code, its files, the year and the draft RouteInput.")
    cached: bool
    ms: float
    types: str = Field(description="draft or saved")
    base: DraftBase
    edit_rev: int | None = None
    arrays: dict[str, list[float | None]] = Field(
        description="limit_ms, v_fwd_ms, v_rev_ms, t_fwd_s, t_rev_s on the section grid of grid "
        "(null where the train never is)."
    )


__all__ = ["DraftIn", "DraftOut", "ROUTE_INPUT", "RUN_RESULT", "RouteInput", "RunResult"]
