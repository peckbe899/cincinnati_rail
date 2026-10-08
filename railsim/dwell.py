"""Dwell time models.

Metro (door-cycle model, after TCQSM 3rd ed. ch. 6 / TCRP Report 165):
    dwell = door_unlock_open + passenger_flow + door_close (incl. warning chime)
            + reopen_allowance + dispatch (closed-and-locked -> motion)
    passenger_flow = max_door_load * (alight * t_alight + board * t_board) / door_channels
    where the busiest door carries `door_peaking` times the average door load.

Commuter / RER (platform-type model):
    dwell = brake_settle + door_open + passenger_flow(platform type, open doors)
            + conductor (all-aboard / door control) + door_close + brake_release
    Low-level platforms mean steps: slower boarding and, on traditional stock, only some
    doors opened by the crew. High-level (level) boarding behaves like a metro door.
    'L' (early-departure) stops and flag stops are handled in the timetable layer.

All volumes are per train per stop and are set by station class in the program configs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class StationClassLoad:
    board: float  # passengers boarding this train
    alight: float  # passengers alighting


@dataclass
class MetroDwell:
    door_open: float = 3.0  # s, unlock + open
    door_close: float = 5.0  # s, warning chime + close + lock
    dispatch: float = 2.5  # s, doors locked -> train moving (ATO start / operator reaction)
    t_board: float = 1.8  # s per boarding passenger per door channel
    t_alight: float = 1.4  # s per alighting passenger per door channel
    door_peaking: float = 1.6  # busiest door load / average door load
    reopen_prob_per_100: float = 0.10  # chance of a door re-open per 100 pax exchanged
    reopen_penalty: float = 8.0  # s per re-open
    min_dwell: float = 15.0
    classes: Dict[str, StationClassLoad] = field(default_factory=lambda: {
        "minor": StationClassLoad(8, 8),
        "standard": StationClassLoad(25, 25),
        "busy": StationClassLoad(60, 60),
        "transfer": StationClassLoad(120, 120),
        "terminal": StationClassLoad(150, 150),
    })

    def dwell(self, station_class: str, doors_total: int, door_channels: int,
              load_scale: float = 1.0, override: Optional[float] = None) -> float:
        if override is not None:
            return float(override)
        c = self.classes.get(station_class, self.classes["standard"])
        board, alight = c.board * load_scale, c.alight * load_scale
        doors = max(doors_total, 1)
        per_door = self.door_peaking / doors
        flow = per_door * (board * self.t_board + alight * self.t_alight) / max(door_channels, 1)
        reopen = self.reopen_prob_per_100 * (board + alight) / 100.0 * self.reopen_penalty
        return max(self.door_open + flow + self.door_close + reopen + self.dispatch, self.min_dwell)


@dataclass
class CommuterDwell:
    brake_settle: float = 1.0  # s, stopped -> doors released
    door_open: float = 3.5
    door_close: float = 6.0  # incl. warning
    conductor: float = 8.0  # s, all-aboard / door control / signal to engineer
    brake_release: float = 4.0  # s, air-brake release before motion (EMUs ~1-2 s)
    t_board_level: float = 2.0  # s/pax/door channel, level boarding
    t_alight_level: float = 1.5
    t_board_steps: float = 3.5  # s/pax via steps (low-level platform)
    t_alight_steps: float = 2.7
    open_door_fraction_low: float = 0.5  # share of doors opened at low platforms (crew-operated)
    door_peaking: float = 1.6
    min_dwell: float = 20.0
    classes: Dict[str, StationClassLoad] = field(default_factory=lambda: {
        "minor": StationClassLoad(5, 5),
        "standard": StationClassLoad(20, 15),
        "busy": StationClassLoad(60, 50),
        "hub": StationClassLoad(150, 150),
        "terminal": StationClassLoad(200, 200),
    })

    def dwell(self, station_class: str, platform: str, doors_total: int, door_channels: int,
              load_scale: float = 1.0, override: Optional[float] = None) -> float:
        if override is not None:
            return float(override)
        c = self.classes.get(station_class, self.classes["standard"])
        board, alight = c.board * load_scale, c.alight * load_scale
        level = platform in ("high", "level")
        tb = self.t_board_level if level else self.t_board_steps
        ta = self.t_alight_level if level else self.t_alight_steps
        doors = max(doors_total, 1)
        if not level:
            doors = max(int(round(doors * self.open_door_fraction_low)), 1)
            door_channels = 1  # one stream down the steps
        flow = self.door_peaking / doors * (board * tb + alight * ta) / max(door_channels, 1)
        total = (self.brake_settle + self.door_open + flow + self.conductor + self.door_close
                 + self.brake_release)
        return max(total, self.min_dwell)
