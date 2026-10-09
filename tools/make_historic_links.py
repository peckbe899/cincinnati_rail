"""Draw the pre-RER connections into Union Terminal (Ben's rulings) in
data/kmz/cincinnati_historic.kml, next to the digitized RER-1 approaches.

  RER-2 (before 1988): Covington Union over the C&O bridge and the C&O viaduct into the top
      platforms (the Falmouth and Verona lines).
  RER-3 (before 1988): a short link along the embankment from the Mill Creek mouth into
      Union Terminal's top (track-level) platforms, a wye off the riverfront line.
  RER-4 (before 1990): Newport west on the C&O through Covington, over the C&O bridge and
      the C&O viaduct into the top platforms.
  RER-5 (before 1996): Norwood Central west to Ivorydale on the existing Norwood-CUT ROW,
      then down the Mill Creek valley (the drawn Mill Creek trunk) into Union Terminal.

Where the railroad still exists the line follows today's track (Overture rail,
data/reference/overture_rail_cincinnati.kml). The C&O viaduct and the Mill Creek link are
gone, so those stretches are smooth curves between the known ends: approximate, redraw
them in the KMZ when you have the 1955 / Sanborn alignments.

    python tools/make_historic_links.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from railsim.geo import LocalProjection  # noqa: E402
from railsim.kml import KmlWriter, read_kml_bytes  # noqa: E402
from railsim.network import Network  # noqa: E402

HIST = ROOT / "data" / "kmz" / "cincinnati_historic.kml"
RAIL = ROOT / "data" / "reference" / "overture_rail_cincinnati.kml"

# Union Terminal's top platforms (track level, 154.0 m), at the station throat west of the
# building, where the digitized RER-1 approaches end
CUT_TOP = (39.1097, -84.5415)


def overture_route(points, max_turn=60.0):
    """Path along today's railroads through `points` [(lat, lon)], as [(lat, lon)]."""
    rl = read_kml_bytes(RAIL.read_bytes())
    lines = [ln for p in rl if p.lines and "tram" not in p.name and "Subway" not in p.name
             for ln in p.lines]
    box = (38.98, 39.20, -84.62, -84.40)
    lines = [ln for ln in lines if any(box[0] <= c[0] <= box[1] and box[2] <= c[1] <= box[3] for c in ln)]
    proj = LocalProjection.around([c[0] for ln in lines for c in ln], [c[1] for ln in lines for c in ln])
    polys = [np.column_stack(proj.to_xy([c[0] for c in ln], [c[1] for c in ln])) for ln in lines]
    net = Network.build(polys, snap_tol=8.0)
    stops = [net.locate(*map(float, proj.to_xy(la, lo)), 400)[:2] for la, lo in points]
    xy, _ = net.route(stops, max_turn)
    lat, lon = proj.to_latlon(xy[:, 0], xy[:, 1])
    return [(float(a), float(b)) for a, b in zip(lat, lon)]


def bezier(p0, p1, p2, p3, n=24):
    t = np.linspace(0.0, 1.0, n)[:, None]
    P = [np.array(p) for p in (p0, p1, p2, p3)]
    pts = (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]
    return [tuple(map(float, q)) for q in pts]


def dedupe(pts, tol=1e-6):
    out = []
    for p in pts:
        if not out or abs(out[-1][0] - p[0]) + abs(out[-1][1] - p[1]) > tol:
            out.append(p)
    return out


def main():
    keep = [p for p in read_kml_bytes(HIST.read_bytes()) if p.lines and p.path_str.endswith("RER-1")]
    kw = KmlWriter("Cincinnati historic rights of way")
    kw.open_folder("Cincinnati Historic")

    kw.open_folder("RER-1")
    for p in keep:
        kw.line(p.name, [(c[0], c[1], 0.0) for c in p.lines[0]], "ff00a5ff", 3.0, p.description or "")
    kw.close_folder()

    # RER-3: wye off the riverfront line at the Mill Creek mouth, north into the top platforms
    merge = (39.1045, -84.5428)
    main = dedupe(bezier(merge, (39.1065, -84.5426), (39.1080, -84.5418), CUT_TOP))
    west = dedupe(bezier((39.10013, -84.54747), (39.10015, -84.54509), (39.1028, -84.5432), merge))
    east = dedupe(bezier((39.09946, -84.54080), (39.09994, -84.54284), (39.1026, -84.5426), merge))
    note = "Approximate (Ben's ruling: a short link along the embankment from the Mill Creek mouth into UT's top platforms); redraw from the 1955 sheets"
    kw.open_folder("RER-3")
    kw.line("Historic Mill Creek link", [(a, b, 0.0) for a, b in main], "ff00a5ff", 3.0, note)
    kw.line("Historic Mill Creek link west leg", [(a, b, 0.0) for a, b in west], "ff00a5ff", 3.0, note)
    kw.line("Historic Mill Creek link east leg", [(a, b, 0.0) for a, b in east], "ff00a5ff", 3.0, note)
    kw.close_folder()

    # RER-4: the C&O from Newport (where the Dover line leaves it) through Covington and over
    # the C&O bridge (today's CSX), then the C&O viaduct (gone) into the top platforms
    co = overture_route([(39.1010, -84.4785), (39.0732, -84.5092), (39.0975, -84.5284)])
    bridge_end = co[-1]
    viaduct = bezier(bridge_end, (39.1030, -84.5345), (39.1060, -84.5418), CUT_TOP)
    kw.open_folder("RER-4")
    kw.line("Historic C&O Newport - Union Terminal", [(a, b, 0.0) for a, b in dedupe(co + viaduct[1:])],
            "ff00a5ff", 3.0, "C&O through Newport and Covington and over the C&O bridge along today's CSX "
            "(Overture rail); the C&O viaduct into Union Terminal is an approximate curve, redraw it")
    kw.close_folder()

    # RER-2 (before 1988): Covington Union over the C&O bridge and the C&O viaduct into the top
    # platforms; the Verona line meets the C&O south of Covington, the Falmouth line in Covington
    cov = overture_route([(39.0513, -84.4994), (39.0732, -84.5092), (39.0975, -84.5284)])
    kw.open_folder("RER-2")
    kw.line("Historic C&O Covington - Union Terminal",
            [(a, b, 0.0) for a, b in dedupe(cov + bezier(cov[-1], (39.1030, -84.5345), (39.1060, -84.5418), CUT_TOP)[1:])],
            "ff00a5ff", 3.0, "C&O through Covington and over the C&O bridge along today's CSX (Overture rail); "
            "the C&O viaduct into Union Terminal is an approximate curve, redraw it")
    kw.close_folder()

    # RER-5: Norwood Central west to the head of the drawn Mill Creek trunk at Ivorydale
    nw = overture_route([(39.1620, -84.4473), (39.1700, -84.5040)])
    nw = dedupe([(39.16198, -84.44731)] + nw + [(39.17003, -84.50404)])
    kw.open_folder("RER-5")
    kw.line("Historic Norwood - Ivorydale", [(a, b, 0.0) for a, b in nw], "ff00a5ff", 3.0,
            "Existing Norwood-CUT ROW from Norwood Central west to Ivorydale, along today's track (Overture rail)")
    kw.close_folder()

    kw.close_folder()
    kw.save(HIST)
    print(f"wrote {HIST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
