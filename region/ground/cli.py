"""python -m region.ground <command>

  works  [--year Y] [--timeline canon|real]        which works count at Y and which are skipped, with the reasons
  compose --year Y --bbox x0 y0 x1 y1 --out F.tif   the ground at Y as a GeoTIFF (and F_src.tif: the layer per cell)
  check  [--tile 4000] [--out report.json]         compose 2026 over the 2026 canon ground's extent, tile by tile, and
                                                   compare with it: inside the works' footprints (must agree) and
                                                   outside them (the change the works do not govern)
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from . import layers as L
from .compose import compose, works_for_year
from .raster import raster_bounds, read, write


def cmd_works(a):
    present, skipped = works_for_year(a.year, a.timeline)
    print("works at %d (%s):" % (a.year, a.timeline))
    for w in present:
        print("  + %-24s %s..%s  %s" % (w.id, w.built_from, w.built_by, w.kind))
    for wid, why in skipped:
        print("  - %-24s %s" % (wid, why))
    for c in L.conflicts():
        print("conflict:", c)


def cmd_compose(a):
    g = compose(a.year, tuple(a.bbox), a.timeline)
    zi = np.where(np.isnan(g.z), L.ND, np.round(g.z * 10)).astype(np.int16)
    write(a.out, zi, g.target)
    write(a.out.replace(".tif", "_src.tif"), g.src, g.target, nodata=0, dtype="uint8")
    print("wrote", a.out, g.target.shape, "applied:", g.applied, "skipped:", g.skipped)


def cmd_check(a):
    x0, y0, x1, y1 = raster_bounds(L.MAP3)
    T = a.tile * L.STEP
    tot = dict(inside=dict(n=0, agree=0, sum_abs=0.0, max=0.0), outside=dict(n=0, hist={}, sum=0.0, sum_abs=0.0, max=0.0),
               outside_in_survey=dict(n=0, sum_abs=0.0), outside_off_survey=dict(n=0, sum_abs=0.0), per_layer={})
    bins = [-1e9, -10, -5, -2, -1, -0.5, -0.25, 0.25, 0.5, 1, 2, 5, 10, 1e9]
    tiles = 0
    for ty in np.arange(y0, y1, T):
        for tx in np.arange(x0, x1, T):
            bbox = (tx, ty, min(tx + T, x1), min(ty + T, y1))
            g = compose(2026, bbox, "canon")
            m3 = read(L.MAP3, g.target).astype(np.float32); m3[m3 == L.ND] = np.nan; m3 /= 10
            cover = read(L.SURVEY_COVER, g.target, nodata=0, dtype=np.uint8) == 1
            ok = ~np.isnan(g.z) & ~np.isnan(m3)
            diff = g.z - m3
            inside = ok & (g.src >= 10)
            outside = ok & (g.src == L.SRC["canon_1912"])
            d_in = diff[inside]; d_out = diff[outside]
            tot["inside"]["n"] += int(inside.sum()); tot["inside"]["agree"] += int((np.abs(d_in) <= 0.051).sum())
            tot["inside"]["sum_abs"] += float(np.abs(d_in).sum()); tot["inside"]["max"] = max(tot["inside"]["max"], float(np.abs(d_in).max()) if d_in.size else 0)
            tot["outside"]["n"] += int(outside.sum()); tot["outside"]["sum"] += float(d_out.sum()); tot["outside"]["sum_abs"] += float(np.abs(d_out).sum())
            tot["outside"]["max"] = max(tot["outside"]["max"], float(np.abs(d_out).max()) if d_out.size else 0)
            h, _ = np.histogram(d_out, bins); hist = tot["outside"]["hist"]
            for k, v in zip(range(len(h)), h):
                hist[k] = hist.get(k, 0) + int(v)
            oi = outside & cover; oo = outside & ~cover
            tot["outside_in_survey"]["n"] += int(oi.sum()); tot["outside_in_survey"]["sum_abs"] += float(np.abs(diff[oi]).sum())
            tot["outside_off_survey"]["n"] += int(oo.sum()); tot["outside_off_survey"]["sum_abs"] += float(np.abs(diff[oo]).sum())
            for code in np.unique(g.src[inside]):
                mm = inside & (g.src == code); pl = tot["per_layer"].setdefault(int(code), dict(n=0, agree=0, sum_abs=0.0))
                pl["n"] += int(mm.sum()); pl["agree"] += int((np.abs(diff[mm]) <= 0.051).sum()); pl["sum_abs"] += float(np.abs(diff[mm]).sum())
            tiles += 1
            print("tile %d %s inside %d outside %d" % (tiles, bbox, inside.sum(), outside.sum()), file=sys.stderr)
    names = compose(2026, (x0, y0, x0 + 4, y0 + 4)).code_names()
    rep = dict(tiles=tiles, step_m=L.STEP, inside_footprints=dict(cells=tot["inside"]["n"], agree_within_5cm=tot["inside"]["agree"],
               mean_abs_m=tot["inside"]["sum_abs"] / max(1, tot["inside"]["n"]), max_abs_m=tot["inside"]["max"],
               per_layer={names.get(c, c): dict(cells=v["n"], agree_within_5cm=v["agree"], mean_abs_m=v["sum_abs"] / max(1, v["n"])) for c, v in tot["per_layer"].items()}),
               outside_footprints=dict(cells=tot["outside"]["n"], mean_m=tot["outside"]["sum"] / max(1, tot["outside"]["n"]),
               mean_abs_m=tot["outside"]["sum_abs"] / max(1, tot["outside"]["n"]), max_abs_m=tot["outside"]["max"],
               hist_m={"%s..%s" % (bins[k], bins[k + 1]): v for k, v in sorted(tot["outside"]["hist"].items())},
               in_1912_survey=dict(cells=tot["outside_in_survey"]["n"], mean_abs_m=tot["outside_in_survey"]["sum_abs"] / max(1, tot["outside_in_survey"]["n"])),
               off_1912_survey=dict(cells=tot["outside_off_survey"]["n"], mean_abs_m=tot["outside_off_survey"]["sum_abs"] / max(1, tot["outside_off_survey"]["n"]))))
    s = json.dumps(rep, indent=1)
    if a.out:
        open(a.out, "w").write(s)
    print(s)


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m region.ground", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("works"); w.add_argument("--year", type=int, default=L.PRESENT); w.add_argument("--timeline", default="canon"); w.set_defaults(f=cmd_works)
    c = sub.add_parser("compose"); c.add_argument("--year", type=int, required=True); c.add_argument("--bbox", type=float, nargs=4, required=True)
    c.add_argument("--timeline", default="canon"); c.add_argument("--out", required=True); c.set_defaults(f=cmd_compose)
    k = sub.add_parser("check"); k.add_argument("--tile", type=int, default=4000); k.add_argument("--out"); k.set_defaults(f=cmd_check)
    a = p.parse_args(argv); a.f(a)


if __name__ == "__main__":
    main()
