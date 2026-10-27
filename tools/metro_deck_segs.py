"""Ties each Metro line of the Rail Profiles page to the Mill Creek Deck's Metro pieces (Ben, 2026-10-27: "This matters for
metro lines too, arguably moreso"): writes `segs` into data/profile/lines/Line_*.json, the same form as the RER routes
(tools/rer_deck_routes.py), so the check and --apply there cover the Metro lines.

Each Deck piece named for the line ("Metro Line 3") is placed by projecting its ends onto the line's current path, in
path order; a piece whose ends land within half its length of each other (a loop or stub at a terminal) is left out.
Where the Deck draws nothing for more than GAP metres (the line leaves the Deck's region, or a stretch it does not draw),
a 'profiles' seg keeps the line's own path. Chainages are the current path's, so --apply maps everything along.

    python tools/metro_deck_segs.py [--write]
"""
import argparse
import os
import sys

from shapely.geometry import LineString, Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rer_deck_routes import SITE, chain_of, deck_pieces, jload, jsave, route_xy   # noqa: E402

GAP = 20.0


def segs_for(r, pieces):
    L = LineString(route_xy(r))
    _, chain, at = chain_of(r['path'])
    lab = 'Metro ' + r['line']
    mine = []
    for pid, (nm, xy) in pieces.items():
        if nm != lab or len(xy) < 2:
            continue
        P = LineString(xy)
        a, b = chain(xy[0]), chain(xy[-1])
        if abs(b - a) < 0.5 * P.length:
            print(f"  {pid}: left out (ends {a:.0f} / {b:.0f}, {P.length:.0f} m long)")
            continue
        mine.append((min(a, b), max(a, b), pid, P, b >= a))
    mine.sort()
    if not mine:   # the Deck draws none of it (CVG Express): not tied
        return []
    segs, cur = [], 0.0
    rnd = lambda p: [round(p[0], 1), round(p[1], 1)]

    def prof(c0, c1):
        segs.append({'piece': 'profiles', 'lines': lab, 'u': rnd(at(c0).coords[0]), 'v': rnd(at(c1).coords[0]), 'c0': round(c0, 1), 'c1': round(c1, 1)})
    for lo, hi, pid, P, fwd in mine:
        if lo - cur > GAP:
            prof(cur, lo)
            cur = lo
        pa, pb = (0.0, P.length) if fwd else (P.length, 0.0)
        if lo < cur - 1:   # overlaps the previous piece: start where that one ended
            pa = P.project(at(cur))
        u, v = P.interpolate(pa), P.interpolate(pb)
        segs.append({'piece': pid, 'lines': lab, 'pa': round(pa, 1), 'pb': round(pb, 1), 'fwd': fwd, 'u': rnd(u.coords[0]), 'v': rnd(v.coords[0]),
                     'c0': round(cur, 1), 'c1': round(max(hi, cur), 1)})
        cur = max(hi, cur)
    if r['length_m'] - cur > GAP:
        prof(cur, r['length_m'])
    if segs:
        segs[-1]['c1'] = r['length_m']
    return segs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    pieces = deck_pieces()
    for e in jload(os.path.join(SITE, 'lines', 'index.json')):
        fn = os.path.join(SITE, 'lines', e['id'] + '.json')
        r = jload(fn)
        print(e['id'])
        segs = segs_for(r, pieces)
        for s in segs:
            print(f"  {s['piece']:28s} c {s['c0']:9.1f} - {s['c1']:9.1f}")
        if a.write and segs:
            r['segs'] = segs
            jsave(fn, r)


if __name__ == '__main__':
    main()
