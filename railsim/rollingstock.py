"""Rolling stock model and YAML library loader.

A train is described physically (mass, power, tractive effort, resistance, brakes) rather
than by a time-to-speed table, so every type accelerates, climbs and brakes differently.

YAML fields (SI unless suffixed; suffixed forms are converted on load):
    name, category           metro | emu | dmu | loco
    length_m                 train length
    cars
    mass_empty_t             tare mass of the whole consist
    mass_load_t              passenger load mass at the chosen load (or give pax + kg_per_pax)
    rotating_mass_factor     lambda in m_eff = m (1 + lambda)
    adhesive_mass_fraction   share of weight on driven axles
    adhesion                 usable adhesion coefficient (dry, with slip control)
    max_te_kn                max tractive effort at the wheel (optional: derived from max_accel)
    power_kw                 power at the wheel (continuous, after HEP and transmission losses)
    natural_speed_kmh        above this, effort falls as 1/v^2 (optional)
    max_accel                commanded acceleration limit, m/s^2 (load-weighed)
    service_brake            normal braking rate used in timetable driving, m/s^2
    max_service_brake        full service brake capability, m/s^2
    emergency_brake          m/s^2 (reporting only)
    brake_delay_s            pure delay before brake effort builds (air brakes), s
    jerk                     m/s^3 comfort jerk limit
    max_speed_kmh / max_speed_mph
    davis: {A_kn, B_kn_per_kmh, C_kn_per_kmh2}  or {A_n, B_n_per_ms, C_n_per_ms2}
    tunnel_factor            multiplier on the C term inside tunnels
    cant_deficiency_in / _mm permitted unbalanced superelevation for this stock
    min_curve_radius_m       route availability: tighter curves are not allowed for this stock
    doors_per_side, door_channels (passenger streams per door), door_open_s, door_close_s
    floor                    level | high | low   (boarding type the stock is built for)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import yaml

from .geo import INCH, KMH, MPH

G = 9.80665


@dataclass
class Train:
    name: str
    category: str
    length: float
    cars: int
    mass_empty: float  # kg
    mass_load: float  # kg of passengers at reference load
    rotating_mass_factor: float
    adhesive_mass_fraction: float
    adhesion: float
    max_te: float  # N
    power: float  # W at wheel
    max_accel: float
    service_brake: float
    max_service_brake: float
    emergency_brake: float
    brake_delay: float
    jerk: float
    max_speed: float  # m/s
    davis_A: float  # N
    davis_B: float  # N/(m/s)
    davis_C: float  # N/(m/s)^2
    tunnel_factor: float = 1.6
    natural_speed: Optional[float] = None
    cant_deficiency: Optional[float] = None
    doors_per_side: int = 0
    door_channels: int = 2
    door_open: float = 3.0
    door_close: float = 4.0
    floor: str = "level"
    regen_efficiency: float = 0.0
    traction_efficiency: float = 0.85
    source_notes: str = ""
    min_curve_radius: float = 0.0  # m; tighter curves are a route-availability ban (e.g. long cars)
    load_factor: float = 1.0  # fraction of mass_load carried in this run
    extra: Dict = field(default_factory=dict)

    # ------------------------------------------------------------------ derived
    @property
    def mass(self) -> float:
        return self.mass_empty + self.load_factor * self.mass_load

    @property
    def mass_eff(self) -> float:
        # rotating inertia is a property of the empty vehicle's wheelsets/motors
        return self.mass + self.rotating_mass_factor * self.mass_empty

    def tractive_effort(self, v: float) -> float:
        """Maximum tractive effort at the wheel (N) at speed v (m/s)."""
        f_adh = self.adhesion * self.adhesive_mass_fraction * self.mass * G
        f = min(self.max_te, f_adh)
        if v > 0:
            f = min(f, self.power / v)
            if self.natural_speed and v > self.natural_speed:
                f = min(f, self.power / self.natural_speed * (self.natural_speed / v) ** 2)
        return f

    def resistance(self, v: float, tunnel: bool = False) -> float:
        c = self.davis_C * (self.tunnel_factor if tunnel else 1.0)
        return self.davis_A + self.davis_B * v + c * v * v

    def with_load(self, load_factor: float) -> "Train":
        from dataclasses import replace
        return replace(self, load_factor=load_factor)


def _get(d, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def train_from_dict(key: str, d: dict) -> Train:
    mass_empty = float(_get(d, "mass_empty_t")) * 1000.0
    if "mass_load_t" in d:
        mass_load = float(d["mass_load_t"]) * 1000.0
    else:
        mass_load = float(_get(d, "pax", default=0)) * float(_get(d, "kg_per_pax", default=75.0))
    max_speed = (float(d["max_speed_kmh"]) * KMH if "max_speed_kmh" in d
                 else float(d["max_speed_mph"]) * MPH)
    power = float(_get(d, "power_kw", default=0.0)) * 1000.0
    rot = float(_get(d, "rotating_mass_factor", default=0.08))
    max_accel = float(d["max_accel"])
    davis = d.get("davis", {})
    if "A_kn" in davis:
        A = davis["A_kn"] * 1000.0
        B = davis.get("B_kn_per_kmh", 0.0) * 1000.0 * 3.6
        C = davis.get("C_kn_per_kmh2", 0.0) * 1000.0 * 3.6 ** 2
    else:
        A = float(davis.get("A_n", 0.0))
        B = float(davis.get("B_n_per_ms", 0.0))
        C = float(davis.get("C_n_per_ms2", 0.0))
    if "max_te_kn" in d:
        max_te = float(d["max_te_kn"]) * 1000.0
    else:
        # derive from the commanded rate at the reference load (rate is held up to that load)
        ref_mass = mass_empty + mass_load
        max_te = (ref_mass + rot * mass_empty) * max_accel + A
    eu = None
    if "cant_deficiency_in" in d:
        eu = float(d["cant_deficiency_in"]) * INCH
    elif "cant_deficiency_mm" in d:
        eu = float(d["cant_deficiency_mm"]) / 1000.0
    nat = d.get("natural_speed_kmh")
    return Train(
        name=str(d.get("name", key)),
        category=str(d.get("category", "emu")),
        length=float(d["length_m"]),
        cars=int(d.get("cars", 1)),
        mass_empty=mass_empty,
        mass_load=mass_load,
        rotating_mass_factor=rot,
        adhesive_mass_fraction=float(_get(d, "adhesive_mass_fraction", default=1.0)),
        adhesion=float(_get(d, "adhesion", default=0.25)),
        max_te=max_te,
        power=power if power > 0 else max_te * 15.0,
        max_accel=max_accel,
        service_brake=float(d["service_brake"]),
        max_service_brake=float(_get(d, "max_service_brake", default=d["service_brake"])),
        emergency_brake=float(_get(d, "emergency_brake", default=1.3 * float(d["service_brake"]))),
        brake_delay=float(_get(d, "brake_delay_s", default=0.0)),
        jerk=float(_get(d, "jerk", default=0.8)),
        max_speed=max_speed,
        davis_A=A, davis_B=B, davis_C=C,
        tunnel_factor=float(_get(d, "tunnel_factor", default=1.6)),
        natural_speed=float(nat) * KMH if nat else None,
        cant_deficiency=eu,
        doors_per_side=int(_get(d, "doors_per_side", default=0)),
        door_channels=int(_get(d, "door_channels", default=2)),
        door_open=float(_get(d, "door_open_s", default=3.0)),
        door_close=float(_get(d, "door_close_s", default=4.0)),
        floor=str(_get(d, "floor", default="level")),
        regen_efficiency=float(_get(d, "regen_efficiency", default=0.0)),
        traction_efficiency=float(_get(d, "traction_efficiency", default=0.85)),
        source_notes=str(_get(d, "sources", default="")),
        min_curve_radius=float(_get(d, "min_curve_radius_m", default=0.0)),
        extra={k: v for k, v in d.items() if k.startswith("x_")},
    )


def load_library(path: str | Path) -> Dict[str, Train]:
    data = yaml.safe_load(Path(path).read_text())
    return {k: train_from_dict(k, v) for k, v in data.items() if isinstance(v, dict)}
