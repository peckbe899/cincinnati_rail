"""Reports: CSV, KMZ of the fitted alignment, and plots."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .geo import MPH
from .kml import KmlWriter, rgb_to_kml
from .speed import zones_from_profile


def zone_list(route):
    out = []
    for z in zones_from_profile(route.speed):
        out.append({"from_km": round(z.s0 / 1000, 3), "to_km": round(z.s1 / 1000, 3),
                    "mph": round(z.speed / MPH, 1), "kmh": round(z.speed * 3.6, 1)})
    return out


def write_csv(out_dir: Path, dr):
    safe = dr.label.replace(" -> ", "_to_").replace("/", "-").replace(" ", "_")
    with open(out_dir / f"stations_{safe}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["station", "km", "arrive_s", "depart_s", "dwell_s", "scheduled_arrive_s"])
        for k, st in enumerate(dr.stations):
            w.writerow([st.name, round((dr.stop_s[k] - dr.stop_s[0]) / 1000, 3),
                        round(dr.run.arrivals[k], 1), round(dr.run.departures[k], 1),
                        round(dr.dwell[k], 1),
                        round(dr.padded_arrivals[k], 1) if dr.padded_arrivals else ""])
    run = dr.run
    with open(out_dir / f"trace_{safe}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "s_m", "v_kmh", "a_ms2"])
        step = max(len(run.t) // 20000, 1)
        for i in range(0, len(run.t), step):
            w.writerow([round(run.t[i], 2), round(run.s[i], 1), round(run.v[i] * 3.6, 2),
                        round(run.a[i], 3)])


def _speed_color(v_mph: float, vmax_mph: float):
    import colorsys
    f = max(0.0, min(1.0, v_mph / max(vmax_mph, 1)))
    r, g, b = colorsys.hsv_to_rgb(0.33 * f, 0.9, 0.95)  # red (slow) -> green (fast)
    return rgb_to_kml(r, g, b)


def write_kml(path: Path, route):
    kw = KmlWriter(f"{route.name} (fitted alignment)")
    vmax = float(np.nanmax(route.speed.limit)) / MPH
    kw.open_folder("Speed zones (posted)")
    for z in zones_from_profile(route.speed):
        s = np.linspace(z.s0, max(z.s1, z.s0 + 1), max(int((z.s1 - z.s0) / 10), 2))
        lat, lon = route.latlon_at(s)
        zz = route.profile.elevation_at(s)
        kw.line(f"{z.speed / MPH:.0f} mph ({z.speed * 3.6:.0f} km/h)",
                list(zip(lat, lon, zz)), _speed_color(z.speed / MPH, vmax), 5,
                f"km {z.s0 / 1000:.2f}-{z.s1 / 1000:.2f}")
    kw.close_folder()
    kw.open_folder("Curves")
    for c in route.horizontal.curves:
        s = np.linspace(c.s_ts, c.s_st, max(int(c.length / 5), 2))
        lat, lon = route.latlon_at(s)
        kw.line(f"R={c.radius:.0f} m", list(zip(lat, lon, np.zeros_like(lat))), "ff00ffff", 2,
                f"radius {c.radius:.0f} m, spirals {c.spiral:.0f} m, cant {c.cant * 1000:.0f} mm, "
                f"deflection {np.degrees(c.deflection):.1f} deg")
    kw.close_folder()
    kw.open_folder("Structures")
    colors = {"viaduct": "ffff0000", "fill": "ff00a5ff", "cut": "ff2a2aa5", "deep-cut": "ff00008b",
              "tunnel": "ff000000", "at-grade": "ff808080"}
    for s0, s1, kind in route.profile.segments():
        if kind == "at-grade":
            continue
        s = np.linspace(s0, max(s1, s0 + 1), max(int((s1 - s0) / 10), 2))
        lat, lon = route.latlon_at(s)
        kw.line(kind, list(zip(lat, lon, np.zeros_like(lat))), colors.get(kind, "ffffffff"), 8)
    kw.close_folder()
    kw.open_folder("Stations")
    for st in route.stations:
        lat, lon = route.latlon_at([st.s])
        kw.point(st.name, float(lat[0]), float(lon[0]),
                 f"km {st.s / 1000:.2f}; class {st.cls}; platform {st.platform}; "
                 f"offset from track {st.offset:.0f} m")
    kw.close_folder()
    kw.save(path)


def plot_run(out_dir: Path, route, dr, train):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    run = dr.run
    L = route.length
    rev = dr.reverse
    td_s = np.linspace(0, L, 4000)
    src_s = (L - td_s) if rev else td_s
    lim = route.speed.at(src_s)
    z = route.profile.elevation_at(src_s)
    ground = np.interp(src_s, route.profile.s, route.profile.ground)
    fig, ax = plt.subplots(3, 1, figsize=(15, 10), sharex=True,
                           gridspec_kw={"height_ratios": [3, 1.4, 1.2]})
    ax[0].step(td_s / 1000, lim * 3.6, where="post", color="#c0392b", lw=1, label="posted limit")
    ax[0].plot(run.s / 1000, run.v * 3.6, color="#1f4e79", lw=1.4, label=train.name)
    for k, st in enumerate(dr.stations):
        ax[0].axvline(dr.stop_s[k] / 1000, color="0.85", lw=0.8, zorder=0)
        ax[0].text(dr.stop_s[k] / 1000, 2, st.name, rotation=90, fontsize=7, va="bottom", ha="right")
    ax[0].set_ylabel("speed (km/h)")
    ax[0].set_ylim(0, max(lim.max(), run.v.max()) * 3.6 * 1.1)
    ax[0].legend(loc="upper right")
    ax[0].set_title(f"{route.name}: {dr.label} | {train.name} | trip {run.arrivals[-1] / 60:.1f} min")
    ax[1].plot(td_s / 1000, ground, color="0.6", lw=0.8, label="ground")
    ax[1].plot(td_s / 1000, z, color="k", lw=1.2, label="track")
    ax[1].set_ylabel("elevation (m)")
    ax[1].legend(loc="upper right")
    gr = np.gradient(z, td_s) * 100
    ax[2].fill_between(td_s / 1000, gr, color="#7f8c8d")
    ax[2].set_ylabel("grade (%)")
    ax[2].set_xlabel("distance (km)")
    for a in ax:
        a.grid(alpha=0.25)
    safe = dr.label.replace(" -> ", "_to_").replace("/", "-").replace(" ", "_")
    fig.tight_layout()
    fig.savefig(out_dir / f"profile_{safe}.png", dpi=130)
    plt.close(fig)
