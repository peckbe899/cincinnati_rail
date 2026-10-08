"""Digitize the historic RER-1 approaches to Union Terminal from a Google Earth screenshot.

data/reference/rer1_historic_approaches.webp shows the pre-RER routes into Union Terminal on
their original railroad rights of way through the Mill Creek yards: Oxford trains (blue) left
today's RER-1 at Hopple, Miamitown trains (green) left it at Westwood and joined the Oxford
route. The screenshot is georeferenced by an affine fit to four RER-1 station markers whose
coordinates are in Cincinnati_Rail.kmz (residuals printed; ~2 m per pixel). The lines are
traced by colour, simplified, and their ends snapped onto the drawn track so the network
joins up. Output: data/kmz/cincinnati_historic.kml (folder "Cincinnati Historic/RER-1").

Replace this with lines drawn in Google Earth when available (same folder and names).

    python tools/digitize_historic.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from railsim.geo import LocalProjection, cumulative_length, project_point_to_polyline  # noqa: E402
from railsim.horizontal import simplify  # noqa: E402
from railsim.kml import KmlWriter, read_kmz, select  # noqa: E402

IMG = ROOT / "data/reference/rer1_historic_approaches.webp"
OUT = ROOT / "data/kmz/cincinnati_historic.kml"
# pixel (x, y) of station markers -> RER-1 station placemark name and lat/lon
CONTROL = [((255, 787), (39.12439, -84.54345)),   # Western Hills (Mill Creek)
           ((126, 822), (39.12377, -84.54642)),   # Westwood
           ((219, 1333), (39.11460, -84.54435)),  # Evans
           ((636, 1592), (39.10974, -84.53471))]  # Union Terminal


def trace(mask, y0, y1, step=3):
    """Centre line of a mostly north-south coloured line: mean x of each pixel row."""
    pts = []
    for y in range(y0, y1 + 1, step):
        xs = np.nonzero(mask[y])[0]
        if len(xs):
            pts.append((float(xs.mean()), float(y)))
    return np.array(pts)


def main():
    im = np.asarray(Image.open(IMG).convert("RGB")).astype(int)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    blue = (B > 180) & (G > 120) & (R < 110) & (B - R > 100)
    green = (G > 170) & (G - R > 50) & (G - B > 110)

    proj = LocalProjection(39.12, -84.54)
    px = np.array([[x, y, 1.0] for (x, y), _ in CONTROL])
    xy = np.array([proj.to_xy(la, lo) for _, (la, lo) in CONTROL], float)
    A, *_ = np.linalg.lstsq(px, xy, rcond=None)
    res = np.hypot(*(px @ A - xy).T)
    print("affine fit residuals (m):", np.round(res, 1))

    def to_xy(p):
        return np.column_stack([p, np.ones(len(p))]) @ A

    ys = np.nonzero(blue)[0]
    oxford = to_xy(trace(blue, int(ys.min()), int(ys.max())))
    # green runs on its own until it meets the blue line (shared ROW below that)
    gy = np.nonzero(green)[0]
    g = trace(green, int(gy.min()), int(gy.max()))
    b_px = trace(blue, int(ys.min()), int(ys.max()))
    bx = np.interp(g[:, 1], b_px[:, 1], b_px[:, 0])
    join = int(np.argmax(np.abs(g[:, 0] - bx) < 6.0))
    miamitown = to_xy(g[:join + 1])

    # snap ends onto the drawn RER-1 track, and the Miamitown line's end onto the Oxford one
    pms = read_kmz(ROOT / "data/kmz/Cincinnati_Rail.kmz")
    track = [np.array(proj.to_xy([c[0] for c in ln], [c[1] for c in ln]), float).T
             for p in select(pms, "Cincinnati RER/RER-1") if p.lines for ln in p.lines]

    def snap(pt, lines):
        best = None
        for ln in lines:
            s = cumulative_length(ln)
            ch, d, _ = project_point_to_polyline(float(pt[0]), float(pt[1]), ln, s)
            if best is None or d < best[0]:
                best = (d, np.array([np.interp(ch, s, ln[:, 0]), np.interp(ch, s, ln[:, 1])]))
        print(f"   snapped {best[0]:.0f} m")
        return best[1]

    oxford = simplify(oxford, 3.0)
    miamitown = simplify(miamitown, 3.0)
    oxford[0], oxford[-1] = snap(oxford[0], track), snap(oxford[-1], track)
    miamitown[0] = snap(miamitown[0], track)
    miamitown[-1] = snap(miamitown[-1], [oxford])

    kw = KmlWriter("Cincinnati historic rights of way")
    kw.open_folder("Cincinnati Historic")
    kw.open_folder("RER-1")
    for name, line, col in (("Historic Oxford approach", oxford, "ffffa000"),
                            ("Historic Miamitown approach", miamitown, "ff00e070")):
        la, lo = proj.to_latlon(line[:, 0], line[:, 1])
        kw.line(name, [(float(a), float(b), 0.0) for a, b in zip(la, lo)], col, 3.0,
                "pre-RER approach to Union Terminal on the original ROW; digitized from "
                "data/reference/rer1_historic_approaches.webp (approximate, ~20 m)")
        print(f"{name}: {cumulative_length(line)[-1] / 1000:.2f} km, {len(line)} vertices")
    kw.close_folder()
    kw.close_folder()
    kw.save(OUT)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
